import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
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


class SidViceTraceTest(unittest.TestCase):
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
