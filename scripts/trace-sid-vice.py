"""Trace a bounded callable PAL PSID program through the headless VICE monitor."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess

from sid_audit_host import COUNTER, HARNESS_BASE, INIT_ACTIVE, harness


ROOT = Path(__file__).resolve().parents[1]
FRAME_CYCLES = 19656


def require(condition, message):
    if not condition:
        raise ValueError(message)


def psid_profile(data, *, subtune=None, profile='strict', host_base=None):
    from psid_profile import psid_profile as validated_profile
    result = validated_profile(data, subtune=subtune, profile=profile, host_base=host_base)
    if result['profile'] == 'strict':
        # Existing callers serialize this shape; the explicit profile owns the
        # extra host fields without rewriting earlier strict-profile receipts.
        return {key: result[key] for key in ('loadAddress', 'endAddress', 'initAddress', 'playAddress',
                                            'sidModel', 'sidBases', 'payload')}
    return result


def monitor_commands(payload, program, profile, labels, first, last):
    require(type(first) is int and type(last) is int and 0 <= first <= last <= 65534, 'Trace window must lie within calls 0..65534')
    for path in (payload, program):
        require(not any(char in str(path) for char in ('"', '\n', '\r')), 'Unsafe monitor path')
    # VICE 3.9 condition expressions evaluate left to right (vice.texi CONDITION); group each comparison.
    host_base = profile.get('hostBase', HARNESS_BASE)
    counter_address = host_base + 0x100
    init_active = counter_address + 2
    counter = f'((@ram:${counter_address + 1:04x} * $0100) + @ram:${counter_address:04x})'
    condition = f'({counter} >= ${first:04x}) && ({counter} <= ${last:04x})'
    banked = profile.get('profile') == 'pal-banked'
    if banked:
        condition = f'(@ram:${init_active:04x} != $00) || ({condition})'
    traces = [f'trace store ${base:04x} ${base + 31:04x} if {condition}' for base in profile['sidBases']]
    lines = ['radix h', 'sidefx off', 'dummy off', 'bank ram']
    # audit_psid starts backing RAM at zero, including reachable scratch above
    # the payload and beneath hidden KERNAL (sid_vice_trace_test's high-RAM fixture).
    lines.extend(['fill $0002 $cfff $00', 'fill $e000 $ffff $00'] if banked else ['fill $0002 $bfff $00'])
    lines.extend([f'load "{payload}" 0', f'load "{program}" 0', 'r a=$00,x=$00,y=$00,sp=$ff,fl=$24', f'r pc=${host_base:04x}'])
    if banked:
        lines.extend([f'trace exec ${profile["initAddress"]:04x}', f'trace exec ${labels["init_return"]:04x}'])
    else:
        lines.append(f'until ${labels["wait"]:04x}')
    if not banked or profile['playAddress'] != profile['initAddress']:
        lines.append(f'trace exec ${profile["playAddress"]:04x}')
    lines.extend([*traces, f'until ${labels["done"]:04x}', 'r', 'bank ram', f'd ${profile["initAddress"]:04x} ${min(profile["endAddress"] - 1, profile["initAddress"] + 0x1000):04x}', f'm ${profile["loadAddress"]:04x} ${profile["endAddress"] - 1:04x}', 'quit', ''])
    return '\n'.join(lines)


TRACE_HEADER = re.compile(r'^#\d+ \(Trace\s+(exec|store)\s+([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\s*$', re.IGNORECASE)
INSTRUCTION = re.compile(r'^\.C:([0-9a-f]{4})\s+((?:[0-9a-f]{2}\s+){1,3})(.*?)\s+-\s+A:([0-9a-f]{2}) X:([0-9a-f]{2}) Y:([0-9a-f]{2}) SP:([0-9a-f]{2}) (\S{8})\s+(\d+)\s*$', re.IGNORECASE)


def parse_trace(log, play_address, sid_bases=(0xd400,), *, init_address=None, init_return=None):
    entries, writes = [], []
    banked = init_address is not None or init_return is not None
    require(not banked or init_address is not None and init_return is not None, 'Both init markers are required')
    init_entry_record = init_return_record = None
    init_executions = []
    phase = 'host'
    lines = log.splitlines()
    for index, line in enumerate(lines):
        header = TRACE_HEADER.fullmatch(line)
        if not header:
            require(not re.match(r'^#\d+ \(Trace', line), 'Unrecognized VICE trace header')
            continue
        require(index + 1 < len(lines), 'Missing trace instruction')
        instruction = INSTRUCTION.fullmatch(lines[index + 1])
        require(instruction, 'Missing or unsupported VICE instruction trace')
        operation, address, raster, raster_cycle = header.groups()
        pc, encoded, mnemonic, a, x, y, sp, flags, cycle = instruction.groups()
        registers = dict(a=int(a, 16), x=int(x, 16), y=int(y, 16), sp=int(sp, 16), flags=flags)
        record = dict(writerPc=int(pc, 16), opcodeHex=''.join(encoded.split()).lower(), instruction=mnemonic.strip(), registers=registers, rasterLine=int(raster), rasterCycle=int(raster_cycle), monitorCycle=int(cycle))
        require(0 <= record['rasterLine'] < 312 and 0 <= record['rasterCycle'] < 63, 'Trace raster context is outside the PAL range')
        address = int(address, 16)
        if operation.lower() == 'exec':
            if banked and address == init_address and init_entry_record is None:
                require(record['writerPc'] == init_address, 'Init marker address disagrees')
                phase = 'init'
                record.update(phase=phase, tick=None)
                init_entry_record = record
                init_executions.append(record)
                continue
            if banked and address == init_return:
                require(record['writerPc'] == init_return and phase == 'init' and init_return_record is None,
                        'Unexpected init-return marker')
                phase = 'host'
                record.update(phase=phase, tick=None)
                init_return_record = record
                continue
            if banked and phase == 'init':
                require(address in (init_address, play_address) and record['writerPc'] == address,
                        'Unexpected init-internal entry marker')
                record.update(phase='init', tick=None)
                init_executions.append(record)
                continue
            require(address == play_address and record['writerPc'] == play_address, 'Unexpected executed trace address')
            if banked:
                require(init_return_record is not None, 'Play entry precedes init return')
                phase = 'play'
                record['phase'] = phase
            record['tick'] = len(entries)
            entries.append(record)
            continue
        if banked and phase == 'init':
            require(record['monitorCycle'] >= init_entry_record['monitorCycle'], 'SID store precedes init entry')
        else:
            require(entries and (not banked or phase == 'play'), 'SID store precedes the first play-entry marker')
            require(entries[-1]['monitorCycle'] <= record['monitorCycle'] < entries[-1]['monitorCycle'] + FRAME_CYCLES, 'SID store timestamp lies outside its PAL play call')
        require(not writes or record['monitorCycle'] > writes[-1]['monitorCycle'], 'SID store monitor timestamps must increase')
        opcode = bytes.fromhex(record['opcodeHex'])
        require(len(opcode) == 3 and opcode[0] in (0x8d, 0x9d, 0x99, 0x8e, 0x8c), 'SID trace requires a supported non-RMW absolute store')
        decoded = re.fullmatch(r'(STA|STX|STY)\s+\$([0-9a-f]{4})(?:,([XY]))?', record['instruction'], re.IGNORECASE)
        expected_mnemonic = 'STX' if opcode[0] == 0x8e else 'STY' if opcode[0] == 0x8c else 'STA'
        expected_index = 'X' if opcode[0] == 0x9d else 'Y' if opcode[0] == 0x99 else None
        require(decoded and decoded[1].upper() == expected_mnemonic and int(decoded[2], 16) == int.from_bytes(opcode[1:], 'little') and (decoded[3].upper() if decoded[3] else None) == expected_index, 'Store bytes and disassembly disagree')
        effective = int.from_bytes(opcode[1:], 'little')
        if opcode[0] == 0x9d:
            effective = (effective + registers['x']) & 65535
        elif opcode[0] == 0x99:
            effective = (effective + registers['y']) & 65535
        require(effective == address and any(base <= address <= base + 31 for base in sid_bases), 'Store opcode and traced SID address disagree')
        register = 'x' if opcode[0] == 0x8e else 'y' if opcode[0] == 0x8c else 'a'
        record.update(tick=None if banked and phase == 'init' else entries[-1]['tick'], address=address, value=registers[register])
        if banked:
            record['phase'] = phase
        writes.append(record)
    require(entries and (writes or banked), 'Missing play entries or SID stores')
    result = dict(entries=entries, writes=writes)
    if banked:
        require(init_entry_record is not None and init_return_record is not None, 'Missing init entry or return marker')
        require(init_entry_record['monitorCycle'] < init_return_record['monitorCycle'] <= entries[0]['monitorCycle'],
                'Init marker timestamps disagree')
        require(all(row['monitorCycle'] < init_return_record['monitorCycle'] for row in writes if row['phase'] == 'init'),
                'Init store occurs after return')
        result.update(initEntry=init_entry_record, initReturn=init_return_record, initExecutions=init_executions)
    return result


def verify_trace(parsed, oracle, first, last):
    require(len(parsed['entries']) == last + 1, 'Missing or extra VICE play calls')
    banked = 'initEntry' in parsed
    if banked:
        actual = [(row['phase'], row['tick'], row['address'], row['value']) for row in parsed['writes']]
        expected = [(row['phase'], row['tick'], row['address'], row['value']) for row in oracle
                    if row['phase'] == 'init' or row['phase'] == 'play' and first <= row['tick'] <= last]
    else:
        actual = [(row['tick'], row['address'], row['value']) for row in parsed['writes']]
        expected = [(row['tick'], row['address'], row['value']) for row in oracle if row['phase'] == 'play' and first <= row['tick'] <= last]
    require(actual == expected and (actual or banked), 'VICE ordered SID stores disagree with the call/address/value oracle')
    start = parsed['entries'][0]['monitorCycle']
    errors = [row['monitorCycle'] - start - row['tick'] * FRAME_CYCLES for row in parsed['entries']]
    require(max(abs(error) for error in errors) <= 9, 'VICE single-PAL cadence exceeds the polling-loop tolerance')
    result = dict(matchedWrites=len(actual), playCalls=len(parsed['entries']), firstCall=first, lastCall=last, frameCycles=FRAME_CYCLES, maximumCadenceError=max(abs(error) for error in errors), cadenceTolerance=9)
    if banked:
        result.update(matchedInitWrites=sum(row['phase'] == 'init' for row in parsed['writes']),
                      matchedPlayWrites=sum(row['phase'] == 'play' for row in parsed['writes']))
    return result


def run_trace(sid, oracle_path, output, first, last, vice, data_directory, *, subtune=None, profile='strict', host_base=None, timeout=60):
    require(type(timeout) in (int, float) and timeout > 0, 'Timeout must be positive finite seconds')
    try:
        finite_timeout = math.isfinite(timeout)
    except OverflowError:
        finite_timeout = False
    require(finite_timeout, 'Timeout must be positive finite seconds')
    sid_bytes, oracle_bytes = sid.read_bytes(), oracle_path.read_bytes()
    profile = psid_profile(sid_bytes, subtune=subtune, profile=profile, host_base=host_base)
    program, labels = harness(profile, last + 1)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh trace output directory')
    output.mkdir(parents=True)
    payload_path, program_path = output / 'payload.prg', output / 'harness.prg'
    payload_path.write_bytes(profile['loadAddress'].to_bytes(2, 'little') + profile['payload'])
    program_path.write_bytes(program)
    monitor = output / 'commands.mon'
    monitor.write_text(monitor_commands(payload_path, program_path, profile, labels, first, last))
    command = [str(vice), '-config', '/dev/null', '-directory', str(data_directory), '-pal', '+logcolorize', '-initbreak', 'ready', '-moncommands', str(monitor), '-monlog', '-monlogname', str(output / 'monitor.log'), '-limitcycles', str(4_000_000 + (last + 1) * FRAME_CYCLES), '-warp', '+sound', '-sidenginemodel', 'resid6581' if profile['sidModel'] == 'MOS6581' else 'resid8580']
    if len(profile['sidBases']) == 2:
        command.extend(['-sidextra', '1', '-sid2address', '0xd420'])
    env = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY'):
        env.pop(key, None)
    for key in ('XDG_CONFIG_HOME', 'XDG_STATE_HOME'):
        env[key] = str(output / key.lower())
        (Path(env[key]) / 'vice').mkdir(parents=True)
    (output / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    with (output / 'process.log').open('w') as process_log:
        subprocess.run(command, env=env, stdout=process_log, stderr=subprocess.STDOUT, timeout=timeout, check=True)
    log = (output / 'monitor.log').read_text(errors='replace')
    markers = dict(init_address=profile['initAddress'], init_return=labels['init_return']) if profile.get('profile') == 'pal-banked' else {}
    parsed = parse_trace(log, profile['playAddress'], profile['sidBases'], **markers)
    verification = verify_trace(parsed, json.loads(oracle_bytes), first, last)
    writers = {}
    for row in parsed['writes']:
        key = f'{row["writerPc"]:04x}'
        writer = writers.setdefault(key, dict(instruction=row['instruction'], opcodeHex=row['opcodeHex'], addresses=set(), writes=0))
        writer['addresses'].add(f'{row["address"]:04x}')
        writer['writes'] += 1
    for writer in writers.values():
        writer['addresses'] = sorted(writer['addresses'])
    result = dict(schemaVersion=1, evidenceLevel='Executed 6510 program in headless VICE', sourceSha256=hashlib.sha256(sid_bytes).hexdigest(), oracleSha256=hashlib.sha256(oracle_bytes).hexdigest(), harnessSha256=hashlib.sha256(program).hexdigest(), viceSha256=hashlib.sha256(vice.read_bytes()).hexdigest(), profile={key: value for key, value in profile.items() if key != 'payload'}, harnessLabels=labels, verification=verification, writers=writers, limitations='A controlled RAM harness calls the original init/play once per PAL frame with IRQs, sprites and display DMA disabled. This is not the original player boot environment. Tracepoint stopwatch/raster values describe monitor checkpoints, not exact SID bus-write cycles. Store values are decoded from unchanged store-source CPU registers and checked against an independent ordered-write oracle. No audio or listening verdict follows from this trace.')
    for path, value in ((output / 'trace.json', parsed), (output / 'study.json', result)):
        path.write_text(json.dumps(value, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sid', type=Path)
    parser.add_argument('--oracle', type=Path, required=True)
    parser.add_argument('--first-call', type=int, default=99)
    parser.add_argument('--last-call', type=int, default=150)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--vice', type=Path, default=ROOT / '.tools/vice-headless-3.9/build/src/x64sc')
    parser.add_argument('--data', type=Path, default=Path('/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice'))
    parser.add_argument('--subtune', type=int, help='Explicit 1-based subtune selection')
    parser.add_argument('--profile', choices=('strict', 'pal-banked'), default='strict')
    parser.add_argument('--host-base', type=lambda value: int(value, 0), help='PAL banked host address; explicit low-RAM page, e.g. 0x0400')
    parser.add_argument('--timeout', type=float, default=60, help='Positive VICE wall-clock timeout in seconds (default: 60)')
    args = parser.parse_args()
    result = run_trace(args.sid.resolve(), args.oracle.resolve(), args.output.resolve(), args.first_call, args.last_call, args.vice.resolve(), args.data.resolve(), subtune=args.subtune, profile=args.profile, host_base=args.host_base, timeout=args.timeout)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
