import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("axel_rhythm_trial", ROOT / "scripts/studies/axel-f/prepare-rhythm-trial.py")
TRIAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRIAL)


class AxelRhythmTrialTest(unittest.TestCase):
    def setUp(self):
        self.palette = {"clock": "pal", "sidCount": 1, "sidModel": "MOS8580", "instruments": {"lead": {}, "harmony": {}, "bass": {}}}
        self.common = {"quarterBpm": 120, "provenance": {"sourceSha256": "source"},
                       "parts": [{"id": "drums", "events": [{"startBeat": [272 + index, 4], "durationBeats": [1, 8], "midi": 70}
                                                              for index in range(68)]}]}
        self.score = {"quarterBpm": 120, "provenance": {"sourceSha256": "source"}, "totalBeats": 349.3125,
                      "voices": [{"name": "melody", "events": [{"startBeat": 64, "durationBeats": 1, "midi": 65}]},
                                 {"name": "harmony", "events": []},
                                 {"name": "bass", "events": [{"startBeat": 64 + index / 4, "durationBeats": 0.125, "midi": 41}
                                                               for index in range(38)]}]}
        self.config = {"format": "axel-f-rhythm-trial-v1", "sourceSha256": "source", "sourceWindowBeats": [68, 100],
                       "arrangedWindowBeats": [64, 96], "sourceMidi": 70, "expectedOnsets": 68, "expectedOffBassOnsets": 30,
                       "basePaletteFingerprint": TRIAL.fingerprint(self.palette), "baseScoreFingerprint": TRIAL.fingerprint(self.score),
                       "instrument": {"name": "MARNOISE", "control": "0a", "hard_restart_adsr": "0f00", "adsr": "1400",
                                      "frame1": "09", "wave": [["81", "c9", "00"]], "pulse": [], "filter": []}}

    def prepare(self):
        return TRIAL.prepare(self.common, self.score, self.palette, self.config)

    def test_preserves_source_maracas_onsets_and_durations_with_identical_tonal_parts(self):
        result = self.prepare()
        before, after = result["baseline-score.json"], result["candidate-score.json"]
        self.assertEqual(before["voices"][0], after["voices"][0])
        self.assertEqual(before["voices"][2], after["voices"][2])
        events = after["voices"][1]["events"]
        self.assertEqual(68, len(events))
        self.assertEqual([index / 4 for index in range(68)], [event["startBeat"] for event in events])
        self.assertEqual({0.125}, {event["durationBeats"] for event in events})
        self.assertEqual(30, result["adaptation.json"]["offBassOnsets"])
        self.assertFalse(result["adaptation.json"]["sourceDurationAdaptation"])

    def test_rejects_missing_source_attacks_or_lost_off_bass_contrast(self):
        self.common["parts"][0]["events"].pop()
        with self.assertRaises(ValueError):
            self.prepare()
        self.setUp()
        self.config["expectedOffBassOnsets"] = 0
        with self.assertRaisesRegex(ValueError, "off-bass"):
            self.prepare()

    def test_rejects_changed_source_and_prior_baseline(self):
        self.common["provenance"]["sourceSha256"] = "different"
        with self.assertRaises(ValueError):
            self.prepare()
        self.setUp()
        self.score["voices"][2]["events"][0]["midi"] = 42
        with self.assertRaises(ValueError):
            self.prepare()

    def test_rejects_occupied_voice_and_source_duration_overlap(self):
        self.score["voices"][1]["events"] = [{"startBeat": 65, "durationBeats": 1, "midi": 70}]
        self.config["baseScoreFingerprint"] = TRIAL.fingerprint(self.score)
        with self.assertRaisesRegex(ValueError, "vacant"):
            self.prepare()
        self.setUp()
        self.common["parts"][0]["events"][0]["durationBeats"] = [1, 2]
        with self.assertRaisesRegex(ValueError, "overlap"):
            self.prepare()

    def test_rejects_coupling_filter_or_additional_timbre_changes(self):
        for key, value in (("filter", [["92", "80", "00"]]), ("wave", [["85", "c9", "00"]]), ("adsr", "14f0")):
            with self.subTest(key=key):
                config = copy.deepcopy(self.config)
                config["instrument"][key] = value
                with self.assertRaises(ValueError):
                    TRIAL.prepare(self.common, self.score, self.palette, config)


if __name__ == "__main__":
    unittest.main()
