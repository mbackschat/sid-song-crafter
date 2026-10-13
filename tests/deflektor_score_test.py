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
