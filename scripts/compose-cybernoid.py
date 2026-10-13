"""Compile editable Cybernoid rows and numeric programs into an independent PAL PSID."""

import argparse
from dataclasses import fields
from enum import IntEnum
import hashlib
import json
from pathlib import Path
import struct

from cybernoid_player import CommandKind, RECORD_FIELDS, compute_writes, ending_parameters, integer, pitch_from_caller, record_bytes, selected
from cybernoid_pitch import PitchState
from cybernoid_state import CallerState, validate
from psid_audit import audit_psid
from sid_assembler import assemble
from verify_player import cpu_type, require


ROOT = Path(__file__).resolve().parents[1]
LOAD_ADDRESS = 0x1000
WORD_FIELDS = ('frequency', 'held_frequency', 'pulse_accumulator', 'pulse_output')


class Opcode(IntEnum):
    ROUTING = 0
    SOUND = 1
    DURATION = 2
    EXTEND_DURATION = 3
    ARPEGGIO = 4
    GLIDE = 5
    NOTE = 6


def data(label, values):
    require(values and all(type(value) is int and 0 <= value <= 255 for value in values),
            f'{label} requires bytes')
    return label + ':\n  .byte ' + ','.join(f'${value:02x}' for value in values) + '\n'


def bytes_table(values, name, *, size=None):
    require(isinstance(values, list) and 1 <= len(values) <= 256, f'{name} requires 1..256 bytes')
    require(size is None or len(values) == size, f'{name} requires {size} bytes')
    for value in values:
        integer(value, 255, name)


def semantic_rows(description):
    declared = integer(description['play_calls'], 65535, 'Declared calls')
    require(declared > 0, 'Declared calls must be positive')
    ending = ending_parameters(description)
    music_calls = ending[0] if ending else declared
    rows = {}
    payloads, payload_indices = [], {}
    schedules = [[], [], []]
    for row in description['rows']:
        tick = integer(row['call'], music_calls - 1, 'Row call')
        voice = integer(row['voiceIndex'], 2, 'Row voice')
        require((tick, voice) not in rows, 'Only one selected row per voice/call')
        transpose = integer(row['transpose'], 255, 'Transpose')
        require(row['patchSetup'] in ('initialize', 'preserve'), 'Unknown patchSetup')
        payload = [transpose, int(row['patchSetup'] == 'preserve')]
        note_seen = False
        for command in row['commands']:
            require(not note_seen, 'Note must be the final row command')
            kind = CommandKind(command['kind'])
            payload.append(int(Opcode[kind.name]))
            if kind is CommandKind.ROUTING:
                payload.append(integer(command['value'], 255, 'Routing'))
            elif kind is CommandKind.SOUND:
                index = integer(command['index'], 255, 'Sound index')
                record_bytes(description, index)
                payload.append(index)
            elif kind in (CommandKind.DURATION, CommandKind.EXTEND_DURATION):
                payload.append(integer(command['reload'], 255, 'Duration reload'))
            elif kind is CommandKind.ARPEGGIO:
                index = integer(command['index'], 254, 'Arpeggio index')
                selected(description['arpeggios'], index, 'Arpeggio table')
                payload.append(index)
            elif kind is CommandKind.GLIDE:
                payload.extend((integer(command['control'], 255, 'Glide control'),
                                integer(command['targetNote'], 255, 'Glide target note')))
            elif kind is CommandKind.NOTE:
                payload.append(integer(command['sourceNote'], 255, 'Source note'))
                note_seen = True
        require(note_seen, 'Selected row requires a note')
        require(len(payload) <= 256, 'Row payload exceeds byte-indexed command space')
        key = tuple(payload)
        if key not in payload_indices:
            payload_indices[key] = len(payloads)
            payloads.append(payload)
        schedules[voice].append((tick, payload_indices[key]))
        rows[tick, voice] = row
    for schedule in schedules:
        schedule.sort()
    remaining = [voice['caller']['row_remaining'] for voice in description['initial_state']['voices']]
    duration = [voice['caller']['row_duration'] for voice in description['initial_state']['voices']]
    globals_ = description['initial_state']['globals']
    countdown, reload = globals_['tempo_countdown'], globals_['tempo_reload']
    for tick in range(music_calls):
        countdown = (countdown - 1) & 255
        if countdown & 128:
            countdown = reload
        scheduled = countdown == reload
        for voice in (2, 1, 0):
            if scheduled:
                remaining[voice] = (remaining[voice] - 1) & 255
            row = rows.get((tick, voice))
            require((scheduled and bool(remaining[voice] & 128)) == (row is not None),
                    f'Row/countdown mismatch at call {tick} voice {voice}')
            if row is not None:
                for command in row['commands']:
                    if CommandKind(command['kind']) in (CommandKind.DURATION, CommandKind.EXTEND_DURATION):
                        duration[voice] = command['reload']
                remaining[voice] = duration[voice]
    return payloads, schedules


