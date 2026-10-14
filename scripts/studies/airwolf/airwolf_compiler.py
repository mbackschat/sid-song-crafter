"""Compile editable Airwolf rows into an independent PAL/MOS6581 player.

Runtime rows contain duration and three tag/high/low triples; tags distinguish
hold, authored gate-off and pitch. Named shadows describe this player's emitted
ports, not physical SID state. Init clears software storage and consumes row
zero, preserving the source's unwritten pulse lows, voice-three pulse and filter
registers. Entries clobber A/X/Y/flags and use reserved zero page $E0–$EF.
"""

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
import airwolf_player as player


LOAD = 0x1000
WORKSPACE = slice(0xe0, 0xf0)
STATE_STORAGE = (('aw_next_row', 1), ('aw_countdown', 1), ('aw_frequency_lo', 3),
    ('aw_frequency_hi', 3), ('aw_control', 3), ('aw_attack_decay', 3),
    ('aw_sustain_release', 3), ('aw_pulse_high', 2), ('aw_volume', 1),
    ('aw_call_lo', 1), ('aw_call_hi', 1), ('aw_ending_phase', 1))
DEFAULT_METADATA = dict(title='Airwolf independent title', author='SID Song Crafter',
    released='2026 independent reconstruction')


def text(value, name):
    require(type(value) is str and '\0' not in value, f'{name} must be text without NUL')
    try:
        return value.encode('latin-1')[:31].ljust(32, b'\0')
    except UnicodeEncodeError as error:
        raise ValueError(f'{name} must be Latin-1 text') from error


def preflight(description):
    for name, default in DEFAULT_METADATA.items():
        text(description.get(name, default), name)
    return player.compute(description)


def declaration(label, values):
    return label + ':\n  .byte ' + ','.join(f'${value:02x}' if type(value) is int else value for value in values) + '\n'


def parameters(description):
    state_bytes = sum(length for _, length in STATE_STORAGE)
    generated = 'aw_state_begin:\n'
    generated += ''.join(declaration(label, [0] * length) for label, length in STATE_STORAGE)
    generated += ('aw_state_end:\naw_restore_state:\n  LDY #$00\n  LDA #$00\n'
        'aw_restore_loop:\n  STA aw_state_begin,Y\n  INY\n  CPY #AW_STATE_BYTES\n'
        '  BNE aw_restore_loop\n  LDX #$0f\naw_clear_workspace:\n  STA $e0,X\n'
        '  DEX\n  BPL aw_clear_workspace\n  RTS\n')
    references = {}
    for half, suffix in enumerate(('lo', 'hi')):
        values = []
        for index in range(len(description['rows'])):
            token = f'AW_ROW_POINTER_{suffix.upper()}_{index}'
            references[token] = f'aw_row_{index}', half * 8
            values.append(token)
        generated += declaration(f'aw_row_ptr_{suffix}', values)
    for index, row in enumerate(description['rows']):
        encoded = [row['duration']]
        for note in row['notes']:
            encoded.extend((0, 0, 0) if note is None else (1, 0, 0) if note == 'off' else (2, note >> 8, note & 255))
        generated += declaration(f'aw_row_{index}', encoded)
    patches = description['sound']['voices']
    for label, name in (('aw_patch_ad', 'attackDecay'), ('aw_patch_sr', 'sustainRelease'),
                        ('aw_patch_control', 'control')):
        generated += declaration(label, [patch[name] for patch in patches])
    generated += declaration('aw_sid_offsets', [0, 7, 14])
    ending = description.get('ending', {})
    start = ending.get('startCall', 0)
    stop = start + ending.get('releaseCalls', 0)
    sound = description['sound']
    constants = dict(AW_STATE_BYTES=state_bytes, AW_ROW_COUNT=len(description['rows']),
        AW_ENDING_ENABLED=int(bool(ending)), AW_END_START_LO=start & 255, AW_END_START_HI=start >> 8,
        AW_END_STOP_LO=stop & 255, AW_END_STOP_HI=stop >> 8, AW_VOLUME=sound['volume'],
        AW_PULSE_HIGH_0=sound['pulseHigh'][0], AW_PULSE_HIGH_1=sound['pulseHigh'][1])
    return generated, references, constants, state_bytes


