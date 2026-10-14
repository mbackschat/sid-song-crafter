"""Guard runtime Airwolf rows, authored releases and the independent CPU boundary."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/studies/airwolf'))
import airwolf_compiler as compiler
import airwolf_player as player


def example(calls=12):
    return player.from_score(dict(rows=[dict(duration=2, notes=[0x09ab, 0x1234, 0x4567]),
        dict(duration=1, notes=[None, 'off', 0x6789])]), calls=calls)


class AirwolfCompilerTest(unittest.TestCase):
    def test_init_rows_wrap_and_every_named_return_match_with_poisoned_reset(self):
        value = example()
        sid, built = compiler.build(value)
        checked, writes = compiler.verify(value, sid, built)
        self.assertEqual(checked['namedStateBoundaries'], 13)
        self.assertEqual(checked['sidWriterValidation']['checkedStores'], len(writes))
        self.assertTrue(checked['resetVerification']['restoredPoisonedState'])
        self.assertTrue(checked['resetVerification']['restoredWorkspace'])
        wrap = [row for row in writes if row['tick'] == 4]
        self.assertEqual([(row['address'], row['value']) for row in wrap[:6]],
            [(0xd418, 15), (0xd403, 40), (0xd40a, 10)] * 2)
        self.assertEqual([(row['address'], row['value']) for row in writes if row['tick'] == 2][3:5],
            [(0xd40b, 64), (0xd413, 9)])
        self.assertFalse({row['address'] for row in writes} & {0xd402, 0xd409, 0xd410, 0xd411, 0xd415, 0xd416, 0xd417})

    def test_full_byte_duration_uses_underflow_equality_and_255_rows_fit_index(self):
        value = example(calls=260)
        value['rows'][0]['duration'] = 255
        sid, built = compiler.build(value)
        checked, _ = compiler.verify(value, sid, built)
        self.assertEqual(checked['namedStateBoundaries'], 261)
        value = example(calls=512)
        value['rows'] = [dict(duration=1, notes=[0x1000 + index, None, None]) for index in range(255)]
        sid, built = compiler.build(value)
        checked, writes = compiler.verify(value, sid, built)
        self.assertEqual(checked['namedStateBoundaries'], 513)
        self.assertEqual(len([row for row in writes if row['tick'] == 509]), 12)

    def test_patch_edits_change_runtime_stores_without_changing_writer_order(self):
        value = example()
        value['sound'] = dict(volume=7, pulseHigh=[0xfe, 0x81], voices=[
            dict(attackDecay=0x92, sustainRelease=0xa4, control=33),
            dict(attackDecay=0x23, sustainRelease=0x45, control=129),
            dict(attackDecay=0x67, sustainRelease=0x89, control=65)])
        sid, built = compiler.build(value)
        _, writes = compiler.verify(value, sid, built)
        init = [(row['address'], row['value']) for row in writes if row['phase'] == 'init']
        self.assertEqual(init[:9], [(0xd418, 7), (0xd403, 254), (0xd40a, 129),
            (0xd405, 146), (0xd406, 164), (0xd404, 0), (0xd404, 33), (0xd401, 9), (0xd400, 171)])
        self.assertIn((0xd40b, 128), [(row['address'], row['value']) for row in writes if row['tick'] == 2])

    def test_ending_crosses_word_counter_carry_and_leaves_64_calls_write_free(self):
        value = example(calls=325)
        value['ending'] = dict(startCall=257, releaseCalls=3)
        sid, built = compiler.build(value)
        checked, writes = compiler.verify(value, sid, built)
        self.assertEqual(checked['namedStateBoundaries'], 326)
        self.assertEqual([(row['address'], row['value']) for row in writes if row['tick'] == 257],
            [(0xd404, 64), (0xd40b, 64), (0xd412, 16)])
        self.assertEqual([(row['address'], row['value']) for row in writes if row['tick'] == 260],
            [(0xd404, 0), (0xd40b, 0), (0xd412, 0), (0xd418, 0)])
        self.assertFalse(any(row['tick'] is not None and row['tick'] > 260 for row in writes))
        self.assertEqual(checked['checkpoints'][-1]['state']['ending'], dict(phase=2, nextCall=260))

    def test_metadata_is_nonruntime_and_psid_declares_one_pal_6581(self):
        value = example()
        sid, built = compiler.build(value)
        altered = deepcopy(value)
        altered['sourceEvidence'] = dict(executable=[0xea], capturedStores=[1, 2, 3])
        altered['rows'][0]['sourceAddress'] = 0xffff
        changed, _ = compiler.build(altered)
        self.assertEqual(sid, changed)
        self.assertEqual(int.from_bytes(sid[118:120], 'big'), 0x14)
        self.assertEqual(sid[122:124], b'\0\0')
        self.assertFalse(built['originalDriverIncluded'])
        self.assertFalse(built['registerDumpPlayback'])
        self.assertTrue(built['runtimeScoreScheduler'])
        altered['title'] = 'An authored title'
        changed, _ = compiler.build(altered)
        self.assertEqual(changed[124:], sid[124:])

    def test_full_admission_rejects_invalid_late_rows_and_unsupported_sound(self):
        value = example(calls=1)
        value['rows'][1]['notes'][0] = 255
        with self.assertRaisesRegex(ValueError, 'Frequency word'):
            compiler.build(value)
        value = example()
        value['sound']['voices'][0]['control'] = 67
        with self.assertRaisesRegex(ValueError, 'single waveform'):
            compiler.build(value)

    def test_decimal_callers_and_actual_prg_bootstrap_use_binary_state(self):
        value = example(calls=2)
        sid, built = compiler.build(value)
        memory = compiler.AuditMemory()
        memory.data[compiler.LOAD:compiler.LOAD + len(sid) - 124] = sid[124:]
        cpu = compiler.cpu_type()(memory=memory)
        for phase, tick, label in (('init', None, 'entry_init'), ('play', 0, 'entry_play')):
            memory.phase, memory.tick = phase, tick
            cpu.p |= cpu.DECIMAL
            cpu.stPushWord(0x01ff)
            cpu.pc = built['symbols'][label]
            began = cpu.processorCycles
            while cpu.pc != 0x0200:
                self.assertLess(cpu.processorCycles - began, 19656)
                memory.instruction = cpu.disassemble[memory.data[cpu.pc]][0]
                cpu.step()
            self.assertFalse(cpu.p & cpu.DECIMAL)
            self.assertEqual(cpu.sp, 255)
        self.assertEqual(compiler.identity(memory.writes), compiler.identity(player.compute(value, calls=1)['writes']))
        prg, labels = compiler.standalone_prg(sid, built, 2)
        checked = compiler.bootstrap_verification(prg, labels, value, built)
        self.assertTrue(checked['passed'])
        self.assertEqual(checked['checkedPlayCalls'], 2)

    def test_export_has_nine_reviewable_files_and_rejects_reused_output(self):
        value = example(calls=2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'composition.json'
            path.write_text(json.dumps(value))
            output = Path(directory) / 'compiled'
            checked = compiler.run(path, output)
            self.assertTrue(checked['completeCompiledRange'])
            self.assertEqual({item.name for item in output.iterdir()}, {'reconstructed.sid', 'reconstructed.prg',
                'player.asm', 'player.listing', 'build.json', 'audit.json', 'writes.json',
                'state-checkpoints.json', 'verification.json'})
            with self.assertRaisesRegex(ValueError, 'fresh directory'):
                compiler.run(path, output)


if __name__ == '__main__':
    unittest.main()
