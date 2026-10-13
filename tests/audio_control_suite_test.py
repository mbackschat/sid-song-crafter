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
SCRIPTS = ROOT / "scripts/studies/audio-assessment"
SUITE_SPEC = importlib.util.spec_from_file_location("audio_control_suite", SCRIPTS / "run-control-suite.py")
suite = importlib.util.module_from_spec(SUITE_SPEC)
SUITE_SPEC.loader.exec_module(suite)
SCORER_SPEC = importlib.util.spec_from_file_location("audio_control_scorer", SCRIPTS / "evaluate-controls.py")
scorer = importlib.util.module_from_spec(SCORER_SPEC)
SCORER_SPEC.loader.exec_module(scorer)
import audio_assessment


class AudioControlSuiteTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.inputs = self.root / "build/inputs"
        self.output = self.root / "build/suite"
        self.inputs.mkdir(parents=True)
        self.report_path = self.output / "qwen/assessment.json"
        self.results = self.output / "qwen/results"
        self.runner_calls = 0
        self.scorer_calls = 0
        for module in (suite, audio_assessment):
            root_patch = patch.object(module, "ROOT", self.root)
            root_patch.start()
            self.addCleanup(root_patch.stop)
        subprocess_patch = patch.object(suite.subprocess, "run", side_effect=self.offline_subprocess)
        subprocess_patch.start()
        self.addCleanup(subprocess_patch.stop)
        cases, expected = [], []
        for number in range(1, 9):
            case_id = f"c{number:02d}"
            path = self.inputs / f"{case_id}.wav"
            self.write_wav(path, number)
            cases.append({"id": case_id, "wav": path.name, "prompt": "Identify the dominant sound."})
            expected.append({"id": case_id, "category": "steady_tone",
                             "audio_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        (self.inputs / "cases.json").write_text(json.dumps({"cases": cases}))
        (self.inputs / "oracle.json").write_text(json.dumps({"cases": expected, "gate": {"required_case_count": 8}}))

    def write_wav(self, path, value):
        with wave.open(str(path), "wb") as target:
            target.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            target.writeframes(struct.pack("<hh", value * 100, -value * 100) * 32)

    def offline_subprocess(self, command, **options):
        if Path(command[1]).name == "audio_assessment.py":
            self.runner_calls += 1
            results = Path(command[command.index("--output") + 1])
            prepared = audio_assessment.run_trial(command[2], results, dry_run=True)
            if "--dry-run" not in command:
                results.mkdir(parents=True, exist_ok=True)
                for number, case in enumerate(prepared, 1):
                    raw = json.dumps({"model": case["model"], "provider": "test-provider", "choices": [{
                        "finish_reason": "stop", "message": {"content": '{"category":"steady_tone"}'}}]}).encode()
                    response_path = results / f"response-{number:02d}.json"
                    response_path.write_bytes(raw)
                    receipt = {"status": "complete", "payload_sha256": case["payload_sha256"],
                               "response_path": response_path.name, "response_sha256": hashlib.sha256(raw).hexdigest(),
                               "cost": 0.001}
                    (results / f"attempt-{number:02d}.json").write_text(json.dumps(receipt))
        elif Path(command[1]).name == "evaluate-controls.py":
            self.scorer_calls += 1
            report = scorer.evaluate(command[2], command[3], command[4])
            path = Path(command[command.index("--output") + 1])
            with path.open("x") as target:
                target.write(json.dumps(report, indent=2) + "\n")
        else:
            raise AssertionError(f"Unexpected subprocess: {command}")

    def run_suite(self, execute=True, oracle=None):
        arguments = ["run-control-suite.py", "--inputs", str(self.inputs),
                     "--output", str(self.output), "--model", "qwen"]
        if execute:
            arguments.append("--execute")
        if oracle is not None:
            arguments.extend(["--oracle", str(oracle)])
        with patch.object(suite.sys, "argv", arguments):
            suite.main()

    def test_unchanged_retained_report_is_rescored_and_preserved(self):
        self.run_suite()
        retained = self.report_path.read_bytes()
        report = json.loads(retained)
        self.assertEqual(report["cases"][0]["receipt_sha256"],
                         hashlib.sha256((self.results / "attempt-01.json").read_bytes()).hexdigest())
        self.run_suite()
        self.assertEqual(self.scorer_calls, 2)
        self.assertEqual(self.report_path.read_bytes(), retained)

    def test_retained_report_from_another_evaluator_is_rejected(self):
        self.run_suite()
        report = json.loads(self.report_path.read_text())
        report["evaluator_sha256"] = "0" * 64
        self.report_path.write_text(json.dumps(report))
        retained = self.report_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "Retained assessment"):
            self.run_suite()
        self.assertEqual(self.runner_calls, 1)
        self.assertEqual(self.report_path.read_bytes(), retained)

    def test_changed_wav_is_rejected_before_request_runner(self):
        self.run_suite()
        retained = self.report_path.read_bytes()
        self.write_wav(self.inputs / "c01.wav", 10)
        with self.assertRaisesRegex(ValueError, "Oracle audio fingerprint"):
            self.run_suite()
        self.assertEqual(self.runner_calls, 1)
        self.assertEqual(self.report_path.read_bytes(), retained)

    def test_tampered_response_is_rejected_before_request_runner(self):
        self.run_suite()
        retained = self.report_path.read_bytes()
        path = self.results / "response-01.json"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "Response fingerprint mismatch"):
            self.run_suite()
        self.assertEqual(self.runner_calls, 1)
        self.assertEqual(self.report_path.read_bytes(), retained)

    def test_changed_valid_receipt_cannot_reuse_old_assessment(self):
        self.run_suite()
        retained = self.report_path.read_bytes()
        path = self.results / "attempt-01.json"
        receipt = json.loads(path.read_text())
        receipt["cost"] = 0.002
        path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "Retained assessment"):
            self.run_suite()
        self.assertEqual(self.runner_calls, 1)
        self.assertEqual(self.report_path.read_bytes(), retained)

    def test_changed_unused_receipt_field_cannot_reuse_old_assessment(self):
        self.run_suite()
        retained = self.report_path.read_bytes()
        path = self.results / "attempt-01.json"
        receipt = json.loads(path.read_text())
        receipt["usage"] = {"prompt_tokens": 999}
        path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "Retained assessment"):
            self.run_suite()
        self.assertEqual(self.runner_calls, 1)
        self.assertEqual(self.report_path.read_bytes(), retained)

    def test_changed_response_with_updated_receipt_hash_cannot_reuse_old_assessment(self):
        self.run_suite()
        retained = self.report_path.read_bytes()
        path = self.results / "response-01.json"
        raw = path.read_bytes() + b"\n"
        path.write_bytes(raw)
        receipt_path = self.results / "attempt-01.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["response_sha256"] = hashlib.sha256(raw).hexdigest()
        receipt_path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "Retained assessment"):
            self.run_suite()
        self.assertEqual(self.runner_calls, 1)
        self.assertEqual(self.report_path.read_bytes(), retained)

    def test_separate_bound_oracle_is_selected_without_changing_original(self):
        original = self.inputs / "oracle.json"
        bound = self.inputs / "oracle-bound.json"
        bound.write_bytes(original.read_bytes())
        original.write_text('{"historical_oracle":"preserved"}')
        original_contents = original.read_bytes()
        self.run_suite(oracle=bound)
        report = json.loads(self.report_path.read_text())
        self.assertEqual(report["oracle_sha256"], hashlib.sha256(bound.read_bytes()).hexdigest())
        self.assertEqual(original.read_bytes(), original_contents)

    def test_default_dry_run_does_not_create_requests_or_assessment(self):
        self.run_suite(execute=False)
        self.assertEqual(self.runner_calls, 1)
        self.assertEqual(self.scorer_calls, 0)
        self.assertFalse(self.results.exists())
        self.assertFalse(self.report_path.exists())


if __name__ == "__main__":
    unittest.main()
