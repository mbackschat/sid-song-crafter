"""Check numeric Monty components against bounded original blocks and retained inputs."""

from collections import Counter
from dataclasses import replace
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import BankedAuditMemory
from psid_profile import psid_profile
from verify_player import cpu_type
from model import Instrument, VoiceState, PitchLookups, initialize_note, advance_body

SOURCE_SHA = '528a7330817e4a0a0f75a505e9fe2444e07c5072ce5383ceaa89f183f0eee3ab'
data = (ROOT / '.local/monty-source.sid').read_bytes()
assert hashlib.sha256(data).hexdigest() == SOURCE_SHA
profile = psid_profile(data, profile='pal-banked', subtune=1)
TRACE = ROOT / 'build/monty-form/boundary.trace.json.gz'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def word(ram, address):
    return ram[address] | ram[address + 1] << 8


def voice_state(ram, voice):
    return VoiceState(ram[0x84d3 + voice], ram[0x84cd + voice], ram[0x84ca + voice],
        ram[0x84f2 + voice] | ram[0x84ef + voice] << 8, ram[0x84d0 + voice],
        ram[0x84e5 + voice], ram[0x84e8 + voice], ram[0x84f5 + voice])


def instrument(ram, index):
    address = 0x93b4 + ((index * 8) & 255)
    return Instrument(word(ram, address), *ram[address + 2:address + 8])


def pitches(ram, note, counter):
    offset = (note * 2) & 255
    octave_offset = (((note + (12 if counter & 1 else 0)) & 255) * 2) & 255
    return PitchLookups(word(ram, 0x8400 + offset), word(ram, 0x8402 + offset), word(ram, 0x8400 + octave_offset))


def fresh_memory():
    memory = BankedAuditMemory((0xd400,))
    memory.data[profile['loadAddress']:profile['endAddress']] = profile['payload']
    memory.phase, memory.tick = 'play', 0
    return memory


def set_state(ram, voice, state, record):
    for base, value in ((0x84d3, state.note), (0x84cd, state.control), (0x84ca, state.remaining),
                        (0x84f2, state.held_frequency & 255), (0x84ef, state.held_frequency >> 8),
                        (0x84d0, state.voice_control), (0x84e5, state.pulse_delay),
                        (0x84e8, state.pulse_direction), (0x84f5, state.portamento)):
        ram[base + voice] = value
    ram[0x84d6 + voice], ram[0x84c3], ram[0x84fd] = 0, voice * 7, 255
    ram[0x93b4:0x93bc] = [record.pulse_word & 255, record.pulse_word >> 8,
                         record.waveform, record.attack_decay, record.sustain_release,
                         record.vibrato_depth, record.pulse_value, record.effects]


def run_block(memory, voice, pc, stop, *, y=0):
    cpu = cpu_type()(memory=memory, pc=pc)
    cpu.x, cpu.y, cpu.sp, cpu.p = voice, y, 0xfd, 0x26
    while cpu.pc != stop:
        if cpu.processorCycles >= 19656:
            raise ValueError('Isolated source block exceeds the PAL budget')
        memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
        memory.instruction_cycle = cpu.processorCycles
        cpu.step()
    assert cpu.sp == 0xfd and cpu.x == voice
    return cpu.processorCycles, tuple((row['address'] - 0xd400 - voice * 7, row['value']) for row in memory.writes)


def isolated_body(voice, state, record, counter, *, release_check=False):
    memory = fresh_memory()
    set_state(memory.data, voice, state, record)
    memory.data[0x84fa] = counter
    lookups = pitches(memory.data, state.note, counter)
    cycles, writes = run_block(memory, voice, 0x8174 if release_check else 0x81a3, 0x8367)
    expected = advance_body(state, record, lookups, counter=counter, release_check=release_check)
    assert writes == expected.writes, (voice, state, record, counter, writes, expected)
    assert voice_state(memory.data, voice) == expected.state
    assert instrument(memory.data, 0) == expected.instrument
    return expected, cycles


def isolated_init(voice, state, record, note, append):
    memory = fresh_memory()
    set_state(memory.data, voice, state, record)
    memory.data[0x84d9] = 254 if append else 255
    memory.data[4:6] = [0, 0x30]
    memory.data[0x3002] = note
    frequency = word(memory.data, 0x8400 + ((note * 2) & 255))
    _, writes = run_block(memory, voice, 0x811b if append else 0x80ed, 0x8171, y=1)
    expected = initialize_note(state, record, append=True) if append else initialize_note(state, record, note=note, frequency_word=frequency)
    assert writes == expected.writes, (writes, expected)
    assert voice_state(memory.data, voice) == expected.state
    assert instrument(memory.data, 0) == expected.instrument
    return expected


def update_named_memory(ram, row):
    address = row.get('operandAddress')
    if address is None:
        return
    mnemonic = row['assembly'].split()[0]
    if mnemonic in ('STA', 'STX', 'STY'):
        ram[address] = row[{'STA': 'a', 'STX': 'x', 'STY': 'y'}[mnemonic]]
    elif mnemonic in ('INC', 'DEC'):
        ram[address] = (row['operandValueBefore'] + (1 if mnemonic == 'INC' else -1)) & 255


