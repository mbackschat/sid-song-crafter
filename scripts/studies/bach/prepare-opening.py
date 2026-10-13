#!/usr/bin/env python3
"""Prepare two original native palettes for the source-backed BWV 565 opening."""

import argparse
from collections import defaultdict
from fractions import Fraction
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from score_tools import beat, import_midi


SOURCE_HASHES = {
    "ToccataFugue.ly": "1640bbd2bf11a95e18db03fea285d30718254af0a694e1c36533d8109d71718c",
    "ToccataFugue.mid": "1aabd00967aded08d6633482c211af46f679d97f01cfeaca43c83a59dfeeeb6b",
}
WARP = [
    (0, 0), (0.5, 2.1), (0.625, 2.3), (1, 3.3), (1.25, 3.8),
    (2, 5.2), (2.5, 7.1), (2.625, 7.3), (3, 8), (3.25, 8.5),
    (4, 10), (4.5, 12), (4.625, 12.2), (5, 13.2), (5.25, 13.8),
    (6, 16), (7, 18), (9, 22), (9.25, 22.4), (9.5, 22.8), (10, 24),
]
PACING_WARPS = {
    "original": WARP,
    "driven": [
        (0, 0), (0.5, 0.8), (0.625, 0.9), (1, 1.9), (1.25, 2.3),
        (2, 2.6), (2.5, 3.4), (2.625, 3.5), (3, 4.2), (3.25, 4.6),
        (4, 4.9), (4.5, 5.7), (4.625, 5.8), (5, 6.8), (5.25, 7.2),
        (6, 7.6), (7, 8.2), (9, 10.2), (9.25, 10.5), (9.5, 10.8), (10, 12),
    ],
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def warp(source_beat, pacing="original"):
    require(pacing in PACING_WARPS, f"Unknown pacing profile: {pacing}")
    position = float(source_beat)
    anchors = PACING_WARPS[pacing]
    for (start, seconds), (end, end_seconds) in zip(anchors, anchors[1:]):
        if start <= position <= end:
            return round(seconds + (position - start) / (end - start) * (end_seconds - seconds), 9)
    raise ValueError("Source beat lies outside the declared opening")


def section_seconds(source_beat, pacing):
    seconds = warp(source_beat, pacing)
    return int(seconds) if seconds.is_integer() else seconds


def instrument(name, adsr, waveform="41", pulse=None, filtr=None):
    return {
        "name": name, "control": "0a", "hard_restart_adsr": "0f00",
        "adsr": adsr, "frame1": "09", "wave": [[waveform, "00", "00"]],
        "pulse": pulse or [], "filter": filtr or [],
    }


def recipes(pacing="original"):
    chord_start, resolution_start, duration = [section_seconds(source, pacing) for source in (7, 9, 10)]
    lead = instrument("BCHLEAD", "0288", pulse=[["87", "80", "00"]])
    bass = instrument("BCHBASS", "02a9", pulse=[["86", "00", "00"]],
                      filtr=[["92", "a0", "00"]])
    harmony = instrument("BCHHARM", "0258", "51", [["86", "00", "00"]])
    common = {
        "format": "sidwizard-arrangement-v1", "score": "score.json",
        "author": "Original SID arrangement", "released": "2026",
        "sidCount": 1, "sidModel": "MOS8580", "timingPolicy": "retain-full-pitch",
    }
    restrained = {
        **common, "title": "Bach opening: sustained", "authorinfo": "ORIGINAL:BACH SUSTAINED OPENING",
        "instruments": {"lead": lead, "bass": bass, "harmony": harmony},
        "sections": [{"name": "Sustained reduced opening", "startBeat": 0, "endBeat": duration,
                      "voices": {"melody": "lead", "bass": "bass", "harmony": "harmony"}}],
    }
    moving_lead = dict(lead, name="BCHPWM", pulse=[
        ["86", "c0", "00"], ["30", "08", "00"], ["30", "f8", "00"], {"jump": 1},
    ])
    # CHORD-01's verified loop requires an explicit waveform at every jump target.
    cycling_harmony = dict(harmony, name="BCHDIM", wave=[
        ["51", f"{offset:02x}", "00"] for offset in (0, 0, 3, 3, 6, 6, 9, 9)
    ] + [{"jump": 0}])
    hybrid = {
        **common, "title": "Bach opening: SID hybrid", "authorinfo": "ORIGINAL:BACH SID HYBRID OPENING",
        "instruments": {"lead": moving_lead, "bass": bass, "harmony": harmony, "diminished-cycle": cycling_harmony},
        "sections": [
            {"name": "Octave gestures and pedal", "startBeat": 0, "endBeat": chord_start,
             "voices": {"melody": "lead", "bass": "bass", "harmony": "harmony"}},
            {"name": "Selective diminished harmony", "startBeat": chord_start, "endBeat": resolution_start,
             "voices": {"melody": "lead", "bass": "bass", "harmony": "diminished-cycle"}},
            {"name": "Written raised-third resolution", "startBeat": resolution_start, "endBeat": duration,
             "voices": {"melody": "lead", "bass": "bass", "harmony": "harmony"}},
        ],
    }
    return {"restrained.json": restrained, "hybrid.json": hybrid}


def prepare(source_dir, output, pacing="original", source_bundle=None):
    source_dir, output = source_dir.resolve(), output.resolve()
    source_bundle = source_bundle.resolve() if source_bundle is not None else None
    require(not output.exists(), "Choose a fresh output directory to preserve prepared inputs")
    require(pacing in PACING_WARPS, f"Unknown pacing profile: {pacing}")
    duration = section_seconds(10, pacing)
    for name, expected in SOURCE_HASHES.items():
        require(digest((source_dir / name).read_bytes()) == expected, f"Pinned source differs: {name}")
    source = import_midi(source_dir / "ToccataFugue.mid", {
        "title": "Toccata and Fugue in D minor, BWV 565: complete Mutopia source",
        "composer": "Johann Sebastian Bach (traditional attribution)",
        "sourceSha256": SOURCE_HASHES["ToccataFugue.mid"], "sourceFile": "source/ToccataFugue.mid",
        "parts": [{"track": 1, "id": "right-manual"}, {"track": 2, "id": "left-manual"}, {"track": 3, "id": "pedal"}],
        "provenance": {"edition": "Mutopia 1780; Bach-Gesellschaft Ausgabe, 1867", "license": "Public Domain"},
    })
    opening = []
    for part in source["parts"]:
        for index, event in enumerate(part["events"]):
            event["sourceId"] = f"{part['id']}-{index:04d}"
            start, end = beat(event["startBeat"]), beat(event["startBeat"]) + beat(event["durationBeats"])
            if start < 10:
                require(end <= 10, "An opening note crosses the declared source boundary")
                opening.append(dict(event, part=part["id"], start=start, end=end))
    require(any(beat(event["startBeat"]) == Fraction(47, 4) and event["midi"] == 61
                for event in source["parts"][0]["events"]), "Expected excluded C-sharp pickup is absent")
    voices = {name: [] for name in ("melody", "bass", "harmony")}
    mapping = []

    def add(role, note, start=None, end=None):
        start = note["start"] if start is None else Fraction(str(start))
        end = note["end"] if end is None else Fraction(str(end))
        require(note["start"] <= start < end <= note["end"], "Prepared event exceeds its source note")
        event = {"startBeat": warp(start, pacing), "durationBeats": round(warp(end, pacing) - warp(start, pacing), 9), "midi": note["midi"]}
        voices[role].append(event)
        mapping.append({"voice": role, "eventIndex": len(voices[role]) - 1, "sourceId": note["sourceId"],
                        "sourceStartBeat": float(start), "sourceEndBeat": float(end), "transposeSemitones": 0,
                        **event})

    def find(part, start, midi):
        found = [note for note in opening if note["part"] == part and note["start"] == start and note["midi"] == midi]
        require(len(found) == 1, f"Expected one source note: {part}, beat {start}, MIDI {midi}")
        return found[0]

    gestures = defaultdict(list)
    for note in opening:
        if note["start"] < 6:
            gestures[note["start"]].append(note)
    for start, notes in sorted(gestures.items()):
        require(len(notes) == 2 and abs(notes[0]["midi"] - notes[1]["midi"]) == 12,
                "Opening gesture is not the expected source octave pair")
        low, high = sorted(notes, key=lambda item: item["midi"])
        add("melody", high)
        add("bass", low)
    add("bass", find("pedal", 6, 38))
    add("melody", find("right-manual", 7, 64))
    add("melody", find("right-manual", 9, 62))
    add("harmony", find("left-manual", 7, 55), 7, 9)
    add("harmony", find("left-manual", 7, 55), 9, 9.25)
    add("harmony", find("left-manual", Fraction(37, 4), 52))
    add("harmony", find("left-manual", Fraction(19, 2), 54))
    for name, events in voices.items():
        previous_end = 0
        for event in events:
            end = round(event["startBeat"] + event["durationBeats"], 9)
            require(event["startBeat"] >= previous_end and event["durationBeats"] > 0 and end <= duration,
                    f"Unsorted, overlapping or out-of-range event in {name}")
            require(12 <= event["midi"] <= 106, "Prepared pitch is outside the native note range")
            previous_end = end
    retained = {entry["sourceId"] for entry in mapping}
    cycle_notes = [find("left-manual", 7, 55)] + [find("right-manual", 7, midi) for midi in (58, 61, 64)]
    require([note["midi"] for note in cycle_notes] == [55, 58, 61, 64], "Chord cycle is not source-backed")
    source_data = json_bytes(source)
    complete_source = "source-notes.json"
    source_paths = {name: f"source/{name}" for name in SOURCE_HASHES}
    if source_bundle is not None:
        require(digest((source_bundle / "source-notes.json").read_bytes()) == digest(source_data),
                "Shared complete source notes differ from the pinned import")
        complete_source = Path(os.path.relpath(source_bundle / "source-notes.json", output)).as_posix()
        for name, expected in SOURCE_HASHES.items():
            source_path = source_bundle / "source" / name
            require(digest(source_path.read_bytes()) == expected, f"Shared pinned source differs: {name}")
            source_paths[name] = Path(os.path.relpath(source_path, output)).as_posix()
    score = {
        "title": f"Bach Toccata opening: {pacing} SID pacing", "composer": "J. S. Bach; original SID arrangement",
        "quarterBpm": 60, "timeSignature": [4, 4], "totalBeats": duration, "tailTicks": 125, "volume": 15,
        "voices": [{"name": name, "events": events} for name, events in voices.items()],
        "provenance": {"completeSource": complete_source, "completeSourceSha256": digest(source_data),
                       "sourceBeatRange": [0, 10], "timing": f"Seconds encoded as beats at quarterBpm 60; deliberate {pacing} pacing, not a recording alignment",
                       "preparation": "preparation.json"},
    }
    prepared_recipes = recipes(pacing)
    spec = importlib.util.spec_from_file_location("native_instruments", ROOT / "scripts/generate-native-instruments.py")
    encoder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(encoder)
    for recipe in prepared_recipes.values():
        for identity, patch in recipe["instruments"].items():
            require(patch["frame1"] == "09", "Every native patch must retain TEST silence on frame one")
            encoder.instrument_bytes(identity, patch)
    def omitted(retained_ids):
        return [{"sourceId": note["sourceId"], "part": note["part"], "midi": note["midi"],
                 "startBeat": float(note["start"]), "endBeat": float(note["end"])}
                for note in opening if note["sourceId"] not in retained_ids]
    metadata = {
        "date": "2026-10-14", "evidenceLevel": "prepared inputs; not rendered or listening-reviewed",
        "scriptSha256": digest(Path(__file__).read_bytes()), "sources": {name: {"path": source_paths[name], "sha256": value} for name, value in SOURCE_HASHES.items()},
        "completeSourceNotesSha256": digest(source_data), "sourceBeatRange": [0, 10],
        "excludedNextPickup": {"sourceBeat": 11.75, "midi": [49, 61]},
        "warpAnchors": [{"sourceBeat": source_beat, "arrangementSeconds": seconds} for source_beat, seconds in PACING_WARPS[pacing]],
        "phrasing": "Expand the three opening A fermatas and intervening silence; retain each descent; let the pedal precede the diminished hold; resolve and release at 24 seconds. This is tighter original SID pacing, not a match to Kibbie.",
        "ornaments": "The MIDI omits printed prall ornaments and fermatas. Fermatas become the explicit warp; prall ornaments are omitted in this first audition. The written chord arpeggio becomes a simultaneous reduced onset; only the hybrid's held chord cycles thereafter.",
        "mapping": mapping, "scoreEvents": {name: len(events) for name, events in voices.items()},
        "reductions": {"restrained": omitted(retained), "hybrid": omitted(retained | {note["sourceId"] for note in cycle_notes})},
        "chordCycle": {"sourceBeatRange": [7, 9], "arrangementSeconds": [section_seconds(source, pacing) for source in (7, 9)], "carrierMidi": 55,
                       "midiCycle": [55, 55, 58, 58, 61, 61, 64, 64], "sourceIds": [note["sourceId"] for note in cycle_notes],
                       "dwellPalCallsPerTone": 2, "scope": "Hybrid only: alternating pitches on one voice, not independent sustained chord tones"},
        "rearticulation": "Split the written tied G3 at source beat 9 to stop the hybrid chord cycle and expose the G-E-F-sharp resolution. The native backend reselects instruments and may retrigger gates; no legato equivalence is claimed.",
        "palettes": {"restrained": "Our reduced sustained SID reference, not an acoustic organ recording", "hybrid": "Our lead PWM plus selective source-tone chord cycling; proposed listening candidate, not approved"},
        "target": {"sidCount": 1, "sidModel": "MOS8580", "clock": "PAL", "concertAHz": 440, "frame1": "09", "timingPolicy": "retain-full-pitch", "sharedFilterOwner": "bass"},
        "modelAssistanceReview": {"date": "2026-10-14", "checkpoint": "First opening preparation", "decision": "skip audio-model inference",
                                  "reason": "No model has a validated organ/chip-character criterion; source mapping and existing CPU guards settle correctness, while musical impact needs human feedback",
                                  "nextCheckpoint": "After the first representative audition and listener feedback"},
    }
    if pacing == "driven":
        metadata["pacingProfile"] = pacing
        metadata["phrasing"] = f"Shorten the three opening A fermatas to 0.8 seconds and compress the intervening gaps; preserve each descent's original speed; let the pedal precede a two-second diminished hold; resolve and release at {duration} seconds. This responds to listener feedback about slow pacing and unwanted pauses, without changing pitches or sound programs."
        metadata["modelAssistanceReview"]["checkpoint"] = "Driven pacing revision after listener feedback"
        metadata["modelAssistanceReview"]["reason"] = "No model has a validated phrasing/energy criterion; source mapping and timing guards settle correctness, while the faster interpretation needs human feedback"
        metadata["modelAssistanceReview"]["nextCheckpoint"] = "After the driven opening audition and listener feedback"
    output.mkdir(parents=True)
    files = {"score.json": json_bytes(score), "preparation.json": json_bytes(metadata),
             **{name: json_bytes(recipe) for name, recipe in prepared_recipes.items()}}
    if source_bundle is None:
        (output / "source").mkdir()
        for name in SOURCE_HASHES:
            shutil.copyfile(source_dir / name, output / "source" / name)
        files = {"source-notes.json": source_data, **files}
    for name, data in files.items():
        (output / name).write_bytes(data)
    print(json.dumps({"output": str(output), "scoreEvents": metadata["scoreEvents"], "seconds": duration,
                      "sourceOpeningNotes": len(opening), "recipes": list(prepared_recipes)}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "build/bach-source-intake")
    parser.add_argument("--output", type=Path, default=ROOT / "songs/studies/bach-toccata-opening")
    parser.add_argument("--pacing", choices=tuple(PACING_WARPS), default="original")
    parser.add_argument("--source-bundle", type=Path, help="Hash-verify and reference an existing complete source bundle instead of copying it")
    args = parser.parse_args()
    prepare(args.source_dir.resolve(), args.output.resolve(), args.pacing,
            args.source_bundle.resolve() if args.source_bundle is not None else None)


if __name__ == "__main__":
    main()
