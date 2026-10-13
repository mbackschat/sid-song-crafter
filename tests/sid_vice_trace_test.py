import importlib.util
import hashlib
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


def store(cycle, value=1, opcode='8D 02 D4', mnemonic='STA $D402', *, address=0xd402, x=0, y=0):
    return f'#2 (Trace store {address:04x})  250/$0fa,  28/$1c\n.C:100c  {opcode}    {mnemonic} - A:{value:02X} X:{x:02X} Y:{y:02X} SP:fd ..-..I.. {cycle}\n'


def marker(cycle, address):
    return f'#1 (Trace  exec {address:04x})  250/$0fa,  12/$0c\n.C:{address:04x}  A9 00    LDA #$00 - A:00 X:00 Y:00 SP:fd ..-..I.. {cycle}\n'


def host_call(cycle):
    return f'#3 (Trace exec c040)  250/$0fa,  6/$06\n.C:c040  20 06 10    JSR $1006 - A:FA X:00 Y:00 SP:fd ..-..I.. {cycle}\n'


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


def high_ram_fixture():
    from verify_player import cpu_type
    cpu_type()
    from sid_assembler import assemble
    source = '''
init:
TSX
LDA $0101,X
STA $D400
LDA $0102,X
STA $D401
LDA #$35
STA $01
LDA $E000
STA $D405
LDA $FFFF
STA $D406
LDA $CFF0
STA $D407
LDA #$37
STA $01
RTS
play:
TSX
LDA $0101,X
STA $D402
LDA $0102,X
STA $D403
LDA $CFF0
STA $D408
LDA #$35
STA $01
LDA $E000
STA $D409
LDA $FFFF
STA $D40A
LDA #$37
STA $01
RTS
'''
    payload, labels, _ = assemble(source)
    header = sid_fixture()[:124]
    for offset, address in ((8, 0xc000), (10, 0xc000), (12, labels['play'] - 0x1000 + 0xc000)):
        header[offset:offset + 2] = address.to_bytes(2, 'big')
    return bytes(header) + payload


