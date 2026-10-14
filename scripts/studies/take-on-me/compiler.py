"""Compile numeric Take On Me score/program data into independent PAL/8580 exports."""

from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import AuditMemory, audit_psid
from sid_assembler import assemble
from sid_audit_host import harness
from verify_player import cpu_type, require
import effects_asm
import player
import programs
import score


LOAD = 0x1000
SCORE_LABELS = dict(remaining='tm_remaining', orderCursor='tm_order_cursor', repeat='tm_repeat',
    transpose='tm_transpose', patternCursor='tm_pattern_cursor', instrument='tm_instrument',
    durationTicks='tm_duration', glideStepLow='tm_glide_step_lo', glideStepHigh='tm_glide_step_hi',
    baseNote='tm_base_note', glideTarget='tm_glide_target', arpeggio='tm_arpeggio')
INVERSES = dict(BCC='BCS', BCS='BCC', BEQ='BNE', BNE='BEQ', BMI='BPL', BPL='BMI', BVC='BVS', BVS='BVC')


def text(value, name):
    require(type(value) is str and '\0' not in value, f'{name} must be text without NUL')
    try:
        return value.encode('latin-1')[:31].ljust(32, b'\0')
    except UnicodeEncodeError as error:
        raise ValueError(f'{name} must be Latin-1 text') from error


def preflight(description):
    count = description['range']['auditCalls']
    require(type(count) is int and 1 <= count <= 65535, 'Compiled auditCalls must be 1..65535')
    require(description['target']['sidModel'] == 'MOS8580', 'Compiled Take On Me requires the selected MOS8580 target')
    text(description.get('title', 'Take On Me independent title'), 'title')
    text(description.get('author', 'SID Song Crafter'), 'author')
    return player.compute(description)


def initial(description):
    scored = deepcopy(description['score']['initialVoices'])
    voices = [player.bridge(programs.VoiceState(**values), scored[index])
              for index, values in enumerate(description['initialSound']['voices'])]
    shared = programs.FilterState(**description['initialSound']['filter'])
    state = dict(tick=None, score=dict(tick=None, active=True,
        dividers=list(description['score']['initialDividers']), voices=scored),
        voices=[asdict(voice) for voice in voices], filter=asdict(shared))
    if 'ending' in description:
        state['ending'] = dict(phase=0, nextCall=0, modeVolume=description['mix']['modeVolume'])
    return voices, shared, state


def parameters(description):
    voices, shared, _ = initial(description)
    states = effects_asm.sound_state_values(voices, shared)
    scored = description['score']['initialVoices']
    for name, label in SCORE_LABELS.items():
        states[label] = [voice[name] for voice in scored]
    states.update(tm_active=[1], tm_divider_a=[description['score']['initialDividers'][0]],
        tm_divider_b=[description['score']['initialDividers'][1]], tm_call_lo=[0], tm_call_hi=[0],
        tm_ending_phase=[0], tm_mode_volume=[description['mix']['modeVolume']], tm_failed=[0])
    states.update({label: [0] * length for label, length in effects_asm.SCRATCH_STORAGE})
    image = [value for values in states.values() for value in values]
    require(1 <= len(image) <= 255, 'Cold mutable image must fit the restore cursor')
    generated = 'tm_state_begin:\n' + effects_asm.declarations(states) + 'tm_state_end:\n'
    generated += effects_asm.declarations({'tm_initial_state': image, 'tm_mix_routing': [description['mix']['routing']]})
    generated += ('tm_restore_state:\n  LDY #$00\ntm_restore_loop:\n'
        '  LDA tm_initial_state,Y\n  STA tm_state_begin,Y\n  INY\n'
        '  CPY #TM_STATE_BYTES\n  BNE tm_restore_loop\n  LDX #$1f\n  LDA #$00\n'
        'tm_clear_workspace:\n  STA $d0,X\n  DEX\n  BPL tm_clear_workspace\n  RTS\n')
    references = {}

    def pointer(label, half):
        if label is None:
            return 0
        token = f'TM_SCORE_POINTER_{len(references)}'
        references[token] = label, half * 8
        return token

    orders = description['score']['orders']
    require(len(orders) == 3, 'Compiled score needs three orders')
    for half, suffix in enumerate(('lo', 'hi')):
        generated += effects_asm.declarations({f'tm_order_ptr_{suffix}': [pointer(f'tm_order_{index}', half) for index in range(3)]})
    for index, order in enumerate(orders):
        require(1 <= len(order['bytes']) <= 256, 'Order must fit its byte cursor')
        generated += effects_asm.declarations({f'tm_order_{index}': order['bytes']})
    patterns = player.numbered(description['score']['patterns'], 'patterns')
    require(all(index < 128 for index in patterns), 'Pattern IDs must be in 0..127')
    for half, suffix in enumerate(('lo', 'hi')):
        generated += effects_asm.declarations({f'tm_pattern_ptr_{suffix}':
            [pointer(f'tm_pattern_{index}' if index in patterns else None, half) for index in range(128)]})
    for index, pattern in patterns.items():
        encoded, _ = score.encode_rows(pattern['rows'])
        generated += effects_asm.declarations({f'tm_pattern_{index}': encoded})
    tables, sound_references = effects_asm.sound_tables(description['sound'])
    references.update(sound_references)
    generated += tables
    ending = description.get('ending', {})
    start = ending.get('startCall', 0)
    stop = start + ending.get('releaseCalls', 0)
    constants = dict(TM_STATE_BYTES=len(image), TM_ENDING_ENABLED=int(bool(ending)),
        TM_END_START_LO=start & 255, TM_END_START_HI=start >> 8,
        TM_END_STOP_LO=stop & 255, TM_END_STOP_HI=stop >> 8,
        TM_DIVIDER_A_RELOAD=description['score']['dividerReloads'][0],
        TM_DIVIDER_B_RELOAD=description['score']['dividerReloads'][1])
    return generated, references, constants, len(image)


