"""Prepare and inspect a frozen single-clip Trap perception calibration."""

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import sys
import wave


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from audio_assessment import TrialError, _prepare
from audio_comparison import inspect_wav, read_pcm16


SOURCE_DIRECTORY = ROOT / "build/trap-transitions-listening"
SOURCE_REGISTRY = SOURCE_DIRECTORY / "sources.json"
HUMAN_REVIEW = ROOT / "evidence/daglish-contrast/transitions/listening-review.json"
SOURCE_HASHES = {
    "trap-original-24to34s.wav": "1059e488fdcba9ed7947a6a4bcc145b360da74cd5f0a474d117962756c62cb18",
    "trap-original-40to52s.wav": "b17823b8e43ba23c8ad52f2c958c0d340efe8fc3af4caff74f9be4dd41da8618",
}
MODELS = {
    "qwen": {"model": "qwen/qwen3.8-omni-flash", "reasoning": True},
    "gemini": {"model": "google/gemini-3.8-flash", "reasoning": True, "reasoning_effort": "low"},
}
PROMPT = (
    "Listen to this single audio clip. Is music present? What is the main perceived "
    "source of rhythmic motion: moving melody, repeated percussive attacks, both, "
    "unclear, or no music? Does the clip develop or predominantly repeat: develops, "
    "repeats, unclear, or no music? Report what you hear, without identifying a "
    "source or ranking quality. Return only JSON with music_present (yes/no/unclear), "
    "rhythmic_motion (moving melody/repeated percussive attacks/both/unclear/no music), "
    "development (develops/repeats/unclear/no music), and evidence (one or two short "
    "objects containing start_seconds, end_seconds, and observation). Times are "
    "relative to the clip and must lie within it. Use unclear when you cannot tell."
)
SCOPE = (
    "Calibration against two already-known, passage-scoped human observations and exact PCM controls; "
    "no held-out validation or model adoption. Only rhythmic_motion is scored on c01 and only "
    "development on c02. No numbered-voice attribution, background independence, musical preference, "
    "full-form judgment or composer-wide claim is tested. Single-clip presentation has no A/B separator; "
    "reversed-pair and A/A controls are inapplicable here and previous failed pair controls remain unresolved."
)


def _sha(contents):
    return hashlib.sha256(contents).hexdigest()


def _read(path):
    return json.loads(path.read_text())


def _write(path, value):
    with path.open("x") as target:
        target.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def _relative(path):
    return str(path.resolve().relative_to(ROOT))


def _source(name, seconds):
    path = SOURCE_DIRECTORY / name
    raw = path.read_bytes()
    if _sha(raw) != SOURCE_HASHES[name]:
        raise ValueError(f"Source fingerprint mismatch: {name}")
    audio = read_pcm16(path)
    if (audio.sample_rate, audio.channels, audio.frames) != (44100, 1, seconds * 44100):
        raise ValueError(f"Source must contain exact {seconds}s of 44.1 kHz mono PCM16: {name}")
    with wave.open(str(path), "rb") as source:
        pcm = source.readframes(source.getnframes())
    if not any(pcm):
        raise ValueError(f"Original source has zero PCM: {name}")
    return raw, pcm


def _write_audio(path, pcm):
    with path.open("xb") as target:
        with wave.open(target, "wb") as audio:
            audio.setparams((1, 2, 44100, 0, "NONE", "not compressed"))
            audio.writeframes(pcm)


