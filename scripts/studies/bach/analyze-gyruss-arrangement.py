#!/usr/bin/env python3
"""Compare observed Gyruss pitch runs with the accepted Bach preparation ledger.

Renderer snapshots support phrase and texture observations, not an exact note or
gate ledger. Pitch-class matches identify shared passages without claiming equal
voicing, duration, articulation, or complete source coverage.
"""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
ACCEPTED_PREPARATION_SHA256 = "1752ba4baec7053610030431ea5cc2f00ff732a94ecc7ee19f239e37f24caaa8"


def fingerprint(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def snapshot_runs(path, clock_hz):
    with path.open() as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    times = [int(row["time_ms"]) / 1000 for row in rows]
    if len(times) < 2 or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("Snapshots must have strictly increasing timestamps")
    voices = [[] for _ in range(3)]
    for row, time in zip(rows, times):
        registers = bytes.fromhex(row["registers_hex"])
        if len(registers) < 25:
            raise ValueError("A snapshot lacks the first SID's register bank")
        for voice, runs in enumerate(voices):
            offset = voice * 7
            word = registers[offset] | registers[offset + 1] << 8
            control = registers[offset + 4]
            if runs and (word, control) == (runs[-1]["frequencyWord"], runs[-1]["control"]):
                runs[-1]["snapshots"] += 1
                continue
            if runs:
                runs[-1]["endSeconds"] = time
            midi = None
            if word and control & 0x70 and not control & 0x88:
                midi = round(69 + 12 * math.log2(word * clock_hz / (2 ** 24 * 440)))
            runs.append(dict(voice=voice + 1, startSeconds=time, endSeconds=times[-1],
                             frequencyWord=word, control=control, snapshots=1, midi=midi,
                             note=None if midi is None else NOTE_NAMES[midi % 12] + str(midi // 12 - 1)))
    gaps = [round(b - a, 6) for a, b in zip(times, times[1:])]
    return voices, dict(count=len(rows), firstSeconds=times[0], lastSeconds=times[-1],
                        minimumGapSeconds=min(gaps), maximumGapSeconds=max(gaps))


def phrase_matches(notes, accepted, minimum_length):
    candidates = []
    for source_index, source in enumerate(notes):
        for accepted_index, target in enumerate(accepted):
            length = 0
            while (source_index + length < len(notes) and accepted_index + length < len(accepted)
                   and notes[source_index + length]["midi"] % 12
                   == accepted[accepted_index + length]["midi"] % 12):
                length += 1
            if length >= minimum_length:
                candidates.append((length, source_index, accepted_index))
    selected = []
    occupied = set()
    for length, source_index, accepted_index in sorted(candidates, key=lambda item: (-item[0], item[1], item[2])):
        indices = set(range(source_index, source_index + length))
        if indices & occupied:
            continue
        occupied.update(indices)
        observed = notes[source_index:source_index + length]
        arranged = accepted[accepted_index:accepted_index + length]
        selected.append(dict(
            voice=observed[0]["voice"], notes=length,
            referenceSeconds=[observed[0]["startSeconds"], observed[-1]["endSeconds"]],
            acceptedSeconds=[arranged[0]["startBeat"], arranged[-1]["startBeat"] + arranged[-1]["durationBeats"]],
            sourceBeats=[arranged[0]["sourceStartBeat"], arranged[-1]["sourceEndBeat"]],
            observedNotes=[event["note"] for event in observed],
            octaveDifferences=sorted(set(event["midi"] - arranged[index]["midi"] for index, event in enumerate(observed))),
            sourceIds=[event["sourceId"] for event in arranged]))
    return sorted(selected, key=lambda item: item["referenceSeconds"][0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshots", required=True, type=Path)
    parser.add_argument("--preparation", required=True, type=Path)
    parser.add_argument("--clock-hz", required=True, type=int)
    parser.add_argument("--minimum-snapshots", type=int, default=2)
    parser.add_argument("--minimum-phrase-notes", type=int, default=10)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.clock_hz <= 0 or args.minimum_snapshots < 1 or args.minimum_phrase_notes < 1:
        parser.error("Clock and observation thresholds must be positive")
    if fingerprint(args.preparation)["sha256"] != ACCEPTED_PREPARATION_SHA256:
        parser.error("This source-specific analysis requires the pinned accepted preparation; another ledger has no established beat-to-second contract")
    args.output.mkdir(parents=True, exist_ok=False)
    preparation = json.loads(args.preparation.read_text())
    accepted = [event for event in preparation["mapping"] if event["voice"] == "melody"]
    if not accepted or any(b["startBeat"] < a["startBeat"] for a, b in zip(accepted, accepted[1:])):
        raise ValueError("Accepted melody mapping must be nonempty and ordered")
    voices, cadence = snapshot_runs(args.snapshots, args.clock_hz)
    matches = []
    retained_counts = []
    for runs in voices:
        notes = [run for run in runs if run["midi"] is not None and run["snapshots"] >= args.minimum_snapshots]
        retained_counts.append(len(notes))
        matches.extend(phrase_matches(notes, accepted, args.minimum_phrase_notes))
    result = dict(
        schemaVersion=1,
        inputs=dict(snapshots=fingerprint(args.snapshots), preparation=fingerprint(args.preparation)),
        settings=dict(clockHz=args.clock_hz, referenceAHz=440, minimumSnapshots=args.minimum_snapshots,
                      minimumPhraseNotes=args.minimum_phrase_notes, acceptedQuarterBpm=60,
                      acceptedTimingBasis="prepare-toccata.py retains the accepted score's quarterBpm 60 from prepare-opening.py, so its pinned mapping beats encode seconds"),
        observation="Renderer iteration snapshots; runs group identical frequency/control observations, not score notes or bus writes",
        limitations="Times bracket observed states at the snapshot cadence. Mid-call partial frequency words, unobserved writes, effects and repeated same-pitch notes can affect runs. One-snapshot states are excluded by default. Matches compare pitch classes only; frequency effects may produce incidental nominal pitches. No hearing, exact gate, harmonic-equivalence or full-form claim follows.",
        cadence=cadence, retainedTonalRunsByVoice=retained_counts,
        pitchClassMatches=matches, acceptedSections=preparation["sections"])
    (args.output / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    with (args.output / "observed-runs.tsv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(voices[0][0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(run for runs in voices for run in runs)
    print(json.dumps(dict(output=str(args.output), cadence=cadence, retainedTonalRunsByVoice=retained_counts,
                          matches=[{key: value for key, value in match.items() if key not in ("observedNotes", "sourceIds")} for match in matches]), indent=2))


if __name__ == "__main__":
    main()
