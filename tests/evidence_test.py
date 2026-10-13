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

    def working(self, name='rows.json', data=b'{"rows":[1,2,3]}\n'):
        path = self.root / 'build/study' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path.relative_to(self.root).as_posix()

    def selection(self, source, path='evidence/new/rows.json.gz'):
        return {'version': 1, 'files': [dict(source=source, path=path,
                                              group='new-proof', reason='Retain the complete checked score.') ]}

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

    def test_promotion_is_deterministic_lossless_and_preserves_existing_metadata_and_sources(self):
        old = deepcopy(self.entry('old.json', b'old retained bytes'))
        self.manifest['extra'] = {'owner': 'study', 'nested': [1, 2]}
        self.save_manifest()
        first = self.working('first.json', b'new original bytes\x00\xff' * 1000)
        second = self.working('second.json', (self.root / first).read_bytes())
        plain = self.working('receipt.json', b'{"complete":true}\n')
        selection = self.selection(first, 'evidence/new/first.json.gz')
        selection['files'].extend([dict(selection['files'][0], source=second, path='evidence/new/second.json.gz'),
                                   dict(selection['files'][0], source=plain, path='evidence/new/receipt.json')])
        originals = {source: (self.root / source).read_bytes() for source in (first, second, plain)}
        original_selection = deepcopy(selection)
        reports = evidence.promote(selection, root=self.root)
        self.assertEqual(['promoted'] * 3, [row['status'] for row in reports])
        manifest = evidence.load_manifest(root=self.root)
        self.assertEqual(old, manifest['files'][0])
        self.assertEqual(self.manifest['extra'], manifest['extra'])
        self.assertEqual(original_selection, selection)
        self.assertEqual((self.root / 'evidence/new/first.json.gz').read_bytes(),
                         (self.root / 'evidence/new/second.json.gz').read_bytes())
        self.assertEqual(originals[plain], (self.root / 'evidence/new/receipt.json').read_bytes())
        self.assertEqual(originals, {source: (self.root / source).read_bytes() for source in originals})
        self.assertEqual(3, len(evidence.verify(manifest, groups=['new-proof'], root=self.root)))
        for source in originals:
            (self.root / source).unlink()
        evidence.restore(manifest, groups=['new-proof'], root=self.root)
        self.assertEqual(originals, {source: (self.root / source).read_bytes() for source in originals})

    def test_late_invalid_selection_has_no_archive_or_manifest_effects(self):
        self.save_manifest()
        good = self.working()
        bad = self.working('reference.wav', b'not even wave data')
        selection = self.selection(good)
        selection['files'].append(dict(selection['files'][0], source=bad, path='evidence/new/bad.json'))
        before = (self.root / 'evidence/manifest.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'Reference'):
            evidence.promote(selection, root=self.root)
        self.assertEqual(before, (self.root / 'evidence/manifest.json').read_bytes())
        self.assertEqual(['manifest.json'], [path.name for path in (self.root / 'evidence').iterdir()])

    def test_promotion_rejects_duplicates_existing_archives_and_manifest_as_destination(self):
        existing = self.entry('old.json', b'old')
        self.save_manifest()
        source = self.working()
        for selection in (self.selection(source, existing['path']),
                          self.selection(source, 'evidence/manifest.json')):
            with self.subTest(selection=selection), self.assertRaises((ValueError, FileExistsError)):
                evidence.promote(selection, root=self.root)
        duplicate = self.selection(source)
        duplicate['files'].append(dict(duplicate['files'][0], path='evidence/new/other.json.gz'))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            evidence.promote(duplicate, root=self.root)
        other = self.working('other.json')
        duplicate['files'][1]['source'] = other
        duplicate['files'][1]['path'] = duplicate['files'][0]['path']
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            evidence.promote(duplicate, root=self.root)
        conflict = self.selection(source, 'evidence/new/data.json')
        conflict['files'].append(dict(conflict['files'][0], source=other,
                                      path='evidence/new/data.json/child.json'))
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            evidence.promote(conflict, root=self.root)
        unindexed = self.root / 'evidence/unindexed.json'
        unindexed.write_bytes(b'keep existing bytes')
        with self.assertRaises(FileExistsError):
            evidence.promote(self.selection(source, 'evidence/unindexed.json'), root=self.root)
        self.assertEqual(b'keep existing bytes', unindexed.read_bytes())

    def test_reference_magic_and_compressed_sources_cannot_be_promoted_under_renamed_paths(self):
        self.save_manifest()
        cases = [('renamed-one.json', b'PSID\x00\x02' + bytes(100)),
                 ('renamed-two.log', b'RSID' + bytes(100)),
                 ('renamed-wave.txt', b'RIFF' + bytes(4) + b'WAVE' + bytes(100)),
                 ('already.json.gz', gzip.compress(b'rows', mtime=0)),
                 ('renamed-compressed.json', gzip.compress(b'rows', mtime=0))]
        for name, data in cases:
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Reference|compressed'):
                evidence.promote(self.selection(self.working(name, data)), root=self.root)
        with self.assertRaisesRegex(ValueError, 'Reference'):
            evidence.promote(self.selection(self.working(), 'evidence/new/reference.sid.gz'), root=self.root)
        self.assertFalse((self.root / 'evidence/new').exists())

    def test_promotion_rejects_symlink_manifest_sources_and_archive_parents(self):
        self.save_manifest()
        source = self.working()
        real = self.root / source
        alias = real.with_name('alias.json')
        alias.symlink_to(real)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            evidence.promote(self.selection(alias.relative_to(self.root).as_posix()), root=self.root)
        outside = self.root / 'outside'
        outside.mkdir()
        (self.root / 'evidence/new').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            evidence.promote(self.selection(source), root=self.root)
        (self.root / 'evidence/new').unlink()
        manifest = self.root / 'evidence/manifest.json'
        manifest.rename(outside / 'manifest.json')
        manifest.symlink_to(outside / 'manifest.json')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            evidence.promote(self.selection(source), root=self.root)
        self.assertEqual(['manifest.json'], [path.name for path in outside.iterdir()])

    def test_source_change_during_copy_aborts_without_publishing(self):
        self.save_manifest()
        source = self.working()
        stream = evidence._stream

        def change_source(reader, target=None):
            if target is not None:
                (self.root / source).write_bytes(b'concurrently changed source')
            return stream(reader, target)

        with patch.object(evidence, '_stream', side_effect=change_source):
            with self.assertRaisesRegex(ValueError, 'changed'):
                evidence.promote(self.selection(source), root=self.root)
        self.assertEqual(self.manifest, evidence.load_manifest(root=self.root))
        self.assertFalse((self.root / 'evidence/new/rows.json.gz').exists())
        self.assertFalse(any((self.root / 'evidence').rglob('.evidence-*')))

    def test_manifest_change_after_archive_publication_is_preserved_and_own_archives_rolled_back(self):
        self.save_manifest()
        source = self.working()
        link = evidence.os.link
        changed = dict(self.manifest, concurrent='keep this update')

        def change_manifest(temporary, target):
            link(temporary, target)
            (self.root / 'evidence/manifest.json').write_text(json.dumps(changed))

        with patch.object(evidence.os, 'link', side_effect=change_manifest):
            with self.assertRaisesRegex(ValueError, 'Manifest changed'):
                evidence.promote(self.selection(source), root=self.root)
        self.assertEqual(changed, evidence.load_manifest(root=self.root))
        self.assertFalse((self.root / 'evidence/new/rows.json.gz').exists())
        self.assertTrue((self.root / source).exists())

    def test_publication_failure_rolls_back_new_archives_and_preserves_concurrent_destination(self):
        self.save_manifest()
        source = self.working()
        other = self.working('other.json')
        selection = self.selection(source)
        selection['files'].append(dict(selection['files'][0], source=other, path='evidence/new/other.json'))
        link = evidence.os.link
        calls = []

        def concurrent_destination(temporary, target):
            calls.append(target)
            if len(calls) == 2:
                Path(target).write_bytes(b'concurrent retained bytes')
            link(temporary, target)

        with patch.object(evidence.os, 'link', side_effect=concurrent_destination):
            with self.assertRaises(FileExistsError):
                evidence.promote(selection, root=self.root)
        self.assertFalse((self.root / selection['files'][0]['path']).exists())
        self.assertEqual(b'concurrent retained bytes', (self.root / selection['files'][1]['path']).read_bytes())
        self.assertEqual(self.manifest, evidence.load_manifest(root=self.root))

    def test_manifest_replace_failure_rolls_back_all_own_archives(self):
        self.save_manifest()
        source = self.working()
        with patch.object(evidence.os, 'replace', side_effect=OSError('injected publication failure')):
            with self.assertRaisesRegex(OSError, 'injected'):
                evidence.promote(self.selection(source), root=self.root)
        self.assertEqual(self.manifest, evidence.load_manifest(root=self.root))
        self.assertFalse((self.root / 'evidence/new/rows.json.gz').exists())
        self.assertTrue((self.root / source).exists())

    def test_rollback_does_not_adopt_a_replacement_after_our_link_succeeds(self):
        self.save_manifest()
        source = self.working()
        other = self.working('other.json')
        selection = self.selection(source)
        selection['files'].append(dict(selection['files'][0], source=other, path='evidence/new/other.json'))
        link = evidence.os.link
        calls = []

        def replace_then_fail(temporary, target):
            calls.append(target)
            if len(calls) == 2:
                raise OSError('injected second publication failure')
            link(temporary, target)
            Path(target).unlink()
            Path(target).write_bytes(b'concurrent replacement must remain')

        with patch.object(evidence.os, 'link', side_effect=replace_then_fail):
            with self.assertRaisesRegex(OSError, 'injected'):
                evidence.promote(selection, root=self.root)
        self.assertEqual(b'concurrent replacement must remain',
                         (self.root / selection['files'][0]['path']).read_bytes())
        self.assertEqual(self.manifest, evidence.load_manifest(root=self.root))

    def test_interrupt_after_atomic_manifest_replace_retains_verifiable_archives(self):
        self.save_manifest()
        source = self.working()
        replace = evidence.os.replace

        def replace_then_interrupt(temporary, target):
            replace(temporary, target)
            raise KeyboardInterrupt('injected interruption after commit')

        with patch.object(evidence.os, 'replace', side_effect=replace_then_interrupt):
            with self.assertRaises(KeyboardInterrupt):
                evidence.promote(self.selection(source), root=self.root)
        self.assertEqual(['verified'], [row['status'] for row in evidence.verify(root=self.root)])
        self.assertTrue((self.root / source).exists())

    def test_source_change_after_publication_rolls_back_unchanged_owned_archive(self):
        self.save_manifest()
        source = self.working()
        link = evidence.os.link

        def change_after_link(temporary, target):
            link(temporary, target)
            (self.root / source).write_bytes(b'new working source must remain')

        with patch.object(evidence.os, 'link', side_effect=change_after_link):
            with self.assertRaisesRegex(ValueError, 'Source changed'):
                evidence.promote(self.selection(source), root=self.root)
        self.assertFalse((self.root / 'evidence/new/rows.json.gz').exists())
        self.assertEqual(b'new working source must remain', (self.root / source).read_bytes())
        self.assertEqual(self.manifest, evidence.load_manifest(root=self.root))

    def test_group_filter_and_promotion_cli_have_unambiguous_selection(self):
        self.save_manifest()
        source = self.working()
        selection = self.selection(source)
        path = self.root / 'build/selection.json'
        path.write_text(json.dumps(selection))
        output = StringIO()
        with patch.object(evidence, 'ROOT', self.root), redirect_stdout(output):
            self.assertEqual(0, evidence.main(['promote', 'build/selection.json']))
        self.assertEqual('promoted', json.loads(output.getvalue())['status'])
        with self.assertRaisesRegex(ValueError, 'either'):
            evidence.verify(paths=['evidence/new/rows.json.gz'], groups=['new-proof'], root=self.root)
        with self.assertRaisesRegex(ValueError, 'group'):
            evidence.restore(groups=['absent'], root=self.root)
        output = StringIO()
        with patch.object(evidence, 'ROOT', self.root), redirect_stdout(output):
            self.assertEqual(0, evidence.main(['verify', '--group', 'new-proof']))
        self.assertEqual('verified', json.loads(output.getvalue())['status'])


if __name__ == '__main__':
    unittest.main()
