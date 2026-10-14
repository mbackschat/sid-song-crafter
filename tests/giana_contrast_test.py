import importlib.util
from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools/test-deps'))
from py65.devices.mpu6502 import MPU


class GianaContrastTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            'giana_probe', ROOT / 'scripts/studies/giana/probe-contrast.py')
        cls.probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.probe)

    def test_returning_init_receives_selection_and_a_real_jsr_stack(self):
        program = self.probe.host_program()
        memory = [0] * 65536
        load = int.from_bytes(program[:2], 'little')
        memory[load:load + len(program) - 2] = program[2:]
        memory[0xcc86] = 0x60
        cpu = MPU(memory=memory, pc=load)
        cpu.a, cpu.x, cpu.y, cpu.sp, cpu.p = 2, 0, 0, 0xff, 0x20
        cpu.step()
        self.assertEqual((cpu.pc, cpu.a, cpu.x, cpu.y, cpu.p),
                         (0xcc86, 2, 0, 0, 0x20))
        self.assertEqual((cpu.sp, memory[0x1ff], memory[0x1fe]),
                         (0xfd, 0x04, 0x02))
        cpu.step()
        self.assertEqual((cpu.pc, cpu.sp), (0x0403, 0xff))
        for _ in range(3):
            cpu.step()
        self.assertEqual(cpu.pc, 0x0403)

    def test_mirrored_sid_store_retains_physical_address_and_instruction(self):
        log = ('#6 (Trace store d518) 256/$100, 17/$11\n'
               '.C:4890  8D 18 D5    STA $D518 - A:0F X:00 Y:00 SP:F9 ..-..... 120000\n')
        rows = self.probe.parse_records(log)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['address'], rows[0]['sidAddress'],
                          rows[0]['value'], rows[0]['pc'], rows[0]['bytes']),
                         (0xd518, 0xd418, 15, 0x4890, '8d18d5'))

    def test_store_address_and_instruction_disagreement_is_rejected(self):
        log = ('#6 (Trace store d418) 256/$100, 17/$11\n'
               '.C:4890  8D 17 D4    STA $D417 - A:0F X:00 Y:00 SP:F9 ..-..... 120000\n')
        with self.assertRaisesRegex(ValueError, 'address'):
            self.probe.parse_records(log)

    def test_unrecognized_or_truncated_trace_cannot_silently_shorten_ledger(self):
        for log in ('#6 (Trace store d418) malformed\n',
                    '#6 (Trace store d418) 256/$100, 17/$11\n'):
            with self.subTest(log=log), self.assertRaises(ValueError):
                self.probe.parse_records(log)

    def test_sid_rmw_is_rejected_instead_of_assuming_one_bus_write(self):
        log = ('#6 (Trace store d418) 256/$100, 17/$11\n'
               '.C:4890  CE 18 D4    DEC $D418 - A:0F X:00 Y:00 SP:F9 ..-..... 120000\n')
        with self.assertRaisesRegex(ValueError, 'RMW|supported'):
            self.probe.parse_records(log)

    def completion_log(self):
        observations = [
            ('Trace', 1, 0xcc86, 'A2 7F', 'LDX #$7F', 2, 0xfd, 10),
            ('Trace', 5, 0xccd9, '20 C9 41', 'JSR $41C9', 1, 0xfc, 20),
            ('Trace', 4, 0xccf1, '20 C0 41', 'JSR $41C0', 0, 0xf7, 30),
            ('Trace', 3, 0xccf0, '60', 'RTS', 0, 0xfd, 40),
            ('Stop on', 2, 0x0403, '4C 03 04', 'JMP $0403', 0, 0xff, 50),
            ('Trace', 4, 0xccf1, '20 C0 41', 'JSR $41C0', 0, 0xf9, 19686),
            ('Trace', 4, 0xccf1, '20 C0 41', 'JSR $41C0', 0, 0xf9, 39342),
            ('Trace', 4, 0xccf1, '20 C0 41', 'JSR $41C0', 0, 0xf9, 58998),
            ('Stop on', 13, 0xccf1, '20 C0 41', 'JSR $41C0', 0, 0xf9, 58998),
        ]
        return ''.join(
            f'#{number} ({kind} exec {pc:04x}) 256/$100, 17/$11\n'
            f'.C:{pc:04x}  {encoded}    {assembly} - A:{a:02X} X:00 Y:00 SP:{sp:02X} ..-..... {cycle}\n'
            for kind, number, pc, encoded, assembly, a, sp, cycle in observations)

    def test_completion_counts_init_irq_separately_from_requested_post_idle_irqs(self):
        rows = self.probe.parse_records(self.completion_log())
        _, summary = self.probe.summarize(rows, 2, {})
        self.assertEqual(summary['capture']['completedInitIrqRefreshes'], 1)
        self.assertEqual(summary['capture']['completedPostIdleRefreshes'], 2)
        self.assertEqual(summary['capture']['completedIrqRefreshes'], 3)
        self.assertFalse(summary['capture']['terminalIrqExecuted'])

    def test_missing_terminal_stop_cannot_be_called_completed(self):
        log = self.completion_log().split('#13 (Stop on')[0]
        with self.assertRaisesRegex(ValueError, 'stop|Stop|terminal'):
            self.probe.summarize(self.probe.parse_records(log), 2, {})

    def test_missing_first_idle_stop_cannot_be_called_completed(self):
        log = re.sub(r'#2 \(Stop on[^\n]*\n[^\n]*\n', '', self.completion_log())
        with self.assertRaisesRegex(ValueError, 'idle|stop|Stop'):
            self.probe.summarize(self.probe.parse_records(log), 2, {})

    def test_stop_after_fewer_post_idle_irqs_cannot_satisfy_request(self):
        log = self.completion_log().replace(
            '#4 (Trace exec ccf1) 256/$100, 17/$11\n'
            '.C:ccf1  20 C0 41    JSR $41C0 - A:00 X:00 Y:00 SP:F9 ..-..... 39342\n', '')
        with self.assertRaisesRegex(ValueError, 'count|requested|refresh'):
            self.probe.summarize(self.probe.parse_records(log), 2, {})

    def contract_log(self):
        records = [(1, 'TRACE', 'cc86', 'Trace exec'), (2, 'BREAK', '0403', 'Stop on exec'),
                   (3, 'TRACE', 'ccf0', 'Trace exec'), (4, 'TRACE', 'ccf1', 'Trace exec'),
                   (5, 'TRACE', 'ccd9', 'Trace exec'), (6, 'TRACE', 'ccb5', 'Trace exec'),
                   (7, 'TRACE', 'd400-$d7ff', 'Trace store'), (8, 'TRACE', 'd400-$d7ff', 'Trace load'),
                   (12, 'TRACE', '0000-$0001', 'Trace store'), (13, 'BREAK', 'ccf1', 'Stop on exec')]
        return ''.join(f'{kind}: {number}  C:${address}  ({operation})\n'
                       for number, kind, address, operation in records) + '>C:0000  2f 37 \n' * 3

    def test_missing_read_checkpoint_cannot_prove_zero_reads(self):
        log = self.contract_log()
        self.probe.validate_monitor_contract(log, [])
        log = re.sub(r'^TRACE: 8[^\n]*\n', '', log, flags=re.MULTILINE)
        with self.assertRaisesRegex(ValueError, 'coverage'):
            self.probe.validate_monitor_contract(log, [])

    def test_mirror_coverage_cannot_be_narrowed_to_canonical_registers(self):
        with self.assertRaisesRegex(ValueError, 'coverage'):
            self.probe.validate_monitor_contract(self.contract_log().replace('$d7ff', '$d418'), [])

    def test_port_snapshots_and_runtime_mutations_are_guarded(self):
        with self.assertRaisesRegex(ValueError, 'CPU port'):
            self.probe.validate_monitor_contract(self.contract_log().replace('2f 37', '2f 34', 1), [])
        with self.assertRaisesRegex(ValueError, 'CPU port'):
            self.probe.validate_monitor_contract(self.contract_log(), [dict(operation='store', address=1)])

    def test_wrong_raster_cannot_pass_only_by_frame_cadence(self):
        log = self.completion_log().replace('256/$100', '0/$000')
        with self.assertRaisesRegex(ValueError, 'raster'):
            self.probe.summarize(self.probe.parse_records(log), 2, {})

    def test_execution_after_stop_cannot_be_reported_as_unexecuted(self):
        rows = self.probe.parse_records(self.completion_log())
        rows.append(dict(rows[-2], monitorCycle=59004))
        with self.assertRaisesRegex(ValueError, 'continued'):
            self.probe.summarize(rows, 2, {})


if __name__ == '__main__':
    unittest.main()
