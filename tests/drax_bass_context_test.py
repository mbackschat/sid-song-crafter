import copy
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import wave


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("drax_context", ROOT / "scripts/context-drax-bass.py")
context = importlib.util.module_from_spec(spec)
spec.loader.exec_module(context)


class DraxBassContextTests(unittest.TestCase):
    def test_reference_hash_rejects_an_unrelated_or_changed_driver(self):
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            context.build_context(bytes(124))

    def test_patch_precondition_rejects_an_unexpected_instruction(self):
        payload = bytearray(64)
        with self.assertRaisesRegex(ValueError, "precondition"):
            context.patch_instruction(payload, 0x1000, 0x1010, bytes.fromhex("9905d4"), bytes.fromhex("200090"))
        self.assertEqual(payload, bytearray(64))

    def test_execution_guard_rejects_changed_companion_and_extra_original_bass(self):
        row = {"phase": "play", "tick": 1, "address": 0xd407, "value": 22, "instructionPc": 0x1433}
        own = {"phase": "play", "tick": 1, "address": 0xd404, "value": 0x40, "instructionPc": 0x8120}
        context.verify_execution([row], [own], [row, own], 2)
        changed = copy.deepcopy(row)
        changed["value"] = 23
        with self.assertRaisesRegex(ValueError, "Companion"):
            context.verify_execution([row], [own], [changed, own], 2)
        extra = dict(row, address=0xd400)
        with self.assertRaisesRegex(ValueError, "Original runtime"):
            context.verify_execution([row], [own], [row, own, extra], 2)

    def test_common_gain_keeps_the_mix_level_difference_and_exact_ab_order(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            paths = [output / "a.wav", output / "b.wav"]
            for path, peak in zip(paths, (10000, 32000)):
                with wave.open(str(path), "wb") as stream:
                    stream.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
                    stream.writeframes(struct.pack("<hh", peak, -peak) * 12000)
            originals = [path.read_bytes() for path in paths]
            report = context.common_gain_comparison(*paths, output)
            gain = report["gain"]
            self.assertLess(gain, 1)
            a = context.read_pcm16(output / "original.wav").samples
            b = context.read_pcm16(output / "reconstructed-in-context.wav").samples
            self.assertEqual(list(a[:2]), [round(10000 * gain), round(-10000 * gain)])
            self.assertEqual(list(b[:2]), [round(32000 * gain), round(-32000 * gain)])
            ab = context.read_pcm16(output / "full.ab.wav").samples
            self.assertEqual(ab[:24000], a)
            self.assertEqual(list(ab[24000:28000]), [0] * 4000)
            self.assertEqual(ab[28000:], b)
            self.assertEqual([path.read_bytes() for path in paths], originals)

    @unittest.skipUnless((ROOT / ".local/research/fuer-elise/drax-fuer-elise.sid").exists(), "Requires the separately archived, hash-pinned DRAX reference")
    def test_actual_hybrid_preserves_companion_calls_and_uses_the_independent_bass(self):
        original = (ROOT / ".local/research/fuer-elise/drax-fuer-elise.sid").read_bytes()
        sid, built = context.build_context(original)
        report = context.audit_context(original, sid, built)
        self.assertTrue(report["companionOrderedCallAddressValueEquality"])
        self.assertTrue(report["independentBassOrderedCallAddressValueEquality"])
        self.assertGreater(report["companionWrites"], 1900)
        self.assertEqual(report["playCalls"], 151)
        self.assertLess(report["hybridAudit"]["maximumPlayCycles"], 19656)
        _, writes = context.observed_audit(sid, 153, built["trampolineOrigins"])
        self.assertEqual([(row["tick"], row["address"], row["value"]) for row in writes if row["tick"] in (151, 152)], [(151, 0xd418, 0), (152, 0xd418, 0)])
        self.assertEqual(original, (ROOT / ".local/research/fuer-elise/drax-fuer-elise.sid").read_bytes())


if __name__ == "__main__":
    unittest.main()
