from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
from psid_audit import AuditMemory, audit_psid
from rambo_compiler_test import compiler, fixture, identity
from rambo_player import LoaderPlayer
from verify_player import cpu_type


def dual_compiler():
    spec = importlib.util.spec_from_file_location('compose_rambo_dual', ROOT / 'scripts/compose-rambo-dual.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pair(calls=32):
    primary, secondary = fixture(calls), fixture(calls)
    secondary['initialization']['volume'] = 9
    secondary['program']['note'].update(sourceNote=113, duration=5)
    for voice, block in enumerate(secondary['initialData']):
        block[24] = [0x47, 0x23, 0x15][voice]
        block[22:24] = [35 + voice, 4]
    return primary, secondary


def expected(primary, secondary):
    mono = compiler()
    players = [LoaderPlayer(description) for description in (primary, secondary)]
    states = {None: [mono.model_state(player) for player in players]}
    grouped = []
    for player in players:
        grouped.append({None: list(player.writes)})
    for call in range(primary['range']['auditCalls']):
        for bank, player in enumerate(players):
            start = len(player.writes)
            player.play(call)
            grouped[bank][call] = player.writes[start:]
        states[call] = [mono.model_state(player) for player in players]
    writes = [dict(row, address=row['address'] + bank * 32)
              for call in [None] + list(range(primary['range']['auditCalls']))
              for bank in range(2) for row in grouped[bank][call]]
    return writes, states


class RamboDualCompilerTest(unittest.TestCase):
    def assert_pair(self, primary, secondary):
        dual, mono = dual_compiler(), compiler()
        sid, built = dual.build(primary, secondary)
        expected_writes, expected_states = expected(primary, secondary)
        states = {}

        def observer(cpu, memory):
            mono.check_sid_writer(cpu, memory)
            boundary = (memory.phase == 'init' and cpu.pc == built['symbols']['dual_init_done']
                        or memory.phase == 'play' and cpu.pc == built['symbols']['dual_call_done'])
            if boundary and cpu.sp == 0xfd:
                states[memory.tick] = dual.read_state(memory, built)

        audit, writes = audit_psid(sid, primary['range']['auditCalls'], observer=observer)
        self.assertEqual(identity(expected_writes), identity(writes))
        self.assertEqual(expected_states, states)
        self.assertLessEqual(audit['maximumPlayCycles'], 19656)
        self.assertFalse(built['registerDumpPlayback'])
        self.assertFalse(built['originalDriverIncluded'])
        return sid, built, audit, writes, states

    def test_independent_six_voices_coupling_globals_masks_and_full_state_match_models(self):
        primary, secondary = pair()
        sid, built, audit, writes, states = self.assert_pair(primary, secondary)
        self.assertEqual((3, 0x54), tuple(int.from_bytes(sid[offset:offset + 2], 'big') for offset in (4, 118)))
        self.assertEqual(b'\x42\x00', sid[122:124])
        self.assertEqual([0xd400, 0xd420], [chip['baseAddress'] for chip in audit['sids']])
        self.assertTrue(all(chip['model'] == 'MOS6581' for chip in audit['sids']))
        a, b = built['players']
        self.assertLessEqual(built['loadAddress'] + built['wrapperBytes'], a['loadAddress'])
        self.assertLessEqual(a['loadAddress'] + a['payloadBytes'], b['loadAddress'])
        self.assertLessEqual(b['loadAddress'] + b['payloadBytes'], 0xa000)
        primary_payload, _ = compiler().assemble_player(primary, load_address=a['loadAddress'])
        primary_start = 124 + a['loadAddress'] - built['loadAddress']
        self.assertEqual(primary_payload, sid[primary_start:primary_start + a['payloadBytes']])
        self.assertEqual([0xd400, 0xd420], [engine['sidBase'] for engine in built['players']])
        self.assertEqual([0, 7, 14], list(b['voiceSidOffsets']))
        self.assertEqual([0, 7], [state['activeMask'] for state in states[3]])
        self.assertEqual([0, 0], [state['activeMask'] for state in states[5]])
        self.assertEqual([15, 9], [row['value'] for row in writes if row['phase'] == 'init'
                                 and row['address'] in (0xd418, 0xd438)])
        for base in (0xd400, 0xd420):
            for voice in range(3):
                self.assertTrue(any(row['phase'] == 'play' and row['address'] == base + voice * 7
                                    and row['value'] for row in writes))
            self.assertEqual([0], [row['value'] for row in writes
                                   if row['phase'] == 'init' and row['address'] == base + 23])
        self.assertEqual(sid, dual_compiler().build(primary, secondary)[0])

    def test_morse_reentrant_refresh_and_separate_graph_state_match_models(self):
        primary, secondary = pair(120)
        primary['program'] = {
            'start': dict(kind='code', codeId='start-morse', next='pitch'),
            'pitch': dict(kind='code', codeId='morse-pitch-one', next='note'),
            'note': dict(kind='row', sourceNote=108, duration=4, next='stop'),
            'other': dict(kind='row', sourceNote=110, duration=3, next='stop'),
            'stop': dict(kind='return'),
        }
        primary['voices'][0]['cursor'] = 'start'
        primary['voices'][1]['cursor'] = primary['voices'][2]['cursor'] = 'other'
        primary['morse']['letters'] = [130, 132, 0]
        primary['morse']['codes'][0] = 65
        self.assert_pair(primary, secondary)

    def test_secondary_edits_do_not_change_primary_writes_or_state(self):
        primary, secondary = pair()
        _, _, _, before, before_states = self.assert_pair(primary, secondary)
        edited = deepcopy(secondary)
        edited['program']['note'].update(sourceNote=119, duration=7)
        edited['initialData'][0][24] = 0x11
        _, _, _, after, after_states = self.assert_pair(primary, edited)
        bank = lambda rows, base: identity([row for row in rows if base <= row['address'] <= base + 24])
        self.assertEqual(bank(before, 0xd400), bank(after, 0xd400))
        self.assertNotEqual(bank(before, 0xd420), bank(after, 0xd420))
        self.assertEqual({call: state[0] for call, state in before_states.items()},
                         {call: state[0] for call, state in after_states.items()})

    def test_reinitialization_restores_both_engines_after_scratch_and_sid_corruption(self):
        primary, secondary = pair(16)
        dual = dual_compiler()
        sid, built = dual.build(primary, secondary)
        memory = AuditMemory((0xd400, 0xd420))
        load = built['loadAddress']
        memory.data[load:load + len(sid) - 124] = sid[124:]
        cpu = cpu_type()(memory=memory)

        def call(label):
            cpu.stPushWord(0x1ff)
            cpu.pc = built['symbols'][label]
            start = cpu.processorCycles
            while cpu.pc != 0x200:
                self.assertLess(cpu.processorCycles - start, 1000000)
                memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
                cpu.step()
            self.assertEqual(0xff, cpu.sp)

        observed = []
        for _ in range(2):
            memory.phase, memory.tick = 'init', None
            memory.writes.clear()
            memory.data[0xe0:0x100] = [0xa5] * 32
            for base in memory.sid_bases:
                memory.data[base:base + 25] = [0x55] * 25
            call('entry_init')
            self.assertEqual([compiler().model_state(LoaderPlayer(description)) for description in (primary, secondary)],
                             dual.read_state(memory, built))
            for base, volume in zip(memory.sid_bases, (15, 9)):
                self.assertEqual([0] * 24 + [volume], memory.data[base:base + 25])
            memory.phase = 'play'
            for tick in range(16):
                memory.tick = tick
                memory.data[0xe0:0x100] = [tick ^ 0xa5] * 32
                call('entry_play')
            observed.append(identity(memory.writes))
        self.assertEqual(observed[0], observed[1])
        self.assertEqual(identity(expected(primary, secondary)[0]), observed[0])

    def test_run_records_both_engine_checkpoints_and_all_executed_sid_writers(self):
        primary, secondary = pair(8)
        with TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ('a.json', 'b.json')]
            for path, description in zip(paths, (primary, secondary)):
                path.write_text(json.dumps(description))
            output = Path(directory) / 'output'
            report = dual_compiler().run(*paths, output, calls=3)
            audit = json.loads((output / 'audit.json').read_text())
            writes = json.loads((output / 'writes.json').read_text())
            states = json.loads((output / 'state-checkpoints.json').read_text())
            self.assertEqual(3, report['checkedPlayCalls'])
            self.assertEqual(4, report['stateComparison']['matchedCheckpoints'])
            self.assertEqual(len(writes), report['sidWriterValidation']['checkedStores'])
            self.assertEqual(audit['initWriteCount'] + audit['playWriteCount'], len(writes))
            self.assertEqual(2, len(states[0]['state']))
            for name in ('primary', 'secondary', 'wrapper'):
                self.assertTrue((output / f'{name}.asm').is_file())
                self.assertTrue((output / f'{name}.listing').is_file())

    def test_capped_run_cannot_hide_later_unsupported_command(self):
        primary, secondary = pair(8)
        secondary['program']['note']['next'] = 'unsupported'
        secondary['program']['unsupported'] = dict(kind='code', codeId='start-morse', next='stop')
        with TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ('a.json', 'b.json')]
            for path, description in zip(paths, (primary, secondary)):
                path.write_text(json.dumps(description))
            output = Path(directory) / 'output'
            with self.assertRaisesRegex(ValueError, 'unavailable'):
                dual_compiler().run(*paths, output, calls=1)
            self.assertFalse(output.exists())

    def test_invalid_pair_ranges_sid_relocation_and_ram_overruns_are_rejected(self):
        primary, secondary = pair(8)
        secondary['range']['auditCalls'] = 9
        with self.assertRaisesRegex(ValueError, 'auditCalls'):
            dual_compiler().build(primary, secondary)
        with self.assertRaisesRegex(ValueError, 'SID base'):
            compiler().assemble_player(primary, sid_base=0xd440)
        with self.assertRaisesRegex(ValueError, 'stereo-bass'):
            compiler().assemble_player(primary, sid_base=0xd420, stereo_bass=True)
        primary, secondary = pair(1)
        secondary['program'].update({f'unreachable-{index}': dict(kind='row', sourceNote=191, duration=1, next='stop')
                                     for index in range(4500)})
        with self.assertRaisesRegex(ValueError, 'callable RAM'):
            dual_compiler().build(primary, secondary)

    def test_two_individually_valid_workloads_cannot_exceed_the_shared_pal_frame(self):
        primary = fixture(1)
        for index in range(20):
            primary['program'][f'poke-{index}'] = dict(
                kind='poke-data', offset=22, value=index,
                next=f'poke-{index + 1}' if index < 19 else 'note')
        for voice in primary['voices']:
            voice['cursor'] = 'poke-0'
        secondary = deepcopy(primary)
        for description in (primary, secondary):
            sid, _ = compiler().build(description)
            report, _ = audit_psid(sid, 1)
            self.assertGreater(report['maximumPlayCycles'], 19656 // 2)
            self.assertLessEqual(report['maximumPlayCycles'], 19656)
        with TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ('a.json', 'b.json')]
            for path, description in zip(paths, (primary, secondary)):
                path.write_text(json.dumps(description))
            output = Path(directory) / 'output'
            with self.assertRaisesRegex(ValueError, '19656-cycle call budget'):
                dual_compiler().run(*paths, output)
            self.assertFalse(output.exists())

    def test_default_mono_export_remains_byte_identical(self):
        description = json.loads((ROOT / 'songs/rambo-loader.json').read_text())
        self.assertEqual((ROOT / 'samples/rambo-loader/rambo-loader.sid').read_bytes(), compiler().build(description)[0])


if __name__ == '__main__':
    unittest.main()
