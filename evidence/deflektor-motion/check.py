"""Check independently computed motion against bounded source segments and retained contexts."""

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, replace
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import BankedAuditMemory
from psid_profile import psid_profile
from verify_player import cpu_type, require
from model import (PulseProgram, PulseState, PitchState, ResonanceState,
                   advance_pwm, initialize_pitch, advance_pitch,
                   initialize_resonance, advance_resonance)

SOURCE_SHA = '606ad4cb19e29c060bb77a9b44253dee62d3d972724acb6cddf625fc2466d44d'
PINS = {'states.json.gz': '3b5fc9904cdb384b2b2e214ba9cf709827e205b1be2d1270833ece542f518891',
        'events.json.gz': '776c2aaa1effe25b1a70dc53630297b2d90961534db8f5febf4a232d59b4748a',
        'writes.json.gz': '7c1ccca95afc19175b4efc50674f8f1e23783b0dcad525d5955a9cf85523fa00'}
INITIAL_SHA = 'd64b226588ada0b67b4408c7d6f000037408193dade2f08665ef8cffc1cd595d'
TOOLS = {'psid_profile.py': 'c2c696db133ed024840cfa5edbc76e3a07ef1f30345cc1820c978a51a73c816d',
         'psid_audit.py': 'eeea11cdbb5159745f36802526ee2f2986d12fe19ce47b3609fedcf15f47e1bd',
         'sid_audit_host.py': 'ea1949d711126b5150225f0d68a3462dbbfe9fffe094e448f9b758889808b0ed',
         'verify_player.py': 'c69317c5d781c175ef0cef39a6e2713187b17e1de5b3f144ad69d49e6a271aab'}
SEGMENTS = {'pwm': (0xc59a, 0xc640), 'pitch': (0xc640, 0xc6cf),
            'pitchInit': (0xc48d, 0xc49e), 'resonance': (0xc7c3, 0xc80f),
            'resonanceInit': (0xc4c8, 0xc4f0)}
FIELDS = {'pwm': {'interval': 0xc0ba, 'table_base': 0xc0bd, 'low_step': 0xc0f3,
                  'elapsed': 0xc0f0, 'position': 0xc0f6},
          'pitch': {'selector': 0xc0c6, 'wait': 0xc0c3, 'position': 0xc0c9},
          'resonance': {'selector': 0xc0ff, 'countdown': 0xc0fc, 'position': 0xc0f9}}
READS = {0xc5b4: 0xc98d, 0xc5e7: 0xc98d, 0xc665: 0xc9a5,
         0xc493: 0xc9a5, 0xc7d7: 0xca12, 0xc7f7: 0xca11,
         0xc801: 0xca11, 0xc4ce: 0xca12}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def original_segment(profile, voice, kind, before):
    memory = BankedAuditMemory((0xd400,), 0x0400)
    memory.data[profile['loadAddress']:profile['endAddress']] = profile['payload']
    ram = memory.data
    family = kind.replace('Init', '')
    for name, address in FIELDS[family].items():
        ram[address + voice] = before[name]
    if family == 'resonance':
        ram[0xc0ac] = before['shared_shadow']
    else:
        offset = 2 if family == 'pwm' else 0
        ram[0xc095 + 7 * voice + offset] = before['word'] & 255
        ram[0xc096 + 7 * voice + offset] = before['word'] >> 8
    ram[0xc089], ram[0xc08a] = 7 * voice, voice
    entry, stop = SEGMENTS[kind]
    cpu = cpu_type()(memory=memory, pc=entry)
    cpu.x, cpu.p = voice, 0x26
    reads, instructions = [], []
    while cpu.pc != stop:
        require(cpu.processorCycles < 6000, 'Isolated segment exceeds bounded budget')
        memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
        require(memory.instruction not in ('???', 'BRK', 'RTI'), 'Unsupported instruction')
        memory.instruction_cycle = cpu.processorCycles
        instructions.append(dict(pc=cpu.pc, opcode=ram[cpu.pc], a=cpu.a, x=cpu.x, y=cpu.y,
                                 p=cpu.p, sp=cpu.sp, instructionStartCycle=cpu.processorCycles))
        if cpu.pc in READS:
            address = READS[cpu.pc] + cpu.y
            reads.append(dict(pc=cpu.pc, address=address, value=ram[address], index=cpu.y))
        cpu.step()
    require(cpu.sp == 255 and not memory.writes, 'Unexpected SID store or stack imbalance')
    after = {name: ram[address + voice] for name, address in FIELDS[family].items()}
    if family == 'resonance':
        after['shared_shadow'] = ram[0xc0ac]
    else:
        after['word'] = ram[0xc095 + 7 * voice + offset] | ram[0xc096 + 7 * voice + offset] << 8
    return after, dict(tableReads=reads, instructions=instructions, cycles=cpu.processorCycles)


