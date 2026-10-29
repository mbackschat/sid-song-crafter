import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("converter_identity", ROOT / "scripts/verify-converter-identity.py")
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)
FIXTURE = ROOT / "tests/fixtures/sidwizard-2sid/recipe.json"


def baseline_with_changed_pitch(ref, destination):
    """Stand in for `git archive`: copy the current converter sources but shift every written note by one semitone."""
    scripts = Path(destination) / "scripts"
    scripts.mkdir()
    for source in (ROOT / "scripts").glob("*.py"):
        shutil.copy(source, scripts / source.name)
    arranger = scripts / "arrange-sidwizard.py"
    changed = arranger.read_text().replace('note["nativeNote"] = written - 11', 'note["nativeNote"] = written - 10')
    assert changed != arranger.read_text()
    arranger.write_text(changed)
    return arranger


class ConverterIdentityTest(unittest.TestCase):
    def test_discovery_finds_recipes_by_format_marker_in_every_searched_root(self):
        found = {path.relative_to(ROOT).as_posix() for path in GUARD.discover_recipes()}
        self.assertIn("songs/fuer-elise-sidwizard.json", found)
        self.assertIn("tests/fixtures/sidwizard-2sid/recipe.json", found)
        self.assertNotIn("tests/fixtures/sidwizard-2sid/score.json", found)

    def test_differences_name_every_observable_that_changed(self):
        baseline = (0, b"out", b"", {"a": b"1", "b": b"2"})
        self.assertEqual(GUARD.differences(baseline, baseline), [])
        current = (1, b"x", b"e", {"a": b"9", "c": b"3"})
        self.assertEqual(GUARD.differences(baseline, current), ["exit code", "stdout", "stderr", "a bytes", "b only in baseline", "c only in current"])

    def test_missing_score_is_replaced_by_a_stand_in_that_still_converts(self):
        with tempfile.TemporaryDirectory() as directory:
            recipe = Path(directory) / "recipe.json"
            recipe.write_text(json.dumps(json.loads(FIXTURE.read_text()), indent=1))
            usable, stand_in = GUARD.usable_recipe(recipe, directory)
            self.assertTrue(stand_in)
            self.assertEqual(GUARD.convert(ROOT / "scripts/arrange-sidwizard.py", usable, None)[0], 0)
        self.assertEqual(GUARD.usable_recipe(FIXTURE, "unused"), (FIXTURE, False))

    def test_unchanged_converter_is_identical_and_a_changed_one_is_reported(self):
        identical = GUARD.verify("HEAD", [FIXTURE], [None], 1)
        self.assertEqual([(row[3], row[4]) for row in identical], [(True, [])])
        with patch.object(GUARD, "export_baseline", baseline_with_changed_pitch):
            changed = GUARD.verify("HEAD", [FIXTURE], [None], 1)
        self.assertIn("recipe.sws bytes", changed[0][4])


if __name__ == "__main__":
    unittest.main()
