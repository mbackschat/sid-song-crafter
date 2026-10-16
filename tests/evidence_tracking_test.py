import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_LOGS = (
    'evidence/daglish-contrast/wrapper-guards.log',
    'evidence/daglish-contrast/filter-diagnostic/guards.log',
)


class EvidenceTrackingTests(unittest.TestCase):
    def test_global_log_ignore_preserves_canonical_log_discovery_and_private_exclusions(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            repository = directory / 'repository'
            repository.mkdir()
            global_ignore = directory / 'global-ignore'
            global_ignore.write_text('*.log\n')
            environment = {name: value for name, value in os.environ.items() if not name.startswith('GIT_')}

            def git(*arguments):
                return subprocess.check_output(
                    ['git', '-c', f'core.excludesFile={global_ignore}', '-c', 'core.fsmonitor=false', '-C', str(repository), *arguments],
                    env=environment,
                )

            git('init', '-q')
            (repository / '.gitignore').write_bytes((ROOT / '.gitignore').read_bytes())
            canonical = {*CANONICAL_LOGS, 'evidence/future-study/deep/guards.log', 'evidence/guards.log'}
            private = {'build/study/guards.log', '.local/capture.log', '.tools/server.log', 'private/capture.log'}
            for name in canonical | private:
                path = repository / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('Passing test receipt\n')

            discoverable = set(git('ls-files', '--others', '--exclude-standard', '-z').decode().strip('\0').split('\0'))
            ignored = set(git('ls-files', '--others', '--ignored', '--exclude-standard', '-z').decode().strip('\0').split('\0'))
            self.assertEqual(canonical | {'.gitignore'}, discoverable)
            self.assertEqual(private, ignored)

    def test_daglish_guard_logs_match_their_canonical_manifest_bytes(self):
        manifest = json.loads((ROOT / 'evidence/manifest.json').read_text())
        entries = {entry['path']: entry for entry in manifest['files']}
        for name in CANONICAL_LOGS:
            with self.subTest(path=name):
                entry = entries[name]
                data = (ROOT / name).read_bytes()
                digest = hashlib.sha256(data).hexdigest()
                self.assertEqual(entry['bytes'], len(data))
                self.assertEqual(entry['sha256'], digest)
                self.assertEqual(entry['originalBytes'], len(data))
                self.assertEqual(entry['originalSha256'], digest)


if __name__ == '__main__':
    unittest.main()
