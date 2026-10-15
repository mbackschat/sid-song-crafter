from array import array
import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("axel_full_rhythm", ROOT / "scripts/studies/axel-f/prepare-full-rhythm.py")
FULL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FULL)


class AxelFullRhythmTest(unittest.TestCase):
    def setUp(self):
        self.palette = dict(clock="pal", sidCount=1, sidModel="MOS8580", score="score.json",
                            instruments={"lead": {}, "harmony": {}, "bass": {}},
                            sections=[dict(startBeat=a, endBeat=b, voices=dict(melody="lead", harmony="harmony", bass="bass"))
                                      for a, b in ((0, 4), (4, 8), (8, 12), (12, 16))])
        self.score = dict(totalBeats=16, quarterBpm=120, provenance=dict(sourceSha256="source"),
                          voices=[dict(name="melody", events=[dict(startBeat=0, durationBeats=16, midi=65)]),
                                  dict(name="harmony", events=[dict(startBeat=6, durationBeats=1, midi=60), dict(startBeat=14, durationBeats=1, midi=60)]),
                                  dict(name="bass", events=[dict(startBeat=0, durationBeats=16, midi=41)])])
        self.common = dict(quarterBpm=120, provenance=dict(sourceSha256="source"),
                           parts=[dict(id="drums", events=[dict(startBeat=[start, 1], durationBeats=[1, 8], midi=70)
                                                           for start in (4, 6, 12, 14)])])
        self.original = dict(instrument=dict(name="MARNOISE", control="0a", hard_restart_adsr="0f00", adsr="1400",
                                            frame1="09", wave=[["81", "c9", "00"]], pulse=[], filter=[]))
        self.balance = dict(adsr="1300", previousConfigurationFingerprint=FULL.fingerprint(self.original))
        self.config = dict(format="axel-f-full-rhythm-v1", sourceSha256="source", sourceBeatOffset=4,
                           commonScoreFingerprint=FULL.fingerprint(self.common),
                           baseScoreFingerprint=FULL.fingerprint(self.score), basePaletteFingerprint=FULL.fingerprint(self.palette),
                           originalRhythmFingerprint=FULL.fingerprint(self.original), acceptedBalanceFingerprint=FULL.fingerprint(self.balance),
                           sourceMidi=70, expectedTonalCounts=[1, 2, 1], expectedRhythmOnsets=4,
                           windows=[dict(startBeat=0, endBeat=4, expectedOnsets=2), dict(startBeat=8, endBeat=12, expectedOnsets=2)])

    def prepare(self):
        return FULL.prepare(self.common, self.score, self.palette, self.original, self.balance, self.config)

    def test_projects_source_events_without_changing_tonal_score_or_existing_instrument_ids(self):
        result = self.prepare()
        candidate = result["candidate-score.json"]
        self.assertEqual(self.score, result["baseline-score.json"])
        self.assertEqual(self.score["voices"][0], candidate["voices"][0])
        self.assertEqual(self.score["voices"][2], candidate["voices"][2])
        self.assertEqual([0, 2, 6, 8, 10, 14], [e["startBeat"] for e in candidate["voices"][1]["events"]])
        self.assertEqual(["lead", "harmony", "bass", "rhythm"], list(result["candidate.json"]["instruments"]))
        self.assertEqual("1300", result["candidate.json"]["instruments"]["rhythm"]["adsr"])
        self.assertEqual(4, len(result["adaptation.json"]["retainedSourceOrigins"]))
        self.assertEqual(["rhythm", "harmony", "rhythm", "harmony"],
                         [s["voices"]["harmony"] for s in result["candidate.json"]["sections"]])

    def test_rejects_occupied_windows_and_crossing_tonal_notes(self):
        self.score["voices"][1]["events"][0]["startBeat"] = 3
        self.score["voices"][1]["events"][0]["durationBeats"] = 2
        self.config["baseScoreFingerprint"] = FULL.fingerprint(self.score)
        with self.assertRaisesRegex(ValueError, "vacant"):
            self.prepare()

    def test_rejects_duplicate_overlapping_and_boundary_crossing_source_hits(self):
        for case in ("duplicate", "overlap", "boundary"):
            with self.subTest(case=case):
                self.setUp()
                events = self.common["parts"][0]["events"]
                if case == "duplicate":
                    events[1]["startBeat"] = [4, 1]
                else:
                    events[0 if case == "overlap" else 1]["durationBeats"] = [3, 1]
                self.config["commonScoreFingerprint"] = FULL.fingerprint(self.common)
                with self.assertRaises(ValueError):
                    self.prepare()

    def test_rejects_source_onset_drift_even_when_counts_and_window_membership_match(self):
        self.common["parts"][0]["events"][0]["startBeat"] = [5, 1]
        with self.assertRaises(ValueError):
            self.prepare()

    def test_rejects_changed_source_palette_or_accepted_noise_program(self):
        for case in ("source", "palette", "balance"):
            with self.subTest(case=case):
                self.setUp()
                if case == "source":
                    self.common["provenance"]["sourceSha256"] = "other"
                elif case == "palette":
                    self.palette["instruments"]["lead"] = {"adsr": "0000"}
                else:
                    self.balance["adsr"] = "1100"
                with self.assertRaises(ValueError):
                    self.prepare()

    def test_register_guard_limits_harmony_changes_to_noise_lifetime(self):
        previous = [[0] * 25 for _ in range(5)]
        candidate = copy.deepcopy(previous)
        candidate[1][12] = 0x13
        self.assertEqual([12], FULL.verify_frames(previous, candidate, [(1, 3)]))
        for tick, offset in ((0, 12), (3, 12), (2, 0), (2, 14), (2, 23), (2, 24)):
            with self.subTest(tick=tick, offset=offset):
                invalid = copy.deepcopy(candidate)
                invalid[tick][offset] = 1
                with self.assertRaises(ValueError):
                    FULL.verify_frames(previous, invalid, [(1, 3)])

    def test_native_schedule_guard_preserves_gate_pitch_and_instrument_identity(self):
        note = dict(eventIndex=0, startTick=0, durationTicks=4, gateOffTick=3, nativeGateOffTick=3, midi=60,
                    instrumentId="harmony", instrument=2, pattern=1, row=0, byteOffset=0)
        previous = [dict(notes=[]), dict(notes=[note]), dict(notes=[])]
        candidate = copy.deepcopy(previous)
        candidate[1]["notes"][0].update(eventIndex=8, pattern=9, row=2, byteOffset=6)
        candidate[1]["notes"].append(dict(note, instrumentId="rhythm", instrument=4, startTick=8))
        FULL.verify_tonal_schedules(previous, candidate)
        for key, value in (("nativeGateOffTick", 4), ("midi", 61), ("instrument", 3)):
            with self.subTest(key=key):
                invalid = copy.deepcopy(candidate)
                invalid[1]["notes"][0][key] = value
                with self.assertRaises(ValueError):
                    FULL.verify_tonal_schedules(previous, invalid)

    def test_rhythm_native_boundaries_are_checked_against_exact_source_beats(self):
        origin = dict(sourceStartBeat=[4, 1], sourceDurationBeats=[1, 8], arrangedStartBeat=0, durationBeats=0.125, midi=70)
        note = dict(startBeat=0, durationBeats=0.125, midi=70, startTick=0, sourceStartTick=0,
                    durationTicks=3, sourceDurationTicks=3, sourceGateOffTick=2)
        FULL.verify_rhythm_schedule(note, origin, 24, 70)
        for key, value in (("startTick", 1), ("sourceStartTick", 1), ("durationTicks", 4),
                           ("sourceDurationTicks", 4), ("sourceGateOffTick", 3), ("midi", 71)):
            with self.subTest(key=key):
                invalid = dict(note, **{key: value})
                with self.assertRaises(ValueError):
                    FULL.verify_rhythm_schedule(invalid, origin, 24, 70)

    def test_diagnostics_must_match_their_own_full_render_register_snapshots(self):
        FULL.verify_diagnostic_snapshots(b"baseline registers", b"baseline registers")
        for wrong in (b"", b"candidate registers"):
            with self.subTest(wrong=wrong):
                with self.assertRaisesRegex(ValueError, "diagnostic"):
                    FULL.verify_diagnostic_snapshots(b"baseline registers", wrong)

    def test_preserved_ordered_stores_allow_cycle_drift_and_noise_history_only(self):
        previous = [dict(phase="play", tick=tick, address=address, value=9, instructionStartCycle=10)
                    for tick, address in ((0, 0xd40b), (1, 0xd40b), (3, 0xd40b), (1, 0xd400))]
        candidate = copy.deepcopy(previous)
        for row in candidate:
            row["instructionStartCycle"] += 20
        candidate[1]["value"] = 0x81
        kept, difference = FULL.verify_ordered_writes(previous, candidate, [(1, 3)])
        self.assertEqual((3, 20), (kept, difference))
        for index in (0, 2, 3):
            with self.subTest(index=index):
                invalid = copy.deepcopy(candidate)
                invalid[index]["value"] = 0x80
                with self.assertRaises(ValueError):
                    FULL.verify_ordered_writes(previous, invalid, [(1, 3)])

    def test_noise_gate_follows_the_exact_contiguous_body_and_release_schedule(self):
        def states(controls):
            result = [[0] * 25 for _ in controls]
            for row, control in zip(result, controls):
                row[7], row[8], row[11], row[12] = 0x9c, 0x45, control, 0x13
            return result
        self.assertEqual(2, FULL.verify_noise_states(states([0x81, 0x81, 0x80, 0x80]), 10, 13, 17820))
        for controls in ([0x81, 0x81, 0x80, 0x81], [0x81, 0x80, 0x81, 0x80]):
            with self.subTest(controls=controls):
                with self.assertRaisesRegex(ValueError, "gate schedule"):
                    FULL.verify_noise_states(states(controls), 10, 13, 17820)

    def test_incoming_test_allows_only_retained_low_byte_until_exact_next_body(self):
        previous = [[0] * 25 for _ in range(5)]
        previous[2][7] = 1
        previous[3][7:14] = [1, 34, 0, 0, 9, 7, 52]
        previous[4][7:14] = [206, 34, 0, 0, 33, 7, 52]
        candidate = copy.deepcopy(previous)
        candidate[1][7:14] = candidate[2][7:14] = [157, 69, 0, 0, 128, 19, 0]
        candidate[3][7] = 157
        FULL.verify_frames(previous, candidate, [(1, 3)], [3])
        for tick, offset, value in ((3, 7, 158), (3, 8, 35), (3, 9, 1), (3, 10, 1),
                                    (3, 11, 0x81), (3, 12, 0x13), (3, 13, 0), (4, 7, 157), (4, 11, 9)):
            with self.subTest(tick=tick, offset=offset):
                invalid = copy.deepcopy(candidate)
                invalid[tick][offset] = value
                with self.assertRaises(ValueError):
                    FULL.verify_frames(previous, invalid, [(1, 3)], [3])

    def test_ordered_test_exception_accepts_only_the_validated_low_byte_pair(self):
        previous = [dict(phase="play", tick=3, address=0xd407, value=1, instructionStartCycle=10),
                    dict(phase="play", tick=3, address=0xd40b, value=9, instructionStartCycle=20),
                    dict(phase="play", tick=4, address=0xd407, value=206, instructionStartCycle=30)]
        candidate = copy.deepcopy(previous)
        candidate[0]["value"] = 157
        self.assertEqual((3, 0), FULL.verify_ordered_writes(previous, candidate, [], {3: (1, 157)}))
        for index, value in ((0, 158), (1, 0x81), (2, 157)):
            with self.subTest(index=index):
                invalid = copy.deepcopy(candidate)
                invalid[index]["value"] = value
                with self.assertRaises(ValueError):
                    FULL.verify_ordered_writes(previous, invalid, [], {3: (1, 157)})

    def test_handover_allows_earlier_release_but_rejects_immediate_or_final_residue(self):
        samples = array("h", [0] * 1000)
        for frame in range(850, 920):
            samples[frame] = 100 if frame % 2 else -100
        audio = FULL.BALANCE.Pcm16(1000, 1, 1000, samples, "")
        measurements = FULL.measure_handover(audio, 1)
        self.assertGreater(measurements[0]["metrics"]["acRms"], 16)
        self.assertEqual([0, 0], [m["metrics"]["acRms"] for m in measurements[1:]])
        for residue_frame in (960, 997):
            with self.subTest(residue_frame=residue_frame):
                invalid = copy.deepcopy(audio)
                invalid.samples[residue_frame] = 400
                with self.assertRaisesRegex(ValueError, "handover"):
                    FULL.measure_handover(invalid, 1)

    def test_rendered_hit_guard_requires_the_exact_known_zero_window(self):
        hits = [dict(startTick=10, acRms=200), dict(startTick=20, acRms=0)]
        self.assertEqual((1, [20]), FULL.verify_rendered_hits(hits, {20}))
        for invalid in ([dict(startTick=10, acRms=0), hits[1]],
                        [hits[0], dict(startTick=20, acRms=200)],
                        [hits[0], dict(startTick=21, acRms=0)], [hits[0]]):
            with self.subTest(hits=invalid):
                with self.assertRaisesRegex(ValueError, "zero-window"):
                    FULL.verify_rendered_hits(invalid, {20})


if __name__ == "__main__":
    unittest.main()
