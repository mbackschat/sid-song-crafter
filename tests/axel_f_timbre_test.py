import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('axel_timbre', ROOT / 'scripts/studies/axel-f/prepare-timbre.py')
TIMBRE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TIMBRE)


class TimbreTest(unittest.TestCase):
    def test_variants_keep_score_roles_and_bass_fixed(self):
        base = dict(sidModel='MOS8580', sidCount=1, clock='pal', score='candidate-score.json',
                    sections=[dict(voices=dict(melody='lead', harmony='kick-1d45', bass='bass'))],
                    instruments=dict(lead=dict(adsr='0a49'), bass=dict(adsr='0999'),
                                     **{'kick-1d45': dict(adsr='2052'), 'hat-2712': dict(adsr='2022'), 'snare-8b3b': dict(adsr='2092')}))
        original = copy.deepcopy(base)
        variants = TIMBRE.variants(base)
        self.assertEqual(base, original)
        self.assertEqual('MOS6581', variants['chip']['sidModel'])
        self.assertEqual(base['instruments'], variants['chip']['instruments'])
        self.assertEqual(base['sections'], variants['contour']['sections'])
        self.assertEqual(base['instruments']['bass'], variants['contour']['instruments']['bass'])
        self.assertEqual('0847', variants['contour']['instruments']['lead']['adsr'])
        self.assertEqual('4052', variants['contour']['instruments']['kick-1d45']['adsr'])
        base['instruments']['lead']['adsr'] = '0749'
        with self.assertRaisesRegex(ValueError, 'lead'):
            TIMBRE.variants(base)

    def test_store_guard_rejects_changes_outside_declared_envelopes_and_event_timing(self):
        before = [dict(phase='play', tick=1, address=0xd405, value=10), dict(phase='play', tick=1, address=0xd400, value=50)]
        after = copy.deepcopy(before)
        after[0]['value'] = 8
        TIMBRE.store_boundary(before, after, {0xd405})
        after[1]['value'] = 51
        with self.assertRaisesRegex(ValueError, 'protected'):
            TIMBRE.store_boundary(before, after, {0xd405})
        after = copy.deepcopy(before)
        after[0]['tick'] = 2
        with self.assertRaisesRegex(ValueError, 'timing'):
            TIMBRE.store_boundary(before, after, {0xd405})


if __name__ == '__main__':
    unittest.main()
