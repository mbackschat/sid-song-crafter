import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import mido


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "moon_river_source", ROOT / "scripts/studies/moon-river/prepare-source.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MoonRiverSourceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.mid"
        midi = mido.MidiFile(ticks_per_beat=480)
        midi.tracks.append(mido.MidiTrack([
            mido.MetaMessage("set_tempo", tempo=857142),
            mido.MetaMessage("time_signature", numerator=3, denominator=4),
            mido.Message("note_on", note=72, velocity=80),
            mido.Message("note_off", note=72, velocity=30, time=1440),
            mido.MetaMessage("set_tempo", tempo=1000000),
            mido.Message("note_on", note=74, velocity=70),
            mido.Message("note_off", note=74, time=480),
            mido.MetaMessage("end_of_track", time=960),
        ]))
        midi.tracks.append(mido.MidiTrack([
            mido.Message("program_change", channel=1, program=0),
            mido.Message("control_change", channel=1, control=64, value=127),
            mido.Message("note_on", channel=1, note=48, velocity=60),
            mido.Message("note_off", channel=1, note=48, time=1440),
            mido.MetaMessage("end_of_track", time=1440),
        ]))
        midi.save(self.source)
        self.recipe = self.root / "import.json"
        self.recipe.write_text(json.dumps({
            "title": "Source test",
            "composer": "Test fixture",
            "quarterBpm": 70,
            "sourceSha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
            "parts": [{"track": 0, "id": "right-hand"}, {"track": 1, "id": "left-hand"}],
        }))

    def test_preserves_note_timing_and_controllers_while_recording_tempo_adaptation(self):
        output = self.root / "prepared"
        MODULE.prepare_source(self.source, self.recipe, output)
        original = mido.MidiFile(self.source)
        derived = mido.MidiFile(output / "constant-tempo.mid")
        for source_track, derived_track in zip(original.tracks, derived.tracks):
            self.assertEqual(len(source_track), len(derived_track))
            for source_message, derived_message in zip(source_track, derived_track):
                expected = source_message.copy(tempo=857142) if source_message.type == "set_tempo" else source_message
                self.assertEqual(expected, derived_message)
        score = json.loads((output / "common-score.json").read_text())
        self.assertEqual([3, 1], score["parts"][0]["events"][1]["startBeat"])
        self.assertEqual([1, 1], score["parts"][0]["events"][1]["durationBeats"])
        self.assertEqual(3, score["provenance"]["importReport"]["sourceNotes"])
        self.assertEqual([6, 1], score["totalBeats"])
        report = json.loads((output / "adaptation.json").read_text())
        self.assertEqual([0, 1440], [event["tick"] for event in report["originalTempoMap"]])
        self.assertEqual([857142, 1000000], [event["microsecondsPerQuarter"] for event in report["originalTempoMap"]])
        self.assertTrue(report["eventTicksPreserved"])
        self.assertEqual(self.source.read_bytes(), (output / "source.mid").read_bytes())

    def test_retains_full_score_separately_from_selected_complete_section(self):
        recipe = json.loads(self.recipe.read_text())
        recipe["performance"] = {"sourceTotalBeats": 6, "spans": [{"startBeat": 0, "endBeat": 3}]}
        self.recipe.write_text(json.dumps(recipe))
        output = self.root / "prepared"
        MODULE.prepare_source(self.source, self.recipe, output)
        full = json.loads((output / "full-common-score.json").read_text())
        selected = json.loads((output / "common-score.json").read_text())
        self.assertEqual([6, 1], full["totalBeats"])
        self.assertEqual(3, sum(len(part["events"]) for part in full["parts"]))
        self.assertEqual([3, 1], selected["totalBeats"])
        self.assertEqual(2, sum(len(part["events"]) for part in selected["parts"]))
        report = json.loads((output / "adaptation.json").read_text())
        self.assertEqual(3, report["sourceNotes"])
        self.assertEqual(2, report["normalizedNotes"])
        self.assertEqual("full-common-score.json", report["fullCommonScore"])

    def test_rejects_source_hash_mismatch_before_creating_output(self):
        recipe = json.loads(self.recipe.read_text())
        recipe["sourceSha256"] = "0" * 64
        self.recipe.write_text(json.dumps(recipe))
        output = self.root / "prepared"
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            MODULE.prepare_source(self.source, self.recipe, output)
        self.assertFalse(output.exists())

    def test_rejects_existing_output(self):
        output = self.root / "prepared"
        output.mkdir()
        with self.assertRaisesRegex(ValueError, "fresh"):
            MODULE.prepare_source(self.source, self.recipe, output)


if __name__ == "__main__":
    unittest.main()
