import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from sid_assembler import assemble
spec = importlib.util.spec_from_file_location("psid_audit", ROOT / "scripts/psid_audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def sid_file(play=bytes((0xee, 0x00, 0x20, 0xad, 0x00, 0x20, 0x8d, 0x02, 0xd4, 0x60))):
    header = bytearray(0x7c)
    header[:4] = b"PSID"
    for offset, value in ((4, 2), (6, 0x7c), (8, 0x1000), (10, 0x1000), (12, 0x1006), (14, 1), (16, 1), (118, 0x24)):
        header[offset:offset + 2] = value.to_bytes(2, "big")
    return header + bytes((0xa9, 0x0f, 0x8d, 0x18, 0xd4, 0x60)) + play


def selected_fixture(init='STA $D402\nRTS', play='RTS', *, load=0xa600, songs=2, default=1, dual=False):
    # sid_assembler supports the old RAM range; these fixtures have only relative branches and external absolute operands.
    code, symbols, _ = assemble(f'init:\n{init}\nplay:\n{play}\n')
    symbols = {name: address - 0x1000 + load for name, address in symbols.items()}
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 3 if dual else 2), (6, 124), (8, load), (10, symbols['init']),
                          (12, symbols['play']), (14, songs), (16, default), (118, 0x54 if dual else 0x14)):
        header[offset:offset + 2] = value.to_bytes(2, 'big')
    if dual:
        header[122] = 0x42
    return bytes(header) + code


def ntsc_fixture(play='RTS', *, dual=False, model='MOS6581'):
    data = bytearray(selected_fixture(play=play, load=0x1000, songs=1, dual=dual))
    flags = {'MOS6581': 0x58, 'MOS8580': 0xa8} if dual else {'MOS6581': 0x18, 'MOS8580': 0x28}
    data[118:120] = flags[model].to_bytes(2, 'big')
    return bytes(data)


