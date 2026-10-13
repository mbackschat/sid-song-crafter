from copy import deepcopy
import unittest

from cybernoid_player_test import opening_fixture, identity
from cybernoid_player import compute_writes, _compute_writes


def finite_fixture(release=2, step=1):
    description = opening_fixture()
    description['ending'] = dict(start_call=2, release_calls=release, fade_step_calls=step)
    description['play_calls'] = 2 + release + 16 * step
    return description


class CybernoidEndingTests(unittest.TestCase):
    def test_music_prefix_is_unchanged_and_tail_never_starts_new_notes(self):
        description = finite_fixture()
        before = deepcopy(description)
        writes = compute_writes(description)
        self.assertEqual(identity(compute_writes(opening_fixture())),
                         identity([w for w in writes if w['tick'] is None or w['tick'] < 2]))
        tail = [w for w in writes if w['tick'] is not None and w['tick'] >= 2]
        controls = [w for w in tail if w['address'] in (0xd404, 0xd40b, 0xd412)]
        self.assertEqual(3 * 18, len(controls))
        self.assertTrue(all(w['value'] & 1 == 0 for w in controls))
        self.assertFalse(any(w['address'] in (0xd405, 0xd40c, 0xd413) for w in tail))
        self.assertEqual(before, description)

    def test_filter_cannot_restore_volume_and_each_fade_level_has_declared_duration(self):
        description = finite_fixture(release=3, step=2)
        writes = compute_writes(description)
        for age in range(35):
            group = [w for w in writes if w['tick'] == age + 2]
            volume = 15 if age < 3 else 15 - (age - 3) // 2
            stores = [w['value'] for w in group if w['address'] == 0xd418]
            self.assertGreater(len(stores), 1)
            self.assertTrue(all(value & 15 == volume for value in stores))
            self.assertEqual(0xd418, group[-1]['address'])
            self.assertEqual(0x30, group[-1]['value'] & 0xf0)
        self.assertEqual(0, writes[-1]['value'] & 15)

    def test_release_keeps_modulation_but_saturates_age_and_freezes_row_calendar(self):
        description = finite_fixture(release=260)
        observed = []
        _compute_writes(description, observer=observed.append)
        for voice in range(3):
            final_music = next(o for o in observed if o['call'] == 1 and o['voiceIndex'] == voice)
            tail = [o for o in observed if o['call'] >= 2 and o['voiceIndex'] == voice]
            self.assertTrue(all(o['row'] is None for o in tail))
            self.assertTrue(all(o['state']['row_remaining'] == final_music['state']['row_remaining'] for o in tail))
            self.assertTrue(all(o['globals']['tempo_countdown'] == final_music['globals']['tempo_countdown'] for o in tail))
            self.assertEqual(255, tail[-1]['state']['note_age'])
        bass = [o['state']['pulse_output'] for o in observed if o['call'] >= 2 and o['voiceIndex'] == 0]
        self.assertGreater(len(set(bass)), 1)

    def test_invalid_endings_and_rows_in_release_are_rejected(self):
        for changes in (dict(start_call=0), dict(start_call=True), dict(release_calls=-1),
                        dict(fade_step_calls=0), dict(fade_step_calls=1.5)):
            description = finite_fixture()
            description['ending'].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                compute_writes(description)
        description = finite_fixture()
        description['play_calls'] += 1
        with self.assertRaisesRegex(ValueError, 'Ending'):
            compute_writes(description)
        description = finite_fixture()
        description['rows'][0]['call'] = 2
        with self.assertRaisesRegex(ValueError, 'Row call'):
            compute_writes(description)


if __name__ == '__main__':
    unittest.main()
