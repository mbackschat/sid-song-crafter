"""Check independent numeric scheduling against retained title observations."""

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from monty_title_score import expand_score


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_equal(actual, expected, name):
    if actual == expected:
        return
    if isinstance(actual, list) and isinstance(expected, list):
        for index, (left, right) in enumerate(zip(actual, expected)):
            if left != right:
                raise AssertionError(f'{name}[{index}]: numeric {left!r}; retained {right!r}')
        raise AssertionError(f'{name} lengths: numeric {len(actual)}; retained {len(expected)}')
    raise AssertionError(f'{name}: numeric {actual!r}; retained {expected!r}')


def main():
    score_path = ROOT / 'songs/monty-title-source.json'
    oracle_path = ROOT / 'evidence/monty-form/full40000/observations.json.gz'
    numeric = json.loads(score_path.read_text())
    oracle = json.loads(gzip.decompress(oracle_path.read_bytes()))
    expanded = expand_score(numeric['score'], calls=oracle['actualProcessedCalls'],
                            initial_state=numeric['initial_state'])
    provenance = numeric['sourceEvidence']
    assert_equal(provenance['sourceSha256'], oracle['provenance']['sourceSha256'], 'Source pin')
    pattern_addresses = {row['pattern_id']: row['address'] for row in provenance['scoreMappings']['patterns']}
    order_addresses = {row['voice_index']: row['address'] for row in provenance['scoreMappings']['orders']}
    read_kinds = {'orderRead', 'rowControlRead', 'instrumentOrPortamentoRead', 'pitchRead', 'patternEndPeek'}
    predicted_reads = [
        (row['call'], row['voice_index'], row['kind'],
         (order_addresses[row['voice_index']] if row['kind'] == 'orderRead'
          else pattern_addresses[row['pattern_id']]) + row['offset'], row['value'])
        for row in expanded['reads']]
    retained_reads = [(row['call'], row['x'], row['kind'], row['sourceAddress'], row['value'])
                      for row in oracle['events'] if row['kind'] in read_kinds]
    assert_equal(predicted_reads, retained_reads, 'Complete consumed-byte stream')

    operations = expanded['operations']
    fields = dict(order_cursor='orderCursor', pattern_cursor='patternCursor', remaining='remaining',
                  control='savedControl', note='note', instrument_index='instrument', portamento='portamento')

    def numeric_state(row):
        return tuple(row[field] for field in fields)

    def retained_state(row, **overrides):
        state = {field: row['state'][native][row['x']] for field, native in fields.items()}
        state.update(overrides)
        return tuple(state[field] for field in fields)

    def projected_actions(kind, predicate=lambda row: True):
        return [(row['call'], row['voice_index'], numeric_state(row)) for row in operations
                if row['operation'] == kind and predicate(row)]

    initializers = projected_actions('initialize')
    retained_initializers = [(row['call'], row['x'], retained_state(row))
                             for row in oracle['events'] if row['kind'] == 'initializerInstrument']
    assert_equal(initializers, retained_initializers, 'Complete initializer sequence state')
    assert_equal(projected_actions('initialize', lambda row: row['append']),
                 [(row['call'], row['x'], retained_state(row))
                  for row in oracle['events'] if row['kind'] == 'appendBranch'], 'Append branches')
    assert_equal(projected_actions('instrument'),
                 [(row['call'], row['x'], retained_state(row, instrument_index=row['a']))
                  for row in oracle['events'] if row['kind'] == 'instrumentSet'], 'Instrument assignments')
    assert_equal(projected_actions('note'),
                 [(row['call'], row['x'], retained_state(row, note=row['value']))
                  for row in oracle['events'] if row['kind'] == 'pitchRead'], 'Pitch assignments')
    assert_equal(projected_actions('row'),
                 [(row['call'], row['x'], retained_state(row, control=row['value'],
                                                       remaining=row['value'] & 31))
                  for row in oracle['events'] if row['kind'] == 'rowControlRead'], 'Rows')
    ends = projected_actions('navigation', lambda row: row.get('pattern_end', False))
    for kind in ('patternReset', 'orderAdvance'):
        expected = [(row['call'], row['x'], retained_state(row, pattern_cursor=0,
                      order_cursor=(row['state']['orderCursor'][row['x']] + 1) & 255))
                    for row in oracle['events'] if row['kind'] == kind]
        assert_equal(ends, expected, kind)
    assert_equal(projected_actions('navigation', lambda row: row.get('order_restart', False)),
                 [(row['call'], row['x'], retained_state(row, order_cursor=0, pattern_cursor=0, remaining=0))
                  for row in oracle['events'] if row['kind'] == 'orderRestart'], 'Order restart state')
    assert_equal(expanded['orderRestarts'],
                 [dict(call=row['call'], voice_index=row['x']) for row in oracle['events']
                  if row['kind'] == 'orderRestart'], 'Order restart calls')

    selections = [(row['call'], row['voice_index'], row['value']) for row in expanded['reads']
                  if row['kind'] == 'orderRead' and row['value'] != 255]
    for kind, key, shift in (('patternPointerLow', 'lowBase', 0),
                             ('patternPointerHigh', 'highBase', 8)):
        expected = [(call, voice, provenance['patternPointerBanks'][key] + pattern,
                     (pattern_addresses[pattern] >> shift) & 255) for call, voice, pattern in selections]
        actual = [(row['call'], row['x'], row['sourceAddress'], row['value']) for row in oracle['events']
                  if row['kind'] == kind]
        assert_equal(expected, actual, kind)

    calls = [row for row in operations if row['operation'] == 'call']
    assert_equal(len(calls), oracle['actualProcessedCalls'], 'Complete call count')
    globals_fields = dict(tempo_countdown='tempo', tempo_reload='tempoReload', counter='counter', status='status')
    for row in oracle['events'] + oracle['boundaryCheckpoints']:
        action = calls[row['call']]
        assert_equal(tuple(action[field] for field in globals_fields),
                     tuple(row['state'][native] for native in globals_fields.values()),
                     f'Globals at call {row["call"]}')
    final = oracle['boundaryCheckpoints'][-1]['state']
    assert_equal([tuple(voice[field] for field in fields) for voice in expanded['finalState']['voices']],
                 [tuple(final[native][index] for native in fields.values()) for index in range(3)],
                 'Final complete sequence state')
    sound_dispatch = [(row['call'], row['voice_index']) for row in operations
                      if row['operation'] in ('initialize', 'body')]
    assert_equal(sound_dispatch, [(call, voice) for call in range(len(calls)) for voice in (2, 1, 0)],
                 'Full call/voice sound dispatch')
    receipt = dict(schemaVersion=1, complete=True, playCalls=len(calls), consumedByteReads=len(predicted_reads),
                   rows=len(initializers), soundDispatches=len(sound_dispatch),
                   retainedHookCounts=dict(Counter(row['kind'] for row in oracle['events'])),
                   orderRestarts=expanded['orderRestarts'], finalState=expanded['finalState'],
                   pins=dict(sourceSha256=provenance['sourceSha256'], scoreSha256=sha(score_path),
                             observationsSha256=sha(oracle_path),
                             schedulerSha256=sha(ROOT / 'scripts/monty_title_score.py'),
                             checkerSha256=sha(Path(__file__))),
                   limits='Retained numeric score consumption and sequence/global state; no CPU rerun, sound programs, cycles, SID internal state or listening judgment.')
    output = Path(__file__).with_name('verification.json')
    output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
