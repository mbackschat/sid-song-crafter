"""Explain the pinned Gyruss subtune-1 sequence using bounded NTSC calls."""

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import BankedAuditMemory
from sid_intake import inspect_sid
from verify_player import cpu_type, require


SOURCE_SHA256 = '06a7cf7ece3d3b69b0ec45c1007c4c0764933b4aabf60d4923f0c07e18f85d04'
NTSC_CLOCK = 1022727.14
FRAME_CYCLES = 263 * 65
CALL_RATE = NTSC_CLOCK / FRAME_CYCLES
NOTE_FIELDS = ('call', 'pitchStartCall', 'voice', 'subtune', 'frequencyWord', 'durationQuanta', 'quantumCalls', 'control', 'pulseLowBefore')


class GyrussMemory(BankedAuditMemory):
    def __init__(self):
        super().__init__((0xd400,))
        self.instruction_pc = None

    def __setitem__(self, address, value):
        super().__setitem__(address, value)
        if 0xd400 <= address <= 0xd41f:
            self.writes[-1]['instructionPc'] = self.instruction_pc


def run_driver(data, calls):
    """Execute only this unchanged source; retain derived events, not program bytes.

    This is a hash-pinned diagnostic, not admission to the PAL production auditor.
    RAM/SID-store guards come from its banked memory, while call budgets and pitch
    conversion explicitly use NTSC. Callable CPU execution does not model IRQ,
    badline, bus-cycle, envelope or audio behavior. Renderer agreement is separate.
    """
    require(hashlib.sha256(data).hexdigest() == SOURCE_SHA256, 'Expected the pinned Gyruss source; no substitute or changed header is admitted')
    require(type(calls) is int and 1 <= calls <= 3000, 'Select 1..3000 bounded calls')
    header = inspect_sid(data, subtune=1)
    require((header['clockDeclaration'], header['sidModelDeclaration'], header['selectedTimingDeclaration']) == ('NTSC', 'MOS6581', 'VBI'), 'Pinned source declarations changed')
    memory = GyrussMemory()
    load, end = header['loadAddress'], header['endAddressExclusive']
    memory.data[load:end] = data[header['dataOffset'] + 2:]
    cpu = cpu_type()(memory=memory, pc=header['initAddress'])
    cpu.a, cpu.x, cpu.y = 0, 0, 0
    cpu.p = cpu.UNUSED | cpu.INTERRUPT | cpu.ZERO
    notes, initializations, ends, pwm, sweep, articulations = [], [], [], [], [], []
    last_note_call = {}
    states, prefixes = [], []

    def observe():
        pc = cpu.pc
        if pc == 0xaaa3:
            initializations.append({'phase': memory.phase, 'call': memory.tick, 'subtune': cpu.a + 1})
        if memory.phase != 'play':
            return
        if pc == 0xabc9 and cpu.a == 0x80:
            ends.append({'call': memory.tick, 'voice': cpu.x // 2 + 1, 'subtune': memory.data[0x97] + 1})
        if pc == 0xac42:
            channel = cpu.x
            notes.append({'call': memory.tick, 'pitchStartCall': memory.tick + 1, 'voice': channel // 2 + 1,
                'subtune': memory.data[0x97] + 1, 'frequencyWord': memory.data[0x99 + channel] | memory.data[0x9a + channel] << 8,
                'durationQuanta': cpu.a, 'quantumCalls': 5, 'control': memory.data[0xab + channel],
                'pulseLowBefore': memory.data[0x9f + channel]})
            last_note_call[channel] = memory.tick
        if pc == 0xac50:
            channel = cpu.x
            articulations.append({'call': memory.tick, 'voice': channel // 2 + 1, 'subtune': memory.data[0x97] + 1,
                'frequencyWord': memory.data[0x99 + channel] | memory.data[0x9a + channel] << 8,
                'remainingQuanta': memory.data[0xa5 + channel], 'scoreEvent': last_note_call.get(channel) == memory.tick})
        if pc == 0xab86:
            channel = cpu.x
            pwm.append({'call': memory.tick, 'voice': channel // 2 + 1,
                'widthBefore': memory.data[0x9f + channel] | memory.data[0xa0 + channel] << 8,
                'subtractOperand': memory.data[pc + 1], 'carryBefore': bool(cpu.p & cpu.CARRY)})
        if pc == 0xaddd:
            sweep.append({'call': memory.tick,
                'frequencyBefore': memory.data[0xb3] | memory.data[0xb0] << 8,
                'subtractWord': memory.data[0xb4] | memory.data[0xb1] << 8,
                'thresholdWord': memory.data[0xb5] | memory.data[0xb2] << 8})

    def call(address, budget):
        cpu.stPushWord(0x01ff)
        cpu.pc = address
        start = cpu.processorCycles
        while cpu.pc != 0x0200:
            require(cpu.processorCycles - start < budget, 'Driver exceeds the declared call budget')
            memory.instruction_pc = cpu.pc
            memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
            require(memory.instruction not in ('???', 'BRK', 'RTI'), f'Unsupported opcode at ${cpu.pc:04x}')
            memory.instruction_cycle = cpu.processorCycles - start
            observe()
            cpu.step()
        require(cpu.sp == 0xff, 'Driver did not restore the call stack')
        used = cpu.processorCycles - start
        require(used <= budget, 'Driver exceeds the declared call budget')
        return used

    init_cycles = call(header['initAddress'], 1000000)
    memory.phase = 'play'
    maximum = 0
    for tick in range(calls):
        memory.tick = tick
        before = bytes(memory.data[0xd400:0xd419])
        first_write = len(memory.writes)
        maximum = max(maximum, call(header['playAddress'], FRAME_CYCLES))
        state = bytearray(before)
        observed = {state.hex()}
        for write in memory.writes[first_write:]:
            if write['address'] <= 0xd418:
                state[write['address'] - 0xd400] = write['value']
            observed.add(state.hex())
        states.append(bytes(memory.data[0xd400:0xd419]).hex())
        prefixes.append(observed)
    report = {'sourceSha256': SOURCE_SHA256, 'clockDeclaration': 'NTSC', 'sidModelDeclaration': 'MOS6581',
        'selectedSubtune': 1, 'clockHz': NTSC_CLOCK, 'callRateHz': CALL_RATE, 'frameCycleBudget': FRAME_CYCLES,
        'playCalls': calls, 'initCycles': init_cycles, 'maximumPlayCycles': maximum,
        'initWriteCount': sum(row['phase'] == 'init' for row in memory.writes),
        'playWriteCount': sum(row['phase'] == 'play' for row in memory.writes),
        'classification': 'Hash-pinned source-specific NTSC callable diagnostic; not a production-auditor pass',
        'entryState': 'Bank $36; init A=0, X/Y=0, P=$26; retain CPU registers between callable play entries; synthetic return $0200',
        'clockBasis': 'MOS6567 R8 NTSC: 263 lines × 65 cycles, 1022727.14 Hz; distinct from renderer mix-chunk length',
        'limitations': 'No IRQ/VIC scheduling, SID reads, synthesis, envelope state, bus timestamps, VICE verification, in-game lifecycle or listening judgment. Sound-register snapshots are cross-checked separately; no source bytes, memory image or disassembly are exported.'}
    return {'report': report, 'states': states, 'prefixes': prefixes, 'writes': memory.writes,
        'noteEvents': notes, 'initializations': initializations, 'scoreEnds': ends, 'pwm': pwm, 'sweep': sweep, 'articulations': articulations}


def compare_snapshots(run, rows):
    """Match snapshots to whole or intermediate calls within two NTSC frames.

    render-sid samples SID state after mix chunks, not necessarily play returns.
    Retaining ordered store prefixes prevents calling a mid-write capture a new
    instrument or pitch; the two-call tolerance covers chunk/timer quantization.
    """
    require(len(rows) > 0, 'Renderer snapshot capture must not be empty')
    final_count, prefix_count, unmatched = 0, 0, []
    previous_time = -1
    for index, row in enumerate(rows):
        timestamp = int(row['time_ms'])
        require(timestamp > previous_time, 'Renderer snapshot times must be nonnegative and strictly increasing')
        previous_time = timestamp
        registers = bytes.fromhex(row['registers_hex'])
        require(len(registers) >= 25, 'Renderer snapshot must retain all 25 sound registers')
        expected = math.floor(timestamp * CALL_RATE / 1000) - 1
        target = registers[:25].hex()
        candidates = range(max(0, expected - 2), min(len(run['states']), expected + 3))
        if any(run['states'][call] == target for call in candidates):
            final_count += 1
        elif any(target in run['prefixes'][call] for call in candidates):
            prefix_count += 1
        else:
            unmatched.append({'row': index, 'timeMs': int(row['time_ms']), 'expectedCall': expected, 'soundRegistersHex': target})
    return {'snapshots': len(rows), 'callEndMatches': final_count, 'orderedPrefixMatches': prefix_count,
        'timeToleranceCalls': 2, 'comparedOffsets': 'SID sound controls $00–$18', 'unmatched': unmatched,
        'limits': 'State/prefix agreement within a bounded time window; not ordered renderer bus-write agreement or exact interrupt timing.'}


def summarize(run):
    states = [bytes.fromhex(state) for state in run['states']]
    changes = []
    previous = None
    for call, state in enumerate(states):
        configuration = tuple(tuple(state[voice * 7 + 4:voice * 7 + 7]) for voice in range(3)) + (tuple(state[21:25]),)
        if configuration != previous:
            changes.append({'call': call, 'secondsFromFirstCall': call / CALL_RATE,
                'voices': [{'voice': voice + 1, 'control': state[voice * 7 + 4],
                    'adsr': state[voice * 7 + 5:voice * 7 + 7].hex()} for voice in range(3)],
                'filterAndVolumeHex': state[21:25].hex()})
        previous = configuration
    movements = Counter(row['widthBefore'] for row in run['pwm'])
    return {'initializations': run['initializations'], 'scoreEndEvents': run['scoreEnds'], 'configurationChanges': changes,
        'scoreClock': {'quantumCalls': 5, 'quantumSeconds': 5 / CALL_RATE},
        'pulseProgram': {'updatesObserved': len(run['pwm']), 'firstUpdates': run['pwm'][:9],
            'subtractOperands': sorted(set(row['subtractOperand'] for row in run['pwm'])),
            'carryAlwaysSetBeforeSubtract': all(row['carryBefore'] for row in run['pwm']),
            'minimumWidthBefore': min(movements) if movements else None, 'maximumWidthBefore': max(movements) if movements else None,
            'basis': 'Executed subtraction at $AB86; all observed carry flags set. Score consumption at $AC44/$AC46 resets only the width high byte to $04, retaining the prior low byte. No autonomous triangle PWM cycle: the note schedule resets each descending sweep.'},
        'openingPulsePitchEffect': {'callsObserved': len(run['sweep']), 'firstCalls': run['sweep'][:12],
            'lastCall': run['sweep'][-1] if run['sweep'] else None,
            'basis': 'Executed voice-3 effect at $ADDD–$AE32 subtracts a 16-bit evolving step, writes frequency, resets state to $8000 after crossing its rising threshold, and raises the threshold by $80 at each reset until its high byte reaches $28. The underflowing result is written before state reset. $AD11 restores tonal voice-3 registers and volume 8.'},
        'bassArticulation': {'events': run['articulations'],
            'basis': 'For voice 2 in mode 3, the nonexpired duration path $ABBE jumps to $AC50: zero frequency, control zero, then gated waveform, every five-call score quantum. The stored D3/A2 alternation lasts ten calls per pitch, but repeated envelope starts create D-D-A-A attacks. This is a programmed rhythmic pulse rather than independent drum-voice allocation.'},
        'sourceSequenceBasis': 'At score command $80, $ABD0–$ABE1 internally calls init: zero-based mode 0 selects mode 3, modes >=3 select mode 6. $AAC7–$AAE4 explicitly installs voices 1/2 noise and zero-sustain ADSR for mode 6. Mode 6 retains their noise-score patterns but replaces voice-3 score consumption with a five-call alternating low-frequency program at $ABA2–$ABA7. This classifies source behavior without identifying its in-game purpose.',
        'noteEvents': run['noteEvents']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sid', type=Path)
    parser.add_argument('--run', type=Path, required=True, help='Completed comparison run.json owning the NTSC gyruss1 snapshots')
    parser.add_argument('--calls', type=int, default=2940)
    parser.add_argument('--output', type=Path, required=True, help='New ignored output directory')
    args = parser.parse_args()
    require(not args.output.exists(), 'Choose a new output directory')
    run_receipt = json.loads(args.run.read_text())
    snapshots_path = Path(run_receipt['deliverables']['gyruss1'] + '.registers.tsv')
    rows = list(csv.DictReader(snapshots_path.open(), delimiter='\t'))
    run = run_driver(args.sid.read_bytes(), args.calls)
    compared = compare_snapshots(run, rows)
    require(not compared['unmatched'], 'NTSC renderer snapshots disagree with the diagnostic; no verified output is written')
    result = {'schemaVersion': 1, 'execution': run['report'], 'mechanisms': summarize(run), 'rendererCrossCheck': compared,
        'sourcePath': str(args.sid), 'snapshotPath': str(snapshots_path),
        'snapshotSha256': hashlib.sha256(snapshots_path.read_bytes()).hexdigest(),
        'analyzerSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencySha256': {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in
            ('scripts/psid_audit.py', 'scripts/sid_intake.py', 'scripts/verify_player.py')}}
    args.output.mkdir(parents=True)
    (args.output / 'analysis.json').write_text(json.dumps(result, indent=2) + '\n')
    (args.output / 'writes.json').write_text(json.dumps(run['writes'], separators=(',', ':')) + '\n')
    with (args.output / 'notes.tsv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=NOTE_FIELDS, delimiter='\t')
        writer.writeheader()
        writer.writerows(run['noteEvents'])
    with (args.output / 'states.tsv').open('w', newline='') as stream:
        writer = csv.writer(stream, delimiter='\t')
        writer.writerow(('call', 'seconds_from_first_call', 'sound_registers_hex'))
        writer.writerows((call, f'{call / CALL_RATE:.9f}', state) for call, state in enumerate(run['states']))
    print(f"Matched {compared['snapshots']} NTSC snapshots; {len(run['noteEvents'])} score events; {args.output}")


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f'Gyruss diagnostic failed: {error}')
