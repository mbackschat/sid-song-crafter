"""Guard native Airwolf updates and the two explicit authored extensions."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/studies/airwolf'))
import airwolf_player as player


def example(calls=24):
    return player.from_score(dict(rows=[dict(duration=2, notes=[3691, 1845, 22121]),
        dict(duration=1, notes=[None, 'off', 17557])]), calls=calls)


class AirwolfPlayerTest(unittest.TestCase):
    def test_init_consumes_first_row_and_native_wrap_duplicates_fixed_stores(self):
        value = example()
        result = player.compute(value, calls=5)
        self.assertEqual(len([item for item in result['writes'] if item['phase'] == 'init']), 21)
        self.assertEqual(result['initial']['nextRow'], 1)
        self.assertEqual(result['initial']['countdown'], 2)
        self.assertEqual(result['restartCalls'], [4])
        wrap = [item for item in result['writes'] if item['tick'] == 4]
        self.assertEqual([(item['address'], item['value']) for item in wrap[:6]],
            [(0xd418, 15), (0xd403, 40), (0xd40a, 10)] * 2)
        self.assertEqual(result['returns'][4]['nextRow'], 1)

    def test_duration_plus_one_and_high_duration_do_not_use_a_sign_test(self):
        for duration in (1, 2, 128, 255):
            value = example(calls=260)
            value['rows'][0]['duration'] = duration
            result = player.compute(value, calls=duration + 1)
            self.assertEqual(result['returns'][duration - 1]['nextRow'], 1)
            self.assertEqual(result['returns'][duration]['nextRow'], 2)

    def test_null_hold_and_authored_off_preserve_pitch_but_differ_in_gate_store(self):
        result = player.compute(example(), calls=3)
        row = [item for item in result['writes'] if item['tick'] == 2]
        self.assertFalse(any(0xd400 <= item['address'] <= 0xd406 for item in row[3:]))
        self.assertEqual([(item['address'], item['value']) for item in row[3:]],
            [(0xd40b, 64), (0xd413, 9), (0xd414, 0), (0xd412, 0),
             (0xd412, 17), (0xd40f, 68), (0xd40e, 149)])
        self.assertEqual(result['returns'][2]['voices'][1]['frequency'], 1845)
        value = example()
        value['rows'][0]['notes'] = ['off', None, None]
        first = player.compute(value, calls=0)
        self.assertEqual(first['writes'][-1]['value'], 0)
        self.assertEqual(first['initial']['voices'][0]['control'], 0)

    def test_ending_closes_actual_controls_then_stops_without_later_stores(self):
        value = example(calls=70)
        value['ending'] = dict(startCall=3, releaseCalls=2)
        result = player.compute(value)
        self.assertEqual([(item['address'], item['value']) for item in result['writes'] if item['tick'] == 3],
            [(0xd404, 64), (0xd40b, 64), (0xd412, 16)])
        self.assertEqual(result['returns'][4]['nextRow'], result['returns'][2]['nextRow'])
        self.assertEqual([(item['address'], item['value']) for item in result['writes'] if item['tick'] == 5],
            [(0xd404, 0), (0xd40b, 0), (0xd412, 0), (0xd418, 0)])
        self.assertFalse(any(item['tick'] is not None and item['tick'] > 5 for item in result['writes']))
        self.assertEqual(result['returns'][-1]['ending'], dict(phase=2, nextCall=5))

    def test_strict_sound_and_score_admission_rejects_ambiguous_or_unsupported_edits(self):
        for notes in ([0, None, None], [255, None, None], ['rest', None, None]):
            value = example()
            value['rows'][0]['notes'] = notes
            with self.assertRaises(ValueError): player.compute(value)
        for control in (0, 16, 67, 73, 97, 145):
            value = example()
            value['sound']['voices'][0]['control'] = control
            with self.assertRaisesRegex(ValueError, 'single waveform'): player.compute(value)
        value = example()
        value['rows'][0]['duration'] = 0
        with self.assertRaises(ValueError): player.compute(value)

    def test_reinitialization_is_pure_and_metadata_only_labels_observations(self):
        value = example()
        retained = deepcopy(value)
        first = player.compute(value)
        self.assertEqual(value, retained)
        self.assertEqual(first, player.compute(value))
        value['sourceEvidence'] = {'sha256': 'arbitrary annotation'}
        value['title'] = 'Different metadata'
        value['rows'][0]['sourceAddress'] = 0x9000
        changed = player.compute(value)
        self.assertEqual(first['writes'], changed['writes'])
        self.assertEqual(first['returns'], changed['returns'])

    def test_plain_triangle_patch_changes_only_its_control_ports(self):
        value = example()
        baseline = player.compute(value)
        value['sound']['voices'][0]['control'] = 17
        changed = player.compute(value)
        self.assertNotEqual(changed['writes'], baseline['writes'])
        self.assertEqual([item for item in changed['writes'] if item['address'] != 0xd404],
            [item for item in baseline['writes'] if item['address'] != 0xd404])
        self.assertEqual(changed['initial']['voices'][0]['control'], 17)
        self.assertEqual(changed['initial']['pulseHigh'], [40, 10])

    def test_target_range_and_redundant_initial_image_reject(self):
        value = example()
        value['target']['sidModel'] = 'MOS8580'
        with self.assertRaisesRegex(ValueError, 'PAL MOS6581'): player.compute(value)
        value = example()
        value['range']['auditCalls'] = True
        with self.assertRaises(ValueError): player.compute(value)
        value = example()
        value['initialSound'] = {}
        with self.assertRaisesRegex(ValueError, 'Unknown composition fields'): player.compute(value)


if __name__ == '__main__':
    unittest.main()
