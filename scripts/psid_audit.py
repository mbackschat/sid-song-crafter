"""Audit RAM-only, single-speed PAL PSID drivers without a score manifest."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from verify_player import CYCLES_PER_FRAME, PAL_CLOCK, cpu_type, require


class AuditMemory:
    def __init__(self):
        self.data = [0] * 65536
        self.data[0:2] = [0x2f, 0x37]
        self.writes = []
        self.phase = "init"
        self.tick = None
        self.instruction_cycle = 0
        self.instruction = ""

    def __getitem__(self, address):
        port = self.data[1]
        require(not (0xd000 <= address <= 0xdfff), f"Unsupported I/O read at ${address:04x}")
        require(not (0xa000 <= address <= 0xbfff and port & 3 == 3), f"Unsupported BASIC ROM read at ${address:04x}")
        require(not (address >= 0xe000 and port & 2), f"Unsupported KERNAL ROM read at ${address:04x}")
        return self.data[address]

    def __setitem__(self, address, value):
        if address == 0:
            require(value & 7 == 7, "CPU port direction must keep mapping bits as outputs")
        if address == 1:
            require(value & 4 and value & 3, "CPU port change would hide SID I/O")
        if 0xd000 <= address <= 0xdfff:
            require(0xd400 <= address <= 0xd418, f"Unsupported I/O write at ${address:04x}")
            require(self.instruction not in ("ASL", "LSR", "ROL", "ROR", "INC", "DEC"), "SID read-modify-write requires a bus-cycle emulator")
            self.writes.append({"phase": self.phase, "tick": self.tick, "instructionStartCycle": self.instruction_cycle, "address": address, "value": value})
        self.data[address] = value


def audit_psid(data, ticks):
    """Run init and bounded VBI calls; report execution evidence, not musical correctness."""
    require(type(ticks) is int and 1 <= ticks <= 100000, "Play-call count must be an integer from 1 to 100000")
    require(len(data) >= 0x7c and data[:4] == b"PSID", "Audit requires a complete PSID header")
    word = lambda offset: int.from_bytes(data[offset:offset + 2], "big")
    require(word(4) == 2 and word(6) == 0x7c, "Audit supports PSID v2NG only")
    require(word(14) == 1 and word(16) == 1, "Audit requires exactly one subtune")
    require(data[18:22] == bytes(4), "CIA timing is unsupported; use a full C64 emulator")
    require(word(118) in (0x14, 0x24), "Audit requires explicit PAL and one declared SID model without MUS/PlaySID flags")
    require(data[122:124] == bytes(2), "Multi-SID/reserved address fields are unsupported")
    load = word(8)
    payload = data[0x7c:]
    if load == 0:
        require(len(payload) >= 2, "Missing embedded load address")
        load = int.from_bytes(payload[:2], "little")
        payload = payload[2:]
    end = load + len(payload)
    init, play = word(10) or load, word(12)
    require(0x0400 <= load < end <= 0xa000, "Audit supports payloads entirely in RAM $0400–$9fff")
    require(load <= init < end and load <= play < end, "Callable init/play must lie inside the payload; IRQ players are unsupported")
    memory = AuditMemory()
    memory.data[load:end] = payload
    cpu = cpu_type()(memory=memory, pc=init)
    cpu.a = cpu.x = cpu.y = 0

    def call(address, budget):
        cpu.stPushWord(0x01ff)
        cpu.pc = address
        start = cpu.processorCycles
        while cpu.pc != 0x0200:
            require(cpu.processorCycles - start < budget, f"Driver exceeds {budget}-cycle call budget")
            memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
            require(memory.instruction not in ("???", "BRK", "RTI"), f"Unsupported opcode at ${cpu.pc:04x}: {memory.instruction}")
            memory.instruction_cycle = cpu.processorCycles - start
            cpu.step()
        require(cpu.sp == 0xff, "Driver did not restore the call stack")
        cycles = cpu.processorCycles - start
        require(cycles <= budget, f"Driver exceeds {budget}-cycle call budget")
        return cycles

    init_cycles = call(init, 1000000)
    memory.phase = "play"
    maximum = 0
    total = 0
    for tick in range(ticks):
        memory.tick = tick
        cycles = call(play, CYCLES_PER_FRAME)
        maximum = max(maximum, cycles)
        total += cycles
    values = defaultdict(list)
    for row in memory.writes:
        if row["phase"] == "play":
            values[row["address"]].append(row["value"])
    report = {
        "schemaVersion": 1, "sourceSha256": hashlib.sha256(data).hexdigest(),
        "cpu": "py65 NMOS 6502", "environment": "RAM-only calls; no CIA, VIC, ROM or SID reads",
        "sidModel": "MOS8580" if word(118) == 0x24 else "MOS6581",
        "loadAddress": load, "initAddress": init, "playAddress": play,
        "clockHz": PAL_CLOCK, "playCalls": ticks, "callRateHz": PAL_CLOCK / CYCLES_PER_FRAME,
        "initCycles": init_cycles, "maximumPlayCycles": maximum, "meanPlayCycles": total / ticks,
        "frameCycleBudget": CYCLES_PER_FRAME,
        "initWriteCount": sum(row["phase"] == "init" for row in memory.writes),
        "playWriteCount": sum(row["phase"] == "play" for row in memory.writes),
        "registers": {f"{address:04x}": {"writes": len(items), "distinctValues": len(set(items)), "minimum": min(items), "maximum": max(items)} for address, items in sorted(values.items())},
        "limitations": "No sound synthesis, interrupt/badline timing, bus-write timestamps, end detection, score equivalence or listening judgment.",
    }
    return report, memory.writes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sid", type=Path)
    parser.add_argument("--ticks", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True, help="JSON report path; writes go in a sibling .writes.json file")
    args = parser.parse_args()
    writes_path = args.output.with_suffix(".writes.json")
    require(args.output.resolve() != args.sid.resolve() and writes_path.resolve() != args.sid.resolve(), "Output must not overwrite the input")
    require(not args.output.exists() and not writes_path.exists(), "Audit outputs already exist; choose a new output path")
    report, writes = audit_psid(args.sid.read_bytes(), args.ticks)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    writes_path.write_text(json.dumps(writes, separators=(",", ":")) + "\n")
    print(f"Audited {report['playCalls']} calls, {report['playWriteCount']} SID writes; peak {report['maximumPlayCycles']}/{CYCLES_PER_FRAME} cycles")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
