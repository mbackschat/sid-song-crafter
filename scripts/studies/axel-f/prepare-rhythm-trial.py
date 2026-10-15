#!/usr/bin/env python3
"""Prepare a source-maracas noise interpretation on Axel F's vacant hook voice."""

import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("axel_kick_helpers", Path(__file__).with_name("prepare-kick-trial.py"))
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)
fingerprint, rational, read, require = HELPERS.fingerprint, HELPERS.rational, HELPERS.read, HELPERS.require
from audio_comparison import Pcm16, measure_pcm, read_pcm16


def prepare(common, score, palette, config):
    require(config["format"] == "axel-f-rhythm-trial-v1", "Unsupported Axel F rhythm trial")
    require(common["provenance"]["sourceSha256"] == score["provenance"]["sourceSha256"] == config["sourceSha256"],
            "Scores must originate in the pinned MIDI")
    require(fingerprint(palette) == config["basePaletteFingerprint"] and fingerprint(score) == config["baseScoreFingerprint"],
            "The established palette or full-score reduction changed")
    require((palette["sidCount"], palette["sidModel"], palette["clock"]) == (1, "MOS8580", "pal"), "Expected one PAL MOS8580")
    require(common["quarterBpm"] == score["quarterBpm"], "Source and reduced tempos differ")
    source_start, source_end = map(rational, config["sourceWindowBeats"])
    start, end = map(rational, config["arrangedWindowBeats"])
    require(source_start - start == source_end - end == 4 and 0 <= start < end <= rational(score["totalBeats"]),
            "The hook must retain the established four-beat source trim")
    require([voice["name"] for voice in score["voices"]] == ["melody", "harmony", "bass"], "Established voice order changed")
    instrument = config["instrument"]
    require(instrument["control"] == "0a" and instrument["hard_restart_adsr"] == "0f00" and instrument["frame1"] == "09"
            and instrument["adsr"][2:] == "00" and len(instrument["adsr"]) == 4
            and len(instrument["wave"]) == 1 and instrument["wave"][0][0] == "81"
            and 0x80 <= int(instrument["wave"][0][1], 16) < 0xe0 and instrument["wave"][0][2] == "00"
            and not instrument["pulse"] and not instrument["filter"]
            and not instrument.get("vibrato", 0) and not instrument.get("vibrato_delay", 0),
            "Use one uncoupled fixed-frequency noise program with zero sustain/release and no filter")
    baseline = deepcopy(score)
    baseline.pop("sections", None)
    baseline["totalBeats"] = float(end - start)
    baseline["provenance"] = {key: value for key, value in score["provenance"].items() if key != "reduction"}
    baseline["provenance"]["rhythmTrial"] = dict(baseScoreFingerprint=fingerprint(score), sourceWindowBeats=config["sourceWindowBeats"])
    for before, after in zip(score["voices"], baseline["voices"]):
        require(not any(rational(event["startBeat"]) < start < rational(event["startBeat"]) + rational(event["durationBeats"])
                        for event in before["events"]), "A tonal note crosses the hook entrance")
        after["events"] = [{**event, "startBeat": float(rational(event["startBeat"]) - start)}
                           for event in before["events"] if start <= rational(event["startBeat"]) < end]
        require(all(rational(event["startBeat"]) + rational(event["durationBeats"]) <= end - start for event in after["events"]),
                "A tonal note crosses the hook ending")
    require(not baseline["voices"][1]["events"], "The harmony voice must be vacant")
    drums = next(part["events"] for part in common["parts"] if part["id"] == "drums")
    selected = [(index, event) for index, event in enumerate(drums)
                if event["midi"] == config["sourceMidi"] and source_start <= rational(event["startBeat"]) < source_end]
    onsets = [rational(event["startBeat"]) for _, event in selected]
    require(len(onsets) == config["expectedOnsets"] and onsets == sorted(set(onsets)), "Source percussion onset count or order changed")
    require(all(onset + rational(event["durationBeats"]) <= next_onset
                for (_, event), onset, next_onset in zip(selected, onsets, onsets[1:] + [source_end])),
            "Source percussion durations overlap; do not silently shorten them")
    bass = {rational(event["startBeat"]) for event in baseline["voices"][2]["events"]}
    off_bass = sum(onset - source_start not in bass for onset in onsets)
    require(off_bass == config["expectedOffBassOnsets"] > 0, "The declared off-bass rhythm contrast changed")
    candidate = deepcopy(baseline)
    candidate["voices"][1]["events"] = [dict(startBeat=float(onset - source_start), durationBeats=float(rational(event["durationBeats"])),
                                              midi=event["midi"]) for (_, event), onset in zip(selected, onsets)]
    native = deepcopy(palette)
    native["title"] = "Axel F maracas noise trial"
    native["instruments"]["rhythm"] = deepcopy(instrument)
    native["sections"] = [dict(name="Source hook with original maracas noise approximation", startBeat=0,
                               endBeat=float(end - start), voices=dict(melody="lead", harmony="rhythm", bass="bass"))]
    reference, with_rhythm = deepcopy(native), deepcopy(native)
    reference["score"], with_rhythm["score"] = "baseline-score.json", "candidate-score.json"
    origins = [dict(sourceEventIndex=index, sourceStartBeat=event["startBeat"], sourceDurationBeats=event["durationBeats"])
               for index, event in selected]
    report = dict(schemaVersion=1, sourceSha256=config["sourceSha256"], sourceWindowBeats=config["sourceWindowBeats"],
                  arrangedWindowBeats=config["arrangedWindowBeats"], sourceMidi=config["sourceMidi"], sourceOnsets=len(selected),
                  offBassOnsets=off_bass, coincidentBassOnsets=len(selected) - off_bass, sourceDurationAdaptation=False,
                  instrumentFingerprint=fingerprint(instrument), retainedSourceOrigins=origins,
                  scope="MIDI70 maracas onset/duration interpretation using an original static-noise patch; not a hi-hat, recovered master patch or complete drum arrangement. Native gate insets remain separate from retained source duration.")
    return {"baseline-score.json": baseline, "candidate-score.json": candidate, "reference.json": reference,
            "candidate.json": with_rhythm, "adaptation.json": report}


