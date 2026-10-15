"""Build a private serialized-speech/NTSC-music audition, not source IRQ identity.

SpeechSynth decodes the pinned private descriptors at build time. The new native
sampler consumes those values and explicit no-write ticks at a fixed 102 cycles;
it never executes source speech code or consumes captured output events. Music
remains the frozen independent runtime score/patch compiler. All speech-bearing
products stay under ignored build/. Shared callable audits remain unchanged.
"""

import argparse
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from sid_assembler import assemble
from sid_clock import NTSC_CLOCK, NTSC_FRAME_CYCLES
from sid_intake import inspect_sid
from verify_player import cpu_type, require


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


compiler = load('ghostbusters_title_music_compiler', Path(__file__).with_name('compiler.py'))
speech = load('ghostbusters_title_speech_decoder', Path(__file__).with_name('speech.py'))
LOAD, WRAPPER, SAMPLE_CYCLES = 0x0801, 0x0820, 102
GAP, INIT_MARKER, MUSIC_MARKER = 255, 252, 254
ADAPTATION = 'Serialized independent speech decoder; new fixed CIA2 Timer B sample player and CIA1 Timer A NTSC music host. Source checkpoint start offsets quantized to sample ticks; no source IRQ, nested NMI, code-byte sample or PCM identity claim.'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def decode_commands(memory):
    synth, commands, aggregates = speech.SpeechSynth(memory), [], []
    oracle_hash = hashlib.sha256()
    for command in (1, 3):
        synth.start(command)
        ticks = []
        while not synth.finished:
            require(len(ticks) < 100000, 'Decoded speech exceeds bounded command length')
            handler = int(synth.handler)
            value = synth.tick()
            require(value is None or type(value) is int and 0 <= value <= 15, 'Decoder produced a non-volume value')
            ticks.append(GAP if value is None else value)
            stores = [] if value is None else [[0xd418, value]]
            oracle_hash.update(json.dumps([command, len(ticks) - 1, handler, stores], separators=(',', ':')).encode())
        require(ticks[0] == ticks[-1] == 7, 'Decoded command must begin/end at neutral volume 7')
        commands.append(bytes(ticks))
        aggregates.append(dict(command=command, ticks=len(ticks), volumeStores=sum(value != GAP for value in ticks),
            decodedTickSha256=sha(bytes(ticks)), cumulativeOracleSequenceSha256=oracle_hash.hexdigest()))
    return commands, aggregates


