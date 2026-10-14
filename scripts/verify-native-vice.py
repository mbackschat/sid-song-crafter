import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess


from sid_clock import clock_spec


ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def expected_states(writes, calls, sid_bases=(0xd400,)):
    offsets = {base + register: chip * 25 + register for chip, base in enumerate(sid_bases) for register in range(25)}
    state = bytearray(25 * len(sid_bases))
    states = {}
    previous_tick = -1
    cursor = 0
    for write in writes:
        phase, tick = write['phase'], write['tick']
        require(phase in ('init', 'play'), 'Unknown audit phase')
        current_tick = -1 if phase == 'init' else tick
        require(isinstance(current_tick, int) and current_tick >= previous_tick, 'Audit ticks must be ordered')
        require(phase != 'init' or previous_tick == -1, 'Init writes must precede play')
        require(phase != 'play' or current_tick >= 0, 'Play ticks must be nonnegative')
        address, value = write['address'], write['value']
        require(address in offsets and isinstance(value, int) and 0 <= value <= 255, 'Invalid SID register write')
        while cursor < len(calls) and calls[cursor] <= current_tick:
            states[calls[cursor]] = bytes(state)
            cursor += 1
        state[offsets[address]] = value
        previous_tick = current_tick
    for count in calls[cursor:]:
        states[count] = bytes(state)
    return states


def monitor_commands(prg, calls, sid_bases=(0xd400,), selector=None):
    require(not any(char in str(prg) for char in ('"', '\n', '\r')), 'Unsafe monitor PRG path')
    require(calls and calls[0] == 0 and calls == sorted(set(calls)), 'Calls must start at zero and increase')
    snapshot = ['r', 'radix h', 'bank io'] + [f'm ${base:04x} ${base + 24:04x}' for base in sid_bases]
    lines = [f'loadbasic "{prg}" 0', 'break exec $1003', 'keybuf run\\n']
    if selector:
        lines += [f'until ${selector["entryAddress"]:04x}', 'radix h', 'bank ram', 'm $03fe $03ff', f'r pc=${selector["returnAddress"]:04x}']
    lines += ['x'] + snapshot
    previous = 0
    for count in calls[1:]:
        lines += ['radix d', f'ignore 1 {count - previous - 1}', 'x'] + snapshot
        previous = count
    return '\n'.join(lines + ['quit', ''])


def verify_selector(log, selector):
    if selector:
        snapshots = re.findall(r'^>C:03fe\s+([^\n]+)', log, re.MULTILINE | re.IGNORECASE)
        expected = selector['baseAddress'].to_bytes(2, 'little').hex(' ')
        require(len(snapshots) == 1 and ' '.join(snapshots[0].lower().split()[:2]) == expected, 'Native saved SID address differs from the declared second chip')


def export_clock(report):
    name = report.get('clock', 'PAL')
    require(name in ('PAL', 'NTSC'), 'Unsupported standalone clock')
    timing = clock_spec(name.lower())
    cycles = report.get('frameCycles', timing.frame_cycles)
    require(type(cycles) is int and cycles == timing.frame_cycles, 'Standalone frame geometry disagrees with its clock')
    require(math.isclose(report.get('clockHz', timing.clock_hz), timing.clock_hz, rel_tol=1e-12)
            and math.isclose(report.get('ticksPerSecond', timing.ticks_per_second), timing.ticks_per_second, rel_tol=1e-12),
            'Standalone timing metadata disagrees with its clock')
    return timing


def export_profile(prg_bytes, report):
    export_clock(report)
    require(hashlib.sha256(prg_bytes).hexdigest() == report['prgSha256'], 'PRG differs from its export report')
    require((report['player'], report['frameSpeed'], report['standalonePlayerPlayAddress']) == ('Extra', 1, 0x1003), 'Unsupported standalone player profile')
    count = report.get('sidCount', 1)
    require(type(count) is int and count in (1, 2), 'Unsupported standalone SID count')
    bases = (0xd400, 0xd420)[:count]
    model = report.get('sidModel', 'MOS8580')
    require(model in ('MOS6581', 'MOS8580') and report.get('sids') == [{'baseAddress': base, 'model': model} for base in bases], 'Unsupported standalone SID layout')
    if count == 1:
        return bases, None, model
    label_bytes = (ROOT / '.tools/sid-wizard-exporter-2sid/exporter.labels').read_bytes()
    require(hashlib.sha256(label_bytes).hexdigest() == report['build']['labelsSha256'], 'Standalone selector labels differ from the exporter build')
    labels = {name: int(value, 16) for value, name in re.findall(r'^al ([\da-fA-F]+) \.(.+)$', label_bytes.decode(), re.MULTILINE)}
    selector = report['standaloneAddressSelector']
    require((selector['entryAddress'], selector['returnAddress'], selector['baseAddress']) == (labels['SetSID2address'], labels['SID2keyExe:endplmi'], 0xd420), 'Standalone selector differs from pinned labels')
    offset = selector['returnAddress'] - 0x0801 + 2
    require(2 <= offset < len(prg_bytes) and prg_bytes[offset] == 0x60, 'Standalone selector must return through its original RTS')
    return bases, selector, model


