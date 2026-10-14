"""Guard the portable Billie Jean header grammar and shared score scheduler."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/studies/billie-jean'))
import billie_jean_score as score


def example(rows=None):
    initial = dict(orderCursor=0, patternCursor=0, remaining=0, transpose=0,
                   baseNote=25, instrumentOffset=8, holdFlag=0, patternIndex=0)
    return dict(schema='billie-jean-score-v1', rowDividerReload=2, initialDivider=0,
        orders=[dict(bytes=[0, 255]) for _ in range(3)],
        patterns={'0': dict(rows=rows or [dict(header=131, instrument=1, note=24)])},
        initialVoices=[deepcopy(initial) for _ in range(3)])


class BillieJeanScoreTest(unittest.TestCase):
    def test_header_duration_plus_one_uses_three_call_divider(self):
        result = score.expand(example(), 15)
        self.assertEqual([row['tick'] for row in result['rows'] if row['voice'] == 0], [2, 14])
        self.assertEqual(result['returns'][0]['divider'], 2)
        self.assertEqual(result['returns'][2]['voices'][0]['remaining'], 3)

    def test_duration_edit_changes_only_header_low_bits(self):
        value = example()
        row = value['patterns']['0']['rows'][0]
        edited = score.set_duration(row, 2)
        self.assertEqual(edited, dict(header=130, instrument=1, note=24))
        self.assertEqual(row['header'], 131)
        value['patterns']['0']['rows'][0] = edited
        self.assertEqual([row['tick'] for row in score.expand(value, 15)['rows'] if row['voice'] == 0], [2, 11])

    def test_duplicate_duration_or_kind_fields_reject_instead_of_becoming_ignored_edits(self):
        for field, value in (('duration', 2), ('kind', 'rest')):
            row = dict(header=131, instrument=1, note=24)
            row[field] = value
            with self.assertRaisesRegex(ValueError, 'Unknown row fields'):
                score.encode_rows([row])

    def test_zero_duration_is_one_divider_step(self):
        value = example([dict(header=128, instrument=1, note=24)])
        self.assertEqual([row['tick'] for row in score.expand(value, 9)['rows'] if row['voice'] == 0], [2, 5, 8])

    def test_rest_class_consumes_no_note_payload_and_retains_note_setup_fields(self):
        value = example([dict(header=195)])
        value['initialVoices'][0]['holdFlag'] = 32
        result = score.expand(value, 3)
        row = result['rows'][-1]
        self.assertEqual(row['kind'], 'rest')
        self.assertEqual(row['state']['baseNote'], 25)
        self.assertEqual(row['state']['instrumentOffset'], 8)
        self.assertEqual(row['state']['holdFlag'], 32)
        self.assertEqual([entry['field'] for entry in result['reads'] if entry['voice'] == 0],
            ['order', 'patternPointerLow', 'patternPointerHigh', 'rowHeader', 'followingByte'])
        with self.assertRaisesRegex(ValueError, 'Rest header'):
            score.encode_rows([dict(header=195, note=24)])

    def test_header_flags_own_payload_width_and_instrument_offset_wrap(self):
        value = example([dict(header=97, glideStep=5, glideTarget=30, note=24),
                         dict(header=129, instrument=35, note=25)])
        value['orders'][0]['bytes'] = [135, 0, 255]
        result = score.expand(value, 9)
        rows = [row for row in result['rows'] if row['voice'] == 0]
        self.assertEqual(rows[0]['command'], dict(header=97, glideStep=5, glideTarget=30, note=24))
        self.assertEqual(rows[0]['state']['baseNote'], 31)
        self.assertEqual(rows[0]['state']['holdFlag'], 32)
        self.assertEqual(rows[1]['state']['instrumentOffset'], 24)
        self.assertEqual(rows[1]['rowIndex'], 1)

    def test_order_ff_resets_every_cursor_without_clearing_retained_transpose(self):
        value = example([dict(header=0, note=10)])
        for voice in value['initialVoices']:
            voice['transpose'] = 7
        result = score.expand(value, 6)
        self.assertEqual(result['wraps'], [dict(tick=5, voice=2)])
        self.assertEqual([voice['orderCursor'] for voice in result['returns'][5]['voices']], [1, 1, 1])
        self.assertTrue(all(voice['transpose'] == 7 for voice in result['returns'][5]['voices']))

    def test_source_addresses_only_label_observations_and_row_offsets_follow_edits(self):
        value = example([dict(header=129, instrument=1, note=24), dict(header=1, note=25)])
        changed = deepcopy(value)
        changed['orders'][0]['sourceAddress'] = 0x6000
        changed['patterns']['0']['sourceAddress'] = 0x7000
        original, edited = score.expand(value, 9), score.expand(changed, 9)
        self.assertEqual(original['returns'], edited['returns'])
        self.assertEqual(edited['rows'][3]['address'], 0x7003)
        self.assertEqual(value, example([dict(header=129, instrument=1, note=24), dict(header=1, note=25)]))

    def test_incomplete_flagged_payload_and_reserved_terminator_reject(self):
        for row in (dict(header=128, note=24), dict(header=64, note=24), dict(header=255)):
            with self.assertRaises(ValueError):
                score.encode_rows([row])


if __name__ == '__main__':
    unittest.main()
