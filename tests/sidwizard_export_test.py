import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from psid_audit import audit_psid
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


def sparse_native_module(rows):
    original = original_module()
    header = bytearray(original[:66])
    header[13] = rows
    body = bytearray((0x80 | 37, 1, 0))
    remaining = rows - 4
    while remaining:
        count = min(9, remaining)
        body.append(0 if count == 1 else 0x70 + count - 2)
        remaining -= count
    body.extend((0x7e, 0))
    pattern = body + bytes((rows + 2, rows))
    return bytes(header) + original[66:75] + pattern + original[-32:-2] + b"\x81\x81"


def stopped_native_module():
    original = original_module()
    header = bytearray(original[:66])
    header[13] = 5
    sequence = bytes((1, 0xa0, 0xfe, 3))
    pattern = bytes((0x80 | 37, 1, 0, 0, 0x7e, 0x7e, 7, 5))
    return bytes(header) + sequence * 3 + pattern + original[-32:-2] + b"\x81\x81"


def six_voice_native_module():
    header = bytearray(64)
    header[:4] = b"SWMS"
    header[4] = 1
    header[11:15] = bytes((8, 6, 6, 2))
    header[19] = 3
    header[21] = 4
    header[24:64] = b"TEST:ORIGINAL SIX VOICE FIXTURE".ljust(40, b" ")
    sequences = b"".join(bytes((index + 1, 0xa0, 0xfe, 3)) for index in range(6))
    patterns = b"".join(bytes((note | 0x80, 1 if index < 3 else 2, 0, 0, 0, 0x7e, 0, 0, 0x7e, 10, 8)) for index, note in enumerate((49, 53, 56, 61, 65, 68)))
    instruments = []
    for cutoff, name in ((0x24, b"LEFTFILT"), (0x78, b"RGHTFILT")):
        parameters = bytes((0x0a, 0x0f, 0, 0x09, 0xa8, 0, 0, 0, 0, 0, 20, 21, 0, 0, 0, 0x09))
        instruments.append(parameters + bytes((0x11, 0, 0, 0xff, 0xff, 0x93, cutoff, 0, 24)) + name)
    return b"\x33\x33" + header + sequences + patterns + b"".join(instruments) + b"\x81\x81"


class SIDWizardExportTest(unittest.TestCase):
    def test_accepts_six_voice_native_stereo_module_and_rejects_other_addresses_or_counts(self):
        data = six_voice_native_module()
        summary = EXPORTER.inspect_module(data)
        self.assertEqual((summary["sidCount"], summary["sequences"], summary["patterns"]), (2, 6, 6))
        for offset, value, message in ((24, 1, "D420"), (14, 3, "one subtune"), (16, 30, "instrument count"), (15, 106, "pattern")):
            bad = bytearray(data)
            bad[offset] = value
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError, message):
                EXPORTER.inspect_module(bytes(bad))

    def test_two_sid_extra_export_executes_six_distinct_pitches_and_independent_filters(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "six-voices.sws"
            original = six_voice_native_module()
            source.write_bytes(original)
            report = EXPORTER.export_module(source, Path(directory) / "out")
            sid = Path(report["sid"]).read_bytes()
            self.assertEqual(sid[:8], b"PSID\x00\x03\x00\x7c")
            self.assertEqual(sid[118:124], b"\x00\xa4\x00\x00\x42\x00")
            self.assertEqual(report["sidCount"], 2)
            self.assertEqual(report["sids"], [{"baseAddress": 0xd400, "model": "MOS8580"}, {"baseAddress": 0xd420, "model": "MOS8580"}])
            self.assertEqual(report["build"]["sidCount"], 2)
            _, writes = audit_psid(sid, 12)
            values = {(row["tick"], row["address"]): row["value"] for row in writes if row["phase"] == "play"}
            words = []
            for voice in range(6):
                base = (0xd400 if voice < 3 else 0xd420) + voice % 3 * 7
                words.append(values[1, base] + 256 * values[1, base + 1])
                self.assertEqual(values[1, base + 4], 0x11)
                self.assertEqual(values[7, base + 4] & 1, 0)
            self.assertEqual(len(set(words)), 6)
            self.assertEqual(values[2, 0xd416], 0x24)
            self.assertEqual(values[2, 0xd436], 0x78)
            self.assertEqual(values[2, 0xd417] & 7, 7)
            self.assertEqual(values[2, 0xd437] & 7, 7)
            for tick in range(7, 12):
                self.assertEqual(values[tick, 0xd418] & 15, 0)
                self.assertEqual(values[tick, 0xd438] & 15, 0)
            selector = report["standaloneAddressSelector"]
            prg = Path(report["prg"]).read_bytes()
            self.assertEqual(prg[selector["returnAddress"] - 0x0801 + 2], 0x60)
            self.assertEqual(source.read_bytes(), original)

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

    def test_sparse_native_patterns_use_the_unpacked_footer_and_execute_without_corrupting_sequences(self):
        for rows in (120, 240):
            with self.subTest(rows=rows), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "sparse.swm"
                source.write_bytes(sparse_native_module(rows))
                report = EXPORTER.export_module(source, Path(directory) / "out")
                audited, writes = audit_psid(Path(report["sid"]).read_bytes(), rows + 5)
                self.assertEqual(audited["playCalls"], rows + 5)
                waveforms = {row["tick"]: row["value"] for row in writes if row["phase"] == "play" and row["address"] == 0xd404}
                self.assertEqual(waveforms[1], 0x21)
                self.assertEqual(waveforms[rows - 3], 0x21)
                self.assertEqual(waveforms[rows - 2], 0x20)

    def test_rejects_a_compressed_pattern_footer_that_counts_packed_bytes(self):
        data = bytearray(sparse_native_module(120))
        data[-34] = len(data[75:-32]) - 1
        with self.assertRaisesRegex(ValueError, "pattern|structure"):
            EXPORTER.inspect_module(bytes(data))

    def test_plain_terminal_gate_off_and_sequence_volume_commands_stop_all_three_voices_on_the_same_call(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "stopped.swm"
            source.write_bytes(stopped_native_module())
            report = EXPORTER.export_module(source, Path(directory) / "out")
            _, writes = audit_psid(Path(report["sid"]).read_bytes(), 10)
            values = {(row["tick"], row["address"]): row["value"] for row in writes if row["phase"] == "play"}
            self.assertEqual(values[3, 0xd418] & 15, 15)
            for tick in range(4, 10):
                self.assertEqual(values[tick, 0xd418] & 15, 0)
                for register in (0xd404, 0xd40b, 0xd412):
                    self.assertEqual(values[tick, register], 0x20)

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
