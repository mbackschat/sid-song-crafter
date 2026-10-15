"""Verify numeric speech against serialized original NMI execution, not CIA timing."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / '.tools/test-deps'))
from py65.devices.mpu6502 import MPU
from speech import Handler, SpeechSynth, private_source_memory


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


class SpeechMemory(list):
    def __init__(self, initial):
        super().__init__(initial)
        self.writes = []

    def __setitem__(self, address, value):
        if isinstance(address, int) and 0xd400 <= address <= 0xd7ff:
            self.writes.append([address, value])
        super().__setitem__(address, value)


def check_state(synth, memory, label):
    fields = {0xf4da: int(synth.next_handler) & 255, 0xf4db: synth.current_base,
              0xf4dc: synth.length, 0xf4dd: synth.gap, 0xf4de: synth.block_count,
              0xf4df: synth.repeat_reload, 0xf4e0: synth.repeat_count,
              0xf4e1: synth.ramp_length, 0xf4e2: synth.ramp_step,
              0xf4e3: synth.previous_base, 0xf4e4: synth.pitch_count,
              0xf4e5: synth.pitch_value, 0xf4e6: synth.pitch_delta & 255,
              0xf1bd: synth.header}
    for address, expected in fields.items():
        require(memory[address] == expected,
                f'{label}: state ${address:04X} source {memory[address]} differs from numeric {expected}')
    for address, expected in [(0xf5, synth.wave_pointer), (0xf7, synth.pitch_pointer), (0xf9, synth.sample_pointer)]:
        require(memory[address] | memory[address + 1] << 8 == expected, f'{label}: pointer ${address:02X} differs')
    require(memory[0xf000:0xf080] == synth.buffer, f'{label}: computed speech buffer differs')


def run_until_idle(cpu, limit=20000):
    for _ in range(limit):
        cpu.step()
        if cpu.pc == 0x403 and cpu.sp == 0xff:
            return
    raise ValueError('Original speech component did not return within instruction bound')


def verify_case(initial, output):
    synth = SpeechSynth(initial)
    memory = SpeechMemory(initial)
    memory[1] = 0x35
    memory[0x400:0x406] = bytes.fromhex('2080f04c0304')
    cpu = MPU(memory=memory, pc=0x400)
    cpu.sp, cpu.p = 0xff, 0x20
    output.mkdir(parents=True)
    results = []
    output_hash = hashlib.sha256()
    with gzip.open(output / 'private-events.jsonl.gz', 'wt') as stream:
        for command in (1, 3):
            cpu.pc, cpu.a = 0x400, command
            memory.writes.clear()
            run_until_idle(cpu)
            synth.start(command)
            require(not memory.writes, 'Original start unexpectedly wrote SID')
            check_state(synth, memory, f'command {command} start')
            count, stores = 0, 0
            while not synth.finished:
                require(count < 100000, 'Speech command exceeded bounded event count')
                handler = memory[0xfffa] | memory[0xfffb] << 8
                require(handler == int(synth.handler), f'command {command} event {count}: NMI handler differs')
                memory.writes.clear()
                cpu.nmi()
                run_until_idle(cpu)
                value = synth.tick()
                expected = [] if value is None else [[0xd418, value]]
                require(memory.writes == expected, f'command {command} event {count}: computed volume differs')
                check_state(synth, memory, f'command {command} event {count}')
                output_hash.update(json.dumps([command, count, handler, expected], separators=(',', ':')).encode())
                stream.write(json.dumps(dict(command=command, event=count, handler=handler, stores=expected,
                                             bufferSha256=digest(bytes(synth.buffer)))) + '\n')
                count += 1
                stores += len(expected)
            require(memory[0xdd0f] == 0x90, 'Original command did not stop its timer')
            results.append(dict(command=command, nmiEvents=count, volumeStores=stores, allBuffersAndNamedStateMatch=True))
    private_path = output / 'private-events.jsonl.gz'
    return dict(commands=results, outputSequenceSha256=output_hash.hexdigest(),
                   privateArtifacts={private_path.name: dict(bytes=private_path.stat().st_size, sha256=digest(private_path.read_bytes()))},
                   scope='Independent descriptor decoding, waveform buffers, named state and every serialized original NMI store for opening commands 1 and 3. Original CPU executes one NMI to completion before the next. No original CIA/VIC timing, nested NMI equivalence, native export or listening acceptance claim.')


def verify(source, output):
    require(not output.exists(), 'Choose a fresh speech verification output')
    require(output.resolve().is_relative_to((ROOT / 'build').resolve()), 'Speech evidence must stay under ignored build/')
    data = source.read_bytes()
    initial = private_source_memory(data)
    dictionary = initial[0xf4e7] | initial[0xf4e8] << 8
    def word(address):
        return initial[address] | initial[address + 1] << 8
    pitch = dictionary + word(dictionary + 4)
    wave = dictionary + word(dictionary + 6)
    blend = wave + 4
    require(initial[blend + 1] & 7 in (2, 3), 'Expected the next descriptor to use waveform interpolation')
    variants = {'baseline': (None, None),
                'pitch-delta': (pitch + 1, (initial[pitch + 1] & 0xf0) | ((initial[pitch + 1] + 1) & 15)),
                'interpolated-wave-blend': (blend, initial[blend] ^ 0x10)}
    output.mkdir(parents=True)
    cases = {}
    for name, (address, value) in variants.items():
        candidate = bytearray(initial)
        if address is not None:
            candidate[address] = value
            require(sum(a != b for a, b in zip(initial, candidate)) == 1, 'Speech control must change exactly one encoded byte')
        case = verify_case(bytes(candidate), output / name)
        case['inputMemorySha256'] = digest(bytes(candidate))
        case['intervention'] = None if address is None else dict(address=address, before=initial[address], after=value)
        cases[name] = case
    for name in variants:
        if name != 'baseline':
            require(cases[name]['outputSequenceSha256'] != cases['baseline']['outputSequenceSha256'],
                    f'Speech intervention {name} did not change computed output')
    receipt = dict(schemaVersion=1, sourceSha256=digest(data), cases=cases,
                   tools={name: digest((Path(__file__).parent / name).read_bytes()) for name in ('speech.py', 'check-speech.py')})
    (output / 'verification.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/research/ghostbusters/Ghostbusters.sid')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.source, args.output), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(f'Ghostbusters speech verification: {error}')
