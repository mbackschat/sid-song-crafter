"""Verify title-selected record parameters, shared pulse storage and a pitch-alias fork."""

from dataclasses import replace
import gzip
import hashlib
import json
from pathlib import Path

from check import (HERE, ROOT, SOURCE_SHA, data, profile, fresh_memory, set_state,
                   word, instrument, voice_state, run_block, isolated_body, sha)
from model import VoiceState, initialize_note

observations_path = ROOT / 'build/monty-form/full40000/observations.json.gz'
ledger_path = ROOT / 'build/monty-form/full40000/audit.writes.json.gz'
observed = json.load(gzip.open(observations_path, 'rt'))
ledger = json.load(gzip.open(ledger_path, 'rt'))
initializers = [row for row in observed['events'] if row['kind'] == 'initializerInstrument']
first = {}
for event in initializers:
    first.setdefault(event['instrumentIndex'], event)
records = []
for index, event in sorted(first.items()):
    selected = [row for row in initializers if row['instrumentIndex'] == index]
    records.append(dict(index=index, address=event['recordAddress'], firstCall=event['call'],
        selectedVoices=sorted({row['x'] for row in selected}), initializerVisits=len(selected),
        firstExecutedValues=event['recordValues'],
        observedPulseWords=sorted({row['recordValues'][0] | row['recordValues'][1] << 8 for row in selected}),
        unchangedFields2Through7=all(row['recordValues'][2:] == event['recordValues'][2:] for row in selected)))
assert all(row['unchangedFields2Through7'] for row in records)
with (HERE / 'records.json').open('x') as output:
    json.dump(dict(sourceSha256=SOURCE_SHA, inputSha256=sha(observations_path), records=records,
        limits='Initializer visits are not note restarts; append setup also selects a record. Pulse words are actual snapshots of mutable table data, not fixed patch constants.'), output, indent=2)
    output.write('\n')

cases = []
for record_info in records:
    values = record_info['firstExecutedValues']
    memory = fresh_memory()
    memory.data[0x93b4:0x93bc] = values
    starting_record = instrument(memory.data, 0)
    for voice in range(3):
        state = VoiceState(19, 31, 30, 0x03a9, starting_record.waveform, 0, 0, 0)
        current = starting_record
        for counter in range(64):
            before_state, before_record = state, current
            result, cycles = isolated_body(voice, state, current, counter)
            cases.append(dict(record=record_info['index'], voice=voice, counter=counter,
                state=vars(before_state), instrument=vars(before_record), outputState=vars(result.state),
                outputInstrument=vars(result.instrument), orderedWrites=result.writes, sourceCycles=cycles))
            state, current = result.state, result.instrument

shared = instrument(fresh_memory().data, 0)
states = [VoiceState(19, 31, 30, 0x03a9, shared.waveform, 0, 0, 0) for _ in range(3)]
shared_rows = []
for counter in range(64):
    for voice in (2, 1, 0):
        before = shared
        result, cycles = isolated_body(voice, states[voice], shared, counter)
        shared_rows.append(dict(counter=counter, voice=voice, pulseBefore=before.pulse_word,
            pulseAfter=result.instrument.pulse_word, delayBefore=states[voice].pulse_delay,
            delayAfter=result.state.pulse_delay, directionAfter=result.state.pulse_direction,
            orderedWrites=result.writes, sourceCycles=cycles))
        states[voice], shared = result.state, result.instrument

aliases = []
for pitch_event in observed['events']:
    if pitch_event['kind'] != 'pitchRead' or pitch_event['value'] != 104:
        continue
    event = next(row for row in initializers if row['call'] == pitch_event['call'] and row['x'] == pitch_event['x'])
    controls = pitch_event['state']['voiceControl']
    expected_word = controls[0] | controls[1] << 8
    voice = event['x']
    actual = [row for row in ledger if row['phase'] == 'play' and row['tick'] == event['call']
              and 0xd400 + voice * 7 <= row['address'] <= 0xd406 + voice * 7]
    assert [(row['address'], row['value']) for row in actual[:2]] == [
        (0xd401 + voice * 7, expected_word >> 8), (0xd400 + voice * 7, expected_word & 255)]
    aliases.append(dict(call=event['call'], voice=voice, rawNote=104, frequencyAddress=0x84d0,
        voiceControlsBeforeLookup=controls, resolvedFrequencyWord=expected_word,
        instrumentIndex=event['instrumentIndex'], mutablePulseWord=event['recordValues'][0] | event['recordValues'][1] << 8))

forks = []
values = first[12]['recordValues']
for previous_control in (0x41, 0x81):
    memory = fresh_memory()
    memory.data[0x93b4:0x93bc] = values
    selected = instrument(memory.data, 0)
    state = VoiceState(19, 0xbf, 31, 0, previous_control, 6, 0, 0)
    set_state(memory.data, 1, state, selected)
    memory.data[0x84d0], memory.data[0x84d1] = 0x41, previous_control
    memory.data[4:6], memory.data[0x3002], memory.data[0x84d9] = [0, 0x30], 104, 255
    frequency = word(memory.data, 0x84d0)
    expected = initialize_note(state, selected, note=104, frequency_word=frequency)
    cycles, writes = run_block(memory, 1, 0x80ed, 0x8171, y=1)
    assert writes == expected.writes and voice_state(memory.data, 1) == expected.state
    forks.append(dict(previousVoiceControl=previous_control, heldFrequency=expected.state.held_frequency,
                      orderedWrites=writes, sourceCycles=cycles))
assert forks[0]['orderedWrites'][1:] == forks[1]['orderedWrites'][1:]
assert forks[0]['orderedWrites'][0] != forks[1]['orderedWrites'][0]

raw = (json.dumps(dict(titleRecordCases=cases, sharedRecordSequence=shared_rows,
    actualTitlePitchAliases=aliases, causalAliasFork=forks), separators=(',', ':')) + '\n').encode()
with (HERE / 'context-cases.json.gz').open('xb') as output:
    output.write(gzip.compress(raw, mtime=0))
result = dict(passed=True, sourceSha256=SOURCE_SHA, sourceBytesUnchanged=(ROOT / '.local/monty-source.sid').read_bytes() == data,
    titleSelectedRecordCount=len(records), sourceCases=len(cases) + len(shared_rows) + len(forks),
    titleRecordCases=len(cases), sharedRecordCases=len(shared_rows),
    actualTitleAliases=aliases, causalAliasFork=forks,
    inputs={str(path.relative_to(ROOT)): sha(path) for path in (observations_path, ledger_path)},
    modelSha256=sha(HERE / 'model.py'), checkerSha256=sha(HERE / 'check.py'), contextCheckerSha256=sha(Path(__file__)),
    contextCasesCompressedSha256=sha(HERE / 'context-cases.json.gz'), contextCasesDecodedSha256=hashlib.sha256(raw).hexdigest(),
    limits='Title-used parameter values checked in synthetic original blocks; the sequence is not the title score. Shared pulse width and separate voice delay/direction are exercised. Alias fork changes prior control context only and proves frequency sensitivity; it does not attribute all traversal differences or audible character.')
with (HERE / 'context-verification.json').open('x') as output:
    json.dump(result, output, indent=2)
    output.write('\n')
print(json.dumps({key: value for key, value in result.items() if key not in ('actualTitleAliases', 'causalAliasFork', 'inputs')}))