class PsidAuditTest(unittest.TestCase):
    def test_explicit_ntsc_accepts_only_declared_single_and_same_model_dual_sid(self):
        from psid_profile import psid_profile
        for dual in (False, True):
            bases = (0xd400, 0xd420) if dual else (0xd400,)
            play = '\n'.join(f'LDA #$51\nSTA ${base + 4:04X}' for base in bases) + '\nRTS'
            for model in ('MOS6581', 'MOS8580'):
                with self.subTest(dual=dual, model=model):
                    data = ntsc_fixture(play, dual=dual, model=model)
                    parsed = psid_profile(data, clock='ntsc')
                    self.assertEqual(list(bases), parsed['sidBases'])
                    report, writes = audit.audit_psid(data, 2, clock='ntsc')
                    self.assertEqual([{'baseAddress': base, 'model': model} for base in bases], report['sids'])
                    self.assertEqual(14318181.82 / 14, report['clockHz'])
                    self.assertEqual(17095, report['frameCycleBudget'])
                    self.assertEqual((14318181.82 / 14) / 17095, report['callRateHz'])
                    self.assertEqual([(base + 4, 0x51) for base in bases],
                                     [(row['address'], row['value']) for row in writes if row['tick'] == 1])
                    self.assertEqual(data, ntsc_fixture(play, dual=dual, model=model))

    def test_explicit_target_rejects_mismatched_unknown_both_and_mixed_sid_headers(self):
        from psid_profile import psid_profile
        for dual in (False, True):
            for clock, flags in (('pal', (0x58, 0xa8) if dual else (0x18, 0x28)),
                                 ('ntsc', (0x50, 0x54, 0x5c, 0x68, 0x98) if dual else (0x08, 0x14, 0x1c, 0x38))):
                for flag in flags:
                    data = bytearray(ntsc_fixture(dual=dual))
                    data[118:120] = flag.to_bytes(2, 'big')
                    with self.subTest(dual=dual, clock=clock, flag=flag):
                        with self.assertRaises(ValueError):
                            psid_profile(data, clock=clock)
                        with self.assertRaises(ValueError):
                            audit.audit_psid(data, 1, clock=clock)
            with self.subTest(default_clock_dual=dual), self.assertRaises(ValueError):
                audit.audit_psid(ntsc_fixture(dual=dual), 1)

    def test_ntsc_does_not_expand_callable_ram_single_subtune_or_model_assumption_contracts(self):
        mutations = ((21, 1), (15, 2), (17, 2), (12, 0), (13, 0xff), (122, 0x44), (123, 0x42))
        for offset, value in mutations:
            data = bytearray(ntsc_fixture())
            data[offset] = value
            with self.subTest(offset=offset, value=value), self.assertRaises(ValueError):
                audit.audit_psid(data, 1, clock='ntsc')
        data = bytearray(ntsc_fixture())
        data[8:10] = (0xa000).to_bytes(2, 'big')
        with self.assertRaisesRegex(ValueError, 'RAM'):
            audit.audit_psid(data, 1, clock='ntsc')
        for option in ({'host_base': 0x0400}, {'assume_sid_model': 'MOS6581'}, {'subtune': 2}):
            with self.subTest(option=option), self.assertRaises(ValueError):
                audit.audit_psid(ntsc_fixture(), 1, clock='ntsc', **option)
        for data in (selected_fixture(load=0x1000, songs=1), ntsc_fixture()):
            with self.subTest(banked_source_flags=data[119]), self.assertRaisesRegex(ValueError, 'PAL'):
                audit.audit_psid(data, 1, profile='pal-banked', subtune=1, clock='ntsc')
        for clock in ('NTSC', 'auto', None, 1, True):
            with self.subTest(clock=clock), self.assertRaises(ValueError):
                audit.audit_psid(ntsc_fixture(), 1, clock=clock)

    def test_ntsc_retains_the_io_rom_and_mapping_guards(self):
        for play, message in (('LDA $D41B\nRTS', 'I/O read'), ('STA $DC04\nRTS', 'I/O write'),
                              ('LDA $A000\nRTS', 'ROM read'), ('LDA #$34\nSTA $01\nRTS', 'hide SID I/O'),
                              ('INC $D404\nRTS', 'I/O read')):
            with self.subTest(play=play), self.assertRaisesRegex(ValueError, message):
                audit.audit_psid(ntsc_fixture(play), 1, clock='ntsc')

    def test_ntsc_call_budget_accepts_the_final_cycle_and_rejects_a_pal_only_driver(self):
        exact_budget = sid_file(bytes((0x24, 0x20)) + b'\xea' * 8543 + b'\x60')
        exact_budget[119] = 0x28
        report, _ = audit.audit_psid(exact_budget, 1, clock='ntsc')
        self.assertEqual(17095, report['maximumPlayCycles'])
        pal_only = sid_file(b'\xea' * 8545 + b'\x60')
        report, _ = audit.audit_psid(pal_only, 1)
        self.assertEqual(17096, report['maximumPlayCycles'])
        pal_only[119] = 0x28
        with self.assertRaisesRegex(ValueError, '17095-cycle call budget'):
            audit.audit_psid(pal_only, 1, clock='ntsc')

    def test_pal_evidence_bytes_remain_compatible_with_both_legacy_profiles(self):
        for profile, expected in (('strict', '7420eca9f621528837161591b55590d5f544a4a0ce46a0fab9cb4f44269c5863'),
                                  ('pal-banked', '6a52aa19dc7f190c795d14e9d1f1bdd89a33977fcf9bbde7091f53cf44800fa0')):
            with self.subTest(profile=profile):
                data = selected_fixture(load=0x1000, songs=1)
                report, writes = audit.audit_psid(data, 3, profile=profile, subtune=1)
                self.assertEqual(expected, hashlib.sha256((json.dumps(report, indent=2) + '\n').encode()).hexdigest())
                self.assertEqual('81a7da336f02750f40cde112e750186cf07dd262d51eeef6240ca854b860f40f',
                                 hashlib.sha256((json.dumps(writes, separators=(',', ':')) + '\n').encode()).hexdigest())
                self.assertEqual((report, writes), audit.audit_psid(data, 3, profile=profile, subtune=1, clock='pal'))

    def test_ntsc_cli_writes_target_timing_evidence_and_preserves_input(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / 'ntsc.sid', Path(directory) / 'audit.json'
            data = ntsc_fixture()
            source.write_bytes(data)
            argv = ['psid_audit.py', str(source), '--ticks', '2', '--clock', 'ntsc', '--output', str(output)]
            with patch.object(sys, 'argv', argv), patch('builtins.print') as printed:
                audit.main()
            report = json.loads(output.read_text())
            self.assertEqual(data, source.read_bytes())
            self.assertEqual(17095, report['frameCycleBudget'])
            self.assertEqual(14318181.82 / 14, report['clockHz'])
            self.assertIn('/17095 cycles', printed.call_args.args[0])

    def test_dual_6581_declaration_keeps_both_models_and_the_same_cpu_evidence(self):
        data = sid_file(bytes((0xa9, 0x51, 0x8d, 0x24, 0xd4, 0x60)))
        data[5], data[119], data[122] = 3, 0xa4, 0x42
        _, expected_writes = audit.audit_psid(data, 2)
        data[119] = 0x54
        report, writes = audit.audit_psid(data, 2)
        self.assertEqual(report["sids"], [{"baseAddress": base, "model": "MOS6581"} for base in (0xd400, 0xd420)])
        self.assertEqual(report["sidModel"], "MOS6581")
        self.assertEqual(writes, expected_writes)

    def test_dual_sid_audit_keeps_both_register_banks_and_one_shared_frame_budget(self):
        data = sid_file(bytes((0xa9, 0x27, 0x8d, 0x04, 0xd4, 0xa9, 0x51, 0x8d, 0x24, 0xd4, 0xa9, 0x1f, 0x8d, 0x38, 0xd4, 0x60)))
        data[5], data[119], data[122] = 3, 0xa4, 0x42
        report, writes = audit.audit_psid(data, 2)
        self.assertEqual(report['sidCount'], 2)
        self.assertEqual(report['sids'], [{'baseAddress': 0xd400, 'model': 'MOS8580'}, {'baseAddress': 0xd420, 'model': 'MOS8580'}])
        self.assertEqual(report['sidModel'], 'MOS8580')
        self.assertEqual(report['frameCycleBudget'], 19656)
        self.assertEqual(report['maximumPlayCycles'], 24)
        self.assertEqual([(row['address'], row['value']) for row in writes if row['tick'] == 1], [(0xd404, 0x27), (0xd424, 0x51), (0xd438, 0x1f)])

    def test_dual_sid_rejects_ambiguous_metadata_reads_and_unconfigured_registers(self):
        original = sid_file()
        original[5], original[119], original[122] = 3, 0xa4, 0x42
        for offset, value in ((5, 4), (119, 0x64), (119, 0xa8), (122, 0x44), (123, 0x44), (21, 1)):
            data = bytearray(original)
            data[offset] = value
            with self.subTest(offset=offset, value=value), self.assertRaises(ValueError):
                audit.audit_psid(data, 1)
        for address in (0xd3ff, 0xd440, 0xd500, 0xdc04):
            data = sid_file(bytes((0xa9, 1, 0x8d, address & 255, address >> 8, 0x60)))
            data[5], data[119], data[122] = 3, 0xa4, 0x42
            with self.subTest(address=address), self.assertRaisesRegex(ValueError, 'I/O write'):
                audit.audit_psid(data, 1)
        data = sid_file(bytes((0xad, 0x3b, 0xd4, 0x60)))
        data[5], data[119], data[122] = 3, 0xa4, 0x42
        with self.assertRaisesRegex(ValueError, 'I/O read'):
            audit.audit_psid(data, 1)

    def test_declared_sid_windows_capture_read_only_unused_and_repeated_init_play_stores(self):
        for dual in (False, True):
            bases = (0xd400, 0xd420) if dual else (0xd400,)
            init_stores = [(base + offset, value) for base in bases for offset, value in ((31, 0x13), (25, 0x79))]
            play_stores = [(base + offset, value) for base in bases for offset, value in
                           ((25, 0x21), (28, 0x9a), (31, 0x34), (25, 0x21))]
            init = '\n'.join(f'LDA #${value:02X}\nSTA ${address:04X}' for address, value in init_stores) + '\nRTS'
            play = '\n'.join(f'LDA #${value:02X}\nSTA ${address:04X}' for address, value in play_stores) + '\nRTS'
            data = selected_fixture(init, play, load=0x1000, songs=1, dual=dual)
            expected = [('init', None, address, value) for address, value in init_stores]
            expected += [('play', tick, address, value) for tick in range(2) for address, value in play_stores]
            for profile in ('strict', 'pal-banked'):
                with self.subTest(dual=dual, profile=profile):
                    report, writes = audit.audit_psid(data, 2, profile=profile, subtune=1)
                    self.assertEqual(expected, [(row['phase'], row['tick'], row['address'], row['value']) for row in writes])
                    self.assertEqual((len(init_stores), 2 * len(play_stores)),
                                     (report['initWriteCount'], report['playWriteCount']))
                    for base in bases:
                        self.assertEqual(4, report['registers'][f'{base + 25:04x}']['writes'])
                        self.assertEqual(1, report['registers'][f'{base + 25:04x}']['distinctValues'])
                    self.assertIn('32-byte', report['limitations'])
                    self.assertIn('read-only/unused', report['limitations'])
                    self.assertIn('bus behavior', report['limitations'])
                    self.assertIn('SID reads', report['limitations'])

    def test_declared_sid_windows_still_reject_outside_ports_mirrors_and_non_sid_io(self):
        for dual in (False, True):
            for profile in ('strict', 'pal-banked'):
                for address in (0xd3ff, 0xd440 if dual else 0xd420, 0xd500, 0xdc04):
                    with self.subTest(dual=dual, profile=profile, address=address), self.assertRaisesRegex(ValueError, 'I/O write'):
                        data = selected_fixture(play=f'STA ${address:04X}\nRTS', load=0x1000, songs=1, dual=dual)
                        audit.audit_psid(data, 1, profile=profile, subtune=1)

    def test_declared_read_only_and_unused_sid_ports_do_not_fabricate_read_values(self):
        for dual in (False, True):
            bases = (0xd400, 0xd420) if dual else (0xd400,)
            for profile in ('strict', 'pal-banked'):
                for base in bases:
                    for offset in (25, 28, 31):
                        with self.subTest(dual=dual, profile=profile, address=base + offset), self.assertRaisesRegex(ValueError, 'I/O read'):
                            data = selected_fixture(play=f'LDA ${base + offset:04X}\nRTS', load=0x1000, songs=1, dual=dual)
                            audit.audit_psid(data, 1, profile=profile, subtune=1)

    def test_all_sid_rmw_modes_remain_rejected_on_read_only_unused_and_sound_ports(self):
        for address in (0xd404, 0xd419, 0xd41c, 0xd41f, 0xd424, 0xd439, 0xd43c, 0xd43f):
            for instruction in ('ASL', 'LSR', 'ROL', 'ROR', 'INC', 'DEC'):
                with self.subTest(address=address, instruction=instruction), self.assertRaisesRegex(ValueError, 'I/O read'):
                    data = selected_fixture(play=f'{instruction} ${address:04X}\nRTS', load=0x1000, songs=1, dual=True)
                    audit.audit_psid(data, 1)
        memory = audit.AuditMemory((0xd400, 0xd420))
        for address in (0xd404, 0xd41f, 0xd424, 0xd43f):
            for instruction in ('ASL', 'LSR', 'ROL', 'ROR', 'INC', 'DEC'):
                memory.instruction = instruction
                with self.subTest(direct_address=address, instruction=instruction), self.assertRaisesRegex(ValueError, 'read-modify-write'):
                    memory[address] = 1
        self.assertEqual([], memory.writes)

    def test_audits_a_driver_without_our_exporter_symbols_or_score(self):
        report, writes = audit.audit_psid(sid_file(), 3)
        self.assertEqual(report["playCalls"], 3)
        self.assertEqual(report["maximumPlayCycles"], 20)
        self.assertEqual(report["initCycles"], 12)
        self.assertEqual([(row["phase"], row["tick"], row["address"], row["value"]) for row in writes], [
            ("init", None, 0xd418, 15), ("play", 0, 0xd402, 1), ("play", 1, 0xd402, 2), ("play", 2, 0xd402, 3),
        ])
        self.assertEqual(report["registers"]["d402"]["distinctValues"], 3)
        self.assertEqual(report["sidModel"], "MOS8580")

    def test_embedded_load_address_and_zero_init_are_supported(self):
        data = sid_file()
        data[8:12] = bytes(4)
        data[0x7c:0x7c] = b"\x00\x10"
        report, _ = audit.audit_psid(data, 1)
        self.assertEqual(report["loadAddress"], 0x1000)
        self.assertEqual(report["initAddress"], 0x1000)

    def test_read_only_instruction_observer_sees_init_and_each_play_call_without_changing_the_audit(self):
        observed = []

        def observer(cpu, memory):
            observed.append((memory.phase, memory.tick, cpu.pc, memory.data[0x2000], memory.instruction_cycle))

        expected_report, expected_writes = audit.audit_psid(sid_file(), 3)
        report, writes = audit.audit_psid(sid_file(), 3, observer=observer)
        self.assertEqual(report, expected_report)
        self.assertEqual(writes, expected_writes)
        self.assertEqual(observed[0], ("init", None, 0x1000, 0, 0))
        self.assertEqual([row for row in observed if row[2] == 0x1006], [("play", 0, 0x1006, 0, 0), ("play", 1, 0x1006, 1, 0), ("play", 2, 0x1006, 2, 0)])
        self.assertIn(("play", 0, 0x1009, 1, 6), observed)

    def test_rejects_other_timing_machine_and_format_contracts(self):
        for name, mutate in [
            ("RSID", lambda data: data.__setitem__(slice(0, 4), b"RSID")),
            ("CIA", lambda data: data.__setitem__(21, 1)),
            ("NTSC", lambda data: data.__setitem__(119, 0x28)),
            ("multi-SID", lambda data: data.__setitem__(122, 0x42)),
            ("IRQ", lambda data: data.__setitem__(slice(12, 14), bytes(2))),
        ]:
            with self.subTest(name=name):
                data = sid_file()
                mutate(data)
                with self.assertRaises(ValueError):
                    audit.audit_psid(data, 1)

    def test_rejects_io_reads_and_hardware_access_instead_of_fabricating_values(self):
        for program in (bytes((0xad, 0x1b, 0xd4, 0x60)), bytes((0xa9, 1, 0x8d, 4, 0xdc, 0x60))):
            with self.subTest(program=program):
                with self.assertRaisesRegex(ValueError, "I/O"):
                    audit.audit_psid(sid_file(program), 1)

    def test_cpu_banking_keeps_sid_visible_and_mapping_bits_as_outputs(self):
        for program, message in (
            (bytes((0xa9, 0x34, 0x85, 0x01, 0x60)), "hide SID I/O"),
            (bytes((0xa9, 0x28, 0x85, 0x00, 0x60)), "mapping bits as outputs"),
        ):
            with self.subTest(program=program), self.assertRaisesRegex(ValueError, message):
                audit.audit_psid(sid_file(program), 1)

    def test_disabling_roms_allows_underlying_ram_reads_while_sid_remains_visible(self):
        program = bytes((0xa9, 0x35, 0x85, 0x01, 0xad, 0x00, 0xa0, 0x8d, 0x02, 0xd4, 0xad, 0x00, 0xe0, 0x8d, 0x03, 0xd4, 0x60))
        report, writes = audit.audit_psid(sid_file(program), 1)
        self.assertEqual(report["playWriteCount"], 2)
        self.assertEqual([(row["address"], row["value"]) for row in writes if row["phase"] == "play"], [(0xd402, 0), (0xd403, 0)])

    def test_mapped_rom_reads_are_rejected(self):
        for address in (0xa000, 0xe000):
            with self.subTest(address=address), self.assertRaisesRegex(ValueError, "ROM read"):
                audit.audit_psid(sid_file(bytes((0xad, address & 255, address >> 8, 0x60))), 1)

    def test_cli_writes_both_evidence_files_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source, output = root / "fixture.sid", root / "fixture.audit.json"
            original = sid_file()
            source.write_bytes(original)
            with patch.object(sys, "argv", ["psid_audit.py", str(source), "--ticks", "3", "--output", str(output)]), patch("builtins.print"):
                audit.main()
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(json.loads(output.read_text())["playCalls"], 3)
            self.assertEqual(len(json.loads(output.with_suffix(".writes.json").read_text())), 4)

    def test_cli_preserves_evidence_created_after_the_output_preflight(self):
        for concurrent_name in ("fixture.audit.json", "fixture.audit.writes.json"):
            with self.subTest(concurrent_name=concurrent_name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                source, output = root / "fixture.sid", root / "fixture.audit.json"
                source.write_bytes(sid_file())
                concurrent_path = root / concurrent_name
                original_open = Path.open

                def concurrent_open(path, mode="r", *args, **kwargs):
                    if path == concurrent_path and mode in ("w", "x"):
                        with original_open(path, "w") as concurrent:
                            concurrent.write("keep concurrent evidence")
                    return original_open(path, mode, *args, **kwargs)

                with patch.object(sys, "argv", ["psid_audit.py", str(source), "--ticks", "1", "--output", str(output)]), patch.object(Path, "open", concurrent_open), patch("builtins.print"), self.assertRaises(FileExistsError):
                    audit.main()
                self.assertEqual(concurrent_path.read_text(), "keep concurrent evidence")
                other = output.with_suffix(".writes.json") if concurrent_path == output else output
                self.assertFalse(other.exists())

    def test_cli_removes_its_incomplete_evidence_when_companion_write_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source, output = root / "fixture.sid", root / "fixture.audit.json"
            writes = output.with_suffix(".writes.json")
            source.write_bytes(sid_file())
            original_open = Path.open

            def failed_open(path, mode="r", *args, **kwargs):
                if path == writes and mode in ("w", "x"):
                    raise OSError("companion unavailable")
                return original_open(path, mode, *args, **kwargs)

            with patch.object(sys, "argv", ["psid_audit.py", str(source), "--ticks", "1", "--output", str(output)]), patch.object(Path, "open", failed_open), self.assertRaisesRegex(OSError, "companion unavailable"):
                audit.main()
            self.assertFalse(output.exists())
            self.assertFalse(writes.exists())

    def test_rejects_unsupported_opcode_and_unbounded_driver(self):
        for program, message in ((b"\x02", "opcode"), (b"\x4c\x06\x10", "budget")):
            with self.subTest(program=program):
                with self.assertRaisesRegex(ValueError, message):
                    audit.audit_psid(sid_file(program), 1)

    def test_validates_header_bounds_and_argument_limits(self):
        for data, ticks in ((sid_file()[:30], 1), (sid_file(), 0), (sid_file(), 1.5), (sid_file(), 100001)):
            with self.subTest(ticks=ticks, size=len(data)):
                with self.assertRaises(ValueError):
                    audit.audit_psid(data, ticks)

    def test_banked_selection_keeps_the_two_song_header_and_passes_zero_based_init_a(self):
        data = selected_fixture()
        for selector in (1, 2):
            with self.subTest(selector=selector):
                report, writes = audit.audit_psid(data, 2, profile='pal-banked', subtune=selector)
                self.assertEqual([('init', None, 0xd402, selector - 1)],
                                 [(row['phase'], row['tick'], row['address'], row['value']) for row in writes])
                self.assertEqual((2, 1, selector, 'pal-banked', 0x36),
                                 (report['subtunes'], report['defaultSubtune'], report['selectedSubtune'],
                                  report['executionProfile'], report['entryBank']))
                self.assertEqual(data, selected_fixture())
        with self.assertRaisesRegex(ValueError, 'one subtune'):
            audit.audit_psid(data, 1)
        with self.assertRaisesRegex(ValueError, 'RAM'):
            audit.audit_psid(selected_fixture(songs=1), 1)

    def test_banked_selection_is_explicit_and_raw_header_counts_are_not_repaired(self):
        for selector in (None, 0, 3, True, 1.0, '1'):
            with self.subTest(selector=selector), self.assertRaises(ValueError):
                audit.audit_psid(selected_fixture(), 1, profile='pal-banked', subtune=selector)
        for songs, default in ((0, 1), (257, 1), (2, 0), (2, 3)):
            with self.subTest(songs=songs, default=default), self.assertRaises(ValueError):
                audit.audit_psid(selected_fixture(songs=songs, default=default), 1, profile='pal-banked', subtune=1)
        report, writes = audit.audit_psid(selected_fixture(songs=256, default=256), 1,
                                          profile='pal-banked', subtune=256)
        self.assertEqual((256, 256, 255), (report['selectedSubtune'], report['defaultSubtune'], writes[0]['value']))
        for selector in (0, 2, True, 1.0):
            with self.subTest(strict_selector=selector), self.assertRaises(ValueError):
                audit.audit_psid(sid_file(), 1, subtune=selector)
        with self.assertRaisesRegex(ValueError, 'profile'):
            audit.audit_psid(sid_file(), 1, profile='permissive')

    def test_banked_entry_matches_init_flags_and_the_raster_poll_accumulator_status_and_xy(self):
        init = ('STA $D402\nBNE invalid\nPHP\nPLA\nAND #$CF\nCMP #$06\nBNE invalid\n'
                'LDX #$12\nLDY #$34\nSED\nCLC\nLDA #$80\nRTS\ninvalid:\nBRK')
        play = ('STA $D403\nSTX $D404\nSTY $D405\nPHP\nPLA\nAND #$CF\nSTA $D406\n'
                'INX\nINY\nCLC\nCLD\nLDA #$80\nRTS')
        _, writes = audit.audit_psid(selected_fixture(init, play), 2, profile='pal-banked', subtune=2)
        self.assertEqual([(0, 0xfa), (0, 0x12), (0, 0x34), (0, 0x0f),
                          (1, 0xfa), (1, 0x13), (1, 0x35), (1, 0x07)],
                         [(row['tick'], row['value']) for row in writes if row['phase'] == 'play'])

    def test_strict_default_keeps_its_legacy_unwrapped_register_and_flag_entry(self):
        init = 'LDX #$12\nLDY #$34\nSED\nCLC\nLDA #$80\nRTS'
        play = 'STA $D403\nSTX $D404\nSTY $D405\nPHP\nPLA\nAND #$CF\nSTA $D406\nCLD\nRTS'
        data = selected_fixture(init, play, load=0x1000, songs=1)
        report, writes = audit.audit_psid(data, 1)
        self.assertEqual([0x80, 0x12, 0x34, 0x88], [row['value'] for row in writes])
        self.assertNotIn('executionProfile', report)
        self.assertEqual((report, writes), audit.audit_psid(data, 1, profile='strict', subtune=1))

    def test_banked_host_restores_basic_ram_before_every_call_without_resetting_player_ram(self):
        play = ('LDA $01\nSTA $D403\nLDA $A000\nSTA $D404\nINC $2000\nLDA $2000\nSTA $D405\n'
                'LDA #$37\nSTA $01\nRTS')
        entries = []
        def observe(cpu, memory):
            if memory.instruction_cycle == 0:
                entries.append((memory.phase, memory.tick, memory.data[1]))
        _, writes = audit.audit_psid(selected_fixture('LDA #$37\nSTA $01\nRTS', play, load=0x1000),
                                     3, profile='pal-banked', subtune=1, observer=observe)
        self.assertEqual([('init', None, 0x36), ('play', 0, 0x36), ('play', 1, 0x36), ('play', 2, 0x36)], entries)
        self.assertEqual([0x36, 0, 1, 0x36, 0, 2, 0x36, 0, 3], [row['value'] for row in writes])

    def test_banked_profile_keeps_io_rom_rmw_and_host_vector_guards(self):
        for instruction in ('LDA $D41B', 'LDA $E000', 'STA $DC04', 'INC $D404', 'LDA $C000', 'LDA $C1FF',
                            'STA $C000', 'STA $C1FF', 'STA $0314', 'STA $0319', 'LDA #$34\nSTA $01'):
            with self.subTest(instruction=instruction), self.assertRaises(ValueError):
                audit.audit_psid(selected_fixture(play=instruction+'\nRTS'), 1, profile='pal-banked', subtune=1)
        for offset, value in ((21, 1), (119, 0x18), (119, 0x34), (122, 0x42)):
            data = bytearray(selected_fixture())
            data[offset] = value
            with self.subTest(offset=offset, value=value), self.assertRaises(ValueError):
                audit.audit_psid(data, 1, profile='pal-banked', subtune=1)
        _, writes = audit.audit_psid(selected_fixture(play='STA $C200\nRTS'), 1, profile='pal-banked', subtune=1)
        self.assertEqual(1, len(writes))

    def test_shared_banked_parser_handles_dual_sid_and_upper_payload_boundary(self):
        from psid_profile import psid_profile
        data = selected_fixture(play='LDA #$41\nSTA $D404\nLDA #$51\nSTA $D424\nRTS', dual=True)
        profile = psid_profile(data, profile='pal-banked', subtune=2)
        self.assertEqual(([0xd400,0xd420], 1, 0x36), (profile['sidBases'], profile['initAccumulator'], profile['entryBank']))
        report, writes = audit.audit_psid(data, 1, profile='pal-banked', subtune=2)
        self.assertEqual(2, report['sidCount'])
        self.assertEqual([(0xd404,0x41),(0xd424,0x51)], [(row['address'],row['value']) for row in writes if row['phase']=='play'])
        boundary = bytearray(selected_fixture(load=0xbff0))
        boundary.extend(bytes(0xc000-(0xbff0+len(boundary)-124)))
        self.assertEqual(0xc000, psid_profile(boundary, profile='pal-banked', subtune=1)['endAddress'])
        with self.assertRaisesRegex(ValueError, 'RAM'):
            psid_profile(boundary+b'\0', profile='pal-banked', subtune=1)

    def test_banked_cli_writes_selected_evidence_without_changing_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root/'fixture.sid', root/'fixture.audit.json'
            data = selected_fixture()
            source.write_bytes(data)
            argv = ['psid_audit.py',str(source),'--ticks','2','--profile','pal-banked','--subtune','2','--output',str(output)]
            with patch.object(sys,'argv',argv), patch('builtins.print'):
                audit.main()
            self.assertEqual(data,source.read_bytes())
            self.assertEqual(2,json.loads(output.read_text())['selectedSubtune'])

    def test_shared_default_harness_bytes_preserve_both_legacy_profiles(self):
        import hashlib
        from psid_profile import psid_profile
        from sid_audit_host import harness
        for profile, expected in (('strict', '48b3e63e958a39ebb6681cfb5ff6076e0b450ed61988c53be4df73327dd42e4e'),
                                  ('pal-banked', 'e368514fc8b972af59d1e6ce5f4b03893aecd6e27297b7d872b595a44e47492a')):
            with self.subTest(profile=profile):
                parsed = psid_profile(selected_fixture(load=0x1000, songs=1), profile=profile, subtune=1)
                program, labels = harness(parsed, 1)
                self.assertEqual(expected, hashlib.sha256(program).hexdigest())
                for label in ('init_return', 'play_return'):
                    offset = labels[label] - 0xc000 + 2
                    self.assertEqual(0x20, program[offset - 3])

    def test_banked_init_and_play_stack_returns_match_the_shared_host_at_each_placement(self):
        from psid_profile import psid_profile
        from sid_audit_host import harness
        init = 'TSX\nLDA $0101,X\nSTA $D400\nLDA $0102,X\nSTA $D401\nRTS'
        play = 'TSX\nLDA $0101,X\nSTA $D407\nLDA $0102,X\nSTA $D408\nRTS'
        for host_base in (None, 0x0400, 0x9e00):
            with self.subTest(host_base=host_base):
                data = selected_fixture(init, play, load=0x1000 if host_base is None else 0xc000, songs=1)
                parsed = psid_profile(data, profile='pal-banked', subtune=1, host_base=host_base)
                _, labels = harness(parsed, 1)
                report, writes = audit.audit_psid(data, 2, profile='pal-banked', subtune=1, host_base=host_base)
                init_word, play_word = labels['init_return'] - 1, labels['play_return'] - 1
                expected = [('init', None, 0xd400, init_word & 255), ('init', None, 0xd401, init_word >> 8)]
                expected += [('play', tick, address, value) for tick in range(2) for address, value in
                             ((0xd407, play_word & 255), (0xd408, play_word >> 8))]
                self.assertEqual(expected, [(row['phase'], row['tick'], row['address'], row['value']) for row in writes])
                self.assertEqual(0xc000 if host_base is None else host_base, report['hostBase'])
                self.assertEqual((labels['init_return'], labels['play_return']),
                                 (report['initReturnAddress'], report['playReturnAddress']))
                self.assertIn('shared', report['entryStateBasis'])

    def test_banked_host_placement_rejects_invalid_explicit_values_and_strict_overrides(self):
        data = selected_fixture(load=0xc000, songs=1)
        with self.assertRaisesRegex(ValueError, 'host RAM'):
            audit.audit_psid(data, 1, profile='pal-banked', subtune=1)
        for base in (True, False, 0x0400 + 1, 0x0300, 0x9f00, 0xc000, -256, '0x0400', 1024.0):
            with self.subTest(host_base=base), self.assertRaises(ValueError):
                audit.audit_psid(data, 1, profile='pal-banked', subtune=1, host_base=base)
        for base in (0x0400, 0xc000, True):
            with self.subTest(strict_host_base=base), self.assertRaisesRegex(ValueError, 'host'):
                audit.audit_psid(sid_file(), 1, host_base=base)

    def test_strict_return_stack_retains_the_legacy_sentinel(self):
        code = 'TSX\nLDA $0101,X\nSTA $D400\nLDA $0102,X\nSTA $D401\nRTS'
        report, writes = audit.audit_psid(selected_fixture(code, code, load=0x1000, songs=1), 2)
        self.assertEqual([0xff, 0x01] * 3, [row['value'] for row in writes])
        self.assertNotIn('hostBase', report)
        self.assertNotIn('initReturnAddress', report)
        self.assertNotIn('playReturnAddress', report)

    def test_banked_payloads_touch_host_boundaries_without_overlapping_and_stop_before_io(self):
        from psid_profile import psid_profile
        before = bytearray(selected_fixture(load=0x0400, songs=1))
        before.extend(bytes(0x0600 - (0x0400 + len(before) - 124)))
        self.assertEqual(0x0600, psid_profile(before, profile='pal-banked', subtune=1, host_base=0x0600)['endAddress'])
        with self.assertRaisesRegex(ValueError, 'host RAM'):
            psid_profile(before + b'\0', profile='pal-banked', subtune=1, host_base=0x0600)
        after = selected_fixture(load=0x0600, songs=1)
        self.assertEqual(0x0600, psid_profile(after, profile='pal-banked', subtune=1, host_base=0x0400)['loadAddress'])
        with self.assertRaisesRegex(ValueError, 'host RAM'):
            psid_profile(selected_fixture(load=0x0500, songs=1), profile='pal-banked', subtune=1, host_base=0x0400)
        high = bytearray(selected_fixture(load=0xc000, songs=1))
        high.extend(bytes(0xd000 - (0xc000 + len(high) - 124)))
        self.assertEqual(0xd000, psid_profile(high, profile='pal-banked', subtune=1, host_base=0x0400)['endAddress'])
        with self.assertRaisesRegex(ValueError, 'RAM'):
            psid_profile(high + b'\0', profile='pal-banked', subtune=1, host_base=0x0400)

    def test_selected_host_workspace_guards_fetch_reads_writes_and_keeps_vectors_protected(self):
        for base in (0x0400, 0x9e00):
            for address in (base, base + 511):
                for instruction in ('LDA', 'STA', 'JMP'):
                    with self.subTest(host_base=base, address=address, instruction=instruction), self.assertRaisesRegex(ValueError, 'host RAM'):
                        data = selected_fixture(play=f'{instruction} ${address:04X}\nRTS', load=0xc000, songs=1)
                        audit.audit_psid(data, 1, profile='pal-banked', subtune=1, host_base=base)
            for address in (0x0314, 0x0319):
                with self.subTest(host_base=base, vector=address), self.assertRaisesRegex(ValueError, 'vector'):
                    data = selected_fixture(play=f'STA ${address:04X}\nRTS', load=0xc000, songs=1)
                    audit.audit_psid(data, 1, profile='pal-banked', subtune=1, host_base=base)
        init = 'LDA #$11\nSTA $C000\nLDA #$22\nSTA $C1FF\nRTS'
        play = 'LDA $C000\nSTA $D400\nLDA $C1FF\nSTA $D401\nSTA $03FF\nSTA $0600\nRTS'
        _, writes = audit.audit_psid(selected_fixture(init, play, load=0xc800, songs=1), 1,
                                     profile='pal-banked', subtune=1, host_base=0x0400)
        self.assertEqual([(0xd400, 0x11), (0xd401, 0x22)], [(row['address'], row['value']) for row in writes])

    def test_host_placement_cli_preserves_the_high_ram_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / 'high.sid', Path(directory) / 'audit.json'
            data = selected_fixture(load=0xc000, songs=1)
            source.write_bytes(data)
            argv = ['psid_audit.py', str(source), '--ticks', '2', '--profile', 'pal-banked', '--subtune', '1',
                    '--host-base', '0x0400', '--output', str(output)]
            with patch.object(sys, 'argv', argv), patch('builtins.print'):
                audit.main()
            self.assertEqual(data, source.read_bytes())
            self.assertEqual(0x0400, json.loads(output.read_text())['hostBase'])

    def test_real_cybernoid_archive_remains_unchanged_and_both_subtunes_are_callable(self):
        path = ROOT/'.local/research/cybernoid-ii/Cybernoid_II.sid'
        if not path.exists():
            self.skipTest('Optional Cybernoid II reference is not installed')
        import hashlib
        data = path.read_bytes()
        self.assertEqual('41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192',hashlib.sha256(data).hexdigest())
        for selector in (1,2):
            report,writes = audit.audit_psid(data,16,profile='pal-banked',subtune=selector)
            self.assertEqual((0xa600,0xa603),(report['initAddress'],report['playAddress']))
            self.assertGreater(report['initWriteCount'],0)
            self.assertGreater(report['playWriteCount'],0)
            self.assertEqual(data,path.read_bytes())


if __name__ == "__main__":
    unittest.main()