def retained_trace_check():
    trace = json.load(gzip.open(TRACE, 'rt'))
    memory = fresh_memory()
    ram, pending, counts, examples = memory.data, None, Counter(), []
    for row in trace['instructions']:
        pc = row['pc']
        if pc in (0x80ee, 0x8118, 0x81a3):
            assert pending is None
            voice = row['x']
            state = voice_state(ram, voice)
            index = ram[0x84d6 + voice]
            record = instrument(ram, index)
            if pc == 0x81a3:
                result = advance_body(state, record, pitches(ram, state.note, ram[0x84fa]), counter=ram[0x84fa])
                kind, stop = 'continuing-effects', 0x8367
            elif pc == 0x8118:
                result = initialize_note(state, record, append=True)
                kind, stop = 'append-setup', 0x8171
            else:
                note = row['operandValueBefore']
                result = initialize_note(state, record, note=note,
                    frequency_word=word(ram, 0x8400 + ((note * 2) & 255)))
                kind, stop = 'note-setup', 0x8171
            pending = dict(call=row['tick'], voice=voice, index=index, kind=kind,
                           inputState=state, inputInstrument=record, result=result, stop=stop, writes=[])
        if pending is not None and pc == pending['stop']:
            result, voice = pending['result'], pending['voice']
            assert tuple(pending['writes']) == result.writes, pending
            assert voice_state(ram, voice) == result.state, pending
            assert instrument(ram, pending['index']) == result.instrument, pending
            counts[pending['kind']] += 1
            if len(examples) < 12:
                examples.append(dict(call=pending['call'], voice=voice, instrumentIndex=pending['index'],
                    kind=pending['kind'], state=vars(pending['inputState']), instrument=vars(pending['inputInstrument']),
                    outputState=vars(result.state), outputInstrument=vars(result.instrument), orderedWrites=result.writes))
            pending = None
        if pending is not None and row['assembly'].split()[0] in ('STA', 'STX', 'STY') and 0xd400 <= row.get('operandAddress', 0) <= 0xd414:
            address = row['operandAddress'] - 0xd400 - pending['voice'] * 7
            value = row[{'STA': 'a', 'STX': 'x', 'STY': 'y'}[row['assembly'].split()[0]]]
            pending['writes'].append((address, value))
        update_named_memory(ram, row)
    assert pending is None
    return dict(matchedComponents=dict(counts), totalMatchedComponents=sum(counts.values()), examples=examples,
        memoryRecovery='Only explicit STA/STX/STY/INC/DEC changes recover named inputs from the recorded operand/CPU observations; no instruction execution or whole-RAM reconstruction is claimed.')


def main():
    state = VoiceState(19, 31, 30, 0x03a9, 0x41, 0, 0, 0)
    record = Instrument(0x0d80, 0x41, 0x48, 0x60, 2, 0x81, 0)
    count, maximum = 0, 0
    for voice, depth, counter, note in itertools.product(range(3), (0, 1, 2, 127, 128, 129, 255), (0, 1, 3, 4, 7, 255), (19, 86, 95, 104)):
        _, cycles = isolated_body(voice, replace(state, note=note), replace(record, vibrato_depth=depth), counter)
        count, maximum = count + 1, max(maximum, cycles)
    for voice, width, pulse, delay, direction in itertools.product(range(3), (0x07f0, 0x0800, 0x0df0, 0xfff0),
            (0, 1, 0x20, 0x5f, 0x81, 0xff), (0, 1, 128, 129, 255), (0, 1, 2, 255)):
        _, cycles = isolated_body(voice, replace(state, pulse_delay=delay, pulse_direction=direction),
                                  replace(record, pulse_word=width, pulse_value=pulse, vibrato_depth=0), 1)
        count, maximum = count + 1, max(maximum, cycles)
    for voice, effects, porta, held, remaining, waveform in itertools.product(range(3), range(8),
            (0, 0x80, 0x81, 0xfe, 0xff), (0, 1, 0xff, 0x100, 0xfff0), (0, 1, 30, 31), (0, 1, 0x41, 0x81)):
        _, cycles = isolated_body(voice, replace(state, held_frequency=held, remaining=remaining, voice_control=waveform, portamento=porta),
            replace(record, effects=effects, vibrato_depth=0, pulse_value=0), 1, release_check=True)
        count, maximum = count + 1, max(maximum, cycles)
    for voice, append, note in itertools.product(range(3), (False, True), (19, 86, 104, 255)):
        isolated_init(voice, replace(state, pulse_delay=7, pulse_direction=1), record, note, append)
        count += 1
    baseline, _ = isolated_body(1, state, record, 1)
    stationary, _ = isolated_body(1, state, replace(record, pulse_value=0), 1)
    assert tuple(pair for pair in baseline.writes if pair[0] not in (2, 3)) == stationary.writes
    assert stationary.instrument.pulse_word == record.pulse_word and stationary.state.pulse_delay == state.pulse_delay
    retained = retained_trace_check()
    result = dict(passed=True, sourceSha256=SOURCE_SHA, sourceBytesUnchanged=(ROOT / '.local/monty-source.sid').read_bytes() == data,
        isolatedCases=count, maximumIsolatedCycles=maximum, retainedTrace=retained,
        negativeControl=dict(parameter='pulse_value 0x81→0', onlyPulseStoresRemoved=True,
            baselineWrites=baseline.writes, stationaryWrites=stationary.writes,
            pulseStateUnchangedWhenDisabled=True),
        artifacts=dict(modelSha256=sha(HERE / 'model.py'), checkerSha256=sha(Path(__file__)), traceSha256=sha(TRACE)),
        tools={name: sha(ROOT / 'scripts' / name) for name in ('psid_audit.py', 'psid_profile.py', 'sid_audit_host.py', 'verify_player.py')},
        limits='Isolated original routine execution and retained512-call components only. Numeric frequency lookups are caller inputs; out-of-table state aliases, score scheduling, overlay flag, globals and full-title synthesis are not implemented by the helper. No reconstruction/render/listening or new40000-call execution.')
    with (HERE / 'verification.json').open('x') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'retainedTrace'}))


if __name__ == '__main__':
    main()
