from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from cybernoid_programs import advance_filter, advance_pulse


class CybernoidProgramsTests(unittest.TestCase):
    def test_opening_pulse_changes_steps_and_retains_turnaround_overshoot(self):
        slot = [7, 13, 3, 0x70, 6, 0x60, 9, 0x50]
        width, direction = 0x500, 1
        observed = {}
        for age in range(1, 64):
            width, direction = advance_pulse(width, direction, age, 0x64, slot)
            if age in (1, 3, 4, 6, 7, 9, 10, 22, 39, 56):
                observed[age] = (width, direction)
        self.assertEqual({1: (0x570, 1), 3: (0x650, 1), 4: (0x6b0, 1),
                          6: (0x770, 1), 7: (0x7c0, 1), 9: (0x860, 1),
                          10: (0x8c0, 1), 22: (0xd40, 0), 39: (0x6e0, 1),
                          56: (0xd40, 0)}, observed)

    def test_pulse_wrap_header_resets_low_to_one_not_zero(self):
        slot = [0x87, 13, 3, 0x70, 6, 0x60, 9, 0x50]
        self.assertEqual((0x701, 1), advance_pulse(0xcc0, 1, 22, 0x64, slot))

    def test_pulse_stage_can_force_descending_before_arithmetic(self):
        slot = [7, 13, 0x83, 0x70, 6, 0x60, 9, 0x50]
        self.assertEqual((0x890, 0), advance_pulse(0x900, 1, 3, 0x64, slot))
        self.assertEqual((0x960, 1), advance_pulse(0x900, 1, 4, 0x64, slot))

    def test_zero_selector_retains_pulse_without_needing_a_slot(self):
        self.assertEqual((0x800, 1), advance_pulse(0x800, 1, 200, 0x80))

    def test_pulse_word_arithmetic_wraps_before_boundary_comparison(self):
        slot = [0, 255, 127, 2, 127, 2, 127, 2]
        self.assertEqual((0xffff, 0), advance_pulse(1, 0, 2, 1, slot))
        self.assertEqual((0, 1), advance_pulse(0xfffe, 1, 2, 1, slot))

    def test_filter_program_retains_all_four_age_boundaries_and_byte_wrap(self):
        program = [0xa0, 0xfe, 1, 0xff, 0x62, 0x3f, 2, 0x22, 0x62, 0xa2]
        self.assertEqual((0x3f, 0xa0), advance_filter(99, 1, program))
        self.assertEqual((0x3f, 0xff), advance_filter(1, 2, program))
        self.assertEqual((0x3f, 0), advance_filter(255, 0x22, program))
        self.assertEqual((0x3f, 255), advance_filter(0, 0x62, program))
        self.assertEqual((0x3f, 0x62), advance_filter(0, 0xa2, program))

    def test_filter_uses_source_threshold_priority_without_sorting(self):
        program = [7, 1, 2, 3, 9, 0x1f, 30, 20, 10, 100]
        self.assertEqual((0x1f, 13), advance_filter(10, 15, program))
        self.assertEqual((0x1f, 7), advance_filter(10, 5, program))

    def test_invalid_program_inputs_fail_without_modifying_tables(self):
        slot = [7, 13, 3, 0x70, 6, 0x60, 9, 0x50]
        before = slot.copy()
        for bad in (-1, 65536, True):
            with self.subTest(width=bad), self.assertRaises(ValueError):
                advance_pulse(bad, 1, 2, 0x64, slot)
        with self.assertRaises(ValueError):
            advance_pulse(0x500, 1, 2, 0x64)
        with self.assertRaises(ValueError):
            advance_filter(0, 0, [0] * 9)
        self.assertEqual(before, slot)


if __name__ == '__main__':
    unittest.main()
