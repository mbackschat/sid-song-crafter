"""Prepare and verify one palette interpretation of the retained Rambo graph."""

import argparse
from array import array
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import sys
import wave


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from audio_comparison import Pcm16, measure_pcm, read_pcm16
from rambo_player import LoaderPlayer
from verify_player import require


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def signed(word):
    return word if word < 32768 else word - 65536


def ordinary_vibrato(values):
    if len(values) < 14:
        return False
    steps = [signed(values[index] | values[index + 1] << 8) for index in (0, 2, 4)]
    return (steps[0] == steps[2] == -steps[1] and steps[0] != 0
            and values[8:12] == [3, 6, 3, 0] and not values[13] & 10)


def changed_dramatic_pitch_banks(source, candidate):
    changed = []
    for node_id, node in source["program"].items():
        if not node_id.startswith("voice-1-") or node["kind"] not in ("frequency", "chord"):
            continue
        original = source["dataBanks"][node["dataId"]]
        replacement = candidate["dataBanks"][candidate["program"][node_id]["dataId"]]
        if not ordinary_vibrato(original) and replacement != original:
            changed.append(node_id)
    return changed


def edit_block(values, offset, role):
    result = values.copy()
    preserve_envelope = (role.get("preserveLongReleaseEnvelopes", False)
                         and offset <= 25 and offset + len(values) > 27
                         and (values[26 - offset] & 15) >= 13)
    vibrato = role.get("ordinaryVibrato")
    if offset == 0 and vibrato and ordinary_vibrato(values):
        steps = [signed(values[index] | values[index + 1] << 8) for index in (0, 2, 4)]
        for index, step in zip((0, 2, 4), steps):
            word = (vibrato["stepWords"] * (1 if step > 0 else -1)) & 65535
            result[index:index + 2] = [word & 255, word >> 8]
        result[12] = vibrato["delayCalls"]
    overrides = {int(key): value for key, value in role["dataOverrides"].items()}
    require(all(0 <= key <= 28 and type(value) is int and 0 <= value <= 255
                for key, value in overrides.items()), "Palette overrides must stay inside instrument bytes 0..28")
    for index, value in enumerate(result):
        position = offset + index
        if position in overrides and not (preserve_envelope and position in (25, 26, 27)):
            result[index] = overrides[position]
        if position == 24 and value & 0xf0:
            result[index] = role["waveform"] | (value & 9)
    return result


