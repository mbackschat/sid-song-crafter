from array import array
import importlib.util
import json
import math
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
import wave


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audio_comparison import Pcm16, read_pcm16


def load_helper():
    spec = importlib.util.spec_from_file_location(
        'centered_native_listening', ROOT / 'scripts/studies/rambo/prepare-centered-native-listening.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pcm(samples, channels=1):
    return Pcm16(8, channels, len(samples) // channels, array('h', samples), '')


def fixture():
    previous, native = [], []
    for frame in range(225 * 8):
        lead = (1200 if frame % 2 else -1200) if frame < 224 * 8 else 0
        support = (300 if frame % 3 else -600) if frame < 200 * 8 else 0
        previous.extend((lead, support))
        native.extend((lead, lead + support))
    diagnostic = pcm([1200, -1200] * (104 * 4))
    proof = dict(passed=True, primaryUnchanged=True,
                 lead=dict(orderedStoresIdentical=True, dataAndSoundIdentical=True, morseIdentical=True),
                 inner=dict(orderedStoresIdentical=True, noteLedgerIdentical=True),
                 phaseHistoryIdentical=False)
    return pcm(previous, 2), pcm(native, 2), diagnostic, diagnostic, proof


def write_wav(path, audio):
    values = array('h', audio.samples)
    if sys.byteorder != 'little':
        values.byteswap()
    with wave.open(str(path), 'wb') as output:
        output.setparams((audio.channels, 2, audio.sample_rate, 0, 'NONE', 'not compressed'))
        output.writeframes(values.tobytes())


class RamboCenteredNativeListeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = load_helper()

    def test_reports_native_bus_and_unscaled_lead_energy_without_claiming_center_perception(self):
        previous, native, source_lead, secondary_lead, proof = fixture()
        report = self.helper.check_audio(previous, native, source_lead, secondary_lead, proof=proof, sample_rate=8)
        self.assertEqual(report['leadDiagnostic']['mainPhrase']['secondaryToSourceAcRmsRatio'], 1)
        self.assertAlmostEqual(report['leadDiagnostic']['mainPhrase']['summedStereoLeadEnergyChangeDb'], 10 * math.log10(2))
        self.assertFalse(report['claims']['phaseCoherentCenterEstablished'])
        self.assertFalse(report['claims']['primaryPcmIdentity'])
        self.assertEqual(report['normalization'], 'none')
        self.assertIsNone(report['listeningVerdict'])

    def test_records_lead_imbalance_as_review_warning_without_changing_gain(self):
        previous, native, source_lead, _, proof = fixture()
        louder = pcm([2400, -2400] * (104 * 4))
        report = self.helper.check_audio(previous, native, source_lead, louder, proof=proof, sample_rate=8)
        self.assertAlmostEqual(report['leadDiagnostic']['mainPhrase']['secondaryMinusSourceDb'], 20 * math.log10(2))
        self.assertTrue(report['leadDiagnostic']['warnings'])
        self.assertEqual(report['normalization'], 'none')

    def test_rejects_invalid_execution_claims(self):
        previous, native, a, b, proof = fixture()
        proof['lead']['orderedStoresIdentical'] = False
        with self.assertRaisesRegex(ValueError, 'source-preservation proof'):
            self.helper.check_audio(previous, native, a, b, proof=proof, sample_rate=8)

    def test_rejects_clipping_truncation_missing_right_closing_body_and_live_tail(self):
        previous, native, a, b, proof = fixture()
        clipped = pcm(native.samples, 2)
        clipped.samples[101] = 32767
        with self.assertRaisesRegex(ValueError, 'rail'):
            self.helper.check_audio(previous, clipped, a, b, proof=proof, sample_rate=8)
        with self.assertRaisesRegex(ValueError, '225'):
            self.helper.check_audio(previous, pcm(native.samples[:-2], 2), a, b, proof=proof, sample_rate=8)
        missing = pcm(native.samples, 2)
        for frame in range(205 * 8, 211 * 8):
            missing.samples[frame * 2 + 1] = 0
        with self.assertRaisesRegex(ValueError, 'closing body'):
            self.helper.check_audio(previous, missing, a, b, proof=proof, sample_rate=8)
        live = pcm(native.samples, 2)
        live.samples[-16:] = array('h', [100, -100, -100, 100]) * 4
        with self.assertRaisesRegex(ValueError, 'tail'):
            self.helper.check_audio(previous, live, a, b, proof=proof, sample_rate=8)

    def test_rejects_empty_mono_fold_down_and_wrong_diagnostic_duration(self):
        previous, native, a, b, proof = fixture()
        canceled = pcm([value for lead in native.samples[::2] for value in (lead, -lead)], 2)
        with self.assertRaisesRegex(ValueError, 'mono'):
            self.helper.check_audio(previous, canceled, a, b, proof=proof, sample_rate=8)
        with self.assertRaisesRegex(ValueError, '104'):
            self.helper.check_audio(previous, native, pcm(a.samples[:-1]), b, proof=proof, sample_rate=8)

    def test_preserves_raw_files_and_exact_initialized_windows(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            previous, native, a, b, proof = fixture()
            paths = [root / name for name in ('previous.wav', 'native.wav', 'source-lead.wav', 'secondary-lead.wav')]
            for path, audio in zip(paths, (previous, native, a, b)):
                write_wav(path, audio)
            original = [path.read_bytes() for path in paths]
            proof_path = root / 'proof.json'
            proof_path.write_text(json.dumps(proof))
            output = root / 'prepared'
            self.helper.prepare(*paths, output, proof_path=proof_path, sample_rate=8)
            self.assertEqual((output / 'previous-raw-full.wav').read_bytes(), original[0])
            self.assertEqual(read_pcm16(output / 'native-raw-phrase.wav').samples, native.samples[88 * 8 * 2:104 * 8 * 2])
            self.assertEqual(read_pcm16(output / 'native-raw-ending.wav').samples, native.samples[205 * 8 * 2:225 * 8 * 2])
            self.assertEqual([path.read_bytes() for path in paths], original)
            with self.assertRaisesRegex(ValueError, 'fresh'):
                self.helper.prepare(*paths, output, proof_path=proof_path, sample_rate=8)


if __name__ == '__main__':
    unittest.main()
