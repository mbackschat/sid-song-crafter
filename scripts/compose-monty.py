"""Compile editable Monty orders and sound programs into an independent PAL PSID."""

import argparse
import hashlib
import json
from pathlib import Path
import struct

from monty_title_player import GLOBAL_FIELDS, SEQUENCE_FIELDS, SOUND_FIELDS, alias_bindings, compute_writes, ending_contract
from monty_title_score import numeric_tables
from psid_audit import audit_psid
from sid_assembler import assemble
from verify_player import cpu_type, require


ROOT = Path(__file__).resolve().parents[1]
LOAD_ADDRESS = 0x1000
VOICE_FIELDS = tuple(dict.fromkeys(SEQUENCE_FIELDS + SOUND_FIELDS))
INSTRUMENT_FIELDS = ('pulse_word', 'waveform', 'attack_decay', 'sustain_release',
                     'vibrato_depth', 'pulse_value', 'effects')


def data(label, values):
    require(values and all(type(value) is int and 0 <= value <= 255 for value in values),
            f'{label} requires bytes')
    return label + ':\n  .byte ' + ','.join(f'${value:02x}' for value in values) + '\n'


def parameters(description):
    orders, patterns = numeric_tables(description['score'])
    initial = description['initial_state']
    instruments = description['instruments']
    source = data('mo_sid_offsets', [0, 7, 14])
    frequency_bytes = [byte for word in description['frequency_words'] for byte in (word & 255, word >> 8)]
    source += data('mo_frequency_bytes', frequency_bytes)
    references = {}

    def pointers(name, labels):
        nonlocal source
        for suffix, shift in (('lo', 0), ('hi', 8)):
            tokens = []
            for index, (label, offset) in enumerate(labels):
                token = f'MO_{name.upper()}_{index}_{suffix.upper()}'
                references[token] = (label, offset, shift)
                tokens.append(token)
            source += f'mo_{name}_ptr_{suffix}:\n  .byte ' + ','.join(tokens) + '\n'

    pointers('order', [(f'mo_order_{voice}', 0) for voice in range(3)])
    for voice in range(3):
        source += data(f'mo_order_{voice}', orders[voice])
    pointers('pattern', [(f'mo_pattern_{index}', 0) if index in patterns else ('mo_unmapped_value', 0)
                         for index in range(max(patterns) + 1)])
    for index, values in patterns.items():
        source += data(f'mo_pattern_{index}', values)

    aliases = alias_bindings(description['frequency_alias_bindings'])
    lookups = [('mo_frequency_bytes', offset) for offset in range(192)]
    lookups.extend((f'mo_{aliases[offset][1]}', aliases[offset][0]) if offset in aliases
                   else ('mo_unmapped_value', 0) for offset in range(192, 258))
    pointers('lookup', lookups[:256])
    for offset in (256, 257):
        label, index = lookups[offset]
        references[f'MO_ALIAS_{offset}'] = (label, index, None)

    states = {'mo_' + name: [initial['globals'][name]] for name in GLOBAL_FIELDS}
    for name in VOICE_FIELDS:
        if name == 'held_frequency':
            for suffix, shift in (('lo', 0), ('hi', 8)):
                states[f'mo_{name}_{suffix}'] = [(voice[name] >> shift) & 255 for voice in initial['voices']]
        else:
            states['mo_' + name] = [voice[name] for voice in initial['voices']]
    for name in INSTRUMENT_FIELDS:
        if name == 'pulse_word':
            for suffix, shift in (('lo', 0), ('hi', 8)):
                states[f'mo_inst_pulse_{suffix}'] = [(record[name] >> shift) & 255 for record in instruments]
        else:
            states['mo_inst_' + name] = [record[name] for record in instruments]
    for name in ('score_tick', 'append', 'lookup_lo', 'lookup_hi', 'unmapped_value'):
        states['mo_' + name] = [0]
    states['mo_actual_control'] = [0, 0, 0]
    for name in ('tick_lo', 'tick_hi', 'tail', 'tail_age', 'stopped', 'volume_scratch'):
        states['mo_' + name] = [0]
    image = [value for values in states.values() for value in values]
    source += 'mo_state_begin:\n' + ''.join(data(name, values) for name, values in states.items())
    source += 'mo_state_end:\n' + data('mo_initial_state', image)
    source += 'mo_restore_state:\n'
    for offset in range(0, len(image), 255):
        size = min(255, len(image) - offset)
        source += (f'  LDY #$00\nmo_restore_{offset}:\n'
                   f'  LDA mo_initial_state++{offset},Y\n'
                   f'  STA mo_state_begin++{offset},Y\n'
                   f'  INY\n  CPY #${size:02x}\n  BNE mo_restore_{offset}\n')
    source += '  RTS\n'
    return source, references, dict(stateBytes=len(image), instrumentCount=len(instruments),
                                   orderBytes=sum(map(len, orders.values())), patternCount=len(patterns),
                                   patternBytes=sum(map(len, patterns.values())), runtimeScoreScheduler=True)


