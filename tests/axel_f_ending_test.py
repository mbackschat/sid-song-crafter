import copy
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('ending', Path(__file__).resolve().parents[1] / 'scripts/studies/axel-f/prepare-ending.py')
ENDING = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENDING)


class EndingTest(unittest.TestCase):
    def setUp(self):
        self.score = dict(totalBeats=8, tailTicks=125, voices=[dict(name='bass', events=[dict(startBeat=1, durationBeats=1, midi=60), dict(startBeat=6, durationBeats=.25, midi=48)])])
        self.native = dict(instruments=dict(bass=dict(adsr='0999'), lead=dict(adsr='0849')), sections=[dict(name='last', startBeat=0, endBeat=8, voices=dict(bass='bass', melody='lead'))])
        self.config = dict(finalBassBeat=6, previousAdsr='0999', endingAdsr='0997', previousTailTicks=125, tailTicks=25)

    def test_only_final_bass_role_and_terminal_padding_change(self):
        original = copy.deepcopy((self.score, self.native))
        score, native = ENDING.project(self.score, self.native, self.config)
        self.assertEqual(original, (self.score, self.native))
        self.assertEqual(self.score['voices'], score['voices'])
        self.assertEqual(8, score['totalBeats'])
        self.assertEqual(25, score['tailTicks'])
        self.assertEqual(self.native['instruments'], {k:v for k,v in native['instruments'].items() if k != 'ending-bass'})
        self.assertEqual({'adsr':'0997'}, native['instruments']['ending-bass'])
        self.assertEqual([(0,6,'bass'),(6,8,'ending-bass')], [(s['startBeat'],s['endBeat'],s['voices']['bass']) for s in native['sections']])

    def test_rejects_nonfinal_note_or_changed_baseline(self):
        for key, value in [('finalBassBeat',1),('previousAdsr','0888'),('previousTailTicks',100),('endingAdsr','0797')]:
            config = dict(self.config, **{key:value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                ENDING.project(self.score, self.native, config)

    def test_guard_rejects_unrelated_register_change(self):
        before = [[0]*25 for _ in range(5)]
        after = copy.deepcopy(before)
        after[3][20] = 0x97
        before[3][20] = 0x99
        ENDING.verify_frames(before, after, 3, 4)
        after[2][0] = 1
        with self.assertRaises(ValueError):
            ENDING.verify_frames(before, after, 3, 4)