def prediction(kind, before, motion, resonance):
    family = kind.replace('Init', '')
    result = dict(before)
    if family == 'pwm':
        program = PulseProgram(*(before[key] for key in ('interval', 'table_base', 'low_step')))
        state = PulseState(*(before[key] for key in ('elapsed', 'position', 'word')))
        result.update(asdict(advance_pwm(program, state, motion)))
    elif family == 'pitch':
        state = PitchState(*(before[key] for key in ('wait', 'position', 'word')))
        function = initialize_pitch if kind.endswith('Init') else advance_pitch
        result.update(asdict(function(before['selector'], state, motion)))
    else:
        state = ResonanceState(before['countdown'], before['position'])
        function = initialize_resonance if kind.endswith('Init') else advance_resonance
        state, shadow = function(before['selector'], state, resonance, before['shared_shadow'])
        result.update(asdict(state), shared_shadow=shadow)
    return result


def isolated_cases(profile, motion, resonance):
    cases = []

    def add(voice, kind, before):
        expected = prediction(kind, before, motion, resonance)
        actual, execution = original_segment(profile, voice, kind, before)
        require(actual == expected, f'Isolated {kind} differs: {before}, {actual}, {expected}')
        cases.append(dict(kind=kind, voiceIndex=voice, before=before, predicted=expected,
                          actual=actual, **execution))

    for voice in range(3):
        for interval, base, step in ((12, 0, 21), (3, 0, 85), (4, 32, 63)):
            positions = (0, 1, 2, 3, 128, 129, 130, 131) if base == 0 else (0, 1, 128, 129)
            for elapsed, position, value in itertools.product((0, interval - 1, 255), positions,
                                                             (0, 65535, 0x01fc, 0x08fc)):
                add(voice, 'pwm', dict(interval=interval, table_base=base, low_step=step,
                                       elapsed=elapsed, position=position, word=value))
        for wait, position, value in itertools.product((0, 1, 127, 128, 129, 255),
                                                       (0, 1, 4, 7, 128, 129, 132, 135, 136, 255),
                                                       (0, 255, 65535, 0x3426)):
            add(voice, 'pitch', dict(selector=8, wait=wait, position=position, word=value))
        for selector in (0, 255):
            for position in (0, 1, 127, 128, 255):
                add(voice, 'pitch', dict(selector=selector, wait=0, position=position, word=65535))
        for selector, countdown, position, low in itertools.product((0, 3, 12, 36), (0, 1, 2, 255),
                                                                    (0, 1, 2, 128, 255), (0, 5, 15)):
            add(voice, 'resonance', dict(selector=selector, countdown=countdown,
                                         position=position, shared_shadow=0xa0 | low))
        for selector, position, value in itertools.product((0, 8, 255), (0, 128, 255), (0, 65535)):
            add(voice, 'pitchInit', dict(selector=selector, wait=255, position=position, word=value))
        for selector, countdown, position, low in itertools.product((0, 3, 12, 36), (0, 255),
                                                                    (0, 255), (0, 5, 15)):
            add(voice, 'resonanceInit', dict(selector=selector, countdown=countdown,
                                             position=position, shared_shadow=0xa0 | low))
    return cases