def long_branches(source):
    lines, number = [], 0
    for line in source.splitlines():
        instruction = line.split(';', 1)[0].strip().split(None, 1)
        if instruction and instruction[0] in INVERSES:
            label = f'tm_compiler_branch_{number}'
            lines.extend((f'  {INVERSES[instruction[0]]} {label}', f'  JMP {instruction[1]}', label + ':'))
            number += 1
        else:
            lines.append(line)
    return '\n'.join(lines) + '\n'


def _build(description):
    generated, references, constants, state_bytes = parameters(description)
    source = long_branches('\n'.join((ROOT / 'songs/players' / name).read_text()
        for name in ('take-on-me.asm', 'take-on-me-effects.asm')) + '\n' + generated)
    cpu_type()
    constants.update({name: 0 for name in references})
    _, preliminary, _ = assemble(source, constants, load=LOAD)
    constants.update({name: (preliminary[label] >> shift) & 255 for name, (label, shift) in references.items()})
    payload, symbols, listing = assemble(source, constants, load=LOAD)
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 2), (6, 124), (8, LOAD), (10, symbols['entry_init']),
                          (12, symbols['entry_play']), (14, 1), (16, 1), (118, 0x24)):
        struct.pack_into('>H', header, offset, value)
    for offset, name, default in ((22, 'title', 'Take On Me independent title'),
                                 (54, 'author', 'SID Song Crafter'),
                                 (86, 'released', '2026 independent reconstruction')):
        header[offset:offset + 32] = text(description.get(name, default), name)
    return bytes(header) + payload, dict(symbols=symbols, source=source, listing=listing,
        stateBytes=state_bytes, loadAddress=LOAD, payloadBytes=len(payload), payloadEndAddress=LOAD + len(payload),
        originalDriverIncluded=False, registerDumpPlayback=False, runtimeScoreScheduler=True,
        indefinitePlaybackSupported=False, profile=dict(clock='pal', sidModel='MOS8580', sidBase=0xd400),
        supportedCallRange=dict(firstInclusive=0, lastExclusive=description['range']['auditCalls']))


def build(description):
    preflight(description)
    return _build(description)


def read_state(memory, built, description, phase, tick):
    ram, symbols = memory.data, built['symbols']
    byte = lambda label, voice=0: ram[symbols[label] + voice]
    ending = description.get('ending')
    score_tick = None if phase == 'init' else min(tick, ending['startCall'] - 1) if ending else tick
    state = dict(tick=tick, score=dict(tick=score_tick, active=bool(byte('tm_active')),
        dividers=[byte('tm_divider_a'), byte('tm_divider_b')],
        voices=[{name: byte(label, voice) for name, label in SCORE_LABELS.items()} for voice in range(3)]),
        voices=[asdict(effects_asm.read_voice(memory, symbols, voice)) for voice in range(3)],
        filter=asdict(effects_asm.read_filter(memory, symbols)))
    if ending:
        state['ending'] = dict(phase=byte('tm_ending_phase'), nextCall=byte('tm_call_lo') | byte('tm_call_hi') << 8,
                               modeVolume=byte('tm_mode_volume'))
    return state


def identity(writes):
    return [(row['phase'], row['tick'], row['address'], row['value']) for row in writes]


