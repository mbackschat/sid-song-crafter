from copy import deepcopy
from contextlib import redirect_stdout
import gzip
import hashlib
import importlib.util
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('evidence', ROOT / 'scripts/evidence.py')
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'evidence').mkdir()
        self.manifest = {'version': 1, 'files': []}

    def entry(self, name='rows.json.gz', data=b'rows\x00\xff\n', original=None):
        stored = gzip.compress(data, mtime=0) if name.endswith('.gz') else data
        path = self.root / 'evidence' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(stored)
        entry = {'path': 'evidence/' + name,
                 'originalPath': original or 'build/study/' + name.removesuffix('.gz'),
                 'sha256': hashlib.sha256(stored).hexdigest(), 'bytes': len(stored),
                 'originalSha256': hashlib.sha256(data).hexdigest(), 'originalBytes': len(data),
                 'purpose': 'Executed score state'}
        self.manifest['files'].append(entry)
        return entry

    def save_manifest(self):
        (self.root / 'evidence/manifest.json').write_text(json.dumps(self.manifest))

    def test_default_verify_and_full_lossless_restore_preserve_evidence(self):
        data = b'rows\x00\xff\n' * 200000
        first = self.entry(data=data)
        second = self.entry('receipt.json', b'{"complete":true}\n')
        self.save_manifest()
        before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns)
                  for path in (self.root / 'evidence').iterdir()}
        self.assertEqual(self.manifest, evidence.load_manifest(root=self.root))
        self.assertEqual(['verified'] * 2, [row['status'] for row in evidence.verify(root=self.root)])
        self.assertFalse((self.root / 'build').exists())
        self.assertEqual(['restored'] * 2, [row['status'] for row in evidence.restore(root=self.root)])
        self.assertEqual(data, (self.root / first['originalPath']).read_bytes())
        self.assertEqual(b'{"complete":true}\n', (self.root / second['originalPath']).read_bytes())
        self.assertEqual(before, {path.name: (path.read_bytes(), path.stat().st_mtime_ns)
                                  for path in (self.root / 'evidence').iterdir()})

    def test_selected_restore_and_identical_existing_target_are_idempotent(self):
        first = self.entry()
        second = self.entry('other.json.gz', b'other')
        paths = [first['path']]
        self.assertEqual('restored', evidence.restore(self.manifest, paths, root=self.root)[0]['status'])
        target = self.root / first['originalPath']
        before = target.stat()
        self.assertEqual('identical', evidence.restore(self.manifest, paths, root=self.root)[0]['status'])
        self.assertEqual((before.st_ino, before.st_mtime_ns), (target.stat().st_ino, target.stat().st_mtime_ns))
        self.assertFalse((self.root / second['originalPath']).exists())
        with self.assertRaisesRegex(ValueError, 'manifest'):
            evidence.restore(self.manifest, ['evidence/not-listed.json.gz'], root=self.root)

    def test_differing_existing_destination_is_preserved(self):
        entry = self.entry()
        target = self.root / entry['originalPath']
        target.parent.mkdir(parents=True)
        target.write_bytes(b'keep authored edits')
        with self.assertRaises(FileExistsError):
            evidence.restore(self.manifest, root=self.root)
        self.assertEqual(b'keep authored edits', target.read_bytes())
        self.assertEqual([target], list(target.parent.iterdir()))

    def test_stored_or_uncompressed_corruption_never_publishes_destination(self):
        entry = self.entry()
        archive = self.root / entry['path']
        archive.write_bytes(archive.read_bytes() + b'changed')
        for operation in (evidence.verify, evidence.restore):
            with self.assertRaisesRegex(ValueError, 'stored'):
                operation(self.manifest, root=self.root)
        self.assertFalse((self.root / entry['originalPath']).exists())
        archive.write_bytes(gzip.compress(b'other valid bytes', mtime=0))
        entry['sha256'] = hashlib.sha256(archive.read_bytes()).hexdigest()
        entry['bytes'] = archive.stat().st_size
        for operation in (evidence.verify, evidence.restore):
            with self.assertRaisesRegex(ValueError, 'original'):
                operation(self.manifest, root=self.root)
        self.assertFalse((self.root / entry['originalPath']).exists())
        self.assertFalse(any((self.root / 'build').rglob('.evidence-*')))

    def test_pointer_and_missing_lfs_object_have_actionable_errors(self):
        entry = self.entry()
        archive = self.root / entry['path']
        archive.write_bytes(b'version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 123\n')
        with self.assertRaisesRegex(ValueError, 'git lfs pull'):
            evidence.verify(self.manifest, root=self.root)
        archive.unlink()
        with self.assertRaisesRegex(FileNotFoundError, 'git lfs pull'):
            evidence.restore(self.manifest, root=self.root)

    def test_manifest_rejects_traversal_absolute_paths_and_duplicate_destinations(self):
        entry = self.entry()
        for field, values in (('path', ['/tmp/rows.gz', 'evidence/../rows.gz', 'build/rows.gz']),
                              ('originalPath', ['/tmp/rows.json', 'build/../rows.json', 'evidence/rows.json'])):
            for value in values:
                manifest = deepcopy(self.manifest)
                manifest['files'][0][field] = value
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        evidence.restore(manifest, root=self.root)
        manifest = deepcopy(self.manifest)
        duplicate = dict(entry, path='evidence/other.json.gz')
        manifest['files'].append(duplicate)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            evidence.verify(manifest, root=self.root)

    def test_symlink_sources_destinations_and_parent_directories_are_rejected(self):
        entry = self.entry()
        archive = self.root / entry['path']
        outside = self.root / 'outside'
        outside.mkdir()
        outside_file = outside / 'rows.gz'
        archive.rename(outside_file)
        archive.symlink_to(outside_file)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            evidence.verify(self.manifest, root=self.root)
        archive.unlink()
        outside_file.rename(archive)
        (self.root / 'build').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            evidence.restore(self.manifest, root=self.root)
        self.assertEqual([], list(outside.iterdir()))
        (self.root / 'build').unlink()
        target = self.root / entry['originalPath']
        target.parent.mkdir(parents=True)
        outside_file.write_bytes(b'keep')
        target.symlink_to(outside_file)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            evidence.restore(self.manifest, root=self.root)
        self.assertEqual(b'keep', outside_file.read_bytes())

    def test_cli_defaults_to_verification_and_restores_only_explicit_selection(self):
        first = self.entry()
        second = self.entry('other.json.gz', b'other')
        self.save_manifest()
        output = StringIO()
        with patch.object(evidence, 'ROOT', self.root), redirect_stdout(output):
            self.assertEqual(0, evidence.main([]))
        reports = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(['verified', 'verified'], [report['status'] for report in reports])
        self.assertFalse((self.root / 'build').exists())
        output = StringIO()
        with patch.object(evidence, 'ROOT', self.root), redirect_stdout(output):
            self.assertEqual(0, evidence.main(['restore', first['path']]))
        self.assertEqual(first['path'], json.loads(output.getvalue())['path'])
        self.assertTrue((self.root / first['originalPath']).exists())
        self.assertFalse((self.root / second['originalPath']).exists())


if __name__ == '__main__':
    unittest.main()
