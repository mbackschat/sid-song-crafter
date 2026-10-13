import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from rambo_score import ScoreRuntime


def initial_voices(cursor='start'):
    return [dict(cursor=cursor, remaining=1, transpose=0, stackIndex=7,
                 stack=[dict(returnNode=None, repeatRemaining=0) for _ in range(8)])
            for _ in range(3)]


class RamboScoreTests(unittest.TestCase):
    def runtime(self, program, *, voices=None, callback=None, active_mask=1,
                duration_lookup=None):
        return ScoreRuntime(program, voices or initial_voices(), active_mask=active_mask,
                            duration_lookup=duration_lookup or (lambda voice, index: index * 4),
                            on_operation=callback)

    def test_call_transpose_return_retains_transpose_and_resumes_next_node(self):
        program = {
            'start': dict(kind='call-transposed', target='phrase', next='after', transpose=250),
            'phrase': dict(kind='row', sourceNote=106, duration=1, next='ret'),
            'ret': dict(kind='return'),
            'after': dict(kind='row', sourceNote=104, duration=1, next='end'),
            'end': dict(kind='return'),
        }
        runtime = self.runtime(program)
        for call in range(3):
            runtime.refresh(call)
        notes = [row for row in runtime.operations if row['operation'] == 'note']
        self.assertEqual([(0, 4), (1, 2)], [(row['call'], row['pitchIndex']) for row in notes])
        self.assertEqual(8, runtime.voices[0]['stackIndex'])
        self.assertEqual(250, runtime.voices[0]['transpose'])
        self.assertEqual(0, runtime.active_mask)
        self.assertEqual(['topReturn', 'sound', 'sound'],
                         [row['operation'] for row in runtime.operations if row['call'] == 2][-3:])

    def test_calls_and_nested_loops_share_stack_and_preserve_iteration_counts(self):
        program = {
            'start': dict(kind='loop', repeat=2, next='call'),
            'call': dict(kind='call', target='inner', next='outerNext'),
            'inner': dict(kind='loop', repeat=3, next='body'),
            'body': dict(kind='row', sourceNote=96, duration=1, next='innerNext'),
            'innerNext': dict(kind='next', next='return'),
            'return': dict(kind='return'),
            'outerNext': dict(kind='next', next='end'),
            'end': dict(kind='return'),
        }
        runtime = self.runtime(program)
        for call in range(7):
            runtime.refresh(call)
        self.assertEqual(list(range(6)), [row['call'] for row in runtime.operations
                                        if row['operation'] == 'row'])
        self.assertEqual(0, runtime.active_mask)
        self.assertEqual(8, runtime.voices[0]['stackIndex'])
        self.assertEqual([0, 0], [runtime.voices[0]['stack'][slot]['repeatRemaining'] for slot in (5, 7)])

    def test_zero_row_duration_wraps_to_256_active_entries(self):
        program = {'start': dict(kind='row', sourceNote=96, duration=0, next='end'),
                   'end': dict(kind='return')}
        runtime = self.runtime(program)
        for call in range(256):
            runtime.refresh(call)
        self.assertEqual(1, runtime.active_mask)
        self.assertEqual(1, runtime.voices[0]['remaining'])
        runtime.refresh(256)
        self.assertEqual(0, runtime.active_mask)
        self.assertEqual([256], [row['call'] for row in runtime.operations if row['operation'] == 'topReturn'])

    def test_zero_repeat_means_256_iterations(self):
        program = {'start': dict(kind='loop', repeat=0, next='body'),
                   'body': dict(kind='row', sourceNote=191, duration=1, next='next'),
                   'next': dict(kind='next', next='end'), 'end': dict(kind='return')}
        runtime = self.runtime(program)
        for call in range(257):
            runtime.refresh(call)
        self.assertEqual(256, len([row for row in runtime.operations if row['operation'] == 'row']))
        self.assertFalse(any(row['operation'] == 'note' for row in runtime.operations))
        self.assertEqual(0, runtime.active_mask)

    def test_table_lookup_is_live_and_hold_rows_do_not_initialize_notes(self):
        duration = [4]

        def handle(runtime, event):
            if event['operation'] == 'command' and event['kind'] == 'poke-data':
                duration[0] = event['value']

        program = {'start': dict(kind='poke-data', offset=33, value=2, next='table'),
                   'table': dict(kind='row', sourceNote=95, duration=1, next='literal'),
                   'literal': dict(kind='row', sourceNote=191, duration=3, next='end'),
                   'end': dict(kind='return')}
        runtime = self.runtime(program, callback=handle,
                               duration_lookup=lambda voice, index: duration[0])
        for call in range(6):
            runtime.refresh(call)
        self.assertEqual([(0, 'table', 2), (2, 'literal', 3)],
                         [(row['call'], row['durationKind'], row['value'])
                          for row in runtime.operations if row['operation'] == 'row'])
        self.assertFalse(any(row['operation'] == 'note' for row in runtime.operations))

    def test_code_callback_can_reenter_refresh_before_cursor_advances(self):
        observations = []

        def handle(runtime, event):
            if event['operation'] == 'command' and event['kind'] == 'code':
                observations.append((runtime.voices[0]['cursor'], runtime.voices[0]['remaining']))
                runtime.refresh(event['call'])

        program = {'start': dict(kind='code', codeId='recursiveRefresh', next='row'),
                   'row': dict(kind='row', sourceNote=191, duration=10, next='end'),
                   'other': dict(kind='row', sourceNote=191, duration=10, next='end'),
                   'end': dict(kind='return')}
        voices = initial_voices()
        voices[1]['cursor'] = voices[2]['cursor'] = 'other'
        runtime = self.runtime(program, voices=voices, callback=handle, active_mask=7)
        runtime.refresh(0)
        self.assertEqual([('start', 0)], observations)
        self.assertEqual([10, 9, 9], [voice['remaining'] for voice in runtime.voices])
        self.assertEqual([0, 1, 2, 0, 1, 2], [row['voiceIndex'] for row in runtime.operations
                                             if row['operation'] == 'sound'])

    def test_missing_code_handler_fails_without_silent_schedule_approximation(self):
        program = {'start': dict(kind='code', codeId='unknown', next='end'),
                   'end': dict(kind='return')}
        runtime = self.runtime(program)
        with self.assertRaisesRegex(ValueError, 'code.*handler'):
            runtime.refresh(0)

    def test_top_level_return_skips_that_voice_sound_but_inactive_entries_emit_sound(self):
        runtime = self.runtime({'start': dict(kind='return')})
        runtime.refresh(0)
        runtime.refresh(1)
        self.assertEqual([1, 2], [row['voiceIndex'] for row in runtime.operations
                                if row['call'] == 0 and row['operation'] == 'sound'])
        self.assertEqual([0, 1, 2], [row['voiceIndex'] for row in runtime.operations
                                   if row['call'] == 1 and row['operation'] == 'sound'])

    def test_jump_transposed_and_standalone_transpose_do_not_push(self):
        program = {'start': dict(kind='transpose', transpose=254, next='jump'),
                   'jump': dict(kind='jump-transposed', transpose=3, target='note'),
                   'note': dict(kind='row', sourceNote=94, duration=1, next='end'),
                   'end': dict(kind='return')}
        runtime = self.runtime(program, active_mask=4)
        runtime.refresh(0)
        note = next(row for row in runtime.operations if row['operation'] == 'note')
        self.assertEqual(97, note['pitchIndex'])
        self.assertEqual(7, runtime.voices[2]['stackIndex'])

    def test_invalid_graph_byte_fields_stack_use_and_unbounded_command_loop_fail(self):
        with self.assertRaisesRegex(ValueError, 'reference'):
            self.runtime({'start': dict(kind='call', target='absent', next='start')})
        with self.assertRaisesRegex(ValueError, 'byte'):
            self.runtime({'start': dict(kind='loop', repeat=256, next='start')})
        runtime = self.runtime({'start': dict(kind='next', next='start')})
        with self.assertRaisesRegex(ValueError, 'stack'):
            runtime.refresh(0)
        runtime = self.runtime({'start': dict(kind='call', target='start', next='start')})
        with self.assertRaisesRegex(ValueError, 'stack'):
            runtime.refresh(0)
        runtime = self.runtime({'start': dict(kind='jump-transposed', transpose=0, target='start')},
                               active_mask=4)
        with self.assertRaisesRegex(ValueError, 'bounded'):
            runtime.refresh(0)

    def test_eighth_call_uses_unsigned_stack_byte_and_can_return(self):
        program = {'start': dict(kind='call', target='call1', next='end'),
                   'end': dict(kind='return'),
                   'row': dict(kind='row', sourceNote=96, duration=1, next='ret7')}
        for depth in range(1, 8):
            program[f'call{depth}'] = dict(kind='call', next=f'ret{depth - 1}',
                                           target=f'call{depth + 1}' if depth < 7 else 'row')
        for depth in range(8):
            program[f'ret{depth}'] = dict(kind='return')
        runtime = self.runtime(program)
        runtime.refresh(0)
        self.assertEqual(255, runtime.voices[0]['stackIndex'])
        runtime.refresh(1)
        self.assertEqual(0, runtime.active_mask)
        self.assertEqual(8, runtime.voices[0]['stackIndex'])

    def test_voice_specific_command_slots_are_enforced(self):
        for voice, kind, fields in ((0, 'write-data', dict(dataId='bank', next='end')),
                                    (1, 'transpose', dict(transpose=1, next='end')),
                                    (2, 'pulse', dict(dataId='bank', next='end'))):
            with self.subTest(voice=voice, kind=kind):
                runtime = self.runtime({'start': dict(kind=kind, **fields),
                                        'end': dict(kind='return')}, active_mask=1 << voice)
                with self.assertRaisesRegex(ValueError, 'unavailable'):
                    runtime.refresh(0)

    def test_runtime_detaches_input_and_callback_event_mutations(self):
        program = {'start': dict(kind='call-transposed', target='row', next='end', transpose=1),
                   'row': dict(kind='row', sourceNote=100, duration=1, next='return'),
                   'return': dict(kind='return'), 'end': dict(kind='return')}
        voices = initial_voices()
        original = copy.deepcopy((program, voices))

        def handle(runtime, event):
            event['call'] = 999

        runtime = self.runtime(program, voices=voices, callback=handle)
        runtime.refresh(0)
        self.assertEqual(original, (program, voices))
        self.assertEqual({0}, {row['call'] for row in runtime.operations})


class RamboVerificationGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'scripts/studies/rambo/check-rambo-player.py'
        spec = importlib.util.spec_from_file_location('rambo_verification', path)
        cls.checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.checker)
        cls.audit = json.loads((ROOT / 'evidence/rambo-form/complete40000/audit.json').read_text())
        cls.form = json.loads((ROOT / 'evidence/rambo-form/complete40000/form.json').read_text())

    def test_quiet_original_calls_require_the_audit_cap_not_the_last_write(self):
        self.checker.validate_coverage(self.audit, self.form, 11000)
        audit = copy.deepcopy(self.audit)
        audit['playCalls'] = 10815
        with self.assertRaisesRegex(ValueError, '40000'):
            self.checker.validate_coverage(audit, self.form, 11000)
        with self.assertRaisesRegex(ValueError, '64 quiet'):
            self.checker.validate_coverage(self.audit, self.form, 10878)
        with self.assertRaisesRegex(ValueError, 'integer'):
            self.checker.validate_coverage(self.audit, self.form, True)

    def test_compressed_reference_pin_is_checked_before_parsing(self):
        raw = gzip.compress(b'[{"phase":"init","tick":null,"address":54296,"value":15}]', mtime=0)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'writes.json.gz'
            path.write_bytes(raw)
            expected = hashlib.sha256(raw).hexdigest()
            self.assertEqual(15, self.checker.read_pinned_json(path, expected, compressed=True)[0]['value'])
            path.write_bytes(b'invalid compressed content')
            with self.assertRaisesRegex(ValueError, 'fingerprint'):
                self.checker.read_pinned_json(path, expected, compressed=True)

    def test_store_comparison_preserves_init_voice_order_and_call_labels(self):
        expected = [dict(phase='init', tick=None, address=0xd418, value=15, instructionStartCycle=12),
                    dict(phase='play', tick=50, address=0xd406, value=160, instructionStartCycle=60),
                    dict(phase='play', tick=50, address=0xd400, value=75, instructionStartCycle=70)]
        actual = [{key: value for key, value in row.items() if key != 'instructionStartCycle'}
                  for row in expected]
        self.checker.compare_writes(expected, actual)
        for changed in (actual[1:], [actual[0], actual[2], actual[1]],
                        [actual[0], dict(actual[1], tick=51), actual[2]]):
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, 'ordered store'):
                self.checker.compare_writes(expected, changed)


if __name__ == '__main__':
    unittest.main()
