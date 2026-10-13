import gzip
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from ghouls_player import GhoulsPlayer, compute_player


def projected(rows):
    return [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]


class GhoulsPlayerTest(unittest.TestCase):
    def description(self):
        return json.loads((ROOT / 'songs/ghouls.json').read_text())

    def test_complete_primary_and_poststop_filter_calls_match_original(self):
        description = self.description()
        calls = description['range']['auditCalls']
        self.assertGreaterEqual(calls, 13060)
        with gzip.open(ROOT / 'evidence/ghouls-form/full40000/audit.writes.json.gz', 'rt') as stream:
            original = json.load(stream)
        expected = [row for row in original if row['phase'] == 'init' or row['tick'] < calls]
        result = compute_player(description, calls=calls)
        self.assertEqual(projected(result['writes']), projected(expected))
        poststop = [row for row in result['writes'] if row['phase'] == 'play' and row['tick'] >= 12996]
        self.assertEqual([(row['tick'], row['address'], row['value']) for row in poststop],
                         [(call, address, 0) for call in range(12996, calls) for address in (0xd415, 0xd416)])

    def test_runtime_reads_only_editable_description(self):
        description = self.description()
        expected = compute_player(description, calls=128)['writes']
        description.pop('sourceEvidence', None)
        def strip_annotations(value):
            if isinstance(value, dict):
                return {key: strip_annotations(item) for key, item in value.items()
                        if key not in ('sourceAddress', 'sourceOpcode', 'sourceEvidence')}
            if isinstance(value, list):
                return [strip_annotations(item) for item in value]
            return value
        description = strip_annotations(description)
        with patch('builtins.open', side_effect=AssertionError('Numeric runtime attempted file access')):
            self.assertEqual(compute_player(description, calls=128)['writes'], expected)

    def test_description_rejects_invalid_state_lookup_and_profile(self):
        for field, value in [('pulseFallbacks', [0, True, 0]),
                             ('filterRestartPhases', [0, 0]),
                             ('frequencyWords', {'19': -1}),
                             ('profile', {})]:
            with self.subTest(field=field):
                description = self.description()
                description[field] = value
                with self.assertRaises(ValueError):
                    GhoulsPlayer(description)


if __name__ == '__main__':
    unittest.main()
