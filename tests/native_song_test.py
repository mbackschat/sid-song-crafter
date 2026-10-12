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

    def test_failed_pcm_guard_retains_renderer_command_and_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recipe, renderer = root / "recipe.json", root / "renderer"
            recipe.write_text("fixture")
            renderer.write_bytes(b"renderer fixture")
            manifest = {"nativePath": str(root / "song.swm"), "title": "Fixture", "author": "Fixture", "released": "2026", "totalTicks": 10, "ticksPerSecond": 50}
            converter = SimpleNamespace(arrange=lambda *args: manifest)
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
