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


def write_two_sid_fixture(path, default_song=1, left=True, right=True):
    # Hand-coded independent oscillators distinguish stereo routing from duplicated mono.
    init = bytearray((0xc9, default_song - 1, 0xf0, 1, 0x60))
    for base, hz, enabled in ((0xd400, 440, left), (0xd420, 660, right)):
        word = round(hz * 2**24 / (17734475 / 18))
        for offset, value in ((24, 15 if enabled else 0), (0, word & 255), (1, word >> 8), (5, 0), (6, 0xf0), (4, 0x11)):
            address = base + offset
            init.extend((0xa9, value, 0x8d, address & 255, address >> 8))
    init.append(0x60)
    header = bytearray(0x7c)
    header[:4] = b"PSID"
    struct.pack_into(">7HI", header, 4, 3, 0x7c, 0x1000, 0x1000, 0x1000 + len(init), 2, default_song, 0)
    struct.pack_into(">H", header, 0x76, 0xa4)
    header[0x7a] = 0x42
    path.write_bytes(header + init + b"\x60")


def read_stereo_samples(path):
    with wave.open(str(path), "rb") as source:
        assert (source.getnchannels(), source.getsampwidth(), source.getframerate()) == (2, 2, RATE)
        frames = source.getnframes()
        samples = struct.unpack("<" + "h" * (frames * 2), source.readframes(frames))
    return frames, samples[0::2], samples[1::2]


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

    def test_renderer_selects_the_declared_default_subtune_before_initialization(self):
        for default_song in (1, 2):
            with self.subTest(default_song=default_song), tempfile.TemporaryDirectory() as directory:
                sid = Path(directory) / "selected-subtune.sid"
                write_a4_sid(sid)
                data = bytearray(sid.read_bytes())
                guard = bytes((0xc9, default_song - 1, 0xf0, 1, 0x60))
                data[0x7c:0x7c] = guard
                struct.pack_into(">H", data, 12, int.from_bytes(data[12:14], "big") + len(guard))
                struct.pack_into(">2H", data, 14, 2, default_song)
                sid.write_bytes(data)
                _, samples = self.render(sid, 0.5, directory)
                self.assertGreater(rms(samples[RATE // 4:]), 100)
                self.assertAlmostEqual(frequency(samples[RATE // 4:]), 440, delta=3)

    def test_two_sid_fixture_has_distinct_stereo_pitches_and_exact_duration(self):
        for default_song in (1, 2):
            with self.subTest(default_song=default_song), tempfile.TemporaryDirectory() as directory:
                sid, output = Path(directory) / "two.sid", Path(directory) / "stereo.wav"
                write_two_sid_fixture(sid, default_song)
                result = subprocess.run([str(RENDERER), str(sid), str(output), "1.00001"], capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                frames, left, right = read_stereo_samples(output)
                self.assertEqual(frames, round(1.00001 * RATE))
                for samples, expected in ((left, 440), (right, 660)):
                    middle = samples[RATE // 4:3 * RATE // 4]
                    self.assertGreater(rms(middle), 100)
                    self.assertAlmostEqual(frequency(middle), expected, delta=3)
                    self.assertFalse(any(value in (-32768, 32767) for value in samples))
                rows = [line.split("\t") for line in Path(str(output) + ".registers.tsv").read_text().splitlines()]
                self.assertEqual(rows[0], ["time_ms", "registers_hex", "registers_sid2_hex"])
                first, second = bytes.fromhex(rows[-1][1]), bytes.fromhex(rows[-1][2])
                self.assertEqual(len(first), 32)
                self.assertEqual(len(second), 32)
                self.assertNotEqual(first[0:2], second[0:2])

    def test_two_sid_muted_variants_prove_each_chip_contributes_only_to_its_channel(self):
        for enabled_left, enabled_right in ((True, False), (False, True)):
            with self.subTest(left=enabled_left, right=enabled_right), tempfile.TemporaryDirectory() as directory:
                sid, output = Path(directory) / "isolated.sid", Path(directory) / "isolated.wav"
                write_two_sid_fixture(sid, left=enabled_left, right=enabled_right)
                result = subprocess.run([str(RENDERER), str(sid), str(output), "0.5"], capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                _, left, right = read_stereo_samples(output)
                for samples, enabled, expected in ((left, enabled_left, 440), (right, enabled_right, 660)):
                    middle = samples[RATE // 4:]
                    if enabled:
                        self.assertGreater(rms(middle), 100)
                        self.assertAlmostEqual(frequency(middle), expected, delta=3)
                    else:
                        self.assertLess(rms(middle), 1)

    def test_two_sid_rejects_unsupported_chip_addresses_models_versions_and_timing_before_output(self):
        mutations = (
            ("third chip", lambda data: data.__setitem__(0x7b, 0x44)),
            ("second address", lambda data: data.__setitem__(0x7a, 0x44)),
            ("invalid address", lambda data: data.__setitem__(0x7a, 0x41)),
            ("duplicate address", lambda data: data.__setitem__(0x7a, 0x40)),
            ("PSID version", lambda data: struct.pack_into(">H", data, 4, 4)),
            ("v2 extra SID", lambda data: struct.pack_into(">H", data, 4, 2)),
            ("NTSC", lambda data: struct.pack_into(">H", data, 0x76, 0xa8)),
            ("unknown clock", lambda data: struct.pack_into(">H", data, 0x76, 0xa0)),
            ("CIA timing", lambda data: data.__setitem__(21, 1)),
            ("second 6581", lambda data: struct.pack_into(">H", data, 0x76, 0x64)),
            ("first 6581", lambda data: struct.pack_into(">H", data, 0x76, 0x94)),
        )
        for name, mutate in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                sid, output = Path(directory) / "unsupported.sid", Path(directory) / "unsupported.wav"
                write_two_sid_fixture(sid)
                data = bytearray(sid.read_bytes())
                mutate(data)
                sid.write_bytes(data)
                result = subprocess.run([str(RENDERER), str(sid), str(output), "0.1"], capture_output=True, text=True, timeout=20)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(result.stderr.strip())
                self.assertFalse(output.exists())
                self.assertFalse(Path(str(output) + ".registers.tsv").exists())

    def test_render_longer_than_one_minute_keeps_exact_length_and_final_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            sid = Path(directory) / "a4.sid"
            output = Path(directory) / "long.wav"
            write_a4_sid(sid)
            subprocess.run([str(RENDERER), str(sid), str(output), "60.01"], check=True, timeout=20, capture_output=True, text=True)
            with wave.open(str(output), "rb") as wav:
                self.assertEqual(wav.getnframes(), round(60.01 * RATE))
                wav.setpos(59 * RATE)
                tail = wav.readframes(RATE)
            samples = struct.unpack("<" + "h" * (len(tail) // 2), tail)
            self.assertGreater(rms(samples), 100)
            self.assertAlmostEqual(frequency(samples), 440, delta=3)

    def test_render_rejects_duration_above_ten_minutes_without_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            sid = Path(directory) / "a4.sid"
            output = Path(directory) / "oversized.wav"
            write_a4_sid(sid)
            result = subprocess.run([str(RENDERER), str(sid), str(output), "600.01"], timeout=20, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("at most 600", result.stderr)
            self.assertFalse(output.exists())

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
