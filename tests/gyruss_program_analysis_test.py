import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
SPEC = importlib.util.spec_from_file_location('gyruss_analysis', ROOT / 'scripts/studies/bach/analyze-gyruss-program.py')
gyruss = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gyruss)


class GyrussProgramAnalysisTest(unittest.TestCase):
    def test_changed_source_is_rejected_before_execution(self):
        with self.assertRaisesRegex(ValueError, 'pinned Gyruss'):
            gyruss.run_driver(b'PSID' + bytes(200), 1)

    def test_renderer_comparison_accepts_an_ordered_mid_call_state(self):
        first = bytes(25)
        middle = bytes([1]) + bytes(24)
        final = bytes([1, 2]) + bytes(23)
        run = {'states': [first.hex(), final.hex()], 'prefixes': [{first.hex()}, {middle.hex(), final.hex()}]}
        rows = [{'time_ms': '35', 'registers_hex': middle.hex() + bytes(7).hex()}]
        result = gyruss.compare_snapshots(run, rows)
        self.assertEqual((result['callEndMatches'], result['orderedPrefixMatches'], result['unmatched']), (0, 1, []))

    def test_renderer_comparison_reports_an_unobserved_state(self):
        first = bytes(25)
        run = {'states': [first.hex()], 'prefixes': [{first.hex()}]}
        rows = [{'time_ms': '17', 'registers_hex': bytes([1]).hex() + bytes(31).hex()}]
        self.assertEqual(len(gyruss.compare_snapshots(run, rows)['unmatched']), 1)

    def test_renderer_comparison_rejects_empty_truncated_or_unordered_capture(self):
        state = bytes(25)
        run = {'states': [state.hex()], 'prefixes': [{state.hex()}]}
        row = {'time_ms': '17', 'registers_hex': state.hex() + bytes(7).hex()}
        for rows in ([], [{'time_ms': '17', 'registers_hex': '00'}], [row, row]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                gyruss.compare_snapshots(run, rows)

    @unittest.skipUnless((ROOT / '.local/research/gyruss/Gyruss.sid').is_file(), 'Pinned local reference is absent')
    def test_pinned_opening_runs_with_unchanged_ntsc_header_and_subdivision(self):
        source = (ROOT / '.local/research/gyruss/Gyruss.sid').read_bytes()
        run = gyruss.run_driver(source, 22)
        self.assertEqual(source[118:120], bytes.fromhex('0018'))
        self.assertEqual(run['report']['frameCycleBudget'], 263 * 65)
        self.assertEqual(run['report']['clockDeclaration'], 'NTSC')
        melody = [event for event in run['noteEvents'] if event['voice'] == 1]
        self.assertEqual([(event['call'], event['frequencyWord'], event['durationQuanta']) for event in melody[:3]], [(0, 7217, 2), (10, 6430, 2), (20, 7217, 16)])
        self.assertEqual([bytes.fromhex(state)[14:16].hex() for state in run['states'][1:6]], ['2061', '4042', '6023', '8004', 'a0e5'])

    @unittest.skipUnless((ROOT / '.local/research/gyruss/Gyruss.sid').is_file(), 'Pinned local reference is absent')
    def test_gameplay_bass_retriggers_inside_a_score_note(self):
        run = gyruss.run_driver((ROOT / '.local/research/gyruss/Gyruss.sid').read_bytes(), 747)
        self.assertEqual(run['initializations'][-1], {'phase': 'play', 'call': 735, 'subtune': 4})
        events = [row for row in run['articulations'] if row['voice'] == 2 and row['subtune'] == 4]
        self.assertEqual([(row['call'], row['frequencyWord'], row['scoreEvent']) for row in events[:3]], [(736, 2408, True), (741, 2408, False), (746, 1804, True)])


if __name__ == '__main__':
    unittest.main()
