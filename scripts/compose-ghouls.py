"""Compile an editable Ghouls graph and computed sound into PAL SID/PRG exports."""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import struct
from time import perf_counter

from ghouls_layout import (SOUND_SCRATCH_STORAGE, SOUND_STATE_STORAGE, SOUND_TABLE_STORAGE,
                           read_filter_state, read_voice_state, sound_values)
from ghouls_player import GhoulsPlayer, VOICE_ASSIGNMENTS
from ghouls_score import COMMAND_FIELDS, ScoreCommand
from psid_audit import AuditMemory, audit_psid
from sid_assembler import assemble
from sid_audit_host import harness
from verify_player import cpu_type, require

ROOT = Path(__file__).resolve().parents[1]
LOAD_ADDRESS = 0x1000
STACK_CAPACITY = 8
KINDS = ('note', 'rest') + tuple(command.value for command in ScoreCommand)


def data(label, values):
    require(bool(values), f'{label} requires data')
    return label + ':\n  .byte ' + ','.join(f'${value:02x}' if type(value) is int else value for value in values) + '\n'


def compiler_contract(description):
    calls = description.get('range', {}).get('auditCalls')
    require(type(calls) is int and 1 <= calls <= 65535, 'Declared auditCalls must be in 1..65535')
    player = GhoulsPlayer(description)
    require(all(len(voice.stack) <= STACK_CAPACITY for voice in player.score.voices),
            'Initial score stack exceeds the compiled capacity of 8')
    for wrapper in player.score.nodes.values():
        for node in wrapper['variants'].values():
            if node.get('command') == 'sid-store-list':
                require(len(node['fields']['stores']) <= 255, 'SID-store list exceeds 255 stores')
    return player


def preflight(description):
    player = compiler_contract(description)
    maximum_depth = max(len(voice.stack) for voice in player.score.voices)
    original_operation = player.operation

    def checked_operation(voice, operation, state):
        nonlocal maximum_depth
        depth = len(player.score.voices[voice].stack)
        maximum_depth = max(maximum_depth, depth)
        require(depth <= STACK_CAPACITY, 'Observed score stack exceeds the compiled capacity of 8')
        return original_operation(voice, operation, state)

    player.operation = checked_operation
    for call in range(description['range']['auditCalls']):
        player.play(call)
    return dict(writes=player.writes, maximumObservedStackDepth=maximum_depth)


