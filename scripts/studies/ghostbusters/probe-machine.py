"""Capture pinned Ghostbusters #1 init/speech and bounded NTSC music bodies."""

import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from reference_intake import managed_output
from sid_clock import NTSC_CLOCK, NTSC_FRAME_CYCLES
from sid_intake import inspect_sid

SOURCE_SHA = 'f7f05616972d7fd5ad31df91284edbf4e0917d39422f8d004d50b40501a0dcde'
MUSIC_ENTRY = 0x93f0
MUSIC_RETURN = 0x90e6
RASTER_LINE = 257
NMI_ENTRIES = (0xf083, 0xf0a4, 0xf0c3, 0xf0d9, 0xf0e1)
SPEECH_WRITERS = (0xf088, 0xf0a9, 0xf0c8, 0xf0e9)
CHECKPOINTS = [
    ('trace', 'exec', 0x900d, None), ('break', 'exec', 0x0403, None),
    ('trace', 'exec', 0x9096, None), ('trace', 'exec', 0x90d2, None),
    ('trace', 'exec', MUSIC_ENTRY, None), ('trace', 'exec', MUSIC_RETURN, None),
    ('trace', 'exec', 0x9056, None), ('trace', 'exec', 0x93e2, None),
    ('trace', 'exec', 0x9097, None),
    *[('trace', 'exec', pc, None) for pc in NMI_ENTRIES],
    ('trace', 'store', 0xd400, 0xd7ff), ('trace', 'load', 0xd400, 0xd7ff),
    ('trace', 'store', 0x0000, 0x0001), ('trace', 'store', 0xfffa, 0xffff),
    ('trace', 'store', 0xdc00, 0xddff), ('trace', 'load', 0xdc00, 0xddff),
    ('trace', 'store', 0xd011, 0xd01a), ('trace', 'load', 0xd011, 0xd01a),
    ('trace', 'store', 0x0314, 0x0319), ('trace', 'load', 0x02a6, None),
]
TERMINAL_CHECKPOINT = len(CHECKPOINTS) + 1
SID_STORE_CHECKPOINT = 15
SID_READ_CHECKPOINT = 16
NMI_VECTOR_CHECKPOINT = 18
spec = importlib.util.spec_from_file_location('ghostbusters_vice_grammar', ROOT / 'scripts/trace-sid-vice.py')
trace_helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace_helpers)
HEADER = re.compile(r'^#(\d+) \((Trace|Stop on)\s+(exec|store|load)\s+([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\s*$', re.IGNORECASE)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def admit_source(data):
    require(sha(data) == SOURCE_SHA, 'Ghostbusters source fingerprint mismatch')
    header = inspect_sid(data, subtune=1)
    require(header['format'] == 'RSID' and header['flags'] == 0x18
            and header['loadAddress'] == header['initAddress'] == 0x900d
            and header['endAddressExclusive'] == 0xa835 and header['playAddress'] == 0
            and header['subtunes'] == 5 and header['defaultSubtune'] == 1
            and header['dataOffset'] == 124 and header['headerLoadAddress'] == 0
            and header['speedWord'] == 0, 'Unexpected Ghostbusters machine contract')
    return header


def host_program():
    """Use psiddrv.a65 setregs/idle's real JSR stack rather than a synthetic RTS."""
    return bytes.fromhex('0004 200d90 4c0304')


