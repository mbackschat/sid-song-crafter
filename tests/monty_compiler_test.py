import copy
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from monty_title_player import compute_player, compute_writes
from psid_audit import AuditMemory, audit_psid
from verify_player import cpu_type


def compiler():
    spec = importlib.util.spec_from_file_location('compose_monty', ROOT / 'scripts/compose-monty.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def identity(rows):
    return [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]


def fixture(calls=64):
    voice = dict(note=0, control=0, remaining=0, held_frequency=0, voice_control=65,
                 pulse_delay=0, pulse_direction=0, portamento=0, instrument_index=0,
                 order_cursor=0, pattern_cursor=0)
    aliases = [(208, 0, 'voice_control'), (209, 1, 'voice_control'),
               (210, 2, 'voice_control'), (211, 0, 'note'),
               (232, 0, 'pulse_direction'), (233, 1, 'pulse_direction')]
    return dict(format='monty-editable-title-v1', play_calls=calls,
                initial_state=dict(globals=dict(tempo_countdown=0, tempo_reload=1, counter=250,
                                               status=64, mode_volume=15, sfx_priority=0,
                                               sfx_flags=255, output_enable=255),
                                   voices=[copy.deepcopy(voice) for _ in range(3)]),
                instruments=[dict(pulse_word=0x880, waveform=65, attack_decay=17,
                                  sustain_release=128, vibrato_depth=2, pulse_value=0xa0, effects=4)],
                frequency_words=[0x200 + index * 19 for index in range(96)],
                frequency_alias_bindings=[dict(offset=offset, voice_index=voice, field=field)
                                          for offset, voice, field in aliases],
                score=dict(orders=[dict(voice_index=voice, bytes=[0, 255]) for voice in range(3)],
                           patterns=[dict(pattern_id=0, bytes=[0x81, 0, 12, 0x60, 255])]))


class MontyCompilerTests(unittest.TestCase):
    def test_run_uses_one_full_model_traversal_for_capped_cpu_and_state_checks(self):
        compiled = compiler()
        with TemporaryDirectory() as directory:
            source = Path(directory) / 'title.json'
            source.write_text(json.dumps(fixture(8)))
            output = Path(directory) / 'candidate'
            with patch.object(compiled, 'compute_player', wraps=compute_player) as model:
                report = compiled.run(source, output, calls=1)
            model.assert_called_once()
            self.assertNotIn('calls', model.call_args.kwargs)
            self.assertEqual({0, 1}, set(model.call_args.kwargs['checkpoint_calls']))
            self.assertEqual(1, report['checkedPlayCalls'])
            self.assertEqual(2, report['stateComparison']['matchedCheckpoints'])
            self.assertEqual(report, json.loads((output / 'build.json').read_text()))
            self.assertEqual({'model', 'assembly', 'cpuAudit', 'checkpointComparison', 'output'},
                             set(report['stageSeconds']))
            self.assertTrue(all(type(value) is float and value >= 0 for value in report['stageSeconds'].values()))

    def test_capped_run_still_rejects_unmapped_numeric_reads_after_the_cpu_prefix(self):
        compiled = compiler()
        description = fixture(8)
        description['score']['patterns'][0]['bytes'] = [0, 12, 0, 96, 255]
        with TemporaryDirectory() as directory:
            source = Path(directory) / 'title.json'
            source.write_text(json.dumps(description))
            output = Path(directory) / 'candidate'
            with self.assertRaisesRegex(ValueError, 'unmapped frequency alias'):
                compiled.run(source, output, calls=1)
            self.assertFalse(output.exists())

    def assert_model(self, description):
        compiled = compiler()
        sid, built = compiled.build(description)
        checkpoints = []
        selected_calls = {0, 1, description['play_calls'] - 1}

        def observer(cpu, memory):
            boundary = (memory.phase == 'init' and cpu.pc == built['symbols']['mo_init_done']
                        or memory.phase == 'play' and memory.tick in selected_calls
                        and cpu.pc == built['symbols']['mo_call_done'])
            if boundary and cpu.sp == 0xfd:
                calls = 0 if memory.phase == 'init' else memory.tick + 1
                checkpoints.append((calls, compiled.read_state(memory, built)))

        audit, actual = audit_psid(sid, description['play_calls'], observer=observer)
        expected_rows, actual_rows = identity(compute_writes(description)), identity(actual)
        self.assertEqual(len(expected_rows), len(actual_rows))
        for index, (expected, observed) in enumerate(zip(expected_rows, actual_rows)):
            if expected != observed:
                self.fail(f'Ordered store {index}: expected {expected}, observed {observed}')
        self.assertLess(audit['maximumPlayCycles'], audit['frameCycleBudget'])
        self.assertLessEqual(built['loadAddress'] + built['payloadBytes'], 0xa000)
        self.assertFalse(built['originalDriverIncluded'])
        self.assertFalse(built['registerDumpPlayback'])
        self.assertEqual(1 + len(selected_calls), len(checkpoints))
        for calls, state in checkpoints:
            numeric = compute_player(description, calls=calls)
            self.assertEqual(numeric['finalState'], state['finalState'])
            self.assertEqual(numeric['instruments'], state['instruments'])
            self.assertEqual(numeric['stopped'], state['stopped'])
        return sid, built, audit

    def test_runtime_rows_append_and_order_restart_match_model(self):
        self.assert_model(fixture())

    def test_late_aliases_follow_current_state_after_shared_pwm(self):
        description = fixture(4)
        description['score']['patterns'][0]['bytes'][2] = 104
        description['instruments'][0].update(pulse_word=0xdc0, pulse_value=0x40)
        description['initial_state']['voices'][0]['voice_control'] = 0x21
        description['initial_state']['voices'][1]['voice_control'] = 0x81
        before = copy.deepcopy(description)
        sid, _, _ = self.assert_model(description)
        self.assertEqual(before, description)
        _, actual = audit_psid(sid, description['play_calls'])
        voice2_start = [(row['address'], row['value']) for row in actual
                        if row['phase'] == 'play' and row['tick'] == 0 and 0xd40e <= row['address'] <= 0xd414]
        self.assertEqual([(0xd40f, 0x81), (0xd40e, 0x21)], voice2_start[:2])
        voice0_body = [(row['address'], row['value']) for row in actual
                       if row['phase'] == 'play' and row['tick'] == 1 and 0xd400 <= row['address'] <= 0xd406]
        self.assertEqual([(0xd401, 1), (0xd400, 1)], voice0_body[-2:])
        description['sourceEvidence'] = dict(reference='/absent.sid', events=[dict(value=0)])
        self.assertEqual(sid, compiler().build(description)[0])

    def test_numeric_edits_change_score_timing_and_sound_without_schedules(self):
        description = fixture()
        description['initial_state']['globals']['tempo_reload'] = 2
        description['score']['patterns'][0]['bytes'] = [0x80, 0x91, 14, 0x81, 0, 15, 255]
        description['instruments'][0].update(effects=3, waveform=0x81, pulse_value=0xe1)
        self.assert_model(description)

    def test_adjacent_lookup_can_read_typed_alias_bytes_256_and_257(self):
        description = fixture(8)
        description['score']['patterns'][0]['bytes'][2] = 127
        description['frequency_alias_bindings'].extend([
            dict(offset=254, voice_index=0, field='voice_control'),
            dict(offset=255, voice_index=1, field='voice_control'),
            dict(offset=256, voice_index=2, field='note'),
            dict(offset=257, voice_index=2, field='pulse_delay')])
        self.assert_model(description)

    def test_initial_image_can_restore_all_32_instruments_across_byte_pages(self):
        description = fixture(8)
        description['instruments'] = [copy.deepcopy(description['instruments'][0]) for _ in range(32)]
        description['instruments'][31]['pulse_word'] = 0xe40
        description['score']['patterns'][0]['bytes'][1] = 31
        _, built, _ = self.assert_model(description)
        self.assertGreater(built['stateBytes'], 255)

    def test_reinitialization_restores_shared_bank_and_caller_zero_page(self):
        description = fixture()
        sid, built = compiler().build(description)
        memory = AuditMemory()
        load = built['loadAddress']
        memory.data[load:load + built['payloadBytes']] = sid[124:]
        memory.data[2:256] = range(2, 256)
        zero_page = memory.data[:256]
        cpu = cpu_type()(memory=memory)

        def call(label):
            cpu.stPushWord(0x01ff)
            cpu.pc = built['symbols'][label]
            start = cpu.processorCycles
            while cpu.pc != 0x0200:
                self.assertLess(cpu.processorCycles - start, 19656)
                cpu.step()
            self.assertEqual(255, cpu.sp)
            self.assertEqual(zero_page, memory.data[:256])

        runs = []
        for _ in range(2):
            memory.writes = []
            memory.phase, memory.tick = 'init', None
            call('entry_init')
            memory.phase = 'play'
            for tick in range(description['play_calls']):
                memory.tick = tick
                call('entry_play')
            runs.append(identity(memory.writes))
        self.assertEqual(runs[0], runs[1])
        self.assertEqual(identity(compute_writes(description)), runs[0])

    def test_unsupported_context_and_unmapped_aliases_reject_before_compiling(self):
        for calls in (0, 65536, True):
            with self.subTest(calls=calls), self.assertRaisesRegex(ValueError, '1..65535'):
                compiler().build(fixture(calls))
        description = fixture()
        description['score']['orders'][2]['bytes'][0] = 254
        with self.assertRaisesRegex(ValueError, 'FE'):
            compiler().build(description)
        description = fixture()
        description['score']['patterns'][0]['bytes'][2] = 127
        with self.assertRaisesRegex(ValueError, 'alias'):
            compiler().build(description)

    def test_finite_tail_clears_actual_controls_freezes_score_fades_and_stops(self):
        description = fixture(132)
        description['ending'] = dict(start_call=4, release_calls=64, fade_step_calls=4)
        description['score']['patterns'][0]['bytes'] = [0xbf, 0, 12, 255]
        description['instruments'][0].update(waveform=1, effects=1, vibrato_depth=0, pulse_value=0)
        sid, built, _ = self.assert_model(description)
        _, actual = audit_psid(sid, description['play_calls'] + 3)
        self.assertEqual(identity(compute_writes(description)), identity(actual))
        first_tail = [(row['address'], row['value']) for row in actual
                      if row['phase'] == 'play' and row['tick'] == 4]
        self.assertEqual([(0xd418, 15), (0xd412, 128), (0xd40b, 128), (0xd404, 128)], first_tail[:4])
        self.assertTrue(built['finiteMusicalEnding'])
        self.assertFalse(any(row['value'] & 1 for row in actual if row['phase'] == 'play'
                             and row['tick'] >= 4 and row['address'] in (0xd404, 0xd40b, 0xd412)))
        volumes = [row['value'] for row in actual if row['phase'] == 'play' and row['address'] == 0xd418]
        self.assertEqual([15] * 68 + [volume for volume in range(15, -1, -1) for _ in range(4)], volumes)


if __name__ == '__main__':
    unittest.main()
