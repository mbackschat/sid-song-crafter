import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from native_frame_comparison import compare_frames


class NativeFrameComparisonTest(unittest.TestCase):
    def test_reports_allowed_pulse_change_without_accepting_pitch_change(self):
        reference = [[0] * 25 for _ in range(3)]
        candidate = [row[:] for row in reference]
        candidate[1][2] = 32
        result = compare_frames(reference, candidate, [2, 3])
        self.assertEqual(result['changedOffsets'], [2])
        self.assertEqual(result['changedFrames'], 1)
        candidate[2][0] = 1
        with self.assertRaisesRegex(ValueError, 'frame 2, offset 0'):
            compare_frames(reference, candidate, [2, 3])

    def test_rejects_missing_evidence_or_absent_intervention(self):
        for reference, candidate in [([], []), ([[0] * 25], []), ([[0] * 25], [[0] * 25])]:
            with self.subTest(reference=reference, candidate=candidate), self.assertRaises(ValueError):
                compare_frames(reference, candidate, [2])

    def test_second_sid_uses_concatenated_bank_offsets(self):
        reference = [[0] * 50]
        candidate = [[0] * 50]
        candidate[0][27] = 64
        self.assertEqual(compare_frames(reference, candidate, [27])['changedOffsets'], [27])

    def test_rejects_malformed_frames_and_outside_offsets(self):
        for reference, candidate, offsets in [([[0] * 24], [[1] * 24], [2]),
                                                ([[0] * 25], [[256] * 25], [2]),
                                                ([[0] * 25], [[1] * 25], [25])]:
            with self.subTest(offsets=offsets), self.assertRaises(ValueError):
                compare_frames(reference, candidate, offsets)


if __name__ == '__main__':
    unittest.main()
