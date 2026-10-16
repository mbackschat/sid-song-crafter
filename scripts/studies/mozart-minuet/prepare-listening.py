"""Check the Mozart native duplication and prepare its fixed-gain stereo review."""

import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import sys
import wave

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from audio_comparison import Pcm16, measure_pcm, prepare_window_comparison, read_pcm16


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write_audio(path, audio):
    samples = array("h", audio.samples)
    if sys.byteorder != "little":
        samples.byteswap()
    with path.open("xb") as handle:
        with wave.open(handle, "wb") as target:
            target.setparams((audio.channels, 2, audio.sample_rate, 0, "NONE", "not compressed"))
            target.writeframes(samples.tobytes())


def verify_frames(frames, conversion):
    require(isinstance(frames, list) and bool(frames), "Expected complete post-call register frames")
    seconds = (conversion["totalTicks"] + 1) / conversion["ticksPerSecond"] + 1
    expected_calls = math.ceil(seconds * conversion["ticksPerSecond"]) + 1
    require(len(frames) == expected_calls, "Register frames do not cover the complete native audit")
    for index, frame in enumerate(frames):
        require(len(frame) == 50, f"Expected two concatenated SID register banks at call {index}")
        require(frame[:14] == frame[25:39], f"Duplicated melody/bass registers differ at call {index}")
        require(frame[24] & 15 == frame[49] & 15, f"Chip master volumes differ at call {index}")
        require(not (frame[24] & 128 or frame[49] & 128), f"An inner voice is disconnected at call {index}")
        require(not (frame[23] & 7 or frame[48] & 7), f"Unexpected oscillator filter routing at call {index}")
        for offset in (4, 11, 18, 29, 36, 43):
            require(not frame[offset] & 6, f"Unexpected cross-oscillator dependency at call {index}")

def prepare(mono_path, stereo_path, frames_path, conversion_path, output):
    require(not output.exists(), "Use a fresh output directory")
    mono, stereo = read_pcm16(mono_path), read_pcm16(stereo_path)
    require(mono.channels == 1 and stereo.channels == 2, "Expected single-SID mono and native dual-SID stereo")
    require((mono.sample_rate, mono.frames) == (stereo.sample_rate, stereo.frames), "Compared complete performances must have identical timing")
    frames = json.loads(frames_path.read_text())
    conversion = json.loads(conversion_path.read_text())
    verify_frames(frames, conversion)
    require(stereo.samples[::2] != stereo.samples[1::2], "Stereo has no distinct side information")
    fold = Pcm16(stereo.sample_rate, 1, stereo.frames,
                 array("h", (round((a + b) / 2) for a, b in zip(stereo.samples[::2], stereo.samples[1::2]))), "")
    expanded_mono = Pcm16(mono.sample_rate, 2, mono.frames,
                         array("h", (sample for value in mono.samples for sample in (value, value))), "")
    metrics = {}
    for name, audio in (("mono", mono), ("stereo", stereo), ("foldDown", fold)):
        metrics[name] = measure_pcm(audio)
        require(metrics[name]["clippedSamples"] == 0 and metrics[name]["acRms"] > 0, name + " is clipped or silent")
        tail_count = round(.5 * audio.sample_rate)
        tail = Pcm16(audio.sample_rate, audio.channels, tail_count, audio.samples[-tail_count * audio.channels:], "")
        require(all(channel["acRms"] < 16 for channel in measure_pcm(tail)["perChannel"]), name + " has an unsettled tail")
    output.mkdir(parents=True)
    write_audio(output / "single-sid-centered.wav", expanded_mono)
    write_audio(output / "stereo-fold-down.wav", fold)
    for name, start, end in (("phrase", 58, 76), ("ending", 132, 146)):
        prepare_window_comparison(output / "single-sid-centered.wav", stereo_path,
                                  output / ("mono-then-stereo-" + name), start_seconds=start, end_seconds=end)
    report = {
        "schemaVersion": 1, "passed": True,
        "inputs": {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in (mono_path, stereo_path, frames_path, conversion_path)},
        "checkedCalls": len(frames), "duplicatedVoiceRegisters": [0, 1],
        "outputMatrix": [[1, 0], [0, 1]], "monoFoldDownMatrix": [[.5, .5]],
        "normalization": "none; one unity gain for both sides and both conditions",
        "audio": metrics,
        "scope": "Complete post-call melody/bass register equality across chips; distinct inner source parts on opposite buses. No physical phase coherence or perceived center is claimed. Fold-down is not the independently reduced single-SID score.",
        "listeningVerdict": None,
    }
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"output": str(output), "checkedCalls": len(frames), "passed": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mono", type=Path)
    parser.add_argument("stereo", type=Path)
    parser.add_argument("frames", type=Path)
    parser.add_argument("conversion", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.mono, args.stereo, args.frames, args.conversion, args.output)
