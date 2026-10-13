"""Transcribe pinned corrected Shades into editable patterns, order and gate commands."""

import argparse
from copy import deepcopy
from enum import Enum
from functools import lru_cache
import hashlib
import importlib.util
import json
from pathlib import Path

from verify_player import require


ROOT = Path(__file__).resolve().parents[1]
SOURCE_NAME = 'Shades_filter_corrected.sid'
STOP_CALL = 24385
PROFILE = {'clock': 'PAL', 'chip': 'MOS6581', 'timing': 'CIA1 Timer A'}


class RowKind(str, Enum):
    NOTE = 'note'
    REST = 'rest'
    HOLD = 'hold'


class Gate(str, Enum):
    ON = 'on'
    OFF = 'off'


class FadeKind(str, Enum):
    RETAIN = 'retain'
    CANCEL = 'cancel'
    START = 'start'


def integer(value, label, minimum, maximum):
    require(type(value) is int and minimum <= value <= maximum,
            f'{label} must be an integer in {minimum}..{maximum}')


def word(memory, address):
    return memory[address] | memory[address + 1] << 8


@lru_cache(maxsize=1)
def load_reference():
    spec = importlib.util.spec_from_file_location('shades_score_reference', ROOT / 'scripts/trace-shades-vice.py')
    reference = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference)
    return reference


def decode_row(value):
    """Decode only executed score branches, keeping hold separate from key-off.

    At $7498/$755A/$75F6, $80 bypasses pitch and gate updates. Other high-bit
    pitches compute a target then enter the key-off branches at $7537/$75D9/
    $7675. They do not preserve GATE as an ordinary legato note would.
    """
    integer(value, 'Score byte', 0, 255)
    if value == 0:
        return {'kind': RowKind.REST.value}
    if value == 128:
        return {'kind': RowKind.HOLD.value}
    return {'kind': RowKind.NOTE.value, 'sourceNote': value & 127,
            'gate': Gate.OFF.value if value & 128 else Gate.ON.value}


def validate_row(row):
    require(type(row) is dict, 'Score command must be an object')
    try:
        kind = RowKind(row['kind'])
    except (KeyError, ValueError):
        raise ValueError('Unsupported score command') from None
    expected = {'kind', 'sourceNote', 'gate'} if kind == RowKind.NOTE else {'kind'}
    require(set(row) == expected, 'Unsupported score command fields')
    if kind == RowKind.NOTE:
        integer(row['sourceNote'], 'sourceNote', 1, 127)
        require(row['gate'] in tuple(Gate), 'Unsupported note gate command')
    return kind


def row_byte(row):
    kind = validate_row(row)
    if kind == RowKind.REST:
        return 0
    if kind == RowKind.HOLD:
        return 128
    return row['sourceNote'] | (128 if row['gate'] == Gate.OFF else 0)


def validate_fade(fade):
    require(type(fade) is dict, 'Fade command must be an object')
    try:
        kind = FadeKind(fade['kind'])
    except (KeyError, ValueError):
        raise ValueError('Unsupported fade command') from None
    require(set(fade) == ({'kind', 'rowInterval'} if kind == FadeKind.START else {'kind'}),
            'Unsupported fade command fields')
    if kind == FadeKind.START:
        integer(fade['rowInterval'], 'Fade row interval', 2, 255)
    return kind


def write_evidence(output, artifacts, metadata):
    """Retain complete structured observations in a fresh caller-selected directory."""
    output = Path(output)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh evidence directory')
    output.mkdir(parents=True)
    for name, content in artifacts.items():
        with (output / name).open('x', encoding='utf-8') as handle:
            json.dump(content, handle, separators=(',', ':'), allow_nan=False)
            handle.write('\n')
    receipt = {**metadata, 'artifacts': {
        name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in artifacts}}
    with (output / 'receipt.json').open('x', encoding='utf-8') as handle:
        json.dump(receipt, handle, indent=2)
        handle.write('\n')


