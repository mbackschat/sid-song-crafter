import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'daglish_contrast_probe', ROOT / 'scripts/studies/deflektor/probe-contrast.py')
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


def store(address, value, tick=0, phase='play', cycle=0):
    return dict(address=address, value=value, tick=tick, phase=phase,
                instructionStartCycle=cycle)


class ContrastProbeTests(unittest.TestCase):
    def test_unknown_initial_control_is_not_a_gate_rise(self):
        result = PROBE.census([store(0xd404, 0x41)])
        self.assertEqual(result['voices'][0]['gateRises'], [])
        self.assertEqual(result['voices'][0]['firstControl']['value'], 0x41)

    def test_init_state_and_multiple_same_call_gate_edges_are_retained(self):
        result = PROBE.census([
            store(0xd404, 0, tick=None, phase='init'),
            store(0xd404, 0x41, cycle=10),
            store(0xd404, 0x40, cycle=20),
            store(0xd404, 0x41, cycle=30),
        ])
        self.assertEqual([row['instructionStartCycle'] for row in result['voices'][0]['gateRises']], [10, 30])

    def test_filter_activation_requires_known_routing_and_mode(self):
        result = PROBE.census([
            store(0xd417, 0x82, tick=None, phase='init'),
            store(0xd418, 0x1f, tick=2, cycle=10),
            store(0xd417, 0, tick=2, cycle=20),
        ])
        active = result['activeFilterIntervals']
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]['start']['tick'], 2)
        self.assertEqual(active[0]['end']['instructionStartCycle'], 20)
        self.assertEqual(active[0]['routing'], 2)
        self.assertEqual(active[0]['modes'], 0x10)

    def test_trace_verification_rejects_lost_same_call_store_order(self):
        writes = [store(0xd40b, 0, cycle=10), store(0xd40b, 65, cycle=20)]
        trace = dict(sourceSha256='source', firstCall=0, lastCallInclusive=0,
                     sidWrites=list(reversed(writes)))
        with self.assertRaisesRegex(ValueError, 'differ'):
            PROBE.verify_trace(trace, 'source', writes)
        trace['sidWrites'] = writes
        self.assertEqual(PROBE.verify_trace(trace, 'source', writes)['matchingStores'], 2)


if __name__ == '__main__':
    unittest.main()
