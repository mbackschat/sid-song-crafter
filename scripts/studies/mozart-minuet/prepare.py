"""Prepare the complete source-backed K. 525 Menuetto/Trio for native mono and stereo."""

import argparse
from collections import defaultdict
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[3]
STUDY = ROOT / "songs/mozart-minuet"
sys.path.insert(0, str(ROOT / "scripts"))
from score_tools import beat, import_midi, rational


PARTS = ("violin-1", "violin-2", "viola", "cello")
SOURCE_COUNTS = (167, 180, 155, 82)
# source/03_allegretto/cello.ily and the 1883 score mark four repeats and Menuetto da capo; our declared return omits repeats.
FORM = ((0, 24), (0, 24), (24, 48), (24, 48), (48, 72), (48, 72), (72, 108), (72, 108), (0, 24), (24, 48))
DOUBLE_STOPS = {Fraction(21): (60, 62), Fraction(22): (59, 62), Fraction(45): (60, 62), Fraction(46): (59, 62)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def identity(origin):
    return origin["sourcePart"], origin["sourceEventIndex"], origin["spanIndex"]


def source_origins(full, common, spans):
    origins = {part: [] for part in PARTS}
    offset = Fraction(0)
    for span_index, span in enumerate(spans):
        start, end = beat(span["startBeat"]), beat(span["endBeat"])
        for part in full["parts"]:
            for index, event in enumerate(part["events"]):
                onset = beat(event["startBeat"])
                if start <= onset < end:
                    origins[part["id"]].append({
                        "sourcePart": part["id"], "sourceEventIndex": index, "spanIndex": span_index,
                        "sourceStartBeat": event["startBeat"], "startBeat": rational(offset + onset - start),
                        **{key: value for key, value in event.items() if key != "startBeat"},
                    })
        offset += end - start
    for part in common["parts"]:
        projected = [{key: origin[key] for key in ("startBeat", "durationBeats", "midi", "velocity")}
                     for origin in origins[part["id"]]]
        require(projected == part["events"], "Unfolded origins differ from the complete imported score")
    return origins


def lower_viola(origins):
    groups = defaultdict(list)
    for origin in origins:
        groups[beat(origin["startBeat"])].append(origin)
    chosen = []
    for group in groups.values():
        if len(group) > 1:
            source_onset = beat(group[0]["sourceStartBeat"])
            require(tuple(sorted(note["midi"] for note in group)) == DOUBLE_STOPS.get(source_onset)
                    and all(beat(note["durationBeats"]) == 1 for note in group),
                    "Unexpected viola double stop; review the retained source before reducing it")
        chosen.append(min(group, key=lambda note: note["midi"]))
    return chosen


def arranged_score(common, plan, voices, origins, *, stereo):
    output, uses = [], defaultdict(list)
    for voice_index, (name, notes) in enumerate(voices):
        events, previous_end = [], Fraction(0)
        for origin in notes:
            start, duration = beat(origin["startBeat"]), beat(origin["durationBeats"])
            require(start >= previous_end and duration > 0 and start + duration <= 264,
                    "Arranged voice overlaps or leaves the complete movement: " + name)
            events.append({"startBeat": float(start), "durationBeats": float(duration), "midi": origin["midi"]})
            uses[identity(origin)].append({"voice": name, "voiceIndex": voice_index, "outputEventIndex": len(events) - 1})
            previous_end = start + duration
        output.append({"name": name, "instrument": {"waveform": 16, "attackDecay": 2, "sustainRelease": 128}, "events": events})
    retained, omitted = [], []
    for part in PARTS:
        for origin in origins[part]:
            targets = uses.get(identity(origin), [])
            if targets:
                retained.append({**origin, "outputs": targets})
            else:
                reason = "Omit upper D4 from the viola double stop; retain lower C4/B3 harmonic color"
                if not stereo and (part == "violin-2" or part == "viola" and beat(origin["sourceStartBeat"]) >= 48):
                    reason = "Omit the complementary inner part for this section's three-voice reduction"
                omitted.append({**origin, "reason": reason})
    source_count = sum(len(notes) for notes in origins.values())
    require(len(retained) + len(omitted) == source_count and len(uses) == len(retained),
            "Every performed source note must be retained or explicitly omitted")
    report = {
        "sourceNotes": source_count, "retainedSourceNotes": len(retained), "omittedSourceNotes": len(omitted),
        "outputEvents": sum(len(voice["events"]) for voice in output),
        "duplicatedSourceNotes": sum(len(note["outputs"]) > 1 for note in retained),
        "voiceNoteCounts": {voice["name"]: len(voice["events"]) for voice in output},
        "retainedEvents": retained, "omittedEvents": omitted, "shortenedNotes": 0,
    }
    score = {
        "title": "Mozart K. 525 III: Menuetto and Trio" + (" stereo" if stereo else " mono"),
        "composer": "Wolfgang Amadeus Mozart", "quarterBpm": plan.get("quarterBpm", common["quarterBpm"]),
        "timeSignature": common["timeSignature"], "totalBeats": 264, "tailTicks": plan["tailTicks"], "volume": 15,
        "voices": output, "provenance": {**common["provenance"], "arrangement": plan["decisions"],
                                            "adaptationReport": "adaptation.json"},
    }
    return score, report


def prepare(output, arrangement=STUDY / "arrangement.json"):
    output, arrangement = Path(output), Path(arrangement)
    require(not output.exists(), "Choose a fresh output directory")
    plan, import_recipe = read_json(arrangement), read_json(STUDY / "import.json")
    require(plan["format"] == "mozart-minuet-arrangement-v1", "Unsupported case arrangement format")
    require(tuple((span["startBeat"], span["endBeat"]) for span in plan["spans"]) == FORM,
            "Complete form must retain AABBCCDDAB, including the Menuetto return")
    require(plan["violaPolicy"] == "lowest-at-onset" and plan["monoInner"] == {"menuetto": "viola", "trio": "violin-2"},
            "Review source-role changes explicitly before changing this case preparation")
    if "quarterBpm" in plan:
        require(type(plan["quarterBpm"]) in (int, float) and math.isfinite(plan["quarterBpm"]) and plan["quarterBpm"] > 0,
                "Tempo must be positive and finite")
    require(type(plan["tailTicks"]) is int and plan["tailTicks"] > 0, "Release tail must contain positive PAL ticks")
    hashes = read_json(STUDY / "source/hashes.json")
    for relative, expected in hashes.items():
        require(hashlib.sha256((STUDY / "source" / relative).read_bytes()).hexdigest() == expected,
                "Retained source hash changed: " + relative)
    source = ROOT / import_recipe["sourceFile"]
    full = import_midi(source, import_recipe)
    require(tuple(part["id"] for part in full["parts"]) == PARTS
            and tuple(len(part["events"]) for part in full["parts"]) == SOURCE_COUNTS
            and beat(full["totalBeats"]) == 108 and full["timeSignature"] == [3, 4]
            and full["provenance"]["importReport"]["microsecondsPerQuarter"] == 535714,
            "Source part, event, timing or form guard failed")
    performance = {"sourceTotalBeats": 108, "spans": [{key: span[key] for key in ("startBeat", "endBeat")} for span in plan["spans"]]}
    common = import_midi(source, {**import_recipe, "performance": performance})
    bpm = plan.get("quarterBpm", common["quarterBpm"])
    require(beat(common["totalBeats"]) == 264, "Performed movement must contain 264 beats")
    origins = source_origins(full, common, plan["spans"])
    viola = lower_viola(origins["viola"])
    inner = sorted([note for note in viola if beat(note["sourceStartBeat"]) < 48]
                   + [note for note in origins["violin-2"] if beat(note["sourceStartBeat"]) >= 48],
                   key=lambda note: beat(note["startBeat"]))
    mono, mono_report = arranged_score(common, plan, [("melody", origins["violin-1"]), ("bass", origins["cello"]), ("inner", inner)], origins, stereo=False)
    stereo, stereo_report = arranged_score(common, plan, [("melody", origins["violin-1"]), ("bass", origins["cello"]),
        ("second", origins["violin-2"]), ("melody-right", origins["violin-1"]),
        ("bass-right", origins["cello"]), ("viola", viola)], origins, stereo=True)
    templates = [STUDY / name for name in ("mono.json", "stereo.json", "plain.json")]
    require(all(path.is_file() for path in templates), "Native palette templates must exist before preparation")
    report = {
        "schemaVersion": 1, "sourceSha256": full["provenance"]["sourceSha256"], "sourceHashes": hashes,
        "sourceNotes": sum(SOURCE_COUNTS), "performedSourceNotes": sum(len(part["events"]) for part in common["parts"]),
        "sourceBeats": 108, "totalBeats": 264, "sourceQuarterBpm": common["quarterBpm"], "quarterBpm": bpm,
        "noteTiming": "Retain exact source beat onsets and durations; no transposition, invented notes, extensions or shortening. Original velocities remain in common-score.json and origin records; native programs set dynamics.",
        "form": plan["spans"], "decisions": plan["decisions"], "mono": mono_report, "stereo": stereo_report,
    }
    output.mkdir(parents=True)
    for name, value in (("common-score", common), ("score-mono", mono), ("score-stereo", stereo), ("adaptation", report)):
        write_json(output / (name + ".json"), value)
    for template in templates:
        shutil.copyfile(template, output / template.name)
    print(json.dumps({"output": str(output), "totalBeats": 264, "quarterBpm": bpm,
                      "monoNoteCounts": mono_report["voiceNoteCounts"], "stereoNoteCounts": stereo_report["voiceNoteCounts"]}, sort_keys=True))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--arrangement", type=Path, default=STUDY / "arrangement.json")
    args = parser.parse_args()
    try:
        prepare(args.output, args.arrangement)
    except (KeyError, OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
