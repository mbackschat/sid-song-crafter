import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SongWorkflowTests(unittest.TestCase):
    def test_another_arrangement_builds_renders_and_returns_to_basic(self):
        (ROOT / "build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/song.py"),
                 str(ROOT / "tests/fixtures/three-voice-score.json"),
                 "--output", directory, "--name", "another-song"],
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            evidence = json.loads((Path(directory) / "another-song.verification.json").read_text())
            self.assertEqual(evidence["registers"]["noteCounts"], [1, 1, 1])
            self.assertTrue(evidence["vice"]["returnedToBasic"])
            for extension in ("sid", "prg", "wav", "events.json"):
                self.assertGreater((Path(directory) / f"another-song.{extension}").stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
