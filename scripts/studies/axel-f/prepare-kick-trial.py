#!/usr/bin/env python3
"""Prepare and check the bounded source-backed Axel F percussion audition."""

import argparse
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from audio_comparison import Pcm16, measure_pcm, read_pcm16


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def rational(value):
    return Fraction(*value) if isinstance(value, list) else Fraction(str(value))


def prepare(common, score, palette, bank, config):
    require(config["format"] == "axel-f-kick-trial-v1", "Unsupported Axel F kick trial")
    require(common["provenance"]["sourceSha256"] == score["provenance"]["sourceSha256"] == config["sourceSha256"],
            "Both scores must originate in the pinned MIDI")
    require(common["quarterBpm"] == score["quarterBpm"], "Source and reduced tempos differ")
    require(fingerprint(palette) == config["basePaletteFingerprint"], "Accepted palette changed")
    require(fingerprint(score) == config["baseScoreFingerprint"], "Established full-score reduction changed")
    require((palette["sidCount"], palette["sidModel"], palette["clock"]) == (1, "MOS8580", "pal"),
            "The trial requires the accepted single-SID PAL MOS8580 target")
    kick = bank["instruments"]["kick-fall"]
    require(fingerprint(kick) == config["kickFingerprint"], "Original KICKFALL program changed")
    source_start, source_end = map(rational, config["sourceWindowBeats"])
    start, end = map(rational, config["arrangedWindowBeats"])
    require(source_start - start == source_end - end == 4, "The full tonal score trims exactly four source beats")
    require(source_end - source_start == end - start > 0 and start >= 0 and end <= rational(score["totalBeats"]),
            "Source and reduced windows must have the same supported length")
    require([voice["name"] for voice in score["voices"]] == ["melody", "harmony", "bass"],
            "The established hook voice order changed")
    baseline = deepcopy(score)
    baseline.pop("sections", None)
    baseline["totalBeats"] = float(end - start)
    baseline["provenance"] = {key: value for key, value in score["provenance"].items() if key != "reduction"}
    baseline["provenance"]["kickTrial"] = dict(baseScoreFingerprint=fingerprint(score), arrangedWindowBeats=config["arrangedWindowBeats"])
    for before, after in zip(score["voices"], baseline["voices"]):
        require(not any(rational(event["startBeat"]) < start < rational(event["startBeat"]) + rational(event["durationBeats"])
                        for event in before["events"]), "A source note crosses the excerpt entrance")
        after["events"] = []
        for event in before["events"]:
            onset, duration = map(rational, (event["startBeat"], event["durationBeats"]))
            if start <= onset < end:
                require(onset + duration <= end, "A tonal note crosses the excerpt ending")
                after["events"].append({**event, "startBeat": float(onset - start)})
    require(not baseline["voices"][1]["events"], "The percussion voice must be vacant throughout the hook")
    drums = next(part for part in common["parts"] if part["id"] == "drums")["events"]
    selected = [(index, event) for index, event in enumerate(drums)
                if event["midi"] == config["kickMidi"] and source_start <= rational(event["startBeat"]) < source_end]
    onsets = [rational(event["startBeat"]) for _, event in selected]
    require(len(onsets) == config["expectedKickOnsets"] and onsets == sorted(set(onsets)),
            "The selected source kick count or distinct onset order changed")
    seconds_per_beat = Fraction(60) / rational(common["quarterBpm"])
    duration_limit = rational(config["kickDurationSeconds"]) / seconds_per_beat
    candidate = deepcopy(baseline)
    retained = []
    for (index, event), onset, next_onset in zip(selected, onsets, onsets[1:] + [source_end]):
        duration = min(duration_limit, next_onset - onset)
        candidate["voices"][1]["events"].append(dict(startBeat=float(onset - source_start),
                                                   durationBeats=float(duration), midi=event["midi"]))
        retained.append(dict(sourceEventIndex=index, sourceStartBeat=event["startBeat"],
                             sourceDurationBeats=event["durationBeats"], outputDurationBeats=[duration.numerator, duration.denominator],
                             cappedByNextOnset=next_onset < source_end and duration < duration_limit))
    native = deepcopy(palette)
    native["title"] = "Axel F hook percussion trial"
    native["instruments"]["kick"] = deepcopy(kick)
    native["sections"] = [dict(name="Source hook with vacant accompaniment voice", startBeat=0,
                               endBeat=float(end - start), voices=dict(melody="lead", harmony="kick", bass="bass"))]
    reference, with_kick = deepcopy(native), deepcopy(native)
    reference["score"], with_kick["score"] = "baseline-score.json", "candidate-score.json"
    bass_onsets = {rational(event["startBeat"]) for event in baseline["voices"][2]["events"]}
    gaps = [(next_onset - onset) * seconds_per_beat for onset, next_onset in zip(onsets, onsets[1:] + [source_end])]
    report = dict(schemaVersion=1, sourceSha256=config["sourceSha256"], sourceWindowBeats=config["sourceWindowBeats"],
                  arrangedWindowBeats=config["arrangedWindowBeats"], basePaletteFingerprint=fingerprint(palette),
                  kickFingerprint=fingerprint(kick), sourceKickOnsets=len(selected),
                  tonalEventCounts=[len(voice["events"]) for voice in baseline["voices"]],
                  addedKickVoice=1, sourceKickMidi=config["kickMidi"], unchangedTonalVoices=[0, 2],
                  durationLimitSeconds=config["kickDurationSeconds"], durationCappedByNextOnsetCount=sum(row["cappedByNextOnset"] for row in retained),
                  minimumOnsetGapSeconds=float(min(gaps)),
                  kickOnsetsWithExactBassOnset=sum(onset - source_start in bass_onsets for onset in onsets),
                  sourceKickDurationsSeconds=sorted({float(rational(event["durationBeats"]) * seconds_per_beat) for _, event in selected}),
                  retainedKickOrigins=retained,
                  scope="Source kick onsets retained; percussion durations deliberately extended and capped. The added voice has its own envelope, not a new independent onset pattern or a reconstruction of the complete reference drums.")
    return {"baseline-score.json": baseline, "candidate-score.json": candidate, "reference.json": reference,
            "candidate.json": with_kick, "adaptation.json": report}


