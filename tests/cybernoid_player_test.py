from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from cybernoid_player import compute_writes


def opening_fixture():
    """Keep the first three semantic rows and their numeric programs source-free.

    The frozen title description e56ed96c supplies these values. Frequency
    slots outside this two-call window are zeroed to avoid a full-song fixture.
    The expected stores below come from
    evidence/cybernoid-form-36000/audit.writes.json.gz, independently of this
    player's component helpers.
    """
    caller_fields = (
        'row_remaining row_duration arpeggio_counter base_pitch current_pitch frequency '
        'held_frequency held_high_copy base_wave wave pulse_flags pulse_accumulator '
        'pulse_output pulse_direction packed_filter gate_mask note_age vibrato_age '
        'glide_enabled glide_active vibrato_direction vibrato_position filter_cutoff '
        'pulse_run_flag pulse_run_low pulse_run_high'
    ).split()
    pitch_fields = (
        'base_note frequency held_frequency vibrato_extent vibrato_direction '
        'vibrato_position vibrato_age glide_enabled glide_active glide_control glide_target'
    ).split()
    voices = []
    for index in range(3):
        caller = dict.fromkeys(caller_fields, 0)
        caller.update(note_age=255, pulse_output=0x800 if index == 2 else 0)
        voices.append(dict(caller=caller, pitch=dict.fromkeys(pitch_fields, 0),
                           sound_index=0, arpeggio_index=None))
    fields = ('pulse_flags', 'wave', 'attack_decay', 'sustain_release',
              'packed_gate_filter', 'fx1', 'fx2', 'fx3')
    records = [dict(zip(fields, values)) for values in (
        (0, 0, 0, 0, 0, 0, 0, 0),
        (5, 0x41, 8, 0x89, 0, 0x53, 0x64, 0x80),
        (8, 0x11, 0, 0xa8, 0xf0, 0, 0, 0x10),
        (8, 0x11, 0, 0xa9, 0xf0, 1, 0, 0x10),
        (4, 0x21, 0, 0xc8, 1, 0, 0x81, 0x85),
    )]
    frequencies = [0] * 257
    for index, word in {0: 451, 16: 1136, 17: 1204, 18: 1275,
                        24: 1804, 25: 1911, 28: 2273, 47: 6812,
                        48: 7217, 55: 10814, 56: 11457}.items():
        frequencies[index] = word
    return dict(
        format='cybernoid-editable-title-v1', play_calls=2,
        initial_state=dict(globals=dict(tempo_reload=2, tempo_countdown=0, play_flag=0, filter_owner=0),
                           voices=voices),
        sid_init=dict(cutoff_high=255, routing=0, mode_volume=31),
        frequency_words=frequencies, records=records, vibrato_wait=[0, 12, 0, 0, 0],
        onset_lengths=[2, 2, 2, 2, 5], onset_waves=[0x81, 0x81, 0x81, 0x81, 0x41],
        pulse_slots=[[4, 12, 2, 48, 4, 48, 6, 48], [4, 12, 4, 128, 8, 96, 12, 64],
                     [1, 15, 2, 102, 8, 66, 12, 40], [7, 13, 3, 112, 6, 96, 9, 80]],
        filter_programs=[[160, 254, 2, 255, 128, 31, 2, 34, 66, 98],
                         [160, 254, 1, 255, 98, 63, 2, 34, 98, 162]],
        arpeggios=[[2, 0, 3, 7], [2, 0, 4, 7], [2, 0, 5, 8]],
        drums=[dict(waves=[11, 0x81, 0x41] + [0x40] * 10,
                    pitch_values=[52, 10, 8, 6, 4, 5, 6, 5, 4, 5, 6, 5]),
               dict(waves=[11, 0x81, 0x41, 0x80, 0x40, 0x80, 0x80, 0x80, 0x80, 0x10, 0x10, 0x10, 0x10],
                    pitch_values=[60, 14, 0, 12, 56, 60, 56, 60, 13, 13, 13, 13])],
        rows=[
            dict(call=0, voiceIndex=2, transpose=16, patchSetup='initialize', commands=[
                dict(kind='sound', index=2), dict(kind='duration', reload=7), dict(kind='note', sourceNote=8)]),
            dict(call=0, voiceIndex=1, transpose=4, patchSetup='initialize', commands=[
                dict(kind='routing', value=0x82), dict(kind='sound', index=4),
                dict(kind='duration', reload=31), dict(kind='arpeggio', index=2), dict(kind='note', sourceNote=43)]),
            dict(call=0, voiceIndex=0, transpose=4, patchSetup='initialize', commands=[
                dict(kind='sound', index=1), dict(kind='duration', reload=31),
                dict(kind='extendDuration', reload=63), dict(kind='glide', control=64, targetNote=24),
                dict(kind='note', sourceNote=12)]),
        ])


