import copy
import hashlib
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('native_vice', ROOT / 'scripts/verify-native-vice.py')
native_vice = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native_vice)


def log_for(states, cycles):
    lines = []
    for state, cycle in zip(states, cycles):
        lines += [f'.;1003 fe 0c 01 f4 2f 35 00110111 254 017 {cycle}', '>C:d400  ' + ' '.join(f'{value:02x}' for value in state)]
    return '\n'.join(lines)


class NativeViceTest(unittest.TestCase):
    def test_ntsc_checkpoints_require_ntsc_cadence(self):
        states = [bytes(25), bytes(25)]
        log = log_for(states, [100, 100 + 10 * 17095 + 2])
        result = native_vice.verify_log(log, [], [0, 10], clock="ntsc")
        self.assertEqual(result["frameCycles"], 17095)
        self.assertEqual(result["checkpoints"][1]["cycleError"], 2)
        with self.assertRaises(ValueError):
            native_vice.verify_log(log, [], [0, 10])
        with self.assertRaises(ValueError):
            native_vice.verify_log(log_for(states, [100, 100 + 10 * 19656]), [], [0, 10], clock="ntsc")

    def test_export_timing_fields_cannot_contradict_declared_clock(self):
        for field, value in (("clockHz", 985248), ("ticksPerSecond", 50), ("frameCycles", 19656), ("frameCycles", 17095.0)):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                native_vice.export_clock({"clock": "NTSC", field: value})

    def test_export_rejects_unknown_or_ambiguous_clock(self):
        prg = b"\x01\x08native"
        report = {"prgSha256": hashlib.sha256(prg).hexdigest(), "player": "Extra", "frameSpeed": 1, "standalonePlayerPlayAddress": 0x1003, "sidModel": "MOS8580", "sids": [{"baseAddress": 0xd400, "model": "MOS8580"}]}
        for clock in ("UNKNOWN", "PAL/NTSC", None):
            with self.subTest(clock=clock), self.assertRaises(ValueError):
                native_vice.export_profile(prg, dict(report, clock=clock))

    def test_6581_export_profile_selects_the_declared_model_for_vice(self):
        prg = b'\x01\x08native'
        report = {'prgSha256': hashlib.sha256(prg).hexdigest(), 'player': 'Extra', 'frameSpeed': 1, 'standalonePlayerPlayAddress': 0x1003, 'sidModel': 'MOS6581', 'sids': [{'baseAddress': 0xd400, 'model': 'MOS6581'}]}
        self.assertEqual(native_vice.export_profile(prg, report), ((0xd400,), None, 'MOS6581'))
        for change in (
            lambda value: value.update(sidModel='unknown'),
            lambda value: value['sids'][0].update(model='MOS8580'),
        ):
            changed = copy.deepcopy(report)
            change(changed)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'SID layout'):
                native_vice.export_profile(prg, changed)

    def test_export_profile_binds_prg_and_selector_to_the_pinned_build(self):
        prg = bytearray(1024)
        prg[:2] = b'\x01\x08'
        prg[0x0bd0 - 0x0801 + 2] = 0x60
        labels = b'al b27 .SetSID2address\nal bd0 .SID2keyExe:endplmi\n'
        report = {'prgSha256': hashlib.sha256(prg).hexdigest(), 'player': 'Extra', 'frameSpeed': 1, 'standalonePlayerPlayAddress': 0x1003, 'sidCount': 2, 'sids': [{'baseAddress': base, 'model': 'MOS8580'} for base in (0xd400, 0xd420)], 'build': {'labelsSha256': hashlib.sha256(labels).hexdigest()}, 'standaloneAddressSelector': {'entryAddress': 0x0b27, 'returnAddress': 0x0bd0, 'baseAddress': 0xd420}}
        with patch.object(Path, 'read_bytes', return_value=labels):
            self.assertEqual(native_vice.export_profile(prg, report)[0], (0xd400, 0xd420))
            old_model = copy.deepcopy(report)
            old_model['sidModel'] = 'MOS6581'
            for chip in old_model['sids']:
                chip['model'] = 'MOS6581'
            self.assertEqual(native_vice.export_profile(prg, old_model), ((0xd400, 0xd420), old_model['standaloneAddressSelector'], 'MOS6581'))
            for change in (
                lambda report: report.update(prgSha256='changed'),
                lambda report: report['build'].update(labelsSha256='changed'),
                lambda report: report['sids'][1].update(baseAddress=0xd440),
                lambda report: report['standaloneAddressSelector'].update(returnAddress=0x0bcf),
                lambda report: report.update(frameSpeed=2),
            ):
                changed = copy.deepcopy(report)
                change(changed)
                with self.subTest(change=change), self.assertRaises(ValueError):
                    native_vice.export_profile(prg, changed)
            prg[0x0bd0 - 0x0801 + 2] = 0xea
            report['prgSha256'] = hashlib.sha256(prg).hexdigest()
            with self.assertRaisesRegex(ValueError, 'original RTS'):
                native_vice.export_profile(prg, report)

    def test_dual_checkpoints_compare_each_bank_without_accepting_mirrors(self):
        writes = [dict(phase='init', tick=None, address=0xd418, value=15), dict(phase='init', tick=None, address=0xd438, value=7), dict(phase='play', tick=0, address=0xd420, value=42)]
        first, second = bytes(24) + bytes([15]), bytes(24) + bytes([7])
        log = log_for([first, first], [100, 100 + 19656]).splitlines()
        log.insert(2, '>C:d420  ' + second.hex(' '))
        log.append('>C:d420  ' + (bytes([42]) + second[1:]).hex(' '))
        log = '\n'.join(log)
        result = native_vice.verify_log(log, writes, [0, 1], (0xd400, 0xd420))
        self.assertEqual(result['checkpoints'][1]['sidRegisters'], (first + bytes([42]) + second[1:]).hex())
        for bad in (log.replace('>C:d420  2a', '>C:d420  00'), log.rsplit('\n', 1)[0]):
            with self.assertRaises(ValueError):
                native_vice.verify_log(bad, writes, [0, 1], (0xd400, 0xd420))

    def test_dual_monitor_dumps_both_banks_at_every_checkpoint(self):
        text = native_vice.monitor_commands(Path('/tmp/song.prg'), [0, 20], (0xd400, 0xd420))
        self.assertEqual(text.count('m $d400 $d418'), 2)
        self.assertEqual(text.count('m $d420 $d438'), 2)

    def test_headless_selector_returns_through_native_code_and_requires_saved_address(self):
        selector = {'entryAddress': 0x0b27, 'returnAddress': 0x0bd0, 'baseAddress': 0xd420}
        text = native_vice.monitor_commands(Path('/tmp/song.prg'), [0, 20], (0xd400, 0xd420), selector)
        self.assertIn('keybuf run\\n\nuntil $0b27\nradix h\nbank ram\nm $03fe $03ff\nr pc=$0bd0\nx', text)
        native_vice.verify_selector('>C:03fe  20 d4', selector)
        for log in ('', '>C:03fe  00 d4', '>C:03fe  20 d4\n>C:03fe  20 d4'):
            with self.assertRaisesRegex(ValueError, 'saved SID address'):
                native_vice.verify_selector(log, selector)

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