def parse_records(log):
    """Reuse the monitor instruction grammar with independently bounded NTSC rows."""
    lines, records = log.splitlines(), []
    for index, line in enumerate(lines):
        match = HEADER.fullmatch(line)
        if match is None:
            require(not re.match(r'^#\d+ \((?:Trace|Stop on)', line), 'Unrecognized VICE trace header')
            continue
        require(index + 1 < len(lines), 'Missing trace instruction')
        instruction = trace_helpers.INSTRUCTION.fullmatch(lines[index + 1])
        require(instruction is not None, 'Unsupported VICE instruction record')
        checkpoint, kind, operation, address, raster, raster_cycle = match.groups()
        pc, encoded, assembly, a, x, y, sp, flags, cycle = instruction.groups()
        row = dict(checkpoint=int(checkpoint), kind=kind.lower(), operation=operation.lower(),
                   address=int(address, 16), pc=int(pc, 16), bytes=''.join(encoded.split()).lower(),
                   assembly=assembly.strip(), a=int(a, 16), x=int(x, 16), y=int(y, 16),
                   sp=int(sp, 16), flags=flags, rasterLine=int(raster),
                   rasterCycle=int(raster_cycle), monitorCycle=int(cycle))
        require(0 <= row['rasterLine'] < 263 and 0 <= row['rasterCycle'] < 65,
                'Checkpoint outside 263-line NTSC raster geometry')
        if 0xd400 <= row['address'] <= 0xd7ff and row['operation'] != 'exec':
            row['sidAddress'] = 0xd400 + (row['address'] & 31)
        if row['operation'] == 'store':
            opcode = bytes.fromhex(row['bytes'])
            if len(opcode) == 3 and opcode[0] in (0x8d, 0x9d, 0x99, 0x8e, 0x8c):
                effective = int.from_bytes(opcode[1:], 'little')
                if opcode[0] == 0x9d:
                    effective = (effective + row['x']) & 65535
                elif opcode[0] == 0x99:
                    effective = (effective + row['y']) & 65535
                row['value'] = row['x'] if opcode[0] == 0x8e else row['y'] if opcode[0] == 0x8c else row['a']
            elif len(opcode) == 2 and opcode[0] in (0x85, 0x86, 0x84):
                effective = opcode[1]
                row['value'] = row['x'] if opcode[0] == 0x86 else row['y'] if opcode[0] == 0x84 else row['a']
            else:
                require('sidAddress' not in row, 'SID RMW/indirect store unsupported by checkpoint decoder')
                effective, row['value'] = row['address'], None
            require(effective == row['address'], 'Traced store address disagrees with opcode/registers')
        require(not records or row['monitorCycle'] >= records[-1]['monitorCycle'],
                'Checkpoint timestamps go backwards')
        records.append(row)
    return records


def monitor_commands(payload, host, refreshes):
    # Matching RSID cold/vicinit/ciainit in libsidplayfp 3.1.1 psiddrv.a65 uses
    # the inherited high raster bit and the NTSC CIA latch, not PAL's $4025.
    lines = ['radix h', 'sidefx off', 'dummy off', 'bank ram',
             f'load "{payload}" 0', f'load "{host}" 0', 'bank cpu',
             '> $0000 $2f $37', '> $d01a $00', '> $d019 $ff',
             '> $dc0d $7f', '> $dd0d $7f', 'sidefx on', 'm $dc0d $dc0d', 'm $dd0d $dd0d',
             'sidefx off', '> $d418 $0f', '> $dc04 $95 $42', '> $dc0e $01',
             '> $d011 $9b $37', '> $dc0d $81',
             'r a=$00,x=$00,y=$00,sp=$ff,fl=$20', 'r pc=$0400']
    snapshots = ['m $0000 $0001', 'm $02a6 $02a6', 'io $d000']
    lines += snapshots
    for kind, operation, first, last in CHECKPOINTS:
        lines.append(f'{kind} {operation} ${first:04x}' + (f' ${last:04x}' if last is not None else ''))
    lines += ['g', 'r', *snapshots, 'm $0314 $0319', 'bank ram', 'm $fffa $ffff',
              'bank cpu', 'delete 2', 'break exec $93f0',
              f'ignore {TERMINAL_CHECKPOINT} ${refreshes:04x}', 'g', 'r', *snapshots,
              'm $0314 $0319', 'bank ram', 'm $fffa $ffff', 'bank cpu', 'quit', '']
    return '\n'.join(lines)


