import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('project_setup', ROOT / 'scripts/setup-project.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class ProjectSetupTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.data = b'PSID' + bytes(124)
        self.reference = dict(id='reference', default=True, path='.local/reference.sid', url='https://example.org/reference.sid', sha256=hashlib.sha256(self.data).hexdigest())
        self.skill_data = b'---\nname: test\n---\n'
        self.skill = dict(id='test', default=True, path='skills/test', activation='.agents/skills/test', checkout='.tools/upstream', repository='https://github.com/example/skills', revision='a' * 40, files=[dict(source='test/SKILL.md', path='SKILL.md', sha256=hashlib.sha256(self.skill_data).hexdigest())])
        self.manifest = dict(version=1, references=[self.reference], skills=[self.skill])

    def test_verified_download_is_reused_without_network(self):
        with patch.object(setup, 'download', return_value=self.data) as fetch:
            setup.install_reference(self.root, self.reference)
            setup.install_reference(self.root, self.reference, offline=True)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual((self.root / self.reference['path']).read_bytes(), self.data)

    def test_bad_or_interrupted_download_never_leaves_an_installed_file(self):
        with patch.object(setup, 'download', return_value=b'wrong'):
            with self.assertRaisesRegex(ValueError, 'checksum'):
                setup.install_reference(self.root, self.reference)
        self.assertFalse((self.root / self.reference['path']).exists())
        with patch.object(setup, 'download', side_effect=OSError('network interrupted')):
            with self.assertRaises(OSError):
                setup.install_reference(self.root, self.reference)
        self.assertFalse((self.root / self.reference['path']).exists())

    def test_modified_cache_is_preserved_and_rejected(self):
        target = self.root / self.reference['path']
        target.parent.mkdir(parents=True)
        target.write_bytes(b'user version')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            setup.install_reference(self.root, self.reference)
        self.assertEqual(target.read_bytes(), b'user version')

    def test_skill_install_is_verified_and_activated_without_network_on_repeat(self):
        with patch.object(setup, 'skill_source', return_value=self.skill_data) as fetch:
            setup.install_skill(self.root, self.skill)
            setup.install_skill(self.root, self.skill, offline=True)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual((self.root / self.skill['activation']).resolve(), (self.root / self.skill['path']).resolve())
        self.assertTrue(all(row['ok'] for row in setup.check_assets(self.root, dict(version=1, references=[], skills=[self.skill]))))

    def test_skill_failure_keeps_partial_content_out_of_active_destination(self):
        self.skill['files'].append(dict(source='test/reference.md', path='reference.md', sha256='b' * 64))
        with patch.object(setup, 'skill_source', side_effect=[self.skill_data, OSError('offline')]):
            with self.assertRaises(OSError):
                setup.install_skill(self.root, self.skill)
        self.assertFalse((self.root / self.skill['path']).exists())
        self.assertFalse((self.root / self.skill['activation']).exists())

    def test_unsafe_paths_and_existing_unrelated_activation_are_rejected(self):
        for name in ('../outside.sid', '/tmp/outside.sid'):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'path'):
                setup.safe_path(self.root, name)
        (self.root / 'outside').symlink_to(self.root.parent, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'path'):
            setup.safe_path(self.root, 'outside/file')
        target = self.root / self.skill['activation']
        target.parent.mkdir(parents=True)
        target.mkdir()
        with patch.object(setup, 'skill_source', return_value=self.skill_data):
            with self.assertRaisesRegex(ValueError, 'activation'):
                setup.install_skill(self.root, self.skill)
        self.assertTrue(target.is_dir())

    def test_missing_optional_assets_do_not_become_required_and_check_is_read_only(self):
        self.skill['default'] = False
        checks = setup.check_assets(self.root, self.manifest)
        self.assertEqual([(c['required'], c['ok']) for c in checks], [(True, False), (False, False)])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_pinned_manifest_rejects_unknown_and_unpinned_selections(self):
        self.assertEqual([item['id'] for _, item in setup.select_assets(self.manifest)], ['reference', 'test'])
        self.skill['default'] = False
        self.assertEqual([item['id'] for _, item in setup.select_assets(self.manifest)], ['reference'])
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            setup.select_assets(self.manifest, include=['typo'])
        self.skill['revision'] = 'main'
        with self.assertRaisesRegex(ValueError, 'revision'):
            setup.validate_manifest(self.manifest)

    def test_claude_code_discovers_the_shared_skill_activation_directory(self):
        # Codex reads .agents/skills and Claude Code reads .claude/skills; one relative
        # directory link keeps every manifest activation visible to both hosts.
        link = ROOT / '.claude/skills'
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), '../.agents/skills')
        manifest = json.loads((ROOT / 'config/local-assets.json').read_text())
        for skill in manifest['skills']:
            with self.subTest(skill=skill['id']):
                self.assertEqual(link.resolve(), (ROOT / PurePosixPath(skill['activation']).parent).resolve())


if __name__ == '__main__':
    unittest.main()
