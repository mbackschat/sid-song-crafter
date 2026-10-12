import json
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("chord_programs", ROOT / "scripts/verify-chord-programs.py")
chords = importlib.util.module_from_spec(spec)


def fixture():
    manifest = {"format": "sidwizard-arrangement-manifest-v1", "clockHz": chords.PAL_CLOCK, "rowTicks": 1, "frameSpeed": 1, "stopTick": 119, "stopVolumeClearTick": 119, "voices": [{"name": "melody", "notes": []}, {"name": "bass", "notes": []}, {"name": "harmony", "notes": [{"instrumentId": "minor", "midi": 57, "startTick": 0, "nativeGateOffTick": 30}, {"instrumentId": "major", "midi": 56, "startTick": 60, "nativeGateOffTick": 90}]}]}
    profiles = {"minor": [0, 3, 7], "major": [0, 3, 8]}
    frames = [[0] * 25 for _ in range(120)]
    for index, note in enumerate(manifest["voices"][2]["notes"]):
        start = note["startTick"]
        end = 60 if index == 0 else 120
        frames[start][18] = 0x09
        for tick in range(start + 1, end):
            interval = profiles[note["instrumentId"]][((tick - start - 1) // 2) % 3]
            word = round(440 * 2 ** ((note["midi"] + interval - 69) / 12) * 2**24 / chords.PAL_CLOCK)
            frames[tick][14:16] = [word & 255, word >> 8]
            frames[tick][18] = 0x51 if tick < note["nativeGateOffTick"] else 0x50
    return manifest, frames, profiles


class ChordProgramsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec.loader.exec_module(chords)

    def test_every_held_and_release_cycle_is_checked_for_both_voicings(self):
        manifest, frames, profiles = fixture()
        result = chords.verify_chords(manifest, frames, profiles, waveform=0x51, dwell=2)
        self.assertEqual(result["checkedNotes"], 2)
        self.assertEqual([note["completeHeldCycles"] for note in result["notes"]], [4, 4])
        self.assertEqual([note["releaseAndRestFrames"] for note in result["notes"]], [30, 30])

    def test_delay_row_loop_failure_is_detected_in_minor_and_major(self):
        for note_index in (0, 1):
            manifest, frames, profiles = fixture()
            note = manifest["voices"][2]["notes"][note_index]
            end = 60 if note_index == 0 else 120
            for tick in range(note["startTick"] + 8, end):
                frames[tick][18] &= 1
            with self.subTest(voicing=note["instrumentId"]), self.assertRaisesRegex(ValueError, note["instrumentId"] + ".*waveform"):
                chords.verify_chords(manifest, frames, profiles, waveform=0x51, dwell=2)

    def test_correct_pitch_set_with_wrong_order_or_dwell_is_rejected(self):
        for tick in (3, 14, 67, 103):
            manifest, frames, profiles = fixture()
            frames[tick][14:16] = frames[tick + 2][14:16]
            with self.subTest(tick=tick), self.assertRaisesRegex(ValueError, "pitch"):
                chords.verify_chords(manifest, frames, profiles, waveform=0x51, dwell=2)

    def test_release_and_late_rest_cannot_reopen_gate(self):
        for tick in (30, 58, 90, 119):
            manifest, frames, profiles = fixture()
            frames[tick][18] |= 1
            with self.subTest(tick=tick), self.assertRaisesRegex(ValueError, "gate"):
                chords.verify_chords(manifest, frames, profiles, waveform=0x51, dwell=2)

    def test_release_must_retain_waveform_and_pitch_before_stop(self):
        for mutate in (lambda frames: frames[35].__setitem__(18, 0), lambda frames: frames[95].__setitem__(14, 0)):
            manifest, frames, profiles = fixture()
            mutate(frames)
            with self.assertRaisesRegex(ValueError, "waveform|pitch"):
                chords.verify_chords(manifest, frames, profiles, waveform=0x51, dwell=2)

    def test_short_or_unobserved_hold_is_not_claimed_as_a_sustained_loop(self):
        manifest, frames, profiles = fixture()
        manifest["voices"][2]["notes"][0]["nativeGateOffTick"] = 10
        with self.assertRaisesRegex(ValueError, "two complete"):
            chords.verify_chords(manifest, frames, profiles, waveform=0x51, dwell=2)
        manifest, frames, profiles = fixture()
        with self.assertRaisesRegex(ValueError, "complete|stop"):
            chords.verify_chords(manifest, frames[:100], profiles, waveform=0x51, dwell=2)

    def test_unknown_profile_and_unsupported_timing_fail_explicitly(self):
        for change in (lambda manifest, profiles: profiles.update(missing=[0, 4, 7]), lambda manifest, profiles: manifest.update(rowTicks=2)):
            manifest, frames, profiles = fixture()
            change(manifest, profiles)
            with self.assertRaisesRegex(ValueError, "missing|timing"):
                chords.verify_chords(manifest, frames, profiles, waveform=0x51, dwell=2)

    def test_post_stop_master_volume_must_be_zero(self):
        manifest, frames, profiles = fixture()
        frames[119][24] = 1
        with self.assertRaisesRegex(ValueError, "Master volume"):
            chords.verify_chords(manifest, frames, profiles, waveform=0x51, dwell=2)

    @unittest.skipUnless((ROOT / ".tools/sid-wizard-exporter/exporter.labels").is_file() and (ROOT / ".local/bin/render-sid").is_file(), "Pinned SID-Wizard exporter and renderer required")
    def test_native_delay_jump_clears_both_voicings_and_explicit_anchor_sustains_release(self):
        native_spec = importlib.util.spec_from_file_location("chord_native_fixture", ROOT / "scripts/native-song.py")
        native = importlib.util.module_from_spec(native_spec)
        native_spec.loader.exec_module(native)
        score = {"title": "Original chord loop fixture", "composer": "Original test notes", "quarterBpm": 72, "totalBeats": 4, "tailTicks": 25, "volume": 15, "voices": [{"name": "melody", "events": []}, {"name": "bass", "events": []}, {"name": "harmony", "events": [{"startBeat": 0, "durationBeats": 1.5, "midi": 57}, {"startBeat": 2, "durationBeats": 1.5, "midi": 56}]}]}
        profiles = {"minor": [0, 3, 7], "major": [0, 3, 8]}
        with tempfile.TemporaryDirectory() as directory, patch("builtins.print"):
            folder = Path(directory)
            (folder / "score.json").write_text(json.dumps(score))
            for corrected in (False, True):
                instruments = {}
                for identity, pitches in profiles.items():
                    wave = [["51", "00", "00"], ["01", "03", "00"], ["01", f"{pitches[2]:02x}", "00"], ["01", "00", "00"], {"jump": 1}]
                    if corrected:
                        wave = [["51", f"{pitch:02x}", "00"] for pitch in pitches for _ in range(2)] + [{"jump": 0}]
                    instruments[identity] = {"name": identity.upper(), "control": "0a", "hard_restart_adsr": "0f00", "adsr": "0349", "frame1": "09", "wave": wave, "pulse": [["86", "00", "00"]], "filter": []}
                recipe = {"format": "sidwizard-arrangement-v1", "score": "score.json", "title": "Original chord loop fixture", "author": "Original test material", "authorinfo": "ORIGINAL:CHORD LOOP FIXTURE", "released": "2026", "timingPolicy": "retain-full-pitch", "instruments": instruments, "sections": [{"name": "Minor hold", "startBeat": 0, "endBeat": 2, "voices": {"melody": "minor", "bass": "minor", "harmony": "minor"}}, {"name": "Major hold", "startBeat": 2, "endBeat": 4, "voices": {"melody": "major", "bass": "major", "harmony": "major"}}]}
                name = "corrected" if corrected else "old"
                recipe_path = folder / f"{name}.json"
                recipe_path.write_text(json.dumps(recipe))
                output = folder / name
                native.run_song(recipe_path, output, excerpt_seconds=1)
                manifest = json.loads((output / f"conversion/{name}.native.json").read_text())
                frames = json.loads((output / "native-song.frames.json").read_text())
                if corrected:
                    result = chords.verify_chords(manifest, frames, profiles, waveform=0x51, dwell=2)
                    self.assertEqual(result["checkedNotes"], 2)
                    self.assertTrue(all(note["completeHeldCycles"] >= 8 for note in result["notes"]))
                    self.assertTrue(all(note["releaseAndRestFrames"] >= 20 for note in result["notes"]))
                else:
                    notes = manifest["voices"][2]["notes"]
                    for index, note in enumerate(notes):
                        start = note["startTick"]
                        end = notes[index + 1]["startTick"] if index + 1 < len(notes) else len(frames)
                        with self.subTest(voicing=note["instrumentId"]):
                            self.assertTrue(all(frames[tick][18] == 0x51 for tick in range(start + 1, start + 8)))
                            self.assertEqual(frames[start + 8][18], 0x01)
                            self.assertTrue(all(frames[tick][18] & 0xf0 == 0 for tick in range(start + 8, end)))


if __name__ == "__main__":
    unittest.main()
