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


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


listening = module('rambo_ensemble_listening', 'scripts/studies/rambo/prepare-ensemble-listening.py')
mixing = module('prepare_dual_listening', 'scripts/prepare-dual-listening.py')


def pcm(samples, channels=1, rate=8):
    return Pcm16(rate, channels, len(samples) // channels, array('h', samples), '')


def write_wav(path, audio):
    samples = array('h', audio.samples)
    if sys.byteorder != 'little':
        samples.byteswap()
    with wave.open(str(path), 'wb') as target:
        target.setparams((audio.channels, 2, audio.sample_rate, 0, 'NONE', 'not compressed'))
        target.writeframes(samples.tobytes())


def complete_raw():
    primary = [(-1200 if frame % 2 else 1200) for frame in range(225 * 8)]
    support = [(-300 if frame % 3 else 600) for frame in range(225 * 8)]
    primary[-8:] = [0] * 8
    support[211 * 8:] = [0] * (14 * 8)
    return pcm(primary), pcm([value for pair in zip(primary, support) for value in pair], 2)


class RamboEnsembleListeningTest(unittest.TestCase):
    def test_contribution_review_flags_quiet_and_loud_without_changing_audio(self):
        primary = [1000, -1000] * 12
        for amplitude, expected in ((100, 'below'), (500, 'inside'), (900, 'above')):
            raw = pcm([value for a in primary for value in (a, amplitude if a > 0 else -amplitude)], 2)
            original = array('h', raw.samples)
            report = listening.contribution(raw)
            self.assertAlmostEqual(report['supportToPrimaryAcRmsRatio'], amplitude / 1000)
            self.assertEqual(report['reviewBandPosition'], expected)
            self.assertEqual(raw.samples, original)
            self.assertFalse(report['audibilityEstablished'])

    def test_each_support_role_must_have_an_actual_signal_residual(self):
        support = pcm([600, -600] * (104 * 4))
        omissions = [pcm([amplitude, -amplitude] * (104 * 4)) for amplitude in (400, 300, 500)]
        report = listening.support_roles(support, omissions)
        self.assertEqual([round(role['residualAcRms']) for role in report], [200, 300, 100])
        self.assertEqual([role['voice'] for role in report], [1, 2, 3])
        with self.assertRaisesRegex(ValueError, 'contribut'):
            listening.support_roles(support, [omissions[0], support, omissions[2]])

    def test_preparation_preserves_centered_mix_reference_and_exact_windows(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            faithful, raw = complete_raw()
            reference_path, raw_path = root / 'faithful.wav', root / 'raw.wav'
            write_wav(reference_path, faithful)
            write_wav(raw_path, raw)
            originals = [path.read_bytes() for path in (reference_path, raw_path)]
            presentation = root / 'presentation'
            mixing.prepare_listening(raw_path, presentation, start=88, stop=104)
            centered = read_pcm16(presentation / 'dual-listening-stereo.wav')
            centered_bytes = (presentation / 'dual-listening-stereo.wav').read_bytes()
            output = root / 'prepared'
            report = listening.prepare(reference_path, raw_path, presentation, output, sample_rate=8)
            doubled = read_pcm16(output / 'faithful-dual-mono.wav')
            expected_reference = array('h', (round(.5 * sample) for sample in faithful.samples))
            self.assertEqual(doubled.samples[::2], expected_reference)
            self.assertEqual(doubled.samples[1::2], expected_reference)
            self.assertEqual(read_pcm16(output / 'ensemble-phrase.wav').samples,
                             centered.samples[88 * 8 * 2:104 * 8 * 2])
            self.assertEqual(read_pcm16(output / 'ensemble-ending.wav').samples,
                             centered.samples[205 * 8 * 2:225 * 8 * 2])
            self.assertEqual(report['windows'][0]['seconds'], [88, 104])
            self.assertEqual(report['matrix'], [[.5, .35], [.5, .65]])
            self.assertEqual(report['referenceMatrix'], [[.5], [.5]])
            self.assertIsNone(report['listeningVerdict'])
            self.assertEqual([path.read_bytes() for path in (reference_path, raw_path)], originals)
            self.assertEqual((presentation / 'dual-listening-stereo.wav').read_bytes(), centered_bytes)
            self.assertEqual(json.loads((output / 'signal.json').read_text()), report)
            with self.assertRaisesRegex(ValueError, 'fresh'):
                listening.prepare(reference_path, raw_path, presentation, output, sample_rate=8)

    def test_health_requires_complete_active_distinct_raw_channels_and_primary_ending(self):
        faithful, raw = complete_raw()
        centered = pcm([value for a, b in zip(raw.samples[::2], raw.samples[1::2])
                        for value in (round(.5 * a + .35 * b), round(.5 * a + .65 * b))], 2)
        listening.check_signal(faithful, raw, centered, sample_rate=8)
        for fault in ('missing-support', 'collapsed', 'clip', 'missing-primary-ending', 'short', 'live-tail'):
            changed = pcm(raw.samples, 2)
            if fault == 'missing-support':
                changed.samples[1::2] = array('h', [0]) * changed.frames
            elif fault == 'collapsed':
                changed.samples[1::2] = changed.samples[::2]
            elif fault == 'clip':
                changed.samples[12] = 32767
            elif fault == 'missing-primary-ending':
                changed.samples[205 * 8 * 2:211 * 8 * 2:2] = array('h', [0]) * (6 * 8)
            elif fault == 'short':
                changed.frames -= 1
                changed.samples = changed.samples[:-2]
            else:
                changed.samples[-16:] = array('h', [100, -100, -100, 100]) * 4
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                listening.check_signal(faithful, changed, centered, sample_rate=8)

    def test_mixed_audio_must_match_the_shared_tools_pinned_matrix_and_inputs(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            faithful, raw = complete_raw()
            reference_path, raw_path = root / 'faithful.wav', root / 'raw.wav'
            write_wav(reference_path, faithful)
            write_wav(raw_path, raw)
            presentation = root / 'presentation'
            mixing.prepare_listening(raw_path, presentation, start=88, stop=104)
            receipt_path = presentation / 'listening.json'
            receipt = json.loads(receipt_path.read_text())
            receipt['matrices']['listeningStereo'] = [[.5, 0], [0, .5]]
            receipt_path.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, 'matrix'):
                listening.prepare(reference_path, raw_path, presentation, root / 'prepared', sample_rate=8)
            self.assertFalse((root / 'prepared').exists())

    def test_centered_pcm_must_obey_the_matrix_even_with_updated_output_hash(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            faithful, raw = complete_raw()
            reference_path, raw_path = root / 'faithful.wav', root / 'raw.wav'
            write_wav(reference_path, faithful)
            write_wav(raw_path, raw)
            presentation = root / 'presentation'
            mixing.prepare_listening(raw_path, presentation, start=88, stop=104)
            centered_path = presentation / 'dual-listening-stereo.wav'
            altered = read_pcm16(centered_path)
            altered.samples[0] += 1
            write_wav(centered_path, altered)
            receipt_path = presentation / 'listening.json'
            receipt = json.loads(receipt_path.read_text())
            receipt['outputs']['stereo']['sha256'] = read_pcm16(centered_path).sha256
            receipt_path.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, 'PCM.*matrix'):
                listening.prepare(reference_path, raw_path, presentation, root / 'prepared', sample_rate=8)
            self.assertFalse((root / 'prepared').exists())


if __name__ == '__main__':
    unittest.main()
