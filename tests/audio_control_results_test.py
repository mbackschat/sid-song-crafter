import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import wave


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("control_results", ROOT / "scripts/studies/audio-assessment/evaluate-controls.py")
control_results = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(control_results)
import audio_assessment


class ControlResultsTest(unittest.TestCase):
    def test_speech_accepts_punctuation_and_digit_without_accepting_missing_words(self):
        expected = {"category": "speech", "required_words": ["blue", "lantern", "seven", "wooden", "boxes"]}
        reply = '{"category":"speech","transcript":"The BLUE lantern is beside 7 wooden boxes."}'
        self.assertTrue(control_results.grade(reply, expected)["passed"])
        reply = '{"category":"speech","transcript":"The blue lantern is beside boxes."}'
        result = control_results.grade(reply, expected)
        self.assertFalse(result["passed"])
        self.assertEqual(result["missing_words"], ["seven", "wooden"])

    def test_correct_fenced_json_passes_but_confident_wrong_category_fails(self):
        expected = {"category": "silence"}
        self.assertTrue(control_results.grade('```json\n{"category":"silence"}\n```', expected)["passed"])
        result = control_results.grade('{"category":"steady_tone","confidence":"high"}', expected)
        self.assertFalse(result["passed"])

    def test_abstention_malformed_json_and_non_object_do_not_pass(self):
        for reply in [None, "I cannot hear it.", "[]", '{"category":"uncertain"}', '{"category":[]}']:
            with self.subTest(reply=reply):
                self.assertFalse(control_results.grade(reply, {"category": "noise"})["passed"])


class ControlEvaluationTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.inputs = self.root / "build/inputs"
        self.results = self.root / "build/results"
        self.inputs.mkdir(parents=True)
        self.results.mkdir(parents=True)
        root_patch = patch.object(audio_assessment, "ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.manifest_path = self.inputs / "cases.json"
        self.oracle_path = self.inputs / "oracle.json"
        cases, expected = [], []
        for number in range(1, 9):
            case_id = f"c{number:02d}"
            path = self.inputs / f"{case_id}.wav"
            with wave.open(str(path), "wb") as target:
                target.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
                target.writeframes(struct.pack("<hh", number * 100, -number * 100) * 32)
            cases.append({"id": case_id, "wav": path.name, "prompt": "Identify the dominant sound."})
            expected.append({"id": case_id, "category": "steady_tone",
                             "audio_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        self.manifest = {"model": "test/audio-model", "cases": cases}
        self.oracle = {"cases": expected, "gate": {"required_case_count": 8}}
        self.write_inputs()
        self.write_receipts()

    def write_inputs(self):
        self.manifest_path.write_text(json.dumps(self.manifest))
        self.oracle_path.write_text(json.dumps(self.oracle))

    def write_receipts(self):
        prepared = audio_assessment.run_trial(self.manifest_path, self.results, dry_run=True)
        for number, case in enumerate(prepared, 1):
            response = {"model": case["model"], "provider": "test-provider", "choices": [{
                "finish_reason": "stop", "message": {"content": '{"category":"steady_tone"}'}}]}
            raw = json.dumps(response).encode()
            response_path = self.results / f"response-{number:02d}.json"
            response_path.write_bytes(raw)
            receipt = {"payload_sha256": case["payload_sha256"], "status": "complete",
                       "response_path": response_path.name, "response_sha256": hashlib.sha256(raw).hexdigest(),
                       "cost": 0.001}
            (self.results / f"attempt-{number:02d}.json").write_text(json.dumps(receipt))

    def evaluate(self):
        return control_results.evaluate(self.manifest_path, self.oracle_path, self.results)

    def test_matching_audio_request_response_and_oracle_fingerprints_pass(self):
        report = self.evaluate()
        self.assertTrue(report["passed"])
        self.assertEqual((report["correct"], report["total"]), (8, 8))
        self.assertEqual(report["total_cost_usd"], "0.008")
        self.assertEqual(report["manifest_sha256"], hashlib.sha256(self.manifest_path.read_bytes()).hexdigest())
        self.assertEqual(report["oracle_sha256"], hashlib.sha256(self.oracle_path.read_bytes()).hexdigest())
        self.assertEqual(report["evaluator_sha256"], hashlib.sha256(Path(control_results.__file__).read_bytes()).hexdigest())
        for row, expected in zip(report["cases"], self.oracle["cases"]):
            self.assertEqual(row["audio_sha256"], expected["audio_sha256"])

    def test_swapped_wavs_with_new_matching_receipts_cannot_reuse_old_oracle(self):
        first, second = self.inputs / "c01.wav", self.inputs / "c02.wav"
        first_audio, second_audio = first.read_bytes(), second.read_bytes()
        first.write_bytes(second_audio)
        second.write_bytes(first_audio)
        self.write_receipts()
        with self.assertRaisesRegex(ValueError, "Oracle audio fingerprint"):
            self.evaluate()

    def test_missing_oracle_audio_fingerprint_is_rejected(self):
        del self.oracle["cases"][0]["audio_sha256"]
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, "Oracle audio fingerprint"):
            self.evaluate()

    def test_matching_subset_cannot_pass_declared_eight_control_gate(self):
        self.manifest["cases"].pop()
        self.oracle["cases"].pop()
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, "different number of controls"):
            self.evaluate()

    def test_valid_json_with_changed_response_bytes_is_rejected(self):
        response_path = self.results / "response-01.json"
        response_path.write_bytes(response_path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "Response fingerprint mismatch"):
            self.evaluate()


if __name__ == "__main__":
    unittest.main()
