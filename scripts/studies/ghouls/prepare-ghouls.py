"""Extract editable score/program data for the pinned finite Ghouls selection 1."""

import argparse
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from ghouls_score import ScoreRuntime
from psid_audit import audit_psid

SOURCE_SHA = "265644a66d6043e6fe5ddeeb0d87e9b4269386a73c3e26457c8d96ce3d042df4"
SOURCE_PATH = ROOT / ".local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid"
COPIES = ((0x2a44, 0x730e, 5083), (0x3eaf, 0x958f, 1907))


def study_module(name):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("ghouls_" + name.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def word(memory, address):
    return memory[address] | memory[address + 1] << 8


def node_id(address):
    return f"phrase_{address:04x}"


def initialize(data):
    initialized = None

    def observe(cpu, memory):
        nonlocal initialized
        if initialized is None and memory.phase == "play":
            initialized = memory.data.copy()

    report, _ = audit_psid(data, 1, observer=observe, profile="pal-banked", subtune=1)
    assert initialized is not None
    return initialized, report


def extract_graph(memory, cursors):
    grammar = study_module("score-probe").COMMANDS
    nodes, evidence = {}, {}
    for start in cursors:
        cursor, override, repeat_remaining, repeat_cursor, stack = start, 0, 0, None, []
        for _ in range(20000):
            address = cursor
            mode = "override" if override else "stream"
            code = memory[address]
            reads = [dict(kind="dispatchRead", address=address, value=code)]

            def read(offset):
                target = (address + offset) & 65535
                value = memory[target]
                reads.append(dict(kind="streamOperandRead", address=target, value=value))
                return value

            if code < 128:
                spec = dict(kind="note" if code else "rest")
                if code:
                    spec["rawNote"] = code
                if not override:
                    spec["duration"] = read(1)
                cursor = (address + (1 if override else 2)) & 65535
                spec["next"] = node_id(cursor)
            else:
                if code not in grammar:
                    raise ValueError(f"Unsupported executed command ${code:02x}")
                command, fields = grammar[code]
                if code == 0x85:
                    offset, stores = 1, []
                    while True:
                        index = read(offset)
                        offset += 1
                        if index >= 128:
                            break
                        value = read(offset)
                        offset += 1
                        stores.append(dict(address=0xd400 + index, value=value))
                    operands = dict(stores=stores)
                else:
                    values = [read(i + 1) for i in range(len(fields))]
                    offset = 1 + len(fields)
                    operands = dict(zip(fields, values))
                next_address = (address + offset) & 65535
                spec = dict(kind="command", command=command, fields=operands)
                if code not in (0x86, 0x8b):
                    spec["next"] = node_id(next_address)
                if code == 0x82:
                    repeat_remaining, repeat_cursor = operands["count"], next_address
                    cursor = next_address
                elif code == 0x81:
                    repeat_remaining = (repeat_remaining - 1) & 255
                    cursor = repeat_cursor if repeat_remaining else next_address
                elif code == 0x8a:
                    stack.append(next_address)
                    cursor = operands["targetLow"] | operands["targetHigh"] << 8
                    spec["target"] = node_id(cursor)
                    spec["fields"] = {}
                elif code == 0x8b:
                    cursor = stack.pop()
                elif code == 0x84:
                    override = operands["durationOverride"]
                    cursor = next_address
                else:
                    cursor = next_address
            identifier = node_id(address)
            existing = nodes.setdefault(identifier, dict(variants={}))["variants"].setdefault(mode, spec)
            assert existing == spec, "A score context decoded inconsistently"
            source_reads = []
            for row in reads:
                original = next(source + row["address"] - destination for source, destination, length in COPIES
                    if destination <= row["address"] < destination + length)
                source_reads.append(dict(row, originalSourceAddress=original))
            evidence.setdefault(identifier, {})[mode] = dict(address=address, opcode=code, reads=source_reads)
            if code == 0x86:
                assert not stack
                break
        else:
            raise ValueError("Finite graph extraction budget exceeded")
    return dict(nodes=nodes), evidence


def description(data):
    assert hashlib.sha256(data).hexdigest() == SOURCE_SHA
    memory, report = initialize(data)
    sound = study_module("sound-probe")
    cursors = [word(memory, 0x21 + 2 * voice) for voice in range(3)]
    program, evidence = extract_graph(memory, cursors)
    voices = []
    for voice, cursor in enumerate(cursors):
        assert memory[0x69 + voice] == 0 and word(memory, 0x30 + 2 * voice) == 0
        voices.append(dict(cursor=node_id(cursor), duration_remaining=memory[0x27 + voice],
            repeat_remaining=memory[0x2d + voice], repeat_cursor=None, stack=[],
            enabled=memory[0x7b + voice], duration_override=memory[(0x640f, 0x65fe, 0x67ed)[voice]]))
    result = dict(format="ghouls-composition-v1", title="Ghouls 'n' Ghosts — selection 1 reconstruction",
        profile=dict(clock="PAL", sidModel="MOS6581", sidCount=1, sidBase=0xd400, frameCycles=19656),
        range=dict(auditCalls=13060), program=program, voices=voices,
        initialSound=[asdict(sound.read_voice(memory, voice)) for voice in range(3)],
        initialFilter=asdict(sound.read_filter(memory)),
        filterRestartPhases=[memory[address] for address in (0x63eb, 0x65da, 0x67c9)],
        pulseFallbacks=[word(memory, 0x6a05 + 2 * voice) for voice in range(3)],
        frequencyWords={str(index): memory[0x6d35 + index] | memory[0x6d96 + index] << 8
            for index in list(range(97)) + [97, 99, 102, 108]},
        sourceEvidence=dict(sourceSha256=SOURCE_SHA, sourceURL="https://www.hvsc.de/download/C64Music/MUSICIANS/F/Follin_Tim/Ghouls_n_Ghosts.sid",
            selectedSubtune=1, musicalRole="provisional", initializedStateCapture="Before first play instruction, after explicit PAL-banked init",
            initializationCopies=[dict(source=s, destination=d, bytes=n) for s, d, n in COPIES],
            initCycles=report["initCycles"], nodes=evidence,
            extractorSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            tools={name: hashlib.sha256((ROOT / "scripts" / name).read_bytes()).hexdigest()
                for name in ("psid_audit.py", "psid_profile.py", "sid_audit_host.py", "verify_player.py", "ghouls_score.py", "ghouls_programs.py")},
            probeHashes={name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                for name in ("score-probe.py", "sound-probe.py")},
            limits="Editable numeric/symbolic data extracted from the pinned initialized source. No original driver instructions, captured store calendar, original IRQ environment, acoustic ending or listening acceptance."))
    ScoreRuntime(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "songs/ghouls.json")
    args = parser.parse_args()
    assert not args.output.exists() and not args.output.is_symlink(), "Choose a fresh output file"
    data = SOURCE_PATH.read_bytes()
    extracted = description(data)
    assert SOURCE_PATH.read_bytes() == data
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(extracted, output, indent=2)
        output.write("\n")
    print(json.dumps(dict(output=str(args.output), nodes=len(extracted["program"]["nodes"]),
        variants=sum(len(n["variants"]) for n in extracted["program"]["nodes"].values()),
        frequencyWords=len(extracted["frequencyWords"]))))


if __name__ == "__main__":
    main()
