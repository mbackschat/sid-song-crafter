import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("drax_bass_experiment", ROOT / "scripts/studies/drax/study-drax-bass.py")
experiment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(experiment)


def psid_fixture(embedded=False):
    header = bytearray(0x7c)
    header[:4] = b"PSID"
    header[4:6] = (2).to_bytes(2, "big")
    header[6:8] = (0x7c).to_bytes(2, "big")
    header[8:10] = (0 if embedded else 0xf00).to_bytes(2, "big")
    payload = bytearray(0x1000)
    payload[0x124b - 0xf00:0x1250 - 0xf00] = bytes.fromhex("a9f18d17d4")
    payload[0x126b - 0xf00:0x126e - 0xf00] = bytes.fromhex("b9a51a")
    payload[0x1aa5 - 0xf00:0x1aa7 - 0xf00] = bytes.fromhex("5006")
    return bytes(header + (b"\x00\x0f" if embedded else b"") + payload)


def fixture_writes():
    writes = []
    for tick in range(151):
        state = [0] * 25
        state[0:2] = [0xa9, 3]
        state[2:4] = [0x70, 4]
        state[4:7] = [0x40, 2, 0xca]
        state[7:14] = [0x25, 0x11, 0, 7, 0x41, 3, 0x64]
        state[14:21] = [0x3a, 8, 0, 6, 0x51, 3, 0x4a]
        state[23:25] = [0xf1 if tick >= 100 else 0, 0x1f]
        if tick == 100:
            state[4] = 9
        if tick == 101:
            state[0:2], state[4] = [0xe0, 0xc4], 0x81
        if tick >= 102:
            width = 0x6a0 + 0x50 * (tick - 102) if tick <= 129 else 0xf10 - 0x50 * (tick - 129)
            state[2:4] = [width & 255, width >> 8]
            state[4] = 0x41 if tick == 102 else 0x40
        for offset, value in enumerate(state):
            writes.append({"phase": "play", "tick": tick, "instructionStartCycle": offset * 6, "address": 0xd400 + offset, "value": value})
    return writes


def frozen_writes(original):
    candidate = copy.deepcopy(original)
    for row in candidate:
        if row["tick"] >= 102 and row["address"] in (0xd402, 0xd403):
            row["value"] = 0xa0 if row["address"] == 0xd402 else 6
        row["instructionStartCycle"] += 13
    return candidate


