import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("drax_study", ROOT / "scripts/study-drax-references.py")
study = importlib.util.module_from_spec(spec)


def frequency(midi):
    return round(440 * 2 ** ((midi - 69) / 12) * 2**24 / study.PAL_CLOCK)


def reference_frames():
    frames = [[0] * 25 for _ in range(6000)]
    for tick, midi in zip((2, 6, 10, 14, 18, 22), (76, 74, 72, 76, 74, 72)):
        word = frequency(midi)
        frames[tick - 1][11] = 0x09
        frames[tick][7:9] = [word & 255, word >> 8]
        frames[tick][11] = 0x41
    return frames


def candidate_fixture():
    events = [{"startBeat": index / 4, "durationBeats": 0.25, "midi": midi} for index, midi in enumerate((76, 74, 79))]
    score = {"quarterBpm": 72, "voices": [{"name": "melody", "events": events}]}
    notes = [dict(event, eventIndex=index, startTick=index * 4) for index, event in enumerate(events)]
    manifest = {"format": "sidwizard-arrangement-manifest-v1", "frameSpeed": 1, "rowTicks": 1, "clockHz": study.PAL_CLOCK, "ticksPerSecond": study.PAL_CLOCK / study.CYCLES_PER_FRAME, "voices": [{"name": "melody", "notes": notes}]}
    frames = [[0] * 25 for _ in range(6000)]
    for note in notes:
        tick, word = note["startTick"] + 1, frequency(note["midi"])
        frames[tick][0:2] = [word & 255, word >> 8]
        frames[tick][4] = 0x21
    return manifest, score, frames


class DraxReferenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec.loader.exec_module(study)

    def test_reference_identity_rejects_changed_or_unknown_inputs(self):
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            study.verify_reference("fuer-elise", b"different SID")
        with self.assertRaisesRegex(ValueError, "Unknown reference"):
            study.verify_reference("another-song", b"different SID")
        source = ROOT / "songs/fuer-elise.json"
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), study.SOURCE_SCORE_SHA256)

    def test_diagnostic_adapter_accepts_only_zero_paddle_writes_during_init(self):
        memory = study.FlashdanceDiagnosticMemory()
        for address in (0xd419, 0xd41a):
            memory[address] = 0
        self.assertEqual([row["address"] for row in memory.ignored_writes], [0xd419, 0xd41a])
        memory[0xd404] = 0x41
        self.assertEqual(memory.writes[-1]["address"], 0xd404)
        for address in (0xd419, 0xd41a, 0xd41b, 0xdc00):
            with self.subTest(address=address), self.assertRaises(ValueError):
                memory[address] = 1
        with self.assertRaisesRegex(ValueError, "Unsupported I/O"):
            memory[0xd41b] = 0
        memory.phase = "play"
        with self.assertRaises(ValueError):
            memory[0xd419] = 0
        with self.assertRaisesRegex(ValueError, "Unsupported I/O read"):
            memory[0xd419]
        with self.assertRaisesRegex(ValueError, "Unsupported I/O write"):
            study.psid_audit.AuditMemory()[0xd419] = 0

    def test_diagnostic_execution_does_not_change_the_production_auditor(self):
        header = bytearray(124)
        header[:4] = b"PSID"
        for offset, value in ((4, 2), (6, 124), (8, 0x1000), (10, 0x1000), (12, 0x1009), (14, 1), (16, 1), (118, 0x14)):
            header[offset:offset + 2] = value.to_bytes(2, "big")
        data = bytes(header) + bytes.fromhex("a9008d19d48d1ad46060")
        original = study.psid_audit.AuditMemory
        with patch.object(study, "verify_reference"):
            report, writes, ignored = study.audit_reference("flashdance", data, 6000)
        self.assertEqual(report["playCalls"], 6000)
        self.assertEqual(len(ignored), 2)
        self.assertEqual(writes, [])
        self.assertIs(study.psid_audit.AuditMemory, original)
        with self.assertRaisesRegex(ValueError, "Unsupported I/O write"):
            study.psid_audit.audit_psid(data, 6000)

    def test_study_claims_require_exactly_6000_complete_single_sid_frames(self):
        for frames in ([[0] * 25] * 5999, [[0] * 25] * 6001, [[0] * 50] * 6000):
            with self.subTest(size=len(frames)), self.assertRaisesRegex(ValueError, "6000|25-register"):
                study.melody_events(frames)

    def test_reference_extractor_ignores_noise_gate_off_and_incomplete_pitch(self):
        frames = reference_frames()
        frames[2][11] = 0x81
        frames[6][11] = 0x40
        frames[10][7:9] = [0, 0]
        events = study.melody_events(frames)
        self.assertEqual([(event["tick"], event["midi"]) for event in events], [(14, 76), (18, 74), (22, 72)])

    def test_cycle_detection_requires_matching_pitches_and_all_tick_offsets(self):
        events = study.melody_events(reference_frames())
        cycle = study.melody_cycle(events)
        self.assertEqual((cycle["notes"], cycle["ticks"], cycle["completeCycles"]), (3, 12, 2))
        events[-1]["tick"] += 1
        self.assertIsNone(study.melody_cycle(events))

    def test_comparison_reports_arrangement_difference_after_actual_pitch_checks(self):
        manifest, score, frames = candidate_fixture()
        result = study.compare_fuer_elise(reference_frames(), frames, manifest, score)
        self.assertEqual(result["consecutiveOpeningPitchMatches"], 2)
        self.assertEqual(result["firstPositionalDifference"]["source"]["midi"], 79)
        self.assertEqual(result["firstPositionalDifference"]["reference"]["midi"], 72)
        self.assertEqual(result["nativeCoveredMelodyNotes"], 3)
        self.assertEqual(result["referenceOpeningSixteenthTicks"], [4])
        self.assertEqual(result["nativeQuarterBpm"], 72)
        self.assertEqual(result["candidateProfile"]["bodyTickOffset"], 1)
        self.assertIn("another study profile", result["candidateProfile"]["requirements"])
        frames[9][0] ^= 128
        with self.assertRaisesRegex(ValueError, "body pitch"):
            study.compare_fuer_elise(reference_frames(), frames, manifest, score)

    def test_candidate_body_requires_gate_pitched_waveform_and_no_test_or_noise(self):
        for control in (0x20, 0x29, 0x81, 0xa1, 0x01):
            manifest, score, frames = candidate_fixture()
            frames[1][4] = control
            with self.subTest(control=control), self.assertRaisesRegex(ValueError, "body control"):
                study.compare_fuer_elise(reference_frames(), frames, manifest, score)

    def test_candidate_manifest_cannot_change_source_notes_or_assume_timing(self):
        for mutate in (
            lambda manifest: manifest["voices"][0]["notes"][0].update(midi=75),
            lambda manifest: manifest["voices"][0]["notes"].pop(),
            lambda manifest: manifest.update(rowTicks=2),
            lambda manifest: manifest.pop("clockHz"),
        ):
            manifest, score, frames = candidate_fixture()
            mutate(manifest)
            with self.subTest(mutate=mutate), self.assertRaisesRegex(ValueError, "source|timing"):
                study.compare_fuer_elise(reference_frames(), frames, manifest, score)

    def test_voice_summary_preserves_pwm_filter_and_control_couplings(self):
        frames = [[0] * 25 for _ in range(6000)]
        frames[2][11] = 0x09
        frames[3][7:14] = [0x11, 0x27, 0x70, 0xfd, 0x11, 3, 0x3c]
        frames[3][21:25] = [7, 160, 0xf1, 0x1f]
        summary = study.sound_design("flashdance", frames)
        sample = summary["voices"][1]["firstAttack"][1]
        self.assertEqual((sample["tick"], sample["pulseWidth"], sample["frequencyWord"]), (3, 3440, 10001))
        self.assertEqual((sample["filterCutoff"], sample["filterRoutingResonance"], sample["filterModeVolume"]), (1287, 0xf1, 0x1f))
        self.assertEqual(summary["voices"][1]["role"], "melody")

    def test_landmark_search_reports_the_observed_matches_not_expected_absence(self):
        score = json.loads((ROOT / "songs/fuer-elise.json").read_text())
        part = score["voices"][0]["events"]
        index = next(index for index, note in enumerate(part) if note["startBeat"] >= 66.5)
        events = [dict(tick=index * 3, midi=note["midi"]) for index, note in enumerate(part[index:index + 10])]
        landmarks = study.episode_landmarks(events, score)
        self.assertEqual(landmarks["F-major"]["referenceMatchTicks"], [0])
        self.assertEqual(landmarks["repeated-bass"]["referenceMatchTicks"], [])

    def test_existing_output_is_rejected_before_reading_or_auditing_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "existing"
            output.mkdir()
            marker = output / "source.sid"
            marker.write_bytes(b"preserve")
            with patch.object(study, "audit_reference") as audit, self.assertRaisesRegex(ValueError, "fresh"):
                study.run_study(marker, marker, marker, marker, marker, output, 6000)
            audit.assert_not_called()
            self.assertEqual(marker.read_bytes(), b"preserve")


if __name__ == "__main__":
    unittest.main()
