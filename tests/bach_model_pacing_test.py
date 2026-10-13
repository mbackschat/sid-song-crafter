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
SPEC = importlib.util.spec_from_file_location("bach_model_pacing", ROOT / "scripts/studies/audio-assessment/prepare-bach-pacing.py")
pacing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pacing)
sys.path.insert(0, str(ROOT / "scripts"))
import audio_assessment


def read_wav(path):
    with wave.open(str(path), "rb") as audio:
        return audio.getparams(), audio.readframes(audio.getnframes())


class BachModelPacingTest(unittest.TestCase):
    def setUp(self):
        (ROOT / "build").mkdir(exist_ok=True)
        directory = tempfile.TemporaryDirectory(prefix="bach-pacing-test-", dir=ROOT / "build")
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.sources = self.directory / "sources"
        self.sources.mkdir()
        self.output = self.directory / "inputs"
        self.pcm = {
            "previous-hybrid.wav": b"\x00\x04\x00\xfc" * (9 * 44100 // 2),
            "driven-hybrid.wav": b"\x00\x08\x00\xf8" * (9 * 44100 // 2),
        }
        hashes, records = {}, []
        for name, pcm in self.pcm.items():
            path = self.sources / name
            self.write_wav(path, pcm)
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
            cache = self.directory / name.removesuffix(".wav")
            cache.mkdir()
            verification = {
                "pcm": {"sha256": hashes[name]},
                "renderer": {"stdout": "test renderer", "executableSha256": "fixture"},
                "audit": {"sidModel": "MOS8580", "sidCount": 1, "clockHz": 985248.6111111111, "callRateHz": 50.12457321485099},
            }
            (cache / "verification.json").write_text(json.dumps(verification))
            records.append({"filename": name, "sha256": hashes[name], "sourcePath": str(cache / "native-song.wav")})
        self.registry = self.sources / "sources.json"
        self.registry.write_text(json.dumps({"files": records}))
        for name, value in (("SOURCE_DIRECTORY", self.sources), ("SOURCE_REGISTRY", self.registry), ("SOURCE_HASHES", hashes)):
            mock = patch.object(pacing, name, value)
            mock.start()
            self.addCleanup(mock.stop)

    def write_wav(self, path, pcm, sample_rate=44100, channels=1):
        with wave.open(str(path), "wb") as audio:
            audio.setparams((channels, 2, sample_rate, 0, "NONE", "not compressed"))
            audio.writeframes(pcm)

    def prepare(self):
        return pacing.prepare_bach_pacing(self.output)

    def test_pair_order_gap_and_identical_controls_preserve_exact_first_eight_seconds(self):
        self.prepare()
        frames = 8 * 44100
        old, new = (self.pcm[name][:frames * 2] for name in ("previous-hybrid.wav", "driven-hybrid.wav"))
        silence, gap = bytes(frames * 2), bytes(44100)
        expected = {"p01": old + gap + new, "p02": new + gap + old, "p03": new + gap + new, "p04": silence + gap + silence}
        for case_id, pcm in expected.items():
            params, actual = read_wav(self.output / f"{case_id}.wav")
            self.assertEqual((params.nchannels, params.sampwidth, params.framerate, params.nframes), (1, 2, 44100, 727650))
            self.assertEqual(actual, pcm)

    def test_songbench_clips_preserve_pcm_and_duplicate_exact_wav_bytes(self):
        self.prepare()
        length = 8 * 44100 * 2
        expected = {"q01": self.pcm["previous-hybrid.wav"][:length], "q02": self.pcm["driven-hybrid.wav"][:length], "q03": bytes(length), "q04": self.pcm["driven-hybrid.wav"][:length]}
        for case_id, pcm in expected.items():
            params, actual = read_wav(self.output / f"{case_id}.wav")
            self.assertEqual((params.nchannels, params.sampwidth, params.framerate, params.nframes), (1, 2, 44100, 352800))
            self.assertEqual(actual, pcm)
        self.assertEqual((self.output / "q02.wav").read_bytes(), (self.output / "q04.wav").read_bytes())

    def test_source_fingerprint_failure_precedes_output_creation(self):
        source = self.sources / "previous-hybrid.wav"
        source.write_bytes(source.read_bytes()[:-2] + b"\x01\x00")
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_publication_cannot_redirect_expected_source_hashes(self):
        registry = json.loads(self.registry.read_text())
        registry["files"][0]["sha256"] = "0" * 64
        self.registry.write_text(json.dumps(registry))
        with self.assertRaisesRegex(ValueError, "publication"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_wrong_format_and_short_source_are_rejected_before_output_creation(self):
        source = self.sources / "previous-hybrid.wav"
        for pcm, rate, channels in ((bytes(7 * 44100 * 2), 44100, 1), (bytes(9 * 22050 * 2), 22050, 1), (bytes(9 * 44100 * 4), 44100, 2)):
            with self.subTest(rate=rate, channels=channels, bytes=len(pcm)):
                self.write_wav(source, pcm, rate, channels)
                expected = hashlib.sha256(source.read_bytes()).hexdigest()
                registry = json.loads(self.registry.read_text())
                registry["files"][0]["sha256"] = expected
                self.registry.write_text(json.dumps(registry))
                with patch.dict(pacing.SOURCE_HASHES, {"previous-hybrid.wav": expected}):
                    with self.assertRaisesRegex(ValueError, "eight seconds.*44.1 kHz mono"):
                        self.prepare()
                self.assertFalse(self.output.exists())

    def test_frozen_requests_hide_oracle_names_and_feedback_and_bind_exact_payloads(self):
        self.prepare()
        manifest = json.loads((self.output / "qwen.json").read_text())
        oracle = json.loads((self.output / "oracle.json").read_text())
        self.assertEqual(set(manifest), {"model", "max_tokens", "reasoning", "cases"})
        self.assertEqual(len({case["prompt"] for case in manifest["cases"]}), 1)
        expected = [
            {"audio_presence": "music", "more_forward_motion": "B", "longer_holds_or_gaps": "A"},
            {"audio_presence": "music", "more_forward_motion": "A", "longer_holds_or_gaps": "B"},
            {"audio_presence": "music", "more_forward_motion": "same", "longer_holds_or_gaps": "same"},
            {"audio_presence": "silence", "more_forward_motion": "same", "longer_holds_or_gaps": "same"},
        ]
        self.assertEqual([case["expected"] for case in oracle["qwen"]["cases"]], expected)
        prepared = audio_assessment._prepare(self.output / "qwen.json", self.directory / "results")
        for case, declared, answer in zip(prepared, manifest["cases"], oracle["qwen"]["cases"]):
            self.assertEqual(set(declared), {"id", "wav", "prompt", "audio_sha256"})
            self.assertEqual(case["audio_sha256"], declared["audio_sha256"])
            self.assertEqual(case["audio_sha256"], answer["audio_sha256"])
            self.assertEqual(case["payload_sha256"], answer["payload_sha256"])
            payload = json.loads(case["payload"])
            content = payload["messages"][0]["content"]
            self.assertEqual(base64.b64decode(content[1]["input_audio"]["data"]), Path(case["wav_path"]).read_bytes())
            self.assertEqual(content[0]["text"], pacing.PROMPT)
            for private in ("bach", "toccata", "previous", "driven", "nice", "accepted", "preferred", "oracle", ".wav"):
                self.assertNotIn(private, content[0]["text"].lower())
        for case in json.loads((self.output / "songbench.json").read_text())["cases"]:
            self.assertEqual(set(case), {"id", "wav", "audio_sha256"})
            self.assertEqual(case["audio_sha256"], hashlib.sha256((self.output / case["wav"]).read_bytes()).hexdigest())

    def test_provenance_and_hypotheses_retain_source_bounds_and_limited_verdict_scope(self):
        self.prepare()
        provenance = json.loads((self.output / "provenance.json").read_text())
        oracle = json.loads((self.output / "oracle.json").read_text())
        self.assertEqual(provenance["gain"], 1)
        self.assertFalse(provenance["normalization"])
        for name, source in provenance["sources"].items():
            self.assertEqual(source["sha256"], pacing.SOURCE_HASHES[name])
            self.assertEqual(source["window"]["start_frame_inclusive"], 0)
            self.assertEqual(source["window"]["end_frame_exclusive"], 352800)
            self.assertEqual(source["window_pcm_sha256"], hashlib.sha256(self.pcm[name][:705600]).hexdigest())
        self.assertEqual(oracle["songbench"]["primary_dimension"], "musicality")
        self.assertEqual(len(oracle["songbench"]["retain_dimensions"]), 7)
        self.assertEqual(oracle["songbench"]["tentative_ranking"]["higher_case"], "q02")
        self.assertEqual(oracle["songbench"]["tentative_ranking"]["lower_case"], "q01")
        self.assertFalse(oracle["human_context"]["eight_second_preference_independently_reviewed"])
        self.assertFalse(oracle["held_out_passage"])
        self.assertFalse(oracle["establishes_model_eligibility"])
        self.assertFalse(oracle["songbench"]["silence"]["musical_quality_ground_truth"])
        self.assertIn("different amounts of the score", oracle["scope"])
        self.assertIn("global tempo", oracle["scope"])

    def test_output_must_be_fresh_and_inside_build(self):
        with self.assertRaisesRegex(ValueError, "build/"):
            pacing.prepare_bach_pacing(ROOT / "tests/forbidden-pacing-output")
        self.output.mkdir()
        kept = self.output / "keep.txt"
        kept.write_text("keep")
        with self.assertRaises(FileExistsError):
            self.prepare()
        self.assertEqual(kept.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
