import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


def preparer():
    path = ROOT / 'scripts/studies/rambo/prepare-ensemble.py'
    spec = importlib.util.spec_from_file_location('rambo_ensemble', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RamboEnsembleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = preparer()
        cls.source = json.loads((ROOT / 'songs/rambo-loader.json').read_text())
        cls.config = json.loads((ROOT / 'songs/studies/rambo-ensemble/arrangement.json').read_text())
        cls.original = copy.deepcopy(cls.source)
        cls.secondary, cls.proof, cls.source_events, cls.events = cls.module.prepare(cls.source, cls.config)

    def test_source_and_primary_contract_remain_unchanged(self):
        self.assertEqual(self.original, self.source)
        self.assertEqual(self.source['profile'], self.secondary['profile'])
        self.assertEqual(self.source['range'], self.secondary['range'])
        self.assertEqual(self.source['frequencyWords'], self.secondary['frequencyWords'])
        self.assertEqual(11000, self.proof['checkedCalls'])

    def test_chord_evidence_preserves_suspensions_and_altered_sets(self):
        regions = self.proof['harmonicRegions']
        self.assertEqual([2, 5, 10], next(r['pitchClasses'] for r in regions if r['startCall'] == 2354))
        self.assertEqual([0, 5, 7], next(r['pitchClasses'] for r in regions if r['startCall'] == 2610))
        self.assertEqual([2, 6, 10], next(r['pitchClasses'] for r in regions if r['startCall'] == 5810))
        self.assertEqual([0, 2, 6, 9], next(r['pitchClasses'] for r in regions if r['startCall'] == 5874))
        self.assertTrue(all(r['sourceRows'] for r in regions))

    def test_support_uses_three_roles_in_main_phrase_and_gives_source_intro_space(self):
        self.assertEqual({0, 1, 2}, {event['voiceIndex'] for event in self.events})
        phrase = self.proof['mainPhraseRoleCoverage']
        self.assertEqual([0, 1, 2], [r['voiceIndex'] for r in phrase])
        self.assertTrue(all(r['soundingCalls'] > 0 for r in phrase))
        self.assertGreaterEqual(min(e['startCall'] for e in self.events), 561)
        self.assertTrue(all(e['endCall'] - e['startCall'] >= 32 for e in self.events))
        self.assertLess(len(self.events), len(self.source_events) // 3)

    def test_whole_lifetime_guard_rejects_a_note_carried_into_changed_harmony(self):
        event = next(e for e in self.events if e['voiceIndex'] == 0 and e['startCall'] == 2354)
        faulty = copy.deepcopy(event)
        faulty['endCall'] = 2611
        with self.assertRaisesRegex(ValueError, 'whole sounding span'):
            self.module.validate_support([faulty], self.proof['harmonicRegions'])

    def test_whole_lifetime_guard_rejects_a_wrong_pitch_inside_correct_boundary(self):
        faulty = copy.deepcopy(self.events[0])
        faulty['pitchIndex'] += 1
        with self.assertRaisesRegex(ValueError, 'whole sounding span'):
            self.module.validate_support([faulty], self.proof['harmonicRegions'])

    def test_numeric_execution_proves_score_pitches_and_all_natural_tail_clears(self):
        self.assertEqual(0, self.proof['ending']['activeMask'])
        self.assertEqual([0, 0, 0], self.proof['ending']['remainingLifetimes'])
        self.assertTrue(all(c < 10400 for c in self.proof['ending']['lastVoiceWriteTicks']))
        self.assertTrue(self.proof['exactGeneratedNoteLedger'])
        self.assertFalse(any(n['kind'] == 'code' for n in self.secondary['program'].values()))
        self.assertTrue(all(p[13] == 0 and p[24] & 6 == 0 for p in self.secondary['initialData']))

    def test_numeric_guard_rejects_an_early_gate_off_even_when_notes_match(self):
        changed = copy.deepcopy(self.secondary)
        gate = next(node for node in changed['program'].values()
                    if node['kind'] == 'poke-data' and node['offset'] == 27)
        gate['value'] -= 1
        with self.assertRaisesRegex(ValueError, 'gate calendar'):
            self.module.verify_support_calendar(changed, self.events)

    def test_numeric_guard_rejects_a_release_lifetime_crossing_its_harmonic_span(self):
        changed = copy.deepcopy(self.secondary)
        lifetime = next(node for node_id, node in changed['program'].items()
                        if node_id.startswith('support-3-') and node['kind'] == 'poke-data' and node['offset'] == 28)
        lifetime['value'] += 1
        with self.assertRaisesRegex(ValueError, 'lifetime calendar'):
            self.module.verify_support_calendar(changed, self.events)

    def test_source_change_is_rejected_before_derivation(self):
        changed = copy.deepcopy(self.source)
        changed['program']['voice-1-row-0090']['sourceNote'] += 1
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            self.module.prepare(changed, self.config)


if __name__ == '__main__':
    unittest.main()
