"""Compile editable Deflektor score/program data into computed PAL/6581 exports."""

import hashlib
import json
from pathlib import Path
import struct
from time import perf_counter

from deflektor_asm import PLAYER, long_branches
from deflektor_player import (GLOBAL_FIELDS, VOICE_FIELDS, compute_writes, initial_state,
                              programs, numeric_table)
from deflektor_score import validate_tables
from psid_audit import AuditMemory, audit_psid
from sid_assembler import assemble
from sid_audit_host import harness
from verify_player import cpu_type, require

ROOT = Path(__file__).resolve().parents[1]
LOAD_ADDRESS = 0x1000
WORD_FIELDS = ('frequency', 'pulse_word', 'glide_step')
PROFILE = dict(clock='pal', sidModel='6581', sidCount=1, sidBases=[0xd400], cadence='vbi')


def data(label, values):
    require(bool(values), f'{label} requires data')
    return label + ':\n  .byte ' + ','.join(f'${value:02x}' if type(value) is int else value for value in values) + '\n'


def header_text(value, field):
    require(type(value) is str and '\0' not in value, f'{field} must be text without embedded NUL')
    try:
        encoded = value.encode('latin-1')
    except UnicodeEncodeError as error:
        raise ValueError(f'{field} must contain only Latin-1 characters') from error
    return encoded[:31].ljust(32, b'\0')


def header_fields(description):
    return [(offset, header_text(value, field)) for offset, field, value in (
        (22, 'title', description.get('title', 'Deflektor independent title')),
        (54, 'author', description.get('author', 'SID Song Crafter')),
        (86, 'released', '2026 independent reconstruction'))]


def preflight(description):
    require(type(description.get('play_calls')) is int and 1 <= description['play_calls'] <= 65535,
            'Compiled play_calls must be in 1..65535')
    require(description.get('profile', PROFILE) == PROFILE,
            'The reconstructed Deflektor backend supports only PAL/6581 single-SID VBI')
    header_fields(description)
    return compute_writes(description)


def parameters(description):
    globals_, voices = initial_state(description)
    validate_tables(description['score'])
    waves, pitches = programs(description)
    references = {}

    def pointer(label):
        if label is None:
            return [0, 0]
        tokens = []
        for shift in (0, 8):
            token = f'DF_POINTER_{len(references)}'
            references[token] = (label, shift)
            tokens.append(token)
        return tokens

    states = {'df_' + field: [globals_[field]] for field in GLOBAL_FIELDS}
    for field in VOICE_FIELDS:
        for shift, suffix in ((0, '_lo'), (8, '_hi')) if field in WORD_FIELDS else ((0, ''),):
            states['df_' + field + suffix] = [(voice[field] >> shift) & 255 for voice in voices]
    orders = {row['voiceIndex']: row for row in description['score']['orders']}
    order_ptrs = [pointer(f'df_order_{voice}') for voice in range(3)]
    stub_ptr = pointer('df_initial_pattern')
    for half, suffix in enumerate(('lo', 'hi')):
        states['df_order_' + suffix] = [pair[half] for pair in order_ptrs]
        states['df_pattern_' + suffix] = [stub_ptr[half]] * 3
    for field in ('order_cursor', 'pattern_cursor', 'repeat_count', 'transpose'):
        states['df_' + field] = [0] * 3
    states['df_mapping'] = list(description['score']['initMappingDefaults']['bytes'])
    states['df_skip'], states['df_failed'] = [0], [0]
    image = [value for values in states.values() for value in values]
    source = 'df_state_begin:\n' + ''.join(data(label, values) for label, values in states.items())
    source += 'df_state_end:\n' + data('df_initial_state', image)
    source += 'df_restore_state:\n'
    for offset in range(0, len(image), 255):
        length = min(255, len(image) - offset)
        source += (f'  LDY #$00\ndf_restore_{offset}:\n'
                   f'  LDA df_initial_state++{offset},Y\n  STA df_state_begin++{offset},Y\n'
                   f'  INY\n  CPY #${length:02x}\n  BNE df_restore_{offset}\n')
    source += '  RTS\n' + data('df_sid_offsets', [0, 7, 14]) + data('df_mapping_offsets', [0, 8, 16])
    source += data('df_initial_pattern', [255])
    for voice, order in sorted(orders.items()):
        source += data(f'df_order_{voice}', order['bytes'])
    patterns = {row['patternId']: row for row in description['score']['patterns']}
    pattern_ptrs = [pointer(f'df_pattern_{index}' if index in patterns else None) for index in range(128)]
    for half, suffix in enumerate(('lo', 'hi')):
        source += data('df_pattern_table_' + suffix, [pair[half] for pair in pattern_ptrs])
    for index, pattern in patterns.items():
        source += data(f'df_pattern_{index}', pattern['bytes'])
    records = {row['recordOffset']: row for row in description['score']['recordTable']['records']}
    size = max(records, default=0) + 1
    for field in range(9):
        source += data(f'df_record_{field}', [records[index]['fields'][field] if index in records else 0
                                            for index in range(size)])
    source += data('df_record_resonance', [records[index]['contextual_resonance_selector'] if index in records else 0
                                         for index in range(size)])
    frequencies = numeric_table(description['frequency_words'], 256, 'frequency_words')
    for shift, suffix in ((0, 'lo'), (8, 'hi')):
        source += data('df_frequency_table_' + suffix,
                       [(frequencies.get(index, 0) >> shift) & 255 for index in range(256)])
    for label, field, size in (('df_motion', 'motion_table', 280), ('df_resonance', 'resonance_table', 257)):
        table = numeric_table(description[field], size, field)
        source += data(label, [table.get(index, 0) for index in range(size)])
    for prefix, values in (('df_wave', waves), ('df_score_pitch', pitches)):
        pairs = [pointer(f'{prefix}_program_{index}' if index in values else None) for index in range(256)]
        for half, suffix in enumerate(('lo', 'hi')):
            source += data(prefix + '_table_' + suffix, [pair[half] for pair in pairs])
        for selector, program in values.items():
            packed = [len(program.stages), int(program.loop)]
            if prefix == 'df_wave':
                packed += [value for stage in program.stages for value in (stage.control_bits, stage.duration)]
            else:
                packed += [program.initial_wait, program.restart_wait]
                packed += [value for stage in program.stages for value in (stage.offset, stage.duration)]
            source += data(f'{prefix}_program_{selector}', packed)
    return source, references, dict(stateBytes=len(image), patternCount=len(patterns), instrumentCount=len(records))


