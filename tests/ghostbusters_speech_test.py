import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GhostbustersSpeechTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('ghostbusters_speech', ROOT / 'scripts/studies/ghostbusters/speech.py')
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    def test_first_nibble_is_repeated_then_low_precedes_high(self):
        values, consumed = self.module.unpack_wave(bytes([0xA3, 0x71]), 4, self.module.Encoding.NIBBLES)
        self.assertEqual(values, [20, 20, 2, 14])
        self.assertEqual(consumed, 2)

    def test_first_two_bit_symbol_selects_scale_and_next_symbol_is_repeated(self):
        values, consumed = self.module.unpack_wave(bytes([0b11100101, 0b00011011]), 8, self.module.Encoding.TWO_BIT)
        self.assertEqual(values, [14, 14, 16, 18, 18, 16, 14, 12])
        self.assertEqual(consumed, 2)

    def test_ramp_one_bit_duplicates_bit_one_and_keeps_remaining_bit_order(self):
        values, consumed = self.module.unpack_wave(bytes([0b10100110]), 8, self.module.Encoding.ONE_BIT)
        self.assertEqual(values, [16, 16, 16, 14, 14, 16, 14, 16])
        self.assertEqual(consumed, 1)

    def test_wave_decoder_rejects_partial_block_and_code_alias_scale(self):
        for data, count, mode in [(b'\x11', 4, self.module.Encoding.NIBBLES),
                                  (b'\x00', 4, self.module.Encoding.TWO_BIT)]:
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.module.unpack_wave(data, count, mode)

    def test_pitch_control_uses_five_bit_count_and_signed_delta(self):
        synth = self.module.SpeechSynth(bytes(65536))
        synth.memory = bytes([0] * 0x200 + [13, 0x30] + [0] * (65536 - 0x202))
        synth.pitch_pointer, synth.pitch_count = 0x200, 255
        synth.update_pitch()
        self.assertEqual((synth.pitch_count, synth.pitch_value, synth.gap, synth.pitch_delta), (0xF3, 12, 6, -12))
        synth.update_pitch()
        self.assertEqual((synth.pitch_value, synth.gap), (0, 0))

    def test_gap_wait_emits_no_volume_until_stop(self):
        synth = self.module.SpeechSynth(bytes(65536))
        synth.handler, synth.gap_count, synth.finished = self.module.Handler.GAP_WAIT, 2, False
        self.assertIsNone(synth.tick())
        self.assertEqual(synth.gap_count, 1)
        synth.handler = self.module.Handler.STOP
        self.assertEqual(synth.tick(), 7)
        self.assertTrue(synth.finished)
        with self.assertRaises(ValueError):
            synth.tick()


if __name__ == '__main__':
    unittest.main()
