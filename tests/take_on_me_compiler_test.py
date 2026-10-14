"""Guard runtime data lowering, callable execution and the actual PRG bootstrap."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/studies/take-on-me'))
import compiler


def diagnostic(calls=4):
    value = json.loads((ROOT / 'evidence/take-on-me-player/composition.json').read_text())
    value['range']['auditCalls'] = calls
    value.pop('ending', None)
    return value


class TakeOnMeCompilerTest(unittest.TestCase):
    def test_callable_and_actual_prg_restore_poisoned_initial_state(self):
        value = diagnostic()
        sid, built = compiler.build(value)
        verified, _ = compiler.verify(value, sid, built)
        self.assertTrue(verified['resetVerification']['restoredPoisonedState'])
        prg, labels = compiler.standalone_prg(sid, built, value['range']['auditCalls'])
        checked = compiler.bootstrap_verification(prg, labels, value, built)
        self.assertTrue(checked['passed'])
        self.assertEqual(checked['checkedPlayCalls'], 2)

    def test_compiled_release_and_later_silence_match_every_named_boundary(self):
        value = diagnostic(calls=69)
        value['ending'] = dict(startCall=2, releaseCalls=2)
        sid, built = compiler.build(value)
        verified, writes = compiler.verify(value, sid, built)
        self.assertEqual(verified['namedStateBoundaries'], 70)
        self.assertEqual([(row['address'], row['value']) for row in writes if row['tick'] == 4],
            [(0xd404, 0), (0xd40b, 0), (0xd412, 0), (0xd418, 16)])
        self.assertFalse(any(row['tick'] is not None and row['tick'] > 4 for row in writes))

    def test_annotations_do_not_enter_payload_or_original_driver(self):
        value = diagnostic()
        altered = deepcopy(value)
        altered['sourceEvidence'] = dict(sha256='not executable data')
        altered['score']['orders'][0]['address'] = 0xffff
        altered['score']['patterns']['0']['address'] = 0xffff
        first, built = compiler.build(value)
        second, _ = compiler.build(altered)
        self.assertEqual(first, second)
        self.assertEqual(int.from_bytes(first[118:120], 'big'), 0x24)
        self.assertFalse(built['originalDriverIncluded'])
        self.assertTrue(built['runtimeScoreScheduler'])

    def test_complete_numeric_preflight_rejects_an_accessed_lookup_hole(self):
        value = diagnostic()
        del value['sound']['programs']['frequencies']['2']
        with self.assertRaisesRegex(ValueError, 'Missing frequency index 2'):
            compiler.build(value)

    def test_decimal_mode_callers_get_binary_score_arithmetic(self):
        value = diagnostic(calls=1)
        value['score']['patterns']['2']['rows'][0]['note'] = 56
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
        expected = compiler.player.compute(value)
        self.assertEqual(compiler.identity(memory.writes), compiler.identity(expected['writes']))


if __name__ == '__main__':
    unittest.main()