def validate_monitor_contract(log, rows, completed_bodies):
    pattern = r'^(TRACE|BREAK): (\d+) +C:\$([0-9a-f]{4})(?:-\$([0-9a-f]{4}))? +\(([^)]+)\)( disabled)?$'
    registrations = {}
    for match in re.finditer(pattern, log, re.MULTILINE | re.IGNORECASE):
        kind, number, first, last, operation, disabled = match.groups()
        require(int(number) not in registrations and not disabled, 'Repeated/disabled coverage checkpoint')
        registrations[int(number)] = (kind, first, last, operation)
    expected = {index: (kind.upper(), f'{first:04x}', f'{last:04x}' if last is not None else None,
                        f'{"Trace" if kind == "trace" else "Stop on"} {operation}')
                for index, (kind, operation, first, last) in enumerate(
                    CHECKPOINTS + [('break', 'exec', MUSIC_ENTRY, None)], 1)}
    require(registrations == expected, 'Missing or altered monitor coverage checkpoint')
    ports = re.findall(r'^>C:0000 +([0-9a-f]{2}) +([0-9a-f]{2})(?: +|$)', log, re.MULTILINE | re.IGNORECASE)
    require(ports == [('2f', '37'), ('2f', '37'), ('2f', '36')],
            'Initial/idle/terminal CPU port snapshots disagree')
    ntsc = re.findall(r'^>C:02a6 +([0-9a-f]{2})(?: +|$)', log, re.MULTILINE | re.IGNORECASE)
    require(ntsc == ['00'] * 3, 'KERNAL PAL/NTSC byte does not prove NTSC at every boundary')
    raster_irqs = [int(value) for value in re.findall(r'^Raster cycle/line: \d+/\d+ IRQ: (\d+)\s*$', log, re.MULTILINE)]
    require(raster_irqs == [311, RASTER_LINE, RASTER_LINE], 'Actual inherited raster comparator differs from seed/source contract')
    port_rows = [row for row in rows if row['operation'] == 'store' and row['address'] in (0, 1)]
    require(all(row['address'] == 1 for row in port_rows), 'Runtime CPU port DDR mutation is outside this contract')
    kernal_ports = [row for row in port_rows if row['pc'] == 0xea79]
    require(all(row['value'] == 0x37 for row in kernal_ports), 'KERNAL CIA dispatch CPU port differs from $37')
    port_writes = [(row['pc'], row['value']) for row in port_rows if row['pc'] != 0xea79]
    expected_ports = [(0x9016, 0x35), (0x9093, 0x37)]
    expected_ports += [(0x90de, 0x36), (0x90f9, 0x37)] * completed_bodies
    expected_ports += [(0x90de, 0x36)]
    require(port_writes == expected_ports, 'Runtime CPU port/DDR writes differ from init/IRQ bank ownership')
    return dict(sidStoreRange=[0xd400, 0xd7ff], sidReadRange=[0xd400, 0xd7ff],
                ciaStoreAndReadRange=[0xdc00, 0xddff], vicStoreAndReadRange=[0xd011, 0xd01a],
                ramVectorStoreRange=[0xfffa, 0xffff], kernalVectorStoreRange=[0x0314, 0x0319],
                cpuPortSnapshots=ports, sourceCpuPortWrites=len(port_writes),
                kernalCiaDispatchPortWrites=len(kernal_ports), kernalVideoSnapshots=ntsc,
                rasterComparatorSnapshots=raster_irqs, dummyAccessesIncluded=False,
                coverage='All registered checkpoints enabled throughout init and retained bodies; no quiet/skipped window.')


def interval_summary(rows):
    values = [after['monitorCycle'] - before['monitorCycle'] for before, after in zip(rows, rows[1:])]
    return dict(count=len(values), minimum=min(values) if values else None,
                maximum=max(values) if values else None,
                histogram={str(value): count for value, count in sorted(Counter(values).items())})


