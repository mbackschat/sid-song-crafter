import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
FRAME_CYCLES = 19656


def require(condition, message):
    if not condition:
        raise ValueError(message)


def expected_states(writes, calls):
    state = bytearray(25)
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
        address, value = write['address'] - 0xd400, write['value']
        require(0 <= address < 25 and isinstance(value, int) and 0 <= value <= 255, 'Invalid SID register write')
        while cursor < len(calls) and calls[cursor] <= current_tick:
            states[calls[cursor]] = bytes(state)
            cursor += 1
        state[address] = value
        previous_tick = current_tick
    for count in calls[cursor:]:
        states[count] = bytes(state)
    return states


def monitor_commands(prg, calls):
    require(not any(char in str(prg) for char in ('"', '\n', '\r')), 'Unsafe monitor PRG path')
    require(calls and calls[0] == 0 and calls == sorted(set(calls)), 'Calls must start at zero and increase')
    lines = [f'loadbasic "{prg}" 0', 'break exec $1003', 'keybuf run\\n', 'x', 'r', 'radix h', 'bank io', 'm $d400 $d418']
    previous = 0
    for count in calls[1:]:
        lines += ['radix d', f'ignore 1 {count - previous - 1}', 'x', 'r', 'radix h', 'bank io', 'm $d400 $d418']
        previous = count
    return '\n'.join(lines + ['quit', ''])


def verify_log(log, writes, calls):
    registers = re.findall(r'^\.;([0-9a-f]{4})\s+[^\n]*?\s+(\d+)\s*$', log, re.MULTILINE | re.IGNORECASE)
    memory = re.findall(r'^>C:d400\s+([^\n]+)', log, re.MULTILINE | re.IGNORECASE)
    require(len(registers) == len(calls) == len(memory), 'Missing or extra VICE checkpoint')
    expected = expected_states(writes, calls)
    first_cycle = int(registers[0][1])
    checkpoints = []
    for count, (pc, cycle), raw in zip(calls, registers, memory):
        require(int(pc, 16) == 0x1003, 'VICE stopped outside the native play entry')
        tokens = raw.split()[:25]
        require(len(tokens) == 25 and all(re.fullmatch('[0-9a-fA-F]{2}', token) for token in tokens), 'Invalid VICE SID snapshot')
        state = bytes(int(token, 16) for token in tokens)
        require(state == expected[count], f'VICE SID registers disagree after {count} play calls')
        error = int(cycle) - first_cycle - count * FRAME_CYCLES
        # SID-Wizard 1.97 exporter.asm rast1st polls $d012; its instruction phase can shift within the seven-cycle polling loop.
        require(abs(error) <= 7, f'VICE PAL cadence disagrees after {count} play calls: {error} cycles')
        checkpoints.append({'completedPlayCalls': count, 'cycle': int(cycle), 'cycleError': error, 'sidRegisters': state.hex()})
    return {'checkpoints': checkpoints, 'frameCycles': FRAME_CYCLES, 'cycleTolerance': 7, 'scope': 'Standalone PRG boot, sampled SID write shadows and single-speed PAL cadence; not continuous write equivalence or listening evidence'}


def main():
    parser = argparse.ArgumentParser(description='Check a SID-Wizard Extra 1x PRG against audited SID writes in headless VICE.')
    parser.add_argument('prg', type=Path)
    parser.add_argument('writes', type=Path)
    parser.add_argument('--calls', type=int, nargs='+', required=True, help='Completed play-call checkpoints; zero is included automatically')
    parser.add_argument('--output', type=Path, required=True)
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
    expected_states(writes, calls)
    require(any(write['phase'] == 'play' and write['tick'] >= calls[-1] - 1 for write in writes), 'Audit writes do not reach the requested final checkpoint')
    output.mkdir(parents=True, exist_ok=False)
    monitor = output / 'commands.mon'
    monitor.write_text(monitor_commands(prg, calls))
    command = [str(args.vice.resolve()), '-config', '/dev/null', '-directory', str(args.data.resolve()), '-pal', '+logcolorize', '-initbreak', 'ready', '-moncommands', str(monitor), '-monlog', '-monlogname', str(output / 'monitor.log'), '-limitcycles', str(4_000_000 + calls[-1] * FRAME_CYCLES), '-warp', '+sound']
    env = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY'):
        env.pop(key, None)
    for key in ('XDG_CONFIG_HOME', 'XDG_STATE_HOME'):
        env[key] = str(output / key.lower())
        (Path(env[key]) / 'vice').mkdir(parents=True)
    (output / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    with (output / 'process.log').open('w') as log:
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=60, check=True)
    result = verify_log((output / 'monitor.log').read_text(errors='replace'), writes, calls)
    result.update(prgSha256=hashlib.sha256(prg_bytes).hexdigest(), writesSha256=hashlib.sha256(writes_bytes).hexdigest(), vice=str(args.vice.resolve()))
    (output / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
