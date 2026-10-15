"""Compile an editable Rambo loader graph into a PAL mono or bass-split PSID."""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import struct
from time import perf_counter

from psid_audit import audit_psid
from rambo_player import LoaderPlayer, MorsePhase, sound_state
from rambo_score import InstructionKind
from sid_assembler import assemble
from verify_player import cpu_type, require


ROOT = Path(__file__).resolve().parents[1]
LOAD_ADDRESS = 0x1000
KINDS = tuple(InstructionKind)
PHASES = tuple(MorsePhase)
COPY_LAYOUT = {'volume': (24, 5), 'write-data': (0, 29), 'frequency': (0, 14),
               'pulse': (14, 10), 'chord': (0, 10)}
HOOKS = ('increment-transpose', 'morse-pitch-one', 'morse-pitch-two', 'start-morse')
STEREO_VOICE_CHIPS = (0, 1, 0)
STEREO_VOICE_OFFSETS = (0, 39, 14)


def data(label, values):
    require(values and all(type(value) is int and 0 <= value <= 255 for value in values),
            f'{label} requires bytes')
    return label + ':\n  .byte ' + ','.join(f'${value:02x}' for value in values) + '\n'


def compiler_contract(description):
    calls = description.get('range', {}).get('auditCalls')
    require(type(calls) is int and 1 <= calls <= 100000, 'Declared auditCalls must be in 1..100000')
    require(len(description.get('morse', {}).get('letters', [])) <= 256,
            'Morse letters must fit a byte index')
    LoaderPlayer(description)


def model_state(player):
    """Retain every mutable numeric input and graph state, excluding operation logs."""
    return dict(data=deepcopy(player.data), sound=deepcopy(player.sound),
                sounds=[sound_state(block) for block in player.sound],
                score=deepcopy(player.score.voices), activeMask=player.score.active_mask,
                morseActive=player.morse_active, morsePhase=player.morse_phase.value)


def stereo_writes(writes, volume):
    """Route the independent bass while preserving the source oscillator groups.

    SID sync/ring recipients depend on the preceding physical oscillator;
    docs/research/sid/advanced-techniques.md owns this hardware constraint.
    Shared filtering and live globals require a separate arrangement contract.
    """
    result = [dict(phase='init', tick=None, address=0xd438, value=volume)]
    result.extend(dict(phase='init', tick=None, address=0xd420 + offset, value=0)
                  for offset in range(23, -1, -1))
    for row in writes:
        address = row['address']
        require(0xd400 <= address <= 0xd418, 'Stereo bass requires source writes in its declared SID bank')
        if address in (0xd415, 0xd416, 0xd417, 0xd418):
            require(row['value'] == 0 if address < 0xd418 else row['phase'] == 'init',
                    'Stereo bass does not support source shared filter or live global changes')
        if address in (0xd404, 0xd40b, 0xd412) and row['value'] & 6:
            voice = (address - 0xd404) // 7
            modulator = (voice + 2) % 3
            require(STEREO_VOICE_CHIPS[voice] == STEREO_VOICE_CHIPS[modulator],
                    f'Stereo bass rejects cross-chip oscillator coupling on source voice {voice + 1}')
        if row['phase'] == 'play' and 0xd407 <= address <= 0xd40d:
            result.append(dict(row, address=address + 32))
        else:
            result.append(row)
    return result


def numeric_run(description, checkpoint_calls=(), *, stereo_bass=False):
    player = LoaderPlayer(description)
    checkpoints = {0: model_state(player)}
    for call in range(description['range']['auditCalls']):
        player.play(call)
        if call + 1 in checkpoint_calls:
            checkpoints[call + 1] = model_state(player)
    writes = stereo_writes(player.writes, description['initialization']['volume']) if stereo_bass else player.writes
    return dict(writes=writes, checkpoints=checkpoints)


