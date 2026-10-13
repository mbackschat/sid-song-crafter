import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from deflektor_score import expand_score


class DeflektorScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = json.loads((ROOT / 'evidence/deflektor-form/full40000/tables.json').read_text())

    def test_complete_title_matches_executed_consumption_and_stop(self):
        path = ROOT / 'evidence/deflektor-form/full40000/events.json.gz'
        raw = path.read_bytes()
        self.assertEqual('776c2aaa1effe25b1a70dc53630297b2d90961534db8f5febf4a232d59b4748a',
                         hashlib.sha256(raw).hexdigest())
        events = json.loads(gzip.decompress(raw))
        actual = expand_score(self.tables, calls=40000)
        comparisons = [
            ('reads', ('orderRead', 'patternRead'),
             ('kind', 'call', 'voiceIndex', 'context', 'sourceAddress', 'sourceValue')),
            ('selections', ('patternSelection',), ('call', 'voiceIndex', 'patternId', 'patternPointer')),
            ('rows', ('rowReload',), ('call', 'voiceIndex', 'rowKind', 'value')),
            ('notes', ('noteSetup',), ('call', 'voiceIndex', 'sourceNote', 'transpose', 'pitchIndex')),
            ('instruments', ('instrumentSelection',), ('call', 'voiceIndex', 'slot', 'recordOffset', 'fields')),
        ]
        for name, kinds, fields in comparisons:
            with self.subTest(component=name):
                expected = [tuple(row[key] for key in fields) for row in events if row['kind'] in kinds]
                self.assertEqual(expected, [tuple(row[key] for key in fields) for row in actual[name]])
        self.assertEqual(8480, actual['firstStopCall'])
        self.assertFalse(any(row['call'] >= 8480 for row in actual['rows']))

    def test_editable_note_changes_pitch_without_changing_schedule_or_input(self):
        original = copy.deepcopy(self.tables)
        baseline = expand_score(original, calls=64)
        edited = copy.deepcopy(original)
        first = baseline['notes'][0]
        selection = next(row for row in baseline['selections'] if row['voiceIndex'] == first['voiceIndex'])
        pattern = next(row for row in edited['patterns'] if row['patternId'] == selection['patternId'])
        read = next(row for row in baseline['reads'] if row['voiceIndex'] == first['voiceIndex']
                    and row['context'] == 'token' and row['sourceValue'] < 128)
        pattern['bytes'][read['sourceAddress'] - pattern['pointer']] += 1
        changed = expand_score(edited, calls=64)
        self.assertEqual(baseline['rows'], changed['rows'])
        self.assertEqual((first['pitchIndex'] + 1) & 255, changed['notes'][0]['pitchIndex'])
        self.assertEqual(self.tables, original)

    def test_call_limit_does_not_invent_a_stop(self):
        self.assertIsNone(expand_score(self.tables, calls=8480)['firstStopCall'])
        self.assertEqual(8480, expand_score(self.tables, calls=8481)['firstStopCall'])

    def test_operations_preserve_effect_instrument_note_row_consumption_order(self):
        actual = expand_score(self.tables, calls=1281)
        operations = [row for row in actual['operations']
                      if row['call'] == 1280 and row['voiceIndex'] == 2]
        self.assertEqual([
            dict(operation='command', call=1280, voiceIndex=2, sourceCommand=0xa8,
                 kind='repeatTotal', value=8),
            dict(operation='command', call=1280, voiceIndex=2, sourceCommand=0x95,
                 kind='opaqueSingleByteEffect'),
            dict(operation='instrument', call=1280, voiceIndex=2, slot=20,
                 recordOffset=36, fields=[3, 8, 0, 9, 10, 2, 85, 0, 10]),
            dict(operation='note', call=1280, voiceIndex=2, sourceNote=42,
                 transpose=10, pitchIndex=72),
            dict(operation='row', call=1280, voiceIndex=2, rowKind='note', value=10),
        ], operations)

    def test_operations_preserve_legacy_categories_voice_order_and_immediate_stop(self):
        actual = expand_score(self.tables, calls=40000)
        operations = actual['operations']
        for operation, category in (('command', 'commands'), ('instrument', 'instruments'),
                                    ('note', 'notes'), ('row', 'rows')):
            with self.subTest(operation=operation):
                projected = [{key: value for key, value in row.items() if key != 'operation'}
                             for row in operations if row['operation'] == operation]
                self.assertEqual(actual[category], projected)
        self.assertEqual(sorted((row['call'], row['voiceIndex']) for row in operations),
                         [(row['call'], row['voiceIndex']) for row in operations])
        self.assertEqual([dict(operation='stop', call=8480, voiceIndex=0)],
                         [row for row in operations if row['call'] >= 8480])
        self.assertEqual('stop', operations[-1]['operation'])

    def test_operation_lists_are_detached_from_input_and_legacy_events(self):
        tables = copy.deepcopy(self.tables)
        tables['patterns'] = [dict(patternId=0, pointer=0x5000,
                                  bytes=[0xc0, 1, 2, 3, 0x80, 12, 1, 255])]
        tables['orders'] = [dict(voiceIndex=voice, pointer=0x4000 + voice * 2,
                                bytes=[0, 255]) for voice in range(3)]
        original = copy.deepcopy(tables)
        actual = expand_score(tables, calls=1)
        expected_instruments = copy.deepcopy(actual['instruments'])
        expected_commands = copy.deepcopy(actual['commands'])
        for row in actual['operations']:
            if row['operation'] == 'instrument':
                row['fields'][0] ^= 255
            elif row['operation'] == 'command' and 'arguments' in row:
                row['arguments'][0] ^= 255
        self.assertEqual(original, tables)
        self.assertEqual(expected_instruments, actual['instruments'])
        self.assertEqual(expected_commands, actual['commands'])

    def test_zero_duration_is_rejected_instead_of_guessing_one_call(self):
        edited = copy.deepcopy(self.tables)
        first = next(row for row in expand_score(edited, calls=1)['reads'] if row['context'] == 'noteDuration')
        pattern = next(row for row in edited['patterns']
                       if row['pointer'] <= first['sourceAddress'] < row['pointer'] + len(row['bytes']))
        pattern['bytes'][first['sourceAddress'] - pattern['pointer']] = 0
        with self.assertRaisesRegex(ValueError, 'zero duration'):
            expand_score(edited, calls=1)

    def test_duplicate_ids_and_invalid_bytes_are_rejected(self):
        duplicate = copy.deepcopy(self.tables)
        duplicate['patterns'].append(duplicate['patterns'][0])
        with self.assertRaisesRegex(ValueError, 'Duplicate pattern'):
            expand_score(duplicate, calls=1)
        invalid = copy.deepcopy(self.tables)
        invalid['orders'][0]['bytes'][0] = 256
        with self.assertRaisesRegex(ValueError, 'byte'):
            expand_score(invalid, calls=1)

    def test_negative_or_boolean_call_limits_are_rejected(self):
        for calls in (-1, True):
            with self.subTest(calls=calls), self.assertRaises(ValueError):
                expand_score(self.tables, calls=calls)


if __name__ == '__main__':
    unittest.main()
