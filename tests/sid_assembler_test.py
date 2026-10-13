from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sid_assembler import assemble


class SidAssemblerTests(unittest.TestCase):
    def test_forward_labels_and_little_endian_words_share_resolved_addresses(self):
        constants = {"SID_CONTROL": 0xd404, "WAVE": 0x41}
        source = """
entry:
  LDA #WAVE ; An instruction comment must not become an operand.
  STA SID_CONTROL
  JMP body
table:
  .byte $00, $ff
  .word body, entry, $1234
body:
  RTS
"""
        payload, symbols, listing = assemble(source, constants, load=0x2000)
        self.assertEqual(payload, bytes.fromhex("a9 41 8d 04 d4 4c 10 20 00 ff 10 20 00 20 34 12 60"))
        self.assertEqual(symbols, dict(constants, entry=0x2000, table=0x2008, body=0x2010))
        self.assertEqual(constants, {"SID_CONTROL": 0xd404, "WAVE": 0x41})
        self.assertIn("200a  102000203412 .word body, entry, $1234\n", listing)

    def test_relative_branch_boundaries_encode_without_wrapping(self):
        padding = ",".join(["$00"] * 127)
        payload, _, _ = assemble(f"BNE target\n.byte {padding}\ntarget:\nRTS")
        self.assertEqual(payload[:2], bytes.fromhex("d0 7f"))
        padding = ",".join(["$00"] * 126)
        payload, _, _ = assemble(f"target:\n.byte {padding}\nBNE target")
        self.assertEqual(payload[-2:], bytes.fromhex("d0 80"))

    def test_forward_and_backward_branch_overflow_is_rejected(self):
        forward = ",".join(["$00"] * 128)
        backward = ",".join(["$00"] * 127)
        for source in (f"BNE target\n.byte {forward}\ntarget:\nRTS", f"target:\n.byte {backward}\nBNE target"):
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError, "Branch out of range"):
                    assemble(source)

    def test_payload_cannot_enter_rom_or_reserved_low_memory(self):
        for load, source in ((0x03ff, "RTS"), (0xa000, "RTS"), (0x9fff, ".word $1234")):
            with self.subTest(load=load, source=source):
                with self.assertRaisesRegex(ValueError, "callable RAM"):
                    assemble(source, load=load)

    def test_duplicate_labels_and_constant_collisions_are_rejected(self):
        for source, constants in (("entry:\nRTS\nentry:\nRTS", None), ("entry:\nRTS", {"entry": 0x2000})):
            with self.subTest(source=source, constants=constants):
                with self.assertRaisesRegex(ValueError, "Duplicate label entry"):
                    assemble(source, constants)

    def test_byte_data_cannot_silently_truncate_a_word(self):
        with self.assertRaisesRegex(ValueError, "byte"):
            assemble(".byte $100")


if __name__ == "__main__":
    unittest.main()
