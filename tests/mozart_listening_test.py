import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "mozart_listening", ROOT / "scripts/studies/mozart-minuet/prepare-listening.py"
)
listening = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(listening)


class MozartListeningTests(unittest.TestCase):
    def setUp(self):
        self.conversion = {"totalTicks": 49, "ticksPerSecond": 50}
        first = [0] * 50
        first[:14] = first[25:39] = [37, 21, 0, 8, 65, 10, 73, 12, 4, 0, 5, 65, 7, 102]
        first[14:21] = [25, 12, 0, 6, 65, 4, 87]
        first[39:46] = [43, 10, 0, 0, 17, 6, 86]
        first[21:23], first[46:48] = [3, 17], [5, 31]
        first[24] = first[49] = 15
        self.frames = [first.copy() for _ in range(101)]
        self.frames[-1][24] = self.frames[-1][49] = 0

    def test_accepts_complete_mirrored_roles_with_distinct_unfiltered_inner_parts(self):
        listening.verify_frames(self.frames, self.conversion)

    def test_rejects_truncated_and_extended_audits(self):
        for frames in (self.frames[:1], self.frames[:-1], self.frames + [self.frames[-1]]):
            with self.subTest(calls=len(frames)), self.assertRaisesRegex(ValueError, "complete native audit"):
                listening.verify_frames(frames, self.conversion)
        with self.assertRaisesRegex(ValueError, "complete post-call"):
            listening.verify_frames([], self.conversion)

    def test_rejects_a_wrong_register_bank_width_late_in_the_performance(self):
        for width in (25, 49, 51):
            frames = copy.deepcopy(self.frames)
            frames[-2] = [0] * width
            with self.subTest(width=width), self.assertRaisesRegex(ValueError, "two concatenated SID"):
                listening.verify_frames(frames, self.conversion)

    def test_rejects_each_mismatched_melody_or_bass_register_late_in_the_performance(self):
        for register in range(14):
            frames = copy.deepcopy(self.frames)
            frames[-2][25 + register] ^= 1
            with self.subTest(register=register), self.assertRaisesRegex(ValueError, "Duplicated melody/bass"):
                listening.verify_frames(frames, self.conversion)

    def test_rejects_asymmetric_master_volume_on_either_chip(self):
        for register in (24, 49):
            frames = copy.deepcopy(self.frames)
            frames[-2][register] = 14
            with self.subTest(register=register), self.assertRaisesRegex(ValueError, "master volumes differ"):
                listening.verify_frames(frames, self.conversion)

    def test_rejects_disconnecting_either_independent_inner_voice(self):
        for register in (24, 49):
            frames = copy.deepcopy(self.frames)
            frames[-2][register] |= 128
            with self.subTest(register=register), self.assertRaisesRegex(ValueError, "inner voice is disconnected"):
                listening.verify_frames(frames, self.conversion)

    def test_rejects_filter_routing_on_either_chip(self):
        for register in (23, 48):
            for voice_bit in (1, 2, 4):
                frames = copy.deepcopy(self.frames)
                frames[-2][register] |= voice_bit
                with self.subTest(register=register, voice=voice_bit), self.assertRaisesRegex(ValueError, "filter routing"):
                    listening.verify_frames(frames, self.conversion)

    def test_rejects_sync_or_ring_dependency_for_every_physical_voice(self):
        for register in (4, 11, 18, 29, 36, 43):
            for dependency in (2, 4):
                frames = copy.deepcopy(self.frames)
                frames[-2][register] |= dependency
                if register < 14:
                    frames[-2][register + 25] |= dependency
                elif register in (29, 36):
                    frames[-2][register - 25] |= dependency
                with self.subTest(register=register, dependency=dependency), self.assertRaisesRegex(ValueError, "cross-oscillator dependency"):
                    listening.verify_frames(frames, self.conversion)


if __name__ == "__main__":
    unittest.main()