def expand_score(description):
    """Schedule semantic pattern rows without source files or address annotations.

    Commands select pitch-table indices, not MIDI notes or audible attack pitches.
    The instrument model owns effects, waveform staging and conditional control
    writers. A rest requests key-off while preserving those programs; a hold
    performs neither pitch nor gate work. Initialization is an extra first call.
    """
    require(type(description) is dict and description.get('format') == 'sid-shades-score-v1',
            'Unsupported Shades score format')
    require(description.get('profile') == PROFILE, 'Unsupported Shades profile')
    bounds = description.get('range', {})
    require(type(bounds) is dict, 'Score range must be an object')
    require(bounds.get('firstCall') == 0 and bounds.get('firstRowCall') == 1,
            'Score range must retain call-zero initialization')
    integer(bounds.get('stopCall'), 'Score range stopCall', 2, 65535)
    patterns, orders = description.get('patterns'), description.get('orders')
    instruments = description.get('instrumentBlocks')
    require(type(patterns) is dict and patterns and type(orders) is list and 1 <= len(orders) <= 128,
            'Expected patterns and 1..128 ordered selections')
    require(type(instruments) is list and instruments and all(type(name) is str for name in instruments)
            and len(set(instruments)) == len(instruments), 'Expected distinct named instrument blocks')
    for name, pattern in patterns.items():
        require(type(name) is str and type(pattern) is dict and set(pattern) == {'rows'}
                and type(pattern['rows']) is list and 1 <= len(pattern['rows']) <= 256,
                'Invalid pattern rows')
        for row in pattern['rows']:
            validate_row(row)
    commands, selections = [], []
    cursor = 1
    fields = {'patternIds', 'instrument', 'transposeSemitones', 'voice1HighNotesAbsolute',
              'rowCount', 'rowDurationCalls', 'timerHigh', 'fade'}
    for index, order in enumerate(orders):
        require(type(order) is dict and set(order) == fields, 'Unsupported order fields')
        require(order['instrument'] in instruments, 'Unknown instrument block')
        ids, transposes = order['patternIds'], order['transposeSemitones']
        require(type(ids) is list and len(ids) == 3 and all(type(name) is str and name in patterns for name in ids),
                'Expected a pattern selection for each physical voice')
        require(type(transposes) is list and len(transposes) == 3, 'Expected three transposes')
        for transpose in transposes:
            integer(transpose, 'Transpose', -128, 127)
        require(type(order['voice1HighNotesAbsolute']) is bool, 'Invalid voice-one transpose policy')
        integer(order['rowCount'], 'Order row count', 1, 256)
        integer(order['rowDurationCalls'], 'Row duration', 1, 256)
        integer(order['timerHigh'], 'Timer high byte', 0, 255)
        validate_fade(order['fade'])
        require(all(len(patterns[name]['rows']) >= order['rowCount'] for name in ids),
                'Order row count exceeds its pattern rows')
        selections.append({'call': 0 if index == 0 else cursor, 'firstRowCall': cursor,
                           'orderIndex': index, **deepcopy(order)})
        for row_index in range(order['rowCount']):
            for voice, name in enumerate(ids, 1):
                row = patterns[name]['rows'][row_index]
                command = {'call': cursor, 'voice': voice, 'orderIndex': index, 'row': row_index,
                           'instrument': order['instrument'], 'durationCalls': order['rowDurationCalls'], **row}
                if row['kind'] == RowKind.NOTE:
                    absolute = voice == 1 and order['voice1HighNotesAbsolute'] and row['sourceNote'] >= 48
                    command['pitchTableIndex'] = (row['sourceNote'] + (0 if absolute else transposes[voice - 1])) & 255
                    integer(command['pitchTableIndex'], 'Resolved pitch-table index', 0, 95)
                commands.append(command)
            cursor += order['rowDurationCalls']
    require(cursor == bounds['stopCall'], 'Score range disagrees with row timing')
    return {'commands': commands, 'selections': selections}


