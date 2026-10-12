import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("verify_player", ROOT / "scripts/verify_player.py")
verification = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verification)


class ExactPlayerVerificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="exact-player-")
        cls.directory = Path(cls.temporary.name)
        instrument = {"waveform": 16, "attackDecay": 2, "sustainRelease": 0x90}
        score = {
            "title": "Gate edge fixture", "composer": "Test fixture", "quarterBpm": 72,
            "totalBeats": 2, "tailTicks": 5, "volume": 15,
            "voices": [
                {"instrument": instrument, "events": [{"startBeat": 0, "durationBeats": 0.125, "midi": 69}, {"startBeat": 0.125, "durationBeats": 0.125, "midi": 69}]},
                {"instrument": instrument, "events": [{"startBeat": 0, "durationBeats": 1, "midi": 48}]},
                {"instrument": instrument, "events": [{"startBeat": 1 / 48, "durationBeats": 1 / 48, "midi": 67}]},
            ],
        }
        source = cls.directory / "score.json"
        source.write_text(json.dumps(score))
        subprocess.run(["bun", "scripts/build-arrangement.ts", str(source), str(cls.directory), "fixture"], cwd=ROOT, check=True, timeout=30, capture_output=True)
        cls.manifest = json.loads((cls.directory / "fixture.events.json").read_text())
        cls.sid = (cls.directory / "fixture.sid").read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def corrupted_sid(self, name, mutate):
        data = bytearray(self.sid)
        mutate(data)
        path = self.directory / f"{name}.sid"
        path.write_bytes(data)
        return path

    def stream_value_offset(self, index):
        return self.sid[6] * 256 + self.sid[7] + self.manifest["symbols"]["event_stream"] - 0x1000 + index * 4 + 3

    def test_checks_every_write_including_repeated_pitch_and_one_frame_grace_edges(self):
        evidence = verification.verify_callable(self.manifest, self.directory / "fixture.sid")
        self.assertEqual(evidence["noteCounts"], [2, 1, 1])
        self.assertEqual(evidence["playWriteCount"], 20)
        self.assertEqual(evidence["checkedTicks"], self.manifest["totalTicks"] + 1)
        self.assertTrue(evidence["restartVerified"])
        self.assertTrue(evidence["zeroPagePreserved"])

    def test_rejects_a_missing_gate_off_between_identical_pitches_in_the_actual_binary(self):
        index = next(i for i, write in enumerate(self.manifest["writes"]) if write["address"] == 0xd404 and write["value"] == 16 and write["tick"] < 10)
        path = self.corrupted_sid("lost-release", lambda data: data.__setitem__(self.stream_value_offset(index), 17))
        with self.assertRaisesRegex(ValueError, "SID writes differ"):
            verification.verify_callable(self.manifest, path)

    def test_rejects_a_missing_one_frame_grace_gate_on_in_the_actual_binary(self):
        index = next(i for i, write in enumerate(self.manifest["writes"]) if write["address"] == 0xd412 and write["value"] == 17)
        path = self.corrupted_sid("lost-grace", lambda data: data.__setitem__(self.stream_value_offset(index), 16))
        with self.assertRaisesRegex(ValueError, "SID writes differ"):
            verification.verify_callable(self.manifest, path)

    def test_rejects_a_manifest_schedule_that_disagrees_with_its_musical_events(self):
        manifest = json.loads(json.dumps(self.manifest))
        manifest["writes"][0]["tick"] += 1
        with self.assertRaisesRegex(ValueError, "Manifest writes disagree"):
            verification.verify_callable(manifest, self.directory / "fixture.sid")

    def test_rejects_a_corrupted_initial_envelope_in_the_actual_binary(self):
        def mutate(data):
            index = data.index(bytes((0xa9, 2, 0x8d, 5, 0xd4)), 0x7c)
            data[index + 1] = 3
        path = self.corrupted_sid("wrong-envelope", mutate)
        with self.assertRaisesRegex(ValueError, "Initialization writes differ"):
            verification.verify_callable(self.manifest, path)


if __name__ == "__main__":
    unittest.main()
