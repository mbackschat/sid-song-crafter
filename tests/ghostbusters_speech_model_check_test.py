"""Guard the speech trial's withheld controls and response fingerprints."""

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ghostbusters_speech_assessor_tests',
    ROOT / 'scripts/studies/ghostbusters/assess-speech-model-check.py')
assessor = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = assessor
spec.loader.exec_module(assessor)


class GhostbustersSpeechModelCheckTest(unittest.TestCase):
    def test_silence_requires_empty_transcript_and_normal_completion(self):
        expected = dict(category='silence', requiredTranscript='')
        parsed = assessor.parse_observation('{"category":"silence","evidence":"none","transcript":""}')
        self.assertTrue(assessor.grade_control(parsed, expected, 'stop')['passed'])
        for transcript in ('word', ' '):
            self.assertFalse(assessor.grade_control(dict(parsed, transcript=transcript), expected, 'stop')['passed'])
        self.assertFalse(assessor.grade_control(parsed, expected, 'length')['passed'])
        self.assertFalse(assessor.grade_control(None, expected, 'stop')['passed'])

    def test_speech_requires_every_word_and_accepts_case_punctuation_and_digit_seven(self):
        expected = dict(category='speech', requiredWords=['the', 'blue', 'lantern', 'is', 'beside', 'seven', 'wooden', 'boxes'])
        parsed = assessor.parse_observation('```json\n{"category":"speech","evidence":"voice","transcript":"THE blue lantern is beside 7 wooden boxes!"}\n```')
        self.assertTrue(assessor.grade_control(parsed, expected, 'stop')['passed'])
        failed = assessor.grade_control(dict(parsed, transcript='The blue lantern beside seven wooden boxes.'), expected, 'stop')
        self.assertFalse(failed['passed'])
        self.assertEqual(failed['missingWords'], ['is'])

    def test_response_bytes_and_payload_bindings_must_match_completed_receipt(self):
        expected = dict(id='p01', audio_sha256='a' * 64, payload_sha256='b' * 64,
            duration_seconds=4.45, model='qwen/qwen3.8-omni-flash', max_tokens=1200,
            reasoning=False, reasoning_effort=None)
        response = dict(model=expected['model'], provider='test', usage=dict(cost=0.0001),
            choices=[dict(finish_reason='stop', message=dict(content='{"category":"speech","evidence":"voice","transcript":"unscored words"}'))])
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            raw = json.dumps(response).encode()
            response_path = directory / 'response-01.json'
            response_path.write_bytes(raw)
            receipt = dict(expected, status='complete', cost=0.0001, usage=response['usage'],
                response_path=response_path.name, response_sha256=hashlib.sha256(raw).hexdigest())
            path = directory / 'attempt-01.json'
            path.write_text(json.dumps(receipt))
            self.assertEqual(assessor.read_bound_response(path, expected)['observation']['transcript'], 'unscored words')
            changed = deepcopy(receipt)
            changed['payload_sha256'] = 'c' * 64
            path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, 'payload_sha256'):
                assessor.read_bound_response(path, expected)
            path.write_text(json.dumps(receipt))
            response_path.write_bytes(raw + b' ')
            with self.assertRaisesRegex(ValueError, 'Response fingerprint'):
                assessor.read_bound_response(path, expected)


if __name__ == '__main__':
    unittest.main()
