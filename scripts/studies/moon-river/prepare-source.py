#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import mido

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from score_tools import arrange_score, import_midi


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_events(original, derived, tempo):
    if (original.type, original.ticks_per_beat, len(original.tracks)) != (
        derived.type, derived.ticks_per_beat, len(derived.tracks)
    ):
        raise ValueError("Tempo adaptation changed the MIDI structure")
    for source_track, derived_track in zip(original.tracks, derived.tracks):
        if len(source_track) != len(derived_track):
            raise ValueError("Tempo adaptation changed the MIDI event count")
        for source_message, derived_message in zip(source_track, derived_track):
            expected = source_message.copy(tempo=tempo) if source_message.type == "set_tempo" else source_message
            if expected != derived_message:
                raise ValueError("Tempo adaptation changed an event beyond its tempo value")


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def prepare_source(source, recipe_path, output, arrangement=None, candidate=None, reference=None):
    source, recipe_path, output = Path(source), Path(recipe_path), Path(output)
    if output.exists():
        raise ValueError("Use a fresh output directory")
    extras = (arrangement, candidate, reference)
    if any(extras) and not all(extras):
        raise ValueError("Supply arrangement, candidate and reference together")
    recipe = json.loads(recipe_path.read_text())
    source_hash = digest(source)
    if source_hash != recipe.get("sourceSha256"):
        raise ValueError("Original source SHA-256 does not match the import recipe")
    original = mido.MidiFile(source)
    tempo_map = []
    for index, track in enumerate(original.tracks):
        tick = 0
        for message in track:
            tick += message.time
            if message.type == "set_tempo":
                tempo_map.append({
                    "track": index,
                    "tick": tick,
                    "microsecondsPerQuarter": message.tempo,
                })
    tempo_map.sort(key=lambda event: (event["tick"], event["track"]))
    if not tempo_map or tempo_map[0]["tick"] != 0:
        raise ValueError("The source must declare its opening tempo at tick zero")
    opening_tempo = tempo_map[0]["microsecondsPerQuarter"]
    adapted = mido.MidiFile(type=original.type, ticks_per_beat=original.ticks_per_beat)
    for track in original.tracks:
        adapted.tracks.append(mido.MidiTrack([
            message.copy(tempo=opening_tempo) if message.type == "set_tempo" else message.copy()
            for message in track
        ]))
    verify_events(original, adapted, opening_tempo)
    output.mkdir(parents=True)
    shutil.copyfile(source, output / "source.mid")
    derived_path = output / "constant-tempo.mid"
    adapted.save(derived_path)
    verify_events(original, mido.MidiFile(derived_path), opening_tempo)
    derived_hash = digest(derived_path)
    import_recipe = dict(recipe)
    import_recipe.update({"sourceFile": derived_path.name, "sourceSha256": derived_hash})
    import_recipe["provenance"] = {
        **recipe.get("provenance", {}),
        "originalSourceFile": source.name,
        "originalSourceSha256": source_hash,
        "tempoAdaptation": "All source tempo values replaced by the original opening tempo; event ticks and other MIDI fields preserved. See adaptation.json for the original tempo map.",
    }
    full_recipe = dict(import_recipe)
    full_recipe.pop("performance", None)
    full_common = import_midi(derived_path, full_recipe)
    common = import_midi(derived_path, import_recipe)
    report = {
        "originalSourceSha256": source_hash,
        "derivedMidiSha256": derived_hash,
        "ticksPerQuarter": original.ticks_per_beat,
        "originalTempoMap": tempo_map,
        "constantMicrosecondsPerQuarter": opening_tempo,
        "declaredQuarterBpm": common["quarterBpm"],
        "originalDurationSeconds": original.length,
        "derivedMidiDurationSeconds": adapted.length,
        "eventTicksPreserved": True,
        "sourceNotes": common["provenance"]["importReport"]["sourceNotes"],
        "normalizedNotes": common["provenance"]["importReport"]["normalizedNotes"],
        "fullCommonScore": "full-common-score.json",
        "selectedCommonScore": "common-score.json",
        "selectedTotalBeats": common["totalBeats"],
        "losses": [
            "Source rubato is deliberately replaced by the opening tempo for the initial SID interpretation.",
            "The full common score retains every sounding track and note; the selected common score follows the recipe's explicit performance spans. The importer loss report describes unsupported MIDI metadata and notation.",
        ],
        "importReport": common["provenance"]["importReport"],
    }
    write_json(output / "import-recipe.json", import_recipe)
    write_json(output / "full-common-score.json", full_common)
    write_json(output / "common-score.json", common)
    write_json(output / "adaptation.json", report)
    if all(extras):
        reduction_recipe = json.loads(Path(arrangement).read_text())
        reduction_recipe["recipeFile"] = str(arrangement)
        arranged = arrange_score(common, reduction_recipe)
        write_json(output / "score.json", arranged)
        for name, template_path in (("candidate", candidate), ("reference", reference)):
            template = json.loads(Path(template_path).read_text())
            template["score"] = "score.json"
            write_json(output / (name + ".json"), template)
        report["reduction"] = arranged["provenance"]["reduction"]
        write_json(output / "adaptation.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description="Prepare the source-backed Moon River piano arrangement at its opening tempo")
    parser.add_argument("source", type=Path)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--arrangement", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    try:
        report = prepare_source(args.source, args.recipe, args.output, args.arrangement, args.candidate, args.reference)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps({"output": str(args.output), "sourceNotes": report["sourceNotes"], "normalizedNotes": report["normalizedNotes"], "derivedMidiSha256": report["derivedMidiSha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