def prepare_trap_perception(output):
    output = Path(output).resolve()
    if not output.is_relative_to((ROOT / "build").resolve()):
        raise ValueError("Output must be a fresh directory under build/")
    if output.exists():
        raise FileExistsError("Output must be a fresh directory under build/")
    registry = _read(SOURCE_REGISTRY)
    published = {record["filename"]: record for record in registry["files"]}
    if any(published.get(name, {}).get("sha256") != expected for name, expected in SOURCE_HASHES.items()):
        raise ValueError("Source publication differs from pinned fingerprints")
    sources = {name: _source(name, seconds) for name, seconds in zip(SOURCE_HASHES, (10, 12))}
    names = list(SOURCE_HASHES)
    pcm = {"c01": sources[names[0]][1], "c02": sources[names[1]][1], "c03": bytes(12 * 44100 * 2), "c04": sources[names[1]][1][:2 * 44100 * 2] * 6}
    human_path = HUMAN_REVIEW
    human = _read(human_path)
    for (name, (_, source_pcm)), verdict in zip(sources.items(), ("In Trap, mostly the  a moving melody", "Trap develops during the excerpt")):
        pair_name = name.replace("trap-original", "deflektor-then-trap").replace(".wav", ".ab.wav")
        record = next(item for item in human["comparisons"] if Path(item["comparison"]).name == pair_name)
        pair_path = SOURCE_DIRECTORY / pair_name
        if record["verbatim"] != verdict or record["sha256"] != _sha(pair_path.read_bytes()):
            raise ValueError("Human observation or submitted comparison fingerprint mismatch")
        with wave.open(str(pair_path), "rb") as pair:
            frames = len(source_pcm) // 2
            if (pair.getnchannels(), pair.getsampwidth(), pair.getframerate(), pair.getnframes()) != (1, 2, 44100, 2 * frames + 22050):
                raise ValueError("Human submitted pair has unexpected PCM format or duration")
            pair.setpos(frames + 22050)
            if pair.readframes(frames) != source_pcm:
                raise ValueError("Human observation is not bound to the exact original excerpt PCM")
    metadata_path = ROOT / "evidence/audio-assessment-gemini/model-metadata.json"
    gemini_metadata = next(record for record in _read(metadata_path) if record["id"] == MODELS["gemini"]["model"])
    qwen_receipt_path = ROOT / "evidence/audio-assessment-openrouter/results/attempt-05.json"
    qwen_receipt = _read(qwen_receipt_path)
    if qwen_receipt.get("model") != MODELS["qwen"]["model"] or qwen_receipt.get("reasoning") is not True or qwen_receipt.get("status") != "complete":
        raise ValueError("Qwen configuration lacks the declared completed local evidence")
    inputs = output / "inputs"
    inputs.mkdir(parents=True, exist_ok=False)
    for case_id in ("c01", "c02"):
        (inputs / f"{case_id}.wav").write_bytes(sources[names[int(case_id[-1]) - 1]][0])
    for case_id in ("c03", "c04"):
        _write_audio(inputs / f"{case_id}.wav", pcm[case_id])
    records = {}
    for case_id, expected_pcm in pcm.items():
        path = inputs / f"{case_id}.wav"
        with wave.open(str(path), "rb") as source:
            if source.readframes(source.getnframes()) != expected_pcm:
                raise ValueError("Prepared PCM differs from declared source/control")
        records[case_id] = {"file": path.name, "pcm_sha256": _sha(expected_pcm), "metrics": {key: value for key, value in inspect_wav(path).items() if key != "path"}}
    expected = [{"rhythmic_motion": "moving melody"}, {"development": "develops"}, {"music_present": "no", "rhythmic_motion": "no music", "development": "no music"}, {"development": "repeats"}]
    oracle_cases = [{"id": case_id, "expected": answer, "basis": basis} for case_id, answer, basis in zip(pcm, expected, ("Scoped human rhythm observation", "Scoped human development observation", "Exact digital silence", "First two seconds of c02 tiled six times with no gain or synthesis change"))]
    bindings, manifests = {}, []
    for label, settings in MODELS.items():
        manifest = inputs / f"{label}.json"
        _write(manifest, {**settings, "max_tokens": 1200, "cases": [{"id": case_id, "wav": f"{case_id}.wav", "prompt": PROMPT, "audio_sha256": records[case_id]["metrics"]["sha256"]} for case_id in pcm]})
        bindings[label] = {"manifest": _relative(manifest), "settings": settings, "cases": [{key: case[key] for key in ("id", "audio_sha256", "payload_sha256", "duration_seconds")} for case in _prepare(manifest, output / "results")]}
        manifests.append(manifest)
    _write(inputs / "oracle.json", {"schema_version": 1, "scope": SCOPE, "cases": oracle_cases, "models": bindings, "held_out_passage": False, "establishes_model_eligibility": False, "criterion": "Each case passes only when finish_reason is stop, all declared expected labels match and the response parses with allowed labels and one or two bounded evidence spans. Require all four cases per model for a calibration pass. Abstention, truncation or malformed response is a miss; do not revise prompt after outputs. Evidence truth requires separate manual review.", "parser": "Accept a JSON object, optionally wrapped in one outer ```json or ``` code fence; do not infer labels from prose.", "budget": {"post_attempts_total_max": 8, "local_admission_cap_usd": "0.10", "shared_results": _relative(output / "results"), "runner": "scripts/audio_assessment.py", "no_retries": True}})
    _write(inputs / "model-metadata.json", {"gemini": {"source": _relative(metadata_path), "source_sha256": _sha(metadata_path.read_bytes()), "record": gemini_metadata}, "qwen": {"configuration_evidence": _relative(qwen_receipt_path), "sha256": _sha(qwen_receipt_path.read_bytes()), "record": qwen_receipt}, "requested_settings": MODELS})
    _write(inputs / "human-context.json", {"source": _relative(human_path), "source_sha256": _sha(human_path.read_bytes()), "record": human})
    _write(inputs / "provenance.json", {"schema_version": 1, "scope": SCOPE, "generator": _relative(Path(__file__)), "generator_sha256": _sha(Path(__file__).read_bytes()), "runner_sha256": _sha((ROOT / "scripts/audio_assessment.py").read_bytes()), "source_publication": {"path": _relative(SOURCE_REGISTRY), "sha256": _sha(SOURCE_REGISTRY.read_bytes()), "record": registry}, "source_sha256s": SOURCE_HASHES, "source_windows_seconds": {"c01": [24, 34], "c02": [40, 52]}, "loop": {"source_case": "c02", "start_frame_inclusive": 0, "end_frame_exclusive": 88200, "repetitions": 6}, "gain": 1, "normalization": False, "resampling": False, "prompt": PROMPT, "prompt_sha256": _sha(PROMPT.encode()), "cases": records, "boundary": "Only one anonymous audio clip, the neutral prompt and fixed runner settings are submitted. Source names, oracle and human judgments remain local."})
    (inputs / "generator-at-capture.py").write_bytes(Path(__file__).read_bytes())
    _write(output / "frozen-inputs.json", {"frozen_at": datetime.now(timezone.utc).isoformat(), "files": {path.name: _sha(path.read_bytes()) for path in sorted(inputs.iterdir()) if path.is_file()}})
    verify_frozen_inputs(output)
    return manifests


