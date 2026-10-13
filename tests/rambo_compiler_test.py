import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import AuditMemory, audit_psid
from rambo_player import LoaderPlayer
from verify_player import cpu_type


def compiler():
    spec = importlib.util.spec_from_file_location('compose_rambo', ROOT / 'scripts/compose-rambo.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def identity(rows):
    return [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]


def fixture(calls=32):
    description = json.loads((ROOT / 'songs/rambo-loader.json').read_text())
    description['range']['auditCalls'] = calls
    description['program'] = {'note': dict(kind='row', sourceNote=108, duration=3, next='stop'),
                              'stop': dict(kind='return')}
    for voice in description['voices']:
        voice['cursor'] = 'note'
    for data in description['initialData']:
        data[13] = data[17] = 0
        data[24:29] = [65, 17, 128, 2, 4]
    return description


class RamboCompilerTest(unittest.TestCase):
    def assert_model(self, description, *, every_call=True):
        compiled = compiler()
        sid, built = compiled.build(description)
        model = LoaderPlayer(description)
        calls = description['range']['auditCalls']
        selected = set(range(calls)) if every_call else {0, 49, 50, 10813, 10814, calls - 1}
        selected = {call for call in selected if call < calls}
        expected_states = {None: compiled.model_state(model)}
        for call in range(calls):
            model.play(call)
            if call in selected:
                expected_states[call] = compiled.model_state(model)
        checkpoints = {}

        def observer(cpu, memory):
            compiled.check_sid_writer(cpu, memory)
            boundary = (memory.phase == 'init' and cpu.pc == built['symbols']['rb_init_done']
                        or memory.phase == 'play' and memory.tick in selected
                        and cpu.pc == built['symbols']['rb_call_done'])
            if boundary and cpu.sp == 0xfd:
                checkpoints[memory.tick] = compiled.read_state(memory, built)

        audit, actual = audit_psid(sid, calls, observer=observer)
        self.assertEqual(identity(model.writes), identity(actual))
        self.assertEqual(expected_states, checkpoints)
        self.assertLess(audit['maximumPlayCycles'], audit['frameCycleBudget'])
        self.assertFalse(built['originalDriverIncluded'])
        self.assertFalse(built['registerDumpPlayback'])
        self.assertTrue(built['runtimeScoreScheduler'])
        return sid, built, audit

    def test_note_initialization_release_and_top_level_returns_match_cpu(self):
        self.assert_model(fixture())

    def test_live_data_copy_pokes_calls_loops_and_transposition_match_cpu(self):
        description = fixture(80)
        description['program'] = {
            'copy': dict(kind='volume', dataId='volume', next='poke'),
            'poke': dict(kind='poke-data', offset=33, value=2, next='loop'),
            'loop': dict(kind='loop', repeat=3, next='call'),
            'call': dict(kind='call-transposed', transpose=7, target='note', next='next'),
            'note': dict(kind='row', sourceNote=12, duration=1, next='return'),
            'return': dict(kind='return'),
            'next': dict(kind='next', next='hold'),
            'hold': dict(kind='row', sourceNote=191, duration=2, next='stop'),
            'stop': dict(kind='return'),
        }
        description['dataBanks'] = {'volume': [33, 3, 160, 1, 3]}
        for voice in description['voices']:
            voice['cursor'] = 'copy'
        self.assert_model(description)

    def test_morse_uses_live_repeat_aliases_and_reentrant_refresh(self):
        description = fixture(120)
        description['program'] = {
            'start': dict(kind='code', codeId='start-morse', next='pitch'),
            'pitch': dict(kind='code', codeId='morse-pitch-one', next='note'),
            'note': dict(kind='row', sourceNote=108, duration=4, next='transpose'),
            'transpose': dict(kind='code', codeId='increment-transpose', next='last'),
            'last': dict(kind='row', sourceNote=109, duration=2, next='stop'),
            'other': dict(kind='row', sourceNote=110, duration=3, next='stop'),
            'stop': dict(kind='return'),
        }
        description['voices'][0]['cursor'] = 'start'
        description['voices'][1]['cursor'] = description['voices'][2]['cursor'] = 'other'
        description['morse']['letters'] = [130, 132, 0]
        description['morse']['codes'][0] = 65
        self.assert_model(description)

    def test_complete_loader_matches_full_store_oracle_and_stopped_state(self):
        description = json.loads((ROOT / 'songs/rambo-loader.json').read_text())
        _, _, audit = self.assert_model(description, every_call=False)
        self.assertEqual(87534, audit['initWriteCount'] + audit['playWriteCount'])

    def test_reinitialization_restores_all_named_state_after_playback(self):
        description = fixture(16)
        compiled = compiler()
        payload, built = compiled.assemble_player(description)
        memory = AuditMemory()
        memory.data[built['loadAddress']:built['loadAddress'] + len(payload)] = payload
        cpu = cpu_type()(memory=memory)

        def call(label):
            cpu.stPushWord(0x1ff)
            cpu.pc = built['symbols'][label]
            for _ in range(100000):
                if cpu.pc == 0x200:
                    return
                memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
                cpu.step()
            self.fail('Compiled routine failed to return')

        call('entry_init')
        initial = compiled.read_state(memory, built)
        first = identity(memory.writes)
        memory.writes.clear()
        memory.phase = 'play'
        for tick in range(16):
            memory.tick = tick
            call('entry_play')
        memory.writes.clear()
        memory.phase, memory.tick = 'init', None
        call('entry_init')
        self.assertEqual(initial, compiled.read_state(memory, built))
        self.assertEqual(first, identity(memory.writes))

    def test_annotation_changes_do_not_change_binary(self):
        description = fixture(8)
        sid = compiler().build(description)[0]
        description['sourceEvidence'] = {'reference': '/absent.sid'}
        for node in description['program'].values():
            node.update(sourceAddress=65535, sourceOpcode=255)
        self.assertEqual(sid, compiler().build(description)[0])

    def test_edited_note_timing_sound_program_pitch_table_and_cold_state_match_cpu(self):
        description = fixture(32)
        description['program']['note']['duration'] = 5
        description['frequencyWords'][12] = 0x2468
        for voice, data in enumerate(description['initialData']):
            data[:8] = [254, 255, 3, 0, 250, 255, 1, 0]
            data[8:14] = [1, 2, 1, 1, 2, 7]
            data[14:24] = [2, 1, 1, 129, 17, 0, 239, 255, 0, 8]
            description['voices'][voice]['remaining'] = voice + 1
            description['voices'][voice]['stack'][0]['repeatRemaining'] = 37 + voice
            description['initialSound'][voice][24:26] = [90, 165]
        self.assert_model(description)

    def test_capped_run_rejects_later_unavailable_voice_commands_before_output(self):
        description = fixture(16)
        description['program']['note']['next'] = 'unsupported'
        description['program']['unsupported'] = dict(kind='code', codeId='start-morse', next='stop')
        with TemporaryDirectory() as directory:
            source = Path(directory) / 'description.json'
            source.write_text(json.dumps(description))
            output = Path(directory) / 'candidate'
            with self.assertRaisesRegex(ValueError, 'unavailable'):
                compiler().run(source, output, calls=1)
            self.assertFalse(output.exists())

    def test_capped_run_validates_full_numeric_range_and_records_timings(self):
        compiled = compiler()
        with TemporaryDirectory() as directory:
            source = Path(directory) / 'description.json'
            source.write_text(json.dumps(fixture(8)))
            report = compiled.run(source, Path(directory) / 'candidate', calls=1)
            self.assertEqual(1, report['checkedPlayCalls'])
            self.assertEqual(2, report['stateComparison']['matchedCheckpoints'])
            self.assertEqual({'model', 'assembly', 'cpuAudit', 'checkpointComparison', 'output'},
                             set(report['stageSeconds']))

    def test_relocated_and_oversized_unreachable_graphs_cannot_escape_callable_ram(self):
        compiled = compiler()
        with self.assertRaisesRegex(ValueError, 'callable RAM'):
            compiled.assemble_player(fixture(1), load_address=0x9f00)
        description = fixture(1)
        description['program'].update({f'unreachable-{index}':
                                       dict(kind='row', sourceNote=191, duration=1, next='stop')
                                       for index in range(6000)})
        with self.assertRaisesRegex(ValueError, 'callable RAM'):
            compiled.build(description)

    def test_state_reader_rejects_nonzero_unmapped_return_pointers(self):
        compiled = compiler()
        payload, built = compiled.assemble_player(fixture(1))
        memory = AuditMemory()
        memory.data[built['loadAddress']:built['loadAddress'] + len(payload)] = payload
        compiled.read_state(memory, built)
        memory.data[built['symbols']['rb_return_lo']] = 1
        with self.assertRaisesRegex(ValueError, 'pointer escapes'):
            compiled.read_state(memory, built)


if __name__ == '__main__':
    unittest.main()
