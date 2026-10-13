"""Measure the pinned Shades players with real CIA Timer A interrupts in VICE."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess

from psid_audit import AuditMemory
from sid_assembler import assemble
from verify_player import PAL_CLOCK, cpu_type, require


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PINS = {
    'Shades_filter_corrected.sid': 'ac7c91d0c4fef41bbc9d9e50840492269151075727efa7182a68dc1a26f1d708',
    'Shades.sid': '75f37752bdc968f8700fe3f791a9c59cae398cdc7846cfea0478460ac6567986',
}
HOST_BASE = 0x0800
COUNTER = 0x0b00
FINISHED = COUNTER + 2
BASELINE_LATCH = 0x4025
ROM_IRQ = 0xff48
CADENCE_TOLERANCE = 4
MAX_CALLS = 65535
spec = importlib.util.spec_from_file_location('fixed_pal_vice_trace', ROOT / 'scripts/trace-sid-vice.py')
fixed_trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixed_trace)


def psid_profile(data):
    """Validate the lower-level single-SID CIA harness contract, including fixtures."""
    require(len(data) >= 124 and data[:4] == b'PSID', 'Expected a complete PSID header')
    word = lambda offset: int.from_bytes(data[offset:offset + 2], 'big')
    require(word(4) == 2 and word(6) == 124 and word(118) == 0x14 and data[122:124] == bytes(2),
            'CIA intake requires PSID v2, explicit PAL MOS6581, and one SID')
    require(word(14) == 1 and word(16) == 1 and int.from_bytes(data[18:22], 'big') == 1,
            'CIA intake requires one default subtune and CIA speed word $00000001')
    load, payload = word(8), data[124:]
    if load == 0:
        require(len(payload) >= 2, 'Missing embedded load address')
        load, payload = int.from_bytes(payload[:2], 'little'), payload[2:]
    end, init, play = load + len(payload), word(10) or load, word(12)
    require(0x0400 <= load < end <= 0xa000, 'Payload must remain in RAM $0400–$9fff')
    require(end <= HOST_BASE or load >= 0x0c00, 'Payload overlaps the CIA host RAM $0800–$0bff')
    require(load <= init < end and load <= play < end, 'Init/play must be callable payload addresses')
    return dict(loadAddress=load, endAddress=end, initAddress=init, playAddress=play,
                sidModel='MOS6581', timing='CIA1 Timer A', defaultSubtune=1, payload=payload)


def source_profile(data):
    digest = hashlib.sha256(data).hexdigest()
    require(digest in SOURCE_PINS.values(), 'Source is not one of the pinned Shades variants')
    return psid_profile(data)


class LatchDiagnosticMemory(AuditMemory):
    def __init__(self):
        super().__init__()
        self.pc = 0
        self.timer_writes = []
        self.port_writes = []

    def __setitem__(self, address, value):
        require(not (HOST_BASE <= address < 0x0c00 or 0x0314 <= address <= 0x0319),
                'Source writes CIA host RAM or interrupt vectors')
        if address in (0xdc04, 0xdc05):
            require(self.phase == 'play' and self.instruction == 'STA',
                    'Diagnostic permits only play-phase non-RMW timer latch stores')
            self.timer_writes.append(dict(phase=self.phase, tick=self.tick, writerPc=self.pc,
                                          instructionStartCycle=self.instruction_cycle,
                                          address=address, value=value))
            self.data[address] = value
            return
        before = len(self.writes)
        super().__setitem__(address, value)
        if address in (0, 1):
            self.port_writes.append(dict(phase=self.phase, tick=self.tick, writerPc=self.pc, address=address, value=value))
        if len(self.writes) != before:
            self.writes[-1]['writerPc'] = self.pc


def bounded_oracle(data, calls, *, observer=None):
    """Execute callable source for ordered-value evidence, without CIA scheduling."""
    profile = psid_profile(data)
    require(type(calls) is int and 1 <= calls <= MAX_CALLS, 'Intake supports 1..65535 play calls')
    memory = LatchDiagnosticMemory()
    memory.data[profile['loadAddress']:profile['endAddress']] = profile['payload']
    cpu = cpu_type()(memory=memory)
    cpu.a = cpu.x = cpu.y = 0
    pcs = set()

    def call(address):
        cpu.stPushWord(0x01ff)
        cpu.pc = address
        start = cpu.processorCycles
        while cpu.pc != 0x0200:
            require(cpu.processorCycles - start < 100000, 'Source call exceeds diagnostic instruction budget')
            memory.pc = cpu.pc
            memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
            require(memory.instruction not in ('???', 'BRK', 'RTI'), 'Unsupported callable source instruction')
            memory.instruction_cycle = cpu.processorCycles - start
            pcs.add(cpu.pc)
            if observer is not None:
                observer(cpu, memory)
            cpu.step()
        require(cpu.sp == 255, 'Source did not restore callable stack')
        return cpu.processorCycles - start

    init_cycles = call(profile['initAddress'])
    idle_x, idle_y = cpu.x, cpu.y
    idle_p = (cpu.p | cpu.ZERO | cpu.INTERRUPT) & ~cpu.NEGATIVE
    memory.phase = 'play'
    cycles = []
    for tick in range(calls):
        memory.tick = tick
        cpu.a, cpu.x, cpu.y = 0, idle_x, idle_y
        # psiddrv.a65 irqjob selects bank $37 and RTI restores the idle flags/XY between calls.
        memory.data[1] = 0x37
        cpu.p = idle_p
        cycles.append(call(profile['playAddress']))
    writes = sorted(memory.writes + memory.timer_writes,
                    key=lambda row: (-1 if row['phase'] == 'init' else row['tick'], row['instructionStartCycle']))
    report = dict(playCalls=calls, initCycles=init_cycles, maximumPlayCycles=max(cycles),
                  playCycles=cycles, portWrites=memory.port_writes,
                  cpuCycleBasis='verify_player.cpu_type',
                  executedPcs=sorted(pcs), additionalIoWrites=[0xdc04, 0xdc05], ioReads=[],
                  limitations='Callable RAM execution checks ordered source values and PCs only; no CIA scheduling, IRQ latency or bus cycles.')
    return report, writes


def shades_oracle(data, calls, *, observer=None):
    """Expose hash-pinned instruction observation without claiming timer emulation."""
    source_profile(data)
    report, writes = bounded_oracle(data, calls, observer=observer)
    require(all(row['address'] == 0xdc05 and row['writerPc'] == 0x7852
                for row in writes if row['address'] in (0xdc04, 0xdc05)),
            'Pinned Shades timer writer differs from the inspected $7852 STA $DC05')
    report['additionalIoWrites'] = [0xdc05]
    return report, writes


def harness(profile, calls):
    require(type(calls) is int and 1 <= calls <= MAX_CALLS, 'Intake supports 1..65535 play calls')
    constants = dict(init_address=profile['initAddress'], play_address=profile['playAddress'],
                     counter=COUNTER, counter_hi=COUNTER + 1, finished=FINISHED,
                     count_lo=calls & 255, count_hi=calls >> 8)
    # libsidplayfp 3.1.1 psiddrv.a65 cold/irqjob defines the latch, bank wrapper and acknowledgement order.
    source = '''
start:
SEI
CLD
LDX #$FF
TXS
LDA #$2F
STA $00
LDA #$37
STA $01
LDA #$00
STA $DC0E
STA $DD0E
STA $DC0F
STA $DD0F
STA $D01A
STA $D011
STA $D015
STA counter
STA counter_hi
STA finished
LDA $D019
STA $D019
LDA #$7F
STA $DC0D
STA $DD0D
LDA $DC0D
LDA $DD0D
LDA #$0F
STA $D418
LDX #$25
LDY #$40
STX $DC04
STY $DC05
LDA irq_vector
STA $0314
LDA irq_vector_hi
STA $0315
LDA #$81
STA $DC0D
LDA #$01
timer_start:
STA $DC0E
LDA #$00
LDX #$00
LDY #$00
JSR init_trampoline
LDA #$37
STA $01
CLI
idle:
LDA finished
BEQ idle
done:
JMP done
irq:
LDA $01
PHA
LDA play_bank
STA $01
LDA #$00
JSR play_trampoline
returned:
PLA
STA $01
DEC $D019
ack:
LDA $DC0D
acknowledged:
INC counter
BNE check_count
INC counter_hi
check_count:
LDA counter
CMP #count_lo
BNE irq_return
LDA counter_hi
CMP #count_hi
BNE irq_return
LDA #$7F
STA $DC0D
LDA #$00
STA $DC0E
LDA #$01
STA finished
irq_return:
PLA
TAY
PLA
TAX
PLA
RTI
init_trampoline:
JMP (init_vector)
play_trampoline:
JMP (play_vector)
init_vector:
.word init_address
play_vector:
.word play_address
irq_vector:
.word irq
play_bank:
.byte $37
'''
    # sid_assembler has no arithmetic syntax; an absolute placeholder also keeps both passes' instruction sizes stable.
    constants['irq_vector_hi'] = HOST_BASE
    payload, labels, _ = assemble(source, constants, load=HOST_BASE)
    constants['irq_vector_hi'] = labels['irq_vector'] + 1
    payload, labels, listing = assemble(source, constants, load=HOST_BASE)
    require(HOST_BASE + len(payload) < COUNTER, 'CIA host overlaps its state')
    return HOST_BASE.to_bytes(2, 'little') + payload, labels, listing


def monitor_commands(payload, program, profile, labels):
    for path in (payload, program):
        require(not any(char in str(path) for char in ('"', '\n', '\r')), 'Unsafe monitor path')
    execs = [profile['initAddress'], profile['playAddress'], ROM_IRQ, labels['irq'], labels['ack'], labels['acknowledged'],
             labels['returned'], labels['timer_start']]
    lines = ['radix h', 'sidefx off', 'dummy off', 'bank ram', 'fill $0002 $bfff $00',
             f'load "{payload}" 0', f'load "{program}" 0', 'r a=$00,x=$00,y=$00,sp=$ff,fl=$24',
             f'r pc=${HOST_BASE:04x}', *[f'trace exec ${address:04x}' for address in execs],
             'trace store $d400 $d418', 'trace store $dc04 $dc05', 'trace store $dc0d $dc0e',
             f'until ${labels["done"]:04x}', 'r', 'bank ram',
             f'm ${COUNTER:04x} ${FINISHED:04x}', 'quit', '']
    return '\n'.join(lines)


def parse_trace(log, profile, labels):
    markers = {profile['initAddress']: 'init', profile['playAddress']: 'play', labels['irq']: 'irq',
               ROM_IRQ: 'romIrq', labels['ack']: 'ack', labels['acknowledged']: 'acknowledged',
               labels['returned']: 'returned', labels['timer_start']: 'timerStart'}
    events, entries, writes = [], [], []
    phase, tick = 'host', None
    lines = log.splitlines()
    for index, line in enumerate(lines):
        header = fixed_trace.TRACE_HEADER.fullmatch(line)
        if not header:
            require(not re.match(r'^#\d+ \(Trace', line), 'Unrecognized VICE trace header')
            continue
        instruction = fixed_trace.INSTRUCTION.fullmatch(lines[index + 1] if index + 1 < len(lines) else '')
        require(instruction, 'Missing VICE instruction checkpoint')
        operation, address, raster, raster_cycle = header.groups()
        pc, encoded, mnemonic, a, x, y, sp, flags, cycle = instruction.groups()
        address, pc = int(address, 16), int(pc, 16)
        registers = dict(a=int(a, 16), x=int(x, 16), y=int(y, 16), sp=int(sp, 16), flags=flags)
        row = dict(writerPc=pc, opcodeHex=''.join(encoded.split()).lower(), instruction=mnemonic.strip(),
                   registers=registers, rasterLine=int(raster), rasterCycle=int(raster_cycle), monitorCycle=int(cycle))
        require(0 <= row['rasterLine'] < 312 and 0 <= row['rasterCycle'] < 63, 'Invalid PAL raster context')
        require(not events or row['monitorCycle'] >= events[-1]['monitorCycle'], 'VICE checkpoint time moved backwards')
        if operation.lower() == 'exec':
            require(address == pc and address in markers, 'Unknown execution checkpoint')
            kind = markers[address]
            if kind == 'init':
                phase, tick = 'init', None
            elif kind == 'play':
                phase, tick = 'play', len(entries)
                entries.append(row)
            elif kind in ('returned', 'ack'):
                phase = 'host'
            row.update(kind=kind, phase=phase, tick=tick)
        else:
            code = bytes.fromhex(row['opcodeHex'])
            require(len(code) == 3 and code[0] in (0x8d, 0x9d, 0x99, 0x8e, 0x8c), 'Trace requires non-RMW absolute stores')
            decoded = re.fullmatch(r'(STA|STX|STY)\s+\$([0-9a-f]{4})(?:,([XY]))?', row['instruction'], re.IGNORECASE)
            expected = 'STX' if code[0] == 0x8e else 'STY' if code[0] == 0x8c else 'STA'
            axis = 'X' if code[0] == 0x9d else 'Y' if code[0] == 0x99 else None
            require(decoded and decoded[1].upper() == expected and int(decoded[2], 16) == int.from_bytes(code[1:], 'little')
                    and (decoded[3].upper() if decoded[3] else None) == axis, 'Store bytes and disassembly disagree')
            effective = (int.from_bytes(code[1:], 'little') + (registers[axis.lower()] if axis else 0)) & 65535
            require(effective == address and (0xd400 <= address <= 0xd418 or address in (0xdc04, 0xdc05, 0xdc0d, 0xdc0e)),
                    'Store address disagrees with supported trace bank')
            source = profile['loadAddress'] <= pc < profile['endAddress']
            register = 'x' if code[0] == 0x8e else 'y' if code[0] == 0x8c else 'a'
            row.update(kind='store', phase=phase if source else 'host', tick=tick, address=address,
                       value=registers[register], source=source)
            writes.append(row)
        events.append(row)
    require(entries, 'Missing CIA-driven play entries')
    return dict(events=events, entries=entries, writes=writes)


def verify_trace(parsed, oracle, calls, oracle_report=None):
    entries, events = parsed['entries'], parsed['events']
    require(len(entries) == calls, 'Missing or extra CIA-driven play calls')
    actual = [(row['phase'], row['tick'], row['writerPc'], row['address'], row['value'])
              for row in parsed['writes'] if row['source']]
    expected = [(row['phase'], row['tick'], row['writerPc'], row['address'], row['value']) for row in oracle]
    require(actual == expected, 'VICE ordered source stores disagree with bounded value oracle')
    irqs = [row for row in events if row['kind'] == 'irq']
    rom_irqs = [row for row in events if row['kind'] == 'romIrq']
    acks = [row for row in events if row['kind'] == 'ack']
    acknowledged = [row for row in events if row['kind'] == 'acknowledged']
    starts = [row for row in parsed['writes'] if row['address'] == 0xdc0e and row['value'] == 1 and not row['source']]
    require(len(rom_irqs) == calls and len(irqs) == calls and len(acks) == calls and len(acknowledged) == calls and len(starts) == 1,
            'Missing IRQ/start/acknowledgement checkpoints')
    require(all(row['registers']['a'] == 0x81 for row in acknowledged), 'IRQ acknowledgement is not CIA1 Timer A')
    require(all(end['monitorCycle'] - start['monitorCycle'] == 4 for start, end in zip(acks, acknowledged)),
            'CIA acknowledgement read duration differs')
    for entry, rom_irq, irq, ack in zip(entries, rom_irqs, irqs, acks):
        require(rom_irq['monitorCycle'] < irq['monitorCycle'] < entry['monitorCycle'] < ack['monitorCycle'], 'IRQ dispatch/acknowledgement order differs')
    latch, loaded = BASELINE_LATCH, BASELINE_LATCH
    expected_intervals = []
    timer_by_tick = {}
    for row in parsed['writes']:
        if row['source'] and row['address'] in (0xdc04, 0xdc05):
            timer_by_tick.setdefault(row['tick'], []).append(row)
    for tick in range(calls - 1):
        expected_intervals.append(loaded + 1)
        for row in timer_by_tick.get(tick, []):
            latch = (latch & 0xff00 | row['value']) if row['address'] == 0xdc04 else (latch & 255 | row['value'] << 8)
        loaded = latch
    intervals = [b['monitorCycle'] - a['monitorCycle'] for a, b in zip(entries, entries[1:])]
    errors = [actual - expected for actual, expected in zip(intervals, expected_intervals)]
    phase_errors, phase_error = [], 0
    for error in errors:
        phase_error += error
        phase_errors.append(phase_error)
    # The four-cycle idle LDA bounds IRQ sampling jitter; interval differences span both endpoints.
    require(max((abs(error) for error in errors + phase_errors), default=0) <= CADENCE_TOLERANCE,
            'CIA cadence differs from continuous latch reload semantics')
    dispatch = [entry['monitorCycle'] - irq['monitorCycle'] for entry, irq in zip(entries, irqs)]
    prologue = [irq['monitorCycle'] - rom_irq['monitorCycle'] for irq, rom_irq in zip(irqs, rom_irqs)]
    require(len(set(dispatch)) == 1, 'CIA host dispatch latency is inconsistent')
    require(len(set(prologue)) == 1, 'KERNAL IRQ prologue latency is inconsistent')
    returned = [row for row in events if row['kind'] == 'returned']
    require(len(returned) == calls, 'Missing source return checkpoints')
    body_cycles = [end['monitorCycle'] - start['monitorCycle'] for start, end in zip(entries, returned)]
    if oracle_report is not None:
        require(body_cycles == oracle_report['playCycles'], 'Executed source instruction durations differ from bounded oracle')
    return dict(playCalls=calls, matchedSourceWrites=len(actual), acknowledgedInterrupts=len(acks),
                ciaAcknowledgementValue=0x81,
                firstPlayAfterTimerStartCycles=entries[0]['monitorCycle'] - starts[0]['monitorCycle'],
                firstRomIrqAfterTimerStartCycles=rom_irqs[0]['monitorCycle'] - starts[0]['monitorCycle'],
                kernalPrologueCycles=prologue[0], irqHandlerToPlayCycles=dispatch[0],
                minimumSourceCallCycles=min(body_cycles), maximumSourceCallCycles=max(body_cycles),
                playToAcknowledgementCycles=[ack['monitorCycle'] - entry['monitorCycle'] for entry, ack in zip(entries, acks)],
                cadence=dict(expectedIntervals=expected_intervals, observedIntervals=intervals, intervalErrors=errors,
                             accumulatedPhaseErrors=phase_errors,
                             maximumAccumulatedPhaseError=max((abs(error) for error in phase_errors), default=0),
                             maximumIntervalError=max((abs(error) for error in errors), default=0),
                             toleranceCycles=CADENCE_TOLERANCE))


def run_profile(data, output, calls, vice, data_directory):
    """Run a validated lower-level CIA fixture; public source intake uses run_trace."""
    profile = psid_profile(data)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh trace output directory')
    oracle_report, oracle = (shades_oracle if hashlib.sha256(data).hexdigest() in SOURCE_PINS.values() else bounded_oracle)(data, calls)
    program, labels, listing = harness(profile, calls)
    output.mkdir(parents=True)
    payload_path, program_path = output / 'payload.prg', output / 'harness.prg'
    payload_path.write_bytes(profile['loadAddress'].to_bytes(2, 'little') + profile['payload'])
    program_path.write_bytes(program)
    (output / 'harness.listing').write_text(listing)
    monitor = output / 'commands.mon'
    monitor.write_text(monitor_commands(payload_path, program_path, profile, labels))
    command = [str(vice), '-config', '/dev/null', '-directory', str(data_directory), '-pal', '+logcolorize',
               '-initbreak', 'ready', '-moncommands', str(monitor), '-monlog', '-monlogname', str(output / 'monitor.log'),
               '-limitcycles', str(4_000_000 + calls * 65536), '-warp', '+sound', '-sidenginemodel', 'resid6581',
               '-cia1model', '1', '-cia2model', '1']
    env = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY'):
        env.pop(key, None)
    for key in ('XDG_CONFIG_HOME', 'XDG_STATE_HOME'):
        env[key] = str(output / key.lower())
        (Path(env[key]) / 'vice').mkdir(parents=True)
    (output / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    with (output / 'process.log').open('w') as process_log:
        subprocess.run(command, env=env, stdout=process_log, stderr=subprocess.STDOUT, timeout=60, check=True)
    parsed = parse_trace((output / 'monitor.log').read_text(errors='replace'), profile, labels)
    verification = verify_trace(parsed, oracle, calls, oracle_report)
    result = dict(schemaVersion=1, evidenceLevel='Real CIA Timer A IRQ dispatch in headless VICE',
                  sourceSha256=hashlib.sha256(data).hexdigest(), viceSha256=hashlib.sha256(vice.read_bytes()).hexdigest(),
                  harnessSha256=hashlib.sha256(program).hexdigest(), profile={k: v for k, v in profile.items() if k != 'payload'},
                  harnessLabels=labels, host=dict(baselineLatch=BASELINE_LATCH, interruptMask=0x81, timerControl=1,
                                                basis='libsidplayfp 3.1.1 src/psiddrv.a65 cold and irqjob',
                                                ciaModel='MOS6526A (new)', ciaModelBasis='libsidplayfp 3.1.1 SidConfig.cpp default MOS8521 (new)',
                                                clockHz=PAL_CLOCK, startupSidVolume=15),
                  oracle=oracle_report, verification=verification,
                  timerWrites=[row for row in parsed['writes'] if row['source'] and row['address'] in (0xdc04, 0xdc05)],
                  limitations='Controlled zero-filled RAM and ROM KERNAL IRQ prologue; display/sprite DMA and unrelated interrupts disabled. CIA starts before default-subtune init; CPU port and source zero-page swaps execute unchanged. Bank wrapper, indirect play dispatch, VIC acknowledge and CIA acknowledge follow libsidplayfp 3.1.1 psiddrv.a65. Added call counting and finite stop occur after acknowledgement. Startup excludes libsidplayfp reset/relocation/raster synchronization and is not PCM alignment evidence. Execution checkpoints precede instructions; store checkpoints follow them, and neither is an exact bus-write timestamp. The callable RAM oracle establishes ordered values, source PCs and source call instruction durations only. No decoded instruments, musical form or listening verdict follows.')
    for name, value in (('trace.json', parsed), ('oracle.writes.json', oracle), ('study.json', result)):
        (output / name).write_text(json.dumps(value, indent=2) + '\n')
    return result


def run_trace(sid, output, calls, vice, data_directory):
    data = sid.read_bytes()
    source_profile(data)
    return run_profile(data, output, calls, vice, data_directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sid', type=Path)
    parser.add_argument('--calls', type=int, default=400)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--vice', type=Path, default=ROOT / '.tools/vice-headless-3.9/build/src/x64sc')
    parser.add_argument('--data', type=Path, default=Path('/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice'))
    args = parser.parse_args()
    result = run_trace(args.sid.resolve(), args.output.resolve(), args.calls, args.vice.resolve(), args.data.resolve())
    print(json.dumps(dict(study=str(args.output.resolve() / 'study.json'), sourceSha256=result['sourceSha256'],
                          playCalls=result['verification']['playCalls'], matchedSourceWrites=result['verification']['matchedSourceWrites'],
                          maximumIntervalError=result['verification']['cadence']['maximumIntervalError'],
                          maximumAccumulatedPhaseError=result['verification']['cadence']['maximumAccumulatedPhaseError'],
                          timerWriteCount=len(result['timerWrites']),
                          timerValues=sorted({row['value'] for row in result['timerWrites']}),
                          firstTimerWriteCall=result['timerWrites'][0]['tick'] if result['timerWrites'] else None,
                          lastTimerWriteCall=result['timerWrites'][-1]['tick'] if result['timerWrites'] else None), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error))
