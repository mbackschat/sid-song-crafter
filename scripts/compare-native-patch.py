"""Compare aligned native SID-Wizard excerpts with one explicit instrument patch."""

import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys

from audio_comparison import inspect_wav, prepare_comparison
from psid_audit import audit_psid
from verify_player import require


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("native_song", ROOT / "scripts/native-song.py")
native_song = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native_song)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def patch_recipe(recipe, patch):
    require(isinstance(patch, dict) and set(patch) == {"format", "instrument", "changes"} and patch["format"] == "sidwizard-instrument-patch-v1", "Unsupported instrument patch format")
    identity = patch["instrument"]
    require(isinstance(identity, str) and identity in recipe["instruments"], "Patch must name an existing instrument")
    require(isinstance(patch["changes"], list) and patch["changes"], "Patch must declare at least one leaf change")
    candidate = copy.deepcopy(recipe)
    original, instrument = recipe["instruments"][identity], candidate["instruments"][identity]
    scalar_fields = {"control", "hard_restart_adsr", "adsr", "frame1", "vibrato", "vibrato_delay"}
    table_fields = {"wave", "pulse", "filter"}
    seen = set()
    for change in patch["changes"]:
        require(isinstance(change, dict), "Each patch change must describe an existing leaf")
        field = change.get("field")
        require(isinstance(field, str) and field in scalar_fields | table_fields and field in original, "Patch field must be an existing native sound field")
        if field in table_fields:
            require(set(change) == {"field", "row", "column", "from", "to"}, "Table patch requires explicit row and column")
            row, column = change["row"], change["column"]
            require(type(row) is int and 0 <= row < len(original[field]) and type(column) is int and 0 <= column < 3, "Table patch position is outside an existing three-byte row")
            require(isinstance(original[field][row], list) and len(original[field][row]) == 3, "Table patch must select a byte leaf rather than a jump row")
            container, key, previous = instrument[field][row], column, original[field][row][column]
            location = (field, row, column)
        else:
            require(set(change) == {"field", "from", "to"}, "Scalar patch requires only field/from/to")
            container, key, previous = instrument, field, original[field]
            location = (field,)
        require(location not in seen, "Duplicate patch leaf")
        seen.add(location)
        require(type(change["from"]) is type(previous) and change["from"] == previous, f"Patch precondition differs at {location}")
        require(type(change["to"]) in (str, int) and change["to"] != previous, "Patch must replace a sound leaf with a different scalar value")
        container[key] = change["to"]
    encoder = native_song.load_script("generate-native-instruments").instrument_bytes
    try:
        before, after = encoder(identity, original), encoder(identity, instrument)
    except TypeError as error:
        raise ValueError(f"Invalid native instrument patch: {error}") from error
    require(before != after, "Patch does not change the encoded native instrument")
    return candidate


def verify_same_schedule(a, b):
    derived = {"recipePath", "recipeSha256", "nativePath", "nativeSha256"}
    require({key: value for key, value in a.items() if key not in derived} == {key: value for key, value in b.items() if key not in derived}, "Instrument patch changed the converted source, layout or schedule")


def verify_excerpt(manifest, observer, ticks):
    require(type(ticks) is int and 0 < ticks <= manifest["stopTick"], "Excerpt audit must remain before the song's terminal stop")
    voice_count = len(native_song.sid_layout(manifest)) * 3
    require(len(manifest["voices"]) == voice_count and all(type(entry["voice"]) is int and 0 <= entry["voice"] < voice_count for entries in (observer.cells, observer.starts, observer.sequence_reads) for entry in entries), "Excerpt contains an unsupported voice layout")
    counts = []
    for voice, part in enumerate(manifest["voices"]):
        fields = ("tick", "pattern", "byteOffset", "noteCode", "instrument")
        cells = [tuple(cell.get(field) for field in fields) for cell in manifest["cellMap"] if cell["voice"] == voice and cell["tick"] < ticks]
        require([tuple(cell.get(field) for field in fields) for cell in observer.cells if cell["voice"] == voice] == cells, f"Voice {voice + 1} excerpt cell consumption differs from conversion")
        starts = [(note["startTick"], note["nativeNote"], note["instrument"]) for note in part["notes"] if note["startTick"] < ticks]
        require([(note["tick"], note["nativeNote"], note["instrument"]) for note in observer.starts if note["voice"] == voice] == starts, f"Voice {voice + 1} excerpt note starts differ from conversion")
        sequence = [(entry["tick"], entry["pattern"]) for entry in part["expectedPatternEntries"] if entry["tick"] is None or entry["tick"] < ticks]
        require([(entry["tick"], entry["entry"]) for entry in observer.sequence_reads if entry["voice"] == voice] == sequence, f"Voice {voice + 1} excerpt sequence reads differ from conversion")
        counts.append(len(starts))
    return {"checkedCalls": ticks, "noteCounts": counts, "fullSongCompletionChecked": False, "method": "Pinned Extra note-column reads, discrete note starts and orderlist reads through the excerpt plus one safety call"}


