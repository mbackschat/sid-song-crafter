import array
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("audio_controls", ROOT / "scripts/studies/audio-assessment/prepare-controls.py")
controls = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(controls)
sys.path.insert(0, str(ROOT / "scripts"))
import audio_assessment


def read_samples(path):
    with wave.open(str(path), "rb") as source:
        params = source.getparams()
        pcm = source.readframes(source.getnframes())
    samples = array.array("h", pcm)
    if sys.byteorder != "little":
        samples.byteswap()
    return params, samples, pcm


def measured_frequency(samples, start_seconds, end_seconds):
    window = samples[round(start_seconds * 16000):round(end_seconds * 16000)]
    crossings = sum(first <= 0 < second for first, second in zip(window, window[1:]))
    return crossings / (end_seconds - start_seconds)


class AudioControlsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.output = self.root / "build/controls"
        for module in (controls, audio_assessment):
            root_patch = patch.object(module, "ROOT", self.root)
            root_patch.start()
            self.addCleanup(root_patch.stop)

    def speech_fixture(self, path):
        with wave.open(str(path), "wb") as target:
            target.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            target.writeframes(b"\x00\x04\x00\xfc" * 32000)
        return {"method": "test fixture", "text": controls.SPEECH_TEXT, "voice": "Samantha"}

    def prepare(self, output=None, **options):
        with patch.object(controls, "_require_speech_tools"), patch.object(controls, "_synthesize_speech", side_effect=self.speech_fixture):
            return controls.prepare_controls(output or self.output, "test/audio-model", **options)

    def test_silence_is_exact_zero_pcm_with_different_durations(self):
        self.prepare()
        for case_id, seconds in (("c01", 4), ("c07", 6)):
            params, samples, pcm = read_samples(self.output / f"{case_id}.wav")
            self.assertEqual((params.nchannels, params.sampwidth, params.framerate), (1, 2, 16000))
            self.assertEqual(params.nframes, seconds * 16000)
            self.assertEqual(pcm, bytes(seconds * 16000 * 2))
            self.assertTrue(all(sample == 0 for sample in samples))

    def test_steady_tones_have_declared_duration_and_pitch(self):
        self.prepare()
        for case_id, seconds, frequency in (("c02", 4, 440), ("c08", 5, 880)):
            params, samples, _ = read_samples(self.output / f"{case_id}.wav")
            self.assertEqual(params.nframes, seconds * 16000)
            self.assertAlmostEqual(measured_frequency(samples, 0.5, seconds - 0.5), frequency, delta=1)
            self.assertLess(max(abs(sample) for sample in samples), 32767)

    def test_sweep_pitch_increases_through_independent_time_regions(self):
        self.prepare()
        params, samples, _ = read_samples(self.output / "c03.wav")
        self.assertEqual(params.nframes, 4 * 16000)
        for start, end in ((0.25, 0.75), (1.75, 2.25), (3.25, 3.75)):
            expected = 220 + 165 * (start + end) / 2
            self.assertAlmostEqual(measured_frequency(samples, start, end), expected, delta=3)

    def test_beeps_are_three_separated_four_tenths_second_regions(self):
        self.prepare()
        params, samples, _ = read_samples(self.output / "c05.wav")
        self.assertEqual(params.nframes, 4 * 16000)
        active_bins = [any(abs(value) > 100 for value in samples[index:index + 160]) for index in range(0, len(samples), 160)]
        starts = [index for index, active in enumerate(active_bins) if active and (index == 0 or not active_bins[index - 1])]
        ends = [index + 1 for index, active in enumerate(active_bins) if active and (index + 1 == len(active_bins) or not active_bins[index + 1])]
        self.assertEqual(starts, [40, 170, 300])
        self.assertEqual([end - start for start, end in zip(starts, ends)], [40, 40, 40])
        self.assertTrue(all(next_start - end >= 90 for end, next_start in zip(ends, starts[1:])))

    def test_seeded_noise_repeats_exact_pcm_and_retains_its_hash(self):
        self.prepare()
        second = self.root / "build/second"
        self.prepare(second)
        params, samples, pcm = read_samples(self.output / "c04.wav")
        self.assertEqual(params.nframes, 4 * 16000)
        self.assertEqual(pcm, read_samples(second / "c04.wav")[2])
        self.assertGreater(len(set(samples)), 10000)
        self.assertLess(abs(sum(samples) / len(samples)), 100)
        provenance = json.loads((self.output / "provenance.json").read_text())
        self.assertEqual(provenance["cases"]["c04"]["pcm"]["pcm_sha256"], hashlib.sha256(pcm).hexdigest())
        self.assertEqual(provenance["cases"]["c04"]["synthesis"]["seed"], 20261013)

    def test_all_requests_use_identical_neutral_prompt_without_oracle_or_clip_names(self):
        self.prepare(reasoning=True, reasoning_effort="low")
        manifest = json.loads((self.output / "cases.json").read_text())
        oracle = json.loads((self.output / "oracle.json").read_text())
        self.assertEqual(len(manifest["cases"]), 8)
        self.assertEqual(len({case["prompt"] for case in manifest["cases"]}), 1)
        self.assertEqual([case["category"] for case in oracle["cases"]], ["silence", "steady_tone", "changing_tone", "noise", "repeated_tones", "speech", "silence", "steady_tone"])
        self.assertEqual(oracle["cases"][5]["required_words"], ["blue", "lantern", "seven", "wooden", "boxes"])
        self.assertEqual(oracle["gate"]["required_case_count"], 8)
        self.assertTrue(oracle["gate"]["require_all_categories_correct"])
        self.assertFalse(oracle["gate"]["establishes_musical_ability"])
        for case in audio_assessment._prepare(self.output / "cases.json", self.root / "build/results"):
            payload = json.loads(case["payload"])
            self.assertEqual(payload["model"], "test/audio-model")
            self.assertEqual(payload["reasoning"], {"enabled": True, "effort": "low"})
            content = payload["messages"][0]["content"]
            self.assertEqual(content[0]["text"], controls.PROMPT)
            self.assertEqual(base64.b64decode(content[1]["input_audio"]["data"]), Path(case["wav_path"]).read_bytes())
            visible = json.dumps({**payload, "messages": [{"role": "user", "content": [content[0]]}]})
            for private in ("blue", "lantern", "boxes", "c01", ".wav", "440", "880", "expected", "oracle"):
                self.assertNotIn(private, visible.lower())

    def test_output_boundary_freshness_and_reasoning_guard_precede_generation(self):
        for output, options in ((self.root / "elsewhere", {}), (self.output, {"reasoning_effort": "low"})):
            with self.assertRaises(ValueError):
                self.prepare(output, **options)
            self.assertFalse(output.exists())
        self.output.mkdir(parents=True)
        existing = self.output / "keep.txt"
        existing.write_text("keep")
        with self.assertRaises(FileExistsError):
            self.prepare()
        self.assertEqual(existing.read_text(), "keep")

    def test_missing_offline_speech_tool_refuses_incomplete_control_bundle(self):
        with patch.object(controls, "_require_speech_tools", side_effect=ValueError("Offline speech tools unavailable")):
            with self.assertRaisesRegex(ValueError, "speech"):
                controls.prepare_controls(self.output, "test/audio-model")
        self.assertFalse(self.output.exists())

    def test_successful_speech_commands_with_empty_pcm_are_refused(self):
        self.output.mkdir(parents=True)
        converted = self.output / ".c06-converted.wav"
        with wave.open(str(converted), "wb") as target:
            target.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            target.writeframes(b"")
        with patch.object(controls, "_run"):
            with self.assertRaisesRegex(ValueError, "nonempty"):
                controls._synthesize_speech(self.output / "c06.wav")
        self.assertFalse((self.output / "c06.wav").exists())


if __name__ == "__main__":
    unittest.main()
