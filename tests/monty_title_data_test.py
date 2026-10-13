import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('prepare_monty_title', ROOT / 'scripts/prepare-monty-title.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
SOURCE = ROOT / '.local/monty-source.sid'


def fixture():
    memory = [0] * 65536
    for address, size in prepare.ORDER_EXTENTS:
        memory[address:address + size] = [0] * (size - 1) + [255]
    memory[prepare.PATTERN_LOW_BASE] = 0
    memory[prepare.PATTERN_HIGH_BASE] = 0x90
    memory[0x9000:0x9007] = [0x83, 2, 19, 0x43, 3, 20, 255]
    return memory


class MontyTitleExtractionGuardsTest(unittest.TestCase):
    def test_source_pin_rejects_before_any_cpu_execution(self):
        with patch.object(prepare, 'audit_psid', side_effect=AssertionError('Must reject before CPU')):
            with self.assertRaisesRegex(ValueError, 'pinned Monty archive'):
                prepare.extract_data(b'wrong source')

    def test_score_extracts_only_referenced_rows_with_native_operand_sizes(self):
        score, locations = prepare.extract_score(fixture(), 0x8000, 0x95c0)
        self.assertEqual(3, len(score['orders']))
        self.assertEqual([dict(pattern_id=0, bytes=[0x83, 2, 19, 0x43, 3, 20, 255])], score['patterns'])
        self.assertEqual(0x9000, locations['patterns'][0]['address'])
        self.assertEqual(7, locations['patterns'][0]['bytes'])

    def test_score_guards_order_exit_pointer_extent_and_missing_pattern_terminator(self):
        memory = fixture()
        memory[prepare.ORDER_EXTENTS[0][0]] = 254
        with self.assertRaisesRegex(ValueError, 'FE'):
            prepare.extract_score(memory, 0x8000, 0x95c0)
        memory = fixture()
        memory[prepare.PATTERN_HIGH_BASE] = 0x70
        with self.assertRaisesRegex(ValueError, 'payload'):
            prepare.extract_score(memory, 0x8000, 0x95c0)
        memory = fixture()
        memory[0x9000:0x9100] = [0x40] * 256
        with self.assertRaisesRegex(ValueError, 'terminate'):
            prepare.extract_score(memory, 0x8000, 0x95c0)
        memory = fixture()
        memory[0x9000:0x9100] = [0x40] * 254 + [0x80, 1]
        with self.assertRaisesRegex(ValueError, 'cursor'):
            prepare.extract_score(memory, 0x8000, 0x95c0)

    def test_alias_bindings_are_named_bytes_at_actual_native_offsets(self):
        self.assertEqual([
            dict(offset=208, voice_index=0, field='voice_control'),
            dict(offset=209, voice_index=1, field='voice_control'),
            dict(offset=210, voice_index=2, field='voice_control'),
            dict(offset=211, voice_index=0, field='note'),
            dict(offset=232, voice_index=0, field='pulse_direction'),
            dict(offset=233, voice_index=1, field='pulse_direction'),
        ], prepare.frequency_alias_bindings())

    def test_fresh_output_and_check_mode_preserve_existing_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'title.json'
            data = {'format': 'test', 'play_calls': 10}
            prepare.write_description(path, data)
            original = path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'fresh'):
                prepare.write_description(path, data)
            prepare.check_description(path, data)
            with self.assertRaisesRegex(ValueError, 'differs'):
                prepare.check_description(path, {'format': 'test', 'play_calls': 11})
            self.assertEqual(original, path.read_bytes())


@unittest.skipUnless(SOURCE.exists(), 'Requires the pinned local Monty SID')
class MontyPinnedTitleDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = SOURCE.read_bytes()
        cls.description = prepare.extract_data(cls.raw)

    def test_extraction_retains_complete_score_programs_and_cold_named_state(self):
        data = self.description
        self.assertEqual(('monty-editable-title-v1', 40000), (data['format'], data['play_calls']))
        self.assertEqual((3, 58, 20, 96), (len(data['score']['orders']), len(data['score']['patterns']),
                                          len(data['instruments']), len(data['frequency_words'])))
        state = data['initial_state']
        self.assertEqual(dict(tempo_countdown=0, tempo_reload=1, counter=250, status=64,
                              mode_volume=15, sfx_priority=0, sfx_flags=255, output_enable=255), state['globals'])
        self.assertEqual([0, 1, 29], [v['pulse_delay'] for v in state['voices']])
        self.assertEqual([1, 0, 0], [v['pulse_direction'] for v in state['voices']])
        self.assertEqual([0x3e08, 0x09c4, 0x3426], [v['held_frequency'] for v in state['voices']])
        self.assertEqual([65] * 3, [v['voice_control'] for v in state['voices']])
        self.assertEqual(0x0ba0, data['instruments'][12]['pulse_word'])
        self.assertEqual(231, data['instruments'][12]['pulse_value'])
        self.assertEqual(2, data['instruments'][12]['effects'])
        self.assertEqual(165, data['sourceEvidence']['initialization']['cycles'])

    def test_source_attribution_and_runtime_numeric_contract_stay_separate(self):
        evidence = self.description['sourceEvidence']
        self.assertEqual(prepare.SOURCE_SHA256, evidence['sourceSha256'])
        self.assertEqual('Rob Hubbard', evidence['musicCredit'])
        self.assertEqual('Charles Williams', evidence['inspiration']['artist'])
        self.assertEqual(1, evidence['inspiration']['subtune'])
        self.assertNotIn('payload', self.description)
        self.assertNotIn('ram', self.description)
        self.assertNotIn('writes', self.description)
        for binding in self.description['frequency_alias_bindings']:
            self.assertEqual({'offset', 'voice_index', 'field'}, set(binding))
        self.assertEqual(self.raw, SOURCE.read_bytes())

    def test_cold_state_and_initialization_store_guards_reject_incomplete_observation(self):
        with patch.object(prepare, 'audit_psid', return_value=({'initCycles': 165}, [])):
            with self.assertRaisesRegex(ValueError, 'cold state'):
                prepare.extract_data(self.raw)
        native = prepare.audit_psid
        def corrupted_init(*args, **kwargs):
            report, stores = native(*args, **kwargs)
            stores[0]['value'] = 1
            return report, stores
        with patch.object(prepare, 'audit_psid', side_effect=corrupted_init):
            with self.assertRaisesRegex(ValueError, 'initialization stores'):
                prepare.extract_data(self.raw)


if __name__ == '__main__':
    unittest.main()
