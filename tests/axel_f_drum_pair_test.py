import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('drum_pair', ROOT / 'scripts/studies/axel-f/prepare-drum-pair.py')
PAIR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PAIR)
import axel_f_rhythm_trial_test as projection_tests


class DrumPairTest(unittest.TestCase):
    def setUp(self):
        fixture = projection_tests.AxelRhythmTrialTest()
        fixture.setUp()
        self.common, self.score, self.palette, self.projection = fixture.common, fixture.score, fixture.palette, fixture.config
        self.common['parts'][0]['events'] += [dict(startBeat=68, durationBeats=.0625, midi=36),
            dict(startBeat=69, durationBeats=.0625, midi=36), dict(startBeat=69, durationBeats=.0625, midi=38),
            dict(startBeat=69.25, durationBeats=.0625, midi=36)]
        self.config = PAIR.read(ROOT / 'songs/axel-f/drum-pair.json')
        self.config.update(projectionFingerprint=PAIR.fingerprint(self.projection),
                           paletteFingerprint=PAIR.fingerprint(self.palette), expectedSourceCounts={'kick': 3, 'snare': 1},
                           expectedOutputCounts={'kick': 2, 'snare': 1}, expectedSharedOnsets=1)

    def prepare(self):
        return PAIR.prepare(self.common, self.score, self.palette, self.projection, self.config)

    def test_source_snare_wins_shared_onsets_and_other_kicks_survive(self):
        result = self.prepare()
        notes = result['candidate-score.json']['voices'][1]['events']
        self.assertEqual([0, 1, 1.25], [n['startBeat'] for n in notes])
        self.assertEqual([36, 38, 36], [n['midi'] for n in notes])
        self.assertEqual(.25, notes[1]['durationBeats'])
        self.assertEqual(result['baseline-score.json']['voices'][0], result['candidate-score.json']['voices'][0])
        self.assertEqual(result['baseline-score.json']['voices'][2], result['candidate-score.json']['voices'][2])
        self.assertEqual(['kick', 'snare', 'kick'], [s['voices']['harmony'] for s in result['candidate.json']['sections']])
        self.assertEqual(1, len(result['adaptation.json']['omittedCollisions']))

    def test_rejects_source_count_drift_and_palette_change(self):
        self.config['expectedSharedOnsets'] = 0
        with self.assertRaisesRegex(ValueError, 'collision'):
            self.prepare()
        self.setUp()
        self.palette['clock'] = 'ntsc'
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            self.prepare()

    def test_rejects_ambiguous_same_role_duplicate_onsets(self):
        self.common['parts'][0]['events'].append(dict(startBeat=68, durationBeats=.0625, midi=36))
        self.config['expectedSourceCounts']['kick'] += 1
        with self.assertRaisesRegex(ValueError, 'onset'):
            self.prepare()

    def test_tonal_identity_ignores_pattern_renumbering_but_preserves_pitch_and_time(self):
        before = {'notes': [dict(pattern=8, midi=41, startTick=0, durationTicks=4, gateOffTick=3)]}
        after = copy.deepcopy(before)
        after['notes'][0]['pattern'] = 10
        PAIR.verify_tonal_notes(before, after)
        for field, value in [('midi', 42), ('gateOffTick', 2), ('startTick', 1)]:
            changed = copy.deepcopy(after)
            changed['notes'][0][field] = value
            with self.assertRaisesRegex(ValueError, 'tonal'):
                PAIR.verify_tonal_notes(before, changed)

    def test_rejects_coupled_and_filtered_programs(self):
        for field, value in [('filter', [['90', '00', '00']]), ('wave', [['15', 'b5', '00']])]:
            with self.subTest(field=field):
                self.setUp()
                self.config['roles']['kick']['instrument'][field] = value
                with self.assertRaises(ValueError):
                    self.prepare()


if __name__ == '__main__':
    unittest.main()
