import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_vice', ROOT / 'scripts/verify-native-vice.py')
native_vice = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native_vice)


def log_for(states, cycles):
    lines = []
    for state, cycle in zip(states, cycles):
        lines += [f'.;1003 fe 0c 01 f4 2f 35 00110111 254 017 {cycle}', '>C:d400  ' + ' '.join(f'{value:02x}' for value in state)]
    return '\n'.join(lines)


class NativeViceTest(unittest.TestCase):
    def test_checks_init_each_checkpoint_and_pal_cadence_with_poll_jitter(self):
        writes = [dict(phase='init', tick=None, address=0xd418, value=15), dict(phase='play', tick=1, address=0xd400, value=42)]
        initial = bytes(24) + bytes([15])
        final = bytes([42]) + initial[1:]
        result = native_vice.verify_log(log_for([initial, final], [100, 100 + 3 * 19656 - 1]), writes, [0, 3])
        self.assertEqual(result['checkpoints'][1]['cycleError'], -1)
        self.assertEqual(result['checkpoints'][1]['completedPlayCalls'], 3)

    def test_rejects_wrong_register_missing_snapshot_and_wrong_cadence(self):
        valid = log_for([bytes(25), bytes(25)], [100, 100 + 3 * 19656])
        for invalid in [valid.replace('>C:d400  00', '>C:d400  ff', 1), valid.rsplit('\n', 1)[0], valid.replace(str(100 + 3 * 19656), str(100 + 4 * 19656))]:
            with self.subTest(log=invalid), self.assertRaises(ValueError):
                native_vice.verify_log(invalid, [], [0, 3])

    def test_monitor_uses_decimal_counts_and_hex_memory_and_exact_crossings(self):
        text = native_vice.monitor_commands(Path('/tmp/song.prg'), [0, 20, 501])
        self.assertIn('radix d\nignore 1 19\nx\nr\nradix h\n', text)
        self.assertIn('radix d\nignore 1 480\nx\nr\nradix h\n', text)
        self.assertEqual(text.count('m $d400 $d418'), 3)
        with self.assertRaises(ValueError):
            native_vice.monitor_commands(Path('/tmp/bad"path'), [0, 20])

    def test_rejects_unordered_or_uncovered_audit_ticks(self):
        for writes in [[dict(phase='play', tick=3, address=0xd400, value=1), dict(phase='play', tick=2, address=0xd400, value=2)], [dict(phase='play', tick=1, address=0xd419, value=1)]]:
            with self.assertRaises(ValueError):
                native_vice.expected_states(writes, [0, 4])


if __name__ == '__main__':
    unittest.main()