def _build(description):
    generated, references, sizes = parameters(description)
    source = long_branches(PLAYER + generated)
    cpu_type()
    constants = {name: 0 for name in references}
    _, preliminary, _ = assemble(source, constants, load=LOAD_ADDRESS)
    constants.update({name: (preliminary[label] >> shift) & 255
                      for name, (label, shift) in references.items()})
    payload, symbols, listing = assemble(source, constants, load=LOAD_ADDRESS)
    require(LOAD_ADDRESS + len(payload) <= 0xa000, 'Compiled Deflektor escapes callable RAM')
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 2), (6, 124), (8, LOAD_ADDRESS), (10, symbols['entry_init']),
                          (12, symbols['entry_play']), (14, 1), (16, 1), (118, 0x14)):
        struct.pack_into('>H', header, offset, value)
    for offset, value in header_fields(description):
        header[offset:offset + 32] = value
    return bytes(header) + payload, dict(symbols=symbols, source=source, listing=listing,
        loadAddress=LOAD_ADDRESS, payloadBytes=len(payload), payloadEndAddress=LOAD_ADDRESS + len(payload),
        originalDriverIncluded=False, registerDumpPlayback=False, runtimeScoreScheduler=True,
        indefinitePlaybackSupported=False, profile=PROFILE,
        supportedCallRange=dict(firstInclusive=0, lastExclusive=description['play_calls']), **sizes)


def build(description):
    """Compile the declared cold finite score after complete numeric admission.

    Orders, patterns, patch fields and numeric program tables remain runtime
    inputs. The export has the reconstructed PAL/6581 cadence and tuning;
    native workflow regional support does not retune this source-specific backend.
    Source annotations have no influence on its executable bytes.
    Optional title/author labels use Latin-1, truncated to 31 bytes plus NUL;
    these header fields do not change the computed player payload.
    """
    preflight(description)
    return _build(description)


def read_state(memory, built):
    symbols, ram = built['symbols'], memory.data
    voices = []
    for voice in range(3):
        state = {}
        for field in VOICE_FIELDS:
            if field in WORD_FIELDS:
                state[field] = ram[symbols['df_' + field + '_lo'] + voice] | ram[symbols['df_' + field + '_hi'] + voice] << 8
            else:
                state[field] = ram[symbols['df_' + field] + voice]
        voices.append(state)
    return dict(globals={field: ram[symbols['df_' + field]] for field in GLOBAL_FIELDS}, voices=voices)


def identity(rows):
    return [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]


