from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('prepare_rambo_elise', ROOT / 'scripts/studies/rambo/prepare-rambo-elise.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
from rambo_player import LoaderPlayer

SOURCE = json.loads((ROOT / 'songs/fuer-elise.json').read_text())
PROGRAMS = json.loads((ROOT / 'songs/rambo-loader.json').read_text())


class RamboEliseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.transfer, cls.reference, cls.report = prepare.prepare_elise(SOURCE, PROGRAMS)

    def test_all_source_notes_keep_pitch_and_absolute_onset(self):
        player = LoaderPlayer(self.transfer)
        for call in range(self.transfer['range']['auditCalls']):
            player.play(call)
        actual = [(r['voiceIndex'], r['call'], r['pitchIndex']) for r in player.score.operations if r['operation'] == 'note']
        expected = []
        words = PROGRAMS['frequencyWords']
        for voice, role in enumerate(('melody', 'bass', 'harmony')):
            events = next(v['events'] for v in SOURCE['voices'] if v['name'] == role)
            for event in events:
                if event['startBeat'] >= 12:
                    continue
                call = math.floor(event['startBeat'] * 60 / 72 * (17734475 / 18) / 19656 + 0.5)
                pitch = min(range(min(95, len(words))), key=lambda i: abs(69 + 12 * math.log2(words[i] * (17734475 / 18) / 2**24 / 440) - event['midi']))
                expected.append((voice, call, pitch))
        self.assertEqual(53, len(actual))
        self.assertEqual(sorted(expected), sorted(actual))
        self.assertEqual(0, player.score.active_mask)
        self.assertTrue(all(s[28] == 0 for s in player.sound))
        last = max(w['tick'] for w in player.writes if w['phase'] == 'play')
        self.assertLess(last, self.transfer['range']['auditCalls'] - 64)

    def test_reference_shares_graph_tuning_and_release_calendar(self):
        for field in ('program', 'voices', 'frequencyWords', 'range', 'morse', 'initialSound'):
            self.assertEqual(self.transfer[field], self.reference[field], field)
        for a, b in zip(self.transfer['initialData'], self.reference['initialData']):
            self.assertEqual(a[27:], b[27:])
            self.assertEqual(17, b[24])
            self.assertEqual((0, 0), (b[13], b[17]))
        self.assertEqual({'melody': 35, 'bass': 6, 'harmony': 12}, self.report['retainedEvents'])
        self.assertNotEqual(self.transfer['sourceEvidence']['changes'], self.reference['sourceEvidence']['changes'])

    def test_rejects_overlap_boundary_crossing_and_unrepresentable_tempo(self):
        for mutate in ('overlap', 'crossing', 'tempo'):
            source = deepcopy(SOURCE)
            melody = next(v for v in source['voices'] if v['name'] == 'melody')
            if mutate == 'overlap':
                melody['events'].insert(1, deepcopy(melody['events'][0]))
            elif mutate == 'crossing':
                melody['events'][0]['durationBeats'] = 13
            else:
                source['quarterBpm'] = 100000
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                prepare.prepare_elise(source, PROGRAMS)

    def test_patch_edits_are_taken_from_live_numeric_program(self):
        changed = deepcopy(PROGRAMS)
        changed['initialData'][0][18] += 1
        transfer, _, _ = prepare.prepare_elise(SOURCE, changed)
        self.assertNotEqual(self.transfer['initialData'][0], transfer['initialData'][0])


if __name__ == '__main__':
    unittest.main()
