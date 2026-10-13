from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from deflektor_player import compute_writes


def fixture():
    fields = ('frequency pulse_word control attack_decay sustain_release remaining rest '
              'release_threshold detune pitch_index pwm_interval pwm_base pwm_elapsed '
              'pwm_step pwm_position pitch_selector pitch_wait pitch_position wave_selector '
              'wave_countdown wave_position score_pitch_selector score_pitch_countdown '
              'score_pitch_position resonance_selector resonance_countdown resonance_position '
              'glide_wait glide_remaining glide_flags glide_step').split()
    words = [0] * 256
    words[20], words[21] = 0x1234, 0x3456
    return dict(schemaVersion='sid-deflektor-player-v1', play_calls=6,
        initial_state=dict(globals=dict(play_flag=15, cutoff_low=0, cutoff_high=10,
                                        routing=0, mode_volume=15),
                           voices=[dict.fromkeys(fields, 0) for _ in range(3)]),
        score=dict(orders=[dict(voiceIndex=i, pointer=0, bytes=[0 if i == 0 else 1, 255]) for i in range(3)],
                   patterns=[dict(patternId=0, pointer=0, bytes=[128, 0, 4, 255]),
                             dict(patternId=1, pointer=0, bytes=[160, 4, 255])],
                   initMappingDefaults=dict(bytes=[0] * 24),
                   recordTable=dict(records=[dict(recordOffset=0, fields=[0, 8, 64, 5, 105, 2, 0, 0, 0],
                                                    contextual_resonance_selector=0)])),
        frequency_words=words, motion_table=[0] * 280, resonance_table=[0] * 257,
        wave_programs={}, score_pitch_programs={})


def group(writes, call):
    return [(w['address'], w['value']) for w in writes if w['tick'] == call]


class DeflektorPlayerTests(unittest.TestCase):
    def test_note_release_order_finite_stop_and_stopped_tail(self):
        result = compute_writes(fixture())
        self.assertFalse(any(w['phase'] == 'init' for w in result))
        first = [(0xd400, 0x34), (0xd401, 0x12), (0xd402, 0), (0xd403, 8),
                 (0xd404, 0x41), (0xd405, 5), (0xd406, 105),
                 (0xd415, 0), (0xd416, 10), (0xd417, 0), (0xd418, 15)]
        self.assertEqual([(0xd40b, 0), (0xd412, 0)] + first, group(result, 0))
        self.assertEqual(first, group(result, 1))
        released = list(first)
        released[4] = (0xd404, 0x40)
        self.assertEqual(released, group(result, 3))
        self.assertEqual([(0xd404, 0), (0xd40b, 0), (0xd412, 0)], group(result, 4))
        self.assertEqual([], group(result, 5))

    def test_global_row_edge_suppresses_writer_but_new_note_is_initialized(self):
        data = fixture()
        data['score']['patterns'][0]['bytes'] = [128, 0, 2, 1, 2, 255]
        result = compute_writes(data)
        self.assertEqual([], group(result, 2))
        self.assertEqual([(0xd400, 0x56), (0xd401, 0x34)], group(result, 3)[:2])

    def test_note_duration_and_pulse_edits_drive_output_without_mutating_input(self):
        baseline = fixture()
        changed = deepcopy(baseline)
        changed['score']['patterns'][0]['bytes'][1] = 1
        before = deepcopy(changed)
        self.assertEqual([(0xd400, 0x56), (0xd401, 0x34)], group(compute_writes(changed), 0)[2:4])
        self.assertEqual(before, changed)
        changed = fixture()
        changed['score']['patterns'][0]['bytes'][2] = 5
        changed['score']['patterns'][1]['bytes'][1] = 5
        self.assertEqual(11, len(group(compute_writes(changed), 4)))
        self.assertEqual([(0xd404, 0), (0xd40b, 0), (0xd412, 0)], group(compute_writes(changed), 5))
        changed = fixture()
        changed['score']['recordTable']['records'][0]['fields'][0] = 4
        changed['score']['recordTable']['records'][0]['fields'][6] = 21
        changed['motion_table'][:4] = [0x11, 2, 3, 0x24]
        self.assertEqual([(0xd402, 21), (0xd403, 1)], group(compute_writes(changed), 1)[2:4])

    def test_source_annotations_are_irrelevant_and_runtime_has_no_filesystem(self):
        data = fixture()
        expected = compute_writes(data)
        data['sourceEvidence'] = dict(sid='/absent/reference.sid', writes=[dict(value=255)])
        with patch('builtins.open', side_effect=AssertionError('File access')), \
             patch.object(Path, 'read_bytes', side_effect=AssertionError('Byte access')), \
             patch.object(Path, 'read_text', side_effect=AssertionError('Text access')):
            self.assertEqual(expected, compute_writes(data))

    def test_caps_invalid_state_and_unsupported_effects_reject(self):
        data = fixture()
        self.assertEqual([w for w in compute_writes(data) if w['tick'] < 4], compute_writes(data, calls=4))
        for count in (-1, True, 1.5, 100001):
            with self.subTest(calls=count), self.assertRaises(ValueError):
                compute_writes(data, calls=count)
        for key, value in [('frequency', -1), ('pwm_elapsed', 256)]:
            changed = deepcopy(data)
            changed['initial_state']['voices'][0][key] = value
            with self.subTest(field=key), self.assertRaises(ValueError):
                compute_writes(changed)
        changed = deepcopy(data)
        changed['score']['patterns'][0]['bytes'].insert(1, 0xb0)
        with self.assertRaises(ValueError):
            compute_writes(changed)

    def test_initial_row_state_requires_a_cold_score_start(self):
        for field in ('remaining', 'rest'):
            data = fixture()
            data['initial_state']['voices'][0][field] = 4
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'cold'):
                compute_writes(data, calls=1)

    def test_truncated_record_rejects_before_instrument_indexing(self):
        data = fixture()
        data['score']['recordTable']['records'][0]['fields'].pop()
        with self.assertRaisesRegex(ValueError, 'nine bytes'):
            compute_writes(data, calls=0)

    def test_program_selector_ids_do_not_coerce_boolean_or_float_values(self):
        program = dict(loop=False, stages=[dict(control_bits=128, duration=1),
                                           dict(control_bits=16, duration=1)])
        for key in (True, 1.5):
            data = fixture()
            data['wave_programs'] = {key: program}
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'selector'):
                compute_writes(data, calls=0)
        for key in (5, '5'):
            data = fixture()
            data['wave_programs'] = {key: program}
            with self.subTest(key=key):
                self.assertEqual([], compute_writes(data, calls=0))


if __name__ == '__main__':
    unittest.main()
