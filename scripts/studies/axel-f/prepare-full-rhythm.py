#!/usr/bin/env python3
"""Project accepted Axel F maracas into entirely vacant harmony sections."""

import argparse
from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("axel_rhythm_trial", Path(__file__).with_name("prepare-rhythm-trial.py"))
TRIAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRIAL)
ROOT, fingerprint, rational, read, require = TRIAL.ROOT, TRIAL.fingerprint, TRIAL.rational, TRIAL.read, TRIAL.require
from audio_comparison import measure_pcm, read_pcm16
SPEC = importlib.util.spec_from_file_location("axel_rhythm_balance", Path(__file__).with_name("prepare-rhythm-balance.py"))
BALANCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BALANCE)


def prepare(common, score, palette, original, balance, config):
    require(config["format"] == "axel-f-full-rhythm-v1", "Unsupported full rhythm projection")
    require(common["provenance"]["sourceSha256"] == score["provenance"]["sourceSha256"] == config["sourceSha256"], "Pinned source changed")
    require(common["quarterBpm"] == score["quarterBpm"], "Source and reduced tempos differ")
    for value, key in ((common, "commonScoreFingerprint"), (score, "baseScoreFingerprint"), (palette, "basePaletteFingerprint"),
                       (original, "originalRhythmFingerprint"), (balance, "acceptedBalanceFingerprint")):
        require(fingerprint(value) == config[key], "Pinned full score, palette or accepted rhythm configuration changed")
    require((palette["sidCount"], palette["sidModel"], palette["clock"]) == (1, "MOS8580", "pal"), "Expected one PAL MOS8580")
    require(balance["adsr"] == "1300" and balance["previousConfigurationFingerprint"] == fingerprint(original), "Use the accepted AD13 balance")
    require([v["name"] for v in score["voices"]] == ["melody", "harmony", "bass"]
            and [len(v["events"]) for v in score["voices"]] == config["expectedTonalCounts"], "Established tonal voices changed")
    instrument = deepcopy(original["instrument"])
    require(instrument["adsr"] == "1400" and instrument["control"] == "0a" and instrument["frame1"] == "09"
            and instrument["hard_restart_adsr"] == "0f00" and instrument["wave"] == [["81", "c9", "00"]]
            and not instrument["pulse"] and not instrument["filter"]
            and not instrument.get("vibrato", 0) and not instrument.get("vibrato_delay", 0), "Original uncoupled fixed-noise program changed")
    instrument["adsr"] = balance["adsr"]
    require("rhythm" not in palette["instruments"] and config["sourceBeatOffset"] == 4, "Preserve existing IDs and the four-beat source trim")
    drums = next(part["events"] for part in common["parts"] if part["id"] == "drums")
    harmony = score["voices"][1]["events"]
    origins, window_reports = [], []
    native, candidate = deepcopy(palette), deepcopy(score)
    native["instruments"]["rhythm"] = instrument
    previous_end = rational(0)
    for window in config["windows"]:
        start, end = map(rational, (window["startBeat"], window["endBeat"]))
        require(previous_end <= start < end <= rational(score["totalBeats"]), "Rhythm windows must be ordered, disjoint and inside the form")
        previous_end = end
        require(not any(rational(e["startBeat"]) < end and start < rational(e["startBeat"]) + rational(e["durationBeats"])
                        for e in harmony), "Each selected harmony section must be entirely vacant")
        matches = [s for s in native["sections"] if rational(s["startBeat"]) == start and rational(s["endBeat"]) == end]
        require(len(matches) == 1, "Use an exact existing section without splitting tonal roles")
        matches[0]["voices"]["harmony"] = "rhythm"
        selected = [(index, e) for index, e in enumerate(drums) if e["midi"] == config["sourceMidi"]
                    and start <= rational(e["startBeat"]) - 4 < end]
        require(len(selected) == window["expectedOnsets"], "Section source onset count changed")
        for index, event in selected:
            onset, duration = rational(event["startBeat"]) - 4, rational(event["durationBeats"])
            require(duration > 0 and onset + duration <= end, "A source rhythm duration crosses its selected section")
            origins.append(dict(sourceEventIndex=index, sourceStartBeat=event["startBeat"], sourceDurationBeats=event["durationBeats"],
                                arrangedStartBeat=float(onset), durationBeats=float(duration), midi=event["midi"]))
        window_reports.append(dict(startBeat=float(start), endBeat=float(end), onsets=len(selected)))
    require(len(origins) == config["expectedRhythmOnsets"], "Complete rhythm count changed")
    onsets = [rational(e["sourceStartBeat"]) - 4 for e in origins]
    require(onsets == sorted(set(onsets)), "Source rhythm attacks must be distinct and ordered")
    require(all(onset + rational(e["sourceDurationBeats"]) <= following
                for e, onset, following in zip(origins, onsets, onsets[1:] + [rational(score["totalBeats"])])), "Source rhythm durations overlap")
    rhythm_events = [dict(startBeat=e["arrangedStartBeat"], durationBeats=e["durationBeats"], midi=e["midi"]) for e in origins]
    candidate["voices"][1]["events"] = sorted(deepcopy(harmony) + rhythm_events, key=lambda e: e["startBeat"])
    reference = deepcopy(palette)
    reference["score"], native["score"] = "baseline-score.json", "candidate-score.json"
    report = dict(schemaVersion=1, configurationFingerprint=fingerprint(config), sourceSha256=config["sourceSha256"],
                  quarterBpm=score["quarterBpm"],
                  baselineScoreFingerprint=fingerprint(score), baselinePaletteFingerprint=fingerprint(palette),
                  rhythmInstrumentFingerprint=fingerprint(instrument), retainedSourceOrigins=origins, windows=window_reports,
                  preservedTonalCounts=config["expectedTonalCounts"], candidateCounts=[len(v["events"]) for v in candidate["voices"]],
                  sourceDurationAdaptation=False, scope="Exact source GM70 projection only into entirely vacant sections; tonal score, form and existing programs retained.")
    return {"baseline-score.json": deepcopy(score), "candidate-score.json": candidate, "reference.json": reference,
            "candidate.json": native, "adaptation.json": report}


