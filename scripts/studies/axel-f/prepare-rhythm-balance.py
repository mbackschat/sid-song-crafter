#!/usr/bin/env python3
"""Reduce the bounded Axel F maracas balance through its native decay rate."""

import argparse
from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("axel_rhythm_trial", Path(__file__).with_name("prepare-rhythm-trial.py"))
TRIAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRIAL)
ROOT, require, read = TRIAL.ROOT, TRIAL.require, TRIAL.read
from audio_comparison import Pcm16, measure_pcm, read_pcm16


def prepare(native, score, previous, config):
    require(config["format"] == "axel-f-rhythm-balance-v1", "Unsupported Axel F balance trial")
    require(TRIAL.fingerprint(previous) == config["previousConfigurationFingerprint"], "Previous rhythm configuration changed")
    require(native["instruments"]["rhythm"] == previous["instrument"], "Previous native noise program changed")
    require(len(score["voices"][1]["events"]) == config["expectedOnsets"], "Source percussion onset count changed")
    original, revised = previous["instrument"]["adsr"], config["adsr"]
    require(len(revised) == 4 and original == "1400" and revised[0] == original[0] and revised[2:] == original[2:]
            and 0 <= int(revised[1], 16) < 4, "Change only the bounded noise decay rate; retain attack, sustain and release")
    candidate = deepcopy(native)
    candidate["instruments"]["rhythm"]["adsr"] = revised
    return {"candidate.json": candidate, "candidate-score.json": deepcopy(score)}


def verify_frames(previous, quiet, previous_ad, revised_ad):
    require(len(previous) == len(quiet) and all(len(row) == 25 for row in previous + quiet), "Frame banks differ")
    changes = [(offset, a, b) for left, right in zip(previous, quiet)
               for offset, (a, b) in enumerate(zip(left, right)) if a != b]
    require(changes and all((offset, a, b) == (12, previous_ad, revised_ad) for offset, a, b in changes),
            "Only the declared voice2 AD value may change; preserve pitch, gate, tonal voices and shared controls")
    return sorted({offset for offset, _, _ in changes})


def verify_isolation(previous_writes, quieter_writes, previous_muted, quieter_muted):
    require(previous_writes and len(previous_writes) == len(quieter_writes), "Ordered SID store counts differ")
    maximum_difference = max(abs(a["instructionStartCycle"] - b["instructionStartCycle"])
                             for a, b in zip(previous_writes, quieter_writes))
    require(maximum_difference == 0, "Native SID store timing changed")
    muted_identical = previous_muted == quieter_muted
    require(muted_identical, "Muted tonal PCM changed")
    return maximum_difference, muted_identical


def measured_reduction(previous_rms, quiet_rms, minimum, maximum):
    require(previous_rms > 1 and quiet_rms > 1, "A balance comparison must retain a nonzero noise contribution")
    change = 20 * math.log10(quiet_rms / previous_rms)
    require(-maximum <= change <= -minimum, "Native noise energy must fall within the declared meaningful balance range")
    return change


def portion(audio, first, last):
    return Pcm16(audio.sample_rate, audio.channels, last - first,
                 audio.samples[first * audio.channels:last * audio.channels], "")


def difference_rms(full, muted, frames):
    difference = [b - a for a, b in zip(muted.samples[:frames * muted.channels], full.samples[:frames * full.channels])]
    mean = sum(difference) / len(difference)
    return (sum((value - mean) ** 2 for value in difference) / len(difference)) ** 0.5


