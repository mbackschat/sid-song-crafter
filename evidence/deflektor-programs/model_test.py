import unittest

from model import Stage, WaveProgram, WaveState, initialize_wave, advance_wave


class WaveModelTests(unittest.TestCase):
    def setUp(self):
        self.program = WaveProgram(False, (Stage(0x80, 2), Stage(0x16, 1)))

    def test_initialization_replaces_previous_program_position(self):
        for position in (0, 7, 127, 128, 255):
            with self.subTest(position=position):
                self.assertEqual(WaveState(3, 1, 0x81),
                                 initialize_wave(self.program, WaveState(255, position, 0x40)))

    def test_finite_program_holds_gate_clear_control_after_counter_wrap(self):
        self.assertEqual(WaveState(1, 255, 0x16), advance_wave(self.program, WaveState(1, 1, 0x80)))
        self.assertEqual(WaveState(0, 255, 0x16), advance_wave(self.program, WaveState(1, 255, 0x16)))
        self.assertEqual(WaveState(255, 255, 0x16), advance_wave(self.program, WaveState(0, 255, 0x16)))

    def test_loop_restarts_stage_zero_without_initial_extra_call(self):
        loop = WaveProgram(True, self.program.stages)
        self.assertEqual(WaveState(1, 0, 0x17), advance_wave(loop, WaveState(1, 1, 0x81)))
        self.assertEqual(WaveState(2, 1, 0x81), advance_wave(loop, WaveState(1, 0, 0x17)))

    def test_disabled_program_preserves_all_state(self):
        before = WaveState(0, 7, 0x80)
        self.assertEqual(before, initialize_wave(None, before))
        self.assertEqual(before, advance_wave(None, before))


if __name__ == '__main__':
    unittest.main()