def verify_tonal_schedules(previous, candidate):
    ignored = {"eventIndex", "pattern", "row", "byteOffset"}
    clean = lambda note: {key: value for key, value in note.items() if key not in ignored}
    before = [[clean(n) for n in voice["notes"]] for voice in previous]
    after = [[clean(n) for n in voice["notes"] if n["instrumentId"] != "rhythm"] for voice in candidate]
    require(before == after, "A tonal pitch, source/native gate schedule or instrument identity changed")


def verify_rhythm_schedule(note, origin, ticks_per_beat, source_midi):
    onset, duration = rational(origin["sourceStartBeat"]) - 4, rational(origin["sourceDurationBeats"])
    require(float(onset) == origin["arrangedStartBeat"] and float(duration) == origin["durationBeats"]
            and note["midi"] == origin["midi"] == source_midi, "Private source mapping or rhythm MIDI identity changed")
    require((note["startBeat"], note["durationBeats"]) == (float(onset), float(duration)), "Native rhythm changed a source onset or duration")
    start, end = (math.floor(float(beat) * ticks_per_beat + 0.5) for beat in (onset, onset + duration))
    require(end - start >= 3 and note["startTick"] == note["sourceStartTick"] == start
            and note["durationTicks"] == note["sourceDurationTicks"] == end - start
            and note["sourceGateOffTick"] == end - 1, "Native rhythm boundaries differ from the retained source grid")


def verify_frames(previous, candidate, intervals, incoming_tests=()):
    require(len(previous) == len(candidate) and all(len(row) == 25 for row in previous + candidate), "Complete frame banks differ")
    for tick in incoming_tests:
        require(0 < tick < len(previous) - 1 and previous[tick][11] == candidate[tick][11] == 9
                and previous[tick][8:14] == candidate[tick][8:14]
                and previous[tick][7] == previous[tick - 1][7] and candidate[tick][7] == candidate[tick - 1][7],
                "Incoming tonal TEST may retain only its preceding inactive frequency low byte")
        require(previous[tick + 1][7:14] == candidate[tick + 1][7:14]
                and previous[tick + 1][11] & 0xf0 and not previous[tick + 1][11] & 8,
                "Incoming tonal body must restore all seven voice registers on the next call")
    changed = set()
    for tick, (left, right) in enumerate(zip(previous, candidate)):
        active = any(start <= tick < end for start, end in intervals)
        for offset, (a, b) in enumerate(zip(left, right)):
            if a != b:
                require((active and 7 <= offset < 14) or (tick in incoming_tests and offset == 7),
                        "A tonal trajectory, predecessor release or shared control changed")
                changed.add(offset)
    require(changed, "The full candidate contains no rhythm intervention")
    return sorted(changed)


def verify_diagnostic_snapshots(full_snapshots, diagnostic_snapshots):
    require(full_snapshots and full_snapshots == diagnostic_snapshots, "Harmony diagnostic does not match its own full-render register snapshots")


