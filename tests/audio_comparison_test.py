from array import array
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audio_comparison import inspect_wav, prepare_comparison


def write_wav(path, samples, rate=8000, channels=1, width=2):
    values = array("h", samples)
    if sys.byteorder != "little":
        values.byteswap()
    with wave.open(str(path), "wb") as output:
        output.setparams((channels, width, rate, 0, "NONE", "not compressed"))
        output.writeframes(values.tobytes() if width == 2 else bytes(samples))


def read_samples(path):
    with wave.open(str(path), "rb") as source:
        params = (source.getnchannels(), source.getframerate(), source.getnframes())
        samples = array("h", source.readframes(source.getnframes()))
    if sys.byteorder != "little":
        samples.byteswap()
    return params, list(samples)


class AudioComparisonTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.a = self.root / "original-a.wav"
        self.b = self.root / "original-b.wav"
        self.prefix = self.root / "trial"

    def test_inspection_separates_dc_and_ac_rms_per_stereo_channel(self):
        write_wav(self.a, [100, -20, 300, 20, 100, -20, 300, 20], channels=2)
        report = inspect_wav(self.a)
        self.assertEqual((report["sampleRate"], report["channels"], report["frames"]), (8000, 2, 4))
        self.assertEqual(report["durationSeconds"], 4 / 8000)
        self.assertEqual(report["peak"], 300)
        self.assertEqual(report["clippedSamples"], 0)
        self.assertEqual(report["perChannel"][0]["dc"], 200)
        self.assertEqual(report["perChannel"][1]["dc"], 0)
        self.assertEqual(report["perChannel"][0]["acRms"], 100)
        self.assertEqual(report["perChannel"][1]["acRms"], 20)
        self.assertAlmostEqual(report["perChannel"][0]["rms"], math.sqrt(50000))
        self.assertAlmostEqual(report["acRms"], math.sqrt((10000 + 400) / 2))

    def test_inspection_counts_both_pcm_rails_and_negative_peak(self):
        write_wav(self.a, [-32768, 32767, -32768, 0])
        report = inspect_wav(self.a)
        self.assertEqual(report["peak"], 32768)
        self.assertEqual(report["peakDbfs"], 0)
        self.assertEqual(report["clippedSamples"], 3)

    def test_inspection_rejects_empty_unsupported_and_truncated_pcm(self):
        write_wav(self.a, [])
        with self.assertRaisesRegex(ValueError, "empty"):
            inspect_wav(self.a)
        write_wav(self.a, [128, 129], width=1)
        with self.assertRaisesRegex(ValueError, "PCM16"):
            inspect_wav(self.a)
        write_wav(self.a, [1, 2, 3, 4])
        self.a.write_bytes(self.a.read_bytes()[:-2])
        with self.assertRaisesRegex(ValueError, "truncated"):
            inspect_wav(self.a)

    def test_default_match_preserves_originals_and_exact_ab_order(self):
        write_wav(self.a, [-1000, 1000, 0, 0], rate=8)
        write_wav(self.b, [-2000, 2000, 0, 0], rate=8)
        originals = [path.read_bytes() for path in (self.a, self.b)]
        report = prepare_comparison(self.a, self.b, self.prefix, gap_seconds=0.25, individual_copies=True)
        self.assertEqual(report["inputs"][0]["gain"], 1)
        self.assertEqual(report["inputs"][1]["gain"], 0.5)
        self.assertAlmostEqual(report["inputs"][1]["gainDb"], 20 * math.log10(0.5))
        self.assertEqual(report["inputs"][0]["original"]["acRms"], math.sqrt(500000))
        params, actual = read_samples(self.root / "trial.ab.wav")
        self.assertEqual(params, (1, 8, 10))
        self.assertEqual(actual, [-1000, 1000, 0, 0, 0, 0, -1000, 1000, 0, 0])
        self.assertEqual(report["segments"], [
            {"label": "A", "startFrame": 0, "endFrame": 4},
            {"label": "silence", "startFrame": 4, "endFrame": 6},
            {"label": "B", "startFrame": 6, "endFrame": 10},
        ])
        for index, source in enumerate((self.a, self.b)):
            self.assertEqual(source.read_bytes(), originals[index])
            self.assertEqual(report["inputs"][index]["sha256"], hashlib.sha256(originals[index]).hexdigest())
        self.assertEqual(read_samples(self.root / "trial.a.matched.wav")[1], [-1000, 1000, 0, 0])
        self.assertEqual(read_samples(self.root / "trial.b.matched.wav")[1], [-1000, 1000, 0, 0])
        self.assertEqual(json.loads((self.root / "trial.comparison.json").read_text()), report)
        self.assertIsNone(report["listeningReview"])

    def test_default_target_reduces_both_files_for_peak_headroom(self):
        write_wav(self.a, [-32000, 32000, 0, 0])
        write_wav(self.b, [-30000, 30000, 0, 0])
        report = prepare_comparison(self.a, self.b, self.prefix, gap_seconds=0)
        peak_limit = math.floor(32767 * 10 ** (-1 / 20))
        for source in report["inputs"]:
            self.assertLess(source["gain"], 1)
            self.assertLessEqual(source["matched"]["peak"], peak_limit)
            self.assertEqual(source["matched"]["clippedSamples"], 0)
        self.assertAlmostEqual(report["inputs"][0]["matched"]["acRms"], report["inputs"][1]["matched"]["acRms"])

    def test_explicit_ac_rms_target_can_boost_without_removing_dc(self):
        write_wav(self.a, [500, 1500, 500, 1500])
        write_wav(self.b, [-1000, 1000, -1000, 1000])
        target = 20 * math.log10(1000 / 32768)
        report = prepare_comparison(self.a, self.b, self.prefix, target_ac_rms_dbfs=target)
        self.assertAlmostEqual(report["inputs"][0]["gain"], 2)
        self.assertEqual(report["inputs"][0]["matched"]["perChannel"][0]["dc"], 2000)
        self.assertEqual(report["inputs"][0]["matched"]["acRms"], 1000)
        self.assertEqual(report["inputs"][1]["matched"]["acRms"], 1000)

    def test_peak_guard_accounts_for_dc_and_both_polarities_before_writing(self):
        for samples in ([30000, 32000], [-32000, -30000]):
            with self.subTest(samples=samples):
                write_wav(self.a, samples)
                write_wav(self.b, [-1000, 1000])
                with self.assertRaisesRegex(ValueError, "headroom"):
                    prepare_comparison(self.a, self.b, self.prefix, target_ac_rms_dbfs=-20)
                self.assertFalse((self.root / "trial.ab.wav").exists())
                self.assertFalse((self.root / "trial.comparison.json").exists())

    def test_preparation_rejects_silence_and_dc_only_audio(self):
        write_wav(self.b, [-1000, 1000])
        for samples in ([0, 0], [500, 500]):
            with self.subTest(samples=samples):
                write_wav(self.a, samples)
                with self.assertRaisesRegex(ValueError, "AC energy"):
                    prepare_comparison(self.a, self.b, self.prefix)

    def test_preparation_rejects_clipped_input_even_if_it_would_be_attenuated(self):
        write_wav(self.a, [-32768, 32767])
        write_wav(self.b, [-1000, 1000])
        with self.assertRaisesRegex(ValueError, "clipping"):
            prepare_comparison(self.a, self.b, self.prefix)

    def test_preparation_rejects_rate_channels_or_duration_mismatch(self):
        write_wav(self.a, [-1000, 1000], rate=8000)
        fixtures = (([-1000, 1000], 16000, 1), ([-1000, 1000, -1000, 1000], 8000, 2), ([-1000, 1000, 0], 8000, 1))
        for samples, rate, channels in fixtures:
            with self.subTest(rate=rate, channels=channels, samples=samples):
                write_wav(self.b, samples, rate=rate, channels=channels)
                with self.assertRaisesRegex(ValueError, "same sample rate, channels, and frame count"):
                    prepare_comparison(self.a, self.b, self.prefix)

    def test_one_gain_preserves_stereo_balance_and_channel_dc(self):
        write_wav(self.a, [-500, 250, 500, 750], channels=2)
        write_wav(self.b, [-1000, 500, 1000, 1500], channels=2)
        report = prepare_comparison(self.a, self.b, self.prefix, individual_copies=True)
        self.assertEqual(report["inputs"][1]["gain"], 0.5)
        params, samples = read_samples(self.root / "trial.b.matched.wav")
        self.assertEqual(params, (2, 8000, 2))
        self.assertEqual(samples, [-500, 250, 500, 750])

    def test_preparation_refuses_existing_outputs_and_source_path_collisions(self):
        write_wav(self.a, [-1000, 1000])
        write_wav(self.b, [-1000, 1000])
        output = self.root / "trial.comparison.json"
        output.write_text("keep previous evidence")
        with self.assertRaisesRegex(ValueError, "exists"):
            prepare_comparison(self.a, self.b, self.prefix)
        self.assertEqual(output.read_text(), "keep previous evidence")
        self.assertFalse((self.root / "trial.ab.wav").exists())
        collision = self.root / "collision.ab.wav"
        write_wav(collision, [-1000, 1000])
        before = collision.read_bytes()
        with self.assertRaisesRegex(ValueError, "source"):
            prepare_comparison(collision, self.b, self.root / "collision")
        self.assertEqual(collision.read_bytes(), before)

    def test_exclusive_write_failure_preserves_a_file_created_after_preflight(self):
        write_wav(self.a, [-1000, 1000])
        write_wav(self.b, [-1000, 1000])
        original_open = Path.open
        output = self.root / "trial.ab.wav"

        def concurrent_open(path, mode="r", *args, **kwargs):
            if path == output and mode == "xb":
                with original_open(path, "wb") as concurrent:
                    concurrent.write(b"keep concurrent evidence")
            return original_open(path, mode, *args, **kwargs)

        with patch.object(Path, "open", concurrent_open), self.assertRaises(FileExistsError):
            prepare_comparison(self.a, self.b, self.prefix)
        self.assertEqual(output.read_bytes(), b"keep concurrent evidence")
        self.assertFalse((self.root / "trial.comparison.json").exists())

    def test_preparation_rejects_a_target_that_quantizes_all_ac_energy_away(self):
        write_wav(self.a, [-1000, 1000])
        write_wav(self.b, [-1000, 1000])
        with self.assertRaisesRegex(ValueError, "quantized away"):
            prepare_comparison(self.a, self.b, self.prefix, target_ac_rms_dbfs=-140)
        self.assertFalse((self.root / "trial.ab.wav").exists())

    def test_preparation_rejects_nonfinite_or_invalid_gain_and_gap_options(self):
        write_wav(self.a, [-1000, 1000])
        write_wav(self.b, [-1000, 1000])
        for options in ({"target_ac_rms_dbfs": math.nan}, {"target_ac_rms_dbfs": 1}, {"peak_headroom_db": -1}, {"peak_headroom_db": math.inf}, {"gap_seconds": -1}, {"gap_seconds": math.inf}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                prepare_comparison(self.a, self.b, self.prefix, **options)

    def test_cli_inspect_and_prepare_work_without_player_manifests(self):
        write_wav(self.a, [-1000, 1000])
        write_wav(self.b, [-2000, 2000])
        result = subprocess.run([sys.executable, str(ROOT / "scripts/compare-audio.py"), "inspect", str(self.a)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["frames"], 2)
        result = subprocess.run([sys.executable, str(ROOT / "scripts/compare-audio.py"), "prepare", str(self.a), str(self.b), str(self.prefix)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / "trial.ab.wav").exists())
        self.assertTrue((self.root / "trial.comparison.json").exists())


if __name__ == "__main__":
    unittest.main()