def pack_timeline(commands, alignment, timer_start_cycle):
    require(len(commands) == 2 and [row['command'] for row in alignment['commands']] == [1, 3],
        'Opening alignment must describe commands 1 and 3')
    targets = [row['firstNmi'] for row in alignment['commands']] + [alignment['internalMusicInit'], alignment['firstMusicBody']]
    require(all(type(value) is int and value > timer_start_cycle for value in targets)
        and targets == sorted(set(targets)), 'Alignment offsets must be strictly increasing integers')
    stream, placements = bytearray(), []
    for target, values, label in zip(targets, commands + [bytes([INIT_MARKER]), bytes([MUSIC_MARKER])],
                                    ('command1', 'command3', 'musicInit', 'musicBody')):
        index = (target - timer_start_cycle + SAMPLE_CYCLES // 2) // SAMPLE_CYCLES - 1
        require(index >= len(stream), 'Serialized speech overlaps the next measured command or handoff')
        if label.startswith('command'):
            require(values and all(value == GAP or 0 <= value <= 15 for value in values), 'Invalid decoded sample token')
        stream.extend([GAP] * (index - len(stream)))
        stream.extend(values)
        actual = timer_start_cycle + (index + 1) * SAMPLE_CYCLES
        placements.append(dict(name=label, tick=index, sourceCheckpointCycle=target,
            scheduledTimerCycle=actual, quantizationCycles=actual - target))
    require(stream[-1] == MUSIC_MARKER and stream.count(INIT_MARKER) == stream.count(MUSIC_MARKER) == 1,
        'Timeline must contain exactly one initialization and terminal music marker')
    return bytes(stream), placements


def wrapper_source(music, stream_address):
    source = (ROOT / 'songs/players/ghostbusters-title.asm').read_text()
    constants = dict(SPEECH_LO=stream_address & 255, SPEECH_HI=stream_address >> 8,
        MUSIC_INIT=music['symbols']['entry_init'], MUSIC_PLAY=music['symbols']['entry_play'],
        NMI_LO=0, NMI_HI=0, IRQ_LO=0, IRQ_HI=0)
    cpu_type()
    _, labels, _ = assemble(source, constants, load=WRAPPER)
    constants.update(NMI_LO=labels['title_nmi'] & 255, NMI_HI=labels['title_nmi'] >> 8,
        IRQ_LO=labels['title_irq'] & 255, IRQ_HI=labels['title_irq'] >> 8)
    payload, labels, listing = assemble(source, constants, load=WRAPPER)
    require(WRAPPER + len(payload) <= compiler.LOAD, 'Title wrapper overlaps music')
    return payload, labels, source, listing


def startup_cycles(wrapper, symbols):
    memory = [0] * 65536
    memory[WRAPPER:WRAPPER + len(wrapper)] = wrapper
    cpu = cpu_type()(memory=memory, pc=symbols['title_init'])
    while cpu.pc != symbols['title_sample_timer_start']:
        require(cpu.processorCycles < 2000, 'Native timer setup does not terminate')
        cpu.step()
    return cpu.processorCycles + 4


def admit_rsid(data):
    header = inspect_sid(data, subtune=1)
    require(header['format'] == 'RSID' and header['headerLoadAddress'] == header['playAddress'] == header['speedWord'] == 0
        and header['dataOffset'] == 124 and header['flags'] == 0x18
        and header['subtunes'] == header['defaultSubtune'] == 1
        and header['loadAddress'] == LOAD <= header['initAddress'] < header['endAddressExclusive'] < 0xd000
        and not any(data[120:124]), 'Native RSID reserved fields, target or memory contract differ')
    return header


def build(composition, memory, alignment, *, seconds=245):
    require(type(seconds) in (int, float) and math.isfinite(seconds) and 5 <= seconds <= 260,
        'Title duration must be a finite 5–260 seconds')
    require(alignment['clockHz'] == NTSC_CLOCK, 'Alignment must use the explicit NTSC clock')
    description = deepcopy(composition)
    calls = math.ceil((seconds * NTSC_CLOCK - alignment['firstMusicBody']) / NTSC_FRAME_CYCLES) + 2
    require(1 <= calls <= 16000, 'Title music exceeds the frozen bounded compiler range')
    description['range']['auditCalls'] = calls
    sid, music = compiler.build(description)
    music_payload = sid[124:]
    stream_address = music['payloadEndAddress']
    wrapper, symbols, source, listing = wrapper_source(music, stream_address)
    timer_start = startup_cycles(wrapper, symbols)
    commands, aggregates = decode_commands(memory)
    stream, placements = pack_timeline(commands, alignment, timer_start)
    end = stream_address + len(stream)
    require(end < 0xd000, 'Decoded speech crosses SID I/O; this wrapper has no banked-data path')
    image = bytearray(end - LOAD)
    image[:12] = bytes.fromhex('0b080a009e32303631000000')
    image[12:18] = bytes([0x20, symbols['title_init'] & 255, symbols['title_init'] >> 8,
        0x4c, symbols['title_idle'] & 255, symbols['title_idle'] >> 8])
    image[WRAPPER - LOAD:WRAPPER - LOAD + len(wrapper)] = wrapper
    image[compiler.LOAD - LOAD:stream_address - LOAD] = music_payload
    image[stream_address - LOAD:] = stream
    header = bytearray(124)
    header[:4] = b'RSID'
    for offset, value in ((4, 2), (6, 124), (10, symbols['title_init']), (14, 1), (16, 1), (118, 0x18)):
        struct.pack_into('>H', header, offset, value)
    for offset, value in ((22, 'Ghostbusters serialized title'), (54, 'SID Song Crafter'), (86, '2026 scheduling adaptation')):
        header[offset:offset + 32] = compiler.text(value, 'metadata')
    prg = LOAD.to_bytes(2, 'little') + image
    rsid = bytes(header) + prg
    admit_rsid(rsid)
    return dict(rsid=rsid, prg=prg, stream=stream, commands=commands, composition=description, music=music, musicSid=sid,
        symbols=symbols, wrapperSource=source, wrapperListing=listing, info=dict(schemaVersion=1,
            adaptation=ADAPTATION, profile=dict(clock='ntsc', sidModel='MOS6581'), durationSeconds=seconds,
            musicCalls=calls, musicCallRange=dict(firstInclusive=0, lastExclusive=calls),
            samplePeriodCycles=SAMPLE_CYCLES, sampleTimer='CIA2 Timer B', musicTimer='CIA1 Timer A',
            musicPeriodCycles=NTSC_FRAME_CYCLES, timerSetupCpuCycles=timer_start,
            loadAddress=LOAD, initAddress=symbols['title_init'], bootstrapAddress=0x080d,
            streamAddress=stream_address, streamBytes=len(stream), streamSha256=sha(stream), payloadEndAddress=end,
            commands=aggregates, alignment=placements, originalInstructionsIncluded=False,
            capturedOutputPlayback=False, decodedPrivateSpeechData=True, runtimeMusicScore=True,
            speechInterleaving='serialized', display='disabled', sourceIrqIdentity=False))


class NativeMemory:
    """Instruction-boundary CIA model for new code only; VICE checks real timers."""

    def __init__(self, prg):
        self.data = [0] * 65536
        address = int.from_bytes(prg[:2], 'little')
        self.data[address:address + len(prg) - 2] = prg[2:]
        self.cpu = None
        self.writes = []
        self.next_nmi = self.next_irq = None
        self.timer_nmi = self.timer_irq = None
        self.nmi_pending = self.irq_pending = False
        self.nmi_mask = self.irq_mask = False

    def __getitem__(self, address):
        if address == 0xdd0d:
            self.nmi_pending = False
            return 0x82
        if address == 0xdc0d:
            self.irq_pending = False
            return 0x81
        return self.data[address]

    def __setitem__(self, address, value):
        self.data[address] = value
        cycle = self.cpu.processorCycles if self.cpu is not None else 0
        if 0xd400 <= address <= 0xd41f:
            self.writes.append(dict(cycle=cycle, address=address, value=value))
        if address in (0xdd0d, 0xdc0d):
            enabled = bool(value & 128)
            if address == 0xdd0d:
                self.nmi_mask = enabled and bool(value & 2)
            else:
                self.irq_mask = enabled and bool(value & 1)
        if address in (0xdd0f, 0xdc0e):
            base = 0xdd06 if address == 0xdd0f else 0xdc04
            period = self.data[base] | self.data[base + 1] << 8
            if address == 0xdd0f:
                self.timer_nmi = period + 1
                self.next_nmi = cycle + 4 + self.timer_nmi if value & 1 else None
            else:
                self.timer_irq = period + 1
                self.next_irq = cycle + 4 + self.timer_irq if value & 1 else None


def pairs(writes):
    return [(row['address'], row['value']) for row in writes]


def verify_native(built, calls=2, *, bootstrap=False, poisoned=False, fast_forward=True):
    require(type(calls) is int and 1 <= calls <= built['info']['musicCalls'], 'Native calls exceed the declared music range')
    memory = NativeMemory(built['prg'])
    cpu = cpu_type()(memory=memory)
    memory.cpu = cpu
    cpu.sp, cpu.p = 255, cpu.UNUSED | cpu.DECIMAL
    symbols, music = built['symbols'], built['music']
    if poisoned:
        compiler.poison(memory, music)
        memory.data[0xd0:0xd2] = [0xa5, 0xa5]
        memory.data[symbols['title_stage']] = 0xa5
    if bootstrap:
        cpu.pc = 0x080d
    else:
        memory.data[0x0400:0x0406] = [0x20, symbols['title_init'] & 255, symbols['title_init'] >> 8, 0x4c, 3, 4]
        cpu.pc = 0x0400
    model = compiler.player.compute(built['composition'], calls=calls)
    expected = [(address, 0) for address in range(0xd417, 0xd3ff, -1)] + [(0xd418, 15)]
    expected += [(0xd418, value) for value in built['stream'] if value <= 15]
    expected += pairs(model['writes'])
    entries, returns, nmis, states = [], 0, [], 0
    init_entry = None
    active_nmi = None
    nmi_cycles = []
    skipped_idle = 0
    limit = built['info']['alignment'][-1]['scheduledTimerCycle'] + (calls + 3) * NTSC_FRAME_CYCLES
    while returns < calls:
        require(cpu.processorCycles < limit, 'Native title exceeded modeled machine diagnostic bound')
        # These exact JMP-to-self instructions cannot change state. Whole
        # three-cycle iterations retain IRQ dispatch phase (title idle guard).
        if fast_forward and cpu.pc in (0x0403, symbols['title_idle']) and memory.next_nmi is None \
                and not memory.irq_pending and memory.next_irq is not None \
                and memory.data[cpu.pc:cpu.pc + 3] == [0x4c, cpu.pc & 255, cpu.pc >> 8]:
            iterations = max(0, (memory.next_irq - cpu.processorCycles - 1) // 3)
            cpu.processorCycles += iterations * 3
            skipped_idle += iterations
        if memory.next_nmi is not None and cpu.processorCycles >= memory.next_nmi:
            require(not memory.nmi_pending and active_nmi is None, 'Native sampler overlapped or lost a timer tick')
            memory.next_nmi += memory.timer_nmi
            memory.nmi_pending = True
            if memory.nmi_mask:
                cpu.nmi()
        if memory.next_irq is not None and cpu.processorCycles >= memory.next_irq:
            memory.next_irq += memory.timer_irq
            memory.irq_pending = True
        if memory.irq_pending and memory.irq_mask and not cpu.p & cpu.INTERRUPT:
            cpu.irq()
        if cpu.pc == symbols['title_init']:
            init_entry = cpu.processorCycles
        if cpu.pc == symbols['title_nmi']:
            require(active_nmi is None, 'Nested native NMI is unsupported')
            active_nmi = cpu.processorCycles
            nmis.append(active_nmi)
        if cpu.pc == symbols['title_nmi_return']:
            nmi_cycles.append(cpu.processorCycles + 6 - active_nmi)
            active_nmi = None
        if cpu.pc == music['symbols']['entry_play']:
            entries.append(cpu.processorCycles)
            require(not memory.nmi_mask and memory.next_nmi is None, 'Music started before sample timer stopped')
            require(not cpu.p & cpu.DECIMAL, 'Native music entered with decimal mode set')
        if cpu.pc == music['symbols']['gb_init_done']:
            require(compiler.read_state(memory, music, built['composition'], 'init', None) == model['initial'], 'Native music init state differs')
            states += 1
        if cpu.pc == music['symbols']['gb_call_done']:
            tick = returns
            require(compiler.read_state(memory, music, built['composition'], 'play', tick) == model['returns'][tick],
                f'Native music named state differs at {tick}')
            returns += 1
            states += 1
        cpu.step()
    require(pairs(memory.writes) == expected, 'Native complete ordered speech/music stores differ')
    require(len(nmis) == len(built['stream']) and max(nmi_cycles) + 7 < SAMPLE_CYCLES, 'Native sample count or interrupt budget differs')
    require(memory.timer_nmi == 102 and memory.timer_irq == NTSC_FRAME_CYCLES, 'Native timer periods differ')
    require(states == calls + 1, 'Native named music boundaries incomplete')
    intervals = [right - left for left, right in zip(entries, entries[1:])]
    require(not intervals or max(abs(value - NTSC_FRAME_CYCLES) for value in intervals) <= 64,
        'Native music cadence exceeds instruction-boundary dispatch allowance')
    return dict(passed=True, scope='py65 new native instructions plus explicit instruction-boundary CIA model; no VIC, ROM, SID synthesis or source IRQ identity',
        bootstrap='Executed SYS2061 machine entry' if bootstrap else 'Real JSR init host',
        checkedMusicCalls=calls, namedMusicStates=states, checkedStores=len(memory.writes),
        generatedSpeechTicks=len(nmis), maximumNmiCyclesIncludingEntry=max(nmi_cycles) + 7,
        timerSampleCycles=memory.timer_nmi, timerMusicCycles=memory.timer_irq,
        musicEntryFromInit=entries[0] - init_entry, musicIntervals=intervals,
        allOrderedStoresMatch=True, noSpeechNmiDuringMusic=True, decimalEntryCleared=True,
        nativeCpuCycles=cpu.processorCycles - init_entry, fastForwardedIdleIterations=skipped_idle,
        timedStoreSequenceSha256=sha(json.dumps(memory.writes, separators=(',', ':')).encode()))


def verify_vice(built, output, vice, calls):
    require(type(calls) is int and 2 <= calls <= built['info']['musicCalls'], 'VICE calls exceed the declared music range')
    grammar = load('ghostbusters_title_machine_trace_grammar', Path(__file__).with_name('probe-machine.py'))
    symbols, music = built['symbols'], built['music']
    host = output / 'private-host.prg'
    host.write_bytes(bytes([0, 4, 0x20, symbols['title_init'] & 255, symbols['title_init'] >> 8, 0x4c, 3, 4]))
    program, monitor = output / 'reconstructed.prg', output / 'commands.mon'
    for path in (program, host, monitor, vice):
        require(not any(character in str(path) for character in ('"', '\n', '\r')), 'Unsafe monitor path')
    observed_labels = [symbols['title_init'], symbols['title_nmi'], symbols['title_nmi_return'],
        music['symbols']['entry_init'], music['symbols']['gb_init_done'], music['symbols']['entry_play'],
        music['symbols']['gb_call_done']]
    lines = ['radix h', 'sidefx off', 'dummy off', 'bank ram', f'load "{program}" 0', f'load "{host}" 0',
        'bank cpu', '> $0000 $2f $37', '> $d01a $00', '> $dc0d $7f', '> $dd0d $7f',
        'sidefx on', 'm $dc0d $dc0d', 'm $dd0d $dd0d',
        'r a=$00,x=$00,y=$00,sp=$ff,fl=$28', 'r pc=$0400']
    lines += [f'trace exec ${pc:04x}' for pc in observed_labels]
    lines += ['trace store $d400 $d7ff', 'trace load $d400 $d7ff',
        f'break exec ${music["symbols"]["entry_play"]:04x}', f'ignore 10 ${calls:04x}', 'g', 'r', 'quit', '']
    monitor.write_text('\n'.join(lines))
    cycle_limit = built['info']['alignment'][-1]['scheduledTimerCycle'] + (calls + 3) * NTSC_FRAME_CYCLES + 4000000
    command = [str(vice), '-config', '/dev/null', '-directory', str(ROOT / '.tools/vice-headless-3.9/source/data'),
        '-ntsc', '+logcolorize', '-initbreak', 'ready', '-moncommands', str(monitor),
        '-monlog', '-monlogname', str(output / 'private-monitor.log'), '-limitcycles', str(cycle_limit),
        '-warp', '+sound', '-sidenginemodel', 'resid6581', '-cia1model', '1', '-cia2model', '1']
    env = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY'):
        env.pop(key, None)
    for key in ('XDG_CONFIG_HOME', 'XDG_STATE_HOME'):
        env[key] = str(output / key.lower())
        (Path(env[key]) / 'vice').mkdir(parents=True)
    write_json(output / 'vice-command.json', command)
    with (output / 'private-process.log').open('w') as file:
        subprocess.run(command, env=env, stdout=file, stderr=subprocess.STDOUT, check=True, timeout=600)
    raw = (output / 'private-monitor.log').read_bytes()
    rows = grammar.parse_records(raw.decode('latin-1'))
    expected_registrations = [(index, 'trace', 'exec', pc, None) for index, pc in enumerate(observed_labels, 1)]
    expected_registrations += [(8, 'trace', 'store', 0xd400, 0xd7ff), (9, 'trace', 'load', 0xd400, 0xd7ff),
        (10, 'break', 'exec', music['symbols']['entry_play'], None)]
    import re
    registrations = re.findall(r'^(TRACE|BREAK): (\d+) +C:\$([0-9a-f]{4})(?:-\$([0-9a-f]{4}))? +\(([^)]+)\)( disabled)?$',
        raw.decode('latin-1'), re.MULTILINE | re.IGNORECASE)
    require(len(registrations) == len(expected_registrations), 'Native VICE checkpoints missing or extra')
    for actual, expected in zip(registrations, expected_registrations):
        kind, number, first, last, operation, disabled = actual
        index, expected_kind, expected_operation, address, end = expected
        require(not disabled and (int(number), kind.lower(), int(first, 16), int(last, 16) if last else None)
            == (index, expected_kind, address, end)
            and operation.lower() == ('trace ' if expected_kind == 'trace' else 'stop on ') + expected_operation,
            'Native VICE checkpoint coverage altered')
    terminal = [row for row in rows if row['kind'] == 'stop on']
    require(len(terminal) == 1 and terminal[0]['checkpoint'] == 10 and rows[-1] == terminal[0],
        'Native VICE terminal play was executed or wrong stop')
    stores = [row for row in rows if row['operation'] == 'store' and 'sidAddress' in row]
    require(not any(row['operation'] == 'load' and 'sidAddress' in row for row in rows), 'Native SID reads unexpectedly present')
    model = compiler.player.compute(built['composition'], calls=calls)
    expected = [(address, 0) for address in range(0xd417, 0xd3ff, -1)] + [(0xd418, 15)]
    expected += [(0xd418, value) for value in built['stream'] if value <= 15] + pairs(model['writes'])
    require([(row['sidAddress'], row['value']) for row in stores] == expected, 'Native VICE ordered speech/music stores differ')
    def exec_at(pc):
        return [row for row in rows if row['operation'] == 'exec' and row['pc'] == pc and row['kind'] == 'trace']
    nmis, nmi_returns = exec_at(symbols['title_nmi']), exec_at(symbols['title_nmi_return'])
    entries, completed = exec_at(music['symbols']['entry_play']), exec_at(music['symbols']['gb_call_done'])
    require(len(nmis) == len(nmi_returns) == len(built['stream']) and len(completed) == calls and len(entries) == calls + 1,
        'Native VICE sample or completed-music coverage differs')
    require(all(left['monitorCycle'] < end['monitorCycle'] < right['monitorCycle']
        for left, end, right in zip(nmis, nmi_returns, nmis[1:])), 'Native VICE NMI nesting occurred')
    sample_jitter = [row['monitorCycle'] - nmis[0]['monitorCycle'] - index * SAMPLE_CYCLES for index, row in enumerate(nmis)]
    require(max(sample_jitter) - min(sample_jitter) <= 24, 'Native fixed sample cadence lost or delayed ticks')
    music_intervals = [right['monitorCycle'] - left['monitorCycle'] for left, right in zip(entries, entries[1:])]
    require(max(abs(value - NTSC_FRAME_CYCLES) for value in music_intervals) <= 64, 'Native VICE music cadence differs')
    require(nmi_returns[-1]['monitorCycle'] < entries[0]['monitorCycle'], 'Native music and speech overlap')
    init = exec_at(symbols['title_init'])
    require(len(init) == len(exec_at(music['symbols']['entry_init'])) == 1, 'Native init count differs')
    command_starts = [nmis[row['tick']]['monitorCycle'] - init[0]['monitorCycle'] for row in built['info']['alignment'][:2]]
    result = dict(passed=True, scope='Actual NTSC VICE, real JSR native init, complete decoded speech stream and bounded music. Ordered stores and timer cadence; no source IRQ/PCM identity, rendered audio or physical hardware claim.',
        checkedMusicCalls=calls, completedMusicCalls=len(completed), terminalPlayExecuted=False,
        cycleLimit=cycle_limit, processTimeoutSeconds=600,
        sidStores=len(stores), sidReads=0, nmiEntries=len(nmis), nestedNmi=False,
        samplePeriodCycles=102, sampleEntryJitter=dict(minimum=min(sample_jitter), maximum=max(sample_jitter)),
        maximumObservedNmiCyclesIncludingEntry=max(end['monitorCycle'] + 6 - start['monitorCycle'] + 7 for start, end in zip(nmis, nmi_returns)),
        musicPeriodCycles=NTSC_FRAME_CYCLES, musicIntervals=dict(minimum=min(music_intervals), maximum=max(music_intervals)),
        actualInitRelativeFirstNmi=command_starts,
        actualInitRelativeMusicInit=exec_at(music['symbols']['entry_init'])[0]['monitorCycle'] - init[0]['monitorCycle'],
        actualInitRelativeFirstMusic=entries[0]['monitorCycle'] - init[0]['monitorCycle'],
        tools=dict(viceSha256=sha(vice.read_bytes()), traceParserSha256=sha(Path(__file__).with_name('probe-machine.py').read_bytes()),
            sharedTraceGrammarSha256=sha((ROOT / 'scripts/trace-sid-vice.py').read_bytes())))
    write_json(output / 'vice.json', result)
    private = {}
    for name in ('private-monitor.log', 'private-process.log'):
        data = (output / name).read_bytes()
        path = output / (name + '.gz')
        path.write_bytes(gzip.compress(data, mtime=0))
        (output / name).unlink()
        private[path.name] = dict(bytes=path.stat().st_size, sha256=sha(path.read_bytes()))
    result['privateArtifacts'] = private
    write_json(output / 'vice.json', result)
    return result


def verify_source_music(source, built):
    oracle = load('ghostbusters_title_source_music_oracle', Path(__file__).with_name('probe-form.py'))
    data = source.read_bytes()
    require(sha(data) == speech.SOURCE_SHA, 'Extended music source fingerprint differs')
    _, _, description = oracle.decode_source(data)
    observed = oracle.observe_source(data, description, built['info']['musicCalls'])
    model = compiler.player.compute(built['composition'])
    require(compiler.identity(observed['writes']) == compiler.identity(model['writes']), 'Extended source music stores differ')
    require(observed['returns'] == [row['score'] for row in model['returns']], 'Extended source music score states differ')
    require(observed['initialCachedControls'] == model['initial']['cachedControls'], 'Extended source initial caches differ')
    require([row['cachedControls'] for row in observed['contexts']] == [row['cachedControls'] for row in model['returns']],
        'Extended source music caches differ')
    compiled, _ = compiler.verify(built['composition'], built['musicSid'], built['music'], computed=model)
    return dict(sourceSha256=sha(data), freshOriginalMusicCpu=True, checkedMusicCalls=built['info']['musicCalls'],
        matchedStores=len(observed['writes']), namedReturns=len(observed['returns']), resetCalls=model['resetCalls'],
        scope=observed['audit']['environment'], speechOrFullMachineSourceIdentity=False,
        fullIndependentCompiledMusic=compiled)


def run(source, composition_path, alignment_path, output, *, seconds=245, calls=16, vice=None, source_music=False):
    require(not output.exists() and output.resolve().is_relative_to((ROOT / 'build').resolve()), 'Choose a fresh private build/ output')
    data = source.read_bytes()
    memory = speech.private_source_memory(data)
    alignment_record = json.loads(alignment_path.read_text())
    require(alignment_record['sourceSha256'] == speech.SOURCE_SHA, 'Alignment source pin differs')
    composition = json.loads(composition_path.read_text())
    built = build(composition, memory, alignment_record['sourceAlignment'], seconds=seconds)
    decoder_receipt_path = ROOT / 'evidence/ghostbusters-components/speech/verification.json'
    decoder_receipt = json.loads(decoder_receipt_path.read_text())
    require(decoder_receipt['sourceSha256'] == speech.SOURCE_SHA
        and decoder_receipt['tools']['speech.py'] == sha(Path(__file__).with_name('speech.py').read_bytes())
        and built['info']['commands'][-1]['cumulativeOracleSequenceSha256']
            == decoder_receipt['cases']['baseline']['outputSequenceSha256'], 'Generated speech differs from frozen serialized original CPU oracle')
    output.mkdir(parents=True)
    for name, product in (('reconstructed.sid', built['rsid']), ('reconstructed.prg', built['prg']), ('private-speech.bin', built['stream'])):
        (output / name).write_bytes(product)
    (output / 'player.asm').write_text(built['wrapperSource'] + '\n' + built['music']['source'])
    (output / 'player.listing').write_text(built['wrapperListing'] + built['music']['listing'])
    write_json(output / 'composition.json', built['composition'])
    built['info']['inputs'] = {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in (source, composition_path, alignment_path, decoder_receipt_path)}
    built['info']['tools'] = {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in (
        Path(__file__), Path(__file__).with_name('compiler.py'), Path(__file__).with_name('player.py'),
        Path(__file__).with_name('score.py'), Path(__file__).with_name('programs.py'), Path(__file__).with_name('speech.py'),
        ROOT / 'songs/players/ghostbusters.asm', ROOT / 'songs/players/ghostbusters-title.asm', ROOT / 'scripts/sid_assembler.py',
        ROOT / 'scripts/sid_clock.py', ROOT / 'scripts/sid_intake.py', ROOT / 'scripts/psid_audit.py',
        ROOT / 'scripts/psid_profile.py', ROOT / 'scripts/sid_audit_host.py', ROOT / 'scripts/verify_player.py')}
    if source_music:
        path = Path(__file__).with_name('probe-form.py')
        built['info']['tools'][str(path.relative_to(ROOT))] = sha(path.read_bytes())
    write_json(output / 'build.json', built['info'])
    result = dict(schemaVersion=1, adaptation=ADAPTATION, cpu=verify_native(built, calls),
        prgBootstrap=verify_native(built, 2, bootstrap=True), poisonedInit=verify_native(built, 2, poisoned=True),
        generatedSpeechMatchesRetainedSerializedOriginalCpu=True, header=admit_rsid(built['rsid']))
    if source_music:
        result['extendedSourceMusic'] = verify_source_music(source, built)
    if vice is not None:
        result['vice'] = verify_vice(built, output, vice, calls)
    result['privateArtifacts'] = {name: dict(bytes=(output / name).stat().st_size, sha256=sha((output / name).read_bytes()))
        for name in ('reconstructed.sid', 'reconstructed.prg', 'private-speech.bin')}
    write_json(output / 'verification.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/research/ghostbusters/Ghostbusters.sid')
    parser.add_argument('--composition', type=Path, default=ROOT / 'evidence/ghostbusters-player/composition.json')
    parser.add_argument('--alignment', type=Path, default=ROOT / 'evidence/ghostbusters-speech-handoff/summary.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=245)
    parser.add_argument('--probe-calls', type=int, default=16)
    parser.add_argument('--vice', type=Path)
    parser.add_argument('--verify-source-music', action='store_true')
    args = parser.parse_args()
    result = run(args.source.resolve(), args.composition.resolve(), args.alignment.resolve(), args.output.resolve(),
        seconds=args.seconds, calls=args.probe_calls, vice=args.vice, source_music=args.verify_source_music)
    print(json.dumps(dict(verification=str(args.output / 'verification.json'), native=result['cpu']['passed'],
        speechTicks=result['cpu']['generatedSpeechTicks'], musicCalls=result['cpu']['checkedMusicCalls'],
        vicePassed=result.get('vice', {}).get('passed'), adaptation=ADAPTATION), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Ghostbusters serialized title: {error}')
