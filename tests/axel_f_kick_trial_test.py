import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("axel_kick_trial", ROOT / "scripts/studies/axel-f/prepare-kick-trial.py")
TRIAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRIAL)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class AxelKickTrialTest(unittest.TestCase):
    def setUp(self):
        self.palette = {"format": "sidwizard-arrangement-v1", "clock": "pal", "sidCount": 1,
                        "sidModel": "MOS8580", "instruments": {"lead": {"name": "LEAD"}, "harmony": {}, "bass": {}},
                        "sections": [], "score": "score.json"}
        self.kick = {"name": "KICKFALL", "wave": [["11", "ac", "00"]], "filter": []}
        self.bank = {"instruments": {"kick-fall": self.kick}}
        self.config = {"format": "axel-f-kick-trial-v1", "sourceSha256": "pinned-source",
                       "sourceWindowBeats": [68, 100], "arrangedWindowBeats": [64, 96],
                       "kickMidi": 36, "expectedKickOnsets": 48, "kickDurationSeconds": 0.18,
                       "basePaletteFingerprint": fingerprint(self.palette), "kickFingerprint": fingerprint(self.kick)}
        events = [{"startBeat": [68 + i // 2, 1] if i % 2 == 0 else [137 + i - 1, 2],
                   "durationBeats": [1, 16], "midi": 36} for i in range(48)]
        self.common = {"quarterBpm": 120, "parts": [{"id": "drums", "events": events}],
                       "provenance": {"sourceSha256": "pinned-source"}}
        self.score = {"title": "synthetic guard fixture", "composer": "test", "quarterBpm": 120,
                      "timeSignature": [4, 4], "totalBeats": 349.3125, "tailTicks": 125, "volume": 15,
                      "provenance": {"sourceSha256": "pinned-source"},
                      "voices": [{"name": "melody", "events": [{"startBeat": 64, "durationBeats": 1, "midi": 65}]},
                                 {"name": "harmony", "events": []},
                                 {"name": "bass", "events": [{"startBeat": 64, "durationBeats": 0.5, "midi": 41}]}]}
        self.config["baseScoreFingerprint"] = fingerprint(self.score)

    def prepare(self):
        return TRIAL.prepare(self.common, self.score, self.palette, self.bank, self.config)

    def test_only_empty_harmony_receives_source_kicks_and_tonal_events_survive(self):
        result = self.prepare()
        baseline, candidate = result["baseline-score.json"], result["candidate-score.json"]
        self.assertEqual(baseline["voices"][0], candidate["voices"][0])
        self.assertEqual(baseline["voices"][2], candidate["voices"][2])
        self.assertEqual([], baseline["voices"][1]["events"])
        self.assertEqual(48, len(candidate["voices"][1]["events"]))
        self.assertEqual(0, candidate["voices"][1]["events"][0]["startBeat"])
        self.assertEqual(0.36, candidate["voices"][1]["events"][0]["durationBeats"])
        self.assertEqual(self.kick, result["candidate.json"]["instruments"]["kick"])

    def test_short_gap_caps_body_without_moving_the_next_source_onset(self):
        events = self.common["parts"][0]["events"]
        events[1]["startBeat"] = [273, 4]
        result = self.prepare()
        kicks = result["candidate-score.json"]["voices"][1]["events"]
        self.assertEqual(0.25, kicks[0]["durationBeats"])
        self.assertEqual(0.25, kicks[1]["startBeat"])
        self.assertEqual(1, result["adaptation.json"]["durationCappedByNextOnsetCount"])

    def test_rejects_changed_source_occupied_harmony_and_modified_palette(self):
        for change in ("source", "occupied", "palette", "tonal-event"):
            with self.subTest(change=change):
                self.setUp()
                if change == "source":
                    self.common["provenance"]["sourceSha256"] = "different"
                elif change == "occupied":
                    self.score["voices"][1]["events"].append({"startBeat": 65, "durationBeats": 1, "midi": 70})
                elif change == "palette":
                    self.palette["instruments"]["lead"]["name"] = "CHANGED"
                else:
                    self.score["voices"][0]["events"][0]["midi"] = 66
                with self.assertRaises(ValueError):
                    self.prepare()

    def test_rejects_lost_or_duplicate_source_kick_onset(self):
        for duplicate in (False, True):
            with self.subTest(duplicate=duplicate):
                self.setUp()
                events = self.common["parts"][0]["events"]
                if duplicate:
                    events[1] = copy.deepcopy(events[0])
                else:
                    events.pop()
                with self.assertRaises(ValueError):
                    self.prepare()

    def test_rejects_a_window_that_does_not_preserve_the_four_beat_trim(self):
        self.config["arrangedWindowBeats"] = [62, 94]
        with self.assertRaisesRegex(ValueError, "four source beats"):
            self.prepare()


if __name__ == "__main__":
    unittest.main()
