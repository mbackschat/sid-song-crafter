"""Guard first-traversal selection without changing native musical data."""

import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/studies/airwolf'))
SPEC = importlib.util.spec_from_file_location('airwolf_title_preparer', ROOT / 'scripts/studies/airwolf/prepare-title.py')
preparer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preparer)


class AirwolfTitleTest(unittest.TestCase):
    def test_preserved_rows_and_native_patches_end_before_internal_restart(self):
        raw = (ROOT / 'evidence/airwolf-form/complete/score.json').read_bytes()
        title, report = preparer.prepare(raw)
        source = json.loads(raw)
        self.assertEqual(title['rows'], source['rows'])
        self.assertEqual(title['sound'], preparer.player.NATIVE_SOUND)
        self.assertEqual(title['ending'], dict(startCall=1241, releaseCalls=32))
        self.assertEqual(title['range'], dict(auditCalls=1338))
        self.assertEqual(report['sourcePrefixStores'], 5586)
        self.assertFalse(report['artificialFade'])

    def test_wrong_source_score_bytes_reject_before_preparation(self):
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            preparer.prepare(b'{}')

    def test_preparation_is_byte_deterministic_and_declares_init_offset(self):
        raw = (ROOT / 'evidence/airwolf-form/complete/score.json').read_bytes()
        first = preparer.prepare(raw)
        second = preparer.prepare(raw)
        self.assertEqual([preparer.encoded(item) for item in first], [preparer.encoded(item) for item in second])
        self.assertEqual(first[1]['cycleUpdatesIncludingInit'], 1242)
        self.assertEqual(first[1]['musicPlayCalls'], 1241)


if __name__ == '__main__':
    unittest.main()