def decode_source(memory, block_names):
    """Parse the selected source order, pointer tables and row bytes independently."""
    require(len(memory) == 65536, 'Source decoder requires full import RAM')
    orders, evidence, pointers = [], [], {}
    for slot in range(128):
        require(memory[0x5580 + slot] == slot,
                'Unsupported source order command; only the pinned identity order was executed')
        ptrs = [word(memory, bank + slot * 2) for bank in (0x5000, 0x5100, 0x5200, 0x5300)]
        info = ptrs[3]
        require(info in block_names, 'Unsupported source instrument block')
        rows = memory[info + 0x32]
        require(rows in (32, 64), 'Unsupported source row limit')
        for pointer in ptrs[:3]:
            require(0x5800 <= pointer < 0x7000, 'Source pattern pointer leaves the inspected data area')
            pointers[pointer] = max(pointers.get(pointer, 0), rows)
        transposes = [memory[bank + slot] for bank in (0x5400, 0x5480, 0x5500)]
        fade = memory[info + 63]
        fade_command = {'kind': FadeKind.CANCEL.value if fade == 255 else FadeKind.RETAIN.value}
        if 0 < fade < 255:
            fade_command = {'kind': FadeKind.START.value, 'rowInterval': fade + 1}
        orders.append({'patternIds': ptrs[:3], 'instrument': block_names[info],
                       'transposeSemitones': [value if value < 128 else value - 256 for value in transposes],
                       'voice1HighNotesAbsolute': bool(memory[info + 11]),
                       'rowCount': rows, 'rowDurationCalls': 3,
                       'timerHigh': memory[info + 14], 'fade': fade_command})
        evidence.append({'orderIndex': slot, 'orderAddress': 0x5580 + slot,
                         'voicePatternAddresses': ptrs[:3], 'instrumentAddress': info,
                         'transposeBytes': transposes, 'rowLimitByte': rows,
                         'timerHighByte': memory[info + 14], 'fadeByte': fade})
    names = {pointer: f'pattern-{index:03d}' for index, pointer in enumerate(sorted(pointers))}
    patterns = {names[pointer]: {'rows': [decode_row(value) for value in memory[pointer:pointer + length]]}
                for pointer, length in sorted(pointers.items())}
    for order in orders:
        order['patternIds'] = [names[pointer] for pointer in order['patternIds']]
    return {'format': 'sid-shades-score-v1', 'profile': dict(PROFILE),
            'range': {'firstCall': 0, 'firstRowCall': 1, 'lastCallInclusive': STOP_CALL - 1,
                      'stopCall': STOP_CALL, 'cycleCalls': STOP_CALL - 1},
            'instrumentBlocks': sorted({order['instrument'] for order in orders}),
            'patterns': patterns, 'orders': orders,
            'sourceEvidence': {'patternAddresses': {name: address for address, name in names.items()},
                               'instrumentAddresses': {block_names[address]: address
                                                       for address in {row['instrumentAddress'] for row in evidence}},
                               'orders': evidence}}


