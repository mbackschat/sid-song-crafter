import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / ".tools/sid-wizard-1.97/resources/examples/instruments"
LOAD_ADDRESS = b"\xa1\x04"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GENERATOR = load("native_instruments", ROOT / "scripts/generate-native-instruments.py")
IMPORTER = load("swi_importer", ROOT / "scripts/import-swi.py")


def swi(name):
    return CORPUS / f"{name}.swi"


def packed(header, wave, pulse, filtr, name=b"TESTNAME"):
    """Assemble native packinst bytes from raw tables, independent of the encoder under test."""
    body = bytearray(header) + wave + pulse + filtr
    body[10] = 16 + len(wave)
    body[11] = body[10] + len(pulse)
    body[-1] = len(body) - 1
    return bytes(body) + name


HEADER = bytes((0x1A, 0x0F, 0x00, 0x00, 0xF0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 9))
WAVE = bytes((0x41, 0, 0, 0xFF))
PULSE = bytes((0x88, 0, 0, 0xFF))
FILTER = bytes((0xFF,))


@unittest.skipUnless(CORPUS.is_dir(), "Pinned SID-Wizard 1.97 examples required")
class UpstreamInstrumentImportTest(unittest.TestCase):
    def test_octave_shifted_bass_keeps_its_shift_and_standard_pulse_jump(self):
        instrument = IMPORTER.read_swi(swi("bass-hellnof"))
        self.assertEqual(instrument["name"], "HELLBASS")
        self.assertEqual(instrument["octave_shift"], -3)
        self.assertEqual(instrument["control"], "1a")
        self.assertEqual(instrument["wave"], [["41", "00", "04"]])
        self.assertEqual(instrument["pulse"][-1], {"jump": 2})
        for absent in ("arp_speed", "default_chord", "gate_off_wave", "gate_off_pulse", "gate_off_filter"):
            self.assertNotIn(absent, instrument)

    def test_rest_pointer_jump_and_wave_gate_off_row_are_imported(self):
        instrument = IMPORTER.read_swi(swi("bass-popfilt"))
        self.assertIn({"jump_pointer": "d0"}, instrument["wave"])
        self.assertEqual(instrument["gate_off_wave"], 4)

    def test_gate_off_pointers_on_every_table_and_a_terminator_pointer(self):
        instrument = IMPORTER.read_swi(swi("chord-autofi"))
        self.assertEqual((instrument["gate_off_pulse"], instrument["gate_off_filter"]), (3, 3))
        self.assertEqual(IMPORTER.read_swi(swi("flute-ocarin"))["gate_off_wave"], 6)

    def test_multispeed_and_default_chord_bytes_are_imported(self):
        self.assertEqual(IMPORTER.read_swi(swi("bass-sweep4x"))["arp_speed"], 128)
        self.assertEqual(IMPORTER.read_swi(swi("bassassa"))["default_chord"], 0)
        self.assertEqual(IMPORTER.read_swi(swi("solo-winterb"))["default_chord"], 17)
        self.assertEqual(IMPORTER.read_swi(swi("agogo"))["octave_shift"], 1)

    def test_no_reset_control_bits_are_kept_in_the_control_byte(self):
        # Bit 6 keeps the pulse table running and bit 7 the filter table when a note carries no instrument cell.
        self.assertEqual(int(IMPORTER.read_swi(swi("solo-41norst"))["control"], 16) & 0xC0, 0x40)
        controls = [int(IMPORTER.read_swi(path)["control"], 16) & 0xC0 for path in sorted(CORPUS.glob("*.swi"))]
        self.assertEqual((controls.count(0x40), controls.count(0x80), controls.count(0xC0)), (12, 6, 0))

    def test_every_upstream_example_re_encodes_byte_for_byte_including_its_name(self):
        files = sorted(CORPUS.glob("*.swi"))
        self.assertEqual(len(files), 324)
        mismatches = []
        for path in files:
            instrument = IMPORTER.read_swi(path)
            # JSON serialization is part of the contract: recipes carry the instrument as JSON.
            instrument = json.loads(json.dumps(instrument))
            if LOAD_ADDRESS + GENERATOR.instrument_bytes(path.stem, instrument) != path.read_bytes():
                mismatches.append(path.name)
        self.assertEqual(mismatches, [])

    def test_instruments_calling_the_song_chord_table_are_flagged(self):
        flagged = [path.stem for path in sorted(CORPUS.glob("*.swi")) if IMPORTER.uses_song_chord_table(IMPORTER.read_swi(path))]
        self.assertEqual(len(flagged), 29)
        self.assertIn("chord-autofi", flagged)
        self.assertFalse(IMPORTER.uses_song_chord_table(IMPORTER.read_swi(swi("bass-hellnof"))))

    def test_command_line_prints_the_instrument_and_warns_about_the_chord_table(self):
        plain = subprocess.run([sys.executable, str(ROOT / "scripts/import-swi.py"), str(swi("bass-hellnof"))], capture_output=True, text=True)
        self.assertEqual(plain.returncode, 0, plain.stderr)
        self.assertEqual(json.loads(plain.stdout), IMPORTER.read_swi(swi("bass-hellnof")))
        self.assertEqual(plain.stderr, "")
        chord = subprocess.run([sys.executable, str(ROOT / "scripts/import-swi.py"), str(swi("chord-autofi"))], capture_output=True, text=True)
        self.assertEqual(chord.returncode, 0, chord.stderr)
        self.assertIn("chord table", chord.stderr)


