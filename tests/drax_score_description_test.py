import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('describe_drax_score', ROOT / 'scripts/studies/drax/describe-drax-score.py')
decoder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(decoder)
SOURCE = ROOT / '.local/research/fuer-elise/drax-fuer-elise.sid'
FRAMES = ROOT / 'build/reference-studies/drax/fuer-elise.frames.json'


@unittest.skipUnless(SOURCE.exists() and FRAMES.exists(), 'Requires the pinned local SID and generated reference frame oracle')
class DraxScoreDescriptionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_bytes()
        cls.score = decoder.describe_score(cls.source)
        cls.frames = json.loads(FRAMES.read_text())

    def test_one_complete_cycle_and_two_short_chord_releases(self):
        self.assertEqual({'bass': 26, 'lead': 123, 'chord': 26}, self.score['evidence']['noteCounts'])
        self.assertEqual(2018, self.score['range']['stopCall'])
        chord = {note['initCall']: note for note in self.score['roles']['chord']['notes']}
        self.assertEqual(392, chord[388]['gateOffCall'])
        self.assertEqual(1616, chord[1612]['gateOffCall'])
        self.assertEqual(4, len(chord[172]['frequencies']))
        self.assertEqual(0, self.score['patches'][chord[172]['patch']]['pulseInitial'])

    def test_source_observations_are_separate_from_executable_parameters(self):
        source_fields = {'sourceInstrumentOffset', 'waveProgramStartIndex', 'vibratoDelayCalls',
                         'vibratoCounter', 'vibratoIncrement'}
        chord_fields = {'pulseLowerHighByte', 'pulseUpperHighByte', 'toneSemitones'}
        for name, patch in self.score['patches'].items():
            self.assertIn('sourceEvidence', patch)
            expected = source_fields | (chord_fields if name.startswith('chord-') else set())
            self.assertEqual(expected, set(patch['sourceEvidence']))
            self.assertTrue(expected.isdisjoint(patch))
            self.assertIn('pulseInitial', patch)
        for note in self.score['roles']['chord']['notes']:
            self.assertNotIn('pulseHighByte', note)
            self.assertNotIn('baseFrequency', note)
            self.assertEqual({'baseFrequency'}, set(note['sourceEvidence']))

    def test_notes_and_chord_cycles_match_independent_frame_oracle(self):
        for role in self.score['roles'].values():
            offset = (role['voice'] - 1) * 7
            for note in role['notes']:
                call = note['initCall']
                self.assertEqual(9, self.frames[call][offset + 4])
                self.assertEqual(8, self.frames[call - 1][offset + 4])
                self.assertEqual(note['frequency'], self.frames[call - 1][offset] | self.frames[call - 1][offset + 1] << 8)
                if 'gateOffCall' in note:
                    self.assertEqual(0, self.frames[note['gateOffCall']][offset + 4] & 1)
                    self.assertEqual(1, self.frames[note['gateOffCall'] - 1][offset + 4] & 1)
                if 'frequencies' in note:
                    for age in range(2 * len(note['frequencies'])):
                        frame = self.frames[call + 1 + age]
                        self.assertEqual(note['frequencies'][age // 2], frame[offset] | frame[offset + 1] << 8)

    def test_fixture_reproduces_exactly(self):
        fixture = json.loads((ROOT / 'songs/studies/drax-full-reconstruction/full-composition.json').read_text())
        self.assertEqual(fixture, self.score)

    def test_source_identity_is_required(self):
        altered = bytearray(self.source)
        altered[22] ^= 1
        with self.assertRaisesRegex(ValueError, 'pinned DRAX'):
            decoder.describe_score(bytes(altered))


if __name__ == '__main__':
    unittest.main()
