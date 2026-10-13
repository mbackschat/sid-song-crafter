from copy import deepcopy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from monty_title_player import compute_player, compute_writes
from monty_title_player_test import fixture, group


def finite_fixture():
    description = fixture()
    description['ending'] = dict(start_call=2, release_calls=64, fade_step_calls=4)
    description['play_calls'] = 130
    description['initial_state']['globals']['mode_volume'] = 0x4f
    description['instruments'][0].update(vibrato_depth=1, pulse_value=64, effects=3)
    description['score']['patterns'][0]['bytes'] = [8, 0, 255]
    description['frequency_words'][1] = 1400
    return description


class MontyEndingTests(unittest.TestCase):
    def test_music_prefix_is_identical_and_score_stays_frozen_during_tail(self):
        finite = finite_fixture()
        looping = deepcopy(finite)
        del looping['ending']
        before = deepcopy(finite)
        at_cut = compute_player(looping, calls=2)
        result = compute_player(finite)
        prefix = [row for row in result['writes'] if row['phase'] == 'init' or row['tick'] < 2]
        self.assertEqual(at_cut['writes'], prefix)
        for index in range(3):
            for name in ('order_cursor', 'pattern_cursor', 'remaining', 'note', 'control',
                         'instrument_index', 'portamento', 'voice_control'):
                self.assertEqual(at_cut['finalState']['voices'][index][name],
                                 result['finalState']['voices'][index][name], name)
        self.assertEqual(at_cut['finalState']['globals']['tempo_countdown'],
                         result['finalState']['globals']['tempo_countdown'])
        self.assertEqual((at_cut['finalState']['globals']['counter'] + 128) & 255,
                         result['finalState']['globals']['counter'])
        self.assertEqual(before, finite)

    def test_first_tail_clears_actual_controls_before_continuing_programs(self):
        description = finite_fixture()
        first = group(compute_writes(description), 2)
        self.assertEqual([(0xd418, 0x4f), (0xd412, 128), (0xd40b, 128), (0xd404, 128)], first[:4])
        self.assertGreater(len(first), 4)
        tail = [row for row in compute_writes(description) if row['phase'] == 'play' and row['tick'] >= 2]
        controls = [row for row in tail if row['address'] in (0xd404, 0xd40b, 0xd412)]
        self.assertTrue(controls)
        self.assertTrue(all(row['value'] & 1 == 0 for row in controls))
        self.assertFalse(any(row['address'] in (0xd405, 0xd406, 0xd40c, 0xd40d, 0xd413, 0xd414)
                             for row in tail))

    def test_release_uses_last_hardware_control_without_changing_saved_alias_fields(self):
        description = finite_fixture()
        description['score']['patterns'][0]['bytes'] = [0, 0, 255]
        description['instruments'][0]['effects'] = 0
        description['ending']['start_call'] = 3
        description['play_calls'] = 131
        result = compute_player(description)
        self.assertEqual([(0xd418, 0x4f), (0xd412, 64), (0xd40b, 64), (0xd404, 64)],
                         group(result['writes'], 3)[:4])
        self.assertEqual([65, 65, 65],
                         [row['voice_control'] for row in result['finalState']['voices']])

    def test_fade_has_all_sixteen_levels_and_stops_at_declared_limit(self):
        description = finite_fixture()
        result = compute_player(description)
        volumes = [row for row in result['writes'] if row['phase'] == 'play' and row['address'] == 0xd418]
        self.assertEqual([0x4f] * 64, [row['value'] for row in volumes[2:66]])
        self.assertEqual([0x40 | level for level in range(15, -1, -1) for _ in range(4)],
                         [row['value'] for row in volumes[66:]])
        self.assertEqual(129, max(row['tick'] for row in result['writes'] if row['phase'] == 'play'))
        self.assertTrue(result['stopped'])
        self.assertEqual(0x40, result['finalState']['globals']['mode_volume'])
        self.assertFalse(compute_player(description, calls=129)['stopped'])
        with self.assertRaises(ValueError):
            compute_player(description, calls=131)

    def test_exclusive_caps_cross_release_and_fade_boundaries_without_resuming_score(self):
        description = finite_fixture()
        complete = compute_writes(description)
        for calls in (0, 1, 2, 3, 65, 66, 67, 126, 130):
            with self.subTest(calls=calls):
                prefix = [row for row in complete if row['phase'] == 'init' or row['tick'] < calls]
                self.assertEqual(prefix, compute_writes(description, calls=calls))

    def test_ending_contract_rejects_wrong_totals_and_unproved_timing(self):
        for field, value in (('start_call', 0), ('start_call', True), ('release_calls', 63),
                             ('release_calls', True), ('fade_step_calls', 3)):
            description = finite_fixture()
            description['ending'][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                compute_player(description)
        description = finite_fixture()
        description['play_calls'] += 1
        with self.assertRaisesRegex(ValueError, 'total'):
            compute_player(description, calls=0)


if __name__ == '__main__':
    unittest.main()
