"""Guard the speech handoff proof against reordered or incomplete evidence."""

from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('ghostbusters_handoff', ROOT / 'scripts/studies/ghostbusters/probe-speech-handoff.py')
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def observed(pc, address, operation, cycle, sp, count, pointer, *, value=None, nmi=321):
    return dict(pc=pc, address=address, operation=operation, monitorCycle=cycle, sp=sp,
        value=value, command=1, nmiIndex=nmi,
        state=dict(forwardCount=count, reverseCount=16, gapCount=0,
            forwardPointer=pointer, reversePointer=15, currentBase=96, length=16))


def example():
    rows = [observed(0xf0f5, 0xfffa, 'store', 100, 246, 0, 15, value=0x83, nmi=320),
        observed(0xf0fb, 0xf0fb, 'exec', 104, 246, 0, 15, nmi=320),
        observed(0xf0fb, 0xf085, 'store', 108, 246, 0, 96, value=96, nmi=320),
        observed(0xf083, 0xf083, 'exec', 119, 243, 0, 96),
        observed(0xf08e, 0xfd, 'store', 141, 242, 255, 96),
        observed(0xf092, 0xf085, 'store', 149, 242, 255, 97),
        observed(0xf101, 0xf101, 'exec', 162, 246, 255, 97),
        observed(0xf101, 0xfd, 'store', 165, 246, 16, 97, value=16),
        observed(0xf09f, 0xf0a6, 'store', 1800, 246, 0, 112, value=112, nmi=337)]
    rows[-1]['state']['reversePointer'] = 112
    return rows


class GhostbustersHandoffTest(unittest.TestCase):
    def test_extension_preserves_base_checkpoint_numbers_and_restores_contract(self):
        original = probe.machine.CHECKPOINTS
        terminal = probe.machine.TERMINAL_CHECKPOINT
        command = probe.machine.monitor_commands
        with probe.extended_monitor() as selected:
            self.assertEqual(original, probe.machine.CHECKPOINTS[:len(original)])
            self.assertEqual(terminal + len(probe.EXTRA_CHECKPOINTS), probe.machine.TERMINAL_CHECKPOINT)
            self.assertIn(probe.machine.NMI_VECTOR_CHECKPOINT, selected)
            lines = probe.machine.monitor_commands(Path('/tmp/payload'), Path('/tmp/host'), 2).splitlines()
            for number in selected:
                self.assertIn(f'command {number} "{probe.RAM_COMMAND}"', lines)
            self.assertEqual(('trace', 'store', 0xd400, 0xd7ff), probe.machine.CHECKPOINTS[14])
        self.assertIs(original, probe.machine.CHECKPOINTS)
        self.assertEqual(terminal, probe.machine.TERMINAL_CHECKPOINT)
        self.assertIs(command, probe.machine.monitor_commands)

    def test_snapshot_parser_requires_every_ram_byte_and_rejects_repeated_values(self):
        row = dict(checkpoint=10, operation='exec', pc=0xf083, address=0xf083, monitorCycle=100)
        log = '\n'.join(['#10 (Trace exec f083) 0/$00, 0/$00', 'instruction placeholder',
            '>C:00fd  00 10 00  ...', '>C:f085  60  .', '>C:f0a6  0f  .', '>C:f4db  60 10  ..'])
        parsed = probe.parse_snapshots(log, [row], {10})
        self.assertEqual(0, parsed[0]['state']['forwardCount'])
        self.assertEqual(96, parsed[0]['state']['forwardPointer'])
        self.assertEqual(16, parsed[0]['state']['length'])
        with self.assertRaisesRegex(ValueError, 'Missing'):
            probe.parse_snapshots(log.rsplit('\n', 1)[0], [row], {10})
        with self.assertRaisesRegex(ValueError, 'Repeated'):
            probe.parse_snapshots(log + '\n>C:00fd  00 10 00', [row], {10})

    def test_proof_requires_observed_zero_to_ff_then_outer_reset_and_advanced_pointer(self):
        result = probe.find_lost_decrements(example())
        self.assertEqual(1, len(result))
        self.assertEqual(321, result[0]['nestedNmiIndex'])
        self.assertEqual([0, 255, 16], result[0]['forwardCounterValues'])
        self.assertEqual([96, 97, 112], result[0]['forwardPointerValues'])
        self.assertEqual(112, result[0]['reverseStartPointer'])

    def test_reset_before_nmi_is_not_accepted_as_a_lost_decrement(self):
        rows = example()
        resets = rows[6:8]
        del rows[6:8]
        for index, reset in enumerate(resets):
            reset['monitorCycle'] = 108 + index
        rows[3:3] = resets
        self.assertEqual([], probe.find_lost_decrements(rows))

    def test_access_record_deferred_past_next_nmi_does_not_prove_pre_reset_interruption(self):
        rows = example()
        reset_exec = rows.pop(6)
        reset_exec['monitorCycle'] = 110
        rows.insert(3, reset_exec)
        rows[7]['sp'] = 243
        self.assertEqual([], probe.find_lost_decrements(rows))

    def test_pointer_access_reported_after_nmi_still_requires_prior_setup_execution(self):
        rows = example()
        pointer_store = rows.pop(2)
        pointer_store['monitorCycle'] = rows[2]['monitorCycle']
        pointer_store['sp'] = rows[2]['sp']
        rows.insert(3, pointer_store)
        self.assertEqual(1, len(probe.find_lost_decrements(rows)))

    def test_missing_or_contradictory_counter_and_pointer_observations_reject(self):
        for index, field, value in ((4, 'forwardCount', 254), (7, 'forwardCount', 15),
            (7, 'forwardPointer', 96), (8, 'reversePointer', 111)):
            rows = deepcopy(example())
            rows[index]['state'][field] = value
            with self.subTest(index=index, field=field), self.assertRaises(ValueError):
                probe.find_lost_decrements(rows)

    def test_retained_capture_requires_every_original_private_artifact_hash(self):
        names = ('payload.prg', 'host.prg', 'trace.json.gz', 'monitor.log.gz', 'process.log.gz')
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            (output / 'capture').mkdir()
            for name in names:
                (output / 'capture' / name).write_bytes(b'private test fixture')
            captured = dict(privateArtifacts={name: probe.fingerprint(output / 'capture' / name) for name in names})
            probe.check_private_files(output, captured)
            with self.assertRaisesRegex(ValueError, 'set differs'):
                probe.check_private_files(output, dict(privateArtifacts={}))
            (output / 'capture/payload.prg').write_bytes(b'changed private test fixture')
            with self.assertRaisesRegex(ValueError, 'fingerprint differs'):
                probe.check_private_files(output, captured)

    def test_identical_observations_have_identical_gzip_bytes_without_time_or_filename(self):
        with tempfile.TemporaryDirectory() as folder:
            first, second = Path(folder) / 'first.json.gz', Path(folder) / 'second.json.gz'
            probe.write_observations(first, example())
            before = first.read_bytes()
            probe.write_observations(first, example())
            probe.write_observations(second, example())
            self.assertEqual(before, first.read_bytes())
            self.assertEqual(before, second.read_bytes())
            self.assertEqual(b'\x00\x00\x00\x00', before[4:8])
            self.assertEqual(0, before[3])


if __name__ == '__main__':
    unittest.main()
