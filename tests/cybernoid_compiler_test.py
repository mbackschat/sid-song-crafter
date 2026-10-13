import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from cybernoid_player import compute_writes
from psid_audit import AuditMemory, audit_psid
from verify_player import cpu_type


def compiler():
    spec = importlib.util.spec_from_file_location('compose_cybernoid', ROOT / 'scripts/compose-cybernoid.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def identity(rows):
    return [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]


class CybernoidCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.description = json.loads((ROOT / 'songs/cybernoid-title.json').read_text())

    def fixture(self, calls=192):
        value = copy.deepcopy(self.description)
        value.pop('ending', None)
        value['play_calls'] = calls
        value['rows'] = [row for row in value['rows'] if row['call'] < calls]
        return value

    def assert_model(self, description):
        sid, built = compiler().build(description)
        audit, actual = audit_psid(sid, description['play_calls'])
        expected_rows, actual_rows = identity(compute_writes(description)), identity(actual)
        self.assertEqual(len(expected_rows), len(actual_rows))
        for index, (expected, observed) in enumerate(zip(expected_rows, actual_rows)):
            if expected != observed:
                self.fail(f'Ordered store {index}: expected {expected}, observed {observed}')
        self.assertLess(audit['maximumPlayCycles'], audit['frameCycleBudget'])
        self.assertLessEqual(built['loadAddress'] + built['payloadBytes'], 0xa000)
        self.assertFalse(built['originalDriverIncluded'])
        self.assertFalse(built['registerDumpPlayback'])
        return sid, built, audit

    def test_opening_ordered_writes_and_cold_preserved_pulse(self):
        description = self.fixture(2)
        description['rows'][0]['patchSetup'] = 'preserve'
        sid, _, _ = self.assert_model(description)
        _, actual = audit_psid(sid, 1)
        self.assertIn(('play', 0, 0xd411, 8), identity(actual))

    def test_note_and_program_edits_leave_the_input_unchanged(self):
        description = self.fixture()
        description['rows'][0]['commands'][-1]['sourceNote'] += 1
        description['records'][2]['wave'] = 0x41
        description['pulse_slots'][0][3] = 0x17
        before = copy.deepcopy(description)
        sid, _, _ = self.assert_model(description)
        self.assertEqual(before, description)
        description.pop('sourceEvidence', None)
        for row in description['rows']:
            row.pop('sourceEvidence', None)
        self.assertEqual(sid, compiler().build(description)[0])

    def test_reinitialization_restores_state_and_caller_zero_page(self):
        description = self.fixture()
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

    def test_row_schedule_must_follow_editable_countdowns(self):
        description = self.fixture()
        description['rows'][3]['call'] += 1
        with self.assertRaisesRegex(ValueError, 'Row/countdown mismatch'):
            compiler().build(description)

    def test_full_first_traversal_fits_ram_and_matches_the_model(self):
        _, built, audit = self.assert_model(self.fixture(17280))
        self.assertEqual(4331, built['rowCount'])
        self.assertEqual(297, built['uniqueRowPayloads'])
        self.assertLess(built['payloadBytes'], 24000)
        self.assertLess(audit['maximumPlayCycles'], 10000)


if __name__ == '__main__':
    unittest.main()
