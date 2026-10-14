"""Guard independent Billie Jean sound and original-routine comparisons."""

from dataclasses import replace
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / 'scripts/studies/billie-jean'
sys.path.insert(0, str(STUDY))
import billie_jean_programs as sound


def bank(pitches=None, waves=None):
    return sound.Programs(frequencies={index: index * 100 for index in range(96)},
        pitches=[126] * 256 if pitches is None else pitches,
        waveforms=[65] * 256 if waves is None else waves)


class BillieJeanSoundTest(unittest.TestCase):
    def test_restart_keeps_old_pitch_and_pulse_direction_and_skips_writer(self):
        state = sound.VoiceState(frequency=1234, pulse=0x345, pulse_direction=1,
            gate_mask=254, base_note=24, age=40, wave_cursor=5)
        instrument = sound.Instrument(attack_decay=3, sustain_release=88, pulse_initial=207,
            vibrato_seed=4, filter_initialize=1, filter_start=32)
        result = sound.note_setup(state, sound.FilterState(), instrument, bank(), 0)
        self.assertEqual(result.writes, [(0xd404, 0), (0xd405, 3), (0xd406, 88), (0xd404, 9)])
        self.assertEqual((result.state.frequency, result.state.pulse, result.state.pulse_direction), (1234, 0xcfcf, 1))
        self.assertEqual((result.state.gate_mask, result.state.age, result.state.wave_cursor), (255, 0, 0))
        self.assertEqual(result.filter_state.cutoff, 32)
        self.assertEqual(state.age, 40)

    def test_legato_retains_motion_and_uses_wrapped_lookup_index(self):
        state = sound.VoiceState(base_note=182, gate_mask=255, pulse=0x345,
            wave_cursor=5, age=128, waveform=65)
        result = sound.note_setup(state, sound.FilterState(cutoff=17),
            sound.Instrument(filter_initialize=1, filter_start=32), bank(), 2)
        self.assertEqual(result.state.frequency, 5400)
        self.assertEqual((result.state.wave_cursor, result.state.age, result.filter_state.cutoff), (5, 128, 17))
        self.assertEqual(result.writes, [(0xd412, 65), (0xd40e, 24), (0xd40f, 21), (0xd410, 69), (0xd411, 3)])

    def test_pwm_masks_high_bits_and_keeps_overshoot_on_direction_change(self):
        state = sound.VoiceState(pulse=0xcfff, pulse_direction=0, base_note=24)
        instrument = sound.Instrument(pulse_step=16, pulse_upper=0, pulse_lower=0)
        result = sound.body_step(state, sound.FilterState(), instrument, bank(), 1, 2)
        self.assertEqual((result.state.pulse, result.state.pulse_direction), (15, 1))

    def test_table_loop_retains_paired_waveform_and_pitch_order(self):
        pitches, waves = [126] * 256, [0] * 256
        pitches[8:12] = [128 | 20, 2, 127, 126]
        waves[8:12] = [129, 65, 0, 0]
        instrument = sound.Instrument(wave_loop=1)
        result = sound.body_step(sound.VoiceState(base_note=24, instrument_offset=8,
            wave_cursor=2, gate_mask=255), sound.FilterState(), instrument, bank(pitches, waves), 0, 2)
        self.assertEqual((result.state.frequency, result.state.waveform, result.state.wave_cursor), (2600, 65, 2))
        pitches[9] = 127
        with self.assertRaisesRegex(ValueError, 'does not reach a value or hold'):
            sound.body_step(sound.VoiceState(instrument_offset=8, wave_cursor=2),
                sound.FilterState(), instrument, bank(pitches, waves), 0, 2)

    def test_downward_glide_bypasses_filter_and_late_gate_and_clamps_at_equality(self):
        state = sound.VoiceState(base_note=24, glide_target=20, glide_step=100,
            frequency=2100, age=1, gate_mask=255, remaining=0)
        instrument = sound.Instrument(filter_enabled=1, filter_step=1, filter_mode=32)
        result = sound.body_step(state, sound.FilterState(cutoff=32, routing=240), instrument, bank(), 0, 1)
        self.assertEqual((result.state.frequency, result.state.glide_step, result.state.gate_mask), (2000, 0, 255))
        self.assertEqual(result.filter_state, sound.FilterState(cutoff=32, routing=240))
        self.assertEqual(len(result.writes), 5)

    def test_high_note_bit_bypasses_zero_vibrato_delay_without_changing_pitch_alias(self):
        instrument = sound.Instrument(vibrato_step=16, vibrato_period=0, vibrato_half=0)
        state = sound.VoiceState(base_note=182, frequency=5400, age=1, vibrato_phase=1)
        result = sound.body_step(state, sound.FilterState(), instrument, bank(), 0, 2)
        self.assertEqual((result.state.frequency, result.state.vibrato_phase), (5416, 1))
        unchanged = sound.body_step(replace(state, base_note=54), sound.FilterState(), instrument, bank(), 0, 2)
        self.assertEqual(unchanged.state.frequency, 5400)

    def test_age_saturates_at_signed_boundary_and_global_volume_is_last(self):
        for age, expected in ((0, 1), (127, 128), (128, 128), (255, 255)):
            state = sound.VoiceState(age=age)
            self.assertEqual(sound.advance_age(state).age, expected)
            self.assertEqual(state.age, age)
        self.assertEqual(sound.global_output(sound.FilterState(mode=48)), [(0xd418, 59)])

    def test_invalid_numeric_state_and_missing_frequency_fail(self):
        with self.assertRaises(ValueError):
            sound.advance_age(sound.VoiceState(age=True))
        with self.assertRaisesRegex(ValueError, 'Missing frequency index 54'):
            sound.note_setup(sound.VoiceState(base_note=182, gate_mask=255), sound.FilterState(),
                sound.Instrument(), sound.Programs(), 0)

    def test_small_baseline_ignores_unused_control_window_and_keeps_call_bounds(self):
        spec = importlib.util.spec_from_file_location('billie_jean_window_guard', STUDY / 'sound-probe.py')
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)
        data = b'Window validation fixture; CPU execution is mocked'
        with patch.object(probe, 'SOURCE_SHA', hashlib.sha256(data).hexdigest()), \
                patch.object(probe, 'execute', return_value={}) as execute:
            for calls in (1, 64, 7107):
                with self.subTest(calls=calls):
                    result = probe.verify(data, calls=calls, controls=False)
                    self.assertEqual(calls, result['playCalls'])
                    execute.assert_called_once_with(data, calls, retain=True)
                    execute.reset_mock()
            for calls in (0, 7108, True, 1.0):
                with self.subTest(calls=calls), self.assertRaisesRegex(ValueError, 'Sound proof supports'):
                    probe.verify(data, calls=calls, controls=False)
                execute.assert_not_called()
            for control_calls in (0, 65, True, 1.0):
                with self.subTest(control_calls=control_calls), self.assertRaisesRegex(ValueError, 'Control calls'):
                    probe.verify(data, calls=64, controls=True, control_calls=control_calls)
                execute.assert_not_called()
            with self.assertRaisesRegex(ValueError, 'Control calls'):
                probe.verify(data, calls=64, controls=True)
            with self.assertRaisesRegex(ValueError, 'source hash'):
                probe.verify(data + b'changed', calls=64, controls=False)
            execute.assert_not_called()

    def test_original_source_boundaries_and_isolated_controls(self):
        source = ROOT / '.local/research/billie-jean/Billie_Jean.sid'
        if not source.exists():
            self.skipTest('Pinned private reference is not installed')
        spec = importlib.util.spec_from_file_location('billie_jean_sound_probe', STUDY / 'sound-probe.py')
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)
        result = probe.verify(source.read_bytes(), calls=1500, controls=True, retain=False)
        self.assertGreater(result['boundaryComparisons'], 6600)
        self.assertEqual(len(result['controls']), 4)
        self.assertTrue(all(control['onlyDeclaredPortsChanged'] for control in result['controls']))


if __name__ == '__main__':
    unittest.main()
