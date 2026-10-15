import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('pink_panther_width', ROOT / 'scripts/studies/pink-panther/probe-width.py')
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def basic_fixture(instrument_line=b'\x8310,41,15,55,65,9,34,15,55,65'):
    load = 0x0801
    program = bytearray()
    for number, content in [(10, b'\x83' + b'7,8,9'), (37, instrument_line), (45, b'\x80')]:
        following = load + len(program) + 5 + len(content)
        program.extend(following.to_bytes(2, 'little') + number.to_bytes(2, 'little') + content + b'\0')
    program.extend(b'\0\0')
    header = bytearray(124)
    header[:4] = b'RSID'
    header[4:8] = b'\0\x02\0\x7c'
    return bytes(header) + load.to_bytes(2, 'little') + program


class PinkPantherWidthDiagnosticTest(unittest.TestCase):
    def test_changes_only_main_patch_width_and_preserves_basic_links(self):
        source = basic_fixture()
        changed, receipt = probe.derive_width_diagnostic(source, expected_sha256=hashlib.sha256(source).hexdigest())
        self.assertEqual(len(changed), len(source))
        self.assertEqual(changed, source.replace(b'9,34,15,55,65', b'9,34,12,55,65'))
        offsets = [index for index, (before, after) in enumerate(zip(source, changed)) if before != after]
        self.assertEqual([entry['fileOffset'] for entry in receipt['changedBytes']], offsets)
        self.assertEqual(len(offsets), 1)
        self.assertEqual(receipt['originalPulseWidth'], 0xf37)
        self.assertEqual(receipt['diagnosticPulseWidth'], 0xc37)
        self.assertEqual(receipt['basicLine'], 37)

    def test_rejects_unpinned_input_and_changed_instrument_contract(self):
        source = basic_fixture()
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            probe.derive_width_diagnostic(source)
        changed = basic_fixture(b'\x8310,41,15,55,65,9,35,15,55,65')
        with self.assertRaisesRegex(ValueError, 'instrument DATA'):
            probe.derive_width_diagnostic(changed, expected_sha256=hashlib.sha256(changed).hexdigest())

    def test_rejects_broken_basic_links_without_writing_outputs(self):
        source = bytearray(basic_fixture())
        source[126] += 1
        with self.assertRaisesRegex(ValueError, 'BASIC link'):
            probe.derive_width_diagnostic(bytes(source), expected_sha256=hashlib.sha256(source).hexdigest())
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / 'source.sid'
            source_path.write_bytes(source)
            output = Path(directory) / 'output'
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                probe.prepare_diagnostic(source_path, output)
            self.assertFalse(output.exists())

    def test_snapshot_check_exposes_timing_and_pitch_confounds(self):
        with tempfile.TemporaryDirectory() as directory:
            reference = Path(directory) / 'reference.tsv'
            diagnostic = Path(directory) / 'diagnostic.tsv'
            before = bytearray(32)
            before[2:4] = b'\x37\x0f'
            after = bytearray(before)
            after[3] = 12
            reference.write_text('time_ms\tregisters_hex\n17\t' + before.hex() + '\n')
            diagnostic.write_text('time_ms\tregisters_hex\n17\t' + after.hex() + '\n')
            self.assertTrue(probe.inspect_snapshots(reference, diagnostic)['snapshotIsolationPassed'])
            after[0] = 1
            diagnostic.write_text('time_ms\tregisters_hex\n18\t' + after.hex() + '\n')
            result = probe.inspect_snapshots(reference, diagnostic)
            self.assertFalse(result['snapshotIsolationPassed'])
            self.assertFalse(result['timestampsEqual'])
            self.assertIn('offset 0', result['snapshotValueCheckError'])


if __name__ == '__main__':
    unittest.main()
