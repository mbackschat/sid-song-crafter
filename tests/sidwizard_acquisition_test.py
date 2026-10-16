import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('sidwizard_acquisition', ROOT / 'scripts/setup-sidwizard.py')
SETUP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SETUP)


class SIDWizardAcquisitionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.archive = Path(temporary.name) / 'downloads/source.tar.gz'
        self.data = b'pinned complete archive contents\n'
        self.digest = hashlib.sha256(self.data).hexdigest()
        self.url = 'https://example.invalid/source.tar.gz'

    def output_path(self, command):
        return Path(command[command.index('-o') + 1])

    def download(self, command, **kwargs):
        self.output_path(command).write_bytes(self.data)
        return subprocess.CompletedProcess(command, 0)

    def test_partial_failed_download_cannot_poison_a_later_successful_acquisition(self):
        def interrupted(command, **kwargs):
            self.output_path(command).write_bytes(b'partial')
            raise subprocess.CalledProcessError(28, command)

        with patch.object(SETUP.subprocess, 'run', side_effect=interrupted):
            with self.assertRaises(subprocess.CalledProcessError):
                SETUP.acquire(self.archive, self.url, self.digest)
        self.assertFalse(self.archive.exists())
        self.assertEqual([], list(self.archive.parent.iterdir()))

        with patch.object(SETUP.subprocess, 'run', side_effect=self.download):
            SETUP.acquire(self.archive, self.url, self.digest)
        self.assertEqual(self.data, self.archive.read_bytes())
        self.assertEqual([self.archive], list(self.archive.parent.iterdir()))

    def test_one_transient_failure_retries_with_a_fresh_unpublished_temporary_file(self):
        outputs = []

        def interrupted_then_complete(command, **kwargs):
            destination = self.output_path(command)
            outputs.append(destination)
            self.assertEqual(self.archive.parent, destination.parent)
            self.assertNotEqual(self.archive, destination)
            self.assertFalse(self.archive.exists())
            if len(outputs) == 1:
                destination.write_bytes(b'partial')
                raise subprocess.CalledProcessError(28, command)
            return self.download(command, **kwargs)

        with patch.object(SETUP.subprocess, 'run', side_effect=interrupted_then_complete) as run:
            SETUP.acquire(self.archive, self.url, self.digest)
        self.assertEqual(2, run.call_count)
        self.assertEqual(2, len(set(outputs)))
        self.assertEqual(self.data, self.archive.read_bytes())
        self.assertEqual([self.archive], list(self.archive.parent.iterdir()))

    def test_checksum_failure_neither_publishes_nor_retries_untrusted_bytes(self):
        def wrong_archive(command, **kwargs):
            self.output_path(command).write_bytes(b'not the pinned archive')
            return subprocess.CompletedProcess(command, 0)

        with patch.object(SETUP.subprocess, 'run', side_effect=wrong_archive) as run:
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                SETUP.acquire(self.archive, self.url, self.digest)
        self.assertEqual(1, run.call_count)
        self.assertFalse(self.archive.exists())
        self.assertEqual([], list(self.archive.parent.iterdir()))

    def test_existing_changed_archive_is_preserved_without_a_download(self):
        self.archive.parent.mkdir()
        self.archive.write_bytes(b'locally changed archive')
        before = self.archive.stat()
        with patch.object(SETUP.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                SETUP.acquire(self.archive, self.url, self.digest)
        run.assert_not_called()
        self.assertEqual(b'locally changed archive', self.archive.read_bytes())
        self.assertEqual(before.st_ino, self.archive.stat().st_ino)
        self.assertEqual(before.st_mtime_ns, self.archive.stat().st_mtime_ns)

    def test_correct_cached_archive_is_reused_without_a_download(self):
        self.archive.parent.mkdir()
        self.archive.write_bytes(self.data)
        before = self.archive.stat()
        with patch.object(SETUP.subprocess, 'run') as run:
            SETUP.acquire(self.archive, self.url, self.digest)
        run.assert_not_called()
        self.assertEqual(self.data, self.archive.read_bytes())
        self.assertEqual(before.st_ino, self.archive.stat().st_ino)
        self.assertEqual(before.st_mtime_ns, self.archive.stat().st_mtime_ns)

    def test_timeout_failures_have_two_bounded_attempts_and_leave_no_cache_file(self):
        def timed_out(command, **kwargs):
            self.output_path(command).write_bytes(b'partial')
            raise subprocess.TimeoutExpired(command, kwargs['timeout'])

        with patch.object(SETUP.subprocess, 'run', side_effect=timed_out) as run:
            with self.assertRaises(subprocess.TimeoutExpired):
                SETUP.acquire(self.archive, self.url, self.digest)
        self.assertEqual(2, run.call_count)
        for call in run.call_args_list:
            command = call.args[0]
            connect_seconds = float(command[command.index('--connect-timeout') + 1])
            transfer_seconds = float(command[command.index('--max-time') + 1])
            self.assertGreater(connect_seconds, 6.2)
            self.assertLessEqual(connect_seconds, 15)
            self.assertLessEqual(connect_seconds, transfer_seconds)
            self.assertLessEqual(transfer_seconds, 60)
            self.assertGreater(call.kwargs['timeout'], transfer_seconds)
            self.assertLessEqual(call.kwargs['timeout'], 75)
            self.assertNotIn('--retry', command)
        self.assertFalse(self.archive.exists())
        self.assertEqual([], list(self.archive.parent.iterdir()))

    def test_changed_archive_appearing_during_download_is_never_overwritten(self):
        def concurrent_changed_file(command, **kwargs):
            result = self.download(command, **kwargs)
            self.archive.write_bytes(b'another writer changed the archive')
            return result

        with patch.object(SETUP.subprocess, 'run', side_effect=concurrent_changed_file):
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                SETUP.acquire(self.archive, self.url, self.digest)
        self.assertEqual(b'another writer changed the archive', self.archive.read_bytes())
        self.assertEqual([self.archive], list(self.archive.parent.iterdir()))

    def test_correct_archive_appearing_during_download_is_reused(self):
        def concurrent_verified_file(command, **kwargs):
            result = self.download(command, **kwargs)
            self.archive.write_bytes(self.data)
            return result

        with patch.object(SETUP.subprocess, 'run', side_effect=concurrent_verified_file):
            SETUP.acquire(self.archive, self.url, self.digest)
        self.assertEqual(self.data, self.archive.read_bytes())
        self.assertEqual([self.archive], list(self.archive.parent.iterdir()))


if __name__ == '__main__':
    unittest.main()
