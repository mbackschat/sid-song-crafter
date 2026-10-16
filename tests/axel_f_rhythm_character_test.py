import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('rhythm_character', ROOT / 'scripts/studies/axel-f/prepare-rhythm-character.py')
CHARACTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHARACTER)
import axel_f_rhythm_trial_test as projection_tests


class RhythmCharacterTest(unittest.TestCase):
    def setUp(self):
        fixture = projection_tests.AxelRhythmTrialTest()
        fixture.setUp()
        self.common, self.score, self.palette, self.projection = fixture.common, fixture.score, fixture.palette, fixture.config
        self.config = CHARACTER.read(ROOT / 'songs/axel-f/rhythm-character.json')
        self.config['projectionFingerprint'] = CHARACTER.fingerprint(self.projection)
        self.config['paletteFingerprint'] = CHARACTER.fingerprint(self.palette)

    def prepare(self):
        return CHARACTER.prepare(self.common, self.score, self.palette, self.projection, self.config)

    def test_changes_only_percussion_instrument_with_unchanged_source_rhythm(self):
        result = self.prepare()
        reference, candidate = result['maracas.json'], result['candidate.json']
        self.assertEqual('candidate-score.json', reference['score'])
        self.assertEqual(reference['score'], candidate['score'])
        self.assertEqual('1300', reference['instruments']['rhythm']['adsr'])
        reference['instruments']['rhythm'] = candidate['instruments']['rhythm']
        reference['title'] = candidate['title']
        self.assertEqual(reference, candidate)
        self.assertEqual(68, len(result['candidate-score.json']['voices'][1]['events']))
        self.assertEqual(result['baseline-score.json']['voices'][0], result['candidate-score.json']['voices'][0])
        self.assertEqual(result['baseline-score.json']['voices'][2], result['candidate-score.json']['voices'][2])

    def test_rejects_changed_palette_and_projection(self):
        self.palette['clock'] = 'ntsc'
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            self.prepare()
        self.setUp()
        self.projection['sourceMidi'] = 69
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            self.prepare()

    def test_rejects_coupling_filter_and_nonfalling_pitch(self):
        for key, value in [('wave', [['15', 'b4', '00']]), ('filter', [['90', '00', '00']]),
                           ('wave', [['11', 'a5', '00'], ['11', 'b4', '00']])]:
            with self.subTest(key=key, value=value):
                self.setUp()
                self.config['instrument'][key] = value
                with self.assertRaises(ValueError):
                    self.prepare()

    def test_preserves_ordered_tonal_writes_not_just_end_of_frame(self):
        frames = [[0] * 25 for _ in range(2)]
        changed = copy.deepcopy(frames)
        changed[1][7] = 1
        store = dict(phase='play', tick=1, address=0xd400, value=5, instructionStartCycle=10)
        CHARACTER.verify_boundary(frames, changed, [store], [store])
        with self.assertRaisesRegex(ValueError, 'Ordered'):
            CHARACTER.verify_boundary(frames, changed, [store], [store, {**store, 'value': 6}, store])
        changed[1][24] = 15
        with self.assertRaisesRegex(ValueError, 'shared'):
            CHARACTER.verify_boundary(frames, changed, [store], [store])


if __name__ == '__main__':
    unittest.main()
