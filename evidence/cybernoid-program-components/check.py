"""Compare editable PWM/filter functions with isolated original archive routines."""
import hashlib
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from cybernoid_programs import advance_filter, advance_pulse
from verify_player import cpu_type


def main():
    output = Path(__file__).with_name('verification.json')
    assert not output.exists()
    source = ROOT / '.local/research/cybernoid-ii/Cybernoid_II.sid'
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    assert digest == '41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192'
    assert int.from_bytes(data[6:8], 'big') == 124 and data[124:126] == b'\x00\xa6'
    memory = [0] * 65536
    memory[0xa600:0xb718] = data[126:]
    cpu_class = cpu_type()
    checks = []

    def execute(entry, stop, changes):
        ram = memory.copy()
        for address, value in changes.items():
            ram[address] = value
        cpu = cpu_class(memory=ram)
        cpu.pc, cpu.x = entry, 0
        steps = 0
        while cpu.pc != stop:
            assert 0xab69 <= cpu.pc < 0xace2, hex(cpu.pc)
            cpu.step()
            steps += 1
            assert steps < 1000
        return ram, steps

    slots = [list(memory[0xb00c:0xb014]), [0x87, 13, 3, 112, 6, 96, 9, 80],
             [7, 13, 0x83, 112, 6, 96, 9, 80], [0, 255, 127, 2, 127, 2, 127, 2]]
    for slot_index, width, direction, age, fx2 in itertools.product(
            range(len(slots)), (0, 1, 0x500, 0x6e0, 0xcc0, 0xd40, 65534, 65535),
            (0, 1, 128, 255), (0, 3, 4, 9, 10, 127, 128, 255), (0x64, 0x80)):
        slot = slots[slot_index]
        changes = {0x41: fx2, 0x48: 0, 0xa65e: age, 0xa654: width & 255,
                   0xa657: width >> 8, 0xa67e: direction}
        changes.update({0xb00c + index: value for index, value in enumerate(slot)})
        ram, steps = execute(0xab8d, 0xac54, changes)
        expected = (ram[0xa654] | ram[0xa657] << 8, ram[0xa67e])
        predicted = advance_pulse(width, direction, age, fx2, slot)
        assert predicted == expected, (slot_index, width, direction, age, fx2, predicted, expected)
        assert expected[0] == ram[0xa6ab] | ram[0xa6ae] << 8
        checks.append(dict(component='pulse', slotIndex=slot_index, width=width, direction=direction,
                           age=age, fx2=fx2, expected=expected, predicted=predicted, instructions=steps))

    programs = [list(memory[0xafd6:0xafe0]), [7, 1, 2, 3, 9, 31, 30, 20, 10, 100],
                [255, 255, 128, 127, 0, 15, 0, 0, 0, 255]]
    for program_index, cutoff, age in itertools.product(range(len(programs)), (0, 1, 127, 254, 255), range(256)):
        program = programs[program_index]
        changes = {0x48: 0, 0xa67b: 0, 0xa65e: age, 0xa678: cutoff, 0xafc4: 0, 0xafc5: 0x70}
        changes.update({0x7000 + index: value for index, value in enumerate(program)})
        ram, steps = execute(0xac6e, 0xace2, changes)
        expected = (ram[0xd418], ram[0xd416])
        predicted = advance_filter(cutoff, age, program)
        assert predicted == expected, (program_index, cutoff, age, predicted, expected)
        assert ram[0xa678] == expected[1] and ram[0xa683] == 0
        checks.append(dict(component='filter', programIndex=program_index, cutoffHigh=cutoff, age=age,
                           expected=expected, predicted=predicted, instructions=steps))
    assert source.read_bytes() == data
    result = dict(schemaVersion=1, sourceSha256=digest,
                  scriptSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  modelSha256=hashlib.sha256((ROOT / 'scripts/cybernoid_programs.py').read_bytes()).hexdigest(),
                  verifierSha256=hashlib.sha256((ROOT / 'scripts/verify_player.py').read_bytes()).hexdigest(),
                  slots=slots, programs=programs,
                  contract=dict(pulseEntry=0xab8d, pulseStopBefore=0xac54, pulseSlotAddress=0xb00c,
                                filterEntry=0xac6e, filterStopBefore=0xace2, filterPointerAddress=0xafc4,
                                syntheticFilterAddress=0x7000, voiceIndex=0), checks=checks,
                  limits='Isolated archive execution with explicit synthetic caller state and table RAM replacements. Original SID file unchanged. No whole-player, score-usage, cycle, SID-state or audio-equivalence claim.')
    with output.open('x') as target:
        json.dump(result, target, indent=2)
        target.write('\n')
    print(json.dumps(dict(checks=len(checks), matched=True, maximumInstructions=max(row['instructions'] for row in checks))))


if __name__ == '__main__':
    main()