def parameters(description, *, stereo_bass=False):
    program = description['program']
    nodes = {node_id: f'rb_node_{index}' for index, node_id in enumerate(program)}
    banks = {bank_id: f'rb_bank_{index}' for index, bank_id in enumerate(description['dataBanks'])}
    source = data('rb_sid_offsets', STEREO_VOICE_OFFSETS if stereo_bass else [0, 7, 14]) + data('rb_voice_bits', [1, 2, 4])
    source += data('rb_stack_bases', [0, 8, 16])
    frequency = description['frequencyWords'] + [0] * (256 - len(description['frequencyWords']))
    source += data('rb_frequency_lo', [word & 255 for word in frequency])
    source += data('rb_frequency_hi', [word >> 8 for word in frequency])
    source += data('rb_morse_letters', description['morse']['letters'])
    source += data('rb_morse_codes', description['morse']['codes'])
    pitches = [description['morse']['initialFrequency']] + description['morse']['pitchChanges']
    source += data('rb_morse_pitch_lo', [pitch & 255 for pitch in pitches])
    source += data('rb_morse_pitch_hi', [pitch >> 8 for pitch in pitches])
    references = {}

    def pointer(label):
        if label is None:
            return ['$00', '$00']
        tokens = []
        for suffix, shift in (('lo', 0), ('hi', 8)):
            token = f'RB_REF_{len(references)}'
            references[token] = label, shift
            tokens.append(token)
        return tokens

    def pointer_table(name, labels):
        pairs = [pointer(label) for label in labels]
        return ''.join(f'rb_{name}_ptr_{suffix}:\n  .byte ' + ','.join(pair[index] for pair in pairs) + '\n'
                       for index, suffix in enumerate(('lo', 'hi')))

    source += pointer_table('data', [f'rb_data_{voice}' for voice in range(3)])
    source += pointer_table('sound', [f'rb_sound_{voice}' for voice in range(3)])
    source += pointer_table('kind', [f'rb_kind_{kind.value.replace("-", "_")}' for kind in KINDS])
    states = {'rb_active_mask': [7], 'rb_morse_active': [0], 'rb_morse_phase': [0],
              'rb_remaining': [voice['remaining'] for voice in description['voices']],
              'rb_transpose': [voice['transpose'] for voice in description['voices']],
              'rb_stack_index': [voice['stackIndex'] for voice in description['voices']]}
    cursors = [pointer(nodes[voice['cursor']]) for voice in description['voices']]
    returns = [pointer(nodes[slot['returnNode']] if slot['returnNode'] else None)
               for voice in description['voices'] for slot in voice['stack']]
    for suffix in ('lo', 'hi'):
        index = 0 if suffix == 'lo' else 1
        states['rb_cursor_' + suffix] = [pair[index] for pair in cursors]
        states['rb_return_' + suffix] = [pair[index] for pair in returns]
    states['rb_repeat'] = [slot['repeatRemaining'] for voice in description['voices'] for slot in voice['stack']]
    for voice in range(3):
        states[f'rb_data_{voice}'] = description['initialData'][voice]
        states[f'rb_sound_{voice}'] = description['initialSound'][voice]
    image = [value for values in states.values() for value in values]

    def mixed_data(label, values):
        return label + ':\n  .byte ' + ','.join(f'${value:02x}' if type(value) is int else value
                                               for value in values) + '\n'

    source += 'rb_state_begin:\n' + ''.join(mixed_data(name, values) for name, values in states.items())
    source += 'rb_state_end:\n' + mixed_data('rb_initial_state', image)
    source += 'rb_restore_state:\n'
    for offset in range(0, len(image), 255):
        size = min(255, len(image) - offset)
        source += (f'  LDY #$00\nrb_restore_{offset}:\n'
                   f'  LDA rb_initial_state++{offset},Y\n  STA rb_state_begin++{offset},Y\n'
                   f'  INY\n  CPY #${size:02x}\n  BNE rb_restore_{offset}\n')
    if stereo_bass:
        source += ('  LDA #RB_INITIAL_VOLUME\n  STA $d438\n  LDX #$17\n  LDA #$00\n'
                   'rb_init_secondary_clear:\n  STA $d420,X\n  DEX\n  BPL rb_init_secondary_clear\n')
    source += '  RTS\n'
    for node_id, node in program.items():
        kind = node['kind']
        args, target = [0, 0], None
        if kind == 'row':
            args = [node['sourceNote'], node['duration']]
        elif kind in ('transpose', 'call-transposed', 'jump-transposed'):
            args[0] = node['transpose']
        elif kind == 'loop':
            args[0] = node['repeat']
        elif kind in ('poke-data', 'poke-sound'):
            args = [node['offset'], node['value']]
        elif kind == 'code':
            args[0] = HOOKS.index(node['codeId'])
        elif kind in COPY_LAYOUT:
            destination, width = COPY_LAYOUT[kind]
            args = [width, destination]
            target = banks[node['dataId']]
        if 'target' in node:
            target = nodes[node['target']]
        values = [KINDS.index(InstructionKind(kind)),
                  *pointer(nodes[node['next']] if 'next' in node else None), *args, *pointer(target)]
        source += mixed_data(nodes[node_id], values)
    source += ''.join(data(banks[bank_id], values) for bank_id, values in description['dataBanks'].items())
    return source, references, dict(stateBytes=len(image), graphNodeCount=len(program),
                                   graphRecordBytes=7, graphBytes=7 * len(program),
                                   dataBankBytes=sum(map(len, description['dataBanks'].values())),
                                   runtimeScoreScheduler=True, nodeLabels=nodes)


