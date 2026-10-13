import unittest

from model import (PulseProgram, PulseState, PitchState, ResonanceState,
                   advance_pwm, advance_pitch, initialize_pitch,
                   advance_resonance, initialize_resonance)


class MotionTests(unittest.TestCase):
    def setUp(self):
        self.motion = {0: 0x11, 1: 2, 2: 3, 3: 0x24, 32: 30,
                       33: 100, 34: 100, 35: 100, 36: 156, 37: 156, 38: 156, 39: 0}
        self.resonance = {3: 0, 4: 0, 5: 0, 12: 0xa2, 13: 0x62, 14: 0x32}

    def test_pwm_deadline_runs_marker_and_interpolation_in_same_invocation(self):
        program = PulseProgram(12, 0, 21)
        self.assertEqual(PulseState(0, 1, 0x0115),
                         advance_pwm(program, PulseState(11, 0, 0x08fc), self.motion))
        self.assertEqual(PulseState(0, 0x81, 0x03eb),
                         advance_pwm(program, PulseState(11, 3, 0x03fc), self.motion))

    def test_pwm_low_byte_wrap_does_not_propagate_to_high(self):
        self.assertEqual(PulseState(6, 1, 0x0111),
                         advance_pwm(PulseProgram(12, 0, 21), PulseState(5, 1, 0x01fc), self.motion))

    def test_aliased_base32_keeps_unshifted_index(self):
        self.assertEqual(PulseState(0, 0, 0x043f),
                         advance_pwm(PulseProgram(4, 32, 63), PulseState(3, 1, 0x0e04), self.motion))

    def test_signed_pitch_wrap_direction_and_delay_modes(self):
        self.assertEqual(PitchState(29, 1, 0x3426),
                         advance_pitch(8, PitchState(30, 1, 0x3426), self.motion))
        self.assertEqual(PitchState(0, 2, 99),
                         advance_pitch(8, PitchState(0, 1, 65535), self.motion))
        self.assertEqual(PitchState(0, 0x82, 0xff9c),
                         advance_pitch(8, PitchState(0, 0x81, 0), self.motion))
        self.assertEqual(PitchState(0x80, 1, 0x3426),
                         advance_pitch(8, PitchState(0x81, 0x87, 0x3426), self.motion))
        self.assertEqual(PitchState(0x80, 1, 0x3426),
                         advance_pitch(8, PitchState(0x80, 1, 0x3426), self.motion))

    def test_zero_resonance_duration_wraps_without_inventing_a_stage_count(self):
        state, shared = initialize_resonance(3, ResonanceState(255, 255), self.resonance, 0xa5)
        self.assertEqual((ResonanceState(1, 1), 5), (state, shared))
        state, shared = advance_resonance(3, state, self.resonance, shared)
        self.assertEqual((ResonanceState(0, 2), 5), (state, shared))
        self.assertEqual((ResonanceState(255, 2), 5),
                         advance_resonance(3, state, self.resonance, shared))

    def test_looped_resonance_preserves_routing_and_voice_order(self):
        state, shared = initialize_resonance(12, ResonanceState(0, 127), self.resonance, 0xa5)
        self.assertEqual((ResonanceState(3, 1), 0x65), (state, shared))
        self.assertEqual((ResonanceState(2, 0), 0x35),
                         advance_resonance(12, ResonanceState(1, 1), self.resonance, shared))
        extra = {36: 6, 37: 5, 38: 0x80}
        _, first = advance_resonance(12, ResonanceState(1, 1), self.resonance, 5)
        _, second = advance_resonance(36, ResonanceState(1, 1), extra, first)
        _, reversed_result = advance_resonance(12, ResonanceState(1, 1), self.resonance, second)
        self.assertEqual((0x85, 0x35), (second, reversed_result))

    def test_disabled_paths_and_inputs_remain_unchanged(self):
        snapshot = dict(self.motion)
        p = PulseState(255, 255, 65535)
        f = PitchState(255, 255, 65535)
        r = ResonanceState(255, 255)
        self.assertEqual(p, advance_pwm(PulseProgram(0, 0, 21), p, {}))
        self.assertEqual(f, advance_pitch(0, f, {}))
        self.assertEqual(f, initialize_pitch(0, f, {}))
        self.assertEqual((r, 0xa5), advance_resonance(0, r, {}, 0xa5))
        self.assertEqual(snapshot, self.motion)

    def test_missing_lookup_and_nonterminating_marker_loop_reject(self):
        with self.assertRaises(ValueError):
            advance_pitch(8, PitchState(0, 1, 0), {})
        with self.assertRaisesRegex(ValueError, 'marker'):
            advance_pwm(PulseProgram(1, 0, 1), PulseState(0, 0, 0), {index: 0x21 for index in range(128)})
        with self.assertRaises(ValueError):
            advance_pitch(0, PitchState(-1, 1, 0), {})


if __name__ == '__main__':
    unittest.main()