def verify_frozen_inputs(output):
    output = Path(output).resolve()
    for name, expected in _read(output / "frozen-inputs.json")["files"].items():
        if _sha((output / "inputs" / name).read_bytes()) != expected:
            raise ValueError(f"Frozen input changed: {name}")
    oracle = _read(output / "inputs/oracle.json")
    for label, model in oracle["models"].items():
        prepared = _prepare(output / "inputs" / f"{label}.json", output / "results")
        if [{key: case[key] for key in ("id", "audio_sha256", "payload_sha256", "duration_seconds")} for case in prepared] != model["cases"]:
            raise ValueError("Frozen payload binding changed")
    return oracle


def parse_answer(content, duration):
    if not isinstance(content, str):
        return {}, ["Content is not text"]
    stripped = content.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        stripped = stripped.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        answer = json.loads(stripped)
    except ValueError:
        return {}, ["Content is not a JSON object"]
    if not isinstance(answer, dict):
        return {}, ["Content is not a JSON object"]
    errors = []
    for field, choices in (("music_present", ("yes", "no", "unclear")), ("rhythmic_motion", ("moving melody", "repeated percussive attacks", "both", "unclear", "no music")), ("development", ("develops", "repeats", "unclear", "no music"))):
        if answer.get(field) not in choices:
            errors.append(f"Invalid {field}")
    evidence = answer.get("evidence")
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= 2:
        errors.append("Require one or two evidence spans")
    else:
        for span in evidence:
            start, end = (span.get(field) for field in ("start_seconds", "end_seconds")) if isinstance(span, dict) else (None, None)
            if not all(type(value) in (int, float) and math.isfinite(value) for value in (start, end)) or not 0 <= start < end <= duration or not isinstance(span.get("observation"), str) or not span["observation"].strip():
                errors.append("Invalid evidence span or clip-relative bounds")
    return answer, errors