class SidViceTraceTest(unittest.TestCase):
    def test_host_call_markers_require_an_entry_and_ordered_timestamps(self):
        log = host_call(90) + entry(100) + entry(120) + store(136)
        parsed = trace.parse_trace(log, 0x1006, host_call=0xc040)
        self.assertEqual(1, len(parsed['entries']))
        self.assertEqual([0], [row['tick'] for row in parsed['playInternalEntries']])
        for invalid in (entry(100) + store(136), host_call(90) + store(136),
                        host_call(90) + host_call(95) + entry(100) + store(136),
                        host_call(110) + entry(100) + store(136),
                        host_call(90).replace('20 06 10', '20 07 10') + entry(100) + store(136)):
            with self.subTest(log=invalid), self.assertRaises(ValueError):
                trace.parse_trace(invalid, 0x1006, host_call=0xc040)

    def test_strict_default_retains_profile_shape_harness_bytes_and_base_monitor_commands(self):
        profile = trace.psid_profile(sid_fixture())
        program, labels = trace.harness(profile, 2)
        commands = trace.monitor_commands(Path('/tmp/payload.prg'), Path('/tmp/harness.prg'), profile, labels, 0, 1)
        self.assertEqual({'endAddress', 'initAddress', 'loadAddress', 'payload', 'playAddress', 'sidBases', 'sidModel'},
                         set(profile))
        self.assertEqual('d8a5ee245b95aa058154b37496dc67fd569a3b10c7a85b0dfb38565f988bff0f',
                         hashlib.sha256(program).hexdigest())
        self.assertEqual('96073ed0d39045f844821442796f4587f27884043ad7401043af14e62898e10c',
                         hashlib.sha256(commands.replace(f'trace exec ${labels["call"]:04x}\n', '').encode()).hexdigest())
        self.assertEqual(1, commands.count(f'trace exec ${labels["call"]:04x}\n'))

    def test_banked_host_placement_moves_code_counters_and_zeroes_reachable_ram(self):
        data = high_ram_fixture()
        for host_base in (0x0400, 0x9e00):
            with self.subTest(host_base=host_base):
                profile = trace.psid_profile(data, subtune=1, profile='pal-banked', host_base=host_base)
                self.assertEqual(host_base, profile['hostBase'])
                program, labels = trace.harness(profile, 2)
                self.assertEqual(host_base.to_bytes(2, 'little'), program[:2])
                self.assertTrue(all(host_base <= address < host_base + 0x100 for address in labels.values()))
                self.assertIn((host_base + 0x100).to_bytes(2, 'little'), program)
                commands = trace.monitor_commands(Path('/tmp/payload.prg'), Path('/tmp/harness.prg'), profile, labels, 0, 1)
                self.assertIn(f'r pc=${host_base:04x}', commands)
                self.assertIn(f'@ram:${host_base + 0x100:04x}', commands)
                self.assertIn(f'@ram:${host_base + 0x101:04x}', commands)
                self.assertIn(f'@ram:${host_base + 0x102:04x}', commands)
                self.assertLess(commands.index('fill $0002 $cfff $00'), commands.index('load "/tmp/payload.prg"'))
                self.assertLess(commands.index('fill $e000 $ffff $00'), commands.index('load "/tmp/payload.prg"'))
    def test_host_placement_rejects_default_collision_invalid_bases_and_strict_override(self):
        with self.assertRaisesRegex(ValueError, 'host'):
            trace.psid_profile(high_ram_fixture(), subtune=1, profile='pal-banked')
        with self.assertRaises(ValueError):
            trace.psid_profile(sid_fixture(), host_base=0x0400)
        for host_base in (True, 0x0300, 0x0401, 0x9f00, 0xa000, 0xc000, 1.0, '0x400'):
            with self.subTest(host_base=host_base), self.assertRaises(ValueError):
                trace.psid_profile(high_ram_fixture(), subtune=1, profile='pal-banked', host_base=host_base)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sid, oracle = root / 'fixture.sid', root / 'oracle.json'
            sid.write_bytes(high_ram_fixture())
            oracle.write_text('[]')
            output = root / 'trace'
            with patch.object(trace.subprocess, 'run') as runner, self.assertRaisesRegex(ValueError, 'host'):
                trace.run_trace(sid, oracle, output, 0, 1, Path('/tmp/vice'), Path('/tmp/data'),
                                subtune=1, profile='pal-banked')
            runner.assert_not_called()
            self.assertFalse(output.exists())

    def test_cli_host_base_accepts_base_zero_integer_and_forwards_it(self):
        arguments = ['trace-sid-vice.py', 'fixture.sid', '--oracle', 'oracle.json', '--output', 'fresh',
                     '--profile', 'pal-banked', '--subtune', '1', '--host-base', '0x0400']
        with patch.object(sys, 'argv', arguments), patch.object(trace, 'run_trace', return_value={}) as runner:
            with patch('sys.stdout', new_callable=io.StringIO):
                trace.main()
        self.assertEqual(0x0400, runner.call_args.kwargs['host_base'])

    def test_headless_high_ram_fixture_matches_host_return_bytes_and_hidden_ram_zeros(self):
        vice = ROOT / '.tools/vice-headless-3.9/build/src/x64sc'
        data_directory = Path('/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice')
        if not vice.is_file() or not data_directory.is_dir():
            self.skipTest('Local headless VICE and ROM data are required for the executed fixture')
        from psid_audit import audit_psid
        data = high_ram_fixture()
        for host_base in (0x0400, 0x9e00):
            with self.subTest(host_base=host_base), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                sid, expected = root / 'fixture.sid', root / 'oracle.json'
                sid.write_bytes(data)
                _, oracle = audit_psid(data, 2, subtune=1, profile='pal-banked', host_base=host_base)
                expected.write_text(json.dumps(oracle))
                result = trace.run_trace(sid, expected, root / 'trace', 0, 1, vice, data_directory,
                                         subtune=1, profile='pal-banked', host_base=host_base)
                self.assertEqual(15, result['verification']['matchedWrites'])
                self.assertEqual(host_base, result['profile']['hostBase'])
                labels = result['harnessLabels']
                init_return, play_return = labels['init_return'] - 1, labels['play_return'] - 1
                self.assertEqual([('init', None, 0xd400, init_return & 255),
                                  ('init', None, 0xd401, init_return >> 8)] +
                                 [('init', None, address, 0) for address in (0xd405, 0xd406, 0xd407)] +
                                 [('play', tick, address, value) for tick in range(2) for address, value in
                                  ((0xd402, play_return & 255), (0xd403, play_return >> 8),
                                   (0xd408, 0), (0xd409, 0), (0xd40a, 0))],
                                 [(row['phase'], row['tick'], row['address'], row['value']) for row in oracle])
                self.assertEqual(data, sid.read_bytes())

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

    def test_headless_play_internal_entries_keep_the_same_host_call(self):
        vice = ROOT / '.tools/vice-headless-3.9/build/src/x64sc'
        data_directory = Path('/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice')
        if not vice.is_file() or not data_directory.is_dir():
            self.skipTest('Local headless VICE and ROM data are required for the executed fixture')
        from psid_audit import audit_psid
        from sid_assembler import assemble
        sources = {
            'reinitialize': 'init:\nLDA #$33\nSTA $D400\nRTS\nplay:\nLDA #$11\nSTA $D402\nJSR init\nLDA #$22\nSTA $D403\nRTS',
            'nested-play': 'init:\nLDA #$00\nSTA $2000\nRTS\nplay:\nLDA $2000\nBNE leaf\nINC $2000\nJSR play\nDEC $2000\nleaf:\nLDA $2000\nSTA $D402\nRTS',
        }
        for kind, source in sources.items():
            for profile in ('strict', 'pal-banked'):
                with self.subTest(kind=kind, profile=profile), tempfile.TemporaryDirectory() as directory:
                    payload, labels, _ = assemble(source)
                    header = sid_fixture()[:124]
                    header[12:14] = labels['play'].to_bytes(2, 'big')
                    encoded = bytes(header) + payload
                    selection = {'subtune': 1} if profile == 'pal-banked' else {}
                    _, oracle = audit_psid(encoded, 3, profile=profile, **selection)
                    root = Path(directory)
                    sid, expected = root / 'fixture.sid', root / 'oracle.json'
                    sid.write_bytes(encoded)
                    expected.write_text(json.dumps(oracle))
                    result = trace.run_trace(sid, expected, root / 'trace', 0, 2, vice, data_directory,
                                             profile=profile, **selection)
                    self.assertEqual(3, result['verification']['playCalls'])
                    parsed = json.loads((root / 'trace/trace.json').read_text())
                    self.assertEqual(3, len(parsed['callMarkers']))
                    if kind == 'nested-play' or profile == 'pal-banked':
                        self.assertEqual([0, 1, 2], [row['tick'] for row in parsed['playInternalEntries']])

    def test_dual_pal_profile_declares_both_chips_and_traces_their_canonical_write_windows(self):
        data = sid_fixture()
        data[5], data[119], data[122] = 3, 0x54, 0x42
        profile = trace.psid_profile(data)
        self.assertEqual([0xd400, 0xd420], profile['sidBases'])
        _, labels = trace.harness(profile, 3)
        commands = trace.monitor_commands(Path('/tmp/payload.prg'), Path('/tmp/harness.prg'), profile, labels, 0, 2)
        self.assertIn('trace store $d400 $d41f if', commands)
        self.assertIn('trace store $d420 $d43f if', commands)
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

    def test_parser_records_every_port_in_each_declared_canonical_sid_window(self):
        for bases in ((0xd400,), (0xd400, 0xd420)):
            with self.subTest(bases=bases):
                addresses = [base + offset for base in bases for offset in range(32)]
                log = entry(100)
                for index, address in enumerate(addresses):
                    log += store(116 + index * 4, index, f'8D {address & 255:02X} {address >> 8:02X}',
                                 f'STA ${address:04X}', address=address)
                parsed = trace.parse_trace(log, 0x1006, bases)
                self.assertEqual([(address, index) for index, address in enumerate(addresses)],
                                 [(row['address'], row['value']) for row in parsed['writes']])
                self.assertTrue(all(row['writerPc'] == 0x100c for row in parsed['writes']))

    def test_parser_rejects_undeclared_adjacent_and_mirrored_sid_stores(self):
        for bases, addresses in (((0xd400,), (0xd3ff, 0xd420, 0xd43f, 0xd440, 0xd500)),
                                 ((0xd400, 0xd420), (0xd3ff, 0xd440, 0xd500))):
            for address in addresses:
                with self.subTest(bases=bases, address=address), self.assertRaisesRegex(ValueError, 'address'):
                    log = entry(100) + store(116, 7, f'8D {address & 255:02X} {address >> 8:02X}',
                                             f'STA ${address:04X}', address=address)
                    trace.parse_trace(log, 0x1006, bases)

    def test_extended_window_stores_keep_index_source_address_and_non_rmw_guards(self):
        cases = [
            ('9D 18 D4', 'STA $D418,X', 0xd419, 1, 0, 0x19),
            ('99 18 D4', 'STA $D418,Y', 0xd41c, 0, 4, 0x19),
            ('8E 1F D4', 'STX $D41F', 0xd41f, 0x7e, 0, 0x7e),
            ('8C 3F D4', 'STY $D43F', 0xd43f, 0, 0x6b, 0x6b),
        ]
        for opcode, mnemonic, address, x, y, expected in cases:
            with self.subTest(instruction=mnemonic):
                parsed = trace.parse_trace(entry(100) + store(116, 0x19, opcode, mnemonic,
                                           address=address, x=x, y=y), 0x1006, (0xd400, 0xd420))
                self.assertEqual((address, expected), (parsed['writes'][0]['address'], parsed['writes'][0]['value']))
        invalid = [
            store(116, opcode='EE 19 D4', mnemonic='INC $D419', address=0xd419),
            store(116, opcode='8D 18 D4', mnemonic='STA $D418', address=0xd419),
            store(116, opcode='9D 3F D4', mnemonic='STA $D43F,X', address=0xd440, x=1),
        ]
        for record in invalid:
            with self.subTest(record=record), self.assertRaises(ValueError):
                trace.parse_trace(entry(100) + record, 0x1006, (0xd400, 0xd420))

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
        pairs += [(base + offset, value) for base in (0xd400, 0xd420)
                  for offset, value in ((0x19, 0x31), (0x1c, 0xa5), (0x1f, 0x5c))]
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
            self.assertEqual(48, result['verification']['matchedWrites'])
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
        self.assertIn('trace store $d400 $d41f if', commands)
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
        data = sid_fixture()[:130] + bytes.fromhex('ee0020ad00208d02d4a9e78d03d4a9318d19d4a9a58d1cd4a95c8d1fd4a99960')
        oracle = [dict(phase='play', tick=tick, address=address, value=value) for tick in range(3)
                  for address, value in ((0xd402, tick + 1), (0xd403, 0xe7), (0xd419, 0x31),
                                         (0xd41c, 0xa5), (0xd41f, 0x5c))]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sid, expected = root / 'fixture.sid', root / 'oracle.json'
            sid.write_bytes(data)
            expected.write_text(json.dumps(oracle))
            result = trace.run_trace(sid, expected, root / 'trace', 0, 2, vice, data_directory)
            parsed = json.loads((root / 'trace/trace.json').read_text())
            self.assertEqual(result['verification']['matchedWrites'], 15)
            self.assertEqual([(row['writerPc'], row['registers']['a']) for row in parsed['writes']],
                             [(pc, value) for tick in range(3) for pc, value in
                              ((0x100c, tick + 1), (0x1011, 0xe7), (0x1016, 0x31),
                               (0x101b, 0xa5), (0x1020, 0x5c))])
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
