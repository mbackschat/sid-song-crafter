import importlib.util
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import wave
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('project_doctor', ROOT / 'scripts/doctor.py')
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)


class ProjectDoctorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.vice = self.root / '.tools/vice-headless-3.9/build/src/x64sc'
        self.renderer = self.root / '.local/bin/render-sid'
        self.roms = self.root / 'roms'

    def write(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def executable(self, path, content):
        self.write(path, '#!/bin/sh\n' + content + '\n')
        path.chmod(0o755)

    def prepare_required(self):
        self.executable(self.vice, 'echo "VICE headless fixture"')
        self.write(self.vice.parent / 'config.h', '#define USE_HEADLESSUI /**/\n/* #undef USE_GTK3UI */\n')
        self.executable(self.renderer, 'echo "Usage: render-sid INPUT.sid OUTPUT.wav SECONDS" >&2\nexit 1')
        self.write(self.root / 'skills/c64-sid/SKILL.md', '---\nname: c64-sid\n---\nSID knowledge\n')
        for name, size in (('basic', 8192), ('kernal', 8192), ('chargen', 4096)):
            path = self.roms / 'C64' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bytes(size))
        deps = self.root / '.tools/test-deps'
        self.write(deps / 'py65/__init__.py', '')
        self.write(deps / 'py65/assembler.py', 'class Assembler: pass\n')
        self.write(deps / 'py65/devices/__init__.py', '')
        self.write(deps / 'py65/devices/mpu6502.py', 'class MPU: pass\n')

    def report(self, **overrides):
        skill = self.root / 'skills/c64-sid/SKILL.md'
        assets = [dict(name='skill:c64-sid', required=True, ok=skill.is_file(), detail='Fixture default skill', path=str(skill))]
        options = dict(root=self.root, vice_data=self.roms, asset_checks=assets)
        options.update(overrides)
        return doctor.check_project(**options)

    def check(self, report, name):
        return next(check for check in report['checks'] if check['name'] == name)

    def prepare_exporter(self, sid_count=1):
        directory = self.root / ('.tools/sid-wizard-exporter' if sid_count == 1 else '.tools/sid-wizard-exporter-2sid')
        self.write(directory / 'exporter.prg', 'exporter fixture')
        self.write(directory / 'exporter.labels', 'label fixture')
        self.write(directory / 'build.json', json.dumps(dict(
            sidCount=sid_count,
            exporterSha256=hashlib.sha256((directory / 'exporter.prg').read_bytes()).hexdigest(),
            labelsSha256=hashlib.sha256((directory / 'exporter.labels').read_bytes()).hexdigest(),
        )))
        return directory

    def test_demo_requires_native_exporter_but_not_vice_midi_or_study_assets(self):
        self.prepare_required()
        directory = self.prepare_exporter()
        self.vice.unlink()
        (self.roms / 'C64/kernal').unlink()
        report = self.report(profile='demo', asset_checks=[])
        self.assertTrue(report['ok'])
        self.assertEqual({check['name'] for check in report['checks']}, {'py65', 'renderer', 'native-exporter'})
        (directory / 'exporter.labels').write_text('changed')
        report = self.report(profile='demo', asset_checks=[])
        self.assertFalse(report['ok'])
        self.assertIn('checksum', self.check(report, 'native-exporter')['detail'].lower())

    def test_demo_reports_missing_and_wrong_chip_count_exporters(self):
        self.prepare_required()
        report = self.report(profile='demo', sid_count=2)
        self.assertFalse(self.check(report, 'native-exporter')['ok'])
        self.assertIn('--sid-count 2', self.check(report, 'native-exporter')['remedy'])
        directory = self.prepare_exporter(sid_count=2)
        manifest = json.loads((directory / 'build.json').read_text())
        manifest['sidCount'] = 1
        self.write(directory / 'build.json', json.dumps(manifest))
        self.assertFalse(self.check(self.report(profile='demo', sid_count=2), 'native-exporter')['ok'])

    def test_score_requires_midi_vice_and_exporter_without_reference_assets(self):
        self.prepare_required()
        self.prepare_exporter()
        self.write(self.root / '.tools/arrangement-deps/mido/__init__.py', '')
        report = self.report(profile='score', asset_checks=[dict(name='reference:unrelated', required=True, ok=False)])
        self.assertTrue(report['ok'])
        self.assertTrue(self.check(report, 'mido')['required'])
        self.vice.unlink()
        self.assertFalse(self.report(profile='score')['ok'])

    def test_samples_need_only_a_readable_shipped_wav_and_do_not_launch_tools(self):
        path = self.root / 'samples/bach-toccata/bach-toccata.wav'
        path.parent.mkdir(parents=True)
        with wave.open(str(path), 'wb') as output:
            output.setparams((1, 2, 44100, 0, 'NONE', 'not compressed'))
            output.writeframes(b'\x01\x00' * 20)
        with patch.object(doctor.subprocess, 'run', side_effect=AssertionError('No tool probes for shipped audio')):
            report = self.report(profile='samples')
        self.assertTrue(report['ok'])
        path.write_text('version https://git-lfs.github.com/spec/v1\n')
        report = self.report(profile='samples')
        self.assertFalse(report['ok'])
        self.assertIn('git lfs', self.check(report, 'sample-audio')['remedy'])

    def test_bridge_profile_is_an_explicit_installation_check_without_launching_server(self):
        self.prepare_required()
        self.write(self.root / '.tools/c64bridge/src/index.ts', '')
        (self.root / '.tools/c64bridge/node_modules').mkdir()
        bun = self.root / 'bin/bun'
        self.executable(bun, 'exit 0')
        with patch.object(doctor.shutil, 'which', return_value=str(bun)):
            report = self.report(profile='bridge')
        self.assertTrue(report['ok'])
        self.assertTrue(self.check(report, 'bridge')['required'])
        self.assertEqual({row['name'] for row in report['checks']}, {'bridge', 'vice', 'vice-roms'})
        self.assertIn('not tested', self.check(report, 'bridge')['detail'])

    def test_bridge_rejects_a_missing_or_nonexecutable_bun_override(self):
        self.prepare_required()
        self.write(self.root / '.tools/c64bridge/src/index.ts', '')
        (self.root / '.tools/c64bridge/node_modules').mkdir()
        bun = self.root / 'bin/bun'
        for present in (False, True):
            if present:
                self.write(bun, 'not executable')
            with patch.dict(doctor.os.environ, {'C64BRIDGE_BUN': str(bun)}):
                self.assertFalse(self.check(self.report(profile='bridge'), 'bridge')['ok'])

    def test_profile_and_sid_count_are_validated_and_cli_identifies_selected_workflow(self):
        for options in ({'profile': 'typo'}, {'profile': 'demo', 'sid_count': 3}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.report(**options)
        output = io.StringIO()
        with patch('sys.stdout', output):
            self.assertEqual(doctor.main(['--root', str(self.root), '--profile', 'demo', '--json']), 1)
        self.assertEqual(json.loads(output.getvalue())['profile'], 'demo')

    def test_available_core_is_ready_when_optional_bridge_and_mido_are_absent(self):
        self.prepare_required()
        report = self.report()
        self.assertTrue(report['ok'])
        for name in ('py65', 'renderer', 'vice', 'vice-roms', 'skill:c64-sid'):
            self.assertTrue(self.check(report, name)['ok'], name)
            self.assertTrue(self.check(report, name)['required'], name)
        self.assertFalse(self.check(report, 'bridge')['required'])
        self.assertFalse(self.check(report, 'bridge')['ok'])
        self.assertFalse(self.check(report, 'mido')['required'])

    def test_missing_required_components_fail_with_setup_remedy(self):
        report = self.report()
        self.assertFalse(report['ok'])
        for name in ('renderer', 'vice', 'vice-roms', 'skill:c64-sid'):
            self.assertFalse(self.check(report, name)['ok'], name)
        self.assertEqual(report['remedy'], 'python3 scripts/setup-project.py')
        self.assertIn('audio-workflow.md', self.check(report, 'renderer')['remedy'])
        self.assertIn('vice-startup-investigation.md', self.check(report, 'vice')['remedy'])

    def test_gui_build_is_rejected_without_launching_the_emulator(self):
        self.prepare_required()
        marker = self.root / 'launched'
        self.executable(self.vice, f'touch "{marker}"')
        self.write(self.vice.parent / 'config.h', '#define USE_GTK3UI 1\n')
        report = self.report()
        self.assertFalse(self.check(report, 'vice')['ok'])
        self.assertIn('GUI', self.check(report, 'vice')['detail'])
        self.assertFalse(marker.exists())

    def test_external_gui_binary_without_build_headers_is_rejected_before_help_launch(self):
        self.prepare_required()
        external = self.root / 'external/x64sc'
        marker = self.root / 'gui-launched'
        self.executable(external, f'touch "{marker}"\necho "VICE GTK3 UI"')
        report = self.report(vice=external)
        self.assertFalse(self.check(report, 'vice')['ok'])
        self.assertFalse(marker.exists())

    def test_renderer_launch_detects_missing_dynamic_dependencies(self):
        self.prepare_required()
        self.executable(self.renderer, 'echo "dyld: Library not loaded: libsidplayfp.dylib" >&2\nexit 127')
        report = self.report()
        self.assertFalse(report['ok'])
        self.assertFalse(self.check(report, 'renderer')['ok'])
        self.assertIn('Library not loaded', self.check(report, 'renderer')['detail'])

    def test_incomplete_rom_directory_is_not_ready(self):
        self.prepare_required()
        (self.roms / 'C64/kernal').write_bytes(b'partial')
        report = self.report()
        self.assertFalse(self.check(report, 'vice-roms')['ok'])
        self.assertIn('kernal', self.check(report, 'vice-roms')['detail'])

    def test_broken_local_py65_is_required_and_dependency_paths_are_used(self):
        self.prepare_required()
        self.write(self.root / '.tools/test-deps/py65/assembler.py', 'import missing_doctor_fixture_dependency\n')
        report = self.report()
        self.assertFalse(self.check(report, 'py65')['ok'])
        self.assertFalse(report['ok'])
        self.assertIn('missing_doctor_fixture_dependency', self.check(report, 'py65')['detail'])
        self.assertIn('uv --cache-dir .local/uv-cache pip install', self.check(report, 'py65')['remedy'])

    def test_external_headless_help_is_bounded_and_timeout_fails_required_check(self):
        self.prepare_required()
        external = self.root / 'external/x64sc'
        self.executable(external, 'echo "Initialising headless ui with args"\nexit 0')
        report = self.report(vice=external)
        self.assertTrue(self.check(report, 'vice')['ok'])
        run = subprocess.run

        def bounded(command, **options):
            if Path(command[0]).resolve() == external.resolve():
                self.assertEqual(options['timeout'], 0.25)
                self.assertIn('-help', command)
                self.assertIn('+saveres', command)
                self.assertNotIn('DISPLAY', options['env'])
                raise subprocess.TimeoutExpired(command, options['timeout'])
            return run(command, **options)

        with patch.object(doctor.subprocess, 'run', side_effect=bounded):
            report = self.report(vice=external, timeout=0.25)
        self.assertFalse(report['ok'])
        self.assertIn('timed out', self.check(report, 'vice')['detail'])

    def test_environment_defaults_and_explicit_path_overrides_are_portable(self):
        self.prepare_required()
        environment = dict(VICE_BINARY=str(self.vice), VICE_DIRECTORY=str(self.roms), SID_RENDERER=str(self.renderer))
        with patch.dict(doctor.os.environ, environment):
            report = doctor.check_project(self.root, asset_checks=[])
            self.assertTrue(report['ok'])
            report = self.report(renderer=self.root / 'missing-renderer')
            self.assertFalse(self.check(report, 'renderer')['ok'])

    def test_asset_hash_failures_keep_required_and_optional_semantics(self):
        self.prepare_required()
        assets = [dict(name='reference:optional', required=False, ok=False, detail='SHA-256 mismatch', path='optional.sid')]
        self.assertTrue(self.report(asset_checks=assets)['ok'])
        assets.append(dict(name='reference:required', required=True, ok=False, detail='SHA-256 mismatch', path='required.sid'))
        self.assertFalse(self.report(asset_checks=assets)['ok'])

    def test_asset_checker_is_loaded_read_only_from_the_installer(self):
        self.prepare_required()
        self.write(self.root / 'scripts/setup-project.py', "def check_assets(root):\n    return [dict(name='reference:fixture', required=True, ok=True, detail='Verified fixture')]\n")
        before = set(self.root.rglob('*'))
        report = self.report(asset_checks=None)
        self.assertTrue(self.check(report, 'reference:fixture')['ok'])
        self.assertEqual(set(self.root.rglob('*')), before)

    def test_json_cli_is_machine_readable_and_returns_nonzero_for_missing_core(self):
        output = io.StringIO()
        with patch('sys.stdout', output):
            status = doctor.main(['--root', str(self.root), '--vice-data', str(self.roms), '--json'])
        report = json.loads(output.getvalue())
        self.assertEqual(status, 1)
        self.assertFalse(report['ok'])
        self.assertIsInstance(report['checks'], list)

    def test_text_cli_prints_specific_repairs_for_missing_runtime_components(self):
        output = io.StringIO()
        with patch('sys.stdout', output):
            self.assertEqual(doctor.main(['--root', str(self.root), '--vice-data', str(self.roms)]), 1)
        self.assertIn('Repair: Build/rebuild render-sid', output.getvalue())
        self.assertIn('Repair: Build genuine headless VICE', output.getvalue())


if __name__ == '__main__':
    unittest.main()