def assess(output):
    output = Path(output).resolve()
    oracle = verify_frozen_inputs(output)
    expected = {case["id"]: case["expected"] for case in oracle["cases"]}
    attempts = sorted((output / "results").glob("attempt-*.json"))
    receipts = {}
    for path in attempts:
        receipt = _read(path)
        receipts[(receipt["model"], receipt["id"])] = (path, receipt)
    if len(receipts) != 8 or len(attempts) != 8:
        raise ValueError("Assessment requires exactly eight distinct model/case attempts")
    results = {}
    for label, model in oracle["models"].items():
        cases = []
        for case in model["cases"]:
            receipt_path, receipt = receipts[(model["settings"]["model"], case["id"])]
            response_path = output / "results" / receipt["response_path"]
            if receipt["status"] != "complete" or any(receipt[key] != case[key] for key in ("audio_sha256", "payload_sha256")) or _sha(response_path.read_bytes()) != receipt["response_sha256"]:
                raise ValueError("Completed receipt, input or response fingerprint mismatch")
            response = _read(response_path)
            choice = response["choices"][0]
            answer, errors = parse_answer(choice["message"].get("content"), case["duration_seconds"])
            matches = {field: answer.get(field) == value for field, value in expected[case["id"]].items()}
            cases.append({**case, "expected": expected[case["id"]], "answer": answer, "content": choice["message"].get("content"), "parse_errors": errors, "field_matches": matches, "pass": choice.get("finish_reason") == "stop" and not errors and all(matches.values()), "cost_usd": receipt["cost"], "actual_model": response.get("model"), "provider": response.get("provider"), "finish_reason": choice.get("finish_reason"), "receipt": _relative(receipt_path), "receipt_sha256": _sha(receipt_path.read_bytes()), "response": _relative(response_path), "response_sha256": receipt["response_sha256"]})
        results[label] = {"cases": cases, "passed_cases": sum(case["pass"] for case in cases), "total_cases": 4, "human_observation_agreements": sum(case["pass"] for case in cases[:2]), "human_observations_total": 2, "control_passes": sum(case["pass"] for case in cases[2:]), "controls_total": 2, "calibration_pass": all(case["pass"] for case in cases), "cost_usd": str(sum(Decimal(str(case["cost_usd"])) for case in cases))}
    report = {"date": "2026-10-14", "scope": SCOPE, "prompt": PROMPT, "frozen_inputs_sha256": _sha((output / "frozen-inputs.json").read_bytes()), "oracle_sha256": _sha((output / "inputs/oracle.json").read_bytes()), "results": results, "post_attempts": 8, "cost_usd": str(sum(Decimal(model["cost_usd"]) for model in results.values())), "held_out_passage": False, "establishes_model_eligibility": False, "eligibility_conclusion": "Calibration outcomes only; neither model is adopted or independently validated for musical acceptance. Prior failed pair controls remain unresolved. Time-grounded explanations require human review."}
    _write(output / "assessment.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--assess", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.assess:
            report = assess(args.output)
            print(json.dumps({"cost_usd": report["cost_usd"], "models": {label: {key: result[key] for key in ("passed_cases", "total_cases", "cost_usd", "calibration_pass")} for label, result in report["results"].items()}}, indent=2))
        elif args.verify:
            verify_frozen_inputs(args.output)
            print("Frozen inputs and payload bindings verified")
        else:
            for manifest in prepare_trap_perception(args.output):
                print(manifest)
    except (ValueError, KeyError, OSError, wave.Error, TrialError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
