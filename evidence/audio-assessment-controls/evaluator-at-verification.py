"""Score basic perception against a withheld oracle and verified request receipts."""

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from audio_assessment import run_trial


def grade(content, expected):
    try:
        text = content.strip()
        if text.startswith("```") and text.endswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        response = json.loads(text)
        if not isinstance(response, dict):
            raise ValueError("Expected object")
    except (AttributeError, ValueError, IndexError):
        return {"passed": False, "error": "No valid JSON object", "observed_category": None}
    transcript = response.get("transcript", "")
    words = set(re.findall(r"\b\w+\b", transcript.lower())) if isinstance(transcript, str) else set()
    if "7" in words:
        words.add("seven")
    missing = [word for word in expected.get("required_words", []) if word.lower() not in words]
    category = response.get("category")
    return {"passed": category == expected["category"] and not missing,
            "observed_category": category, "missing_words": missing, "response": response}


def evaluate(manifest, oracle_path, results):
    prepared = run_trial(manifest, results, dry_run=True)
    oracle = json.loads(Path(oracle_path).read_text())
    expected = {case["id"]: case for case in oracle["cases"]}
    if len(expected) != len(oracle["cases"]) or set(expected) != {case["id"] for case in prepared}:
        raise ValueError("Oracle and manifest must have identical unique case IDs")
    if len(prepared) != oracle.get("gate", {}).get("required_case_count", len(prepared)):
        raise ValueError("Oracle requires a different number of controls")
    for case in prepared:
        if expected[case["id"]].get("audio_sha256") != case["audio_sha256"]:
            raise ValueError(f"Oracle audio fingerprint missing or mismatched for {case['id']}")
    results = Path(results)
    receipts = [json.loads(path.read_text()) for path in sorted(results.glob("attempt-*.json"))]
    rows = []
    for case in prepared:
        receipt = next((value for value in receipts if value.get("payload_sha256") == case["payload_sha256"]
                        and value.get("status") == "complete"), None)
        if receipt is None:
            raise ValueError(f"No completed request for {case['id']}")
        response_path = results / receipt["response_path"]
        raw = response_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != receipt["response_sha256"]:
            raise ValueError("Response fingerprint mismatch")
        response = json.loads(raw)
        choice = response.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content")
        outcome = grade(content, expected[case["id"]])
        if choice.get("finish_reason") != "stop":
            outcome.update(passed=False, error="Response did not complete normally")
        rows.append({"id": case["id"], "expected": expected[case["id"]], **outcome,
                     "audio_sha256": case["audio_sha256"], "payload_sha256": case["payload_sha256"],
                     "response_sha256": receipt["response_sha256"], "content": content,
                     "cost_usd": receipt["cost"], "response_model": response.get("model"),
                     "provider": response.get("provider")})
    costs = [Decimal(str(row["cost_usd"])) for row in rows]
    if any(not value.is_finite() or value < 0 for value in costs):
        raise ValueError("Invalid recorded cost")
    return {"model": prepared[0]["model"], "passed": all(row["passed"] for row in rows),
            "manifest_sha256": hashlib.sha256(Path(manifest).read_bytes()).hexdigest(),
            "oracle_sha256": hashlib.sha256(Path(oracle_path).read_bytes()).hexdigest(),
            "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "correct": sum(row["passed"] for row in rows), "total": len(rows),
            "total_cost_usd": str(sum(costs, Decimal(0))), "cases": rows,
            "scope": "Basic perception gate only; passing does not establish musical judgment."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("oracle", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT / "build"):
        parser.error("Output must be under build/.")
    report = evaluate(args.manifest, args.oracle, args.results)
    with args.output.open("x") as target:
        target.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"{report['model']}: {report['correct']}/{report['total']}; "
          f"gate={'pass' if report['passed'] else 'fail'}; cost=${report['total_cost_usd']}")


if __name__ == "__main__":
    main()