def identity(writes):
    return [(w['phase'], w['tick'], w['address'], w['value']) for w in writes]


def bass_boundary_fixture():
    description = opening_fixture()
    row = description['rows'][2]
    row['transpose'] = 0
    row['commands'] = [c for c in row['commands'] if c['kind'] != 'glide']
    row['commands'][-1]['sourceNote'] = 255
    description['records'][1].update(fx3=0, fx1=0x53)
    description['vibrato_wait'][1] = 0
    for index, word in ((255, 1000), (256, 1032), (0, 9999)):
        description['frequency_words'][index] = word
    return description


class CybernoidPlayerTests(unittest.TestCase):
    def test_first_two_calls_match_exact_source_init_setup_and_macro_write_order(self):
        expected = [('init', None, address, value) for address, value in
                    [(0xd416, 255), (0xd417, 0), (0xd418, 31)] +
                    [(address, 0) for address in range(0xd415, 0xd3ff, -1)]]
        opening = [
            (0xd40f, 7), (0xd40e, 12), (0xd413, 0), (0xd414, 0xa8),
            (0xd412, 0x11), (0xd40e, 12), (0xd40f, 7), (0xd410, 0), (0xd411, 8),
            (0xd417, 0x82), (0xd408, 0x1a), (0xd407, 0x9c), (0xd40c, 0), (0xd40d, 0xc8),
            (0xd40b, 0x21), (0xd407, 0x9c), (0xd408, 0x1a), (0xd409, 0), (0xd40a, 4),
            (0xd401, 4), (0xd400, 0x70), (0xd405, 8), (0xd406, 0x89),
            (0xd404, 0x41), (0xd400, 0x70), (0xd401, 4), (0xd402, 0), (0xd403, 5),
        ]
        body = [
            (0xd412, 0x81), (0xd40e, 0), (0xd40f, 0x34), (0xd410, 0), (0xd411, 8),
            (0xd418, 0x3f), (0xd416, 0xa0), (0xd40b, 0x41), (0xd407, 0x3e), (0xd408, 0x2a),
            (0xd409, 0x30), (0xd40a, 4), (0xd404, 0x81), (0xd400, 0xcf), (0xd401, 0xfa),
            (0xd402, 0x70), (0xd403, 5),
        ]
        expected.extend(('play', tick, address, value) for tick, group in ((0, opening), (1, body))
                        for address, value in group)
        self.assertEqual(expected, identity(compute_writes(opening_fixture())))

    def test_call_limit_returns_only_requested_prefix_and_rejects_invalid_counts(self):
        description = opening_fixture()
        expected = [w for w in compute_writes(description) if w['tick'] is None or w['tick'] == 0]
        self.assertEqual(expected, compute_writes(description, calls=1))
        for count in (0, 3, True, 1.5):
            with self.subTest(calls=count), self.assertRaises(ValueError):
                compute_writes(description, calls=count)

    def test_source_evidence_is_irrelevant_and_computation_needs_no_filesystem(self):
        description = opening_fixture()
        expected = compute_writes(description)
        description['sourceEvidence'] = dict(path='/absent/original.sid', sidWrites=[dict(value=0)])
        for row in description['rows']:
            row['sourceEvidence'] = dict(pitchIndex=255, soundIndex=18, countdownReload=0)
            for command in row['commands']:
                command['sourceEvidence'] = dict(sourceAddress=65535, value=0)
        for record in description['records']:
            record['sourceEvidence'] = dict(fx3=255)
        with patch('builtins.open', side_effect=AssertionError('Player opens a file')), \
             patch.object(Path, 'open', side_effect=AssertionError('Player opens a path')), \
             patch.object(Path, 'read_bytes', side_effect=AssertionError('Player reads bytes')), \
             patch.object(Path, 'read_text', side_effect=AssertionError('Player reads text')):
            self.assertEqual(expected, compute_writes(description))

    def test_editable_note_changes_bass_pitch_without_mutating_input(self):
        original = opening_fixture()
        changed = deepcopy(original)
        changed['rows'][2]['commands'][-1]['sourceNote'] = 13
        before = deepcopy(changed)
        baseline, edited = compute_writes(original), compute_writes(changed)
        self.assertEqual(before, changed)
        differences = [(a, b) for a, b in zip(baseline, edited) if a != b]
        self.assertTrue(differences)
        self.assertEqual(len(baseline), len(edited))
        self.assertTrue(all(a['address'] == b['address'] and a['address'] in (0xd400, 0xd401)
                            for a, b in differences))
        self.assertEqual([(0xd401, 4), (0xd400, 0xb4)],
                         [(w['address'], w['value']) for w in edited
                          if w['tick'] == 0 and w['address'] in (0xd400, 0xd401)][:2])

    def test_editable_pwm_changes_only_the_selected_body_pulse_store(self):
        original = opening_fixture()
        changed = deepcopy(original)
        changed['pulse_slots'][3][3] = 120
        before = deepcopy(changed)
        baseline, edited = compute_writes(original), compute_writes(changed)
        self.assertEqual(before, changed)
        self.assertEqual([(dict(phase='play', tick=1, address=0xd402, value=0x70),
                           dict(phase='play', tick=1, address=0xd402, value=0x78))],
                         [(a, b) for a, b in zip(baseline, edited) if a != b])

    def test_duplicate_rows_and_absolute_countdown_mismatches_are_rejected(self):
        duplicate = opening_fixture()
        duplicate['rows'].append(deepcopy(duplicate['rows'][0]))
        with self.assertRaises(ValueError):
            compute_writes(duplicate)
        late = opening_fixture()
        late['rows'][0]['call'] = 1
        exhausted = opening_fixture()
        exhausted['play_calls'] = 4
        exhausted['rows'][2]['commands'][2]['reload'] = 0
        for name, description in (('late row', late), ('exhausted countdown', exhausted)):
            with self.subTest(case=name), self.assertRaisesRegex(ValueError, '[Rr]ow/countdown'):
                compute_writes(description)

    def test_initial_pitch_is_validated_before_initializer_can_overwrite_it(self):
        for direction in (-1, 1):
            description = opening_fixture()
            description['initial_state']['voices'][0]['pitch']['vibrato_direction'] = direction
            with self.subTest(direction=direction), self.assertRaises(ValueError):
                compute_writes(description, calls=1)

    def test_note255_uses_unmasked_pitch_and_unwrapped_adjacent_slot256(self):
        description = bass_boundary_fixture()
        writes = compute_writes(description)
        onset = [(w['address'], w['value']) for w in writes if w['tick'] == 0 and w['address'] in (0xd400, 0xd401)]
        self.assertEqual([(0xd401, 3), (0xd400, 0xe8), (0xd400, 0xe8), (0xd401, 3)], onset)
        body = {w['address']: w['value'] for w in writes if w['tick'] == 1}
        self.assertEqual(996, body[0xd400] | body[0xd401] << 8)
        changed = deepcopy(description)
        changed['frequency_words'][0] = 1111
        self.assertEqual(writes, compute_writes(changed))
        changed['frequency_words'][256] = 1000
        body = {w['address']: w['value'] for w in compute_writes(changed) if w['tick'] == 1}
        self.assertEqual(1000, body[0xd400] | body[0xd401] << 8)


if __name__ == '__main__':
    unittest.main()
