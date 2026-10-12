import math
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import wave


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / ".local/bin/render-sid"
RATE = 44100


def read_samples(path):
    with wave.open(str(path), "rb") as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, RATE)
        data = wav.readframes(wav.getnframes())
    return struct.unpack("<" + "h" * (len(data) // 2), data)


def rms(samples):
    centre = sum(samples) / len(samples)
    return math.sqrt(sum((value - centre) ** 2 for value in samples) / len(samples))


def frequency(samples):
    centre = sum(samples) / len(samples)
    crossings = [index for index in range(1, len(samples)) if samples[index - 1] <= centre < samples[index]]
    return (len(crossings) - 1) * RATE / (crossings[-1] - crossings[0])


def write_a4_sid(path):
    # A separate PSID fixture settles pitch against 440 Hz without using the song compiler.
    init = bytes.fromhex("A9 0F 8D 18 D4 A9 45 8D 00 D4 A9 1D 8D 01 D4 A9 00 8D 05 D4 A9 F0 8D 06 D4 A9 11 8D 04 D4 60")
    header = bytearray(0x7C)
    header[:4] = b"PSID"
    struct.pack_into(">7HI", header, 4, 2, 0x7C, 0x1000, 0x1000, 0x1000 + len(init), 1, 1, 0)
    struct.pack_into(">H", header, 0x76, 0x24)
    path.write_bytes(header + init + b"\x60")


class HeadlessRenderTest(unittest.TestCase):
    def render(self, sid, seconds, directory):
        output = Path(directory) / "render.wav"
        subprocess.run([str(RENDERER), str(sid), str(output), str(seconds)], check=True, timeout=20, capture_output=True, text=True)
        return output, read_samples(output)

    def test_independent_a4_fixture_has_expected_duration_and_pitch(self):
        with tempfile.TemporaryDirectory() as directory:
            sid = Path(directory) / "a4.sid"
            write_a4_sid(sid)
            _, samples = self.render(sid, 1, directory)
            self.assertEqual(len(samples), RATE)
            middle = samples[RATE // 4:3 * RATE // 4]
            self.assertGreater(rms(middle), 100)
            self.assertAlmostEqual(frequency(middle), 440, delta=3)

    def test_fuer_elise_has_nine_pitches_and_a_silent_ending(self):
        with tempfile.TemporaryDirectory() as directory:
            output, samples = self.render(ROOT / "build/fuer-elise-opening.sid", 3.2, directory)
            self.assertEqual(len(samples), round(3.2 * RATE))
            self.assertGreater(rms(samples[RATE // 10:2 * RATE]), 100)
            self.assertLess(rms(samples[3 * RATE:]), 2)
            rows = [(int(line.split("\t")[0]) / 1000, bytes.fromhex(line.split("\t")[1])) for line in Path(str(output) + ".registers.tsv").read_text().splitlines()[1:]]
            notes = []
            previous_gate = False
            for timestamp, state in rows:
                gate = bool(state[4] & 1)
                if gate and not previous_gate:
                    notes.append([timestamp, None, state[0] | (state[1] << 8)])
                if not gate and previous_gate:
                    notes[-1][1] = timestamp
                previous_gate = gate
            clock = 985248.6111111111
            expected_hz = [659.255, 622.254, 659.255, 622.254, 659.255, 493.883, 587.330, 523.251, 440]
            expected_ticks = [0, 10, 21, 31, 42, 52, 63, 73, 84]
            self.assertEqual(len(notes), len(expected_hz))
            for (onset, offset, word), expected, tick in zip(notes, expected_hz, expected_ticks):
                self.assertAlmostEqual(word * clock / 2**24, expected, delta=0.1)
                self.assertAlmostEqual(onset - notes[0][0], tick * 19656 / clock, delta=0.021)
                active = samples[round((onset + 0.04) * RATE):round((offset - 0.025) * RATE)]
                self.assertGreater(rms(active), 100)
                self.assertAlmostEqual(frequency(active), expected, delta=3)
            self.assertEqual(rows[-1][1][0x18] & 15, 0)


if __name__ == "__main__":
    unittest.main()
