"""Compile an editable Flashdance composition into an independent callable PSID."""

import argparse
from enum import IntEnum
import hashlib
import json
from pathlib import Path
import struct

from flashdance_player import CommandKind, EffectKind, compute_writes
from flashdance_programs import PitchMode, PreloadedState, Programs
from psid_audit import audit_psid
from sid_assembler import assemble
from verify_player import require


ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / 'songs/players'
LOAD_ADDRESS = 0x1000


class Opcode(IntEnum):
    INSTRUMENT = 0
    NOTE = 1
    HOLD = 2
    OFF = 3
    VIBRATO = 4
    SLIDE = 5
    SUSTAIN_RELEASE = 6


def data(label, values):
    require(values and all(type(value) is int and 0 <= value <= 255 for value in values),
            f'{label} must contain bytes')
    return label + ':\n  .byte ' + ','.join(f'${value:02x}' for value in values) + '\n'


def table(label, bank, field):
    values = [field(bank[index]) if index in bank else 0 for index in range(max(bank) + 1)]
    return data(label, values)


def encode_commands(commands, bindings):
    """Encode timed musical commands as eight-byte records, never SID stores."""
    records = []
    durations = {}
    for command in commands:
        if 'durationCalls' in command:
            durations.setdefault(command['call'], command['durationCalls'])
    for command in commands:
        kind = CommandKind(command['kind'])
        params = []
        if kind == CommandKind.INSTRUMENT:
            opcode, params = Opcode.INSTRUMENT, [bindings[command['instrument']] // 8]
        elif kind == CommandKind.NOTE:
            opcode, params = Opcode.NOTE, [command['sourceNote'], command['transposeSemitones'] * 2,
                                          int(command['restart'])]
        elif kind == CommandKind.HOLD:
            opcode = Opcode.HOLD
        elif kind == CommandKind.OFF:
            opcode = Opcode.OFF
        elif kind == CommandKind.EFFECT:
            effect, value = EffectKind(command['effect']), command['parameters']
            if effect == EffectKind.VIBRATO:
                opcode, params = Opcode.VIBRATO, [value['remainingNotes'], value['reloadCounter'],
                                                 value['initialCounter'], value['pitchDeltaRightShifts'],
                                                 value['deltaHighByteIncrement']]
            elif effect == EffectKind.PITCH_OFFSET:
                opcode, params = Opcode.SLIDE, [value['remainingNotes'], value['stepWord'] & 255,
                                               value['stepWord'] >> 8]
            elif effect == EffectKind.SUSTAIN_RELEASE_AHEAD:
                delay = durations[command['call']] - value['callsBeforeNextRow']
                opcode, params = Opcode.SUSTAIN_RELEASE, [delay, value['sustainRelease']]
        call = command['call']
        records.extend([call & 255, call >> 8, int(opcode)] + params + [0] * (5 - len(params)))
    records.extend([255, 255, 255, 0, 0, 0, 0, 0])
    return records


def parameters(description, programs, initial):
    source = ''
    for name, field in (
        ('pwm_lower', lambda row: row.lower), ('pwm_upper', lambda row: row.upper),
        ('pwm_step', lambda row: row.step), ('pwm_duration', lambda row: row.duration),
        ('pwm_reset_lo', lambda row: (row.reset_width or 0) & 255),
        ('pwm_reset_hi', lambda row: (row.reset_width or 0) >> 8),
        ('pwm_reset', lambda row: int(row.reset_width is not None)), ('pwm_hold', lambda row: int(row.hold)),
    ):
        source += table(name, programs.pwm_rows, field)
    for name, field in (
        ('filter_lower_table', lambda row: row.lower), ('filter_upper_table', lambda row: row.upper),
        ('filter_step_table', lambda row: row.step), ('filter_duration_table', lambda row: row.duration),
        ('filter_reset_cutoff_table', lambda row: row.reset_cutoff or 0),
        ('filter_reset_table', lambda row: int(row.reset_cutoff is not None)),
        ('filter_hold_table', lambda row: int(row.hold)),
    ):
        source += table(name, programs.filter_rows, field)
    for name, field in (
        ('wave_note', lambda row: row.note), ('wave_control_table', lambda row: row.control),
        ('wave_mode', lambda row: int(row.mode == PitchMode.ABSOLUTE)),
        ('wave_jump', lambda row: row.jump or 0), ('wave_is_jump', lambda row: int(row.jump is not None)),
    ):
        source += table(name, programs.wave_rows, field)
    instruments = {offset // 8: row for offset, row in programs.instruments.items()}
    for name, attribute in (('instrument_ad', 'attack_decay'), ('instrument_sr', 'sustain_release'),
                            ('instrument_filter_command', 'filter_command'), ('instrument_filter_row', 'filter_row'),
                            ('instrument_pwm_row', 'pwm_row'), ('instrument_wave_row', 'wave_row')):
        source += table(name, instruments, lambda row: getattr(row, attribute))
    source += data('frequency_table_lo', [word & 255 for word in programs.frequency_words])
    source += data('frequency_table_hi', [word >> 8 for word in programs.frequency_words])
    source += data('fd_voice_offsets', [0, 7, 14])
    source += data('fd_voice_filter_bits', [1, 2, 4])
    source += data('fd_voice_filter_masks', [254, 253, 251])
    source += 'fd_score_starts:\n  .word fd_score_0,fd_score_1,fd_score_2\n'
    for voice, name in enumerate(('bass', 'lead', 'chord')):
        source += data(f'fd_score_{voice}', encode_commands(description['score']['roles'][name]['commands'],
                                                          description['instrumentBindings']))
    states = {}
    for name, field in (
        ('pulse_lower', lambda voice: voice.pwm.lower), ('pulse_upper', lambda voice: voice.pwm.upper),
        ('pulse_step', lambda voice: voice.pwm.step), ('pulse_direction', lambda voice: voice.pwm.direction),
        ('pulse_row', lambda voice: voice.pwm.row), ('pulse_remaining', lambda voice: voice.pwm.remaining),
        ('pulse_lo', lambda voice: voice.pwm.width & 255), ('pulse_hi', lambda voice: voice.pwm.width >> 8),
        ('wave_row', lambda voice: voice.wave_row),
    ):
        states[name] = [field(voice) for voice in initial.voices]
    for name in ('base_note', 'transpose', 'gate_mask', 'frequency_lo', 'frequency_hi',
                 'wave_control', 'absolute_pitch', 'instrument', 'fd_score_lo', 'fd_score_hi',
                 'fd_pending_sr', 'fd_sr_tick_lo', 'fd_sr_tick_hi', 'fd_sr_value'):
        states[name] = [0] * 3
    states['tuning'] = [description['score']['roles'][name]['fineTuneWord'] for name in ('bass', 'lead', 'chord')]
    for name, field in (
        ('slide_enabled', lambda value: value['slide']['enabled']),
        ('slide_step_lo', lambda value: value['slide']['step'] & 255),
        ('slide_step_hi', lambda value: value['slide']['step'] >> 8),
        ('slide_subtract', lambda value: int(value['slide']['subtract'])),
        ('slide_offset_lo', lambda value: value['slide']['offset'] & 255),
        ('slide_offset_hi', lambda value: value['slide']['offset'] >> 8),
        ('vibrato_enabled', lambda value: value['vibrato']['enabled']),
        ('vibrato_interval', lambda value: value['vibrato']['interval']),
        ('vibrato_remaining', lambda value: value['vibrato']['remaining']),
        ('vibrato_direction', lambda value: value['vibrato']['direction']),
        ('vibrato_shift', lambda value: value['vibrato']['shift']),
        ('vibrato_growth', lambda value: value['vibrato']['growth']),
        ('vibrato_depth', lambda value: value['vibrato']['depth']),
        ('vibrato_offset_lo', lambda value: value['vibrato']['offset'] & 255),
        ('vibrato_offset_hi', lambda value: value['vibrato']['offset'] >> 8),
    ):
        states[name] = [field(value) for value in description['initialEffects']]
    for name, attribute in (('filter_lower', 'lower'), ('filter_upper', 'upper'), ('filter_step', 'step'),
                            ('filter_direction', 'direction'), ('filter_row', 'row'),
                            ('filter_remaining', 'remaining'), ('filter_cutoff', 'cutoff')):
        states[name] = [getattr(initial.filter, attribute)]
    fade_start = description['score']['range']['stopCall'] + description['ending']['releaseCalls']
    states.update(fd_tick_lo=[0], fd_tick_hi=[0], fd_ended=[0], fd_tail=[0], fd_restart=[0],
                  fd_volume=[description['initialVolume']], fd_routing=[description['initialRouting']],
                  fd_filter_mode=[0], fd_fade_tick_lo=[fade_start & 255], fd_fade_tick_hi=[fade_start >> 8],
                  fd_tmp_lo=[0], fd_tmp_hi=[0])
    defaults = [value for values in states.values() for value in values]
    require(0 < len(defaults) < 256, 'Mutable player state must fit its byte-indexed initialization image')
    source += 'fd_state_begin:\n'
    source += ''.join(data(name, values) for name, values in states.items())
    source += 'fd_state_end:\n' + data('fd_initial_state', defaults)
    return source, len(defaults)


def build(description):
    """Build from semantic data only; source annotations cannot affect output."""
    try:
        compute_writes(description, calls=1)
        stop = description['score']['range']['stopCall']
        end = stop + description['ending']['releaseCalls'] + 16 * description['ending']['fadeStepCalls']
        compute_writes(description, calls=end + 1)
    except IndexError as error:
        raise ValueError('Composition pitch lies outside its frequency table') from error
    programs = Programs.from_dict(description['programs'])
    initial = PreloadedState.from_dict(description['preloaded'], programs)
    generated, state_bytes = parameters(description, programs, initial)
    constants = {f'FD_CMD_{opcode.name}': int(opcode) for opcode in Opcode}
    constants.update(FD_STATE_BYTES=state_bytes, FD_FILTER_OWNER=programs.filter_owner,
                     FD_STOP_LO=stop & 255, FD_STOP_HI=stop >> 8, FD_END_LO=end & 255, FD_END_HI=end >> 8,
                     FD_FADE_STEP=description['ending']['fadeStepCalls'])
    source = '\n'.join((PLAYER / name).read_text() for name in
                       ('flashdance.asm', 'flashdance-programs.asm', 'flashdance-pitch.asm')) + '\n' + generated
    payload, symbols, listing = assemble(source, constants, load=LOAD_ADDRESS)
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 2), (6, 124), (8, LOAD_ADDRESS), (10, symbols['entry_init']),
                          (12, symbols['entry_play']), (14, 1), (16, 1), (118, 0x14)):
        struct.pack_into('>H', header, offset, value)
    for offset, value in ((22, 'Flashdance independent SID study'), (54, 'SID Song Crafter'),
                          (86, '2026 independent reconstruction')):
        header[offset:offset + 31] = value.encode('ascii')[:31].ljust(31, b'\0')
    return bytes(header) + payload, {
        'symbols': symbols, 'payloadBytes': len(payload), 'source': source, 'listing': listing,
        'stopCall': stop, 'endCall': end, 'scoreRecordBytes': 8,
        'originalDriverIncluded': False, 'registerDumpPlayback': False,
    }