def verify_noise_gate(controls, start_tick, gate_off_tick):
    require(isinstance(gate_off_tick, int) and gate_off_tick > start_tick + 1 and controls,
            "Every source attack needs a nonempty noise gate schedule")
    require(all(control == (0x81 if tick < gate_off_tick else 0x80)
                for tick, control in enumerate(controls, start_tick + 1)), "Native noise gate schedule changed")
    return sum(control == 0x81 for control in controls)


def verify(reference, candidate, noise_only, noise_muted, config):
    reference, candidate = Path(reference), Path(candidate)
    before, after = (read(directory / "native-song.frames.json") for directory in (reference, candidate))
    require(len(before) == len(after) and all(len(row) == 25 for row in before + after), "Frame banks differ")
    changed = {index for left, right in zip(before, after) for index, (a, b) in enumerate(zip(left, right)) if a != b}
    require(changed and changed <= set(range(7, 14)), "Rhythm changed tonal voices or shared SID controls")
    ledgers = [[row for row in read(directory / "native-song.writes.json") if not 0xd407 <= row["address"] <= 0xd40d]
               for directory in (reference, candidate)]
    identities = lambda rows: [(row["phase"], row["tick"], row["address"], row["value"]) for row in rows]
    require(identities(ledgers[0]) == identities(ledgers[1]), "Ordered non-rhythm SID stores changed")
    manifest = read(candidate / "conversion.json")
    notes = manifest["voices"][1]["notes"]
    require(len(notes) == config["expectedOnsets"], "Native percussion onset count changed")
    absolute_note = int(config["instrument"]["wave"][0][1], 16) - 0x80 + 11
    expected_word = round(440 * 2 ** ((absolute_note - 69) / 12) * 2 ** 24 / manifest["clockHz"])
    bodies = []
    for index, note in enumerate(notes):
        start = note["startTick"]
        next_start = notes[index + 1]["startTick"] if index + 1 < len(notes) else manifest["scoreTicks"]
        require(after[start][11] == 9 and note["durationTicks"] == note["sourceDurationTicks"],
                "Native TEST onset or unchanged quantized source duration lost")
        states = after[start + 1:next_start]
        body_calls = verify_noise_gate([state[11] for state in states], start, note["gateOffTick"])
        require(all(abs(state[7] + 256 * state[8] - expected_word) <= 1 and state[12:14] == [0x14, 0]
                    for state in states), "Fixed noise frequency or declared envelope changed")
        first_off = next((start + 1 + i for i, state in enumerate(states) if state[11] == 0x80), None)
        require(first_off == note["gateOffTick"], "Executed gate differs from native duration policy")
        bodies.append(dict(startTick=start, sourceDurationTicks=note["sourceDurationTicks"], sourceGateOffTick=note["sourceGateOffTick"],
                           firstObservedGateOffTick=first_off, gatedNoiseBodyCalls=body_calls, nextOnsetTick=next_start))
    require(all(state[23] & 15 == 4 for state in after[:manifest["stopTick"]]), "Bass lost sole filter ownership")
    require(Path(str(noise_muted) + ".registers.tsv").read_bytes() == (candidate / "native-song.wav.registers.tsv").read_bytes(),
            "Same-SID muted and unmuted snapshots differ")
    original, full, solo, muted = (read_pcm16(path) for path in (reference / "native-song.wav", candidate / "native-song.wav", noise_only, noise_muted))
    require(len({(audio.frames, audio.sample_rate, audio.channels) for audio in (original, full, solo, muted)}) == 1, "PCM layouts differ")
    difference = [b - a for a, b in zip(muted.samples, full.samples)]
    require(any(difference), "Primary comparison contains no rhythm contribution")
    frames = round(manifest["scoreTicks"] / manifest["ticksPerSecond"] * full.sample_rate)
    metrics = {label: measure_pcm(Pcm16(audio.sample_rate, audio.channels, frames, audio.samples[:frames], ""))
               for label, audio in (("full", full), ("noiseOnly", solo), ("noiseMuted", muted))}
    require(all(value["clippedSamples"] == 0 and value["acRms"] > 1 for value in metrics.values()), "Clipped or silent rhythm diagnostic")
    stop = manifest["stopTick"] / manifest["ticksPerSecond"]
    first, last = (round((stop - offset) * full.sample_rate) for offset in (0.5, 0.1))
    release = measure_pcm(Pcm16(full.sample_rate, full.channels, last - first, full.samples[first:last], ""))
    require(release["acRms"] <= 16, "Release does not settle before volume clear")
    return dict(schemaVersion=1, frames=len(after), changedOffsets=sorted(changed), unchangedLeadBassAndSharedControls=True,
                matchedOrderedNonRhythmStores=len(ledgers[0]),
                maximumNonRhythmInstructionStartDifferenceCycles=max(abs(a["instructionStartCycle"] - b["instructionStartCycle"]) for a, b in zip(*ledgers)),
                noiseOnsets=len(notes), fixedNoiseFrequencyWord=expected_word, sourceDurationAdaptation=False,
                gatedNoiseBodyCallCounts={str(count): sum(row["gatedNoiseBodyCalls"] == count for row in bodies)
                                         for count in sorted({row["gatedNoiseBodyCalls"] for row in bodies})},
                actualNoiseBodies=bodies, phrasePcm=metrics, sameSidRendererSnapshotsIdentical=True,
                sameSidPairDifferenceRms=(sum(value * value for value in difference) / len(difference)) ** 0.5,
                sameSidPairDifferentSamples=sum(value != 0 for value in difference), preStopReleaseAcRms=release["acRms"],
                scope="Complete native schedule, source durations, noise body/release and shared-control checks. Same-SID muting is a diagnostic with unchanged oscillator coupling/filter roles; not linear stems, hardware equivalence or musical acceptance.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    preparation = sub.add_parser("prepare")
    for name in ("common", "score", "palette", "config"):
        preparation.add_argument(name, type=Path)
    preparation.add_argument("--output", required=True, type=Path)
    checking = sub.add_parser("verify")
    for name in ("reference", "candidate", "noise_only", "noise_muted", "config"):
        checking.add_argument(name, type=Path)
    checking.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    require(args.output.resolve().is_relative_to(ROOT / "build") and not args.output.exists(), "Choose fresh private output under build/")
    if args.command == "prepare":
        results = prepare(*(read(getattr(args, name)) for name in ("common", "score", "palette", "config")))
        args.output.mkdir(parents=True)
        for name, value in results.items():
            (args.output / name).write_text(json.dumps(value, indent=2) + "\n")
    else:
        value = verify(args.reference, args.candidate, args.noise_only, args.noise_muted, read(args.config))
        with args.output.open("x") as output:
            output.write(json.dumps(value, indent=2) + "\n")


if __name__ == "__main__":
    main()
