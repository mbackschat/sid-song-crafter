from array import array
from copy import deepcopy
import importlib.util
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
import wave


ROOT = Path(__file__).resolve().parents[1]
SID_BYTES = b'private native SID fixture'
sys.path.insert(0, str(ROOT / 'scripts'))
from audio_comparison import Pcm16, read_pcm16


def load_helper():
    spec = importlib.util.spec_from_file_location(
        'ghostbusters_stereo_listening', ROOT / 'scripts/studies/ghostbusters/prepare-stereo-listening.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pcm(samples, channels=1):
    return Pcm16(8, channels, len(samples) // channels, array('h', samples), '')


def fixture(seconds=245, calls=14389):
    mono, native = [], []
    for frame in range(seconds * 8):
        lead = 1200 if frame % 2 else -1200
        support = 300 if frame % 3 else -600
        mono.append(lead)
        native.extend((lead * 2, lead + support))
    proof = dict(header=dict(sidCount=2, sha256=hashlib.sha256(SID_BYTES).hexdigest(),
                             format='RSID', version=3, clockDeclaration='NTSC', sidModelDeclaration='MOS6581'),
                 cpu=dict(passed=True, checkedMusicCalls=calls, allOrderedStoresMatch=True,
                          sidBases=[0xd400, 0xd420], perBankStores={'54272': 100, '54304': 80},
                          leadMirrorStores=20, sharedVolumeMirrorStores=30, supportStores=10,
                          maximumNmiCyclesIncludingEntry=90, noSpeechNmiDuringMusic=True),
                 vice=dict(passed=True, checkedMusicCalls=calls, completedMusicCalls=calls,
                           sidBases=[0xd400, 0xd420], perBankStores={'54272': 100, '54304': 80},
                           maximumObservedNmiCyclesIncludingEntry=90))
    return pcm(mono), pcm(native, 2), proof


def write_wav(path, audio):
    values = array('h', audio.samples)
    if sys.byteorder != 'little':
        values.byteswap()
    with wave.open(str(path), 'wb') as output:
        output.setparams((audio.channels, 2, audio.sample_rate, 0, 'NONE', 'not compressed'))
        output.writeframes(values.tobytes())


class GhostbustersStereoListeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = load_helper()

    def test_requires_executed_banks_full_call_coverage_and_mirrored_speech_budget(self):
        reference, native, proof = fixture()
        for section, field, value in (
                ('cpu', 'sidBases', [0xd400]), ('vice', 'perBankStores', {'54272': 100, '54304': 0}),
                ('vice', 'completedMusicCalls', 14388), ('cpu', 'sharedVolumeMirrorStores', 0),
                ('cpu', 'supportStores', 0), ('cpu', 'maximumNmiCyclesIncludingEntry', 102),
                ('cpu', 'allOrderedStoresMatch', False)):
            invalid = deepcopy(proof)
            invalid[section][field] = value
            with self.subTest(section=section, field=field), self.assertRaisesRegex(ValueError, 'native proof'):
                self.helper.check_audio(reference, native, proof=invalid, sample_rate=8)

    def test_duplicates_reference_exactly_and_uses_one_full_file_gain_for_both_chip_channels(self):
        reference, native, proof = fixture()
        report, duplicated, matched_reference, matched_native = self.helper.check_audio(
            reference, native, proof=proof, sample_rate=8)
        self.assertEqual(duplicated.samples[::2], reference.samples)
        self.assertEqual(duplicated.samples[1::2], reference.samples)
        self.assertEqual(matched_reference.samples[::2], matched_reference.samples[1::2])
        gain = report['matching']['inputs'][1]['gain']
        self.assertEqual(matched_native.samples, array('h', (round(value * gain) for value in native.samples)))
        self.assertLessEqual(gain, 1)
        self.assertFalse(report['claims']['phaseCoherentCenterEstablished'])
        self.assertFalse(report['claims']['musicalAcceptanceEstablished'])
        self.assertIsNone(report['listeningVerdict'])
        self.assertGreater(report['phrase']['sideAcRms'], 0)

    def test_rejects_clipping_truncation_wrong_channels_empty_chip_and_missing_ending_body(self):
        reference, native, proof = fixture()
        cases = []
        clipped = pcm(native.samples, 2)
        clipped.samples[20] = 32767
        cases.append((clipped, 'rail'))
        cases.append((pcm(native.samples[:-2], 2), '245'))
        cases.append((pcm(native.samples[::2]), 'stereo'))
        cases.append((pcm([value for left in native.samples[::2] for value in (left, 0)], 2), 'empty chip'))
        ended = pcm(native.samples, 2)
        ended.samples[225 * 8 * 2:] = array('h', [0]) * (20 * 8 * 2)
        cases.append((ended, 'continuation'))
        for audio, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.helper.check_audio(reference, audio, proof=proof, sample_rate=8)

    def test_preparation_keeps_full_inputs_and_same_gain_in_opening_phrase_and_ending(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            reference, native, proof = fixture()
            paths = [root / name for name in ('reference.wav', 'native.wav')]
            for path, audio in zip(paths, (reference, native)):
                write_wav(path, audio)
            originals = [path.read_bytes() for path in paths]
            proof_path = root / 'proof.json'
            proof_path.write_text(json.dumps(proof))
            sid_path = root / 'native.sid'
            sid_path.write_bytes(SID_BYTES)
            output = root / 'prepared'
            report = self.helper.prepare(*paths, output, proof_path=proof_path, sid_path=sid_path, sample_rate=8)
            matched_reference = read_pcm16(output / 'reference-matched-full.wav')
            matched_native = read_pcm16(output / 'native-matched-full.wav')
            for role, start, end in (('opening', 0, 12), ('phrase', 16, 32), ('ending', 225, 245)):
                comparison = read_pcm16(output / f'{role}-mono-then-stereo.ab.wav')
                frames = (end - start) * 8
                self.assertEqual(comparison.samples[:frames * 2], matched_reference.samples[start * 8 * 2:end * 8 * 2])
                self.assertEqual(comparison.samples[-frames * 2:], matched_native.samples[start * 8 * 2:end * 8 * 2])
                receipt = json.loads((output / f'{role}-mono-then-stereo.comparison.json').read_text())
                self.assertEqual(receipt['matching'], 'none')
            self.assertEqual([path.read_bytes() for path in paths], originals)
            self.assertEqual(report['matching']['scopeSeconds'], [0, 245])
            projection = json.loads((output / 'native-proof.json').read_text())
            self.assertEqual(projection['header']['sha256'], hashlib.sha256(SID_BYTES).hexdigest())
            with self.assertRaisesRegex(ValueError, 'fresh'):
                self.helper.prepare(*paths, output, proof_path=proof_path, sid_path=sid_path, sample_rate=8)

    def test_public_proof_projection_excludes_private_checkpoints_and_binds_actual_sid_hash(self):
        _, _, proof = fixture()
        proof['header']['sourceNotes'] = ['must stay private']
        proof['cpu']['checkpoints'] = [{'note': 36}]
        proof['extendedSourceMusic'] = dict(sourceSha256='1' * 64, freshOriginalMusicCpu=True,
            checkedMusicCalls=14389, matchedStores=41803, namedReturns=14389,
            fullIndependentCompiledMusic=dict(completeNumericRange=True, completeCompiledRange=True,
                                             checkpoints=[dict(note=36)]))
        raw = json.dumps(proof).encode()
        report = self.helper.public_native_proof(proof, raw, SID_BYTES)
        serialized = json.dumps(report)
        self.assertNotIn('"checkpoints":', serialized)
        self.assertNotIn('"sourceNotes":', serialized)
        self.assertNotIn('"note":', serialized)
        self.assertEqual(report['privateNativeProof']['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertTrue(report['sourceMusic']['independentCompiled']['completeCompiledRange'])
        with self.assertRaisesRegex(ValueError, 'actual SID'):
            self.helper.public_native_proof(proof, raw, SID_BYTES + b'changed')

    def test_support_control_requires_unchanged_left_and_pre_support_audio_then_reports_right_contribution(self):
        _, native, _ = fixture()
        disabled = pcm(native.samples, 2)
        for frame in range(16 * 8, 32 * 8):
            disabled.samples[frame * 2 + 1] -= 150 if frame % 2 else -150
        report = self.helper.check_support_control(native, disabled, gain=.75, sample_rate=8)
        self.assertTrue(report['leftPcmIdentical'])
        self.assertTrue(report['preSupportPcmIdentical'])
        self.assertEqual(report['phrase']['rightDifferenceAcRms'], 150)
        self.assertEqual(report['phrase']['matchedRightDifferenceAcRms'], 112.5)
        self.assertFalse(report['audibleUsefulnessEstablished'])
        damaged = pcm(disabled.samples, 2)
        damaged.samples[16 * 8 * 2] += 1
        with self.assertRaisesRegex(ValueError, 'left'):
            self.helper.check_support_control(native, damaged, gain=.75, sample_rate=8)
        damaged = pcm(disabled.samples, 2)
        damaged.samples[1] += 1
        with self.assertRaisesRegex(ValueError, 'before'):
            self.helper.check_support_control(native, damaged, gain=.75, sample_rate=8)
        with self.assertRaisesRegex(ValueError, 'contribution'):
            self.helper.check_support_control(native, native, gain=.75, sample_rate=8)

    def test_short_diagnostic_requires_its_own_full_native_proof_and_emits_no_complete_ending_claim(self):
        reference, _, _ = fixture()
        _, native, proof = fixture(seconds=48, calls=2600)
        report, *_ = self.helper.check_audio(reference, native, proof=proof, sample_rate=8, seconds=48, calls=2600)
        self.assertEqual(report['scope'], '48-second initialized diagnostic')
        self.assertNotIn('continuation', report)

    def test_recipe_binds_private_source_and_both_native_proofs_before_matched_publication(self):
        import listening_package
        recipe = json.loads((ROOT / 'config/listening/ghostbusters-stereo.json').read_text())
        listening_package._validate_recipe(recipe)
        stages = {stage['id']: stage for stage in recipe['stages']}
        for name, seconds, calls in (('diagnostic', '48', '2600'), ('complete', '245', '14389')):
            native = stages[name + '-native']
            command = native['command']
            self.assertEqual(command[command.index('--seconds') + 1], seconds)
            self.assertEqual(command[command.index('--probe-calls') + 1], calls)
            self.assertIn('--vice', command)
            self.assertTrue({'.local/research/ghostbusters/Ghostbusters.sid',
                             'scripts/studies/ghostbusters/stereo.py',
                             'songs/studies/ghostbusters-stereo/arrangement.json'} <= set(native['inputs']))
            preparation = stages[name + '-listening']
            self.assertIn('{stage:' + name + '-native}/candidate/verification.json', preparation['inputs'])
            self.assertIn('build/ghostbusters-listening/reconstructed.wav', preparation['inputs'])
        selection = json.loads((ROOT / 'songs/studies/ghostbusters-stereo/audition.json').read_text())
        self.assertEqual(set(selection), {'fullReference', 'fullCandidate', 'openingComparison', 'phraseComparison', 'endingComparison'})
        for label in ('fullReference', 'fullCandidate'):
            self.assertIn('matched-full.wav', recipe['deliverables'][label])
        self.assertIn('evidence/ghostbusters-independent-full/native/composition.json', stages['focused-guards']['inputs'])
        self.assertIn('/native-proof.json', recipe['deliverables']['nativeProof'])


if __name__ == '__main__':
    unittest.main()
