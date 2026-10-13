"""Prepare the pinned, anonymous Gauntlet audio-assessment pilot without network access."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import wave


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from audio_comparison import prepare_window_comparison


SOURCES = {
    "reference.wav": "96000bb434c2fa7e17a2264f2c13c7b78de1e2e83edbec1305870500a7378112",
    "stationary-pulse.wav": "18079bcbbe3e5ef27fa354eddf6f46d117d730ba6f344c9f2fe731995f854fce",
}
PROMPT = (
    "Listen to the attached instrumental audio. Segment A is 0–8 seconds; "
    "after 0.5 seconds of silence, segment B is 8.5–16.5 seconds. "
    "Compare the audible timbre, modulation, balance and phrasing. "
    "Do you hear a meaningful difference? If so describe it concretely and identify "
    "which segment has more animated or changing tone. No meaningful difference "
    "and uncertainty are valid answers. Do not infer how the sounds were produced. "
    "Reply with JSON fields difference (yes/no/uncertain), more_animated "
    "(A/B/neither/uncertain), observations (short text), confidence (low/medium/high)."
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="qwen/qwen3.8-omni-flash")
    parser.add_argument("--reasoning", action="store_true")
    parser.add_argument("--reasoning-effort", choices=["low", "medium", "high"])
    args = parser.parse_args()
    if args.reasoning_effort and not args.reasoning:
        parser.error("--reasoning-effort requires --reasoning")
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "build"):
        parser.error("Output must be a fresh directory under build/.")
    sources = ROOT / "build/gauntlet-listening"
    for filename, expected in SOURCES.items():
        if hashlib.sha256((sources / filename).read_bytes()).hexdigest() != expected:
            raise SystemExit(f"Source fingerprint mismatch: {filename}")
    output.mkdir(parents=True, exist_ok=False)
    original, stationary = (sources / name for name in SOURCES)
    with wave.open(str(original), "rb") as source:
        params = source.getparams()
        source.setpos(16 * params.framerate)
        pcm = source.readframes(4 * params.framerate)
    with wave.open(str(output / "s00.wav"), "wb") as target:
        target.setparams(params)
        target.writeframes(pcm)
    with wave.open(str(output / "s01.wav"), "wb") as target:
        target.setparams(params)
        target.writeframes(bytes(len(pcm)))
    cases = [{"id": "s00", "wav": "s00.wav", "prompt":
              "Describe the audible sounds in this short clip in at most three sentences. "
              "State whether there is music or speech and describe the instrumental texture. "
              "If you cannot hear or assess the audio, say so."}]
    mapping = {}
    for case_id, first, second, role in [
        ("t01", original, original, "identical A/A control"),
        ("t02", stationary, original, "stationary first, moving pulse second"),
        ("t03", original, stationary, "moving pulse first, stationary second"),
    ]:
        report = prepare_window_comparison(first, second, output / case_id,
                                           start_seconds=16, end_seconds=24)
        cases.append({"id": case_id, "wav": f"{case_id}.ab.wav", "prompt": PROMPT})
        mapping[case_id] = {"role": role, "sha256": report["comparison"]["sha256"]}
    manifest = {"model": args.model, "max_tokens": 1200, "cases": cases}
    if args.reasoning:
        manifest["reasoning"] = True
    if args.reasoning_effort:
        manifest["reasoning_effort"] = args.reasoning_effort
    for name, document in {
        "trial": manifest,
        "pilot": {**manifest, "cases": cases + [{**cases[0], "id": "s01", "wav": "s01.wav"}]},
        "smoke": {**manifest, "cases": cases[:1]},
        "reasoning": {**manifest, "reasoning": True, "cases": cases[1:]},
        "silence": {**manifest, "cases": [{**cases[0], "id": "s01", "wav": "s01.wav"}]},
    }.items():
        (output / f"{name}.json").write_text(json.dumps(document, indent=2) + "\n")
    (output / "provenance.json").write_text(json.dumps({
        "sources": SOURCES, "sourceWindowSeconds": [16, 24],
        "smokeWindowSeconds": [16, 20], "gain": 1, "gapSeconds": 0.5,
        "silenceControl": "Four seconds of zero PCM, same format and prompt as smoke.",
        "cases": mapping,
        "reference": "docs/research/composition/follin-contrast.md",
        "boundary": "Reference-derived audio stays local; model receives only anonymous prompt and PCM.",
    }, indent=2) + "\n")
    print(output / "trial.json")


if __name__ == "__main__":
    main()
