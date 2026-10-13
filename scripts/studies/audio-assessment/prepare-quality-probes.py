"""Prepare anonymous, source-pinned Gauntlet quality probes without network access."""

import argparse
import array
import hashlib
import json
from pathlib import Path
import sys
import wave


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from audio_comparison import inspect_wav, read_pcm16


REGISTRY = ROOT / "evidence/follin-contrast/audition-sources.json"
VERDICT = ROOT / "evidence/follin-contrast/listening-verdict.json"
SAMPLE_RATE = 44100
START_FRAME = 16 * SAMPLE_RATE
END_FRAME = 24 * SAMPLE_RATE
DROPOUT_BLOCK_FRAMES = SAMPLE_RATE // 4


def _sha256(contents):
    return hashlib.sha256(contents).hexdigest()


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def _window(path, expected_hash):
    audio = read_pcm16(path)
    if audio.sha256 != expected_hash:
        raise ValueError(f"Source fingerprint mismatch: {path.name}")
    if (audio.sample_rate, audio.channels) != (SAMPLE_RATE, 1) or audio.frames < END_FRAME:
        raise ValueError("Sources must contain at least 24 seconds of 44.1 kHz mono PCM16")
    with wave.open(str(path), "rb") as source:
        source.setpos(START_FRAME)
        pcm = source.readframes(END_FRAME - START_FRAME)
    if len(pcm) != (END_FRAME - START_FRAME) * 2:
        raise ValueError("Source window PCM is truncated")
    return pcm


def _write_wav(path, pcm):
    with path.open("xb") as file:
        with wave.open(file, "wb") as target:
            target.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
            target.writeframes(pcm)


def prepare_quality_probes(output):
    output = Path(output).resolve()
    if not output.is_relative_to((ROOT / "build").resolve()):
        raise ValueError("Output must be a fresh directory under build/")
    if output.exists():
        raise FileExistsError("Output must be a fresh directory under build/")
    registry = json.loads(REGISTRY.read_text())
    verdict = json.loads(VERDICT.read_text())
    records = {record["filename"]: record for record in registry["files"]}
    source_paths = {name: ROOT / "build/gauntlet-listening" / name for name in ("reference.wav", "stationary-pulse.wav")}
    windows = {name: _window(path, records[name]["sha256"]) for name, path in source_paths.items()}
    published = {record["filename"]: record["sha256"] for record in verdict["publication"]["files"]}
    if verdict.get("status") != "reviewed" or any(published[name] != records[name]["sha256"] for name in source_paths):
        raise ValueError("Human verdict must refer to the exact pinned audition sources")
    original = windows["reference.wav"]
    block_bytes = DROPOUT_BLOCK_FRAMES * 2
    dropout = bytearray(original)
    for start in range(block_bytes, len(dropout), 2 * block_bytes):
        dropout[start:start + block_bytes] = bytes(block_bytes)
    pcm_cases = {"q01": original, "q02": windows["stationary-pulse.wav"], "q03": bytes(dropout), "q04": bytes(len(original))}
    if original == pcm_cases["q02"] or not any(original):
        raise ValueError("Original and stationary controls must be audible and distinct")
    for block, start in enumerate(range(0, len(original), block_bytes)):
        expected = original[start:start + block_bytes] if block % 2 == 0 else bytes(block_bytes)
        if pcm_cases["q03"][start:start + block_bytes] != expected:
            raise ValueError("Dropout control must preserve alternating blocks exactly")
    output.mkdir(parents=True, exist_ok=False)
    output_records = {}
    for case_id, pcm in pcm_cases.items():
        path = output / f"{case_id}.wav"
        _write_wav(path, pcm)
        metrics = inspect_wav(path)
        if (metrics["sampleRate"], metrics["channels"], metrics["frames"]) != (SAMPLE_RATE, 1, END_FRAME - START_FRAME):
            raise ValueError("Output WAV format or frame count changed")
        reopened = read_pcm16(path)
        samples = array.array("h", reopened.samples)
        if sys.byteorder != "little":
            samples.byteswap()
        if samples.tobytes() != pcm:
            raise ValueError("Output PCM differs from the prepared control")
        if case_id == "q04" and metrics["peak"] != 0:
            raise ValueError("Silence negative control must contain only zero PCM")
        output_records[case_id] = {"file": path.name, "pcm_sha256": _sha256(pcm), "metrics": {key: value for key, value in metrics.items() if key != "path"}}
    _write_json(output / "oracle.json", {
        "schema_version": 1,
        "cases": [
            {"id": "q01", "audio_sha256": output_records["q01"]["metrics"]["sha256"], "role": "original moving-pulse passage"},
            {"id": "q02", "audio_sha256": output_records["q02"]["metrics"]["sha256"], "role": "same-material stationary-pulse diagnostic"},
            {"id": "q03", "audio_sha256": output_records["q03"]["metrics"]["sha256"], "role": "original with deterministic 50 percent dropout"},
            {"id": "q04", "audio_sha256": output_records["q04"]["metrics"]["sha256"], "role": "digital silence input negative control", "musical_quality_ground_truth": False},
        ],
        "human_preference": {
            "preferred_case": "q01", "other_case": "q02",
            "evidence": str(VERDICT.relative_to(ROOT)), "evidence_sha256": _sha256(VERDICT.read_bytes()),
            "date": verdict["date"], "verdict": verdict["verdict"], "scope": verdict["scope"],
        },
        "hypotheses": [{"higher_quality_case": "q01", "lower_quality_case": "q03", "status": "untested quality hypothesis; no human verdict", "basis": "The dropout transform interrupts half of the original passage with abrupt silence"}],
        "boundary": "Only q01 versus q02 has a retained human preference. Dropout degradation is a hypothesis. Silence tests input handling and has no musical-score ground truth. No absolute scores or complete ordering are declared.",
    })
    _write_json(output / "provenance.json", {
        "schema_version": 1,
        "generator": str(Path(__file__).resolve().relative_to(ROOT)), "generator_sha256": _sha256(Path(__file__).read_bytes()),
        "source_registry": str(REGISTRY.relative_to(ROOT)), "source_registry_sha256": _sha256(REGISTRY.read_bytes()),
        "sources": {name: {"path": str(path.relative_to(ROOT)), "sha256": records[name]["sha256"], "window_pcm_sha256": _sha256(windows[name])} for name, path in source_paths.items()},
        "window": {"sample_rate_hz": SAMPLE_RATE, "channels": 1, "sample_width_bits": 16, "start_frame_inclusive": START_FRAME, "end_frame_exclusive": END_FRAME, "frames": END_FRAME - START_FRAME, "seconds": [16, 24]},
        "gain": 1,
        "dropout": {"case_id": "q03", "source_case": "q01", "block_frames": DROPOUT_BLOCK_FRAMES, "block_seconds": 0.25, "pattern": ["original PCM", "zero PCM"], "period_seconds": 0.5, "zeroed_frame_fraction": 0.5, "zeroed_frames": (END_FRAME - START_FRAME) // 2, "fade": "none; abrupt boundaries"},
        "cases": output_records,
        "boundary": "Local reference-derived audio stays under ignored build/. Only anonymous IDs and filenames appear in cases.json; oracle and provenance must not be uploaded as model inputs.",
    })
    manifest = {"cases": [{"id": case_id, "wav": f"{case_id}.wav", "audio_sha256": output_records[case_id]["metrics"]["sha256"]} for case_id in pcm_cases]}
    _write_json(output / "cases.json", manifest)
    return output / "cases.json"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(prepare_quality_probes(args.output))
    except (ValueError, KeyError, OSError, wave.Error) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
