import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("native_song_motion", ROOT / "scripts/native-song.py")
native_song = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native_song)
SOURCE = ROOT / "songs/studies/bach-toccata-integrated-motion"
ACCEPTED = ROOT / "songs/studies/bach-toccata-opening-driven"


class BachIntegratedMotionTest(unittest.TestCase):
    @unittest.skipUnless((ROOT / ".tools/sid-wizard-exporter/exporter.labels").is_file() and (ROOT / ".local/bin/render-sid").is_file(), "Pinned native exporter and renderer required")
    def test_cpu_executes_finite_onset_then_slower_body_without_score_changes(self):
        self.assertEqual((SOURCE / "score.json").read_bytes(), (ACCEPTED / "score.json").read_bytes())
        accepted = json.loads((ACCEPTED / "hybrid.json").read_text())
        candidate = json.loads((SOURCE / "hybrid.json").read_text())
        accepted["instruments"]["lead"]["pulse"] = candidate["instruments"]["lead"]["pulse"]
        self.assertEqual(candidate, accepted)
        onset = [0x400] + [0x400 + 0x40 * step for step in range(1, 17)] + [0x800]
        body = ([0x800 - 0x18 * step for step in range(1, 33)] + [0x500]
                + [0x500 + 0x18 * step for step in range(1, 33)] + [0x800, 0x800])
        with tempfile.TemporaryDirectory() as directory, patch("builtins.print"):
            output = Path(directory) / "song"
            report = native_song.run_song(SOURCE / "hybrid.json", output, excerpt_seconds=12)
            frames = json.loads((output / "native-song.frames.json").read_text())
            conversion = json.loads((output / "conversion.json").read_text())
            checked = 0
            for note in conversion["voices"][0]["notes"]:
                start, end = note["startTick"] + 1, note["gateOffTick"]
                for age, state in enumerate(frames[start:end]):
                    width = state[2] | (state[3] & 15) << 8
                    expected = onset[age] if age < len(onset) else body[(age - len(onset)) % len(body)]
                    self.assertEqual(width, expected, f"Lead note {note['eventIndex']} tick {start + age}")
                    checked += 1
            self.assertGreater(checked, 450)
            self.assertEqual(report["schedule"]["noteCounts"], [21, 20, 4])
            self.assertTrue(report["schedule"]["postStopGatesAndVolumeClear"])
            self.assertEqual(report["pcm"]["clippedSamples"], 0)


if __name__ == "__main__":
    unittest.main()