def _assemble_player(description, *, load_address=LOAD_ADDRESS, sid_base=0xd400, stereo_bass=False):
    require(type(load_address) is int and 0x0400 <= load_address < 0xa000,
            'Payload must remain in callable RAM')
    require(type(sid_base) is int and sid_base in (0xd400, 0xd420),
            'SID base must be $D400 or $D420')
    require(not stereo_bass or sid_base == 0xd400,
            'The stereo-bass layout cannot be combined with SID relocation')
    generated, references, sizes = parameters(description, stereo_bass=stereo_bass)
    constants = {name: 0 for name in references}
    constants['RB_INITIAL_VOLUME'] = description['initialization']['volume']
    source = '\n'.join((ROOT / 'songs/players' / name).read_text()
                       for name in ('rambo.asm', 'rambo-sound.asm')) + '\n' + generated
    if sid_base != 0xd400:
        for offset in range(25):
            name = f'RB_SID_REGISTER_{offset:02X}'
            source = source.replace(f'${0xd400 + offset:04x}', name)
            constants[name] = sid_base + offset
    cpu_type()
    _, preliminary, _ = assemble(source, constants, load=load_address)
    constants.update({name: (preliminary[label] >> shift) & 255
                      for name, (label, shift) in references.items()})
    payload, symbols, listing = assemble(source, constants, load=load_address)
    require(load_address + len(payload) <= 0xa000, 'Payload must remain in callable RAM')
    layout = dict(outputLayout='stereo-bass', sidBases=[0xd400, 0xd420]) if stereo_bass else {}
    return payload, dict(symbols=symbols, source=source, listing=listing, loadAddress=load_address,
                         sidBase=sid_base, voiceSidOffsets=list(STEREO_VOICE_OFFSETS if stereo_bass else (0, 7, 14)),
                         payloadBytes=len(payload), playCalls=description['range']['auditCalls'],
                         originalDriverIncluded=False, registerDumpPlayback=False,
                         supportedCallRange=dict(firstInclusive=0, lastExclusive=description['range']['auditCalls']),
                         indefinitePlaybackSupported=False,
                         endingMechanism='Top-level score returns and sound lifetimes; no added fade', **sizes, **layout)


def assemble_player(description, *, load_address=LOAD_ADDRESS, sid_base=0xd400, stereo_bass=False):
    compiler_contract(description)
    numeric_run(description, stereo_bass=stereo_bass)
    return _assemble_player(description, load_address=load_address, sid_base=sid_base, stereo_bass=stereo_bass)


