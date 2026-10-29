import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/generate-native-instruments.py"
SOURCE = ROOT / "songs/studies/sidwizard-repertoire/repertoire.json"


class NativeInstrumentsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("native_instruments", SCRIPT)
        cls.generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.generator)

    def test_original_bank_keeps_separate_native_programs(self):
        bank = json.loads(SOURCE.read_text())
        outputs = self.generator.generate(bank)
        moving = outputs["instruments/pulse-moving.swi"][2:]
        self.assertEqual(moving[5:7], bytes((0x24, 12)))
        pulse_start, filter_start = moving[10:12]
        self.assertEqual(moving[16:pulse_start], bytes((0x41, 0, 0, 0xFF)))
        self.assertEqual(moving[pulse_start:filter_start], bytes((
            0x84, 0, 0, 0x20, 0x20, 0, 0x20, 0xE0, 0,
            0xFE, pulse_start + 3, 0, 0xFF,
        )))
        self.assertEqual(moving[-8:], b"PULSEMOV")

    def test_comparisons_change_instrument_programs_and_keep_phrase_bytes(self):
        bank = json.loads(SOURCE.read_text())
        outputs = self.generator.generate(bank)
        for role in ("pulse", "pluck", "bass", "mix"):
            reference = outputs[f"{role}-reference.swm"]
            candidate = outputs[f"{role}-candidate.swm"]
            prefix_end = self.generator.instrument_data_offset(bank, f"{role}-reference")
            self.assertEqual(reference[:prefix_end], candidate[:prefix_end], role)
            self.assertNotEqual(reference[prefix_end:], candidate[prefix_end:], role)

    def test_native_workfiles_are_reproducible_from_the_retained_source(self):
        bank = json.loads(SOURCE.read_text())
        first = self.generator.generate(bank)
        second = self.generator.generate(bank)
        self.assertEqual(first, second)
        for relative, data in first.items():
            self.assertEqual((SOURCE.parent / "native" / relative).read_bytes(), data, relative)

    def test_invalid_native_table_jump_is_rejected_before_writing(self):
        bank = json.loads(SOURCE.read_text())
        bank["instruments"]["pulse-moving"]["pulse"][-1]["jump"] = 99
        with self.assertRaisesRegex(ValueError, "pulse-moving.*jump"):
            self.generator.generate(bank)

    def test_native_pattern_limit_is_checked_after_column_encoding(self):
        bank = json.loads(SOURCE.read_text())
        bank["phrases"]["melody"]["rows"] = 200
        bank["phrases"]["melody"]["events"] = [
            {"row": row, "note": "C4", "instrument": "primary"}
            for row in range(200)
        ]
        with self.assertRaisesRegex(ValueError, "melody.*249"):
            self.generator.generate(bank)

    def test_unknown_instrument_role_is_rejected_before_writing(self):
        bank = json.loads(SOURCE.read_text())
        bank["phrases"]["melody"]["events"][0]["instrument"] = "missing"
        with self.assertRaisesRegex(ValueError, "missing"):
            self.generator.generate(bank)


def table_instrument(**fields):
    instrument = {
        "name": "HEADER", "control": "1a", "hard_restart_adsr": "0f00", "adsr": "00f0", "frame1": "09",
        "wave": [["41", "00", "00"], ["10", "00", "00"]],
        "pulse": [["88", "00", "00"], ["10", "08", "00"]],
        "filter": [["9f", "10", "00"], ["0a", "af", "00"]],
    }
    instrument.update(fields)
    return instrument


class NativeInstrumentHeaderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("native_instruments", SCRIPT)
        cls.generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.generator)

    def encode(self, **fields):
        return self.generator.instrument_bytes("header", table_instrument(**fields))

    def test_absent_header_fields_keep_the_bytes_written_before_they_existed(self):
        data = self.encode()
        self.assertEqual(data[7:10], bytes((0, 1, 0)))
        self.assertEqual(data[12:15], bytes((0, 0, 0)))

    def test_header_fields_land_at_their_native_positions(self):
        data = self.encode(arp_speed=0x81, default_chord=4, octave_shift=-3, gate_off_wave=1, gate_off_pulse=0, gate_off_filter=1)
        pulse_start, filter_start = data[10], data[11]
        self.assertEqual(data[7], 0x81)
        self.assertEqual(data[8], 4)
        self.assertEqual(data[9], (-36) & 0xFF)
        # Gate-off pointers are instrument-relative table positions; row 0 is a real pointer, absence is zero.
        self.assertEqual(data[12], 16 + 3)
        self.assertEqual(data[13], pulse_start)
        self.assertEqual(data[14], filter_start + 3)

    def test_octave_shift_is_written_in_semitones_for_both_directions(self):
        self.assertEqual(self.encode(octave_shift=2)[9], 24)
        self.assertEqual(self.encode(octave_shift=-1)[9], 244)
        self.assertEqual(self.encode(octave_shift=0)[9], 0)

    def test_gate_off_may_name_the_wave_or_pulse_terminator_but_not_the_filter_size_byte(self):
        data = self.encode(gate_off_wave=2, gate_off_pulse=2)
        self.assertEqual(data[12], 16 + 6)
        self.assertEqual(data[13], data[10] + 6)
        with self.assertRaisesRegex(ValueError, "gate_off_wave"):
            self.encode(gate_off_wave=3)
        with self.assertRaisesRegex(ValueError, "gate_off_filter"):
            self.encode(gate_off_filter=2)

    def test_invalid_header_fields_are_rejected(self):
        for field, value in (
            ("octave_shift", 11), ("octave_shift", -11), ("octave_shift", 1.5), ("octave_shift", True),
            ("arp_speed", 256), ("default_chord", -1), ("gate_off_wave", -1), ("gate_off_pulse", True), ("gate_off_filter", "1"),
        ):
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                self.encode(**{field: value})

    def test_jump_pointer_writes_a_raw_rest_pointer_and_leaves_the_row_jump_form_alone(self):
        data = self.encode(wave=[["41", "00", "00"], {"jump_pointer": "d0"}, ["10", "00", "00"]], pulse=[["88", "00", "00"], {"jump": 0}])
        self.assertEqual(data[19:22], bytes((0xFE, 0xD0, 0)))
        pulse_start = data[10]
        self.assertEqual(data[pulse_start + 3:pulse_start + 6], bytes((0xFE, pulse_start, 0)))

    def test_jump_pointer_must_be_a_rest_pointer_and_cannot_combine_with_a_row_jump(self):
        for row in ({"jump_pointer": "20"}, {"jump_pointer": 0x7F}, {"jump_pointer": "d0", "jump": 0}, {"jump_pointer": 256}):
            with self.subTest(row=row), self.assertRaisesRegex(ValueError, "jump"):
                self.encode(wave=[["41", "00", "00"], row])


if __name__ == "__main__":
    unittest.main()