def parameters(description):
    nodes = description['program']['nodes']
    labels = {node_id: f'gh_node_{index}' for index, node_id in enumerate(nodes)}
    references = {}

    def pointer(label):
        if label is None:
            return [0, 0]
        pair = []
        for shift in (0, 8):
            token = f'GH_POINTER_{len(references)}'
            references[token] = label, shift
            pair.append(token)
        return pair

    states = {
        'gh_score_cursor_lo': [], 'gh_score_cursor_hi': [],
        'gh_score_remaining': [], 'gh_score_repeat': [],
        'gh_score_repeat_lo': [], 'gh_score_repeat_hi': [],
        'gh_score_depth': [], 'gh_score_enabled': [], 'gh_score_override': [],
        'gh_score_return_lo': [], 'gh_score_return_hi': [],
        'gh_score_failed': [0], 'gh_command_budget_lo': [0], 'gh_command_budget_hi': [0],
    }
    for voice in GhoulsPlayer(description).score.snapshot():
        cursor = pointer(labels[voice['cursor']])
        repeat = pointer(labels[voice['repeat_cursor']] if voice['repeat_cursor'] else None)
        for suffix, half in (('lo', 0), ('hi', 1)):
            states['gh_score_cursor_' + suffix].append(cursor[half])
            states['gh_score_repeat_' + suffix].append(repeat[half])
        for label, field in (('remaining', 'duration_remaining'), ('repeat', 'repeat_remaining'),
                             ('enabled', 'enabled'), ('override', 'duration_override')):
            states['gh_score_' + label].append(voice[field])
        states['gh_score_depth'].append(len(voice['stack']))
        returns = [pointer(labels[node]) for node in voice['stack']] + [[0, 0]] * (STACK_CAPACITY - len(voice['stack']))
        for suffix, half in (('lo', 0), ('hi', 1)):
            states['gh_score_return_' + suffix].extend(pair[half] for pair in returns)
    sound = sound_values(description['initialSound'], description['initialFilter'],
                               {int(index): value for index, value in description['frequencyWords'].items()},
                               description['filterRestartPhases'], description['pulseFallbacks'])
    for label, _ in SOUND_STATE_STORAGE + SOUND_SCRATCH_STORAGE:
        states[label] = sound[label]
    source = 'gh_state_begin:\n' + ''.join(data(label, values) for label, values in states.items())
    image = [value for values in states.values() for value in values]
    source += 'gh_state_end:\n' + data('gh_initial_state', image)
    source += 'gh_restore_state:\n'
    for offset in range(0, len(image), 255):
        size = min(255, len(image) - offset)
        source += (f'  LDY #$00\ngh_restore_{offset}:\n'
                   f'  LDA gh_initial_state++{offset},Y\n  STA gh_state_begin++{offset},Y\n'
                   f'  INY\n  CPY #${size:02x}\n  BNE gh_restore_{offset}\n')
    source += '  RTS\n'
    source += ''.join(data(label, sound[label]) for label, _ in SOUND_TABLE_STORAGE)
    source += data('gh_stack_bases', [0, 8, 16])
    handlers = ['gh_kind_note', 'gh_kind_rest'] + ['gh_cmd_' + kind.replace('-', '_') for kind in KINDS[2:]]
    pairs = [pointer(label) for label in handlers]
    source += data('gh_kind_ptr_lo', [pair[0] for pair in pairs])
    source += data('gh_kind_ptr_hi', [pair[1] for pair in pairs])
    for node_id, wrapper in nodes.items():
        variants = {mode: f'{labels[node_id]}_{mode}' for mode in wrapper['variants']}
        source += data(labels[node_id], [*pointer(variants.get('stream')), *pointer(variants.get('override'))])
        for mode, node in wrapper['variants'].items():
            kind = node.get('command', node['kind'])
            args = []
            if kind in ('note', 'rest'):
                args = [node.get('rawNote', 0), node.get('duration', 0)]
            elif kind == 'sid-store-list':
                stores = node['fields']['stores']
                args = [len(stores), *[value for store in stores for value in (store['address'] - 0xd400, store['value'])]]
            else:
                args = [node['fields'][field] for field in COMMAND_FIELDS[ScoreCommand(kind)]]
            source += data(variants[mode], [KINDS.index(kind),
                           *pointer(labels[node['next']] if 'next' in node else None),
                           *pointer(labels[node['target']] if 'target' in node else None), *args])
    return source, references, dict(stateBytes=len(image), graphNodeCount=len(nodes),
                                   graphVariantCount=sum(len(node['variants']) for node in nodes.values()),
                                   nodeLabels=labels)


def assignment_handlers():
    assignments = {command: tuple(fields.values()) for command, fields in VOICE_ASSIGNMENTS.items()}
    assignments['duration-override'] = ('score_override',)
    assignments['onset-parameters'] = ('onset_delay', 'onset_control', 'onset_frequency_lo', 'onset_frequency_hi')
    source = ''
    for command, fields in assignments.items():
        source += 'gh_cmd_' + command.replace('-', '_') + ':\n  LDY #$05\n'
        for index, field in enumerate(fields):
            source += f'  LDA ($e2),Y\n  STA gh_{field},X\n'
            if index < len(fields) - 1:
                source += '  INY\n'
        source += '  JMP gh_continue\n'
    return source


def _assemble_player(description, load_address=LOAD_ADDRESS):
    generated, references, sizes = parameters(description)
    source = '\n'.join((ROOT / 'songs/players' / name).read_text()
                       for name in ('ghouls.asm', 'ghouls-sound.asm')) + '\n' + assignment_handlers() + generated
    cpu_type()
    constants = {name: 0 for name in references}
    _, preliminary, _ = assemble(source, constants, load=load_address)
    constants.update({name: (preliminary[label] >> shift) & 255
                      for name, (label, shift) in references.items()})
    payload, symbols, listing = assemble(source, constants, load=load_address)
    require(load_address + len(payload) <= 0xa000, 'Compiled payload escapes callable RAM')
    return payload, dict(symbols=symbols, source=source, listing=listing, loadAddress=load_address,
                         payloadBytes=len(payload), payloadEndAddress=load_address + len(payload),
                         originalDriverIncluded=False, registerDumpPlayback=False,
                         supportedCallRange=dict(firstInclusive=0, lastExclusive=description['range']['auditCalls']),
                         runtimeScoreScheduler=True, indefinitePlaybackSupported=False, **sizes)


def _build(description):
    payload, built = _assemble_player(description)
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 2), (6, 124), (8, LOAD_ADDRESS), (10, built['symbols']['entry_init']),
                          (12, built['symbols']['entry_play']), (14, 1), (16, 1), (118, 0x14)):
        struct.pack_into('>H', header, offset, value)
    for offset, value in ((22, 'Ghouls independent composition'), (54, 'SID Song Crafter'),
                          (86, '2026 independent reconstruction')):
        header[offset:offset + 31] = value.encode('ascii')[:31].ljust(31, b'\0')
    return bytes(header) + payload, built


