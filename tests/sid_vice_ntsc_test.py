import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from sid_vice_trace_test import ROOT, entry, sid_fixture, store, trace


def ntsc_fixture():
    data = bytearray(sid_fixture())
    data[118:120] = (0x18).to_bytes(2, 'big')
    return bytes(data)


class SidViceNtscTest(unittest.TestCase):
    def test_explicit_clock_admits_only_matching_strict_source(self):
        profile = trace.psid_profile(ntsc_fixture(), clock='ntsc')
        self.assertEqual(profile['sidModel'], 'MOS6581')
        for data, options in ((ntsc_fixture(), {}), (sid_fixture(), {'clock': 'ntsc'}),
                              (ntsc_fixture(), {'clock': 'ntsc', 'profile': 'pal-banked'})):
            with self.subTest(options=options), self.assertRaises(ValueError):
                trace.psid_profile(data, **options)

    def test_ntsc_geometry_and_cadence_are_checked_together(self):
        log = entry(100, 64) + store(116) + entry(17195, 64) + store(17211, 2)
        parsed = trace.parse_trace(log, 0x1006, clock='ntsc')
        oracle = [dict(phase='play', tick=i, address=0xd402, value=i + 1) for i in range(2)]
        result = trace.verify_trace(parsed, oracle, 0, 1, clock='ntsc')
        self.assertEqual(result['frameCycles'], 17095)
        self.assertEqual(result['maximumCadenceError'], 0)
        with self.assertRaises(ValueError):
            trace.parse_trace(log, 0x1006)
        with self.assertRaises(ValueError):
            trace.verify_trace(parsed, oracle, 0, 1)
        for bad in (entry(100, 65), entry(100).replace('250/$0fa', '263/$107')):
            with self.subTest(log=bad), self.assertRaises(ValueError):
                trace.parse_trace(bad + store(116), 0x1006, clock='ntsc')

    def test_ntsc_call_store_bound_does_not_accept_pal_length_work(self):
        with self.assertRaises(ValueError):
            trace.parse_trace(entry(100) + store(18000), 0x1006, clock='ntsc')
        self.assertEqual(len(trace.parse_trace(entry(100) + store(18000), 0x1006)['writes']), 1)

    def test_run_selects_ntsc_machine_and_matching_cycle_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sid, oracle = root / 'fixture.sid', root / 'oracle.json'
            sid.write_bytes(ntsc_fixture())
            oracle.write_text('[]')
            with patch.object(trace.subprocess, 'run', side_effect=trace.subprocess.TimeoutExpired('fixture', 1)) as runner:
                with self.assertRaises(trace.subprocess.TimeoutExpired):
                    trace.run_trace(sid, oracle, root / 'trace', 0, 1, Path('/tmp/vice'), Path('/tmp/data'), clock='ntsc')
            command = runner.call_args.args[0]
            self.assertIn('-ntsc', command)
            self.assertNotIn('-pal', command)
            self.assertEqual(command[command.index('-limitcycles') + 1], str(4_000_000 + 2 * 17095))

    def test_cli_forwards_explicit_clock(self):
        args = ['trace-sid-vice.py', 'fixture.sid', '--oracle', 'oracle.json', '--output', 'fresh', '--clock', 'ntsc']
        with patch.object(sys, 'argv', args), patch.object(trace, 'run_trace', return_value={}) as runner:
            with patch('sys.stdout', new_callable=io.StringIO):
                trace.main()
        self.assertEqual(runner.call_args.kwargs['clock'], 'ntsc')

    def test_headless_ntsc_fixture_matches_independent_cpu(self):
        vice = ROOT / '.tools/vice-headless-3.9/build/src/x64sc'
        data = ROOT / '.tools/vice-headless-3.9/source/data'
        if not vice.is_file() or not data.is_dir():
            self.skipTest('Pinned headless VICE is required for machine execution')
        from psid_audit import audit_psid
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sid, oracle = root / 'fixture.sid', root / 'oracle.json'
            sid.write_bytes(ntsc_fixture())
            _, writes = audit_psid(ntsc_fixture(), 3, clock='ntsc')
            oracle.write_text(json.dumps(writes))
            result = trace.run_trace(sid, oracle, root / 'trace', 0, 2, vice, data, clock='ntsc')
            self.assertEqual(result['verification']['matchedWrites'], 3)
            self.assertEqual(result['verification']['frameCycles'], 17095)
            self.assertEqual(result['clock'], 'ntsc')


if __name__ == '__main__':
    unittest.main()
