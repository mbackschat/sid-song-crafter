import hashlib
import importlib.util
import json
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


if __name__ == "__main__":
    unittest.main()
