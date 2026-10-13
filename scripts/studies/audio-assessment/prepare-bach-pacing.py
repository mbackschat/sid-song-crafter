"""Prepare anonymous, source-pinned Bach pacing probes without network access."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import wave


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from audio_assessment import TrialError, _prepare
from audio_comparison import inspect_wav, read_pcm16


SOURCE_DIRECTORY = ROOT / "build/bach-toccata-opening-driven-listening"
SOURCE_REGISTRY = SOURCE_DIRECTORY / "sources.json"
SOURCE_HASHES = {
    "previous-hybrid.wav": "b1a905e379eedecea1df1e405233165850a319d3a14631a2479d6f3ce6102318",
    "driven-hybrid.wav": "62ebf90fc8fa531f016bbcdad4236c01958a5e83d827e0a56efdab330e991b04",
}
SAMPLE_RATE = 44100
WINDOW_FRAMES = 8 * SAMPLE_RATE
GAP_FRAMES = SAMPLE_RATE // 2
PROMPT = (
    "Listen to segment A (0–8 s) and segment B (8.5–16.5 s). Compare their audible "
    "phrasing and pacing. Which segment has more forward motion, and which has "
    "longer holds or gaps? Use same when there is no audible difference and "
    "uncertain when you cannot tell. Return only JSON with audio_presence "
    "(music/silence/other/uncertain), more_forward_motion (A/B/same/uncertain), "
    "longer_holds_or_gaps (A/B/same/uncertain), and observations (short audible observations)."
)
SCOPE = (
    "First eight seconds of the same composition with differing phrasing contain different amounts of the score; "
    "the clips are not aligned to the same notes and do not isolate global tempo. "
    "The full-opening acceptance does not independently establish an eight-second preference. "
    "This tiny trial has no held-out passage and cannot establish model eligibility or adoption."
)


def _sha256(contents):
    return hashlib.sha256(contents).hexdigest()


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def _relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def _window(path, expected_hash):
    audio = read_pcm16(path)
    if audio.sha256 != expected_hash:
        raise ValueError(f"Source fingerprint mismatch: {path.name}")
    if (audio.sample_rate, audio.channels) != (SAMPLE_RATE, 1) or audio.frames < WINDOW_FRAMES:
        raise ValueError("Sources must contain at least eight seconds of 44.1 kHz mono PCM16")
    with wave.open(str(path), "rb") as source:
        pcm = source.readframes(WINDOW_FRAMES)
    return pcm


def _write_audio(path, pcm):
    with path.open("xb") as file:
        with wave.open(file, "wb") as target:
            target.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
            target.writeframes(pcm)
    with wave.open(str(path), "rb") as reopened:
        if reopened.getnframes() * 2 != len(pcm) or reopened.readframes(reopened.getnframes()) != pcm:
            raise ValueError("Output differs from exact prepared PCM")
    return {"file": path.name, "pcm_sha256": _sha256(pcm), "metrics": {key: value for key, value in inspect_wav(path).items() if key != "path"}}


def prepare_bach_pacing(output):
    output = Path(output).resolve()
    if not output.is_relative_to((ROOT / "build").resolve()):
        raise ValueError("Output must be a fresh directory under build/")
    if output.exists():
        raise FileExistsError("Output must be a fresh directory under build/")
    registry = json.loads(SOURCE_REGISTRY.read_text())
    published = {record["filename"]: record for record in registry["files"]}
    if any(published.get(name, {}).get("sha256") != expected for name, expected in SOURCE_HASHES.items()):
        raise ValueError("Source publication does not match the pinned source fingerprints")
    windows = {name: _window(SOURCE_DIRECTORY / name, expected) for name, expected in SOURCE_HASHES.items()}
    previous, driven = windows["previous-hybrid.wav"], windows["driven-hybrid.wav"]
    if previous == driven or not any(previous) or not any(driven):
        raise ValueError("Previous and driven windows must be audible and distinct")
    window = {"sample_rate_hz": SAMPLE_RATE, "channels": 1, "sample_width_bits": 16, "start_frame_inclusive": 0, "end_frame_exclusive": WINDOW_FRAMES, "seconds": [0, 8]}
    sources = {}
    for name, expected in SOURCE_HASHES.items():
        verification_path = Path(published[name]["sourcePath"]).parent / "verification.json"
        verification = json.loads(verification_path.read_text())
        if verification["pcm"]["sha256"] != expected:
            raise ValueError("Source render verification fingerprint mismatch")
        sources[name] = {
            "path": _relative(SOURCE_DIRECTORY / name), "sha256": expected,
            "published_source": published[name], "window": window, "window_pcm_sha256": _sha256(windows[name]),
            "render_verification": {"path": _relative(verification_path), "sha256": _sha256(verification_path.read_bytes())},
            "renderer": verification["renderer"],
            "sid_configuration": {key: verification["audit"][key] for key in ("sidModel", "sidCount", "clockHz", "callRateHz")},
        }
    silence, gap = bytes(WINDOW_FRAMES * 2), bytes(GAP_FRAMES * 2)
    pairs = {"p01": (previous, driven), "p02": (driven, previous), "p03": (driven, driven), "p04": (silence, silence)}
    clips = {"q01": previous, "q02": driven, "q03": silence, "q04": driven}
    output.mkdir(parents=True, exist_ok=False)
    records = {case_id: _write_audio(output / f"{case_id}.wav", first + gap + second) for case_id, (first, second) in pairs.items()}
    records.update({case_id: _write_audio(output / f"{case_id}.wav", pcm) for case_id, pcm in clips.items()})
    qwen = output / "qwen.json"
    _write_json(qwen, {"model": "qwen/qwen3.8-omni-flash", "max_tokens": 1200, "reasoning": False, "cases": [{"id": case_id, "wav": records[case_id]["file"], "audio_sha256": records[case_id]["metrics"]["sha256"], "prompt": PROMPT} for case_id in pairs]})
    _write_json(output / "songbench.json", {"cases": [{"id": case_id, "wav": records[case_id]["file"], "audio_sha256": records[case_id]["metrics"]["sha256"]} for case_id in clips]})
    prepared = _prepare(qwen, output.parent / "qwen-results")
    expected = {
        "p01": {"audio_presence": "music", "more_forward_motion": "B", "longer_holds_or_gaps": "A"},
        "p02": {"audio_presence": "music", "more_forward_motion": "A", "longer_holds_or_gaps": "B"},
        "p03": {"audio_presence": "music", "more_forward_motion": "same", "longer_holds_or_gaps": "same"},
        "p04": {"audio_presence": "silence", "more_forward_motion": "same", "longer_holds_or_gaps": "same"},
    }
    mapping = {"p01": ["previous-hybrid.wav", "driven-hybrid.wav"], "p02": ["driven-hybrid.wav", "previous-hybrid.wav"], "p03": ["driven-hybrid.wav", "driven-hybrid.wav"], "p04": ["zero PCM", "zero PCM"], "q01": ["previous-hybrid.wav"], "q02": ["driven-hybrid.wav"], "q03": ["zero PCM"], "q04": ["driven-hybrid.wav"]}
    _write_json(output / "oracle.json", {
        "schema_version": 1, "source_sha256s": SOURCE_HASHES, "scope": SCOPE,
        "human_context": {"date": "2026-10-14", "verdict": "nice", "accepted_source": "driven-hybrid.wav", "accepted_source_sha256": SOURCE_HASHES["driven-hybrid.wav"], "scope": "Acceptance of the presented full faster hybrid opening and direction for continued arrangement", "eight_second_preference_independently_reviewed": False},
        "qwen": {"cases": [{"id": case["id"], "audio_sha256": case["audio_sha256"], "payload_sha256": case["payload_sha256"], "expected": expected[case["id"]], "basis": "Exact zero PCM" if case["id"] == "p04" else "Exact segment PCM identity" if case["id"] == "p03" else "Differing phrasing schedule and contextual listener feedback; eight-second direction is an inferred hypothesis"} for case in prepared], "criterion": "Require all three declared fields on all four cases; report misses and abstentions without adjusting the prompt"},
        "songbench": {"cases": [{"id": case_id, "audio_sha256": records[case_id]["metrics"]["sha256"], "pcm_sha256": records[case_id]["pcm_sha256"], "sources": mapping[case_id]} for case_id in clips], "primary_dimension": "musicality", "retain_dimensions": ["melody", "arrangement", "musicality", "vocal", "instrumental", "mixing", "structure"], "tentative_ranking": {"higher_case": "q02", "lower_case": "q01", "status": "Inferred contextual hypothesis; not independently listener-reviewed for these eight-second clips"}, "repeatability": {"cases": ["q02", "q04"], "basis": "Exact WAV and PCM identity", "criterion": "Retain absolute differences for all seven dimensions; no adoption threshold"}, "silence": {"case": "q03", "role": "input negative control", "musical_quality_ground_truth": False}},
        "held_out_passage": False, "establishes_model_eligibility": False,
    })
    _write_json(output / "provenance.json", {
        "schema_version": 1, "generator": _relative(Path(__file__)), "generator_sha256": _sha256(Path(__file__).read_bytes()),
        "source_publication": {"path": _relative(SOURCE_REGISTRY), "sha256": _sha256(SOURCE_REGISTRY.read_bytes()), "record": registry},
        "sources": sources, "gain": 1, "normalization": False, "resampling": False, "scope": SCOPE,
        "prompt": PROMPT, "prompt_sha256": _sha256(PROMPT.encode()),
        "pair_segments_frames": {"A": [0, WINDOW_FRAMES], "gap": [WINDOW_FRAMES, WINDOW_FRAMES + GAP_FRAMES], "B": [WINDOW_FRAMES + GAP_FRAMES, 2 * WINDOW_FRAMES + GAP_FRAMES]},
        "cases": {case_id: {**record, "sources": mapping[case_id]} for case_id, record in records.items()},
        "boundary": "Only anonymous audio, prompt and runner settings reach models. Oracle, source names and listener feedback remain local. Original render levels are retained.",
    })
    return qwen


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(prepare_bach_pacing(args.output))
    except (ValueError, KeyError, OSError, wave.Error, TrialError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
