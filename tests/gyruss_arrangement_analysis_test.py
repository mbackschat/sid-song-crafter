import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/studies/bach/analyze-gyruss-arrangement.py'
spec = importlib.util.spec_from_file_location('arrangement_analysis', SCRIPT)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class ArrangementEvidenceTest(unittest.TestCase):
    def test_pitch_class_match_accepts_octave_changes_and_rejects_changed_pitch(self):
        accepted = [dict(midi=midi, startBeat=index, durationBeats=1, sourceStartBeat=index,
                         sourceEndBeat=index + 1, sourceId=str(index)) for index, midi in enumerate([69, 71, 72])]
        observed = [dict(midi=midi - 12, voice=1, startSeconds=index, endSeconds=index + 1,
                         note=str(midi - 12)) for index, midi in enumerate([69, 71, 72])]
        self.assertEqual(analysis.phrase_matches(observed, accepted, 3)[0]['octaveDifferences'], [-12])
        observed[1]['midi'] += 1
        self.assertEqual(analysis.phrase_matches(observed, accepted, 3), [])

    def test_noise_control_is_excluded_from_nominal_pitches(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'snapshots.tsv'
            registers = bytearray(32)
            registers[0:2] = (7217).to_bytes(2, 'little')
            registers[4] = 0x81
            path.write_text('time_ms\tregisters_hex\n17\t' + registers.hex() + '\n35\t' + registers.hex() + '\n')
            voices, _ = analysis.snapshot_runs(path, 1022727)
            self.assertIsNone(voices[0][0]['midi'])

    def test_modified_preparation_is_rejected_before_seconds_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            preparation = json.loads((ROOT / 'songs/studies/bach-toccata-full/preparation.json').read_text())
            preparation['date'] = 'changed'
            preparation_path = directory / 'preparation.json'
            preparation_path.write_text(json.dumps(preparation))
            result = subprocess.run([sys.executable, str(SCRIPT), '--snapshots', str(directory / 'unused.tsv'),
                                     '--preparation', str(preparation_path), '--clock-hz', '1022727', '--output', str(directory / 'output')],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('pinned accepted preparation', result.stderr)


if __name__ == '__main__':
    unittest.main()