def verify_execution(data, description, *, evidence_output=None):
    """Check every consumed row, selection, pitch target and gate branch against execution."""
    expanded = expand_score(description)
    addresses = description['sourceEvidence']['patternAddresses']
    orders = description['orders']
    expected_reads, expected_pitches, expected_gates = [], [], []
    for command in expanded['commands']:
        call, voice = command['call'], command['voice']
        pattern = orders[command['orderIndex']]['patternIds'][voice - 1]
        row = description['patterns'][pattern]['rows'][command['row']]
        expected_reads.append((call, voice, addresses[pattern] + command['row'], row_byte(row)))
        if command['kind'] == RowKind.NOTE:
            expected_pitches.append((call, voice, command['pitchTableIndex']))
        if command['kind'] != RowKind.HOLD:
            expected_gates.append((call, voice, command.get('gate', Gate.OFF.value)))
    reads, selections, pitches, gates, timers, fades = [], [], [], [], [], []
    row_states, call_states = [], []
    read_pcs = {0x748e: (1, 0xa5), 0x7553: (2, 0xa7), 0x75ef: (3, 0xa9)}
    pitch_pcs = {0x74b0: 1, 0x7568: 2, 0x7606: 3}
    gate_pcs = {0x74f4: (1, 'on'), 0x7531: (1, 'on'), 0x7537: (1, 'off'),
                0x75a9: (2, 'on'), 0x75d9: (2, 'off'), 0x7645: (3, 'on'), 0x7675: (3, 'off')}

    def score_state(memory, pointer_base):
        return {'restartFlag': memory[0x033c], 'playingFlag': memory[0x033d],
                'advanceFlag': memory[0x033e], 'nextOrder': memory[0x033f],
                'rowIndex': memory[0x0340], 'rowCounter': memory[0x0341],
                'rowReload': memory[0x0342], 'transposes': list(memory[0x0343:0x0346]),
                'rowLimit': memory[0x036f], 'previousRows': list(memory[0x0371:0x0374]),
                'fade': list(memory[0x0377:0x037a]),
                'activePointers': [word(memory, pointer_base + offset) for offset in (0, 2, 4, 6)]}

    def observe(cpu, memory):
        if memory.phase != 'play':
            return
        call, pc, m = memory.tick, cpu.pc, memory.data
        if evidence_output is not None and pc == 0x742e:
            call_states.append({'call': call, 'stateBeforeCall': score_state(m, 0x07e9)})
        if pc in read_pcs:
            voice, pointer = read_pcs[pc]
            address = word(m, pointer) + cpu.y
            reads.append((call, voice, address, m[address]))
            require(m[0x0341] == m[0x0342] == 2, 'Executed row countdown differs')
            if evidence_output is not None and voice == 1:
                state = score_state(m, 0xa5)
                row_states.append({'call': call, 'stateBeforeRow': state,
                                   'sourceAddresses': [pointer + cpu.y for pointer in state['activePointers'][:3]],
                                   'bytes': [m[pointer + cpu.y] for pointer in state['activePointers'][:3]]})
        if pc == 0x77e9:
            selections.append((call, cpu.x))
        if pc in pitch_pcs:
            pitches.append((call, pitch_pcs[pc], cpu.a))
        if pc in gate_pcs:
            voice, gate = gate_pcs[pc]
            gates.append((call, voice, gate))
        if pc == 0x7852:
            timers.append((call, cpu.a))
        if pc == 0x7860:
            fades.append((call, cpu.a))

    report, writes = load_reference().shades_oracle(data, STOP_CALL, observer=observe)
    expected_selections = [(row['call'], row['orderIndex']) for row in expanded['selections']]
    expected_timers = [(row['call'], row['timerHigh']) for row in expanded['selections']]
    expected_fades = [(row['call'], 255 if row['fade']['kind'] == FadeKind.CANCEL else
                      row['fade']['rowInterval'] - 1 if row['fade']['kind'] == FadeKind.START else 0)
                     for row in expanded['selections']]
    for actual, expected, label in ((reads, expected_reads, 'score-byte consumption'),
                                    (selections, expected_selections, 'pattern order'),
                                    (pitches, expected_pitches, 'pitch targets'),
                                    (gates, expected_gates, 'gate branches'),
                                    (timers, expected_timers, 'timer commands'),
                                    (fades, expected_fades, 'fade commands')):
        require(actual == expected, f'Decoded {label} differs from executed source')
    if evidence_output is not None:
        artifacts = {
            'score-events.json': {'reads': reads, 'selections': selections, 'pitchTargets': pitches,
                                  'gateBranches': gates, 'timerCommands': timers, 'fadeCommands': fades},
            'row-state.json': row_states, 'call-state.json': call_states,
            'audit.json': report, 'writes.json': writes,
            'semantic-expansion.json': expanded, 'source-mapping.json': description['sourceEvidence'],
        }
        receipt = {'sourceSha256': hashlib.sha256(data).hexdigest(),
                   'toolSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   'verifiedCalls': STOP_CALL, 'completeConsumedEventsMatch': True,
                   'limitations': 'Lossless observed score/state/write evidence for explicit RAM calls; no native CIA scheduler, bus timing, source-player inclusion or register-replay authoring.'}
        write_evidence(evidence_output, artifacts, receipt)
    return {'completeConsumedEventsMatch': True, 'verifiedPlayCalls': STOP_CALL,
            'scoreReads': len(reads), 'patternSelections': len(selections),
            'pitchTargets': len(pitches), 'gateBranches': len(gates),
            'resolvedPitchTableRange': [min(row[2] for row in pitches), max(row[2] for row in pitches)],
            'maximumPlayCycles': report['maximumPlayCycles'],
            'diagnostic': 'Pinned callable RAM oracle, with inspected STA $DC05 allowance; no CIA scheduling or production-auditor pass'}