class SwiRejectionTest(unittest.TestCase):
    def import_bytes(self, data, prefix=LOAD_ADDRESS):
        return IMPORTER.instrument_from_swi("synthetic", prefix + data)

    def test_a_well_formed_synthetic_instrument_round_trips(self):
        data = packed(HEADER, WAVE, PULSE, FILTER)
        instrument = self.import_bytes(data)
        self.assertEqual(GENERATOR.instrument_bytes("synthetic", instrument), data)

    def test_name_padding_is_kept_verbatim_and_trailing_spaces_are_not(self):
        self.assertEqual(self.import_bytes(packed(HEADER, WAVE, PULSE, FILTER, b"AB......"))["name"], "AB......")
        self.assertEqual(self.import_bytes(packed(HEADER, WAVE, PULSE, FILTER, b"AB      "))["name"], "AB")

    def test_unrepresentable_bytes_are_rejected_instead_of_dropped(self):
        header = lambda changes: bytes(changes.get(index, value) for index, value in enumerate(HEADER))
        cases = {
            "load address": (packed(HEADER, WAVE, PULSE, FILTER), b"\x01\x08"),
            "truncated": (packed(HEADER, WAVE, PULSE, FILTER)[:20], LOAD_ADDRESS),
            "lowercase name": (packed(HEADER, WAVE, PULSE, FILTER, b"lowcase!"), LOAD_ADDRESS),
            "blank name": (packed(HEADER, WAVE, PULSE, FILTER, b"        "), LOAD_ADDRESS),
            "fractional octave": (packed(header({9: 5}), WAVE, PULSE, FILTER), LOAD_ADDRESS),
            "jump argument": (packed(HEADER, bytes((0xFE, 0x10, 1, 0xFF)), PULSE, FILTER), LOAD_ADDRESS),
            "misaligned jump": (packed(HEADER, bytes((0x41, 0, 0, 0xFE, 0x12, 0, 0xFF)), PULSE, FILTER), LOAD_ADDRESS),
            "jump outside table": (packed(HEADER, bytes((0xFE, 0x30, 0, 0xFF)), PULSE, FILTER), LOAD_ADDRESS),
            "gate-off off a row": (packed(header({12: 17}), WAVE, PULSE, FILTER), LOAD_ADDRESS),
            "gate-off into the filter size byte": (packed(header({14: 16 + 4 + 4 + 3}), WAVE, PULSE, bytes((0x9F, 0x10, 0, 0xFF))), LOAD_ADDRESS),
            "unterminated wave table": (packed(HEADER, bytes((0x41, 0, 0, 0x10)), PULSE, FILTER), LOAD_ADDRESS),
        }
        for label, (data, prefix) in cases.items():
            with self.subTest(label), self.assertRaises(ValueError):
                self.import_bytes(data, prefix)

    def test_size_marker_must_match_the_instrument_length(self):
        data = bytearray(packed(HEADER, WAVE, PULSE, FILTER))
        data[len(data) - 8 - 1] += 1
        with self.assertRaisesRegex(ValueError, "size"):
            self.import_bytes(bytes(data))


if __name__ == "__main__":
    unittest.main()
