"""Compare pure Ghostbusters sound stages with the shared original music oracle.

Only the isolated music wrapper executes here. Speech data, fetches and NMI
amplitude streams remain private and are outside this component proof.
"""

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
SOURCE_SHA = 'f7f05616972d7fd5ad31df91284edbf4e0917d39422f8d004d50b40501a0dcde'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sound = load_module('ghostbusters_numeric_sound', Path(__file__).with_name('programs.py'))


def source_ram(data):
    offset = int.from_bytes(data[6:8], 'big')
    load = int.from_bytes(data[8:10], 'big')
    payload = data[offset:]
    if not load:
        load, payload = int.from_bytes(payload[:2], 'little'), payload[2:]
    sound.require(load == 0x900d and load + len(payload) == 0xa835, 'Unexpected original source image')
    ram = [0] * 65536
    ram[load:load + len(payload)] = payload
    return ram, offset + (2 if int.from_bytes(data[8:10], 'big') == 0 else 0), load


def describe(data):
    ram, _, _ = source_ram(data)
    return dict(schema='ghostbusters-sound-v1', target=dict(clock='ntsc', sidModel='MOS6581',
        sidBase=0xd400, frameCycles=17095),
        patches={str(index): asdict(sound.Patch(*ram[0xa7ef + index * 8:0xa7ef + index * 8 + 6]))
            for index in range(9)},
        frequencies={str(index): ram[0xa1f4 + index * 2] | ram[0xa1f5 + index * 2] << 8
            for index in range(96)},
        volumePolicy=dict(autoNibble=15, subtractFrom=109, orderCursorVoice=0, halfVolume=False),
        sourceEvidence=dict(sha256=hashlib.sha256(data).hexdigest(), patchBase=0xa7ef, frequencyBase=0xa1f4),
        limits='Named port/control behavior only; no oscillator/envelope state, IRQ cadence, speech decoding or listening verdict.')


