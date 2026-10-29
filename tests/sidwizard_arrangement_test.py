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


def expanded_native_cells(manifest):
    data = Path(manifest["nativePath"]).read_bytes()
    cursor = 66 + sum(len(voice["sequence"]) + 3 for voice in manifest["voices"])
    patterns = {}
    for pattern in manifest["patterns"]:
        packed = data[cursor:cursor + pattern["packedBytes"] + 1]
        cursor += len(packed)
        cells = []
        index = 0
        while index < len(packed) - 2:
            value = packed[index]
            if 0x70 <= value <= 0x77:
                cells.extend([b"\x00"] * (value - 0x6e))
                index += 1
            else:
                size = 2 if value & 0x80 else 1
                cells.append(packed[index:index + size])
                index += size
        if len(cells) != packed[-1] or sum(map(len, cells)) + 1 != packed[-2]:
            raise AssertionError("Saved pattern disagrees with its decoded footer")
        patterns[pattern["number"]] = cells
    return [[cell for number in voice["sequence"] for cell in patterns[number]] for voice in manifest["voices"]]


class SIDWizardArrangementTest(unittest.TestCase):
    def create(self, directory, score, sid_count=None, sid_model=None, **overrides):
        source = Path(directory) / "score.json"
        source.write_text(json.dumps(score))
        configuration = Path(directory) / "native.json"
        settings = recipe(source, score)
        if sid_count is not None:
            settings["sidCount"] = sid_count
        if sid_model is not None:
            settings["sidModel"] = sid_model
        settings.update(overrides)
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
            self.assertIsNone(default["patternBeats"])
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

    def test_beat_boundaries_use_absolute_rounding_and_preserve_byte_limited_cells(self):
        cells = [b"\xb1\x01" if index % 2 == 0 else b"\x00" for index in range(1500)]
        chunks = list(ARRANGER.pattern_chunks(cells, pattern_beats=400.4, ticks_per_beat=1.003))
        boundaries = [math.floor(index * 400.4 * 1.003 + 0.5) for index in range(1, 4)]
        starts = [start for start, chunk in chunks]
        self.assertTrue(all(boundary in starts for boundary in boundaries))
        self.assertEqual([cell for start, chunk in chunks for cell in chunk], cells)
        for start, chunk in chunks:
            self.assertLessEqual(len(chunk), 248)
            self.assertLessEqual(sum(map(len, chunk)) + 1, 249)
            self.assertFalse(any(start < boundary < start + len(chunk) for boundary in boundaries))
        sparse = list(ARRANGER.pattern_chunks([b"\x00"] * 450, pattern_beats=100.2))
        self.assertEqual([start for start, chunk in sparse], [0, 100, 200, 301, 401])

    def test_beat_packing_preserves_every_native_cell_note_gate_and_partial_tail(self):
        score = synthetic_score([
            {"startBeat": 0, "durationBeats": 9, "midi": 60},
            {"startBeat": 9, "durationBeats": 6, "midi": 62},
            {"startBeat": 27, "durationBeats": 6, "midi": 64},
        ], beats=33.2)
        score["tailTicks"] = 15
        score["voices"][1]["events"] = [{"startBeat": 3, "durationBeats": 23, "midi": 48}]
        for clock in ("pal", "ntsc"):
            with self.subTest(clock=clock), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "default").mkdir()
                (root / "beats").mkdir()
                _, default = self.create(root / "default", score, clock=clock)
                _, bounded = self.create(root / "beats", score, clock=clock, patternBeats=5.5)
                self.assertEqual(bounded["patternBeats"], 5.5)
                self.assertEqual(expanded_native_cells(bounded), expanded_native_cells(default))
                for field in ("rowCount", "scoreTicks", "tailTicks", "stopTick", "stopVolumeClearTick", "timingChanges", "articulationChanges"):
                    self.assertEqual(bounded[field], default[field])
                rate = bounded["ticksPerSecond"] * 60 / score["quarterBpm"]
                boundaries = [0]
                index = 1
                while math.floor(index * 5.5 * rate + 0.5) < bounded["rowCount"]:
                    boundaries.append(math.floor(index * 5.5 * rate + 0.5))
                    index += 1
                for original, voice, cells in zip(default["voices"], bounded["voices"], expanded_native_cells(bounded)):
                    self.assertEqual([None if tick == 0 else tick - 1 for tick in boundaries], [entry["tick"] for entry in voice["expectedPatternEntries"]])
                    self.assertEqual([{key: value for key, value in note.items() if key not in ("pattern", "row", "byteOffset")} for note in voice["notes"]], [{key: value for key, value in note.items() if key not in ("pattern", "row", "byteOffset")} for note in original["notes"]])
                    self.assertEqual(len(cells), bounded["rowCount"])
                    self.assertEqual(cells[-1], b"\x7e")

    def test_beat_packing_reuses_repeated_phrases_that_exceed_greedy_pattern_capacity(self):
        score = synthetic_score([], beats=223 * 40)
        for voice_index, voice in enumerate(score["voices"]):
            voice["events"] = [{"startBeat": repeat * 223 + offset, "durationBeats": 8, "midi": 48 + 12 * voice_index + note} for repeat in range(40) for note, offset in enumerate((0, 17, 43, 78, 113, 140, 167, 211))]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "default").mkdir()
            (root / "beats").mkdir()
            with self.assertRaisesRegex(ValueError, "100-pattern limit"):
                self.create(root / "default", score)
            _, manifest = self.create(root / "beats", score, patternBeats=223)
            self.assertEqual(len(manifest["patterns"]), 4)
            self.assertEqual([len(voice["sequence"]) for voice in manifest["voices"]], [41, 41, 41])
            self.assertEqual([len(cells) for cells in expanded_native_cells(manifest)], [8924] * 3)
            self.assertEqual(sum(len(voice["notes"]) for voice in manifest["voices"]), 960)

    def test_invalid_or_subtick_pattern_beats_are_rejected_before_output(self):
        for value in (None, True, False, "8", [], {}, 0, -1, math.inf, -math.inf, math.nan, 0.99):
            with self.subTest(pattern_beats=value), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(ValueError, "patternBeats"):
                    self.create(directory, synthetic_score([], beats=4), patternBeats=value)
                self.assertFalse((Path(directory) / "out").exists())

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

    def shifted_recipe(self, directory, melody, bass=(), *, shift=-1, short_melody="pluck"):
        score = synthetic_score(melody)
        score["voices"][1]["events"] = list(bass)
        overrides = {
            "instruments": {"pluck": INSTRUMENT, "low": dict(INSTRUMENT, name="LOWBASS", octave_shift=shift)},
            "sections": [{"name": "Whole score", "startBeat": 0, "endBeat": score["totalBeats"], "voices": {"melody": "low", "bass": "pluck", "harmony": "pluck"}}],
            "shortNoteInstruments": {"melody": short_melody, "bass": "pluck", "harmony": "pluck"},
        }
        return self.create(directory, score, **overrides)

    def test_shifted_instrument_records_its_shift_on_its_notes_only(self):
        melody = [{"startBeat": 0, "durationBeats": 10, "midi": 60}, {"startBeat": 20, "durationBeats": 10, "midi": 72}]
        bass = [{"startBeat": 0, "durationBeats": 10, "midi": 40}]
        with tempfile.TemporaryDirectory() as directory:
            _, manifest = self.shifted_recipe(directory, melody, bass)
            notes = manifest["voices"][0]["notes"]
            # The cell keeps the written pitch; the driver adds the instrument's shift when the note starts.
            self.assertEqual([(note["nativeNote"], note["octaveShiftSemitones"]) for note in notes], [(49, -12), (61, -12)])
            self.assertNotIn("octaveShiftSemitones", manifest["voices"][1]["notes"][0])
            self.assertEqual((Path(directory) / "out/instruments/low.swi").read_bytes()[2:][9], 244)

    def test_notes_pushed_out_of_range_by_the_shift_are_rejected_at_the_range_edges(self):
        for shift, midi, accepted in ((-1, 24, True), (-1, 23, False), (1, 94, True), (1, 95, False), (-3, 48, True), (-3, 47, False)):
            with self.subTest(shift=shift, midi=midi), tempfile.TemporaryDirectory() as directory:
                melody = [{"startBeat": 0, "durationBeats": 10, "midi": midi}]
                if accepted:
                    _, manifest = self.shifted_recipe(directory, melody, shift=shift)
                    self.assertEqual(manifest["voices"][0]["notes"][0]["octaveShiftSemitones"], 12 * shift)
                else:
                    with self.assertRaisesRegex(ValueError, r"melody.*low.*octave shift"):
                        self.shifted_recipe(directory, melody, shift=shift)
                    self.assertFalse((Path(directory) / "out").exists())

    def test_range_is_checked_against_the_instrument_that_finally_plays_the_note(self):
        short = [{"startBeat": 10, "durationBeats": 2, "midi": 20}]
        with tempfile.TemporaryDirectory() as directory:
            # A two-tick note moves to the unshifted short-note instrument, so the shifted section instrument never plays it.
            _, manifest = self.shifted_recipe(directory, short, short_melody="pluck")
            note = manifest["voices"][0]["notes"][0]
            self.assertEqual((note["instrumentId"], "octaveShiftSemitones" in note), ("pluck", False))
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(ValueError, r"melody.*low.*octave shift"):
            self.shifted_recipe(directory, short, short_melody="low")

    def test_critical_short_notes_carry_the_shift_of_their_instrument(self):
        with tempfile.TemporaryDirectory() as directory:
            _, manifest = self.shifted_recipe(directory, [{"startBeat": 10, "durationBeats": 2, "midi": 60}], short_melody="low")
            self.assertEqual([note["octaveShiftSemitones"] for note in manifest["criticalNotes"]], [-12])

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
