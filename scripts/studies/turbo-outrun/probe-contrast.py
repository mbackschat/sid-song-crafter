"""Capture Turbo Outrun intro #1 in its returning IRQ/NMI machine host."""

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
from sid_intake import inspect_sid

SOURCE_SHA = '02e3840800c4f5f8b626864eeae92bd46a3742085c6a37b532acb363ad5cabfc'
FRAME_CYCLES = 19656
PAL_CYCLES_PER_SECOND = 985248
spec = importlib.util.spec_from_file_location('turbo_vice_grammar', ROOT / 'scripts/trace-sid-vice.py')
trace_helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace_helpers)
HEADER = re.compile(r'^#(\d+) \((Trace|Stop on)\s+(exec|store|load)\s+([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\s*$', re.IGNORECASE)
CHECKPOINTS = [
    ('trace', 'exec', 0xcb40, None), ('break', 'exec', 0x0403, None),
    ('trace', 'exec', 0xcd00, None), ('trace', 'exec', 0xcd2f, None),
    ('trace', 'exec', 0xcd30, None), ('trace', 'exec', 0x0943, None),
    ('trace', 'store', 0xd400, 0xd7ff), ('trace', 'load', 0xd400, 0xd7ff),
    ('trace', 'store', 0, 1), ('trace', 'store', 0xfffa, 0xffff),
    ('trace', 'store', 0xdc00, 0xddff), ('trace', 'store', 0xd011, 0xd01a),
    ('trace', 'exec', 0x0810, None), ('trace', 'exec', 0x0819, None),
    ('trace', 'exec', 0x0949, None), ('trace', 'exec', 0x094c, None),
    ('trace', 'exec', 0x0963, None), ('trace', 'exec', 0x0974, None),
    ('trace', 'exec', 0x0936, None), ('trace', 'exec', 0x0904, None),
    ('trace', 'exec', 0x0909, None),
]
TERMINAL_CHECKPOINT = len(CHECKPOINTS) + 1
TONAL_CHECKPOINTS = [
    ('trace', 'store', 0xe5, 0xf6), ('trace', 'store', 0x0834, 0x0836),
    ('trace', 'store', 0x082b, 0x082d), ('trace', 'exec', 0x0e08, None),
    ('trace', 'exec', 0x0e0d, None), ('trace', 'exec', 0x0e18, None),
    ('trace', 'exec', 0x0e36, None), ('trace', 'exec', 0x0e39, None),
    ('trace', 'exec', 0x0c6e, None), ('trace', 'exec', 0x0cf0, None),
]
QUIET_CHECKPOINTS = (6, 7, 8, 11, 12, 15, 16, 17, 18, 19, 20, 21)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def host_program():
    """Use psiddrv.a65's JSR/idle stack contract with archive intro selection A=0."""
    return bytes.fromhex('0004 2040cb 4c0304')


def parse_records(log):
    lines, records = log.splitlines(), []
    for index, line in enumerate(lines):
        header = HEADER.fullmatch(line)
        if header is None:
            require(not re.match(r'^#\d+ \((?:Trace|Stop on)', line), 'Unrecognized VICE trace header')
            continue
        require(index + 1 < len(lines), 'Missing trace instruction')
        instruction = trace_helpers.INSTRUCTION.fullmatch(lines[index + 1])
        require(instruction is not None, 'Unsupported VICE instruction record')
        checkpoint, kind, operation, address, raster, raster_cycle = header.groups()
        pc, encoded, assembly, a, x, y, sp, flags, cycle = instruction.groups()
        row = dict(checkpoint=int(checkpoint), kind=kind.lower(), operation=operation.lower(), address=int(address, 16), pc=int(pc, 16),
                   bytes=''.join(encoded.split()).lower(), assembly=assembly.strip(),
                   a=int(a, 16), x=int(x, 16), y=int(y, 16), sp=int(sp, 16), flags=flags,
                   rasterLine=int(raster), rasterCycle=int(raster_cycle), monitorCycle=int(cycle))
        require(0 <= row['rasterLine'] < 312 and 0 <= row['rasterCycle'] < 63, 'Checkpoint outside PAL raster geometry')
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
        require(not records or row['monitorCycle'] >= records[-1]['monitorCycle'], 'Checkpoint timestamps go backwards')
        records.append(row)
    return records