def pulse_state(voice):
    return PulseState(voice['driverC0F0'], voice['driverC0F6'],
                      voice['sidShadow'][2] | voice['sidShadow'][3] << 8)


def pulse_program(voice):
    return PulseProgram(voice['driverC0BA'], voice['driverC0BD'], voice['driverC0F3'])


def pitch_state(voice):
    return PitchState(voice['driverC0C3'], voice['driverC0C9'],
                      voice['sidShadow'][0] | voice['sidShadow'][1] << 8)


def resonance_state(voice):
    return ResonanceState(voice['driverC0FC'], voice['driverC0F9'])


def contexts(states, events, writes, initial, motion, resonance):
    rows = {(event['call'], event['voiceIndex']): event for event in events if event['kind'] == 'rowReload'}
    patches = {(event['call'], event['voiceIndex']): event for event in events if event['kind'] == 'instrumentSelection'}
    require(not any(event['kind'] == 'patternRead' and event.get('context') == 'token'
                    and event.get('sourceValue') in (0xa1, 0xa2)
                    for event in events), 'Unexpected shared routing command')
    by_call = defaultdict(list)
    for record in writes:
        if record['phase'] == 'play':
            by_call[record['tick']].append(record)
    comparisons, mutations = [], defaultdict(list)
    counts = Counter()
    local = [resonance_state(voice) for voice in initial['voices']]
    shadow = initial['globals']['filterRouting']
    for call in range(8481):
        previous = initial if call == 0 else states[call - 1]
        current = states[call]
        actions, eligible = [], []
        for voice in range(3):
            a, b = previous['voices'][voice], current['voices'][voice]
            body = (current['returnKind'] == 'writer' and (call, voice) not in rows
                    and not a['restCountdown'] and a['rowCountdown'] > 1)
            if body:
                eligible.append(voice)
                program, before = pulse_program(a), pulse_state(a)
                predicted = advance_pwm(program, before, motion)
                require(predicted == pulse_state(b), f'PWM context differs at {call}/{voice}')
                counts['pwmContexts'] += 1
                if program.interval:
                    counts['enabledPwmContexts'] += 1
                    pair = [item['value'] for item in by_call[call]
                            if item['address'] in (0xd402 + 7 * voice, 0xd403 + 7 * voice)]
                    require(pair == [predicted.word & 255, predicted.word >> 8], 'PWM stores differ')
                    altered = advance_pwm(replace(program, low_step=(program.low_step + 1) & 255), before, motion)
                    if altered != predicted:
                        mutations['pulseStep'].append(dict(call=call, voiceIndex=voice,
                                                           expected=asdict(predicted), altered=asdict(altered)))
                comparisons.append(dict(call=call, voiceIndex=voice, kind='pwm', program=asdict(program),
                                        before=asdict(before), predicted=asdict(predicted), actual=asdict(pulse_state(b))))
                selector, before = a['driverC0C6'], pitch_state(a)
                predicted = advance_pitch(selector, before, motion)
                if selector:
                    require(selector == 8 and a['driverC0D5'] == b['driverC0D5'] == 0,
                            'Later score pitch could hide delayed-pitch output')
                    require(a['driverC0D8'] == 0, 'Score glide could alter incoming frequency')
                    require(predicted == pitch_state(b), f'Pitch context differs at {call}/{voice}')
                    counts['enabledPitchContexts'] += 1
                    pair = [item['value'] for item in by_call[call]
                            if item['address'] in (0xd400 + 7 * voice, 0xd401 + 7 * voice)]
                    require(pair == [predicted.word & 255, predicted.word >> 8], 'Pitch stores differ')
                    altered_table = dict(motion)
                    altered_table[33] = 99
                    altered = advance_pitch(selector, before, altered_table)
                    if altered != predicted:
                        mutations['pitchStep'].append(dict(call=call, voiceIndex=voice,
                                                          expected=asdict(predicted), altered=asdict(altered)))
                    comparisons.append(dict(call=call, voiceIndex=voice, kind='pitch', selector=selector,
                                            before=asdict(before), predicted=asdict(predicted), actual=asdict(pitch_state(b))))
                else:
                    require(predicted.wait == b['driverC0C3'] and predicted.position == b['driverC0C9'],
                            'Disabled pitch state unexpectedly changes')
                    counts['disabledPitchContexts'] += 1
            patch, row = patches.get((call, voice)), rows.get((call, voice))
            before_local = local[voice]
            if patch:
                local[voice] = replace(local[voice], position=0)
                counts['patchResets'] += 1
            selector = b['driverC0FF']
            if row and row['rowKind'] == 'note':
                action = 'initialize'
                counts['resonanceNoteInitializers'] += 1
            elif body:
                action = 'advance'
                counts['resonanceBodyContexts'] += 1
            else:
                action = 'hold'
            actions.append((voice, selector, action, local[voice]))
            incoming_shadow = shadow
            if action != 'hold':
                function = initialize_resonance if action == 'initialize' else advance_resonance
                local[voice], shadow = function(selector, local[voice], resonance, shadow)
            require(local[voice] == resonance_state(b), f'Resonance state differs at {call}/{voice}')
            comparisons.append(dict(call=call, voiceIndex=voice, kind='resonance', action=action,
                                    patchReset=bool(patch), selector=selector, before=asdict(before_local),
                                    incomingShared=incoming_shadow, predicted=asdict(local[voice]),
                                    actual=asdict(resonance_state(b)), outgoingShared=shadow))
        require(shadow == current['globals']['filterRouting'], f'Shared resonance differs at {call}')
        if current['returnKind'] == 'writer':
            stores = [item['value'] for item in by_call[call] if item['address'] == 0xd417]
            require(stores == [shadow], 'Shared resonance writer differs')
            counts['sharedWriterChecks'] += 1
        wrong_shadow = previous['globals']['filterRouting']
        for voice, selector, action, state in reversed(actions):
            if action != 'hold':
                function = initialize_resonance if action == 'initialize' else advance_resonance
                _, wrong_shadow = function(selector, state, resonance, wrong_shadow)
        if wrong_shadow != shadow:
            mutations['reverseVoiceOrder'].append(dict(call=call, expected=shadow, altered=wrong_shadow))
    require(all(len(mutations[kind]) >= 2 for kind in ('pulseStep', 'pitchStep', 'reverseVoiceOrder')),
            'Mutation controls need two independent contexts each')
    return comparisons, dict(counts), dict(mutations)


