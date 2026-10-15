"""Probe the pinned Axel F lead without admitting it to the VBI/CIA auditors."""

import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import AuditMemory
from sid_intake import inspect_sid
from verify_player import PAL_CLOCK, cpu_type, require


SOURCE_SHA256 = '87e0a1e8ad618a497e54fc5d4228dee7be53ef6365a30900debcdafbcd21251b'
LOAD_ADDRESS = 0xa000
END_ADDRESS = 0xcbd4
INIT_ADDRESS = 0xc000
PLAY_ADDRESS = 0xc020
PATCH_ADDRESS = 0xae37
PATCH_OFFSET = 126 + PATCH_ADDRESS - LOAD_ADDRESS
INITIAL_TIMER_PERIOD = 0x4026
INIT_HOST_ALLOWANCE = 24
IRQ_HOST_ALLOWANCE = 160
WATCHED_PCS = {0xc1e3, 0xc20e, 0xc239, 0xc364, 0xc380, 0xc38c,
               0xc673, 0xc6ec, 0xc730, 0xc736, 0xc73c, 0xc74d,
               0xc775, 0xc790, 0xcaa6, 0xcb21}
PULSE_ADDRESSES = {0xd409, 0xd40a}

spec = importlib.util.spec_from_file_location('axel_cia_helpers', ROOT / 'scripts/trace-shades-vice.py')
cia = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cia)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def write_gzip(path, value):
    with gzip.open(path, 'wt') as stream:
        json.dump(value, stream, separators=(',', ':'))


def admit_source(data):
    require(digest(data) == SOURCE_SHA256, 'Axel F source fingerprint mismatch')
    header = inspect_sid(data, subtune=1)
    require(header['format'] == 'PSID' and header['version'] == 2
            and header['flags'] == 0x14 and header['dataOffset'] == 124
            and header['headerLoadAddress'] == 0 and header['loadAddress'] == LOAD_ADDRESS
            and header['endAddressExclusive'] == END_ADDRESS
            and header['initAddress'] == INIT_ADDRESS and header['playAddress'] == PLAY_ADDRESS
            and header['subtunes'] == header['defaultSubtune'] == 1
            and header['speedWord'] == 1, 'Unexpected Axel F CIA/banked payload contract')
    require(data[PATCH_OFFSET] == 0x20, 'Pinned pulse-step byte differs')
    return header


class StudyMemory(AuditMemory):
    def __init__(self):
        super().__init__()
        self.pc = 0
        self.timer_writes = []
        self.port_writes = []

    def __getitem__(self, address):
        require(not 0x0800 <= address < 0x0c00, 'Source reads reserved CIA host RAM')
        return super().__getitem__(address)

    def __setitem__(self, address, value):
        require(not (0x0800 <= address < 0x0c00 or 0x0314 <= address <= 0x0319),
                'Source writes reserved CIA host RAM or vectors')
        if address in (0xdc04, 0xdc05):
            require(self.phase == 'play' and self.instruction == 'STA',
                    'Study permits only play-phase non-RMW timer-latch STA')
            self.timer_writes.append(dict(phase=self.phase, tick=self.tick, writerPc=self.pc,
                                          instructionStartCycle=self.instruction_cycle,
                                          address=address, value=value))
            self.data[address] = value
            return
        before = len(self.writes)
        super().__setitem__(address, value)
        if address in (0, 1):
            self.port_writes.append(dict(phase=self.phase, tick=self.tick,
                                         writerPc=self.pc, address=address, value=value))
        if len(self.writes) != before:
            self.writes[-1]['writerPc'] = self.pc


