import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("psid_audit", ROOT / "scripts/psid_audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def sid_file(play=bytes((0xee, 0x00, 0x20, 0xad, 0x00, 0x20, 0x8d, 0x02, 0xd4, 0x60))):
    header = bytearray(0x7c)
    header[:4] = b"PSID"
    for offset, value in ((4, 2), (6, 0x7c), (8, 0x1000), (10, 0x1000), (12, 0x1006), (14, 1), (16, 1), (118, 0x24)):
        header[offset:offset + 2] = value.to_bytes(2, "big")
    return header + bytes((0xa9, 0x0f, 0x8d, 0x18, 0xd4, 0x60)) + play


class PsidAuditTest(unittest.TestCase):
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
        for address in (0xd419, 0xd41f, 0xd439, 0xd440):
            data = sid_file(bytes((0xa9, 1, 0x8d, address & 255, address >> 8, 0x60)))
            data[5], data[119], data[122] = 3, 0xa4, 0x42
            with self.subTest(address=address), self.assertRaisesRegex(ValueError, 'I/O write'):
                audit.audit_psid(data, 1)
        data = sid_file(bytes((0xad, 0x3b, 0xd4, 0x60)))
        data[5], data[119], data[122] = 3, 0xa4, 0x42
        with self.assertRaisesRegex(ValueError, 'I/O read'):
            audit.audit_psid(data, 1)

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


if __name__ == "__main__":
    unittest.main()