def prepare(config_path, output):
    config = json.loads(Path(config_path).read_text())
    require(config.get("format") == "rambo-interpretation-v1", "Wrong interpretation config")
    source_path = ROOT / config["source"]
    source_bytes = source_path.read_bytes()
    require(digest(source_bytes) == config["sourceSha256"], "Retained source fingerprint changed")
    source = json.loads(source_bytes)
    candidate = deepcopy(source)
    roles = {role["voice"]: role for role in config["roles"]}
    require(set(roles) == {0, 1, 2}, "Declare exactly the three physical roles")
    candidate["initialData"] = [edit_block(block, 0, roles[voice])
                                for voice, block in enumerate(source["initialData"])]
    candidate["dataBanks"] = {}
    bank_map, edits = {}, []
    offsets = {"write-data": 0, "volume": 24, "frequency": 0, "pulse": 14, "chord": 0}
    for node_id, original in source["program"].items():
        voice = int(node_id.split("-")[1]) - 1
        node = candidate["program"][node_id]
        if node["kind"] in offsets:
            old_id = node["dataId"]
            new_id = f"{old_id}-voice-{voice + 1}"
            values = source["dataBanks"][old_id]
            changed = edit_block(values, offsets[node["kind"]], roles[voice])
            candidate["dataBanks"][new_id] = changed
            bank_map[new_id] = old_id
            node["dataId"] = new_id
            if values != changed:
                edits.append(dict(nodeId=node_id, voice=voice, sourceBank=old_id,
                                  candidateBank=new_id, kind=node["kind"],
                                  changedOffsets=[offsets[node["kind"]] + i for i, pair in enumerate(zip(values, changed)) if pair[0] != pair[1]]))
        elif node["kind"] == "poke-data" and node["offset"] <= 28:
            node["value"] = edit_block([node["value"]], node["offset"], roles[voice])[0]
            if node["value"] != original["value"]:
                edits.append(dict(nodeId=node_id, voice=voice, kind="poke-data",
                                  changedOffsets=[node["offset"]], sourceValue=original["value"], candidateValue=node["value"]))

    def execute(description, normalize=False):
        player = LoaderPlayer(description)
        final_note_ids = {"voice-1-row-0449", "voice-2-row-0287", "voice-3-row-0338"}
        final_notes, envelope_pokes = [], []
        original_note = player.note
        original_operation = player.operation

        def observed_note(event):
            original_note(event)
            if event["nodeId"] in final_note_ids:
                block = player.data[event["voiceIndex"]]
                final_notes.append(dict(nodeId=event["nodeId"], voice=event["voiceIndex"], call=event["call"],
                                        attackDecay=block[25], sustainRelease=block[26],
                                        releaseCountdown=block[27], life=block[28]))

        def observed_operation(runtime, event):
            if event["operation"] == "command" and event["kind"] == "poke-data" and event["offset"] in (25, 26, 27):
                block = player.data[event["voiceIndex"]]
                envelope_pokes.append(dict(nodeId=event["nodeId"], call=event["call"], offset=event["offset"],
                                           sourceEnvelope=block[25:28],
                                           longRelease=(block[26] & 15) >= 13 or event["offset"] == 26 and (event["value"] & 15) >= 13))
            original_operation(runtime, event)

        player.note = observed_note
        player.score.on_operation = observed_operation
        for call in range(description["range"]["auditCalls"]):
            player.play(call)
        events = deepcopy(player.score.operations)
        if normalize:
            for event in events:
                if event.get("operation") == "command":
                    if "dataId" in event:
                        event["dataId"] = bank_map[event["dataId"]]
                    if event.get("kind") == "poke-data":
                        event["value"] = source["program"][event["nodeId"]]["value"]
        last_writes = [max(row["tick"] for row in player.writes
                           if row["phase"] == "play" and 0xd400 + voice * 7 <= row["address"] < 0xd407 + voice * 7)
                       for voice in range(3)]
        return events, last_writes, final_notes, envelope_pokes

    normalized = deepcopy(candidate)
    normalized["initialData"] = source["initialData"]
    normalized["dataBanks"] = source["dataBanks"]
    for node_id, node in normalized["program"].items():
        if "dataId" in node:
            node["dataId"] = bank_map[node["dataId"]]
        if node["kind"] == "poke-data":
            node["value"] = source["program"][node_id]["value"]
    require(normalized == source, "Candidate changed fields outside instrument data")
    require(not changed_dramatic_pitch_banks(source, candidate), "A dramatic lead pitch bank changed")
    preserved_pokes = [node_id for node_id, node in source["program"].items()
                       if node_id.startswith("voice-1-") and
                       (node["kind"] == "poke-sound" or node["kind"] == "poke-data" and node["offset"] < 14)]
    require(all(candidate["program"][node_id] == source["program"][node_id]
                for node_id in preserved_pokes), "An explicit lead pitch/sound poke changed")
    source_events, source_last_writes, source_final_notes, envelope_pokes = execute(source)
    candidate_events, candidate_last_writes, candidate_final_notes, _ = execute(candidate, True)
    require(source_events == candidate_events, "Full source-note, row, fetch, return or command timing changed")
    require(all(int(event["nodeId"].split("-")[1]) - 1 == event["voiceIndex"]
                for event in source_events if "nodeId" in event), "Source node ownership disagrees with executed physical voice")
    require(not any(poke["longRelease"] for poke in envelope_pokes),
            "Retained graph has an individual envelope poke inside a long-release patch; add an explicit preservation rule before interpreting it")
    require([(note["voice"], note["call"]) for note in source_final_notes] == [(1, 10034), (2, 10034), (0, 10035)],
            "Retained final-note landmarks changed")
    require(candidate_final_notes == source_final_notes,
            "Actual final-note entry lost the source ending AD/SR, gate countdown or lifetime")
    negative_controls = []
    faulty_bank = deepcopy(candidate)
    dramatic_node = next(node_id for node_id, node in source["program"].items()
                         if node_id.startswith("voice-1-") and node.get("dataId") == "data-2bbc-14")
    faulty_bank["dataBanks"][candidate["program"][dramatic_node]["dataId"]][12] -= 1
    require(changed_dramatic_pitch_banks(source, faulty_bank), "Dramatic pitch preservation guard missed a changed slide delay")
    negative_controls.append(dict(name="changed dramatic slide delay", sourceBank="data-2bbc-14",
                                  field="frequencyDelay", rejectedByPitchBankGuard=True))
    for name, node_id, field in (("changed source pitch", "voice-1-row-0090", "sourceNote"),
                                 ("changed literal row duration", "voice-1-row-0000", "duration")):
        fault = deepcopy(candidate)
        fault["program"][node_id][field] += 1
        fault_events, *_ = execute(fault, True)
        require(fault_events != source_events, f"Score identity guard missed {name}")
        negative_controls.append(dict(name=name, nodeId=node_id, field=field, rejectedByScoreLedger=True))
    faulty_ending = deepcopy(candidate)
    faulty_ending["dataBanks"]["data-2b74-5-voice-2"][2] = 0xb8
    _, _, faulty_final_notes, _ = execute(faulty_ending, True)
    require(faulty_final_notes != source_final_notes, "Final-note entry guard missed a shortened release")
    negative_controls.append(dict(name="shortened final release", sourceBank="data-2b74-5",
                                  field="sustainRelease", rejectedByActualNoteEntryGuard=True))
    for voice in range(3):
        require(source["initialData"][voice][29:] == candidate["initialData"][voice][29:], "Duration table changed")
    notes = [event for event in source_events if event["operation"] == "note"]
    ledger = json.dumps(source_events, separators=(",", ":"), allow_nan=False).encode()
    output = Path(output)
    require(not output.exists(), "Choose a fresh preparation output directory")
    output.mkdir(parents=True)
    (output / "candidate.json").write_bytes(json_bytes(candidate))
    (output / "score-events.json.gz").write_bytes(gzip.compress(ledger, mtime=0))
    report = dict(schemaVersion=1, sourceSha256=digest(source_bytes),
                  configSha256=digest(Path(config_path).read_bytes()),
                  candidateSha256=digest(json_bytes(candidate)),
                  unchanged=dict(profile=True, completeGraphTopology=True, sourceNotes=True, noteCalls=True,
                                 rowDurations=True, frequencyWords=True, Morse=True, form=True,
                                 initialSound=True, globalVolume=True, dramaticLeadPitchBanksAndSoundPokes=True),
                  checkedCalls=source["range"]["auditCalls"], semanticEvents=len(source_events),
                  lastVoiceWriteTicks=dict(faithful=source_last_writes, candidate=candidate_last_writes),
                  endingEnvelopePreservation=dict(actualFinalNotes=source_final_notes,
                                                  actualCandidateFinalNotes=candidate_final_notes,
                                                  individualSourceEnvelopePokes=envelope_pokes,
                                                  noLongReleaseIndividualPokes=True),
                  sameNormalizedScoreEventsSha256=digest(ledger),
                  negativeControls=negative_controls,
                  noteCounts=[sum(event["voiceIndex"] == voice for event in notes) for voice in range(3)],
                  phraseNoteCounts=[sum(event["voiceIndex"] == voice and 32 <= event["call"] / (17734475 / 18 / 19656) < 48 for event in notes) for voice in range(3)],
                  roles=config["roles"], bankAndPokeEdits=edits,
                  limitations="Gate length, envelopes, waveform and native modulation intentionally change. Semantic note/row identity does not establish identical pitch effects, bus timing, audio or musical success.",
                  modelAssistance=config["modelAssistance"])
    (output / "score-invariants.json").write_bytes(json_bytes(report))
    print(f"Prepared {output / 'candidate.json'}; identical complete semantic score over {report['checkedCalls']} calls")


