"""Guard the Gauntlet source data interventions and bounded executed contrast."""

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('gauntlet_probe', ROOT / 'scripts/studies/gauntlet/probe-contrast.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
SOURCE = ROOT / '.local/research/gauntlet-iii/Gauntlet_III.sid'


class GauntletContrastTest(unittest.TestCase):
    def test_data_patch_requires_original_value_and_payload_correspondence(self):
        header = dict(dataOffset=4, headerLoadAddress=0, loadAddress=0x1000)
        original = b'head\x00\x10\x2a\x0f'
        changed = probe.patch_source(original, header, [dict(address=0x1000, original=42, candidate=0)])
        self.assertEqual(changed, b'head\x00\x10\x00\x0f')
        self.assertEqual(original, b'head\x00\x10\x2a\x0f')
        for edit in (dict(address=0x1000, original=41, candidate=0), dict(address=0x0fff, original=0, candidate=0)):
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                probe.patch_source(original, header, [edit])

    @unittest.skipUnless(SOURCE.is_file(), 'Pinned private Gauntlet SID is required for source CPU corroboration')
    def test_initialized_cpu_controls_distinguish_natural_notes_and_edited_rests(self):
        original = SOURCE.read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(), probe.SOURCE_SHA)
        base = ROOT / 'build/follin-contrast'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as directory:
            output = Path(directory) / 'proof'
            result = probe.run(SOURCE, output, calls=817)
            findings = json.loads((output / 'findings.json').read_text())
            self.assertEqual(result['source']['selectedSubtune'], 2)
            self.assertEqual(result['method']['hostBase'], 0x8000)
            self.assertEqual((result['method']['clock'], result['method']['sidModel']), ('PAL', 'MOS6581'))
            self.assertGreater(result['initializedOriginal']['matchedContexts'], 4900)
            attack = findings['attack']['examples'][0]
            self.assertEqual((attack['voice'], attack['onsetCall'], attack['restoreCall']), (2, 336, 337))
            self.assertEqual((attack['attackControl'], attack['bodyControl'], attack['attackWord'], attack['bodyWord']),
                             (129, 17, 10240, 2864))
            self.assertEqual(attack['envelope'], [9, 15])
            retained = findings['pulseAcrossNotes']['retainedZeroDefaultNotes']
            self.assertEqual([(row['call'], row['beforeWord'], row['afterWord']) for row in retained[:3]],
                             [(768, 0, 0), (784, 640, 640), (800, 1280, 1280)])
            self.assertEqual(findings['pulseAcrossRests']['naturalGauntletRests'], 0)
            self.assertIn(800, findings['pulseAcrossRests']['controlledRestCalls'])
            self.assertTrue(findings['pulseAcrossRests']['completeVoice1PulseTrajectoryUnchanged'])
            self.assertEqual(len(result['interventions']['stationary-pwm']['changes']), 2)
            self.assertTrue(findings['pulseAcrossNotes']['stationaryChangesOnlyVoice1PulseStores'])
            for filename, fingerprint in result['outputHashes'].items():
                self.assertEqual(hashlib.sha256((output / filename).read_bytes()).hexdigest(), fingerprint['sha256'])
        self.assertEqual(SOURCE.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