def monitor_commands(payload, host, refreshes, skip_refreshes=0):
    checkpoints = CHECKPOINTS + (TONAL_CHECKPOINTS if skip_refreshes else [])
    terminal_checkpoint = len(checkpoints) + 1
    lines = ['radix h', 'sidefx off', 'dummy off', 'bank ram',
             f'load "{payload}" 0', f'load "{host}" 0', 'bank cpu',
             '> $0000 $2f $37', '> $d01a $00', '> $d019 $ff',
             '> $dc0d $7f', '> $dd0d $7f', 'sidefx on', 'm $dc0d $dc0d', 'm $dd0d $dd0d',
             'sidefx off', '> $d418 $0f', '> $dc04 $25 $40', '> $dc0e $01',
             '> $d011 $9b $37', '> $dc0d $81',
             'r a=$00,x=$00,y=$00,sp=$ff,fl=$20', 'r pc=$0400', 'm $0000 $0001']
    for kind, operation, start, end in checkpoints:
        lines.append(f'{kind} {operation} ${start:04x}' + (f' ${end:04x}' if end is not None else ''))
    lines += ['g', 'r', 'm $0000 $0001', 'm $fffa $ffff', 'delete 2', 'break exec $cd30']
    if skip_refreshes:
        lines += [f'disable {number}' for number in QUIET_CHECKPOINTS]
        lines += [f'disable {number}' for number in range(len(CHECKPOINTS) + 1, len(checkpoints) + 1)]
        lines += ['break', f'ignore {terminal_checkpoint} ${skip_refreshes:04x}', 'g', 'r', 'm $0000 $0001', 'm $fffa $ffff']
        lines += [f'enable {number}' for number in (7, 8, 11, 12)]
        lines += [f'enable {number}' for number in range(len(CHECKPOINTS) + 1, len(checkpoints) + 1)]
        lines += ['break', f'ignore {terminal_checkpoint} ${refreshes - 1:04x}']
    else:
        lines += [f'ignore {terminal_checkpoint} ${refreshes:04x}']
    lines += ['g', 'r', 'm $0000 $0001', 'm $fffa $ffff', 'quit', '']
    return '\n'.join(lines)


