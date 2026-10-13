import importlib.util
import io
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('sid_vice_trace', ROOT / 'scripts/trace-sid-vice.py')
trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace)


def sid_fixture():
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 2), (6, 124), (8, 0x1000), (10, 0x1000), (12, 0x1006), (14, 1), (16, 1), (118, 0x14)):
        header[offset:offset + 2] = value.to_bytes(2, 'big')
    return header + bytes.fromhex('a90f8d18d460ee0020ad00208d02d460')


def entry(cycle, raster_cycle=12):
    return f'#1 (Trace  exec 1006)  250/$0fa, {raster_cycle:3}/$0c\n.C:1006  EE 00 20    INC $2000 - A:FA X:00 Y:00 SP:fd ..-..I.. {cycle}\n'


def store(cycle, value=1, opcode='8D 02 D4', mnemonic='STA $D402'):
    return f'#2 (Trace store d402)  250/$0fa,  28/$1c\n.C:100c  {opcode}    {mnemonic} - A:{value:02X} X:00 Y:00 SP:fd ..-..I.. {cycle}\n'


def marker(cycle, address):
    return f'#1 (Trace  exec {address:04x})  250/$0fa,  12/$0c\n.C:{address:04x}  A9 00    LDA #$00 - A:00 X:00 Y:00 SP:fd ..-..I.. {cycle}\n'


def banked_fixture():
    from verify_player import cpu_type
    cpu_type()
    from sid_assembler import assemble
    source = '''
init:
STA $D400
PHP
PLA
AND #$C7
STA $D401
LDX #$31
LDY #$42
LDA #$37
STA $01
RTS
play:
STA $D402
PHP
PLA
AND #$C7
STA $D403
STX $D405
STY $D406
LDA $B000
STA $D407
LDA #$37
STA $01
RTS
'''
    payload, labels, _ = assemble(source)
    header = sid_fixture()[:124]
    header[12:14] = labels['play'].to_bytes(2, 'big')
    header[14:16] = (2).to_bytes(2, 'big')
    payload += bytes(0xb000 - 0x1000 - len(payload)) + bytes([0x7c])
    return bytes(header) + payload


