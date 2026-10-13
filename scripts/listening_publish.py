"""Publish explicitly selected, hash-verified WAV copies in a fresh local folder."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import unicodedata


ROOT = Path(__file__).resolve().parents[1]
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class PublishError(RuntimeError):
    """A listening run, selected artifact or publication path failed validation."""


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _path(value, root):
    if not isinstance(value, (str, Path)) or not str(value) or "\0" in str(value) or "\\" in str(value):
        raise PublishError("Paths must be nonempty and contain no traversal")
    path = Path(value)
    if ".." in path.parts:
        raise PublishError(f"Path traversal is unsupported: {value}")
    path = path if path.is_absolute() else root / path
    _no_symlinks(path)
    return path.resolve()


def _no_symlinks(path):
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current = current / component
        if current.is_symlink():
            raise PublishError(f"Symlink paths are unsupported: {current}")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PublishError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path):
    if not path.is_file():
        raise PublishError(f"Missing regular JSON file: {path}")
    raw = path.read_bytes()
    value = json.loads(raw, object_pairs_hook=_unique_object)
    return value, dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def _filename(value):
    if not isinstance(value, str) or not value or value != value.strip() or value.startswith(".") \
            or "/" in value or "\\" in value or any(ord(char) < 32 for char in value) \
            or Path(value).suffix.lower() != ".wav":
        raise PublishError(f"Friendly names must be flat WAV filenames: {value!r}")
    return unicodedata.normalize("NFC", value).casefold()


def _select(run, selection, root, output):
    if not isinstance(run, dict) or type(run.get("schemaVersion")) is not int or run["schemaVersion"] != 1 \
            or run.get("status") != "completed" or not isinstance(run.get("finishedAt"), str) or not run["finishedAt"]:
        raise PublishError("Publication requires a completed schemaVersion 1 listening run")
    stages = run.get("stages")
    if not isinstance(stages, list) or not stages:
        raise PublishError("Completed run has no successful stages")
    by_id = {}
    for stage in stages:
        if not isinstance(stage, dict) or not isinstance(stage.get("id"), str) or not stage["id"] \
                or stage["id"] in by_id or stage.get("status") not in ("completed", "reused") \
                or "returnCode" in stage and (type(stage["returnCode"]) is not int or stage["returnCode"] != 0):
            raise PublishError("Listening run contains an incomplete or failed stage")
        by_id[stage["id"]] = stage
        if "attemptDirectory" in stage and output.is_relative_to(_path(stage["attemptDirectory"], root)):
            raise PublishError("Publication output must not change a live attempt cache")
    deliverables, artifacts = run.get("deliverables"), run.get("artifacts")
    if not isinstance(deliverables, dict) or not isinstance(artifacts, list):
        raise PublishError("Listening run lacks authoritative deliverables/artifacts")
    if not isinstance(selection, dict) or not selection:
        raise PublishError("Selection must explicitly map deliverable labels to WAV filenames")
    selected, names = [], set()
    for label, filename in selection.items():
        if not isinstance(label, str) or not label or label not in deliverables:
            raise PublishError(f"Unknown deliverable label: {label!r}")
        normalized = _filename(filename)
        if normalized in names:
            raise PublishError(f"Selected filenames collide: {filename}")
        names.add(normalized)
        original = deliverables[label]
        if not isinstance(original, str) or not Path(original).is_absolute():
            raise PublishError(f"Deliverable must have its recorded absolute path: {label}")
        matching = [record for record in artifacts if isinstance(record, dict) and record.get("path") == original]
        if len(matching) != 1:
            raise PublishError(f"Deliverable has no unique pinned artifact: {label}")
        artifact = matching[0]
        if artifact.get("type") != "file" or not isinstance(artifact.get("sha256"), str) \
                or not _SHA256.fullmatch(artifact["sha256"]):
            raise PublishError(f"Deliverable is not a pinned WAV file artifact: {label}")
        stage = by_id.get(artifact.get("stageId"))
        if stage is None or not isinstance(stage.get("artifacts"), list) \
                or sum(record == artifact for record in stage["artifacts"]) != 1:
            raise PublishError(f"Deliverable differs from its successful stage artifact: {label}")
        source = _path(original, root)
        if source.suffix.lower() != ".wav" or not source.is_file():
            raise PublishError(f"Only regular WAV audio deliverables can be published: {label}")
        if _sha256(source) != artifact["sha256"]:
            raise PublishError(f"Pinned source hash changed: {label}")
        selected.append(dict(label=label, sourcePath=str(source), filename=filename,
            sha256=artifact["sha256"], bytes=source.stat().st_size, stageId=artifact["stageId"]))
    return selected


def _unchanged(path, fingerprint, name):
    _no_symlinks(path)
    if not path.is_file() or path.stat().st_size != fingerprint["bytes"] or _sha256(path) != fingerprint["sha256"]:
        raise PublishError(f"{name} changed during publication")


def publish_listening(run_path, selection_path, output, *, root=ROOT):
    """Copy selected WAVs after verifying completed-run artifact pins.

    Source and index hashes are checked again before publishing. A private staging
    folder holds all files until an exclusive final-directory reservation succeeds;
    the complete staging folder then replaces that empty reservation atomically.
    Existing destinations and source/cache files are never overwritten.
    """
    staging, reserved = None, False
    try:
        root = Path(root).resolve()
        output = _path(output, root)
        build = root / "build"
        if output == build or not output.is_relative_to(build):
            raise PublishError("Publication output must be a fresh directory below repository build/")
        if output.exists():
            raise PublishError("Publication output must be a fresh directory")
        run_path, selection_path = _path(run_path, root), _path(selection_path, root)
        run, run_fingerprint = _read_json(run_path)
        selection, selection_fingerprint = _read_json(selection_path)
        selected = _select(run, selection, root, output)
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
        for record in selected:
            source = Path(record["sourcePath"])
            _no_symlinks(source)
            target = staging / record["filename"]
            shutil.copyfile(source, target)
            _unchanged(target, record, "Copied audio")
        manifest = dict(schemaVersion=1, run=run_fingerprint, selection=selection_fingerprint, files=selected)
        (staging / "sources.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        for record in selected:
            _unchanged(staging / record["filename"], record, "Copied audio")
            _unchanged(Path(record["sourcePath"]), record, "Source audio")
        _unchanged(run_path, run_fingerprint, "Listening run")
        _unchanged(selection_path, selection_fingerprint, "Selection")
        _no_symlinks(output)
        output.mkdir()
        reserved = True
        os.replace(staging, output)
        staging = None
        reserved = False
        return manifest
    except PublishError:
        raise
    except (OSError, ValueError, TypeError) as error:
        raise PublishError(str(error)) from error
    finally:
        if staging is not None:
            shutil.rmtree(staging)
        if reserved:
            # A failed rename must preserve files another writer added; rmdir's
            # empty-directory rule enforces that constraint.
            try:
                output.rmdir()
            except OSError:
                pass
