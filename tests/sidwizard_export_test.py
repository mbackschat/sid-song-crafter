import importlib.util
from pathlib import Path
import re
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
    def test_explicit_pal_and_default_exports_preserve_the_frozen_pinned_binaries(self):
        fixtures = (
            (original_module(), "e67ec343370c86bda1108474b5943029c6239ca0c27367ddc587541aeea73807", "97eba2ba9a7dea7dd42abfbb1a5254327fd3812a8d4bff39b3e5c3873b29b236"),
            (six_voice_native_module(), "0ebd35a38f068777762241015c2d4c552f0422a61d9492a84da29c7406210a62", "ce0c570753621233136128ef1dcf5b9186723745da01e1aaf62b2ad72ca03c77"),
        )
        for count, (data, sid_hash, prg_hash) in enumerate(fixtures, start=1):
            with self.subTest(sid_count=count), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / "fixture.swm"
                source.write_bytes(data)
                default = EXPORTER.export_module(source, root / "default")
                explicit = EXPORTER.export_module(source, root / "explicit", clock="pal")
                self.assertEqual(default["clock"], "PAL")
                self.assertEqual(default["sidSha256"], sid_hash)
                self.assertEqual(default["prgSha256"], prg_hash)
                for kind in ("sid", "prg"):
                    self.assertEqual(Path(default[kind]).read_bytes(), Path(explicit[kind]).read_bytes())

    def test_ntsc_exports_declare_the_region_and_patch_the_complete_equal_temperament_table(self):
        for count, data in ((1, original_module()), (2, six_voice_native_module())):
            label_dir = "sid-wizard-exporter" if count == 1 else "sid-wizard-exporter-2sid"
            labels = {name: int(value, 16) for value, name in re.findall(r"^al ([\da-fA-F]+) \.(.+)$", (ROOT / ".tools" / label_dir / "exporter.labels").read_text(), re.MULTILINE)}
            for model, flags in (("MOS6581", 0x18 if count == 1 else 0x58), ("MOS8580", 0x28 if count == 1 else 0xa8)):
                with self.subTest(sid_count=count, model=model), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    source = root / "fixture.swm"
                    source.write_bytes(data)
                    report = EXPORTER.export_module(source, root / "out", clock="ntsc", sid_model=model)
                    sid, prg = Path(report["sid"]).read_bytes(), Path(report["prg"]).read_bytes()
                    self.assertEqual(int.from_bytes(sid[118:120], "big"), flags)
                    self.assertEqual((report["clock"], report["frameCycles"], report["clockHz"]), ("NTSC", 17095, 14318181.82 / 14))
                    hi, lo = (labels[f"extraPlayer:player:{name}"] for name in ("FREQTBH", "FREQTBL"))
                    for native_note in range(96):
                        midi = native_note + 11
                        expected = round(440 * 2 ** ((midi - 69) / 12) * 2**24 / (14318181.82 / 14))
                        sid_word = sid[126 + lo - 0x1000 + native_note] | sid[126 + hi - 0x1000 + native_note] << 8
                        prg_word = prg[2 + lo - labels["EXEstarter"] + native_note] | prg[2 + hi - labels["EXEstarter"] + native_note] << 8
                        self.assertEqual(sid_word, expected, f"SID native note {native_note}")
                        self.assertEqual(prg_word, expected, f"PRG native note {native_note}")
                    self.assertEqual(source.read_bytes(), data)
                    self.assertEqual(report["effectTimingPolicy"], "target-vbi")
                    self.assertEqual(report["envelopeTimingPolicy"], "retain-sid-adsr-codes")

    def test_export_rejects_unknown_clock_before_reading_or_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for clock in ("PAL", "auto", "old-ntsc", None, True):
                with self.subTest(clock=clock), self.assertRaisesRegex(ValueError, "clock"):
                    EXPORTER.export_module(root / "absent.swm", root / "out", clock=clock)
                self.assertFalse((root / "out").exists())

    def test_ntsc_execution_uses_retuned_base_and_absolute_waveform_notes(self):
        for absolute in (False, True):
            with self.subTest(absolute_waveform_pitch=absolute), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                data = bytearray(stopped_native_module())
                wave_start = len(data) - 32 + 16
                data[wave_start] = 0x11
                if absolute:
                    data[wave_start + 1] = 0x80 | 58
                else:
                    data[78] = 0x80 | 58
                source = root / "a4.swm"
                source.write_bytes(data)
                exported = EXPORTER.export_module(source, root / "out", clock="ntsc")
                report, writes = audit_psid(Path(exported["sid"]).read_bytes(), 12, clock="ntsc")
                values = {(row["tick"], row["address"]): row["value"] for row in writes if row["phase"] == "play"}
                self.assertEqual(values[1, 0xd400] | values[1, 0xd401] << 8, 7218)
                self.assertEqual(values[1, 0xd404], 0x11)
                self.assertEqual(report["frameCycleBudget"], 17095)
                for tick in range(4, 12):
                    self.assertEqual(values[tick, 0xd418] & 15, 0)
                    self.assertTrue(all(values[tick, address] & 1 == 0 for address in (0xd404, 0xd40b, 0xd412)))

    def test_ntsc_dual_execution_retains_distinct_tuned_notes_filters_and_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "six.sws"
            source.write_bytes(six_voice_native_module())
            exported = EXPORTER.export_module(source, root / "out", clock="ntsc")
            _, writes = audit_psid(Path(exported["sid"]).read_bytes(), 12, clock="ntsc")
            values = {(row["tick"], row["address"]): row["value"] for row in writes if row["phase"] == "play"}
            for voice, midi in enumerate((60, 64, 67, 72, 76, 79)):
                base = 0xd400 + voice // 3 * 0x20 + voice % 3 * 7
                word = values[1, base] | values[1, base + 1] << 8
                self.assertEqual(word, round(440 * 2 ** ((midi - 69) / 12) * 2**24 / (14318181.82 / 14)))
                self.assertEqual(values[1, base + 4], 0x11)
                self.assertTrue(all(values[tick, base + 4] & 1 == 0 for tick in range(7, 12)))
            self.assertEqual((values[2, 0xd416], values[2, 0xd436]), (0x24, 0x78))
            self.assertTrue(all(values[tick, address] & 15 == 0 for tick in range(7, 12) for address in (0xd418, 0xd438)))

    def test_native_model_selection_sets_psid_flags_and_preserves_standalone_player_bytes(self):
        for count, data, flags in ((1, original_module(), 0x14), (2, six_voice_native_module(), 0x54)):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "model.swm"
                source.write_bytes(data)
                old = EXPORTER.export_module(source, Path(directory) / "6581", sid_model="MOS6581")
                new = EXPORTER.export_module(source, Path(directory) / "8580")
                sid = Path(old["sid"]).read_bytes()
                self.assertEqual(int.from_bytes(sid[118:120], "big"), flags)
                self.assertEqual(old["sidModel"], "MOS6581")
                self.assertEqual(old["sids"], [{"baseAddress": base, "model": "MOS6581"} for base in (0xd400, 0xd420)[:count]])
                audited, old_writes = audit_psid(sid, 12)
                _, new_writes = audit_psid(Path(new["sid"]).read_bytes(), 12)
                self.assertEqual(audited["sids"], old["sids"])
                self.assertEqual(old_writes, new_writes)
                old_prg, new_prg = Path(old["prg"]).read_bytes(), Path(new["prg"]).read_bytes()
                label_dir = "sid-wizard-exporter" if count == 1 else "sid-wizard-exporter-2sid"
                labels = {name: int(value, 16) for value, name in re.findall(r"^al ([\da-fA-F]+) \.(.+)$", (ROOT / ".tools" / label_dir / "exporter.labels").read_text(), re.MULTILINE)}
                flag_offset = labels["SIDflags"] + 1 - labels["EXEstarter"] + 2
                self.assertEqual([index for index, pair in enumerate(zip(old_prg, new_prg)) if pair[0] != pair[1]], [flag_offset])
                self.assertEqual(old_prg[flag_offset], flags)
                self.assertEqual(len(old_prg), len(new_prg))
                self.assertEqual(sid[:118] + sid[120:], Path(new["sid"]).read_bytes()[:118] + Path(new["sid"]).read_bytes()[120:])
                self.assertEqual(source.read_bytes(), data)

    def test_export_rejects_invalid_model_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "model.swm", Path(directory) / "out"
            source.write_bytes(original_module())
            with self.assertRaisesRegex(ValueError, "SID model"):
                EXPORTER.export_module(source, output, sid_model="unknown")
            self.assertFalse(output.exists())

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