def verify(reference, candidate, kick_only, kick_muted):
    reference, candidate = Path(reference), Path(candidate)
    before, after = (read(directory / "native-song.frames.json") for directory in (reference, candidate))
    require(len(before) == len(after) and all(len(row) == 25 for row in before + after), "Frame banks differ")
    changed = {index for left, right in zip(before, after) for index, (a, b) in enumerate(zip(left, right)) if a != b}
    require(changed and changed <= set(range(7, 14)), "The kick changed lead, bass or shared SID controls")
    ledgers = [[row for row in read(directory / "native-song.writes.json") if not 0xd407 <= row["address"] <= 0xd40d]
               for directory in (reference, candidate)]
    identities = lambda rows: [(row["phase"], row["tick"], row["address"], row["value"]) for row in rows]
    require(identities(ledgers[0]) == identities(ledgers[1]), "The kick changed ordered non-kick SID store values")
    manifest = read(candidate / "conversion.json")
    notes = manifest["voices"][1]["notes"]
    require(len(notes) == 48, "The native candidate lost a kick onset")
    reports = []
    expected_words = (3337, 2227, 1668, 1113, 556)
    for index, note in enumerate(notes):
        start = note["startTick"]
        next_start = notes[index + 1]["startTick"] if index + 1 < len(notes) else manifest["scoreTicks"]
        require(after[start][11] == 9, "A kick lacks the declared native TEST onset")
        for offset, expected in enumerate(expected_words, 1):
            if start + offset < next_start:
                state = after[start + offset]
                require(state[11] & 0xf0 == 0x10 and abs(state[7] + 256 * state[8] - expected) <= 1,
                        "The exported kick does not retain the original triangle pitch-fall program")
        states = after[start + 1:min(next_start, start + 12)]
        first_gate_off = next((start + 1 + offset for offset, state in enumerate(states) if not state[11] & 1), None)
        low_gated = sum(state[11] & 1 and state[11] & 0xf0 == 0x10 and state[7] + 256 * state[8] in (556, 557) for state in states)
        reports.append(dict(startTick=start, nextOnsetTick=next_start, sourceDurationTicks=note["sourceDurationTicks"],
                            converterGateOffTick=note["gateOffTick"], firstObservedGateOffTick=first_gate_off,
                            lowBodyGatedCalls=low_gated, lowBodyGatedSeconds=low_gated / manifest["ticksPerSecond"]))
    require(all(state[23] & 15 == 4 for state in after[:manifest["stopTick"]])
            and all(state[23] == 0x44 and state[24] == 0x1f for state in after[1:manifest["stopTick"]]),
            "The bass must retain sole filter ownership and unchanged master volume")
    audio_a, audio_b = (read_pcm16(directory / "native-song.wav") for directory in (reference, candidate))
    require((audio_a.frames, audio_a.channels, audio_a.sample_rate) == (audio_b.frames, audio_b.channels, audio_b.sample_rate), "PCM layouts differ")
    difference = [b - a for a, b in zip(audio_a.samples, audio_b.samples)]
    require(any(difference), "The submitted pair has no kick signal contribution")
    stop = manifest["stopTick"] / manifest["ticksPerSecond"]
    first, last = (round((stop - offset) * audio_b.sample_rate) for offset in (0.5, 0.1))
    release = measure_pcm(Pcm16(audio_b.sample_rate, audio_b.channels, last - first, audio_b.samples[first:last], ""))
    require(release["acRms"] <= 16, "The candidate does not settle before master volume clear")
    diagnostic = read_pcm16(kick_only)
    diagnostic_metrics = measure_pcm(diagnostic)
    require(diagnostic_metrics["acRms"] > 1 and diagnostic_metrics["clippedSamples"] == 0,
            "The kick-only diagnostic must contain a healthy signal")
    muted = read_pcm16(kick_muted)
    require(muted.sample_rate == audio_a.sample_rate and muted.channels == audio_a.channels and muted.frames >= audio_a.frames,
            "The muted diagnostic must cover the complete comparison")
    muted_difference = [b - a for a, b in zip(audio_a.samples, muted.samples[:audio_a.frames])]
    direct_difference = [b - a for a, b in zip(muted.samples[:audio_b.frames], audio_b.samples)]
    require(Path(kick_muted + ".registers.tsv").read_bytes() == (candidate / "native-song.wav.registers.tsv").read_bytes(),
            "Same-SID muted and unmuted renderer snapshots differ")
    phrase_frames = round(manifest["scoreTicks"] / manifest["ticksPerSecond"] * audio_a.sample_rate)
    phrase_metrics = {label: measure_pcm(Pcm16(audio.sample_rate, audio.channels, phrase_frames,
                                              audio.samples[:phrase_frames], ""))
                      for label, audio in (("nativeWithoutKick", audio_a), ("candidate", audio_b), ("kickOnly", diagnostic), ("kickMuted", muted))}
    return dict(schemaVersion=1, frames=len(after), allowedChangedOffsets=list(range(7, 14)), changedOffsets=sorted(changed),
                unchangedLeadBassAndSharedControls=True, sharedFilterRoute=0x44, kickOnsets=len(notes),
                matchedOrderedNonKickStores=len(ledgers[0]),
                maximumNonKickInstructionStartDifferenceCycles=max(abs(a["instructionStartCycle"] - b["instructionStartCycle"])
                                                                   for a, b in zip(*ledgers)),
                gatedLowBodyCallCounts={str(count): sum(row["lowBodyGatedCalls"] == count for row in reports)
                                        for count in sorted({row["lowBodyGatedCalls"] for row in reports})},
                actualKickBodies=reports, nativeScorePairDifferenceRms=(sum(value * value for value in difference) / len(difference)) ** 0.5,
                differentPcmSamples=sum(value != 0 for value in difference), preStopReleaseAcRms=release["acRms"],
                pcm=dict(nativeWithoutKick=measure_pcm(audio_a), candidate=measure_pcm(audio_b), kickOnly=diagnostic_metrics, kickMuted=measure_pcm(muted)),
                phrasePcm=phrase_metrics,
                sameSidPairDifferenceRms=(sum(value * value for value in direct_difference) / len(direct_difference)) ** 0.5,
                sameSidPairDifferentSamples=sum(value != 0 for value in direct_difference),
                sameSidRendererSnapshotsIdentical=True,
                kickMutedVersusBaselineDifferenceRms=(sum(value * value for value in muted_difference) / len(muted_difference)) ** 0.5,
                diagnosticLimitation="Voice muting changes synthesis inputs; the solo is not an output stem or proof of audibility in the full mix.",
                scope="Complete native note schedule and post-call register checks; actual interrupted bodies are recorded, not assumed to complete. PCM contribution is not audibility, useful groove, musical acceptance or hardware equivalence.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    preparation = sub.add_parser("prepare")
    for name in ("common", "score", "palette", "bank", "config"):
        preparation.add_argument(name, type=Path)
    preparation.add_argument("--output", required=True, type=Path)
    checking = sub.add_parser("verify")
    checking.add_argument("reference", type=Path)
    checking.add_argument("candidate", type=Path)
    checking.add_argument("--kick-only", required=True, type=Path)
    checking.add_argument("--kick-muted", required=True, type=Path)
    checking.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    require(args.output.resolve().is_relative_to(ROOT / "build") and not args.output.exists(),
            "Choose fresh private output under build/")
    if args.command == "prepare":
        results = prepare(*(read(getattr(args, name)) for name in ("common", "score", "palette", "bank", "config")))
        args.output.mkdir(parents=True)
        for name, value in results.items():
            (args.output / name).write_text(json.dumps(value, indent=2) + "\n")
    else:
        result = verify(args.reference, args.candidate, args.kick_only, str(args.kick_muted))
        with args.output.open("x") as output:
            output.write(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
