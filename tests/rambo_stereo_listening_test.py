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
from audio_comparison import Pcm16, prepare_comparison, read_pcm16

spec = importlib.util.spec_from_file_location(
    'rambo_stereo_listening', ROOT / 'scripts/studies/rambo/prepare-stereo-listening.py')
listening = importlib.util.module_from_spec(spec)
spec.loader.exec_module(listening)


def audio(samples, channels=1, rate=8):
    return Pcm16(rate, channels, len(samples) // channels, array('h', samples), '')


def write_wav(path, value):
    samples = array('h', value.samples)
    if sys.byteorder != 'little':
        samples.byteswap()
    with wave.open(str(path), 'wb') as output:
        output.setparams((value.channels, 2, value.sample_rate, 0, 'NONE', 'not compressed'))
        output.writeframes(samples.tobytes())


def complete_audio():
    reference = [200 if frame % 2 else -200 for frame in range(225 * 8)]
    candidate = [sample for frame in range(225 * 8)
                 for sample in ((100, 300) if frame % 2 else (-100, -300))]
    reference[-8:] = [0] * 8
    candidate[-16:] = [0] * 16
    return audio(reference), audio(candidate, 2)


class RamboStereoListeningTest(unittest.TestCase):
    def test_mono_reference_is_duplicated_without_gain_or_sample_changes(self):
        source = audio([-32768, -3, 0, 7, 32767])
        result = listening.dual_mono(source)
        self.assertEqual((result.sample_rate, result.channels, result.frames), (8, 2, 5))
        self.assertEqual(list(result.samples), [-32768, -32768, -3, -3, 0, 0, 7, 7, 32767, 32767])
        self.assertEqual(list(source.samples), [-32768, -3, 0, 7, 32767])

    def test_mono_sum_averages_channels_with_signed_rounding_and_no_overflow(self):
        source = audio([-32768, -32768, 32767, 32767, -3, 0, 3, 0, -100, 100], 2)
        result = listening.mono_sum(source)
        self.assertEqual((result.channels, result.frames), (1, 5))
        self.assertEqual(list(result.samples), [-32768, 32767, -2, 2, 0])
        with self.assertRaisesRegex(ValueError, 'mono'):
            listening.dual_mono(source)
        with self.assertRaisesRegex(ValueError, 'stereo'):
            listening.mono_sum(audio([1, 2]))

    def test_health_catches_missing_or_collapsed_channels_clipping_and_truncated_source(self):
        reference, candidate = complete_audio()
        report = listening.check_signal(reference, candidate, sample_rate=8)
        self.assertEqual(report['closingBody']['seconds'], [205, 211])
        self.assertEqual(report['durationSeconds'], 225)
        self.assertFalse(report['claims']['pcmIdentity'])
        faults = []
        for mode in ('silent-right', 'same-channels', 'clip', 'lost-closing-body', 'lost-right-closing-body', 'live-tail', 'short'):
            changed = audio(candidate.samples, 2)
            if mode == 'silent-right':
                changed.samples[1::2] = array('h', [0]) * changed.frames
            elif mode == 'same-channels':
                changed.samples[1::2] = changed.samples[0::2]
            elif mode == 'clip':
                changed.samples[12] = 32767
            elif mode == 'lost-closing-body':
                changed.samples[205 * 8 * 2:211 * 8 * 2] = array('h', [0]) * (6 * 8 * 2)
            elif mode == 'lost-right-closing-body':
                changed.samples[205 * 8 * 2 + 1:211 * 8 * 2:2] = array('h', [0]) * (6 * 8)
            elif mode == 'live-tail':
                changed.samples[-16:] = array('h', [100, -100, -100, 100]) * 4
            else:
                changed.frames -= 1
                changed.samples = changed.samples[:-2]
            faults.append((mode, changed))
        for mode, changed in faults:
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                listening.check_signal(reference, changed, sample_rate=8)
        with self.assertRaisesRegex(ValueError, '225'):
            listening.check_signal(audio(reference.samples[:-1]), candidate, sample_rate=8)

    def test_preparation_preserves_inputs_and_extracts_initialized_windows(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            reference, candidate = complete_audio()
            faithful, stereo = root / 'faithful.wav', root / 'stereo.wav'
            write_wav(faithful, reference)
            write_wav(stereo, candidate)
            original = [path.read_bytes() for path in (faithful, stereo)]
            output = root / 'prepared'
            report = listening.prepare(faithful, stereo, output, sample_rate=8)
            duplicated = read_pcm16(output / 'faithful-dual-mono.wav')
            self.assertEqual(duplicated.samples[::2], reference.samples)
            self.assertEqual(duplicated.samples[1::2], reference.samples)
            self.assertEqual(read_pcm16(output / 'stereo-phrase.wav').samples,
                             candidate.samples[32 * 8 * 2:48 * 8 * 2])
            self.assertEqual(read_pcm16(output / 'stereo-ending.wav').samples,
                             candidate.samples[205 * 8 * 2:225 * 8 * 2])
            self.assertEqual(read_pcm16(output / 'stereo-mono-sum.wav').samples, reference.samples)
            self.assertEqual([path.read_bytes() for path in (faithful, stereo)], original)
            self.assertEqual(json.loads((output / 'signal.json').read_text()), report)
            with self.assertRaisesRegex(ValueError, 'fresh'):
                listening.prepare(faithful, stereo, output, sample_rate=8)

    def test_shared_matching_preserves_the_candidate_channel_ratio(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            a, b = root / 'a.wav', root / 'b.wav'
            write_wav(a, listening.dual_mono(audio([-1000, 1000] * 8)))
            write_wav(b, audio([-200, -600, 200, 600] * 8, 2))
            report = prepare_comparison(a, b, root / 'ab', individual_copies=True)
            matched = read_pcm16(root / 'ab.b.matched.wav')
            gain = report['inputs'][1]['gain']
            self.assertEqual(list(matched.samples),
                             [round(sample * gain) for sample in read_pcm16(b).samples])
            self.assertTrue(all(right == 3 * left for left, right in zip(matched.samples[::2], matched.samples[1::2])))


if __name__ == '__main__':
    unittest.main()
