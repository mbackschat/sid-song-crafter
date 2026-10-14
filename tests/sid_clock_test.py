import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from sid_clock import clock_spec


class SidClockTest(unittest.TestCase):
    def test_explicit_targets_use_the_documented_machine_geometry(self):
        for name, clock, cycles in (("pal", 17734475 / 18, 19656), ("ntsc", 14318181.82 / 14, 17095)):
            with self.subTest(clock=name):
                spec = clock_spec(name)
                self.assertEqual((spec.name, spec.clock_hz, spec.frame_cycles), (name, clock, cycles))
                self.assertEqual(spec.ticks_per_second, clock / cycles)
        self.assertEqual(clock_spec(), clock_spec("pal"))

    def test_unknown_machine_variants_cannot_silently_use_pal(self):
        for value in (None, "PAL", "NTSC", "auto", "both", "old-ntsc", "pal-n", "", True):
            with self.subTest(clock=value), self.assertRaisesRegex(ValueError, "clock"):
                clock_spec(value)


if __name__ == "__main__":
    unittest.main()
