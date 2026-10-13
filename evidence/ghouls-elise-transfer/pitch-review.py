#!/usr/bin/env python3
"""Review retained compiled transfer stores against the independent source score."""

import argparse
import gzip
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evidence/ghouls-elise-transfer"
CLOCK = Fraction(17734475, 18)
FRAME_CYCLES = 19656
FRAME_SECONDS = Fraction(FRAME_CYCLES, 1) / CLOCK
SID_BASE = 0xD400
INPUTS = {}


def read(path):
    path = Path(path)
    data = path.read_bytes()
    INPUTS[str(path.relative_to(ROOT))] = {
        "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)
    }
    return data


def load(path):
    return json.loads(read(path))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nearest_call(beat, bpm):
    calls = Fraction(str(beat)) * 60 / bpm / FRAME_SECONDS
    return (2 * calls.numerator + calls.denominator) // (2 * calls.denominator)


def note_name(midi):
    return ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][midi % 12] + str(midi // 12 - 1)


def pitch(word, expected_midi):
    hz = word * float(CLOCK) / 2**24
    midi = 69 + 12 * math.log2(hz / 440)
    return {
        "word": word, "hz": hz, "nearestMidi": math.floor(midi + 0.5),
        "signedCentsFromSource": 100 * (midi - expected_midi),
    }


def artifact(run, stage, suffix):
    matches = [row for row in run["artifacts"]
               if row["stageId"] == stage and row["relativePath"] == suffix]
    require(len(matches) == 1, "Ambiguous artifact: " + stage + "/" + suffix)
    return matches[0]


def local_build_path(historical):
    parts = Path(historical).parts
    require(parts.count("build") == 1, "Expected an original build artifact path")
    return ROOT.joinpath(*parts[parts.index("build"):])


def decode(writes, calls):
    registers = [0] * 29
    frequencies = []
    controls = []
    snapshots = []
    play = {}
    for position, row in enumerate(writes):
        offset = row["address"] - SID_BASE
        require(0 <= offset < len(registers), "Non-SID ledger store")
        if row["phase"] == "init":
            registers[offset] = row["value"]
        else:
            play.setdefault(row["tick"], []).append((position, row))
    for call in range(calls):
        for position, row in play.get(call, []):
            offset = row["address"] - SID_BASE
            registers[offset] = row["value"]
            if offset < 21 and offset % 7 == 1:
                previous = writes[position - 1]
                require(previous["tick"] == call and previous["address"] == row["address"] - 1,
                        "Frequency word is not an ordered low/high pair")
                frequencies.append({
                    "voice": offset // 7, "call": call,
                    "word": registers[offset - 1] + 256 * registers[offset],
                    "instructionStartCycle": row["instructionStartCycle"],
                })
            if offset < 21 and offset % 7 == 4:
                controls.append({
                    "voice": offset // 7, "call": call, "value": row["value"],
                    "instructionStartCycle": row["instructionStartCycle"],
                })
        snapshots.append([
            {"word": registers[v * 7] + 256 * registers[v * 7 + 1],
             "control": registers[v * 7 + 4], "ad": registers[v * 7 + 5],
             "sr": registers[v * 7 + 6]}
            for v in range(3)
        ])
    return {"frequencies": frequencies, "controls": controls, "snapshots": snapshots}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/ghouls-transfer-pitch-review/check",
                        help="Fresh output directory under build/; defaults to build/ghouls-transfer-pitch-review/check")
    args = parser.parse_args()
    output = args.output.resolve()
    require(output != ROOT / "build" and ROOT / "build" in output.parents,
            "Output must be a fresh directory under build/")
    require(not output.exists(), "Output already exists: " + str(output))
    source = load(ROOT / "songs/fuer-elise.json")
    run = load(EVIDENCE / "run.json")
    audio = load(EVIDENCE / "audio.json")
    publication = load(EVIDENCE / "listening-review.json")["publication"]
    require(run["status"] == "completed" and audio["passed"], "Incomplete listening package")
    require(publication["run"]["sha256"] == INPUTS["evidence/ghouls-elise-transfer/run.json"]["sha256"],
            "Published package has a different run")
    for item in publication["files"]:
        data = read(ROOT / "build/ghouls-elise-listening" / item["filename"])
        require(hashlib.sha256(data).hexdigest() == item["sha256"], "Submitted WAV changed")
        pin = next(row for row in run["artifacts"] if row["path"] == item["sourcePath"])
        require(pin["sha256"] == item["sha256"], "Submitted WAV differs from the completed run")

    decoded = {}
    descriptions = {}
    audio_pins = {}
    for role, filename, deliverable in [
        ("candidate", "ghouls-elise-transfer.json", "fullCandidate"),
        ("reference", "ghouls-elise-reference.json", "fullReference"),
    ]:
        description = load(ROOT / "songs" / filename)
        descriptions[role] = description
        proof = load(EVIDENCE / role / "verification.json")
        require(proof["descriptionSha256"] == INPUTS["songs/" + filename]["sha256"], "Description changed")
        require(description["sourceEvidence"]["sourceSha256"] == INPUTS["songs/fuer-elise.json"]["sha256"], "Source changed")
        require(description["profile"] == {"clock": "PAL", "sidModel": "MOS6581", "sidCount": 1,
                                            "sidBase": SID_BASE, "frameCycles": FRAME_CYCLES}, "Unexpected profile")
        raw = gzip.decompress(read(EVIDENCE / role / "writes.json.gz"))
        raw_sha = hashlib.sha256(raw).hexdigest()
        write_pin = artifact(run, role + "-build", "candidate/writes.json")
        require(raw_sha == write_pin["sha256"], "Retained ledger differs from compiled run")
        sid_pin = artifact(run, role + "-build", "candidate/reconstructed.sid")
        require(proof["sidSha256"] == sid_pin["sha256"], "Compiled source pin differs")
        require(hashlib.sha256(read(local_build_path(sid_pin["path"]))).hexdigest() == sid_pin["sha256"], "Compiled SID changed")
        verification_pin = artifact(run, role + "-build", "candidate/verification.json")
        require(INPUTS["evidence/ghouls-elise-transfer/" + role + "/verification.json"]["sha256"] == verification_pin["sha256"],
                "Retained verification differs from compiled run")
        wav = next(item for item in audio["inputs"] if item["label"] == role)
        published = next(item for item in publication["files"] if item["label"] == deliverable)
        require(wav["sha256"] == published["sha256"] and wav["path"] == published["sourcePath"], "Audio pin differs")
        audio_pins[role] = {"compiledSidSha256": sid_pin["sha256"], "ledgerRawSha256": raw_sha,
                            "submittedWavSha256": wav["sha256"], "filename": published["filename"]}
        decoded[role] = decode(json.loads(raw), proof["checkedPlayCalls"])

    notes = []
    intervals = []
    timing_errors = []
    attack_rows = []
    covered_pairs = {role: set() for role in decoded}
    covered_ons = {role: set() for role in decoded}
    counts = {}
    for voice, part in enumerate(source["voices"]):
        events = [event for event in part["events"] if 0 <= event["startBeat"] < 12]
        counts[part["name"]] = len(events)
        previous = None
        for index, event in enumerate(events):
            start = nearest_call(event["startBeat"], source["quarterBpm"])
            end = nearest_call(Fraction(str(event["startBeat"])) + Fraction(str(event["durationBeats"])), source["quarterBpm"])
            end_beat = event["startBeat"] + event["durationBeats"]
            timing_errors.extend([float(start * FRAME_SECONDS - Fraction(str(event["startBeat"])) * 60 / source["quarterBpm"]),
                                  float(end * FRAME_SECONDS - Fraction(str(end_beat)) * 60 / source["quarterBpm"])])
            row = {"role": part["name"], "index": index, "sourceMidi": event["midi"],
                   "sourceNote": note_name(event["midi"]), "startBeat": event["startBeat"],
                   "durationBeats": event["durationBeats"], "scheduledStartCall": start,
                   "scheduledEndCall": end, "quantizedDurationCalls": end - start}
            for role, data in decoded.items():
                pairs = [pair for pair in data["frequencies"] if pair["voice"] == voice and start <= pair["call"] < end]
                controls = [control for control in data["controls"] if control["voice"] == voice and start <= control["call"] < end]
                require(pairs and pairs[0]["call"] == start, "Missing or mistimed note: " + str(row))
                off = [control for control in data["controls"]
                       if control["voice"] == voice and control["call"] == end and not control["value"] & 1]
                require(off, "Missing source end gate-off: " + str(row))
                states = data["snapshots"][start:end]
                tonal_calls = [start + i for i, snapshot in enumerate(states)
                               if snapshot[voice]["control"] & 1 and snapshot[voice]["control"] & 0x70]
                require(tonal_calls, "No tonal note body")
                tonal_start = tonal_calls[0]
                require(tonal_calls == list(range(tonal_start, end)), "Interrupted note body")
                body_word = data["snapshots"][tonal_start][voice]["word"]
                measured = pitch(body_word, event["midi"])
                require(measured["nearestMidi"] == event["midi"], "Wrong compiled pitch: " + str(row) + str(measured))
                require(all(data["snapshots"][call][voice]["word"] == body_word for call in tonal_calls), "Pitch changes inside body")
                require(all(control["value"] & 1 for control in controls if control["call"] > start), "Premature gate-off")
                require(all(not data["snapshots"][call][voice]["control"] & 0x0e for call in range(start, end)), "Ring/sync/TEST found")
                on = next(control for control in controls if control["value"] & 1)
                require(on["call"] == start, "Mistimed gate-on")
                noise_calls = [call for call in range(start, end) if data["snapshots"][call][voice]["control"] & 0x80]
                expected_noise = [start] if role == "candidate" and part["name"] == "bass" else []
                require(noise_calls == expected_noise, "Unexpected attack-only frequency change")
                require(len(pairs) == (3 if expected_noise else 1), "Unexpected frequency store")
                require(pairs[0]["word"] == body_word and pairs[-1]["word"] == body_word, "Attack loses source body pitch")
                if expected_noise:
                    require(pairs[1]["call"] == start and pairs[2]["call"] == start + 1, "Wrong onset restore timing")
                    attack_rows.append({"role": part["name"], "index": index, "startCall": start,
                                        "bodyCall": tonal_start, "tonalWord": body_word,
                                        "noiseWord": pairs[1]["word"], "noiseControl": on["value"],
                                        "nominalBodyDelaySeconds": float(FRAME_SECONDS)})
                for pair in pairs:
                    covered_pairs[role].add((pair["voice"], pair["call"], pair["instructionStartCycle"]))
                for control in controls:
                    if control["value"] & 1:
                        covered_ons[role].add((control["voice"], control["call"], control["instructionStartCycle"]))
                node = descriptions[role]["program"]["nodes"][part["name"] + "-note-" + str(index)]["variants"]["stream"]
                require(node["duration"] == end - start, "Graph duration differs from source boundary")
                row[role] = {**measured, "rawGraphNote": node["rawNote"], "tonalStartCall": tonal_start,
                             "onsetControl": on, "endGateOff": off[0],
                             "frequencyPairs": pairs, "bodyAd": data["snapshots"][tonal_start][voice]["ad"],
                             "bodySr": data["snapshots"][tonal_start][voice]["sr"]}
            require(row["candidate"]["word"] == row["reference"]["word"], "Reference/candidate body pitches differ")
            notes.append(row)
            if previous:
                expected = event["midi"] - previous["sourceMidi"]
                measured_cents = 1200 * math.log2(row["candidate"]["word"] / previous["candidate"]["word"])
                intervals.append({"role": part["name"], "fromIndex": index - 1, "toIndex": index,
                                  "sourceSemitones": expected, "measuredCents": measured_cents,
                                  "centsError": measured_cents - expected * 100,
                                  "nearestSemitones": math.floor(measured_cents / 100 + 0.5)})
                require(intervals[-1]["nearestSemitones"] == expected, "Incorrect melodic interval")
            previous = row
    for role, data in decoded.items():
        require(len(covered_pairs[role]) == len(data["frequencies"]), "Extra frequency store outside source notes")
        ons = [row for row in data["controls"] if row["value"] & 1]
        require(len(covered_ons[role]) == len(ons), "Extra gate-on outside source notes")
        for voice, part in enumerate(source["voices"]):
            part_rows = [row for row in notes if row["role"] == part["name"]]
            for current, following in zip(part_rows, part_rows[1:] + [None]):
                end = current["scheduledEndCall"]
                next_start = following["scheduledStartCall"] if following else len(data["snapshots"])
                require(all(not data["snapshots"][call][voice]["control"] & 1 for call in range(end, next_start)),
                        "Unexpected gate-on in source rest")

    cents = [row["candidate"]["signedCentsFromSource"] for row in notes]
    onset_cycle_deltas = [row["candidate"]["onsetControl"]["instructionStartCycle"] -
                         row["reference"]["onsetControl"]["instructionStartCycle"] for row in notes]
    summary = {
        "sourceNoteCount": len(notes), "byRole": counts, "pitchMismatches": 0,
        "scheduledOnsetMismatches": 0, "scheduledGateOffMismatches": 0,
        "bodyPitchChanges": 0, "unassignedFrequencyPairs": 0, "unexpectedGateOnsInGaps": 0,
        "frequencyPairs": {role: len(data["frequencies"]) for role, data in decoded.items()},
        "intentionalBassNoiseAttacks": len(attack_rows),
        "nativeSignedCentsFromA440": {"minimum": min(cents), "maximum": max(cents)},
        "maximumAbsoluteIntervalCentsError": max(abs(row["centsError"]) for row in intervals),
        "maximumAbsoluteBoundaryQuantizationErrorSeconds": max(abs(value) for value in timing_errors),
        "candidateMinusReferenceGateOnStoreOffsetSeconds": {
            "minimum": min(onset_cycle_deltas) / float(CLOCK),
            "maximum": max(onset_cycle_deltas) / float(CLOCK)},
        "melodySourceNotes": [row["sourceNote"] for row in notes if row["role"] == "melody"],
    }
    report = {
        "schemaVersion": 1, "check": "compiled-transfer-pitch-against-source-score", "passed": True,
        "scope": "Submitted compiled candidate and generated plain reference, source beats [0,12); no new capture/render or listening judgment.",
        "method": {"palClockHz": {"numerator": CLOCK.numerator, "denominator": CLOCK.denominator},
                   "frameCycles": FRAME_CYCLES, "frequencyFormula": "Hz = observed complete SID frequency word * PAL clock / 2^24",
                   "pitchIdentity": "Nearest equal-tempered MIDI with A4=440Hz; signed cents are retained separately.",
                   "timingFormula": "Source absolute beat boundary * 60 / quarterBpm, quantized to nearest PAL call with exact rational arithmetic.",
                   "independence": "Does not import the transfer preparer, MIDI-to-native-note mapping, player or frequency lookup; decodes complete ordered compiled SID writes directly.",
                   "stableBody": "Every gated tonal end-of-call state from first tonal call to source note end has one frequency word; low/high intermediate bus words are not treated as notes.",
                   "timingLimit": "Calls verify schedule. instructionStartCycle reports offsets within each call, not measured perceived acoustic onset."},
        "summary": summary, "audioPins": audio_pins, "notes": notes, "successiveIntervals": intervals,
        "attackOnlyChanges": attack_rows,
        "interpretation": {
            "proven": "All 53 stable tonal notes, source gate-on calls, gate-off calls and gaps match. Candidate and plain reference have identical body words and relative intervals. No compiled note mapping or timing defect was found.",
            "sharedTuning": "Both versions retain the same native table, approximately 35 cents sharp of A440 equal temperament. This could differ from another remembered/reference rendition, but cannot by itself explain a candidate-versus-plain pitch difference.",
            "plausibleOnly": "Candidate pulse timbre/PWM, six brief bass noise onsets and native release nibble 15 before earlier gaps can alter clarity or perceived pitch. A SID voice retains the current oscillator word after gate-off; its release carries through the gap until retrigger, rather than mixing independent old and new pitches on that voice. These are possible perceptual influences, not an established cause of the user's uncertainty.",
            "finalRelease": "The submitted final release is shortened from nibble 15 to 9 at each voice's final note end; the retained audio check reports zero final-window AC RMS.",
            "notEstablished": "This check does not judge transcription fidelity to an external score/performance or determine why the listener perceived a slightly wrong tune. It compares the submitted files with the existing songs/fuer-elise.json source only."},
        "inputs": INPUTS,
        "tool": {"path": str(Path(__file__).relative_to(ROOT)), "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
    }
    for path, pin in INPUTS.items():
        require(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == pin["sha256"], "Input changed during review: " + path)
    output.mkdir(parents=True, exist_ok=False)
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
