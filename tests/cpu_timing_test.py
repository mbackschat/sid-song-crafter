import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import psid_audit
from verify_player import CYCLES_PER_FRAME, cpu_type


def load_exporter():
    spec = importlib.util.spec_from_file_location('sidwizard_cpu_timing_exporter', ROOT / 'scripts/export-sidwizard.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def decrement_workload(count):
    header = bytearray(0x7c)
    header[:4] = b'PSID'
    for offset, value in ((4, 2), (6, 0x7c), (8, 0x1000), (10, 0x1000),
                          (12, 0x1001), (14, 1), (16, 1), (118, 0x14)):
        header[offset:offset + 2] = value.to_bytes(2, 'big')
    return bytes(header) + b'\x60' + b'\xce\x00\x90' * count + b'\x60'


class CpuTimingTests(unittest.TestCase):
    def test_absolute_decrement_costs_six_cycles_for_ram_addresses_and_values(self):
        for address in (0x0040, 0x0100, 0x03ff, 0x2000, 0x9fff):
            for value in (0, 1, 127, 128, 255):
                memory = [0] * 65536
                memory[0x1000:0x1003] = [0xce, address & 255, address >> 8]
                memory[address] = value
                cpu = cpu_type()(memory=memory, pc=0x1000)
                cpu.step()
                self.assertEqual(6, cpu.processorCycles, (address, value))
                self.assertEqual((value - 1) & 255, memory[address])

    def test_other_decrement_modes_keep_their_nmos_timings(self):
        vectors = (([0xc6, 0x40], 0, 0x40, 5), ([0xd6, 0x40], 5, 0x45, 6),
                   ([0xde, 0x00, 0x20], 1, 0x2001, 7), ([0xde, 0xff, 0x01], 1, 0x0200, 7))
        for code, index, address, cycles in vectors:
            memory = [0] * 65536
            memory[0x1000:0x1000 + len(code)] = code
            memory[address] = 2
            cpu = cpu_type()(memory=memory, pc=0x1000)
            cpu.x = index
            cpu.step()
            self.assertEqual(cycles, cpu.processorCycles)
            self.assertEqual(1, memory[address])

    def test_loader_uses_a_private_table_without_changing_upstream(self):
        cpu_type()
        from py65.devices.mpu6502 import MPU
        original = list(MPU.cycletime)
        corrected = cpu_type()
        self.assertIsNot(corrected.cycletime, MPU.cycletime)
        self.assertEqual(original, MPU.cycletime)
        expected = original.copy()
        expected[0xce] = 6
        self.assertEqual(expected, corrected.cycletime)

    def test_loader_remains_compatible_with_an_already_correct_upstream(self):
        cpu_type()
        from py65.devices.mpu6502 import MPU

        class CorrectUpstream(MPU):
            cycletime = MPU.cycletime.copy()
            cycletime[0xce] = 6

        before = CorrectUpstream.cycletime.copy()
        with patch('py65.devices.mpu6502.MPU', CorrectUpstream):
            corrected = cpu_type()
        self.assertEqual(before, corrected.cycletime)
        self.assertEqual(before, CorrectUpstream.cycletime)
        memory = [0] * 65536
        memory[0x1000:0x1003] = [0xce, 0x00, 0x20]
        cpu = corrected(memory=memory, pc=0x1000)
        cpu.step()
        self.assertEqual(6, cpu.processorCycles)

    def test_correct_timing_rejects_a_callable_workload_the_undercount_accepts(self):
        cpu_type()
        from py65.devices.mpu6502 import MPU

        class UndercountedCpu(MPU):
            cycletime = MPU.cycletime.copy()
            cycletime[0xce] = 3

        count = 3300
        data = decrement_workload(count)
        with patch.object(psid_audit, 'cpu_type', return_value=UndercountedCpu):
            report, writes = psid_audit.audit_psid(data, 1)
        self.assertEqual(count * 3 + 6, report['maximumPlayCycles'])
        self.assertLess(report['maximumPlayCycles'], CYCLES_PER_FRAME)
        self.assertGreater(count * 6 + 6, CYCLES_PER_FRAME)
        self.assertEqual([], writes)
        with self.assertRaisesRegex(ValueError, f'Driver exceeds {CYCLES_PER_FRAME}-cycle call budget'):
            psid_audit.audit_psid(data, 1)

    def test_sidwizard_exporter_uses_correct_absolute_decrement_timing(self):
        exporter = load_exporter()
        memory = [0] * 65536
        memory[0x1000:0x1004] = [0xce, 0x00, 0x20, 0x60]
        memory[0x2000] = 2
        cpu = exporter.cpu_type()(memory=memory)
        self.assertEqual(12, exporter.call(cpu, {'play': 0x1000}, 'play'))
        self.assertEqual(1, memory[0x2000])


if __name__ == '__main__':
    unittest.main()
