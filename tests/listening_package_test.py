import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import listening_package


class ListeningPackageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.output = self.root / 'build' / 'package'
        self.recipe_path = self.root / 'recipe.json'
        (self.root / 'source.txt').write_text('SID bytes')
        (self.root / 'window.txt').write_text('8:16')
        self.write_tool('build', "target = Path(sys.argv[1]) / 'candidate'\ntarget.mkdir()\n(target / 'song.sid').write_bytes(Path('source.txt').read_bytes())")
        self.write_tool('render', "Path(sys.argv[1], 'song.wav').write_bytes(b'WAV ' + Path(sys.argv[2]).read_bytes())")
        self.write_tool('compare', "Path(sys.argv[1], 'comparison.wav').write_bytes(Path(sys.argv[2]).read_bytes() + Path('window.txt').read_bytes())")
        self.recipe = {
            'schemaVersion': 1,
            'stages': [
                {'id': 'build', 'command': ['{python}', 'build.py', '{out}'],
                 'inputs': ['build.py', 'source.txt'], 'outputs': ['candidate/song.sid'], 'timeoutSeconds': 5},
                {'id': 'render', 'command': ['{python}', 'render.py', '{out}', '{stage:build}/candidate/song.sid'],
                 'inputs': ['render.py', '{stage:build}/candidate/song.sid'], 'outputs': ['song.wav'], 'timeoutSeconds': 5},
                {'id': 'compare', 'command': ['{python}', 'compare.py', '{out}', '{stage:render}/song.wav'],
                 'inputs': ['compare.py', 'window.txt', '{stage:render}/song.wav'], 'outputs': ['comparison.wav'], 'timeoutSeconds': 5},
            ],
            'deliverables': {'fullCandidate': '{stage:render}/song.wav', 'opening': '{stage:compare}/comparison.wav'},
        }

    def write_tool(self, name, body):
        (self.root / f'{name}.py').write_text(
            'from pathlib import Path\nimport sys\n'
            f"with Path('launches.txt').open('a') as launches:\n    launches.write('{name}\\n')\n"
            + body + '\n')

    def run_package(self):
        self.recipe_path.write_text(json.dumps(self.recipe))
        return listening_package.run_recipe(self.recipe_path, self.output, root=self.root, progress=lambda _: None)

    def launches(self):
        return (self.root / 'launches.txt').read_text().splitlines()

    def test_hot_cache_launches_no_process_and_reports_timings_and_portable_deliverables(self):
        first = self.run_package()
        with patch.object(listening_package.subprocess, 'Popen', side_effect=AssertionError('cache launched a process')):
            second = self.run_package()
        self.assertEqual(self.launches(), ['build', 'render', 'compare'])
        self.assertEqual(second['status'], 'completed')
        self.assertEqual(second['deliverables'], first['deliverables'])
        self.assertTrue(all(stage['cacheHit'] for stage in second['stages']))
        self.assertTrue(all(stage['wallSeconds'] >= 0 and stage['executionSeconds'] == 0 for stage in second['stages']))
        self.assertGreater(second['wallSeconds'], 0)
        self.assertEqual(json.loads((self.output / 'run.json').read_text()), second)
        index = (self.output / 'listening.md').read_text()
        self.assertIn('[fullCandidate](cache/render/', index)
        self.assertNotIn(str(self.root), index)
        self.assertTrue(Path(second['deliverables']['opening']).is_file())

    def test_changed_window_reruns_only_comparison(self):
        first = self.run_package()
        (self.root / 'window.txt').write_text('16:24')
        second = self.run_package()
        self.assertEqual(self.launches(), ['build', 'render', 'compare', 'compare'])
        self.assertEqual([stage['cacheHit'] for stage in second['stages']], [True, True, False])
        self.assertEqual(first['stages'][1]['attemptDirectory'], second['stages'][1]['attemptDirectory'])

    def test_changed_build_tool_with_identical_sid_bytes_reuses_downstream_outputs(self):
        first = self.run_package()
        with (self.root / 'build.py').open('a') as tool:
            tool.write('# Another implementation producing the same bytes.\n')
        second = self.run_package()
        self.assertEqual(self.launches(), ['build', 'render', 'compare', 'build'])
        self.assertEqual([stage['cacheHit'] for stage in second['stages']], [False, True, True])
        self.assertNotEqual(first['stages'][0]['attemptDirectory'], second['stages'][0]['attemptDirectory'])
        self.assertEqual(first['deliverables'], second['deliverables'])

    def test_directory_input_hashes_file_contents_and_rejects_symlinks(self):
        dependency = self.root / 'dependency'
        dependency.mkdir()
        (dependency / 'module.py').write_text('version = 1\n')
        self.recipe['stages'][0]['inputs'].append('dependency')
        self.run_package()
        (dependency / 'module.py').write_text('version = 2\n')
        self.assertEqual([stage['cacheHit'] for stage in self.run_package()['stages']], [False, True, True])
        (dependency / 'link.py').symlink_to(dependency / 'module.py')
        with self.assertRaisesRegex(listening_package.PackageError, 'symlink'):
            self.run_package()

    def test_explicit_library_input_follows_symlinks_and_reuses_equal_content(self):
        with tempfile.TemporaryDirectory() as external:
            directory = Path(external).resolve()
            (directory / 'first.dylib').write_bytes(b'library version 1')
            (directory / 'same.dylib').write_bytes(b'library version 1')
            (directory / 'second.dylib').write_bytes(b'library version 2')
            link = directory / 'stable.dylib'
            link.symlink_to(directory / 'first.dylib')
            self.recipe['stages'][0]['inputs'].append(str(link))
            self.run_package()
            link.unlink()
            link.symlink_to(directory / 'same.dylib')
            self.assertTrue(self.run_package()['stages'][0]['cacheHit'])
            link.unlink()
            link.symlink_to(directory / 'second.dylib')
            self.assertEqual([stage['cacheHit'] for stage in self.run_package()['stages']], [False, True, True])

    def test_executable_contents_are_fingerprinted_without_explicit_input(self):
        executable = self.root / 'emit'
        executable.write_text('#!/bin/sh\nprintf bytes > "$1/clip.wav"\n')
        executable.chmod(0o755)
        self.recipe['stages'] = [{'id': 'emit', 'command': ['{root}/emit', '{out}'], 'inputs': [],
                                 'outputs': ['clip.wav'], 'timeoutSeconds': 5}]
        self.recipe['deliverables'] = {'opening': '{stage:emit}/clip.wav'}
        first = self.run_package()
        with executable.open('a') as tool:
            tool.write('# Changed executable, same emitted bytes.\n')
        second = self.run_package()
        self.assertFalse(second['stages'][0]['cacheHit'])
        self.assertNotEqual(first['stages'][0]['attemptDirectory'], second['stages'][0]['attemptDirectory'])
        self.assertTrue(self.run_package()['stages'][0]['cacheHit'])

    def test_receipt_retains_reviewable_fingerprint_and_expanded_command(self):
        report = self.run_package()
        stage = report['stages'][1]
        receipt = json.loads((Path(stage['attemptDirectory']) / 'success.json').read_text())
        fingerprint = receipt['fingerprint']
        canonical = json.dumps(fingerprint, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), receipt['key'])
        self.assertEqual(fingerprint['command'], self.recipe['stages'][1]['command'])
        self.assertEqual(fingerprint['inputs'][1]['path'], '{stage:build}/candidate/song.sid')
        self.assertEqual(receipt['command'][2], stage['attemptDirectory'])
        self.assertIn('executableSha256', fingerprint['runtime']['python'])

    def test_corrupt_or_missing_output_reruns_fresh_and_preserves_other_attempts(self):
        first = self.run_package()
        original = Path(first['stages'][0]['attemptDirectory'])
        sid = original / 'candidate' / 'song.sid'
        sid.write_bytes(b'corrupted')
        second = self.run_package()
        self.assertEqual([stage['cacheHit'] for stage in second['stages']], [False, True, True])
        self.assertEqual(sid.read_bytes(), b'corrupted')
        current = Path(second['stages'][0]['attemptDirectory'])
        self.assertNotEqual(current, original)
        (current / 'candidate' / 'song.sid').unlink()
        third = self.run_package()
        self.assertFalse(third['stages'][0]['cacheHit'])
        self.assertFalse((current / 'candidate' / 'song.sid').exists())
        self.assertTrue(original.is_dir())

    def test_nonzero_exit_records_failure_without_success_receipt_or_stale_index(self):
        first = self.run_package()
        old_audio = Path(first['deliverables']['opening'])
        old_bytes = old_audio.read_bytes()
        self.write_tool('compare', "Path(sys.argv[1], 'comparison.wav').write_text('partial')\nraise SystemExit(7)")
        for _ in range(2):
            with self.assertRaisesRegex(listening_package.PackageError, 'exit status 7'):
                self.run_package()
            failed = json.loads((self.output / 'run.json').read_text())
            stage = failed['stages'][-1]
            self.assertEqual(failed['status'], 'failed')
            self.assertFalse((Path(stage['attemptDirectory']) / 'success.json').exists())
            self.assertEqual(stage['returnCode'], 7)
        self.assertEqual(self.launches(), ['build', 'render', 'compare', 'compare', 'compare'])
        self.assertEqual(old_audio.read_bytes(), old_bytes)
        self.assertNotIn('[opening]', (self.output / 'listening.md').read_text())

    def test_timeout_kills_descendants_and_records_timing(self):
        self.write_tool('build', "import subprocess\nimport time\nsubprocess.Popen([sys.executable, '-c', \"import time; from pathlib import Path; time.sleep(.5); Path('orphan.txt').write_text('alive')\"])\ntime.sleep(5)")
        self.recipe['stages'][0]['timeoutSeconds'] = .15
        started = time.monotonic()
        with self.assertRaisesRegex(listening_package.PackageError, 'timed out'):
            self.run_package()
        self.assertLess(time.monotonic() - started, 2)
        failed = json.loads((self.output / 'run.json').read_text())
        self.assertGreaterEqual(failed['stages'][0]['executionSeconds'], .15)
        time.sleep(.6)
        self.assertFalse((self.root / 'orphan.txt').exists())

    def test_missing_declared_output_or_changed_input_prevents_success_receipt(self):
        for body, message in (("pass", 'missing'),
                              ("Path(sys.argv[1], 'candidate').mkdir()\nPath(sys.argv[1], 'candidate/song.sid').write_text('ok')\nPath('source.txt').write_text('mutated')", 'changed during')):
            with self.subTest(message=message):
                self.write_tool('build', body)
                with self.assertRaisesRegex(listening_package.PackageError, message):
                    self.run_package()
                failed = json.loads((self.output / 'run.json').read_text())
                self.assertFalse((Path(failed['stages'][0]['attemptDirectory']) / 'success.json').exists())

    def test_read_only_stage_with_no_outputs_is_cached_and_env_is_expanded(self):
        self.write_tool('check', "import os\nassert os.environ['SOURCE'] == str(Path.cwd() / 'source.txt')")
        self.recipe['stages'] = [{'id': 'check', 'command': ['{python}', 'check.py'], 'inputs': ['check.py', 'source.txt'],
                                 'outputs': [], 'timeoutSeconds': 5, 'env': {'SOURCE': '{root}/source.txt'}}]
        self.recipe['deliverables'] = {}
        self.run_package()
        self.assertTrue(self.run_package()['stages'][0]['cacheHit'])
        self.assertEqual(self.launches(), ['check'])

    def test_later_stage_changing_earlier_input_rejects_package_including_cache_hits(self):
        for source in ('source.txt', 'build.py'):
            with self.subTest(source=source):
                first = self.run_package()
                old_audio = Path(first['deliverables']['opening'])
                old_bytes = old_audio.read_bytes()
                self.write_tool('render',
                                "Path(sys.argv[1], 'song.wav').write_bytes(b'WAV ' + Path(sys.argv[2]).read_bytes())\n"
                                f"with Path({source!r}).open('a') as source:\n    source.write('\\n# changed')")
                with self.assertRaisesRegex(listening_package.PackageError, 'build:.*changed.*completion'):
                    self.run_package()
                failed = json.loads((self.output / 'run.json').read_text())
                self.assertTrue(failed['stages'][0]['cacheHit'])
                self.assertEqual(failed['status'], 'failed')
                self.assertEqual(failed['deliverables'], {})
                self.assertNotIn('[opening]', (self.output / 'listening.md').read_text())
                self.assertEqual(old_audio.read_bytes(), old_bytes)
                self.write_tool('render', "Path(sys.argv[1], 'song.wav').write_bytes(b'WAV ' + Path(sys.argv[2]).read_bytes())")

    def test_later_stage_changing_earlier_executable_rejects_package(self):
        executable = self.root / 'emit'
        executable.write_text('#!/bin/sh\nmkdir "$1/candidate"\ncp source.txt "$1/candidate/song.sid"\n')
        executable.chmod(0o755)
        self.recipe['stages'][0]['command'] = ['{root}/emit', '{out}']
        self.write_tool('render',
                        "Path(sys.argv[1], 'song.wav').write_bytes(b'WAV ' + Path(sys.argv[2]).read_bytes())\n"
                        "with Path('emit').open('a') as executable:\n    executable.write('\\n# changed')")
        with self.assertRaisesRegex(listening_package.PackageError, 'build: executable changed before package completion'):
            self.run_package()
        failed = json.loads((self.output / 'run.json').read_text())
        self.assertEqual(failed['status'], 'failed')
        self.assertEqual(failed['deliverables'], {})

    def test_changed_runner_runtime_rejects_package(self):
        runtime = listening_package._runtime_fingerprint()
        changed = {**runtime, 'runnerVersion': runtime['runnerVersion'] + 1}
        with patch.object(listening_package, '_runtime_fingerprint', side_effect=[runtime] * 4 + [changed]):
            with self.assertRaisesRegex(listening_package.PackageError, 'runtime changed before package completion'):
                self.run_package()
        failed = json.loads((self.output / 'run.json').read_text())
        self.assertEqual(failed['status'], 'failed')
        self.assertEqual(failed['deliverables'], {})

    def test_executable_changed_before_launch_cannot_leave_a_reusable_receipt(self):
        executable = self.root / 'emit'
        original = '#!/bin/sh\nprintf old > "$1/clip.wav"\n'
        executable.write_text(original)
        executable.chmod(0o755)
        self.recipe['stages'] = [{'id': 'emit', 'command': ['{root}/emit', '{out}'], 'inputs': [],
                                 'outputs': ['clip.wav'], 'timeoutSeconds': 5}]
        self.recipe['deliverables'] = {'opening': '{stage:emit}/clip.wav'}
        self.recipe_path.write_text(json.dumps(self.recipe))

        def change_before_launch(message):
            if message == 'emit: starting':
                executable.write_text(original.replace('printf old', 'printf new'))

        with self.assertRaisesRegex(listening_package.PackageError, 'executable changed'):
            listening_package.run_recipe(self.recipe_path, self.output, root=self.root, progress=change_before_launch)
        failed = json.loads((self.output / 'run.json').read_text())
        self.assertFalse((Path(failed['stages'][0]['attemptDirectory']) / 'success.json').exists())
        executable.write_text(original)
        restored = self.run_package()
        self.assertFalse(restored['stages'][0]['cacheHit'])
        self.assertEqual(Path(restored['deliverables']['opening']).read_text(), 'old')

    def test_runtime_changed_during_stage_cannot_leave_a_reusable_receipt(self):
        runtime = listening_package._runtime_fingerprint()
        changed = {**runtime, 'runnerVersion': runtime['runnerVersion'] + 1}
        with patch.object(listening_package, '_runtime_fingerprint', side_effect=[runtime, changed]):
            with self.assertRaisesRegex(listening_package.PackageError, 'runtime changed'):
                self.run_package()
        failed = json.loads((self.output / 'run.json').read_text())
        self.assertFalse((Path(failed['stages'][0]['attemptDirectory']) / 'success.json').exists())

    def test_invalid_schema_paths_and_forward_dependencies_launch_nothing(self):
        cases = [
            ('schemaVersion', lambda: self.recipe.update(schemaVersion=2)),
            ('unique', lambda: self.recipe['stages'][1].update(id='build')),
            ('id', lambda: self.recipe['stages'][0].update(id='../escape')),
            ('relative', lambda: self.recipe['stages'][0].update(outputs=['../escape.sid'])),
            ('relative', lambda: self.recipe['stages'][0].update(outputs=['/escape.sid'])),
            ('input', lambda: self.recipe['stages'][0].update(inputs=['../escape.txt'])),
            ('input', lambda: self.recipe['stages'][0].update(inputs=['{out}/source.txt'])),
            ('previous', lambda: self.recipe['stages'][0].update(inputs=['{stage:render}/song.wav'])),
            ('previous', lambda: self.recipe['stages'][0].update(command=['{python}', '{stage:render}/script.py'])),
            ('previous', lambda: self.recipe['stages'][0].update(env={'FILE': '{stage:render}/song.wav'})),
            ('placeholder', lambda: self.recipe['stages'][0].update(command=['{unknown}'])),
            ('timeoutSeconds', lambda: self.recipe['stages'][0].update(timeoutSeconds=0)),
            ('declared', lambda: self.recipe.update(deliverables={'bad': '{stage:build}/unknown.sid'})),
        ]
        original = json.loads(json.dumps(self.recipe))
        for message, mutate in cases:
            with self.subTest(message=message):
                self.recipe = json.loads(json.dumps(original))
                mutate()
                with self.assertRaisesRegex(listening_package.PackageError, message):
                    self.run_package()
                self.assertFalse((self.root / 'launches.txt').exists())

    def test_output_must_stay_under_build_without_symlink_ancestors(self):
        self.output = self.root / 'outside'
        with self.assertRaisesRegex(listening_package.PackageError, 'build'):
            self.run_package()
        target = self.root / 'target'
        target.mkdir()
        (self.root / 'build').symlink_to(target)
        self.output = self.root / 'build' / 'linked'
        with self.assertRaisesRegex(listening_package.PackageError, 'symlink'):
            self.run_package()
        self.assertEqual(list(target.iterdir()), [])

    def test_symlink_output_is_not_cached_or_followed(self):
        self.write_tool('build', "Path(sys.argv[1], 'candidate').mkdir()\nPath(sys.argv[1], 'candidate/song.sid').symlink_to(Path.cwd() / 'source.txt')")
        with self.assertRaisesRegex(listening_package.PackageError, 'symlink'):
            self.run_package()
        self.assertEqual((self.root / 'source.txt').read_text(), 'SID bytes')

    def test_cli_prints_stage_timings_and_deliverable_paths(self):
        (ROOT / 'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='listening-cli-', dir=ROOT / 'build') as temporary:
            directory = Path(temporary)
            recipe = directory / 'recipe.json'
            recipe.write_text(json.dumps({'schemaVersion': 1, 'stages': [{
                'id': 'clip', 'command': ['{python}', '-c', "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('ok')", '{out}/clip.wav'],
                'inputs': [], 'outputs': ['clip.wav'], 'timeoutSeconds': 5,
            }], 'deliverables': {'opening': '{stage:clip}/clip.wav'}}))
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/listening-package.py'), str(recipe),
                                     '--output', str(directory / 'package')], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('clip: run', result.stdout)
            self.assertIn('opening:', result.stdout)
            self.assertIn('listening.md', result.stdout)


if __name__ == '__main__':
    unittest.main()
