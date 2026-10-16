import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/launch-c64bridge.py'


class BridgeLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='sid bridge ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / 'checkout with spaces $literal'
        self.bridge = self.root / '.tools/c64bridge'
        (self.bridge / 'src').mkdir(parents=True)
        (self.bridge / 'src/index.ts').write_text('')
        (self.bridge / 'node_modules').mkdir()
        (self.root / 'scripts').mkdir()
        shutil.copyfile(SCRIPT, self.root / 'scripts/launch-c64bridge.py')
        self.bun = self.root / 'bin with spaces/bun'
        self.bun.parent.mkdir()
        self.bun.write_text('#!' + sys.executable + '\nimport json, os, sys\nprint(json.dumps(dict(argv=sys.argv[1:], cwd=os.getcwd(), env=dict(os.environ))))\n')
        self.bun.chmod(0o755)
        self.vice = self.root / '.tools/vice-headless-3.9/build/src/x64sc'
        self.vice.parent.mkdir(parents=True)
        self.vice.write_text('#!/bin/sh\nexit 99\n')
        self.vice.chmod(0o755)
        self.roms = self.root / 'ROM files $(never-executed)'
        (self.roms / 'C64').mkdir(parents=True)
        self.environment = dict(os.environ, C64BRIDGE_BUN=str(self.bun), VICE_DIRECTORY=str(self.roms))
        self.environment.pop('VICE_BINARY', None)

    def run_launcher(self, *arguments, env=None):
        return subprocess.run([sys.executable, str(self.root / 'scripts/launch-c64bridge.py'), *arguments],
                              cwd=self.temporary.name, env=env or self.environment,
                              capture_output=True, text=True, timeout=10, check=False)

    def test_launch_uses_its_own_checkout_from_an_unrelated_cwd_without_shell_expansion(self):
        result = self.run_launcher()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['argv'], ['src/index.ts'])
        self.assertEqual(report['cwd'], str(self.bridge))
        self.assertEqual(report['env']['VICE_BINARY'], str(self.vice))
        self.assertEqual(report['env']['VICE_DIRECTORY'], str(self.roms))
        self.assertEqual(report['env']['VICE_ARGS'], '-pal +logcolorize')
        self.assertEqual(report['env']['C64_TASK_STATE_FILE'], str(self.root / '.local/c64bridge/tasks.json'))
        self.assertEqual(report['env']['VICE_HEADLESS'], '0')

    def test_explicit_local_binary_and_runtime_overrides_are_preserved(self):
        external = self.root / 'other VICE/x64sc'
        external.parent.mkdir()
        shutil.copyfile(self.vice, external)
        external.chmod(0o755)
        environment = dict(self.environment, VICE_BINARY=str(external), VICE_ARGS='-ntsc +logcolorize', VICE_MODE='ntsc', C64_TASK_STATE_FILE=str(self.root / 'custom state.json'))
        result = self.run_launcher(env=environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        resolved = json.loads(result.stdout)['env']
        self.assertEqual(resolved['VICE_BINARY'], str(external))
        self.assertEqual(resolved['VICE_MODE'], 'ntsc')
        self.assertEqual(resolved['VICE_ARGS'], '-ntsc +logcolorize')
        self.assertEqual(resolved['C64_TASK_STATE_FILE'], environment['C64_TASK_STATE_FILE'])

    def test_check_mode_is_read_only_and_does_not_start_bun_or_vice(self):
        before = set(self.root.rglob('*'))
        result = self.run_launcher('--check')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['command'], [str(self.bun), 'src/index.ts'])
        self.assertNotIn('env', report)
        self.assertEqual(set(self.root.rglob('*')), before)

    def assert_setup_failure(self, expected):
        result = self.run_launcher('--check')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected, result.stderr)

    def test_missing_rom_setting_fails_before_starting_server(self):
        self.environment.pop('VICE_DIRECTORY')
        self.assert_setup_failure('VICE_DIRECTORY')

    def test_relative_local_settings_resolve_against_checkout_not_host_cwd(self):
        environment = dict(self.environment, C64BRIDGE_BUN=str(self.bun.relative_to(self.root)), VICE_DIRECTORY=str(self.roms.relative_to(self.root)), VICE_BINARY=str(self.vice.relative_to(self.root)), C64_TASK_STATE_FILE='custom state/tasks.json')
        result = self.run_launcher('--check', env=environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['command'][0], str(self.bun))
        self.assertEqual(report['settings']['VICE_BINARY'], str(self.vice))
        self.assertEqual(report['settings']['VICE_DIRECTORY'], str(self.roms))
        self.assertEqual(report['settings']['C64_TASK_STATE_FILE'], str(self.root / 'custom state/tasks.json'))

    def test_invalid_resource_directory_fails_before_starting_server(self):
        self.environment['VICE_DIRECTORY'] = str(self.root / 'missing-rom-directory')
        self.assert_setup_failure('C64 resource directory')

    def test_nonexecutable_bun_fails_before_starting_server(self):
        self.bun.chmod(0o644)
        self.assert_setup_failure('executable')

    def test_missing_vice_fails_before_starting_server(self):
        self.vice.unlink()
        self.assert_setup_failure('VICE')

    def test_missing_packages_fail_before_starting_server(self):
        (self.bridge / 'node_modules').rmdir()
        self.assert_setup_failure('bun install')

    def test_templates_share_one_portable_launcher_and_only_require_local_path_edits(self):
        try:
            import tomllib
        except ImportError:
            self.skipTest('TOML parsing requires Python 3.11; launcher supports Python 3.9')
        codex = tomllib.loads((ROOT / 'config/codex.toml').read_text())['mcp_servers']['c64bridge']
        claude = json.loads((ROOT / 'config/claude-mcp.json').read_text())['mcpServers']['c64bridge']
        for template in (codex, claude):
            self.assertEqual(template['command'], 'python3')
            self.assertNotIn('/Users/', json.dumps(template))
            self.assertNotIn('/opt/homebrew/', json.dumps(template))
            arguments = [argument.replace('/ABSOLUTE/PATH/TO/sid-song-crafter', str(self.root)) for argument in template['args']]
            environment = dict(self.environment, **{name: value.replace('/ABSOLUTE/PATH/TO/VICE_DATA', str(self.roms)) for name, value in template['env'].items()})
            result = subprocess.run([template['command'], *arguments], cwd=self.temporary.name,
                                    env=environment, capture_output=True, text=True, timeout=10, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['cwd'], str(self.bridge))
            self.assertEqual(report['argv'], ['src/index.ts'])
            self.assertEqual(report['env']['VICE_DIRECTORY'], str(self.roms))


if __name__ == '__main__':
    unittest.main()
