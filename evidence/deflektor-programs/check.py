"""Check a named-state waveform model against pinned original routines and initialized calls."""

import argparse
from dataclasses import asdict, replace
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import BankedAuditMemory, audit_psid
from psid_profile import psid_profile
from verify_player import cpu_type, require
from model import Stage, WaveProgram, WaveState, initialize_wave, advance_wave, voice_writes


SOURCE_SHA = '606ad4cb19e29c060bb77a9b44253dee62d3d972724acb6cddf625fc2466d44d'
TOOLS = {
    'psid_profile.py': 'edc1109d1b393541a1df1c8d678923faab1d5240996c2eaee63db8691e9ea0ff',
    'psid_audit.py': '4446a19a325e625e59f100aac0b186478fb1633f65886b260db2ad3da11419a5',
    'sid_audit_host.py': 'ea1949d711126b5150225f0d68a3462dbbfe9fffe094e448f9b758889808b0ed',
    'verify_player.py': 'c69317c5d781c175ef0cef39a6e2713187b17e1de5b3f144ad69d49e6a271aab',
}
LEDGER_SHA = '7c1ccca95afc19175b4efc50674f8f1e23783b0dcad525d5955a9cf85523fa00'
FIELD_BINDINGS = [
    dict(offset=0, name='packedPulse', readerPc=0xc41f, targets=[0xc0ba, 0xc0bd],
         meaning='Low nibble is pulse update interval; unshifted high nibble is pulse-table base. Setup resets interval counter to low nibble minus one and pulse position to zero.'),
    dict(offset=1, name='initialPulseHigh', readerPc=0xc3e6, targets=[0xc098], meaning='Copies the high-byte PW shadow; does not clear its low byte.'),
    dict(offset=2, name='initialControl', readerPc=0xc3ec, targets=[0xc099], meaning='Copies base control; note setup ORs gate one, and enabled waveform initialization can replace it.'),
    dict(offset=3, name='attackDecay', readerPc=0xc3f2, targets=[0xc09a], meaning='Copies attack/decay register shadow.'),
    dict(offset=4, name='sustainRelease', readerPc=0xc3f8, targets=[0xc09b], meaning='Copies sustain/release register shadow.'),
    dict(offset=5, name='gateReleaseCountdown', readerPc=0xc401, targets=[0xc0b7], meaning='Body clears gate when incoming row countdown equals this byte.'),
    dict(offset=6, name='pulseLowStep', readerPc=0xc419, targets=[0xc0f3], meaning='Adds/subtracts only pulse low byte between high-byte table targets; no carry/borrow propagation to PW high in this branch.'),
    dict(offset=7, name='pitchProgramOffset', readerPc=0xc407, targets=[0xc0c6], meaning='Zero disables; nonzero selects delayed signed frequency-word steps from C9A5. This is separate from score-selected pitch tables.'),
    dict(offset=8, name='waveProgramOffset', readerPc=0xc40d, targets=[0xc0cc], meaning='Zero disables; nonzero selects timed waveform/control stages and header from C9C1/C9C0.'),
    dict(offset=9, name='resonanceProgramOffset', readerPc=0xc413, targets=[0xc0ff], meaning='Contextual tenth load lies after the nine-byte record stride. Nonzero selects timed D417 resonance high nibble, preserving routing low nibble.'),
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def extract(data):
    require(digest(data) == SOURCE_SHA, 'Source is not the pinned Deflektor archive')
    profile = psid_profile(data, profile='pal-banked', subtune=1, host_base=0x0400)
    ram = [0] * 65536
    ram[profile['loadAddress']:profile['endAddress']] = profile['payload']
    controls = ram[0xc9bd:0xc9c5]
    programs = {}
    descriptions = {}
    for offset in (5, 10, 15):
        header = ram[0xc9c0 + offset]
        packed = ram[0xc9c1 + offset:0xc9c1 + offset + (header & 7)]
        program = WaveProgram(bool(header & 128), tuple(Stage(controls[value & 7], value >> 4) for value in packed))
        programs[offset] = program
        descriptions[f'wave-{offset:02d}'] = dict(loop=program.loop, stages=[asdict(stage) for stage in program.stages],
            sourceEvidence=dict(offset=offset, headerAddress=0xc9c0 + offset, header=header,
                                stageAddress=0xc9c1 + offset, packedStages=packed,
                                controlTableAddress=0xc9bd, controlTable=controls))
    records = []
    for index in range(9):
        raw = ram[0xc007 + 9 * index:0xc011 + 9 * index]
        named = {field['name']: raw[field['offset']] for field in FIELD_BINDINGS}
        named.update(pulseInterval=raw[0] & 15, pulseTableBase=raw[0] & 240)
        records.append(dict(recordIndex=index, parameters=named,
                            sourceEvidence=dict(address=0xc007 + 9 * index, stride=9,
                                                recordBytes=raw[:9], trailingSelectorAddress=0xc010 + 9 * index,
                                                trailingSelector=raw[9])))
    lookup = dict(schemaVersion=1, sourceSha256=SOURCE_SHA, recordStride=9, fieldBindings=FIELD_BINDINGS,
                  records=records, wavePrograms=descriptions,
                  bodyPaths=[dict(name='gateRelease', entry=0xc529, exit=0xc53c),
                             dict(name='pulseTable', entry=0xc59a, exit=0xc640),
                             dict(name='delayedSignedPitch', entry=0xc640, exit=0xc6cf),
                             dict(name='waveform', entry=0xc6cf, exit=0xc726),
                             dict(name='scoreSelectedPitch', entry=0xc726, exit=0xc7c3),
                             dict(name='sharedResonance', entry=0xc7c3, exit=0xc80f)],
                  boundaries='Nine-byte mapping stride does not limit setup reads to nine bytes. Trailing selectors and shared table aliases are retained as contextual source facts. This schema models waveform stages only; other paths are source-bound lookups, not independent synthesis implementations.')
    return profile, ram, programs, lookup


def state(ram, voice):
    return WaveState(ram[0xc0d2 + voice], ram[0xc0cf + voice], ram[0xc099 + 7 * voice])


def execute_segment(profile, voice, offset, before, entry, stop):
    memory = BankedAuditMemory((0xd400,), 0x0400)
    memory.data[profile['loadAddress']:profile['endAddress']] = profile['payload']
    ram = memory.data
    ram[0xc08a], ram[0xc089], ram[0xc0cc + voice] = voice, 7 * voice, offset
    ram[0xc0d2 + voice], ram[0xc0cf + voice], ram[0xc099 + 7 * voice] = before.countdown, before.position, before.control
    cpu = cpu_type()(memory=memory, pc=entry)
    cpu.x, cpu.a, cpu.y, cpu.p = voice, 0x33, 0x44, 0x26
    memory.phase, memory.tick = 'play', 0
    pcs = []
    while cpu.pc != stop:
        require(cpu.processorCycles < 5000, 'Isolated waveform routine exceeded its bounded budget')
        pcs.append(cpu.pc)
        memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
        require(memory.instruction not in ('???', 'BRK', 'RTI'), 'Unsupported isolated instruction')
        memory.instruction_cycle = cpu.processorCycles
        cpu.step()
    require(cpu.sp == 0xff and not memory.writes, 'Wave routine unexpectedly uses the caller stack or SID stores')
    after = state(ram, voice)
    macro_cycles = cpu.processorCycles
    # The seven-register writer receives caller-supplied numeric context; it is not a pitch/PWM model.
    shadow = [0x34, 0x12, 0, 8, after.control, 6, 10]
    ram[0xc095 + 7 * voice:0xc09c + 7 * voice] = shadow
    ram[0xc0e7:0xc0ea] = [1, 1, 1]
    ram[0xc0e7 + voice] = 0
    ram[0xc094] = 0
    cpu.pc = 0xc1e5
    while cpu.pc != 0xc279:
        require(cpu.processorCycles < 6000, 'Isolated voice writer exceeded its bounded budget')
        pcs.append(cpu.pc)
        memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
        memory.instruction_cycle = cpu.processorCycles
        cpu.step()
    expected_writes = voice_writes(voice, frequency=0x1234, pulse_word=0x0800,
                                  control=after.control, attack_decay=6, sustain_release=10)
    require([(row['address'], row['value']) for row in memory.writes] == expected_writes,
            'Seven-register writer differs from its numeric inputs')
    return after, dict(executedPcs=pcs, macroCycles=macro_cycles, writes=memory.writes)


def isolated_cases(profile, programs):
    cases = []
    for offset, program in [*programs.items(), (0, None)]:
        positions = list(range(len(program.stages))) + [0x80, 0xff] if program else [0, 0xff]
        for voice, countdown, position, gate in itertools.product(range(3), (0, 1, 2, 255), positions, (0, 1)):
            before = WaveState(countdown, position, 0x40 | gate)
            expected = advance_wave(program, before)
            actual, execution = execute_segment(profile, voice, offset, before, 0xc6cf, 0xc726)
            require(actual == expected, f'Body waveform mismatch for offset{offset},voice{voice},{before}')
            cases.append(dict(kind='body', voiceIndex=voice, programOffset=offset, before=asdict(before),
                              expected=asdict(expected), actual=asdict(actual), **execution))
        for voice, control, position in itertools.product(range(3), (0, 0x41, 0x80, 0xff), (0, 7, 127, 255)):
            before = WaveState(255, position, control)
            expected = initialize_wave(program, before)
            actual, execution = execute_segment(profile, voice, offset, before, 0xc49e, 0xc4c8)
            require(actual == expected, 'Initial waveform mismatch')
            cases.append(dict(kind='initialize', voiceIndex=voice, programOffset=offset, before=asdict(before),
                              expected=asdict(expected), actual=asdict(actual), **execution))
    return cases


def observe_initialized(data, programs):
    observations, instructions, pending = [], [], {}
    writer_controls = {}

    def observe(cpu, memory):
        if memory.phase != 'play' or not 640 <= memory.tick <= 671:
            return
        ram = memory.data
        instructions.append(dict(call=memory.tick, instructionStartCycle=memory.instruction_cycle,
                                 pc=cpu.pc, opcode=ram[cpu.pc], a=cpu.a, x=cpu.x, y=cpu.y, p=cpu.p, sp=cpu.sp))
        voice = ram[0xc08a]
        if voice != 0 or ram[0xc0cc] != 5:
            return
        if cpu.pc in (0xc49e, 0xc6cf):
            kind = 'initialize' if cpu.pc == 0xc49e else 'body'
            before = state(ram, 0)
            expected = initialize_wave(programs[5], before) if kind == 'initialize' else advance_wave(programs[5], before)
            pending[kind] = dict(call=memory.tick, voiceIndex=0, kind=kind, entryPc=cpu.pc,
                                 entryCycle=memory.instruction_cycle, before=asdict(before),
                                 expected=asdict(expected), rowCountdown=ram[0xc0b1],
                                 pitchIndex=ram[0xc102], programOffset=5)
        if cpu.pc in (0xc4c8, 0xc726):
            kind = 'initialize' if cpu.pc == 0xc4c8 else 'body'
            item = pending.pop(kind, None)
            require(item is not None and item['call'] == memory.tick, 'Waveform boundary has no matched entry')
            actual = state(ram, 0)
            require(asdict(actual) == item['expected'], 'Initialized source waveform state differs from independent helper')
            observations.append(dict(**item, exitPc=cpu.pc, exitCycle=memory.instruction_cycle, actual=asdict(actual)))
            writer_controls[memory.tick] = actual.control

    report, writes = audit_psid(data, 672, profile='pal-banked', subtune=1, host_base=0x0400, observer=observe)
    require(not pending and observations, 'Initialized waveform proof has incomplete boundaries')
    controls = [row for row in writes if row['phase'] == 'play' and 640 <= row['tick'] <= 671 and row['address'] == 0xd404]
    require(all(row['value'] == writer_controls[row['tick']] for row in controls), 'Computed control differs from observed SID store')
    require(any(row['value'] == 0x17 for row in controls), 'Selected trace does not execute the coupled triangle stage')
    require(any(row['value'] == 0x80 for row in controls), 'Selected trace does not cover gate-clear noise release')
    return report, observations, instructions, writes, controls


def save(path, value, compressed=False):
    with path.open('xb') as raw:
        if compressed:
            with gzip.GzipFile(filename='', mode='wb', fileobj=raw, compresslevel=6, mtime=0) as output:
                for chunk in json.JSONEncoder(separators=(',', ':')).iterencode(value):
                    output.write(chunk.encode())
                output.write(b'\n')
        else:
            raw.write((json.dumps(value, indent=2) + '\n').encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sid', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.output.is_symlink(), 'Choose a fresh output directory')
    for name, pin in TOOLS.items():
        require(digest((ROOT / 'scripts' / name).read_bytes()) == pin, f'Dependency changed: {name}')
    data = args.sid.read_bytes()
    profile, source, programs, lookup = extract(data)
    cases = isolated_cases(profile, programs)
    report, observations, instructions, writes, controls = observe_initialized(data, programs)
    ledger = ROOT / 'evidence/deflektor-form/full40000/writes.json.gz'
    require(digest(ledger.read_bytes()) == LEDGER_SHA, 'Canonical form ledger pin differs')
    expected = [row for row in read_json(ledger) if row['phase'] == 'init' or row['tick'] < 672]
    require(writes == expected, 'Initialized observation changed the complete ordered 672-call SID ledger')
    program = programs[5]
    changed = replace(program, stages=program.stages[:2] + (replace(program.stages[2], control_bits=0x10),) + program.stages[3:])
    differences = []
    for item in observations:
        before = WaveState(**item['before'])
        mutant = initialize_wave(changed, before) if item['kind'] == 'initialize' else advance_wave(changed, before)
        if asdict(mutant) != item['actual']:
            differences.append(dict(call=item['call'], original=item['actual'], edited=asdict(mutant)))
    require([item['call'] for item in differences] == [644, 664], 'Control-stage mutation lacks its two predicted actual divergences')
    all_events = read_json(ROOT / 'evidence/deflektor-form/full40000/events.json.gz')
    selected, onsets = [None] * 3, []
    for event in all_events:
        if event['kind'] == 'instrumentSelection':
            selected[event['voiceIndex']] = event['recordIndex']
        if event['kind'] == 'noteSetup' and selected[event['voiceIndex']] == 0:
            onsets.append(dict(call=event['call'], voiceIndex=event['voiceIndex'], pitchIndex=event['pitchIndex']))
    lookup['candidate'] = dict(recordIndex=0, noteOnsets=len(onsets), onsets=onsets,
        context='Recurring zero-sustain noise/triangle/coupled-triangle/noise program; a register-based percussive/metallic candidate only, not an identified cowbell or listening verdict.')
    verification = dict(schemaVersion=1, sourceSha256=SOURCE_SHA, selectedProfile='pal-banked', subtune=1, hostBase=0x0400,
        modelSha256=digest(Path(__file__).with_name('model.py').read_bytes()), checkerSha256=digest(Path(__file__).read_bytes()), dependencies=TOOLS,
        isolatedCases=len(cases), isolatedMacroStateMatches=len(cases), isolatedWriterStores=sum(len(case['writes']) for case in cases),
        syntheticBasis='Original source segments C49E..beforeC4C8 and C6CF..beforeC726 under explicitly seeded named state; selected source programs5/10/15 and disabled0, all three voice offsets, gates, zero/one/two/255 countdowns and active/stopped positions. Writer context is explicitly supplied, not a pitch/PWM model.',
        observedMacroStatesMatched=len(observations), observedControlStoresMatched=len(controls), initializedPlayCalls=672,
        completeInitializedLedgerMatches=len(writes), canonicalLedgerSha256=LEDGER_SHA,
        candidateWindowInclusive=[640, 671], candidateOnsets=len(onsets), mutationDifferences=differences,
        limits=['Only the waveform initializer/body and seven-register writer are independently computed. Row scheduling, gate-release eligibility, pitch, pulse and resonance trajectories remain caller/source context.',
                'Synthetic cases compare named waveform state and ordered writer values, not complete CPU flags or every unrelated RAM field. Active body lookups beyond supplied stages and arbitrary unselected table offsets are unsupported; initialization replaces prior position regardless of its old program.',
                'Initialized observations share the guarded CPU implementation with the canonical ledger. No additional VICE, sound synthesis, reference audio, listening or cowbell identification is claimed.',
                'Control17 engages triangle with sync+ring and depends on the preceding oscillator; its numeric agreement does not establish acoustic similarity across contexts.'])
    args.output.mkdir(parents=True)
    files = [('lookup.json', lookup, False), ('verification.json', verification, False), ('audit672.json', report, False),
             ('isolated-cases.json.gz', cases, True), ('observed-wave.json.gz', observations, True),
             ('instructions640-671.json.gz', instructions, True), ('writes672.json.gz', writes, True)]
    for name, value, compressed in files:
        save(args.output / name, value, compressed)
    save(args.output / 'receipt.json', dict(schemaVersion=1, sourceSha256=SOURCE_SHA,
        sourceUrl='https://www.hvsc.de/download/C64Music/MUSICIANS/D/Daglish_Ben/Deflektor.sid', sourceBytes=len(data),
        modelSha256=verification['modelSha256'], checkerSha256=verification['checkerSha256'], dependencies=TOOLS,
        canonicalEvidenceSha256={str(ledger.relative_to(ROOT)):LEDGER_SHA,
            'evidence/deflektor-form/full40000/events.json.gz':digest((ROOT/'evidence/deflektor-form/full40000/events.json.gz').read_bytes())},
        sourcePayloadExported=False, fullRamExported=False,
        files=[dict(path=name, sha256=digest((args.output / name).read_bytes()), bytes=(args.output / name).stat().st_size)
               for name, _, _ in files]))
    print(json.dumps({name: verification[name] for name in ('isolatedCases', 'isolatedWriterStores',
        'observedMacroStatesMatched', 'observedControlStoresMatched', 'completeInitializedLedgerMatches', 'mutationDifferences')}))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