def verify(previous, quiet, previous_solo, quiet_solo, previous_muted, quiet_muted, config):
    previous, quiet = Path(previous), Path(quiet)
    before, after = (read(directory / "native-song.frames.json") for directory in (previous, quiet))
    previous_ad, revised_ad = 0x14, int(config["adsr"][:2], 16)
    changed = verify_frames(before, after, previous_ad, revised_ad)
    manifests = [read(directory / "conversion.json") for directory in (previous, quiet)]
    require(manifests[0]["voices"] == manifests[1]["voices"], "Native note identities, timing, durations or assignments changed")
    require((previous / "native-song.schedule.json").read_bytes() == (quiet / "native-song.schedule.json").read_bytes(),
            "Native source schedule checks changed")
    manifest = manifests[1]
    notes = manifest["voices"][1]["notes"]
    require(len(notes) == config["expectedOnsets"] == 68, "Every selected source attack must remain")
    previous_config = read(ROOT / config["previousConfiguration"])
    require(TRIAL.fingerprint(previous_config) == config["previousConfigurationFingerprint"], "Previous rhythm configuration changed")
    absolute_note = int(previous_config["instrument"]["wave"][0][1], 16) - 0x80 + 11
    expected_word = round(440 * 2 ** ((absolute_note - 69) / 12) * 2 ** 24 / manifest["clockHz"])
    bodies = []
    for index, note in enumerate(notes):
        start = note["startTick"]
        next_start = notes[index + 1]["startTick"] if index + 1 < len(notes) else manifest["scoreTicks"]
        require(after[start][11] == 9 and note["durationTicks"] == note["sourceDurationTicks"], "Native TEST onset or source duration lost")
        states = after[start + 1:next_start]
        gated = [state for state in states if state[11] & 1]
        require(gated and all(state[11] in (0x80, 0x81) and state[12:14] == [revised_ad, 0] for state in states),
                "Every source attack needs the declared noise body and release")
        require(all(abs(state[7] + 256 * state[8] - expected_word) <= 1 for state in states), "Fixed source noise clock changed")
        first_off = next((start + 1 + i for i, state in enumerate(states) if state[11] == 0x80), None)
        require(first_off == note["gateOffTick"], "Executed noise gate differs from the source duration policy")
        bodies.append(dict(startTick=start, gatedNoiseBodyCalls=len(gated), gateOffTick=first_off, nextOnsetTick=next_start))
    ledgers = [read(directory / "native-song.writes.json") for directory in (previous, quiet)]
    require(len(ledgers[0]) == len(ledgers[1]), "Ordered SID store counts differ")
    for left, right in zip(*ledgers):
        require(all(left[key] == right[key] for key in ("phase", "tick", "address")), "Ordered SID store locations changed")
        require(left["value"] == right["value"] or (left["address"], left["value"], right["value"]) == (0xd40c, previous_ad, revised_ad),
                "A SID store changed outside the declared noise decay rate")
    full = [read_pcm16(directory / "native-song.wav") for directory in (previous, quiet)]
    solos = [read_pcm16(path) for path in (previous_solo, quiet_solo)]
    muted = [read_pcm16(path) for path in (previous_muted, quiet_muted)]
    require(len({(audio.frames, audio.channels, audio.sample_rate) for audio in full + solos + muted}) == 1, "PCM layouts differ")
    for directory, path in zip((previous, quiet), (previous_muted, quiet_muted)):
        require(Path(str(path) + ".registers.tsv").read_bytes() == (directory / "native-song.wav.registers.tsv").read_bytes(),
                "Same-SID muted and full renderer snapshots differ")
    timing_difference, muted_identical = verify_isolation(*ledgers, muted[0].samples, muted[1].samples)
    frames = round(manifest["scoreTicks"] / manifest["ticksPerSecond"] * full[0].sample_rate)
    metrics = {label: measure_pcm(portion(audio, 0, frames)) for label, audio in
               zip(("previousFull", "quieterFull", "previousNoiseOnly", "quieterNoiseOnly", "previousMuted", "quieterMuted"), full + solos + muted)}
    require(all(value["clippedSamples"] == 0 for value in metrics.values()), "A phrase render clips")
    minimum, maximum = config["noiseReductionDbRange"]
    solo_change = measured_reduction(metrics["previousNoiseOnly"]["acRms"], metrics["quieterNoiseOnly"]["acRms"], minimum, maximum)
    contributions = [difference_rms(a, b, frames) for a, b in zip(full, muted)]
    contribution_change = measured_reduction(*contributions, minimum, maximum)
    attack_levels = []
    for note, body in zip(notes, bodies):
        first, last = (round(tick / manifest["ticksPerSecond"] * solos[1].sample_rate)
                       for tick in (note["startTick"], body["nextOnsetTick"]))
        rms = measure_pcm(portion(solos[1], first, last))["acRms"]
        require(rms > 1, "A quieter source attack has no rendered noise energy")
        attack_levels.append(dict(startTick=note["startTick"], acRms=rms))
    stop = manifest["stopTick"] / manifest["ticksPerSecond"]
    first, last = (round((stop - offset) * full[1].sample_rate) for offset in (0.5, 0.1))
    release = measure_pcm(portion(full[1], first, last))
    require(release["acRms"] <= 16 and measure_pcm(full[1])["clippedSamples"] == 0, "The quieter render clips or fails to settle before stop")
    return dict(schemaVersion=1, cpuCalls=len(after), changedFrameOffsets=changed, changedRegister="D40C voice2 AD only",
                previousAd=previous_ad, quieterAd=revised_ad, unchangedSourceSchedule=True, unchangedTonalVoicesAndSharedControls=True,
                noiseOnsets=len(notes), renderedNonzeroNoiseAttacks=len(attack_levels), actualNoiseBodies=bodies,
                gatedNoiseBodyCallCounts={str(count): sum(body["gatedNoiseBodyCalls"] == count for body in bodies)
                                         for count in sorted({body["gatedNoiseBodyCalls"] for body in bodies})},
                fixedNoiseFrequencyWord=expected_word,
                sourceDurationAdaptation=False, matchedOrderedSidStores=len(ledgers[0]),
                maximumInstructionStartDifferenceCycles=timing_difference,
                sameSidMutedRendererSnapshotsIdentical=True, mutedPreviousAndQuieterPcmIdentical=muted_identical,
                phrasePcm=metrics, noiseOnlyChangeDb=solo_change, sameSidDifferenceAcRms=contributions,
                sameSidDifferenceChangeDb=contribution_change, perAttackNoiseEnergy=attack_levels,
                preStopReleaseAcRms=release["acRms"],
                limitation="Same-SID voice muting is a contribution diagnostic, not an additive stem. The previous/quieter exports are separate native programs; ordered values and instruction timing are checked, while internal synthesis equivalence and musical acceptance remain unclaimed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    preparation = sub.add_parser("prepare")
    for name in ("native", "score", "previous", "config"):
        preparation.add_argument(name, type=Path)
    checking = sub.add_parser("verify")
    for name in ("previous", "quiet", "previous_solo", "quiet_solo", "previous_muted", "quiet_muted", "config"):
        checking.add_argument(name, type=Path)
    for command in (preparation, checking):
        command.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    require(args.output.resolve().is_relative_to(ROOT / "build") and not args.output.exists(), "Choose fresh private output under build/")
    if args.command == "prepare":
        result = prepare(*(read(getattr(args, name)) for name in ("native", "score", "previous", "config")))
        args.output.mkdir(parents=True)
        for name, value in result.items():
            (args.output / name).write_text(json.dumps(value, indent=2) + "\n")
    else:
        result = verify(*(getattr(args, name) for name in ("previous", "quiet", "previous_solo", "quiet_solo", "previous_muted", "quiet_muted")), read(args.config))
        with args.output.open("x") as output:
            output.write(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
