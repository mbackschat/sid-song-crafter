import copy
import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("transfer", ROOT / "scripts/transfer-drax-bass.py")
transfer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transfer)


class BassTransferTests(unittest.TestCase):
    def test_phrase_selection_preserves_roots_and_rejects_interrupted_evolution(self):
        recipe = transfer.reconstruction.read_recipe(transfer.reconstruction.STUDY / "instrument.json")
        recipe["playCalls"] = 226
        recipe["notes"] = [{"initCall": tick, "frequency": pitch} for tick, pitch in [(84, 936), (115, 1403), (136, 936), (146, 1403), (178, 1051), (198, 1403), (209, 936)]]
        beats = [2, 2.75, 3.25, 3.5, 4.25, 4.75, 5]
        manifest = {"voices": [{}, {"notes": [dict(startBeat=beat, startTick=note["initCall"]) for beat, note in zip(beats, recipe["notes"])]}]}
        policy = {"format": "sid-bass-phrasing-v1", "retainStartBeats": [2, 3.5, 5], "minimumEvolutionCalls": 36}
        adapted = transfer.apply_phrasing(recipe, manifest, policy)
        self.assertEqual([n["initCall"] for n in adapted["notes"]], [84, 146, 209])
        self.assertEqual(adapted["instrument"], recipe["instrument"])
        self.assertEqual(len(recipe["notes"]), 7)
        with self.assertRaisesRegex(ValueError, "interrupt"):
            transfer.apply_phrasing(recipe, manifest, dict(policy, retainStartBeats=[2, 2.75, 5]))
        with self.assertRaisesRegex(ValueError, "existing"):
            transfer.apply_phrasing(recipe, manifest, dict(policy, retainStartBeats=[2, 3, 5]))

    def test_evolution_guard_observes_turnaround_and_rejects_changed_release(self):
        recipe = transfer.reconstruction.read_recipe(transfer.reconstruction.STUDY / "instrument.json")
        recipe["playCalls"] = 226
        recipe["notes"] = [{"initCall": 84, "frequency": 936}, {"initCall": 146, "frequency": 1403}, {"initCall": 209, "frequency": 936}]
        sid, _ = transfer.build_bass(recipe)
        _, writes = transfer.context.observed_audit(sid, 226)
        guard = transfer.verify_evolution(recipe, writes, 36)
        self.assertEqual([r["complete"] for r in guard], [True, True, False])
        self.assertEqual([r["observedAges"] for r in guard], [36, 36, 16])
        self.assertEqual([r["upperTurnaroundAge"] for r in guard], [29, 29, None])
        self.assertEqual([r["maximumPulseWidth"] for r in guard[:2]], [0xf10, 0xf10])
        self.assertEqual([r["lastPulseWidth"] for r in guard[:2]], [0xce0, 0xce0])
        altered = copy.deepcopy(writes)
        next(r for r in altered if r["phase"] == "play" and r["tick"] == 114 and r["address"] == 0xd40b)["value"] = 0x08
        with self.assertRaisesRegex(ValueError, "evolution"):
            transfer.verify_evolution(recipe, altered, 36)
        missing = [r for r in writes if not (r["phase"] == "play" and r["tick"] == 114 and r["address"] == 0xd40c)]
        with self.assertRaisesRegex(ValueError, "evolution"):
            transfer.verify_evolution(recipe, missing, 36)
        interrupted = copy.deepcopy(recipe)
        interrupted["notes"].insert(1, {"initCall": 115, "frequency": 1403})
        sid, _ = transfer.build_bass(interrupted)
        _, interrupted_writes = transfer.context.observed_audit(sid, 226)
        with self.assertRaisesRegex(ValueError, "evolution"):
            transfer.verify_evolution(interrupted, interrupted_writes, 36)

    def test_channel_interception_preserves_flags_registers_and_other_voices(self):
        from py65.devices.mpu6502 import MPU

        for voice in (0, 7, 14):
            for flags in (0x30, 0xff):
                cpu = MPU()
                routine = transfer.voice_interceptor(0xd404)
                cpu.memory[0x9000:0x9000 + len(routine)] = routine
                cpu.pc, cpu.a, cpu.x, cpu.y, cpu.p = 0x9000, 0x41, voice, 39, flags
                cpu.stPushWord(0x01ff)
                while cpu.pc != 0x0200:
                    cpu.step()
                self.assertEqual((cpu.a, cpu.x, cpu.y, cpu.p, cpu.sp), (0x41, voice, 39, flags, 0xff))
                self.assertEqual(cpu.memory[0xd404 + voice], 0 if voice == 7 else 0x41)

    def test_adapted_instrument_owns_only_voice_two_and_shared_filter(self):
        recipe = transfer.reconstruction.read_recipe(transfer.reconstruction.STUDY / "transfer.json")
        sid, _ = transfer.build_bass(recipe)
        _, writes = transfer.context.observed_audit(sid, recipe["playCalls"] + 2)
        rows = [r for r in writes if r["phase"] == "play"]
        self.assertTrue(all(r["address"] in transfer.BASS_REGISTERS | transfer.GLOBAL_REGISTERS for r in rows))
        frames = transfer.native.frame_states(writes, recipe["playCalls"] + 2)
        self.assertEqual([frames[t][11] for t in (100, 101, 102, 103)], [9, 0x81, 0x41, 0x40])
        self.assertEqual(frames[102][7] | frames[102][8] << 8, 937)
        self.assertEqual(frames[152][7] | frames[152][8] << 8, 1404)
        self.assertEqual(frames[102][23], 0xf2)
        self.assertEqual(frames[220][24], 0)
        self.assertEqual(recipe["instrument"]["filterRoutingResonance"], 0xf1)

    def test_transfer_uses_executed_pitch_and_preserves_start_calls(self):
        manifest = {"voices": [{}, {"name": "bass", "notes": [{"startTick": 84}, {"startTick": 115}, {"startTick": 240}]}]}
        frames = [[0] * 25 for _ in range(226)]
        for tick, word in ((86, 937), (117, 1404)):
            frames[tick][7:9] = [word & 255, word >> 8]
            frames[tick][11] = 0x41
        recipe = transfer.transfer_recipe(manifest, frames, 226)
        self.assertEqual(recipe["notes"], [{"initCall": 84, "frequency": 937}, {"initCall": 115, "frequency": 1404}])
        self.assertEqual(recipe["instrument"]["pulseStep"], 80)
        frames[117][7:9] = [0, 0]
        with self.assertRaisesRegex(ValueError, "pitched body"):
            transfer.transfer_recipe(manifest, frames, 226)
        frames[117][7:9] = [224, 196]
        frames[117][11] = 0x81
        with self.assertRaisesRegex(ValueError, "pitched body"):
            transfer.transfer_recipe(manifest, frames, 226)

    def test_filter_and_oscillator_dependencies_must_allow_bass_substitution(self):
        frames = [[0] * 25]
        transfer.verify_independence(frames)
        frames[0][23] = 0xf2
        transfer.verify_independence(frames)
        frames[0][23] = 0xf3
        with self.assertRaisesRegex(ValueError, "filter"):
            transfer.verify_independence(frames)
        frames[0][23] = 0xf2
        frames[0][18] = 0x15
        with self.assertRaisesRegex(ValueError, "coupling"):
            transfer.verify_independence(frames)

    def test_execution_guard_rejects_companion_changes_and_bass_leakage(self):
        row = lambda pc, address, value: dict(phase="play", tick=0, instructionPc=pc, address=address, value=value, instructionStartCycle=10)
        original = [row(0x1100, 0xd400, 30)]
        own = [row(0x8100, 0xd407, 40)]
        combined = original + own
        guard = transfer.verify_transfer(original, own, combined)
        self.assertEqual(guard["companionWrites"], 1)
        altered = copy.deepcopy(combined)
        altered[0]["value"] = 31
        with self.assertRaisesRegex(ValueError, "Companion"):
            transfer.verify_transfer(original, own, altered)
        with self.assertRaisesRegex(ValueError, "Native runtime"):
            transfer.verify_transfer(original, own, combined + [row(0x1100, 0xd407, 0)])


if __name__ == "__main__":
    unittest.main()
