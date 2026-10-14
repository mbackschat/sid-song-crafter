"""Guard the title's source-preserving form selection and declared ending."""

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('take_on_me_prepare_title',
    ROOT / 'scripts/studies/take-on-me/prepare-title.py')
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)


class TakeOnMePreparationTest(unittest.TestCase):
    def test_preserves_all_musical_inputs_and_selects_the_first_complete_loop(self):
        raw = (ROOT / prepare.SOURCE).read_bytes()
        original = json.loads(raw)
        title, report = prepare.prepare(raw)
        for field in ('score', 'sound', 'initialSound', 'mix', 'target'):
            self.assertEqual(title[field], original[field])
        form = json.loads((ROOT / 'evidence/take-on-me-form/receipt.json').read_text())
        self.assertEqual(title['ending']['startCall'], form['scoreRecurrence']['repeatedReturnCall'])
        self.assertEqual(title['range']['auditCalls'], report['stopCall'] + 1 + 64)
        self.assertEqual(title['sound']['programs']['frequencies']['32'], 1712)
        self.assertEqual(raw, (ROOT / prepare.SOURCE).read_bytes())

    def test_declares_the_authored_tail_separately_from_source_behavior(self):
        title, report = prepare.prepare((ROOT / prepare.SOURCE).read_bytes())
        self.assertEqual(title['ending'], dict(startCall=4864, releaseCalls=32))
        self.assertEqual(report['stopCall'], 4896)
        self.assertFalse(report['artificialFade'])
        self.assertEqual(report['originalSourceModel'], 'unknown')
        self.assertEqual(title['target']['sidModel'], 'MOS8580')
        self.assertIn('authored', report['endingBasis'])

    def test_rejects_a_changed_canonical_composition(self):
        raw = (ROOT / prepare.SOURCE).read_bytes()
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            prepare.prepare(raw + b'\n')


if __name__ == '__main__':
    unittest.main()
