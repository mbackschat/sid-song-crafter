from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from sidwizard_export_test import original_module
from sample_exports import stereo_module, split_module


class SampleExportsTest(unittest.TestCase):
    def test_stereo_keeps_patterns_instruments_and_original_voice_indices(self):
        source = original_module()
        stereo = stereo_module(source)
        before = split_module(source)
        after = split_module(stereo)
        self.assertEqual(after['sequences'], [before['sequences'][0], before['sequences'][1],
                         bytes((2, 0xfe, 2)), before['sequences'][0], bytes((2, 0xfe, 2)), before['sequences'][2]])
        self.assertEqual(after['patterns'][:-1], before['patterns'])
        self.assertEqual(after['tail'], before['tail'])
        self.assertEqual(after['header'][:4], b'SWMS')

    def test_rejects_already_stereo_instead_of_duplicating_it(self):
        with self.assertRaisesRegex(ValueError, 'one SID'):
            stereo_module(stereo_module(original_module()))


if __name__ == '__main__':
    unittest.main()