def save(path, value, compressed=False):
    raw = (json.dumps(value, separators=(',', ':')) + '\n').encode() if compressed else (json.dumps(value, indent=2) + '\n').encode()
    stored = gzip.compress(raw, compresslevel=6, mtime=0) if compressed else raw
    with path.open('xb') as stream:
        stream.write(stored)
    return dict(path=path.name, sha256=digest(stored), bytes=len(stored), originalSha256=digest(raw), originalBytes=len(raw))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sid', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.output.is_symlink(), 'Choose a fresh output directory')
    data = args.sid.read_bytes()
    require(digest(data) == SOURCE_SHA, 'Source is not pinned Deflektor')
    for name, pin in TOOLS.items():
        require(digest((ROOT / 'scripts' / name).read_bytes()) == pin, f'Dependency changed: {name}')
    profile = psid_profile(data, profile='pal-banked', subtune=1, host_base=0x0400)
    inputs = {}
    base = ROOT / 'evidence/deflektor-form/full40000'
    for name, pin in PINS.items():
        raw = (base / name).read_bytes()
        require(digest(raw) == pin, f'Retained input differs: {name}')
        inputs[name] = json.loads(gzip.decompress(raw))
    initial_raw = (base / 'initial-state.json').read_bytes()
    require(digest(initial_raw) == INITIAL_SHA, 'Retained initial state differs')
    initial = json.loads(initial_raw)
    ram = [0] * 65536
    ram[profile['loadAddress']:profile['endAddress']] = profile['payload']
    motion = {index: ram[0xc98d + index] for index in range(280)}
    resonance = {index: ram[0xca11 + index] for index in range(257)}
    cases = isolated_cases(profile, motion, resonance)
    compared, counts, mutations = contexts(inputs['states.json.gz'], inputs['events.json.gz'],
                                           inputs['writes.json.gz'], initial, motion, resonance)
    args.output.mkdir(parents=True)
    artifacts = [save(args.output / 'numeric-tables.json', dict(schemaVersion=1, motionTable=motion,
                       resonanceTable=resonance, sourceEvidence=dict(motionBase=0xc98d, resonanceBase=0xca11,
                       pitchLogicalBase=24, resonanceStageLogicalBase=1,
                       sourceSha256=SOURCE_SHA))),
                 save(args.output / 'isolated-cases.json.gz', cases, True),
                 save(args.output / 'contexts.json.gz', compared, True),
                 save(args.output / 'mutation-controls.json.gz', mutations, True)]
    verification = dict(schemaVersion=1, sourceSha256=SOURCE_SHA, dependencies=TOOLS,
                        canonicalEvidenceSha256=dict(PINS, **{'initial-state.json': INITIAL_SHA}),
                        source=dict(url='https://www.hvsc.de/download/C64Music/MUSICIANS/D/Daglish_Ben/Deflektor.sid',
                            credit='Ben Daglish', bytes=len(data), selectedSubtune=1, profile='pal-banked',
                            hostBase=0x0400, loadAddress=profile['loadAddress'],
                            endAddressExclusive=profile['endAddress'], initAddress=profile['initAddress'],
                            playAddress=profile['playAddress'], sidModel=profile['sids'][0]['model']),
                        checkerSha256=digest(Path(__file__).read_bytes()),
                        modelSha256=digest(Path(__file__).with_name('model.py').read_bytes()),
                        testSha256=digest(Path(__file__).with_name('model_test.py').read_bytes()),
                        sourceSegmentSha256={kind: dict(start=start, endExclusive=end,
                            sha256=digest(bytes(ram[start:end]))) for kind, (start, end) in SEGMENTS.items()},
                        isolatedCaseCounts=dict(Counter(case['kind'] for case in cases)),
                        isolatedMaximumCycles=max(case['cycles'] for case in cases),
                        isolatedTableReads={kind: sorted({read['address'] for case in cases if case['kind'] == kind
                            for read in case['tableReads']}) for kind in SEGMENTS},
                        observedCounts=counts,
                        mutationCounts={kind: len(items) for kind, items in mutations.items()},
                        mutationExamples={kind: items[:2] for kind, items in mutations.items()},
                        artifacts=artifacts,
                        limits=['Independent numeric component predictions are compared to isolated original instructions and retained full-form states/stores. All oracles use the shared py65 CPU; no new full-title CPU or VICE run is made.',
                                'Observed PWM and delayed-pitch comparisons exclude row setup, rests and global suppression. Enabled delayed pitch is exposed only where score glide and later score-pitch macros are disabled. Resonance independently evolves local timers/positions and the shared shadow through selected calls0..8480, using selectors and row/patch actions supplied by retained source evidence; this is not an independent score scheduler.',
                                'Mutation controls change one numeric input against retained incoming contexts, or reverse same-call resonance processing. They demonstrate comparison sensitivity, not edited full-source reruns.',
                                'Tables retain literal aliased numeric byte ranges, not a raw RAM image, source payload or original code. Synthetic selector/phase edges use those same pinned bytes; they do not establish musical use of every table entry.',
                                'Non-terminating PWM marker chains reject explicitly. This component does not implement scheduling, complete note setup, complete synthesis, host IRQs, bus timing, audio or listening judgments.'])
    save(args.output / 'verification.json', verification)
    print(json.dumps(dict(isolatedCases=len(cases), observedCounts=counts,
                          mutationCounts=verification['mutationCounts'], output=str(args.output))))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