def validate_monitor_contract(log, rows, skip_refreshes=0):
    pattern = r'^(TRACE|BREAK): (\d+) +C:\$([0-9a-f]{4})(?:-\$([0-9a-f]{4}))? +\(([^)]+)\)( disabled)?$'
    registrations = {}
    observations = []
    for match in re.finditer(pattern, log, re.MULTILINE | re.IGNORECASE):
        kind, number, first, last, operation, disabled = match.groups()
        observations.append((int(number), (kind, first, last, operation), bool(disabled)))
    checkpoints = CHECKPOINTS + (TONAL_CHECKPOINTS if skip_refreshes else [])
    expected = {number: (kind.upper(), f'{start:04x}', f'{end:04x}' if end is not None else None,
                         f'{"Trace" if kind == "trace" else "Stop on"} {operation}')
                for number, (kind, operation, start, end) in enumerate(checkpoints, 1)}
    expected[len(checkpoints) + 1] = ('BREAK', 'cd30', None, 'Stop on exec')
    for number, definition, disabled in observations[:len(expected)]:
        require(number not in registrations and not disabled, 'Repeated/disabled initial checkpoint registration')
        registrations[number] = definition
    require(registrations == expected, 'Missing or altered monitor coverage checkpoint')
    if skip_refreshes:
        table_numbers = [number for number in expected if number != 2]
        table_size = len(table_numbers)
        require(len(observations) == len(expected) + table_size * 2, 'Missing quiet/window coverage state table')
        quiet_disabled = set(QUIET_CHECKPOINTS) | set(range(len(CHECKPOINTS) + 1, len(checkpoints) + 1))
        window_disabled = set(QUIET_CHECKPOINTS) - {7, 8, 11, 12}
        for offset, disabled_numbers in ((0, quiet_disabled), (table_size, window_disabled)):
            table = observations[len(expected) + offset:len(expected) + offset + table_size]
            require([number for number, _, _ in table] == table_numbers, 'Coverage table checkpoint order differs')
            require(all(definition == expected[number] and disabled == (number in disabled_numbers)
                        for number, definition, disabled in table), 'Quiet/window checkpoint coverage state differs')
    else:
        require(len(observations) == len(expected), 'Repeated checkpoint registration')
    ports = re.findall(r'^>C:0000 +([0-9a-f]{2}) +([0-9a-f]{2})(?: +|$)', log, re.MULTILINE | re.IGNORECASE)
    require(ports == [('2f', '37')] + [('2f', '35')] * (3 if skip_refreshes else 2), 'CPU port snapshots differ from initial $37 / running $35 bank')
    port_writes = [(row['pc'], row['address'], row['value']) for row in rows
                   if row['operation'] == 'store' and row['address'] in (0, 1)]
    require(port_writes == [(0xcb47, 1, 0x35), (0xcd03, 1, 0x35)], 'Unexpected runtime CPU port/DDR mutation')
    vectors = [(row['address'], row['value']) for row in rows if row['operation'] == 'store' and 0xfffa <= row['address'] <= 0xffff]
    require(vectors == [(0xffff, 0xcd), (0xfffe, 0x30), (0xfffa, 0x43), (0xfffb, 0x09)], 'IRQ/NMI RAM vector contract differs')
    return dict(sidStoreRange=[0xd400, 0xd7ff], sidReadRange=[0xd400, 0xd7ff],
                cpuPortSnapshots=ports, cpuPortWrites=port_writes, ramVectorWrites=vectors, dummyAccessesIncluded=False,
                sidCoverage='Initialization and retained window; disabled during explicitly bounded skipped IRQs.' if skip_refreshes else 'Entire initialized capture.',
                quietAndWindowCheckpointStatesVerified=bool(skip_refreshes))


