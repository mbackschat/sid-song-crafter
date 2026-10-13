"""Check the extracted numeric interface independently of source execution or synthesis."""

from collections import Counter
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
TABLE_LENGTHS = dict(records=19, vibrato_wait=20, onset_lengths=12, onset_waves=12,
                     pulse_slots=4, filter_programs=4, arpeggios=8, drums=2)
COMMAND_FIELDS = dict(note={'kind', 'sourceNote'}, glide={'kind', 'control', 'targetNote'},
                      sound={'kind', 'index'}, arpeggio={'kind', 'index'},
                      duration={'kind', 'reload'}, extendDuration={'kind', 'reload'},
                      routing={'kind', 'value'})


def validate(data):
    assert set(data['initial_state']) == {'globals', 'voices'}
    assert len(data['initial_state']['voices']) == 3
    assert all(set(v) == {'caller', 'pitch', 'sound_index', 'arpeggio_index'}
               for v in data['initial_state']['voices'])
    assert set(data['sid_init']) == {'cutoff_high', 'routing', 'mode_volume'}
    assert len(data['frequency_words']) == 257
    assert all(type(n) is int and 0 <= n <= 65535 for n in data['frequency_words'])
    assert {name: len(data[name]) for name in TABLE_LENGTHS} == TABLE_LENGTHS
    assert all(len(v) == 8 for v in data['pulse_slots'])
    assert all(len(v) == 10 for v in data['filter_programs'])
    assert all(len(v) == v[0] + 2 for v in data['arpeggios'])
    assert all(len(v['waves']) == 13 and len(v['pitch_values']) == 12 for v in data['drums'])
    assert data['play_calls'] == 36000 and len(data['rows']) == 8760
    counts = Counter()
    last = (-1, -3)
    for row in data['rows']:
        order = (row['call'], -row['voiceIndex'])
        assert last < order and 0 <= row['call'] < data['play_calls'] and row['voiceIndex'] in (0, 1, 2)
        last = order
        assert row['patchSetup'] in ('initialize', 'preserve') and 0 <= row['transpose'] <= 255
        assert len([c for c in row['commands'] if c['kind'] == 'note']) == 1
        for command in row['commands']:
            kind = command['kind']
            counts[kind] += 1
            assert kind in COMMAND_FIELDS and set(command) == COMMAND_FIELDS[kind]
            assert all(type(v) is int and 0 <= v <= 255 for k, v in command.items() if k != 'kind')
            if kind == 'note':
                assert ((command['sourceNote'] + row['transpose']) & 255) == row['sourceEvidence']['pitchIndex']
            elif kind == 'sound':
                assert command['index'] < len(data['records'])
            elif kind == 'arpeggio':
                assert command['index'] < len(data['arpeggios'])
    return dict(sorted(counts.items()))


def runtime(value):
    if isinstance(value, dict):
        return {k: runtime(v) for k, v in value.items() if k != 'sourceEvidence'}
    if isinstance(value, list):
        return [runtime(v) for v in value]
    return value


def fingerprint(path):
    return dict(path=str(path.relative_to(BASE)), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == '__main__':
    path = BASE / 'title-runtime.json'
    data = json.loads(path.read_bytes())
    counts = validate(data)
    mutations = {
        'missing-adjacent-slot256': dict(data, frequency_words=data['frequency_words'][:-1]),
        'wrong-same-call-voice-order': dict(data, rows=list(reversed(data['rows'][:3])) + data['rows'][3:]),
        'duplicate-runtime-initial-config': dict(data, initial_state=dict(data['initial_state'], initial_sid=data['sid_init'])),
    }
    for name, changed in mutations.items():
        try:
            validate(changed)
        except AssertionError:
            continue
        raise AssertionError(f'Negative control accepted: {name}')
    semantic = json.dumps(runtime(data), sort_keys=True, separators=(',', ':')).encode()
    receipt = dict(classification='Static numeric interface checks; no source CPU, events or register-ledger input',
                   data=fingerprint(path), extractor=fingerprint(BASE / 'extract.py'), checker=fingerprint(Path(__file__)),
                   runtimeSemanticSha256=hashlib.sha256(semantic).hexdigest(),
                   playCalls=data['play_calls'], rows=len(data['rows']), commandCounts=counts,
                   tableLengths=TABLE_LENGTHS, frequencyWordCount=257,
                   rowOrder='Unique call/voice positions, call ascending and source voice dispatch 2,1,0',
                   noteTransform='Every sourceNote+transpose uint8 sum equals the independent decoder pitchIndex annotation',
                   negativeControls=list(mutations),
                   limits=['Changing duration requires rescheduling later absolute row calls',
                           'Opaque frequency words87..256 are not inferred chromatic notes',
                           'Interface/transformation checks do not establish composed-model synthesis or audio'])
    with (BASE / 'interface-verification.json').open('x') as output:
        json.dump(receipt, output, indent=2)
        output.write('\n')
    print(json.dumps(receipt, indent=2))
