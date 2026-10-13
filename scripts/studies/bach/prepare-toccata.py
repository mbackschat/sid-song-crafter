#!/usr/bin/env python3
"""Prepare the complete source-backed single-SID Toccata, preserving its accepted opening."""

import argparse
from collections import defaultdict
import copy
from enum import Enum
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PLAN = ROOT / "songs/studies/bach-toccata-full/arrangement.json"
SOURCE_HASH = "04fb11fcf3d643ffa152b0050e14297e3df64b4ababbd12209f3d4cee8022329"
SOURCE_HASHES = {
    "ToccataFugue.ly": "1640bbd2bf11a95e18db03fea285d30718254af0a694e1c36533d8109d71718c",
    "ToccataFugue.mid": "1aabd00967aded08d6633482c211af46f679d97f01cfeaca43c83a59dfeeeb6b",
}
ROLES = ("melody", "bass", "harmony")
PATCHES = {"melody": "lead", "bass": "bass", "harmony": "harmony"}
PAL_RATE = (17734475 / 18) / (312 * 63)


class Voicing(Enum):
    MANUAL_PAIR = "manual-pair"
    PEDAL_AND_MANUALS = "pedal-and-manuals"
    RIGHT_HAND_LED = "right-hand-led"
    INTERLEAVED_MANUALS = "interleaved-manuals"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def number(value):
    return Fraction(*value) if isinstance(value, list) else Fraction(str(value))


def span(entry):
    return tuple(number(value) for value in entry["sourceBeatRange"])


def contains(entry, position):
    start, end = span(entry)
    return start <= position < end


def warp(position, anchors):
    position = number(position)
    for (start, seconds), (end, end_seconds) in zip(anchors, anchors[1:]):
        if number(start) <= position <= number(end):
            proportion = float((position - number(start)) / (number(end) - number(start)))
            return round(seconds + proportion * (end_seconds - seconds), 9)
    raise ValueError(f"Source beat {position} lies outside the Toccata timing map")


def latest(notes, high=True):
    return max(notes, key=lambda note: (note["start"], note["midi"] if high else -note["midi"])) if notes else None


def choose_voices(active, mode):
    manuals = [note for note in active if note["part"] != "pedal"]
    right = [note for note in manuals if note["part"] == "right-manual"]
    left = [note for note in manuals if note["part"] == "left-manual"]
    pedal = latest([note for note in active if note["part"] == "pedal"], high=False)
    if mode == Voicing.INTERLEAVED_MANUALS:
        melody, bass = latest(manuals), pedal
    elif mode == Voicing.MANUAL_PAIR:
        melody, bass = latest(right), pedal or latest(left, high=False)
    elif mode == Voicing.RIGHT_HAND_LED:
        return {"melody": latest(right), "bass": pedal, "harmony": latest(left, high=False)}
    elif mode == Voicing.PEDAL_AND_MANUALS:
        melody, bass = latest(right), pedal
    else:
        raise ValueError(f"Unsupported voicing mode: {mode}")
    used = {note["sourceId"] for note in (melody, bass) if note is not None}
    harmony = latest([note for note in manuals if note["sourceId"] not in used], high=False)
    return {"melody": melody, "bass": bass, "harmony": harmony}


def combined_intervals(intervals):
    result = []
    for start, end in sorted(intervals):
        if result and start <= result[-1][1]:
            result[-1][1] = max(end, result[-1][1])
        else:
            result.append([start, end])
    return result


def uncovered(start, end, intervals):
    result, cursor = [], start
    for first, last in combined_intervals(intervals):
        if first > cursor:
            result.append([cursor, first])
        cursor = max(cursor, last)
    if cursor < end:
        result.append([cursor, end])
    return result