class SidViceTraceTest(unittest.TestCase):
    def test_process_timeout_keeps_default_and_forwards_positive_override(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sid, oracle = root / 'fixture.sid', root / 'oracle.json'
            sid.write_bytes(sid_fixture())
            oracle.write_text('[]')
            for name, options, seconds in (('default', {}, 60), ('override', {'timeout': 180.5}, 180.5)):
                with self.subTest(name=name), patch.object(trace.subprocess, 'run',
                        side_effect=trace.subprocess.TimeoutExpired('VICE fixture', seconds)) as runner:
                    with self.assertRaises(trace.subprocess.TimeoutExpired):
                        trace.run_trace(sid, oracle, root / name, 0, 1, Path('/tmp/vice'), Path('/tmp/data'), **options)
                    self.assertEqual(seconds, runner.call_args.kwargs['timeout'])
                    self.assertFalse((root / name / 'study.json').exists())

    def test_invalid_timeouts_fail_before_input_read_or_output_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for seconds in (0, -1, True, float('nan'), float('inf'), '180'):
                output = root / 'output'
                with self.subTest(timeout=seconds), self.assertRaisesRegex(ValueError, 'Timeout'):
                    trace.run_trace(root / 'absent.sid', root / 'absent.json', output, 0, 1,
                                    Path('/tmp/vice'), Path('/tmp/data'), timeout=seconds)
                self.assertFalse(output.exists())

    def test_cli_timeout_seconds_reach_the_public_runner(self):
        arguments = ['trace-sid-vice.py', 'fixture.sid', '--oracle', 'oracle.json', '--output', 'fresh',
                     '--timeout', '180.5']
        with patch.object(sys, 'argv', arguments), patch.object(trace, 'run_trace', return_value={}) as runner:
            with patch('sys.stdout', new_callable=io.StringIO):
                trace.main()
        self.assertEqual(180.5, runner.call_args.kwargs['timeout'])

    def test_selected_banked_profile_requires_explicit_selection_without_mutating_header(self):
        data = banked_fixture()
        original = bytes(data)
        for selected in (1, 2):
            profile = trace.psid_profile(data, subtune=selected, profile='pal-banked')
            self.assertEqual(0xb001, profile['endAddress'])
            self.assertEqual(selected - 1, profile['initAccumulator'])
            self.assertEqual(0x36, profile['entryBank'])
        self.assertEqual(original, data)
        with self.assertRaises(ValueError):
            trace.psid_profile(data)
        for selected in (None, 0, 3, True, 1.5):
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                trace.psid_profile(data, subtune=selected, profile='pal-banked')

    def test_banked_harness_restores_bank_outside_nine_cycle_poll_and_traces_init(self):
        profile = trace.psid_profile(banked_fixture(), subtune=2, profile='pal-banked')
        program, labels = trace.harness(profile, 2)
        poll = labels['wait'] - trace.HARNESS_BASE + 2
        self.assertEqual(bytes.fromhex('a9facd12d0d0'), program[poll:poll + 6])
        self.assertLess(labels['restore_bank'], labels['wait'])
        restore = labels['restore_bank'] - trace.HARNESS_BASE + 2
        self.assertEqual(bytes.fromhex('a9368501'), program[restore:restore + 4])
        self.assertIn(bytes.fromhex('a901a200a000200010'), program)
        commands = trace.monitor_commands(Path('/tmp/payload.prg'), Path('/tmp/harness.prg'), profile, labels, 1, 1)
        self.assertIn('trace exec $1000', commands)
        self.assertIn(f'trace exec ${labels["init_return"]:04x}', commands)
        self.assertIn('@ram:$c102', commands)

    def test_banked_parser_and_oracle_require_all_init_stores_and_both_markers(self):
        log = marker(10, 0x1000) + store(20, 9) + marker(30, 0xc050)
        log += entry(100) + entry(19756) + store(19772, 2)
        parsed = trace.parse_trace(log, 0x1006, init_address=0x1000, init_return=0xc050)
        expected = [dict(phase='init', tick=None, address=0xd402, value=9),
                    dict(phase='play', tick=1, address=0xd402, value=2)]
        result = trace.verify_trace(parsed, expected, 1, 1)
        self.assertEqual((1, 1), (result['matchedInitWrites'], result['matchedPlayWrites']))
        for oracle in (expected[1:], [dict(expected[0], value=8), expected[1]]):
            with self.subTest(oracle=oracle), self.assertRaisesRegex(ValueError, 'ordered'):
                trace.verify_trace(parsed, oracle, 1, 1)
        for invalid in (log.replace(marker(10, 0x1000), ''),
                        log.replace(marker(30, 0xc050), ''),
                        log.replace(marker(30, 0xc050), marker(15, 0xc050))):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                trace.parse_trace(invalid, 0x1006, init_address=0x1000, init_return=0xc050)

    def test_headless_banked_selection_init_flags_poll_flags_and_bank_restoration(self):
        vice = ROOT / '.tools/vice-headless-3.9/build/src/x64sc'
        data_directory = Path('/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice')
        if not vice.is_file() or not data_directory.is_dir():
            self.skipTest('Local headless VICE and ROM data are required for the executed fixture')
        from psid_audit import audit_psid
        data = banked_fixture()
        for selected, first in ((1, 0), (2, 1)):
            with self.subTest(selected=selected), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                sid, expected = root / 'fixture.sid', root / 'oracle.json'
                sid.write_bytes(data)
                _, oracle = audit_psid(data, 2, subtune=selected, profile='pal-banked')
                expected.write_text(json.dumps(oracle))
                result = trace.run_trace(sid, expected, root / 'trace', first, 1, vice, data_directory,
                                         subtune=selected, profile='pal-banked')
                parsed = json.loads((root / 'trace/trace.json').read_text())
                self.assertEqual([('init', None, 0xd400, selected - 1), ('init', None, 0xd401, 6)] +
                                 [('play', tick, address, value) for tick in range(first, 2)
                                  for address, value in ((0xd402, 250), (0xd403, 7), (0xd405, 0x31),
                                                        (0xd406, 0x42), (0xd407, 0x7c))],
                                 [(row['phase'], row['tick'], row['address'], row['value']) for row in parsed['writes']])
                self.assertEqual(2, result['verification']['matchedInitWrites'])
                self.assertEqual(data, sid.read_bytes())

    def test_headless_init_internal_play_and_shared_entry_are_not_extra_play_calls(self):
        vice = ROOT / '.tools/vice-headless-3.9/build/src/x64sc'
        data_directory = Path('/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice')
        if not vice.is_file() or not data_directory.is_dir():
            self.skipTest('Local headless VICE and ROM data are required for the executed fixture')
        from psid_audit import audit_psid
        from sid_assembler import assemble
        sources = {
            'internal': 'init:\nLDA #$11\nSTA $D400\nJSR play\nLDA #$22\nSTA $D401\nRTS\nplay:\nSTA $D402\nRTS',
            'shared': 'init:\nplay:\nSTA $D400\nPHP\nPLA\nAND #$C7\nSTA $D401\nRTS',
        }
        for kind, source in sources.items():
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                payload, labels, _ = assemble(source)
                header = sid_fixture()[:124]
                header[12:14] = labels['play'].to_bytes(2, 'big')
                encoded = bytes(header) + payload
                _, oracle = audit_psid(encoded, 2, subtune=1, profile='pal-banked')
                root = Path(directory)
                sid, expected = root / 'fixture.sid', root / 'oracle.json'
                sid.write_bytes(encoded)
                expected.write_text(json.dumps(oracle))
                result = trace.run_trace(sid, expected, root / 'trace', 0, 1, vice, data_directory,
                                         subtune=1, profile='pal-banked')
                self.assertEqual(2, result['verification']['playCalls'])
                self.assertEqual(len(oracle), result['verification']['matchedWrites'])
                parsed = json.loads((root / 'trace/trace.json').read_text())
                self.assertEqual(2 if kind == 'internal' else 1, len(parsed['initExecutions']))
                self.assertTrue(all(row['phase'] == 'init' and row['tick'] is None
                                    for row in parsed['initExecutions']))
                if kind == 'shared':
                    commands = (root / 'trace/commands.mon').read_text()
                    self.assertEqual(1, commands.count('trace exec $1000'))

    def test_dual_pal_profile_declares_both_chips_and_traces_only_their_sound_registers(self):
        data = sid_fixture()
        data[5], data[119], data[122] = 3, 0x54, 0x42
        profile = trace.psid_profile(data)
        self.assertEqual([0xd400, 0xd420], profile['sidBases'])
        _, labels = trace.harness(profile, 3)
        commands = trace.monitor_commands(Path('/tmp/payload.prg'), Path('/tmp/harness.prg'), profile, labels, 0, 2)
        self.assertIn('trace store $d400 $d418 if', commands)
        self.assertIn('trace store $d420 $d438 if', commands)
        second = store(120, 9, '8D 22 D4', 'STA $D422').replace('store d402', 'store d422')
        parsed = trace.parse_trace(entry(100) + store(116) + second, 0x1006, profile['sidBases'])
        self.assertEqual([0xd402, 0xd422], [row['address'] for row in parsed['writes']])
        with self.assertRaisesRegex(ValueError, 'address'):
            trace.parse_trace(entry(100) + second, 0x1006)
        for offset, value in ((119, 0x94), (122, 0x50), (123, 0x44)):
            invalid = bytearray(data)
            invalid[offset] = value
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                trace.psid_profile(invalid)

    def test_headless_vice_dual_fixture_preserves_chip_filters_and_six_voice_writes(self):
        vice = ROOT / '.tools/vice-headless-3.9/build/src/x64sc'
        data_directory = Path('/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice')
        if not vice.is_file() or not data_directory.is_dir():
            self.skipTest('Local headless VICE and ROM data are required for the executed fixture')
        data = sid_fixture()[:130]
        data[5], data[119], data[122] = 3, 0x54, 0x42
        pairs = [(base + voice * 7, value) for base, start in ((0xd400, 0x11), (0xd420, 0x51))
                 for voice, value in enumerate(range(start, start + 3))]
        pairs += [(0xd416, 0x20), (0xd436, 0xb0), (0xd418, 0x1f), (0xd438, 0x1a)]
        for address, value in pairs:
            data.extend((0xa9, value, 0x8d, address & 255, address >> 8))
        data.append(0x60)
        oracle = [dict(phase='play', tick=tick, address=address, value=value)
                  for tick in range(3) for address, value in pairs]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sid, expected = root / 'dual.sid', root / 'oracle.json'
            sid.write_bytes(data)
            expected.write_text(json.dumps(oracle))
            result = trace.run_trace(sid, expected, root / 'trace', 0, 2, vice, data_directory)
            self.assertEqual(30, result['verification']['matchedWrites'])
            command = json.loads((root / 'trace/command.json').read_text())
            self.assertIn('-sidextra', command)
            self.assertIn('0xd420', command)

    def test_accepts_explicit_single_pal_callable_ram_fixture_and_rejects_other_contracts(self):
        profile = trace.psid_profile(sid_fixture())
        self.assertEqual((profile['loadAddress'], profile['initAddress'], profile['playAddress'], profile['sidModel']), (0x1000, 0x1000, 0x1006, 'MOS6581'))
        for offset, value in ((5, 3), (119, 0x18), (21, 1), (15, 2), (17, 2), (122, 0x42)):
            data = sid_fixture()
            data[offset] = value
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                trace.psid_profile(data)
        data = sid_fixture()
        data[8:10] = (0xc000).to_bytes(2, 'big')
        with self.assertRaisesRegex(ValueError, 'RAM'):
            trace.psid_profile(data)

    def test_harness_bounds_play_calls_and_monitor_does_not_trace_outside_window(self):
        profile = trace.psid_profile(sid_fixture())
        program, labels = trace.harness(profile, 4)
        self.assertEqual(program[:2], b'\x00\xc0')
        self.assertIn(bytes.fromhex('200610'), program)
        self.assertGreater(labels['done'], 0xc000)
        commands = trace.monitor_commands(Path('/tmp/payload.prg'), Path('/tmp/harness.prg'), profile, labels, 1, 3)
        self.assertIn('trace store $d400 $d418 if', commands)
        counter = '((@ram:$c101 * $0100) + @ram:$c100)'
        self.assertIn(f'({counter} >= $0001) && ({counter} <= $0003)', commands)
        self.assertIn('dummy off', commands)
        self.assertIn('sidefx off', commands)
        for count in (0, True, 65536):
            with self.subTest(count=count), self.assertRaises(ValueError):
                trace.harness(profile, count)
        with self.assertRaisesRegex(ValueError, 'path'):
            trace.monitor_commands(Path('/tmp/bad"path'), Path('/tmp/harness.prg'), profile, labels, 1, 3)

    def test_monitor_window_and_harness_support_a_full_2018_call_trace(self):
        profile = trace.psid_profile(sid_fixture())
        program, labels = trace.harness(profile, 2018)
        self.assertIn(bytes.fromhex('ee00c1'), program)
        self.assertIn(bytes.fromhex('ee01c1'), program)
        commands = trace.monitor_commands(Path('/tmp/payload.prg'), Path('/tmp/harness.prg'), profile, labels, 254, 2017)
        counter = '((@ram:$c101 * $0100) + @ram:$c100)'
        self.assertIn(f'({counter} >= $00fe) && ({counter} <= $07e1)', commands)
        for first, last in ((-1, 3), (3, 2), (0, 65535), (True, 3)):
            with self.subTest(first=first, last=last), self.assertRaises(ValueError):
                trace.monitor_commands(Path('/tmp/payload.prg'), Path('/tmp/harness.prg'), profile, labels, first, last)

    def test_parser_associates_writes_with_calls_and_preserves_instruction_context(self):
        parsed = trace.parse_trace(entry(100) + store(116) + entry(19757, 13) + store(19773, 2), 0x1006)
        self.assertEqual([row['tick'] for row in parsed['writes']], [0, 1])
        self.assertEqual(parsed['writes'][0], dict(tick=0, address=0xd402, value=1, writerPc=0x100c, opcodeHex='8d02d4', instruction='STA $D402', registers=dict(a=1, x=0, y=0, sp=0xfd, flags='..-..I..'), rasterLine=250, rasterCycle=28, monitorCycle=116))
        expected = [dict(phase='play', tick=tick, address=0xd402, value=tick + 1) for tick in range(2)]
        result = trace.verify_trace(parsed, expected, 0, 1)
        self.assertEqual(result['matchedWrites'], 2)
        self.assertEqual(result['maximumCadenceError'], 1)

    def test_oracle_guard_rejects_reordered_missing_changed_and_extra_stores(self):
        valid = trace.parse_trace(entry(100) + store(116) + entry(19756) + store(19772, 2), 0x1006)
        expected = [dict(phase='play', tick=tick, address=0xd402, value=tick + 1) for tick in range(2)]
        for writes in (expected[::-1], expected[:-1], expected + expected[-1:], [dict(expected[0], value=9), expected[1]]):
            with self.subTest(writes=writes), self.assertRaises(ValueError):
                trace.verify_trace(valid, writes, 0, 1)
        bad = trace.parse_trace(entry(100) + store(116) + entry(20000) + store(20016, 2), 0x1006)
        with self.assertRaisesRegex(ValueError, 'cadence'):
            trace.verify_trace(bad, expected, 0, 1)

    def test_parser_fails_closed_on_unpaired_nonstore_and_index_address_disagreement(self):
        for text in (store(116), entry(100) + store(116, opcode='EE 02 D4', mnemonic='INC $D402'), entry(100) + store(116, mnemonic='STA $D403'), entry(100) + '#2 (Trace store d402)  250/$0fa, 28/$1c\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                trace.parse_trace(text, 0x1006)

    def test_headless_vice_independent_fixture_binds_writer_pc_and_store_source_before_following_load(self):
        vice = ROOT / '.tools/vice-headless-3.9/build/src/x64sc'
        data_directory = Path('/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice')
        if not vice.is_file() or not data_directory.is_dir():
            self.skipTest('Local headless VICE and ROM data are required for the executed fixture')
        data = sid_fixture()[:130] + bytes.fromhex('ee0020ad00208d02d4a9e78d03d4a99960')
        oracle = [dict(phase='play', tick=tick, address=address, value=value) for tick in range(3) for address, value in ((0xd402, tick + 1), (0xd403, 0xe7))]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sid, expected = root / 'fixture.sid', root / 'oracle.json'
            sid.write_bytes(data)
            expected.write_text(json.dumps(oracle))
            result = trace.run_trace(sid, expected, root / 'trace', 0, 2, vice, data_directory)
            parsed = json.loads((root / 'trace/trace.json').read_text())
            self.assertEqual(result['verification']['matchedWrites'], 6)
            self.assertEqual([(row['writerPc'], row['registers']['a']) for row in parsed['writes']], [(0x100c, 1), (0x1011, 0xe7), (0x100c, 2), (0x1011, 0xe7), (0x100c, 3), (0x1011, 0xe7)])
            self.assertEqual({row['monitorCycle'] - parsed['entries'][row['tick']]['monitorCycle'] for row in parsed['writes'] if row['writerPc'] == 0x100c}, {14})

    def test_headless_vice_full_cycle_preserves_call_numbers_and_window_across_byte_rollovers(self):
        vice = ROOT / '.tools/vice-headless-3.9/build/src/x64sc'
        data_directory = Path('/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice')
        if not vice.is_file() or not data_directory.is_dir():
            self.skipTest('Local headless VICE and ROM data are required for the executed fixture')
        data = sid_fixture()
        oracle = [dict(phase='play', tick=tick, address=0xd402, value=(tick + 1) & 255) for tick in range(2018)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sid, expected = root / 'fixture.sid', root / 'oracle.json'
            sid.write_bytes(data)
            expected.write_text(json.dumps(oracle))
            result = trace.run_trace(sid, expected, root / 'trace', 254, 2017, vice, data_directory)
            parsed = json.loads((root / 'trace/trace.json').read_text())
            self.assertEqual(result['verification']['playCalls'], 2018)
            self.assertEqual(result['verification']['matchedWrites'], 2018 - 254)
            self.assertEqual([row['tick'] for row in parsed['writes']], list(range(254, 2018)))
            self.assertEqual([row['value'] for row in parsed['writes'][:4]], [255, 0, 1, 2])


if __name__ == '__main__':
    unittest.main()
