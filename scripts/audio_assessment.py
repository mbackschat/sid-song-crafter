#!/usr/bin/env python3
import argparse
import base64
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import wave


ROOT = Path(__file__).resolve().parents[1]
API = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "qwen/qwen3.8-omni-flash"
TRIAL_CAP = Decimal("0.10")
CALL_RESERVE = Decimal("0.01")
MAX_ATTEMPTS = 8


class TrialError(Exception):
    pass


def _sha256(contents):
    return hashlib.sha256(contents).hexdigest()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _write(path, contents):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as target:
        target.write(contents)
        target.flush()
        os.fsync(target.fileno())
    os.replace(temporary, path)


def _write_json(path, value):
    _write(path, (json.dumps(value, indent=2, allow_nan=False) + "\n").encode())


def _money(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TrialError("API cost and limit values must be finite numbers")
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise TrialError("API cost and limit values must be finite numbers") from None
    if not number.is_finite() or number < 0:
        raise TrialError("API cost and limit values must be finite nonnegative numbers")
    return number


def _load_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        raise TrialError(f"Cannot read valid JSON: {path}") from None


def _prepare(manifest_path, output_path):
    try:
        output_path.resolve().relative_to((ROOT / "build").resolve())
    except ValueError:
        raise TrialError("Output directory must be under the repository build directory") from None
    manifest = _load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise TrialError("Manifest must be a JSON object")
    model = manifest.get("model", DEFAULT_MODEL)
    max_tokens = manifest.get("max_tokens", 1200)
    reasoning = manifest.get("reasoning", False)
    reasoning_effort = manifest.get("reasoning_effort")
    cases = manifest.get("cases")
    if not isinstance(model, str) or not model.strip():
        raise TrialError("Manifest model must be a nonempty string")
    if type(max_tokens) is not int or not 1 <= max_tokens <= 1200:
        raise TrialError("Manifest max_tokens must be an integer from 1 through 1200")
    if reasoning is not None and type(reasoning) is not bool:
        raise TrialError("Manifest reasoning must be a boolean or null")
    if "reasoning_effort" in manifest and reasoning_effort not in ("low", "medium", "high"):
        raise TrialError("Manifest reasoning_effort must be low, medium or high")
    if reasoning_effort is not None and not reasoning:
        raise TrialError("Manifest reasoning_effort requires reasoning true")
    if not isinstance(cases, list) or not 1 <= len(cases) <= MAX_ATTEMPTS:
        raise TrialError("Manifest must have one through eight cases")
    prepared = []
    ids = set()
    for case in cases:
        if not isinstance(case, dict) or any(not isinstance(case.get(field), str) or not case[field].strip() for field in ("id", "prompt", "wav")):
            raise TrialError("Each case needs nonempty id, prompt and wav strings")
        if case["id"] in ids:
            raise TrialError("Case ids must be unique")
        ids.add(case["id"])
        path = (manifest_path.parent / case["wav"]).resolve()
        try:
            if path.stat().st_size > 8 * 1024 * 1024:
                raise TrialError("WAV exceeds 8 MiB")
            audio = path.read_bytes()
            with wave.open(io.BytesIO(audio), "rb") as source:
                frames = source.getnframes()
                duration = frames / source.getframerate()
                if source.getcomptype() != "NONE" or source.getsampwidth() not in (1, 2, 3, 4) or source.getnchannels() not in (1, 2) or frames <= 0:
                    raise TrialError("WAV must contain nonempty mono or stereo integer PCM")
                if duration > 30:
                    raise TrialError("WAV exceeds 30 seconds")
                if len(source.readframes(frames)) != frames * source.getsampwidth() * source.getnchannels():
                    raise TrialError("WAV PCM is truncated")
        except (OSError, EOFError, wave.Error, ZeroDivisionError):
            raise TrialError(f"Cannot read valid PCM WAV: {path}") from None
        payload = {"model": model, "max_tokens": max_tokens, "temperature": 0, "provider": {"allow_fallbacks": False}, "messages": [{"role": "user", "content": [{"type": "text", "text": case["prompt"]}, {"type": "input_audio", "input_audio": {"data": base64.b64encode(audio).decode("ascii"), "format": "wav"}}]}]}
        if reasoning is not None:
            payload["reasoning"] = {"enabled": reasoning}
        if reasoning_effort is not None:
            payload["reasoning"]["effort"] = reasoning_effort
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        prepared.append({"id": case["id"], "wav_path": str(path), "audio_sha256": _sha256(audio), "duration_seconds": duration, "model": model, "max_tokens": max_tokens, "reasoning": reasoning, "reasoning_effort": reasoning_effort, "payload_sha256": _sha256(encoded), "payload": encoded})
    return prepared


def _request(path, key, opener, payload=None):
    request = Request(API + path, data=payload, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST" if payload is not None else "GET")
    try:
        with opener(request, timeout=45) as response:
            contents = response.read(2 * 1024 * 1024 + 1)
    except HTTPError as error:
        raise TrialError(f"API HTTP {error.code}") from None
    except (URLError, TimeoutError, socket.timeout, OSError):
        raise TrialError("API transport failed; request outcome is uncertain") from None
    if len(contents) > 2 * 1024 * 1024:
        raise TrialError("API response exceeds 2 MiB; request outcome is uncertain")
    return contents.replace(key.encode(), b"[redacted]")


def _key_guard(key, opener):
    try:
        data = json.loads(_request("/key", key, opener))["data"]
        limit = _money(data.get("limit"))
        remaining = _money(data.get("limit_remaining"))
        if not 0 < limit <= 10 or remaining < CALL_RESERVE or data.get("limit_reset") is not None:
            raise TrialError("Key requires a positive cap no greater than $10, at least $0.01 remaining, and no reset")
        return {"limit": float(limit), "limit_remaining": float(remaining), "limit_reset": None}
    except (ValueError, KeyError, TypeError, AttributeError):
        raise TrialError("Invalid API key-limit response") from None


def _content(response):
    try:
        return response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None


def _execute(cases, output_path, key_path, opener):
    records = [(path, _load_json(path)) for path in sorted(output_path.glob("attempt-*.json"))]
    if any(not isinstance(record, dict) for _, record in records):
        raise TrialError("Invalid attempt receipt")
    total = sum((_money(record["cost"]) for _, record in records if record.get("cost") is not None), Decimal(0))
    results = []
    key = None
    for case in cases:
        cached = next((record for _, record in records if record.get("payload_sha256") == case["payload_sha256"] and record.get("status") == "complete"), None)
        if cached:
            response_path = output_path / cached["response_path"]
            if not response_path.is_file() or _sha256(response_path.read_bytes()) != cached["response_sha256"]:
                raise TrialError("Cached response is missing or changed; refusing to repeat a billed request")
            results.append({**{field: value for field, value in case.items() if field != "payload"}, "cached": True, "cost": cached["cost"], "content": _content(_load_json(response_path))})
            continue
        if len(records) >= MAX_ATTEMPTS:
            raise TrialError("Trial reached eight POST attempts; no further requests allowed")
        if any(record.get("status") == "pending" for _, record in records):
            raise TrialError("An earlier request has an uncertain outcome; refusing another request")
        if any(record.get("cost") is None for _, record in records):
            raise TrialError("An earlier request has unknown cost; refusing another request")
        if total + CALL_RESERVE > TRIAL_CAP:
            raise TrialError("Trial cost leaves less than the $0.01 reserve within the $0.10 cap")
        if key is None:
            try:
                key = key_path.read_text().strip()
            except OSError:
                raise TrialError("Cannot read the API key file") from None
            if not key or any(character.isspace() for character in key):
                raise TrialError("API key file must contain one nonempty token")
        key_limits = _key_guard(key, opener)
        number = len(records) + 1
        attempt_path = output_path / f"attempt-{number:02d}.json"
        response_path = output_path / f"response-{number:02d}.json"
        receipt = {field: value for field, value in case.items() if field != "payload"}
        receipt.update({"status": "pending", "started_at": _now(), "cost": None, "key_limits": key_limits})
        _write_json(attempt_path, receipt)
        try:
            contents = _request("/chat/completions", key, opener, case["payload"])
        except TrialError as error:
            if str(error).startswith("API HTTP "):
                receipt.update({"status": "http_error", "http_status": int(str(error).split()[-1]), "finished_at": _now()})
                _write_json(attempt_path, receipt)
            raise
        _write(response_path, contents)
        receipt.update({"status": "unknown_cost", "response_path": response_path.name, "response_sha256": _sha256(contents), "finished_at": _now()})
        try:
            response = json.loads(contents)
            usage = response.get("usage", {})
            receipt["usage"] = usage
            cost = _money(usage.get("cost"))
        except (ValueError, AttributeError, TrialError):
            _write_json(attempt_path, receipt)
            raise TrialError("Response saved but usage.cost is missing or invalid; stopping") from None
        receipt.update({"status": "complete", "cost": float(cost)})
        _write_json(attempt_path, receipt)
        records.append((attempt_path, receipt))
        total += cost
        results.append({**{field: value for field, value in case.items() if field != "payload"}, "cached": False, "cost": float(cost), "content": _content(response)})
        if total > TRIAL_CAP:
            raise TrialError("Response saved; measured trial cost exceeded $0.10, stopping")
    return results


def run_trial(manifest_path, output_path, key_path=None, dry_run=False, opener=urlopen):
    manifest_path, output_path = Path(manifest_path).resolve(), Path(output_path).resolve()
    cases = _prepare(manifest_path, output_path)
    if dry_run:
        return [{field: value for field, value in case.items() if field != "payload"} for case in cases]
    output_path.mkdir(parents=True, exist_ok=True)
    with (output_path / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise TrialError("Another process is using this trial directory") from None
        return _execute(cases, output_path, Path(key_path) if key_path is not None else ROOT / ".local" / "openrouter-api-key", opener)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run a bounded, cached OpenRouter WAV assessment trial.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--key-file", type=Path, default=ROOT / ".local" / "openrouter-api-key")
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        results = run_trial(arguments.manifest, arguments.output, arguments.key_file, arguments.dry_run)
    except (TrialError, OSError):
        error = sys.exc_info()[1]
        print(str(error) if isinstance(error, TrialError) else "Local file operation failed", file=sys.stderr)
        return 1
    for result in results:
        if arguments.dry_run:
            print(f"{result['id']}: {result['duration_seconds']:.3f}s WAV, {result['model']}, max_tokens={result['max_tokens']}, payload={result['payload_sha256']}")
        else:
            print(f"{result['id']}: {'cached' if result['cached'] else 'completed'}, cost=${result['cost']}")
            if result["content"] is not None:
                print(result["content"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
