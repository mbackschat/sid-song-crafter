import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sidwizard_setup", ROOT / "scripts/setup-sidwizard.py")
SETUP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SETUP)


class SIDWizardSetupTest(unittest.TestCase):
    def test_rejects_unsupported_chip_counts_before_acquiring_dependencies(self):
        with patch.object(SETUP, "acquire") as acquire:
            for value in (0, 3, True, "2"):
                with self.subTest(value=value), self.assertRaisesRegex(ValueError, "SID count"):
                    SETUP.setup(value)
            acquire.assert_not_called()

    def test_two_sid_build_has_a_separate_binary_and_matching_receipt(self):
        original = (SETUP.TOOL_ROOT / "exporter.prg").read_bytes()
        manifest = SETUP.setup(2)
        root = ROOT / ".tools/sid-wizard-exporter-2sid"
        self.assertEqual(manifest["sidCount"], 2)
        self.assertEqual(json.loads((root / "build.json").read_text()), manifest)
        self.assertEqual(SETUP.sha256(root / "exporter.prg"), manifest["exporterSha256"])
        self.assertEqual(SETUP.sha256(root / "exporter.labels"), manifest["labelsSha256"])
        self.assertFalse(manifest["sourceModified"])
        self.assertNotEqual((root / "exporter.prg").read_bytes(), original)
        self.assertEqual((SETUP.TOOL_ROOT / "exporter.prg").read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
