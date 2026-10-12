"""Trace a bounded callable PAL PSID program through the headless VICE monitor."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
FRAME_CYCLES = 19656
HARNESS_BASE = 0xc000
COUNTER = 0xc100


def require(condition, message):
    if not condition:
        raise ValueError(message)


def psid_profile(data):
    require(len(data) >= 124 and data[:4] == b'PSID', 'Expected a complete PSID header')
    word = lambda offset: int.from_bytes(data[offset:offset + 2], 'big')
    require(word(4) == 2 and word(6) == 124, 'Trace supports PSID v2 with a $7c-byte header')
    require(word(14) == 1 and word(16) == 1, 'Trace requires exactly one subtune, initialized with A=0')
    require(data[18:22] == bytes(4) and word(118) in (0x14, 0x24) and data[122:124] == bytes(2), 'Trace requires one declared SID model, explicit PAL VBI and no additional SID or MUS/PlaySID flags')
    load = word(8)
    payload = data[124:]
    if load == 0:
        require(len(payload) >= 2, 'Missing embedded load address')
        load = int.from_bytes(payload[:2], 'little')
        payload = payload[2:]
    end = load + len(payload)
    init, play = word(10) or load, word(12)
    require(0x0400 <= load < end <= 0xa000, 'Payload must lie entirely in RAM $0400–$9fff')
    require(load <= init < end and load <= play < end, 'Init and play must be callable addresses inside the payload')
    return dict(loadAddress=load, endAddress=end, initAddress=init, playAddress=play, sidModel='MOS6581' if word(118) == 0x14 else 'MOS8580', payload=payload)


def harness(profile, calls):
    require(type(calls) is int and 1 <= calls <= 255, 'Harness supports 1..255 play calls')
    code = bytearray()
    labels, branches = {}, []

    def emit(*values):
        code.extend(values)

    def absolute(opcode, address):
        emit(opcode, address & 255, address >> 8)

    def label(name):
        labels[name] = HARNESS_BASE + len(code)

    def branch(opcode, name):
        emit(opcode, 0)
        branches.append((len(code) - 1, name))

    # psid_audit.audit_psid starts init with SP=$FF and decimal mode clear; retain those call assumptions.
    emit(0x78, 0xd8, 0xa2, 0xff, 0x9a)
    emit(0xa9, 0x7f)
    absolute(0x8d, 0xdc0d)
    absolute(0x8d, 0xdd0d)
    absolute(0xad, 0xdc0d)
    absolute(0xad, 0xdd0d)
    emit(0xa9, 0)
    for address in (0xd01a, 0xd011, 0xd015, COUNTER):
        absolute(0x8d, address)
    emit(0xa9, 0x2f, 0x85, 0, 0xa9, 0x37, 0x85, 1, 0xa9, 0, 0xa2, 0, 0xa0, 0)
    absolute(0x20, profile['initAddress'])
    label('wait')
    emit(0xa9, 250)
    absolute(0xcd, 0xd012)
    branch(0xd0, 'wait')
    label('call')
    absolute(0x20, profile['playAddress'])
    absolute(0xee, COUNTER)
    absolute(0xad, COUNTER)
    emit(0xc9, calls)
    branch(0xf0, 'done')
    label('leave')
    emit(0xa9, 250)
    absolute(0xcd, 0xd012)
    branch(0xf0, 'leave')
    absolute(0x4c, labels['wait'])
    label('done')
    absolute(0x4c, labels['done'])
    for offset, target in branches:
        distance = labels[target] - (HARNESS_BASE + offset + 1)
        require(-128 <= distance <= 127, 'Harness branch exceeds the relative range')
        code[offset] = distance & 255
    require(HARNESS_BASE + len(code) < COUNTER, 'Harness overlaps its call counter')
    return HARNESS_BASE.to_bytes(2, 'little') + code, labels


def monitor_commands(payload, program, profile, labels, first, last):
    require(type(first) is int and type(last) is int and 0 <= first <= last <= 254, 'Trace window must lie within calls 0..254')
    for path in (payload, program):
        require(not any(char in str(path) for char in ('"', '\n', '\r')), 'Unsafe monitor path')
    # VICE 3.9 condition expressions evaluate left to right (vice.texi CONDITION); group each comparison.
    condition = f'(@ram:${COUNTER:04x} >= ${first:02x}) && (@ram:${COUNTER:04x} <= ${last:02x})'
    lines = ['radix h', 'sidefx off', 'dummy off', 'bank ram', 'fill $0002 $bfff $00', f'load "{payload}" 0', f'load "{program}" 0', 'r a=$00,x=$00,y=$00,sp=$ff,fl=$24', f'r pc=${HARNESS_BASE:04x}', f'until ${labels["wait"]:04x}', f'trace exec ${profile["playAddress"]:04x}', f'trace store $d400 $d418 if {condition}', f'until ${labels["done"]:04x}', 'r', 'bank ram', f'd ${profile["initAddress"]:04x} ${min(profile["endAddress"] - 1, profile["initAddress"] + 0x1000):04x}', f'm ${profile["loadAddress"]:04x} ${profile["endAddress"] - 1:04x}', 'quit', '']
    return '\n'.join(lines)


TRACE_HEADER = re.compile(r'^#\d+ \(Trace\s+(exec|store)\s+([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\s*$', re.IGNORECASE)
INSTRUCTION = re.compile(r'^\.C:([0-9a-f]{4})\s+((?:[0-9a-f]{2}\s+){1,3})(.*?)\s+-\s+A:([0-9a-f]{2}) X:([0-9a-f]{2}) Y:([0-9a-f]{2}) SP:([0-9a-f]{2}) (\S{8})\s+(\d+)\s*$', re.IGNORECASE)


def parse_trace(log, play_address):
    entries, writes = [], []
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
            require(address == play_address and record['writerPc'] == play_address, 'Unexpected executed trace address')
            record['tick'] = len(entries)
            entries.append(record)
            continue
        require(entries, 'SID store precedes the first play-entry marker')
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
        require(effective == address and 0xd400 <= address <= 0xd418, 'Store opcode and traced SID address disagree')
        register = 'x' if opcode[0] == 0x8e else 'y' if opcode[0] == 0x8c else 'a'
        record.update(tick=entries[-1]['tick'], address=address, value=registers[register])
        writes.append(record)
    require(entries and writes, 'Missing play entries or SID stores')
    return dict(entries=entries, writes=writes)


def verify_trace(parsed, oracle, first, last):
    require(len(parsed['entries']) == last + 1, 'Missing or extra VICE play calls')
    actual = [(row['tick'], row['address'], row['value']) for row in parsed['writes']]
    expected = [(row['tick'], row['address'], row['value']) for row in oracle if row['phase'] == 'play' and first <= row['tick'] <= last]
    require(actual == expected and actual, 'VICE ordered SID stores disagree with the call/address/value oracle')
    start = parsed['entries'][0]['monitorCycle']
    errors = [row['monitorCycle'] - start - row['tick'] * FRAME_CYCLES for row in parsed['entries']]
    require(max(abs(error) for error in errors) <= 9, 'VICE single-PAL cadence exceeds the polling-loop tolerance')
    return dict(matchedWrites=len(actual), playCalls=len(parsed['entries']), firstCall=first, lastCall=last, frameCycles=FRAME_CYCLES, maximumCadenceError=max(abs(error) for error in errors), cadenceTolerance=9)


def run_trace(sid, oracle_path, output, first, last, vice, data_directory):
    sid_bytes, oracle_bytes = sid.read_bytes(), oracle_path.read_bytes()
    profile = psid_profile(sid_bytes)
    program, labels = harness(profile, last + 1)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh trace output directory')
    output.mkdir(parents=True)
    payload_path, program_path = output / 'payload.prg', output / 'harness.prg'
    payload_path.write_bytes(profile['loadAddress'].to_bytes(2, 'little') + profile['payload'])
    program_path.write_bytes(program)
    monitor = output / 'commands.mon'
    monitor.write_text(monitor_commands(payload_path, program_path, profile, labels, first, last))
    command = [str(vice), '-config', '/dev/null', '-directory', str(data_directory), '-pal', '+logcolorize', '-initbreak', 'ready', '-moncommands', str(monitor), '-monlog', '-monlogname', str(output / 'monitor.log'), '-limitcycles', str(4_000_000 + (last + 1) * FRAME_CYCLES), '-warp', '+sound', '-sidenginemodel', 'resid6581' if profile['sidModel'] == 'MOS6581' else 'resid8580']
    env = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY'):
        env.pop(key, None)
    for key in ('XDG_CONFIG_HOME', 'XDG_STATE_HOME'):
        env[key] = str(output / key.lower())
        (Path(env[key]) / 'vice').mkdir(parents=True)
    (output / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    with (output / 'process.log').open('w') as process_log:
        subprocess.run(command, env=env, stdout=process_log, stderr=subprocess.STDOUT, timeout=60, check=True)
    log = (output / 'monitor.log').read_text(errors='replace')
    parsed = parse_trace(log, profile['playAddress'])
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
    args = parser.parse_args()
    result = run_trace(args.sid.resolve(), args.oracle.resolve(), args.output.resolve(), args.first_call, args.last_call, args.vice.resolve(), args.data.resolve())
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
