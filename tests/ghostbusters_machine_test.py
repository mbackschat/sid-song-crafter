import importlib.util
from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools/test-deps'))
from py65.devices.mpu6502 import MPU


class GhostbustersMachineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            'ghostbusters_machine_probe', ROOT / 'scripts/studies/ghostbusters/probe-machine.py')
        cls.probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.probe)

    def record(self, pc, cycle, checkpoint, *, kind='trace', encoded='ea', sp=0xf7,
               a=0, line=6, raster_cycle=2, operation='exec', address=None, **extra):
        return dict(pc=pc, address=pc if address is None else address, operation=operation,
                    monitorCycle=cycle, checkpoint=checkpoint, kind=kind, bytes=encoded,
                    sp=sp, a=a, x=0, y=0, flags='..-.....', rasterLine=line,
                    rasterCycle=raster_cycle, **extra)

    def completion_rows(self):
        rows = [self.record(0x900d, 10, 1, encoded='78', sp=0xfd)]
        for command, start in ((1, 20), (3, 200)):
            rows.append(self.record(0x9097, start, 9, a=command))
            for offset, (address, value) in enumerate(((0xdd0f, 0x90), (0xdd0f, 0x91),
                    (0xdd06, 0x65), (0xdd07, 0), (0xdd0d, 0x82)), 1):
                rows.append(self.record(0xf480, start + offset, 19, operation='store', address=address, value=value))
            for index, entry in enumerate(self.probe.NMI_ENTRIES):
                cycle = start + 10 + index * 4
                rows.append(self.record(entry, cycle, 10 + index))
                if entry == 0xf0e1:
                    rows.append(self.record(0xf0e4, cycle + 1, 19, operation='store', address=0xdd0f, value=0x90))
                if entry != 0xf0d9:
                    writer = {0xf083: 0xf088, 0xf0a4: 0xf0a9, 0xf0c3: 0xf0c8, 0xf0e1: 0xf0e9}[entry]
                    rows.append(self.record(writer, cycle + 2, 15, operation='store', address=0xd418,
                                            encoded='8d18d4', value=7, sidAddress=0xd418))
        rows += [self.record(0x93e2, 400, 8),
                 self.record(0x9096, 410, 3, encoded='60', sp=0xfd),
                 self.record(0x0403, 420, 2, kind='stop on', encoded='4c0304', sp=0xff)]
        for index in range(3):
            cycle = 1000 + index * 17095
            rows.append(self.record(0x93f0, cycle, 5, encoded='a900'))
            if index < 2:
                rows.append(self.record(0x90e6, cycle + 300, 6, encoded='e6e2'))
        rows.append(self.record(0x93f0, 35190, self.probe.TERMINAL_CHECKPOINT,
                                kind='stop on', encoded='a900'))
        return rows

    def test_real_jsr_selects_default_and_returns_with_original_stack(self):
        memory = [0] * 65536
        memory[0x400:0x406] = self.probe.host_program()[2:]
        memory[0x900d] = 0x60
        cpu = MPU(memory=memory, pc=0x400)
        cpu.a, cpu.x, cpu.y, cpu.sp, cpu.p = 0, 0, 0, 0xff, 0x20
        cpu.step()
        self.assertEqual((cpu.pc, cpu.a, cpu.sp), (0x900d, 0, 0xfd))
        self.assertEqual((memory[0x1ff], memory[0x1fe]), (4, 2))
        cpu.step()
        self.assertEqual((cpu.pc, cpu.sp), (0x403, 0xff))

    def test_ntsc_last_line_and_cycle_are_admitted_but_pal_geometry_is_rejected(self):
        def log(line, cycle):
            return (f'#15 (Trace store d518) {line}/${line:03x}, {cycle}/${cycle:02x}\n'
                    '.C:F088  8D 18 D5    STA $D518 - A:07 X:00 Y:00 SP:F7 ..-..... 100\n')
        row, = self.probe.parse_records(log(262, 64))
        self.assertEqual((row['address'], row['sidAddress'], row['value']), (0xd518, 0xd418, 7))
        for line, cycle in ((263, 0), (0, 65), (311, 17)):
            with self.subTest(line=line, cycle=cycle), self.assertRaisesRegex(ValueError, 'NTSC'):
                self.probe.parse_records(log(line, cycle))

    def test_sid_rmw_wrong_indexed_address_and_truncated_records_cannot_pass(self):
        prefix = '#15 (Trace store d418) 257/$101, 17/$11\n'
        for instruction in ('CE 18 D4    DEC $D418', '99 18 D4    STA $D418,Y'):
            log = prefix + f'.C:F088  {instruction} - A:07 X:00 Y:01 SP:F7 ..-..... 100\n'
            with self.subTest(instruction=instruction), self.assertRaises(ValueError):
                self.probe.parse_records(log)
        for log in (prefix, '#15 (Trace store d418) malformed\n'):
            with self.subTest(log=log), self.assertRaises(ValueError):
                self.probe.parse_records(log)

    def test_zero_page_port_store_is_decoded_and_timestamp_reversal_rejected(self):
        log = ('#17 (Trace store 0001) 257/$101, 17/$11\n'
               '.C:9016  85 01    STA $01 - A:35 X:00 Y:00 SP:FD ..-..... 100\n')
        self.assertEqual(self.probe.parse_records(log)[0]['value'], 0x35)
        with self.assertRaisesRegex(ValueError, 'backwards'):
            self.probe.parse_records(log + log.replace('100\n', '99\n'))

    def test_each_completed_body_needs_a_return_and_terminal_body_is_unexecuted(self):
        retained, summary = self.probe.summarize(self.completion_rows(), 2, {})
        self.assertEqual(summary['capture']['completedPostIdleBodies'], 2)
        self.assertEqual(summary['capture']['rasterNormalizedIntervals'], [17095, 17095])
        self.assertFalse(summary['capture']['terminalBodyExecuted'])
        self.assertFalse(any(row['kind'] == 'stop on' and row['pc'] == 0x93f0 for row in retained))
        self.assertEqual(summary['sid']['storeCount'], 8)
        for pc in (0x90e6, 0x9096, 0x403):
            rows = self.completion_rows()
            rows.pop(next(index for index, row in enumerate(rows) if row['pc'] == pc))
            with self.subTest(pc=pc), self.assertRaises(ValueError):
                self.probe.summarize(rows, 2, {})

    def test_nmi_delayed_body_is_normalized_but_one_cycle_schedule_error_fails(self):
        rows = self.completion_rows()
        middle = next(row for row in rows if row['pc'] == 0x93f0 and row['monitorCycle'] == 18095)
        middle.update(monitorCycle=18115, rasterCycle=22)
        self.probe.summarize(rows, 2, {})
        middle['monitorCycle'] += 1
        with self.assertRaisesRegex(ValueError, 'cadence'):
            self.probe.summarize(rows, 2, {})

    def test_wrong_raster_or_execution_after_terminal_cannot_pass(self):
        for change in ('raster', 'continued'):
            rows = self.completion_rows()
            if change == 'raster':
                rows = [dict(row, rasterLine=1) if row['pc'] == 0x93f0 else row for row in rows]
            else:
                rows.append(dict(rows[-3], monitorCycle=35196))
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.probe.summarize(rows, 2, {})

    def test_default_opening_speech_commands_and_music_init_are_required(self):
        for pc in (0x9097, 0x93e2):
            rows = [row for row in self.completion_rows() if row['pc'] != pc]
            with self.subTest(pc=pc), self.assertRaises(ValueError):
                self.probe.summarize(rows, 2, {})
        rows = self.completion_rows()
        next(row for row in rows if row['pc'] == 0x9097)['a'] = 2
        with self.assertRaisesRegex(ValueError, 'speech'):
            self.probe.summarize(rows, 2, {})

    def test_registered_but_missing_nmi_volume_or_timer_groups_cannot_prove_speech(self):
        for group in ('nmi', 'volume', 'timer'):
            rows = self.completion_rows()
            if group == 'nmi':
                rows = [row for row in rows if row['pc'] not in self.probe.NMI_ENTRIES]
            elif group == 'volume':
                rows = [row for row in rows if row['pc'] != 0xf0a9]
            else:
                rows = [row for row in rows if row['address'] != 0xdd06]
            with self.subTest(group=group), self.assertRaisesRegex(ValueError, 'speech|NMI|Timer'):
                self.probe.summarize(rows, 2, {})

    def contract_log(self):
        registrations = self.probe.CHECKPOINTS + [('break', 'exec', 0x93f0, None)]
        text = ''.join(f'{kind.upper()}: {index}  C:${first:04x}'
                       + (f'-${last:04x}' if last is not None else '')
                       + f'  ({"Trace" if kind == "trace" else "Stop on"} {operation})\n'
                       for index, (kind, operation, first, last) in enumerate(registrations, 1))
        for port, raster in ((0x37, 311), (0x37, 257), (0x36, 257)):
            text += f'>C:0000  2f {port:02x} \n>C:02a6  00 \nRaster cycle/line: 17/257 IRQ: {raster}\n'
        return text

    def port_rows(self):
        values = [(0x9016, 0x35), (0x9093, 0x37), (0x90de, 0x36),
                  (0x90f9, 0x37), (0x90de, 0x36), (0x90f9, 0x37), (0x90de, 0x36)]
        return [dict(operation='store', address=1, pc=pc, value=value) for pc, value in values]

    def test_missing_read_mirror_or_nmi_coverage_cannot_prove_census(self):
        log, rows = self.contract_log(), self.port_rows()
        self.probe.validate_monitor_contract(log, rows, 2)
        for number in (self.probe.SID_READ_CHECKPOINT, self.probe.SID_STORE_CHECKPOINT,
                       self.probe.NMI_VECTOR_CHECKPOINT):
            incomplete = re.sub(rf'^TRACE: {number}[^\n]*\n', '', log, flags=re.MULTILINE)
            with self.subTest(number=number), self.assertRaisesRegex(ValueError, 'coverage'):
                self.probe.validate_monitor_contract(incomplete, rows, 2)
        with self.assertRaisesRegex(ValueError, 'coverage'):
            self.probe.validate_monitor_contract(log.replace('$d7ff', '$d418'), rows, 2)

    def test_ntsc_seed_and_terminal_irq_bank_are_verified(self):
        log, rows = self.contract_log(), self.port_rows()
        for changed in (log.replace('>C:02a6  00', '>C:02a6  01', 1),
                        log.replace('IRQ: 311', 'IRQ: 55'),
                        log.replace('2f 36', '2f 37')):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.probe.validate_monitor_contract(changed, rows, 2)
        with self.assertRaisesRegex(ValueError, 'port'):
            self.probe.validate_monitor_contract(log, rows[:-1], 2)

    def test_known_kernal_cia_dispatch_port_write_is_distinguished_from_source(self):
        rows = self.port_rows()
        rows.insert(2, dict(operation='store', address=1, pc=0xea79, value=0x37))
        self.probe.validate_monitor_contract(self.contract_log(), rows, 2)
        for pc, value in ((0xea79, 0x35), (0xea7a, 0x37)):
            changed = [dict(row, pc=pc, value=value) if row['pc'] == 0xea79 else row for row in rows]
            with self.subTest(pc=pc, value=value), self.assertRaisesRegex(ValueError, 'port'):
                self.probe.validate_monitor_contract(self.contract_log(), changed, 2)

    def test_monitor_declares_ntsc_timer_and_traces_before_real_init(self):
        commands = self.probe.monitor_commands(Path('/tmp/payload.prg'), Path('/tmp/host.prg'), 128)
        self.assertIn('> $dc04 $95 $42', commands)
        self.assertIn('> $d011 $9b $37', commands)
        self.assertLess(commands.index('trace store $d400 $d7ff'), commands.index('\ng\n'))
        self.assertIn(f'ignore {self.probe.TERMINAL_CHECKPOINT} $0080', commands)

    def test_wrong_source_is_rejected_before_machine_launch(self):
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            self.probe.admit_source(b'not the original')


if __name__ == '__main__':
    unittest.main()