def execute(data, calls, output):
    """Retain ordered callable observations; CIA counters remain a separate proof."""
    memory = StudyMemory()
    memory.data[LOAD_ADDRESS:END_ADDRESS] = data[126:]
    cpu = cpu_type()(memory=memory)
    cpu.a = cpu.x = cpu.y = 0
    cpu.p = cpu.UNUSED | cpu.INTERRUPT | cpu.ZERO
    observations, snapshots = [], []

    def call(address, budget):
        cpu.stPushWord(0x01ff)
        cpu.pc = address
        start = cpu.processorCycles
        while cpu.pc != 0x0200:
            require(cpu.processorCycles - start < budget, 'Source exceeds callable cost bound')
            memory.pc = cpu.pc
            memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
            memory.instruction_cycle = cpu.processorCycles - start
            require(memory.instruction not in ('???', 'BRK', 'RTI'), 'Unsupported callable instruction')
            if cpu.pc in WATCHED_PCS:
                observations.append(dict(phase=memory.phase, tick=memory.tick, pc=cpu.pc,
                    instructionStartCycle=memory.instruction_cycle, a=cpu.a, x=cpu.x, y=cpu.y,
                    status=cpu.p, zeroPage=bytes(memory.data[0xa5:0xad]).hex(),
                    soundState=bytes(memory.data[0xcc00:0xce30]).hex()))
            cpu.step()
            require(cpu.p & cpu.INTERRUPT, 'Source unmasked IRQs inside its callable body')
        require(cpu.sp == 255, 'Source did not restore the callable stack')
        duration = cpu.processorCycles - start
        require(duration <= budget, 'Source exceeds callable cost bound')
        return duration

    init_cycles = call(INIT_ADDRESS, INITIAL_TIMER_PERIOD - INIT_HOST_ALLOWANCE - 1)
    idle_x, idle_y = cpu.x, cpu.y
    idle_status = (cpu.p | cpu.ZERO | cpu.INTERRUPT) & ~cpu.NEGATIVE
    memory.phase = 'play'
    cycles = []
    for tick in range(calls):
        memory.tick = tick
        memory.data[1] = 0x37
        cpu.a, cpu.x, cpu.y, cpu.p = 0, idle_x, idle_y, idle_status
        cycles.append(call(PLAY_ADDRESS, INITIAL_TIMER_PERIOD - IRQ_HOST_ALLOWANCE - 1))
        snapshots.append(dict(tick=tick, sid=bytes(memory.data[0xd400:0xd420]).hex(),
                              soundState=bytes(memory.data[0xcc00:0xce30]).hex()))
    low, high = 0x25, 0x40
    periods = [INITIAL_TIMER_PERIOD]
    for row in memory.timer_writes:
        if row['address'] == 0xdc04:
            low = row['value']
        else:
            high = row['value']
        periods.append(low + 256 * high + 1)
    require(max(cycles) + IRQ_HOST_ALLOWANCE < min(periods), 'Source exceeds shortest timer window')
    writes = sorted(memory.writes + memory.timer_writes,
                    key=lambda row: (-1 if row['phase'] == 'init' else row['tick'],
                                     row['instructionStartCycle']))
    report = dict(playCalls=calls, sourceSha256=digest(data), initCycles=init_cycles,
                  playCycles=cycles, maximumPlayCycles=max(cycles),
                  minimumTimerPeriodCycles=min(periods), timerWrites=memory.timer_writes,
                  portWrites=memory.port_writes, initHostAllowanceCycles=INIT_HOST_ALLOWANCE,
                  irqHostAllowanceCycles=IRQ_HOST_ALLOWANCE,
                  limitations='Source-specific callable CPU observations, with strict I/O/visible-ROM reads, '
                  'SID RMW, host/vector and stack guards. Only play-phase STA DC04/DC05 extends AuditMemory. '
                  'No CIA-counter emulation, interrupt cadence, bus-write times, PCM or listening judgment.')
    output.mkdir()
    write_json(output / 'report.json', report)
    write_gzip(output / 'writes.json.gz', writes)
    write_gzip(output / 'observations.json.gz', observations)
    write_gzip(output / 'snapshots.json.gz', snapshots)
    return report, writes, snapshots


def freeze_step(data):
    require(data[PATCH_OFFSET] == 0x20, 'Pulse-step mutation precondition differs')
    changed = bytearray(data)
    changed[PATCH_OFFSET] = 0
    changed = bytes(changed)
    require([index for index, pair in enumerate(zip(data, changed)) if pair[0] != pair[1]]
            == [PATCH_OFFSET], 'Intervention must change exactly one pinned source byte')
    return changed