def assemble_player(description, *, load_address=LOAD_ADDRESS):
    """Validate declared numeric reads before assembling the runtime player.

    The numeric player settles logical table bounds that absolute 6502 readers
    cannot enforce. Generated lookup pointers bind typed aliases to named state
    bytes, so setup, vibrato and late octave reads observe their own stages.

    Supported calls are [0, play_calls), with 1..65535 declared calls. A
    description without an ending produces a bounded diagnostic export;
    indefinite playback is outside that contract. Musical exports require
    the declared finite ending, whose subsequent play calls return silently.
    """
    compiler_contract(description)
    compute_writes(description)
    return _assemble_player(description, load_address=load_address)


def _assemble_player(description, *, load_address=LOAD_ADDRESS):
    require(type(load_address) is int and 0x0400 <= load_address < 0xa000,
            'Payload must remain in callable RAM')
    compiler_contract(description)
    generated, references, sizes = parameters(description)
    ending = ending_contract(description, description['play_calls'])
    # py65 chooses zero-page encodings from values; alias loads must keep their
    # absolute instruction width in both sid_assembler.assemble passes.
    constants = {name: (0xffff if references[name][2] is None else 0) for name in references}
    music_calls = ending['start_call'] if ending is not None else description['play_calls']
    constants.update(MO_HAS_ENDING=int(ending is not None), MO_MUSIC_LO=music_calls & 255,
                     MO_MUSIC_HI=music_calls >> 8)
    source = '\n'.join((ROOT / 'songs/players' / name).read_text()
                       for name in ('monty.asm', 'monty-effects.asm')) + '\n' + generated
    cpu_type()
    _, preliminary, _ = assemble(source, constants, load=load_address)
    constants.update({token: ((preliminary[label] + offset) >> shift) & 255 if shift is not None
                      else preliminary[label] + offset
                      for token, (label, offset, shift) in references.items()})
    payload, symbols, listing = assemble(source, constants, load=load_address)
    require(load_address + len(payload) <= 0xa000, 'Payload must remain in callable RAM')
    return payload, dict(symbols=symbols, source=source, listing=listing, payloadBytes=len(payload),
                         loadAddress=load_address, playCalls=description['play_calls'],
                         supportedCallRange=dict(firstInclusive=0, lastExclusive=description['play_calls']),
                         diagnosticExport=ending is None, indefinitePlaybackSupported=False,
                         originalDriverIncluded=False, registerDumpPlayback=False,
                         finiteMusicalEnding=ending is not None, **sizes)


def compiler_contract(description):
    require(type(description['play_calls']) is int and 1 <= description['play_calls'] <= 65535,
            'Compiled play_calls must be in 1..65535')


def build(description):
    """Return a PAL 6581 PSID containing independently computed score and sound."""
    compiler_contract(description)
    compute_writes(description)
    return _build(description)


def _build(description):
    payload, built = _assemble_player(description)
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 2), (6, 124), (8, LOAD_ADDRESS), (10, built['symbols']['entry_init']),
                          (12, built['symbols']['entry_play']), (14, 1), (16, 1), (118, 0x14)):
        struct.pack_into('>H', header, offset, value)
    for offset, value in ((22, 'Monty independent title study'), (54, 'SID Song Crafter'),
                          (86, '2026 independent reconstruction')):
        header[offset:offset + 31] = value.encode('ascii')[:31].ljust(31, b'\0')
    return bytes(header) + payload, built