class DraxBassExperimentTest(unittest.TestCase):
    def test_payload_mapping_handles_declared_and_embedded_load_addresses(self):
        for embedded in (False, True):
            data = psid_fixture(embedded)
            self.assertEqual(experiment.payload_offset(data, 0x1aa5), 0xc21 + 2 * embedded)
            with self.assertRaisesRegex(ValueError, "payload"):
                experiment.payload_offset(data, 0xeff)
            with self.assertRaisesRegex(ValueError, "payload"):
                experiment.payload_offset(data, 0x1f00)

    def test_variant_patches_are_exact_and_do_not_modify_source_bytes(self):
        for embedded in (False, True):
            data = psid_fixture(embedded)
            with patch.object(experiment, "SOURCE_SHA256", hashlib.sha256(data).hexdigest()):
                for variant, expected in (("original", {}), ("no-pwm", {0x1aa5: 0, 0x1aa6: 0xa6}), ("filter-bypass", {0x124c: 0xf0})):
                    result, receipt = experiment.make_variant(data, variant)
                    differences = {address: result[experiment.payload_offset(data, address)] for address in range(0xf00, 0x1f00) if data[experiment.payload_offset(data, address)] != result[experiment.payload_offset(data, address)]}
                    self.assertEqual(differences, expected)
                    self.assertEqual(len(receipt["patches"]), len(expected))
                    self.assertEqual(data, psid_fixture(embedded))

    def test_wrong_source_and_stale_patch_preconditions_are_rejected(self):
        data = psid_fixture()
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            experiment.make_variant(data, "no-pwm")
        for address in (0x1aa5, 0x1aa6, 0x126b, 0x124b):
            changed = bytearray(data)
            changed[experiment.payload_offset(data, address)] ^= 1
            changed = bytes(changed)
            with patch.object(experiment, "SOURCE_SHA256", hashlib.sha256(changed).hexdigest()), self.assertRaisesRegex(ValueError, "precondition"):
                experiment.make_variant(changed, "no-pwm" if address != 0x124b else "filter-bypass")

    def test_register_comparison_accepts_fixed_width_and_reports_cycle_shifts(self):
        original = fixture_writes()
        report = experiment.verify_experiment(original, frozen_writes(original), "no-pwm")
        self.assertEqual(report["frozenPulseWidth"], 0x6a0)
        self.assertTrue(report["unchangedWriteOrderAndCounts"])
        self.assertGreater(report["instructionCycleShifts"]["count"], 0)
        self.assertEqual(report["instructionCycleShifts"]["minimumDelta"], 13)
        self.assertFalse(report["busExactTimingClaimed"])

    def test_filter_bypass_changes_only_the_bass_routing_bit(self):
        original = fixture_writes()
        candidate = copy.deepcopy(original)
        for row in candidate:
            if row["address"] == 0xd417 and row["value"] == 0xf1:
                row["value"] = 0xf0
        report = experiment.verify_experiment(original, candidate, "filter-bypass")
        self.assertEqual(report["changedAddresses"], [0xd417])
        self.assertTrue(report["bassFilterBypassed"])
        candidate[-2]["value"] = 0xe0
        with self.assertRaisesRegex(ValueError, "routing"):
            experiment.verify_experiment(original, candidate, "filter-bypass")

    def test_changes_to_pitch_gate_adsr_companions_or_write_structure_fail(self):
        original = fixture_writes()
        for address in (0xd400, 0xd404, 0xd405, 0xd406, 0xd407, 0xd40b, 0xd40e, 0xd412, 0xd418):
            candidate = frozen_writes(original)
            row = next(row for row in candidate if row["tick"] == 110 and row["address"] == address)
            row["value"] ^= 1
            with self.subTest(address=address), self.assertRaisesRegex(ValueError, "outside"):
                experiment.verify_experiment(original, candidate, "no-pwm")
        for mutation in (lambda rows: rows.pop(), lambda rows: rows.reverse(), lambda rows: rows[200].update(tick=7)):
            candidate = frozen_writes(original)
            mutation(candidate)
            with self.assertRaisesRegex(ValueError, "order|count"):
                experiment.verify_experiment(original, candidate, "no-pwm")

    def test_remaining_pwm_and_an_unverified_reference_motion_are_rejected(self):
        original = fixture_writes()
        candidate = frozen_writes(original)
        next(row for row in candidate if row["tick"] == 110 and row["address"] == 0xd402)["value"] += 1
        with self.assertRaisesRegex(ValueError, "frozen"):
            experiment.verify_experiment(original, candidate, "no-pwm")
        next(row for row in original if row["tick"] == 129 and row["address"] == 0xd403)["value"] = 6
        with self.assertRaisesRegex(ValueError, "reference.*PWM"):
            experiment.verify_experiment(original, frozen_writes(original), "no-pwm")

    def test_short_coverage_and_unchanged_counterfactual_are_rejected(self):
        original = fixture_writes()
        with self.assertRaisesRegex(ValueError, "151"):
            experiment.verify_experiment(original[:140 * 25], frozen_writes(original)[:140 * 25], "no-pwm")
        with self.assertRaisesRegex(ValueError, "frozen|no register"):
            experiment.verify_experiment(original, original, "no-pwm")

    def test_existing_output_and_unpinned_source_fail_before_creating_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / "fixture.sid"
            source.write_bytes(psid_fixture())
            output = folder / "output"
            output.mkdir()
            with self.assertRaisesRegex(ValueError, "existing|fresh"):
                experiment.run_study(source, output)
            self.assertEqual(list(output.iterdir()), [])
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                experiment.run_study(source, folder / "fresh")
            self.assertFalse((folder / "fresh").exists())

    @unittest.skipUnless((ROOT / ".local/research/fuer-elise/drax-fuer-elise.sid").is_file(), "Pinned archived reference required")
    def test_actual_driver_variants_preserve_other_register_programs(self):
        data = (ROOT / ".local/research/fuer-elise/drax-fuer-elise.sid").read_bytes()
        _, original = experiment.audit_psid(data, 151)
        for variant in ("no-pwm", "filter-bypass"):
            patched, _ = experiment.make_variant(data, variant)
            _, writes = experiment.audit_psid(patched, 151)
            report = experiment.verify_experiment(original, writes, variant)
            self.assertTrue(report["unchangedWriteOrderAndCounts"])


if __name__ == "__main__":
    unittest.main()
