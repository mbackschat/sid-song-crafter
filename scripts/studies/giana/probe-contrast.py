"""Capture Giana in-game subtune 3 through its returning init and raster IRQ."""

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

SOURCE_SHA = '014764e6ee11df4b458c6b30e235ea639d702bd56766a87b5e90d4737558b1c8'
FRAME_CYCLES = 19656
PAL_CYCLES_PER_SECOND = 985248
spec = importlib.util.spec_from_file_location('giana_vice_grammar', ROOT / 'scripts/trace-sid-vice.py')
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


def host_program():
    """Supply the real JSR/idle boundary used by psiddrv.a65 setregs/idle."""
    return bytes.fromhex('0004 2086cc 4c0304')


def parse_records(log):
    """Decode monitor checkpoints; reject incomplete or ambiguous SID writes."""
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
        require(0 <= row['rasterLine'] < 312 and 0 <= row['rasterCycle'] < 63,
                'Checkpoint is outside PAL raster geometry')
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
                require(effective == row['address'], 'Traced store address disagrees with opcode/registers')
                row['value'] = row['x'] if opcode[0] == 0x8e else row['y'] if opcode[0] == 0x8c else row['a']
            else:
                require('sidAddress' not in row, 'SID RMW/indirect store is unsupported by this checkpoint decoder')
                row['value'] = None
        require(not records or row['monitorCycle'] >= records[-1]['monitorCycle'],
                'Checkpoint timestamps must not go backwards')
        records.append(row)
    return records


def monitor_commands(payload, host, refreshes):
    lines = ['radix h', 'sidefx off', 'dummy off', 'bank ram',
             f'load "{payload}" 0', f'load "{host}" 0', 'bank cpu',
             '> $0000 $2f $37', '> $d01a $00', '> $d019 $ff',
             '> $dc0d $7f', '> $dd0d $7f', 'sidefx on', 'm $dc0d $dc0d', 'm $dd0d $dd0d',
             'sidefx off', '> $d418 $0f', '> $dc04 $25 $40', '> $dc0e $01',
             '> $d011 $9b $37', '> $dc0d $81',
             'r a=$02,x=$00,y=$00,sp=$ff,fl=$20', 'r pc=$0400', 'm $0000 $0001',
             'trace exec $cc86', 'break exec $0403', 'trace exec $ccf0',
             'trace exec $ccf1', 'trace exec $ccd9', 'trace exec $ccb5',
             'trace store $d400 $d7ff', 'trace load $d400 $d7ff',
             'trace store $d011 $d01a', 'trace store $dc00 $ddff',
             'trace store $0314 $0319', 'trace store $0000 $0001',
             'g', 'r', 'm $0000 $0001', 'm $0314 $0319',
             'delete 2', 'break exec $ccf1', f'ignore 13 ${refreshes:04x}',
             'trace load $41ec', 'trace store $4263 $4268', 'trace store $4219 $421b',
             'trace store $41f2 $41f4', 'trace store $423b $4242', 'trace store $424a',
             'g', 'r', 'm $0000 $0001', 'quit', '']
    return '\n'.join(lines)


def validate_monitor_contract(log, rows):
    required = {
        1: ('TRACE', 'cc86', None, 'Trace exec'),
        2: ('BREAK', '0403', None, 'Stop on exec'),
        3: ('TRACE', 'ccf0', None, 'Trace exec'),
        4: ('TRACE', 'ccf1', None, 'Trace exec'),
        5: ('TRACE', 'ccd9', None, 'Trace exec'),
        6: ('TRACE', 'ccb5', None, 'Trace exec'),
        7: ('TRACE', 'd400', 'd7ff', 'Trace store'),
        8: ('TRACE', 'd400', 'd7ff', 'Trace load'),
        12: ('TRACE', '0000', '0001', 'Trace store'),
        13: ('BREAK', 'ccf1', None, 'Stop on exec'),
    }
    registrations = {}
    pattern = r'^(TRACE|BREAK): (\d+) +C:\$([0-9a-f]{4})(?:-\$([0-9a-f]{4}))? +\(([^)]+)\)$'
    for match in re.finditer(pattern, log, re.MULTILINE | re.IGNORECASE):
        kind, number, first, last, operation = match.groups()
        require(int(number) not in registrations, 'Repeated checkpoint registration')
        registrations[int(number)] = (kind, first, last, operation)
    for number, expected in required.items():
        require(registrations.get(number) == expected,
                f'Missing or altered monitor coverage checkpoint {number}')
    ports = re.findall(r'^>C:0000 +([0-9a-f]{2}) +([0-9a-f]{2})(?: +|$)', log, re.MULTILINE | re.IGNORECASE)
    require(len(ports) == 3 and all(pair == ('2f', '37') for pair in ports),
            'Initial/idle/terminal CPU port evidence differs from $2F/$37')
    require(not any(row['operation'] == 'store' and row['address'] in (0, 1) for row in rows),
            'Runtime CPU port/DDR mutation is outside this source-specific contract')
    return dict(sidStoreRange=[0xd400, 0xd7ff], sidReadRange=[0xd400, 0xd7ff],
                cpuPortSnapshots=ports, cpuPortWrites=0, dummyAccessesIncluded=False)


