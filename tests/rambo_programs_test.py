from copy import deepcopy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from rambo_programs import advance_voice


def sound_state(**changes):
    state = dict(frequencySteps=[0, 0, 0, 0], frequencyDurations=[0, 0, 0, 0],
                 frequencyDelay=0, frequencyFlags=0,
                 pulseDurations=[0, 0], pulseDelay=0, pulseFlags=0,
                 pulseSteps=[0, 0], pulseInitial=0, control=0x41,
                 releaseCountdown=0, life=100, frequency=0x1000,
                 frequencyRemaining=[0, 0, 0, 0], pulse=0x0800, pulseRemaining=[0, 0])
    state.update(changes)
    return state


class RamboProgramsTests(unittest.TestCase):
    def test_arpeggio_runs_backward_through_encoded_chord_bytes_and_restarts(self):
        state = sound_state(frequencySteps=[0x0700, 0x0c04, 0, 0],
                            frequencyDurations=[0, 0, 48, 3], frequencyDelay=255,
                            frequencyFlags=8)
        frequencies = {48: 0x1234, 55: 0x2345, 52: 0x3456, 60: 0x4567}
        pitches, positions = [], []
        for _ in range(6):
            state, writes = advance_voice(state, voice=0, row_remaining=0, frequency_words=frequencies)
            pitches.append(state['frequency'])
            positions.append(state['frequencyDelay'])
            self.assertEqual([(0xd400, state['frequency'] & 255), (0xd401, state['frequency'] >> 8)], writes)
        self.assertEqual([0x4567, 0x3456, 0x2345, 0x1234, 0x4567, 0x3456], pitches)
        self.assertEqual([2, 1, 0, 255, 2, 1], positions)

    def test_arpeggio_wraps_pitch_index_and_uses_current_position_even_when_nonzero(self):
        state = sound_state(frequencySteps=[0x0109, 0, 0, 0],
                            frequencyDurations=[0, 0, 250, 1], frequencyDelay=0,
                            frequencyFlags=10)
        updated, writes = advance_voice(state, voice=2, row_remaining=255, frequency_words={3: 0xabcd})
        self.assertEqual(255, updated['frequencyDelay'])
        self.assertEqual(0xabcd, updated['frequency'])
        self.assertEqual([(0xd40e, 0xcd), (0xd40f, 0xab)], writes)

    def test_physical_second_and_third_voices_reload_after_three_sequential_phases(self):
        state = sound_state(frequencySteps=[1, 2, 3, 99], frequencyFlags=5,
                            frequencyDurations=[1, 0, 0, 7], frequencyRemaining=[0, 0, 0, 1])
        for voice in (1, 2):
            with self.subTest(voice=voice):
                updated, _ = advance_voice(state, voice=voice, row_remaining=0)
                self.assertEqual(0x1001, updated['frequency'])
                self.assertEqual([0, 0, 0, 7], updated['frequencyRemaining'])
        updated, _ = advance_voice(state, voice=0, row_remaining=0)
        self.assertEqual(0x1063, updated['frequency'])
        self.assertEqual([0, 0, 0, 0], updated['frequencyRemaining'])

    def test_delayed_fourth_step_runs_on_all_voices_without_decrementing_phase_counters(self):
        state = sound_state(frequencySteps=[0, 0, 0, 65535], frequencyDelay=1,
                            frequencyFlags=2, frequencyRemaining=[1, 2, 3, 4], frequency=0)
        for voice in range(3):
            with self.subTest(voice=voice):
                updated, _ = advance_voice(state, voice=voice, row_remaining=0)
                self.assertEqual(65535, updated['frequency'])
                self.assertEqual(0, updated['frequencyDelay'])
                self.assertEqual([1, 2, 3, 4], updated['frequencyRemaining'])

    def test_second_voice_ignores_arpeggio_flag_and_still_runs_sequential_pitch(self):
        state = sound_state(frequencySteps=[2, 0, 0, 0], frequencyFlags=8,
                            frequencyRemaining=[1, 0, 0, 0])
        updated, writes = advance_voice(state, voice=1, row_remaining=0)
        self.assertEqual(0x1002, updated['frequency'])
        self.assertEqual([(0xd407, 2), (0xd408, 0x10)], writes)

    def test_release_pwm_and_pitch_keep_source_write_order_and_full_pulse_word(self):
        state = sound_state(releaseCountdown=1, pulseFlags=0x80,
                            pulseInitial=0xffff, pulseDurations=[1, 0], pulseSteps=[1, 0],
                            frequencyFlags=8, frequencyDurations=[0, 0, 2, 0], frequencyDelay=255)
        original = deepcopy(state)
        updated, writes = advance_voice(state, voice=0, row_remaining=0, frequency_words={2: 0x1234})
        self.assertEqual(original, state)
        self.assertEqual(0x41, updated['control'])
        self.assertEqual(100, updated['life'])
        self.assertEqual(0, updated['pulse'])
        self.assertEqual([(0xd404, 0x40), (0xd402, 0), (0xd403, 0), (0xd400, 0x34), (0xd401, 0x12)], writes)

    def test_terminal_clear_precedes_both_programs_without_requiring_frequency_table(self):
        state = sound_state(life=1, frequencyFlags=8, pulseFlags=0x80)
        updated, writes = advance_voice(state, voice=2, row_remaining=0)
        self.assertEqual(0, updated['life'])
        self.assertEqual(state['frequencyDelay'], updated['frequencyDelay'])
        self.assertEqual(state['pulseRemaining'], updated['pulseRemaining'])
        self.assertEqual([(address, 0) for address in range(0xd414, 0xd40d, -1)], writes)

    def test_arpeggio_requires_present_numeric_lookup_and_ten_byte_chord_bounds(self):
        state = sound_state(frequencyFlags=8)
        for values in (None, {}, {0: True}, {0: 65536}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                advance_voice(state, voice=0, row_remaining=0, frequency_words=values)
        for position in (10, 127):
            with self.subTest(position=position), self.assertRaises(ValueError):
                advance_voice(sound_state(frequencyFlags=8, frequencyDelay=position),
                              voice=2, row_remaining=0, frequency_words={0: 0})

    def test_zero_duration_programs_fail_instead_of_entering_source_infinite_reload(self):
        for changes in ({'pulseFlags': 1}, {'frequencyFlags': 1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                advance_voice(sound_state(**changes), voice=0, row_remaining=0)

    def test_named_state_rejects_unknown_fields_and_boolean_values(self):
        for changes in ({'life': True}, {'unknown': 0}, {'frequencySteps': [0] * 3}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                advance_voice(sound_state(**changes), voice=0, row_remaining=0)


if __name__ == '__main__':
    unittest.main()
