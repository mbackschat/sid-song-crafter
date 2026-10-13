"""Decode the pinned Flashdance score bytes and verify their executed semantics."""

import argparse
from enum import IntEnum
import hashlib
import importlib.util
import json
from pathlib import Path

from verify_player import CYCLES_PER_FRAME, require


ROOT = Path(__file__).resolve().parents[1]
TRACK_ADDRESSES = (0x207b, 0x247b, 0x287b)
FIRST_SCORE_CALL = 2
CYCLE_CALLS = 1536
STOP_CALL = FIRST_SCORE_CALL + CYCLE_CALLS
ROLE_NAMES = ('bass', 'lead', 'chord')


class CommandClass(IntEnum):
    DURATION = 0x80
    INSTRUMENT = 0xa0
    EFFECT = 0xc0


def load_script(filename, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reference = load_script('study-drax-references.py', 'flashdance_score_reference')
SOURCE_SHA256 = reference.REFERENCES['flashdance']['sha256']


def word(memory, address):
    return memory[address] | memory[address + 1] << 8


def source_memory(data):
    offset = int.from_bytes(data[6:8], 'big')
    load = int.from_bytes(data[8:10], 'big')
    if load == 0:
        load = int.from_bytes(data[offset:offset + 2], 'little')
        offset += 2
    memory = bytearray(65536)
    memory[load:load + len(data) - offset] = data[offset:]
    return memory


def instrument_record(memory, offset):
    require(offset % 8 == 0 and 0 <= offset <= 248, 'Invalid instrument record offset')
    address = 0x1c7b + offset
    row = memory[address:address + 8]
    return {
        'attackDecay': row[0], 'sustainRelease': row[1],
        'sourceEvidence': {
            'recordOffset': offset, 'address': address, 'bytes': list(row),
            'alternatePitchMode': row[2], 'filterSetup': row[3], 'filterProgramOffset': row[4],
            'pulseProgramOffset': row[5], 'wavePitchProgramOffset': row[6], 'releaseProgramOffset': row[7],
        },
    }


def effect_command(memory, value):
    """Translate only effect branches executed in the selected Flashdance form."""
    address = 0x1f7b + 2 * (value & 63)
    mode, parameter = memory[address:address + 2]
    if mode == 0x82:
        effect, parameters = 'sustainReleaseAhead', {'callsBeforeNextRow': 2, 'sustainRelease': parameter}
    elif mode == 0x60:
        counter = parameter >> 4
        require(counter > 0, 'Vibrato requires a nonzero direction counter')
        effect, parameters = 'vibrato', {
            'initialCounter': counter - 1, 'reloadCounter': counter,
            'pitchDeltaRightShifts': parameter & 15, 'deltaHighByteIncrement': 0, 'remainingNotes': 1,
        }
    elif mode == 0x10:
        effect, parameters = 'pitchOffset', {'stepWord': parameter, 'remainingNotes': 1}
    else:
        raise ValueError(f'Unsupported score effect ${mode:02x}/${parameter:02x}')
    return {'kind': 'effect', 'effect': effect, 'parameters': parameters,
            'sourceEvidence': {'effectTableAddress': address, 'effectBytes': [mode, parameter]}}


def decode_score(memory, *, stop_call=STOP_CALL + CYCLE_CALLS):
    """Independently consume source tracks/patterns, without executing the driver.

    Runtime commands contain editable notes, durations, articulation and effects.
    Source addresses and byte encodings remain annotations; no SID write stream
    supplies the composition. The owning study is docs/research/composition/
    flashdance-preparation.md, with executed score reader $1141 and restart $12AD.
    """
    require(len(memory) == 65536, 'Score decoder requires complete source RAM')
    require(type(stop_call) is int and FIRST_SCORE_CALL < stop_call <= STOP_CALL + CYCLE_CALLS,
            'Select a bounded first or second Flashdance score cycle')
    roles = {name: {'voice': voice, 'fineTuneWord': memory[0x1761 + voice], 'commands': []}
             for voice, name in enumerate(ROLE_NAMES, 1)}
    states = [{'track': track, 'cursor': 0, 'transpose': 0, 'duration': 1, 'counter': 0,
               'instrument': None, 'srTrigger': 0, 'srValue': 0, 'patternKey': None}
              for track in TRACK_ADDRESSES]
    reads, initializers, sr_writes, patterns, loops, instruments = [], [], [], [], [], {}
    frequency_table = [word(memory, 0x1628 + 2 * index) for index in range(96)]
    for call in range(FIRST_SCORE_CALL, stop_call):
        for channel in (2, 1, 0):
            voice, state = channel + 1, states[channel]
            role = roles[ROLE_NAMES[channel]]
            if state['counter']:
                if state['counter'] == state['srTrigger']:
                    sr_writes.append((call, voice, state['srValue']))
                    state['srTrigger'] = 0
                state['counter'] -= 1
                continue
            track_value = memory[state['track']]
            require(track_value != 255, 'Track loop must be consumed after its preceding score row')
            if track_value & 128:
                state['transpose'] = track_value & 127
                state['track'] += 1
            pattern = memory[state['track']]
            require(pattern < 128, 'Invalid source pattern selection')
            pattern_address = memory[0x1d7b + pattern] | memory[0x1e7b + pattern] << 8
            key = (state['track'], pattern, state['transpose'])
            if state['patternKey'] != key:
                patterns.append({'call': call, 'voice': voice, 'trackPointer': state['track'],
                                 'pattern': pattern, 'patternAddress': pattern_address,
                                 'transposeBytes': state['transpose'] * 2})
                state['patternKey'] = key
            restart = True
            duration_evidence = []
            for _ in range(256):
                require(0 <= state['cursor'] < 256, 'Pattern cursor wraps before a score event')
                address = pattern_address + state['cursor']
                value = memory[address]
                reads.append((call, voice, address, value))
                evidence = {'address': address, 'value': value, 'pattern': pattern}
                state['cursor'] += 1
                if value < 128:
                    require(value != 127, 'Unexpected pattern end in place of a score event')
                    kind = 'off' if value == 0 else 'hold' if value == 126 else 'note'
                    command = {'call': call, 'kind': kind, 'durationCalls': state['duration']}
                    if kind == 'note':
                        require(state['instrument'] is not None, 'Score note lacks an instrument selection')
                        index = (value + state['transpose']) & 127
                        require(index < len(frequency_table), 'Score pitch lies outside the pinned frequency table')
                        command.update(sourceNote=value, transposeSemitones=state['transpose'], restart=restart)
                        evidence.update(pitchTableIndex=index,
                                        frequencyWord=(frequency_table[index] + role['fineTuneWord']) & 65535)
                        if restart:
                            initializers.append((call, voice))
                    evidence['durationCommands'] = duration_evidence
                    command['sourceEvidence'] = evidence
                    role['commands'].append(command)
                    state['counter'] = state['duration'] - 1
                    marker = memory[pattern_address + state['cursor']]
                    require(marker != 254, 'Selected score contains a terminating track command')
                    if marker == 127:
                        state['cursor'] = 0
                        state['track'] += 1
                        if memory[state['track']] == 255:
                            loops.append({'call': call, 'voice': voice, 'endPointer': state['track'],
                                          'loopPointer': TRACK_ADDRESSES[channel]})
                            state['track'] = TRACK_ADDRESSES[channel]
                    break
                try:
                    command_class = CommandClass(value & 0xe0)
                except ValueError:
                    raise ValueError(f'Unsupported score command ${value:02x}') from None
                if command_class == CommandClass.DURATION:
                    restart = not bool(value & 16)
                    state['duration'] = memory[0x1765 + (value & 15)] + 1
                    duration_evidence.append({'address': address, 'value': value})
                elif command_class == CommandClass.INSTRUMENT:
                    offset = (value << 3) & 255
                    name = f'record-{offset:02x}'
                    instruments[name] = instrument_record(memory, offset)
                    state['instrument'] = name
                    role['commands'].append({'call': call, 'kind': 'instrument', 'instrument': name,
                                             'sourceEvidence': evidence})
                elif command_class == CommandClass.EFFECT:
                    command = effect_command(memory, value)
                    command.update(call=call)
                    command['sourceEvidence'].update(evidence)
                    role['commands'].append(command)
                    if command['effect'] == 'sustainReleaseAhead':
                        state['srTrigger'] = command['parameters']['callsBeforeNextRow']
                        state['srValue'] = command['parameters']['sustainRelease']
            else:
                raise ValueError('Score row fails to consume a terminal note/hold/off')
    return {'roles': roles, 'instruments': instruments, 'frequencyTable': frequency_table,
            'scoreReads': reads, 'initializers': initializers, 'sustainReleaseWrites': sr_writes,
            'patternSelections': patterns, 'trackLoops': loops}


def verify_recurrence(roles, *, first_call=FIRST_SCORE_CALL, cycle_calls=CYCLE_CALLS):
    for role in roles.values():
        def selected(start):
            return [dict(command, call=command['call'] - start) for command in role['commands']
                    if start <= command['call'] < start + cycle_calls]
        require(selected(first_call) and selected(first_call) == selected(first_call + cycle_calls),
                'Decoded recurring score commands differ')


def verify_execution(data, decoded, calls):
    diagnostic = load_script('psid_audit.py', 'flashdance_score_private_audit')
    memories = []

    def memory_factory(sid_bases):
        memory = reference.FlashdanceDiagnosticMemory(sid_bases)
        memories.append(memory)
        return memory

    diagnostic.AuditMemory = memory_factory
    reads, initializers, sr_writes, patterns, loops, previous = [], [], [], [], [], {}

    def observe(cpu, memory):
        if memory.phase != 'play':
            return
        current, voice, call = memory.data, cpu.x + 1, memory.tick
        if cpu.pc == 0x10ec and call == 0:
            require(current[0x1716 + cpu.x] == FIRST_SCORE_CALL, 'Startup score countdown differs')
            pointer = current[0x16e9 + cpu.x] | current[0x16ec + cpu.x] << 8
            require(pointer == TRACK_ADDRESSES[cpu.x], 'Startup track pointer differs')
        if cpu.pc == 0x1141:
            address = word(current, 0xfb) + cpu.y
            reads.append((call, voice, address, current[address]))
        if cpu.pc == 0x12e0:
            initializers.append((call, voice))
        if cpu.pc == 0x1101:
            sr_writes.append((call, voice, cpu.a))
        if cpu.pc == 0x1134:
            pointer = current[0x16e9 + cpu.x] | current[0x16ec + cpu.x] << 8
            key = (pointer, cpu.y, current[0x1017 + cpu.x])
            if previous.get(voice) != key:
                patterns.append({'call': call, 'voice': voice, 'trackPointer': pointer, 'pattern': cpu.y,
                                 'patternAddress': current[0x1d7b + cpu.y] | current[0x1e7b + cpu.y] << 8,
                                 'transposeBytes': current[0x1017 + cpu.x]})
                previous[voice] = key
        if cpu.pc == 0x128f:
            loops.append({'call': call, 'voice': voice,
                          'endPointer': current[0x16e9 + cpu.x] | current[0x16ec + cpu.x] << 8,
                          'loopPointer': current[0x16ef + cpu.x] | current[0x16f2 + cpu.x] << 8})
        require(cpu.pc != 0x129f, 'Executed score contains a terminating track command')

    report, writes = diagnostic.audit_psid(data, calls, observer=observe)
    ignored = memories[0].ignored_writes
    require([(row['address'], row['value']) for row in ignored] == [(0xd419, 0), (0xd41a, 0)],
            'Pinned Flashdance init paddle writes changed')
    for actual, expected, name in ((reads, decoded['scoreReads'], 'score-byte consumption'),
                                   (initializers, decoded['initializers'], 'instrument initializations'),
                                   (sr_writes, decoded['sustainReleaseWrites'], 'scheduled sustain/release writes'),
                                   (patterns, decoded['patternSelections'], 'pattern selections'),
                                   (loops, decoded['trackLoops'], 'track-loop restores')):
        require(actual == expected, f'Decoded {name} differs from original execution')
    onsets = [(row['tick'], (row['address'] - 0xd404) // 7 + 1) for row in writes
              if row['phase'] == 'play' and row['address'] in (0xd404, 0xd40b, 0xd412) and row['value'] == 9]
    require(onsets == initializers, 'Initializer commands differ from SID TEST/GATE onset signatures')
    return report, ignored


def describe_score(data):
    require(hashlib.sha256(data).hexdigest() == SOURCE_SHA256, 'Source differs from pinned Flashdance tune')
    memory = source_memory(data)
    calls = STOP_CALL + CYCLE_CALLS
    decoded = decode_score(memory, stop_call=calls)
    verify_recurrence(decoded['roles'])
    report, ignored = verify_execution(data, decoded, calls)
    for role in decoded['roles'].values():
        role['commands'] = [command for command in role['commands'] if command['call'] < STOP_CALL]
    note_counts = {name: sum(command['kind'] == 'note' for command in role['commands'])
                   for name, role in decoded['roles'].items()}
    require(note_counts == {'bass': 37, 'lead': 44, 'chord': 13}, 'Selected-form note counts differ')
    return {
        'format': 'sid-flashdance-score-v1',
        'source': {'path': '.local/research/flashdance/drax-flashdance-conversion.sid', 'sha256': SOURCE_SHA256,
                   'initAddress': 4096, 'playAddress': 4099},
        'profile': {'clock': 'PAL', 'chip': 'MOS6581', 'callCycles': CYCLES_PER_FRAME},
        'range': {'firstCall': 0, 'firstScoreCall': FIRST_SCORE_CALL, 'lastCallInclusive': STOP_CALL - 1,
                  'stopCall': STOP_CALL, 'cycleCalls': CYCLE_CALLS},
        'roles': decoded['roles'], 'instruments': decoded['instruments'], 'frequencyTable': decoded['frequencyTable'],
        'sourceEvidence': {'patternSelections': [row for row in decoded['patternSelections'] if row['call'] < STOP_CALL],
                           'trackLoops': [row for row in decoded['trackLoops'] if row['call'] < STOP_CALL]},
        'evidence': {
            'method': 'Independent source track/pattern parsing, checked against executed score reads, instrument onsets, scheduled SR writes, pattern selections and loop restores across two complete score cycles.',
            'executedScoreMatches': True, 'secondScoreCycleMatches': True, 'verifiedPlayCalls': calls,
            'noteCounts': note_counts, 'originalDriverIncluded': False, 'registerDumpPlayback': False,
            'diagnostic': {'classification': 'Pinned diagnostic adapter; not a production-auditor pass',
                           'ignoredInitPaddleWrites': ignored, 'maximumPlayCycles': report['maximumPlayCycles']},
            'sourcePCs': {'scoreRead': 0x1141, 'note': 0x114b, 'hold': 0x1161, 'off': 0x116c,
                          'restartDecision': 0x12ad, 'instrumentInit': 0x12e0, 'sustainReleaseOverride': 0x1101},
        },
        'limits': 'Complete selected recurring SID score from initialization, with no independently authored ending. Instrument waveform/PWM/filter synthesis is outside this score model. Notes name score roots, not every audible attack; frequencyWord excludes active instrument/effect modulation. No bus-timing, original-song section coverage or listening-acceptance claim.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sid', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check', action='store_true', help='Verify an existing description without modifying it')
    parser.add_argument('--composition', action='store_true', help='Include independently computed instrument programs and ending parameters')
    args = parser.parse_args()
    data = args.sid.read_bytes()
    result = describe_score(data)
    if args.composition:
        from flashdance_player import describe_player
        result = describe_player(data, result)
    if args.check:
        require(json.loads(args.output.read_text()) == result, 'Existing description differs from decoded source')
        print(f'Verified Flashdance score: {args.output}')
    else:
        require(not args.output.exists() and not args.output.is_symlink(), 'Choose a fresh output file')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as output:
            json.dump(result, output, indent=2, allow_nan=False)
            output.write('\n')
        print(f'Described Flashdance score: {args.output}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f'Flashdance score description failed: {error}')
