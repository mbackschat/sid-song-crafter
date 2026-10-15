from array import array
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
import wave


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audio_comparison import Pcm16, read_pcm16

spec = importlib.util.spec_from_file_location(
    'chord_expansion_listening', ROOT / 'scripts/studies/rambo/prepare-chord-expansion-listening.py')
listening = importlib.util.module_from_spec(spec)
spec.loader.exec_module(listening)


TIMING = dict(passed=True, primaryPayloadMatchesReference=True, primaryOrderedStoresIdentical=True,
              primaryRelativeCpuTimingIdentical=True, primaryViceOffsetsIdentical=True,
              firstSecondaryDifferenceCall=2354)


def pcm(samples, channels=1, rate=8):
    return Pcm16(rate, channels, len(samples) // channels, array('h', samples), '')


def fixture():
    primary = [1200 if frame % 2 else -1200 for frame in range(225 * 8)]
    primary[-8:] = [0] * 8
    old, new = [], []
    for frame, value in enumerate(primary):
        backing = (300 if frame % 3 else -600) if frame < 200 * 8 else 0
        third = (200 if frame % 2 else -200) if 50 * 8 <= frame < 149 * 8 else 0
        old.extend((value, backing))
        new.extend((value, backing + third))
    support = pcm([600, -600] * (104 * 4))
    omitted = pcm([400, -400] * (104 * 4))
    return pcm(old, 2), pcm(new, 2), support, omitted


def write_wav(path, audio):
    samples = array('h', audio.samples)
    if sys.byteorder != 'little':
        samples.byteswap()
    with wave.open(str(path), 'wb') as target:
        target.setparams((audio.channels, 2, audio.sample_rate, 0, 'NONE', 'not compressed'))
        target.writeframes(samples.tobytes())


class RamboChordExpansionListeningTest(unittest.TestCase):
    def test_measures_primary_and_ending_pcm_and_actual_third_voice_residual(self):
        old, new, support, omitted = fixture()
        report = listening.check_audio(old, new, support, omitted, timing=TIMING, sample_rate=8)
        self.assertTrue(report['primaryPcmComparison']['identical'])
        self.assertTrue(report['endingPcmComparison']['identical'])
        self.assertEqual(report['thirdVoiceContribution']['residualAcRms'], 200)
        self.assertAlmostEqual(report['thirdVoiceContribution']['residualToSupportAcRmsRatio'], 1 / 3)
        self.assertIsNone(report['listeningVerdict'])

    def test_rejects_primary_changes_before_intervention_and_absent_third_voice(self):
        old, new, support, omitted = fixture()
        changed_primary = pcm(new.samples, 2)
        changed_primary.samples[100] += 1
        with self.assertRaisesRegex(ValueError, 'prefix'):
            listening.check_audio(old, changed_primary, support, omitted, timing=TIMING, sample_rate=8)
        with self.assertRaisesRegex(ValueError, 'contribut'):
            listening.check_audio(old, new, support, support, timing=TIMING, sample_rate=8)

    def test_reports_later_phase_differences_only_with_required_timing_proof(self):
        old, new, support, omitted = fixture()
        changed = pcm(new.samples, 2)
        changed.samples[100 * 8 * 2] += 1
        changed.samples[210 * 8 * 2] += 1
        report = listening.check_audio(old, changed, support, omitted, timing=TIMING, sample_rate=8)
        self.assertFalse(report['primaryPcmComparison']['identical'])
        self.assertEqual(report['primaryPcmComparison']['firstDifferenceFrame'], 100 * 8)
        self.assertFalse(report['endingPcmComparison']['identical'])
        invalid = dict(TIMING, primaryRelativeCpuTimingIdentical=False)
        with self.assertRaisesRegex(ValueError, 'timing proof'):
            listening.check_audio(old, changed, support, omitted, timing=invalid, sample_rate=8)

    def test_rejects_clipping_truncation_and_an_unsettled_tail(self):
        old, new, support, omitted = fixture()
        clipped = pcm(new.samples, 2)
        clipped.samples[101] = 32767
        with self.assertRaisesRegex(ValueError, 'rail'):
            listening.check_audio(old, clipped, support, omitted, timing=TIMING, sample_rate=8)
        with self.assertRaisesRegex(ValueError, '225'):
            listening.check_audio(old, pcm(new.samples[:-2], 2), support, omitted, timing=TIMING, sample_rate=8)
        live_tail = pcm(new.samples, 2)
        live_tail.samples[-16:] = array('h', [100, -100, -100, 100]) * 4
        with self.assertRaisesRegex(ValueError, 'tail'):
            listening.check_audio(old, live_tail, support, omitted, timing=TIMING, sample_rate=8)

    def test_copies_raw_reference_and_initialized_phrase_without_changing_gain(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [root / name for name in ('old.wav', 'new.wav', 'support.wav', 'omitted.wav')]
            values = fixture()
            for path, audio in zip(paths, values):
                write_wav(path, audio)
            original = [path.read_bytes() for path in paths]
            timing = root / 'timing.json'
            timing.write_text(json.dumps(TIMING))
            output = root / 'prepared'
            listening.prepare(*paths, output, timing_path=timing, sample_rate=8)
            self.assertEqual((output / 'previous-raw-full.wav').read_bytes(), original[0])
            for filename, audio in zip(('previous-raw-phrase.wav', 'expanded-raw-phrase.wav'), values):
                self.assertEqual(read_pcm16(output / filename).samples, audio.samples[88 * 8 * 2:104 * 8 * 2])
            self.assertEqual([path.read_bytes() for path in paths], original)
            expected_mono = [round((left + right) / 2) for left, right in zip(values[1].samples[::2], values[1].samples[1::2])]
            self.assertEqual(list(read_pcm16(output / 'expanded-mono-diagnostic.wav').samples), expected_mono)
            with self.assertRaisesRegex(ValueError, 'fresh'):
                listening.prepare(*paths, output, timing_path=timing, sample_rate=8)


if __name__ == '__main__':
    unittest.main()