def build(description):
    preflight(description)
    return _build(description)


def standalone_prg(sid, built, calls):
    host, labels = harness(dict(initAddress=built['symbols']['entry_init'],
                               playAddress=built['symbols']['entry_play']), calls)
    host_address = int.from_bytes(host[:2], 'little')
    first = 0x0801
    image = bytearray(host_address + len(host) - 2 - first)
    basic = bytes.fromhex('0b080a009e32303631000000')
    image[:len(basic)] = basic
    image[len(basic):len(basic) + 3] = bytes((0x4c, host_address & 255, host_address >> 8))
    payload = sid[124:]
    image[LOAD_ADDRESS - first:LOAD_ADDRESS - first + len(payload)] = payload
    image[host_address - first:] = host[2:]
    return first.to_bytes(2, 'little') + image, labels


def read_state(memory, built):
    ram, symbols = memory.data, built['symbols']
    reverse = {symbols[label]: node_id for node_id, label in built['nodeLabels'].items()}

    def byte(label, index=0):
        return ram[symbols[label] + index]

    def node(low, high, index):
        address = byte(low, index) | byte(high, index) << 8
        require(address == 0 or address in reverse, 'Compiled score pointer escapes its symbolic graph')
        return reverse.get(address)

    score = []
    for voice in range(3):
        depth = byte('gh_score_depth', voice)
        require(depth <= STACK_CAPACITY, 'Compiled score stack exceeds 8')
        score.append(dict(cursor=node('gh_score_cursor_lo', 'gh_score_cursor_hi', voice),
                          duration_remaining=byte('gh_score_remaining', voice),
                          repeat_remaining=byte('gh_score_repeat', voice),
                          repeat_cursor=node('gh_score_repeat_lo', 'gh_score_repeat_hi', voice),
                          stack=[node('gh_score_return_lo', 'gh_score_return_hi', voice * STACK_CAPACITY + slot)
                                 for slot in range(depth)],
                          enabled=byte('gh_score_enabled', voice), duration_override=byte('gh_score_override', voice)))
    return dict(score=score, sounds=[asdict(read_voice_state(ram, symbols, voice)) for voice in range(3)],
                filter=asdict(read_filter_state(ram, symbols)),
                filterRestartPhases=[byte('gh_filter_restart_phase', voice) for voice in range(3)])


def check_sid_writer(cpu, memory):
    opcode = memory.data[cpu.pc]
    if opcode not in (0x8d, 0x9d, 0x99, 0x8e, 0x8c):
        return None
    address = memory.data[cpu.pc + 1] | memory.data[cpu.pc + 2] << 8
    address += cpu.x if opcode == 0x9d else cpu.y if opcode == 0x99 else 0
    return (cpu.pc, opcode, address) if 0xd400 <= address <= 0xd41f else None


def reset_verification(cpu, memory, description, built):
    require(cpu.pc == 0x0200 and cpu.sp == 255, 'Reset proof requires the completed callable boundary')
    fresh = GhoulsPlayer(description)

    def call(address, phase, tick):
        first_write = len(memory.writes)
        memory.phase, memory.tick = phase, tick
        cpu.stPushWord(0x01ff)
        cpu.pc = address
        started = cpu.processorCycles
        while cpu.pc != 0x0200:
            require(cpu.processorCycles - started < 19656, 'Reset call exceeds the PAL budget')
            memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
            memory.instruction_cycle = cpu.processorCycles - started
            cpu.step()
        require(cpu.sp == 255, 'Reset did not restore the callable stack')
        return [(row['address'], row['value']) for row in memory.writes[first_write:]]

    init_writes = call(built['symbols']['entry_init'], 'init', None)
    require(init_writes == [(row['address'], row['value']) for row in fresh.writes], 'Reinit stores differ')
    require(read_state(memory, built) == fresh.state(), 'Reinit named state differs')
    first = len(fresh.writes)
    fresh.play(0)
    play_writes = call(built['symbols']['entry_play'], 'play', 0)
    require(play_writes == [(row['address'], row['value']) for row in fresh.writes[first:]], 'First-call reset stores differ')
    require(read_state(memory, built) == fresh.state(), 'First-call reset state differs')
    return dict(passed=True, matchedInitStores=len(init_writes), matchedFirstCallStores=len(play_writes))


