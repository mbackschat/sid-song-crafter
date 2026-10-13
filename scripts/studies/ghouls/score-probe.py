"""Expand the pinned selection-1 score independently and verify its source boundary.

The model reads initialized score data, never original driver instructions. Native
execution is an oracle for command setters and scheduler gate edges; it does not
provide the model's event calendar or stream navigation.
"""

import argparse
from collections import Counter
from dataclasses import dataclass, field
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from psid_audit import audit_psid
from psid_profile import psid_profile

SOURCE_SHA = "265644a66d6043e6fe5ddeeb0d87e9b4269386a73c3e26457c8d96ce3d042df4"
FINITE_PROOF_CALLS = 12996
DISPATCH = (0x6362, 0x654f, 0x673e)
BOUNDARIES = (0x6421, 0x6610, 0x67ff)
COUNTDOWN = (0x6338, 0x6525, 0x6714)
PULSE_PHASE = (0x62ee, 0x64db, 0x66ca)
PULSE_RESTART = (0x63d4, 0x65c1, 0x67b0)
FILTER_RESTART = (0x63eb, 0x65da, 0x67c9)
ONSET_WORD = (0x6bda, 0x6bf5, 0x6c10)
OVERRIDE = (0x640f, 0x65fe, 0x67ed)
COMMANDS = {
    0x80: ("pulse-parameters", ("pulseStep", "pulseDefaultLow", "pulseDefaultHigh")),
    0x81: ("repeat-end", ()), 0x82: ("repeat-start", ("count",)),
    0x83: ("rest-parameters", ("restReload",)),
    0x84: ("duration-override", ("durationOverride",)),
    0x85: ("sid-store-list", ("stores",)), 0x86: ("disable-voice", ()),
    0x88: ("filter-parameters", ("filterStep", "filterRestartPhase", "filterDefaultLow", "filterDefaultHigh", "filterLowerLow", "filterLowerHigh", "filterUpperLow", "filterUpperHigh")),
    0x89: ("filter-owner", ()), 0x8a: ("call", ("targetLow", "targetHigh")),
    0x8b: ("return", ()), 0x8c: ("transpose", ("transpose",)),
    0x8d: ("waveform", ("waveform",)),
    0x8e: ("frequency-motion", ("frequencyDelayReload", "frequencyStep", "frequencyHalfReload", "frequencyDirectionDefault")),
    0x8f: ("onset-parameters", ("onsetDelay", "onsetControl", "onsetFrequencyLow", "onsetFrequencyHigh")),
    0x90: ("gate-time", ("gateTime",)),
    0x91: ("note-motion", ("noteStep", "notePositiveDuration", "noteNegativeDuration")),
    0x92: ("glide-rate", ("glideRate",)),
}
PER_VOICE = {
    "waveform": 0x2a, "gateEnabled": 0x36, "restReload": 0x39,
    "restRemaining": 0x3c, "pulseStep": 0x4b, "transpose": 0x4e,
    "onsetDelay": 0x51, "onsetControl": 0x54, "frequencyDelayReload": 0x57,
    "notePositiveDuration": 0x5a, "noteNegativeDuration": 0x5d,
    "glideRate": 0x63, "frequencyDirectionDefault": 0x81,
    "frequencyHalfReload": 0x87, "frequencyStep": 0x8a,
    "gateTime": 0x90, "noteStep": 0x93,
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def word(memory, address):
    return memory[address] | memory[(address + 1) & 65535] << 8


def named(memory, voice):
    result = {name: memory[base + voice] for name, base in PER_VOICE.items()}
    result.update(pulseWord=word(memory, 0x3f + 2 * voice),
        pulseDefault=word(memory, 0x45 + 2 * voice),
        pulseFallback=word(memory, 0x6a05 + 2 * voice),
        pulseDirection=memory[PULSE_PHASE[voice]], pulseRestartPhase=memory[PULSE_RESTART[voice]],
        filterRestartPhase=memory[FILTER_RESTART[voice]],
        onsetFrequency=word(memory, ONSET_WORD[voice]), durationOverride=memory[OVERRIDE[voice]],
        filterWord=word(memory, 0x6f), filterDefault=word(memory, 0x71),
        filterStep=memory[0x73], filterOwner=memory[0x74],
        filterLowerWord=memory[0x6819] | memory[0x6813] << 8,
        filterUpperWord=memory[0x6833] | memory[0x682d] << 8)
    return result


@dataclass
class Voice:
    pointer: int
    duration: int = 1
    repeat_remaining: int = 0
    repeat_pointer: int = 0
    stack: list = field(default_factory=list)
    enabled: int = 255
    transpose: int = 0
    override: int = 0
    waveform: int = 0
    gate_time: int = 255
    rest_reload: int = 0
    rest_remaining: int = 0


def state(voices, call):
    return dict(call=call, streamPointers=[v.pointer for v in voices],
        durationRemaining=[v.duration for v in voices], repeatRemaining=[v.repeat_remaining for v in voices],
        repeatPointers=[v.repeat_pointer for v in voices], callDepth=[len(v.stack) for v in voices],
        enableFlags=[v.enabled for v in voices], transpose=[v.transpose for v in voices])


def expand(memory, ticks, *, duration_plus_one=False, ignore_override=False):
    voices = [Voice(memory[0x730e + voice * 14] | memory[0x7315 + voice * 14] << 8) for voice in range(3)]
    reads, events, bodies, gates = [], [], [], []

    def read(v, voice, call, offset, dispatch=False):
        address = (v.pointer + offset) & 65535
        value = memory[address]
        reads.append(dict(call=call, voice=voice, address=address, value=value,
            kind="dispatchRead" if dispatch else "streamOperandRead",
            callDepth=len(v.stack), repeatRemaining=v.repeat_remaining))
        return value

    for call in range(ticks):
        for voice, v in enumerate(voices):
            if v.enabled < 128:
                continue
            v.duration = (v.duration - 1) & 255
            if v.duration == v.gate_time or v.rest_remaining == 0:
                gates.append(dict(call=call, voice=voice, address=0xd404 + voice * 7, value=v.waveform & 254))
                v.rest_remaining = (v.rest_remaining + 1) & 255
            v.rest_remaining = (v.rest_remaining - 1) & 255
            if v.duration:
                continue
            for _ in range(256):
                address = v.pointer
                code = read(v, voice, call, 0, True)
                event = dict(call=call, voice=voice, address=address, code=code,
                    callDepth=len(v.stack), repeatRemaining=v.repeat_remaining)
                if code < 128:
                    override = 0 if ignore_override else v.override
                    duration = override or read(v, voice, call, 1)
                    v.duration = (duration + int(duration_plus_one)) & 255
                    v.pointer = (v.pointer + (1 if override else 2)) & 65535
                    v.rest_remaining = v.rest_reload
                    event.update(kind="note" if code else "rest", duration=duration,
                        durationSource="override" if override else "stream",
                        transpose=v.transpose, requestedNoteIndex=(code + v.transpose) & 255 if code else None)
                    events.append(event)
                    break
                if code not in COMMANDS:
                    raise ValueError(f"Unexecuted/unsupported command ${code:02x} at ${address:04x}")
                name, fields = COMMANDS[code]
                event.update(kind="command", command=name)
                if code == 0x8a:
                    v.stack.append((v.pointer + 3) & 65535)
                operands = []
                if code == 0x85:
                    offset, stores = 1, []
                    while True:
                        index = read(v, voice, call, offset)
                        operands.append(index)
                        offset += 1
                        if index >= 128:
                            if not stores:
                                raise ValueError("Empty SID-store list is outside the executed grammar")
                            break
                        value = read(v, voice, call, offset)
                        operands.append(value)
                        stores.append(dict(address=0xd400 + index, value=value))
                        offset += 1
                    event["fields"] = dict(stores=stores, terminator=operands[-1])
                else:
                    operands = [read(v, voice, call, offset + 1) for offset in range(len(fields))]
                    offset = len(operands) + 1
                    event["fields"] = dict(zip(fields, operands))
                event["operandBytes"] = operands
                if code == 0x82:
                    v.repeat_remaining = operands[0]
                    v.repeat_pointer = (v.pointer + 2) & 65535
                elif code == 0x81:
                    v.repeat_remaining = (v.repeat_remaining - 1) & 255
                    if v.repeat_remaining:
                        v.pointer = v.repeat_pointer
                        events.append(event)
                        continue
                elif code == 0x86:
                    v.enabled = (v.enabled + 1) & 255
                    events.append(event)
                    break
                elif code == 0x8a:
                    v.pointer = operands[0] | operands[1] << 8
                    events.append(event)
                    continue
                elif code == 0x8b:
                    v.pointer = v.stack.pop()
                    events.append(event)
                    continue
                elif code == 0x83:
                    v.rest_reload = operands[0]
                elif code == 0x84:
                    v.override = operands[0]
                elif code == 0x8c:
                    v.transpose = operands[0]
                elif code == 0x8d:
                    v.waveform = operands[0]
                elif code == 0x90:
                    v.gate_time = operands[0]
                v.pointer = (v.pointer + offset) & 65535
                events.append(event)
            else:
                raise ValueError("Same-call score command budget exceeded")
        bodies.append(state(voices, call))
    return dict(events=events, reads=reads, bodies=bodies, gateWrites=gates)


def setter(event, before):
    """Return the independently calculated fields and immediate command stores."""
    code, fields, voice = event["code"], event["fields"], event["voice"]
    changed, writes = {}, []
    if code == 0x80:
        default = fields["pulseDefaultLow"] | fields["pulseDefaultHigh"] << 8
        changed = dict(pulseStep=fields["pulseStep"], pulseDefault=default,
            pulseWord=default or before["pulseFallback"])
    elif code == 0x83:
        changed = dict(gateEnabled=1, restReload=fields["restReload"])
    elif code == 0x85:
        writes = fields["stores"]
    elif code == 0x88:
        default = fields["filterDefaultLow"] | fields["filterDefaultHigh"] << 8
        changed = dict(filterStep=fields["filterStep"], filterRestartPhase=fields["filterRestartPhase"],
            filterWord=default, filterDefault=default,
            filterLowerWord=fields["filterLowerLow"] | fields["filterLowerHigh"] << 8,
            filterUpperWord=fields["filterUpperLow"] | fields["filterUpperHigh"] << 8)
    elif code == 0x89:
        changed = dict(filterOwner=voice)
    elif code == 0x8d:
        phase = 255 if fields["waveform"] & 64 else 1
        changed = dict(waveform=fields["waveform"], pulseDirection=phase, pulseRestartPhase=phase)
        writes = [dict(address=0xd404 + voice * 7, value=fields["waveform"])]
    elif code == 0x8f:
        changed = dict(onsetDelay=fields["onsetDelay"], onsetControl=fields["onsetControl"],
            onsetFrequency=fields["onsetFrequencyLow"] | fields["onsetFrequencyHigh"] << 8)
    elif code in (0x84, 0x8c, 0x8e, 0x90, 0x91, 0x92):
        changed = dict(fields)
    return changed, writes


def capture(data, ticks, *, intervention=None):
    records, gates, bodies, pending = [], [], [], {}

    def flush(voice, memory):
        if voice not in pending:
            return
        row, first_write = pending.pop(voice)
        row["after"] = named(memory.data, voice)
        row["writes"] = [dict(address=w["address"], value=w["value"]) for w in memory.writes[first_write:]]
        records.append(row)

    def observe(cpu, memory):
        if memory.phase != "play":
            return
        ram, pc, call = memory.data, cpu.pc, memory.tick
        if pc == 0x6857 and cpu.sp == 0xfd:
            bodies.append(dict(call=call,
                streamPointers=[word(ram, 0x21 + 2 * v) for v in range(3)],
                durationRemaining=ram[0x27:0x2a], repeatRemaining=ram[0x2d:0x30],
                repeatPointers=[word(ram, 0x30 + 2 * v) for v in range(3)],
                callDepth=ram[0x69:0x6c], enableFlags=ram[0x7b:0x7e], transpose=ram[0x4e:0x51]))
        if pc in BOUNDARIES:
            flush(BOUNDARIES.index(pc), memory)
        if pc in COUNTDOWN:
            voice = COUNTDOWN.index(pc)
            duration = (ram[0x27 + voice] - 1) & 255
            gates.append(dict(call=call, voice=voice, durationBefore=ram[0x27 + voice],
                durationAfterDecrement=duration, restBefore=ram[0x3c + voice],
                gateTime=ram[0x90 + voice], waveform=ram[0x2a + voice],
                write=(duration == ram[0x90 + voice] or ram[0x3c + voice] == 0)))
        if pc not in DISPATCH:
            return
        voice = DISPATCH.index(pc)
        flush(voice, memory)
        address = word(ram, 0x21 + 2 * voice)
        if intervention and call == 0 and voice == 0:
            for target, value in intervention.items():
                ram[target] = value
        code = ram[address]
        pending[voice] = (dict(call=call, voice=voice, address=address, code=code,
            before=named(ram, voice)), len(memory.writes))

    report, writes = audit_psid(data, ticks, observer=observe, profile="pal-banked", subtune=1)
    assert not pending
    return dict(events=records, gates=gates, bodies=bodies, audit=report), writes


def first_difference(left, right):
    for index, (a, b) in enumerate(zip(left, right)):
        if a != b:
            return dict(index=index, model=a, oracle=b)
    if len(left) != len(right):
        return dict(index=min(len(left), len(right)), modelLength=len(left), oracleLength=len(right))
    return None


def compare(model, observed):
    fields = ("kind", "call", "voice", "address", "value", "callDepth", "repeatRemaining")
    projection = lambda rows: [dict((key, row[key]) for key in fields) for row in rows]
    reads = [r for r in observed["events"] if r["kind"] != "commandDispatch"]
    difference = first_difference(projection(model["reads"]), projection(reads))
    if difference:
        return dict(passed=False, boundary="stream-reads", firstDifference=difference)
    bodies = [{key: row[key] for key in model["bodies"][0]} for row in observed["bodies"][:len(model["bodies"])]]
    difference = first_difference(model["bodies"], bodies)
    return dict(passed=difference is None, boundary="named-score-bodies", firstDifference=difference,
        comparedReads=len(reads), comparedBodies=len(bodies))


def publish(directory, name, data, compressed=False):
    raw = (json.dumps(data, separators=(",", ":") if compressed else None,
        indent=None if compressed else 2) + "\n").encode()
    stored = gzip.compress(raw, mtime=0) if compressed else raw
    with (directory / name).open("xb") as output:
        output.write(stored)
    return dict(sha256=hashlib.sha256(stored).hexdigest(), bytes=len(stored),
        decodedSha256=hashlib.sha256(raw).hexdigest(), decodedBytes=len(raw))


def contract():
    return dict(supportedSelection=1,
        grammar=[dict(code=code, name=name, operandFields=list(fields)) for code, (name, fields) in COMMANDS.items()],
        unexecutedCommandsExcluded=[0x87, 0x93, 0x94],
        scheduler=dict(voiceOrder=[0, 1, 2], active="enableFlag >= 128",
            sequence=["continuing sound stages", "duration=(duration-1)&255", "gate edge", "restRemaining=(restRemaining-1)&255", "if duration==0 consume score", "next voice", "shared filter update"],
            gatePredicate="durationAfterDecrement == gateTime or restRemaining == 0",
            gateStore="voice control = waveform & 254; restRemaining=(restRemaining+1)&255 before its unconditional decrement",
            disable="increment enableFlag modulo256; do not advance stream pointer; skip subsequent voice processing"),
        notes=dict(positive="1..127; apply transpose modulo256; sound setup resolves current/target pitch",
            zero="rest; reload restRemaining only, with no pitch/onset setup or immediate SID store",
            duration="Persistent nonzero override supplies the duration and omits the stream duration byte; zero override consumes the following byte",
            durationZero="Zero byte lasts 256 subsequent calls by decrement-before-zero scheduling",
            spacing="A note loaded at call N with nonzero duration D advances again at N+D"),
        control=dict(commandTiming="Execute setters and navigation in stream order in the same call, ending at a note/rest/disable",
            repeat="One saved pointer/counter per voice; start replaces them; end decrements modulo256, jumping while nonzero",
            scoreCall="Save address+3, increment depth before reading destination operands; return pops the saved address",
            sidStoreList="One or more nonnegative offset/value pairs at $D400+offset, terminated by a negative offset byte; zero pairs are outside executed contract",
            pulseZeroDefault="A zero pulse default loads the separate pulseFallback into live pulseWord; all observed fallback words are zero and $94 is unexecuted"),
        soundBoundary=dict(noteInput=["voice", "rawNote", "transpose", "named current sound state"],
            restInput=["voice", "restReload"],
            commandInput="Typed operand fields plus current named state; command-setters.json.gz retains assignments and immediate SID stores",
            ownership="Score owns navigation/countdown/gate/rest and setters. Sound owns continuing body stages and positive-note setup, retaining state between notes.",
            noteSetupEvidence="Sound probe owns full onset/reset arithmetic; this score proof only independently schedules its input events"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--observations", type=Path, default=ROOT / "evidence/ghouls-form/full40000/observations.json.gz")
    args = parser.parse_args()
    assert not args.output.exists() and not args.output.is_symlink(), "Choose a fresh output directory"
    source_path = ROOT / ".local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid"
    data = source_path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == SOURCE_SHA
    observed = json.load(gzip.open(args.observations, "rt"))
    provenance_path = ROOT / "evidence/ghouls-form/provenance.json"
    provenance = json.loads(provenance_path.read_text())
    assert sha(args.observations) == provenance["artifacts"]["full40000/observations.json.gz"]["sha256"]
    assert observed["initializationCopies"] == provenance["sourceCopies"]
    observed = dict(observed, events=[r for r in observed["events"] if r["call"] < FINITE_PROOF_CALLS])
    profile = psid_profile(data, profile="pal-banked", subtune=1)
    memory = [0] * 65536
    memory[profile["loadAddress"]:profile["endAddress"]] = profile["payload"]
    for row in observed["initializationCopies"]:
        memory[row["destination"]:row["destination"] + row["bytes"]] = memory[row["source"]:row["source"] + row["bytes"]]
    model = expand(memory, FINITE_PROOF_CALLS)
    comparison = compare(model, observed)
    assert comparison["passed"], comparison
    controls = {}
    for name, mutation in (("durationPlusOne", dict(duration_plus_one=True)),
            ("ignorePersistentOverride", dict(ignore_override=True))):
        try:
            controls[name] = compare(expand(memory, FINITE_PROOF_CALLS, **mutation), observed)
        except ValueError as error:
            controls[name] = dict(passed=False, boundary="score-grammar", error=str(error))
    assert all(not row["passed"] for row in controls.values())
    native, writes = capture(data, FINITE_PROOF_CALLS)
    assert model["bodies"] == native["bodies"]
    writes_path = args.observations.parent / "audit.writes.json.gz"
    assert sha(writes_path) == provenance["artifacts"]["full40000/audit.writes.json.gz"]["sha256"]
    retained_writes = json.load(gzip.open(writes_path, "rt"))
    assert writes == [row for row in retained_writes if row["phase"] == "init" or row["tick"] < FINITE_PROOF_CALLS]
    key = lambda row: tuple(row[name] for name in ("call", "voice", "address", "code"))
    assert [key(r) for r in model["events"]] == [key(r) for r in native["events"]]
    setter_records = []
    for event, oracle in zip(model["events"], native["events"]):
        if event["kind"] != "command":
            continue
        changed, expected_writes = setter(event, oracle["before"])
        expected = dict(oracle["before"], **changed)
        assert expected == oracle["after"], (event, expected, oracle["after"])
        assert expected_writes == oracle["writes"], (event, expected_writes, oracle["writes"])
        setter_records.append(dict(call=event["call"], voice=event["voice"], address=event["address"],
            command=event["command"], assignedFields=changed, writes=expected_writes))
    expected_gates = [dict(call=r["call"], voice=r["voice"], address=0xd404 + r["voice"] * 7,
        value=r["waveform"] & 254) for r in native["gates"] if r["write"]]
    assert model["gateWrites"] == expected_gates
    stop_keys = {(r["call"], r["voice"]) for r in model["events"] if r["code"] == 0x86}
    native_keys = [(r["call"], r["voice"]) for r in native["gates"]]
    assert native_keys == [(r["call"], voice) for r in model["bodies"]
        for voice in range(3) if r["enableFlags"][voice] >= 128 or (r["call"], voice) in stop_keys]
    first = next(r for r in model["events"] if r["voice"] == 0 and r["kind"] == "note")
    rest_native, _ = capture(data, 1, intervention={first["address"]: 0})
    rest_memory = memory.copy()
    rest_memory[first["address"]] = 0
    rest_model = expand(rest_memory, 1)
    assert rest_model["bodies"] == rest_native["bodies"]
    rest_record = next(r for r in rest_native["events"] if r["voice"] == 0 and r["code"] == 0)
    assert next(r for r in rest_model["events"] if r["voice"] == 0 and r["kind"] == "rest")["duration"] == first["duration"]
    assert rest_record["writes"] == []
    assert rest_record["after"] == dict(rest_record["before"], restRemaining=rest_record["before"]["restReload"])
    zero_memory = memory.copy()
    zero_memory[first["address"] + 1] = 0
    zero_model = expand(zero_memory, 257)
    zero_native, _ = capture(data, 257, intervention={first["address"] + 1: 0})
    assert zero_model["bodies"] == zero_native["bodies"]
    assert [key(r) for r in zero_model["events"]] == [key(r) for r in zero_native["events"]]
    next_note = next(r for r in zero_model["events"] if r["voice"] == 0 and r["kind"] == "note" and r["call"] > 0)
    assert next_note["call"] == 256
    args.output.mkdir(parents=True)
    outputs = {}
    for name, value, compressed in [("expanded.json.gz", model, True), ("native-boundaries.json.gz", native, True),
            ("command-setters.json.gz", setter_records, True), ("negative-controls.json", controls, False),
            ("rest-intervention.json", dict(sourceNote=first, model=rest_model, native=rest_native), False),
            ("duration-zero-intervention.json.gz", dict(sourceNote=first, model=zero_model, native=zero_native), True),
            ("contract.json", contract(), False)]:
        outputs[name] = publish(args.output, name, value, compressed)
    counts = Counter(r["kind"] for r in model["events"])
    receipt = dict(passed=True, sourceSha256=SOURCE_SHA, selectedSubtune=1, processedCalls=FINITE_PROOF_CALLS,
        sourceBytesUnchanged=source_path.read_bytes() == data, scriptSha256=sha(Path(__file__)),
        tools={name: sha(ROOT / "scripts" / name) for name in ("psid_audit.py", "psid_profile.py", "sid_audit_host.py", "verify_player.py")},
        observationsSha256=sha(args.observations), retainedWritesSha256=sha(writes_path),
        formProvenanceSha256=sha(provenance_path), matchedNativePrefixStores=len(writes),
        comparison=comparison, counts=dict(counts),
        commandCounts=dict(Counter(r["command"] for r in model["events"] if r["kind"] == "command")),
        verifiedCommandSetters=len(setter_records), verifiedGateEdges=len(expected_gates),
        maximumObservedScoreCallDepth=max(max(r["callDepth"]) for r in model["bodies"]),
        negativeControlsFailedAsExpected=True, zeroRestSyntheticInterventionPassed=True,
        durationZeroSyntheticInterventionPassed=True,
        outputHashes=outputs,
        limits="Pinned selection-1 score grammar and executed setters. No unexecuted command support; no copied native driver/player; no independent sound synthesis, CPU-cycle, SID-internal, acoustic or listening claim. Native body sound is an oracle only for the separately calculated scheduler gate predicates and command setters.")
    publish(args.output, "receipt.json", receipt)
    print(json.dumps({key: receipt[key] for key in ("passed", "processedCalls", "counts", "verifiedCommandSetters", "verifiedGateEdges")}))


if __name__ == "__main__":
    main()
