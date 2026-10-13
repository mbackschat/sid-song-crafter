from dataclasses import replace
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from cybernoid_pitch import (GlideAction, PitchInputs, PitchParameters, PitchState,
                             advance_phase, advance_pitch, centered_pitch,
                             glide_divisor, rounded_glide_step)
from cybernoid_output import (advance_arpeggio, advance_pulse_run, apply_wave_program,
                              sweep_high_byte, voice_writes)
from cybernoid_state import CallerState, begin_row, begin_voice_call, body_prelude, filter_ownership, initialize_note


class CybernoidComponentTests(unittest.TestCase):
    def test_signed_phase_fallthrough_and_wait_bypass_match_isolated_source(self):
        self.assertEqual((0x81, 1), advance_phase(0x80, 1, 5))
        self.assertEqual(0x8f1, centered_pitch(0x8e1, 16, 0, 1, 0, 12))
        self.assertEqual(0x8e1, centered_pitch(0x8e1, 16, 5, 1, 0, 12))
        self.assertEqual(0x8d1, centered_pitch(0x8e1, 16, 5, 1, 13, 12))

    def test_glide_keeps_original_divider_and_signed_counter_behavior(self):
        self.assertEqual(32768, rounded_glide_step(32768, 2))
        self.assertEqual(0, rounded_glide_step(199, 200))
        self.assertEqual(14, glide_divisor(15, 17))
        self.assertEqual(15, glide_divisor(15, 129))

    def test_ordinary_vibrato_matches_extended_source_case_three(self):
        state = PitchState(28, 2273, 65535, 0, 0, 0, 255, 0, 0, 66, 28)
        inputs = PitchInputs(2273, 2408, 2273, 2273, 255, 1, 0, 129)
        result = advance_pitch(state, PitchParameters(83, 12), inputs)
        self.assertEqual(replace(state, frequency=2257, held_frequency=2257,
                                 vibrato_extent=5, vibrato_position=1), result.state)
        self.assertEqual(16, result.vibrato_delta)
        self.assertEqual(GlideAction.DISABLED, result.glide_action)
        self.assertEqual(65535, state.held_frequency)

    def test_arpeggio_consumes_reverse_offsets_and_wraps_pitch_index(self):
        words = list(range(256))
        result = advance_arpeggio(0, 47, [2, 0, 5, 8], words)
        self.assertEqual((2, 55, 55), (result.counter, result.pitch_index, result.frequency_word))
        result = advance_arpeggio(1, 255, [0, 2], words)
        self.assertEqual(1, result.pitch_index)

    def test_sweep_retains_distinct_saved_and_output_low_bytes(self):
        self.assertEqual((0xffef, 0xffcf), sweep_high_byte(0x00ef, 0x12cf))

    def test_pulse_run_retains_its_accumulator_until_reactivated(self):
        inactive = advance_pulse_run(False, 0, 200, 14, 5)
        self.assertEqual((1, 200, 14, None), (inactive.needs_initialization, inactive.low,
                                           inactive.high, inactive.pulse_override))
        active = advance_pulse_run(True, 1, 200, 14, 5)
        self.assertEqual(0x563, active.pulse_override)
        wrapped = advance_pulse_run(True, 0, 200, 14, 5)
        self.assertEqual(0x72b, wrapped.pulse_override)

    def test_expired_drum_still_suppresses_enabled_onset(self):
        result = apply_wave_program(0x90, 11, 0, 0, [11], [], [],
                                    20, 0x81, 0x41, 0xbeef, 0x21, 0x12cf, 0xfe)
        self.assertEqual((0x21, 0x12cf, 0xfe, 'expiredDrum'),
                         (result.wave, result.frequency_word, result.gate_mask, result.phase))

    def test_writer_preserves_store_order_and_masks_only_control(self):
        self.assertEqual([(0xd40b, 0x40), (0xd407, 0x34), (0xd408, 0x12),
                          (0xd409, 0xcd), (0xd40a, 0xab)],
                         voice_writes(1, 0x41, 0xfe, 0x1234, 0xabcd))

    def caller(self):
        return CallerState(row_remaining=1, row_duration=7, arpeggio_counter=2,
                           base_pitch=12, current_pitch=55, frequency=0x1234,
                           held_frequency=0x5678, held_high_copy=0x56, base_wave=0x21,
                           wave=0x81, pulse_flags=0, pulse_accumulator=0xabc,
                           pulse_output=0xdef, pulse_direction=0, packed_filter=0,
                           gate_mask=0xfe, note_age=255, vibrato_age=25,
                           glide_enabled=1, glide_active=1, vibrato_direction=255,
                           vibrato_position=1, filter_cutoff=99, pulse_run_flag=0,
                           pulse_run_low=200, pulse_run_high=14)

    def test_note_setup_retains_modulation_and_writes_frequency_high_first(self):
        before = self.caller()
        aged = begin_voice_call(before)
        self.assertEqual(0, aged.note_age)
        reset = begin_row(aged)
        self.assertEqual((0, 0, 0, 0), (reset.note_age, reset.vibrato_age,
                                       reset.glide_enabled, reset.glide_active))
        state, writes = initialize_note(reset, 0, 28, 0x8e1, [5, 0x41, 8, 0x89, 0, 0x53, 0x64, 0x80])
        self.assertEqual([(0xd401, 8), (0xd400, 0xe1), (0xd405, 8), (0xd406, 0x89)], writes)
        for field in ('current_pitch', 'vibrato_direction', 'vibrato_position',
                      'filter_cutoff', 'pulse_run_flag', 'pulse_run_low', 'pulse_run_high'):
            self.assertEqual(getattr(before, field), getattr(state, field), field)

    def test_scheduled_gate_and_repeated_owner_fallback_keep_separate_state(self):
        state = replace(self.caller(), gate_mask=255)
        record = [0, 0x41, 0, 0, 0x10, 0x53, 0x64, 0]
        nonscheduled, _, _ = body_prelude(state, 0, record, 1, False)
        scheduled, _, _ = body_prelude(state, 0, record, 2, True)
        self.assertEqual(255, nonscheduled.gate_mask)
        self.assertEqual(254, scheduled.gate_mask)
        first = filter_ownership(0, 0, 0, 0, 99)
        second = filter_ownership(0, 0, 0, first[0], first[1])
        self.assertEqual((0, 128, False, [(0xd418, 31), (0xd416, 128)]), first)
        self.assertEqual(first, second)


if __name__ == '__main__':
    unittest.main()