def _build(description, *, stereo_bass=False):
    payload, built = _assemble_player(description, stereo_bass=stereo_bass)
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 3 if stereo_bass else 2), (6, 124), (8, LOAD_ADDRESS), (10, built['symbols']['entry_init']),
                          (12, built['symbols']['entry_play']), (14, 1), (16, 1), (118, 0x54 if stereo_bass else 0x14)):
        struct.pack_into('>H', header, offset, value)
    if stereo_bass:
        header[122] = 0x42
    for offset, value in ((22, 'Rambo bass-split stereo' if stereo_bass else 'Rambo independent loader'), (54, 'SID Song Crafter'),
                          (86, '2026 independent reconstruction')):
        header[offset:offset + 31] = value.encode('ascii')[:31].ljust(31, b'\0')
    return bytes(header) + payload, built


def build(description, *, stereo_bass=False):
    compiler_contract(description)
    numeric_run(description, stereo_bass=stereo_bass)
    return _build(description, stereo_bass=stereo_bass)


def read_state(memory, built):
    symbols = built['symbols']
    reverse = {symbols[label]: node_id for node_id, label in built['nodeLabels'].items()}

    def byte(label, index=0):
        return memory.data[symbols[label] + index]

    def node(lo, hi, index):
        address = byte(lo, index) | byte(hi, index) << 8
        require(address == 0 or address in reverse, 'Compiled state pointer escapes the instruction graph')
        return reverse[address] if address else None

    data_blocks = [[byte(f'rb_data_{voice}', offset) for offset in range(49)] for voice in range(3)]
    sound_blocks = [[byte(f'rb_sound_{voice}', offset) for offset in range(39)] for voice in range(3)]
    voices = [dict(cursor=node('rb_cursor_lo', 'rb_cursor_hi', voice),
                   remaining=byte('rb_remaining', voice), transpose=byte('rb_transpose', voice),
                   stackIndex=byte('rb_stack_index', voice),
                   stack=[dict(returnNode=node('rb_return_lo', 'rb_return_hi', voice * 8 + slot),
                               repeatRemaining=byte('rb_repeat', voice * 8 + slot)) for slot in range(8)])
              for voice in range(3)]
    return dict(data=data_blocks, sound=sound_blocks, sounds=[sound_state(block) for block in sound_blocks],
                score=voices, activeMask=byte('rb_active_mask'), morseActive=bool(byte('rb_morse_active')),
                morsePhase=PHASES[byte('rb_morse_phase')].value)


def check_sid_writer(cpu, memory):
    """Require the executed SID stores supported by trace-sid-vice.py's decoder."""
    opcode = memory.data[cpu.pc]
    mnemonic, mode = cpu.disassemble[opcode]
    if mnemonic not in ('STA', 'STX', 'STY'):
        return None
    operand = memory.data[(cpu.pc + 1) & 65535]
    if mode in ('abs', 'abx', 'aby'):
        address = operand | memory.data[(cpu.pc + 2) & 65535] << 8
        address += cpu.x if mode == 'abx' else cpu.y if mode == 'aby' else 0
    elif mode in ('inx', 'iny'):
        pointer = (operand + cpu.x) & 255 if mode == 'inx' else operand
        address = memory.data[pointer] | memory.data[(pointer + 1) & 255] << 8
        address += cpu.y if mode == 'iny' else 0
    else:
        return None
    address &= 65535
    if not any(base <= address <= base + 31 for base in memory.sid_bases):
        return None
    require(opcode in (0x8d, 0x9d, 0x99, 0x8e, 0x8c),
            f'SID writer at ${cpu.pc:04x} requires a trace-supported non-RMW absolute store')
    return cpu.pc, opcode, address