def verify_ordered_writes(previous, candidate, intervals, incoming_test_lows=None):
    incoming_test_lows = incoming_test_lows or {}
    def preserved(row):
        tick = row["tick"]
        return not (0xd407 <= row["address"] <= 0xd40d and isinstance(tick, int)
                    and any(start <= tick < end for start, end in intervals))
    ledgers = [[row for row in rows if preserved(row)] for rows in (previous, candidate)]
    locations = lambda rows: [(r["phase"], r["tick"], r["address"]) for r in rows]
    require(locations(ledgers[0]) == locations(ledgers[1]), "Ordered tonal or shared SID store locations changed outside noise history")
    for left, right in zip(*ledgers):
        require(left["value"] == right["value"] or (left["phase"] == "play" and left["address"] == 0xd407
                and (left["value"], right["value"]) == incoming_test_lows.get(left["tick"])),
                "Ordered tonal or shared SID stores changed outside noise history")
    return len(ledgers[0]), max(abs(a["instructionStartCycle"] - b["instructionStartCycle"]) for a, b in zip(*ledgers))


def verify_noise_states(states, start_tick, gate_off_tick, frequency_word):
    require(isinstance(gate_off_tick, int) and gate_off_tick > start_tick + 1 and states,
            "Every source attack needs a nonempty noise gate schedule")
    require(all(state[11] == (0x81 if tick < gate_off_tick else 0x80) and state[12:14] == [0x13, 0]
                and abs(state[7] + 256 * state[8] - frequency_word) <= 1
                for tick, state in enumerate(states, start_tick + 1)), "Accepted noise gate schedule, envelope or clock changed")
    return sum(state[11] == 0x81 for state in states)


def measure_handover(audio, end_seconds):
    measurements = []
    for label, offsets, quiet in (("earlier-preserved-release", (0.15, 0.03), False),
                                  ("immediate-handover", (0.06, 0.005), True),
                                  ("final-handover", (0.025, 0.001), True)):
        first, last = (round((end_seconds - offset) * audio.sample_rate) for offset in offsets)
        require(0 <= first < last <= audio.frames, "Boundary release window is invalid")
        metrics = measure_pcm(BALANCE.portion(audio, first, last))
        require(not quiet or (metrics["acRms"] <= 16 and metrics["clippedSamples"] == 0), "Harmony residue is not quiet at handover")
        measurements.append(dict(label=label, requiredQuiet=quiet, requestedOffsetsSeconds=[-v for v in offsets],
                                 startFrame=first, endFrame=last, metrics=metrics))
    return measurements


def verify_rendered_hits(hits, expected_zero_ticks):
    zero_ticks = {hit["startTick"] for hit in hits if hit["acRms"] <= 1}
    require(zero_ticks == set(expected_zero_ticks), "Rendered rhythm zero-window identities changed")
    return len(hits) - len(zero_ticks), sorted(zero_ticks)


