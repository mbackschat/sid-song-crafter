from copy import deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from monty_title_player import compute_player, compute_writes
from monty_title_programs import Instrument, VoiceState, PitchLookups, advance_body, initialize_note


def fixture():
    voice = dict(note=0, control=0, remaining=0, held_frequency=0, voice_control=65,
                 pulse_delay=0, pulse_direction=0, portamento=0, instrument_index=0,
                 order_cursor=0, pattern_cursor=0)
    return dict(format='monty-editable-title-v1', play_calls=4,
        initial_state=dict(globals=dict(tempo_countdown=0, tempo_reload=1, counter=0, status=0,
                           mode_volume=15, sfx_priority=0, sfx_flags=255, output_enable=255),
                           voices=[dict(voice) for _ in range(3)]),
        score=dict(orders=[dict(voice_index=i, bytes=[0, 255]) for i in range(3)],
                   patterns=[dict(pattern_id=0, bytes=[0, 0, 255])]),
        instruments=[dict(pulse_word=0x800, waveform=65, attack_decay=72, sustain_release=96,
                          vibrato_depth=0, pulse_value=0, effects=0)],
        frequency_words=[1000] + [0] * 95, frequency_alias_bindings=[])


def group(writes, call):
    return [(w['address'], w['value']) for w in writes if w['tick'] == call]


class MontyTitlePlayerTests(unittest.TestCase):
    def test_state_result_exposes_named_final_state_and_shared_bank(self):
        description = fixture()
        description['instruments'][0]['pulse_value'] = 128
        result = compute_player(description, calls=2)
        self.assertEqual(compute_writes(description, calls=2), result['writes'])
        self.assertEqual(0x980, result['instruments'][0]['pulse_word'])
        self.assertEqual(2, result['finalState']['globals']['counter'])
        self.assertEqual([0, 0, 0], [voice['pulse_delay'] for voice in result['finalState']['voices']])
        result['finalState']['voices'][0]['note'] = 99
        self.assertEqual(0, description['initial_state']['voices'][0]['note'])
        cold = compute_player(description, calls=0)
        self.assertEqual(description['initial_state'], cold['finalState'])
        self.assertFalse(cold['stopped'])

    def test_init_new_notes_and_exclusive_caps_preserve_store_order(self):
        description = fixture()
        writes = compute_writes(description)
        self.assertEqual([('init', None, address, 0) for address in (0xd404, 0xd40b, 0xd412)],
            [(w['phase'], w['tick'], w['address'], w['value']) for w in writes if w['phase'] == 'init'])
        first = [(0xd418, 15)]
        for voice in (2, 1, 0):
            base = 0xd400 + 7 * voice
            first.extend((base + offset, value) for offset, value in
                         ((1, 3), (0, 232), (4, 65), (2, 0), (3, 8), (5, 72), (6, 96)))
        self.assertEqual(first, group(writes, 0))
        self.assertEqual([(0xd418, 15)], group(writes, 1))
        self.assertEqual(first, group(writes, 2))
        for calls in range(description['play_calls'] + 1):
            with self.subTest(calls=calls):
                expected = [row for row in writes if row['phase'] == 'init' or row['tick'] < calls]
                self.assertEqual(expected, compute_writes(description, calls=calls))

    def test_notes_and_shared_pwm_edits_change_output_without_mutating_input(self):
        description = fixture()
        description['score']['patterns'][0]['bytes'][1] = 1
        description['frequency_words'][1] = 2000
        before = deepcopy(description)
        self.assertEqual([(0xd40f, 7), (0xd40e, 208)], group(compute_writes(description), 0)[1:3])
        self.assertEqual(before, description)
        description = fixture()
        description['instruments'][0]['pulse_value'] = 128
        body = group(compute_writes(description), 1)
        self.assertEqual([(0xd418, 15), (0xd411, 8), (0xd410, 128), (0xd40a, 9), (0xd409, 0),
                          (0xd403, 9), (0xd402, 128)], body)

    def test_initializer_alias_reads_prior_control_before_each_voice_update(self):
        description = fixture()
        description['score']['patterns'][0]['bytes'][1] = 104
        description['instruments'][0]['waveform'] = 129
        description['frequency_alias_bindings'] = [
            dict(offset=208, voice_index=2, field='voice_control'),
            dict(offset=209, voice_index=1, field='voice_control')]
        first = group(compute_writes(description), 0)
        self.assertEqual([(0xd40f, 65), (0xd40e, 65)], first[1:3])
        self.assertEqual([(0xd408, 65), (0xd407, 129)], first[8:10])
        self.assertEqual([(0xd401, 129), (0xd400, 129)], first[15:17])

    def test_octave_alias_reads_pwm_direction_after_same_voice_update(self):
        description = fixture()
        description['initial_state']['globals']['counter'] = 255
        description['score']['patterns'][0]['bytes'][1] = 104
        description['instruments'][0].update(pulse_word=0xdc0, pulse_value=64, effects=4)
        description['frequency_alias_bindings'] = [
            dict(offset=208, voice_index=0, field='voice_control'),
            dict(offset=209, voice_index=1, field='voice_control'),
            dict(offset=232, voice_index=2, field='pulse_direction'),
            dict(offset=233, voice_index=1, field='pulse_direction')]
        self.assertEqual([(0xd418, 15),
                          (0xd411, 14), (0xd410, 0), (0xd40f, 0), (0xd40e, 1),
                          (0xd40a, 14), (0xd409, 64), (0xd408, 1), (0xd407, 1),
                          (0xd403, 14), (0xd402, 128), (0xd401, 1), (0xd400, 1)],
                         group(compute_writes(description), 1))

    def test_source_annotations_do_not_supply_runtime_state_or_file_access(self):
        description = fixture()
        expected = compute_writes(description)
        description['sourceEvidence'] = dict(sid='/absent/original.sid', writes=[dict(value=255)])
        description['score']['sourceEvidence'] = dict(events=[dict(call=0, value=255)])
        before = deepcopy(description)
        with patch('builtins.open', side_effect=AssertionError('Runtime file access')), \
             patch('io.open', side_effect=AssertionError('Runtime file access')):
            self.assertEqual(expected, compute_writes(description))
        self.assertEqual(before, description)

    def test_declared_calls_and_optional_cap_require_bounded_integers(self):
        for calls in (-1, True, 1.5, 5, 100001):
            with self.subTest(calls=calls), self.assertRaises(ValueError):
                compute_writes(fixture(), calls=calls)
        for declared in (-1, True, 1.5, 100001):
            description = fixture()
            description['play_calls'] = declared
            with self.subTest(declared=declared), self.assertRaises(ValueError):
                compute_writes(description, calls=0)

    def test_unmapped_alias_and_unsupported_overlay_reject(self):
        description = fixture()
        description['score']['patterns'][0]['bytes'][1] = 96
        with self.assertRaisesRegex(ValueError, 'unmapped frequency alias'):
            compute_writes(description)
        for name, value in (('sfx_priority', 1), ('sfx_flags', 0), ('output_enable', 127)):
            description = fixture()
            description['initial_state']['globals'][name] = value
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'overlay/output'):
                compute_writes(description)

    def test_aliases_require_unique_byte_fields_outside_frequency_table(self):
        binding = dict(offset=192, voice_index=0, field='voice_control')
        for bindings in ([dict(binding, offset=191)], [dict(binding, voice_index=True)],
                         [dict(binding, field='held_frequency')], [binding, binding]):
            description = fixture()
            description['frequency_alias_bindings'] = bindings
            with self.subTest(bindings=bindings), self.assertRaises(ValueError):
                compute_writes(description)


