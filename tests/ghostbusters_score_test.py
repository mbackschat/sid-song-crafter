from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class GhostbustersScoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('ghostbusters_score_test_subject',
            ROOT / 'scripts/studies/ghostbusters/score.py')
        cls.score = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.score)

    def example(self):
        return dict(schemaVersion=1,
            orders=[dict(patterns=[voice]) for voice in range(3)],
            patterns={'0': dict(rows=[dict(header=35, note=45), dict(header=35, note=46)]),
                      '1': dict(rows=[dict(header=63, note=23)]),
                      '2': dict(rows=[dict(header=63, note=47)])},
            initialState=dict(phase=0, voices=[dict(orderCursor=0, patternCursor=0,
                remaining=0, note=0, header=0, instrument=0) for _ in range(3)]))

    def test_header_owns_duration_and_exact_payload_width(self):
        values, offsets = self.score.encode_rows([
            dict(header=0xc4), dict(header=0x85, note=45, parameter=dict(volume=6, instrument=1)),
            dict(header=0x26, note=46)])
        self.assertEqual(values, [0xc4, 0x85, 45, 0x61, 0x26, 46, 255])
        self.assertEqual(offsets, [0, 1, 4])
        for row in (dict(header=0xff), dict(header=0x85, note=45),
                    dict(header=0x40, note=45), dict(header=5, note=45, duration=5),
                    dict(header=5, note=96), dict(header=0x85, note=45, parameter=dict(volume=6, instrument=9))):
            with self.subTest(row=row), self.assertRaises(ValueError):
                self.score.encode_rows([row])

    def test_duration_plus_one_and_quarter_phase_define_next_row(self):
        before = self.score.expand(self.example(), 25)
        changed = self.example()
        changed['patterns']['0']['rows'][0] = self.score.set_duration(changed['patterns']['0']['rows'][0], 4)
        after = self.score.expand(changed, 25)
        self.assertEqual([row['tick'] for row in before['rows'] if row['voice'] == 0], [0, 16])
        self.assertEqual([row['tick'] for row in after['rows'] if row['voice'] == 0], [0, 20])
        self.assertEqual([row for row in before['rows'] if row['voice'] != 0],
                         [row for row in after['rows'] if row['voice'] != 0])
        self.assertEqual([row['phaseAfter'] for row in before['returns'][:5]], [1, 2, 3, 4, 5])

    def test_phase_wrap_preserves_quarter_alignment(self):
        description = self.example()
        description['initialState']['phase'] = 255
        computed = self.score.expand(description, 3)
        self.assertEqual([row['phaseAfter'] for row in computed['returns']], [0, 1, 2])
        self.assertEqual([row['tick'] for row in computed['rows']], [1, 1, 1])

    def test_rest_retains_note_and_instrument_and_ignores_parameter_flag(self):
        description = self.example()
        description['patterns']['0']['rows'] = [dict(header=0x80, note=45,
            parameter=dict(volume=6, instrument=1)), dict(header=0xc0)]
        result = self.score.expand(description, 5)
        rows = [row for row in result['rows'] if row['voice'] == 0]
        self.assertEqual([(row['tick'], row['kind'], row['state']['note'], row['state']['instrument'])
                          for row in rows], [(0, 'note', 45, 1), (4, 'rest', 45, 1)])
        self.assertEqual(len([row for row in result['reads'] if row['voice'] == 0
                              and row['field'] == 'packedParameter']), 1)

    def test_reset_clears_only_cursor_and_remaining_and_skips_lower_voices(self):
        description = self.example()
        description['patterns']['2']['rows'] = [dict(header=0x80, note=47,
            parameter=dict(volume=6, instrument=3))]
        result = self.score.expand(description, 9)
        self.assertEqual([(row['tick'], row['voice']) for row in result['resets']], [(4, 2)])
        reset = result['returns'][4]
        self.assertEqual(reset['phaseAfter'], 5)
        self.assertEqual([(voice['orderCursor'], voice['patternCursor'], voice['remaining'])
                          for voice in reset['voices']], [(0, 0, 0)] * 3)
        self.assertEqual((reset['voices'][2]['note'], reset['voices'][2]['header'],
                          reset['voices'][2]['instrument']), (47, 0x80, 3))
        self.assertFalse(any(row['tick'] == 4 for row in result['rows']))
        self.assertEqual([row['voice'] for row in result['rows'] if row['tick'] == 8], [2, 1, 0])

    def test_order_and_pattern_lookahead_reads_repeat_from_semantic_data(self):
        result = self.score.expand(self.example(), 21)
        headers = [row for row in result['reads'] if row['voice'] == 0 and row['field'] == 'rowHeader']
        self.assertEqual([(row['tick'], row['offset'], row['value']) for row in headers], [(0, 0, 35), (16, 2, 35)])
        lookahead = [row for row in result['reads'] if row['voice'] == 0 and row['field'] == 'patternLookahead']
        self.assertEqual([row['value'] for row in lookahead], [35, 255])
        self.assertEqual(result['returns'][16]['voices'][0]['orderCursor'], 1)
        self.assertEqual(len([row for row in result['reads'] if row['field'] == 'orderPointerLow']), 18)

    def test_negative_remaining_skips_quarter_score_without_mutation(self):
        description = self.example()
        description['initialState']['voices'][2]['remaining'] = 255
        result = self.score.expand(description, 5)
        self.assertFalse(any(row['voice'] == 2 for row in result['rows']))
        self.assertEqual(result['returns'][4]['voices'][2]['remaining'], 255)

    def test_volume_action_observes_voice_zero_cursor_in_descending_order(self):
        description = self.example()
        description['orders'][0]['patterns'] = [0] * 109
        description['initialState']['voices'][0]['orderCursor'] = 100
        description['patterns']['2']['rows'] = [dict(header=0x80, note=47,
            parameter=dict(volume=15, instrument=3))]
        result = self.score.expand(description, 1)
        command, = [row for row in result['actions'] if row['stage'] == 'volume']
        self.assertEqual((command['voice'], command['nibble'], command['voice0OrderCursor']), (2, 15, 100))

    def test_source_metadata_is_not_runtime_state(self):
        description = self.example()
        annotated = deepcopy(description)
        for voice, order in enumerate(annotated['orders']):
            order['sourceEvidence'] = dict(address=0xa2bd + voice * 110)
        for pattern, value in annotated['patterns'].items():
            value['sourceEvidence'] = dict(address=0xa400 + int(pattern) * 32)
            value['rows'][0]['sourceEvidence'] = dict(arbitrary='annotation')
        left, right = self.score.expand(description, 25), self.score.expand(annotated, 25)
        for key in ('rows', 'returns', 'resets', 'actions'):
            self.assertEqual(left[key], right[key])

    def test_unknown_state_or_duplicate_editable_fields_are_rejected(self):
        for change in ('duration', 'control', 'empty_order', 'missing_pattern'):
            description = self.example()
            if change == 'duration':
                description['patterns']['0']['rows'][0]['duration'] = 3
            elif change == 'control':
                description['initialState']['voices'][0]['cachedControl'] = 65
            elif change == 'empty_order':
                description['orders'][0]['patterns'] = []
            else:
                description['orders'][0]['patterns'] = [99]
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.score.expand(description, 1)


if __name__ == '__main__':
    unittest.main()
