"""Prepare a bounded offline Qwen prompt/sample-rate presentation follow-up."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import wave


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from audio_assessment import _prepare
from audio_comparison import inspect_wav, read_pcm16


PILOT = ROOT / "build/audio-assessment-openrouter-20261013"
REPRO = ROOT / "build/audio-assessment-openrouter-repro-20261013"
CONTROLS = ROOT / "build/audio-perception-controls-20261013/inputs-local"
CONTROL_TRIAL = ROOT / "build/audio-perception-controls-20261014/qwen"
VERDICT = ROOT / "evidence/follin-contrast/listening-verdict.json"
AFCONVERT = Path("/usr/bin/afconvert")
MODEL = "qwen/qwen3.8-omni-flash"
PROMPT = (
    "Compare the lead sound’s tone color in A (0–8 s) and B (8.5–16.5 s). "
    "Ignore the shared melody and rhythm. Is one lead tone more periodically "
    "changing or wavering in brightness, or is there no audible difference? "
    "Return JSON difference yes/no/uncertain, more_animated A/B/neither/uncertain, "
    "observations, confidence. Do not infer synthesis method."
)


def _sha256(contents):
    return hashlib.sha256(contents).hexdigest()


def _json(path):
    return json.loads(path.read_text())


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def _receipts(directory, case_id):
    records = [(path, _json(path)) for path in sorted(directory.glob("attempt-*.json"))]
    matches = [(path, record) for path, record in records if record.get("id") == case_id and record.get("status") == "complete"]
    if not matches or len({record["audio_sha256"] for _, record in matches}) != 1:
        raise ValueError(f"Missing or conflicting completed audio receipts: {case_id}")
    return matches


def _verified_audio(path, expected, rate, seconds, silence=False):
    audio = read_pcm16(path)
    if audio.sha256 != expected:
        raise ValueError(f"Source fingerprint mismatch: {path.name}")
    if (audio.sample_rate, audio.channels, audio.frames) != (rate, 1, round(seconds * rate)):
        raise ValueError(f"Unexpected source format or frame count: {path.name}")
    if silence and any(audio.samples):
        raise ValueError("Silence control contains nonzero PCM")
    return audio


def _run(command, check=True):
    try:
        return subprocess.run(command, capture_output=True, text=True, check=check, timeout=30)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"Offline conversion failed ({type(error).__name__})") from None


def prepare_presentation(output):
    output = Path(output).resolve()
    if not output.is_relative_to((ROOT / "build").resolve()):
        raise ValueError("Output must be a fresh directory under build/")
    if output.exists():
        raise FileExistsError("Output must be a fresh directory under build/")
    if not AFCONVERT.is_file() or not os.access(AFCONVERT, os.X_OK):
        raise ValueError("Presentation follow-up requires executable /usr/bin/afconvert")
    pilot = _json(PILOT / "trial.json")
    pilot_provenance = _json(PILOT / "provenance.json")
    controls = _json(CONTROLS / "cases.json")
    controls_provenance = _json(CONTROLS / "provenance.json")
    verdict = _json(VERDICT)
    freeform_prompt = next(case["prompt"] for case in pilot["cases"] if case["id"] == "s00")
    category_prompt = next(case["prompt"] for case in controls["cases"] if case["id"] == "c01")
    silence44_receipts = _receipts(PILOT / "results", "s01")
    silence16_receipts = _receipts(CONTROL_TRIAL / "results", "c01")
    silence44 = REPRO / "s01.wav"
    silence16 = CONTROLS / "c01.wav"
    _verified_audio(silence44, silence44_receipts[0][1]["audio_sha256"], 44100, 4, silence=True)
    silence16_hash = controls_provenance["cases"]["c01"]["pcm"]["wav_sha256"]
    if silence16_hash != silence16_receipts[0][1]["audio_sha256"]:
        raise ValueError("16 kHz control provenance and completed receipt disagree")
    _verified_audio(silence16, silence16_hash, 16000, 4, silence=True)
    originals = {}
    receipt_records = {}
    for case_id in ("t01", "t02", "t03"):
        receipts = _receipts(PILOT / "results", case_id)
        expected = pilot_provenance["cases"][case_id]["sha256"]
        if expected != receipts[0][1]["audio_sha256"]:
            raise ValueError(f"Pilot provenance and completed receipt disagree: {case_id}")
        originals[case_id] = _verified_audio(PILOT / f"{case_id}.ab.wav", expected, 44100, 16.5)
        receipt_records[case_id] = [str(path.relative_to(ROOT)) for path, _ in receipts]
    segment_frames, gap_frames = 8 * 44100, 44100 // 2
    aa, ba, ab = (originals[name].samples for name in ("t01", "t02", "t03"))
    first, second = ab[:segment_frames], ab[segment_frames + gap_frames:]
    if first == second or aa[:segment_frames] != first or aa[segment_frames + gap_frames:] != first or ba[:segment_frames] != second or ba[segment_frames + gap_frames:] != first:
        raise ValueError("Pilot comparisons do not contain the declared A/A and reversed A/B segment identities")
    if any(any(value.samples[segment_frames:segment_frames + gap_frames]) for value in originals.values()):
        raise ValueError("Pilot comparison gap contains nonzero PCM")
    if verdict.get("status") != "reviewed" or not any(record["sha256"] == originals["t03"].sha256 for record in verdict["publication"]["files"]):
        raise ValueError("Human verdict is not bound to the exact submitted A/B audio")
    output.mkdir(parents=True, exist_ok=False)
    source_cases = {
        "p01": (silence44, freeform_prompt, "44.1 kHz silence; original freeform prompt"),
        "p02": (silence44, category_prompt, "44.1 kHz silence; category prompt"),
        "p03": (silence16, freeform_prompt, "16 kHz silence; original freeform prompt"),
        "p04": (silence16, category_prompt, "16 kHz silence; category prompt; deliberate exact-payload replication"),
        "p05": (PILOT / "t03.ab.wav", PROMPT, "original A; stationary B; narrower lead-tone prompt"),
        "p06": (PILOT / "t02.ab.wav", PROMPT, "stationary A; original B; narrower lead-tone prompt"),
        "p07": (PILOT / "t01.ab.wav", PROMPT, "original A; original B; identical-pair control"),
    }
    provenance_cases = {}
    cases = []
    for case_id, (source, prompt, role) in source_cases.items():
        path = output / f"{case_id}.wav"
        path.write_bytes(source.read_bytes())
        cases.append({"id": case_id, "wav": path.name, "prompt": prompt})
        provenance_cases[case_id] = {"role": role, "source": str(source.relative_to(ROOT)), "source_sha256": _sha256(source.read_bytes()), "prompt": prompt, "prompt_sha256": _sha256(prompt.encode()), "output": {key: value for key, value in inspect_wav(path).items() if key != "path"}}
    converted = output / ".p08-converted.wav"
    command = [str(AFCONVERT), "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", "-r", "127", str(output / "p05.wav"), str(converted)]
    _run(command)
    audio = read_pcm16(converted)
    if (audio.sample_rate, audio.channels, audio.frames) != (16000, 1, 264000):
        raise ValueError("Resampled comparison must remain exactly 16.5 seconds at 16 kHz")
    if any(audio.samples[128160:135840]):
        raise ValueError("Resampled comparison must preserve the interior of the half-second silent gap")
    path = output / "p08.wav"
    with wave.open(str(converted), "rb") as source:
        pcm = source.readframes(source.getnframes())
    with wave.open(str(path), "wb") as target:
        target.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        target.writeframes(pcm)
    raw_converted_hash = _sha256(converted.read_bytes())
    converted.unlink()
    cases.append({"id": "p08", "wav": "p08.wav", "prompt": PROMPT})
    provenance_cases["p08"] = {"role": "original A; stationary B; narrower lead-tone prompt; 16 kHz resample of p05", "source": "p05.wav", "source_sha256": originals["t03"].sha256, "prompt": PROMPT, "prompt_sha256": _sha256(PROMPT.encode()), "conversion_command": command, "converted_container_sha256": raw_converted_hash, "container_metadata_removed": True, "segments_frames": {"A": [0, 128000], "gap": [128000, 136000], "B": [136000, 264000]}, "output": {key: value for key, value in inspect_wav(path).items() if key != "path"}}
    manifest_path = output / "cases.json"
    _write_json(manifest_path, {"model": MODEL, "max_tokens": 1200, "reasoning": False, "cases": cases})
    prepared = _prepare(manifest_path, output.parent / "results")
    payloads = {case["id"]: case for case in prepared}
    if payloads["p04"]["payload_sha256"] != silence16_receipts[0][1]["payload_sha256"] or payloads["p01"]["payload_sha256"] != silence44_receipts[0][1]["payload_sha256"]:
        raise ValueError("Declared silence replications do not reproduce the earlier exact payloads")
    oracle_cases = []
    for case in prepared:
        case_id = case["id"]
        expected = {"category": "silence", "music": False, "speech": False} if case_id in ("p01", "p02", "p03", "p04") else {"difference": "no" if case_id == "p07" else "yes", "more_animated": "neither" if case_id == "p07" else "B" if case_id == "p06" else "A"}
        oracle_cases.append({"id": case_id, "audio_sha256": case["audio_sha256"], "payload_sha256": case["payload_sha256"], "expected": expected, "basis": "zero PCM" if case_id in ("p01", "p02", "p03", "p04") else "exact segment PCM identity" if case_id == "p07" else "scoped human moving-pulse animation verdict; narrower-question target is an inference"})
    _write_json(output / "oracle.json", {"schema_version": 1, "cases": oracle_cases, "human_evidence": {"path": str(VERDICT.relative_to(ROOT)), "sha256": _sha256(VERDICT.read_bytes()), "date": verdict["date"], "verdict": verdict["verdict"], "scope": verdict["scope"]}, "boundary": "A/B expected direction applies the user's scoped animation judgment to a narrower question. It does not establish a unique lead-tone cue, isolated PWM rate, resampled listening acceptance or general musical ability. p08 has no separate human verdict. Silence is not musical-score ground truth."})
    help_result = _run([str(AFCONVERT), "-h"], check=False)
    version = next((line.strip().split(":", 1)[1].strip() for line in (help_result.stdout + help_result.stderr).splitlines() if line.strip().startswith("Version:")), None)
    _write_json(output / "provenance.json", {"schema_version": 1, "generator": str(Path(__file__).resolve().relative_to(ROOT)), "generator_sha256": _sha256(Path(__file__).read_bytes()), "pilot_provenance": {"path": str((PILOT / "provenance.json").relative_to(ROOT)), "sha256": _sha256((PILOT / "provenance.json").read_bytes())}, "controls_provenance": {"path": str((CONTROLS / "provenance.json").relative_to(ROOT)), "sha256": _sha256((CONTROLS / "provenance.json").read_bytes())}, "completed_receipts": {**receipt_records, "silence44": [str(path.relative_to(ROOT)) for path, _ in silence44_receipts], "silence16": [str(path.relative_to(ROOT)) for path, _ in silence16_receipts]}, "afconvert": {"path": str(AFCONVERT), "sha256": _sha256(AFCONVERT.read_bytes()), "version": version, "version_command": [str(AFCONVERT), "-h"]}, "gain": 1, "normalization": False, "cases": provenance_cases, "deliberate_replications": {"p01": "original 44.1 kHz freeform silence exact payload", "p04": "basic-control c01 16 kHz category silence exact payload"}, "boundary": "cases.json contains anonymous IDs, filenames and prompts. Oracle/provenance remain local and must not be attached. All oracle cases bind to exact audio and payload hashes."})
    return manifest_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(prepare_presentation(args.output))
    except (ValueError, KeyError, OSError, wave.Error) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