def parameters(description):
    initial = description['initial_state']
    require(len(initial['voices']) == 3, 'Three initial voices required')
    for name in ('tempo_reload', 'tempo_countdown', 'play_flag', 'filter_owner'):
        integer(initial['globals'][name], 255, name)
    require(initial['globals']['play_flag'] == 0, 'Stopped initialization is outside the selected title contract')
    for voice in initial['voices']:
        state, pitch = CallerState(**voice['caller']), PitchState(**voice['pitch'])
        validate(state)
        for name, value in vars(pitch).items():
            integer(value, 65535 if name in ('frequency', 'held_frequency') else 255, f'Initial pitch {name}')
        require(pitch_from_caller(state, pitch) == pitch, 'Initial caller and pitch fields must agree')
        integer(voice['sound_index'], 255, 'Sound index')
        record_bytes(description, voice['sound_index'])
        if voice['arpeggio_index'] is not None:
            integer(voice['arpeggio_index'], 254, 'Arpeggio index')
            selected(description['arpeggios'], voice['arpeggio_index'], 'Initial arpeggio table')
    frequencies = description['frequency_words']
    require(isinstance(frequencies, list) and len(frequencies) == 257, 'Frequency table requires 257 words')
    for value in frequencies:
        integer(value, 65535, 'Frequency word')
    require(1 <= len(description['records']) <= 256, 'Record table requires 1..256 records')
    for index in range(len(description['records'])):
        record_bytes(description, index)
    for name in ('vibrato_wait', 'onset_lengths', 'onset_waves'):
        bytes_table(description[name], name)
    require(len(description['vibrato_wait']) >= len(description['records']), 'Vibrato wait lacks a record selection')
    for name, size in (('pulse_slots', 8), ('filter_programs', 10), ('arpeggios', None)):
        require(1 <= len(description[name]) <= (255 if name == 'arpeggios' else 256), f'{name} has too many selections')
        for table in description[name]:
            bytes_table(table, name, size=size)
    require(1 <= len(description['drums']) <= 256, 'Drum table has too many selections')
    for drum in description['drums']:
        for name in ('waves', 'pitch_values'):
            bytes_table(drum[name], 'Drum ' + name)
    for name in ('cutoff_high', 'routing', 'mode_volume'):
        integer(description['sid_init'][name], 255, 'Initial ' + name)
    payloads, schedules = semantic_rows(description)
    source = data('cy_sid_offsets', [0, 7, 14])
    for suffix, shift in (('lo', 0), ('hi', 8)):
        source += data('cy_freq_' + suffix, [(value >> shift) & 255 for value in frequencies])
    for field in RECORD_FIELDS:
        source += data('cy_record_' + field, [record[field] for record in description['records']])
    for name in ('vibrato_wait', 'onset_lengths', 'onset_waves'):
        source += data('cy_' + name, description[name])
    references = {}

    def pointers(name, labels):
        nonlocal source
        for suffix, shift in (('lo', 0), ('hi', 8)):
            tokens = []
            for index, label in enumerate(labels):
                token = f'CY_{name.upper()}_PTR_{index}_{suffix.upper()}'
                references[token] = (label, shift)
                tokens.append(token)
            source += f'cy_{name}_ptr_{suffix}:\n  .byte ' + ','.join(tokens) + '\n'

    for name, description_name in (('pulse', 'pulse_slots'), ('filter', 'filter_programs'), ('arp', 'arpeggios')):
        labels = [f'cy_{name}_program_{index}' for index in range(len(description[description_name]))]
        pointers(name, labels)
        for label, table in zip(labels, description[description_name]):
            source += data(label, table)
    for name, field in (('drum_wave', 'waves'), ('drum_pitch', 'pitch_values')):
        labels = [f'cy_{name}_program_{index}' for index in range(len(description['drums']))]
        pointers(name, labels)
        for label, drum in zip(labels, description['drums']):
            source += data(label, drum[field])
    source += 'cy_schedule_bases:\n  .word cy_schedule_0,cy_schedule_1,cy_schedule_2\n'
    for voice, schedule in enumerate(schedules):
        source += f'cy_schedule_{voice}:\n'
        for tick, index in schedule:
            source += f'  .word ${tick:04x},cy_row_{index}\n'
        source += '  .word $ffff\n'
    for index, payload in enumerate(payloads):
        source += data(f'cy_row_{index}', payload)
    states = {}
    for field in fields(CallerState):
        if field.name in WORD_FIELDS:
            for suffix, shift in (('lo', 0), ('hi', 8)):
                states[f'cy_{field.name}_{suffix}'] = [(voice['caller'][field.name] >> shift) & 255
                                                       for voice in initial['voices']]
        else:
            name = 'cy_output_wave' if field.name == 'wave' else 'cy_' + field.name
            states[name] = [voice['caller'][field.name] for voice in initial['voices']]
    for field in ('vibrato_extent', 'glide_control', 'glide_target'):
        states['cy_' + field] = [voice['pitch'][field] for voice in initial['voices']]
    states['cy_sound_index'] = [voice['sound_index'] for voice in initial['voices']]
    states['cy_arpeggio_index'] = [255 if voice['arpeggio_index'] is None else voice['arpeggio_index']
                                  for voice in initial['voices']]
    for field in ('tempo_reload', 'tempo_countdown', 'filter_owner'):
        states['cy_' + field] = [initial['globals'][field]]
    for field in ('schedule_lo', 'schedule_hi'):
        states['cy_' + field] = [0] * 3
    for field in ('scheduled', 'fx1', 'fx2', 'fx3', 'tick_lo', 'tick_hi', 'core_transpose',
                  'core_preserve', 'core_threshold', 'core_row_lo', 'core_row_hi',
                  'tail', 'fading', 'mode_volume'):
        states['cy_' + field] = [0]
    ending = ending_parameters(description)
    states['cy_tail_volume'] = [15]
    states['cy_fade_remaining'] = [ending[2] if ending else 1]
    image = [value for values in states.values() for value in values]
    require(len(image) < 256, 'Named initialization state exceeds its byte-indexed image')
    source += 'cy_state_begin:\n' + ''.join(data(name, values) for name, values in states.items())
    source += 'cy_state_end:\n' + data('cy_initial_state', image)
    return source, references, dict(stateBytes=len(image), rowCount=sum(map(len, schedules)),
                                   uniqueRowPayloads=len(payloads), rowPayloadBytes=sum(map(len, payloads)),
                                   scheduleBytes=sum(map(len, schedules)) * 4 + 6)


