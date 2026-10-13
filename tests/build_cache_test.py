import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_cache', ROOT / 'scripts/build-cache.py')
cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cache)


class BuildCacheTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.build = self.root / 'build'
        self.build.mkdir()

    def test_lossless_round_trip_and_deterministic_archive_receipt(self):
        original = self.build / 'rows.json'
        data = json.dumps({'rows': ['pitch\u0000\u00ff'] * 100000}).encode() + b'\n'
        original.write_bytes(data)
        receipt, = cache.compact([original], min_bytes=0, root=self.root)
        archive = original.with_name(original.name + '.gz')
        encoded = archive.read_bytes()
        self.assertFalse(original.exists())
        self.assertEqual(data, gzip.decompress(encoded))
        self.assertEqual('build/rows.json', receipt['originalPath'])
        self.assertEqual('build/rows.json.gz', receipt['compressedPath'])
        self.assertEqual(hashlib.sha256(data).hexdigest(), receipt['originalSha256'])
        self.assertEqual(hashlib.sha256(encoded).hexdigest(), receipt['compressedSha256'])
        self.assertEqual(len(data), receipt['originalBytes'])
        self.assertEqual(len(encoded), receipt['compressedBytes'])
        self.assertEqual([receipt], cache.restore([archive], root=self.root))
        self.assertEqual(data, original.read_bytes())
        self.assertFalse(archive.exists())
        cache.compact([original], min_bytes=0, root=self.root)
        self.assertEqual(encoded, archive.read_bytes())

    def test_existing_archive_or_restore_target_is_never_overwritten(self):
        original = self.build / 'rows.json'
        original.write_bytes(b'original')
        archive = self.build / 'rows.json.gz'
        archive.write_bytes(gzip.compress(b'archive'))
        with self.assertRaises(FileExistsError):
            cache.compact([original], min_bytes=0, root=self.root)
        with self.assertRaises(FileExistsError):
            cache.restore([archive], root=self.root)
        self.assertEqual(b'original', original.read_bytes())
        self.assertEqual(b'archive', gzip.decompress(archive.read_bytes()))

    def test_symlinks_are_skipped_and_paths_outside_build_are_rejected(self):
        outside = self.root / 'outside.json'
        outside.write_bytes(b'keep')
        (self.build / 'linked.json').symlink_to(outside)
        (self.build / 'linked-directory').symlink_to(self.root, target_is_directory=True)
        self.assertEqual([], cache.compact([self.build], min_bytes=0, root=self.root))
        self.assertEqual([], cache.compact([self.build / 'linked-directory/outside.json'], min_bytes=0, root=self.root))
        with self.assertRaisesRegex(ValueError, 'build'):
            cache.compact([outside], min_bytes=0, root=self.root)
        with self.assertRaisesRegex(ValueError, 'build'):
            cache.restore([outside.with_suffix('.json.gz')], root=self.root)
        archive = self.build / 'linked.json.gz'
        archive.symlink_to(outside)
        self.assertEqual([], cache.restore([archive], root=self.root))
        self.assertEqual(b'keep', outside.read_bytes())

    def test_recursive_selection_skips_small_and_noneligible_files(self):
        nested = self.build / 'evidence'
        nested.mkdir()
        for name in ('rows.json', 'events.jsonl', 'monitor.log', 'notes.txt'):
            (nested / name).write_bytes(b'x' * 32)
        (nested / 'small.json').write_bytes(b'small')
        (nested / 'reference.sid').write_bytes(b'x' * 32)
        (nested / 'reference.wav').write_bytes(b'x' * 32)
        self.assertEqual([], cache.compact([self.build], root=self.root))
        receipts = cache.compact([self.build, nested / 'rows.json'], min_bytes=16, root=self.root)
        self.assertEqual(4, len(receipts))
        self.assertEqual({'small.json', 'reference.sid', 'reference.wav'},
                         {path.name for path in nested.iterdir() if path.suffix != '.gz'})
        self.assertEqual(1048576, cache.DEFAULT_MIN_BYTES)

    def test_changed_source_is_preserved_and_unpublished_archive_cleaned_up(self):
        original = self.build / 'rows.json'
        original.write_bytes(b'first version')
        verify = cache._verify_gzip

        def change_source(*args):
            result = verify(*args)
            original.write_bytes(b'new writer version')
            return result

        with patch.object(cache, '_verify_gzip', side_effect=change_source):
            with self.assertRaisesRegex(ValueError, 'changed'):
                cache.compact([original], min_bytes=0, root=self.root)
        self.assertEqual(b'new writer version', original.read_bytes())
        self.assertEqual([original], list(self.build.iterdir()))

    def test_invalid_archive_leaves_source_and_target_untouched(self):
        archive = self.build / 'rows.json.gz'
        archive.write_bytes(gzip.compress(b'rows')[:-3])
        with self.assertRaises((EOFError, OSError)):
            cache.restore([archive], root=self.root)
        self.assertEqual([archive], list(self.build.iterdir()))

    def test_target_appearing_during_compression_is_preserved(self):
        original = self.build / 'rows.json'
        original.write_bytes(b'evidence')
        archive = self.build / 'rows.json.gz'
        link = cache.os.link

        def create_competing_target(source, target):
            target.write_bytes(b'other publisher')
            link(source, target)

        with patch.object(cache.os, 'link', side_effect=create_competing_target):
            with self.assertRaises(FileExistsError):
                cache.compact([original], min_bytes=0, root=self.root)
        self.assertEqual(b'evidence', original.read_bytes())
        self.assertEqual(b'other publisher', archive.read_bytes())
        self.assertEqual({original, archive}, set(self.build.iterdir()))


if __name__ == '__main__':
    unittest.main()
