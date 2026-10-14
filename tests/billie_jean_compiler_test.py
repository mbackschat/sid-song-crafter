"""Guard independent runtime lowering, cold reset and actual PRG bootstrap."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/studies/billie-jean'))
import billie_jean_compiler as compiler
from billie_jean_player_test import example


class BillieJeanCompilerTest(unittest.TestCase):
    def test_callable_and_actual_prg_restore_poisoned_cold_state(self):
        value = example(calls=7)
        sid, built = compiler.build(value)
        verified, _ = compiler.verify(value, sid, built)
        self.assertEqual(verified['namedStateBoundaries'], 8)
        self.assertTrue(verified['resetVerification']['restoredPoisonedState'])
        prg, labels = compiler.standalone_prg(sid, built, value['range']['auditCalls'])
        self.assertTrue(compiler.bootstrap_verification(prg, labels, value, built)['passed'])

    def test_runtime_global_wrap_retains_transpose_and_sound_state(self):
        value = example([dict(header=32, note=20)], calls=9)
        for voice in value['score']['initialVoices']:
            voice['transpose'] = 7
            voice['holdFlag'] = 32
        for voice in value['initialSound']['voices']:
            voice.update(gate_mask=255, wave_cursor=4, age=5)
        sid, built = compiler.build(value)
        verified, _ = compiler.verify(value, sid, built)
        self.assertEqual(verified['namedStateBoundaries'], 10)

    def test_compiled_ending_uses_actual_control_and_stays_write_free_after_stop(self):
        value = example(calls=68)
        value['score']['initialDivider'] = 1
        value['initialSound']['filter']['mode'] = 48
        value['ending'] = dict(startCall=1, releaseCalls=2)
        sid, built = compiler.build(value)
        verified, writes = compiler.verify(value, sid, built)
        self.assertEqual(verified['namedStateBoundaries'], 69)
        self.assertEqual([(row['address'], row['value']) for row in writes if row['tick'] == 1],
            [(0xd404, 8), (0xd40b, 8), (0xd412, 8)])
        self.assertEqual([(row['address'], row['value']) for row in writes if row['tick'] == 3],
            [(0xd404, 0), (0xd40b, 0), (0xd412, 0), (0xd418, 48)])
        self.assertFalse(any(row['tick'] is not None and row['tick'] > 3 for row in writes))

    def test_compiled_glide_setters_transpose_and_rest_body_preserve_shared_ownership(self):
        value = example([dict(header=64, glideStep=20, glideTarget=25, note=20),
                         dict(header=192), dict(header=0, note=21)], calls=9)
        for order in value['score']['orders']:
            order['bytes'] = [135, 0, 255]
        sid, built = compiler.build(value)
        verified, _ = compiler.verify(value, sid, built)
        self.assertEqual(verified['namedStateBoundaries'], 10)

    def test_annotations_do_not_enter_payload_and_header_declares_native_target(self):
        value = example(calls=3)
        altered = deepcopy(value)
        altered['sourceEvidence'] = {'anything': 'nonexecuting'}
        altered['score']['orders'][0]['sourceAddress'] = 0xffff
        altered['score']['patterns']['0']['sourceAddress'] = 0xffff
        first, built = compiler.build(value)
        second, _ = compiler.build(altered)
        self.assertEqual(first, second)
        self.assertEqual(int.from_bytes(first[118:120], 'big'), 0x14)
        self.assertFalse(built['originalDriverIncluded'])
        self.assertTrue(built['runtimeScoreScheduler'])

    def test_full_numeric_admission_rejects_a_late_accessed_frequency_hole(self):
        value = example(calls=3)
        value['initialSound']['voices'][0]['gate_mask'] = 255
        value['score']['initialVoices'][0]['holdFlag'] = 32
        del value['sound']['programs']['frequencies']['20']
        with self.assertRaisesRegex(ValueError, 'Missing frequency index 20'):
            compiler.build(value)

    def test_decimal_mode_callers_get_binary_row_transpose(self):
        value = example(calls=1)
        value['score']['initialDivider'] = 1
        for order in value['score']['orders']:
            order['bytes'] = [135, 0, 255]
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
        self.assertEqual(compiler.identity(memory.writes), compiler.identity(compiler.player.compute(value)['writes']))


if __name__ == '__main__':
    unittest.main()
