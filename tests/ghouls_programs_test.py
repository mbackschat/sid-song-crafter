"""Check the pure Ghouls sound programs against retained executed boundaries."""

from dataclasses import asdict, replace
import gzip
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import ghouls_programs as programs


class GhoulsProgramsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        evidence = ROOT / 'evidence/ghouls-components/sound'
        cls.receipt = json.loads((evidence / 'receipt.json').read_text())
        encoded = (evidence / 'proofs.json.gz').read_bytes()
        if hashlib.sha256(encoded).hexdigest() != cls.receipt['outputHashes']['proofs.json.gz']['sha256']:
            raise AssertionError('Retained executed sound proof changed')
        cls.proof = json.loads(gzip.decompress(encoded))
        cls.controls = json.loads((evidence / 'controls.json').read_text())

    def test_complete_finite_executed_boundaries(self):
        lookup = self.proof['lookup']
        programs.validate_lookup(lookup)
        checked = 0
        for row in self.proof['comparisons']:
            stage, voice = row['stage'], row['voice']
            expected_writes = [tuple(write) for write in row['writes']]
            if stage == 'filter':
                state = programs.FilterState(**row['before'])
                result, writes, path = programs.filter_step(state)
            else:
                state = programs.VoiceState(**row['before'])
                if stage == 'setup':
                    raw_note = next_row_note(row)
                    result, _, writes = programs.note_setup(state, programs.FilterState(), voice, raw_note, lookup)
                    path = 'positive-note'
                else:
                    function = {'onset': programs.onset_step, 'frequency': programs.frequency_step,
                                'note': programs.note_step, 'pulse': programs.pulse_step}[stage]
                    transition = function(state, voice, lookup) if stage == 'note' else function(state, voice)
                    result, writes, path = transition.state, transition.writes, transition.path
            self.assertEqual(asdict(result), row['after'], f'{stage} state at call {row["call"]}, voice {voice}')
            self.assertEqual(writes, expected_writes, f'{stage} stores at call {row["call"]}, voice {voice}')
            self.assertEqual(path, row['path'])
            self.assertEqual(asdict(state), row['before'], 'Programs must preserve their input state')
            checked += 1
        self.assertEqual(checked, 170648)

    def test_retained_controlled_parameters(self):
        lookup = self.proof['lookup']
        for row in self.controls:
            stage, voice = row['stage'], row['voice']
            if stage == 'filter':
                result, writes, path = programs.filter_step(programs.FilterState(**row['before']))
            else:
                state = programs.VoiceState(**row['before'])
                if stage == 'setup':
                    raw_note = next_row_note(row)
                    result, _, writes = programs.note_setup(state, programs.FilterState(), voice, raw_note, lookup)
                    path = 'positive-note'
                else:
                    function = {'onset': programs.onset_step, 'frequency': programs.frequency_step,
                                'note': programs.note_step, 'pulse': programs.pulse_step}[stage]
                    transition = function(state, voice, lookup) if stage == 'note' else function(state, voice)
                    result, writes, path = transition.state, transition.writes, transition.path
            with self.subTest(purpose=row['purpose']):
                self.assertEqual(asdict(result), row['after'])
                self.assertEqual(writes, [tuple(write) for write in row['writes']])
                self.assertEqual(path, row['path'])
        self.assertEqual(len(self.controls), 18)

    def test_sparse_lookup_preserves_adjacent_data_pitch_alias(self):
        state = programs.VoiceState(note_index=96, note_step=1, note_remaining=1)
        result = programs.note_step(state, 2, {97: 8961})
        self.assertEqual(result.state.note_index, 97)
        self.assertEqual(result.state.current_frequency, 8961)
        self.assertEqual(result.writes, [(0xd40e, 1), (0xd40f, 35)])

    def test_missing_accessed_frequency_index_fails_clearly(self):
        state = programs.VoiceState(note_index=96, note_step=1, note_remaining=1)
        for lookup in ({96: 8000}, [0] * 97):
            with self.subTest(kind=type(lookup).__name__):
                with self.assertRaisesRegex(ValueError, 'Missing numeric frequency lookup for index 97'):
                    programs.note_step(state, 0, lookup)
        with self.assertRaisesRegex(ValueError, 'Missing numeric frequency lookup for index 21'):
            programs.note_setup(programs.VoiceState(), programs.FilterState(), 0, 21, {})

    def test_invalid_numeric_description_inputs_are_rejected(self):
        for field, value in (('pulse_word', 65536), ('frequency_step', -1), ('note_index', True),
                             ('onset_delay', 1.5), ('pulse_direction', 128)):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    programs.validate_voice_state(replace(programs.VoiceState(), **{field: value}))
        for field, value in (('word', -1), ('step', 256), ('owner', 3), ('direction', True)):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    programs.validate_filter_state(replace(programs.FilterState(), **{field: value}))
        for lookup in ({True: 100}, {256: 100}, {20: 65536}, {20: 1.5}, '123'):
            with self.subTest(lookup=lookup):
                with self.assertRaises(ValueError):
                    programs.validate_lookup(lookup)
        for voice in (-1, 3, True, 1.0):
            with self.assertRaises(ValueError):
                programs.onset_step(programs.VoiceState(), voice)

    def test_note_setup_resets_only_nonzero_owner_filter_default(self):
        state = programs.VoiceState(pulse_word=900, pulse_default=240, pulse_restart=255,
                                    frequency_direction=255, frequency_delay_reload=0)
        filter_state = programs.FilterState(word=75, default=256, owner=1, direction=255, reset_direction=0)
        changed, reset, _ = programs.note_setup(state, filter_state, 1, 21, {21: 902})
        self.assertEqual((changed.pulse_word, changed.pulse_direction), (240, 255))
        self.assertEqual(changed.frequency_direction, 255)
        self.assertEqual((reset.word, reset.direction), (256, 0))
        _, other_owner, _ = programs.note_setup(state, filter_state, 0, 21, {21: 902})
        self.assertEqual(other_owner, filter_state)
        _, zero_default, _ = programs.note_setup(state, replace(filter_state, default=0), 1, 21, {21: 902})
        self.assertEqual((zero_default.word, zero_default.direction), (75, 255))

    def test_filter_sign_check_requires_a_low_byte_borrow(self):
        for before, expected_word, expected_direction, expected_high, expected_path in (
                (programs.FilterState(word=0x8001, step=1, upper=0xffff), 0x8000, 0, 8, 'down'),
                (programs.FilterState(word=0x8100, step=1, upper=0xffff), 0x8100, 255, 40, 'lower-reverse/up')):
            with self.subTest(word=before.word):
                after, writes, path = programs.filter_step(before)
                self.assertEqual((after.word, after.direction), (expected_word, expected_direction))
                self.assertEqual(writes, [(0xd415, expected_word & 255), (0xd416, expected_high)])
                self.assertEqual(path, expected_path)

    def test_nonterminating_filter_parameters_fail_with_a_bounded_guard(self):
        with self.assertRaisesRegex(ValueError, 'Filter parameters do not reach the output boundary'):
            programs.filter_step(programs.FilterState(word=1, step=1, lower=2, upper=1))


def next_row_note(row):
    before, after = row['before'], row['after']
    index = after['target_note_index'] if before['glide_rate'] else after['note_index']
    raw_note = (index - before['transpose']) & 255
    if before['pitch_index_mode'] == 255:
        raw_note = index
    if not 1 <= raw_note <= 127:
        raise AssertionError('Retained setup no longer supplies a positive native score note')
    return raw_note


if __name__ == '__main__':
    unittest.main()