def verify_opening_speech(rows, commands, music_init):
    """Check observed NMI/writer ownership per command, without decoding samples."""
    writer_for_entry = dict(zip((0xf083, 0xf0a4, 0xf0c3, 0xf0e1), SPEECH_WRITERS))
    results = []
    for command, stop in zip(commands, commands[1:] + [music_init]):
        window = [row for row in rows if command['monitorCycle'] < row['monitorCycle'] < stop['monitorCycle']]
        entries = [row for row in window if row['kind'] == 'trace'
                   and row['operation'] == 'exec' and row['pc'] in NMI_ENTRIES]
        volumes = [row for row in window if row['operation'] == 'store' and row.get('sidAddress') == 0xd418]
        entry_counts, writer_counts = Counter(row['pc'] for row in entries), Counter(row['pc'] for row in volumes)
        require(set(entry_counts) == set(NMI_ENTRIES), 'Opening speech NMI handler group is missing')
        require(set(writer_counts) == set(SPEECH_WRITERS), 'Opening speech volume writer group is missing or unknown')
        require(all(entry_counts[entry] == writer_counts[writer] for entry, writer in writer_for_entry.items()),
                'Opening speech NMI/volume counts disagree')
        pending_writer = None
        for row in window:
            if row['kind'] == 'trace' and row['operation'] == 'exec' and row['pc'] in NMI_ENTRIES:
                require(pending_writer is None, 'Opening speech NMI volume writer was omitted or reordered')
                pending_writer = writer_for_entry.get(row['pc'])
            elif row['operation'] == 'store' and row.get('sidAddress') == 0xd418:
                require(pending_writer == row['pc'], 'Opening speech volume writer lacks its executed NMI entry')
                pending_writer = None
        require(pending_writer is None, 'Opening speech ended with an unfinished NMI volume writer')
        timer_writes = [(row['address'], row['value']) for row in window
                        if row['operation'] == 'store' and row['address'] in (0xdd06, 0xdd07, 0xdd0d, 0xdd0f)]
        require(timer_writes == [(0xdd0f, 0x90), (0xdd0f, 0x91), (0xdd06, 0x65),
                                 (0xdd07, 0), (0xdd0d, 0x82), (0xdd0f, 0x90)],
                'Opening speech CIA2 Timer B setup/stop sequence differs')
        results.append(dict(command=command['a'], nmiEntryCount=len(entries), volumeStoreCount=len(volumes),
                            nmiEntryPcCounts={f'{pc:04x}': count for pc, count in sorted(entry_counts.items())},
                            volumeWriterCounts={f'{pc:04x}': count for pc, count in sorted(writer_counts.items())},
                            timerBLatch=0x65, timerBControl=0x91, interruptMask=0x82,
                            firstNmiCycle=entries[0]['monitorCycle'], lastNmiCycle=entries[-1]['monitorCycle'],
                            nmiCheckpointIntervals=interval_summary(entries)))
    return results