def run(composition, output, calls=None):
    composition, output = Path(composition), Path(output)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh output directory')
    encoded = composition.read_bytes()
    description = json.loads(encoded)
    sid, built = build(description)
    calls = built['endCall'] + 1 if calls is None else calls
    expected = compute_writes(description, calls=calls)
    audit, writes = audit_psid(sid, calls)
    identity = lambda rows: [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]
    require(identity(expected) == identity(writes), 'Compiled ordered SID writes differ from the computed model')
    output.mkdir(parents=True)
    (output / 'reconstructed.sid').write_bytes(sid)
    (output / 'player.asm').write_text(built.pop('source'))
    (output / 'player.listing').write_text(built.pop('listing'))
    report = {
        'compositionPath': str(composition.resolve()), 'compositionSha256': hashlib.sha256(encoded).hexdigest(),
        'sidSha256': hashlib.sha256(sid).hexdigest(), 'playCalls': calls,
        'orderedWriteComparison': {'matchedWrites': len(writes), 'sameCallAddressValueOrder': True,
                                   'allSoundRegisters': True, 'exactCycleEquality': False},
        'limits': 'Computed independent synthesis and CPU execution only; no original driver or register replay. Instruction timing, VICE execution, audio rendering and listening acceptance require separate evidence.',
        **built,
    }
    for name, value in (('build.json', report), ('audit.json', audit), ('writes.json', writes)):
        with (output / name).open('x', encoding='utf-8') as target:
            json.dump(value, target, indent=None if name == 'writes.json' else 2, allow_nan=False)
            target.write('\n')
    print(f'Independent Flashdance player: {output}')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('composition', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calls', type=int, help='Override the default complete score, tail and first silent call')
    args = parser.parse_args()
    run(args.composition, args.output, args.calls)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, IndexError) as error:
        raise SystemExit(f'Flashdance compilation failed: {error}')