def execute(data, calls, oracle):
    _, _, scored = oracle.decode_source(data)
    contexts, paths, volume_pending = [], Counter(), []
    active, comparisons, last_controls = [], 0, [0, 0, 0]

    def inputs(ram, voice):
        return sound.VoiceInputs(ram[0x8b + voice], ram[0x8e + voice],
            ram[0x88 + voice], ram[0x91 + voice])

    def start(cpu, memory, kind):
        voice, ram = cpu.x, memory.data
        state = inputs(ram, voice)
        instrument = ram[0x94 + voice]
        patch = sound.Patch(*ram[0xa7ef + instrument * 8:0xa7ef + instrument * 8 + 6])
        bank = {}
        need_pitch = kind == 'onset' and not state.header & 64
        need_pair = kind == 'body' and patch.vibrato_shift and not (ram[0xe2] & 3 == 0 and state.remaining & 128)
        if need_pitch or need_pair:
            index = state.note & 127
            for note in (index, index + 1) if need_pair else (index,):
                address = 0xa1f4 + note * 2
                bank[note] = ram[address] | ram[address + 1] << 8
        phase, mute = ram[0xe2], ram[0x9594]
        result = sound.onset(state, patch, bank, voice, mute) if kind == 'onset' else \
            sound.body(state, patch, bank, voice, phase, mute)
        active[:] = [dict(kind=kind, call=memory.tick, voice=voice, physicalVoice=voice + 1,
            inputs=asdict(state), instrument=instrument, patch=asdict(patch), frequencies=bank,
            phase=phase, mute=mute, lastWrittenControlBefore=last_controls[voice],
            firstWrite=len(memory.writes), result=result)]

    def finish(memory):
        nonlocal comparisons
        context = active.pop()
        result = context.pop('result')
        first = context.pop('firstWrite')
        actual = [(row['address'], row['value']) for row in memory.writes[first:]]
        sound.require(actual == result.writes,
            f"Sound stores differ at {context['call']}/{context['physicalVoice']}/{context['kind']}: {actual} != {result.writes}")
        cached = memory.data[0x91 + context['voice']]
        sound.require(cached == result.cached_control, 'Original cached control differs')
        for address, value in actual:
            if address in (0xd404, 0xd40b, 0xd412):
                last_controls[(address - 0xd404) // 7] = value
        context.update(cachedControl=cached, writes=actual, path=result.path)
        contexts.append(context)
        paths[result.path] += 1
        comparisons += 1

    def observe(cpu, memory):
        nonlocal comparisons
        pc, ram = cpu.pc, memory.data
        if memory.phase != 'play':
            return
        if pc == 0x945c:
            address = (ram[0xe5] | ram[0xe6] << 8) + cpu.y
            volume_pending[:] = [dict(kind='volume', call=memory.tick, voice=cpu.x,
                physicalVoice=cpu.x + 1, packed=ram[address], orderCursorVoice0=ram[0x82],
                half=bool(ram[0x947c]), firstWrite=len(memory.writes))]
        elif pc == 0x9489:
            sound.require(bool(volume_pending), 'Original volume store lacked packed input')
            context = volume_pending.pop()
            expected = sound.volume_write(context['packed'] >> 4, context['orderCursorVoice0'], context['half'])
            actual = [(row['address'], row['value']) for row in memory.writes[context.pop('firstWrite'):]]
            sound.require(actual == expected, 'Original shared volume differs')
            context.update(writes=actual, path='volume')
            contexts.append(context)
            paths['volume'] += 1
            comparisons += 1
        if pc in (0x9496, 0x94b0):
            sound.require(not active, 'Sound onset overlapped another stage')
            start(cpu, memory, 'onset')
        elif pc == 0x94ff or pc == 0x951f and not active:
            start(cpu, memory, 'body')
        elif pc == 0x941a and cpu.x < 3 and not active:
            start(cpu, memory, 'body')
        elif pc == 0x958c and active:
            finish(memory)

    observed = oracle.observe_source(data, scored, calls, observer=observe)
    sound.require(not active and not volume_pending, 'Source sound stage did not reach a boundary')
    music_writes = [row for row in observed['writes'] if row['phase'] == 'play']
    covered = sum(len(context['writes']) for context in contexts)
    sound.require(covered == len(music_writes), 'Sound contexts did not partition all original music stores')
    return dict(contexts=contexts, writes=music_writes, boundaryComparisons=comparisons,
        originalInitStores=len(observed['writes']) - len(music_writes),
        paths=dict(paths), description=describe(data))


CONTROLS = (
    ('pulse-low', 0xa7ef, 0x40, 0x20, {0xd402, 0xd410}),
    ('sustain-release', 0xa7fb, 0x88, 0x84, {0xd40d}),
    ('vibrato-shift', 0xa834, 3, 2, {0xd400, 0xd401}),
    ('row-volume', 0xa60c, 0x61, 0x91, {0xd418}))


def verify(data, calls=128, controls=False, control_calls=1700, output=None, oracle=None):
    sound.require(hashlib.sha256(data).hexdigest() == SOURCE_SHA, 'Pinned source hash differs')
    sound.require(type(calls) is int and 1 <= calls <= 13961, 'Sound proof supports 1..13961 calls')
    if controls:
        sound.require(type(control_calls) is int and 1 <= control_calls <= calls, 'Control calls exceed baseline')
    if output is not None:
        sound.require(not output.exists(), 'Sound output exists; choose a fresh directory')
    if oracle is None:
        oracle = load_module('ghostbusters_source_form_oracle', Path(__file__).with_name('probe-form.py'))
    baseline = execute(data, calls, oracle)
    receipt = dict(schemaVersion=1, sourceSha256=SOURCE_SHA, playCalls=calls,
        boundaryComparisons=baseline['boundaryComparisons'], paths=baseline['paths'],
        originalInitStores=baseline['originalInitStores'], musicStores=len(baseline['writes']), controls=[],
        scope='Isolated original music wrapper and independent sound helper comparison; no speech execution, full-machine timing or musical verdict.')
    products = {'description.json': baseline['description'], 'contexts.json': baseline['contexts']}
    if controls:
        original = [(row['tick'], row['address'], row['value']) for row in baseline['writes'] if row['tick'] < control_calls]
        _, offset, load = source_ram(data)
        for name, address, before, after, ports in CONTROLS:
            changed = bytearray(data)
            position = offset + address - load
            sound.require(changed[position] == before, f'Control baseline byte differs: {name}')
            changed[position] = after
            checked = execute(bytes(changed), control_calls, oracle)
            edited = [(row['tick'], row['address'], row['value']) for row in checked['writes']]
            unchanged_original = [row for row in original if row[1] not in ports]
            unchanged_edited = [row for row in edited if row[1] not in ports]
            sound.require(unchanged_original == unchanged_edited, f'Control escaped declared ports: {name}')
            sound.require(original != edited, f'Control did not affect ordered output: {name}')
            control = dict(name=name, sourceAddress=address, before=before, after=after,
                calls=control_calls, changedSourceSha256=hashlib.sha256(changed).hexdigest(),
                boundaryComparisons=checked['boundaryComparisons'], onlyDeclaredPortsChanged=True,
                allowedPorts=sorted(ports))
            if name == 'vibrato-shift':
                eligible = next((context for context in baseline['contexts']
                    if context['kind'] == 'body' and context['call'] < control_calls and
                    context['instrument'] == 8 and context['inputs']['header'] & 31 >= 5 and
                    context['phase'] & 7 not in (0, 7) and context['lastWrittenControlBefore'] & 1), None)
                sound.require(eligible is not None, 'Vibrato control window lacks a gated eligible patch-8 body')
                counterpart = next(context for context in checked['contexts'] if context['kind'] == 'body'
                    and context['call'] == eligible['call'] and context['voice'] == eligible['voice'])
                sound.require(eligible['writes'] != counterpart['writes'], 'Eligible vibrato context did not change pitch')
                control['eligibleContext'] = {key: eligible[key] for key in
                    ('call', 'voice', 'physicalVoice', 'instrument', 'inputs', 'phase', 'lastWrittenControlBefore')}
                control['eligibleContext'].update(originalWrites=eligible['writes'], editedWrites=counterpart['writes'])
            receipt['controls'].append(control)
            products[f'control-{name}.contexts.json'] = checked['contexts']
            products[f'control-{name}.description.json'] = checked['description']
    if output is not None:
        output.mkdir(parents=True, exist_ok=False)
        for name, value in products.items():
            (output / name).write_text(json.dumps(value, separators=(',', ':')) + '\n')
        receipt['outputs'] = {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in products}
        (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/research/ghostbusters/Ghostbusters.sid')
    parser.add_argument('--calls', type=int, default=128)
    parser.add_argument('--controls', action='store_true')
    parser.add_argument('--control-calls', type=int, default=1700)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.source.read_bytes(), args.calls, args.controls, args.control_calls, args.output)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
