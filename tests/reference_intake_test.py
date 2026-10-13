import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import reference_intake


def sid_fixture(*, magic=b'PSID', flags=0x14, speed=0, play=0x1003):
    raw = bytearray(124)
    raw[:4] = magic
    for offset, value in ((4, 2), (6, 124), (10, 0x1000), (12, play),
                          (14, 3), (16, 1), (118, flags)):
        raw[offset:offset + 2] = value.to_bytes(2, 'big')
    raw[18:22] = speed.to_bytes(4, 'big')
    return bytes(raw) + b'\x00\x10' + b'\x60' * 8


class ReferenceIntakeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / 'config').mkdir()
        (self.root / '.local').mkdir()
        self.source = self.root / '.local/source.sid'
        self.source.write_bytes(sid_fixture())
        self.registry = self.root / 'config/local-assets.json'
        self.asset = dict(id='fixture', title='Fixture', credit='Test composer',
                          path='.local/source.sid', url='https://example.test/source.sid',
                          sha256=hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.write_registry()
        self.spec_path = self.root / 'config/intake.json'
        self.spec = dict(schemaVersion=1, selections=[dict(
            assetId='fixture', role='Original source', subtune=2, route='pal-banked',
            calls=4, renderSeconds=0.1)], windows=[dict(id='opening', startSeconds=0,
                                                     endSeconds=0.05)], gapSeconds=0.01)
        self.output = self.root / 'build/intake'

    def write_registry(self):
        self.registry.write_text(json.dumps(dict(version=1, references=[self.asset])))

    def write_spec(self):
        self.spec_path.write_text(json.dumps(self.spec))

    def recipe(self):
        self.write_spec()
        return reference_intake.make_recipe(self.spec_path, root=self.root)

    def install_tools(self):
        scripts = self.root / 'scripts'
        scripts.mkdir()
        for name in reference_intake.CODE_DEPENDENCIES:
            shutil.copy2(ROOT / name, self.root / name)
        library = self.root / reference_intake.RENDER_LIBRARY
        library.parent.mkdir(parents=True)
        library.write_bytes(b'linked-library-fixture')
        shutil.copytree(ROOT / '.tools/test-deps/py65', self.root / '.tools/test-deps/py65')
        renderer = self.root / reference_intake.RENDERER
        renderer.parent.mkdir(parents=True)
        renderer.write_text(
            '#!' + sys.executable + '\n'
            'from array import array\nfrom pathlib import Path\nimport sys, wave\n'
            'assert sys.argv[4] == "--subtune"\n'
            'selection = int(sys.argv[5])\n'
            'with Path("launches.txt").open("a") as log: log.write(str(selection) + "\\n")\n'
            'with wave.open(sys.argv[2], "wb") as out:\n'
            ' out.setparams((1, 2, 44100, 0, "NONE", "not compressed"))\n'
            ' out.writeframes(array("h", [selection * (100 if i % 2 else -100) for i in range(round(float(sys.argv[3]) * 44100))]).tobytes())\n'
            'Path(sys.argv[2] + ".registers.tsv").write_text("time_ms\\tregisters_hex\\n0\\t" + "00" * 32 + "\\n")\n')
        renderer.chmod(0o755)

    def test_pin_mismatch_fails_before_creating_outputs(self):
        self.source.write_bytes(sid_fixture(flags=0x24))
        self.write_spec()
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            reference_intake.run_intake(self.spec_path, self.output, root=self.root)
        self.assertFalse(self.output.exists())

    def test_explicit_selection_reaches_header_audit_and_renderer(self):
        recipe = self.recipe()
        stages = {stage['id']: stage for stage in recipe['stages']}
        for stage_id in ('sourceA-audit', 'sourceA-render'):
            command = stages[stage_id]['command']
            self.assertEqual('2', command[command.index('--subtune') + 1])
        receipt = reference_intake.selection_receipt(self.spec['selections'][0], root=self.root)
        self.assertEqual(2, receipt['header']['selectedSubtune'])
        self.assertEqual(self.asset['url'], receipt['source']['url'])
        self.assertEqual(self.asset['sha256'], receipt['source']['sha256'])
        self.assertIsNone(receipt['listeningReview'])
        self.assertTrue(receipt['evidence']['cpuOrderedStoresRequested'])
        self.assertIn('sourceACpuAudit', recipe['deliverables'])
        self.assertIn('sourceAOrderedStores', recipe['deliverables'])

    def test_source_header_and_fingerprint_describe_the_same_read(self):
        original_read = Path.read_bytes

        def change_after_read(path):
            raw = original_read(path)
            if path == self.source:
                self.source.write_bytes(sid_fixture(flags=0x24))
            return raw

        with patch.object(Path, 'read_bytes', change_after_read):
            receipt = reference_intake.selection_receipt(self.spec['selections'][0], root=self.root)
        self.assertEqual('MOS6581', receipt['header']['sidModelDeclaration'])
        self.assertEqual(receipt['header']['sha256'], receipt['source']['sha256'])
        self.assertEqual(self.asset['sha256'], receipt['source']['sha256'])

    def test_cia_and_rsid_reject_callable_route_and_keep_machine_evidence_distinct(self):
        for raw in (sid_fixture(speed=2), sid_fixture(magic=b'RSID', play=0)):
            with self.subTest(format=raw[:4], speed=raw[18:22]):
                self.source.write_bytes(raw)
                self.asset['sha256'] = hashlib.sha256(raw).hexdigest()
                self.write_registry()
                with self.assertRaisesRegex(ValueError, 'callable'):
                    self.recipe()
                self.spec['selections'][0]['route'] = 'full-machine-render'
                self.spec['selections'][0].pop('calls')
                recipe = self.recipe()
                self.assertFalse(any(stage['id'].endswith('-audit') for stage in recipe['stages']))
                receipt = reference_intake.selection_receipt(self.spec['selections'][0], root=self.root)
                self.assertFalse(receipt['evidence']['cpuCausalProof'])
                self.assertFalse(receipt['evidence']['cpuOrderedStoresRequested'])
                self.assertIn('snapshots', receipt['evidence']['registerObservation'])
                self.assertFalse(receipt['header']['callableProfile']['accepted'])
                self.spec['selections'][0].update(route='pal-banked', calls=4)

    def test_unknown_or_incompatible_clock_model_and_extra_sid_reject(self):
        for flags, extra in ((0x04, 0), (0x10, 0), (0x18, 0), (0x34, 0), (0x14, 0x42)):
            raw = bytearray(sid_fixture(flags=flags))
            raw[122] = extra
            self.source.write_bytes(raw)
            self.asset['sha256'] = hashlib.sha256(raw).hexdigest()
            self.write_registry()
            with self.subTest(flags=flags, extra=extra), self.assertRaisesRegex(ValueError, 'PAL|model|one SID'):
                self.recipe()

    def test_invalid_selection_and_execution_window_bounds_reject(self):
        original = copy.deepcopy(self.spec)
        cases = [('subtune', 0), ('subtune', True), ('subtune', 4),
                 ('calls', 0), ('calls', 40001), ('renderSeconds', 0),
                 ('renderSeconds', float('nan')), ('renderSeconds', 601)]
        for field, value in cases:
            self.spec = copy.deepcopy(original)
            self.spec['selections'][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.recipe()
        self.spec = copy.deepcopy(original)
        self.spec['windows'][0]['endSeconds'] = 0.2
        with self.assertRaisesRegex(ValueError, 'window'):
            self.recipe()

    def test_pair_is_source_contrast_with_explicit_roles_and_bounded_render_links(self):
        second = dict(self.spec['selections'][0], subtune=1, role='Contrasting source')
        self.spec['selections'].append(second)
        recipe = self.recipe()
        self.assertIn('sourceARender', recipe['deliverables'])
        self.assertIn('sourceBRender', recipe['deliverables'])
        self.assertIn('sourceContrast-opening', recipe['deliverables'])
        self.assertNotIn('candidate', json.dumps(recipe))

    def test_window_only_edit_reuses_source_execution_and_selection_edit_invalidates_it(self):
        self.install_tools()
        self.write_spec()
        first = reference_intake.run_intake(self.spec_path, self.output, root=self.root, progress=lambda _: None)
        self.spec['windows'][0]['startSeconds'] = 0.01
        self.write_spec()
        second = reference_intake.run_intake(self.spec_path, self.output, root=self.root, progress=lambda _: None)
        self.assertTrue(all(stage['cacheHit'] for stage in second['stages'][:-1]))
        self.assertFalse(second['stages'][-1]['cacheHit'])
        self.assertEqual(first['deliverables']['sourceARender'], second['deliverables']['sourceARender'])
        self.spec['selections'][0]['subtune'] = 1
        self.write_spec()
        third = reference_intake.run_intake(self.spec_path, self.output, root=self.root, progress=lambda _: None)
        self.assertTrue(all(not stage['cacheHit'] for stage in third['stages']))
        self.assertEqual(['2', '1'], (self.root / 'launches.txt').read_text().splitlines())

    def test_generated_recipe_subdirectory_symlink_cannot_write_outside_build(self):
        self.write_spec()
        target = self.root / 'target'
        target.mkdir()
        self.output.mkdir(parents=True)
        (self.output / 'recipes').symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            reference_intake.run_intake(self.spec_path, self.output, root=self.root)
        self.assertEqual([], list(target.iterdir()))

    def test_declared_dependencies_cache_and_invalidate_changed_renderer(self):
        self.install_tools()
        self.spec['selections'][0]['role'] = 'Literal {root} and {"part": "two"}'
        self.write_spec()
        first = reference_intake.run_intake(self.spec_path, self.output, root=self.root, progress=lambda _: None)
        second = reference_intake.run_intake(self.spec_path, self.output, root=self.root, progress=lambda _: None)
        self.assertTrue(all(stage['cacheHit'] for stage in second['stages']))
        self.assertEqual(first['deliverables'], second['deliverables'])
        self.assertEqual(['2'], (self.root / 'launches.txt').read_text().splitlines())
        receipt = json.loads(Path(first['deliverables']['sourceAReceipt']).read_text())
        self.assertEqual(self.spec['selections'][0]['role'], receipt['selection']['role'])
        renderer = self.root / reference_intake.RENDERER
        renderer.write_text(renderer.read_text() + '\n# changed executable fixture\n')
        third = reference_intake.run_intake(self.spec_path, self.output, root=self.root, progress=lambda _: None)
        by_id = {stage['id']: stage for stage in third['stages']}
        self.assertTrue(by_id['sourceA-selection']['cacheHit'])
        self.assertTrue(by_id['sourceA-audit']['cacheHit'])
        self.assertFalse(by_id['sourceA-render']['cacheHit'])
        self.assertEqual(['2', '2'], (self.root / 'launches.txt').read_text().splitlines())
        self.assertTrue(all(Path(path).is_file() for path in first['deliverables'].values()))

    def test_output_outside_build_or_through_symlink_is_rejected(self):
        self.write_spec()
        for output in (self.root / 'outside', self.root / 'build/../outside'):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, 'build|traversal'):
                reference_intake.run_intake(self.spec_path, output, root=self.root)
        target = self.root / 'target'
        target.mkdir()
        (self.root / 'build').symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            reference_intake.run_intake(self.spec_path, self.output, root=self.root)
        self.assertEqual([], list(target.iterdir()))


if __name__ == '__main__':
    unittest.main()
