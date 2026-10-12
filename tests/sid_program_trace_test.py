import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('sid_program_trace', ROOT / 'scripts/trace-sid-program.py')
trace = importlib.util.module_from_spec(spec)


def fixture():
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 2), (6, 124), (8, 0x1000), (10, 0x1000), (12, 0x1006), (14, 1), (16, 1), (118, 0x14)):
        header[offset:offset + 2] = value.to_bytes(2, 'big')
    init = bytes.fromhex('a9 0f 8d 18 d4 60')
    play = bytes.fromhex('ee 00 20 a2 01 bd ff 1f 18 69 50 9d 01 d4 60')
    return bytes(header) + init + play


class SidProgramTraceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec.loader.exec_module(trace)

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
            with self.subTest(first=first, last=last), self.assertRaises(ValueError):
                trace.trace_program(fixture(), first_call=first, last_call=last)


if __name__ == '__main__':
    unittest.main()
