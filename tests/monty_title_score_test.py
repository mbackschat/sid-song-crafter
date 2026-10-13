from copy import deepcopy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from monty_title_score import expand_score


def initial_state():
    return dict(globals=dict(tempo_countdown=0, tempo_reload=1, counter=250, status=64),
                voices=[dict(order_cursor=4, pattern_cursor=5, remaining=19, control=37,
                             note=70, instrument_index=7, portamento=0) for _ in range(3)])


def tables(pattern=None):
    return dict(orders=[dict(voice_index=i, bytes=[0, 255]) for i in range(3)],
                patterns=[dict(pattern_id=0, bytes=pattern or [0x81, 3, 12, 1, 13, 255])])


def voice_operations(result, call, voice=2):
    return [row for row in result['operations'] if row['call'] == call and row.get('voice_index') == voice]


class MontyTitleScoreTests(unittest.TestCase):
    def test_first_status_restart_resets_sequence_and_counter_before_voice_order(self):
        result = expand_score(tables(), calls=1, initial_state=initial_state())
        call = result['operations'][0]
        self.assertEqual(dict(operation='call', call=0, counter=0, status=0,
                              tempo_countdown=1, tempo_reload=1, score_tick=True,
                              reset_sequence=True), call)
        self.assertEqual([2, 1, 0], [row['voice_index'] for row in result['operations']
                                    if row['operation'] == 'initialize'])
        for row in result['operations']:
            if row['operation'] == 'row':
                self.assertEqual((0, 0, 0, 1),
                                 (row['order_cursor'], row['pattern_cursor'], row['note'], row['remaining']))

    def test_duration_owns_one_more_score_tick_and_release_only_on_tick(self):
        result = expand_score(tables(), calls=5, initial_state=initial_state())
        rows = [row for row in result['operations'] if row['operation'] == 'row' and row['voice_index'] == 2]
        self.assertEqual([0, 4], [row['call'] for row in rows])
        body = [row for row in result['operations'] if row['operation'] == 'body' and row['voice_index'] == 2]
        self.assertEqual([(1, 1, False), (2, 0, True), (3, 0, False)],
                         [(row['call'], row['remaining'], row['release_check']) for row in body])

    def test_append_ignores_parameter_bit_retains_note_and_clears_portamento(self):
        result = expand_score(tables([0x80, 0x91, 12, 0xc0, 0, 13, 255]),
                              calls=5, initial_state=initial_state())
        append = voice_operations(result, 2)
        self.assertEqual(['row', 'initialize', 'navigation'], [row['operation'] for row in append])
        initializer = append[1]
        self.assertTrue(initializer['append'])
        self.assertEqual((12, 7, 0, 3), (initializer['note'], initializer['instrument_index'],
                                        initializer['portamento'], initializer['pattern_cursor']))
        self.assertEqual([3], [row['offset'] for row in result['reads']
                              if row['call'] == 2 and row['voice_index'] == 2 and row['kind'] == 'rowControlRead'])
        self.assertFalse(any(row['kind'] in ('instrumentOrPortamentoRead', 'pitchRead')
                             and row['call'] == 2 for row in result['reads']))
        self.assertEqual(13, next(row['note'] for row in voice_operations(result, 4)
                                  if row['operation'] == 'note'))

    def test_portamento_and_instrument_updates_precede_pitch_initializer(self):
        result = expand_score(tables([0x80, 0x91, 14, 0x80, 2, 15, 255]),
                              calls=3, initial_state=initial_state())
        first = voice_operations(result, 0)
        self.assertEqual(['row', 'portamento', 'note', 'initialize', 'navigation'],
                         [row['operation'] for row in first])
        self.assertEqual((7, 0x91, 14), (first[3]['instrument_index'], first[3]['portamento'], first[3]['note']))
        second = voice_operations(result, 2)
        self.assertEqual(['row', 'instrument', 'note', 'initialize', 'navigation'],
                         [row['operation'] for row in second])
        self.assertEqual((2, 0, 15), (second[3]['instrument_index'], second[3]['portamento'], second[3]['note']))

    def test_pattern_end_peek_follows_initializer_and_order_wrap_retains_counter(self):
        result = expand_score(tables([0, 12, 255]), calls=5, initial_state=initial_state())
        first = voice_operations(result, 0)
        self.assertEqual((0, 1), (first[-2]['order_cursor'], first[-2]['pattern_cursor']))
        self.assertEqual((1, 0, True),
                         (first[-1]['order_cursor'], first[-1]['pattern_cursor'], first[-1]['pattern_end']))
        self.assertEqual([(call, voice) for call in (2, 4) for voice in (2, 1, 0)],
                         [(row['call'], row['voice_index']) for row in result['orderRestarts']])
        calls = [row for row in result['operations'] if row['operation'] == 'call']
        self.assertEqual([0, 1, 2, 3, 4], [row['counter'] for row in calls])
        self.assertEqual('navigation', voice_operations(result, 2)[0]['operation'])

    def test_inputs_and_source_annotations_are_not_runtime_state(self):
        state, score = initial_state(), tables()
        score['sourceEvidence'] = dict(reference='/absent.sid', events=[dict(value=255)])
        before_state, before_score = deepcopy(state), deepcopy(score)
        result = expand_score(score, calls=3, initial_state=state)
        self.assertEqual(before_state, state)
        self.assertEqual(before_score, score)
        result['finalState']['voices'][0]['note'] = 99
        self.assertEqual(before_state, state)
        clean = deepcopy(score)
        del clean['sourceEvidence']
        self.assertEqual(result['operations'], expand_score(clean, calls=3, initial_state=state)['operations'])

    def test_invalid_numeric_data_and_unsupported_paths_reject(self):
        for calls in (-1, True, 1.5, 100001):
            with self.subTest(calls=calls), self.assertRaises(ValueError):
                expand_score(tables(), calls=calls, initial_state=initial_state())
        for changed in (tables([255]), tables([0x80]), tables([0, 12, 256])):
            with self.subTest(score=changed), self.assertRaises(ValueError):
                expand_score(changed, calls=1, initial_state=initial_state())
        duplicate = tables()
        duplicate['patterns'].append(deepcopy(duplicate['patterns'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate pattern'):
            expand_score(duplicate, calls=1, initial_state=initial_state())
        exit_score = tables()
        exit_score['orders'][2]['bytes'][0] = 254
        with self.assertRaisesRegex(ValueError, 'FE'):
            expand_score(exit_score, calls=1, initial_state=initial_state())
        state = initial_state()
        state['globals']['status'] = 128
        with self.assertRaisesRegex(ValueError, 'status'):
            expand_score(tables(), calls=1, initial_state=state)

    def test_order_restart_loop_rejects_instead_of_hanging(self):
        score = tables()
        score['orders'][2]['bytes'] = [255]
        with self.assertRaisesRegex(ValueError, 'restart loop'):
            expand_score(score, calls=1, initial_state=initial_state())

    def test_tempo_dispatch_uses_post_decrement_equality_without_requiring_reload(self):
        state = initial_state()
        state['globals'].update(status=0, tempo_countdown=2, tempo_reload=1)
        for voice in state['voices']:
            voice.update(order_cursor=0, pattern_cursor=0, remaining=0)
        result = expand_score(tables(), calls=3, initial_state=state)
        calls = [row for row in result['operations'] if row['operation'] == 'call']
        self.assertEqual([(251, 1, True), (252, 0, False), (253, 1, True)],
                         [(row['counter'], row['tempo_countdown'], row['score_tick']) for row in calls])
        self.assertEqual('row', voice_operations(result, 0)[0]['operation'])

    def test_editing_reload_duration_and_pitch_changes_computed_schedule(self):
        state = initial_state()
        state['globals']['tempo_reload'] = 2
        result = expand_score(tables([0x80, 2, 14, 255]), calls=8, initial_state=state)
        starts = [row for row in result['operations']
                  if row['operation'] == 'initialize' and row['voice_index'] == 2]
        self.assertEqual([(0, 14, 2), (3, 14, 2), (6, 14, 2)],
                         [(row['call'], row['note'], row['instrument_index']) for row in starts])
        state['globals']['tempo_reload'] = 0
        result = expand_score(tables([31, 15, 255]), calls=34, initial_state=state)
        starts = [row for row in result['operations']
                  if row['operation'] == 'initialize' and row['voice_index'] == 2]
        self.assertEqual([(0, 15), (32, 15)], [(row['call'], row['note']) for row in starts])

    def test_remaining_decrement_uses_byte_sign_after_subtraction(self):
        state = initial_state()
        state['globals']['status'] = 0
        for voice in state['voices']:
            voice['remaining'] = 128
        result = expand_score(tables(), calls=1, initial_state=state)
        self.assertEqual(['body'], [row['operation'] for row in voice_operations(result, 0)])
        self.assertEqual(127, voice_operations(result, 0)[0]['remaining'])
        self.assertEqual([], result['reads'])

    def test_optional_output_and_overlay_context_must_match_title_contract(self):
        for field, value in (('output_enable', 127), ('sfx_priority', 1), ('sfx_flags', 0)):
            state = initial_state()
            state['globals'][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'context'):
                expand_score(tables(), calls=1, initial_state=state)


if __name__ == '__main__':
    unittest.main()
