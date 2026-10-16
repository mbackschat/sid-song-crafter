import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_archive', ROOT / 'scripts/archive-build.py')
archive_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive_tool)


class BuildArchiveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.root = self.directory / 'checkout with spaces'
        (self.root / 'build').mkdir(parents=True)
        self.destination = self.directory / 'external archive'
        self.original = b'RIFF\x00WAVE exact bytes\x00\xff' * 200

    def source(self, relative='build/run/cache/one.wav', data=None):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.original if data is None else data)
        raw = path.read_bytes()
        return dict(path=relative, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), reason='Retain a reviewed regenerable cache output locally')

    def selection(self, *rows):
        return dict(version=1, files=list(rows))

    def archive(self, *rows, remove=False, link=False):
        return archive_tool.archive(self.selection(*rows), self.destination, remove=remove, link=link, root=self.root)

    def manifest(self):
        return self.destination / 'manifest.json'

    def test_deduplicated_archive_restores_exact_bytes_and_preserves_existing_identical_file(self):
        a, b = self.source(), self.source('build/other/cache/two.wav')
        report = self.archive(a, b, remove=True)
        self.assertEqual(report['removedPaths'], [a['path'], b['path']])
        self.assertFalse((self.root / a['path']).exists())
        manifest = json.loads(self.manifest().read_text())
        self.assertEqual(len(list((self.destination / 'objects').glob('*.gz'))), 1)
        self.assertEqual(gzip.decompress((self.destination / manifest['files'][0]['object']).read_bytes()), self.original)
        archive_tool.restore(self.manifest(), root=self.root)
        for row in (a, b):
            self.assertEqual((self.root / row['path']).read_bytes(), self.original)
        before = (self.root / a['path']).stat().st_ino
        result = archive_tool.restore(self.manifest(), paths=[a['path']], root=self.root)
        self.assertEqual(result['unchangedPaths'], [a['path']])
        self.assertEqual((self.root / a['path']).stat().st_ino, before)

    def test_archive_without_remove_keeps_sources_and_manifest_records_review_reason(self):
        row = self.source()
        self.archive(row)
        self.assertEqual((self.root / row['path']).read_bytes(), self.original)
        manifest = json.loads(self.manifest().read_text())
        self.assertEqual({key: manifest['files'][0][key] for key in row}, row)

    def test_link_mode_deduplicates_raw_readonly_objects_and_preserves_playback_paths(self):
        a, b = self.source(), self.source('build/listening/two.wav')
        report = self.archive(a, b, link=True)
        manifest = json.loads(self.manifest().read_text())
        self.assertEqual(manifest['compression'], 'none')
        objects = list((self.destination / 'objects').iterdir())
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0].name, a['sha256'] + '.raw')
        self.assertEqual(objects[0].read_bytes(), self.original)
        self.assertEqual(stat.S_IMODE(objects[0].stat().st_mode), 0o444)
        for entry in manifest['files']:
            path = self.root / entry['path']
            self.assertTrue(path.is_symlink())
            self.assertEqual(os.readlink(path), str(self.destination / entry['object']))
            self.assertEqual(path.read_bytes(), self.original)
        self.assertEqual(report['linkedPaths'], [a['path'], b['path']])
        self.assertEqual(report['removedPaths'], [])

    def test_restore_materializes_owned_links_without_changing_archive_or_other_links(self):
        a, b = self.source(), self.source('build/listening/two.wav')
        self.archive(a, b, link=True)
        entry = json.loads(self.manifest().read_text())['files'][0]
        object_path = self.destination / entry['object']
        before = object_path.stat()
        result = archive_tool.restore(self.manifest(), paths=[a['path']], root=self.root)
        target = self.root / a['path']
        self.assertEqual(result['restoredPaths'], [a['path']])
        self.assertFalse(target.is_symlink())
        self.assertEqual(target.read_bytes(), self.original)
        self.assertNotEqual(target.stat().st_ino, before.st_ino)
        after = object_path.stat()
        self.assertEqual((after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
                         (before.st_ino, before.st_mode, before.st_size, before.st_mtime_ns, before.st_ctime_ns))
        target.write_bytes(b'editable restored copy')
        self.assertEqual((self.root / b['path']).read_bytes(), self.original)

    def test_raw_restore_rejects_unrelated_same_byte_symlink_and_corrupt_object(self):
        row = self.source()
        self.archive(row, link=True)
        target = self.root / row['path']
        unrelated = self.directory / 'same-byte-unrelated.wav'
        unrelated.write_bytes(self.original)
        target.unlink()
        target.symlink_to(unrelated)
        with self.assertRaisesRegex(ValueError, 'symlink|Symlink'):
            archive_tool.restore(self.manifest(), root=self.root)
        self.assertEqual(os.readlink(target), str(unrelated))
        entry = json.loads(self.manifest().read_text())['files'][0]
        object_path = self.destination / entry['object']
        target.unlink()
        target.symlink_to(object_path)
        object_path.chmod(0o644)
        object_path.write_bytes(b'x' * row['bytes'])
        object_path.chmod(0o444)
        with self.assertRaisesRegex(ValueError, 'match original'):
            archive_tool.restore(self.manifest(), root=self.root)
        self.assertTrue(target.is_symlink())

    def test_raw_manifest_rejects_gzip_suffix_and_arbitrary_object_path(self):
        row = self.source()
        self.archive(row, link=True)
        manifest = json.loads(self.manifest().read_text())
        for object_path in ('objects/' + row['sha256'] + '.gz', '../outside.raw'):
            manifest['files'][0]['object'] = object_path
            self.manifest().write_text(json.dumps(manifest))
            with self.subTest(object_path=object_path), self.assertRaises(ValueError):
                archive_tool.restore(self.manifest(), root=self.root)
        self.assertTrue((self.root / row['path']).is_symlink())

    def test_link_mode_never_overwrites_a_source_changed_before_atomic_replacement(self):
        row = self.source()
        publish = archive_tool._write_manifest

        def changed(*arguments):
            publish(*arguments)
            (self.root / row['path']).write_bytes(b'concurrent source edit')

        with patch.object(archive_tool, '_write_manifest', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.archive(row, link=True)
        self.assertFalse((self.root / row['path']).is_symlink())
        self.assertEqual((self.root / row['path']).read_bytes(), b'concurrent source edit')
        self.assertTrue(self.manifest().is_file())
        self.assertEqual(list((self.root / row['path']).parent.glob('.*archive-link-*')), [])

    def test_partial_link_failure_retains_manifest_for_links_and_unchanged_originals(self):
        a, b = self.source(), self.source('build/second.wav', b'different')
        replace = os.replace

        def fail_second(source, destination):
            if Path(destination) == self.root / b['path']:
                raise OSError('fixture source replacement denied')
            return replace(source, destination)

        with patch.object(archive_tool.os, 'replace', side_effect=fail_second):
            with self.assertRaisesRegex(ValueError, 'source replacement denied'):
                self.archive(a, b, link=True)
        self.assertTrue((self.root / a['path']).is_symlink())
        self.assertFalse((self.root / b['path']).is_symlink())
        self.assertEqual((self.root / b['path']).read_bytes(), b'different')
        summary = json.loads((self.destination / 'operation.json').read_text())
        self.assertEqual(summary['linkedPaths'], [a['path']])
        archive_tool.restore(self.manifest(), root=self.root)
        self.assertFalse((self.root / a['path']).is_symlink())
        self.assertEqual((self.root / a['path']).read_bytes(), self.original)

    def test_restore_never_overwrites_an_owned_link_replaced_while_materializing(self):
        row = self.source()
        self.archive(row, link=True)
        target = self.root / row['path']
        read_object = archive_tool._read_object

        def replaced(entry, directory, output=None):
            result = read_object(entry, directory, output)
            if output is not None:
                target.unlink()
                target.write_bytes(b'concurrent regular file')
            return result

        with patch.object(archive_tool, '_read_object', side_effect=replaced):
            with self.assertRaisesRegex(ValueError, 'conflict|changed'):
                archive_tool.restore(self.manifest(), root=self.root)
        self.assertEqual(target.read_bytes(), b'concurrent regular file')

    def test_restore_detects_owned_link_identity_change_even_with_same_object_target(self):
        row = self.source()
        self.archive(row, link=True)
        target = self.root / row['path']
        expected = os.readlink(target)
        read_object = archive_tool._read_object

        def replaced(entry, directory, output=None):
            result = read_object(entry, directory, output)
            if output is not None:
                target.unlink()
                target.symlink_to(expected)
            return result

        with patch.object(archive_tool, '_read_object', side_effect=replaced):
            with self.assertRaisesRegex(ValueError, 'changed'):
                archive_tool.restore(self.manifest(), root=self.root)
        self.assertTrue(target.is_symlink())
        self.assertEqual(os.readlink(target), expected)

    def test_raw_restore_rejects_parent_symlinks(self):
        row = self.source()
        self.archive(row, link=True)
        path = self.root / row['path']
        path.unlink()
        path.parent.rmdir()
        outside = self.directory / 'outside-raw'
        outside.mkdir()
        path.parent.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink|Symlink'):
            archive_tool.restore(self.manifest(), root=self.root)
        self.assertEqual(list(outside.iterdir()), [])

    def test_cli_link_mode_publishes_owned_playback_links(self):
        row = self.source()
        selection = self.root / 'selection.json'
        selection.write_text(json.dumps(self.selection(row)))
        with patch('sys.stdout', io.StringIO()):
            self.assertEqual(archive_tool.main(['archive', str(selection), '--archive', str(self.destination), '--link'], root=self.root), 0)
        self.assertTrue((self.root / row['path']).is_symlink())
        self.assertEqual((self.root / row['path']).read_bytes(), self.original)

    def test_link_and_remove_are_mutually_exclusive_in_api_and_cli(self):
        row = self.source()
        with self.assertRaisesRegex(ValueError, 'exclusive|together'):
            self.archive(row, remove=True, link=True)
        self.assertFalse(self.destination.exists())
        with patch('sys.stderr', io.StringIO()), self.assertRaises(SystemExit):
            archive_tool.main(['archive', 'unused.json', '--archive', str(self.destination), '--remove', '--link'], root=self.root)

    def test_complete_selection_is_validated_before_creating_archive(self):
        good, wrong = self.source(), self.source('build/two.wav', b'other')
        wrong['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'match|changed'):
            self.archive(good, wrong, remove=True)
        self.assertFalse(self.destination.exists())
        self.assertTrue((self.root / good['path']).exists())

    def test_traversal_absolute_duplicate_and_symlink_sources_are_rejected(self):
        row = self.source()
        for path in ('build/../outside.wav', '/absolute.wav', 'songs/score.json'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.archive(dict(row, path=path))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.archive(row, row)
        link = self.root / 'build/link.wav'
        link.symlink_to(self.root / row['path'])
        with self.assertRaisesRegex(ValueError, 'Symlink|symlink'):
            self.archive(dict(row, path='build/link.wav'))
        parent = self.root / 'build/linked'
        parent.symlink_to((self.root / row['path']).parent, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink|symlink'):
            self.archive(dict(row, path='build/linked/one.wav'))
        self.assertFalse(self.destination.exists())

    def test_archive_directory_must_be_fresh_and_outside_checkout(self):
        row = self.source()
        for destination in (self.root / 'build/archive', self.root / 'archive', self.directory):
            with self.subTest(destination=destination), self.assertRaises(ValueError):
                archive_tool.archive(self.selection(row), destination, root=self.root)
        self.assertEqual((self.root / row['path']).read_bytes(), self.original)

    def test_nonregular_source_is_rejected_without_reading_it(self):
        fifo = self.root / 'build/fifo'
        os.mkfifo(fifo)
        row = dict(path='build/fifo', bytes=0, sha256=hashlib.sha256(b'').hexdigest(), reason='Invalid nonregular fixture')
        with self.assertRaisesRegex(ValueError, 'regular file'):
            self.archive(row)
        self.assertFalse(self.destination.exists())

    def test_all_objects_are_verified_before_any_source_is_deleted(self):
        a, b = self.source(), self.source('build/second.wav', b'different')
        verify = archive_tool._read_object
        calls = 0

        def corrupt_last(entry, directory, target=None):
            nonlocal calls
            calls += 1
            if calls == 2:
                (directory / entry['object']).write_bytes(b'corrupt gzip')
            return verify(entry, directory, target)

        with patch.object(archive_tool, '_read_object', side_effect=corrupt_last):
            with self.assertRaises(ValueError):
                self.archive(a, b, remove=True)
        self.assertTrue((self.root / a['path']).exists())
        self.assertTrue((self.root / b['path']).exists())

    def test_source_changed_after_manifest_is_preserved_and_archive_remains_recoverable(self):
        row = self.source()
        publish = archive_tool._write_manifest

        def changed(*arguments):
            publish(*arguments)
            (self.root / row['path']).write_bytes(b'concurrent replacement')

        with patch.object(archive_tool, '_write_manifest', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.archive(row, remove=True)
        self.assertEqual((self.root / row['path']).read_bytes(), b'concurrent replacement')
        self.assertTrue(self.manifest().is_file())
        (self.root / row['path']).unlink()
        archive_tool.restore(self.manifest(), root=self.root)
        self.assertEqual((self.root / row['path']).read_bytes(), self.original)

    def test_partial_deletion_failure_keeps_manifest_for_all_original_paths(self):
        a, b = self.source(), self.source('build/second.wav', b'different')
        remove = archive_tool._remove_source

        def fail_second(row, root):
            if row['path'] == b['path']:
                raise OSError('fixture unlink denied')
            return remove(row, root)

        with patch.object(archive_tool, '_remove_source', side_effect=fail_second):
            with self.assertRaisesRegex(ValueError, 'fixture unlink denied'):
                self.archive(a, b, remove=True)
        self.assertFalse((self.root / a['path']).exists())
        self.assertTrue((self.root / b['path']).exists())
        summary = json.loads((self.destination / 'operation.json').read_text())
        self.assertEqual(summary['removedPaths'], [a['path']])
        self.assertFalse(summary['passed'])
        archive_tool.restore(self.manifest(), root=self.root)
        self.assertEqual((self.root / a['path']).read_bytes(), self.original)

    def test_identical_byte_source_replacement_is_not_deleted_after_manifest(self):
        row = self.source()
        publish = archive_tool._write_manifest

        def replaced(*arguments):
            publish(*arguments)
            temporary = self.root / 'build/replacement'
            temporary.write_bytes(self.original)
            os.replace(temporary, self.root / row['path'])

        with patch.object(archive_tool, '_write_manifest', side_effect=replaced):
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.archive(row, remove=True)
        self.assertEqual((self.root / row['path']).read_bytes(), self.original)
        self.assertTrue(self.manifest().is_file())

    def test_restore_preflights_corruption_and_conflicts_before_publishing_any_files(self):
        a, b = self.source(), self.source('build/second.wav', b'different')
        self.archive(a, b, remove=True)
        manifest = json.loads(self.manifest().read_text())
        (self.root / b['path']).write_bytes(b'changed existing file')
        with self.assertRaisesRegex(ValueError, 'conflict|different'):
            archive_tool.restore(self.manifest(), root=self.root)
        self.assertFalse((self.root / a['path']).exists())
        (self.root / b['path']).unlink()
        (self.destination / manifest['files'][1]['object']).write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            archive_tool.restore(self.manifest(), root=self.root)
        self.assertFalse((self.root / a['path']).exists())

    def test_restore_rejects_symlink_targets_objects_and_manifest_traversal(self):
        row = self.source()
        self.archive(row, remove=True)
        target = self.root / row['path']
        outside = self.directory / 'outside'
        outside.write_bytes(self.original)
        target.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'Symlink|symlink'):
            archive_tool.restore(self.manifest(), root=self.root)
        target.unlink()
        manifest = json.loads(self.manifest().read_text())
        object_path = self.destination / manifest['files'][0]['object']
        object_path.unlink()
        object_path.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'Symlink|symlink'):
            archive_tool.restore(self.manifest(), root=self.root)
        manifest['files'][0]['object'] = '../outside'
        self.manifest().write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            archive_tool.restore(self.manifest(), root=self.root)

    def test_selected_restore_rejects_unknown_path_and_restores_only_requested_file(self):
        a, b = self.source(), self.source('build/second.wav', b'different')
        self.archive(a, b, remove=True)
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            archive_tool.restore(self.manifest(), paths=['build/missing.wav'], root=self.root)
        archive_tool.restore(self.manifest(), paths=[b['path']], root=self.root)
        self.assertFalse((self.root / a['path']).exists())
        self.assertEqual((self.root / b['path']).read_bytes(), b'different')

    def test_restore_rejects_symlink_parent_without_writing_outside_build(self):
        row = self.source()
        self.archive(row, remove=True)
        parent = (self.root / row['path']).parent
        parent.rmdir()
        outside = self.directory / 'outside-directory'
        outside.mkdir()
        parent.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink|symlink'):
            archive_tool.restore(self.manifest(), root=self.root)
        self.assertEqual(list(outside.iterdir()), [])

    def test_restore_rejects_valid_gzip_with_wrong_original_hash(self):
        row = self.source()
        self.archive(row, remove=True)
        manifest = json.loads(self.manifest().read_text())
        (self.destination / manifest['files'][0]['object']).write_bytes(gzip.compress(b'x' * row['bytes']))
        with self.assertRaisesRegex(ValueError, 'match original'):
            archive_tool.restore(self.manifest(), root=self.root)
        self.assertFalse((self.root / row['path']).exists())

    def test_partial_restore_keeps_published_files_and_can_be_retried(self):
        a, b = self.source(), self.source('build/second.wav', b'different')
        self.archive(a, b, remove=True)
        restore_entry = archive_tool._restore_entry

        def fail_second(entry, directory, root):
            if entry['path'] == b['path']:
                raise OSError('fixture target publish denied')
            return restore_entry(entry, directory, root)

        with patch.object(archive_tool, '_restore_entry', side_effect=fail_second):
            with self.assertRaisesRegex(ValueError, 'after 1 published files'):
                archive_tool.restore(self.manifest(), root=self.root)
        self.assertEqual((self.root / a['path']).read_bytes(), self.original)
        self.assertFalse((self.root / b['path']).exists())
        self.assertTrue(self.manifest().is_file())
        archive_tool.restore(self.manifest(), root=self.root)
        self.assertEqual((self.root / b['path']).read_bytes(), b'different')

    def test_cli_reports_archive_and_restoration_with_repeatable_path_selection(self):
        a, b = self.source(), self.source('build/second.wav', b'different')
        selection = self.root / 'selection.json'
        selection.write_text(json.dumps(self.selection(a, b)))
        with patch('sys.stdout', io.StringIO()):
            self.assertEqual(archive_tool.main(['archive', str(selection), '--archive', str(self.destination), '--remove'], root=self.root), 0)
            self.assertEqual(archive_tool.main(['restore', str(self.manifest()), '--path', a['path'], '--path', b['path']], root=self.root), 0)
        self.assertEqual((self.root / a['path']).read_bytes(), self.original)


if __name__ == '__main__':
    unittest.main()
