"""Guard the bounded Commando drum substitution and mutable PWM evidence."""

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('commando_contrast', ROOT / 'scripts/studies/commando/probe-contrast.py')
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class CommandoContrastTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ROOT / '.local/commando-source.sid'
        if not cls.source.exists():
            raise unittest.SkipTest('Pinned private Commando source is not installed')
        cls.data = cls.source.read_bytes()
        cls.original = probe.execute(cls.data, 128)
        cls.candidate_data, cls.change = probe.remove_record7_drum(cls.data)
        cls.candidate = probe.execute(cls.candidate_data, 128)

    def test_noise_substitution_returns_same_voice_to_tone(self):
        findings = probe.analyze(self.original, self.candidate)
        example = findings['channelSharing']['examples'][0]
        self.assertEqual((example['voice'], example['setupCall'], example['noiseCall'], example['restoreCall']), (1, 0, 1, 3))
        self.assertEqual((example['setupControl'], example['noiseControl'], example['restoreControl']), (0x15, 0x80, 0x14))
        self.assertTrue(example['envelopeRetained'])
        self.assertTrue(any(row['voice'] == 2 and row['instrument'] == 1 for row in findings['channelSharing']['examples']))

    def test_low_byte_pwm_retains_high_byte_and_incoming_carry(self):
        self.assertEqual(probe.advance_low_pulse(0xff, 0x16, 0), 0x15)
        self.assertEqual(probe.advance_low_pulse(0xff, 0x16, 1), 0x16)
        contexts = self.original['pwm']
        self.assertTrue(contexts)
        for row in contexts:
            self.assertEqual(row['afterLow'], probe.advance_low_pulse(row['beforeLow'], row['step'], row['incomingCarry']))
            self.assertEqual(row['afterHigh'], row['beforeHigh'])
        self.assertTrue(any(row['incomingCarry'] == 0 for row in contexts))

    def test_new_note_reads_mutated_record_and_skips_body(self):
        notes = [row for row in self.original['notes'] if row['voice'] == 3 and row['instrument'] == 2]
        self.assertEqual([(row['call'], row['pulseWord']) for row in notes[:4]], [(0, 0x180), (18, 0x1f6), (36, 0x164), (48, 0x156)])
        bodies = {(row['voice'], row['call']) for row in self.original['bodies']}
        self.assertFalse(any((row['voice'], row['call']) in bodies for row in self.original['notes']))
        self.assertTrue(all(row['phaseBefore'] == row['phaseAfter'] for row in self.original['notes']))

    def test_intervention_changes_only_verified_byte_and_protected_outputs(self):
        self.assertEqual(self.change, {'address': 0x55d0, 'original': 5, 'candidate': 4, 'parameter': 'instrument 7 drum flag'})
        self.assertEqual(sum(left != right for left, right in zip(self.data, self.candidate_data)), 1)
        findings = probe.analyze(self.original, self.candidate)
        self.assertTrue(findings['intervention']['protectedProjectionEqual'])
        self.assertTrue(findings['intervention']['record7NoiseRemoved'])
        self.assertEqual(self.source.read_bytes(), self.data)

    def test_protected_projection_rejects_companion_change(self):
        altered = dict(self.candidate, stores=[dict(row) for row in self.candidate['stores']])
        row = next(row for row in altered['stores'] if row['address'] == 0xd408)
        row['value'] ^= 1
        with self.assertRaisesRegex(ValueError, 'protected'):
            probe.analyze(self.original, altered)

    def test_exact_removal_rejects_changed_remaining_voice1_pitch(self):
        altered = dict(self.candidate, stores=[dict(row) for row in self.candidate['stores']])
        row = next(row for row in altered['stores'] if row['address'] == 0xd401 and row['pc'] == 0x5386)
        row['value'] ^= 1
        with self.assertRaisesRegex(ValueError, 'exact record 7'):
            probe.analyze(self.original, altered)


if __name__ == '__main__':
    unittest.main()
