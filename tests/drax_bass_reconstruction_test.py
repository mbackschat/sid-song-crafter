import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("reconstruction", ROOT / "scripts/reconstruct-drax-bass.py")
reconstruction = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reconstruction)


class DraxBassReconstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe = reconstruction.read_recipe(reconstruction.STUDY / "instrument.json")
        cls.source = (reconstruction.STUDY / "player.asm").read_text()

    def execute(self, recipe, calls=None):
        sid, _ = reconstruction.build_psid(recipe, self.source)
        audit, writes = reconstruction.audit_psid(sid, calls or recipe["playCalls"])
        addresses = sorted(reconstruction.REGISTERS)
        frames = [dict(zip(addresses, frame)) for frame in reconstruction.frame_projection(writes, audit["playCalls"])]
        return audit, writes, frames

    def test_executed_instrument_keeps_test_restart_noise_pulse_and_releasing_pwm(self):
        audit, _, frames = self.execute(self.recipe)
        self.assertEqual(audit["sidModel"], "MOS6581")
        self.assertEqual([frame[0xd404] for frame in frames[98:104]], [0x40, 0x08, 0x09, 0x81, 0x41, 0x40])
        self.assertEqual([(frame[0xd405], frame[0xd406]) for frame in frames[98:102]], [(0x0f, 0), (0, 0), (2, 0xca), (2, 0xca)])
        self.assertEqual(frames[101][0xd400] | frames[101][0xd401] << 8, 0xc4e0)
        self.assertEqual(frames[102][0xd400] | frames[102][0xd401] << 8, 0x03a9)
        self.assertEqual([frame[0xd416] for frame in frames[100:103]], [8, 0xf0, 8])
        width = lambda call: frames[call][0xd402] | frames[call][0xd403] << 8
        self.assertEqual([width(call) for call in (101, 102, 103, 128, 129, 130, 150)], [0x650, 0x6a0, 0x6f0, 0xec0, 0xf10, 0xec0, 0x880])
        self.assertTrue(all(frame[0xd404] == 0x40 for frame in frames[103:]))

    def test_same_assembled_mechanism_accepts_two_note_frequencies_and_finishes(self):
        recipe = reconstruction.read_recipe(reconstruction.STUDY / "transfer.json")
        _, _, frames = self.execute(recipe, recipe["playCalls"] + 2)
        pitch = lambda call: frames[call][0xd400] | frames[call][0xd401] << 8
        self.assertEqual([pitch(call) for call in (102, 152)], [937, 1404])
        self.assertEqual([frames[call][0xd404] for call in (149, 150, 151, 152, 153)], [8, 9, 0x81, 0x41, 0x40])
        self.assertEqual([frames[call][0xd418] for call in (219, 220, 221)], [0x1f, 0, 0])
        self.assertLess(max(frame[0xd403] for frame in frames[151:220]), 16)

    def test_invalid_sweep_initialization_is_rejected_before_assembly(self):
        recipe = copy.deepcopy(self.recipe)
        recipe["instrument"]["pulseInitial"] = 0xf10
        with self.assertRaisesRegex(ValueError, "between its reversal bounds"):
            reconstruction.build_psid(recipe, self.source)

    def test_silent_pwm_cannot_cross_its_bound_on_the_first_step(self):
        for width in (0, 0x410):
            with self.subTest(width=width):
                recipe = copy.deepcopy(self.recipe)
                recipe["silentPrehistory"]["initialPulse"] = width
                with self.assertRaisesRegex(ValueError, "Initial silent PWM direction"):
                    reconstruction.build_psid(recipe, self.source)

    def read_changed_recipe(self, recipe):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recipe.json"
            reconstruction.write_json(path, recipe)
            return reconstruction.read_recipe(path)

    def test_first_note_can_initialize_on_call_two_or_three(self):
        for start in (2, 3):
            with self.subTest(start=start):
                recipe = copy.deepcopy(self.recipe)
                recipe["notes"][0]["initCall"] = start
                _, _, frames = self.execute(self.read_changed_recipe(recipe))
                self.assertEqual([frames[call][0xd404] for call in range(start - 1, start + 4)], [8, 9, 0x81, 0x41, 0x40])

    def test_note_setup_cannot_suppress_previous_instrument_gate_closure(self):
        recipe = copy.deepcopy(self.recipe)
        recipe["notes"].append({"initCall": 105, "frequency": 1404})
        with self.assertRaisesRegex(ValueError, "previous attack/release sequence"):
            self.read_changed_recipe(recipe)
        recipe["notes"][-1]["initCall"] = 106
        _, _, frames = self.execute(self.read_changed_recipe(recipe))
        self.assertEqual(frames[103][0xd404], 0x40)
        self.assertEqual(frames[104][0xd405], 0x0f)

    def test_projection_rejects_changed_instrument_but_tolerates_prior_cutoff_repeat(self):
        _, writes, _ = self.execute(self.recipe)
        reference = copy.deepcopy(writes)
        target = next(index for index, row in enumerate(reference) if row["tick"] == 101 and row["address"] == 0xd416)
        reference.insert(target, dict(reference[target], value=8))
        self.assertTrue(reconstruction.compare_registers(reference, writes, 151)["orderedAddressValueCallEquality"])
        altered = copy.deepcopy(writes)
        next(row for row in altered if row["tick"] == 103 and row["address"] == 0xd404)["value"] = 0x41
        with self.assertRaisesRegex(ValueError, "differ in value, order or call"):
            reconstruction.compare_registers(reference, altered, 151)


if __name__ == "__main__":
    unittest.main()
