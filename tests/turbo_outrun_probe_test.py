import importlib.util
from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools/test-deps'))
from py65.devices.mpu6502 import MPU


class TurboOutrunProbeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            'turbo_outrun_probe', ROOT / 'scripts/studies/turbo-outrun/probe-contrast.py')
        cls.probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.probe)

    def test_intro_init_receives_zero_and_real_return_stack(self):
        memory = [0] * 65536
        memory[0x400:0x406] = self.probe.host_program()[2:]
        memory[0xcb40] = 0x60
        cpu = MPU(memory=memory, pc=0x400)
        cpu.a, cpu.sp, cpu.p = 0, 0xff, 0x20
        cpu.step()
        self.assertEqual((cpu.pc, cpu.a, cpu.sp), (0xcb40, 0, 0xfd))
        self.assertEqual((memory[0x1ff], memory[0x1fe]), (4, 2))
        cpu.step()
        self.assertEqual((cpu.pc, cpu.sp), (0x403, 0xff))

    def test_mirrored_indexed_store_retains_physical_address(self):
        log = ('#7 (Trace store d52b) 52/$034, 17/$11\n'
               '.C:0E46  99 24 D5    STA $D524,Y - A:41 X:01 Y:07 SP:F7 ..-..... 100\n')
        row, = self.probe.parse_records(log)
        self.assertEqual((row['address'], row['sidAddress'], row['value']), (0xd52b, 0xd40b, 0x41))

    def test_truncated_or_unrecognized_record_is_rejected(self):
        for log in ('#7 (Trace store d418) bad\n', '#7 (Trace store d418) 52/$034, 17/$11\n'):
            with self.subTest(log=log), self.assertRaises(ValueError):
                self.probe.parse_records(log)

    def test_sid_rmw_and_effective_address_mismatch_are_rejected(self):
        for encoded, assembly in (('CE 18 D4', 'DEC $D418'), ('8D 17 D4', 'STA $D417')):
            log = ('#7 (Trace store d418) 52/$034, 17/$11\n'
                   f'.C:0967  {encoded}    {assembly} - A:38 X:00 Y:00 SP:F7 ..-..... 100\n')
            with self.subTest(encoded=encoded), self.assertRaises(ValueError):
                self.probe.parse_records(log)

    def completion_rows(self):
        def row(pc, cycle, checkpoint, kind='trace', sp=0xf7, encoded='48', a=0):
            return dict(pc=pc, address=pc, operation='exec', monitorCycle=cycle,
                        checkpoint=checkpoint, kind=kind, sp=sp, bytes=encoded,
                        a=a, x=0, y=0, flags='..-.....', rasterLine=52, rasterCycle=17)
        return [row(0xcb40, 10, 1, sp=0xfd, encoded='78'),
                row(0xcd00, 20, 3, sp=0xfd, encoded='78'),
                row(0x810, 30, 13, sp=0xfb, encoded='4c040a'),
                row(0x819, 40, 14, sp=0xfb, encoded='4c6b08'),
                row(0xcd2f, 50, 4, sp=0xfd, encoded='60'),
                row(0x403, 60, 2, 'stop on', 0xff, '4c0304'),
                row(0xcd30, 1000, 5), row(0xcd30, 20656, 5), row(0xcd30, 40312, 5),
                row(0xcd30, 40312, 22, 'stop on')]

    def test_completed_capture_excludes_unexecuted_terminal_irq(self):
        retained, summary = self.probe.summarize(self.completion_rows(), 2, {})
        self.assertEqual(summary['capture']['completedPostIdleRefreshes'], 2)
        self.assertFalse(summary['capture']['terminalIrqExecuted'])
        self.assertEqual([r['irqIndex'] for r in retained if r['pc'] == 0xcd30], [0, 1])

    def test_missing_stop_or_wrong_raster_or_short_capture_cannot_pass(self):
        for mutate in (lambda rows: rows[:-1], lambda rows: rows[:7] + rows[8:],
                       lambda rows: [dict(r, rasterLine=256) if r['pc'] == 0xcd30 else r for r in rows]):
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                self.probe.summarize(mutate(self.completion_rows()), 2, {})

    def test_skip_window_counts_unlogged_irqs_and_requires_both_boundaries(self):
        rows = self.completion_rows()[:6]
        entry = self.completion_rows()[6]
        for index in range(5):
            current = dict(entry, monitorCycle=1000 + index * 19656)
            rows.append(current)
            if index in (2, 4):
                rows.append(dict(current, checkpoint=32, kind='stop on'))
        retained, summary = self.probe.summarize(rows, 2, {}, 2)
        self.assertEqual(summary['capture']['completedIrqRefreshes'], 4)
        self.assertEqual(summary['capture']['completedSkippedRefreshes'], 2)
        self.assertEqual([r['irqIndex'] for r in retained if r['operation'] == 'exec' and r['pc'] == 0xcd30 and r['kind'] == 'trace'], [2, 3])
        with self.assertRaisesRegex(ValueError, 'stop|boundary'):
            self.probe.summarize([r for r in rows if r != rows[9]], 2, {}, 2)

    def test_nmi_delayed_entry_requires_exact_raster_normalized_frame(self):
        rows = self.completion_rows()
        rows[7].update(rasterCycle=37, monitorCycle=20676)
        self.probe.summarize(rows, 2, {})
        rows[7]['monitorCycle'] += 1
        with self.assertRaisesRegex(ValueError, 'cadence'):
            self.probe.summarize(rows, 2, {})

    def test_narrowed_sid_read_or_store_coverage_cannot_prove_census(self):
        log = self.registration_fixture() + '>C:0000  2f 37 \n>C:0000  2f 35 \n>C:0000  2f 35 \n'
        rows = [dict(operation='store', address=1, pc=0xcb47, value=0x35),
                dict(operation='store', address=1, pc=0xcd03, value=0x35)]
        rows += [dict(operation='store', address=address, value=value) for address, value
                 in ((0xffff, 0xcd), (0xfffe, 0x30), (0xfffa, 0x43), (0xfffb, 9))]
        self.probe.validate_monitor_contract(log, rows)
        for checkpoint in (7, 8):
            incomplete = re.sub(rf'^TRACE: {checkpoint}[^\n]*\n', '', log, flags=re.MULTILINE)
            with self.subTest(checkpoint=checkpoint), self.assertRaises(ValueError):
                self.probe.validate_monitor_contract(incomplete, rows)

    def test_bank_mutation_is_verified_instead_of_inheriting_giana_contract(self):
        log = self.registration_fixture() + '>C:0000  2f 37 \n>C:0000  2f 35 \n>C:0000  2f 35 \n'
        with self.assertRaisesRegex(ValueError, 'port|bank'):
            self.probe.validate_monitor_contract(log, [dict(operation='store', address=1, pc=0xcb47, value=0x34)])

    def test_registered_but_disabled_window_read_checkpoint_cannot_prove_zero_reads(self):
        initial = self.registration_fixture().replace('BREAK: 22  C:$cd30  (Stop on exec)\n', '') + '''TRACE: 22  C:$00e5-$00f6  (Trace store)
TRACE: 23  C:$0834-$0836  (Trace store)
TRACE: 24  C:$082b-$082d  (Trace store)
TRACE: 25  C:$0e08  (Trace exec)
TRACE: 26  C:$0e0d  (Trace exec)
TRACE: 27  C:$0e18  (Trace exec)
TRACE: 28  C:$0e36  (Trace exec)
TRACE: 29  C:$0e39  (Trace exec)
TRACE: 30  C:$0c6e  (Trace exec)
TRACE: 31  C:$0cf0  (Trace exec)
BREAK: 32  C:$cd30  (Stop on exec)
'''
        lines = [line for line in initial.splitlines() if not line.startswith('BREAK: 2 ')]
        quiet_disabled = {6, 7, 8, 11, 12, *range(15, 32)}
        window_disabled = {6, *range(15, 22)}
        def table(disabled):
            return ''.join(line + (' disabled' if int(line.split()[1]) in disabled else '') + '\n' for line in lines)
        snapshots = '>C:0000  2f 37 \n' + '>C:0000  2f 35 \n' * 3
        rows = [dict(operation='store', address=1, pc=0xcb47, value=0x35), dict(operation='store', address=1, pc=0xcd03, value=0x35)]
        rows += [dict(operation='store', address=address, value=value) for address, value
                 in ((0xffff, 0xcd), (0xfffe, 0x30), (0xfffa, 0x43), (0xfffb, 9))]
        log = initial + table(quiet_disabled) + table(window_disabled) + snapshots
        self.probe.validate_monitor_contract(log, rows, 1120)
        wrong_window = initial + table(quiet_disabled) + table(window_disabled | {8}) + snapshots
        with self.assertRaisesRegex(ValueError, 'coverage state'):
            self.probe.validate_monitor_contract(wrong_window, rows, 1120)

    def test_terminal_pending_low_nibble_is_explicit_and_partial_nmi_is_rejected(self):
        rows, payload = self.sample_rows(), self.sample_payload()
        proof = self.probe.verify_sample_path(rows + rows[:8], payload)
        self.assertEqual(proof['counts']['terminalPendingLowNibbles'], 1)
        with self.assertRaisesRegex(ValueError, 'unfinished|incomplete'):
            self.probe.verify_sample_path(rows + rows[:6], payload)

    def registration_fixture(self):
        return '''TRACE: 1  C:$cb40  (Trace exec)
BREAK: 2  C:$0403  (Stop on exec)
TRACE: 3  C:$cd00  (Trace exec)
TRACE: 4  C:$cd2f  (Trace exec)
TRACE: 5  C:$cd30  (Trace exec)
TRACE: 6  C:$0943  (Trace exec)
TRACE: 7  C:$d400-$d7ff  (Trace store)
TRACE: 8  C:$d400-$d7ff  (Trace load)
TRACE: 9  C:$0000-$0001  (Trace store)
TRACE: 10  C:$fffa-$ffff  (Trace store)
TRACE: 11  C:$dc00-$ddff  (Trace store)
TRACE: 12  C:$d011-$d01a  (Trace store)
TRACE: 13  C:$0810  (Trace exec)
TRACE: 14  C:$0819  (Trace exec)
TRACE: 15  C:$0949  (Trace exec)
TRACE: 16  C:$094c  (Trace exec)
TRACE: 17  C:$0963  (Trace exec)
TRACE: 18  C:$0974  (Trace exec)
TRACE: 19  C:$0936  (Trace exec)
TRACE: 20  C:$0904  (Trace exec)
TRACE: 21  C:$0909  (Trace exec)
BREAK: 22  C:$cd30  (Stop on exec)
'''

    def sample_rows(self):
        def row(pc, operation='exec', **values):
            return dict(pc=pc, operation=operation, monitorCycle=100 + pc,
                        irqIndex=0, bytes='ea', a=0, y=0, **values)
        return [dict(row(0x904), bytes='a000'), dict(row(0x909), a=0),
                dict(row(0x936), bytes='a900'), row(0x943),
                dict(row(0x949), bytes='ad0020'), dict(row(0x94c), bytes='c91f', a=0x23),
                dict(row(0x963), a=2), dict(row(0x967, 'store'), address=0xd418, bytes='8d18d4', value=0x32),
                row(0x943), dict(row(0x974), a=3), dict(row(0x978, 'store'), address=0xd418, bytes='8d18d4', value=0x33)]

    def sample_payload(self):
        payload = bytearray(0x6200 - 0x810)
        payload[0x9a4 - 0x810] = 0x2a
        payload[0x2000 - 0x810] = 0x23
        return payload

    def test_packed_nibble_oracle_rejects_missing_reordered_and_duplicate_phases(self):
        rows, payload = self.sample_rows(), self.sample_payload()
        self.probe.verify_sample_path(rows, payload)
        for changed in (rows[:6] + rows[7:], rows[:7] + rows[8:], rows[:7] + [rows[7], rows[7]] + rows[8:],
                        rows[:9] + [rows[10], rows[9]]):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.probe.verify_sample_path(changed, payload)

    def test_wrong_payload_or_volume_value_cannot_pass_packed_nibble_proof(self):
        rows, payload = self.sample_rows(), self.sample_payload()
        for changed in (rows[:5] + [dict(rows[5], a=0x24)] + rows[6:],
                        rows[:7] + [dict(rows[7], value=0x33)] + rows[8:]):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.probe.verify_sample_path(changed, payload)

    def test_sample_endpoint_and_terminator_opcode_are_part_of_the_proof(self):
        rows, payload = self.sample_rows(), self.sample_payload()
        for changed in (rows[:5] + [dict(rows[5], bytes='c920')] + rows[6:],
                        rows[:7] + [dict(rows[7], address=0xd417, bytes='8d17d4')] + rows[8:]):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.probe.verify_sample_path(changed, payload)

    def test_explicit_restart_can_cancel_pending_low_but_unmarked_fetch_cannot(self):
        rows, payload = self.sample_rows(), self.sample_payload()
        prefix = rows[:8]
        cancelled = prefix + rows[:3] + rows[3:]
        proof = self.probe.verify_sample_path(cancelled, payload)
        self.assertEqual(proof['counts']['restartCancelledLowNibbles'], 1)
        with self.assertRaisesRegex(ValueError, 'completed|restart'):
            self.probe.verify_sample_path(prefix + rows[3:], payload)

    def test_each_sample_path_needs_its_own_executed_nmi_entry(self):
        rows, payload = self.sample_rows(), self.sample_payload()
        with self.assertRaisesRegex(ValueError, 'NMI'):
            self.probe.verify_sample_path(rows[:8] + rows[9:], payload)
        with self.assertRaisesRegex(ValueError, 'NMI'):
            self.probe.verify_sample_path(rows[:4] + [rows[3]] + rows[4:], payload)


if __name__ == '__main__':
    unittest.main()