def summarize(rows, refreshes, header):
    stops = [row for row in rows if row['kind'] == 'stop on']
    require(len(stops) == 2 and stops[0]['checkpoint'] == 2 and stops[0]['pc'] == 0x0403,
            'Missing first idle stop or unexpected stop')
    idle, terminal = stops
    require(idle['sp'] == 0xff and idle['bytes'] == '4c0304', 'Init did not return to real idle stack')
    require(terminal['checkpoint'] == TERMINAL_CHECKPOINT and terminal['pc'] == MUSIC_ENTRY
            and terminal['bytes'] == 'a900', 'Missing unexecuted terminal music body stop')
    require(rows[-1] == terminal, 'Execution continued after terminal stop')
    exec_rows = [row for row in rows if row['kind'] == 'trace' and row['operation'] == 'exec']
    markers = {}
    for pc in (0x900d, 0x93e2, 0x9096):
        matches = [row for row in exec_rows if row['pc'] == pc]
        require(len(matches) == 1, 'Unexpected initialization entry/music-init/return count')
        markers[pc] = matches[0]
    require(not any(row['pc'] == 0x9056 for row in exec_rows), 'Non-default speech-only return path executed')
    require(markers[0x900d]['a'] == 0 and markers[0x900d]['sp'] == 0xfd
            and markers[0x9096]['sp'] == 0xfd, 'Default selection or real JSR stack disagrees')
    speech_commands = [row for row in exec_rows if row['pc'] == 0x9097]
    require([row['a'] for row in speech_commands] == [1, 3], 'Default opening speech command sequence differs')
    ordered = [markers[0x900d]['monitorCycle'], *[row['monitorCycle'] for row in speech_commands],
               markers[0x93e2]['monitorCycle'], markers[0x9096]['monitorCycle'], idle['monitorCycle']]
    require(ordered == sorted(set(ordered)), 'Init speech/music/return/idle ordering differs')
    opening_speech = verify_opening_speech(rows, speech_commands, markers[0x93e2])
    entries = [row for row in exec_rows if row['pc'] == MUSIC_ENTRY]
    returns = [row for row in exec_rows if row['pc'] == MUSIC_RETURN]
    require(entries and entries[-1]['monitorCycle'] == terminal['monitorCycle'],
            'Terminal music trace and stop disagree')
    init_entries = [row for row in entries if row['monitorCycle'] < idle['monitorCycle']]
    post_idle = [row for row in entries if row['monitorCycle'] > idle['monitorCycle']]
    require(len(post_idle) == refreshes + 1, 'Requested completed post-idle body count differs')
    require(len(returns) == len(entries) - 1, 'Music entry/return count differs')
    for index, returned in enumerate(returns):
        require(entries[index]['monitorCycle'] < returned['monitorCycle'] < entries[index + 1]['monitorCycle'],
                'Music body return is missing, reordered or attributed to another entry')
    phases = [((row['rasterLine'] - RASTER_LINE) * 65 + row['rasterCycle']) % NTSC_FRAME_CYCLES for row in entries]
    # $90B3–$90D1 swaps 32 bytes in 712 cycles; its JSR and the body JSR add
    # 12. A body cannot arrive before that work, and normally wraps to line 6.
    require(all(724 <= phase <= 1024 for phase in phases), 'Music body outside bounded wrapper latency from raster 257')
    intervals = [b['monitorCycle'] - a['monitorCycle'] for a, b in zip(entries, entries[1:])]
    normalized = [interval - (after - before) for interval, before, after in zip(intervals, phases, phases[1:])]
    require(normalized and all(value == NTSC_FRAME_CYCLES for value in normalized),
            'Raster-normalized music cadence differs from one 263-line NTSC frame')
    elapsed = terminal['monitorCycle'] - markers[0x900d]['monitorCycle']
    require(0 < elapsed <= 16 * NTSC_CLOCK, 'Capture exceeds 16-second initialized bound')
    retained = [row for row in rows if row['monitorCycle'] < terminal['monitorCycle']]
    body_index = -1
    for row in retained:
        if row['kind'] == 'trace' and row['operation'] == 'exec' and row['pc'] == MUSIC_ENTRY:
            body_index += 1
        row['bodyIndex'] = body_index if body_index >= 0 else None
        row['phase'] = 'init' if row['monitorCycle'] <= markers[0x9096]['monitorCycle'] else 'play'
    stores = [row for row in retained if row['operation'] == 'store' and 'sidAddress' in row]
    reads = [row for row in retained if row['operation'] == 'load' and 'sidAddress' in row]
    volumes = [row for row in stores if row['sidAddress'] == 0xd418]
    nmis = [row for row in retained if row['kind'] == 'trace' and row['operation'] == 'exec' and row['pc'] in NMI_ENTRIES]
    writers = {}
    for row in stores:
        writer = writers.setdefault(f'{row["pc"]:04x}', dict(instruction=row.get('assembly'), bytes=row['bytes'],
                                                           count=0, addresses=set(), phases=Counter()))
        writer['count'] += 1
        writer['addresses'].add(f'{row["address"]:04x}')
        writer['phases'][row['phase']] += 1
    for writer in writers.values():
        writer['addresses'], writer['phases'] = sorted(writer['addresses']), dict(writer['phases'])
    cia2_writes = [dict(pc=row['pc'], address=row['address'], value=row['value'], monitorCycle=row['monitorCycle'])
                   for row in retained if row['operation'] == 'store' and row['address'] in (0xdd06, 0xdd07, 0xdd0d, 0xdd0f)]
    nmi_vectors = [dict(pc=row['pc'], address=row['address'], value=row['value'])
                   for row in retained if row['operation'] == 'store' and row['address'] in (0xfffa, 0xfffb)]
    return retained, dict(header=header, initialization=dict(entry=markers[0x900d],
        beforeReturn=markers[0x9096], internalMusicInit=markers[0x93e2], idle=idle,
        speechCommands=[dict(command=row['a'], monitorCycle=row['monitorCycle']) for row in speech_commands],
        cyclesToIdle=idle['monitorCycle'] - markers[0x900d]['monitorCycle']),
        capture=dict(requestedPostIdleBodies=refreshes, completedInitBodies=len(init_entries),
                     completedPostIdleBodies=len(post_idle) - 1, completedBodies=len(returns),
                     terminalBodyExecuted=False, initializedCycles=elapsed, initializedSeconds=elapsed / NTSC_CLOCK,
                     bodyIntervals=intervals, rasterNormalizedIntervals=normalized,
                     frameCycles=NTSC_FRAME_CYCLES, scheduledRasterLine=RASTER_LINE,
                     observedRasterLines=sorted({row['rasterLine'] for row in entries}),
                     minimumBodyEntryLatency=min(phases), maximumBodyEntryLatency=max(phases),
                     minimumBodyCycles=min(b['monitorCycle'] - a['monitorCycle'] for a, b in zip(entries, returns)),
                     maximumBodyCycles=max(b['monitorCycle'] - a['monitorCycle'] for a, b in zip(entries, returns))),
        sid=dict(storeCount=len(stores), readCount=len(reads), phaseStoreCounts=dict(Counter(row['phase'] for row in stores)),
                 physicalAddressCounts={f'{address:04x}': count for address, count in sorted(Counter(row['address'] for row in stores).items())},
                 writers=writers),
        speech=dict(nmiEntryCount=len(nmis), nmiEntryPcCounts=dict(Counter(f'{row["pc"]:04x}' for row in nmis)),
                    verifiedOpeningCommands=opening_speech,
                    phaseNmiCounts=dict(Counter(row['phase'] for row in nmis)), nmiCheckpointIntervals=interval_summary(nmis),
                    volumeStoreCount=len(volumes), volumeWriterCounts=dict(Counter(f'{row["pc"]:04x}' for row in volumes)),
                    phaseVolumeCounts=dict(Counter(row['phase'] for row in volumes)),
                    firstVolumeCycle=volumes[0]['monitorCycle'] if volumes else None,
                    lastVolumeCycle=volumes[-1]['monitorCycle'] if volumes else None,
                    cia2TimerBWrites=cia2_writes,
                    nmiVectorWriteCount=len(nmi_vectors),
                    nmiVectorWriterCounts=dict(Counter(f'{row["pc"]:04x}' for row in nmi_vectors)),
                    nmiVectorValuesByAddress={f'{address:04x}': sorted({row['value'] for row in nmi_vectors if row['address'] == address})
                                              for address in (0xfffa, 0xfffb)}),
        listeningReview=None,
        limitations='Controlled NTSC VICE KERNAL-READY real-JSR host with matching selected init/VIC/CIA entry seeds, not original-game or complete renderer cold-state identity. Physical SID $D400–$D7FF reads/stores cover init and retained music calls; dummy accesses disabled. Exec checkpoints precede instructions, access checkpoints follow instructions; neither is an exact SID bus timestamp. Full amplitude streams and monitor logs remain private. No full score form, independent synthesis, speech decoder, physical hardware, PCM identity or musical acceptance claim.')