def summarize(rows, refreshes, header, skip_refreshes=0):
    stops = [row for row in rows if row['kind'] == 'stop on']
    require(len(stops) == (3 if skip_refreshes else 2) and stops[0]['checkpoint'] == 2 and stops[0]['pc'] == 0x403, 'Missing first idle stop or unexpected stop')
    idle, terminal = stops[0], stops[-1]
    require(idle['sp'] == 0xff and idle['bytes'] == '4c0304', 'Init did not return to real idle stack')
    terminal_checkpoint = TERMINAL_CHECKPOINT + (len(TONAL_CHECKPOINTS) if skip_refreshes else 0)
    require(terminal['checkpoint'] == terminal_checkpoint and terminal['pc'] == 0xcd30 and terminal['bytes'] == '48', 'Missing terminal IRQ stop')
    require(rows[-1] == terminal, 'Execution continued after terminal stop')
    entries = [row for row in rows if row['kind'] == 'trace' and row['operation'] == 'exec' and row['pc'] == 0xcd30]
    require(entries and entries[-1]['monitorCycle'] == terminal['monitorCycle'], 'Terminal IRQ trace and stop disagree')
    init_entries = [row for row in entries if row['monitorCycle'] < idle['monitorCycle']]
    post_idle = [row for row in entries if row['monitorCycle'] > idle['monitorCycle']]
    require(len(post_idle) == skip_refreshes + refreshes + 1, 'Post-idle refresh count differs from requested capture')
    window_start = post_idle[skip_refreshes]
    if skip_refreshes:
        require(stops[1]['checkpoint'] == terminal_checkpoint and stops[1]['pc'] == 0xcd30
                and stops[1]['monitorCycle'] == window_start['monitorCycle'], 'Skipped-IRQ window boundary disagrees')
        require(not any('sidAddress' in row and idle['monitorCycle'] < row['monitorCycle'] < window_start['monitorCycle']
                        for row in rows), 'SID records leak into declared quiet advance')
    phases = [(row['rasterLine'] - 52) * 63 + row['rasterCycle'] for row in entries]
    require(all(0 <= phase <= 128 for phase in phases), 'Intro IRQ outside bounded latency from raster 52')
    markers = {}
    for pc in (0xcb40, 0xcd00, 0x810, 0x819, 0xcd2f):
        found = [row for row in rows if row['operation'] == 'exec' and row['pc'] == pc]
        require(len(found) == 1, 'Unexpected initialization entry/return path')
        markers[pc] = found[0]
    require(markers[0xcb40]['a'] == 0 and markers[0xcb40]['sp'] == 0xfd, 'Archive intro selection or real JSR stack disagrees')
    require(markers[0xcd2f]['sp'] == 0xfd, 'Init return stack changed')
    ordered = [markers[pc]['monitorCycle'] for pc in (0xcb40, 0xcd00, 0x810, 0x819, 0xcd2f)] + [idle['monitorCycle'], terminal['monitorCycle']]
    require(ordered == sorted(set(ordered)), 'Initialization/idle/terminal ordering disagrees')
    elapsed = terminal['monitorCycle'] - markers[0xcb40]['monitorCycle']
    require(0 < elapsed <= 34 * PAL_CYCLES_PER_SECOND, 'Capture exceeds 34-second initialized bound')
    intervals = [b['monitorCycle'] - a['monitorCycle'] for a, b in zip(entries, entries[1:])]
    scheduled_intervals = [interval - (after - before) for interval, before, after in zip(intervals, phases, phases[1:])]
    require(scheduled_intervals and all(value == FRAME_CYCLES for value in scheduled_intervals), 'Raster-normalized IRQ cadence differs from one PAL frame')
    irq_index = -1
    for row in rows:
        if row['kind'] == 'trace' and row['operation'] == 'exec' and row['pc'] == 0xcd30:
            irq_index += 1
        row['irqIndex'] = irq_index if irq_index >= 0 else None
        row['phase'] = 'init' if row['monitorCycle'] <= markers[0xcd2f]['monitorCycle'] else 'play'
    retained = [row for row in rows if row['monitorCycle'] < terminal['monitorCycle']
                and (not skip_refreshes or row['phase'] == 'init' or row['monitorCycle'] >= window_start['monitorCycle'])]
    stores = [row for row in retained if row['operation'] == 'store' and 'sidAddress' in row]
    reads = [row for row in retained if row['operation'] == 'load' and 'sidAddress' in row]
    volumes = [row for row in stores if row['sidAddress'] == 0xd418]
    volume_intervals = [b['monitorCycle'] - a['monitorCycle'] for a, b in zip(volumes, volumes[1:])]
    writers = {}
    for row in stores:
        writer = writers.setdefault(f'{row["pc"]:04x}', dict(instruction=row['assembly'], bytes=row['bytes'], count=0, addresses=set()))
        writer['count'] += 1
        writer['addresses'].add(f'{row["address"]:04x}')
    for writer in writers.values():
        writer['addresses'] = sorted(writer['addresses'])
    return retained, dict(header=header, initialization={f'{pc:04x}': row for pc, row in markers.items()},
        capture=dict(requestedPostIdleRefreshes=refreshes, completedInitIrqRefreshes=len(init_entries), completedPostIdleRefreshes=len(post_idle) - 1,
                     completedIrqRefreshes=len(entries) - 1, terminalIrqExecuted=False, initializedCycles=elapsed,
                     completedSkippedRefreshes=skip_refreshes, firstRetainedIrqIndex=skip_refreshes,
                     retainedIrqCount=refreshes, windowStart=window_start, windowStop=terminal,
                     initializedSeconds=elapsed / PAL_CYCLES_PER_SECOND, irqIntervals=intervals,
                     rasterNormalizedIntervals=scheduled_intervals,
                     scheduledRasterLine=52, observedRasterLines=sorted({row['rasterLine'] for row in entries}),
                     minimumEntryLatencyFromRasterStart=min(phases), maximumEntryLatencyFromRasterStart=max(phases)),
        sid=dict(storeCount=len(stores), readCount=len(reads), physicalAddressCounts=dict(Counter(f'{row["address"]:04x}' for row in stores)), writers=writers),
        volume=dict(storeCount=len(volumes), writerCounts=dict(Counter(f'{row["pc"]:04x}' for row in volumes)),
                    minimumCheckpointInterval=min(volume_intervals) if volume_intervals else None,
                    maximumCheckpointInterval=max(volume_intervals) if volume_intervals else None),
        limitations='Controlled VICE KERNAL-READY host with renderer-compatible selected init/VIC/CIA setup; not original-game host or renderer/PCM identity. Exec checkpoints precede instructions and store checkpoints follow instructions, neither is an exact SID bus timestamp. Raw volume/sample records remain private because they can reconstruct reference audio.')


