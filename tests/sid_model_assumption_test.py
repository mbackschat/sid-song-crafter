import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid
from psid_profile import psid_profile


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / 'scripts' / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


trace = load_script('trace-sid-program.py')
vice_trace = load_script('trace-sid-vice.py')
VICE = ROOT / '.tools/vice-headless-3.9/build/src/x64sc'
VICE_DATA = Path('/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice')


def fixture(flags=4):
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 2), (6, 124), (8, 0x1000), (10, 0x1000),
                          (12, 0x1006), (14, 1), (16, 1), (118, flags)):
        header[offset:offset + 2] = value.to_bytes(2, 'big')
    return bytes(header) + bytes.fromhex('a90f8d18d460a9518d04d460')


class SidModelAssumptionTest(unittest.TestCase):
    def test_unknown_header_stays_intact_and_assumption_is_explicit_in_every_report(self):
        data = fixture()
        original = bytes(data)
        for model, flags in (('MOS6581', 0x14), ('MOS8580', 0x24)):
            with self.subTest(model=model):
                expected = {'declared': 'unknown', 'assumed': model}
                options = dict(profile='pal-banked', subtune=1, assume_sid_model=model)
                profile = psid_profile(data, **options)
                self.assertEqual(expected, profile['sidModelAssumption'])
                self.assertEqual(model, profile['sidModel'])
                report, writes = audit_psid(data, 2, **options)
                _, declared_writes = audit_psid(fixture(flags), 2, profile='pal-banked', subtune=1)
                self.assertEqual(declared_writes, writes)
                self.assertEqual(expected, report['sidModelAssumption'])
                self.assertEqual(hashlib.sha256(data).hexdigest(), report['sourceSha256'])
                observed = trace.trace_program(data, first_call=0, last_call=1, **options)
                self.assertEqual(expected, observed['audit']['sidModelAssumption'])
                self.assertEqual(expected, vice_trace.psid_profile(data, **options)['sidModelAssumption'])
                self.assertEqual(original, data)

    def test_assumption_cannot_override_a_declaration_or_relax_other_header_guards(self):
        with self.assertRaises(ValueError):
            psid_profile(fixture(), profile='pal-banked', subtune=1)
        cases = [dict(data=fixture(), profile='strict', model='MOS6581'),
                 dict(data=fixture(), profile='pal-banked', model='6581')]
        for flags in (0x14, 0x24, 0x34, 0, 8, 12, 5, 6, 0x104):
            cases.append(dict(data=fixture(flags), profile='pal-banked', model='MOS6581'))
        for offset, value in ((5, 3), (21, 1), (122, 0x42)):
            data = bytearray(fixture())
            data[offset] = value
            cases.append(dict(data=bytes(data), profile='pal-banked', model='MOS6581'))
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                psid_profile(case['data'], profile=case['profile'], subtune=1,
                             assume_sid_model=case['model'])
        with self.assertRaises(ValueError):
            trace.trace_program(fixture(), first_call=0, last_call=0,
                                profile='flashdance-diagnostic', assume_sid_model='MOS6581')

    def test_cpu_and_instruction_clis_retain_assumption_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / 'source.sid'
            source.write_bytes(fixture())
            for script, extra in (('psid_audit.py', ['--ticks', '2']),
                                  ('trace-sid-program.py', ['--first-call', '0', '--last-call', '1'])):
                output = directory / (script + '.json')
                result = subprocess.run([sys.executable, str(ROOT / 'scripts' / script), str(source),
                                         '--profile', 'pal-banked', '--subtune', '1',
                                         '--assume-sid-model', 'MOS8580', '--output', str(output), *extra],
                                        capture_output=True, text=True, timeout=10)
                self.assertEqual(0, result.returncode, result.stderr)
                report = json.loads(output.read_text())
                if script == 'trace-sid-program.py':
                    report = report['audit']
                self.assertEqual({'declared': 'unknown', 'assumed': 'MOS8580'}, report['sidModelAssumption'])
            self.assertEqual(fixture(), source.read_bytes())

    @unittest.skipUnless(VICE.is_file() and VICE_DATA.is_dir(), 'Headless VICE installation required')
    def test_vice_cli_selects_assumed_model_and_matches_unchanged_source_stores(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source, oracle = directory / 'source.sid', directory / 'oracle.json'
            source.write_bytes(fixture())
            for model, engine in (('MOS6581', 'resid6581'), ('MOS8580', 'resid8580')):
                _, writes = audit_psid(source.read_bytes(), 2, profile='pal-banked', subtune=1,
                                       assume_sid_model=model)
                oracle.write_text(json.dumps(writes))
                output = directory / model
                result = subprocess.run([sys.executable, str(ROOT / 'scripts/trace-sid-vice.py'), str(source),
                                         '--profile', 'pal-banked', '--subtune', '1', '--assume-sid-model', model,
                                         '--oracle', str(oracle), '--first-call', '0', '--last-call', '1',
                                         '--output', str(output), '--vice', str(VICE), '--data', str(VICE_DATA)],
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(0, result.returncode, result.stderr)
                study = json.loads((output / 'study.json').read_text())
                self.assertEqual({'declared': 'unknown', 'assumed': model}, study['profile']['sidModelAssumption'])
                self.assertEqual(3, study['verification']['matchedWrites'])
                command = json.loads((output / 'command.json').read_text())
                self.assertEqual(engine, command[command.index('-sidenginemodel') + 1])
            self.assertEqual(fixture(), source.read_bytes())


if __name__ == '__main__':
    unittest.main()
