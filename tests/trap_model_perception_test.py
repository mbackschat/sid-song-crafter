import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("trap_model_perception", ROOT / "scripts/studies/audio-assessment/prepare-trap-perception.py")
perception = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(perception)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TrapModelPerceptionTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="trap-perception-test-", dir=ROOT / "build")
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.sources = self.directory / "sources"
        self.sources.mkdir()
        self.output = self.directory / "trial"
        self.pcm = {
            "trap-original-24to34s.wav": b"\x00\x04\x00\xfc" * (10 * 44100 // 2),
            "trap-original-40to52s.wav": b"\x00\x08\x00\xf8" * 44100 + b"\x00\x10\x00\xf0" * (10 * 44100 // 2),
        }
        hashes, records = {}, []
        for name, pcm in self.pcm.items():
            path = self.sources / name
            self.write_wav(path, pcm)
            hashes[name] = sha(path)
            records.append({"filename": name, "sha256": hashes[name], "sourcePath": str(path)})
        self.registry = self.sources / "sources.json"
        self.registry.write_text(json.dumps({"files": records}))
        human_records = []
        for (name, pcm), verdict in zip(self.pcm.items(), ("In Trap, mostly the  a moving melody", "Trap develops during the excerpt")):
            pair_name = name.replace("trap-original", "deflektor-then-trap").replace(".wav", ".ab.wav")
            pair_path = self.sources / pair_name
            self.write_wav(pair_path, pcm + bytes(22050 * 2) + pcm)
            human_records.append({"comparison": str(pair_path), "sha256": sha(pair_path), "verbatim": verdict})
        human_path = self.sources / "human.json"
        human_path.write_text(json.dumps({"comparisons": human_records}))
        for name, value in (("SOURCE_DIRECTORY", self.sources), ("SOURCE_REGISTRY", self.registry), ("SOURCE_HASHES", hashes), ("HUMAN_REVIEW", human_path)):
            mock = patch.object(perception, name, value)
            mock.start()
            self.addCleanup(mock.stop)

    def write_wav(self, path, pcm, rate=44100, channels=1):
        with wave.open(str(path), "wb") as audio:
            audio.setparams((channels, 2, rate, 0, "NONE", "not compressed"))
            audio.writeframes(pcm)

    def prepare(self):
        return perception.prepare_trap_perception(self.output)

    def test_exact_originals_silence_and_six_tiled_two_second_copies(self):
        self.prepare()
        inputs = self.output / "inputs"
        for case_id, name in (("c01", "trap-original-24to34s.wav"), ("c02", "trap-original-40to52s.wav")):
            self.assertEqual((inputs / f"{case_id}.wav").read_bytes(), (self.sources / name).read_bytes())
        expected = {"c03": bytes(12 * 44100 * 2), "c04": self.pcm["trap-original-40to52s.wav"][:2 * 44100 * 2] * 6}
        for case_id, pcm in expected.items():
            with wave.open(str(inputs / f"{case_id}.wav"), "rb") as audio:
                self.assertEqual((audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getnframes()), (1, 2, 44100, 12 * 44100))
                self.assertEqual(audio.readframes(audio.getnframes()), pcm)

    def test_source_mismatch_and_missing_source_stop_before_output_creation(self):
        source = self.sources / "trap-original-24to34s.wav"
        contents = source.read_bytes()
        source.write_bytes(contents[:-2] + b"\x01\x00")
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            self.prepare()
        self.assertFalse(self.output.exists())
        source.unlink()
        with self.assertRaises(OSError):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_publication_cannot_replace_pinned_source_identity(self):
        document = json.loads(self.registry.read_text())
        document["files"][0]["sha256"] = "0" * 64
        self.registry.write_text(json.dumps(document))
        with self.assertRaisesRegex(ValueError, "publication"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_wrong_format_and_duration_are_rejected_before_output_creation(self):
        name = "trap-original-24to34s.wav"
        for pcm, rate, channels in ((bytes(9 * 44100 * 2), 44100, 1), (bytes(10 * 22050 * 2), 22050, 1), (bytes(10 * 44100 * 4), 44100, 2)):
            with self.subTest(rate=rate, channels=channels, bytes=len(pcm)):
                self.write_wav(self.sources / name, pcm, rate, channels)
                expected = sha(self.sources / name)
                document = json.loads(self.registry.read_text())
                document["files"][0]["sha256"] = expected
                self.registry.write_text(json.dumps(document))
                with patch.dict(perception.SOURCE_HASHES, {name: expected}):
                    with self.assertRaisesRegex(ValueError, "exact.*mono PCM16"):
                        self.prepare()
                self.assertFalse(self.output.exists())

    def test_same_blind_prompt_and_model_settings_bind_to_frozen_oracle(self):
        self.prepare()
        oracle = json.loads((self.output / "inputs/oracle.json").read_text())
        self.assertEqual([case["expected"] for case in oracle["cases"]], [
            {"rhythmic_motion": "moving melody"}, {"development": "develops"},
            {"music_present": "no", "rhythmic_motion": "no music", "development": "no music"},
            {"development": "repeats"},
        ])
        self.assertFalse(oracle["held_out_passage"])
        self.assertFalse(oracle["establishes_model_eligibility"])
        for label, settings in perception.MODELS.items():
            manifest = self.output / "inputs" / f"{label}.json"
            document = json.loads(manifest.read_text())
            self.assertEqual(document["model"], settings["model"])
            self.assertTrue(document["reasoning"])
            self.assertEqual(document.get("reasoning_effort"), "low" if label == "gemini" else None)
            cases = perception._prepare(manifest, self.output / "results")
            for case, expected in zip(cases, oracle["models"][label]["cases"]):
                self.assertEqual(case["audio_sha256"], expected["audio_sha256"])
                self.assertEqual(case["payload_sha256"], expected["payload_sha256"])
                content = json.loads(case["payload"])["messages"][0]["content"]
                self.assertEqual(content[0]["text"], perception.PROMPT)
                self.assertEqual(base64.b64decode(content[1]["input_audio"]["data"]), Path(case["wav_path"]).read_bytes())
                for private in ("trap", "daglish", "composer", "oracle", "verdict", ".wav"):
                    self.assertNotIn(private, content[0]["text"].lower())

    def test_frozen_inputs_reject_mutation(self):
        self.prepare()
        perception.verify_frozen_inputs(self.output)
        path = self.output / "inputs/qwen.json"
        path.write_text(path.read_text().replace("moving melody", "moving bass"))
        with self.assertRaisesRegex(ValueError, "Frozen input"):
            perception.verify_frozen_inputs(self.output)

    def test_parser_rejects_unstructured_labels_and_evidence_outside_clip(self):
        answer = {"music_present": "yes", "rhythmic_motion": "moving melody", "development": "unclear", "evidence": [{"start_seconds": 0, "end_seconds": 10, "observation": "Pitch motion continues."}]}
        self.assertEqual(perception.parse_answer(json.dumps(answer), 10), (answer, []))
        for changed in ({**answer, "rhythmic_motion": "melody"}, {**answer, "evidence": [{"start_seconds": 0, "end_seconds": 11, "observation": "Claim"}]}, {**answer, "evidence": []}):
            self.assertTrue(perception.parse_answer(json.dumps(changed), 10)[1])
        self.assertTrue(perception.parse_answer("Here is my opinion.", 10)[1])

    def test_output_must_be_fresh_and_under_build(self):
        with self.assertRaisesRegex(ValueError, "build/"):
            perception.prepare_trap_perception(ROOT / "tests/forbidden-trap-output")
        self.output.mkdir()
        with self.assertRaises(FileExistsError):
            self.prepare()


if __name__ == "__main__":
    unittest.main()
