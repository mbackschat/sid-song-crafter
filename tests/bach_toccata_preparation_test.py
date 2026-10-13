import contextlib
from fractions import Fraction
import importlib.util
import io
import json
import math
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "songs/studies/bach-toccata-full"
SOURCE = ROOT / "songs/studies/bach-toccata-opening"
OPENING = ROOT / "songs/studies/bach-toccata-opening-driven"
spec = importlib.util.spec_from_file_location("bach_toccata", ROOT / "scripts/studies/bach/prepare-toccata.py")
preparation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preparation)


def read_json(path):
    return json.loads(path.read_text())


def source_notes():
    return {note["sourceId"]: dict(note, part=part["id"])
            for part in read_json(SOURCE / "source-notes.json")["parts"] for note in part["events"]}


class BachToccataPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output_root = Path(self.temporary.name)
        self.output = self.output_root / "first"
        with contextlib.redirect_stdout(io.StringIO()):
            preparation.prepare(STUDY / "arrangement.json", self.output)
        self.score = read_json(self.output / "score.json")
        self.metadata = read_json(self.output / "preparation.json")

    def test_preserves_accepted_opening_notes_sections_and_first_four_patches(self):
        opening = read_json(OPENING / "score.json")
        for old, new in zip(opening["voices"], self.score["voices"]):
            self.assertEqual(old["events"], [event for event in new["events"] if event["startBeat"] < 12])
        recipe = read_json(self.output / "hybrid.json")
        accepted = read_json(OPENING / "hybrid.json")
        self.assertEqual(accepted["sections"], recipe["sections"][:3])
        self.assertEqual(list(accepted["instruments"]), list(recipe["instruments"])[:4])
        for identity, patch in accepted["instruments"].items():
            self.assertEqual(patch, recipe["instruments"][identity])

    def test_accounts_for_every_source_note_and_excludes_fugue(self):
        source = source_notes()
        expected = {identity for identity, note in source.items() if Fraction(*note["startBeat"]) < 118}
        dispositions = self.metadata["sourceDisposition"]
        self.assertEqual(expected, {entry["sourceId"] for entry in dispositions})
        self.assertTrue(all(entry["status"] in ("retained", "partial", "cycled", "omitted") for entry in dispositions))
        self.assertTrue(all(entry["reason"] for entry in dispositions if entry["status"] != "retained"))
        self.assertEqual([0, 118], self.score["provenance"]["sourceBeatRange"])
        seen = set()
        for entry in self.metadata["mapping"]:
            self.assertLess(entry["sourceStartBeat"], entry["sourceEndBeat"])
            self.assertLessEqual(entry["sourceEndBeat"], 118)
            note = source[entry["sourceId"]]
            self.assertLess(Fraction(*note["startBeat"]), 118)
            self.assertEqual(note["midi"] + entry["transposeSemitones"], entry["midi"])
            self.assertGreaterEqual(entry["sourceStartBeat"] + 1e-8, float(Fraction(*note["startBeat"])))
            self.assertLessEqual(entry["sourceEndBeat"], float(Fraction(*note["startBeat"]) + Fraction(*note["durationBeats"])) + 1e-8)
            event = self.score["voices"][[voice["name"] for voice in self.score["voices"]].index(entry["voice"])]["events"][entry["eventIndex"]]
            self.assertEqual({key: entry[key] for key in ("startBeat", "durationBeats", "midi")}, event)
            seen.add((entry["voice"], entry["eventIndex"]))
        self.assertEqual(sum(len(voice["events"]) for voice in self.score["voices"]), len(seen))

    def test_preserves_right_hand_foreground_against_higher_offbeat_accompaniment(self):
        source = source_notes()
        expected = {identity for identity, note in source.items()
                    if note["part"] == "right-manual" and Fraction(183, 4) <= Fraction(*note["startBeat"]) < Fraction(121, 2)}
        actual = {entry["sourceId"] for entry in self.metadata["mapping"] if entry["voice"] == "melody"}
        self.assertTrue(expected <= actual, expected - actual)
        self.assertFalse(any(entry["voice"] == "melody" and entry["sourceId"].startswith("left-manual")
                             and 45.75 <= entry["sourceStartBeat"] < 60.5 for entry in self.metadata["mapping"]))

    def test_fractional_triplets_do_not_acquire_fictitious_omitted_tails(self):
        triplet = next(entry for entry in self.metadata["sourceDisposition"] if entry["sourceId"] == "right-manual-0026")
        self.assertEqual("retained", triplet["status"])
        self.assertEqual([], triplet["omittedIntervals"])
        self.assertTrue(all(end - start > 1e-7 for entry in self.metadata["sourceDisposition"]
                            for start, end in entry["omittedIntervals"]))

    def test_preserves_interleaved_moving_line_and_tied_triplet_entry(self):
        source = source_notes()
        required = {identity for identity, note in source.items()
                    if note["part"] != "pedal" and (Fraction(121, 2) <= Fraction(*note["startBeat"]) < 64
                                                    or Fraction(129, 2) <= Fraction(*note["startBeat"]) < 68)}
        retained = {entry["sourceId"] for entry in self.metadata["mapping"]}
        self.assertTrue(required <= retained, required - retained)
        for identity, voice in (("right-manual-0379", "melody"), ("left-manual-0228", "bass")):
            self.assertTrue(any(entry["sourceId"] == identity and entry["voice"] == voice
                                and entry["sourceStartBeat"] == 86 for entry in self.metadata["mapping"]))

    def test_exposes_final_minor_cadence_and_written_inner_resolution(self):
        final = [entry for entry in self.metadata["mapping"] if entry["sourceEndBeat"] > 116]
        self.assertEqual([62], [entry["midi"] for entry in final if entry["voice"] == "melody"])
        self.assertEqual([38], [entry["midi"] for entry in final if entry["voice"] == "bass"])
        self.assertEqual([55, 53, 52, 53], [entry["midi"] for entry in final if entry["voice"] == "harmony"])
        self.assertEqual([115.75, 116.5, 116.75, 117], [entry["sourceStartBeat"] for entry in final if entry["voice"] == "harmony"])
        lead = [entry for entry in self.metadata["mapping"] if entry["voice"] == "melody" and 114.5 <= entry["sourceStartBeat"] < 116]
        self.assertEqual([65, 64], [entry["midi"] for entry in lead])

    def test_printed_trill_has_explicit_derived_upper_neighbour_and_finite_pitch_frames(self):
        trill = [entry for entry in self.metadata["mapping"] if entry["sourceId"] == "right-manual-0167"]
        self.assertEqual([65, 67, 65, 67, 65, 67, 65], [entry["midi"] for entry in trill])
        self.assertTrue(all(entry["derivation"]["kind"] == "printed-trill" for entry in trill))
        rate = (17734475 / 18) / (312 * 63)
        for voice in self.score["voices"]:
            previous_end = 0
            for event in voice["events"]:
                start, end = event["startBeat"], event["startBeat"] + event["durationBeats"]
                self.assertGreaterEqual(start + 1e-8, previous_end)
                self.assertLessEqual(end, self.score["totalBeats"] + 1e-8)
                self.assertGreaterEqual(math.floor(end * rate + .5) - math.floor(start * rate + .5), 2)
                previous_end = end
        self.assertGreaterEqual(self.score["totalBeats"], 75)
        self.assertLessEqual(self.score["totalBeats"], 100)

    def test_native_recipe_covers_score_and_fits_capacity_without_timing_borrow(self):
        native_spec = importlib.util.spec_from_file_location("toccata_native", ROOT / "scripts/arrange-sidwizard.py")
        native = importlib.util.module_from_spec(native_spec)
        native_spec.loader.exec_module(native)
        for palette in ("hybrid", "restrained"):
            manifest = native.arrange(self.output / (palette + ".json"), self.output_root / palette)
            self.assertLessEqual(len(manifest["patterns"]), 100)
            self.assertLessEqual(len(manifest["instruments"]), 36)
            self.assertEqual([], manifest["timingChanges"])
            self.assertEqual(1, manifest["sidCount"])
            self.assertEqual("MOS8580", manifest["sidModel"])
            self.assertTrue(all(note["durationTicks"] >= 2 for voice in manifest["voices"] for note in voice["notes"]))

    def test_outputs_are_deterministic_and_existing_workfiles_are_preserved(self):
        second = self.output_root / "second"
        with contextlib.redirect_stdout(io.StringIO()):
            preparation.prepare(STUDY / "arrangement.json", second)
        for name in ("score.json", "hybrid.json", "restrained.json", "preparation.json"):
            self.assertEqual((self.output / name).read_bytes(), (second / name).read_bytes())
        with self.assertRaisesRegex(ValueError, "fresh output"):
            preparation.prepare(STUDY / "arrangement.json", self.output)


if __name__ == "__main__":
    unittest.main()
