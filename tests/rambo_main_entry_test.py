import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from rambo_player import LoaderPlayer

SPEC = importlib.util.spec_from_file_location('rambo_main_entry', ROOT / 'scripts/studies/rambo/prepare-main-entry.py')
entry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(entry)


class RamboMainEntryTest(unittest.TestCase):
    def test_two_entry_points_preserve_future_score_and_sound_state(self):
        source = json.loads((ROOT / 'songs/rambo-loader.json').read_text())
        for cut in (1586, 1715):
            with self.subTest(cut=cut):
                prepared, registers = entry.rebase(source, cut)
                original, candidate = LoaderPlayer(source), LoaderPlayer(prepared)
                for tick in range(cut):
                    original.play(tick)
                self.assertEqual(registers, entry.registers_after(original.writes))
                for tick in range(300):
                    start_a, start_b = len(original.writes), len(candidate.writes)
                    original.play(cut + tick)
                    candidate.play(tick)
                    self.assertEqual([(r['address'], r['value']) for r in original.writes[start_a:]],
                                     [(r['address'], r['value']) for r in candidate.writes[start_b:]])
                self.assertEqual(original.data, candidate.data)
                self.assertEqual(original.sound, candidate.sound)
                self.assertEqual(original.score.voices, candidate.score.voices)

    def test_rejects_a_cut_outside_the_verified_range(self):
        source = json.loads((ROOT / 'songs/rambo-loader.json').read_text())
        for cut in (-1, 11000, True):
            with self.assertRaises(ValueError):
                entry.rebase(source, cut)


if __name__ == '__main__':
    unittest.main()
