"""Audit RAM-only, single-speed VBI PSID drivers without a score manifest."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from psid_profile import ExecutionProfile, SID_MODELS, psid_profile
from sid_audit_host import DEFAULT_HOST_BASE, HOST_SIZE, harness
from sid_clock import clock_spec
from verify_player import cpu_type, require


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
    def __init__(self, sid_bases, host_base=DEFAULT_HOST_BASE):
        super().__init__(sid_bases)
        self.data[1] = 0x36
        self.host_base = host_base

    def __getitem__(self, address):
        require(not self.host_base <= address < self.host_base + HOST_SIZE, f'Unsupported fixed host RAM read at ${address:04x}')
        return super().__getitem__(address)

    def __setitem__(self, address, value):
        require(not (self.host_base <= address < self.host_base + HOST_SIZE or 0x0314 <= address <= 0x0319),
                f'Unsupported fixed host RAM or interrupt vector write at ${address:04x}')
        super().__setitem__(address, value)


def audit_psid(data, ticks, *, observer=None, subtune=None, profile='strict', host_base=None, assume_sid_model=None, clock='pal'):
    """Run init and bounded VBI calls; report execution evidence, not musical correctness.

    An optional read-only observer receives the CPU and memory immediately before
    each instruction. It can inspect phase, tick and instruction-start cycle to
    record driver-specific consumption without changing the execution model.
    PAL banked requires an explicit subtune and mirrors the controlled raster
    host's bank/register/flag and callable-return stack state; host_base selects
    its protected workspace. It is not libsidplayfp IRQ execution.
    Strict supports explicit PAL or NTSC headers with the target frame budget;
    omitting clock retains the legacy PAL-only interpretation.
    """
    require(type(ticks) is int and 1 <= ticks <= 100000, "Play-call count must be an integer from 1 to 100000")
    parsed = psid_profile(data, subtune=subtune, profile=profile, host_base=host_base, assume_sid_model=assume_sid_model, clock=clock)
    target = clock_spec(clock)
    banked = parsed['profile'] == ExecutionProfile.PAL_BANKED.value
    load, init, play = (parsed[key] for key in ('loadAddress', 'initAddress', 'playAddress'))
    sids = parsed['sids']
    memory = BankedAuditMemory(tuple(parsed['sidBases']), parsed['hostBase']) if banked else AuditMemory(tuple(parsed['sidBases']))
    memory.data[load:parsed['endAddress']] = parsed['payload']
    cpu = cpu_type()(memory=memory, pc=init)
    cpu.a, cpu.x, cpu.y = parsed['initAccumulator'], 0, 0
    if banked:
        # trace-sid-vice's banked monitor starts FL=$24; SEI/CLD and final LDX/LDY #0 leave P=$26.
        cpu.p = cpu.UNUSED | cpu.INTERRUPT | cpu.ZERO
        _, host_labels = harness(parsed, 1)
        init_return, play_return = host_labels['init_return'], host_labels['play_return']
    else:
        init_return = play_return = 0x0200

    def call(address, budget, return_address):
        # The shared host's JSR saves return-1; matching that word permits stack
        # introspection while stopping before protected caller RAM is fetched.
        cpu.stPushWord(return_address - 1)
        cpu.pc = address
        start = cpu.processorCycles
        while cpu.pc != return_address:
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

    init_cycles = call(init, 1000000, init_return)
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
        cycles = call(play, target.frame_cycles, play_return)
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
        "clockHz": target.clock_hz, "playCalls": ticks, "callRateHz": target.ticks_per_second,
        "initCycles": init_cycles, "maximumPlayCycles": maximum, "meanPlayCycles": total / ticks,
        "frameCycleBudget": target.frame_cycles,
        "initWriteCount": sum(row["phase"] == "init" for row in memory.writes),
        "playWriteCount": sum(row["phase"] == "play" for row in memory.writes),
        "registers": {f"{address:04x}": {"writes": len(items), "distinctValues": len(set(items)), "minimum": min(items), "maximum": max(items)} for address, items in sorted(values.items())},
        "limitations": "Standard audits capture read-only/unused ports in each declared 32-byte window; explicit diagnostic projections may narrow this coverage. No SID reads, internal bus behavior, sound synthesis, interrupt/badline timing, bus-write timestamps, end detection, score equivalence or listening judgment.",
    }
    if assume_sid_model is not None:
        report['sidModelAssumption'] = parsed['sidModelAssumption']
    if banked:
        report.update(executionProfile=parsed['profile'], subtunes=parsed['subtunes'],
                      defaultSubtune=parsed['defaultSubtune'], selectedSubtune=parsed['selectedSubtune'],
                      entryBank=parsed['entryBank'], hostBase=parsed['hostBase'],
                      initReturnAddress=init_return, playReturnAddress=play_return,
                      entryStateBasis='Controlled PAL raster host: init A=selection-1, X/Y=0, P=$26; play A=$FA, retained X/Y, CMP-equal C/Z set and N clear; bank $36 before each call; callable return words derive from the shared harness JSR labels')
    return report, memory.writes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sid", type=Path)
    parser.add_argument("--ticks", type=int, required=True)
    parser.add_argument('--profile', choices=[profile.value for profile in ExecutionProfile], default='strict')
    parser.add_argument('--clock', choices=('pal', 'ntsc'), default='pal', help='Explicit header clock target; NTSC requires strict')
    parser.add_argument('--subtune', type=int, help='Explicit one-based selection; required for pal-banked')
    parser.add_argument('--host-base', type=lambda value: int(value, 0), help='Explicit page-aligned lower-RAM caller placement; pal-banked only')
    parser.add_argument('--assume-sid-model', choices=SID_MODELS, help='Explicit experiment model for an unknown-model PAL PSID v2; pal-banked only')
    parser.add_argument("--output", type=Path, required=True, help="JSON report path; writes go in a sibling .writes.json file")
    args = parser.parse_args()
    writes_path = args.output.with_suffix(".writes.json")
    require(args.output.resolve() != args.sid.resolve() and writes_path.resolve() != args.sid.resolve(), "Output must not overwrite the input")
    require(not any(path.exists() or path.is_symlink() for path in (args.output, writes_path)), "Audit outputs already exist; choose a new output path")
    report, writes = audit_psid(args.sid.read_bytes(), args.ticks, profile=args.profile, subtune=args.subtune, host_base=args.host_base, assume_sid_model=args.assume_sid_model, clock=args.clock)
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
    print(f"Audited {report['playCalls']} calls, {report['playWriteCount']} SID writes; peak {report['maximumPlayCycles']}/{report['frameCycleBudget']} cycles")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