def verify_sample_path(rows, payload):
    """Connect private packed-byte reads to nibble mapping, retaining public aggregates."""
    current_byte, current_address, shifted, counts = None, None, None, Counter()
    state, selector, selector_flag = 'fetch', None, None
    next_address, active = None, False
    nmi_active = False
    launches = []
    fetches, nmis, writes = [], [], []
    for row in rows:
        if row['operation'] == 'exec' and row['pc'] == 0x904:
            code = bytes.fromhex(row['bytes'])
            require(len(code) == 2 and code[0] == 0xa0, 'Sample selector is not immediate LDY')
            selector = code[1]
            require(0 <= selector < 23, 'Sample selector outside the 23-entry metadata tables')
        elif row['operation'] == 'exec' and row['pc'] == 0x909:
            require(selector == row['y'] and row['a'] == payload[0x9bb + selector - 0x810], 'Sample selector flag differs from pinned table')
            selector_flag = row['a']
        elif row['operation'] == 'exec' and row['pc'] == 0x936:
            require(not nmi_active, 'Sample restart occurs within unfinished NMI')
            require(selector is not None and selector_flag is not None and row['bytes'] == 'a900', 'Sample restart lacks executed selector')
            require(state in ('fetch', 'lowDepth'), 'Sample restart interrupts an incomplete NMI path')
            if state == 'lowDepth':
                counts['restartCancelledLowNibbles'] += 1
            state, current_byte = 'fetch', None
            next_address = payload[0x98d + selector - 0x810] + (((payload[0x9a4 + selector - 0x810] - 10) & 255) << 8)
            active = True
            launches.append(dict(selector=selector, flag=selector_flag, irqIndex=row['irqIndex'], monitorCycle=row['monitorCycle']))
        elif row['operation'] == 'exec' and row['pc'] == 0x943:
            require(not nmi_active, 'New NMI enters before previous sample NMI path completed')
            nmi_active = True
            nmis.append(row['monitorCycle'])
        elif row['operation'] == 'exec' and row['pc'] == 0x949:
            require(nmi_active, 'Sample fetch lacks executed NMI entry')
            require(state == 'fetch', 'Sample fetch occurs before prior nibble path completed/restarted')
            code = bytes.fromhex(row['bytes'])
            require(len(code) == 3 and code[0] == 0xad, 'Sample fetch is not absolute LDA')
            current_address = int.from_bytes(code[1:], 'little')
            require(active and current_address == next_address, 'Sample fetch differs from selected pointer/sequential packed stream')
            require(0x810 <= current_address < 0x810 + len(payload), 'Sample fetch outside pinned payload')
            current_byte = payload[current_address - 0x810]
            fetches.append(current_address)
            state = 'compare'
        elif row['operation'] == 'exec' and row['pc'] == 0x94c:
            require(nmi_active, 'Sample compare lacks executed NMI entry')
            require(row['bytes'] == 'c91f', 'Sample comparison is not the $1F terminator test')
            require(state == 'compare' and current_byte == row['a'], 'Executed sample compare/order differs from pinned payload')
            counts['verifiedPayloadFetches'] += 1
            state = 'terminate' if current_byte == 0x1f else 'highDepth'
        elif row['operation'] == 'exec' and row['pc'] in (0x963, 0x974):
            require(nmi_active, 'Sample depth mapping lacks executed NMI entry')
            require(state == ('highDepth' if row['pc'] == 0x963 else 'lowDepth'), 'Missing/misordered sample nibble depth phase')
            require(row['bytes'] in ('ea', '4a'), 'Sample depth opcode differs from NOP/LSR')
            shifted = row['bytes'] == '4a'
            require(shifted == bool(selector_flag), 'Executed depth opcode disagrees with selected metadata')
            expected = current_byte >> 4 if row['pc'] == 0x963 else current_byte & 15
            require(row['a'] == expected, 'Packed nibble does not reach executed depth mapping')
            counts['halfDepthNibbles' if shifted else 'fullDepthNibbles'] += 1
            state = 'highWrite' if row['pc'] == 0x963 else 'lowWrite'
        elif row['operation'] == 'store' and row['pc'] in (0x967, 0x978):
            require(nmi_active, 'Sample nibble write lacks executed NMI entry')
            require(row.get('address') == 0xd418 and row['bytes'] == '8d18d4', 'Sample nibble endpoint differs from physical $D418')
            require(state == ('highWrite' if row['pc'] == 0x967 else 'lowWrite'), 'Missing/misordered sample nibble write phase')
            nibble = current_byte >> 4 if row['pc'] == 0x967 else current_byte & 15
            expected = (nibble >> 1) + 0x34 if shifted else nibble + 0x30
            require(row['value'] == expected, 'Sample SID value disagrees with packed-nibble mapping')
            counts['highNibbleWrites' if row['pc'] == 0x967 else 'lowNibbleWrites'] += 1
            writes.append(row['monitorCycle'])
            state = 'lowDepth' if row['pc'] == 0x967 else 'fetch'
            nmi_active = False
            if row['pc'] == 0x978:
                next_address += 1
        elif row['operation'] == 'store' and row['pc'] == 0x957:
            require(nmi_active, 'Sample center write lacks executed NMI entry')
            require(row.get('address') == 0xd418 and row['bytes'] == '8d18d4', 'Sample center endpoint differs from physical $D418')
            require(state == 'terminate' and current_byte == 0x1f and row['value'] == 0x38, 'Sample terminator/order or restored center disagrees')
            counts['terminationCenterWrites'] += 1
            state = 'fetch'
            active = False
            nmi_active = False
    require(not nmi_active, 'Capture ends within unfinished sample NMI')
    require(state in ('fetch', 'lowDepth'), 'Capture ends within an incomplete NMI path')
    counts['terminalPendingLowNibbles'] = int(state == 'lowDepth')
    require(counts['verifiedPayloadFetches'] > 0 and counts['highNibbleWrites'] > 0 and counts['lowNibbleWrites'] > 0, 'Capture did not execute packed sample path')
    intervals = [b - a for a, b in zip(nmis, nmis[1:])]
    return dict(verified=True, counts=dict(counts), nmiCount=len(nmis), sampleFetchAddressRange=[min(fetches), max(fetches)],
                nmiMinimumCheckpointInterval=min(intervals), nmiMaximumCheckpointInterval=max(intervals),
                launches=launches, selectorLaunchCounts=dict(Counter(str(row['selector']) for row in launches)),
                packedDataPublished=False, orderedAmplitudeStreamPublished=False,
                interpretation='CIA2 Timer-A NMI reads a packed source byte, emits its high then low nibble through $D418 with optional half-depth mapping, and stops at $1F restoring $38. Historical sampled-drum/voice origin requires published credits, not volume writes alone.')


