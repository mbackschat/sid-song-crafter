import importlib.util
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("sidwizard_arrangement", ROOT / "scripts/arrange-sidwizard.py")
ARRANGER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ARRANGER)


INSTRUMENT = {
    "name": "TESTPLK", "control": "0a", "hard_restart_adsr": "0f00", "adsr": "0734", "frame1": "09",
    "wave": [["11", "00", "00"]], "pulse": [], "filter": [],
}


def recipe(score_path, score):
    return {
        "format": "sidwizard-arrangement-v1", "score": str(score_path), "title": "Native test", "author": "Test", "released": "2026", "timingPolicy": "retain-full-pitch",
        "instruments": {"pluck": INSTRUMENT},
        "sections": [{"name": "Whole score", "startBeat": 0, "endBeat": score["totalBeats"], "voices": {voice["name"]: "pluck" for voice in score["voices"]}}],
        "shortNoteMaxTicks": 2, "shortNoteInstruments": {voice["name"]: "pluck" for voice in score["voices"]},
    }


def synthetic_score(events, beats=500):
    return {
        "title": "Original timing test", "composer": "Test", "quarterBpm": 60 * (17734475 / 18) / (312 * 63),
        "totalBeats": beats, "tailTicks": 3, "volume": 15,
        "voices": [{"name": name, "events": events if index == 0 else []} for index, name in enumerate(("melody", "bass", "harmony"))],
    }


