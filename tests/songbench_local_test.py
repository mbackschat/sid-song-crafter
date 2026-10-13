import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import wave


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/studies/audio-assessment/songbench-local.py"


class SongBenchLocalTest(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("songbench_local", SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def write_wav(self, path, seconds, channels=1):
        with wave.open(str(path), "wb") as out:
            out.setnchannels(channels)
            out.setsampwidth(2)
            out.setframerate(24000)
            out.writeframes(b"\x00\x00" * int(seconds * 24000) * channels)

    def test_reject_long_audio_before_loading_model(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "long.wav"
            self.write_wav(audio, 10.01)
            with self.assertRaisesRegex(ValueError, "10 seconds"):
                self.module.audio_info(audio)

    def test_duplicate_ids_cannot_overwrite_trial_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "short.wav"
            self.write_wav(audio, 0.1)
            manifest = Path(directory) / "trial.json"
            manifest.write_text('{"cases":[{"id":"same","wav":"short.wav"},{"id":"same","wav":"short.wav"}]}')
            with self.assertRaisesRegex(ValueError, "unique"):
                self.module.load_cases(manifest)

    def test_reject_truncated_mono_and_partial_stereo_frames_despite_valid_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "short.wav"
            for channels, removed_bytes in ((1, 2), (2, 3)):
                with self.subTest(channels=channels):
                    self.write_wav(audio, 0.1, channels)
                    audio.write_bytes(audio.read_bytes()[:-removed_bytes])
                    with wave.open(str(audio), "rb") as source:
                        self.assertEqual(source.getnframes(), 2400)
                    with self.assertRaisesRegex(ValueError, "truncated"):
                        self.module.audio_info(audio)

    def test_decoded_count_rejects_cropping_and_padding_when_resampled_duration_is_integral(self):
        original = {"frames": 384000, "sample_rate": 48000}
        self.module.verify_decoded_frames(192000, 24000, original)
        for frames in (96000, 191999, 192001):
            with self.subTest(frames=frames):
                with self.assertRaisesRegex(ValueError, "decoded frame count"):
                    self.module.verify_decoded_frames(frames, 24000, original)

    def test_decoded_count_accepts_librosa_float_ceiling_without_allowing_arbitrary_padding(self):
        for original_frames, nominal_frames in ((352800, 192000), (44100, 24000)):
            original = {"frames": original_frames, "sample_rate": 44100}
            with self.subTest(original_frames=original_frames):
                self.module.verify_decoded_frames(nominal_frames, 24000, original)
                self.module.verify_decoded_frames(nominal_frames + 1, 24000, original)
                for frames in (0, nominal_frames // 2, nominal_frames - 1, nominal_frames + 2):
                    with self.subTest(decoded_frames=frames):
                        with self.assertRaisesRegex(ValueError, "decoded frame count"):
                            self.module.verify_decoded_frames(frames, 24000, original)

    def test_decoded_count_allows_only_adjacent_integer_rounding_for_fractional_duration(self):
        original = {"frames": 101, "sample_rate": 44100}
        for frames in (54, 55):
            self.module.verify_decoded_frames(frames, 24000, original)
        for frames in (0, 53, 56):
            with self.subTest(frames=frames):
                with self.assertRaisesRegex(ValueError, "decoded frame count"):
                    self.module.verify_decoded_frames(frames, 24000, original)

    def test_changed_audio_under_pinned_manifest_is_rejected_before_model_load(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "short.wav"
            self.write_wav(audio, 0.1)
            expected = hashlib.sha256(audio.read_bytes()).hexdigest()
            manifest = Path(directory) / "trial.json"
            manifest.write_text(json.dumps({"cases": [{"id": "pinned", "wav": audio.name, "audio_sha256": expected}]}))
            self.assertEqual(self.module.load_cases(manifest)[0]["input"]["sha256"], expected)
            self.write_wav(audio, 0.2)
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                self.module.load_cases(manifest)


if __name__ == "__main__":
    unittest.main()
