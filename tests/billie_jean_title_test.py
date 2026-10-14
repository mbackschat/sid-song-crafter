"""Guard the source-preserving Billie Jean traversal selection."""

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('billie_jean_title', ROOT / 'scripts/studies/billie-jean/prepare-title.py')
title = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(title)


class BillieJeanTitleTest(unittest.TestCase):
    def test_title_preserves_all_musical_inputs_and_stops_before_the_global_wrap(self):
        raw = (ROOT / title.SOURCE).read_bytes()
        original = json.loads(raw)
        selected, report = title.prepare(raw)
        for key in ('target', 'score', 'sound', 'initialSound'):
            self.assertEqual(selected[key], original[key])
        self.assertEqual(selected['ending'], dict(startCall=7106, releaseCalls=32))
        self.assertEqual(selected['range'], dict(auditCalls=7203))
        self.assertEqual(report['musicCalls'], 7106)
        self.assertEqual(report['stopCall'], 7138)
        self.assertEqual(report['confirmationCalls'], 64)
        self.assertFalse(report['artificialFade'])
        self.assertEqual(title.prepare(raw), (selected, report))
        self.assertEqual((ROOT / title.SOURCE).read_bytes(), raw)

    def test_changed_source_requires_an_explicit_new_selection(self):
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            title.prepare((ROOT / title.SOURCE).read_bytes() + b' ')


if __name__ == '__main__':
    unittest.main()
