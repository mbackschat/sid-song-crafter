import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import shades_player


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ShadesPlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.score = json.loads((ROOT / 'songs/shades-score.json').read_text())
        cls.programs = json.loads((ROOT / 'songs/shades-programs.json').read_text())

    def test_computed_opening_matches_every_ordered_source_sid_and_timer_store(self):
        source = ROOT / '.local/research/shades/Shades_filter_corrected.sid'
        if not source.exists():
            self.skipTest('Pinned Shades reference is not installed')
        _, expected = load_script('trace-shades-vice').shades_oracle(source.read_bytes(), 1280)
        actual = shades_player.compute(self.score, self.programs, calls=1280)
        project = lambda rows: [(row['tick'], row['address'], row['value']) for row in rows]
        self.assertEqual(project(expected), project(actual))

    def test_source_annotations_are_not_runtime_inputs(self):
        score, programs = copy.deepcopy(self.score), copy.deepcopy(self.programs)
        score.pop('sourceEvidence', None)
        programs.pop('sourceEvidence', None)
        self.assertEqual(shades_player.compute(self.score, self.programs, calls=512),
                         shades_player.compute(score, programs, calls=512))

    def test_malformed_container_shapes_raise_validation_errors(self):
        for description in (None, [], {'format': 'sid-shades-programs-v1'}):
            with self.subTest(programs=description), self.assertRaises(ValueError):
                shades_player.compute(self.score, description, calls=1)
        for field, value in (('range', None), ('patternIds', [[], 'unused', 'unused'])):
            score = copy.deepcopy(self.score)
            if field == 'range':
                score[field] = value
            else:
                score['orders'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                shades_player.compute(score, self.programs, calls=1)

    def test_editable_pulse_step_changes_only_its_pulse_stores(self):
        programs = copy.deepcopy(self.programs)
        programs['programs']['blocks']['opening-pulse']['voices'][0]['pulse_step'] = 0
        baseline = shades_player.compute(self.score, self.programs, calls=1280)
        frozen = shades_player.compute(self.score, programs, calls=1280)
        self.assertEqual(len(baseline), len(frozen))
        changes = [(a, b) for a, b in zip(baseline, frozen) if a != b]
        self.assertTrue(changes)
        self.assertTrue(all(a['address'] == b['address'] and a['address'] in (0xd402, 0xd403)
                            and a['tick'] == b['tick'] for a, b in changes))

    def test_finite_stop_follows_the_complete_source_fade(self):
        writes = shades_player.compute(self.score, self.programs, include_stop=True)
        stop = self.score['range']['stopCall']
        volume = [(row['tick'], row['value']) for row in writes
                  if row['address'] == 0xd418 and row['tick'] < stop]
        self.assertEqual((24244, 0x10), next(row for row in volume if row[0] > 22849 and row[1] & 15 == 0))
        terminal = [row for row in writes if row['tick'] == stop]
        self.assertEqual([(0xd404, 0), (0xd40b, 0), (0xd412, 0), (0xd418, 0)],
                         [(row['address'], row['value']) for row in terminal])
        self.assertFalse(any(row['tick'] > stop for row in writes))


if __name__ == '__main__':
    unittest.main()