def window(audio, start, end):
    first, last = round(start * audio.sample_rate), round(end * audio.sample_rate)
    require(0 <= first < last <= audio.frames, "Requested window exceeds initialized render")
    return Pcm16(audio.sample_rate, audio.channels, last - first,
                 audio.samples[first * audio.channels:last * audio.channels], "")


def windows(faithful, candidate, original, output):
    output = Path(output)
    require(not output.exists(), "Choose a fresh windows directory")
    output.mkdir(parents=True)
    report = []
    for label, path in (("faithful", faithful), ("interpretation", candidate), ("original-source", original)):
        audio = read_pcm16(path)
        for name, first, last in (("phrase", 32, 48), ("ending", 205, 225)):
            clip = window(audio, first, last)
            samples = array("h", clip.samples)
            if sys.byteorder != "little":
                samples.byteswap()
            target = output / f"{label}-{name}.wav"
            with wave.open(str(target), "wb") as wav:
                wav.setparams((clip.channels, 2, clip.sample_rate, 0, "NONE", "not compressed"))
                wav.writeframes(samples.tobytes())
            report.append(dict(label=label, sourceSha256=audio.sha256, startSeconds=first,
                               endSeconds=last, path=str(target), sha256=digest(target.read_bytes()), gain=1))
    (output / "windows.json").write_bytes(json_bytes(report))


