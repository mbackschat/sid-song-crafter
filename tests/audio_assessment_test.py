import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import wave


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audio_assessment


class Response(io.BytesIO):
    def __init__(self, value):
        super().__init__(json.dumps(value).encode())


class Transport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return Response(response)


def key_info(**changes):
    value = {"limit": 10, "limit_remaining": 10, "limit_reset": None}
    value.update(changes)
    return {"data": value}


def completion(cost=0.002):
    return {"id": "completion-1", "choices": [{"message": {"content": "The audio has two sections."}}], "usage": {"cost": cost, "prompt_tokens": 20, "completion_tokens": 8}}


class AudioAssessmentTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.output = self.root / "build" / "trial"
        self.key = self.root / "key"
        self.key.write_text("private-test-token\n")
        self.wav = self.root / "clip.wav"
        self.write_wav()
        self.manifest = self.root / "manifest.json"
        self.document = {"model": "qwen/qwen3.8-omni-flash", "max_tokens": 1200, "cases": [{"id": "first", "prompt": "Describe the sections.", "wav": "clip.wav"}]}
        self.write_manifest()
        root_patch = patch.object(audio_assessment, "ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)

    def write_wav(self, frames=8000):
        with wave.open(str(self.wav), "wb") as output:
            output.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
            output.writeframes(b"\x01\x00" * frames)

    def write_manifest(self):
        self.manifest.write_text(json.dumps(self.document))

    def run_trial(self, transport, **options):
        return audio_assessment.run_trial(self.manifest, self.output, self.key, opener=transport, **options)

    def test_dry_run_checks_audio_without_key_network_or_output_writes(self):
        self.key.unlink()
        transport = Transport([])
        result = self.run_trial(transport, dry_run=True)
        self.assertEqual(result[0]["id"], "first")
        self.assertEqual(result[0]["duration_seconds"], 1)
        self.assertFalse(self.output.exists())
        self.assertEqual(transport.requests, [])

    def test_exact_payload_cache_avoids_key_and_network_access(self):
        transport = Transport([key_info(), completion()])
        self.run_trial(transport)
        self.key.unlink()
        result = self.run_trial(Transport([]))
        self.assertTrue(result[0]["cached"])
        self.assertEqual(len(transport.requests), 2)

    def test_audio_prompt_model_token_reasoning_and_effort_changes_invalidate_cache(self):
        transport = Transport([key_info(), completion()] * 7)
        hashes = [self.run_trial(transport)[0]["payload_sha256"]]
        self.write_wav(frames=4000)
        hashes.append(self.run_trial(transport)[0]["payload_sha256"])
        self.document["cases"][0]["prompt"] = "Describe the timbre."
        self.write_manifest()
        hashes.append(self.run_trial(transport)[0]["payload_sha256"])
        self.document["model"] = "another/audio-model"
        self.write_manifest()
        hashes.append(self.run_trial(transport)[0]["payload_sha256"])
        self.document["max_tokens"] = 500
        self.write_manifest()
        hashes.append(self.run_trial(transport)[0]["payload_sha256"])
        self.document["reasoning"] = True
        self.write_manifest()
        hashes.append(self.run_trial(transport)[0]["payload_sha256"])
        self.assertEqual(json.loads(transport.requests[-1][0].data)["reasoning"], {"enabled": True})
        self.document["reasoning_effort"] = "low"
        self.write_manifest()
        final = self.run_trial(transport)[0]
        hashes.append(final["payload_sha256"])
        self.assertEqual(len(set(hashes)), 7)
        self.assertEqual(len(list(self.output.glob("attempt-*.json"))), 7)
        self.assertEqual(json.loads(transport.requests[-1][0].data)["reasoning"], {"enabled": True, "effort": "low"})
        self.assertEqual(json.loads((self.output / "attempt-07.json").read_text())["reasoning_effort"], "low")

    def test_cache_tampering_refuses_to_repeat_a_billed_request(self):
        self.run_trial(Transport([key_info(), completion()]))
        (self.output / "response-01.json").write_text("{}")
        transport = Transport([])
        with self.assertRaisesRegex(audio_assessment.TrialError, "missing or changed"):
            self.run_trial(transport)
        self.assertEqual(transport.requests, [])

    def test_reasoning_requires_a_boolean_before_network(self):
        for value in ("false", 0, None, {}):
            self.document["reasoning"] = value
            self.write_manifest()
            transport = Transport([])
            with self.assertRaisesRegex(audio_assessment.TrialError, "reasoning.*boolean"):
                self.run_trial(transport)
            self.assertEqual(transport.requests, [])

    def test_reasoning_effort_requires_supported_value_and_enabled_reasoning(self):
        self.document["reasoning"] = True
        for value in ("minimal", "", 0, None):
            self.document["reasoning_effort"] = value
            self.write_manifest()
            transport = Transport([])
            with self.assertRaisesRegex(audio_assessment.TrialError, "reasoning_effort"):
                self.run_trial(transport)
            self.assertEqual(transport.requests, [])
        self.document["reasoning"] = False
        self.document["reasoning_effort"] = "low"
        self.write_manifest()
        transport = Transport([])
        with self.assertRaisesRegex(audio_assessment.TrialError, "reasoning.*true"):
            self.run_trial(transport)
        self.assertEqual(transport.requests, [])

    def test_reasoning_effort_accepts_low_medium_and_high(self):
        self.document["reasoning"] = True
        transport = Transport([key_info(), completion()] * 3)
        for effort in ("low", "medium", "high"):
            self.document["reasoning_effort"] = effort
            self.write_manifest()
            self.run_trial(transport)
            self.assertEqual(json.loads(transport.requests[-1][0].data)["reasoning"], {"enabled": True, "effort": effort})

    def test_request_marker_precedes_post_and_receipt_excludes_credentials_and_audio(self):
        transport = Transport([key_info(), completion()])
        def opener(request, timeout):
            if request.method == "POST":
                marker = json.loads((self.output / "attempt-01.json").read_text())
                self.assertEqual(marker["status"], "pending")
            return transport(request, timeout)
        result = self.run_trial(opener)
        post, timeout = transport.requests[1]
        payload = json.loads(post.data)
        self.assertEqual(timeout, 45)
        self.assertEqual(post.full_url, "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(payload["reasoning"], {"enabled": False})
        self.assertEqual(payload["provider"], {"allow_fallbacks": False})
        self.assertEqual(payload["temperature"], 0)
        self.assertEqual(payload["messages"][0]["content"][1]["input_audio"]["format"], "wav")
        written = "".join(path.read_text() for path in self.output.glob("*.json"))
        self.assertNotIn("private-test-token", written)
        self.assertNotIn(payload["messages"][0]["content"][1]["input_audio"]["data"], written)
        self.assertEqual(result[0]["cost"], 0.002)

    def test_rejects_case_count_token_budget_and_audio_bounds_before_network(self):
        transport = Transport([])
        self.document["cases"] *= 9
        self.write_manifest()
        with self.assertRaisesRegex(audio_assessment.TrialError, "eight"):
            self.run_trial(transport)
        self.document["cases"] = [self.document["cases"][0]]
        self.document["max_tokens"] = 1201
        self.write_manifest()
        with self.assertRaisesRegex(audio_assessment.TrialError, "1200"):
            self.run_trial(transport)
        self.document["max_tokens"] = 1200
        self.write_manifest()
        self.write_wav(frames=8000 * 31)
        with self.assertRaisesRegex(audio_assessment.TrialError, "30 seconds"):
            self.run_trial(transport)
        self.wav.write_bytes(b"x" * (8 * 1024 * 1024 + 1))
        with self.assertRaisesRegex(audio_assessment.TrialError, "8 MiB"):
            self.run_trial(transport)
        self.assertEqual(transport.requests, [])

    def test_rejects_non_pcm_empty_and_truncated_wav(self):
        for contents in (b"not a wav", self.wav.read_bytes()[:-2]):
            self.wav.write_bytes(contents)
            with self.assertRaises(audio_assessment.TrialError):
                self.run_trial(Transport([]), dry_run=True)
        self.write_wav(frames=0)
        with self.assertRaises(audio_assessment.TrialError):
            self.run_trial(Transport([]), dry_run=True)

    def test_rejects_outputs_outside_build(self):
        with self.assertRaisesRegex(audio_assessment.TrialError, "build"):
            audio_assessment.run_trial(self.manifest, self.root / "elsewhere", self.key, dry_run=True)

    def test_key_cap_remaining_and_reset_guards_precede_post(self):
        for data in ({"limit": None}, {"limit": 11}, {"limit": float("inf")}, {"limit_remaining": 0.009}, {"limit_remaining": None}, {"limit_reset": "monthly"}):
            with self.subTest(data=data):
                transport = Transport([key_info(**data)])
                with self.assertRaises(audio_assessment.TrialError):
                    self.run_trial(transport)
                self.assertEqual(len(transport.requests), 1)
                self.assertFalse(list(self.output.glob("attempt-*.json")))

    def test_trial_cost_reserve_stops_before_second_post(self):
        self.document["cases"].append({"id": "second", "prompt": "Another question.", "wav": "clip.wav"})
        self.write_manifest()
        transport = Transport([key_info(), completion(cost=0.091)])
        with self.assertRaisesRegex(audio_assessment.TrialError, "cost"):
            self.run_trial(transport)
        self.assertEqual(len(transport.requests), 2)
        self.assertEqual(json.loads((self.output / "attempt-01.json").read_text())["cost"], 0.091)

    def test_eight_attempt_guard_includes_existing_errors(self):
        self.output.mkdir(parents=True)
        for number in range(1, 9):
            (self.output / f"attempt-{number:02d}.json").write_text(json.dumps({"status": "http_error", "cost": 0, "payload_sha256": f"old-{number}"}))
        transport = Transport([])
        with self.assertRaisesRegex(audio_assessment.TrialError, "eight"):
            self.run_trial(transport)
        self.assertEqual(transport.requests, [])

    def test_uncertain_transport_failure_is_not_retried(self):
        transport = Transport([key_info(), URLError("private-test-token")])
        with self.assertRaisesRegex(audio_assessment.TrialError, "transport"):
            self.run_trial(transport)
        marker = json.loads((self.output / "attempt-01.json").read_text())
        self.assertEqual(marker["status"], "pending")
        with self.assertRaisesRegex(audio_assessment.TrialError, "uncertain"):
            self.run_trial(Transport([]))

    def test_missing_cost_stores_response_and_blocks_subsequent_calls(self):
        response = completion()
        del response["usage"]["cost"]
        with self.assertRaisesRegex(audio_assessment.TrialError, "usage.cost"):
            self.run_trial(Transport([key_info(), response]))
        self.assertTrue((self.output / "response-01.json").is_file())
        with self.assertRaisesRegex(audio_assessment.TrialError, "unknown cost"):
            self.run_trial(Transport([]))

    def test_http_error_never_discloses_remote_body_or_retries(self):
        error = HTTPError("https://openrouter.ai/api/v1/chat/completions", 400, "private-test-token", {}, io.BytesIO(b"private-test-token echoed audio"))
        with self.assertRaisesRegex(audio_assessment.TrialError, "HTTP 400") as caught:
            self.run_trial(Transport([key_info(), error]))
        self.assertNotIn("private-test-token", str(caught.exception))
        marker = json.loads((self.output / "attempt-01.json").read_text())
        self.assertEqual(marker["status"], "http_error")
        self.assertEqual(marker["http_status"], 400)
        self.assertNotIn("private-test-token", (self.output / "attempt-01.json").read_text())


if __name__ == "__main__":
    unittest.main()
