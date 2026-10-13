from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('monty_title_ending', ROOT / 'scripts/studies/monty/prepare-monty-title-ending.py')
preparation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preparation)


class MontyTitleEndingPreparationTest(unittest.TestCase):
    def test_arrangement_preserves_numeric_music_and_declares_added_tail(self):
        source = json.loads((ROOT / 'songs/monty-title-source.json').read_text())
        original = deepcopy(source)
        candidate = preparation.prepare_title(source)
        self.assertEqual(original, source)
        self.assertEqual(17664, candidate['play_calls'])
        self.assertEqual(dict(start_call=17536, release_calls=64, fade_step_calls=4), candidate['ending'])
        for field in ('score', 'frequency_words', 'frequency_alias_bindings', 'instruments', 'initial_state'):
            self.assertEqual(source[field], candidate[field])
        self.assertIn('restart', candidate['sourceEvidence']['arrangement']['endingDifference'])

    def test_selected_cycle_requires_the_pinned_source_description(self):
        source = json.loads((ROOT / 'songs/monty-title-source.json').read_text())
        source['score']['patterns'][0]['bytes'][0] ^= 1
        with self.assertRaisesRegex(ValueError, 'pinned'):
            preparation.prepare_title(source)


if __name__ == '__main__':
    unittest.main()
