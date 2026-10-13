from array import array
import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
import wave


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('shades_pwm', ROOT / 'scripts/studies/shades/compare-shades-pwm.py')
pwm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pwm)


def records():
    report = dict(playCalls=3, initCycles=36, playCycles=[100, 100, 100],
                  portWrites=[], executedPcs=[0x7302, 0x7852], ioReads=[])
    rows = [dict(phase='play', tick=0, writerPc=0x7852, instructionStartCycle=10, address=0xdc05, value=0x30),
            dict(phase='play', tick=1, writerPc=0x7302, instructionStartCycle=20, address=0xd402, value=0x10),
            dict(phase='play', tick=1, writerPc=0x7310, instructionStartCycle=30, address=0xd404, value=0x41)]
    changed = copy.deepcopy(rows)
    changed[1]['value'] = 0
    return report, rows, changed


class ShadesPwmTest(unittest.TestCase):
    def test_comparison_preserves_ordered_context_and_confines_changed_values_to_pulse(self):
        report, original, changed = records()
        result = pwm.verify_comparison(report, original, report, changed)
        self.assertEqual(1, result['changedWrites'])
        self.assertEqual([0xd402], result['changedAddresses'])
        self.assertEqual(1, result['firstChangedCall'])
        for mutation in ('other_value', 'writer', 'time', 'call', 'order', 'missing'):
            invalid = copy.deepcopy(changed)
            if mutation == 'other_value':
                invalid[-1]['value'] = 0x40
            elif mutation == 'writer':
                invalid[1]['writerPc'] += 1
            elif mutation == 'time':
                invalid[1]['instructionStartCycle'] += 1
            elif mutation == 'call':
                invalid[1]['tick'] += 1
            elif mutation == 'order':
                invalid.reverse()
            else:
                invalid.pop()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                pwm.verify_comparison(report, original, report, invalid)
        altered_report = copy.deepcopy(report)
        altered_report['playCycles'][1] += 1
        with self.assertRaisesRegex(ValueError, 'execution'):
            pwm.verify_comparison(report, original, altered_report, changed)
        with self.assertRaisesRegex(ValueError, 'pulse register'):
            pwm.verify_comparison(report, original, report, original)

    def test_unpinned_source_cannot_be_mutated(self):
        with self.assertRaisesRegex(ValueError, 'pinned corrected Shades'):
            pwm.patch_source(bytes(12000))

    def test_corrected_source_patch_and_bounded_isolation_match_retained_experiment(self):
        source = ROOT / '.local/research/shades/Shades_filter_corrected.sid'
        if not source.is_file():
            self.skipTest('Pinned ignored reference is required')
        data = source.read_bytes()
        patched, receipt, before, after = pwm.compare_source(data)
        self.assertEqual([2157], [index for index, pair in enumerate(zip(data, patched)) if pair[0] != pair[1]])
        self.assertEqual((16, 0), (data[2157], patched[2157]))
        self.assertEqual('5033822bd7d4020b49e243d55b591652c9eefb1bd47097bf5f31edbd38790c64', hashlib.sha256(patched).hexdigest())
        self.assertEqual(1280, receipt['verification']['playCalls'])
        self.assertEqual(1906, receipt['verification']['changedWrites'])
        self.assertEqual([0xd402, 0xd403], receipt['verification']['changedAddresses'])
        self.assertEqual(386, receipt['verification']['firstChangedCall'])
        self.assertEqual(len(before), len(after))
        altered = bytearray(data)
        altered[2156] ^= 1
        with self.assertRaisesRegex(ValueError, 'pinned corrected Shades'):
            pwm.patch_source(altered)

    def test_fresh_output_guard_preserves_existing_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'existing'
            output.mkdir()
            marker = output / 'evidence.json'
            marker.write_text('preserve')
            with self.assertRaisesRegex(ValueError, 'fresh'):
                pwm.run_comparison(Path(temporary) / 'absent.sid', output)
            self.assertEqual('preserve', marker.read_text())

    def test_unity_window_keeps_level_difference_and_exact_half_second_gap(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = [Path(temporary) / name for name in ('a.wav', 'b.wav', 'pair.wav')]
            for path, level in zip(paths, (100, 200)):
                values = array('h', [level, -level] * 75)
                if sys.byteorder != 'little':
                    values.byteswap()
                with wave.open(str(path), 'wb') as wav:
                    wav.setparams((1, 2, 10, 0, 'NONE', 'not compressed'))
                    wav.writeframes(values.tobytes())
            report = pwm.prepare_listening(paths[0], paths[1], paths[2])
            with wave.open(str(paths[2]), 'rb') as wav:
                self.assertEqual(145, wav.getnframes())
                values = array('h', wav.readframes(145))
                if sys.byteorder != 'little':
                    values.byteswap()
            self.assertEqual([100, -100] * 35 + [0] * 5 + [200, -200] * 35, list(values))
            self.assertEqual([100, 200], [row['window']['acRms'] for row in report['inputs']])
            self.assertEqual((1, False, [5, 12]), (report['gain'], report['normalization'], report['windowSeconds']))
            with self.assertRaisesRegex(ValueError, 'exists'):
                pwm.prepare_listening(paths[0], paths[1], paths[2])

    def test_prefix_check_distinguishes_matching_duration_from_identical_samples(self):
        with tempfile.TemporaryDirectory() as temporary:
            reference, current = (Path(temporary) / name for name in ('reference.wav', 'current.wav'))

            def write(path, values):
                values = array('h', values)
                if sys.byteorder != 'little':
                    values.byteswap()
                with wave.open(str(path), 'wb') as wav:
                    wav.setparams((1, 2, 10, 0, 'NONE', 'not compressed'))
                    wav.writeframes(values.tobytes())

            write(reference, [100, -100] * 100)
            write(current, [100, -100] * 80)
            result = pwm.verify_baseline_prefix(reference, current)
            self.assertEqual(160, result['frames'])
            self.assertTrue(result['identicalPcmPrefix'])
            altered = [100, -100] * 80
            altered[90] = 101
            write(current, altered)
            with self.assertRaisesRegex(ValueError, 'prefix differs'):
                pwm.verify_baseline_prefix(reference, current)


if __name__ == '__main__':
    unittest.main()
