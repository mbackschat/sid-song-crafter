"""Check isolated phase/arithmetic byte edges against the pinned executed routine."""

import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_player import cpu_type


def main():
    folder = Path(__file__).parent
    output = folder / 'edge-verification.json'
    assert not output.exists()
    source = ROOT / '.local/research/cybernoid-ii/Cybernoid_II.sid'
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    assert digest == '41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192'
    offset = int.from_bytes(data[6:8], 'big')
    load = int.from_bytes(data[offset:offset + 2], 'little')
    assert load == 0xa600
    memory = [0] * 65536
    memory[load:load + len(data) - offset - 2] = data[offset + 2:]
    assert memory[0xaa5b] == 0xc9
    base = memory[0xae3f + 28] | memory[0xae96 + 28] << 8
    spec = importlib.util.spec_from_file_location('pitch_model', folder / 'model.py')
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    cpu_class, checks = cpu_type(), []
    for extent, direction, position, age in itertools.product((0, 1, 5, 7), (0, 127, 128, 254, 255),
                                                             (0, 1, 5, 7, 127, 128, 129, 255), (0, 13)):
        ram = memory.copy()
        # The driver normally supplies these scratch/state bytes before $AA20;
        # only its self-modified wait operand is code, at $AA5C (canonical trace).
        inputs = {0xa664: extent, 0xa667: direction, 0xa66a: position,
                  0xa63c: 28, 0xa65e: age, 0xaa5c: 12, 0x4f: 16, 0x4e: 0}
        for address, value in inputs.items():
            ram[address] = value
        cpu = cpu_class(memory=ram)
        cpu.pc, cpu.x = 0xaa20, 0
        steps = 0
        while cpu.pc != 0xaa85:
            assert 0xaa20 <= cpu.pc < 0xaa85, hex(cpu.pc)
            cpu.step()
            steps += 1
            assert steps < 5000
        phase = model.advance_phase(direction, position, extent)
        predicted = model.centered_pitch(base, 16, extent, phase[1], age, 12)
        actual = ram[0x4c] | ram[0x4d] << 8
        assert phase == (ram[0xa667], ram[0xa66a])
        assert predicted == actual, (extent, direction, position, age, predicted, actual)
        checks.append(dict(extent=extent, direction=direction, position=position, noteAge=age,
                           nextDirection=phase[0], nextPosition=phase[1], expected=actual,
                           predicted=predicted, instructions=steps))
    assert source.read_bytes() == data
    result = dict(schemaVersion=1, sourceSha256=digest,
                  scriptSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  modelSha256=hashlib.sha256((folder / 'model.py').read_bytes()).hexdigest(),
                  verifierSha256=hashlib.sha256((ROOT / 'scripts/verify_player.py').read_bytes()).hexdigest(),
                  contract=dict(entryPc=0xaa20, stopBeforePc=0xaa85, voiceIndex=0, pitchTableIndex=28,
                                baseFrequency=base, delta=16, wait=12), checks=checks,
                  limits='Isolated original routine executed with synthetic caller-supplied RAM/scratch and wait operand. No original source file changes, whole-player execution, score usage, glide/delta selection, cycle equality, SID-state or audio claim.')
    with output.open('x') as target:
        json.dump(result, target, indent=2)
        target.write('\n')
    print(json.dumps(dict(checks=len(checks), matched=True, maximumInstructions=max(r['instructions'] for r in checks))))


if __name__ == '__main__':
    main()
