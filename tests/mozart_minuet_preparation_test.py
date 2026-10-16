import contextlib
from fractions import Fraction
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "songs/mozart-minuet"
spec = importlib.util.spec_from_file_location("mozart_minuet_preparation", ROOT / "scripts/studies/mozart-minuet/prepare.py")
preparation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preparation)


def read_json(path):
    return json.loads(path.read_text())


class MozartMinuetPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.output = self.directory / "prepared"
        with contextlib.redirect_stdout(io.StringIO()):
            self.report = preparation.prepare(self.output)
        self.mono = read_json(self.output / "score-mono.json")
        self.stereo = read_json(self.output / "score-stereo.json")

    def test_complete_form_retains_written_repeats_and_menuetto_return(self):
        common = read_json(self.output / "common-score.json")
        self.assertEqual(common["totalBeats"], [264, 1])
        self.assertEqual(self.report["sourceNotes"], 584)
        self.assertEqual(self.report["performedSourceNotes"], 1393)
        self.assertEqual([(x["startBeat"], x["endBeat"]) for x in self.report["form"]],
                         [(0, 24), (0, 24), (24, 48), (24, 48), (48, 72), (48, 72), (72, 108), (72, 108), (0, 24), (24, 48)])
        self.assertEqual([len(p["events"]) for p in common["parts"]], [402, 428, 358, 205])
        self.assertEqual(self.mono["voices"][1]["events"][-1], {"startBeat": 263.0, "durationBeats": 1.0, "midi": 55})
        self.assertEqual(self.mono["tailTicks"], 125)

    def test_source_accounting_is_exhaustive_unique_and_preserves_note_identity(self):
        for label, score, expected in (("mono", self.mono, (963, 430, 0)), ("stereo", self.stereo, (1381, 12, 607))):
            report = self.report[label]
            self.assertEqual((report["retainedSourceNotes"], report["omittedSourceNotes"], report["duplicatedSourceNotes"]), expected)
            all_notes = report["retainedEvents"] + report["omittedEvents"]
            identities = [(n["sourcePart"], n["sourceEventIndex"], n["spanIndex"]) for n in all_notes]
            self.assertEqual(len(identities), 1393)
            self.assertEqual(len(set(identities)), 1393)
            destinations = set()
            for note in report["retainedEvents"]:
                for target in note["outputs"]:
                    key = (target["voiceIndex"], target["outputEventIndex"])
                    self.assertNotIn(key, destinations)
                    destinations.add(key)
                    event = score["voices"][key[0]]["events"][key[1]]
                    self.assertEqual(event, {"startBeat": float(Fraction(*note["startBeat"])),
                                             "durationBeats": float(Fraction(*note["durationBeats"])), "midi": note["midi"]})
            self.assertEqual(len(destinations), sum(len(v["events"]) for v in score["voices"]))
            self.assertTrue(all(n["reason"] for n in report["omittedEvents"]))

    def test_viola_keeps_lower_harmonic_tone_in_every_repeated_double_stop(self):
        expected = {21: 60, 22: 59, 45: 60, 46: 59, 69: 60, 70: 59, 93: 60, 94: 59, 237: 60, 238: 59, 261: 60, 262: 59}
        for start, pitch in expected.items():
            for voice in (self.mono["voices"][2], self.stereo["voices"][5]):
                self.assertEqual([n["midi"] for n in voice["events"] if n["startBeat"] == start], [pitch])
        self.assertTrue(all(n["midi"] == 62 and n["sourcePart"] == "viola" for n in self.report["stereo"]["omittedEvents"]))

    def test_mono_inner_role_changes_only_at_source_section_boundaries_and_duplicates_are_exact(self):
        for note in self.report["mono"]["retainedEvents"]:
            if any(target["voice"] == "inner" for target in note["outputs"]):
                expected_part = "violin-2" if 96 <= Fraction(*note["startBeat"]) < 216 else "viola"
                self.assertEqual(note["sourcePart"], expected_part)
        for left, right in ((0, 3), (1, 4)):
            self.assertEqual(self.stereo["voices"][left]["events"], self.stereo["voices"][right]["events"])
            self.assertEqual(self.mono["voices"][left]["events"], self.stereo["voices"][left]["events"])
        for score in (self.mono, self.stereo):
            for voice in score["voices"]:
                for first, second in zip(voice["events"], voice["events"][1:]):
                    self.assertLessEqual(first["startBeat"] + first["durationBeats"], second["startBeat"] + 1e-12)

    def test_native_templates_remain_exact_and_existing_output_is_preserved(self):
        for name in ("mono.json", "stereo.json", "plain.json"):
            self.assertEqual((self.output / name).read_bytes(), (STUDY / name).read_bytes())
        with self.assertRaisesRegex(ValueError, "fresh"):
            preparation.prepare(self.output)

    def test_rejects_changed_source_and_incomplete_form_before_output(self):
        copied = self.directory / "study"
        shutil.copytree(STUDY, copied)
        source = copied / "source/MozartWA-KV525-mov-03.mid"
        source.write_bytes(source.read_bytes() + b"changed")
        destination = self.directory / "rejected-source"
        with patch.object(preparation, "STUDY", copied), self.assertRaisesRegex(ValueError, "hash changed"):
            preparation.prepare(destination)
        self.assertFalse(destination.exists())
        plan = read_json(STUDY / "arrangement.json")
        plan["spans"] = plan["spans"][:-2]
        path = self.directory / "incomplete.json"
        path.write_text(json.dumps(plan))
        with self.assertRaisesRegex(ValueError, "Menuetto return"):
            preparation.prepare(self.directory / "rejected-form", path)

    def test_optional_tempo_override_changes_no_note_data(self):
        plan = read_json(STUDY / "arrangement.json")
        plan["quarterBpm"] = 120
        path = self.directory / "tempo.json"
        path.write_text(json.dumps(plan))
        output = self.directory / "tempo"
        with contextlib.redirect_stdout(io.StringIO()):
            preparation.prepare(output, path)
        altered = read_json(output / "score-mono.json")
        self.assertEqual(altered["quarterBpm"], 120)
        self.assertEqual(altered["voices"], self.mono["voices"])


if __name__ == "__main__":
    unittest.main()
