"""Guard bounded editable Take On Me sound against independent execution."""

from dataclasses import replace
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / 'scripts/studies/take-on-me'
sys.path.insert(0, str(STUDY))
import programs


class TakeOnMeSoundTest(unittest.TestCase):
    def test_table_jump_keeps_terminal_hold_and_rejects_cycles(self):
        self.assertEqual(programs.table_step((8, 3, 255, 0), 2), (8, 1))
        self.assertEqual(programs.table_step((129, 65, 16, 254), 3), (None, 3))
        with self.assertRaisesRegex(ValueError, 'does not reach a value or hold'):
            programs.table_step((255, 0), 0)

    def test_pulse_word_crossing_stops_after_the_overshooting_body(self):
        motion = programs.SweepProgram(0, 96, 0x8c0, 255, 0, 0, 0)
        word, initial, direction = programs.sweep_step(0x900, 255, 0, motion)
        self.assertEqual((word, initial, direction), (0x8a0, 255, 255))
        self.assertEqual(programs.sweep_step(word, initial, direction, motion), (word, 255, 255))

    def test_sweep_phase_changes_keep_the_overshooting_word(self):
        motion = programs.SweepProgram(1, 48, 0x200, 1, 48, 0xe00, 0)
        self.assertEqual(programs.sweep_step(0xdf0, 255, 1, motion), (0xe20, 255, 0))
        self.assertEqual(programs.sweep_step(0x210, 255, 0, motion), (0x1e0, 255, 1))

    def test_glide_suppresses_vibrato_until_target_crossing(self):
        state = programs.VoiceState(frequency=1000, base_note=10, glide_target=11,
                                   glide_step=30, glide_active=1, vibrato_delay=7)
        instrument = programs.Instrument(vibrato_program=1)
        sound = programs.Programs(frequencies={10: 1000, 11: 1020},
                                 vibratos={1: programs.VibratoProgram(9, 0, 3, 2)})
        result = programs.body_step(state, programs.FilterState(), instrument, sound, 1)
        self.assertEqual((result.state.frequency, result.state.glide_active), (1020, 0))
        self.assertEqual(result.state.vibrato_delay, 7)
        self.assertEqual(state.frequency, 1000)

    def test_vibrato_direction_change_has_a_stationary_frame(self):
        state = programs.VoiceState(frequency=1000, base_note=10, onset_initial=255,
                                   vibrato_initial=255, vibrato_delay=0,
                                   vibrato_remaining=0, vibrato_direction=0, vibrato_step=5)
        sound = programs.Programs(frequencies={10: 1000, 11: 1020},
                                 vibratos={1: programs.VibratoProgram(9, 0, 3, 2)})
        result = programs.body_step(state, programs.FilterState(),
                                    programs.Instrument(vibrato_program=1), sound, 1)
        self.assertEqual((result.state.frequency, result.state.vibrato_remaining,
                          result.state.vibrato_direction), (1000, 3, 1))
        moved = programs.body_step(result.state, result.filter_state,
                                  programs.Instrument(vibrato_program=1), sound, 1)
        self.assertEqual(moved.state.frequency, 1005)

    def test_standalone_vibrato_helper_preserves_input_state(self):
        state = programs.VoiceState(frequency=1000, base_note=10)
        changed = programs.vibrato_step(state, programs.VibratoProgram(9, 0, 3, 2), {10: 1000, 11: 1020})
        self.assertEqual(state, programs.VoiceState(frequency=1000, base_note=10))
        self.assertEqual((changed.vibrato_delay, changed.vibrato_step), (8, 5))

    def test_voice_zero_owns_filter_and_ordered_output(self):
        state = programs.VoiceState(frequency=0x1234, pulse=0xabc, control=65)
        self.assertEqual(programs.voice_output(state, 2),
                         [(0xd412, 65), (0xd411, 10), (0xd410, 188), (0xd40f, 18), (0xd40e, 52)])
        instrument = programs.Instrument(pulse=512, onset_control=65,
                                         attack_decay=2, sustain_release=92, filter_word=0xc000)
        before = programs.FilterState(word=0x2000, initial=255, direction=255)
        result = programs.note_setup(state, before, instrument, 1, {0: 4321})
        self.assertEqual(result.filter_state, before)
        result = programs.note_setup(replace(state, base_note=20), before, instrument, 0, {20: 4321})
        self.assertEqual((result.filter_state.word, result.filter_state.initial), (0xc000, 0))
        self.assertEqual(result.writes, [(0xd405, 2), (0xd406, 92)])
        self.assertEqual(programs.filter_output(result.filter_state), [(0xd415, 0), (0xd416, 192)])

    def test_invalid_parameters_and_missing_lookup_are_rejected(self):
        for state in (programs.VoiceState(frequency=65536), programs.VoiceState(control=True)):
            with self.assertRaises(ValueError):
                programs.voice_output(state, 0)
        with self.assertRaisesRegex(ValueError, 'Missing frequency index 20'):
            programs.note_setup(programs.VoiceState(base_note=20), programs.FilterState(),
                                programs.Instrument(), 0, {})
        with self.assertRaises(ValueError):
            programs.voice_output(programs.VoiceState(), 3)

    def test_original_routines_and_isolated_parameter_controls(self):
        source = ROOT / '.local/research/take-on-me/Take_on_Me.sid'
        if not source.exists():
            self.skipTest('Pinned private reference is not installed')
        spec = importlib.util.spec_from_file_location('take_on_me_sound_probe', STUDY / 'sound-probe.py')
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)
        result = probe.verify(source.read_bytes(), calls=1024, controls=True)
        self.assertEqual(result['sourceSha256'], probe.SOURCE_SHA)
        self.assertGreater(result['boundaryComparisons'], 3000)
        self.assertEqual(result['instrumentIds'], [0, 1, 2, 3, 4])
        self.assertEqual(len(result['controls']), 5)
        self.assertTrue(all(row['onlyDeclaredPortsChanged'] for row in result['controls']))


if __name__ == '__main__':
    unittest.main()