def reset_verification(cpu, memory, description, built):
    require(cpu.pc == 0x0200 and cpu.sp == 255, 'Reset requires a completed callable boundary')
    symbols = built['symbols']
    memory.data[symbols['df_state_begin']:symbols['df_state_end']] = [0xa5] * built['stateBytes']

    def call(address, phase, tick):
        start = len(memory.writes)
        memory.phase, memory.tick = phase, tick
        cpu.stPushWord(0x01ff)
        cpu.pc = address
        began = cpu.processorCycles
        while cpu.pc != 0x0200:
            require(cpu.processorCycles - began < 19656, 'Reset call exceeds the PAL budget')
            memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
            memory.instruction_cycle = cpu.processorCycles - began
            cpu.step()
        require(cpu.sp == 255, 'Reset did not preserve its callable stack')
        return memory.writes[start:]

    require(not call(symbols['entry_init'], 'init', None), 'Cold initialization must emit no SID stores')
    require(read_state(memory, built) == description['initial_state'], 'Reinit cold named state differs')
    play = call(symbols['entry_play'], 'play', 0)
    require(identity(play) == identity(compute_writes(description, calls=1)), 'First-call reset stores differ')
    return dict(passed=True, restoredPoisonedState=True, matchedInitStores=0, matchedFirstCallStores=len(play))


def verify(description, sid, built, calls=None):
    """Check all ordered numeric stores, CPU budgets and cold reset without a SID source."""
    count = description['play_calls'] if calls is None else calls
    require(type(count) is int and 1 <= count <= description['play_calls'], 'Requested calls exceed declared range')
    expected = compute_writes(description, calls=count)
    boundaries, last_cpu = 0, []
    first_stop, writer_count, writers = [], 0, {}
    checkpoints = []
    retained = {0, 1, 63, 255, 256, 8479, 8480, 8481, count - 1}

    def observer(cpu, memory):
        nonlocal boundaries, writer_count
        opcode = memory.data[cpu.pc]
        if opcode in (0x8d, 0x9d, 0x99, 0x8e, 0x8c):
            address = memory.data[cpu.pc + 1] | memory.data[cpu.pc + 2] << 8
            address += cpu.x if opcode == 0x9d else cpu.y if opcode == 0x99 else 0
            if 0xd400 <= address <= 0xd41f:
                writers.setdefault(cpu.pc, dict(opcode=opcode, addresses=set()))['addresses'].add(address)
                writer_count += 1
        if cpu.pc not in (built['symbols']['df_init_done'], built['symbols']['df_call_done']) or cpu.sp != 0xfd:
            return
        require(not memory.data[built['symbols']['df_failed']], 'Compiled unsupported score guard fired')
        if memory.phase == 'play' and not memory.data[built['symbols']['df_play_flag']] and not first_stop:
            first_stop.append(memory.tick)
        boundaries += 1
        if memory.phase == 'init' or memory.tick in retained:
            checkpoints.append(dict(phase=memory.phase, call=memory.tick, state=read_state(memory, built)))
        last_cpu[:] = [cpu, memory]

    audit, captured = audit_psid(sid, count, observer=observer)
    writes = list(captured)
    wanted, actual = identity(expected), identity(writes)
    for index, (left, right) in enumerate(zip(wanted, actual)):
        require(left == right, f'Compiled store differs at {index}: {left} != {right}')
    require(len(wanted) == len(actual), f'Compiled store count differs: {len(wanted)} != {len(actual)}')
    require(boundaries == count + 1 and writer_count == len(writes), 'Callable/store proof coverage incomplete')
    stop = first_stop[0] if first_stop else None
    stop_stores = [(row['address'], row['value']) for row in writes if row['tick'] == stop]
    naturally_stopped = stop is not None and stop_stores[-3:] == [(0xd404, 0), (0xd40b, 0), (0xd412, 0)]
    following = [row for row in writes if stop is not None and row['tick'] > stop]
    require(not following, 'Stopped player emitted later SID stores')
    reset = reset_verification(*last_cpu, description, built)
    report = dict(checkedPlayCalls=count, maximumPlayCycles=audit['maximumPlayCycles'],
        orderedStoreComparison=dict(matchedStores=len(writes), fields=['phase', 'tick', 'address', 'value']),
        coldInitializationStores=audit['initWriteCount'], completeDeclaredRange=count == description['play_calls'],
        ending=dict(firstStopCall=stop, naturalControlZeroStop=naturally_stopped,
                    stopStores=[dict(address=address, value=value) for address, value in stop_stores],
                    followingCallsWithoutStores=count - stop - 1 if stop is not None else 0,
                    artificialFade=False),
        sidWriterValidation=dict(checkedStores=writer_count,
            writers=[dict(pc=pc, opcode=site['opcode'], addresses=sorted(site['addresses']))
                     for pc, site in sorted(writers.items())]),
        resetVerification=reset, callableBoundaries=boundaries, audit=audit, checkpoints=checkpoints)
    return report, writes


def standalone_prg(sid, built, calls):
    require(type(calls) is int and 1 <= calls <= built['supportedCallRange']['lastExclusive'],
            'Standalone calls exceed the compiled range')
    host, labels = harness(dict(initAddress=built['symbols']['entry_init'], playAddress=built['symbols']['entry_play']), calls)
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


