import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from flashdance_player import compute_writes


def load_script(filename, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


SOURCE = ROOT / '.local/research/flashdance/drax-flashdance-conversion.sid'


class FlashdancePlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.description = json.loads((ROOT / 'songs/flashdance-decoded.json').read_text())

    @unittest.skipUnless(SOURCE.exists(), 'Requires pinned local Flashdance source')
    def test_complete_selected_form_matches_every_ordered_sound_write(self):
        data = SOURCE.read_bytes()
        reference = load_script('study-drax-references.py', 'player_reference')
        reference.verify_reference('flashdance', data)
        diagnostic = reference.load_script('psid_audit.py', 'player_reference_auditor')
        diagnostic.AuditMemory = reference.FlashdanceDiagnosticMemory
        _, original = diagnostic.audit_psid(data, 1538)
        actual = compute_writes(self.description)
        identity = lambda rows: [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]
        self.assertEqual(identity(original), identity(actual))

    def test_serialized_description_runs_without_source_reads_or_captured_writes(self):
        description = json.loads(json.dumps(self.description))
        description['score']['source']['path'] = '/not-present.sid'
        for role in description['score']['roles'].values():
            for command in role['commands']:
                command.pop('sourceEvidence', None)
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('Unexpected source read')), \
                patch.object(Path, 'read_text', side_effect=AssertionError('Unexpected source read')):
            actual = compute_writes(description, calls=514)
        self.assertEqual(9345, len(actual))
        self.assertNotIn('sidWrites', description)
        self.assertNotIn('registers', description)

    def test_editing_score_pitch_changes_output_without_changing_source_annotations(self):
        description = copy.deepcopy(self.description)
        lead = description['score']['roles']['lead']['commands']
        note = next(row for row in lead if row['kind'] == 'note')
        note['sourceNote'] += 2
        actual = compute_writes(description, calls=4)
        values = {row['address']: row['value'] for row in actual if row['phase'] == 'play' and row['tick'] == 3}
        index = note['sourceNote'] + note['transposeSemitones']
        expected = description['programs']['frequency_words'][index] + 1
        self.assertEqual(expected, values[0xd407] | values[0xd408] << 8)

    def test_initializer_and_legato_preserve_distinct_write_shapes(self):
        writes = compute_writes(self.description, calls=103)
        selected = lambda call: [row['address'] for row in writes if row['phase'] == 'play'
                                  and row['tick'] == call and 0xd407 <= row['address'] <= 0xd40d]
        self.assertEqual([0xd40c, 0xd40d, 0xd40b, 0xd40c, 0xd40d, 0xd40b], selected(98))
        self.assertEqual([0xd409, 0xd40a, 0xd407, 0xd408, 0xd40b], selected(102))

    def test_unknown_command_and_invalid_call_range_fail_before_output(self):
        description = copy.deepcopy(self.description)
        description['score']['roles']['lead']['commands'][0]['kind'] = 'glissnado'
        with self.assertRaisesRegex(ValueError, 'command'):
            compute_writes(description)
        with self.assertRaisesRegex(ValueError, 'call'):
            compute_writes(self.description, calls=100001)

    def test_ending_releases_then_fades_and_stays_silent(self):
        stop = self.description['score']['range']['stopCall']
        writes = compute_writes(self.description, calls=stop + 132)
        ending = [row for row in writes if row['phase'] == 'play' and row['tick'] >= stop]
        for row in ending:
            if row['address'] in (0xd404, 0xd40b, 0xd412):
                self.assertEqual(0, row['value'] & 1)
        volumes = [(row['tick'] - stop, row['value']) for row in ending if row['address'] == 0xd418]
        self.assertEqual([(64 + step * 4, 0x10 | max(0, 14 - step)) for step in range(16)], volumes[:16])
        self.assertEqual([(128 + step, 0) for step in range(4)], volumes[16:])
        body_pulse = [row['value'] for row in ending if row['address'] == 0xd409 and row['tick'] < stop + 64]
        self.assertGreater(len(set(body_pulse)), 1)
        self.assertFalse(any(row['address'] in (0xd405, 0xd40c, 0xd413) for row in ending))

    def test_ending_parameters_cannot_wrap_the_compiled_word_counter(self):
        description = copy.deepcopy(self.description)
        description['ending'] = {'releaseCalls': 65535, 'fadeStepCalls': 4}
        with self.assertRaisesRegex(ValueError, 'ending'):
            compute_writes(description)

    def test_negative_calls_and_unknown_runtime_fields_are_rejected_for_every_role(self):
        for role in ('bass', 'lead', 'chord'):
            with self.subTest(role=role):
                description = copy.deepcopy(self.description)
                description['score']['roles'][role]['commands'][0]['call'] = -1
                with self.assertRaisesRegex(ValueError, 'call'):
                    compute_writes(description)
                description = copy.deepcopy(self.description)
                note = next(row for row in description['score']['roles'][role]['commands'] if row['kind'] == 'note')
                note['articulation'] = 'portamento'
                with self.assertRaisesRegex(ValueError, 'fields'):
                    compute_writes(description)

    def test_invalid_effect_state_and_inconsistent_filter_owner_are_rejected(self):
        invalid = (
            ('initialEffects', lambda value: value.pop()),
            ('initialEffects', lambda value: value[0]['vibrato'].update(shift=-1)),
            ('initialEffects', lambda value: value[0]['slide'].update(offset=65536)),
            ('preloaded', lambda value: value.update(filter_owner=2)),
        )
        for field, change in invalid:
            with self.subTest(field=field):
                description = copy.deepcopy(self.description)
                change(description[field])
                with self.assertRaises(ValueError):
                    compute_writes(description)

    def test_invalid_effect_parameters_and_boolean_note_values_fail_before_output(self):
        for field, value in (('sourceNote', True), ('restart', 1), ('transposeSemitones', -1)):
            with self.subTest(field=field):
                description = copy.deepcopy(self.description)
                note = next(row for row in description['score']['roles']['lead']['commands'] if row['kind'] == 'note')
                note[field] = value
                with self.assertRaises(ValueError):
                    compute_writes(description)
        description = copy.deepcopy(self.description)
        effect = next(row for row in description['score']['roles']['lead']['commands'] if row.get('effect') == 'vibrato')
        effect['parameters']['pitchDeltaRightShifts'] = -1
        with self.assertRaises(ValueError):
            compute_writes(description)

    def test_composed_pitch_inputs_outside_table_are_rejected_for_every_role(self):
        for role in ('bass', 'lead', 'chord'):
            with self.subTest(role=role):
                description = copy.deepcopy(self.description)
                note = next(row for row in description['score']['roles'][role]['commands'] if row['kind'] == 'note')
                note['sourceNote'] = 95
                with self.assertRaisesRegex(ValueError, 'frequency table'):
                    compute_writes(description, calls=5)
        description = copy.deepcopy(self.description)
        description['programs']['wave_rows']['11']['note'] = 40
        with self.assertRaisesRegex(ValueError, 'frequency table'):
            compute_writes(description, calls=4)

    def test_active_vibrato_at_last_table_note_is_rejected(self):
        description = copy.deepcopy(self.description)
        commands = description['score']['roles']['lead']['commands']
        note = next(row for row in commands if row['kind'] == 'note')
        note.update(sourceNote=95, transposeSemitones=0)
        commands.insert(2, {'call': 3, 'kind': 'effect', 'effect': 'vibrato', 'parameters': {
            'remainingNotes': 1, 'reloadCounter': 4, 'initialCounter': 3,
            'pitchDeltaRightShifts': 2, 'deltaHighByteIncrement': 0,
        }})
        with self.assertRaisesRegex(ValueError, 'frequency table'):
            compute_writes(description, calls=4)

    def test_envelope_effect_requires_same_call_duration_and_positive_lead_time(self):
        for call, duration in ((1, None), (3, None), (1, 2)):
            with self.subTest(call=call, duration=duration):
                description = copy.deepcopy(self.description)
                additions = [{'call': call, 'kind': 'effect', 'effect': 'sustainReleaseAhead',
                              'parameters': {'callsBeforeNextRow': 2, 'sustainRelease': 0}}]
                if duration is not None:
                    additions.append({'call': call, 'kind': 'hold', 'durationCalls': duration})
                commands = description['score']['roles']['lead']['commands']
                commands.extend(additions)
                commands.sort(key=lambda command: command['call'])
                with self.assertRaisesRegex(ValueError, 'envelope'):
                    compute_writes(description, calls=1)

    def test_envelope_effect_keeps_first_duration_when_rows_share_call(self):
        description = copy.deepcopy(self.description)
        commands = description['score']['roles']['lead']['commands']
        commands[0:0] = [
            {'call': 1, 'kind': 'effect', 'effect': 'sustainReleaseAhead',
             'parameters': {'callsBeforeNextRow': 2, 'sustainRelease': 0x27}},
            {'call': 1, 'kind': 'hold', 'durationCalls': 4},
            {'call': 1, 'kind': 'hold', 'durationCalls': 8},
        ]
        writes = compute_writes(description, calls=4)
        self.assertIn({'phase': 'play', 'tick': 3, 'address': 0xd40d, 'value': 0x27}, writes)

    def test_malformed_score_containers_and_instrument_names_raise_value_error(self):
        changes = (
            lambda value: value.update(score=None),
            lambda value: value['score'].update(range=None),
            lambda value: value['score'].update(roles=None),
            lambda value: value['score']['roles'].update(lead=None),
            lambda value: value['score']['roles']['lead'].update(commands=None),
            lambda value: value['score']['roles']['lead'].update(commands='notes'),
            lambda value: value.update(instrumentBindings=[]),
            lambda value: value['score']['roles']['lead']['commands'][0].update(instrument=[]),
        )
        for change in changes:
            description = copy.deepcopy(self.description)
            change(description)
            with self.subTest(description=description['score'] is None):
                with self.assertRaises(ValueError):
                    compute_writes(description, calls=1)


if __name__ == '__main__':
    unittest.main()
