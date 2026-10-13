from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('shades_score', ROOT / 'scripts/describe-shades-score.py')
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)
SOURCE = ROOT / '.local/research/shades/Shades_filter_corrected.sid'


def example():
    order = {'patternIds': ['phrase'] * 3, 'instrument': 'example', 'transposeSemitones': [-6, 1, 1],
             'voice1HighNotesAbsolute': True, 'rowCount': 3, 'rowDurationCalls': 3,
             'timerHigh': 48, 'fade': {'kind': 'retain'}}
    return {'format': 'sid-shades-score-v1',
            'profile': {'clock': 'PAL', 'chip': 'MOS6581', 'timing': 'CIA1 Timer A'},
            'range': {'firstCall': 0, 'firstRowCall': 1, 'stopCall': 19},
            'instrumentBlocks': ['example'],
            'patterns': {'phrase': {'rows': [score.decode_row(value) for value in (0x32, 0x80, 0)]}},
            'orders': [deepcopy(order), deepcopy(order)]}


class ShadesScoreTests(unittest.TestCase):
    def test_rest_hold_and_pitched_gate_off_are_distinct(self):
        self.assertEqual({'kind': 'rest'}, score.decode_row(0))
        self.assertEqual({'kind': 'hold'}, score.decode_row(0x80))
        self.assertEqual({'kind': 'note', 'sourceNote': 45, 'gate': 'on'}, score.decode_row(45))
        self.assertEqual({'kind': 'note', 'sourceNote': 45, 'gate': 'off'}, score.decode_row(0xad))
        with self.assertRaisesRegex(ValueError, 'byte'):
            score.decode_row(256)

    def test_source_free_expansion_preserves_timing_and_voice_one_pitch_exception(self):
        description = example()
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('Source read')), \
                patch.object(Path, 'read_text', side_effect=AssertionError('Source read')):
            result = score.expand_score(description)
        self.assertEqual([0, 10], [row['call'] for row in result['selections']])
        first = result['commands'][:3]
        self.assertEqual([1, 1, 1], [row['call'] for row in first])
        self.assertEqual([50, 51, 51], [row['pitchTableIndex'] for row in first])
        self.assertEqual([4, 4, 4], [row['call'] for row in result['commands'][3:6]])
        self.assertEqual(['hold'] * 3, [row['kind'] for row in result['commands'][3:6]])
        self.assertEqual(['rest'] * 3, [row['kind'] for row in result['commands'][6:9]])

    def test_editing_semantic_pitch_and_gate_changes_consumption_without_source_annotations(self):
        original = example()
        edited = deepcopy(original)
        edited['patterns']['phrase']['rows'][0] = {'kind': 'note', 'sourceNote': 45, 'gate': 'off'}
        row = score.expand_score(edited)['commands'][0]
        self.assertEqual((39, 'off'), (row['pitchTableIndex'], row['gate']))
        self.assertNotEqual(score.expand_score(original), score.expand_score(edited))

    def test_unknown_commands_and_inconsistent_row_bounds_fail(self):
        description = example()
        description['patterns']['phrase']['rows'][1] = {'kind': 'slide', 'amount': 3}
        with self.assertRaisesRegex(ValueError, 'command'):
            score.expand_score(description)
        description = example()
        description['orders'][0]['rowCount'] = 4
        with self.assertRaisesRegex(ValueError, 'row'):
            score.expand_score(description)
        description = example()
        description['range']['stopCall'] -= 1
        with self.assertRaisesRegex(ValueError, 'range'):
            score.expand_score(description)

    def test_source_pin_precedes_decoding_or_execution(self):
        with patch.object(score, 'decode_source', side_effect=AssertionError('Decode before pin')), \
                patch.object(score, 'verify_execution', side_effect=AssertionError('Execute before pin')):
            with self.assertRaisesRegex(ValueError, 'pinned'):
                score.describe_score(bytes(124))

    def test_saved_json_expands_without_source_addresses_or_reads(self):
        description = json.loads((ROOT / 'songs/shades-score.json').read_text())
        expected = score.expand_score(description)
        for annotation in ('sourceEvidence', 'evidence', 'limits'):
            description.pop(annotation, None)
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('Source read')), \
                patch.object(Path, 'read_text', side_effect=AssertionError('Source read')):
            self.assertEqual(expected, score.expand_score(description))

    def test_lossless_evidence_accepts_an_arbitrary_fresh_output_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'structured-evidence'
            artifacts = {'rows.json': [{'call': 1, 'sourceValue': 0xad, 'gate': 'off'}]}
            score.write_evidence(output, artifacts, {'sourceSha256': 'example'})
            self.assertEqual(artifacts['rows.json'], json.loads((output / 'rows.json').read_text()))
            self.assertIn('rows.json', json.loads((output / 'receipt.json').read_text())['artifacts'])
            with self.assertRaisesRegex(ValueError, 'fresh'):
                score.write_evidence(output, artifacts, {})

    @unittest.skipUnless(SOURCE.exists(), 'Requires pinned local corrected Shades reference')
    def test_full_selected_form_matches_every_executed_score_consumption(self):
        result = score.describe_score(SOURCE.read_bytes())
        expanded = score.expand_score(result)
        self.assertEqual(24384, len(expanded['commands']))
        self.assertEqual(128, len(expanded['selections']))
        self.assertEqual(24385, result['range']['stopCall'])
        self.assertTrue(result['evidence']['completeConsumedEventsMatch'])
        self.assertEqual([2, 95], result['evidence']['resolvedPitchTableRange'])
        self.assertEqual(result, json.loads((ROOT / 'songs/shades-score.json').read_text()))


if __name__ == '__main__':
    unittest.main()
