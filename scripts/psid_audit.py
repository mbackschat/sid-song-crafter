"""Audit RAM-only, single-speed PAL PSID drivers without a score manifest."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from psid_profile import ExecutionProfile, psid_profile
from verify_player import CYCLES_PER_FRAME, PAL_CLOCK, cpu_type, require


class AuditMemory:
    def __init__(self, sid_bases=(0xd400,)):
        self.sid_bases = sid_bases
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
            # VICE 3.9 reSID SID::write updates its bus value before sound-register dispatch;
            # retain stores to read-only/unused ports without admitting undeclared mirrors.
            require(any(base <= address <= base + 31 for base in self.sid_bases), f"Unsupported I/O write at ${address:04x}")
            require(self.instruction not in ("ASL", "LSR", "ROL", "ROR", "INC", "DEC"), "SID read-modify-write requires a bus-cycle emulator")
            self.writes.append({"phase": self.phase, "tick": self.tick, "instructionStartCycle": self.instruction_cycle, "address": address, "value": value})
        self.data[address] = value


class BankedAuditMemory(AuditMemory):
    def __init__(self, sid_bases):
        super().__init__(sid_bases)
        self.data[1] = 0x36

    def __getitem__(self, address):
        require(not 0xc000 <= address <= 0xc1ff, f'Unsupported fixed host RAM read at ${address:04x}')
        return super().__getitem__(address)

    def __setitem__(self, address, value):
        require(not (0xc000 <= address <= 0xc1ff or 0x0314 <= address <= 0x0319),
                f'Unsupported fixed host RAM or interrupt vector write at ${address:04x}')
        super().__setitem__(address, value)


def audit_psid(data, ticks, *, observer=None, subtune=None, profile='strict'):
    """Run init and bounded VBI calls; report execution evidence, not musical correctness.

    An optional read-only observer receives the CPU and memory immediately before
    each instruction. It can inspect phase, tick and instruction-start cycle to
    record driver-specific consumption without changing the execution model.
    PAL banked requires an explicit subtune and mirrors the controlled raster
    host's bank/register/flag entry state; it is not libsidplayfp IRQ execution.
    """
    require(type(ticks) is int and 1 <= ticks <= 100000, "Play-call count must be an integer from 1 to 100000")
    parsed = psid_profile(data, subtune=subtune, profile=profile)
    banked = parsed['profile'] == ExecutionProfile.PAL_BANKED.value
    load, init, play = (parsed[key] for key in ('loadAddress', 'initAddress', 'playAddress'))
    sids = parsed['sids']
    memory = (BankedAuditMemory if banked else AuditMemory)(tuple(parsed['sidBases']))
    memory.data[load:parsed['endAddress']] = parsed['payload']
    cpu = cpu_type()(memory=memory, pc=init)
    cpu.a, cpu.x, cpu.y = parsed['initAccumulator'], 0, 0
    if banked:
        # trace-sid-vice's banked monitor starts FL=$24; SEI/CLD and final LDX/LDY #0 leave P=$26.
        cpu.p = cpu.UNUSED | cpu.INTERRUPT | cpu.ZERO

    def call(address, budget):
        cpu.stPushWord(0x01ff)
        cpu.pc = address
        start = cpu.processorCycles
        while cpu.pc != 0x0200:
            require(cpu.processorCycles - start < budget, f"Driver exceeds {budget}-cycle call budget")
            memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
            require(memory.instruction not in ("???", "BRK", "RTI"), f"Unsupported opcode at ${cpu.pc:04x}: {memory.instruction}")
            memory.instruction_cycle = cpu.processorCycles - start
            if observer is not None:
                observer(cpu, memory)
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
        if banked:
            # trace-sid-vice's successful LDA #$FA / CMP $D012 preserves X/Y and other status flags.
            memory.data[1] = parsed['entryBank']
            cpu.a = 0xfa
            cpu.p = (cpu.p | cpu.CARRY | cpu.ZERO) & ~cpu.NEGATIVE
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
        "sidModel": sids[0]["model"], "sidCount": len(sids), "sids": sids,
        "loadAddress": load, "initAddress": init, "playAddress": play,
        "clockHz": PAL_CLOCK, "playCalls": ticks, "callRateHz": PAL_CLOCK / CYCLES_PER_FRAME,
        "initCycles": init_cycles, "maximumPlayCycles": maximum, "meanPlayCycles": total / ticks,
        "frameCycleBudget": CYCLES_PER_FRAME,
        "initWriteCount": sum(row["phase"] == "init" for row in memory.writes),
        "playWriteCount": sum(row["phase"] == "play" for row in memory.writes),
        "registers": {f"{address:04x}": {"writes": len(items), "distinctValues": len(set(items)), "minimum": min(items), "maximum": max(items)} for address, items in sorted(values.items())},
        "limitations": "Standard audits capture read-only/unused ports in each declared 32-byte window; explicit diagnostic projections may narrow this coverage. No SID reads, internal bus behavior, sound synthesis, interrupt/badline timing, bus-write timestamps, end detection, score equivalence or listening judgment.",
    }
    if banked:
        report.update(executionProfile=parsed['profile'], subtunes=parsed['subtunes'],
                      defaultSubtune=parsed['defaultSubtune'], selectedSubtune=parsed['selectedSubtune'],
                      entryBank=parsed['entryBank'],
                      entryStateBasis='Controlled PAL raster host: init A=selection-1, X/Y=0, P=$26; play A=$FA, retained X/Y, CMP-equal C/Z set and N clear; bank $36 before each call')
    return report, memory.writes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sid", type=Path)
    parser.add_argument("--ticks", type=int, required=True)
    parser.add_argument('--profile', choices=[profile.value for profile in ExecutionProfile], default='strict')
    parser.add_argument('--subtune', type=int, help='Explicit one-based selection; required for pal-banked')
    parser.add_argument("--output", type=Path, required=True, help="JSON report path; writes go in a sibling .writes.json file")
    args = parser.parse_args()
    writes_path = args.output.with_suffix(".writes.json")
    require(args.output.resolve() != args.sid.resolve() and writes_path.resolve() != args.sid.resolve(), "Output must not overwrite the input")
    require(not any(path.exists() or path.is_symlink() for path in (args.output, writes_path)), "Audit outputs already exist; choose a new output path")
    report, writes = audit_psid(args.sid.read_bytes(), args.ticks, profile=args.profile, subtune=args.subtune)
    evidence = ((args.output, json.dumps(report, indent=2) + "\n"), (writes_path, json.dumps(writes, separators=(",", ":")) + "\n"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        for path, content in evidence:
            with path.open("x", encoding="utf-8") as output:
                created.append(path)
                output.write(content)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    print(f"Audited {report['playCalls']} calls, {report['playWriteCount']} SID writes; peak {report['maximumPlayCycles']}/{CYCLES_PER_FRAME} cycles")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