def read_state(memory, built):
    """Read named numeric boundary state, excluding assembler scratch and CPU state."""
    symbols = built['symbols']

    def byte(name, index=0):
        return memory.data[symbols[name] + index]

    voices = []
    for index in range(3):
        voice = {}
        for name in VOICE_FIELDS:
            voice[name] = (byte('mo_held_frequency_lo', index) | byte('mo_held_frequency_hi', index) << 8
                           if name == 'held_frequency' else byte('mo_' + name, index))
        voices.append(voice)
    instruments = []
    for index in range(built['instrumentCount']):
        instruments.append({name: (byte('mo_inst_pulse_lo', index) | byte('mo_inst_pulse_hi', index) << 8
                                    if name == 'pulse_word' else byte('mo_inst_' + name, index))
                            for name in INSTRUMENT_FIELDS})
    return dict(finalState=dict(globals={name: byte('mo_' + name) for name in GLOBAL_FIELDS}, voices=voices),
                instruments=instruments, stopped=bool(byte('mo_stopped')))


def run(description_path, output, calls=None):
    from monty_title_player import compute_player

    description_path, output = Path(description_path), Path(output)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh output directory')
    input_data = description_path.read_bytes()
    description = json.loads(input_data)
    compiler_contract(description)
    expected = compute_writes(description)
    sid, built = _build(description)
    count = built['playCalls'] if calls is None else calls
    require(type(count) is int and 1 <= count <= built['playCalls'], 'Requested calls exceed declared range')
    expected = [row for row in expected if row['tick'] is None or row['tick'] < count]
    checkpoint_calls = {call for call in (0, 1, 17535, 17536, 17537, 35071, 35072, count - 1)
                        if call < count}
    ending = ending_contract(description, description['play_calls'])
    if ending is not None:
        start = ending['start_call']
        checkpoint_calls.update(call for call in (start - 1, start, start + 1, start + 63, start + 64,
                                                  start + 67, start + 124) if call < count)
    checkpoints = []

    def observer(cpu, memory):
        boundary = (memory.phase == 'init' and cpu.pc == built['symbols']['mo_init_done']
                    or memory.phase == 'play' and memory.tick in checkpoint_calls
                    and cpu.pc == built['symbols']['mo_call_done'])
        if boundary and cpu.sp == 0xfd:
            checkpoints.append(dict(phase=memory.phase, call=memory.tick, **read_state(memory, built)))

    audit, writes = audit_psid(sid, count, observer=observer)
    identity = lambda rows: [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]
    if identity(expected) != identity(writes):
        for index, (wanted, actual) in enumerate(zip(identity(expected), identity(writes))):
            require(wanted == actual, f'Compiled SID stores differ at {index}: expected {wanted}, observed {actual}')
        raise ValueError(f'Compiled SID store count differs: expected {len(expected)}, observed {len(writes)}')
    require(len(checkpoints) == len(checkpoint_calls) + 1, 'Compiled state checkpoint coverage is incomplete')
    for checkpoint in checkpoints:
        checked_calls = 0 if checkpoint['phase'] == 'init' else checkpoint['call'] + 1
        numeric = compute_player(description, calls=checked_calls)
        for name in ('finalState', 'instruments', 'stopped'):
            require(checkpoint[name] == numeric[name],
                    f'Compiled {name} differs at {checkpoint["phase"]} call {checkpoint["call"]}')
    output.mkdir(parents=True)
    (output / 'reconstructed.sid').write_bytes(sid)
    (output / 'player.asm').write_text(built.pop('source'))
    (output / 'player.listing').write_text(built.pop('listing'))
    report = dict(descriptionPath=str(description_path.resolve()),
                  descriptionSha256=hashlib.sha256(input_data).hexdigest(),
                  sidSha256=hashlib.sha256(sid).hexdigest(), checkedPlayCalls=count,
                  orderedStoreComparison=dict(matchedStores=len(writes), fields=['phase', 'tick', 'address', 'value']),
                  stateComparison=dict(matchedCheckpoints=len(checkpoints),
                                       fields=['globals', 'voices', 'sharedInstrumentBank']),
                  toolSha256={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
                              ('scripts/compose-monty.py', 'songs/players/monty.asm',
                               'songs/players/monty-effects.asm', 'scripts/monty_title_player.py',
                               'scripts/monty_title_score.py', 'scripts/monty_title_programs.py')},
                  limits='Independent compiled state computation; no bus timing, audio or listening claim.', **built)
    for name, value in (('build.json', report), ('audit.json', audit), ('writes.json', writes),
                        ('state-checkpoints.json', checkpoints)):
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
        raise SystemExit(f'Monty compilation failed: {error}')