class MontyTitleProgramsTests(unittest.TestCase):
    def test_initializer_append_retains_pitch_and_pwm_state(self):
        state = VoiceState(19, 8, 7, 1000, 65, 3, 1, 0)
        instrument = Instrument(0x800, 129, 72, 96, 0, 128, 0)
        result = initialize_note(state, instrument, append=True)
        self.assertEqual(((4, 128), (2, 0), (3, 8), (5, 72), (6, 96)), result.writes)
        self.assertEqual((19, 1000, 3, 1), (result.state.note, result.state.held_frequency,
                                         result.state.pulse_delay, result.state.pulse_direction))
        self.assertEqual(65, state.voice_control)
        with self.assertRaises(FrozenInstanceError):
            result.state.note = 20

    def test_combined_programs_preserve_vibrato_pwm_portamento_drum_sweep_octave_order(self):
        state = VoiceState(19, 8, 3, 0x1234, 65, 0, 0, 2)
        instrument = Instrument(0xdc0, 65, 72, 96, 1, 64, 7)
        result = advance_body(state, instrument, PitchLookups(1000, 1400, 2000), counter=1)
        self.assertEqual(((0, 76), (1, 4), (3, 14), (2, 0), (0, 54), (1, 18),
                          (1, 18), (4, 64), (1, 17), (1, 7), (0, 208)), result.writes)
        self.assertEqual(0x1036, result.state.held_frequency)
        self.assertEqual(0xe00, result.instrument.pulse_word)
        self.assertEqual(0x1234, state.held_frequency)
        self.assertEqual(0xdc0, instrument.pulse_word)

    def test_release_precedes_continuing_stores_without_changing_saved_control(self):
        state = VoiceState(19, 0, 0, 1000, 65, 0, 0, 0)
        instrument = Instrument(0x800, 65, 72, 96, 1, 0, 0)
        result = advance_body(state, instrument, PitchLookups(1000, 1400, 0),
                              counter=1, release_check=True)
        self.assertEqual(((4, 64), (5, 0), (6, 0), (0, 232), (1, 3)), result.writes)
        self.assertEqual(65, result.state.voice_control)


if __name__ == '__main__':
    unittest.main()