def bootstrap_verification(prg, host_labels, description, built):
    """Execute the PRG's SYS entry and first calls with modeled raster reads.

    The shared harness disables display DMA and interrupts. This focused CPU
    check models its VIC line reads and cleared CIA interrupt latches; it does
    not establish a VICE autostart, SID internals or original game-host behavior.
    """
    class RasterMemory(AuditMemory):
        cpu = None

        def __getitem__(self, address):
            if address == 0xd012:
                return (self.cpu.processorCycles // 63 % 312) & 255
            if address in (0xdc0d, 0xdd0d):
                return 0
            return super().__getitem__(address)

        def __setitem__(self, address, value):
            if address in (0xdc0d, 0xdd0d, 0xd01a, 0xd011, 0xd015):
                self.data[address] = value
            else:
                super().__setitem__(address, value)

    memory = RasterMemory()
    load = int.from_bytes(prg[:2], 'little')
    require(load == 0x0801 and prg[2:14] == bytes.fromhex('0b080a009e32303631000000'),
            'Standalone PRG lacks its declared SYS 2061 bootstrap')
    memory.data[load:load + len(prg) - 2] = prg[2:]
    symbols = built['symbols']
    memory.data[symbols['gh_state_begin']:symbols['gh_state_end']] = [0xa5] * (symbols['gh_state_end'] - symbols['gh_state_begin'])
    cpu = cpu_type()(memory=memory, pc=2061)
    memory.cpu = cpu
    model = GhoulsPlayer(description)
    target_calls = min(2, description['range']['auditCalls'])
    checked_calls, checked_init = 0, False
    entries = []
    while checked_calls < target_calls:
        require(cpu.processorCycles < 19656 * (target_calls + 2), 'Standalone bootstrap exceeds its bounded raster run')
        if cpu.pc == host_labels['init_return']:
            require(read_state(memory, built) == model.state(), 'Standalone init did not restore poisoned named state')
            checked_init = True
        if cpu.pc == host_labels['call']:
            require(checked_init, 'Standalone play preceded initialization')
            memory.phase, memory.tick = 'play', checked_calls
            entries.append(cpu.processorCycles)
        if cpu.pc == host_labels['play_return']:
            model.play(checked_calls)
            require(read_state(memory, built) == model.state(), 'Standalone first-call named state differs')
            require(cpu.sp == 255, 'Standalone play did not preserve the harness stack')
            checked_calls += 1
            if checked_calls == target_calls:
                break
        memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
        memory.instruction_cycle = cpu.processorCycles
        cpu.step()
    identity = lambda rows: [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]
    require(identity(memory.writes) == identity(model.writes), 'Standalone bootstrap SID stores differ')
    cadence = [right - left for left, right in zip(entries, entries[1:])]
    require(all(abs(cycles - 19656) <= 9 for cycles in cadence), 'Standalone first-call cadence leaves the PAL grid')
    return dict(passed=True, sysAddress=2061, checkedPlayCalls=checked_calls, restoredPoisonedState=True,
                matchedStores=len(memory.writes), playEntryCycles=entries, callCadenceCycles=cadence,
                bank=0x37, scope='Executed PRG bootstrap/first calls with modeled raster and CIA reads; separate from PAL-banked callable VICE.')


def run(description_path, output, calls=None):
    description_path, output = Path(description_path), Path(output)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh output directory')
    input_data = description_path.read_bytes()
    description = json.loads(input_data)
    count = description['range']['auditCalls'] if calls is None else calls
    require(type(count) is int and 1 <= count <= description['range']['auditCalls'], 'Requested calls exceed declared range')
    stages = {}
    started = perf_counter()
    numeric = preflight(description)
    stages['numericPreflight'] = perf_counter() - started
    started = perf_counter()
    sid, built = _build(description)
    stages['assembly'] = perf_counter() - started
    model = GhoulsPlayer(description)
    matched_boundaries, writer_count = 0, 0
    checkpoints, writer_sites, last_cpu = [], {}, []
    retained_calls = {0, 1, 43, 255, 256, 12947, 12971, 12995, count - 1}

    def observer(cpu, memory):
        nonlocal matched_boundaries, writer_count
        writer = check_sid_writer(cpu, memory)
        if writer:
            pc, opcode, address = writer
            writer_sites.setdefault(pc, dict(opcode=opcode, addresses=set()))['addresses'].add(address)
            writer_count += 1
        boundary = (memory.phase == 'init' and cpu.pc == built['symbols']['gh_init_done']
                    or memory.phase == 'play' and cpu.pc == built['symbols']['gh_call_done'])
        if not boundary or cpu.sp != 0xfd:
            return
        require(not memory.data[built['symbols']['gh_score_failed']], 'Compiled score failure guard fired')
        require(not memory.data[built['symbols']['gh_filter_failed']], 'Compiled filter failure guard fired')
        if memory.phase == 'play':
            model.play(memory.tick)
        actual = read_state(memory, built)
        expected_state = model.state()
        if actual != expected_state:
            raise ValueError(f'Compiled named state differs at {memory.phase} call {memory.tick}: {actual} != {expected_state}')
        matched_boundaries += 1
        if memory.phase == 'init' or memory.tick in retained_calls:
            checkpoints.append(dict(phase=memory.phase, call=memory.tick, state=actual))
        last_cpu[:] = [cpu, memory]

    started = perf_counter()
    audit, captured = audit_psid(sid, count, observer=observer)
    writes = list(captured)
    stages['cpuProof'] = perf_counter() - started
    expected = [row for row in numeric['writes'] if row['tick'] is None or row['tick'] < count]
    identity = lambda rows: [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]
    for index, (wanted, actual) in enumerate(zip(identity(expected), identity(writes))):
        require(wanted == actual, f'Compiled store differs at {index}: {wanted} != {actual}')
    require(len(expected) == len(writes), 'Compiled ordered-store count differs')
    require(matched_boundaries == count + 1 and writer_count == len(writes), 'Compiled proof coverage incomplete')
    reset = reset_verification(*last_cpu, description, built)
    prg, host_labels = standalone_prg(sid, built, description['range']['auditCalls'])
    bootstrap = bootstrap_verification(prg, host_labels, description, built)
    output.mkdir(parents=True)
    (output / 'reconstructed.sid').write_bytes(sid)
    (output / 'reconstructed.prg').write_bytes(prg)
    (output / 'player.asm').write_text(built.pop('source'))
    (output / 'player.listing').write_text(built.pop('listing'))
    for name, value in (('audit.json', audit), ('writes.json', writes), ('state-checkpoints.json', checkpoints)):
        (output / name).write_text(json.dumps(value, indent=None if name == 'writes.json' else 2) + '\n')
    report = dict(descriptionPath=str(description_path.resolve()), descriptionSha256=hashlib.sha256(input_data).hexdigest(),
                  sidSha256=hashlib.sha256(sid).hexdigest(), prgSha256=hashlib.sha256(prg).hexdigest(),
                  checkedPlayCalls=count, maximumPlayCycles=audit['maximumPlayCycles'],
                  orderedStoreComparison=dict(matchedStores=len(writes), fields=['phase', 'tick', 'address', 'value']),
                  stateComparison=dict(matchedBoundaries=matched_boundaries, retainedCheckpoints=len(checkpoints),
                                       fields=['score', 'sounds', 'filter', 'filterRestartPhases']),
                  compilerContract=dict(stackCapacity=STACK_CAPACITY,
                                        maximumObservedStackDepth=numeric['maximumObservedStackDepth'],
                                        fullDeclaredNumericPreflight=True, calls=description['range']['auditCalls']),
                  sidWriterValidation=dict(checkedStores=writer_count,
                                           writers=[dict(pc=pc, opcode=site['opcode'], addresses=sorted(site['addresses']))
                                                    for pc, site in sorted(writer_sites.items())]),
                  resetVerification=reset, standaloneHost=dict(labels=host_labels, calls=description['range']['auditCalls']),
                  standaloneBootstrapVerification=bootstrap,
                  stageSeconds=stages, toolSha256={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
                  ('scripts/compose-ghouls.py', 'scripts/ghouls_player.py', 'scripts/ghouls_score.py',
                   'scripts/ghouls_programs.py', 'scripts/ghouls_layout.py', 'scripts/sid_assembler.py',
                   'scripts/psid_audit.py', 'scripts/psid_profile.py', 'scripts/sid_audit_host.py',
                   'scripts/verify_player.py', 'songs/players/ghouls.asm', 'songs/players/ghouls-sound.asm')},
                  limits='Ordered values and named computed state; no bus-cycle, SID-internal, rendered or listening claim.', **built)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('description', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calls', type=int)
    args = parser.parse_args()
    result = run(args.description, args.output, args.calls)
    print(json.dumps(dict(output=str(args.output), calls=result['checkedPlayCalls'],
                          stores=result['orderedStoreComparison']['matchedStores'],
                          maximumPlayCycles=result['maximumPlayCycles'])))


if __name__ == '__main__':
    try:
        main()
    except (KeyError, OSError, ValueError) as error:
        raise SystemExit(f'Ghouls compilation failed: {error}')