class SIDWizardArrangementTest(unittest.TestCase):
    def create(self, directory, score, sid_count=None, sid_model=None):
        source = Path(directory) / "score.json"
        source.write_text(json.dumps(score))
        configuration = Path(directory) / "native.json"
        settings = recipe(source, score)
        if sid_count is not None:
            settings["sidCount"] = sid_count
        if sid_model is not None:
            settings["sidModel"] = sid_model
        configuration.write_text(json.dumps(settings))
        return configuration, ARRANGER.arrange(configuration, Path(directory) / "out")

    def test_ntsc_target_quantizes_absolute_seconds_and_retains_the_pal_tail_duration(self):
        for count in (1, 2):
            with self.subTest(sid_count=count), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                score = synthetic_score([], beats=5)
                score["quarterBpm"] = 60
                score["voices"] = [{"name": f"part-{voice}", "events": [{"startBeat": 1.1, "durationBeats": 0.37, "midi": 69 + voice}]} for voice in range(count * 3)]
                source, configuration = root / "score.json", root / "recipe.json"
                source.write_text(json.dumps(score))
                settings = recipe(source, score)
                settings.update(sidCount=count, clock="ntsc")
                configuration.write_text(json.dumps(settings))
                manifest = ARRANGER.arrange(configuration, root / "out")
                self.assertEqual(manifest["clock"], "NTSC")
                self.assertEqual(manifest["clockHz"], 14318181.82 / 14)
                self.assertEqual(manifest["frameCycles"], 17095)
                rate = (14318181.82 / 14) / 17095
                for voice in manifest["voices"]:
                    note = voice["notes"][0]
                    self.assertLessEqual(abs(note["sourceStartTick"] / rate - 1.1), 0.5 / rate)
                    self.assertLessEqual(abs((note["sourceStartTick"] + note["sourceDurationTicks"]) / rate - 1.47), 0.5 / rate)
                self.assertLessEqual(abs(manifest["scoreTicks"] / rate - 5), 0.5 / rate)
                self.assertEqual(manifest["tailTicks"], 4)
                self.assertEqual(manifest["sourceTailPalTicks"], 3)
                self.assertEqual(manifest["effectTimingPolicy"], "target-vbi")
                self.assertEqual(manifest["envelopeTimingPolicy"], "retain-sid-adsr-codes")
                self.assertEqual(manifest["effectUpdateRateHz"], rate)

    def test_clock_override_and_omitted_clock_preserve_the_frozen_pal_native_fixture(self):
        configuration = ROOT / "tests/fixtures/sidwizard-2sid/recipe.json"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            default = ARRANGER.arrange(configuration, root / "default")
            explicit = ARRANGER.arrange(configuration, root / "explicit", clock="pal")
            self.assertEqual(default["clock"], "PAL")
            self.assertEqual(Path(default["nativePath"]).read_bytes(), Path(explicit["nativePath"]).read_bytes())
            self.assertEqual(default["nativeSha256"], "c11f92387cbdec63124ba1933b804e1e78f040eade3658b29ebdd6ad4d600624")
            settings = json.loads(configuration.read_text())
            settings["score"] = str((configuration.parent / settings["score"]).resolve())
            settings["clock"] = "ntsc"
            alternate = root / "alternate.json"
            alternate.write_text(json.dumps(settings))
            overridden = ARRANGER.arrange(alternate, root / "override", clock="pal")
            self.assertEqual(overridden["clock"], "PAL")
            self.assertEqual(overridden["nativeSha256"], default["nativeSha256"])

    def test_ntsc_short_patch_threshold_retains_original_pal_source_duration(self):
        score = synthetic_score([{"startBeat": 0, "durationBeats": 2.1, "midi": 60}], beats=8)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "score.json"
            source.write_text(json.dumps(score))
            settings = recipe(source, score)
            settings.update(clock="ntsc")
            settings["instruments"]["short"] = dict(INSTRUMENT, name="SHORT")
            settings["shortNoteInstruments"]["melody"] = "short"
            configuration = root / "recipe.json"
            configuration.write_text(json.dumps(settings))
            manifest = ARRANGER.arrange(configuration, root / "out")
            note = manifest["voices"][0]["notes"][0]
            self.assertEqual(note["sourcePalDurationTicks"], 2)
            self.assertEqual(note["durationTicks"], 3)
            self.assertEqual(note["instrumentId"], "short")

    def test_unknown_recipe_or_override_clock_is_rejected_before_output(self):
        for value in ("auto", "PAL", "old-ntsc", None, True):
            with self.subTest(clock=value), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                score = synthetic_score([], beats=4)
                source, configuration = root / "score.json", root / "recipe.json"
                source.write_text(json.dumps(score))
                settings = recipe(source, score)
                settings["clock"] = value
                configuration.write_text(json.dumps(settings))
                with self.assertRaisesRegex(ValueError, "clock"):
                    ARRANGER.arrange(configuration, root / "out")
                self.assertFalse((root / "out").exists())
                if value is not None:
                    with self.assertRaisesRegex(ValueError, "clock"):
                        ARRANGER.arrange(configuration, root / "out", clock=value)

    def test_sid_model_is_retained_for_each_chip_without_changing_native_bytes(self):
        for count in (1, 2):
            score = synthetic_score([], beats=8)
            score["voices"] = [{"name": f"part-{index}", "events": []} for index in range(count * 3)]
            native_bytes = []
            for model in ("MOS6581", "MOS8580"):
                with self.subTest(count=count, model=model), tempfile.TemporaryDirectory() as directory:
                    _, manifest = self.create(directory, score, sid_count=count, sid_model=model)
                    self.assertEqual(manifest["sidModel"], model)
                    self.assertEqual(manifest["sids"], [{"baseAddress": base, "model": model} for base in (0xd400, 0xd420)[:count]])
                    native_bytes.append(Path(manifest["nativePath"]).read_bytes())
            self.assertEqual(native_bytes[0], native_bytes[1])

    def test_invalid_sid_model_is_rejected_before_output(self):
        for model in ("6581", "unknown", 6581, True):
            with self.subTest(model=model), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(ValueError, "SID model"):
                    self.create(directory, synthetic_score([], beats=8), sid_model=model)
                self.assertFalse((Path(directory) / "out").exists())

    def test_two_sid_recipe_retains_six_ordered_voices_and_emits_native_stereo_header(self):
        score = synthetic_score([], beats=8)
        score["voices"] = [{"name": f"part-{index}", "events": [{"startBeat": index % 3, "durationBeats": 3, "midi": 60 + index}]} for index in range(6)]
        with tempfile.TemporaryDirectory() as directory:
            _, manifest = self.create(directory, score, sid_count=2)
            native = Path(manifest["nativePath"])
            data = native.read_bytes()
            self.assertEqual(native.suffix, ".sws")
            self.assertEqual(data[2:6], b"SWMS")
            self.assertEqual(data[14], 6)
            self.assertEqual(data[23:25], b"\x04\x00")
            self.assertEqual(manifest["sidCount"], 2)
            self.assertEqual(manifest["sids"], [{"baseAddress": 0xd400, "model": "MOS8580"}, {"baseAddress": 0xd420, "model": "MOS8580"}])
            self.assertEqual([(voice["sidIndex"], voice["sidVoice"]) for voice in manifest["voices"]], [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)])
            self.assertEqual([voice["notes"][0]["midi"] for voice in manifest["voices"]], list(range(60, 66)))
            self.assertEqual(manifest["nativeSha256"], hashlib.sha256(data).hexdigest())

    def test_chip_count_requires_exactly_three_or_six_distinct_voices(self):
        for sid_count, voices in ((2, 3), (1, 6), (3, 6), (True, 3), ("2", 6)):
            with self.subTest(sid_count=sid_count, voices=voices), tempfile.TemporaryDirectory() as directory:
                score = synthetic_score([], beats=4)
                score["voices"] = [{"name": f"part-{index}", "events": []} for index in range(voices)]
                with self.assertRaisesRegex(ValueError, "SID count|voices"):
                    self.create(directory, score, sid_count=sid_count)
                self.assertFalse((Path(directory) / "out").exists())

    def test_two_sid_instrument_capacity_is_29_without_raising_native_limits(self):
        score = synthetic_score([], beats=4)
        score["voices"] = [{"name": f"part-{index}", "events": []} for index in range(6)]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "score.json"
            source.write_text(json.dumps(score))
            settings = recipe(source, score)
            settings["sidCount"] = 2
            settings["instruments"].update({f"patch-{index}": INSTRUMENT for index in range(29)})
            configuration = Path(directory) / "native.json"
            configuration.write_text(json.dumps(settings))
            with self.assertRaisesRegex(ValueError, "29 instruments"):
                ARRANGER.arrange(configuration, Path(directory) / "out")
            self.assertFalse((Path(directory) / "out").exists())

    def test_retained_six_voice_fixture_keeps_both_original_filter_programs(self):
        configuration = ROOT / "tests/fixtures/sidwizard-2sid/recipe.json"
        with tempfile.TemporaryDirectory() as directory:
            manifest = ARRANGER.arrange(configuration, Path(directory) / "out")
            self.assertEqual(sum(len(voice["notes"]) for voice in manifest["voices"]), 12)
            self.assertEqual(manifest["timingChanges"], [])
            left = (Path(directory) / "out/instruments/left-filter.swi").read_bytes()[2:]
            right = (Path(directory) / "out/instruments/right-filter.swi").read_bytes()[2:]
            self.assertEqual(left[left[11]:left[11] + 3], b"\x93\x24\x00")
            self.assertEqual(right[right[11]:right[11] + 3], b"\x93\x78\x00")

    def test_full_score_preserves_all_981_notes_and_absolute_pal_timing_within_native_limits(self):
        score = json.loads((ROOT / "songs/fuer-elise.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            _, manifest = self.create(directory, score)
            self.assertEqual(sum(len(voice["notes"]) for voice in manifest["voices"]), 981)
            self.assertLessEqual(len(manifest["patterns"]), 100)
            self.assertTrue(all(pattern["rows"] <= 248 and pattern["unpackedBytes"] <= 249 for pattern in manifest["patterns"]))
            self.assertTrue(all(len(voice["sequence"]) < 128 for voice in manifest["voices"]))
            rate = (17734475 / 18) / (312 * 63) * 60 / 72
            for source_voice, native_voice in zip(score["voices"], manifest["voices"]):
                for source_note, native_note in zip(source_voice["events"], native_voice["notes"]):
                    start = math.floor(source_note["startBeat"] * rate + 0.5)
                    end = math.floor((source_note["startBeat"] + source_note["durationBeats"]) * rate + 0.5)
                    self.assertEqual((native_note["sourceStartTick"], native_note["sourceDurationTicks"]), (start, end - start))
                    self.assertEqual(native_note["nativeNote"], source_note["midi"] - 11)
            self.assertEqual(len(manifest["timingChanges"]), 2)
            grace, following = manifest["voices"][0]["notes"][206:208]
            self.assertEqual((grace["startTick"], grace["durationTicks"]), (3006, 2))
            self.assertEqual(following["startTick"], 3008)
            self.assertEqual(following["startTick"] + following["durationTicks"], following["sourceStartTick"] + following["sourceDurationTicks"])
            self.assertEqual([note["audibleCheckTick"] for note in manifest["criticalNotes"]], [2774, 3007])
            self.assertEqual(manifest["scoreTicks"], 7832)
            self.assertEqual(manifest["totalTicks"], 7857)
            self.assertEqual(manifest["rowCount"], 7858)
            self.assertEqual(manifest["stopTick"], 7857)
            self.assertEqual(manifest["stopVolumeClearTick"], 7857)
            for voice in manifest["voices"]:
                self.assertEqual(voice["expectedSequenceEnding"], [{"tick": 7857, "entry": 0xa0}, {"tick": 7857, "entry": 0xfe}])
                terminal = [cell for cell in manifest["cellMap"] if cell["voice"] == manifest["voices"].index(voice) and cell["tick"] == 7857]
                self.assertEqual([(cell["nativeByte"], cell["instrument"]) for cell in terminal], [(0x7e, None)])

    def test_one_frame_note_survives_and_colliding_release_is_reported(self):
        score = synthetic_score([{"startBeat": 0, "durationBeats": 1, "midi": 60}, {"startBeat": 1, "durationBeats": 3, "midi": 60}], beats=4)
        with tempfile.TemporaryDirectory() as directory:
            _, manifest = self.create(directory, score)
            notes = manifest["voices"][0]["notes"]
            self.assertEqual([(note["startTick"], note["durationTicks"]) for note in notes], [(0, 2), (2, 2)])
            self.assertEqual(notes[0]["nativeGateOffTick"], None)
            self.assertEqual([(change["startTickDelta"], change["durationTicksDelta"]) for change in manifest["timingChanges"]], [(0, 1), (1, -1)])
            self.assertEqual([change["kind"] for change in manifest["articulationChanges"]].count("same-tick-release-replaced-by-note"), 1)

    def test_pattern_boundary_preserves_next_row_without_an_extra_tick(self):
        score = synthetic_score([{"startBeat": 246, "durationBeats": 2, "midi": 60}, {"startBeat": 248, "durationBeats": 3, "midi": 62}], beats=251)
        with tempfile.TemporaryDirectory() as directory:
            _, manifest = self.create(directory, score)
            cells = [cell for cell in manifest["cellMap"] if cell["voice"] == 0 and cell["kind"] == "note"]
            self.assertEqual([cell["tick"] for cell in cells], [246, 248])
            self.assertEqual(cells[0]["row"], 246)
            self.assertEqual(cells[1]["row"], 1)
            self.assertEqual(manifest["voices"][0]["expectedPatternEntries"][1]["tick"], 246)

    def test_rle_footer_counts_decoded_bytes_and_chunks_respect_editable_native_capacity(self):
        score = synthetic_score([{"startBeat": 0, "durationBeats": 20, "midi": 60}], beats=500)
        with tempfile.TemporaryDirectory() as directory:
            _, manifest = self.create(directory, score)
            pattern = manifest["patterns"][0]
            self.assertEqual(pattern["unpackedBytes"], 249)
            self.assertLess(pattern["packedBytes"], pattern["unpackedBytes"])
            self.assertEqual(pattern["rows"], 247)

    def test_rejects_overlapping_sections_and_note_collisions(self):
        score = synthetic_score([{"startBeat": 0, "durationBeats": 2, "midi": 60}, {"startBeat": 0, "durationBeats": 2, "midi": 64}], beats=4)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "overlap|collision"):
                self.create(directory, score)

    def test_rejects_incomplete_and_overlapping_section_schedules(self):
        score = synthetic_score([], beats=4)
        for boundaries in [[(0, 3)], [(0, 3), (2, 4)], [(0, 1), (2, 4)]]:
            with self.subTest(boundaries=boundaries), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "score.json"
                source.write_text(json.dumps(score))
                configuration = recipe(source, score)
                prototype = configuration["sections"][0]
                configuration["sections"] = [dict(prototype, startBeat=start, endBeat=end) for start, end in boundaries]
                path = Path(directory) / "native.json"
                path.write_text(json.dumps(configuration))
                with self.assertRaisesRegex(ValueError, "full|overlap|gaps"):
                    ARRANGER.arrange(path, Path(directory) / "out")

    def test_rejects_adjacent_one_frame_notes_without_a_borrowable_frame(self):
        score = synthetic_score([{"startBeat": 0, "durationBeats": 1, "midi": 60}, {"startBeat": 1, "durationBeats": 1, "midi": 62}], beats=2)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "timing budget"):
                self.create(directory, score)

    def test_shortened_following_note_uses_short_patch_and_gets_body_verification(self):
        score = synthetic_score([{"startBeat": 0, "durationBeats": 1, "midi": 60}, {"startBeat": 1, "durationBeats": 3, "midi": 62}], beats=4)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "score.json"
            source.write_text(json.dumps(score))
            configuration = recipe(source, score)
            configuration["instruments"]["short"] = dict(INSTRUMENT, name="SHORT")
            configuration["shortNoteInstruments"]["melody"] = "short"
            path = Path(directory) / "native.json"
            path.write_text(json.dumps(configuration))
            manifest = ARRANGER.arrange(path, Path(directory) / "out")
            self.assertEqual([note["instrumentId"] for note in manifest["voices"][0]["notes"]], ["short", "short"])
            self.assertEqual([note["audibleCheckTick"] for note in manifest["criticalNotes"]], [1, 3])
            self.assertEqual(manifest["sourceSha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(manifest["recipeSha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(manifest["nativeSha256"], hashlib.sha256(Path(manifest["nativePath"]).read_bytes()).hexdigest())

    def test_refuses_existing_native_output(self):
        score = synthetic_score([], beats=4)
        with tempfile.TemporaryDirectory() as directory:
            configuration, _ = self.create(directory, score)
            with self.assertRaisesRegex(ValueError, "existing|fresh"):
                ARRANGER.arrange(configuration, Path(directory) / "out")

    def test_instrument_ids_cannot_leave_the_native_output_directory(self):
        score = synthetic_score([], beats=4)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "score.json"
            source.write_text(json.dumps(score))
            configuration = recipe(source, score)
            configuration["instruments"] = {"../escape": INSTRUMENT}
            configuration["sections"][0]["voices"] = {voice["name"]: "../escape" for voice in score["voices"]}
            configuration["shortNoteInstruments"] = {}
            path = Path(directory) / "native.json"
            path.write_text(json.dumps(configuration))
            with self.assertRaisesRegex(ValueError, "instrument id"):
                ARRANGER.arrange(path, Path(directory) / "out")
            self.assertFalse((Path(directory) / "out").exists())


if __name__ == "__main__":
    unittest.main()
