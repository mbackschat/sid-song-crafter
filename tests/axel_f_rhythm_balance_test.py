import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("axel_rhythm_balance", ROOT / "scripts/studies/axel-f/prepare-rhythm-balance.py")
BALANCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BALANCE)


class AxelRhythmBalanceTest(unittest.TestCase):
    def setUp(self):
        self.previous = {"instrument": {"name": "MARNOISE", "adsr": "1400", "wave": [["81", "c9", "00"]]}}
        self.native = {"score": "candidate-score.json", "instruments": {"lead": {}, "rhythm": self.previous["instrument"], "bass": {}}}
        self.score = {"voices": [{"events": []}, {"events": [{}] * 68}, {"events": []}]}
        self.config = {"format": "axel-f-rhythm-balance-v1", "previousConfigurationFingerprint": BALANCE.TRIAL.fingerprint(self.previous),
                       "adsr": "1100", "expectedOnsets": 68}

    def test_changes_only_noise_decay_rate_and_keeps_the_exact_source_score(self):
        result = BALANCE.prepare(self.native, self.score, self.previous, self.config)
        expected = copy.deepcopy(self.native)
        expected["instruments"]["rhythm"]["adsr"] = "1100"
        self.assertEqual(expected, result["candidate.json"])
        self.assertEqual(self.score, result["candidate-score.json"])
        self.assertEqual("1400", self.native["instruments"]["rhythm"]["adsr"])

    def test_rejects_baseline_drift_duration_loss_and_other_envelope_changes(self):
        for mutation in ("baseline", "events", "sustain", "attack"):
            with self.subTest(mutation=mutation):
                self.setUp()
                if mutation == "baseline":
                    self.native["instruments"]["rhythm"] = {**self.previous["instrument"], "adsr": "2400"}
                elif mutation == "events":
                    self.score["voices"][1]["events"].pop()
                else:
                    self.config["adsr"] = "1110" if mutation == "sustain" else "2100"
                with self.assertRaises(ValueError):
                    BALANCE.prepare(self.native, self.score, self.previous, self.config)

    def test_execution_guard_allows_only_the_declared_ad_register_value(self):
        previous = [[0] * 25, [0] * 25]
        previous[1][12] = 0x14
        quiet = copy.deepcopy(previous)
        quiet[1][12] = 0x34
        self.assertEqual([12], BALANCE.verify_frames(previous, quiet, 0x14, 0x34))
        for offset in (7, 8, 11, 13, 23, 24):
            with self.subTest(offset=offset):
                invalid = copy.deepcopy(quiet)
                invalid[1][offset] = 1
                with self.assertRaises(ValueError):
                    BALANCE.verify_frames(previous, invalid, 0x14, 0x34)
        quiet[1][12] = 0x44
        with self.assertRaises(ValueError):
            BALANCE.verify_frames(previous, quiet, 0x14, 0x34)

    def test_signal_guard_requires_meaningful_reduction_without_silencing(self):
        self.assertAlmostEqual(-6.0206, BALANCE.measured_reduction(700, 350, 3, 8), places=4)
        for quiet in (0, 1, 699, 701):
            with self.subTest(quiet=quiet):
                with self.assertRaises(ValueError):
                    BALANCE.measured_reduction(700, quiet, 3, 8)

    def test_isolation_accepts_identical_store_timing_and_muted_pcm(self):
        writes = [{"instructionStartCycle": 10}, {"instructionStartCycle": 20}]
        self.assertEqual((0, True), BALANCE.verify_isolation(writes, copy.deepcopy(writes), [1, 2, 3], [1, 2, 3]))

    def test_isolation_rejects_shifted_store_timing_with_identical_muted_pcm(self):
        previous = [{"instructionStartCycle": 10}, {"instructionStartCycle": 20}]
        shifted = [{"instructionStartCycle": 10}, {"instructionStartCycle": 21}]
        with self.assertRaisesRegex(ValueError, "store timing"):
            BALANCE.verify_isolation(previous, shifted, [1, 2, 3], [1, 2, 3])

    def test_isolation_rejects_changed_muted_pcm_with_identical_store_timing(self):
        writes = [{"instructionStartCycle": 10}, {"instructionStartCycle": 20}]
        with self.assertRaisesRegex(ValueError, "Muted tonal PCM"):
            BALANCE.verify_isolation(writes, copy.deepcopy(writes), [1, 2, 3], [1, 2, 4])


if __name__ == "__main__":
    unittest.main()
