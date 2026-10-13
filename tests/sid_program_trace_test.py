from contextlib import contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import psid_audit

spec = importlib.util.spec_from_file_location('sid_program_trace', ROOT / 'scripts/trace-sid-program.py')
trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace)
SOURCE = ROOT / '.local/research/flashdance/drax-flashdance-conversion.sid'
ORACLE = ROOT / 'build/reference-studies/drax/flashdance.writes.json'


def fixture():
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 2), (6, 124), (8, 0x1000), (10, 0x1000), (12, 0x1006), (14, 1), (16, 1), (118, 0x14)):
        header[offset:offset + 2] = value.to_bytes(2, 'big')
    init = bytes.fromhex('a9 0f 8d 18 d4 60')
    play = bytes.fromhex('ee 00 20 a2 01 bd ff 1f 18 69 50 9d 01 d4 60')
    return bytes(header) + init + play


def paddle_fixture(init=bytes.fromhex('a9 00 8d 19 d4 8d 1a d4 a9 0f 8d 18 d4 60'),
                   play=bytes.fromhex('a9 50 8d 00 d4 60')):
    header = bytearray(fixture()[:124])
    header[12:14] = (0x1000 + len(init)).to_bytes(2, 'big')
    return bytes(header) + init + play


@contextmanager
def pinned_fixture(data):
    spec = importlib.util.spec_from_file_location('trace_fixture_reference', ROOT / 'scripts/study-drax-references.py')
    reference = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference)
    with patch.object(trace, 'load_reference', return_value=reference), \
            patch.dict(reference.REFERENCES['flashdance'], sha256=hashlib.sha256(data).hexdigest()):
        yield reference