def reset_verification(cpu, memory, description, built):
    symbols = built['symbols']
    require(cpu.pc == 0x0200 and cpu.sp == 255, 'Reset requires a completed callable boundary')
    memory.data[symbols['tm_state_begin']:symbols['tm_state_end']] = [0xa5] * built['stateBytes']
    memory.data[0xd0:0xf0] = [0xa5] * 32

    def call(address, phase, tick):
        first = len(memory.writes)
        memory.phase, memory.tick = phase, tick
        cpu.stPushWord(0x01ff)
        cpu.pc = address
        began = cpu.processorCycles
        while cpu.pc != 0x0200:
            require(cpu.processorCycles - began < 19656, 'Reset call exceeds PAL budget')
            memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
            memory.instruction_cycle = cpu.processorCycles - began
            cpu.step()
        require(cpu.sp == 255, 'Reset did not restore the call stack')
        return memory.writes[first:]

    first = player.compute(description, calls=1)
    init = call(symbols['entry_init'], 'init', None)
    require(identity(init) == identity([row for row in first['writes'] if row['phase'] == 'init']), 'Poisoned init stores differ')
    require(read_state(memory, built, description, 'init', None) == initial(description)[2], 'Poisoned init state differs')
    restored = memory.data[symbols['tm_state_begin']:symbols['tm_state_end']]
    expected_image = memory.data[symbols['tm_initial_state']:symbols['tm_initial_state'] + built['stateBytes']]
    require(restored == expected_image and memory.data[0xd0:0xf0] == [0] * 32, 'Cold reset did not restore all mutable storage')
    played = call(symbols['entry_play'], 'play', 0)
    require(identity(played) == identity([row for row in first['writes'] if row['phase'] == 'play']), 'Poisoned first-call stores differ')
    require(read_state(memory, built, description, 'play', 0) == first['returns'][0], 'Poisoned first-call state differs')
    return dict(passed=True, restoredPoisonedState=True, restoredWorkspace=True,
        matchedInitStores=len(init), matchedFirstCallStores=len(played))


def verify(description, sid, built, calls=None, computed=None):
    full = preflight(description) if computed is None else computed
    count = description['range']['auditCalls'] if calls is None else calls
    require(type(count) is int and 1 <= count <= description['range']['auditCalls'], 'CPU diagnostic calls exceed declared range')
    expected = [row for row in full['writes'] if row['tick'] is None or row['tick'] < count]
    boundary_count, writer_count, writers, checkpoints, last = 0, 0, {}, [], []
    retained = {0, 1, 63, 255, 767, 768, count - 1}
    if 'ending' in description:
        start = description['ending']['startCall']
        retained.update((start - 1, start, start + description['ending']['releaseCalls'] - 1,
                         start + description['ending']['releaseCalls']))

    def observe(cpu, memory):
        nonlocal boundary_count, writer_count
        opcode = memory.data[cpu.pc]
        if opcode in (0x8d, 0x9d, 0x99, 0x8e, 0x8c):
            address = memory.data[cpu.pc + 1] | memory.data[cpu.pc + 2] << 8
            address += cpu.x if opcode == 0x9d else cpu.y if opcode == 0x99 else 0
            if 0xd400 <= address <= 0xd41f:
                writers.setdefault(cpu.pc, dict(opcode=opcode, addresses=set()))['addresses'].add(address)
                writer_count += 1
        if cpu.pc not in (built['symbols']['tm_init_done'], built['symbols']['tm_call_done']) or cpu.sp != 0xfd:
            return
        require(memory.data[built['symbols']['tm_failed']] == 0, 'Compiled sound guard fired')
        actual = read_state(memory, built, description, memory.phase, memory.tick)
        wanted = initial(description)[2] if memory.phase == 'init' else full['returns'][memory.tick]
        require(actual == wanted, f'Compiled named state differs at {memory.phase}/{memory.tick}: {actual} != {wanted}')
        boundary_count += 1
        if memory.phase == 'init' or memory.tick in retained:
            checkpoints.append(dict(phase=memory.phase, call=memory.tick, state=actual))
        last[:] = [cpu, memory]

    audit, captured = audit_psid(sid, count, observer=observe)
    writes = list(captured)
    actual, wanted = identity(writes), identity(expected)
    for index, pair in enumerate(zip(actual, wanted)):
        require(pair[0] == pair[1], f'Compiled store differs at {index}: {pair[0]} != {pair[1]}')
    require(len(actual) == len(wanted), 'Compiled ordered-store count differs')
    require(boundary_count == count + 1 and writer_count == len(writes), 'Compiled boundary/writer proof incomplete')
    reset = reset_verification(*last, description, built)
    return dict(checkedPlayCalls=count, completeNumericRange=True,
        completeCompiledRange=count == description['range']['auditCalls'], maximumPlayCycles=audit['maximumPlayCycles'],
        orderedStoreComparison=dict(matchedStores=len(writes), fields=['phase', 'tick', 'address', 'value']),
        callableBoundaries=boundary_count, namedStateBoundaries=boundary_count,
        sidWriterValidation=dict(checkedStores=writer_count, writers=[dict(pc=pc, opcode=value['opcode'],
            addresses=sorted(value['addresses'])) for pc, value in sorted(writers.items())]),
        resetVerification=reset, audit=audit, checkpoints=checkpoints), writes


