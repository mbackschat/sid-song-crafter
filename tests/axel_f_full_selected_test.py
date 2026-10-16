import copy
import importlib.util
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('full_selected', ROOT / 'scripts/studies/axel-f/prepare-full-selected.py')
FULL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FULL)

class FullSelectedTest(unittest.TestCase):

    def setUp(self):
        self.score = dict(totalBeats=8, voices=[dict(name=n, events=[]) for n in ('melody', 'harmony', 'bass')])
        self.score['voices'][0]['events'] = [dict(startBeat=0, durationBeats=8, midi=60)]
        self.score['voices'][1]['events'] = [dict(startBeat=0, durationBeats=1, midi=64), dict(startBeat=6, durationBeats=1, midi=67)]
        self.palette = dict(instruments=dict(lead=dict(adsr='old'), harmony={}, bass={}, **{'held-support': dict(adsr='held')}), sections=[dict(name='first', startBeat=0, endBeat=2, voices=dict(melody='lead', harmony='harmony', bass='bass')), dict(name='held', startBeat=2, endBeat=6, voices=dict(melody='held-support', harmony='harmony', bass='bass')), dict(name='return', startBeat=6, endBeat=8, voices=dict(melody='lead', harmony='harmony', bass='bass'))])
        self.hook = dict(totalBeats=2, voices=[dict(events=[]), dict(events=[dict(startBeat=0, durationBeats=0.4, midi=38), dict(startBeat=1.75, durationBeats=0.25, midi=38)]), dict(events=[])])
        self.native = dict(instruments=dict(lead=dict(adsr='selected'), **{'snare-x': dict(adsr='4072')}), sections=[dict(startBeat=0, endBeat=2, voices=dict(harmony='snare-x'))])
        self.windows = [[2, 6]]

    def test_projection_preserves_tonal_score_roles_and_reserves_handover(self):
        score, palette, report = FULL.project(self.score, self.palette, self.hook, self.native, self.windows, 0.5)
        self.assertEqual(self.score['voices'][0], score['voices'][0])
        self.assertEqual([2, 3.75, 4], [n['startBeat'] for n in score['voices'][1]['events'] if n['midi'] == 38])
        self.assertEqual([5.75], [n['startBeat'] for n in report['omittedForRelease']])
        self.assertEqual('selected', palette['instruments']['lead']['adsr'])
        self.assertEqual('held', palette['instruments']['held-support']['adsr'])
        self.assertTrue(all((s['voices']['melody'] == 'held-support' for s in palette['sections'] if 2 <= s['startBeat'] < 6)))
        self.assertEqual('old', self.palette['instruments']['lead']['adsr'])

    def test_projection_rejects_occupied_or_overlapping_windows(self):
        for windows in ([[0, 2]], [[2, 5], [4, 6]]):
            with self.subTest(windows=windows), self.assertRaises(ValueError):
                FULL.project(self.score, self.palette, self.hook, self.native, windows, 0.5)
        self.score['voices'][1]['events'][0]['durationBeats'] = 3
        with self.assertRaisesRegex(ValueError, 'vacant'):
            FULL.project(self.score, self.palette, self.hook, self.native, self.windows, 0.5)

    def test_projection_rejects_a_missing_selected_drum_program(self):
        del self.native['instruments']['snare-x']
        with self.assertRaises(ValueError):
            FULL.project(self.score, self.palette, self.hook, self.native, self.windows, 0.5)

    def test_schedule_guard_preserves_section_pitch_and_gate(self):
        note = dict(eventIndex=0, pattern=1, row=0, byteOffset=0, instrumentId='lead', section='held', midi=60, nativeGateOffTick=10)
        before = [dict(notes=[note]), dict(notes=[]), dict(notes=[])]
        after = copy.deepcopy(before)
        after[0]['notes'][0]['pattern'] = 4
        after[1]['notes'].append(dict(instrumentId='snare-x'))
        FULL.verify_notes(before, after)
        for key, value in [('midi', 61), ('nativeGateOffTick', 11), ('section', 'other')]:
            bad = copy.deepcopy(after)
            bad[0]['notes'][0][key] = value
            with self.assertRaises(ValueError):
                FULL.verify_notes(before, bad)
if __name__ == '__main__':
    unittest.main()
