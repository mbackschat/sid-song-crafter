import importlib.util
import math
from pathlib import Path
import tempfile
import unittest
import sys
import subprocess


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("verify_arrangement", ROOT / "scripts/verify-arrangement.py")
verification = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verification)


def fixture():
    clock = 17734475 / 18
    voices = []
    for voice, midi in enumerate((69, 71, 72)):
        word = round(440 * 2 ** ((midi - 69) / 12) * 2**24 / clock)
        voices.append({
            "instrument": {"waveform": 16, "attackDecay": 6, "sustainRelease": 65},
            "events": [{"voice": voice, "midi": midi, "startTick": voice * 10, "durationTicks": 10, "gateOffTick": voice * 10 + 8, "frequencyWord": word}],
        })
    rows = []
    writes = []
    for voice, part in enumerate(voices):
        event = part["events"][0]
        writes.extend([
            {"tick": event["startTick"], "address": 0xd400 + voice * 7, "value": event["frequencyWord"] & 255},
            {"tick": event["startTick"], "address": 0xd401 + voice * 7, "value": event["frequencyWord"] >> 8},
            {"tick": event["startTick"], "address": 0xd404 + voice * 7, "value": 17},
            {"tick": event["gateOffTick"], "address": 0xd404 + voice * 7, "value": 16},
        ])
    writes.append({"tick": 30, "address": 0xd418, "value": 0})
    writes.sort(key=lambda write: write["tick"])
    for tick in range(36):
        state = bytearray(32)
        state[24] = 0 if tick >= 30 else 15
        for voice, part in enumerate(voices):
            event = part["events"][0]
            offset = voice * 7
            state[offset] = (event["frequencyWord"] & 255) if tick >= event["startTick"] else 0
            state[offset + 1] = (event["frequencyWord"] >> 8) if tick >= event["startTick"] else 0
            state[offset + 3] = 8
            state[offset + 4] = 16 | int(event["startTick"] <= tick < event["gateOffTick"])
            state[offset + 5] = 6
            state[offset + 6] = 65
        rows.append((round(tick * 20), state))
    return {"clockHz": clock, "ticksPerSecond": 50, "totalTicks": 35, "durationSeconds": 0.7, "volume": 15, "voices": voices, "writes": writes}, rows


def write_trace(path, rows):
    path.write_text("time_ms\tregisters_hex\n" + "".join(f"{timestamp}\t{state.hex()}\n" for timestamp, state in rows))


class ArrangementVerificationTest(unittest.TestCase):
    def test_checks_notes_and_releases_on_each_voice(self):
        manifest, rows = fixture()
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.tsv"
            write_trace(trace, rows)
            evidence = verification.verify_register_trace(manifest, trace)
        self.assertEqual(evidence["noteCounts"], [1, 1, 1])
        self.assertEqual(evidence["snapshots"], len(rows))
        self.assertNotIn("frames", evidence)

    def test_rejects_wrong_frequency_on_a_non_melody_voice(self):
        manifest, rows = fixture()
        rows[10][1][7] ^= 64
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.tsv"
            write_trace(trace, rows)
            with self.assertRaisesRegex(ValueError, "voice 2.*frequency"):
                verification.verify_register_trace(manifest, trace)

    def test_rejects_a_missing_onset_even_when_other_voices_match(self):
        manifest, rows = fixture()
        for _, state in rows:
            state[18] &= 254
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.tsv"
            write_trace(trace, rows)
            with self.assertRaisesRegex(ValueError, "voice 3"):
                verification.verify_register_trace(manifest, trace)

    def test_accepts_a_snapshot_between_frequency_writes_and_the_gate_write(self):
        manifest, rows = fixture()
        rows[10][1][11] = 16
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.tsv"
            write_trace(trace, rows)
            evidence = verification.verify_register_trace(manifest, trace)
        self.assertEqual(evidence["noteCounts"], [1, 1, 1])

    def test_pcm_health_rejects_sound_persisting_after_the_ending(self):
        samples = [round(2000 * math.sin(2 * math.pi * 440 * index / 44100)) for index in range(44100)]
        with self.assertRaisesRegex(ValueError, "ending"):
            verification.verify_pcm_health(samples, 44100)

    def test_pitch_anchor_does_not_treat_a_slow_releasing_voice_as_silent(self):
        manifest, _ = fixture()
        manifest["voices"][0]["events"][0].update(startTick=10, gateOffTick=28)
        manifest["voices"][1]["events"][0].update(startTick=0, gateOffTick=1)
        manifest["voices"][1]["instrument"]["sustainRelease"] = 0x6f
        manifest["voices"][2]["events"] = []
        samples = [round(2000 * math.sin(2 * math.pi * 440 * index / 44100)) for index in range(44100)]
        self.assertEqual(verification.verify_pitch_anchors(manifest, samples, 0), [])

    def test_failed_prerequisite_check_removes_an_old_success_report(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "arrangement.events.json"
            report = Path(directory) / "arrangement.verification.json"
            manifest.write_text("{}")
            report.write_text("previous success")
            result = subprocess.run([sys.executable, str(ROOT / "scripts/verify-arrangement.py"), str(manifest)], capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(report.exists())


if __name__ == "__main__":
    unittest.main()
