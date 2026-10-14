from array import array
import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
SPEC = importlib.util.spec_from_file_location(
    'trap_filter_diagnostic', ROOT / 'scripts/studies/deflektor/trap-filter-diagnostic.py')
DIAGNOSTIC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DIAGNOSTIC)


def store(address, value, tick=601, cycle=2068):
    return dict(phase='play', tick=tick, instructionStartCycle=cycle,
                address=address, value=value)


class TrapFilterDiagnosticTests(unittest.TestCase):
    def test_patch_changes_one_verified_data_byte_and_preserves_original(self):
        header = dict(dataOffset=124, headerLoadAddress=0, loadAddress=0xbf00)
        data = bytearray(4478)
        offset = 126 + 0xc936 - 0xbf00
        data[offset] = 0x82
        original = bytes(data)
        patched, change = DIAGNOSTIC.patch_source(original, header)
        self.assertEqual(original[offset], 0x82)
        self.assertEqual(patched[offset], 0x80)
        self.assertEqual([index for index, pair in enumerate(zip(original, patched)) if pair[0] != pair[1]], [offset])
        self.assertEqual(change['address'], 0xc936)
        with self.assertRaisesRegex(ValueError, 'source byte'):
            DIAGNOSTIC.patch_source(patched, header)

    def test_store_guard_allows_only_voice_two_route_bit(self):
        source = [store(0xd417, 0x82), store(0xd418, 0x1f)]
        candidate = [store(0xd417, 0x80), store(0xd418, 0x1f)]
        self.assertEqual(len(DIAGNOSTIC.compare_ledgers(source, candidate)), 1)
        candidate[1]['value'] = 0x0f
        with self.assertRaisesRegex(ValueError, 'outside'):
            DIAGNOSTIC.compare_ledgers(source, candidate)

    def test_store_guard_rejects_timing_or_route_direction_changes(self):
        source = [store(0xd417, 0x82)]
        with self.assertRaisesRegex(ValueError, 'timing'):
            DIAGNOSTIC.compare_ledgers(source, [store(0xd417, 0x80, cycle=2069)])
        with self.assertRaisesRegex(ValueError, 'route bit'):
            DIAGNOSTIC.compare_ledgers(source, [store(0xd417, 0x81)])

    def test_signal_guard_rejects_identical_and_dc_only_differences(self):
        from audio_comparison import Pcm16
        source = Pcm16(4, 1, 4, array('h', [0, 1, 0, -1]), 'source')
        identical = Pcm16(4, 1, 4, array('h', [0, 1, 0, -1]), 'same')
        dc_only = Pcm16(4, 1, 4, array('h', [1, 2, 1, 0]), 'dc')
        for candidate in (identical, dc_only):
            with self.assertRaisesRegex(ValueError, 'AC difference'):
                DIAGNOSTIC.signal_delta(source, candidate, 0, 1)
        changed = Pcm16(4, 1, 4, array('h', [0, 2, 0, -2]), 'changed')
        self.assertEqual(DIAGNOSTIC.signal_delta(source, changed, 0, 1)['changedSamples'], 2)


if __name__ == '__main__':
    unittest.main()