class SidProgramTraceTest(unittest.TestCase):
    def test_indexed_writer_and_ram_operand_are_linked_without_changing_execution(self):
        data = fixture()
        expected_report, expected_writes = trace.audit_psid(data, 4)
        result = trace.trace_program(data, first_call=1, last_call=3)
        self.assertEqual(result['audit'], expected_report)
        writes = result['sidWrites']
        self.assertEqual([{key: value for key, value in row.items() if key != 'instructionPc'} for row in writes], [row for row in expected_writes if row['phase'] == 'play' and row['tick'] >= 1])
        self.assertEqual([row['instructionPc'] for row in writes], [0x1011] * 3)
        self.assertEqual([row['value'] for row in writes], [0x52, 0x53, 0x54])
        loads = [row for row in result['instructions'] if row['pc'] == 0x100b]
        self.assertEqual([row['operandAddress'] for row in loads], [0x2000] * 3)
        self.assertEqual([row['operandValueBefore'] for row in loads], [2, 3, 4])
        self.assertEqual({row['tick'] for row in result['instructions']}, {1, 2, 3})

    def test_initialization_writes_are_retained_outside_the_play_window(self):
        result = trace.trace_program(fixture(), first_call=1, last_call=3)
        self.assertEqual([{'phase': 'init', 'tick': None, 'instructionStartCycle': 2,
                          'address': 0xd418, 'value': 15}], result['initSidWrites'])
        self.assertNotIn('diagnostic', result)

    def test_flashdance_profile_is_private_and_leaves_default_paddle_rejection_intact(self):
        data = paddle_fixture()
        original = psid_audit.AuditMemory
        with self.assertRaisesRegex(ValueError, 'Unsupported I/O write'):
            trace.trace_program(data, first_call=0, last_call=0)
        with pinned_fixture(data):
            result = trace.trace_program(data, first_call=0, last_call=0, profile='flashdance-diagnostic')
        self.assertIs(original, psid_audit.AuditMemory)
        self.assertEqual([0x50], [row['value'] for row in result['sidWrites']])
        self.assertEqual([15], [row['value'] for row in result['initSidWrites']])
        self.assertIn('not a production', result['diagnostic']['classification'])
        self.assertEqual([{'phase': 'init', 'tick': None, 'address': address, 'value': 0}
                          for address in (0xd419, 0xd41a)], result['diagnostic']['ignoredInitPaddleWrites'])
        with self.assertRaisesRegex(ValueError, 'Unsupported I/O write'):
            trace.trace_program(data, first_call=0, last_call=0)

    def test_flashdance_profile_requires_the_manifest_pin_before_execution(self):
        data = paddle_fixture()
        with pinned_fixture(data) as reference:
            with patch.object(reference.FlashdanceDiagnosticMemory, '__init__', side_effect=AssertionError('Executed an unpinned source')):
                with self.assertRaisesRegex(ValueError, 'pinned'):
                    trace.trace_program(data + b'\x00', first_call=0, last_call=0, profile='flashdance-diagnostic')

    def test_flashdance_profile_rejects_nonzero_runtime_and_other_io_writes(self):
        invalid = (
            (paddle_fixture(init=bytes.fromhex('a9 01 8d 19 d4 8d 1a d4 60')), 'init zero'),
            (paddle_fixture(play=bytes.fromhex('a9 00 8d 19 d4 60')), 'init zero'),
            (paddle_fixture(play=bytes.fromhex('a9 00 8d 00 d5 60')), 'Unsupported I/O write'),
            (paddle_fixture(play=bytes.fromhex('ad 00 d4 60')), 'Unsupported I/O read'),
        )
        for data, message in invalid:
            with self.subTest(message=message), pinned_fixture(data), self.assertRaisesRegex(ValueError, message):
                trace.trace_program(data, first_call=0, last_call=0, profile='flashdance-diagnostic')

    def test_flashdance_profile_requires_exact_paddle_initialization_sequence(self):
        for init in (bytes.fromhex('a9 00 8d 19 d4 60'),
                     bytes.fromhex('a9 00 8d 1a d4 8d 19 d4 60'),
                     bytes.fromhex('a9 00 8d 19 d4 8d 1a d4 8d 1a d4 60')):
            data = paddle_fixture(init=init)
            with self.subTest(init=init.hex()), pinned_fixture(data), self.assertRaisesRegex(ValueError, 'sequence'):
                trace.trace_program(data, first_call=0, last_call=0, profile='flashdance-diagnostic')

    def test_unknown_profile_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'profile'):
            trace.trace_program(fixture(), first_call=0, last_call=0, profile='allow-io')

    def test_indirect_indexed_address_uses_zero_page_wrap(self):
        class Cpu:
            x, y = 2, 7
        memory = [0] * 65536
        memory[0xff], memory[0] = 0xfc, 0x1f
        self.assertEqual(trace.operand_address('iny', bytes([0xff]), Cpu(), memory), 0x2003)
        memory[1], memory[2] = 0x34, 0x12
        self.assertEqual(trace.operand_address('inx', bytes([0xff]), Cpu(), memory), 0x1234)

    def test_empty_backwards_or_excessive_windows_are_rejected(self):
        for first, last in ((-1, 4), (5, 4), (0, 512), (False, 1), (1, 100000)):
            for profile in ('strict', 'flashdance-diagnostic'):
                with self.subTest(first=first, last=last, profile=profile), self.assertRaisesRegex(ValueError, '1..512'):
                    trace.trace_program(fixture(), first_call=first, last_call=last, profile=profile)


@unittest.skipUnless(SOURCE.exists() and ORACLE.exists(), 'Requires pinned local SID and reference writes')
class FlashdanceTraceTest(unittest.TestCase):
    def test_pinned_profile_matches_cached_initialization_and_ordered_play_writes(self):
        result = trace.trace_program(SOURCE.read_bytes(), first_call=0, last_call=12, profile='flashdance-diagnostic')
        oracle = json.loads(ORACLE.read_text())
        identity = lambda row: (row['phase'], row['tick'], row['address'], row['value'])
        self.assertEqual([identity(row) for row in oracle if row['phase'] == 'init'],
                         [identity(row) for row in result['initSidWrites']])
        self.assertEqual([identity(row) for row in oracle if row['phase'] == 'play' and row['tick'] <= 12],
                         [identity(row) for row in result['sidWrites']])


if __name__ == '__main__':
    unittest.main()