def assemble_player(description, *, load_address=LOAD_ADDRESS):
    """Validate every declared program read before assembling indexed 6502 computation.

    Indirect CPU readers cannot enforce logical table bounds; the complete
    source-free numeric execution validates every reachable selection and index.
    """
    compute_writes(description)
    return _assemble_player(description, load_address=load_address)


def _assemble_player(description, *, load_address=LOAD_ADDRESS):
    require(type(load_address) is int and 0x0400 <= load_address < 0xa000,
            'Payload must remain in callable RAM')
    generated, references, sizes = parameters(description)
    ending = ending_parameters(description)
    music_calls = ending[0] if ending else description['play_calls']
    fade_start = music_calls + ending[1] if ending else music_calls
    constants = {name: 0 for name in references}
    constants.update({f'CY_OP_{opcode.name}': int(opcode) for opcode in Opcode})
    constants.update(CY_STATE_BYTES=sizes['stateBytes'], CY_CALLS_LO=description['play_calls'] & 255,
                     CY_CALLS_HI=description['play_calls'] >> 8,
                     CY_MUSIC_LO=music_calls & 255, CY_MUSIC_HI=music_calls >> 8,
                     CY_FADE_LO=fade_start & 255, CY_FADE_HI=fade_start >> 8,
                     CY_FADE_STEP=ending[2] if ending else 1,
                     CY_INIT_CUTOFF=description['sid_init']['cutoff_high'],
                     CY_INIT_ROUTING=description['sid_init']['routing'],
                     CY_INIT_MODE_VOLUME=description['sid_init']['mode_volume'])
    source = '\n'.join((ROOT / 'songs/players' / name).read_text()
                       for name in ('cybernoid.asm', 'cybernoid-pitch.asm', 'cybernoid-effects.asm')) + '\n' + generated
    cpu_type()
    _, preliminary, _ = assemble(source, constants, load=load_address)
    constants.update({token: (preliminary[label] >> shift) & 255
                      for token, (label, shift) in references.items()})
    payload, symbols, listing = assemble(source, constants, load=load_address)
    require(load_address + len(payload) <= 0xa000, 'Payload must remain in callable RAM')
    return payload, dict(symbols=symbols, source=source, listing=listing, payloadBytes=len(payload),
                         loadAddress=load_address, playCalls=description['play_calls'],
                         originalDriverIncluded=False, registerDumpPlayback=False, finiteMusicalEnding=ending is not None,
                         **sizes)


