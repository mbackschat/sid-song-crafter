import importlib.util
from pathlib import Path
import sys
import unittest


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