def run(description_path, output, calls=None, *, stereo_bass=False):
    description_path, output = Path(description_path), Path(output)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh output directory')
    input_data = description_path.read_bytes()
    description = json.loads(input_data)
    compiler_contract(description)
    count = description['range']['auditCalls'] if calls is None else calls
    require(type(count) is int and 1 <= count <= description['range']['auditCalls'],
            'Requested calls exceed declared range')
    checkpoint_calls = {call for call in (0, 1, 49, 50, 51, 10813, 10814, 10815, count - 1) if call < count}
    stages = {}
    started = perf_counter()
    numeric = numeric_run(description, {call + 1 for call in checkpoint_calls}, stereo_bass=stereo_bass)
    stages['model'] = perf_counter() - started
    started = perf_counter()
    sid, built = _build(description, stereo_bass=stereo_bass)
    stages['assembly'] = perf_counter() - started
    checkpoints = []
    writer_sites = {}
    writer_store_count = 0

    def observer(cpu, memory):
        nonlocal writer_store_count
        writer = check_sid_writer(cpu, memory)
        if writer is not None:
            pc, opcode, address = writer
            writer_sites.setdefault(pc, dict(opcode=opcode, addresses=set()))['addresses'].add(address)
            writer_store_count += 1
        boundary = (memory.phase == 'init' and cpu.pc == built['symbols']['rb_init_done']
                    or memory.phase == 'play' and memory.tick in checkpoint_calls
                    and cpu.pc == built['symbols']['rb_call_done'])
        if boundary and cpu.sp == 0xfd:
            checkpoints.append(dict(phase=memory.phase, call=memory.tick, state=read_state(memory, built)))

    started = perf_counter()
    audit, writes = audit_psid(sid, count, observer=observer)
    stages['cpuAudit'] = perf_counter() - started
    started = perf_counter()
    identity = lambda rows: [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]
    expected = [row for row in numeric['writes'] if row['tick'] is None or row['tick'] < count]
    for index, (wanted, actual) in enumerate(zip(identity(expected), identity(writes))):
        require(wanted == actual, f'Compiled SID stores differ at {index}: expected {wanted}, observed {actual}')
    require(len(expected) == len(writes), f'Compiled store count differs: expected {len(expected)}, observed {len(writes)}')
    require(writer_store_count == len(writes), 'Executed SID writer coverage is incomplete')
    require(len(checkpoints) == len(checkpoint_calls) + 1, 'Compiled state checkpoint coverage is incomplete')
    for checkpoint in checkpoints:
        calls_at_boundary = 0 if checkpoint['phase'] == 'init' else checkpoint['call'] + 1
        require(checkpoint['state'] == numeric['checkpoints'][calls_at_boundary],
                f'Compiled state differs at {checkpoint["phase"]} call {checkpoint["call"]}')
    stages['checkpointComparison'] = perf_counter() - started
    started = perf_counter()
    output.mkdir(parents=True)
    (output / 'reconstructed.sid').write_bytes(sid)
    (output / 'player.asm').write_text(built.pop('source'))
    (output / 'player.listing').write_text(built.pop('listing'))
    report = dict(descriptionPath=str(description_path.resolve()), descriptionSha256=hashlib.sha256(input_data).hexdigest(),
                  sidSha256=hashlib.sha256(sid).hexdigest(), checkedPlayCalls=count,
                  orderedStoreComparison=dict(matchedStores=len(writes), fields=['phase', 'tick', 'address', 'value']),
                  stateComparison=dict(matchedCheckpoints=len(checkpoints), fields=['data', 'sound', 'score', 'Morse']),
                  sidWriterValidation=dict(checkedStores=writer_store_count,
                                           writers=[dict(pc=pc, opcode=site['opcode'], addresses=sorted(site['addresses']))
                                                    for pc, site in sorted(writer_sites.items())]),
                  stageSeconds=stages, toolSha256={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
                  ('scripts/compose-rambo.py', 'songs/players/rambo.asm', 'songs/players/rambo-sound.asm',
                   'scripts/rambo_player.py', 'scripts/rambo_score.py', 'scripts/rambo_programs.py')},
                  limits='Independent compiled state computation; no bus timing, audio or listening claim.', **built)
    for name, value in (('audit.json', audit), ('writes.json', writes), ('state-checkpoints.json', checkpoints)):
        with (output / name).open('x') as handle:
            json.dump(value, handle, indent=None if name == 'writes.json' else 2, allow_nan=False)
            handle.write('\n')
    stages['output'] = perf_counter() - started
    with (output / 'build.json').open('x') as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('description', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calls', type=int)
    parser.add_argument('--stereo-bass', action='store_true',
                        help='Move source voice 2 to SID 2 at $D420, retaining voices 1/3 and their oscillator coupling on SID 1')
    args = parser.parse_args()
    print(json.dumps(run(args.description, args.output, args.calls, stereo_bass=args.stereo_bass), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f'Rambo compilation failed: {error}')
