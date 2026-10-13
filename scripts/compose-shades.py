"""Compile editable Shades patterns and programs into an independent CIA PSID."""

import argparse
from enum import IntEnum
import hashlib
import json
from pathlib import Path
import struct

from shades_player import Player, compute, score_module
from shades_programs import PortamentoMode, RowKind
from sid_assembler import assemble
from verify_player import cpu_type, require


ROOT = Path(__file__).resolve().parents[1]
LOAD_ADDRESS = 0x1000


class Mode(IntEnum):
    TARGET = 0
    DOWN = 1
    UP = 2


def data(label, values):
    require(values and all(type(value) is int and 0 <= value <= 255 for value in values),
            f'{label} requires bytes')
    return label + ':\n  .byte ' + ','.join(f'${value:02x}' for value in values) + '\n'


def parameters(score, player):
    names = list(dict.fromkeys(order['instrument'] for order in score['orders']))
    require(len(names) <= 85, 'Compiled voice parameter tables support at most 85 selected blocks')
    blocks = [player.programs.blocks[name] for name in names]
    modes = {mode.value: int(Mode[mode.name]) for mode in PortamentoMode}
    source = ''
    patches = [voice for block in blocks for voice in block.voices]
    fields = ('control', 'attack_decay', 'sustain_release', 'pulse_up_calls', 'pulse_down_calls',
              'pulse_step', 'vibrato_delay', 'vibrato_extent', 'vibrato_step', 'fine_tune')
    for field in fields:
        source += data('sd_patch_' + field, [getattr(patch, field) for patch in patches])
    for field in ('pulse_width', 'portamento_step'):
        for suffix, shift in (('lo', 0), ('hi', 8)):
            source += data(f'sd_patch_{field}_{suffix}', [(getattr(patch, field) >> shift) & 255 for patch in patches])
    source += data('sd_patch_mode', [modes[patch.portamento_mode] for patch in patches])
    for field in ('routing', 'mode_volume', 'trigger_mask', 'percussion_mode_volume'):
        source += data('sd_block_' + field, [getattr(block.filter, field) for block in blocks])
    source += data('sd_block_percussion_control', [block.percussion_control for block in blocks])
    for variant in ('contour', 'percussion_contour'):
        for field in ('cutoff_low', 'cutoff_high', 'up_calls', 'down_calls', 'fine_step', 'coarse_step'):
            source += data(f'sd_{variant}_{field}', [getattr(getattr(block.filter, variant), field) for block in blocks])
    source += data('sd_frequency_table_lo', [word & 255 for word in player.programs.frequency_words])
    source += data('sd_frequency_table_hi', [word >> 8 for word in player.programs.frequency_words])
    source += data('sd_voice_offsets', [0, 7, 14]) + data('sd_voice_bits', [1, 2, 4])
    pattern_names = {name: f'sd_pattern_{index}' for index, name in enumerate(score['patterns'])}
    for name, pattern in score['patterns'].items():
        source += data(pattern_names[name], [score_module.row_byte(row) for row in pattern['rows']])
    source += 'sd_order_base:\n  .word sd_orders\nsd_orders:\n'
    for order in score['orders']:
        source += '  .word ' + ','.join(pattern_names[name] for name in order['patternIds']) + '\n'
        fade = order['fade']
        fade_byte = {'retain': 0, 'cancel': 1}.get(fade['kind'], fade.get('rowInterval'))
        record = ([value & 255 for value in order['transposeSemitones']] +
                  [names.index(order['instrument']), int(order['voice1HighNotesAbsolute']),
                   order['rowCount'] & 255, order['rowDurationCalls'] & 255,
                   order['timerHigh'], fade_byte, 0])
        source += '  .byte ' + ','.join(f'${value:02x}' for value in record) + '\n'
    states = {}
    for field in ('frequency', 'target_frequency', 'pulse_width', 'portamento_step'):
        for suffix, shift in (('lo', 0), ('hi', 8)):
            states[f'sd_{field}_{suffix}'] = [(getattr(voice, field) >> shift) & 255 for voice in player.state.voices]
    for field in ('control', 'attack_decay', 'sustain_release', 'pulse_up_calls', 'pulse_down_calls',
                  'pulse_step', 'vibrato_delay', 'vibrato_extent', 'vibrato_step', 'vibrato_phase'):
        states['sd_' + field] = [getattr(voice, field) for voice in player.state.voices]
    states['sd_mode'] = [modes[voice.portamento_mode] for voice in player.state.voices]
    states['sd_last_row'] = [{RowKind.REST: 0, RowKind.HOLD: 1, RowKind.NOTE: 2}[voice.last_row]
                             for voice in player.state.voices]
    for field, value in vars(player.state.filter).items():
        states['sd_filter_' + field] = [value]
    states['sd_percussion'] = [int(player.state.percussion_active)]
    for field in ('pattern_lo', 'pattern_hi', 'transpose'):
        states['sd_' + field] = [0] * 3
    for field in ('tick_lo', 'tick_hi', 'ended', 'order', 'row', 'rows_left', 'duration',
                  'counter', 'select_pending', 'block', 'absolute', 'fade_interval', 'fade_countdown',
                  'fade_volume', 'tmp_lo', 'tmp_hi', 'note', 'gate', 'previous', 'patch_index'):
        states['sd_' + field] = [0]
    initial = [value for values in states.values() for value in values]
    require(len(initial) < 256, 'Named initialization state exceeds its byte-indexed image')
    source += 'sd_state_begin:\n' + ''.join(data(name, values) for name, values in states.items())
    source += 'sd_state_end:\n' + data('sd_initial_state', initial)
    return source, len(initial), len(names), sum(len(row['rows']) for row in score['patterns'].values())


