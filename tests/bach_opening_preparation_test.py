import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "songs/studies/bach-toccata-opening"
spec = importlib.util.spec_from_file_location("bach_opening", ROOT / "scripts/studies/bach/prepare-opening.py")
preparation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preparation)


def read_json(path):
    return json.loads(path.read_text())


class BachOpeningPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output_root = Path(self.temporary.name)

    def prepare(self, name, pacing=None, source_bundle=None):
        output = self.output_root / name
        options = {}
        if pacing is not None:
            options["pacing"] = pacing
        if source_bundle is not None:
            options["source_bundle"] = source_bundle
        with contextlib.redirect_stdout(io.StringIO()):
            preparation.prepare(BASELINE / "source", output, **options)
        return output

    def test_default_reproduces_frozen_original_musical_inputs(self):
        output = self.prepare("original")
        for name in ("score.json", "restrained.json", "hybrid.json", "source-notes.json"):
            with self.subTest(name=name):
                self.assertEqual((BASELINE / name).read_bytes(), (output / name).read_bytes())
        original = read_json(BASELINE / "preparation.json")
        generated = read_json(output / "preparation.json")
        original.pop("scriptSha256")
        generated.pop("scriptSha256")
        self.assertEqual(original, generated)

    def test_driven_changes_timing_without_changing_source_mapping_or_sound(self):
        output = self.prepare("driven", "driven")
        original_score = read_json(BASELINE / "score.json")
        driven_score = read_json(output / "score.json")
        for original_voice, driven_voice in zip(original_score["voices"], driven_score["voices"]):
            self.assertEqual(original_voice["name"], driven_voice["name"])
            self.assertEqual([event["midi"] for event in original_voice["events"]],
                             [event["midi"] for event in driven_voice["events"]])
        fields = ("voice", "eventIndex", "sourceId", "sourceStartBeat", "sourceEndBeat", "transposeSemitones", "midi")
        original_metadata = read_json(BASELINE / "preparation.json")
        driven_metadata = read_json(output / "preparation.json")
        self.assertEqual([{key: entry[key] for key in fields} for entry in original_metadata["mapping"]],
                         [{key: entry[key] for key in fields} for entry in driven_metadata["mapping"]])
        self.assertEqual(original_metadata["reductions"], driven_metadata["reductions"])
        for name in ("restrained.json", "hybrid.json"):
            self.assertEqual(read_json(BASELINE / name)["instruments"], read_json(output / name)["instruments"])
        self.assertEqual(original_score["tailTicks"], driven_score["tailTicks"])

    def test_driven_reduces_holds_and_silence_but_preserves_descent_speed(self):
        output = self.prepare("driven", "driven")
        original = read_json(BASELINE / "preparation.json")["mapping"]
        driven = read_json(output / "preparation.json")["mapping"]
        for source_start in (0, 2, 4):
            event = next(entry for entry in driven if entry["voice"] == "melody" and entry["sourceStartBeat"] == source_start)
            self.assertLessEqual(event["durationBeats"], 0.8)
        for descent_start, descent_end in ((0.625, 1), (2.625, 3), (4.625, 5)):
            for before, after in zip(original, driven):
                if descent_start <= before["sourceStartBeat"] < descent_end:
                    self.assertAlmostEqual(before["durationBeats"], after["durationBeats"], places=8)

        def silent_spans(mapping):
            spans = []
            previous_end = 0
            for event in sorted(mapping, key=lambda entry: entry["startBeat"]):
                if event["startBeat"] > previous_end + 1e-8:
                    spans.append(event["startBeat"] - previous_end)
                previous_end = max(previous_end, event["startBeat"] + event["durationBeats"])
            return spans

        original_gaps, driven_gaps = silent_spans(original), silent_spans(driven)
        self.assertLessEqual(max(driven_gaps), 0.4 + 1e-8)
        self.assertLess(sum(driven_gaps), sum(original_gaps) / 3)

    def test_both_profiles_derive_complete_sections_and_chord_metadata_from_warp(self):
        for pacing, expected in (("original", [0, 18, 22, 24]), ("driven", [0, 8.2, 10.2, 12])):
            with self.subTest(pacing=pacing):
                output = self.prepare(pacing, pacing)
                score = read_json(output / "score.json")
                hybrid = read_json(output / "hybrid.json")
                metadata = read_json(output / "preparation.json")
                self.assertEqual(expected, [preparation.warp(source, pacing) for source in (0, 7, 9, 10)])
                self.assertEqual(list(zip(expected, expected[1:])),
                                 [(section["startBeat"], section["endBeat"]) for section in hybrid["sections"]])
                self.assertEqual(expected[1:3], metadata["chordCycle"]["arrangementSeconds"])
                self.assertEqual(expected[-1], score["totalBeats"])
                restrained = read_json(output / "restrained.json")["sections"]
                self.assertEqual([(0, expected[-1])], [(section["startBeat"], section["endBeat"]) for section in restrained])

    def test_shared_source_is_hash_verified_and_referenced_without_copying(self):
        output = self.prepare("shared", "driven", BASELINE)
        self.assertEqual({"score.json", "preparation.json", "restrained.json", "hybrid.json"},
                         {path.name for path in output.iterdir()})
        score = read_json(output / "score.json")
        self.assertEqual(BASELINE / "source-notes.json", (output / score["provenance"]["completeSource"]).resolve())
        for name, source in read_json(output / "preparation.json")["sources"].items():
            self.assertEqual(BASELINE / "source" / name, (output / source["path"]).resolve())
        modified = self.output_root / "modified-source"
        shutil.copytree(BASELINE, modified)
        (modified / "source-notes.json").write_text("{}\n")
        with self.assertRaisesRegex(ValueError, "Shared complete source notes differ"):
            self.prepare("rejected", "driven", modified)
        self.assertFalse((self.output_root / "rejected").exists())

    def test_each_profile_is_deterministic(self):
        for pacing in ("original", "driven"):
            with self.subTest(pacing=pacing):
                first = self.prepare(pacing + "-first", pacing)
                second = self.prepare(pacing + "-second", pacing)
                first_files = {path.relative_to(first): path.read_bytes() for path in first.rglob("*") if path.is_file()}
                second_files = {path.relative_to(second): path.read_bytes() for path in second.rglob("*") if path.is_file()}
                self.assertEqual(first_files, second_files)


if __name__ == "__main__":
    unittest.main()
