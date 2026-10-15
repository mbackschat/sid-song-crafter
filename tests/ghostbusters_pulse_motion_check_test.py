"""Guard the retained non-pulse isolation summary against meaningful changes."""

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

from ghostbusters_stereo_test import articulated_example


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gb_motion_summary_tests', ROOT / 'scripts/studies/ghostbusters/check-pulse-motion.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class GhostbustersPulseMotionCheckTest(unittest.TestCase):
    def test_summary_retains_counts_and_hash_without_note_or_store_data(self):
        composition, _, _, baseline = articulated_example()
        candidate = deepcopy(baseline)
        candidate['support']['pulseMotion'] = 'triangle-600-a00'
        result = check.compare(composition, baseline, candidate)
        self.assertEqual((result['checkedMusicCalls'],result['addedPulseStores']), (300,600))
        self.assertEqual((result['supportPhrases'],result['supportGateCalls']), (3,120))
        self.assertEqual(len(result['gateLedgerSha256']),64)
        self.assertFalse({'writes','supportLedger','rootNote','sourceNote'} & set(result))

    def test_envelope_change_cannot_pass_as_pulse_only(self):
        composition, _, _, baseline = articulated_example()
        candidate = deepcopy(baseline)
        candidate['support']['pulseMotion'] = 'triangle-600-a00'
        candidate['support']['patch']['attack_decay'] ^= 1
        with self.assertRaisesRegex(ValueError, 'non-pulse store'):
            check.compare(composition, baseline, candidate)


if __name__ == '__main__':
    unittest.main()
