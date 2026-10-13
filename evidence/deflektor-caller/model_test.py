import unittest

from model import BodyState, PitchStage, ScorePitchProgram, ScorePitchState, advance_prelude, advance_score_pitch


class CallerTests(unittest.TestCase):
    def test_release_precedes_rest_and_global_skip_blocks_glide(self):
        state = BodyState(5, 2, 0x81, 65535, 5, 0, 255, 0, 2)
        after, programs = advance_prelude(state, global_skip=False)
        self.assertEqual((4, 1, 0x80, 65535, False),
                         (after.remaining, after.rest, after.control, after.frequency, programs))
        state = BodyState(3, 0, 0x41, 65535, 0, 0, 255, 0, 2)
        after, programs = advance_prelude(state, global_skip=True)
        self.assertEqual((2, 65535, 255, False),
                         (after.remaining, after.frequency, after.glide_remaining, programs))

    def test_final_glide_step_wraps_before_other_programs(self):
        state = BodyState(3, 0, 0x41, 0, 0, 0, 1, 0x20, 1)
        after, programs = advance_prelude(state, global_skip=False)
        self.assertEqual((65535, 0, True), (after.frequency, after.glide_remaining, programs))

    def test_finite_score_pitch_restores_base_once_then_holds(self):
        program = ScorePitchProgram(2, 1, False, (PitchStage(1, 1),))
        words = {24: 1000, 25: 1500}
        state = advance_score_pitch(program, ScorePitchState(1, 1, 0), pitch_index=24,
                                    detune=255, frequency_words=words)
        self.assertEqual(ScorePitchState(1, 255, 1755), state)
        state = advance_score_pitch(program, state, pitch_index=24, detune=255, frequency_words=words)
        self.assertEqual(ScorePitchState(0, 254, 1255), state)
        self.assertEqual(ScorePitchState(255, 254, 1255),
                         advance_score_pitch(program, state, pitch_index=24, detune=255, frequency_words=words))


if __name__ == '__main__':
    unittest.main()