def assemble_player(score, programs, *, load_address=LOAD_ADDRESS):
    """Assemble compact semantic patterns, orders and independently computed effects."""
    player = Player(score, programs)
    generated, state_bytes, block_count, token_count = parameters(score, player)
    constants = dict(SD_STATE_BYTES=state_bytes, SD_STOP_LO=player.stop_call & 255,
                     SD_STOP_HI=player.stop_call >> 8)
    source = '\n'.join((ROOT / 'songs/players' / name).read_text()
                       for name in ('shades.asm', 'shades-effects.asm')) + '\n' + generated
    # The shared loader locates the pinned local dependency without requiring
    # callers to manage PYTHONPATH; assembly itself uses sid_assembler's parser.
    cpu_type()
    payload, symbols, listing = assemble(source, constants, load=load_address)
    require(not (load_address < 0x0c00 and load_address + len(payload) > 0x0800),
            'Player payload overlaps the CIA host workspace $0800-$0bff')
    return payload, dict(symbols=symbols, source=source, listing=listing, payloadBytes=len(payload),
                         loadAddress=load_address, stopCall=player.stop_call, stateBytes=state_bytes,
                         patternTokens=token_count, orders=len(score['orders']), blocks=block_count,
                         originalDriverIncluded=False, registerDumpPlayback=False)


def build(score, programs):
    payload, built = assemble_player(score, programs)
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 2), (6, 124), (8, LOAD_ADDRESS), (10, built['symbols']['entry_init']),
                          (12, built['symbols']['entry_play']), (14, 1), (16, 1), (118, 0x14)):
        struct.pack_into('>H', header, offset, value)
    struct.pack_into('>I', header, 18, 1)
    for offset, value in ((22, 'Shades independent SID study'), (54, 'SID Song Crafter'),
                          (86, '2026 independent reconstruction')):
        header[offset:offset + 31] = value.encode('ascii')[:31].ljust(31, b'\0')
    return bytes(header) + payload, built


def run(score_path, programs_path, output, calls=None):
    from shades_audit import audit_candidate
    score_path, programs_path, output = Path(score_path), Path(programs_path), Path(output)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh output directory')
    score_data, program_data = score_path.read_bytes(), programs_path.read_bytes()
    score, programs = json.loads(score_data), json.loads(program_data)
    sid, built = build(score, programs)
    count = built['stopCall'] + 1 if calls is None else calls
    require(type(count) is int and 1 <= count <= built['stopCall'] + 1, 'Requested calls exceed the declared score and stop')
    expected = compute(score, programs, calls=count, include_stop=True)
    audit, writes = audit_candidate(sid, count)
    identity = lambda rows: [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]
    require(identity(expected) == identity(writes), 'Compiled ordered SID/timer stores differ from the semantic model')
    output.mkdir(parents=True)
    (output / 'reconstructed.sid').write_bytes(sid)
    (output / 'player.asm').write_text(built.pop('source'))
    (output / 'player.listing').write_text(built.pop('listing'))
    report = dict(scorePath=str(score_path.resolve()), programsPath=str(programs_path.resolve()),
                  scoreSha256=hashlib.sha256(score_data).hexdigest(),
                  programsSha256=hashlib.sha256(program_data).hexdigest(),
                  sidSha256=hashlib.sha256(sid).hexdigest(), playCalls=count,
                  orderedStoreComparison=dict(matchedStores=len(writes), fields=['phase', 'tick', 'address', 'value']),
                  limits='Independent compiled state computation; no bus timing, audio or listening claim.', **built)
    for name, value in (('build.json', report), ('audit.json', audit), ('writes.json', writes)):
        with (output / name).open('x') as handle:
            json.dump(value, handle, indent=None if name == 'writes.json' else 2, allow_nan=False)
            handle.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('score', type=Path)
    parser.add_argument('--programs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calls', type=int)
    args = parser.parse_args()
    print(json.dumps(run(args.score, args.programs, args.output, args.calls), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f'Shades compilation failed: {error}')
