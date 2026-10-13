"""Compare named pitch operations with short isolated pinned-archive execution."""

from collections import Counter
from dataclasses import asdict
import hashlib
import itertools
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import BankedAuditMemory
from psid_profile import psid_profile
from verify_player import cpu_type
from model import (PitchInputs, PitchParameters, PitchState, advance_pitch,
                   glide_divisor, rounded_glide_step)

SOURCE = ROOT / '.local/research/cybernoid-ii/Cybernoid_II.sid'
SOURCE_SHA = '41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192'
FIELDS = dict(base_note=0xa63f, frequency=(0xa693, 0xa696),
              held_frequency=(0xa64b, 0xa645), vibrato_extent=0xa664,
              vibrato_direction=0xa667, vibrato_position=0xa66a,
              vibrato_age=0xa6a8, glide_enabled=0xa64e, glide_active=0xa651,
              glide_control=0xa690, glide_target=0xa68d)
BRANCH_HOOKS = {0xa9ca, 0xa9ec, 0xa9f8, 0xaa20, 0xaa25, 0xaa2a, 0xaa2f,
                0xaa3a, 0xaa5f, 0xaa75, 0xaaa4, 0xaac4, 0xaad2, 0xaaf0,
                0xab02, 0xab3d, 0xab41, 0xab52, 0xab6c}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folder = Path(__file__).parent
    output = folder / 'verification.json'
    assert not output.exists()
    data = SOURCE.read_bytes()
    assert hashlib.sha256(data).hexdigest() == SOURCE_SHA
    parsed = psid_profile(data, profile='pal-banked', subtune=1)
    base = [0] * 65536
    base[parsed['loadAddress']:parsed['endAddress']] = parsed['payload']
    cpu_class = cpu_type()

    def memory():
        ram = BankedAuditMemory((0xd400,))
        ram.data[:] = base
        ram.data[0:2] = [0x2f, 0x36]
        ram.phase = 'play'
        return ram

    def execute(ram, entry, stop):
        cpu = cpu_class(memory=ram)
        cpu.pc, cpu.x = entry, ram.data[0x48]
        cpu.p = 0x26
        steps, hooks, delta = 0, set(), None
        while cpu.pc != stop:
            assert entry <= cpu.pc < stop, hex(cpu.pc)
            if cpu.pc in BRANCH_HOOKS:
                hooks.add(cpu.pc)
            if cpu.pc == 0xaa20:
                delta = ram.data[0x4f] | ram.data[0x4e] << 8
            ram.instruction = cpu.disassemble[cpu.memory[cpu.pc]][0]
            cpu.step()
            steps += 1
            assert steps < 20000
        assert not ram.writes
        return steps, sorted(hooks), delta

    def table_word(index):
        return base[0xae3f + index] | base[0xae96 + index] << 8

    def put_state(ram, voice, state):
        for name, location in FIELDS.items():
            value = getattr(state, name)
            if isinstance(location, tuple):
                ram.data[location[0] + voice], ram.data[location[1] + voice] = value & 255, value >> 8
            else:
                ram.data[location + voice] = value

    def get_state(ram, voice):
        values = {}
        for name, location in FIELDS.items():
            values[name] = (ram.data[location[0] + voice] | ram.data[location[1] + voice] << 8
                            if isinstance(location, tuple) else ram.data[location + voice])
        return PitchState(**values)

    division_checks, divisor_checks = [], []
    division_edges = itertools.product((0, 1, 2, 7, 128, 199, 255, 256, 257, 1137, 32767, 32768, 65534, 65535),
                                       (0, 1, 2, 3, 7, 12, 127, 128, 129, 200, 255))
    for distance, divisor in division_edges:
        ram = memory()
        ram.data[0x50:0x53] = [distance & 255, distance >> 8, divisor]
        steps, _, _ = execute(ram, 0xab1a, 0xab43)
        actual = ram.data[0x50] | ram.data[0x51] << 8
        predicted = rounded_glide_step(distance, divisor)
        assert actual == predicted, (distance, divisor, actual, predicted)
        division_checks.append(dict(distance=distance, divisor=divisor, actual=actual,
                                    predicted=predicted, instructions=steps))
    for length, speed in itertools.product((0, 1, 4, 15), (0, 1, 2, 15, 16, 17, 127, 128, 129, 255)):
        ram = memory()
        ram.data[0xa629] = speed
        # $AB14 is normally patched to length by $AAB0; this isolated entry
        # supplies that caller-established operand, as in the earlier edge proof.
        ram.data[0xab14] = length
        steps, _, _ = execute(ram, 0xab0d, 0xab1a)
        actual, predicted = ram.data[0x52], glide_divisor(length, speed)
        assert actual == predicted, (length, speed, actual, predicted)
        divisor_checks.append(dict(length=length, speed=speed, actual=actual,
                                   predicted=predicted, instructions=steps))

    checks, branch_counts = [], Counter()
    randomizer = random.Random(8388001)
    controls = (0, 1, 0x10, 0x53, 0x80, 0x91, 0xf0, 0xff)
    glide_controls = (0, 1, 0x10, 0x11, 0x40, 0x42, 0xf0, 0xff)
    for number in range(512):
        voice = number % 3
        effective = randomizer.choice((0, 16, 28, 47, 71, 84))
        base_note, target = randomizer.choice(((16, 28), (28, 16), (0, 84), (84, 0), (28, 28)))
        state = PitchState(base_note, randomizer.choice((0, 65535, table_word(effective))),
                           randomizer.choice((0, 65535, table_word(base_note))),
                           randomizer.choice((0, 7, 255)), randomizer.choice((0, 127, 128, 254, 255)),
                           randomizer.choice((0, 1, 7, 127, 128, 129, 255)),
                           randomizer.choice((0, 47, 48, 255)), (number // (2 * len(controls))) % 2, (number // len(controls)) % 2,
                           randomizer.choice(glide_controls), target)
        instrument = randomizer.choice((0, 1, 4, 7, 8, 12, 15))
        if controls[number % len(controls)] == 0x53:
            instrument = 1
        parameters = PitchParameters(controls[number % len(controls)], base[0xb0ac + instrument], number % 7 == 0)
        inputs = PitchInputs(table_word(effective), table_word(effective + 1), table_word(base_note), table_word(target),
                             randomizer.choice((0, 1, 12, 13, 255)), randomizer.choice((0, 1, 59, 63, 254, 255)),
                             randomizer.choice((0, 1, 63, 255)), randomizer.choice((0, 2, 17, 128, 129, 255)))
        ram = memory()
        for other in range(3):
            put_state(ram, other, state)
        ram.data[0x40], ram.data[0x48] = parameters.vibrato_control, voice
        ram.data[0xa642 + voice], ram.data[0xa63c + voice] = instrument, effective
        ram.data[0xa65e + voice] = inputs.note_age
        ram.data[0xa633 + voice], ram.data[0xa636 + voice] = inputs.row_remaining, inputs.row_duration
        ram.data[0xa629] = inputs.speed
        predicted = advance_pitch(state, parameters, inputs)
        steps, hooks, actual_delta = execute(ram, 0xaa97 if parameters.drum_mode else 0xa9c1, 0xab8d)
        actual = get_state(ram, voice)
        assert actual == predicted.state, (number, state, parameters, inputs, actual, predicted)
        assert actual_delta == predicted.vibrato_delta
        assert all(get_state(ram, other) == state for other in range(3) if other != voice)
        branch_counts.update(hooks)
        checks.append(dict(case=number, voice=voice, effectiveNote=effective, instrument=instrument,
                           state=asdict(state), parameters=asdict(parameters), inputs=asdict(inputs),
                           actual=asdict(actual), predicted=asdict(predicted), branchHooks=hooks,
                           actualVibratoDelta=actual_delta, instructions=steps))

    coverage = {(row['parameters']['vibrato_control'], row['state']['glide_active'])
                for row in checks if not row['parameters']['drum_mode']}
    assert coverage == set(itertools.product(controls, (0, 1))), 'Control/glide-state coverage is correlated'
    ordinary = [row for row in checks if row['parameters']['vibrato_control'] == 0x53
                and row['state']['glide_active'] == 0 and not row['parameters']['drum_mode']]
    assert any(0xaa5f in row['branchHooks'] for row in ordinary), 'Ordinary centered subtraction not executed'
    assert any(row['inputs']['note_age'] < row['parameters']['vibrato_wait']
               and 0xaa5f not in row['branchHooks'] for row in ordinary), 'Ordinary wait bypass not executed'

    # Conventional rounded 16-bit division is a materially different mechanism.
    assert rounded_glide_step(32768, 2) != round(32768 / 2)
    assert rounded_glide_step(199, 200) != round(199 / 200)
    assert glide_divisor(15, 17) == 14
    assert glide_divisor(15, 129) == 15
    assert SOURCE.read_bytes() == data
    result = dict(schemaVersion=1, sourceSha256=SOURCE_SHA, scriptSha256=digest(Path(__file__)),
                  modelSha256=digest(folder / 'model.py'),
                  tools={name: digest(ROOT / 'scripts' / name) for name in ('psid_audit.py', 'psid_profile.py', 'verify_player.py')},
                  componentRange=dict(vibratoEntryPc=0xa9c1, drumBypassEntryPc=0xaa97, stopBeforePc=0xab8d),
                  randomSeed=8388001, divisionChecks=division_checks, divisorChecks=divisor_checks,
                  componentChecks=checks, branchCounts={f'{pc:04X}': count for pc, count in sorted(branch_counts.items())},
                  inputSourcePolicy='Pinned static frequency/wait tables are unchanged. Synthetic caller RAM/state/scratch is named; divisor-only entry supplies the length operand normally patched by the routine. No input SID file changes.',
                  limits='Isolated original routines with synthetic caller state, not intact score execution, per-body title coverage, a complete player, instruction-cycle equality, SID state, audio or listening evidence. Standard banked no-I/O-read/ROM/host guards are retained; no SID stores are permitted in these blocks.')
    with output.open('x') as target:
        json.dump(result, target, separators=(',', ':'))
        target.write('\n')
    print(json.dumps(dict(divisionChecks=len(division_checks), divisorChecks=len(divisor_checks),
                          componentChecks=len(checks), matched=True,
                          maximumInstructions=max(c['instructions'] for c in checks))))


if __name__ == '__main__':
    main()