def bootstrap_verification(prg, labels, description, built):
    """Execute SYS 2061 and two raster-paced calls with modeled VIC/CIA reads."""
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

    require(prg[:2] == b'\x01\x08' and prg[2:14] == bytes.fromhex('0b080a009e32303631000000'),
            'Standalone PRG lacks its SYS 2061 bootstrap')
    memory = RasterMemory()
    memory.data[0x0801:0x0801 + len(prg) - 2] = prg[2:]
    symbols = built['symbols']
    memory.data[symbols['df_state_begin']:symbols['df_state_end']] = [0xa5] * built['stateBytes']
    cpu = cpu_type()(memory=memory, pc=2061)
    memory.cpu = cpu
    calls, initialized, entries = 0, False, []
    target = min(2, description['play_calls'])
    while calls < target:
        require(cpu.processorCycles < 19656 * (target + 2), 'Standalone bootstrap exceeds its raster bound')
        if cpu.pc == labels['init_return'] and not initialized:
            require(read_state(memory, built) == description['initial_state'], 'Standalone did not restore cold named state')
            initialized = True
        if cpu.pc == labels['call']:
            require(initialized, 'Standalone play preceded initialization')
            memory.phase, memory.tick = 'play', calls
            entries.append(cpu.processorCycles)
        if cpu.pc == labels['play_return']:
            require(cpu.sp == 255, 'Standalone play did not preserve its harness stack')
            calls += 1
            if calls == target:
                break
        memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
        memory.instruction_cycle = cpu.processorCycles
        cpu.step()
    require(identity(memory.writes) == identity(compute_writes(description, calls=target)), 'Standalone bootstrap stores differ')
    cadence = [right - left for left, right in zip(entries, entries[1:])]
    require(all(abs(cycles - 19656) <= 9 for cycles in cadence), 'Standalone cadence leaves the PAL grid')
    return dict(passed=True, sysAddress=2061, restoredPoisonedState=True, checkedPlayCalls=calls,
        matchedStores=len(memory.writes), playEntryCycles=entries, callCadenceCycles=cadence, bank=0x37,
        scope='Executed bootstrap and first calls with modeled raster/CIA reads; separate from VICE and SID synthesis.')


def run(description_path, output, calls=None):
    description_path, output = Path(description_path), Path(output)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh output directory')
    source_bytes = description_path.read_bytes()
    description = json.loads(source_bytes)
    stages = {}
    started = perf_counter()
    preflight(description)
    stages['numericPreflight'] = perf_counter() - started
    started = perf_counter()
    sid, built = _build(description)
    stages['assembly'] = perf_counter() - started
    started = perf_counter()
    checked, writes = verify(description, sid, built, calls)
    stages['cpuProof'] = perf_counter() - started
    prg, labels = standalone_prg(sid, built, description['play_calls'])
    bootstrap = bootstrap_verification(prg, labels, description, built)
    output.mkdir(parents=True)
    for name, value in (('reconstructed.sid', sid), ('reconstructed.prg', prg)):
        (output / name).write_bytes(value)
    (output / 'player.asm').write_text(built.pop('source'))
    (output / 'player.listing').write_text(built.pop('listing'))
    for name, value in (('writes.json', writes), ('audit.json', checked.pop('audit')),
                        ('state-checkpoints.json', checked.pop('checkpoints'))):
        (output / name).write_text(json.dumps(value, indent=None if name == 'writes.json' else 2) + '\n')
    report = dict(descriptionPath=str(description_path.resolve()),
        descriptionSha256=hashlib.sha256(source_bytes).hexdigest(), sidSha256=hashlib.sha256(sid).hexdigest(),
        prgSha256=hashlib.sha256(prg).hexdigest(), standaloneHost=dict(labels=labels, calls=description['play_calls']),
        standaloneBootstrapVerification=bootstrap, stageSeconds=stages,
        compilerContract=dict(fullDeclaredNumericPreflight=True, playCalls=description['play_calls'],
                              grammar='Verified title order/pattern commands and numeric programs'),
        toolSha256={name: hashlib.sha256((ROOT / 'scripts' / name).read_bytes()).hexdigest() for name in
                    ('deflektor_compiler.py', 'deflektor_asm.py', 'compose-deflektor.py', 'deflektor_player.py',
                     'deflektor_programs.py', 'deflektor_score.py', 'sid_assembler.py', 'psid_audit.py',
                     'psid_profile.py', 'sid_clock.py',
                     'sid_audit_host.py', 'verify_player.py')},
        limits='Ordered register values and CPU budget; no original bus timing, SID internal, rendered or listening claim.',
        **checked, **built)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