def signal(config_path, faithful, candidate, diagnostics, comparison, invariants, output):
    config = json.loads(Path(config_path).read_text())
    faithful_audio, candidate_audio = read_pcm16(faithful), read_pcm16(candidate)
    baseline = window(faithful_audio, 32, 48)
    interpretation = window(candidate_audio, 32, 48)
    matching = json.loads(Path(comparison).read_text())
    gains = [entry["gain"] for entry in matching["inputs"]]
    require(baseline.channels == interpretation.channels == 1 and baseline.frames == interpretation.frames,
            "Contribution checks require matched mono phrase windows")

    def rms(values):
        values = list(values)
        mean = sum(values) / len(values)
        return (sum((value - mean) ** 2 for value in values) / len(values)) ** 0.5

    matched_rms = rms(value * gains[0] for value in baseline.samples)
    difference = rms(b * gains[1] - a * gains[0] for a, b in zip(baseline.samples, interpretation.samples))
    require(difference / matched_rms >= config["signalGuards"]["minimumMatchedChangeRatio"],
            "Matched candidate has too little signal change for this intended palette intervention")
    roles = []
    clear_ticks = json.loads(Path(invariants).read_text())["lastVoiceWriteTicks"]
    cadence = 17734475 / 18 / 19656
    for role, path in zip(config["roles"], diagnostics):
        diagnostic_audio = read_pcm16(path)
        diagnostic = window(diagnostic_audio, 32, 48)
        require(diagnostic.frames == interpretation.frames, "Diagnostic window differs")
        contribution = rms(a - b for a, b in zip(interpretation.samples, diagnostic.samples))
        ratio = contribution / rms(interpretation.samples)
        require(ratio >= config["signalGuards"]["minimumRoleContributionRatio"], "An intended role contributes too little rendered signal")
        clear_seconds = (clear_ticks["candidate"][role["voice"]] + 1) / cadence
        before_clear = [clear_seconds - 0.5, clear_seconds - 0.1]
        mixed_tail = window(candidate_audio, *before_clear)
        omitted_tail = window(diagnostic_audio, *before_clear)
        tail_residual = rms(a - b for a, b in zip(mixed_tail.samples, omitted_tail.samples))
        require(tail_residual <= 16, "An interpreted role still has substantial AC energy immediately before lifetime clear")
        roles.append(dict(voice=role["voice"], role=role["role"], omittedVoiceDiagnosticPath=str(path),
                          residualAcRms=contribution, residualToMixAcRmsRatio=ratio,
                          modelLastWriteTick=clear_ticks["candidate"][role["voice"]],
                          estimatedClearSeconds=clear_seconds, preClearWindowSeconds=before_clear,
                          preClearResidualAcRms=tail_residual, maximumPreClearResidualAcRms=16))
    tail_windows = []
    for label, audio in (("faithful", faithful_audio), ("candidate", candidate_audio)):
        end = (max(clear_ticks[label]) + 1) / cadence
        tail_windows.append(dict(label=label, estimatedFinalClearSeconds=end,
                                 precedingWindows=[dict(seconds=[end - width, end - 0.05],
                                                        metrics=measure_pcm(window(audio, end - width, end - 0.05)))
                                                   for width in (0.5, 0.25, 0.1)]))
    report = dict(schemaVersion=1, phraseSeconds=[32, 48], matchingGains=gains,
                  matchedDifferenceAcRms=difference, matchedDifferenceToFaithfulAcRmsRatio=difference / matched_rms,
                  roles=roles, candidatePhrase=measure_pcm(interpretation), endingBeforeLifetimeClears=tail_windows,
                  scope="Rendered signal change and control-mask omission contributions, not perceptual audibility, exact stems or musical acceptance. Muting changes SID control state. Clear windows use model-call time, not measured SID bus timestamps; the submitted ending A/B remains the listening check.")
    closing_body = measure_pcm(window(candidate_audio, 205, 211))
    require(closing_body["acRms"] >= config["signalGuards"]["minimumClosingBodyAcRms"],
            "The interpreted final held/decaying phrase has lost its rendered body")
    report["closingBody"] = dict(seconds=[205, 211], metrics=closing_body,
                                 minimumAcRms=config["signalGuards"]["minimumClosingBodyAcRms"])
    Path(output).write_bytes(json_bytes(report))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("config", type=Path)
    prepare_parser.add_argument("--output", type=Path, required=True)
    clips = commands.add_parser("windows")
    for name in ("faithful", "candidate", "original"):
        clips.add_argument(f"--{name}", type=Path, required=True)
    clips.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("signal")
    check.add_argument("config", type=Path)
    for name in ("faithful", "candidate", "comparison", "invariants", "output"):
        check.add_argument(f"--{name}", type=Path, required=True)
    check.add_argument("--diagnostics", type=Path, nargs=3, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.config, args.output)
    elif args.command == "windows":
        windows(args.faithful, args.candidate, args.original, args.output)
    else:
        signal(args.config, args.faithful, args.candidate, args.diagnostics, args.comparison, args.invariants, args.output)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
