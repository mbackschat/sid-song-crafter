import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sidwizard_export", ROOT / "scripts/export-sidwizard.py")
EXPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORTER)


def original_module():
    header = bytearray(64)
    header[:4] = b"SWM1"
    header[4] = 1
    header[11:15] = bytes([8, 3, 1, 1])
    header[19] = 3
    header[24:64] = b"TEST:ORIGINAL EXPORT FIXTURE".ljust(40, b" ")
    sequence = bytes([1, 0xfe, 2])
    pattern = bytes([0x80 | 37, 1, 0, 0, 0x7e, 0, 0, 0, 0, 10, 8])
    parameters = bytes([0x12, 0x0f, 0, 0x09, 0xa8, 0, 0, 0, 0, 0, 20, 21, 0, 0, 0, 0x09])
    instrument = parameters + bytes([0x21, 0, 0, 0xff, 0xff, 21]) + b"TESTSAW "
    return b"\x33\x33" + header + sequence * 3 + pattern + instrument + bytes([0x86, 0x83])


class SIDWizardExportTest(unittest.TestCase):
    def test_accepts_original_native_module_and_keeps_instrument_name(self):
        summary = EXPORTER.inspect_module(original_module())
        self.assertEqual(summary["instruments"], [{"name": "TESTSAW", "size": 22}])
        self.assertEqual(summary["patterns"], 1)

    def test_rejects_unsupported_schedule_and_variant(self):
        for offset, value, message in [(6, 2, "1x"), (21, 0, "Extra"), (14, 6, "one subtune")]:
            data = bytearray(original_module())
            data[offset] = value
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError, message):
                EXPORTER.inspect_module(bytes(data))

    def test_rejects_truncated_native_table_before_cpu_execution(self):
        with self.assertRaisesRegex(ValueError, "structure"):
            EXPORTER.inspect_module(original_module()[:-12])

    def test_rejects_references_outside_the_saved_native_patterns_and_instruments(self):
        for offset, value, message in [(66, 2, "pattern reference"), (76, 2, "instrument reference")]:
            data = bytearray(original_module())
            data[offset] = value
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError, message):
                EXPORTER.inspect_module(bytes(data))

    def test_refuses_output_collision_without_changing_the_native_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "original.sid"
            source.write_bytes(original_module())
            with self.assertRaisesRegex(ValueError, "overwrite"):
                EXPORTER.export_module(source, Path(directory))
            self.assertEqual(source.read_bytes(), original_module())

    def test_refuses_changed_output_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "original.swm"
            source.write_bytes(original_module())
            report = EXPORTER.export_module(source, Path(directory) / "out", title="First")
            saved = Path(report["sid"]).read_bytes()
            with self.assertRaisesRegex(ValueError, "fresh output directory"):
                EXPORTER.export_module(source, Path(directory) / "out", title="Changed")
            self.assertEqual(Path(report["sid"]).read_bytes(), saved)

    def test_exports_native_extra_bytes_and_standalone_starter_deterministically(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            source = output / "original.swm"
            source.write_bytes(original_module())
            first = EXPORTER.export_module(source, output / "first", title="Original", author="Test", released="2026")
            second = EXPORTER.export_module(source, output / "second", title="Original", author="Test", released="2026")
            sid = Path(first["sid"]).read_bytes()
            prg = Path(first["prg"]).read_bytes()
            self.assertEqual(sid, Path(second["sid"]).read_bytes())
            self.assertEqual(prg, Path(second["prg"]).read_bytes())
            self.assertEqual(sid[:8], b"PSID\x00\x02\x00\x7c")
            self.assertEqual(sid[10:14], b"\x10\x00\x10\x03")
            self.assertEqual(sid[18:22], b"\x00" * 4)
            self.assertEqual(sid[118:120], b"\x00\x24")
            self.assertEqual(sid[124:126], b"\x00\x10")
            self.assertEqual(prg[:2], b"\x01\x08")
            self.assertEqual(prg[6], 0x9e)
            table = original_module()[-32:-2]
            self.assertIn(table[:21] + b"\xff", sid)
            self.assertEqual(source.read_bytes(), original_module())
            self.assertEqual(first["player"], "Extra")


if __name__ == "__main__":
    unittest.main()