def summarize(rows, refreshes, header):
    stops = [row for row in rows if row['kind'] == 'stop on']
    require(len(stops) == 2 and stops[0]['checkpoint'] == 2 and stops[0]['pc'] == 0x0403,
            'Missing first idle stop or unexpected stop')
    idle, terminal = stops
    require(idle['sp'] == 0xff and idle['bytes'] == '4c0304', 'Init did not return to the real idle stack')
    require(terminal['checkpoint'] == 13 and terminal['pc'] == 0xccf1
            and terminal['bytes'] == '20c041', 'Missing terminal IRQ stop')
    require(rows[-1] == terminal, 'Execution continued after terminal stop')
    entries = [row for row in rows if row['kind'] == 'trace'
               and row['operation'] == 'exec' and row['pc'] == 0xccf1]
    require(entries and entries[-1]['monitorCycle'] == terminal['monitorCycle'],
            'Terminal IRQ trace and stop disagree')
    init_entries = [row for row in entries if row['monitorCycle'] < idle['monitorCycle']]
    post_idle = [row for row in entries if row['monitorCycle'] > idle['monitorCycle']]
    require(len(post_idle) == refreshes + 1, 'Post-idle refresh count differs from requested capture')
    require(all(row['rasterLine'] == 256 for row in entries[1:]), 'Post-startup raster must be 256')
    init = [row for row in rows if row['operation'] == 'exec' and row['pc'] == 0xcc86]
    returns = [row for row in rows if row['operation'] == 'exec' and row['pc'] == 0xccf0]
    internal = [row for row in rows if row['operation'] == 'exec' and row['pc'] == 0xccd9]
    require(len(init) == len(returns) == len(internal) == 1, 'Unexpected initialization entry/return path')
    require(init[0]['monitorCycle'] < returns[0]['monitorCycle'] < idle['monitorCycle']
            < terminal['monitorCycle'], 'Initialization/idle/terminal order disagrees')
    require(init[0]['a'] == 2 and init[0]['sp'] == 0xfd and internal[0]['a'] == 1,
            'Archive #3 selection or real JSR stack contract disagrees')
    elapsed = entries[-1]['monitorCycle'] - init[0]['monitorCycle']
    require(0 < elapsed <= 12 * PAL_CYCLES_PER_SECOND, 'Capture exceeds the 12-second initialized bound')
    intervals = [b['monitorCycle'] - a['monitorCycle'] for a, b in zip(entries, entries[1:])]
    require(intervals and max(abs(value - FRAME_CYCLES) for value in intervals[1:]) <= 12,
            'Post-startup IRQ cadence disagrees with one PAL frame')
    irq_index = -1
    for row in rows:
        if row['kind'] == 'trace' and row['operation'] == 'exec' and row['pc'] == 0xccf1:
            irq_index += 1
        row['irqIndex'] = irq_index if irq_index >= 0 else None
        row['phase'] = 'init' if row['monitorCycle'] <= returns[0]['monitorCycle'] else 'play'
    retained = [row for row in rows if row['monitorCycle'] < entries[-1]['monitorCycle']]
    stores = [row for row in retained if row['operation'] == 'store' and 'sidAddress' in row]
    reads = [row for row in retained if row['operation'] == 'load' and 'sidAddress' in row]
    volumes = [row for row in stores if row['sidAddress'] == 0xd418]
    volume_intervals = [b['monitorCycle'] - a['monitorCycle'] for a, b in zip(volumes, volumes[1:])]
    writers = {}
    for row in stores:
        writer = writers.setdefault(f'{row["pc"]:04x}', dict(instruction=row['assembly'], bytes=row['bytes'],
                                                           count=0, addresses=set(), values=set()))
        writer['count'] += 1
        writer['addresses'].add(f'{row["address"]:04x}')
        writer['values'].add(row['value'])
    for writer in writers.values():
        writer['addresses'], writer['values'] = sorted(writer['addresses']), sorted(writer['values'])
    copy = [row for row in retained if row['operation'] == 'exec' and row['pc'] == 0xccb5]
    return retained, dict(header=header, initialization=dict(entry=init[0], beforeReturn=returns[0],
        internalMusicInit=internal[0], relocationWriterCount=len(copy)),
        capture=dict(requestedPostIdleRefreshes=refreshes, completedInitIrqRefreshes=len(init_entries),
                     completedPostIdleRefreshes=len(post_idle) - 1,
                     completedIrqRefreshes=len(entries) - 1, terminalIrqExecuted=False,
                     initializedCycles=elapsed, initializedSeconds=elapsed / PAL_CYCLES_PER_SECOND,
                     irqIntervals=intervals, maximumPostStartupCadenceError=max(abs(v - FRAME_CYCLES) for v in intervals[1:])),
        sid=dict(storeCount=len(stores), readCount=len(reads),
                 physicalAddressCounts={f'{address:04x}': count for address, count in Counter(row['address'] for row in stores).items()},
                 writers=writers),
        volume=dict(storeCount=len(volumes), writerCounts=dict(Counter(f'{row["pc"]:04x}' for row in volumes)),
                    values=sorted({row['value'] for row in volumes}),
                    minimumCheckpointInterval=min(volume_intervals) if volume_intervals else None,
                    maximumCheckpointInterval=max(volume_intervals) if volume_intervals else None),
        listeningReview=None,
        limitations='Controlled VICE KERNAL-READY host with renderer-compatible selected init/VIC/CIA setup, not original-game host or renderer-state/PCM identity. SID stores/reads cover physical $D400–$D7FF with dummy accesses disabled; store checkpoints follow instructions, exec checkpoints precede them, and neither is an exact SID bus-cycle timestamp. No original audio quality or musical acceptance follows.')


