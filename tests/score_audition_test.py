import hashlib
import importlib.util
import json
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

import mido


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("score_audition", ROOT / "scripts/prepare-score-audition.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ScoreAuditionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.mid"
        midi = mido.MidiFile(ticks_per_beat=96)
        self.notes = {
            "lead": [(0, 96, 60), (384, 32, 63), (448, 32, 64), (1152, 96, 67)],
            "bass": [(384, 31, 36), (1152, 95, 38)],
            "chords": [(384, 64, 48), (384, 64, 55), (1152, 96, 48), (1152, 96, 52), (1152, 96, 55)],
            "sax": [(384, 96, 64)],
            "baritone": [(384, 31, 36)],
            "drums": [(384, 31, 42)],
        }
        for part, notes in self.notes.items():
            track = mido.MidiTrack([mido.MetaMessage("track_name", name=part)])
            if part == "lead":
                track.extend([mido.MetaMessage("set_tempo", tempo=540540), mido.MetaMessage("time_signature", numerator=4, denominator=4)])
            messages = []
            for start, duration, pitch in notes:
                messages.extend([(start, mido.Message("note_on", note=pitch, velocity=90)), (start + duration, mido.Message("note_off", note=pitch))])
            tick = 0
            for start, message in sorted(messages, key=lambda item: (item[0], item[1].type == "note_on")):
                track.append(message.copy(time=start - tick))
                tick = start
            track.append(mido.MetaMessage("end_of_track", time=1536 - tick))
            midi.tracks.append(track)
        midi.save(self.source)
        self.recipe = self.root / "import.json"
        self.recipe.write_text(json.dumps({
            "title": "Source fixture", "composer": "Test fixture",
            "sourceSha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
            "parts": [{"track": index, "id": part} for index, part in enumerate(self.notes)],
        }))
        self.projection = {
            "spans": [{"startBeat": 4, "endBeat": 8}, {"startBeat": 12, "endBeat": 16}],
            "voices": [{"name": name, "sourcePart": part, "monophonicPolicy": policy, "instrument": {"waveform": 16, "attackDecay": 2, "sustainRelease": 128}} for name, part, policy in (
                ("melody", "lead", "reject-overlap"), ("bass", "bass", "reject-overlap"), ("harmony", "chords", "highest-at-onset"),
            )],
            "omittedParts": {part: "Fixture voice-budget omission" for part in ("sax", "baritone", "drums")},
        }
        self.arrangement = self.root / "projection.json"
        self.output = self.root / "prepared"

    def prepare(self, **kwargs):
        self.arrangement.write_text(json.dumps(self.projection))
        return MODULE.prepare_source(self.source, self.recipe, self.output, self.arrangement, **kwargs)

    def test_preserves_full_source_and_accounts_for_every_selected_note_without_retiming(self):
        report = self.prepare()
        full = json.loads((self.output / "full-common-score.json").read_text())
        selected = json.loads((self.output / "common-score.json").read_text())
        score = json.loads((self.output / "score.json").read_text())
        self.assertEqual(self.source.read_bytes(), (self.output / "source.mid").read_bytes())
        self.assertEqual(14, sum(len(part["events"]) for part in full["parts"]))
        self.assertEqual([16, 1], full["totalBeats"])
        self.assertEqual([8, 1], selected["totalBeats"])
        self.assertEqual(13, report["selectedNotes"])
        self.assertEqual(7, report["reduction"]["retainedNotes"])
        self.assertEqual(6, report["reduction"]["omittedNotes"])
        lead = selected["parts"][0]["events"]
        self.assertEqual([[0, 1], [2, 3], [4, 1]], [event["startBeat"] for event in lead])
        self.assertEqual([55, 55], [event["midi"] for event in score["voices"][2]["events"]])
        all_notes = report["reduction"]["retainedEvents"] + report["reduction"]["omittedEvents"]
        self.assertEqual(13, len({(note["spanIndex"], note["source"]["part"], note["source"]["eventIndex"]) for note in all_notes}))
        for note in report["reduction"]["retainedEvents"]:
            origin = note["source"]
            full_part = next(part for part in full["parts"] if part["id"] == origin["part"])
            self.assertEqual(full_part["events"][origin["eventIndex"]], {key: value for key, value in origin.items() if key not in ("part", "eventIndex")})
            event = score["voices"][note["voiceIndex"]]["events"][note["outputEventIndex"]]
            self.assertEqual(float(MODULE.beat(origin["durationBeats"])), event["durationBeats"])
            self.assertEqual(origin["midi"], event["midi"])
        self.assertEqual(540540, report["importReport"]["microsecondsPerQuarter"])

    def test_rejects_undeclared_source_part_omission_before_creating_output(self):
        del self.projection["omittedParts"]["drums"]
        with self.assertRaisesRegex(ValueError, "Every source part"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_rejects_polyphony_in_a_preserved_melody(self):
        self.projection["voices"][2]["monophonicPolicy"] = "reject-overlap"
        with self.assertRaisesRegex(ValueError, "overlap"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_explicit_omission_uses_complete_source_index_before_chord_reduction(self):
        reason = "Preserve the lower chord tone for this arrangement"
        self.projection["voices"][2]["omittedEvents"] = [{"sourceEventIndex": 1, "reason": reason}]
        report = self.prepare()
        score = json.loads((self.output / "score.json").read_text())
        self.assertEqual([48, 55], [event["midi"] for event in score["voices"][2]["events"]])
        losses = [event for event in report["reduction"]["omittedEvents"] if event["reason"] == reason]
        self.assertEqual(1, len(losses))
        self.assertEqual({"spanIndex": 0, "selectedStartBeat": [0, 1], "source": {
            "part": "chords", "eventIndex": 1, "startBeat": [4, 1],
            "durationBeats": [2, 3], "midi": 55, "velocity": 90,
        }, "reason": reason}, losses[0])
        self.assertEqual(13, report["reduction"]["retainedNotes"] + report["reduction"]["omittedNotes"])

    def test_explicit_omission_accounts_for_each_repeated_source_occurrence(self):
        self.projection["spans"] = [self.projection["spans"][0]] * 2
        reason = "Deliberately omit this source note in both repetitions"
        self.projection["voices"][0]["omittedEvents"] = [{"sourceEventIndex": 1, "reason": reason}]
        report = self.prepare()
        score = json.loads((self.output / "score.json").read_text())
        self.assertEqual([64, 64], [event["midi"] for event in score["voices"][0]["events"]])
        losses = [event for event in report["reduction"]["omittedEvents"] if event["reason"] == reason]
        self.assertEqual([0, 1], [event["spanIndex"] for event in losses])
        self.assertEqual([[0, 1], [4, 1]], [event["selectedStartBeat"] for event in losses])
        self.assertEqual([1, 1], [event["source"]["eventIndex"] for event in losses])
        self.assertEqual(16, report["reduction"]["sourceNotes"])
        self.assertEqual(16, report["reduction"]["retainedNotes"] + report["reduction"]["omittedNotes"])

    def test_omitting_later_overlapping_note_preserves_original_durations(self):
        full = {"title": "Overlap fixture", "composer": "Test fixture", "quarterBpm": 120,
                "timeSignature": [4, 4], "totalBeats": [8, 1], "provenance": {},
                "parts": [{"id": part, "events": []} for part in ("lead", "bass", "chords")]}
        upper = {"startBeat": [0, 1], "durationBeats": [5, 1], "midi": 59, "velocity": 90}
        lower = {"startBeat": [4, 1], "durationBeats": [2, 1], "midi": 52, "velocity": 80}
        full["parts"][2]["events"] = [upper, lower]
        projection = {**self.projection, "spans": [{"startBeat": 0, "endBeat": 8}], "omittedParts": {}}
        with self.assertRaisesRegex(ValueError, "overlap"):
            MODULE.project_score(full, full, projection)
        projection["voices"][2]["omittedEvents"] = [{"sourceEventIndex": 1, "reason": "Preserve the upper held note"}]
        score = MODULE.project_score(full, full, projection)
        self.assertEqual([{"startBeat": 0.0, "durationBeats": 5.0, "midi": 59}], score["voices"][2]["events"])
        self.assertEqual([upper, lower], full["parts"][2]["events"])
        reduction = score["provenance"]["reduction"]
        self.assertEqual(0, reduction["shortenedNotes"])
        self.assertEqual(lower, {key: value for key, value in reduction["omittedEvents"][0]["source"].items() if key not in ("part", "eventIndex")})

    def test_rejects_invalid_explicit_omissions_before_creating_output(self):
        invalid = [
            ([{"sourceEventIndex": value, "reason": "Deliberate omission"}], "nonnegative integer")
            for value in (-1, True, 1.0, "1", None)
        ] + [
            ([{"reason": "Missing source index"}], "nonnegative integer"),
        ]
        invalid.extend(([{"sourceEventIndex": 1, "reason": reason}], "nonblank reason") for reason in ("", "  ", None, 42))
        invalid.extend([
            ([{"sourceEventIndex": 1}], "nonblank reason"),
            ([{"sourceEventIndex": 1, "reason": "One"}, {"sourceEventIndex": 1, "reason": "Two"}], "Duplicate"),
            ([{"sourceEventIndex": 99, "reason": "Unknown note"}], "does not exist"),
            ([{"sourceEventIndex": 0, "reason": "Outside selected passage"}], "not selected"),
            ({"sourceEventIndex": 1, "reason": "Wrong container"}, "list"),
            ([1], "object"),
        ])
        for index, (omissions, message) in enumerate(invalid):
            with self.subTest(omissions=omissions):
                self.output = self.root / ("invalid-" + str(index))
                self.projection["voices"][0]["omittedEvents"] = omissions
                with self.assertRaisesRegex(ValueError, message):
                    self.prepare()
                self.assertFalse(self.output.exists())

    def test_rejects_tied_highest_pitches_with_different_source_durations(self):
        midi = mido.MidiFile(self.source)
        midi.tracks[2] = mido.MidiTrack([
            mido.Message("note_on", note=67, velocity=90, time=384),
            mido.Message("note_on", note=67, velocity=90),
            mido.Message("note_off", note=67, time=48),
            mido.Message("note_off", note=67, time=144),
            mido.MetaMessage("end_of_track", time=960),
        ])
        midi.save(self.source)
        recipe = json.loads(self.recipe.read_text())
        recipe["sourceSha256"] = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.recipe.write_text(json.dumps(recipe))
        with self.assertRaisesRegex(ValueError, "tied highest"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_rejects_source_note_crossing_a_passage_boundary(self):
        self.projection["spans"][0]["endBeat"] = [25, 6]
        with self.assertRaisesRegex(ValueError, "crosses"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_rejects_source_hash_mismatch_before_creating_output(self):
        recipe = json.loads(self.recipe.read_text())
        recipe["sourceSha256"] = "0" * 64
        self.recipe.write_text(json.dumps(recipe))
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_materializes_candidate_and_reference_templates_against_the_same_score(self):
        candidate, reference = self.root / "candidate.json", self.root / "reference.json"
        candidate.write_text(json.dumps({"title": "Candidate", "score": "other.json"}))
        reference.write_text(json.dumps({"title": "Reference"}))
        self.prepare(candidate=candidate, reference=reference)
        self.assertEqual({"title": "Candidate", "score": "score.json"}, json.loads((self.output / "candidate.json").read_text()))
        self.assertEqual({"title": "Reference", "score": "score.json"}, json.loads((self.output / "reference.json").read_text()))

    def test_rejects_unpaired_comparison_template(self):
        with self.assertRaisesRegex(ValueError, "candidate and reference"):
            self.prepare(candidate=self.recipe)
        self.assertFalse(self.output.exists())

    def test_rejects_unknown_policy_and_duplicate_part_mapping(self):
        self.projection["voices"][0]["monophonicPolicy"] = "flatten"
        with self.assertRaisesRegex(ValueError, "monophonic policy"):
            self.prepare()
        self.projection["voices"][0]["monophonicPolicy"] = "reject-overlap"
        self.projection["voices"][1]["sourcePart"] = "lead"
        with self.assertRaisesRegex(ValueError, "distinct"):
            self.prepare()
        self.assertFalse(self.output.exists())


class MultiPartProjectionTest(unittest.TestCase):
    def setUp(self):
        self.full = {
            "title": "Sequential parts fixture", "composer": "Test fixture", "quarterBpm": 120,
            "timeSignature": [4, 4], "totalBeats": [8, 1], "provenance": {},
            "parts": [
                {"id": "intro", "events": [{"startBeat": [0, 1], "durationBeats": [1, 1], "midi": 60, "velocity": 80}]},
                {"id": "lead", "events": [{"startBeat": [2, 1], "durationBeats": [3, 2], "midi": 64, "velocity": 90}]},
                {"id": "bass", "events": []},
                {"id": "chords", "events": []},
            ],
        }
        self.projection = {
            "spans": [{"startBeat": 0, "endBeat": 8}],
            "voices": [
                {"name": "melody", "sourceParts": ["lead", "intro"], "monophonicPolicy": "reject-overlap", "instrument": {}},
                {"name": "bass", "sourcePart": "bass", "monophonicPolicy": "reject-overlap", "instrument": {}},
                {"name": "harmony", "sourcePart": "chords", "monophonicPolicy": "highest-at-onset", "instrument": {}},
            ],
        }

    def project(self):
        return MODULE.project_score(self.full, self.full, self.projection)

    def test_merges_sequential_parts_by_onset_with_unchanged_source_identity(self):
        original = deepcopy(self.full)
        score = self.project()
        self.assertEqual([
            {"startBeat": 0.0, "durationBeats": 1.0, "midi": 60},
            {"startBeat": 2.0, "durationBeats": 1.5, "midi": 64},
        ], score["voices"][0]["events"])
        reduction = score["provenance"]["reduction"]
        self.assertEqual(2, reduction["sourceNotes"])
        self.assertEqual(2, reduction["retainedNotes"])
        self.assertEqual(0, reduction["omittedNotes"])
        self.assertEqual(0, reduction["shortenedNotes"])
        self.assertEqual(self.projection["voices"][0]["sourceParts"], reduction["voices"][0]["sourceParts"])
        self.assertNotIn("sourcePart", reduction["voices"][0])
        self.assertEqual("bass", reduction["voices"][1]["sourcePart"])
        for output_index, origin in enumerate(reduction["retainedEvents"]):
            part = self.full["parts"][output_index]
            self.assertEqual({"part": part["id"], "eventIndex": 0, **part["events"][0]}, origin["source"])
            self.assertEqual(output_index, origin["outputEventIndex"])
        self.assertEqual(original, self.full)

    def test_rejects_cross_part_overlap_without_shortening_either_note(self):
        self.full["parts"][0]["events"][0]["durationBeats"] = [3, 1]
        original = deepcopy(self.full)
        for policy in ("reject-overlap", "highest-at-onset"):
            with self.subTest(policy=policy):
                self.projection["voices"][0]["monophonicPolicy"] = policy
                with self.assertRaisesRegex(ValueError, "overlap"):
                    self.project()
                self.assertEqual(original, self.full)

    def test_explicit_overlap_shortening_preserves_all_onsets_and_original_durations(self):
        self.full["parts"][0]["events"][0]["durationBeats"] = [5, 2]
        self.full["parts"][1]["events"][0]["startBeat"] = [7, 3]
        original = deepcopy(self.full)
        for policy in ("reject-overlap", "highest-at-onset"):
            with self.subTest(policy=policy):
                self.projection["voices"][0].update({"monophonicPolicy": policy, "overlapPolicy": "shorten-to-next-onset"})
                score = self.project()
                self.assertEqual([
                    {"startBeat": 0.0, "durationBeats": 7 / 3, "midi": 60},
                    {"startBeat": 7 / 3, "durationBeats": 1.5, "midi": 64},
                ], score["voices"][0]["events"])
                reduction = score["provenance"]["reduction"]
                self.assertEqual(2, reduction["retainedNotes"])
                self.assertEqual(0, reduction["omittedNotes"])
                self.assertEqual(1, reduction["shortenedNotes"])
                self.assertEqual([reduction["retainedEvents"][0]], reduction["shortenedEvents"])
                self.assertEqual([5, 2], reduction["shortenedEvents"][0]["source"]["durationBeats"])
                self.assertEqual([7, 3], reduction["shortenedEvents"][0]["outputDurationBeats"])
                self.assertNotIn("outputDurationBeats", reduction["retainedEvents"][1])
                self.assertEqual("shorten-to-next-onset", reduction["voices"][0]["overlapPolicy"])
                self.assertEqual(original, self.full)

    def test_explicit_shortening_keeps_nonoverlapping_and_final_notes_unchanged(self):
        self.projection["voices"][0]["overlapPolicy"] = "shorten-to-next-onset"
        reduction = self.project()["provenance"]["reduction"]
        self.assertEqual(0, reduction["shortenedNotes"])
        self.assertEqual([], reduction["shortenedEvents"])
        self.assertTrue(all("outputDurationBeats" not in origin for origin in reduction["retainedEvents"]))

    def test_explicit_shortening_rejects_simultaneous_notes_and_tied_highest_pitches(self):
        self.full["parts"][1]["events"][0]["startBeat"] = [0, 1]
        self.projection["voices"][0]["overlapPolicy"] = "shorten-to-next-onset"
        with self.assertRaisesRegex(ValueError, "simultaneous|overlap"):
            self.project()
        self.projection["voices"][0]["monophonicPolicy"] = "highest-at-onset"
        self.full["parts"][1]["events"][0]["midi"] = 60
        with self.assertRaisesRegex(ValueError, "tied highest"):
            self.project()

    def test_rejects_unknown_overlap_policy(self):
        self.projection["voices"][0]["overlapPolicy"] = "truncate-whatever"
        with self.assertRaisesRegex(ValueError, "overlap policy"):
            self.project()

    def test_highest_at_onset_reduces_across_parts_with_complete_loss_provenance(self):
        self.full["parts"][1]["events"][0]["startBeat"] = [0, 1]
        self.projection["voices"][0]["monophonicPolicy"] = "highest-at-onset"
        score = self.project()
        self.assertEqual([{"startBeat": 0.0, "durationBeats": 1.5, "midi": 64}], score["voices"][0]["events"])
        reduction = score["provenance"]["reduction"]
        self.assertEqual("lead", reduction["retainedEvents"][0]["source"]["part"])
        self.assertEqual({"part": "intro", "eventIndex": 0, **self.full["parts"][0]["events"][0]}, reduction["omittedEvents"][0]["source"])
        self.assertEqual("Lower chord note omitted by highest-at-onset", reduction["omittedEvents"][0]["reason"])

    def test_rejects_tied_highest_pitches_across_parts(self):
        self.full["parts"][1]["events"][0].update({"startBeat": [0, 1], "midi": 60})
        self.projection["voices"][0]["monophonicPolicy"] = "highest-at-onset"
        with self.assertRaisesRegex(ValueError, "tied highest"):
            self.project()

    def test_explicit_omissions_distinguish_same_event_index_in_each_source_part(self):
        self.projection["voices"][0]["omittedEvents"] = [{"sourcePart": "lead", "sourceEventIndex": 0, "reason": "Keep the introduction only"}]
        score = self.project()
        reduction = score["provenance"]["reduction"]
        self.assertEqual([60], [event["midi"] for event in score["voices"][0]["events"]])
        self.assertEqual("intro", reduction["retainedEvents"][0]["source"]["part"])
        self.assertEqual("lead", reduction["omittedEvents"][0]["source"]["part"])
        self.projection["voices"][0]["omittedEvents"].append({"sourcePart": "intro", "sourceEventIndex": 0, "reason": "Explicitly omit both independent notes"})
        reduction = self.project()["provenance"]["reduction"]
        self.assertEqual(0, reduction["retainedNotes"])
        self.assertEqual(2, reduction["omittedNotes"])

    def test_rejects_ambiguous_unowned_and_duplicate_multi_part_omissions(self):
        for omissions, message in (
            ([{"sourceEventIndex": 0, "reason": "Ambiguous source"}], "sourcePart"),
            ([{"sourcePart": "bass", "sourceEventIndex": 0, "reason": "Unowned source"}], "sourcePart"),
            ([{"sourcePart": ["lead"], "sourceEventIndex": 0, "reason": "Invalid source"}], "sourcePart"),
            ([{"sourcePart": "lead", "sourceEventIndex": 0, "reason": "One"}, {"sourcePart": "lead", "sourceEventIndex": 0, "reason": "Two"}], "Duplicate"),
        ):
            with self.subTest(omissions=omissions):
                self.projection["voices"][0]["omittedEvents"] = omissions
                with self.assertRaisesRegex(ValueError, message):
                    self.project()

    def test_single_part_list_keeps_legacy_omission_declarations(self):
        self.projection["voices"][0]["sourceParts"] = ["lead"]
        self.projection["omittedParts"] = {"intro": "Not needed in this fixture"}
        self.projection["voices"][0]["omittedEvents"] = [{"sourceEventIndex": 0, "reason": "Legacy single-part omission"}]
        reduction = self.project()["provenance"]["reduction"]
        self.assertEqual(0, reduction["retainedNotes"])
        self.assertEqual(2, reduction["omittedNotes"])

    def test_rejects_invalid_or_conflicting_source_part_declarations(self):
        invalid = [
            {"sourceParts": []}, {"sourceParts": "lead"}, {"sourceParts": ["lead", "lead"]},
            {"sourceParts": ["lead", None]}, {"sourceParts": ["lead", ""]},
            {"sourceParts": ["lead"], "sourcePart": "intro"}, {},
        ]
        for declaration in invalid:
            with self.subTest(declaration=declaration):
                voice = self.projection["voices"][0]
                voice.pop("sourceParts", None)
                voice.pop("sourcePart", None)
                voice.update(declaration)
                with self.assertRaisesRegex(ValueError, "sourcePart"):
                    self.project()

    def test_rejects_duplicate_ownership_and_mapped_omissions(self):
        self.projection["voices"][1]["sourcePart"] = "intro"
        with self.assertRaisesRegex(ValueError, "distinct|mapped once"):
            self.project()
        self.projection["voices"][1]["sourcePart"] = "bass"
        self.projection["omittedParts"] = {"intro": "Already mapped"}
        with self.assertRaisesRegex(ValueError, "Every source part"):
            self.project()
        del self.projection["omittedParts"]
        self.projection["voices"][0]["sourceParts"] = ["lead", "unknown"]
        with self.assertRaisesRegex(ValueError, "Every source part"):
            self.project()


if __name__ == "__main__":
    unittest.main()
