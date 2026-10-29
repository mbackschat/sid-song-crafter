import copy
import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("compare_native_patch", ROOT / "scripts/compare-native-patch.py")
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)
RECIPE = ROOT / "songs/fuer-elise-sidwizard.json"
PATCH = ROOT / "songs/studies/fuer-elise-attack/triangle-attack.json"


def source_recipe():
    return json.loads(RECIPE.read_text())


def attack_patch():
    return {"format": "sidwizard-instrument-patch-v1", "instrument": "melody-pluck", "changes": [{"field": "wave", "row": 0, "column": 0, "from": "21", "to": "11"}]}


def prefix_fixture():
    manifest = {"stopTick": 10, "cellMap": [{"voice": 0, "tick": 0, "pattern": 1, "byteOffset": 0, "noteCode": 61, "instrument": 1}, {"voice": 0, "tick": 4, "pattern": 1, "byteOffset": 3, "noteCode": 62, "instrument": 1}], "voices": [{"notes": [{"startTick": 0, "nativeNote": 61, "instrument": 1}, {"startTick": 4, "nativeNote": 62, "instrument": 1}], "expectedPatternEntries": [{"tick": None, "pattern": 1}], "expectedSequenceEnding": [{"tick": 10, "entry": 160}, {"tick": 10, "entry": 254}]}, {"notes": [], "expectedPatternEntries": [{"tick": None, "pattern": 2}], "expectedSequenceEnding": []}, {"notes": [], "expectedPatternEntries": [{"tick": None, "pattern": 3}], "expectedSequenceEnding": []}]}
    observer = SimpleNamespace(cells=copy.deepcopy(manifest["cellMap"][:1]), starts=[{"voice": 0, "tick": 0, "nativeNote": 61, "instrument": 1}], sequence_reads=[{"voice": voice, "tick": None, "entry": voice + 1} for voice in range(3)])
    return manifest, observer


