import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('axel_model', ROOT / 'scripts/studies/axel-f/prepare-model-perception.py')
MODEL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODEL)


class ModelPreparationTest(unittest.TestCase):
    def test_pcm_controls_preserve_source_and_reject_changed_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.wav'
            pcm = b'\x01\x00' * (44100 * 11)
            MODEL.TRAP._write_audio(path, pcm)
            digest = MODEL.TRAP._sha(path.read_bytes())
            crop = MODEL.read_crop(path, digest)
            self.assertEqual(pcm[:926100], crop)
            cases = MODEL.control_cases(crop, crop)
            self.assertEqual(bytes(926100), cases['c03'])
            self.assertEqual(crop[:185220] * 5, cases['c04'])
            with self.assertRaisesRegex(ValueError, 'fingerprint'):
                MODEL.read_crop(path, 'changed')

    def test_frozen_prompt_has_no_source_identity_or_preference(self):
        self.assertIn('without identifying a source or ranking quality', MODEL.TRAP.PROMPT)
        for text in ('Hülsbeck', 'Axel', 'boring', 'preferred'):
            self.assertNotIn(text, MODEL.TRAP.PROMPT)


if __name__ == '__main__':
    unittest.main()