def probe(source, output, vice, refreshes):
    require(type(refreshes) is int and 2 <= refreshes <= 128, 'Choose 2–128 bounded music bodies')
    data = source.read_bytes()
    header = admit_source(data)
    output = managed_output(output, ROOT)
    require(not output.exists(), 'Choose a fresh output directory')
    for path in (source, output, vice):
        require(not any(character in str(path) for character in ('"', '\n', '\r')), 'Unsafe monitor path')
    output.mkdir(parents=True)
    payload, host = output / 'payload.prg', output / 'host.prg'
    payload.write_bytes(data[124:])
    host.write_bytes(host_program())
    monitor = output / 'commands.mon'
    monitor.write_text(monitor_commands(payload, host, refreshes))
    command = [str(vice), '-config', '/dev/null', '-directory', str(ROOT / '.tools/vice-headless-3.9/source/data'),
               '-ntsc', '+logcolorize', '-initbreak', 'ready', '-moncommands', str(monitor),
               '-monlog', '-monlogname', str(output / 'monitor.log'), '-limitcycles', '20000000',
               '-warp', '+sound', '-sidenginemodel', 'resid6581', '-cia1model', '1', '-cia2model', '1']
    env = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY'):
        env.pop(key, None)
    for key in ('XDG_CONFIG_HOME', 'XDG_STATE_HOME'):
        env[key] = str(output / key.lower())
        (Path(env[key]) / 'vice').mkdir(parents=True)
    write_json(output / 'command.json', command)
    with (output / 'process.log').open('w') as log:
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=60)
    # The monitor character column contains raw bytes; latin-1 preserves them.
    monitor_log = (output / 'monitor.log').read_text(encoding='latin-1')
    rows = parse_records(monitor_log)
    retained, result = summarize(rows, refreshes, header)
    result['monitorContract'] = validate_monitor_contract(monitor_log, rows, result['capture']['completedBodies'])
    result.update(schemaVersion=1, sourceSha256=sha(data),
        tools=dict(probeSha256=sha(Path(__file__).read_bytes()), viceSha256=sha(vice.read_bytes()),
                   traceGrammarSha256=sha((ROOT / 'scripts/trace-sid-vice.py').read_bytes()),
                   clockSha256=sha((ROOT / 'scripts/sid_clock.py').read_bytes()),
                   inspectorSha256=sha((ROOT / 'scripts/sid_intake.py').read_bytes())),
        host=dict(base=0x0400, idle=0x0403, init=0x900d, initA=0, initX=0, initY=0,
                  stackBeforeJsr=255, flags=0x20, initialCpuPort=0x37, speechCpuPort=0x35,
                  musicCpuPort=0x36, idleCpuPort=0x37, irqVector=0x90d2,
                  vicD011=0x9b, vicD012=0x37, cia1TimerA=0x4295, cia1ControlA=1,
                  clock='NTSC', sidModel='MOS6581', cia1Model=1, cia2Model=1,
                  setupBasis='libsidplayfp 3.1.1 psiddrv.a65 cold/vicinit/ciainit/setregs/idle and psiddrv.cpp selected-song/flags; actual KERNAL NTSC byte and VIC comparator are checked. KERNAL-READY RAM differs from renderer power-on initialization.'))
    with gzip.open(output / 'trace.json.gz', 'wt') as file:
        json.dump(retained, file, separators=(',', ':'))
    for name in ('monitor.log', 'process.log'):
        raw = (output / name).read_bytes()
        with gzip.open(output / f'{name}.gz', 'wb') as file:
            file.write(raw)
        require(gzip.decompress((output / f'{name}.gz').read_bytes()) == raw, f'Compressed {name} differs')
        (output / name).unlink()
    result['privateArtifacts'] = {name: dict(bytes=(output / name).stat().st_size, sha256=sha((output / name).read_bytes()))
                                  for name in ('payload.prg', 'host.prg', 'trace.json.gz', 'monitor.log.gz', 'process.log.gz')}
    write_json(output / 'verification.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/research/ghostbusters/Ghostbusters.sid')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--vice', type=Path, default=ROOT / '.tools/vice-headless-3.9/build/src/x64sc')
    parser.add_argument('--refreshes', type=int, default=128)
    args = parser.parse_args()
    result = probe(args.source.resolve(), args.output.resolve(), args.vice.resolve(), args.refreshes)
    print(json.dumps(dict(verification=str(args.output.resolve() / 'verification.json'),
                         completedBodies=result['capture']['completedBodies'],
                         initializedSeconds=result['capture']['initializedSeconds'],
                         sidStores=result['sid']['storeCount'], nmiEntries=result['speech']['nmiEntryCount'],
                         volumeStores=result['speech']['volumeStoreCount']), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Ghostbusters machine probe: {error}')