def verify_log(log, writes, calls, sid_bases=(0xd400,), *, clock='pal'):
    timing = clock_spec(clock)
    registers = re.findall(r'^\.;([0-9a-f]{4})\s+[^\n]*?\s+(\d+)\s*$', log, re.MULTILINE | re.IGNORECASE)
    memory = [re.findall(rf'^>C:{base:04x}\s+([^\n]+)', log, re.MULTILINE | re.IGNORECASE) for base in sid_bases]
    require(len(registers) == len(calls) and all(len(bank) == len(calls) for bank in memory), 'Missing or extra VICE checkpoint')
    expected = expected_states(writes, calls, sid_bases)
    first_cycle = int(registers[0][1])
    checkpoints = []
    for index, (count, (pc, cycle)) in enumerate(zip(calls, registers)):
        require(int(pc, 16) == 0x1003, 'VICE stopped outside the native play entry')
        tokens = []
        for bank in memory:
            row = bank[index].split()[:25]
            require(len(row) == 25 and all(re.fullmatch('[0-9a-fA-F]{2}', token) for token in row), 'Invalid VICE SID snapshot')
            tokens.extend(row)
        state = bytes(int(token, 16) for token in tokens)
        require(state == expected[count], f'VICE SID registers disagree after {count} play calls')
        error = int(cycle) - first_cycle - count * timing.frame_cycles
        # SID-Wizard 1.97 exporter.asm rast1st polls $d012; its instruction phase can shift within the seven-cycle polling loop.
        require(abs(error) <= 7, f'VICE {timing.name.upper()} cadence disagrees after {count} play calls: {error} cycles')
        checkpoints.append({'completedPlayCalls': count, 'cycle': int(cycle), 'cycleError': error, 'sidRegisters': state.hex()})
    return {'checkpoints': checkpoints, 'frameCycles': timing.frame_cycles, 'cycleTolerance': 7, 'scope': f'Standalone PRG boot, sampled SID write shadows and single-speed {timing.name.upper()} cadence; not continuous write equivalence or listening evidence'}


def main():
    parser = argparse.ArgumentParser(description='Check a SID-Wizard Extra 1x PRG against audited SID writes in headless VICE.')
    parser.add_argument('prg', type=Path)
    parser.add_argument('writes', type=Path)
    parser.add_argument('--calls', type=int, nargs='+', required=True, help='Completed play-call checkpoints; zero is included automatically')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--export-report', type=Path, help='Native export report; selects SID model and is required for two-SID layout and headless address selection')
    parser.add_argument('--vice', type=Path, default=ROOT / '.tools/vice-headless-3.9/build/src/x64sc')
    parser.add_argument('--data', type=Path, default=Path('/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice'))
    args = parser.parse_args()
    require(all(0 < value <= 30000 for value in args.calls), 'Play-call checkpoints must be within 1..30000')
    calls = sorted(set([0] + args.calls))
    prg, writes_path, output = args.prg.resolve(), args.writes.resolve(), args.output.resolve()
    prg_bytes = prg.read_bytes()
    writes_bytes = writes_path.read_bytes()
    writes = json.loads(writes_bytes)
    require(prg_bytes[:2] == b'\x01\x08', 'Expected a BASIC-loadable native PRG')
    exported = json.loads(args.export_report.read_text()) if args.export_report else {}
    timing = export_clock(exported)
    sid_bases, selector, sid_model = export_profile(prg_bytes, exported) if args.export_report else ((0xd400,), None, 'MOS8580')
    expected_states(writes, calls, sid_bases)
    require(any(write['phase'] == 'play' and write['tick'] >= calls[-1] - 1 for write in writes), 'Audit writes do not reach the requested final checkpoint')
    output.mkdir(parents=True, exist_ok=False)
    monitor = output / 'commands.mon'
    monitor.write_text(monitor_commands(prg, calls, sid_bases, selector))
    command = [str(args.vice.resolve()), '-config', '/dev/null', '-directory', str(args.data.resolve()), '-' + timing.name, '+logcolorize', '-initbreak', 'ready', '-moncommands', str(monitor), '-monlog', '-monlogname', str(output / 'monitor.log'), '-limitcycles', str(4_000_000 + calls[-1] * timing.frame_cycles), '-warp', '+sound']
    command += ['-sidenginemodel', 'resid6581' if sid_model == 'MOS6581' else 'resid8580']
    if len(sid_bases) == 2:
        command += ['-sidextra', '1', '-sid2address', '0xd420', '-soundoutput', '2']
    env = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY'):
        env.pop(key, None)
    for key in ('XDG_CONFIG_HOME', 'XDG_STATE_HOME'):
        env[key] = str(output / key.lower())
        (Path(env[key]) / 'vice').mkdir(parents=True)
    (output / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    with (output / 'process.log').open('w') as log:
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=60, check=True)
    monitor_log = (output / 'monitor.log').read_text(errors='replace')
    verify_selector(monitor_log, selector)
    result = verify_log(monitor_log, writes, calls, sid_bases, clock=timing.name)
    result.update(sidBases=list(sid_bases), sidModel=sid_model, standaloneAddressSelector=selector)
    result.update(prgSha256=hashlib.sha256(prg_bytes).hexdigest(), writesSha256=hashlib.sha256(writes_bytes).hexdigest(), vice=str(args.vice.resolve()))
    (output / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
