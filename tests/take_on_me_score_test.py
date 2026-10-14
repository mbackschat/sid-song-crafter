"""Guard the contextual Take On Me score grammar and its countdown scheduler."""

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('take_on_me_score', ROOT / 'scripts/studies/take-on-me/score.py')
score = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(score)


def example(orders=None, rows=None):
    return {
        'schemaVersion': 1,
        'dividerReloads': [0, 0],
        'initialDividers': [0, 0],
        'orders': [{'address': 0x2000 + voice * 16, 'bytes': orders or [0, 255, 0]} for voice in range(3)],
        'patterns': {'0': {'address': 0x2100, 'rows': rows or [{'durationUnits': 1, 'note': 24}]}},
        'initialVoices': [dict(remaining=1, orderCursor=0, repeat=0, transpose=0,
                              patternCursor=0, instrument=0, durationTicks=0,
                              glideStepLow=0, glideStepHigh=0, baseNote=0,
                              glideTarget=0, arpeggio=0) for _ in range(3)],
    }


class TakeOnMeScoreTest(unittest.TestCase):
    def test_repeat_counter_replays_pattern_before_advancing_order(self):
        result = score.expand(example([194, 0, 0, 255, 1]), 9)
        rows = [row for row in result['rows'] if row['voice'] == 0]
        self.assertEqual([row['tick'] for row in rows], [0, 2, 4, 6, 8])
        self.assertEqual([row['state']['orderCursor'] for row in rows], [1, 1, 2, 3, 2])
        self.assertEqual([row['state']['repeat'] for row in rows[:3]], [1, 0, 0])
        self.assertEqual(result['wraps'][0]['tick'], 8)

    def test_transpose_and_pattern_arpeggio_commands_use_distinct_contexts(self):
        result = score.expand(example([130, 0, 255, 1], [dict(arpeggio=3, instrument=2, durationUnits=1, note=24)]), 1)
        row = result['rows'][-1]
        self.assertEqual(row['state']['baseNote'], 26)
        self.assertEqual(row['state']['arpeggio'], 3)
        self.assertEqual(row['state']['instrument'], 2)
        self.assertEqual(row['state']['durationTicks'], 2)
        self.assertEqual([r['value'] for r in result['reads'] if r['voice'] == 0 and r['pc'] in (0x10ec, 0x10f5, 0x10fb, 0x1107, 0x1114)], [254, 3, 194, 129, 24])

    def test_zero_duration_requires_a_full_byte_countdown(self):
        result = score.expand(example(rows=[dict(durationUnits=0, note=24)]), 257)
        self.assertEqual([row['tick'] for row in result['rows'] if row['voice'] == 0], [0, 256])

    def test_long_duration_requires_instrument_context_to_avoid_command_alias(self):
        with self.assertRaisesRegex(ValueError, 'instrument context'):
            score.encode_rows([dict(durationUnits=64, note=24)])
        values, _ = score.encode_rows([dict(instrument=2, durationUnits=127, note=24)])
        self.assertEqual(values, [194, 255, 24, 255])

    def test_signed_divider_underflow_controls_row_cadence(self):
        value = example()
        value['dividerReloads'] = [1, 1]
        result = score.expand(value, 12)
        self.assertEqual([row['tick'] for row in result['rows'] if row['voice'] == 0], [1, 9])

    def test_glide_target_addition_retains_first_note_carry(self):
        result = score.expand(example([159, 0, 255, 1], [dict(durationUnits=1, glide=dict(stepWord=258, note=250, target=24))]), 1)
        row = result['rows'][-1]
        self.assertEqual(row['state']['baseNote'], 25)
        self.assertEqual(row['state']['glideTarget'], 56)
        self.assertEqual(row['state']['glideStepLow'], 2)
        self.assertEqual(row['state']['glideStepHigh'], 1)
        self.assertEqual(row['glideActive'], 1)

    def test_duration_edit_moves_later_rows_without_changing_other_voices(self):
        value = example()
        changed = deepcopy(value)
        changed['patterns']['1'] = deepcopy(value['patterns']['0'])
        changed['patterns']['1']['rows'][0]['durationUnits'] = 2
        changed['orders'][0]['bytes'][0] = 1
        before, after = score.expand(value, 5), score.expand(changed, 5)
        self.assertEqual([row['tick'] for row in after['rows'] if row['voice'] == 0], [0, 4])
        self.assertEqual([row for row in before['rows'] if row['voice'] != 0], [row for row in after['rows'] if row['voice'] != 0])

    def test_order_stop_ends_the_current_call_before_lower_voices(self):
        value = example()
        value['orders'][2]['bytes'] = [254]
        result = score.expand(value, 4)
        self.assertEqual(result['rows'], [])
        self.assertEqual(result['stops'], [dict(tick=0, voice=2)])
        self.assertTrue(all(not state['active'] for state in result['returns']))


if __name__ == '__main__':
    unittest.main()
