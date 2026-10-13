"""Run or dry-run the three requested model profiles against one control bundle."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[3]
PROFILES = {
    "qwen": {"model": "qwen/qwen3.8-omni-flash", "reasoning": False},
    "gemini": {"model": "google/gemini-3.8-flash", "reasoning": True, "reasoning_effort": "low"},
    "mini": {"model": "openai/gpt-audio-mini", "reasoning": None},
}


def verify_assessment(manifest, oracle, results, report):
    with tempfile.TemporaryDirectory(prefix=".assessment-", dir=report.parent) as temporary:
        verified = Path(temporary) / "assessment.json"
        subprocess.run([sys.executable, str(Path(__file__).with_name("evaluate-controls.py")),
                        str(manifest), str(oracle), str(results), "--output", str(verified)],
                       check=True, timeout=30)
        if report.exists():
            if json.loads(report.read_text()) != json.loads(verified.read_text()):
                raise ValueError("Retained assessment differs from verified inputs, evaluator, or evidence; review it before continuing")
            print(f"Verified retained assessment: {report}", flush=True)
        else:
            with report.open("xb") as target:
                target.write(verified.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--oracle", type=Path, help="Withheld oracle; defaults to INPUTS/oracle.json")
    parser.add_argument("--model", choices=list(PROFILES), action="append")
    parser.add_argument("--execute", action="store_true", help="Make bounded paid requests; otherwise validate only")
    args = parser.parse_args()
    inputs, output = args.inputs.resolve(), args.output.resolve()
    oracle = args.oracle.resolve() if args.oracle is not None else inputs / "oracle.json"
    if not output.is_relative_to(ROOT / "build"):
        parser.error("Output must be under build/.")
    base = json.loads((inputs / "cases.json").read_text())
    if not oracle.is_file():
        parser.error("Missing withheld oracle")
    output.mkdir(parents=True, exist_ok=True)
    for label in args.model or PROFILES:
        directory = output / label
        directory.mkdir(exist_ok=True)
        manifest = {**base, **PROFILES[label], "cases": [
            {**case, "wav": str((inputs / case["wav"]).resolve())} for case in base["cases"]]}
        path = directory / "cases.json"
        path.write_text(json.dumps(manifest, indent=2) + "\n")
        report = directory / "assessment.json"
        if args.execute and report.exists():
            verify_assessment(path, oracle, directory / "results", report)
            continue
        command = [sys.executable, str(ROOT / "scripts/audio_assessment.py"), str(path),
                   "--output", str(directory / "results")]
        if not args.execute:
            command.append("--dry-run")
        print(f"{'RUN' if args.execute else 'VALIDATE'} {label}", flush=True)
        subprocess.run(command, check=True, timeout=420)
        if args.execute:
            verify_assessment(path, oracle, directory / "results", report)


if __name__ == "__main__":
    main()
