"""Prepare anonymous audio-perception controls offline; no API calls or credentials."""

import argparse
import array
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import wave


ROOT = Path(__file__).resolve().parents[3]
SAMPLE_RATE = 16000
AMPLITUDE = 8192
FADE_SECONDS = 0.01
NOISE_SEED = 20261013
SPEECH_TEXT = "The blue lantern is beside seven wooden boxes."
SPEECH_VOICE = "Samantha"
SAY = Path("/usr/bin/say")
AFCONVERT = Path("/usr/bin/afconvert")
PROMPT = (
    "Listen to the attached audio and identify the dominant audible sound. "
    "Reply with JSON fields category, evidence, transcript. Category must be one "
    "of silence, speech, steady_tone, changing_tone, noise, repeated_tones, other, "
    "uncertain. Give brief evidence based on what you hear. If speech is present, "
    "transcribe it in transcript; otherwise use an empty string. If you cannot "
    "hear or assess the audio, choose uncertain."
)


def _sha256(contents):
    return hashlib.sha256(contents).hexdigest()


def _write_json(path, document):
    path.write_text(json.dumps(document, indent=2) + "\n")


def _write_pcm(path, samples):
    pcm = array.array("h", samples)
    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(str(path), "wb") as target:
        target.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
        target.writeframes(pcm.tobytes())


def _tone(seconds, frequency, end_frequency=None):
    frames = round(seconds * SAMPLE_RATE)
    fade_frames = round(FADE_SECONDS * SAMPLE_RATE)
    slope = 0 if end_frequency is None else (end_frequency - frequency) / seconds
    samples = []
    for frame in range(frames):
        time = frame / SAMPLE_RATE
        phase = 2 * math.pi * (frequency * time + 0.5 * slope * time * time)
        envelope = min(1, frame / fade_frames, (frames - 1 - frame) / fade_frames)
        samples.append(round(AMPLITUDE * envelope * math.sin(phase)))
    return samples


def _pcm_info(path):
    with wave.open(str(path), "rb") as source:
        params = source.getparams()
        pcm = source.readframes(params.nframes)
    if (params.nchannels, params.sampwidth, params.framerate, params.comptype) != (1, 2, SAMPLE_RATE, "NONE"):
        raise ValueError("Controls must be 16 kHz mono PCM16 WAV")
    if not 0 < params.nframes <= 30 * SAMPLE_RATE or len(pcm) != params.nframes * 2:
        raise ValueError("Control PCM must be complete, nonempty and no longer than 30 seconds")
    samples = array.array("h", pcm)
    if sys.byteorder != "little":
        samples.byteswap()
    return {
        "sample_rate_hz": params.framerate,
        "channels": params.nchannels,
        "sample_width_bits": params.sampwidth * 8,
        "frames": params.nframes,
        "duration_seconds": params.nframes / params.framerate,
        "minimum_sample": min(samples),
        "maximum_sample": max(samples),
        "nonzero_samples": sum(value != 0 for value in samples),
        "clipped_samples": sum(value in (-32768, 32767) for value in samples),
        "rms": math.sqrt(sum(value * value for value in samples) / len(samples)) / 32768,
        "pcm_sha256": _sha256(pcm),
        "wav_sha256": _sha256(path.read_bytes()),
    }


def _require_speech_tools():
    if any(not path.is_file() or not os.access(path, os.X_OK) for path in (SAY, AFCONVERT)):
        raise ValueError("Offline speech requires executable /usr/bin/say and /usr/bin/afconvert; no complete control bundle was created")


def _run(command, check=True):
    try:
        return subprocess.run(command, capture_output=True, text=True, check=check, timeout=30)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"Offline speech command failed: {command[0]} ({type(error).__name__})") from None