def describe_score(data, *, evidence_output=None):
    reference = load_reference()
    require(hashlib.sha256(data).hexdigest() == reference.SOURCE_PINS[SOURCE_NAME],
            'Source differs from the pinned corrected Shades reference')
    profile = reference.source_profile(data)
    from shades_programs import SOURCE_BLOCK_NAMES
    memory = bytearray(65536)
    memory[profile['loadAddress']:profile['endAddress']] = profile['payload']
    description = decode_source(memory, SOURCE_BLOCK_NAMES)
    description['sourceEvidence']['source'] = {
        'archivePath': '/MUSICIANS/H/Huelsbeck_Chris/' + SOURCE_NAME,
        'url': 'https://www.hvsc.de/download/C64Music/MUSICIANS/H/Huelsbeck_Chris/' + SOURCE_NAME,
        'sha256': reference.SOURCE_PINS[SOURCE_NAME], 'subtune': 1,
        'initAddress': profile['initAddress'], 'playAddress': profile['playAddress'],
        **{name: data[offset:offset + 32].split(b'\0')[0].decode('latin1')
           for name, offset in (('title', 22), ('author', 54), ('released', 86))}}
    description['evidence'] = verify_execution(data, description, evidence_output=evidence_output)
    description['limits'] = ('Complete selected score calls 0–24384 with finite stop 24385. Named instrument block IDs join '
                             'the separate synthesis model. This is pattern/transpose/gate/fade data, not a driver or '
                             'register replay. Note indices select the source pitch table, including index95; they are '
                             'not automatically MIDI pitches. Rest requests key-off and hold preserves pitch/gate work; '
                             'high-bit pitches select a target then key-off. Shared program state and conditional '
                             'writers remain instrument-model responsibilities. Only pinned identity order, 32/64-row '
                             'blocks and three-call rows were imported; other order/control encodings are unsupported. '
                             'No elapsed-time, CIA bus scheduling, source-editor compatibility or listening claim.')
    return description


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sid', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check', action='store_true', help='Check an existing JSON without changing it')
    parser.add_argument('--evidence-output', type=Path, help='Fresh directory for lossless execution/state/source-mapping evidence')
    args = parser.parse_args()
    result = describe_score(args.sid.read_bytes(), evidence_output=args.evidence_output)
    if args.check:
        require(json.loads(args.output.read_text()) == result, 'Saved score differs from verified source')
        print(f'Verified Shades score: {args.output}')
        return
    require(not args.output.exists() and not args.output.is_symlink(), 'Choose a fresh score output')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(result, output, indent=2, allow_nan=False)
        output.write('\n')
    print(f'Described Shades score: {args.output}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f'Shades score description failed: {error}')
