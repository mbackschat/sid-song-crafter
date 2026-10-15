import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cleanup_build', ROOT / 'scripts/cleanup-build.py')
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


class CleanupBuildTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'build').mkdir()
        self.source = self.file('build/work/cache/render/attempt/render.wav', b'RIFF retained exact audio')
        self.retained = self.file('build/song-listening/full.wav', self.source.read_bytes())
        self.unique = self.file('build/work/cache/unique.wav', b'RIFF unique audio')
        self.text = self.file('build/work/cache/proof/trace.json', b'{"data":"' + b'x' * (1024 * 1024) + b'"}\n')
        self.output = self.root / 'build/cleanup-test'

    def file(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_default_dry_run_records_selection_without_mutating_candidates(self):
        summary = cleanup.cleanup(self.output, root=self.root)
        self.assertEqual(summary['mode'], 'dry-run')
        self.assertEqual(summary['selectedDuplicateWavs'], 1)
        self.assertEqual(summary['selectedTextFiles'], 1)
        self.assertTrue(self.source.exists())
        self.assertTrue(self.text.exists())
        self.assertFalse(self.text.with_suffix('.json.gz').exists())
        self.assertTrue((self.output / 'selection.json').exists())
        self.assertTrue((self.output / 'inventory-before.json').exists())
        self.assertTrue((self.output / 'inventory-after.json').exists())

    def test_apply_deletes_only_verified_cache_duplicate_and_roundtrips_text(self):
        original = self.text.read_bytes()
        summary = cleanup.cleanup(self.output, apply=True, root=self.root)
        self.assertTrue(summary['passed'])
        self.assertFalse(self.source.exists())
        self.assertEqual(self.retained.read_bytes(), b'RIFF retained exact audio')
        self.assertTrue(self.unique.exists())
        self.assertFalse(self.text.exists())
        archive = self.text.with_suffix('.json.gz')
        self.assertEqual(gzip.decompress(archive.read_bytes()), original)
        self.assertEqual(summary['controlledLogicalBytesReclaimed'],
                         len(b'RIFF retained exact audio') + len(original) - archive.stat().st_size)
        operations = [json.loads(line) for line in (self.output / 'operations.jsonl').read_text().splitlines()]
        deleted = next(row for row in operations if row['operation'] == 'delete-duplicate' and row['status'] == 'completed')
        self.assertEqual(deleted['sha256'], hashlib.sha256(self.retained.read_bytes()).hexdigest())
        self.assertEqual(deleted['retained'], 'build/song-listening/full.wav')
        repeated = cleanup.cleanup(self.root / 'build/cleanup-repeat', apply=True, root=self.root)
        self.assertTrue(repeated['passed'])
        self.assertEqual((repeated['selectedDuplicateWavs'], repeated['selectedTextFiles']), (0, 0))
        self.assertEqual(repeated['controlledLogicalBytesReclaimed'], 0)

    def test_missing_build_directory_produces_an_empty_fresh_report(self):
        checkout = self.root / 'clean-checkout'
        checkout.mkdir()
        output = checkout / 'build/cleanup-empty'
        summary = cleanup.cleanup(output, root=checkout)
        self.assertTrue(summary['passed'])
        self.assertEqual(summary['mode'], 'dry-run')
        self.assertEqual((summary['selectedDuplicateWavs'], summary['selectedTextFiles']), (0, 0))
        self.assertEqual(summary['before']['logicalBytes'], 0)
        self.assertEqual(summary['before']['duAllocatedBytes'], 0)
        self.assertEqual(summary['after']['logicalBytes'], 0)
        self.assertTrue((output / 'summary.json').exists())

    def test_listening_explicit_deferred_and_literal_recipe_inputs_are_protected(self):
        listening_text = self.file('build/song-listening/trace.json', self.text.read_bytes())
        deferred = self.file('build/deferred-study/cache/trace.json', self.text.read_bytes())
        pinned = self.file('build/pinned/trace.json', self.text.read_bytes())
        asset = self.file('build/source-assets/score.json', self.text.read_bytes())
        self.file('config/listening/case.json', json.dumps({'stages': [{'inputs': ['build/pinned/trace.json', '{stage:x}/generated.json']}]}).encode())
        self.file('config/local-assets.json', json.dumps({'references': [{'path': 'build/source-assets/score.json'}]}).encode())
        cleanup.cleanup(self.output, apply=True, protect=['build/deferred-study', 'build/future-not-created'], root=self.root)
        for path in (listening_text, deferred, pinned, asset):
            self.assertTrue(path.exists(), path)
            self.assertFalse(path.with_suffix('.json.gz').exists(), path)

    def test_symlink_files_and_directories_are_not_followed(self):
        outside = self.file('outside/trace.json', self.text.read_bytes())
        (self.root / 'build/link-directory').symlink_to(outside.parent, target_is_directory=True)
        (self.root / 'build/work/cache/link.wav').symlink_to(self.retained)
        cleanup.cleanup(self.output, apply=True, root=self.root)
        self.assertTrue(outside.exists())
        self.assertFalse(outside.with_suffix('.json.gz').exists())
        self.assertTrue((self.root / 'build/work/cache/link.wav').is_symlink())

    def test_changed_or_replaced_retained_copy_prevents_deletion(self):
        for replacement in ('changed', 'symlink'):
            with self.subTest(replacement=replacement):
                output = self.root / ('build/cleanup-' + replacement)
                self.retained.unlink(missing_ok=True)
                self.retained.write_bytes(self.source.read_bytes())
                original_write = cleanup._write_json
                def change_after_selection(path, value):
                    original_write(path, value)
                    if path.name == 'selection.json':
                        self.retained.unlink()
                        if replacement == 'symlink':
                            self.retained.symlink_to(self.unique)
                        else:
                            self.retained.write_bytes(b'changed evidence')
                with patch.object(cleanup, '_write_json', side_effect=change_after_selection):
                    with self.assertRaises((ValueError, OSError)):
                        cleanup.cleanup(output, apply=True, root=self.root)
                self.assertTrue(self.source.exists())
                self.assertTrue((output / 'selection.json').exists())
                self.assertFalse(json.loads((output / 'summary.json').read_text())['passed'])

    def test_existing_gzip_is_preserved_and_original_not_compacted(self):
        archive = self.text.with_suffix('.json.gz')
        archive.write_bytes(b'preexisting archive')
        cleanup.cleanup(self.output, apply=True, root=self.root)
        self.assertTrue(self.text.exists())
        self.assertEqual(archive.read_bytes(), b'preexisting archive')

    def test_fresh_report_and_build_boundary_are_enforced(self):
        for output in (self.root / 'outside-report', self.root / 'build'):
            with self.subTest(output=output):
                with self.assertRaises(ValueError):
                    cleanup.cleanup(output, root=self.root)
        (self.root / 'build/report-link').symlink_to(self.root / 'missing')
        with self.assertRaises(ValueError):
            cleanup.cleanup(self.root / 'build/report-link/new', root=self.root)
        with self.assertRaises(ValueError):
            cleanup.cleanup(self.output, protect=['../outside'], root=self.root)
        self.assertTrue(self.source.exists())


if __name__ == '__main__':
    unittest.main()
