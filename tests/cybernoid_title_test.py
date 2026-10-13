from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/prepare-cybernoid-title.py'
SOURCE = ROOT / 'evidence/cybernoid-editable-data/title-runtime.json.gz'
TITLE = ROOT / 'songs/cybernoid-title.json'
SOURCE_SHA256 = 'e56ed96c2a4dd6e9bacbbddf25253537c9d783b63dd986f2e7aaeb1b78179816'
sys.path.insert(0, str(ROOT / 'scripts'))
from cybernoid_player import compute_writes


def load_preparer():
    spec = importlib.util.spec_from_file_location('prepare_cybernoid_title', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def without_evidence(value):
    if isinstance(value, dict):
        return {key: without_evidence(item) for key, item in value.items() if key != 'sourceEvidence'}
    if isinstance(value, list):
        return [without_evidence(item) for item in value]
    return value


class CybernoidTitleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preparer = load_preparer()
        cls.raw_source = gzip.decompress(SOURCE.read_bytes())
        cls.source = json.loads(cls.raw_source)

    def test_pinned_evidence_and_saved_editable_title_are_deterministic(self):
        self.assertEqual(SOURCE_SHA256, hashlib.sha256(self.raw_source).hexdigest())
        self.assertEqual(self.source, self.preparer.read_source(SOURCE))
        prepared = self.preparer.prepare_title(self.source)
        self.assertEqual(self.preparer.encoded(prepared), TITLE.read_bytes())
        self.assertEqual(self.preparer.encoded(prepared), self.preparer.encoded(self.preparer.prepare_title(self.source)))
        provenance = prepared['sourceEvidence']
        self.assertEqual({'path': 'evidence/cybernoid-editable-data/title-runtime.json.gz',
                          'rawSha256': SOURCE_SHA256}, provenance['canonicalEvidence'])
        self.assertEqual('41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192',
                         provenance['originalSid']['sha256'])
        self.assertEqual('Jeroen Tel', provenance['originalSid']['music'])
        self.assertIn('Charles Deenen', provenance['originalSid']['driver'])

    def test_first_cycle_selection_preserves_every_numeric_program_and_row(self):
        prepared = self.preparer.prepare_title(self.source)
        expected = without_evidence(self.source)
        expected['rows'] = [row for row in expected['rows'] if row['call'] < 17280]
        expected['play_calls'] = 17408
        expected['ending'] = {'start_call': 17280, 'release_calls': 64, 'fade_step_calls': 4}
        self.assertEqual(expected, without_evidence(prepared))
        self.assertEqual(4331, len(prepared['rows']))
        self.assertEqual(0, min(row['call'] for row in prepared['rows']))
        self.assertEqual(17274, max(row['call'] for row in prepared['rows']))
        self.assertTrue(any(row['call'] == 17280 for row in self.source['rows']))
        self.assertTrue(all(row['call'] < prepared['ending']['start_call'] for row in prepared['rows']))

    def test_exclusive_cycle_boundary_and_recursive_evidence_removal(self):
        source = deepcopy(self.source)
        source['rows'] = [dict(call=call, voiceIndex=0, transpose=0, patchSetup='preserve',
                               commands=[dict(kind='note', sourceNote=28,
                                              sourceEvidence={'value': 'irrelevant'})],
                               sourceEvidence={'sourceAddress': 0})
                          for call in (0, 17279, 17280, 17407)]
        source['records'][0]['sourceEvidence'] = {'nested': [{'sourceEvidence': {'fx1': 255}}]}
        prepared = self.preparer.prepare_title(source)
        self.assertEqual([0, 17279], [row['call'] for row in prepared['rows']])
        self.assertEqual(without_evidence(prepared['rows']), prepared['rows'])
        self.assertEqual(without_evidence(prepared['records']), prepared['records'])

    def test_preparation_does_not_mutate_or_alias_its_input(self):
        source = deepcopy(self.source)
        before = deepcopy(source)
        prepared = self.preparer.prepare_title(source)
        self.assertEqual(before, source)
        prepared['rows'][0]['commands'][-1]['sourceNote'] = 255
        prepared['frequency_words'][0] = 65535
        prepared['initial_state']['voices'][0]['caller']['note_age'] = 0
        self.assertEqual(before, source)

    def test_changed_canonical_bytes_are_rejected_before_output_creation(self):
        with TemporaryDirectory() as folder:
            changed = Path(folder) / 'changed.json.gz'
            output = Path(folder) / 'title.json'
            changed.write_bytes(gzip.compress(self.raw_source + b'\n'))
            with self.assertRaisesRegex(ValueError, '[Ff]ingerprint'):
                self.preparer.read_source(changed)
            result = subprocess.run([sys.executable, str(SCRIPT), '--source', str(changed),
                                     '--output', str(output)], capture_output=True, text=True)
            self.assertNotEqual(0, result.returncode)
            self.assertIn('fingerprint', result.stderr.lower())
            self.assertFalse(output.exists())

    def test_cli_uses_fresh_output_and_check_preserves_existing_bytes(self):
        with TemporaryDirectory() as folder:
            output = Path(folder) / 'title.json'
            command = [sys.executable, str(SCRIPT), '--output', str(output)]
            created = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, created.returncode, created.stderr)
            self.assertEqual(TITLE.read_bytes(), output.read_bytes())
            blocked = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(0, blocked.returncode)
            self.assertIn('fresh', blocked.stderr.lower())
            checked = subprocess.run(command + ['--check'], capture_output=True, text=True)
            self.assertEqual(0, checked.returncode, checked.stderr)
            output.write_bytes(b'existing user edit\n')
            blocked = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(0, blocked.returncode)
            self.assertEqual(b'existing user edit\n', output.read_bytes())
            checked = subprocess.run(command + ['--check'], capture_output=True, text=True)
            self.assertNotEqual(0, checked.returncode)
            self.assertEqual(b'existing user edit\n', output.read_bytes())

    def test_complete_selected_prefix_has_identical_numeric_sid_writes(self):
        prepared = self.preparer.prepare_title(self.source)
        self.assertEqual(compute_writes(self.source, calls=17280), compute_writes(prepared, calls=17280))


if __name__ == '__main__':
    unittest.main()
