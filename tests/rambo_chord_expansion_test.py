from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from rambo_ensemble_test import preparer


CASE = 'songs/studies/rambo-chord-expansion/arrangement.json'


class RamboChordExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = preparer()
        cls.source = json.loads((ROOT / 'songs/rambo-loader.json').read_text())
        cls.baseline_config = json.loads((ROOT / 'songs/studies/rambo-ensemble/arrangement.json').read_text())
        cls.config = json.loads((ROOT / CASE).read_text())
        cls.baseline, cls.baseline_proof, _, cls.baseline_events = cls.module.prepare(cls.source, cls.baseline_config)
        cls.secondary, cls.proof, cls.source_events, cls.events = cls.module.prepare(
            cls.source, cls.config, arrangement_path=CASE)

    def test_changed_config_only_revises_the_third_role_calendar_and_case_annotations(self):
        self.assertEqual(self.baseline_config['sections'], self.config['sections'])
        self.assertEqual(self.baseline_config['roles'][:2], self.config['roles'][:2])
        old, new = deepcopy(self.baseline_config['roles'][2]), deepcopy(self.config['roles'][2])
        for field in ('role', 'chordRegionStride', 'entryFraction', 'maximumSpanCalls'):
            old.pop(field)
            new.pop(field)
        self.assertEqual(old, new)
        self.assertEqual((1, 0, 128), tuple(self.config['roles'][2][key]
                                         for key in ('chordRegionStride', 'entryFraction', 'maximumSpanCalls')))

    def test_both_existing_support_roles_keep_their_exact_note_gate_and_lifetime_ledgers(self):
        for voice in (0, 1):
            self.assertEqual([row for row in self.baseline_events if row['voiceIndex'] == voice],
                             [row for row in self.events if row['voiceIndex'] == voice])
        self.assertEqual(self.baseline['initialData'], self.secondary['initialData'])
        self.assertEqual(self.baseline['profile'], self.secondary['profile'])
        self.assertEqual(self.source['range'], self.secondary['range'])
        self.assertEqual(self.source['frequencyWords'], self.secondary['frequencyWords'])

    def test_every_actual_chord_region_has_three_distinct_supported_tones_through_the_whole_span(self):
        regions = [row for row in self.proof['harmonicRegions'] if row['kind'] == 'chord']
        self.assertEqual(42, len(regions))
        third = [row for row in self.events if row['voiceIndex'] == 2]
        self.assertEqual([(row['startCall'], row['endCall']) for row in regions],
                         [(row['startCall'], row['endCall']) for row in third])
        for region in regions:
            chord = [row for row in self.events if row['startCall'] == region['startCall']
                     and row['endCall'] == region['endCall']]
            self.assertEqual([0, 1, 2], [row['voiceIndex'] for row in sorted(chord, key=lambda row: row['voiceIndex'])])
            classes = {row['pitchIndex'] % 12 for row in chord}
            self.assertEqual(3, len(classes))
            self.assertLessEqual(classes, set(region['pitchClasses']))
            self.assertTrue(all(row['gateOffCall'] < row['endCall'] for row in chord))
        self.assertEqual((2354, 7474), (third[0]['startCall'], third[-1]['endCall']))
        self.assertEqual(5120, sum(row['endCall'] - row['startCall'] for row in third))
        self.assertTrue(any(len(row['pitchClasses']) == 4 for row in regions))

    def test_whole_call_calendar_and_final_clear_preserve_the_source_ending(self):
        self.assertEqual([56, 42, 42], self.proof['supportNoteCounts'])
        self.assertTrue(self.proof['exactEveryCallGatePitchAndLifetimeCalendar'])
        self.assertEqual([802, 802, 802], [row['soundingCalls'] for row in self.proof['mainPhraseRoleCoverage']])
        self.assertEqual(0, self.proof['ending']['activeMask'])
        self.assertEqual([0, 0, 0], self.proof['ending']['remainingLifetimes'])
        self.assertEqual(7474, self.proof['ending']['lastVoiceWriteTicks'][2])
        self.assertEqual(self.baseline_proof['ending']['lastVoiceWriteTicks'][:2],
                         self.proof['ending']['lastVoiceWriteTicks'][:2])

    def test_generated_provenance_names_the_new_case_and_pins_its_actual_config(self):
        self.assertEqual(CASE, self.secondary['sourceEvidence']['arrangement'])
        self.assertEqual(self.module.digest(self.config), self.secondary['sourceEvidence']['arrangementSha256'])
        self.assertEqual('songs/studies/rambo-ensemble/arrangement.json',
                         self.baseline['sourceEvidence']['arrangement'])
        self.assertFalse(any('spaced' in change for change in self.secondary['sourceEvidence']['changes']))

    def test_harmonic_and_execution_guards_reject_wrong_third_tone_and_overlong_release(self):
        third = next(row for row in self.events if row['voiceIndex'] == 2)
        wrong = deepcopy(third)
        wrong['pitchIndex'] += 1
        with self.assertRaisesRegex(ValueError, 'whole sounding span'):
            self.module.validate_support([wrong], self.proof['harmonicRegions'])
        changed = deepcopy(self.secondary)
        lifetime = next(node for name, node in changed['program'].items()
                        if name.startswith('support-3-') and node['kind'] == 'poke-data' and node['offset'] == 28)
        lifetime['value'] += 1
        with self.assertRaisesRegex(ValueError, 'lifetime calendar'):
            self.module.verify_support_calendar(changed, self.events)


if __name__ == '__main__':
    unittest.main()
