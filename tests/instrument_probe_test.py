import importlib.util
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("instrument_probe", ROOT / "scripts/instrument_probe.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)
LIBRARY_SPEC = importlib.util.spec_from_file_location("instrument_library", ROOT / "scripts/instrument_library.py")
library = importlib.util.module_from_spec(LIBRARY_SPEC)
LIBRARY_SPEC.loader.exec_module(library)

RATE = 44100
UPDATE_HZ = 50.0


def note(wave, midi, amplitude=0.5, offset=0.0):
    """Silence until the probe onset, then the waveform for the probe's gate and tail."""
    f0 = 440 * 2 ** ((midi - 69) / 12)
    onset = round(probe.START_UPDATE / UPDATE_HZ * RATE)
    total = onset + round(3.0 * RATE)
    return [offset + (amplitude * wave((n - onset) * f0 / RATE % 1.0) if n >= onset else 0.0) for n in range(total)]


def sine(phase):
    return math.sin(2 * math.pi * phase)


def triangle(phase):
    return 4 * abs(phase - 0.5) - 1


def square(phase):
    return 1.0 if phase < 0.5 else -1.0


class InstrumentProbeTest(unittest.TestCase):
    def test_role_pitches(self):
        self.assertEqual([probe.role_pitch(role) for role in ("bass", "lead", "harmony", "chord")], [45, 69, 57, 57])

    def test_level_is_ac_rms_so_a_dc_offset_does_not_count(self):
        # The renderer's output carries a DC offset of up to about 0.04 full scale (probe renders, 2026-10-29);
        # raw RMS overstated quiet triangles by up to 2.7 dB.
        plain = probe.measure(note(sine, 69), RATE, 69, UPDATE_HZ)
        shifted = probe.measure(note(sine, 69, offset=0.04), RATE, 69, UPDATE_HZ)
        self.assertAlmostEqual(plain["sustainDb"], 20 * math.log10(0.5 / math.sqrt(2)), places=1)
        self.assertEqual(plain["sustainDb"], shifted["sustainDb"])
        self.assertEqual(plain["onsetDb"], shifted["onsetDb"])

    def test_brightness_is_centroid_over_fundamental(self):
        self.assertEqual(probe.measure(note(sine, 57), RATE, 57, UPDATE_HZ)["bodyCentroidRatio"], 1.0)
        self.assertEqual(probe.measure(note(triangle, 45), RATE, 45, UPDATE_HZ)["bodyCentroidRatio"], 1.0)
        self.assertGreater(probe.measure(note(square, 57), RATE, 57, UPDATE_HZ)["bodyCentroidRatio"], 2.0)

    def test_fft_matches_a_direct_transform(self):
        values = [math.sin(n * 0.3) + 0.25 * math.cos(n * 1.1) for n in range(16)]
        direct = [sum(values[n] * complex(math.cos(-2 * math.pi * k * n / 16), math.sin(-2 * math.pi * k * n / 16)) for n in range(16)) for k in range(16)]
        for fast, slow in zip(probe.fft([complex(value) for value in values]), direct):
            self.assertAlmostEqual(abs(fast - slow), 0.0, places=9)

    def test_claims_satisfy_the_library_contract(self):
        claims = probe.claims(probe.measure(note(triangle, 69), RATE, 69, UPDATE_HZ), 69)
        character = {
            "summary": "s", "waveforms": {"basis": "unknown"}, "attack": {"basis": "unknown"}, "body": {"basis": "unknown"},
            "release": {"basis": "unknown"}, "motion": [], **claims}
        library.validate_character(character, "probe", ROOT)
        self.assertTrue(claims["level"]["detail"].startswith(probe.PROBE_ID))

    def test_probe_score_gates_one_note_at_the_role_pitch(self):
        score, recipe = probe.inputs({"name": "X"}, "bass", 50.0)
        events = [event for voice in score["voices"] for event in voice["events"]]
        self.assertEqual(events, [{"startBeat": probe.START_UPDATE, "durationBeats": probe.GATE_UPDATES, "midi": 45}])
        self.assertEqual(recipe["instruments"], {"probe": {"name": "X"}})


if __name__ == "__main__":
    unittest.main()