def audit_excerpt(manifest, exported, directory, ticks):
    sids = native_song.sid_layout(manifest)
    require(native_song.sid_layout(exported) == sids, "Conversion and export SID layouts disagree")
    require(digest(Path(manifest["nativePath"]).read_bytes()) == manifest["nativeSha256"] == exported["sourceSha256"], "Native source differs from conversion/export evidence")
    sid = Path(exported["sid"]).read_bytes()
    require(digest(sid) == exported["sidSha256"], "SID differs from its export evidence")
    require((exported["player"], exported["loadAddress"], exported["initAddress"], exported["playAddress"]) == ("Extra", 0x1000, 0x1000, 0x1003), "Excerpt observer requires the pinned Extra player at $1000")
    exporter_directory = "sid-wizard-exporter-2sid" if len(sids) == 2 else "sid-wizard-exporter"
    label_bytes = (ROOT / ".tools" / exporter_directory / "exporter.labels").read_bytes()
    require(digest(label_bytes) == exported["build"]["labelsSha256"], "Observer labels differ from the exporter build")
    labels = {name: int(value, 16) for value, name in re.findall(r"^al ([\da-fA-F]+) \.(.+)$", label_bytes.decode(), re.MULTILINE)}
    observer = native_song.NativeObserver(labels, len(sids))
    audited, writes = audit_psid(sid, ticks, observer=observer)
    require(native_song.sid_layout(audited) == sids, "Audited SID layout differs from conversion")
    frames = native_song.frame_states(writes, ticks, tuple(sid["baseAddress"] for sid in sids))
    evidence = {"audit": audited, "writes": writes, "frames": frames, "native-events": {"cells": observer.cells, "starts": observer.starts, "sequenceReads": observer.sequence_reads}}
    for name, value in evidence.items():
        native_song.write_json(directory / f"{name}.json", value)
    schedule = verify_excerpt(manifest, observer, ticks)
    native_song.write_json(directory / "schedule.json", schedule)
    return audited, schedule