def build(description):
    """Validate all music and ending program reads and return the independent PSID."""
    compute_writes(description)
    return _build(description)


def _build(description):
    payload, built = _assemble_player(description)
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 2), (6, 124), (8, LOAD_ADDRESS), (10, built['symbols']['entry_init']),
                          (12, built['symbols']['entry_play']), (14, 1), (16, 1), (118, 0x14)):
        struct.pack_into('>H', header, offset, value)
    for offset, value in ((22, 'Cybernoid II independent study'), (54, 'SID Song Crafter'),
                          (86, '2026 independent reconstruction')):
        header[offset:offset + 31] = value.encode('ascii')[:31].ljust(31, b'\0')
    return bytes(header) + payload, built


def run(description_path, output, calls=None):
    description_path, output = Path(description_path), Path(output)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh output directory')
    input_data = description_path.read_bytes()
    description = json.loads(input_data)
    expected = compute_writes(description)
    sid, built = _build(description)
    count = built['playCalls'] if calls is None else calls
    require(type(count) is int and 1 <= count <= built['playCalls'], 'Requested calls exceed the declared music range')
    if count < built['playCalls']:
        expected = [row for row in expected if row['tick'] is None or row['tick'] < count]
    audit, writes = audit_psid(sid, count)
    identity = lambda rows: [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]
    if identity(expected) != identity(writes):
        for index, (wanted, actual) in enumerate(zip(identity(expected), identity(writes))):
            require(wanted == actual, f'Compiled SID stores differ at {index}: expected {wanted}, observed {actual}')
        raise ValueError(f'Compiled SID store count differs: expected {len(expected)}, observed {len(writes)}')
    output.mkdir(parents=True)
    (output / 'reconstructed.sid').write_bytes(sid)
    (output / 'player.asm').write_text(built.pop('source'))
    (output / 'player.listing').write_text(built.pop('listing'))
    report = dict(descriptionPath=str(description_path.resolve()),
                  descriptionSha256=hashlib.sha256(input_data).hexdigest(),
                  sidSha256=hashlib.sha256(sid).hexdigest(), checkedPlayCalls=count,
                  orderedStoreComparison=dict(matchedStores=len(writes), fields=['phase', 'tick', 'address', 'value']),
                  limits='Independent compiled state computation; no bus timing, audio or listening claim.', **built)
    for name, value in (('build.json', report), ('audit.json', audit), ('writes.json', writes)):
        with (output / name).open('x') as handle:
            json.dump(value, handle, indent=None if name == 'writes.json' else 2, allow_nan=False)
            handle.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('description', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calls', type=int)
    args = parser.parse_args()
    print(json.dumps(run(args.description, args.output, args.calls), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f'Cybernoid compilation failed: {error}')