def prepare(plan_path, output):
    plan_path, output = Path(plan_path).resolve(), Path(output).resolve()
    require(not output.exists(), "Choose a fresh output directory to preserve prepared workfiles")
    plan_bytes = plan_path.read_bytes()
    plan = json.loads(plan_bytes)
    require(plan["format"] == "bach-toccata-arrangement-v1", "Unsupported Toccata arrangement plan")
    require(plan["sourceBeatRange"] == [0, 118], "The complete Toccata ends at source beat 118 before the Fugue")
    bundle = (ROOT / plan["sourceBundle"]).resolve()
    opening = (ROOT / plan["acceptedOpening"]).resolve()
    source_bytes = (bundle / "source-notes.json").read_bytes()
    require(digest(source_bytes) == SOURCE_HASH, "Pinned complete source notes differ")
    for name, expected in SOURCE_HASHES.items():
        require(digest((bundle / "source" / name).read_bytes()) == expected, f"Pinned source differs: {name}")
    accepted_score = json.loads((opening / "score.json").read_bytes())
    accepted_metadata = json.loads((opening / "preparation.json").read_bytes())
    accepted_hybrid = json.loads((opening / "hybrid.json").read_bytes())
    accepted_restrained = json.loads((opening / "restrained.json").read_bytes())
    require(accepted_score["totalBeats"] == 12 and accepted_score["provenance"]["sourceBeatRange"] == [0, 10],
            "The accepted driven opening must cover source 0–10 in twelve seconds")
    anchors = [(entry["sourceBeat"], entry["arrangementSeconds"]) for entry in accepted_metadata["warpAnchors"]]
    require(plan["continuationAnchors"][0] == [10, 12], "Continuation must preserve the accepted opening endpoint")
    anchors += [tuple(entry) for entry in plan["continuationAnchors"][1:]]
    require(anchors[-1][0] == 118, "Timing map must end before the Fugue")
    require(all(a < b and seconds < last for (a, seconds), (b, last) in zip(anchors, anchors[1:])),
            "Timing anchors must be strictly increasing")
    previous = Fraction(10)
    for scene in plan["scenes"]:
        first, last = span(scene)
        require(first == previous and first < last, "Voicing scenes must continuously cover the continuation")
        Voicing(scene["mode"])
        previous = last
    require(previous == 118, "Voicing scenes must end at source beat 118")

    notes = {}
    for part in json.loads(source_bytes)["parts"]:
        for event in part["events"]:
            start = number(event["startBeat"])
            if start < 118:
                notes[event["sourceId"]] = dict(event, part=part["id"], start=start,
                                                end=min(start + number(event["durationBeats"]), Fraction(118)))
    require(len(notes) == 940, "Pinned Toccata scope must retain all 940 source events")

    cycles = copy.deepcopy(plan["chordCycles"])
    patches = copy.deepcopy(accepted_hybrid["instruments"])
    patch_names = {"dominant-cycle": "BCHDOM", "minor-cycle": "BCHMIN",
                   "subdominant-cycle": "BCHSUB", "dominant-inner-cycle": "BCHINNR"}
    for cycle in cycles:
        first, last = span(cycle)
        carrier = notes[cycle["carrierSourceId"]]
        tones = [notes[identity] for identity in cycle["sourceIds"]]
        require(all(note["start"] <= first < last <= note["end"] for note in tones),
                "Every cycle tone must be active in the source chord")
        offsets = [note["midi"] - carrier["midi"] for note in tones for _ in range(2)]
        require(all(0 <= offset < 0x60 for offset in offsets), "Cycle requires supported relative native offsets")
        wave = [["51", f"{offset:02x}", "00"] for offset in offsets] + [{"jump": 0}]
        identity = cycle["instrumentId"]
        if identity in patches:
            require(patches[identity]["wave"] == wave, "Retained cycle patch differs from the authored chord")
        else:
            patches[identity] = dict(copy.deepcopy(patches["harmony"]), name=patch_names[identity], wave=wave)
        cycle.update(carrierMidi=carrier["midi"], midiCycle=[carrier["midi"] + offset for offset in offsets],
                     dwellPalCallsPerTone=2, arrangementSeconds=[warp(first, anchors), warp(last, anchors)],
                     scope="Time-shared source tones on one voice; independent sustained chord tails are reduced")

    boundaries = {Fraction(10), Fraction(118)}
    for note in notes.values():
        boundaries.update(value for value in (note["start"], note["end"]) if 10 < value < 118)
    for entry in plan["scenes"] + plan["voiceOverrides"] + cycles + plan["octaveChanges"]:
        boundaries.update(span(entry))
    for ornament in plan["ornaments"]:
        first, last = span(ornament)
        note = notes[ornament["sourceId"]]
        require(note["start"] == first and note["end"] == last, "Ornament must identify its complete printed principal note")
        boundaries.update(first + (last - first) * index / len(ornament["offsets"])
                          for index in range(len(ornament["offsets"]) + 1))

    selected = {role: [] for role in ROLES}
    ordered = sorted(boundaries)
    for first, last in zip(ordered, ordered[1:]):
        scene = next(scene for scene in plan["scenes"] if contains(scene, first))
        active = [note for note in notes.values() if note["start"] <= first < note["end"]]
        voices = choose_voices(active, Voicing(scene["mode"]))
        for override in plan["voiceOverrides"]:
            if contains(override, first):
                note = notes[override["sourceId"]]
                require(note in active and last <= note["end"], "Voice override exceeds its source note")
                voices[override["voice"]] = note
        identities = dict(PATCHES)
        for cycle in cycles:
            if contains(cycle, first):
                voices[cycle["voice"]] = notes[cycle["carrierSourceId"]]
                identities[cycle["voice"]] = cycle["instrumentId"]
        require(len({note["sourceId"] for note in voices.values() if note}) == len([note for note in voices.values() if note]),
                "A source note cannot occupy two static voice lanes at once")
        for role, note in voices.items():
            if note is None:
                continue
            transpose, derivation = 0, None
            for change in plan["octaveChanges"]:
                if change["voice"] == role and change["sourcePart"] == note["part"] and contains(change, first):
                    transpose += change["semitones"]
                    derivation = {"kind": "octave-reduction", "basis": change["reason"]}
            for ornament in plan["ornaments"]:
                if ornament["sourceId"] == note["sourceId"] and contains(ornament, first):
                    beginning, ending = span(ornament)
                    index = int((first - beginning) / (ending - beginning) * len(ornament["offsets"]))
                    transpose += ornament["offsets"][index]
                    derivation = {"kind": ornament["kind"], "basis": ornament["basis"],
                                  "interpretation": ornament["interpretation"], "ornamentStep": index}
            item = {"sourceId": note["sourceId"], "start": first, "end": last,
                    "transposeSemitones": transpose, "midi": note["midi"] + transpose,
                    "instrumentId": identities[role], "derivation": derivation}
            track = selected[role]
            if track and track[-1]["end"] == first and all(track[-1][key] == item[key]
                    for key in ("sourceId", "transposeSemitones", "instrumentId", "derivation")):
                track[-1]["end"] = last
            else:
                track.append(item)

    score = copy.deepcopy(accepted_score)
    score.update(title="Toccata from BWV 565: complete single-SID hybrid", totalBeats=warp(118, anchors),
                 tailTicks=plan["tailTicks"])
    mapping = copy.deepcopy(accepted_metadata["mapping"])
    for entry in mapping:
        section = next(section for section in accepted_hybrid["sections"]
                       if section["startBeat"] <= entry["startBeat"] < section["endBeat"])
        entry["instrumentId"] = section["voices"][entry["voice"]]
    for voice in score["voices"]:
        role = voice["name"]
        for item in selected[role]:
            start, end = warp(item["start"], anchors), warp(item["end"], anchors)
            event = {"startBeat": start, "durationBeats": round(end - start, 9), "midi": item["midi"]}
            mapping.append({"voice": role, "eventIndex": len(voice["events"]), "sourceId": item["sourceId"],
                            "sourceStartBeat": round(float(item["start"]), 9), "sourceEndBeat": round(float(item["end"]), 9),
                            "transposeSemitones": item["transposeSemitones"], "instrumentId": item["instrumentId"],
                            **({"derivation": item["derivation"]} if item["derivation"] else {}), **event})
            voice["events"].append(event)
    score["provenance"] = {
        "completeSource": Path(os.path.relpath(bundle / "source-notes.json", output)).as_posix(),
        "completeSourceSha256": SOURCE_HASH, "sourceBeatRange": [0, 118],
        "timing": plan["timing"], "preparation": "preparation.json", "arrangementPlan": "arrangement.json",
    }
    shortest = None
    for voice in score["voices"]:
        previous_end = 0
        for index, event in enumerate(voice["events"]):
            start, end = event["startBeat"], round(event["startBeat"] + event["durationBeats"], 9)
            require(start >= previous_end - 1e-8 and end <= score["totalBeats"] + 1e-8, "Overlapping or out-of-range arranged notes")
            ticks = math.floor(end * PAL_RATE + .5) - math.floor(start * PAL_RATE + .5)
            require(ticks >= 2, f"{voice['name']} event {index} lacks a native full-pitch body frame")
            require(12 <= event["midi"] <= 106, "Pitch lies outside the native note range")
            shortest = ticks if shortest is None else min(shortest, ticks)
            previous_end = end

    sections = copy.deepcopy(accepted_hybrid["sections"])
    section_boundaries = sorted({value for entry in plan["scenes"] + cycles for value in span(entry)})
    for first, last in zip(section_boundaries, section_boundaries[1:]):
        scene = next(scene for scene in plan["scenes"] if contains(scene, first))
        voices = dict(PATCHES)
        for cycle in cycles:
            if contains(cycle, first):
                voices[cycle["voice"]] = cycle["instrumentId"]
        sections.append({"name": scene["name"], "startBeat": warp(first, anchors), "endBeat": warp(last, anchors), "voices": voices})
    hybrid = copy.deepcopy(accepted_hybrid)
    hybrid.update(title="Bach Toccata: full SID hybrid", authorinfo="ORIGINAL:BACH TOCCATA SID HYBRID",
                  instruments=patches, sections=sections)
    restrained = copy.deepcopy(accepted_restrained)
    restrained.update(title="Bach Toccata: reduced sustained SID", authorinfo="ORIGINAL:BACH TOCCATA SUSTAINED",
                       sections=[{"name": "Reduced sustained SID reference", "startBeat": 0,
                                  "endBeat": score["totalBeats"], "voices": dict(PATCHES)}])
    encoder_spec = importlib.util.spec_from_file_location("bach_instrument_encoder", ROOT / "scripts/generate-native-instruments.py")
    encoder = importlib.util.module_from_spec(encoder_spec)
    encoder_spec.loader.exec_module(encoder)
    for identity, patch in patches.items():
        require(patch["frame1"] == "09", "Native first frame must retain TEST silence")
        encoder.instrument_bytes(identity, patch)

    opening_cycle = dict(copy.deepcopy(accepted_metadata["chordCycle"]), voice="harmony", instrumentId="diminished-cycle")
    all_cycles = [opening_cycle] + cycles
    representations = defaultdict(list)
    for entry in accepted_metadata["mapping"]:
        representations[entry["sourceId"]].append((number(entry["sourceStartBeat"]), number(entry["sourceEndBeat"])))
    for track in selected.values():
        for entry in track:
            representations[entry["sourceId"]].append((entry["start"], entry["end"]))
    cycle_representations = defaultdict(list)
    for cycle in all_cycles:
        first, last = span(cycle)
        for identity in cycle["sourceIds"]:
            cycle_representations[identity].append((first, last))
    disposition = []
    for identity, note in notes.items():
        static = representations[identity]
        cycled = cycle_representations[identity]
        intervals = combined_intervals(static + cycled)
        gaps = uncovered(note["start"], note["end"], intervals)
        if not intervals:
            status = "omitted"
        elif gaps:
            status = "partial"
        elif cycled:
            status = "cycled"
        else:
            status = "retained"
        scene = next((scene for scene in plan["scenes"] if contains(scene, max(note["start"], Fraction(10)))), None)
        reason = "Accepted opening's three-voice octave/pedal/chord reduction; preserve its frozen voicing."
        if note["start"] >= 10 and scene is not None:
            reason = scene["reduction"]
        disposition.append({"sourceId": identity, "part": note["part"], "midi": note["midi"],
                            "sourceStartBeat": float(note["start"]), "sourceEndBeat": float(note["end"]),
                            "status": status, "representedIntervals": [[float(a), float(b)] for a, b in intervals],
                            "omittedIntervals": [[float(a), float(b)] for a, b in gaps],
                            "reason": reason if status != "retained" else "Source event retained; authored timing and any octave/ornament derivation are recorded in mapping."})
    counts = {status: sum(entry["status"] == status for entry in disposition) for status in ("retained", "partial", "cycled", "omitted")}
    score_ticks = math.floor(score["totalBeats"] * PAL_RATE + .5)
    metadata = {
        "date": "2026-10-14", "evidenceLevel": "prepared editable inputs; full-form musical acceptance pending",
        "scriptSha256": digest(Path(__file__).read_bytes()), "arrangementPlanSha256": digest(plan_bytes),
        "sources": {name: {"path": Path(os.path.relpath(bundle / "source" / name, output)).as_posix(), "sha256": expected}
                    for name, expected in SOURCE_HASHES.items()},
        "completeSourceNotesSha256": SOURCE_HASH, "sourceBeatRange": [0, 118],
        "scope": "Toccata from BWV 565: measures 1–29 and measure 30 beats 1–2; no Fugue",
        "excludedFuguePickup": {"sourceId": "left-manual-0360", "sourceBeat": 118.25, "midi": 69},
        "acceptedOpening": {"path": Path(os.path.relpath(opening / "hybrid.json", output)).as_posix(),
                            "scoreSha256": digest((opening / "score.json").read_bytes()),
                            "recipeSha256": digest((opening / "hybrid.json").read_bytes()),
                            "arrangementSeconds": [0, 12], "sourceBeatRange": [0, 10],
                            "contract": "Score events and first four sound programs remain unchanged; the former ending becomes a continuation."},
        "warpAnchors": [{"sourceBeat": source, "arrangementSeconds": seconds} for source, seconds in anchors],
        "mapping": mapping, "chordCycles": all_cycles, "sourceDisposition": disposition,
        "sourceNotes": len(notes), "sourceDispositionCounts": counts,
        "scoreEvents": {voice["name"]: len(voice["events"]) for voice in score["voices"]},
        "sections": [{"name": scene["name"], "sourceBeatRange": scene["sourceBeatRange"],
                      "arrangementSeconds": [warp(first, anchors) for first in scene["sourceBeatRange"]],
                      "reduction": scene["reduction"]} for scene in plan["scenes"]],
        "ornaments": plan["ornaments"], "reviewUncertainties": plan["reviewUncertainties"],
        "nativeTiming": {"ticksPerSecond": PAL_RATE, "minimumDurationTicks": shortest, "scoreTicks": score_ticks,
                         "tailTicks": score["tailTicks"], "stopTick": score_ticks + score["tailTicks"],
                         "policy": "Reserve at least two PAL calls per note; no borrowed note timing is needed."},
        "target": {"sidCount": 1, "sidModel": "MOS8580", "clock": "PAL", "concertAHz": 440,
                   "frame1": "09", "timingPolicy": "retain-full-pitch", "sharedFilterOwner": "bass"},
        "paletteReference": "restrained.json is our same-score reduced sustained SID palette, not an acoustic organ transcription or performance reference.",
        "rearticulation": "Native note selection resets sound tables. At tempo 1 adjacent notes can retain envelope state; no organ legato or independent overlapping tails are claimed.",
        "modelAssistanceReview": {"date": "2026-10-14", "checkpoint": "Full Toccata preparation",
                                  "decision": "skip unvalidated audio-model musical judgment",
                                  "reason": "The Bach pacing calibration failed its identical-pair gate; source/execution checks and human full-form listening settle different questions.",
                                  "nextCheckpoint": "Full representative audition, listener feedback and pre-closure review"},
    }
    output.mkdir(parents=True)
    for name, data in {"arrangement.json": plan_bytes, "score.json": json_bytes(score), "hybrid.json": json_bytes(hybrid),
                       "restrained.json": json_bytes(restrained), "preparation.json": json_bytes(metadata)}.items():
        (output / name).write_bytes(data)
    result = {"output": str(output), "seconds": score["totalBeats"], "scoreEvents": metadata["scoreEvents"],
              "sourceDispositionCounts": counts, **metadata["nativeTiming"]}
    print(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output", type=Path, required=True, help="Fresh output directory")
    args = parser.parse_args()
    prepare(args.plan, args.output)


if __name__ == "__main__":
    main()