def run_comparison(recipe_path, patch_path, output, *, seconds=20, renderer=ROOT / ".local/bin/render-sid"):
    require(math.isfinite(seconds) and 0 < seconds <= 60 and round(seconds * 44100) > 0, "Excerpt duration must be finite, positive, at most 60 seconds and contain a PCM frame")
    recipe_path, patch_path, output, renderer = (Path(path).resolve() for path in (recipe_path, patch_path, output, renderer))
    require(not output.exists(), "Comparison output already exists; choose a fresh directory")
    require(recipe_path.is_file() and patch_path.is_file() and renderer.is_file(), "Recipe, patch and documented renderer must exist")
    recipe_bytes, patch_bytes = recipe_path.read_bytes(), patch_path.read_bytes()
    recipe, patch = json.loads(recipe_bytes), json.loads(patch_bytes)
    candidate = patch_recipe(recipe, patch)
    source = (recipe_path.parent / recipe["score"]).resolve()
    score_bytes = source.read_bytes()
    output.mkdir(parents=True)
    inputs = output / "inputs"
    inputs.mkdir()
    for name, data in (("recipe", recipe_bytes), ("patch", patch_bytes), ("score", score_bytes)):
        with (inputs / f"{name}.json").open("xb") as file:
            file.write(data)
    converter, exporter = (native_song.load_script(name) for name in ("arrange-sidwizard", "export-sidwizard"))
    manifests, variants = {}, {}
    for label, derived in (("A", copy.deepcopy(recipe)), ("B", candidate)):
        directory = output / label.lower()
        directory.mkdir()
        derived["score"] = str(inputs / "score.json")
        native_song.write_json(directory / "recipe.json", derived)
        manifests[label] = converter.arrange(directory / "recipe.json", directory / "conversion")
        native_song.write_json(directory / "conversion.json", manifests[label])
    verify_same_schedule(manifests["A"], manifests["B"])
    ticks = math.ceil(seconds * manifests["A"]["ticksPerSecond"]) + 1
    require(ticks <= manifests["A"]["stopTick"], "Excerpt plus safety call must remain before the song's terminal stop")
    for label, manifest in manifests.items():
        print(f"Export, audit and render {label}: {seconds:g}-second excerpt, {ticks} calls", flush=True)
        directory = output / label.lower()
        exported = exporter.export_module(manifest["nativePath"], directory / "export", title=manifest["title"], author=manifest["author"], released=manifest["released"])
        native_song.write_json(directory / "export.json", exported)
        audited, schedule = audit_excerpt(manifest, exported, directory, ticks)
        wav = directory / "excerpt.wav"
        command = [str(renderer), exported["sid"], str(wav), str(seconds)]
        rendered = subprocess.run(command, check=False, timeout=60, capture_output=True, text=True)
        render_report = {"command": command, "executableSha256": digest(renderer.read_bytes()), "deadlineSeconds": 60, "returnCode": rendered.returncode, "stdout": rendered.stdout.strip(), "stderr": rendered.stderr.strip()}
        native_song.write_json(directory / "render.json", render_report)
        if rendered.returncode:
            raise subprocess.CalledProcessError(rendered.returncode, command, rendered.stdout, rendered.stderr)
        pcm = inspect_wav(wav)
        native_song.verify_render(pcm, seconds, len(native_song.sid_layout(manifest)))
        variants[label] = {"recipe": str(directory / "recipe.json"), "conversion": str(directory / "conversion.json"), "export": str(directory / "export.json"), "audit": audited, "schedule": schedule, "writes": str(directory / "writes.json"), "frames": str(directory / "frames.json"), "nativeEvents": str(directory / "native-events.json"), "pcm": pcm, "renderer": render_report}
    matched = prepare_comparison(variants["A"]["pcm"]["path"], variants["B"]["pcm"]["path"], output / "opening", individual_copies=True)
    instrument_number = next(item["number"] for item in manifests["A"]["instruments"] if item["id"] == patch["instrument"])
    report = {"schemaVersion": 1, "evidenceLevel": "excerpt comparison", "fullSongCompletionChecked": False, "listeningReview": None, "seconds": seconds, "sameSchedule": True, "patch": patch, "patchedInstrumentStarts": sum(note["instrument"] == instrument_number and note["startTick"] < ticks for voice in manifests["A"]["voices"] for note in voice["notes"]), "inputs": {"recipe": {"path": str(recipe_path), "sha256": digest(recipe_bytes)}, "patch": {"path": str(patch_path), "sha256": digest(patch_bytes)}, "score": {"path": str(source), "sha256": digest(score_bytes)}}, "variants": variants, "comparison": matched, "limitations": "Opening excerpt CPU scheduling and emulated PCM health only; full-song completion, per-voice PCM audibility, hardware sound and musical quality are not established. Level matching uses full-excerpt AC RMS including silence, not perceptual loudness."}
    native_song.write_json(output / "comparison.json", report)
    print(f"Prepared excerpt comparison: {matched['comparison']['path']}", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("patch", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=20)
    parser.add_argument("--renderer", type=Path, default=ROOT / ".local/bin/render-sid")
    args = parser.parse_args()
    run_comparison(args.recipe, args.patch, args.output, seconds=args.seconds, renderer=args.renderer)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error))