def probe(source, output, vice, refreshes, *, expected_sha=SOURCE_SHA):
    require(type(refreshes) is int and 2 <= refreshes <= 550, 'Choose 2–550 bounded raster refreshes')
    data = source.read_bytes()
    require(sha(data) == expected_sha, 'Giana source fingerprint mismatch')
    header = inspect_sid(data, subtune=3)
    require(header['format'] == 'RSID' and header['flags'] == 0x14
            and header['loadAddress'] == 0x71e3 and header['initAddress'] == 0xcc86
            and header['playAddress'] == 0 and header['subtunes'] == 23, 'Unexpected Giana machine contract')
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
               '-pal', '+logcolorize', '-initbreak', 'ready', '-moncommands', str(monitor),
               '-monlog', '-monlogname', str(output / 'monitor.log'), '-limitcycles', '17000000',
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
    # VICE's memory-dump character column contains raw bytes; preserve them without UTF-8 replacement.
    monitor_log = (output / 'monitor.log').read_text(encoding='latin-1')
    rows = parse_records(monitor_log)
    contract = validate_monitor_contract(monitor_log, rows)
    retained, result = summarize(rows, refreshes, header)
    result['monitorContract'] = contract
    result.update(schemaVersion=1, sourceSha256=sha(data),
        tools=dict(probeSha256=sha(Path(__file__).read_bytes()), viceSha256=sha(vice.read_bytes()),
                   traceGrammarSha256=sha((ROOT / 'scripts/trace-sid-vice.py').read_bytes())),
        host=dict(base=0x0400, idle=0x0403, init=0xcc86, initA=2, initX=0, initY=0,
                  stackBeforeJsr=255, flags=0x20, cpuPort=0x37, vicD011=0x9b, vicD012=0x37,
                  cia1TimerA=0x4025, cia1ControlA=1,
                  setupBasis='libsidplayfp 3.1.1 src/psiddrv.a65 cold/vicinit/ciainit/setregs/idle and src/psiddrv.cpp song-number/flags; Giana masks CIA IRQs and sets raster low byte 0.'))
    with gzip.open(output / 'trace.json.gz', 'wt') as file:
        json.dump(retained, file, separators=(',', ':'))
    write_json(output / 'verification.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/research/giana/Great_Giana_Sisters.sid')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--vice', type=Path, default=ROOT / '.tools/vice-headless-3.9/build/src/x64sc')
    parser.add_argument('--refreshes', type=int, default=512)
    args = parser.parse_args()
    result = probe(args.source.resolve(), args.output.resolve(), args.vice.resolve(), args.refreshes)
    print(json.dumps(dict(verification=str(args.output.resolve() / 'verification.json'),
                          capture=result['capture'], sidStoreCount=result['sid']['storeCount'],
                          sidReadCount=result['sid']['readCount'], volume=result['volume']), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Giana contrast probe: {error}')