def verify(previous, candidate, adaptation, config, baseline_harmony_wav, candidate_harmony_wav):
    previous, candidate = Path(previous), Path(candidate)
    require(adaptation["configurationFingerprint"] == fingerprint(config), "Private provenance configuration changed")
    manifests = [read(path / "conversion.json") for path in (previous, candidate)]
    before, after = manifests
    require(all(before[key] == after[key] for key in ("stopTick", "stopVolumeClearTick", "clock", "clockHz", "sidModel", "sidCount", "scoreTicks", "totalTicks", "ticksPerSecond")), "Native target or form changed")
    verify_tonal_schedules(before["voices"], after["voices"])
    require(before["instruments"] == after["instruments"][:-1] and after["instruments"][-1]["id"] == "rhythm", "Existing native instrument IDs shifted")
    notes = after["voices"][1]["notes"]
    rhythm = [n for n in notes if n["instrumentId"] == "rhythm"]
    origins = adaptation["retainedSourceOrigins"]
    require(len(rhythm) == len(origins) == config["expectedRhythmOnsets"], "Native rhythm onset count changed")
    require([len(v["notes"]) for v in before["voices"]] == config["expectedTonalCounts"], "Baseline tonal count changed")
    frames = [read(path / "native-song.frames.json") for path in (previous, candidate)]
    expected_word = round(440 * 2 ** ((84 - 69) / 12) * 2 ** 24 / after["clockHz"])
    ticks_per_beat = after["ticksPerSecond"] * 60 / adaptation["quarterBpm"]
    bodies = []
    for note, origin in zip(rhythm, origins):
        verify_rhythm_schedule(note, origin, ticks_per_beat, config["sourceMidi"])
        start = note["startTick"]
        following = next((n["startTick"] for n in notes if n["startTick"] > start), after["scoreTicks"])
        require(frames[1][start][11] == 9 and note["durationTicks"] == note["sourceDurationTicks"], "Native TEST onset or retained duration lost")
        states = frames[1][start + 1:following]
        body_calls = verify_noise_states(states, start, note["nativeGateOffTick"], expected_word)
        off = next((start + 1 + i for i, s in enumerate(states) if s[11] == 0x80), None)
        require(off == note["nativeGateOffTick"] == note["sourceGateOffTick"], "Native noise gate differs from source timing")
        bodies.append(dict(startTick=start, gateOffTick=off, nextOnsetTick=following, gatedNoiseBodyCalls=body_calls))
    intervals, boundaries = [], []
    tonal = before["voices"][1]["notes"]
    for first_beat, last_beat in ((32, 96), (128, 172)):
        selected = [(n, b) for n, b in zip(rhythm, bodies) if first_beat <= n["startBeat"] < last_beat]
        require(selected, "A required full rhythm block is missing")
        first, last = selected[0][0], selected[-1][0]
        incoming = next(n for n in tonal if n["startTick"] > last["startTick"])
        predecessor = next((n for n in reversed(tonal) if n["startTick"] < first["startTick"]), None)
        intervals.append((first["startTick"], incoming["startTick"]))
        boundaries.append(dict(firstNoiseTick=first["startTick"], predecessorGateOffTick=predecessor["nativeGateOffTick"] if predecessor else None,
                               lastNoiseTick=last["startTick"], lastNoiseGateOffTick=last["nativeGateOffTick"],
                               incomingTonalTestTick=incoming["startTick"], incomingTonalBodyTick=incoming["startTick"] + 1))
    incoming_tests = [b["incomingTonalTestTick"] for b in boundaries]
    changed = verify_frames(*frames, intervals, incoming_tests)
    incoming_test_lows = {tick: (frames[0][tick][7], frames[1][tick][7]) for tick in incoming_tests}
    for boundary in boundaries:
        tick = boundary["incomingTonalTestTick"]
        boundary["incomingTestLowBytes"] = list(incoming_test_lows[tick])
        boundary["incomingTonalBodyRegistersEqual"] = True
    ledgers = [read(path / "native-song.writes.json") for path in (previous, candidate)]
    preserved_stores, maximum_cycle_shift = verify_ordered_writes(*ledgers, intervals, incoming_test_lows)
    non_rhythm_stores = sum(not 0xd407 <= row["address"] <= 0xd40d for row in ledgers[0])
    diagnostics = [read_pcm16(path) for path in (baseline_harmony_wav, candidate_harmony_wav)]
    full = [read_pcm16(path / "native-song.wav") for path in (previous, candidate)]
    require(len({(a.frames, a.channels, a.sample_rate) for a in diagnostics + full}) == 1, "Full and harmony-only PCM layouts differ")
    for directory, diagnostic in zip((previous, candidate), (baseline_harmony_wav, candidate_harmony_wav)):
        verify_diagnostic_snapshots((directory / "native-song.wav.registers.tsv").read_bytes(), Path(str(diagnostic) + ".registers.tsv").read_bytes())
    for boundary in boundaries:
        boundary["quietWindows"] = []
        boundary["preservedReleaseWindows"] = []
        boundary["releaseBins"] = []
        for key in ("firstNoiseTick", "incomingTonalTestTick"):
            end = boundary[key] / after["ticksPerSecond"]
            measurements = [measure_handover(a, end) for a in diagnostics]
            for baseline, candidate_measurement in zip(*measurements):
                target = "quietWindows" if baseline["requiredQuiet"] else "preservedReleaseWindows"
                boundary[target].append(dict(before=key, label=baseline["label"], requestedOffsetsSeconds=baseline["requestedOffsetsSeconds"],
                                             startFrame=baseline["startFrame"], endFrame=baseline["endFrame"],
                                             baseline=baseline["metrics"], candidate=candidate_measurement["metrics"]))
            for start_ms in range(-160, 41, 20):
                offsets = [start_ms / 1000, (start_ms + 20) / 1000]
                first, last = (round((end + offset) * diagnostics[0].sample_rate) for offset in offsets)
                require(0 <= first < last <= diagnostics[0].frames, "Release diagnostic bin exceeds the rendered audio")
                metrics = [measure_pcm(BALANCE.portion(a, first, last)) for a in diagnostics]
                boundary["releaseBins"].append(dict(before=key, requestedOffsetsSeconds=offsets, startFrame=first, endFrame=last,
                                                    baseline=metrics[0], candidate=metrics[1]))
    rendered_hits = []
    for note, body in zip(rhythm, bodies):
        first = round(note["startTick"] / after["ticksPerSecond"] * diagnostics[1].sample_rate)
        last = round(min(body["nextOnsetTick"], note["startTick"] + 10) / after["ticksPerSecond"] * diagnostics[1].sample_rate)
        metrics = measure_pcm(BALANCE.portion(diagnostics[1], first, last))
        require(metrics["clippedSamples"] == 0, "A source maracas diagnostic window clips")
        rendered_hits.append(dict(startTick=note["startTick"], arrangedStartBeat=note["startBeat"],
                                  windowStartFrame=first, windowEndFrame=last, acRms=metrics["acRms"]))
    nonzero_hits, zero_ticks = verify_rendered_hits(rendered_hits, {4246})
    stop = after["stopTick"] / after["ticksPerSecond"]
    first, last = (round((stop - offset) * full[1].sample_rate) for offset in (0.5, 0.1))
    release = measure_pcm(BALANCE.portion(full[1], first, last))
    require(release["acRms"] <= 16 and all(measure_pcm(a)["clippedSamples"] == 0 for a in full), "Full PCM clips or fails to settle before volume clear")
    return dict(schemaVersion=1, cpuCalls=len(frames[1]), preservedTonalCounts=config["expectedTonalCounts"],
                candidateCounts=[len(v["notes"]) for v in after["voices"]], sourceRhythmOnsets=len(rhythm), renderedNonzeroNoiseAttacks=nonzero_hits,
                knownZeroDiagnosticWindowTicks=zero_ticks, knownZeroDiagnosticWindowCount=len(zero_ticks),
                perHitMeasurementScope="Scheduled onset to the next onset or ten native calls, whichever comes first. Nonzero/zero PCM-window evidence is distinct from source/native triggers, perceived audibility and a proven synthesis mechanism.",
                sourceDurationAdaptation=False, existingInstrumentIdsRetained=True, allTonalSchedulesEqual=True,
                leadBassSharedRegisterTrajectoriesEqual=True, tonalHarmonyAndPredecessorReleaseTrajectoriesEqual=True,
                changedFrameOffsets=changed, allowedHarmonyHistoryIntervals=intervals, actualNoiseBodies=bodies,
                gatedNoiseBodyCallCounts={str(count): sum(b["gatedNoiseBodyCalls"] == count for b in bodies) for count in sorted({b["gatedNoiseBodyCalls"] for b in bodies})},
                boundaries=boundaries, renderedHitEnergy=rendered_hits, matchedOrderedNonRhythmStores=non_rhythm_stores,
                matchedOrderedPreservedStores=preserved_stores, sameSidHarmonyDiagnosticSnapshotsIdentical=True,
                maximumPreservedInstructionStartDifferenceCycles=maximum_cycle_shift,
                preStopReleaseAcRms=release["acRms"],
                limitation="Added processing may shift native write timing and tonal oscillator phase; separate-export PCM subtraction is not a percussion stem. Voice2-only rendering is a diagnostic assessed only inside the declared vacant/boundary windows. No hardware equivalence or full-song listening acceptance is claimed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    preparation = sub.add_parser("prepare")
    for name in ("common", "score", "palette", "original", "balance", "config"):
        preparation.add_argument(name, type=Path)
    checking = sub.add_parser("verify")
    for name in ("previous", "candidate", "adaptation", "config"):
        checking.add_argument(name, type=Path)
    checking.add_argument("--baseline-harmony-wav", required=True, type=Path)
    checking.add_argument("--candidate-harmony-wav", required=True, type=Path)
    for command in (preparation, checking):
        command.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    require(args.output.resolve().is_relative_to(ROOT / "build") and not args.output.exists(), "Choose fresh private output under build/")
    if args.command == "prepare":
        result = prepare(*(read(getattr(args, name)) for name in ("common", "score", "palette", "original", "balance", "config")))
        args.output.mkdir(parents=True)
        for name, value in result.items():
            (args.output / name).write_text(json.dumps(value, indent=2) + "\n")
    else:
        result = verify(args.previous, args.candidate, read(args.adaptation), read(args.config), args.baseline_harmony_wav, args.candidate_harmony_wav)
        with args.output.open("x") as output:
            output.write(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
