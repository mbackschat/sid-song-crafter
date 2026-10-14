import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def store(address, value, *, pc=0x4876, x=0, irq=388):
    return dict(operation='store', address=address, value=value, pc=pc, x=x,
                irqIndex=irq, monitorCycle=irq * 19656, phase='play')


class GianaAnalysisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            'giana_analysis', ROOT / 'scripts/studies/giana/analyze-contrast.py')
        cls.analysis = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.analysis)

    def test_gate_off_motion_does_not_count_a_retriggering_onset(self):
        rows = [store(0xd403, 8), store(0xd402, 64), store(0xd404, 64),
                store(0xd402, 80), store(0xd404, 65)]
        self.assertEqual(self.analysis.pulse_motion(rows), [])
        rows[-1]['value'] = 64
        motion = self.analysis.pulse_motion(rows)
        self.assertEqual([(r['voice'], r['before'], r['after']) for r in motion],
                         [(1, 0x840, 0x850)])

    def test_shared_filter_requires_matching_ram_state_and_sid_output(self):
        rows = [store(0x4241, 32, pc=0x454c),
                store(0x4241, 33, pc=0x47ea, x=1), store(0xd416, 33, pc=0x47ed, x=1),
                store(0x4241, 34, pc=0x47ea), store(0xd416, 34, pc=0x47ed)]
        updates = self.analysis.filter_motion(rows)
        self.assertEqual([(r['voice'], r['before'], r['after']) for r in updates],
                         [(2, 32, 33), (1, 33, 34)])
        rows[-1]['value'] = 99
        with self.assertRaisesRegex(ValueError, 'filter|state'):
            self.analysis.filter_motion(rows)

    def test_executed_macro_step_must_match_its_pinned_source_byte(self):
        data = bytearray(126 + 0xccfa - 0x71e3)
        data[126 + 0x8c29 - 0x71e3] = 16
        rows = [store(0x4263, 0xfd, pc=0x44ad), store(0x4266, 0x5b, pc=0x44b2),
                store(0x4219, 16, pc=0x44fe)]
        mapping = self.analysis.parameter_map(rows, bytes(data))
        self.assertEqual((mapping[0]['macroAddress'], mapping[0]['sourceAddress'], mapping[0]['step']),
                         (0x5bfd, 0x8c29, 16))
        rows[-1]['value'] = 15
        with self.assertRaisesRegex(ValueError, 'source|step'):
            self.analysis.parameter_map(rows, bytes(data))

    def test_voice_three_pwm_is_protected_by_the_diagnostic_projection(self):
        original = [store(0xd402, 16), store(0xd410, 32)]
        changed = [store(0xd402, 0), store(0xd410, 99)]
        with self.assertRaisesRegex(ValueError, 'protected|non-target'):
            self.analysis.compare_stores(original, changed)

    def test_saved_trace_must_match_the_monitor_rederived_rows(self):
        oracle = dict(header={}, capture={}, sid={}, volume={}, initialization={}, monitorContract={})
        with patch.object(self.analysis.probe, 'parse_records', return_value=['raw']), \
                patch.object(self.analysis.probe, 'validate_monitor_contract', return_value={}), \
                patch.object(self.analysis.probe, 'summarize', return_value=(['verified'], oracle)):
            oracle['capture'] = {'requestedPostIdleRefreshes': 2}
            with self.assertRaisesRegex(ValueError, 'trace|rows'):
                self.analysis.validate_baseline('monitor', ['modified'], oracle)

    def test_saved_receipt_must_match_the_monitor_rederived_summary(self):
        oracle = dict(header={}, capture={'requestedPostIdleRefreshes': 2},
                      sid={'storeCount': 10}, volume={}, initialization={}, monitorContract={})
        receipt = {**oracle, 'sid': {'storeCount': 9}}
        with patch.object(self.analysis.probe, 'parse_records', return_value=['raw']), \
                patch.object(self.analysis.probe, 'validate_monitor_contract', return_value={}), \
                patch.object(self.analysis.probe, 'summarize', return_value=(['verified'], oracle)):
            with self.assertRaisesRegex(ValueError, 'receipt|sid'):
                self.analysis.validate_baseline('monitor', ['verified'], receipt)


if __name__ == '__main__':
    unittest.main()