class NativePatchComparisonTest(unittest.TestCase):
    def test_exact_leaf_patch_preserves_every_other_recipe_value_and_original(self):
        original = source_recipe()
        before = copy.deepcopy(original)
        candidate = comparison.patch_recipe(original, attack_patch())
        expected = copy.deepcopy(original)
        expected["instruments"]["melody-pluck"]["wave"][0][0] = "11"
        self.assertEqual(candidate, expected)
        self.assertEqual(original, before)
        self.assertEqual(json.loads(PATCH.read_text()), attack_patch())

    def test_scalar_and_multiple_table_leaf_changes_use_existing_encoder_semantics(self):
        source = source_recipe()
        change = attack_patch()
        change["changes"].extend([{"field": "adsr", "from": "0754", "to": "0764"}, {"field": "wave", "row": 1, "column": 0, "from": "11", "to": "41"}])
        candidate = comparison.patch_recipe(source, change)
        self.assertEqual(candidate["instruments"]["melody-pluck"]["adsr"], "0764")
        self.assertEqual(candidate["instruments"]["melody-pluck"]["wave"][1][0], "41")
        change["changes"][1]["to"] = "07"
        with self.assertRaisesRegex(ValueError, "ADSR"):
            comparison.patch_recipe(source, change)
        change["changes"][1]["to"] = 7
        with self.assertRaises(ValueError):
            comparison.patch_recipe(source, change)

    def test_rejects_stale_duplicate_noop_unknown_and_nonleaf_patches(self):
        for mutate in (
            lambda value: value.update(format="other"),
            lambda value: value.update(instrument="missing"),
            lambda value: value.update(changes=[]),
            lambda value: value["changes"][0].update(**{"from": "41"}),
            lambda value: value["changes"][0].update(to="21"),
            lambda value: value["changes"].append(copy.deepcopy(value["changes"][0])),
            lambda value: value["changes"][0].update(field="name"),
            lambda value: value["changes"][0].update(row=-1),
            lambda value: value["changes"][0].update(row=True),
            lambda value: value["changes"][0].update(column=3),
            lambda value: value["changes"][0].pop("row"),
            lambda value: value["changes"][0].update(to=["11", "00", "00"]),
            lambda value: value["changes"][0].update(to="021"),
            lambda value: value["changes"][0].update(extra="unexpected"),
        ):
            value = attack_patch()
            mutate(value)
            with self.subTest(patch=value), self.assertRaises(ValueError):
                comparison.patch_recipe(source_recipe(), value)

    def test_schedule_guard_allows_only_derived_paths_and_content_hashes(self):
        base = {"recipePath": "a.json", "recipeSha256": "a", "nativePath": "a.swm", "nativeSha256": "a", "sourceSha256": "score", "sidCount": 1, "cellMap": [{"tick": 0, "instrument": 1}], "voices": [{"notes": [{"startTick": 0, "durationTicks": 4, "nativeNote": 61}], "sequence": [1], "expectedPatternEntries": [{"tick": None, "pattern": 1}]}]}
        candidate = dict(copy.deepcopy(base), recipePath="b.json", recipeSha256="b", nativePath="b.swm", nativeSha256="b")
        comparison.verify_same_schedule(base, candidate)
        for mutate in (
            lambda value: value.update(sourceSha256="other"),
            lambda value: value.update(sidCount=2),
            lambda value: value["voices"][0]["notes"][0].update(startTick=1),
            lambda value: value["voices"][0]["notes"][0].update(nativeNote=62),
            lambda value: value["voices"][0]["sequence"].append(2),
            lambda value: value["voices"][0]["expectedPatternEntries"][0].update(tick=0),
            lambda value: value["cellMap"][0].update(instrument=2),
        ):
            changed = copy.deepcopy(candidate)
            mutate(changed)
            with self.subTest(change=changed), self.assertRaisesRegex(ValueError, "schedule"):
                comparison.verify_same_schedule(base, changed)

    def test_excerpt_oracle_checks_only_requested_prefix_without_claiming_completion(self):
        manifest, observer = prefix_fixture()
        result = comparison.verify_excerpt(manifest, observer, 4)
        self.assertEqual(result["noteCounts"], [1, 0, 0])
        self.assertEqual(result["checkedCalls"], 4)
        self.assertFalse(result["fullSongCompletionChecked"])
        with self.assertRaisesRegex(ValueError, "before"):
            comparison.verify_excerpt(manifest, observer, 11)

    def test_excerpt_oracle_adds_the_instrument_octave_shift_to_the_written_note(self):
        manifest, observer = prefix_fixture()
        manifest["voices"][0]["notes"][0]["octaveShiftSemitones"] = -12
        observer.starts[0]["nativeNote"] = 61 - 12
        self.assertEqual(comparison.verify_excerpt(manifest, observer, 4)["noteCounts"], [1, 0, 0])
        observer.starts[0]["nativeNote"] = 61
        with self.assertRaisesRegex(ValueError, "note starts"):
            comparison.verify_excerpt(manifest, observer, 4)

    def test_excerpt_oracle_rejects_missing_extra_mistimed_and_wrong_voice_events(self):
        for mutate in (
            lambda value: value.cells.clear(),
            lambda value: value.cells[0].update(tick=1),
            lambda value: value.cells[0].update(voice=4),
            lambda value: value.starts.clear(),
            lambda value: value.starts[0].update(instrument=2),
            lambda value: value.starts.append(dict(value.starts[0], tick=3)),
            lambda value: value.sequence_reads[0].update(entry=2),
            lambda value: value.sequence_reads.append({"voice": 1, "tick": 3, "entry": 254}),
        ):
            manifest, observer = prefix_fixture()
            mutate(observer)
            with self.subTest(change=mutate), self.assertRaises(ValueError):
                comparison.verify_excerpt(manifest, observer, 4)

    def test_invalid_duration_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "unused"
            for seconds in (0, -1, math.inf, math.nan, 60.1, 0.000001):
                with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                    comparison.run_comparison(RECIPE, PATCH, output, seconds=seconds)
                self.assertFalse(output.exists())

    @unittest.skipUnless((ROOT / ".tools/sid-wizard-exporter/exporter.labels").is_file() and (ROOT / ".local/bin/render-sid").is_file(), "Pinned exporter and renderer required")
    def test_actual_native_exports_verify_schedule_and_render_the_declared_attack_change(self):
        recipe_bytes, patch_bytes = RECIPE.read_bytes(), PATCH.read_bytes()
        source = RECIPE.parent / source_recipe()["score"]
        score_bytes = source.read_bytes()
        with tempfile.TemporaryDirectory() as directory, patch("builtins.print"):
            output = Path(directory) / "comparison"
            report = comparison.run_comparison(RECIPE, PATCH, output, seconds=0.5)
            self.assertEqual(RECIPE.read_bytes(), recipe_bytes)
            self.assertEqual(PATCH.read_bytes(), patch_bytes)
            self.assertEqual(source.read_bytes(), score_bytes)
            self.assertEqual((output / "inputs/recipe.json").read_bytes(), recipe_bytes)
            self.assertEqual((output / "inputs/patch.json").read_bytes(), patch_bytes)
            self.assertEqual((output / "inputs/score.json").read_bytes(), score_bytes)
            self.assertEqual(report["evidenceLevel"], "excerpt comparison")
            self.assertFalse(report["fullSongCompletionChecked"])
            self.assertIsNone(report["listeningReview"])
            self.assertTrue(report["sameSchedule"])
            a, b = report["variants"]["A"], report["variants"]["B"]
            self.assertEqual(a["schedule"]["checkedCalls"], 27)
            self.assertEqual(a["schedule"], b["schedule"])
            for variant in (a, b):
                derived = json.loads(Path(variant["recipe"]).read_text())
                self.assertEqual(Path(derived["score"]), (output / "inputs/score.json").resolve())
                self.assertEqual(variant["pcm"]["frames"], 22050)
                self.assertEqual(variant["pcm"]["clippedSamples"], 0)
                self.assertGreater(variant["pcm"]["acRms"], 1)
            self.assertNotEqual(a["pcm"]["sha256"], b["pcm"]["sha256"])
            frames = [json.loads(Path(variant["frames"]).read_text()) for variant in (a, b)]
            self.assertEqual([state[:4] for state in frames[0]], [state[:4] for state in frames[1]])
            self.assertEqual(frames[0][1][4], 0x21)
            self.assertEqual(frames[1][1][4], 0x11)
            matched = report["comparison"]["inputs"]
            self.assertLess(abs(matched[0]["matched"]["acRms"] - matched[1]["matched"]["acRms"]), 1)
            self.assertTrue(all(Path(value["matchedCopy"]).is_file() for value in matched))
            saved = (output / "comparison.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "exists"):
                comparison.run_comparison(RECIPE, PATCH, output, seconds=0.5)
            self.assertEqual((output / "comparison.json").read_bytes(), saved)


if __name__ == "__main__":
    unittest.main()
