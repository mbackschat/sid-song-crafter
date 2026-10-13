import gzip
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from rambo_player import compute_player


class RamboPlayerTest(unittest.TestCase):
    def description(self):
        return json.loads((ROOT / 'songs/rambo-loader.json').read_text())

    def test_complete_loader_matches_every_original_store_and_stays_stopped(self):
        description = json.loads((ROOT / 'songs/rambo-loader.json').read_text())
        expected = json.load(gzip.open(ROOT / 'evidence/rambo-form/complete40000/writes.json.gz', 'rt'))
        result = compute_player(description, calls=11000)
        projected = lambda rows: [(r['phase'], r['tick'], r['address'], r['value']) for r in rows]
        self.assertEqual(projected(expected), projected(result['writes']))
        self.assertEqual(result['activeMask'], 0)
        self.assertTrue(all(state['life'] == 0 for state in result['sounds']))
        self.assertEqual(max(r['tick'] for r in result['writes'] if r['phase'] == 'play'), 10814)

    def test_runtime_needs_only_editable_data_and_ignores_source_annotations(self):
        description = self.description()
        expected = compute_player(description, calls=64)['writes']
        description.pop('sourceEvidence')
        for node in description['program'].values():
            node.pop('sourceAddress', None)
            node.pop('sourceOpcode', None)
        with patch('builtins.open', side_effect=AssertionError('Runtime attempted file access')):
            self.assertEqual(compute_player(description, calls=64)['writes'], expected)

    def test_note_timing_and_instrument_delay_edits_match_independent_source_execution(self):
        from psid_audit import audit_psid
        source = (ROOT / '.local/rambo-source.sid').read_bytes()
        payload = int.from_bytes(source[6:8], 'big') + 2
        for kind in ('row-duration', 'frequency-delay'):
            with self.subTest(kind=kind):
                description = self.description()
                changed = bytearray(source)
                if kind == 'row-duration':
                    node = description['program'][description['voices'][0]['cursor']]
                    address, original, value = node['sourceAddress'] + 1, 50, 51
                    node['duration'] = value
                else:
                    address, original, value = 0x291e + 12, 50, 0
                    description['initialData'][1][12] = value
                offset = payload + address - 0x2000
                self.assertEqual(changed[offset], original)
                changed[offset] = value
                _, expected = audit_psid(bytes(changed), 64, profile='pal-banked', subtune=1)
                actual = compute_player(description, calls=64)['writes']
                project = lambda rows: [(r['phase'], r['tick'], r['address'], r['value']) for r in rows]
                self.assertEqual(project(expected), project(actual))
                self.assertNotEqual(actual, compute_player(self.description(), calls=64)['writes'])

    def test_invalid_data_and_unsupported_poke_aliases_are_rejected(self):
        for field, replacement in (('frequencyWords', [True]), ('initialSound', [[0] * 38] * 3),
                                   ('initialData', [[0] * 48] * 3)):
            with self.subTest(field=field):
                description = self.description()
                description[field] = replacement
                with self.assertRaises(ValueError):
                    compute_player(description, calls=1)
        description = self.description()
        node = next(node for node in description['program'].values() if node['kind'] == 'poke-data')
        node['offset'] = 65
        with self.assertRaisesRegex(ValueError, 'stack alias'):
            compute_player(description, calls=1)

    def test_write_data_rejects_banks_that_overwrite_duration_tables(self):
        description = self.description()
        node = next(node for node in description['program'].values() if node['kind'] == 'write-data')
        description['dataBanks'][node['dataId']] += [0] * 20
        with self.assertRaisesRegex(ValueError, 'Invalid write-data data-bank width'):
            compute_player(description, calls=1)


if __name__ == '__main__':
    unittest.main()