def probe(source, output, vice, refreshes, *, skip_refreshes=0, expected_sha=SOURCE_SHA):
    require(type(refreshes) is int and 2 <= refreshes <= 550, 'Choose 2–550 bounded raster refreshes')
    data = source.read_bytes()
    require(type(skip_refreshes) is int and 0 <= skip_refreshes <= 1400
            and skip_refreshes + refreshes <= 1650, 'Choose a bounded skip/capture ending within 1650 IRQs')
    require(sha(data) == expected_sha, 'Turbo Outrun source fingerprint mismatch')
    header = inspect_sid(data, subtune=1)
    require(header['format'] == 'RSID' and header['flags'] == 0x14 and header['loadAddress'] == 0x810
            and header['initAddress'] == 0xcb40 and header['playAddress'] == 0 and header['subtunes'] == 12
            and header['endAddressExclusive'] == 0xe400, 'Unexpected Turbo Outrun machine contract')
    output = managed_output(output, ROOT)
    require(not output.exists(), 'Choose a fresh output directory')
    for path in (source, output, vice):
        require(not any(c in str(path) for c in ('"', '\n', '\r')), 'Unsafe monitor path')
    output.mkdir(parents=True)
    payload, host = output / 'payload.prg', output / 'host.prg'
    payload.write_bytes(data[124:])
    host.write_bytes(host_program())
    monitor = output / 'commands.mon'
    monitor.write_text(monitor_commands(payload, host, refreshes, skip_refreshes))
    command = [str(vice), '-config', '/dev/null', '-directory', str(ROOT / '.tools/vice-headless-3.9/source/data'),
               '-pal', '+logcolorize', '-initbreak', 'ready', '-moncommands', str(monitor),
               '-monlog', '-monlogname', str(output / 'monitor.log'), '-limitcycles', '36000000',
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
    raw = (output / 'monitor.log').read_bytes()
    rows = parse_records(raw.decode('latin-1'))
    contract = validate_monitor_contract(raw.decode('latin-1'), rows, skip_refreshes)
    retained, result = summarize(rows, refreshes, header, skip_refreshes)
    result.update(schemaVersion=1, sourceSha256=sha(data), monitorContract=contract,
        samplePath=verify_sample_path(retained, data[126:]) if not skip_refreshes else
            dict(verified=False, reason='Targeted tonal window omits packed-fetch/depth hooks; opening capture owns sample arithmetic proof.'),
        tools=dict(probeSha256=sha(Path(__file__).read_bytes()), viceSha256=sha(vice.read_bytes()), traceGrammarSha256=sha((ROOT / 'scripts/trace-sid-vice.py').read_bytes())),
        host=dict(base=0x400, idle=0x403, init=0xcb40, initA=0, stackBeforeJsr=255, flags=0x20,
                  initialCpuPort=0x37, runningCpuPort=0x35, irqVector=0xcd30, nmiVector=0x943, rasterLine=52,
                  setupBasis='libsidplayfp 3.1.1 psiddrv.a65 cold/vicinit/ciainit/setregs/idle; archive intro init supplies RAM vectors and CIA2 sample setup.'))
    with gzip.open(output / 'trace.json.gz', 'wt') as file:
        json.dump(retained, file, separators=(',', ':'))
    for name in ('monitor.log', 'process.log'):
        raw_log = (output / name).read_bytes()
        with gzip.open(output / f'{name}.gz', 'wb') as file:
            file.write(raw_log)
        require(gzip.decompress((output / f'{name}.gz').read_bytes()) == raw_log, f'Compressed {name} differs')
        (output / name).unlink()
    result['privateArtifacts'] = {name: dict(bytes=(output / name).stat().st_size, sha256=sha((output / name).read_bytes()))
                                  for name in ('trace.json.gz', 'monitor.log.gz', 'process.log.gz')}
    write_json(output / 'verification.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/research/turbo-outrun/Turbo_Outrun.sid')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--vice', type=Path, default=ROOT / '.tools/vice-headless-3.9/build/src/x64sc')
    parser.add_argument('--refreshes', type=int, default=128)
    parser.add_argument('--skip-refreshes', type=int, default=0)
    args = parser.parse_args()
    result = probe(args.source.resolve(), args.output.resolve(), args.vice.resolve(), args.refreshes, skip_refreshes=args.skip_refreshes)
    capture = {key: result['capture'][key] for key in ('completedIrqRefreshes', 'completedSkippedRefreshes', 'retainedIrqCount', 'initializedSeconds', 'terminalIrqExecuted')}
    print(json.dumps(dict(verification=str(args.output.resolve() / 'verification.json'), capture=capture,
                          sidStoreCount=result['sid']['storeCount'], samplePath=result['samplePath']), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Turbo Outrun contrast probe: {error}')