def verify_intervention(original, frozen):
    require(len(original) == len(frozen), 'Intervention changed ordered store count')
    differences = []
    maximum_time_difference = 0
    for before, after in zip(original, frozen):
        require(all(before[key] == after[key] for key in ('phase', 'tick', 'writerPc', 'address')),
                'Intervention changed ordered store identity')
        maximum_time_difference = max(maximum_time_difference,
                                     abs(before['instructionStartCycle'] - after['instructionStartCycle']))
        if before['value'] != after['value']:
            require(before['address'] in PULSE_ADDRESSES,
                    'Intervention changed a non-pulse register or timer')
            differences.append(dict(phase=before['phase'], tick=before['tick'],
                                    address=before['address'], before=before['value'], after=after['value']))
    require(differences, 'Pulse intervention had no register effect')
    return dict(changedByteAddress=PATCH_ADDRESS, changedFileOffset=PATCH_OFFSET,
                before=0x20, after=0, matchedOrderedStoreIdentities=len(original),
                changedPulseStoreValues=len(differences),
                changedAddressCounts={f'{address:04x}': count for address, count in
                                      sorted(Counter(row['address'] for row in differences).items())},
                maximumInstructionStartDifferenceCycles=maximum_time_difference,
                limitations='Values/order/count of every non-pulse SID/timer store are preserved. '
                'Recorded store instruction-start timing is checked separately; no SID bus-time or PCM identity follows.'), differences


def verify_pulse_model(writes, snapshots):
    """Check a parameter/state model independently of the source's pulse routine."""
    onsets = {row['tick'] for row in writes if row['writerPc'] == 0xc775 and row['value'] == 0x41}
    require(min(onsets) == 519, 'Lead entrance differs from the bounded source')
    width, ascending, descending = 0x200, 32, 16
    checked = 0
    for snapshot in snapshots[519:]:
        tick = snapshot['tick']
        if tick in onsets:
            width, ascending, descending = 0x200, 32, 16
        else:
            if ascending:
                width = (width + 32) & 65535
                ascending -= 1
            if not ascending:
                if descending:
                    width = (width - 32) & 65535
                    descending -= 1
                else:
                    ascending, descending = 32, 16
        registers = bytes.fromhex(snapshot['sid'])
        require(registers[9] + 256 * registers[10] == width,
                f'Independent pulse progression disagrees at call {tick}')
        checked += 1
    gate_off_motion = 0
    for before, after in zip(snapshots[519:], snapshots[520:]):
        previous = bytes.fromhex(before['sid'])
        current = bytes.fromhex(after['sid'])
        if not current[11] & 1 and current[9:11] != previous[9:11]:
            gate_off_motion += 1
    require(gate_off_motion > 0, 'Bounded source did not exercise pulse motion with GATE clear')
    return dict(comparedLeadCallStates=checked, leadOnsets=len(onsets),
                changingPulseStatesWithGateOff=gate_off_motion,
                initialWidth=0x200, pulseStep=32, ascendingCalls=32, descendingCalls=16,
                repeatReloadsBothCounters=True,
                lastAscentAndFirstDescentCanShareCall=True,
                netWidthChangePerCompleteCycle=0x200,
                independentOfGateState=True,
                limitations='Numeric pulse-state proof driven by observed onset boundaries; '
                'not a score decoder, independently scheduled song or listening result.')


def run_vice(data, calls, output, vice, rom_data, report, oracle):
    profile = dict(loadAddress=LOAD_ADDRESS, endAddress=END_ADDRESS, initAddress=INIT_ADDRESS,
                   playAddress=PLAY_ADDRESS)
    program, labels, listing = cia.harness(profile, calls)
    output.mkdir()
    payload, host = output / 'payload.prg', output / 'harness.prg'
    payload.write_bytes(data[124:])
    host.write_bytes(program)
    (output / 'harness.listing').write_text(listing)
    monitor = output / 'commands.mon'
    # The pinned payload ends below $CC00; its banked workspace extends through $CE26.
    # Zeroing through $CFFF matches the callable initial RAM without modifying source bytes.
    commands = cia.monitor_commands(payload, host, profile, labels).replace(
        'fill $0002 $bfff $00', 'fill $0002 $cfff $00')
    monitor.write_text(commands)
    command = [str(vice), '-config', '/dev/null', '-directory', str(rom_data), '-pal', '+logcolorize',
               '-initbreak', 'ready', '-moncommands', str(monitor), '-monlog', '-monlogname',
               str(output / 'monitor.log'), '-limitcycles', str(4_000_000 + calls * 20000),
               '-warp', '+sound', '-sidenginemodel', 'resid6581', '-cia1model', '1', '-cia2model', '1']
    environment = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY'):
        environment.pop(key, None)
    for key in ('XDG_CONFIG_HOME', 'XDG_STATE_HOME'):
        environment[key] = str(output / key.lower())
        (Path(environment[key]) / 'vice').mkdir(parents=True)
    write_json(output / 'command.json', command)
    with (output / 'process.log').open('w') as process_log:
        subprocess.run(command, env=environment, stdout=process_log, stderr=subprocess.STDOUT,
                       timeout=60, check=True)
    parsed = cia.parse_trace((output / 'monitor.log').read_text(errors='replace'), profile, labels)
    verification = cia.verify_trace(parsed, oracle, calls, report)
    write_gzip(output / 'trace.json.gz', parsed)
    write_json(output / 'verification.json', verification)
    return verification, digest(program)


