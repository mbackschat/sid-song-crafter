import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("score_tools", ROOT / "scripts/score_tools.py")
TOOLS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOLS)


def midi_fixture():
    control = bytes.fromhex("00 ff 51 03 07 a1 20 00 ff 58 04 04 02 18 08 00 ff 2f 00")
    right = bytes.fromhex("00 ff 03 02 75 70 00 90 3c 40 00 90 40 5a 60 80 3c 00 00 80 40 00 00 90 43 46 30 80 43 00 30 ff 2f 00")
    left = bytes.fromhex("00 ff 03 04 64 6f 77 6e 00 91 24 37 00 91 30 3c 18 81 24 00 00 81 30 00 00 91 34 3e 18 81 34 00 00 91 37 40 18 81 37 00 48 91 43 40 30 81 43 00 00 ff 2f 00")
    return bytes.fromhex("4d546864 00000006 0001 0003 0060") + b"".join(b"MTrk" + len(track).to_bytes(4, "big") + track for track in (control, right, left))


def read_score(path):
    return json.loads((ROOT / path).read_text())


class MidiFixture(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "fixture.mid"
        self.path.write_bytes(midi_fixture())
        self.recipe = {
            "title": "Fixture",
            "composer": "Test",
            "parts": [{"track": 1, "id": "right"}, {"track": 2, "id": "left"}],
        }

    def tearDown(self):
        self.directory.cleanup()


class MidiImportTest(MidiFixture):
    def test_preserve_polyphony_velocity_and_written_rest(self):
        score = TOOLS.import_midi(self.path, self.recipe)
        self.assertEqual(score["schemaVersion"], 1)
        self.assertEqual(score["quarterBpm"], 120)
        self.assertEqual(score["timeSignature"], [4, 4])
        self.assertEqual(score["totalBeats"], [2, 1])
        self.assertEqual([event["midi"] for event in score["parts"][0]["events"]], [60, 64, 67])
        self.assertEqual(score["parts"][0]["events"][1]["velocity"], 90)
        self.assertEqual(score["parts"][0]["events"][2]["startBeat"], [1, 1])
        self.assertEqual(score["parts"][0]["events"][2]["durationBeats"], [1, 2])
        self.assertEqual(sum(len(part["events"]) for part in score["parts"]), 8)

    def test_unfold_explicit_performance_spans_without_losing_notes(self):
        self.recipe["performance"] = {"sourceTotalBeats": [5, 2], "spans": [{"startBeat": 0, "endBeat": 1}, {"startBeat": 0, "endBeat": [5, 2]}]}
        score = TOOLS.import_midi(self.path, self.recipe)
        self.assertEqual(score["totalBeats"], [7, 2])
        self.assertEqual(sum(len(part["events"]) for part in score["parts"]), 14)
        self.assertEqual([event["startBeat"] for event in score["parts"][0]["events"]], [[0, 1], [0, 1], [1, 1], [1, 1], [2, 1]])

    def test_reject_checksum_mismatch_and_mid_note_repeat_boundaries(self):
        self.recipe["sourceSha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            TOOLS.import_midi(self.path, self.recipe)
        del self.recipe["sourceSha256"]
        self.recipe["performance"] = {"spans": [{"startBeat": 0, "endBeat": [1, 2]}]}
        with self.assertRaisesRegex(ValueError, "crosses.*boundary"):
            TOOLS.import_midi(self.path, self.recipe)

    def test_reject_tempo_or_meter_changes(self):
        import mido
        for message in (mido.MetaMessage("set_tempo", tempo=600000, time=48), mido.MetaMessage("time_signature", numerator=3, denominator=4, time=48)):
            with self.subTest(message=message.type):
                midi = mido.MidiFile(self.path)
                midi.tracks[0].insert(-1, message)
                midi.save(self.path)
                with self.assertRaisesRegex(ValueError, "constant"):
                    TOOLS.import_midi(self.path, self.recipe)
                self.path.write_bytes(midi_fixture())

    def test_reject_single_late_tempo_or_meter_change_from_midi_defaults(self):
        import mido
        for kind, message in (("set_tempo", mido.MetaMessage("set_tempo", tempo=600000, time=48)), ("time_signature", mido.MetaMessage("time_signature", numerator=3, denominator=4, time=48))):
            with self.subTest(message=kind):
                midi = mido.MidiFile(self.path)
                midi.tracks[0] = mido.MidiTrack(item for item in midi.tracks[0] if item.type != kind)
                midi.tracks[0].insert(-1, message)
                midi.save(self.path)
                with self.assertRaisesRegex(ValueError, "constant"):
                    TOOLS.import_midi(self.path, self.recipe)
                self.path.write_bytes(midi_fixture())

    def test_report_fields_omitted_from_normalized_notes_and_meter(self):
        score = TOOLS.import_midi(self.path, self.recipe)
        report = score["provenance"]["importReport"]
        self.assertIn("channel", report["unmappedFields"]["note_on"])
        self.assertIn("velocity", report["unmappedFields"]["note_off"])
        self.assertIn("clocks_per_click", report["unmappedFields"]["time_signature"])


class VoiceArrangementTest(MidiFixture):
    def arrangement_recipe(self):
        return {
            "melodyPart": "right",
            "accompanimentPart": "left",
            "bass": {"belowMidi": 48, "onMeasureStart": True, "measureBeats": 4, "firstMeasureBeat": 0},
            "harmonyPriority": ["accompaniment", "melody"],
            "instruments": [{"waveform": 16, "attackDecay": 2, "sustainRelease": 146}, {"waveform": 16, "attackDecay": 3, "sustainRelease": 98}, {"waveform": 16, "attackDecay": 3, "sustainRelease": 98}],
        }

    def test_allocate_real_notes_and_preserve_cross_hand_treble(self):
        score = TOOLS.import_midi(self.path, self.recipe)
        arranged = TOOLS.arrange_score(score, self.arrangement_recipe())
        self.assertEqual([[event["midi"] for event in voice["events"]] for voice in arranged["voices"]], [[64, 67], [36], [48, 52, 55, 60, 67]])
        self.assertEqual(arranged["voices"][2]["events"][-1], {"startBeat": 1.5, "durationBeats": 0.5, "midi": 67})
        self.assertEqual(arranged["provenance"]["reduction"]["omittedNotes"], 0)
        self.assertEqual(arranged["provenance"]["reduction"]["shortenedNotes"], 1)
        self.assertEqual(arranged["provenance"]["reduction"]["sourceNotes"], 8)

    def test_shorter_higher_note_reveals_sustained_lower_melody(self):
        score = TOOLS.import_midi(self.path, self.recipe)
        score["parts"][0]["events"] = [{"startBeat": [0, 1], "durationBeats": [1, 1], "midi": 60}, {"startBeat": [1, 4], "durationBeats": [1, 4], "midi": 72}]
        arranged = TOOLS.arrange_score(score, self.arrangement_recipe())
        self.assertEqual(arranged["voices"][0]["events"], [{"startBeat": 0.0, "durationBeats": 0.25, "midi": 60}, {"startBeat": 0.25, "durationBeats": 0.25, "midi": 72}, {"startBeat": 0.5, "durationBeats": 0.5, "midi": 60}])

    def test_reject_duplicate_parts_invalid_roles_or_nonpositive_notes(self):
        score = TOOLS.import_midi(self.path, self.recipe)
        bad = copy.deepcopy(score)
        bad["parts"][1]["id"] = "right"
        with self.assertRaisesRegex(ValueError, "unique"):
            TOOLS.arrange_score(bad, self.arrangement_recipe())
        bad = copy.deepcopy(score)
        bad["parts"][0]["events"][0]["durationBeats"] = [0, 1]
        with self.assertRaisesRegex(ValueError, "duration"):
            TOOLS.arrange_score(bad, self.arrangement_recipe())
        recipe = self.arrangement_recipe()
        recipe["melodyPart"] = "missing"
        with self.assertRaisesRegex(ValueError, "part"):
            TOOLS.arrange_score(score, recipe)


class FullEliseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.score = read_score("songs/fuer-elise.json")
        cls.common = read_score("songs/sources/fuer-elise.score.json")

    def note_at(self, voice, beat):
        return next(event for event in self.score["voices"][voice]["events"] if abs(event["startBeat"] - beat) < 1e-9)

    def test_full_form_repeats_and_source_counts(self):
        self.assertEqual(self.score["quarterBpm"], 72)
        self.assertEqual(self.score["totalBeats"], 187.5)
        self.assertEqual(self.common["totalBeats"], [375, 2])
        self.assertEqual([len(part["events"]) for part in self.common["parts"]], [605, 436])
        for beat, pitch in ((0, 76), (12, 76), (24.5, 76), (45.5, 76), (66.5, 72), (122, 73), (147.5, 57), (155, 76), (186.5, 69)):
            with self.subTest(beat=beat):
                self.assertEqual(self.note_at(0, beat)["midi"], pitch)

    def test_independent_musical_landmarks_and_short_notes(self):
        self.assertEqual([event["midi"] for event in self.score["voices"][0]["events"][:9]], [76, 75, 76, 75, 76, 71, 74, 72, 69])
        self.assertEqual(self.note_at(0, 67.5), {"startBeat": 67.5, "durationBeats": 0.375, "midi": 77})
        self.assertEqual(self.note_at(0, 148), {"startBeat": 148.0, "durationBeats": 1 / 6, "midi": 69})
        self.assertEqual(max(event["midi"] for event in self.score["voices"][0]["events"]), 100)
        self.assertAlmostEqual(min(event["durationBeats"] for event in self.score["voices"][0]["events"]), 10 / 384)
        self.assertEqual(self.note_at(1, 120.5)["midi"], 45)
        self.assertEqual(self.note_at(1, 186.5)["midi"], 33)

    def test_three_monophonic_voices_real_pitches_and_final_rest(self):
        self.assertEqual(len(self.score["voices"]), 3)
        self.assertNotIn("instrument", self.common)
        for part in self.common["parts"]:
            self.assertNotIn("instrument", part)
        for voice in self.score["voices"]:
            self.assertGreater(len(voice["events"]), 10)
            previous_end = 0
            for event in voice["events"]:
                self.assertGreaterEqual(event["startBeat"] + 1e-9, previous_end)
                self.assertGreater(event["durationBeats"], 0)
                self.assertIn(event["midi"], range(128))
                previous_end = event["startBeat"] + event["durationBeats"]
            self.assertLessEqual(previous_end, 187)
        self.assertEqual(self.note_at(0, 186.5)["durationBeats"], 0.5)

    def test_common_score_rearranges_deterministically(self):
        recipe = read_score("songs/fuer-elise-arrangement.json")
        self.assertEqual(TOOLS.arrange_score(self.common, recipe), self.score)
        self.assertEqual(TOOLS.arrange_score(self.common, recipe), TOOLS.arrange_score(self.common, recipe))
        self.assertEqual(self.common["provenance"]["sourceSha256"], "1c12c21c7bbf4cf163896732672648a69d497636059837abd153c71abe50215a")

    def test_original_sources_reimport_with_identical_common_score(self):
        original = ROOT / "songs/sources/fuer-elise.mid"
        recipe = read_score("songs/fuer-elise-import.json")
        self.assertEqual(TOOLS.import_midi(original, recipe), self.common)
        notation = (ROOT / "songs/sources/fuer-elise.ly").read_bytes()
        self.assertEqual(hashlib.sha256(notation).hexdigest(), "828a7bd1b42e441fe1b0eb0389ba46f1502dab28bbe488389e635fb446ba7a67")

    def test_source_directory_anchors_both_output_layers_to_originals(self):
        for score in (self.common, self.score):
            provenance = score["provenance"]
            self.assertEqual(provenance["sourceDirectory"], "songs/sources")
            directory = ROOT / provenance["sourceDirectory"]
            for filename, digest in (("sourceFile", "sourceSha256"), ("notationFile", "notationSha256")):
                source = directory / provenance[filename]
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), provenance[digest])


if __name__ == "__main__":
    unittest.main()