def _build(description):
    generated, references, constants, state_bytes = parameters(description)
    source = (ROOT / 'songs/players/airwolf.asm').read_text() + '\n' + generated
    cpu_type()
    constants.update({name: 0 for name in references})
    _, preliminary, _ = assemble(source, constants, load=LOAD)
    constants.update({name: (preliminary[label] >> shift) & 255 for name, (label, shift) in references.items()})
    payload, symbols, listing = assemble(source, constants, load=LOAD)
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 2), (6, 124), (8, LOAD), (10, symbols['entry_init']),
                          (12, symbols['entry_play']), (14, 1), (16, 1), (118, 0x14)):
        struct.pack_into('>H', header, offset, value)
    for offset, name in ((22, 'title'), (54, 'author'), (86, 'released')):
        header[offset:offset + 32] = text(description.get(name, DEFAULT_METADATA[name]), name)
    return bytes(header) + payload, dict(symbols=symbols, source=source, listing=listing,
        stateBytes=state_bytes, loadAddress=LOAD, payloadBytes=len(payload), payloadEndAddress=LOAD + len(payload),
        originalDriverIncluded=False, registerDumpPlayback=False, runtimeScoreScheduler=True,
        profile=dict(clock='pal', sidModel='MOS6581', sidBase=0xd400),
        supportedCallRange=dict(firstInclusive=0, lastExclusive=description['range']['auditCalls']),
        hardwareReset=False, untouchedRegisters=['d402', 'd409', 'd410', 'd411', 'd415', 'd416', 'd417'])


def build(description):
    preflight(description)
    return _build(description)


def read_state(memory, built, description, phase, tick):
    ram, symbols = memory.data, built['symbols']

    def byte(label, voice=0):
        return ram[symbols[label] + voice]

    state = dict(tick=tick, nextRow=byte('aw_next_row'), countdown=byte('aw_countdown'),
        voices=[dict(frequency=byte('aw_frequency_lo', voice) | byte('aw_frequency_hi', voice) << 8,
            control=byte('aw_control', voice), attackDecay=byte('aw_attack_decay', voice),
            sustainRelease=byte('aw_sustain_release', voice)) for voice in range(3)],
        pulseHigh=[byte('aw_pulse_high', voice) for voice in range(2)], volume=byte('aw_volume'))
    if 'ending' in description:
        state['ending'] = dict(phase=byte('aw_ending_phase'), nextCall=byte('aw_call_lo') | byte('aw_call_hi') << 8)
    return state


def identity(writes):
    return [(row['phase'], row['tick'], row['address'], row['value']) for row in writes]


def runtime_image(memory, built):
    symbols = built['symbols']
    return memory.data[symbols['aw_state_begin']:symbols['aw_state_end']], memory.data[WORKSPACE]


def poison(memory, built):
    symbols = built['symbols']
    memory.data[symbols['aw_state_begin']:symbols['aw_state_end']] = [0xa5] * built['stateBytes']
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
            require(cpu.processorCycles - began < 19656, 'Reset call exceeds PAL budget')
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
    retained = {0, 1, 2, 63, 255, count - 1} | set(full['restartCalls'])
    if 'ending' in description:
        start = description['ending']['startCall']
        stop = start + description['ending']['releaseCalls']
        retained.update((start - 1, start, stop - 1, stop))

    def observe(cpu, memory):
        nonlocal boundary_count, writer_count
        opcode = memory.data[cpu.pc]
        if opcode in (0x8d, 0x9d, 0x99, 0x8e, 0x8c):
            address = memory.data[cpu.pc + 1] | memory.data[cpu.pc + 2] << 8
            address += cpu.x if opcode == 0x9d else cpu.y if opcode == 0x99 else 0
            if 0xd400 <= address <= 0xd41f:
                writers.setdefault(cpu.pc, dict(opcode=opcode, addresses=set()))['addresses'].add(address)
                writer_count += 1
        if cpu.pc not in (built['symbols']['aw_init_done'], built['symbols']['aw_call_done']) or cpu.sp != 0xfd:
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

    audit, captured = audit_psid(sid, count, observer=observe)
    writes = list(captured)
    actual, wanted = identity(writes), identity(expected)
    for index, pair in enumerate(zip(actual, wanted)):
        require(pair[0] == pair[1], f'Compiled store differs at {index}: {pair[0]} != {pair[1]}')
    require(len(actual) == len(wanted), 'Compiled ordered-store count differs')
    require(boundary_count == count + 1 and writer_count == len(writes), 'Compiled boundary/writer proof incomplete')
    require(audit['maximumPlayCycles'] < 19656, 'Compiled play exceeds PAL budget')
    reset = reset_verification(*last, description, built, cold[0])
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
    poison(memory, built)
    cpu = cpu_type()(memory=memory, pc=2061)
    memory.cpu = cpu
    count = min(2, description['range']['auditCalls'])
    model = player.compute(description, calls=count)
    checked, initialized, entries = 0, False, []
    while checked < count:
        require(cpu.processorCycles < 19656 * (count + 3), 'Standalone bootstrap exceeds bounded raster run')
        # sid_audit_host.harness aliases strict init_return to the repeating wait loop.
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
        limitations='Independent runtime rows and patches; callable RAM-only PAL numeric equivalence. Software reset does not reset physical SID state or untouched registers. Original bus timing, full VICE playback, rendered sound and musical acceptance remain separate.')
    (output / 'verification.json').write_text(json.dumps(checked, indent=2) + '\n')
    return checked
