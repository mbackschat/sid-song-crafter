"""Compile editable Ghostbusters music into an independent NTSC component.

Runtime orders select packed semantic rows and numeric patch/frequency tables;
source annotations never become instructions or store schedules. Score columns
and sound-owned cached controls remain separate. Reset clears only the three
cursor/countdown columns, exits the current voice loop and retains phase/caches.
Entries clobber A/X/Y/flags and reserve zero page $E0–$EF. The standalone raster
host is music-only: no speech, source IRQ context swap or interrupt interleaving.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import AuditMemory, audit_psid
from sid_assembler import assemble
from sid_audit_host import harness
from sid_clock import NTSC_FRAME_CYCLES
from verify_player import cpu_type, require


spec = importlib.util.spec_from_file_location('ghostbusters_compiler_numeric_player',
    Path(__file__).with_name('player.py'))
player = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = player
spec.loader.exec_module(player)

LOAD = 0x1000
WORKSPACE = slice(0xe0, 0xf0)
SCORE_LABELS = dict(orderCursor='gb_order_cursor', patternCursor='gb_pattern_cursor',
    remaining='gb_remaining', note='gb_note', header='gb_header', instrument='gb_instrument')
STATE_STORAGE = (('gb_phase', 1),) + tuple((label, 3) for label in SCORE_LABELS.values()) + (('gb_cached_control', 3),)
DEFAULT_METADATA = dict(title='Ghostbusters music component', author='SID Song Crafter',
    released='2026 independent music only')


def text(value, name):
    require(type(value) is str and '\0' not in value, f'{name} must be text without NUL')
    try:
        return value.encode('latin-1')[:31].ljust(32, b'\0')
    except UnicodeEncodeError as error:
        raise ValueError(f'{name} must be Latin-1 text') from error


def preflight(description):
    for name, default in DEFAULT_METADATA.items():
        text(description.get(name, default), name)
    computed = player.compute(description)
    patches, frequencies = player.sound_data(description['sound'])
    selected = {voice['instrument'] for voice in description['score']['initialState']['voices']}
    for pattern in description['score']['patterns'].values():
        for row in pattern['rows']:
            if 'parameter' in row:
                selected.add(row['parameter']['instrument'])
            if 'note' in row:
                require(row['note'] in frequencies, f'Missing serialized note frequency {row["note"]}')
    require(selected <= set(patches), 'Missing serialized selected patch')
    return computed


def declaration(label, values):
    return label + ':\n  .byte ' + ','.join(f'${value:02x}' if type(value) is int else value for value in values) + '\n'


def parameters(description):
    initial = description['score']['initialState']
    state = {'gb_phase': [initial['phase']], 'gb_cached_control': description['initialSound']['cachedControls']}
    state.update({label: [voice[field] for voice in initial['voices']] for field, label in SCORE_LABELS.items()})
    state_bytes = sum(length for _, length in STATE_STORAGE)
    generated = 'gb_state_begin:\n' + ''.join(declaration(label, [0] * length) for label, length in STATE_STORAGE)
    generated += 'gb_state_end:\n' + declaration('gb_initial_image', [value for label, _ in STATE_STORAGE for value in state[label]])
    generated += ('gb_restore_state:\n  LDY #GB_STATE_LAST\ngb_restore_loop:\n'
        '  LDA gb_initial_image,Y\n  STA gb_state_begin,Y\n  DEY\n  BPL gb_restore_loop\n'
        '  LDX #$0f\n  LDA #$00\ngb_clear_workspace:\n  STA $e0,X\n  DEX\n'
        '  BPL gb_clear_workspace\n  RTS\n')
    references = {}

    def pointer_table(label, destinations):
        nonlocal generated
        for half, suffix in enumerate(('lo', 'hi')):
            values = []
            for index, destination in enumerate(destinations):
                if destination is None:
                    values.append(0)
                    continue
                token = f'{label.upper()}_{suffix.upper()}_{index}'
                references[token] = destination, half * 8
                values.append(token)
            generated += declaration(label + '_' + suffix, values)

    scored = description['score']
    pointer_table('gb_order_ptr', [f'gb_order_{voice}' for voice in range(3)])
    pointer_table('gb_pattern_ptr', [f'gb_pattern_{index}' if str(index) in scored['patterns'] else None for index in range(128)])
    for voice, order in enumerate(scored['orders']):
        generated += declaration(f'gb_order_{voice}', order['patterns'] + [255])
    for index, pattern in sorted(scored['patterns'].items(), key=lambda item: int(item[0])):
        generated += declaration(f'gb_pattern_{index}', player.score.encode_rows(pattern['rows'])[0])
    patches, frequencies = player.sound_data(description['sound'])
    for field in ('pulse_low', 'pulse_high', 'control', 'attack_decay', 'sustain_release', 'vibrato_shift'):
        generated += declaration('gb_patch_' + field, [getattr(patches[index], field) if index in patches else 0 for index in range(9)])
    for shift, suffix in ((0, 'lo'), (8, 'hi')):
        generated += declaration('gb_frequency_' + suffix, [frequencies.get(index, 0) >> shift & 255 for index in range(96)])
    generated += declaration('gb_sid_offsets', [0, 7, 14])
    return generated, references, dict(GB_STATE_LAST=state_bytes - 1), state_bytes


def _build(description):
    generated, references, constants, state_bytes = parameters(description)
    source = (ROOT / 'songs/players/ghostbusters.asm').read_text() + '\n' + generated
    cpu_type()
    constants.update({name: 0 for name in references})
    _, preliminary, _ = assemble(source, constants, load=LOAD)
    constants.update({name: preliminary[label] >> shift & 255 for name, (label, shift) in references.items()})
    payload, symbols, listing = assemble(source, constants, load=LOAD)
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 2), (6, 124), (8, LOAD), (10, symbols['entry_init']),
                          (12, symbols['entry_play']), (14, 1), (16, 1), (118, 0x18)):
        struct.pack_into('>H', header, offset, value)
    for offset, name in ((22, 'title'), (54, 'author'), (86, 'released')):
        header[offset:offset + 32] = text(description.get(name, DEFAULT_METADATA[name]), name)
    return bytes(header) + payload, dict(symbols=symbols, source=source, listing=listing,
        stateBytes=state_bytes, loadAddress=LOAD, payloadBytes=len(payload), payloadEndAddress=LOAD + len(payload),
        originalDriverIncluded=False, registerDumpPlayback=False, runtimeScoreScheduler=True,
        profile=dict(clock='ntsc', sidModel='MOS6581', sidBase=0xd400, frameCycles=NTSC_FRAME_CYCLES),
        supportedCallRange=dict(firstInclusive=0, lastExclusive=description['range']['auditCalls']),
        musicComponentOnly=True, speechIncluded=False, hardwareReset=False,
        initialization=dict(zeroPortsDescending=['d417', 'd400'], stores=24, volumeStore=False))


def build(description):
    preflight(description)
    return _build(description)


def read_state(memory, built, description, phase, tick):
    ram, symbols = memory.data, built['symbols']

    def byte(label, voice=0):
        return ram[symbols[label] + voice]

    after = byte('gb_phase')
    voices = [{field: byte(label, voice) for field, label in SCORE_LABELS.items()} for voice in range(3)]
    cached = [byte('gb_cached_control', voice) for voice in range(3)]
    if phase == 'init':
        return dict(score=dict(phase=after, voices=voices), cachedControls=cached)
    return dict(tick=tick, score=dict(tick=tick, phaseBefore=(after - 1) & 255,
        phaseAfter=after, voices=voices), cachedControls=cached)


def identity(writes):
    return [(row['phase'], row['tick'], row['address'], row['value']) for row in writes]


def runtime_image(memory, built):
    symbols = built['symbols']
    return memory.data[symbols['gb_state_begin']:symbols['gb_state_end']], memory.data[WORKSPACE]


def poison(memory, built):
    symbols = built['symbols']
    memory.data[symbols['gb_state_begin']:symbols['gb_state_end']] = [0xa5] * built['stateBytes']
    memory.data[WORKSPACE] = [0xa5] * 16


def reset_verification(cpu, memory, description, built, cold_image):
    symbols = built['symbols']
    require(cpu.pc == 0x0200 and cpu.sp == 255, 'Reset requires a completed callable boundary')
    poison(memory, built)

    def call(label, phase, tick):
        first = len(memory.writes)
        memory.phase, memory.tick = phase, tick
        cpu.p |= cpu.DECIMAL
        cpu.stPushWord(0x01ff)
        cpu.pc = symbols[label]
        began = cpu.processorCycles
        while cpu.pc != 0x0200:
            require(cpu.processorCycles - began < NTSC_FRAME_CYCLES, 'Reset call exceeds NTSC budget')
            memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
            memory.instruction_cycle = cpu.processorCycles - began
            cpu.step()
        require(cpu.sp == 255 and not cpu.p & cpu.DECIMAL, 'Reset stack/decimal contract differs')
        return memory.writes[first:]

    model = player.compute(description, calls=1)
    init = call('entry_init', 'init', None)
    require(identity(init) == identity([row for row in model['writes'] if row['phase'] == 'init']), 'Poisoned init stores differ')
    require(read_state(memory, built, description, 'init', None) == model['initial'], 'Poisoned init state differs')
    require(runtime_image(memory, built) == cold_image, 'Reset did not restore all software storage/workspace')
    played = call('entry_play', 'play', 0)
    require(identity(played) == identity([row for row in model['writes'] if row['phase'] == 'play']), 'Poisoned first-call stores differ')
    require(read_state(memory, built, description, 'play', 0) == model['returns'][0], 'Poisoned first-call state differs')
    return dict(passed=True, restoredPoisonedState=True, restoredWorkspace=True, decimalModeCleared=True,
        matchedInitStores=len(init), matchedFirstCallStores=len(played), hardwareReset=False)


def verify(description, sid, built, calls=None, computed=None):
    full = preflight(description) if computed is None else computed
    count = description['range']['auditCalls'] if calls is None else calls
    require(type(count) is int and 1 <= count <= description['range']['auditCalls'], 'CPU diagnostic calls exceed declared range')
    expected = [row for row in full['writes'] if row['tick'] is None or row['tick'] < count]
    boundary_count, writer_count, writers, checkpoints, last, cold = 0, 0, {}, [], [], []
    retained = {0, 1, 2, 63, 255, count - 1} | set(full['resetCalls']) | {call + 4 for call in full['resetCalls']}

    def observe(cpu, memory):
        nonlocal boundary_count, writer_count
        opcode = memory.data[cpu.pc]
        if opcode in (0x8d, 0x9d, 0x99, 0x8e, 0x8c):
            address = memory.data[cpu.pc + 1] | memory.data[cpu.pc + 2] << 8
            address += cpu.x if opcode == 0x9d else cpu.y if opcode == 0x99 else 0
            if 0xd400 <= address <= 0xd41f:
                writers.setdefault(cpu.pc, dict(opcode=opcode, addresses=set()))['addresses'].add(address)
                writer_count += 1
        if cpu.pc not in (built['symbols']['gb_init_done'], built['symbols']['gb_call_done']) or cpu.sp != 0xfd:
            return
        actual = read_state(memory, built, description, memory.phase, memory.tick)
        wanted = full['initial'] if memory.phase == 'init' else full['returns'][memory.tick]
        require(actual == wanted, f'Compiled named state differs at {memory.phase}/{memory.tick}: {actual} != {wanted}')
        boundary_count += 1
        if memory.phase == 'init':
            cold[:] = [runtime_image(memory, built)]
        if memory.phase == 'init' or memory.tick in retained:
            checkpoints.append(dict(phase=memory.phase, call=memory.tick, state=actual))
        last[:] = [cpu, memory]

    audit, captured = audit_psid(sid, count, observer=observe, clock='ntsc')
    writes = list(captured)
    actual, wanted = identity(writes), identity(expected)
    for index, pair in enumerate(zip(actual, wanted)):
        require(pair[0] == pair[1], f'Compiled store differs at {index}: {pair[0]} != {pair[1]}')
    require(len(actual) == len(wanted), 'Compiled ordered-store count differs')
    require(boundary_count == count + 1 and writer_count == len(writes), 'Compiled boundary/writer proof incomplete')
    require(audit['maximumPlayCycles'] < NTSC_FRAME_CYCLES, 'Compiled play exceeds NTSC budget')
    reset = reset_verification(*last, description, built, cold[0])
    return dict(checkedPlayCalls=count, completeNumericRange=True,
        completeCompiledRange=count == description['range']['auditCalls'], maximumPlayCycles=audit['maximumPlayCycles'],
        orderedStoreComparison=dict(matchedStores=len(writes), fields=['phase', 'tick', 'address', 'value']),
        callableBoundaries=boundary_count, namedStateBoundaries=boundary_count,
        resetCalls=[call for call in full['resetCalls'] if call < count],
        sidWriterValidation=dict(checkedStores=writer_count, writers=[dict(pc=pc, opcode=value['opcode'],
            addresses=sorted(value['addresses'])) for pc, value in sorted(writers.items())]),
        resetVerification=reset, audit=audit, checkpoints=checkpoints), writes


def standalone_prg(sid, built, calls):
    require(type(calls) is int and 1 <= calls <= built['supportedCallRange']['lastExclusive'],
        'Standalone host calls exceed the declared range')
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
                return (self.cpu.processorCycles // 65 % 263) & 255
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
    poison(memory, built)
    cpu = cpu_type()(memory=memory, pc=2061)
    memory.cpu = cpu
    count = min(2, description['range']['auditCalls'])
    model = player.compute(description, calls=count)
    checked, initialized, entries = 0, False, []
    while checked < count:
        require(cpu.processorCycles < NTSC_FRAME_CYCLES * (count + 3), 'Standalone bootstrap exceeds bounded NTSC raster run')
        # The shared strict host aliases init_return to its repeating wait loop.
        if not initialized and cpu.pc == labels['init_return']:
            require(read_state(memory, built, description, 'init', None) == model['initial'], 'PRG poisoned init state differs')
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
    require(all(abs(value - NTSC_FRAME_CYCLES) <= 9 for value in cadence), 'PRG first-call cadence leaves NTSC grid')
    return dict(passed=True, sysAddress=2061, checkedPlayCalls=count, restoredPoisonedState=True,
        matchedStores=len(memory.writes), cadenceCycles=cadence,
        scope='Actual PRG bootstrap with modeled 263-line NTSC raster/CIA reads; separate from real VICE autostart.')


def run(description_path, output, calls=None):
    require(not output.exists(), 'Compiler output exists; choose a fresh directory')
    description = json.loads(description_path.read_text())
    computed = preflight(description)
    sid, built = _build(description)
    checked, writes = verify(description, sid, built, calls, computed)
    prg, labels = standalone_prg(sid, built, description['range']['auditCalls'])
    checked['standaloneBootstrapVerification'] = bootstrap_verification(prg, labels, description, built)
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
        limitations='Independent runtime music orders/rows/patches; RAM-only NTSC numeric equivalence. Speech, source IRQ context swaps/interleaving, original bus timing, full VICE execution, rendered sound and musical acceptance are separate. Software initialization emits only the original 24 zero stores and no volume store; it is not physical SID reset.')
    (output / 'verification.json').write_text(json.dumps(checked, indent=2) + '\n')
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('composition', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calls', type=int, help='Diagnostic prefix; default verifies every declared call')
    args = parser.parse_args()
    checked = run(args.composition, args.output, args.calls)
    print(json.dumps({name: checked[name] for name in ('checkedPlayCalls', 'completeCompiledRange',
        'maximumPlayCycles', 'orderedStoreComparison', 'namedStateBoundaries', 'resetCalls')}))


if __name__ == '__main__':
    main()