def standalone_prg(sid, built, calls):
    host, labels = harness(dict(initAddress=built['symbols']['entry_init'], playAddress=built['symbols']['entry_play']), calls)
    host_address = int.from_bytes(host[:2], 'little')
    first = 0x0801
    image = bytearray(host_address + len(host) - 2 - first)
    basic = bytes.fromhex('0b080a009e32303631000000')
    image[:len(basic)] = basic
    image[len(basic):len(basic) + 3] = bytes((0x4c, host_address & 255, host_address >> 8))
    payload = sid[124:]
    image[LOAD - first:LOAD - first + len(payload)] = payload
    image[host_address - first:] = host[2:]
    return first.to_bytes(2, 'little') + image, labels


def bootstrap_verification(prg, labels, description, built):
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

    require(prg[:14] == b'\x01\x08' + bytes.fromhex('0b080a009e32303631000000'), 'PRG SYS 2061 bootstrap differs')
    memory = RasterMemory()
    memory.data[0x0801:0x0801 + len(prg) - 2] = prg[2:]
    symbols = built['symbols']
    memory.data[symbols['tm_state_begin']:symbols['tm_state_end']] = [0xa5] * built['stateBytes']
    memory.data[0xd0:0xf0] = [0xa5] * 32
    cpu = cpu_type()(memory=memory, pc=2061)
    memory.cpu = cpu
    count = min(2, description['range']['auditCalls'])
    model = player.compute(description, calls=count)
    checked, initialized, entries = 0, False, []
    while checked < count:
        require(cpu.processorCycles < 19656 * (count + 3), 'Standalone bootstrap exceeds bounded raster run')
        # sid_audit_host.harness aliases strict init_return to wait, which repeats every frame.
        if not initialized and cpu.pc == labels['init_return']:
            actual = read_state(memory, built, description, 'init', None)
            expected = initial(description)[2]
            require(actual == expected, f'PRG poisoned init state differs: {actual} != {expected}')
            initialized = True
        if cpu.pc == labels['call']:
            require(initialized, 'PRG play preceded init')
            memory.phase, memory.tick = 'play', checked
            entries.append(cpu.processorCycles)
        if cpu.pc == labels['play_return']:
            require(read_state(memory, built, description, 'play', checked) == model['returns'][checked], 'PRG first-call state differs')
            require(cpu.sp == 255, 'PRG call stack differs')
            checked += 1
            if checked == count:
                break
        memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
        memory.instruction_cycle = cpu.processorCycles
        cpu.step()
    require(identity(memory.writes) == identity(model['writes']), 'PRG init/first-call stores differ')
    cadence = [right - left for left, right in zip(entries, entries[1:])]
    require(all(abs(value - 19656) <= 9 for value in cadence), 'PRG first-call cadence leaves PAL grid')
    return dict(passed=True, sysAddress=2061, checkedPlayCalls=count, restoredPoisonedState=True,
        matchedStores=len(memory.writes), cadenceCycles=cadence,
        scope='Actual PRG bootstrap with modeled raster/CIA reads; separate from real VICE autostart.')


def run(description_path, output, calls=None):
    require(not output.exists(), 'Compiler output exists; choose a fresh directory')
    description = json.loads(description_path.read_text())
    computed = preflight(description)
    sid, built = _build(description)
    checked, writes = verify(description, sid, built, calls, computed)
    prg, labels = standalone_prg(sid, built, description['range']['auditCalls'])
    bootstrap = bootstrap_verification(prg, labels, description, built)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'reconstructed.sid').write_bytes(sid)
    (output / 'reconstructed.prg').write_bytes(prg)
    (output / 'player.asm').write_text(built.pop('source'))
    (output / 'player.listing').write_text(built.pop('listing'))
    (output / 'build.json').write_text(json.dumps(built, indent=2) + '\n')
    (output / 'audit.json').write_text(json.dumps(checked['audit'], indent=2) + '\n')
    (output / 'writes.json').write_text(json.dumps(writes, separators=(',', ':')) + '\n')
    (output / 'state-checkpoints.json').write_text(json.dumps(checked.pop('checkpoints'), indent=2) + '\n')
    checked.update(sidSha256=hashlib.sha256(sid).hexdigest(), prgSha256=hashlib.sha256(prg).hexdigest(),
        compositionSha256=hashlib.sha256(description_path.read_bytes()).hexdigest(),
        standaloneBootstrapVerification=bootstrap,
        limitations='Independent runtime score/program tables and compiled numeric equivalence under callable RAM-only PAL execution. Exact original instruction/bus timing, VICE, rendering and musical acceptance remain separate.')
    (output / 'verification.json').write_text(json.dumps(checked, indent=2) + '\n')
    return checked
