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


if __name__ == "__main__":
    unittest.main()