def _synthesize_speech(path):
    source = path.with_suffix(".aiff")
    converted = path.with_name(".c06-converted.wav")
    commands = [
        [str(SAY), "-v", SPEECH_VOICE, "-r", "150", "-o", str(source), SPEECH_TEXT],
        [str(AFCONVERT), "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(source), str(converted)],
    ]
    for command in commands:
        _run(command)
    info = _pcm_info(converted)
    if info["nonzero_samples"] == 0:
        raise ValueError("Offline speech produced only zero PCM")
    with wave.open(str(converted), "rb") as audio:
        samples = array.array("h", audio.readframes(audio.getnframes()))
    if sys.byteorder != "little":
        samples.byteswap()
    # Re-encode PCM because afconvert's container metadata must not expose source labels.
    _write_pcm(path, samples)
    converted.unlink()
    version_command = [str(AFCONVERT), "-h"]
    help_result = _run(version_command, check=False)
    afconvert_version = next((line.strip().split(":", 1)[1].strip() for line in (help_result.stdout + help_result.stderr).splitlines() if line.strip().startswith("Version:")), None)
    return {
        "method": "offline macOS speech synthesis",
        "text": SPEECH_TEXT,
        "voice": SPEECH_VOICE,
        "rate_words_per_minute": 150,
        "commands": commands,
        "source_file": source.name,
        "source_sha256": _sha256(source.read_bytes()),
        "converted_wav_sha256": info["wav_sha256"],
        "container_metadata_removed": True,
        "tools": {
            "say": {"path": str(SAY), "sha256": _sha256(SAY.read_bytes()), "version": None, "version_note": "say does not expose a version option"},
            "afconvert": {"path": str(AFCONVERT), "sha256": _sha256(AFCONVERT.read_bytes()), "version": afconvert_version, "version_command": version_command},
        },
        "macos_version": platform.mac_ver()[0] or None,
    }


def prepare_controls(output, model="qwen/qwen3.8-omni-flash", reasoning=False, reasoning_effort=None):
    output = Path(output).resolve()
    if not output.is_relative_to((ROOT / "build").resolve()):
        raise ValueError("Output must be a fresh directory under build/")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("Model must be a nonempty string")
    if type(reasoning) is not bool or reasoning_effort not in (None, "low", "medium", "high"):
        raise ValueError("Reasoning must be boolean and effort must be low, medium or high")
    if reasoning_effort is not None and not reasoning:
        raise ValueError("--reasoning-effort requires --reasoning")
    if output.exists():
        raise FileExistsError("Output must be a fresh directory under build/")
    _require_speech_tools()
    output.mkdir(parents=True, exist_ok=False)
    noise = random.Random(NOISE_SEED)
    beeps = [0] * (4 * SAMPLE_RATE)
    beep = _tone(0.4, 700)
    for start in (0.4, 1.7, 3.0):
        frame = round(start * SAMPLE_RATE)
        beeps[frame:frame + len(beep)] = beep
    signals = {
        "c01": ([0] * (4 * SAMPLE_RATE), "silence", {"method": "zero PCM", "duration_seconds": 4}),
        "c02": (_tone(4, 440), "steady_tone", {"method": "sine", "duration_seconds": 4, "frequency_hz": 440}),
        "c03": (_tone(4, 220, 880), "changing_tone", {"method": "linear sine sweep", "duration_seconds": 4, "start_frequency_hz": 220, "end_frequency_hz": 880}),
        "c04": ([noise.randint(-6553, 6553) for _ in range(4 * SAMPLE_RATE)], "noise", {"method": "uniform independent integer noise", "duration_seconds": 4, "seed": NOISE_SEED, "minimum_sample": -6553, "maximum_sample": 6553, "generator": "random.Random"}),
        "c05": (beeps, "repeated_tones", {"method": "three sine beeps with zero PCM gaps", "duration_seconds": 4, "frequency_hz": 700, "beep_duration_seconds": 0.4, "beep_start_seconds": [0.4, 1.7, 3.0]}),
        "c07": ([0] * (6 * SAMPLE_RATE), "silence", {"method": "zero PCM", "duration_seconds": 6}),
        "c08": (_tone(5, 880), "steady_tone", {"method": "sine", "duration_seconds": 5, "frequency_hz": 880}),
    }
    provenance = {}
    for case_id, (samples, category, synthesis) in signals.items():
        if category in ("steady_tone", "changing_tone", "repeated_tones"):
            synthesis.update({"peak_amplitude_pcm16": AMPLITUDE, "fade_seconds": FADE_SECONDS, "phase_at_start_radians": 0})
        path = output / f"{case_id}.wav"
        _write_pcm(path, samples)
        provenance[case_id] = {"synthesis": synthesis, "pcm": _pcm_info(path)}
    path = output / "c06.wav"
    provenance["c06"] = {"synthesis": _synthesize_speech(path), "pcm": _pcm_info(path)}
    cases = [{"id": f"c{number:02d}", "wav": f"c{number:02d}.wav", "prompt": PROMPT} for number in range(1, 9)]
    manifest = {"model": model, "max_tokens": 1200, "cases": cases}
    if reasoning:
        manifest["reasoning"] = True
    if reasoning_effort is not None:
        manifest["reasoning_effort"] = reasoning_effort
    oracle_cases = [{"id": case["id"], "category": signals[case["id"]][1] if case["id"] in signals else "speech",
                     "audio_sha256": provenance[case["id"]]["pcm"]["wav_sha256"]} for case in cases]
    oracle_cases[5]["required_words"] = ["blue", "lantern", "seven", "wooden", "boxes"]
    _write_json(output / "oracle.json", {
        "schema_version": 1,
        "cases": oracle_cases,
        "gate": {
            "required_case_count": 8,
            "require_all_categories_correct": True,
            "require_all_speech_words": True,
            "transcript_matching": "Case and punctuation ignored; 7 is equivalent to seven",
            "establishes_musical_ability": False,
            "scope": "A pass establishes perception of these elementary controls only; it does not establish musical comparison or judgment",
        },
    })
    _write_json(output / "provenance.json", {
        "schema_version": 1,
        "generator": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[3])),
        "generator_sha256": _sha256(Path(__file__).read_bytes()),
        "python_version": sys.version,
        "prompt_sha256": _sha256(PROMPT.encode()),
        "cases": {case["id"]: provenance[case["id"]] for case in cases},
        "boundary": "cases.json contains anonymous IDs and one neutral prompt; the request includes only that prompt and re-encoded PCM WAV. Oracle and provenance are local and must not be attached.",
    })
    _write_json(output / "cases.json", manifest)
    return output / "cases.json"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="qwen/qwen3.8-omni-flash")
    parser.add_argument("--reasoning", action="store_true")
    parser.add_argument("--reasoning-effort", choices=["low", "medium", "high"])
    args = parser.parse_args(argv)
    try:
        manifest = prepare_controls(args.output, args.model, args.reasoning, args.reasoning_effort)
    except (ValueError, OSError, wave.Error) as error:
        parser.error(str(error))
    print(manifest)


if __name__ == "__main__":
    main()
