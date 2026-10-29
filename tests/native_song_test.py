import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("native_song", ROOT / "scripts/native-song.py")
native_song = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native_song)


class NativeClockContractTest(unittest.TestCase):
    def test_conversion_export_must_agree_on_clock_and_grid(self):
        manifest = {"clock": "NTSC", "clockHz": 14318181.82 / 14, "ticksPerSecond": (14318181.82 / 14) / 17095}
        self.assertEqual(native_song.native_clock(manifest, {"clock": "NTSC"}).name, "ntsc")
        for change in ({"clock": "PAL"}, {"clock": "unknown"}, {}):
            with self.subTest(export=change), self.assertRaises(ValueError):
                native_song.native_clock(manifest, change)
        for key in ("clockHz", "ticksPerSecond"):
            changed = dict(manifest)
            changed[key] *= 1.2
            with self.subTest(field=key), self.assertRaises(ValueError):
                native_song.native_clock(changed, {"clock": "NTSC"})

    def test_export_timing_metadata_cannot_contradict_its_clock(self):
        for field, value in (("clockHz", 985248), ("ticksPerSecond", 50), ("frameCycles", 19656)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                native_song.native_clock({"clock": "NTSC"}, {"clock": "NTSC", field: value})

    def test_frame_geometry_must_match_declared_region(self):
        for clock, cycles in (("PAL", 19656), ("NTSC", 17095)):
            for value in (cycles + 1, float(cycles), True):
                with self.subTest(clock=clock, value=value), self.assertRaises(ValueError):
                    native_song.native_clock({"clock": clock, "frameCycles": value}, {"clock": clock})

    def test_legacy_pal_manifest_retains_its_clock(self):
        manifest = {"clockHz": 17734475 / 18, "ticksPerSecond": (17734475 / 18) / 19656}
        self.assertEqual(native_song.native_clock(manifest, {"clock": "PAL"}).name, "pal")


def fixture():
    cells = [
        {"voice": 0, "tick": 0, "pattern": 1, "byteOffset": 0, "noteCode": 61, "instrument": 1},
        {"voice": 0, "tick": 2, "pattern": 1, "byteOffset": 3, "noteCode": 62, "instrument": 1},
        {"voice": 0, "tick": 4, "pattern": 1, "byteOffset": 6, "noteCode": 126, "instrument": None},
        {"voice": 0, "tick": 5, "pattern": 1, "byteOffset": 7, "noteCode": 126, "instrument": None},
        {"voice": 1, "tick": 1, "pattern": 2, "byteOffset": 1, "noteCode": 49, "instrument": 2},
        {"voice": 1, "tick": 3, "pattern": 2, "byteOffset": 4, "noteCode": 126, "instrument": None},
        {"voice": 1, "tick": 5, "pattern": 2, "byteOffset": 6, "noteCode": 126, "instrument": None},
        {"voice": 2, "tick": 0, "pattern": 3, "byteOffset": 0, "noteCode": 126, "instrument": None},
        {"voice": 2, "tick": 5, "pattern": 3, "byteOffset": 3, "noteCode": 126, "instrument": None},
    ]
    notes = [[{"startTick": 0, "nativeNote": 61, "instrument": 1}, {"startTick": 2, "nativeNote": 62, "instrument": 1}], [{"startTick": 1, "nativeNote": 49, "instrument": 2}], []]
    manifest = {"cellMap": cells, "stopTick": 5, "stopVolumeClearTick": 5, "clockHz": 17734475 / 18, "criticalNotes": [{"voice": 0, "startTick": 0, "audibleCheckTick": 1, "midi": 72}], "voices": [{"notes": part, "expectedPatternEntries": [{"pattern": voice + 1, "tick": None}], "expectedSequenceEnding": [{"tick": 5, "entry": 254}]} for voice, part in enumerate(notes)]}
    starts = [{"voice": voice, "tick": note["startTick"], "nativeNote": note["nativeNote"], "instrument": note["instrument"]} for voice, part in enumerate(notes) for note in part]
    sequences = [{"voice": voice, "tick": None, "entry": voice + 1} for voice in range(3)] + [{"voice": voice, "tick": 5, "entry": 254} for voice in range(3)]
    observer = SimpleNamespace(cells=copy.deepcopy(cells), starts=starts, sequence_reads=sequences)
    frames = [[0] * 25 for _ in range(8)]
    word = round(440 * 2 ** ((72 - 69) / 12) * 2**24 / manifest["clockHz"])
    frames[1][0:2] = [word & 255, word >> 8]
    frames[1][4] = 0x11
    return manifest, observer, frames


class NativeSongTest(unittest.TestCase):
    @unittest.skipUnless((ROOT / ".tools/sid-wizard-exporter-2sid/exporter.labels").is_file() and (ROOT / ".local/bin/render-sid").is_file(), "Pinned two-SID exporter and renderer required")
    def test_6581_recipe_survives_conversion_export_cpu_audit_and_stereo_render(self):
        with tempfile.TemporaryDirectory() as directory, patch("builtins.print"):
            recipe = json.loads((ROOT / "tests/fixtures/sidwizard-2sid/recipe.json").read_text())
            recipe.update(sidModel="MOS6581", score=str(ROOT / "tests/fixtures/sidwizard-2sid/score.json"))
            path = Path(directory) / "recipe.json"
            path.write_text(json.dumps(recipe))
            output = Path(directory) / "song"
            report = native_song.run_song(path, output, excerpt_seconds=1)
            self.assertEqual(report["audit"]["sidModel"], "MOS6581")
            self.assertEqual(report["audit"]["sids"], [{"baseAddress": base, "model": "MOS6581"} for base in (0xd400, 0xd420)])
            self.assertEqual(report["schedule"]["noteCounts"], [2] * 6)
            self.assertEqual(report["pcm"]["channels"], 2)
            for name in ("conversion.json", "export.json"):
                self.assertEqual(json.loads((output / name).read_text())["sidModel"], "MOS6581")

    def test_layout_rejects_invalid_model_and_disagreement_with_chip_metadata(self):
        self.assertEqual(native_song.sid_layout({"sidModel": "MOS6581"}), [{"baseAddress": 0xd400, "model": "MOS6581"}])
        for report in (
            {"sidModel": "unknown"},
            {"sidModel": "MOS6581", "sids": [{"baseAddress": 0xd400, "model": "MOS8580"}]},
            {"sidCount": 2, "sidModel": "MOS6581", "sids": [{"baseAddress": base, "model": "MOS8580"} for base in (0xd400, 0xd420)]},
        ):
            with self.subTest(report=report), self.assertRaisesRegex(ValueError, "layout"):
                native_song.sid_layout(report)

    @unittest.skipUnless((ROOT / ".tools/sid-wizard-exporter-2sid/exporter.labels").is_file() and (ROOT / ".local/bin/render-sid").is_file(), "Pinned two-SID exporter and renderer required")
    def test_original_six_voice_fixture_survives_the_complete_native_workflow(self):
        with tempfile.TemporaryDirectory() as directory, patch("builtins.print"):
            report = native_song.run_song(ROOT / "tests/fixtures/sidwizard-2sid/recipe.json", Path(directory) / "song", excerpt_start=0.5, excerpt_seconds=1)
            self.assertEqual(report["schedule"]["noteCounts"], [2] * 6)
            self.assertTrue(report["schedule"]["postStopGatesAndVolumeClear"])
            self.assertEqual(report["audit"]["sidCount"], 2)
            self.assertEqual(report["pcm"]["channels"], 2)
            self.assertEqual(report["excerpt"]["sourceStartFrame"], 22050)
            excerpt = native_song.read_pcm16(report["excerpt"]["path"])
            original = native_song.read_pcm16(Path(directory) / "song/native-song.wav")
            self.assertEqual(excerpt.frames, 44100)
            self.assertEqual(excerpt.channels, 2)
            self.assertEqual(excerpt.samples, original.samples[44100:132300])

    def dual_fixture(self):
        manifest, observer, frames = fixture()
        manifest["sidCount"] = 2
        manifest["sids"] = [{"baseAddress": base, "model": "MOS8580"} for base in (0xd400, 0xd420)]
        manifest["voices"] += copy.deepcopy(manifest["voices"])
        for collection in (manifest["cellMap"], observer.cells, observer.starts, observer.sequence_reads):
            collection.extend([dict(entry, voice=entry["voice"] + 3) for entry in collection])
        manifest["criticalNotes"].append(dict(manifest["criticalNotes"][0], voice=3))
        return manifest, observer, [state + state for state in frames]

    def test_dual_schedule_checks_all_six_voices_and_both_stopped_chips(self):
        manifest, observer, frames = self.dual_fixture()
        result = native_song.verify_driver_events(manifest, observer, frames)
        self.assertEqual(result["noteCounts"], [2, 1, 0, 2, 1, 0])
        self.assertEqual([note["voice"] for note in result["criticalNotes"]], [0, 3])
        for register in (29, 36, 43, 49):
            changed = copy.deepcopy(frames)
            changed[5][register] = 1
            with self.subTest(register=register), self.assertRaisesRegex(ValueError, "post-stop"):
                native_song.verify_driver_events(manifest, observer, changed)
        frames[1][25] ^= 32
        with self.assertRaisesRegex(ValueError, "Voice 4 critical"):
            native_song.verify_driver_events(manifest, observer, frames)

    def test_rejects_inconsistent_chip_voice_and_frame_layouts(self):
        for change in (
            lambda manifest, frames: manifest.update(sidCount=3),
            lambda manifest, frames: manifest["voices"].pop(),
            lambda manifest, frames: manifest["sids"][1].update(baseAddress=0xd400),
            lambda manifest, frames: manifest["sids"][1].update(model="MOS6581"),
            lambda manifest, frames: manifest["voices"][3].update(sidIndex=0, sidVoice=0),
            lambda manifest, frames: frames[0].pop(),
        ):
            manifest, observer, frames = self.dual_fixture()
            change(manifest, frames)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "layout"):
                native_song.verify_driver_events(manifest, observer, frames)

    def test_dual_frame_reconstruction_keeps_register_banks_independent(self):
        writes = [dict(phase="init", tick=None, address=0xd438, value=15), dict(phase="play", tick=0, address=0xd400, value=12), dict(phase="play", tick=1, address=0xd420, value=34)]
        frames = native_song.frame_states(writes, 3, (0xd400, 0xd420))
        self.assertEqual([(state[0], state[25], state[49]) for state in frames], [(12, 0, 15), (12, 34, 15), (12, 34, 15)])
        with self.assertRaisesRegex(ValueError, "register"):
            native_song.frame_states([dict(phase="init", tick=None, address=0xd419, value=1)], 1, (0xd400, 0xd420))

    def test_observer_maps_second_sid_channels_without_aliasing_first_chip(self):
        names = ("CHNOTEC", "CURPTN", "STRTSND", "DPITCH", "CURINS", "INIPTN", "SEQPOS", "SEQFXL2")
        labels = {"extraPlayer:player:" + name: 0x2000 + index * 64 for index, name in enumerate(names)}
        labels["PLAYERZP"] = 0xfe
        memory = SimpleNamespace(phase="play", tick=1, data=bytearray(65536))
        for voice in range(6):
            memory.data[labels["extraPlayer:player:DPITCH"] + voice * 7] = 40 + voice
            memory.data[labels["extraPlayer:player:CURINS"] + voice * 7] = voice + 1
        observer = native_song.NativeObserver(labels, 2)
        for voice in range(6):
            observer(SimpleNamespace(pc=labels["extraPlayer:player:STRTSND"], x=voice * 7), memory)
        self.assertEqual([entry["nativeNote"] for entry in observer.starts], list(range(40, 46)))
        self.assertEqual([entry["voice"] for entry in observer.starts], list(range(6)))
        with self.assertRaisesRegex(ValueError, "channel layout"):
            native_song.NativeObserver(labels)(SimpleNamespace(pc=labels["extraPlayer:player:STRTSND"], x=21), memory)

    def test_stereo_pcm_requires_energy_in_each_chip_channel_and_exact_frame_count(self):
        pcm = {"sampleRate": 44100, "channels": 2, "frames": 88200, "clippedSamples": 0, "acRms": 100, "perChannel": [{"acRms": 50}, {"acRms": 100}]}
        native_song.verify_render(pcm, 2, 2)
        for change in (
            lambda pcm: pcm["perChannel"][1].update(acRms=0),
            lambda pcm: pcm.update(frames=176400),
            lambda pcm: pcm.update(channels=1),
            lambda pcm: pcm.update(clippedSamples=1),
        ):
            changed = copy.deepcopy(pcm)
            change(changed)
            with self.subTest(change=change), self.assertRaises(ValueError):
                native_song.verify_render(changed, 2, 2)

    def test_dual_metadata_requires_explicit_ordered_chips(self):
        with self.assertRaisesRegex(ValueError, "layout"):
            native_song.sid_layout({"sidCount": 2})
        self.assertEqual(native_song.sid_layout({}), [{"baseAddress": 0xd400, "model": "MOS8580"}])

    def test_checks_every_note_cell_note_start_pattern_and_terminal_stop(self):
        manifest, observer, frames = fixture()
        report = native_song.verify_driver_events(manifest, observer, frames)
        self.assertEqual(report["noteCounts"], [2, 1, 0])
        self.assertEqual(report["lastNotes"][0]["nativeNote"], 62)
        self.assertEqual(report["stopTicks"], [5, 5, 5])
        self.assertTrue(report["postStopGatesAndVolumeClear"])
        self.assertEqual(report["criticalNotes"][0]["midi"], 72)
        self.assertNotIn("audiblePitchVerified", report)

    def test_rejects_missing_wrong_extra_and_mistimed_cells_on_any_voice(self):
        for change in (
            lambda observer: observer.cells.pop(4),
            lambda observer: observer.cells[4].update(noteCode=50),
            lambda observer: observer.cells[4].update(tick=2),
            lambda observer: observer.cells.append(dict(observer.cells[4], tick=7)),
        ):
            manifest, observer, frames = fixture()
            change(observer)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "cell consumption"):
                native_song.verify_driver_events(manifest, observer, frames)

    def test_rejects_a_fetched_note_that_never_starts_or_uses_the_wrong_instrument(self):
        for change in (lambda observer: observer.starts.pop(), lambda observer: observer.starts[-1].update(instrument=1)):
            manifest, observer, frames = fixture()
            change(observer)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "discrete note start"):
                native_song.verify_driver_events(manifest, observer, frames)

    def test_rejects_missing_pattern_completion_wrong_stop_and_a_loop(self):
        for change in (
            lambda observer: observer.sequence_reads.pop(0),
            lambda observer: observer.sequence_reads[-1].update(tick=4),
            lambda observer: observer.sequence_reads.append({"voice": 0, "tick": 6, "entry": 1}),
        ):
            manifest, observer, frames = fixture()
            change(observer)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "sequence completion"):
                native_song.verify_driver_events(manifest, observer, frames)

    def test_only_exact_terminal_off_rereads_are_classified_after_the_declared_fe_stop(self):
        manifest, observer, frames = fixture()
        terminal = next(cell for cell in observer.cells if cell["voice"] == 0 and cell["tick"] == 5)
        observer.cells.extend([dict(terminal, tick=6), dict(terminal, tick=7)])
        report = native_song.verify_driver_events(manifest, observer, frames)
        self.assertEqual(report["postStopOffReads"], [2, 0, 0])
        for field, value in (("pattern", 2), ("byteOffset", 8), ("noteCode", 61), ("instrument", 1), ("tick", 5)):
            changed = copy.deepcopy(observer)
            changed.cells[-1][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "cell consumption"):
                native_song.verify_driver_events(manifest, changed, frames)

    def test_sequence_volume_commands_clear_volume_on_the_same_proven_stop_call(self):
        manifest, observer, frames = fixture()
        for voice, part in enumerate(manifest["voices"]):
            part["expectedSequenceEnding"].insert(0, {"tick": 5, "entry": 160})
            observer.sequence_reads.insert(3, {"voice": voice, "tick": 5, "entry": 160})
        report = native_song.verify_driver_events(manifest, observer, frames)
        self.assertEqual(report["stopVolumeClearTick"], 5)
        manifest["stopVolumeClearTick"] = 6
        frames[5][24] = 15
        with self.assertRaisesRegex(ValueError, "volume clear tick"):
            native_song.verify_driver_events(manifest, observer, frames)

    def test_terminal_off_rereads_do_not_mask_a_new_discrete_sound_start(self):
        manifest, observer, frames = fixture()
        terminal = next(cell for cell in observer.cells if cell["voice"] == 0 and cell["tick"] == 5)
        observer.cells.append(dict(terminal, tick=6))
        observer.starts.append({"voice": 0, "tick": 6, "nativeNote": 32, "instrument": 1})
        with self.assertRaisesRegex(ValueError, "discrete note start"):
            native_song.verify_driver_events(manifest, observer, frames)

    def test_only_declared_volume_zero_rereads_are_classified_after_fe(self):
        manifest, observer, frames = fixture()
        for voice, part in enumerate(manifest["voices"]):
            part["expectedSequenceEnding"].insert(0, {"tick": 5, "entry": 160})
            observer.sequence_reads.insert(3, {"voice": voice, "tick": 5, "entry": 160})
            observer.sequence_reads.append({"voice": voice, "tick": 6, "entry": 160})
        report = native_song.verify_driver_events(manifest, observer, frames)
        self.assertEqual(report["postStopVolumeReads"], [1, 1, 1])
        for tick, entry in ((5, 160), (6, 161), (6, 1)):
            changed = copy.deepcopy(observer)
            changed.sequence_reads[-1].update(tick=tick, entry=entry)
            with self.subTest(tick=tick, entry=entry), self.assertRaisesRegex(ValueError, "sequence completion"):
                native_song.verify_driver_events(manifest, changed, frames)

    def test_rejects_open_gates_or_volume_at_or_after_stop(self):
        for tick, register in ((5, 4), (6, 11), (7, 18), (5, 24)):
            manifest, observer, frames = fixture()
            frames[tick][register] = 1
            with self.subTest(tick=tick, register=register), self.assertRaisesRegex(ValueError, "post-stop"):
                native_song.verify_driver_events(manifest, observer, frames)

    def test_critical_short_notes_require_full_pitch_and_an_active_pitched_waveform(self):
        for change in (
            lambda frames: frames[1].__setitem__(0, 0),
            lambda frames: frames[1].__setitem__(4, 0x09),
            lambda frames: frames[1].__setitem__(4, 0x10),
            lambda frames: frames[1].__setitem__(4, 0x81),
        ):
            manifest, observer, frames = fixture()
            change(frames)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "critical short note"):
                native_song.verify_driver_events(manifest, observer, frames)

    def test_note_start_check_adds_the_instrument_octave_shift_to_the_written_note(self):
        manifest, observer, frames = fixture()
        manifest["voices"][0]["notes"][1]["octaveShiftSemitones"] = -12
        # The driver's DPITCH is the written note plus the instrument's shift.
        observer.starts[1]["nativeNote"] = 62 - 12
        self.assertEqual(native_song.verify_driver_events(manifest, observer, frames)["noteCounts"], [2, 1, 0])
        observer.starts[1]["nativeNote"] = 62
        with self.assertRaisesRegex(ValueError, "discrete note start"):
            native_song.verify_driver_events(manifest, observer, frames)

    def test_critical_note_pitch_target_follows_the_shifted_sounding_pitch(self):
        manifest, observer, frames = fixture()
        manifest["criticalNotes"][0]["octaveShiftSemitones"] = -12
        with self.assertRaisesRegex(ValueError, "critical short note"):
            native_song.verify_driver_events(manifest, observer, frames)
        word = round(440 * 2 ** ((60 - 69) / 12) * 2**24 / manifest["clockHz"])
        frames[1][0:2] = [word & 255, word >> 8]
        report = native_song.verify_driver_events(manifest, observer, frames)
        self.assertEqual(report["criticalNotes"][0]["expectedFrequencyWord"], word)

    def test_frame_reconstruction_applies_init_and_retains_exact_last_writes(self):
        writes = [{"phase": "init", "tick": None, "address": 0xd418, "value": 15}, {"phase": "play", "tick": 1, "address": 0xd400, "value": 10}, {"phase": "play", "tick": 1, "address": 0xd400, "value": 11}]
        frames = native_song.frame_states(writes, 3)
        self.assertEqual([state[0] for state in frames], [0, 11, 11])
        self.assertEqual([state[24] for state in frames], [15, 15, 15])

    def test_excerpt_uses_exact_frames_and_preserves_the_original(self):
        from array import array
        import wave
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "full.wav"
            excerpt = Path(directory) / "excerpt.wav"
            with wave.open(str(original), "wb") as output:
                output.setparams((1, 2, 8, 0, "NONE", "not compressed"))
                values = array("h", range(24))
                if sys.byteorder != "little":
                    values.byteswap()
                output.writeframes(values.tobytes())
            before = original.read_bytes()
            report = native_song.write_excerpt(original, excerpt, 1, 1.5)
            self.assertEqual(report["sourceStartFrame"], 8)
            self.assertEqual(report["frames"], 12)
            self.assertEqual(original.read_bytes(), before)
            with wave.open(str(excerpt), "rb") as source:
                values = array("h", source.readframes(source.getnframes()))
                if sys.byteorder != "little":
                    values.byteswap()
                self.assertEqual(list(values), list(range(8, 20)))

    def test_failed_schedule_guard_retains_raw_driver_evidence(self):
        manifest, observer, _ = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            native, sid = root / "native.swm", root / "song.sid"
            native.write_bytes(b"fixture native source")
            sid.write_bytes(b"fixture SID")
            manifest.update(nativePath=str(native), nativeSha256=hashlib.sha256(native.read_bytes()).hexdigest())
            label_bytes = b"al fe .PLAYERZP\n"
            exported = {"sourceSha256": manifest["nativeSha256"], "sid": str(sid), "sidSha256": hashlib.sha256(sid.read_bytes()).hexdigest(), "player": "Extra", "loadAddress": 0x1000, "initAddress": 0x1000, "playAddress": 0x1003, "build": {"labelsSha256": hashlib.sha256(label_bytes).hexdigest()}}
            manifest_path, export_path = root / "conversion.json", root / "export.json"
            manifest_path.write_text(json.dumps(manifest))
            export_path.write_text(json.dumps(exported))
            original_read = Path.read_bytes

            def read_bytes(path):
                return label_bytes if path.name == "exporter.labels" else original_read(path)

            prefix = root / "result"
            with patch.object(Path, "read_bytes", read_bytes), patch.object(native_song, "NativeObserver", return_value=observer), patch.object(native_song, "audit_psid", return_value=({"playCalls": 8}, [])), patch.object(native_song, "verify_driver_events", side_effect=ValueError("schedule rejected")), self.assertRaisesRegex(ValueError, "schedule rejected"):
                native_song.audit_native(manifest_path, export_path, prefix, 8)
            for suffix in (".audit.json", ".writes.json", ".frames.json", ".native-events.json"):
                self.assertTrue(Path(str(prefix) + suffix).exists(), suffix)
            self.assertFalse(Path(str(prefix) + ".schedule.json").exists())

    def test_invalid_excerpt_options_fail_before_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for start, seconds in ((float("nan"), 1), (-1, 1), (0, 0), (0, float("inf"))):
                with self.subTest(start=start, seconds=seconds), self.assertRaisesRegex(ValueError, "Excerpt"):
                    native_song.run_song(root / "recipe.json", root / "output", excerpt_start=start, excerpt_seconds=seconds)
                self.assertFalse((root / "output").exists())

    def test_audit_deadline_can_cover_a_longer_complete_schedule(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recipe, renderer = root / "recipe.json", root / "renderer"
            recipe.write_text("fixture")
            renderer.write_bytes(b"renderer fixture")
            manifest = {"nativePath": str(root / "song.swm"), "title": "Fixture", "author": "Fixture", "released": "2026", "totalTicks": 10, "ticksPerSecond": 50}
            converter = SimpleNamespace(arrange=lambda *args, **kwargs: manifest)
            exporter = SimpleNamespace(export_module=lambda *args, **kwargs: {"sid": str(root / "song.sid")})
            for deadline in (120, 300):
                kwargs = {} if deadline == 120 else {"audit_timeout_seconds": deadline}
                with patch.object(native_song, "load_script", side_effect=[converter, exporter]), patch.object(native_song.subprocess, "run", side_effect=subprocess.TimeoutExpired("audit", deadline)) as run, patch("builtins.print"), self.assertRaises(subprocess.TimeoutExpired):
                    native_song.run_song(recipe, root / str(deadline), renderer, excerpt_seconds=0.5, **kwargs)
                self.assertEqual(deadline, run.call_args.kwargs["timeout"])
                self.assertIn("--ticks", run.call_args.args[0])

    def test_invalid_audit_deadline_fails_before_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for deadline in (0, -1, float("nan"), float("inf")):
                with self.subTest(deadline=deadline), self.assertRaisesRegex(ValueError, "Audit deadline"):
                    native_song.run_song(root / "recipe.json", root / "output", audit_timeout_seconds=deadline)
                self.assertFalse((root / "output").exists())

    def test_failed_pcm_guard_retains_renderer_command_and_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recipe, renderer = root / "recipe.json", root / "renderer"
            recipe.write_text("fixture")
            renderer.write_bytes(b"renderer fixture")
            manifest = {"nativePath": str(root / "song.swm"), "title": "Fixture", "author": "Fixture", "released": "2026", "totalTicks": 10, "ticksPerSecond": 50}
            converter = SimpleNamespace(arrange=lambda *args, **kwargs: manifest)
            exporter = SimpleNamespace(export_module=lambda *args, **kwargs: {"sid": str(root / "song.sid")})
            completed = subprocess.CompletedProcess([], 0, "renderer identity", "renderer warning")
            invalid_pcm = {"sampleRate": 44100, "channels": 1, "frames": 1}
            output = root / "output"
            with patch.object(native_song, "load_script", side_effect=[converter, exporter]), patch.object(native_song.subprocess, "run", return_value=completed), patch.object(native_song, "inspect_wav", return_value=invalid_pcm), patch("builtins.print"), self.assertRaisesRegex(ValueError, "complete mono"):
                native_song.run_song(recipe, output, renderer, excerpt_seconds=0.5)
            report = json.loads((output / "native-song.render.json").read_text())
            self.assertEqual(report["stdout"], "renderer identity")
            self.assertEqual(report["stderr"], "renderer warning")
            self.assertEqual(report["returnCode"], 0)
            self.assertEqual(report["command"][0], str(renderer.resolve()))
            self.assertFalse((output / "verification.json").exists())


if __name__ == "__main__":
    unittest.main()