def study(source, output, calls, vice, rom_data):
    require(type(calls) is int and 1000 <= calls <= 1600, 'Choose 1000–1600 bounded play calls')
    data = source.read_bytes()
    header = admit_source(data)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh output directory')
    require(output.is_relative_to(ROOT / 'build'), 'Private study output must be under build/')
    for path in (source, output, vice, rom_data):
        require(not any(character in str(path) for character in ('"', '\n', '\r')), 'Unsafe monitor path')
    output.mkdir(parents=True)
    frozen = freeze_step(data)
    (output / 'frozen-pwm.sid').write_bytes(frozen)
    original_report, original_writes, snapshots = execute(data, calls, output / 'original')
    frozen_report, frozen_writes, _ = execute(frozen, calls, output / 'frozen')
    intervention, differences = verify_intervention(original_writes, frozen_writes)
    intervention['identicalPlayCallCycles'] = original_report['playCycles'] == frozen_report['playCycles']
    require(intervention['identicalPlayCallCycles'], 'Intervention changed callable play costs')
    pulse = verify_pulse_model(original_writes, snapshots)
    write_gzip(output / 'intervention-differences.json.gz', differences)
    original_vice, harness_sha = run_vice(data, calls, output / 'vice-original', vice, rom_data,
                                         original_report, original_writes)
    frozen_vice, _ = run_vice(frozen, calls, output / 'vice-frozen', vice, rom_data,
                             frozen_report, frozen_writes)
    result = dict(schemaVersion=1, sourceSha256=SOURCE_SHA256, workingFrozenSha256=digest(frozen),
                  header=header, calls=calls, pulseModel=pulse, intervention=intervention,
                  viceSha256=digest(vice.read_bytes()), harnessSha256=harness_sha,
                  initialTimerPeriodCycles=INITIAL_TIMER_PERIOD, steadyTimerPeriodCycles=0x4601,
                  steadyCallsPerSecond=PAL_CLOCK / 0x4601,
                  original=dict(initCycles=original_report['initCycles'],
                                maximumPlayCycles=original_report['maximumPlayCycles'],
                                matchedSourceWrites=original_vice['matchedSourceWrites'],
                                acknowledgedInterrupts=original_vice['acknowledgedInterrupts'],
                                maximumIntervalError=original_vice['cadence']['maximumIntervalError'],
                                maximumAccumulatedPhaseError=original_vice['cadence']['maximumAccumulatedPhaseError']),
                  frozen=dict(maximumPlayCycles=frozen_report['maximumPlayCycles'],
                              matchedSourceWrites=frozen_vice['matchedSourceWrites'],
                              acknowledgedInterrupts=frozen_vice['acknowledgedInterrupts'],
                              maximumIntervalError=frozen_vice['cadence']['maximumIntervalError'],
                              maximumAccumulatedPhaseError=frozen_vice['cadence']['maximumAccumulatedPhaseError']),
                  limitations='Bounded unchanged source and one-byte intervention under a controlled bank-aware CIA '
                  'IRQ host, not a full song, original-game/renderer startup, SID bus timing, instrument transfer, '
                  'PCM equivalence or musical acceptance. No generic source admission is expanded.')
    write_json(output / 'verification.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calls', type=int, default=1600)
    parser.add_argument('--vice', type=Path, default=ROOT / '.tools/vice-headless-3.9/build/src/x64sc')
    parser.add_argument('--data', type=Path, default=ROOT / '.tools/vice-headless-3.9/source/data')
    args = parser.parse_args()
    result = study(args.source.resolve(), args.output.resolve(), args.calls,
                   args.vice.resolve(), args.data.resolve())
    print(json.dumps(dict(verification=str(args.output / 'verification.json'), calls=result['calls'],
                          original=result['original'], frozen=result['frozen'],
                          intervention=result['intervention']), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error))
