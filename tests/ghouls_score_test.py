from dataclasses import dataclass, replace
from pathlib import Path
import copy
import gzip
import hashlib
import json
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ghouls_score import COMMAND_FIELDS, ScoreCommand, ScoreRuntime


@dataclass
class SchedulerSound:
    waveform: int = 65
    rest_remaining: int = 255
    rest_reload: int = 255
    gate_time: int = 255
    transpose: int = 0


def fixture():
    return dict(format="ghouls-composition-v1", voices=[
        dict(cursor="start", duration_remaining=1, repeat_remaining=0,
            repeat_cursor=None, stack=[], enabled=255 if v == 0 else 0, duration_override=0)
        for v in range(3)], program=dict(nodes={
            "start": dict(variants=dict(stream=dict(kind="note", rawNote=40, duration=2, next="stop"))),
            "stop": dict(variants=dict(stream=dict(kind="command", command="disable-voice", fields={}))),
        }))


class GhoulsScoreTest(unittest.TestCase):
    def description(self):
        return json.loads((ROOT / "songs/ghouls.json").read_text())

    def run_score(self, description, calls):
        runtime = ScoreRuntime(description)
        sounds = [SchedulerSound(**{name: row[name] for name in SchedulerSound.__dataclass_fields__})
            for row in description["initialSound"]]
        operations, bodies = [], []

        def apply(voice, operation, current):
            operations.append(dict(operation, voice=voice))
            if operation["kind"] in ("note", "rest"):
                return replace(current, rest_remaining=current.rest_reload)
            if operation["kind"] != "command":
                return current
            fields = operation["fields"]
            command = ScoreCommand(operation["command"])
            if command == ScoreCommand.REST_PARAMETERS:
                return replace(current, rest_reload=fields["restReload"])
            if command == ScoreCommand.WAVEFORM:
                return replace(current, waveform=fields["waveform"])
            if command == ScoreCommand.GATE_TIME:
                return replace(current, gate_time=fields["gateTime"])
            if command == ScoreCommand.TRANSPOSE:
                return replace(current, transpose=fields["transpose"])
            return current

        for call in range(calls):
            for voice in range(3):
                sounds[voice] = runtime.begin_voice(voice, call, sounds[voice], apply)
            bodies.append(dict(call=call, score=runtime.snapshot(), transpose=[s.transpose for s in sounds]))
        return operations, bodies

    def projection(self, description, operations, bodies):
        annotations = description["sourceEvidence"]["nodes"]
        address = lambda cursor: annotations[cursor][next(iter(annotations[cursor]))]["address"] if cursor else 0
        codes = {command: code for command, code in zip(ScoreCommand,
            (0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x88, 0x89, 0x8a, 0x8b, 0x8c, 0x8d, 0x8e, 0x8f, 0x90, 0x91, 0x92))}
        reads = []
        for operation in operations:
            if operation["kind"] == "gate":
                continue
            metadata = annotations[operation["node"]][operation["mode"]]
            command = ScoreCommand(operation["command"]) if operation["kind"] == "command" else None
            if command:
                values = [codes[command]]
                fields = operation["fields"]
                if command == ScoreCommand.CALL:
                    target = address(operation["target"])
                    values += [target & 255, target >> 8]
                elif command == ScoreCommand.SID_STORE_LIST:
                    for store in fields["stores"]:
                        values += [store["address"] - 0xd400, store["value"]]
                    values.append(metadata["reads"][-1]["value"])
                else:
                    values += [fields[name] for name in COMMAND_FIELDS[command]]
            else:
                values = [operation.get("rawNote", 0)]
                if operation["mode"] == "stream":
                    values.append(operation["duration"])
            self.assertEqual(len(values), len(metadata["reads"]), operation)
            for index, (value, original) in enumerate(zip(values, metadata["reads"])):
                reads.append(dict(kind=original["kind"], call=operation["call"], voice=operation["voice"],
                    address=original["address"], value=value,
                    callDepth=operation["callDepth"] + int(command == ScoreCommand.CALL and index > 0),
                    repeatRemaining=operation["repeatRemaining"]))
        states = []
        for body in bodies:
            voices = body["score"]
            states.append(dict(call=body["call"], streamPointers=[address(v["cursor"]) for v in voices],
                durationRemaining=[v["duration_remaining"] for v in voices],
                repeatRemaining=[v["repeat_remaining"] for v in voices],
                repeatPointers=[address(v["repeat_cursor"]) for v in voices],
                callDepth=[len(v["stack"]) for v in voices], enableFlags=[v["enabled"] for v in voices],
                transpose=body["transpose"]))
        gates = [dict(call=op["call"], voice=op["voice"], address=op["address"], value=op["value"])
            for op in operations if op["kind"] == "gate"]
        return reads, states, gates

    def run_fixture(self, description, calls):
        runtime = ScoreRuntime(description)
        sound = SchedulerSound()
        operations = []

        def apply(voice, operation, current):
            operations.append(dict(operation, voice=voice))
            if operation["kind"] in ("note", "rest"):
                return replace(current, rest_remaining=current.rest_reload)
            return current

        for call in range(calls):
            sound = runtime.begin_voice(0, call, sound, apply)
        return runtime, sound, operations

    def test_duration_counts_down_before_next_score_event(self):
        runtime, _, operations = self.run_fixture(fixture(), 4)
        events = [op for op in operations if op["kind"] != "gate"]
        self.assertEqual([(op["call"], op["kind"]) for op in events], [(0, "note"), (2, "command")])
        self.assertEqual(runtime.voices[0].enabled, 0)
        self.assertEqual(runtime.voices[0].cursor, "stop")

    def test_zero_duration_advances_after_256_calls(self):
        description = fixture()
        description["program"]["nodes"]["start"]["variants"]["stream"]["duration"] = 0
        _, _, operations = self.run_fixture(description, 257)
        self.assertEqual([op["call"] for op in operations if op["kind"] == "command"], [256])

    def test_note_duration_and_control_flow_are_editable(self):
        description = fixture()
        node = description["program"]["nodes"]["start"]["variants"]["stream"]
        node.update(rawNote=44, duration=3, next="rest")
        description["program"]["nodes"]["rest"] = dict(variants=dict(stream=dict(kind="rest", duration=1, next="stop")))
        _, _, operations = self.run_fixture(description, 5)
        events = [op for op in operations if op["kind"] != "gate"]
        self.assertEqual([(op["call"], op["kind"]) for op in events], [(0, "note"), (3, "rest"), (4, "command")])
        self.assertEqual(events[0]["rawNote"], 44)

    def test_persistent_override_selects_grammar_until_explicitly_cleared(self):
        description = fixture()
        nodes = description["program"]["nodes"]
        nodes["start"] = dict(variants=dict(stream=dict(kind="command", command="duration-override",
            fields=dict(durationOverride=3), next="held")))
        nodes["held"] = dict(variants=dict(override=dict(kind="note", rawNote=40, next="clear")))
        nodes["clear"] = dict(variants=dict(override=dict(kind="command", command="duration-override",
            fields=dict(durationOverride=0), next="rest")))
        nodes["rest"] = dict(variants=dict(stream=dict(kind="rest", duration=1, next="stop")))
        for duration in (3, 5):
            with self.subTest(duration=duration):
                nodes["start"]["variants"]["stream"]["fields"]["durationOverride"] = duration
                runtime, _, operations = self.run_fixture(description, duration + 2)
                events = [(op["call"], op["kind"]) for op in operations if op["kind"] != "gate"]
                self.assertEqual(events, [(0, "command"), (0, "note"),
                    (duration, "command"), (duration, "rest"), (duration + 1, "command")])
                self.assertEqual(runtime.voices[0].duration_override, 0)

    def test_same_call_commands_pass_updated_live_sound_to_next_note(self):
        description = fixture()
        description["program"]["nodes"]["transpose"] = dict(variants=dict(stream=dict(
            kind="command", command="transpose", fields=dict(transpose=12), next="start")))
        description["voices"][0]["cursor"] = "transpose"
        runtime = ScoreRuntime(description)
        operations = []

        def apply(voice, operation, current):
            operations.append(operation)
            if operation.get("command") == "transpose":
                return replace(current, transpose=operation["fields"]["transpose"])
            return current

        result = runtime.begin_voice(0, 0, SchedulerSound(), apply)
        note = next(op for op in operations if op["kind"] == "note")
        self.assertEqual((note["rawNote"], note["transpose"]), (40, 12))
        self.assertEqual(result.transpose, 12)

    def test_complete_graph_matches_4998_reads_and_every_retained_score_body(self):
        description = self.description()
        observations = json.load(gzip.open(ROOT / "evidence/ghouls-form/full40000/observations.json.gz", "rt"))
        operations, bodies = self.run_score(description, 13060)
        reads, states, gates = self.projection(description, operations, bodies)
        keys = ("kind", "call", "voice", "address", "value", "callDepth", "repeatRemaining")
        expected_reads = [{key: row[key] for key in keys} for row in observations["events"] if row["kind"] != "commandDispatch"]
        self.assertEqual(len(reads), 4998)
        self.assertEqual(reads, expected_reads)
        for state, expected in zip(states, observations["bodies"]):
            self.assertEqual(state, {key: expected[key] for key in state})
        self.assertEqual([v["enabled"] for v in bodies[-1]["score"]], [0, 0, 0])
        self.assertFalse(any(op["call"] > 12995 for op in operations))
        boundary = json.load(gzip.open(ROOT / "evidence/ghouls-components/score/native-boundaries.json.gz", "rt"))
        expected_gates = [dict(call=row["call"], voice=row["voice"], address=0xd404 + 7 * row["voice"],
            value=row["waveform"] & 254) for row in boundary["gates"] if row["write"]]
        self.assertEqual(gates, expected_gates)

    def test_runtime_ignores_source_annotations_and_needs_no_files(self):
        description = self.description()
        expected = self.run_score(description, 512)
        description.pop("sourceEvidence")
        with patch("builtins.open", side_effect=AssertionError("Score runtime attempted file access")):
            self.assertEqual(self.run_score(description, 512), expected)

    def native_score(self, calls, edits):
        from psid_audit import audit_psid
        source = ROOT / ".local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid"
        if not source.exists():
            self.skipTest("Pinned private SID is required for edited native score checks")
        data = source.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), "265644a66d6043e6fe5ddeeb0d87e9b4269386a73c3e26457c8d96ce3d042df4")
        reads, bodies, gates = [], [], []
        ranges = ((0x6356, 0x6421), (0x6543, 0x6610), (0x6732, 0x67ff), (0x6858, 0x6cb7))
        dispatch = (0x6362, 0x654f, 0x673e)

        def observe(cpu, memory):
            if memory.phase != "play":
                return
            ram, pc, call = memory.data, cpu.pc, memory.tick
            if pc == 0x6234 and call == 0:
                for target, value in edits.items():
                    ram[target] = value
            if pc in (0x6348, 0x6535, 0x6724):
                voice = (0x6348, 0x6535, 0x6724).index(pc)
                gates.append(dict(call=call, voice=voice, address=0xd404 + 7 * voice, value=cpu.a))
            if any(first <= pc < end for first, end in ranges) and ram[pc] == 0xb1 and ram[pc + 1] in (0x21, 0x23, 0x25):
                voice = (ram[pc + 1] - 0x21) // 2
                pointer = ram[ram[pc + 1]] | ram[ram[pc + 1] + 1] << 8
                target = (pointer + cpu.y) & 65535
                reads.append(dict(kind="dispatchRead" if pc in dispatch else "streamOperandRead",
                    call=call, voice=voice, address=target, value=ram[target],
                    callDepth=ram[0x69 + voice], repeatRemaining=ram[0x2d + voice]))
            if pc == 0x6857 and cpu.sp == 0xfd:
                word = lambda address: ram[address] | ram[address + 1] << 8
                bodies.append(dict(call=call, streamPointers=[word(0x21 + 2 * v) for v in range(3)],
                    durationRemaining=ram[0x27:0x2a], repeatRemaining=ram[0x2d:0x30],
                    repeatPointers=[word(0x30 + 2 * v) for v in range(3)], callDepth=ram[0x69:0x6c],
                    enableFlags=ram[0x7b:0x7e], transpose=ram[0x4e:0x51]))

        audit_psid(data, calls, observer=observe, profile="pal-banked", subtune=1)
        self.assertEqual(source.read_bytes(), data)
        return reads, bodies, gates

    def test_duration_note_repeat_gate_setter_and_rest_edits_match_native_score(self):
        original = self.description()
        operations, _ = self.run_score(original, 1)
        first = next(op for op in operations if op["kind"] == "note" and op["voice"] == 0)
        repeat = next(op for op in operations if op["kind"] == "command" and op["command"] == "repeat-start")
        gate = next(op for op in operations if op["kind"] == "command" and op["command"] == "gate-time")
        for edit in ("duration", "note", "repeat", "gate-time", "rest"):
            with self.subTest(edit=edit):
                description = copy.deepcopy(original)
                selected = repeat if edit == "repeat" else gate if edit == "gate-time" else first
                node = description["program"]["nodes"][selected["node"]]["variants"][selected["mode"]]
                metadata = description["sourceEvidence"]["nodes"][selected["node"]][selected["mode"]]
                if edit == "duration":
                    node["duration"] += 1
                    edits = {metadata["reads"][1]["address"]: node["duration"]}
                elif edit == "note":
                    node["rawNote"] -= 1
                    edits = {metadata["address"]: node["rawNote"]}
                elif edit == "repeat":
                    node["fields"]["count"] -= 1
                    edits = {metadata["reads"][1]["address"]: node["fields"]["count"]}
                elif edit == "gate-time":
                    node["fields"]["gateTime"] = 2
                    edits = {metadata["reads"][1]["address"]: 2}
                else:
                    node["kind"] = "rest"
                    del node["rawNote"]
                    edits = {metadata["address"]: 0}
                actual = self.projection(description, *self.run_score(description, 224))
                expected = self.native_score(224, edits)
                self.assertEqual(actual, expected)
                self.assertNotEqual(actual, self.projection(original, *self.run_score(original, 224)))

    def test_invalid_links_fields_and_context_are_rejected(self):
        description = fixture()
        description["program"]["nodes"]["start"]["variants"]["stream"]["next"] = "missing"
        with self.assertRaisesRegex(ValueError, "symbolic next"):
            ScoreRuntime(description)
        description = fixture()
        description["voices"][0]["duration_override"] = 1
        with self.assertRaisesRegex(ValueError, "override grammar variant"):
            self.run_fixture(description, 1)


if __name__ == "__main__":
    unittest.main()
