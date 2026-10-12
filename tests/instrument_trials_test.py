import json
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("instrument_trials", ROOT / "scripts/run-instrument-trials.py")
trials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trials)


class InstrumentTrialsTest(unittest.TestCase):
    def test_rejects_reversed_pluck_transition_even_when_both_waveforms_exist(self):
        reference = [[0] * 25 for _ in range(96)]
        candidate = [[0] * 25 for _ in range(96)]
        for frames in (reference, candidate):
            for state in frames:
                state[4] = 0x11
        candidate[5][4] = 0x21
        with self.assertRaisesRegex(ValueError, "attack"):
            trials.check_technique("pluck", reference, candidate)

    def test_rejects_bass_transient_that_never_recovers_the_reference_pitch(self):
        reference = [[0] * 25 for _ in range(24)]
        candidate = [[0] * 25 for _ in range(24)]
        for index, (a, b) in enumerate(zip(reference, candidate)):
            a[14], a[18] = 100, 0x41
            pitch = (250, 200, 150)[index] if index < 3 else 150
            b[14], b[18] = pitch, 0x11 if index < 3 else 0x41
        with self.assertRaisesRegex(ValueError, "recover|fall"):
            trials.check_technique("bass", reference, candidate)

    def test_real_pulse_pair_exports_audits_renders_and_preserves_native_sources(self):
        native = ROOT / "songs/studies/sidwizard-repertoire/native"
        before = {path: path.read_bytes() for path in native.rglob("*") if path.is_file()}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "trial"
            command = [sys.executable, str(ROOT / "scripts/run-instrument-trials.py"), "--pair", "pulse", "--output", str(output)]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads((output / "trial.json").read_text())
            self.assertEqual(set(report["studies"]), {"pulse-reference", "pulse-candidate"})
            self.assertEqual(report["evidenceLevel"], "rendered experiment")
            self.assertIsNone(report["listeningReview"])
            self.assertTrue(report["techniques"]["pulse"]["pulseMotionObserved"])
            for study in report["studies"].values():
                self.assertGreater(study["audit"]["playWriteCount"], 0)
                self.assertEqual(study["pcm"]["frames"], 441000)
                self.assertEqual(study["pcm"]["clippedSamples"], 0)
            comparison = report["comparisons"]["pulse"]
            self.assertTrue(Path(comparison["comparison"]["path"]).is_file())
            self.assertAlmostEqual(comparison["inputs"][0]["matched"]["acRms"], comparison["inputs"][1]["matched"]["acRms"], delta=1)
            previous = (output / "trial.json").read_bytes()
            repeated = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual((output / "trial.json").read_bytes(), previous)
        for path, data in before.items():
            self.assertEqual(path.read_bytes(), data)


if __name__ == "__main__":
    unittest.main()
