from array import array
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import wave


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audio_comparison import read_pcm16

spec = importlib.util.spec_from_file_location('prepare_dual_listening', ROOT / 'scripts/prepare-dual-listening.py')
listening = importlib.util.module_from_spec(spec)
spec.loader.exec_module(listening)


def write_wav(path, samples, *, rate=8, channels=2, width=2):
    values = array('h', samples)
    if sys.byteorder != 'little':
        values.byteswap()
    with wave.open(str(path), 'wb') as output:
        output.setparams((channels, width, rate, 0, 'NONE', 'not compressed'))
        output.writeframes(values.tobytes() if width == 2 else bytes(samples))


class DualListeningTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / 'raw.wav'
        self.output = self.root / 'listening'
        self.pairs = [(1001, 333), (2, 1), (-1001, -333), (0, 0), (7, -11),
                      (3, 5), (-1, 2), (19, 31), (30, 40), (50, 60)]
        write_wav(self.source, [value for pair in self.pairs for value in pair])

    def test_fixed_channel_matrices_window_gap_and_input_preservation(self):
        original = self.source.read_bytes()
        report = listening.prepare_listening(self.source, self.output, start=0, stop=1)
        mono = read_pcm16(self.output / 'dual-mono.wav')
        stereo = read_pcm16(self.output / 'dual-listening-stereo.wav')
        comparison = read_pcm16(self.output / 'three-then-six-voices.wav')
        self.assertEqual((mono.channels, mono.frames, stereo.channels, stereo.frames), (1, 10, 2, 10))
        self.assertEqual(list(mono.samples), [round(.5 * a + .5 * b) for a, b in self.pairs])
        self.assertEqual(list(stereo.samples), [value for a, b in self.pairs
                                              for value in (round(.5 * a + .35 * b), round(.5 * a + .65 * b))])
        for index, sample in enumerate(mono.samples):
            self.assertLessEqual(abs((stereo.samples[2 * index] + stereo.samples[2 * index + 1]) / 2 - sample), 1)
        self.assertEqual(list(comparison.samples), [round(.5 * a) for a, _ in self.pairs[:8]] + [0] * 4 + list(mono.samples[:8]))
        self.assertEqual(comparison.frames, 20)
        self.assertEqual(report['matrices'], {'mono': [[.5, .5]], 'listeningStereo': [[.5, .35], [.5, .65]],
                                              'comparisonPrimary': [[.5, 0]], 'secondChipDiagnostic': [[0, 1.0]]})
        self.assertEqual(report['window']['startFrame'], 0)
        self.assertEqual(report['window']['stopFrame'], 8)
        self.assertEqual(report['gapFrames'], 4)
        self.assertEqual(report['normalization'], 'none')
        self.assertEqual(report['input']['sha256'], hashlib.sha256(original).hexdigest())
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(json.loads((self.output / 'listening.json').read_text()), report)
        self.assertIsNone(report['listeningVerdict'])

    def test_primary_gain_is_equal_across_comparison_segments(self):
        write_wav(self.source, [value for a, _ in self.pairs for value in (a, 0)])
        listening.prepare_listening(self.source, self.output, start=0, stop=1)
        comparison = read_pcm16(self.output / 'three-then-six-voices.wav')
        self.assertEqual(comparison.samples[:8], comparison.samples[12:])
        self.assertEqual(list(comparison.samples[:8]), [round(.5 * a) for a, _ in self.pairs[:8]])

    def test_second_chip_diagnostic_retains_full_raw_channel_and_original_gain(self):
        report = listening.prepare_listening(self.source, self.output, start=0, stop=1)
        diagnostic = read_pcm16(self.output / 'second-chip-only.wav')
        self.assertEqual((diagnostic.channels, diagnostic.frames, diagnostic.sample_rate), (1, len(self.pairs), 8))
        self.assertEqual(list(diagnostic.samples), [b for _, b in self.pairs])
        self.assertEqual(report['matrices']['secondChipDiagnostic'], [[0, 1.0]])
        self.assertIn('diagnostic', report['outputs']['secondChipDiagnostic']['label'].lower())
        self.assertIn('gain 1.0', report['outputs']['secondChipDiagnostic']['label'])
        self.assertEqual(report['outputs']['secondChipDiagnostic']['normalization'], 'none')

    def test_clipped_input_or_mixed_samples_fail_before_creating_output(self):
        for pair in ((-32768, 0), (0, 32767), (30000, 30000), (30174, 27200), (-30176, -27200)):
            with self.subTest(pair=pair):
                write_wav(self.source, list(pair) * 8)
                original = self.source.read_bytes()
                with self.assertRaisesRegex(ValueError, 'clip'):
                    listening.prepare_listening(self.source, self.output, start=0, stop=1)
                self.assertFalse(self.output.exists())
                self.assertEqual(self.source.read_bytes(), original)

    def test_invalid_or_empty_quantized_windows_fail_without_outputs(self):
        for start, stop in ((-1, 1), (1, 1), (1, 2), (math.nan, 1), (0, math.inf), (0, .001), (False, 1)):
            with self.subTest(start=start, stop=stop):
                with self.assertRaisesRegex(ValueError, 'window'):
                    listening.prepare_listening(self.source, self.output, start=start, stop=stop)
                self.assertFalse(self.output.exists())

    def test_existing_directory_and_symlink_are_preserved(self):
        self.output.mkdir()
        sentinel = self.output / 'keep.wav'
        sentinel.write_bytes(b'previous evidence')
        with self.assertRaisesRegex(ValueError, 'fresh'):
            listening.prepare_listening(self.source, self.output, start=0, stop=1)
        self.assertEqual(sentinel.read_bytes(), b'previous evidence')
        link = self.root / 'linked-output'
        link.symlink_to(self.root / 'not-present')
        with self.assertRaisesRegex(ValueError, 'fresh'):
            listening.prepare_listening(self.source, link, start=0, stop=1)
        self.assertTrue(link.is_symlink())

    def test_only_stereo_pcm16_is_accepted(self):
        write_wav(self.source, [1, 2, 3, 4], channels=1)
        with self.assertRaisesRegex(ValueError, 'stereo'):
            listening.prepare_listening(self.source, self.output, start=0, stop=.25)
        write_wav(self.source, [128, 129, 130, 131], width=1)
        with self.assertRaisesRegex(ValueError, 'PCM16'):
            listening.prepare_listening(self.source, self.output, start=0, stop=.25)
        self.assertFalse(self.output.exists())

    def test_tail_metrics_measure_both_quiet_and_nonquiet_inputs_without_requiring_silence(self):
        report = listening.prepare_listening(self.source, self.output, start=0, stop=1)
        self.assertGreater(report['input']['tail']['acRms'], 0)
        self.assertGreater(report['outputs']['mono']['tail']['acRms'], 0)
        write_wav(self.source, [value for pair in self.pairs[:6] + [(0, 0)] * 4 for value in pair])
        report = listening.prepare_listening(self.source, self.root / 'quiet', start=0, stop=1)
        self.assertEqual(report['input']['tail']['acRms'], 0)
        self.assertEqual(report['outputs']['mono']['tail']['acRms'], 0)

    def test_cli_defaults_select_eight_to_sixteen_seconds(self):
        write_wav(self.source, [value for index in range(160) for value in (100 + index, 80 - index)])
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/prepare-dual-listening.py'),
                                 str(self.source), '--output', str(self.output)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((self.output / 'listening.json').read_text())
        self.assertEqual((report['window']['startFrame'], report['window']['stopFrame']), (64, 128))
        self.assertEqual(read_pcm16(self.output / 'three-then-six-voices.wav').frames, 132)


if __name__ == '__main__':
    unittest.main()
