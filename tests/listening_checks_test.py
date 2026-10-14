from array import array
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from listening_checks import check_asset, check_audio, check_writes


def write_wav(path, samples, *, rate=8, channels=1, width=2):
    values = array('h', samples)
    if sys.byteorder != 'little':
        values.byteswap()
    with wave.open(str(path), 'wb') as output:
        output.setparams((channels, width, rate, 0, 'NONE', 'not compressed'))
        output.writeframes(values.tobytes() if width == 2 else bytes(samples))


def writes(calls=2):
    rows = [dict(phase='init', tick=None, address=0xd404, value=0)]
    for tick in range(calls):
        rows.extend([dict(phase='play', tick=tick, address=0xd418, value=15),
                     dict(phase='play', tick=tick, address=0xd400, value=tick + 10),
                     dict(phase='play', tick=tick, address=0xd400, value=tick + 10)])
    return rows


class ListeningChecksTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / 'source.json.gz'
        self.candidate = self.root / 'candidate.json'
        self.output = self.root / 'receipts' / 'check.json'
        self.raw = json.dumps(writes(3)).encode()
        self.source.write_bytes(gzip.compress(self.raw))
        self.candidate.write_text(json.dumps(writes(2)))
        self.pin = hashlib.sha256(self.raw).hexdigest()

    def check_writes(self):
        return check_writes(self.source, self.candidate, source_sha256=self.pin, calls=2, output=self.output)

    def test_write_check_keeps_duplicate_order_and_pins_decompressed_source(self):
        originals = [path.read_bytes() for path in (self.source, self.candidate)]
        report = self.check_writes()
        self.assertEqual(7, report['matchedWrites'])
        self.assertEqual(self.pin, report['inputs'][0]['decompressedSha256'])
        self.assertEqual(hashlib.sha256(originals[0]).hexdigest(), report['inputs'][0]['sha256'])
        self.assertEqual(2, report['scope']['playCalls'])
        self.assertFalse(report['scope']['candidatePrefix'])
        self.assertEqual(0, report['excludedCandidateWrites'])
        self.assertFalse(report['claims']['busCycleIdentity'])
        self.assertFalse(report['claims']['perceptualAgreement'])
        self.assertEqual(report, json.loads(self.output.read_text()))
        self.assertEqual(originals, [path.read_bytes() for path in (self.source, self.candidate)])

    def test_write_check_rejects_pin_of_compressed_file_or_wrong_source(self):
        for pin in (hashlib.sha256(self.source.read_bytes()).hexdigest(), '0' * 64):
            with self.subTest(pin=pin), self.assertRaisesRegex(ValueError, 'source SHA-256'):
                check_writes(self.source, self.candidate, source_sha256=pin, calls=2, output=self.output)
        self.assertFalse(self.output.exists())

    def test_write_check_rejects_value_order_duplicate_and_init_changes(self):
        variants = []
        changed = writes()
        changed[2]['value'] += 1
        variants.append(changed)
        changed = writes()
        changed[1:3] = reversed(changed[1:3])
        variants.append(changed)
        variants.append(writes()[:3] + writes()[4:])
        changed = writes()
        changed[0]['value'] = 1
        variants.append(changed)
        for rows in variants:
            with self.subTest(rows=rows):
                self.candidate.write_text(json.dumps(rows))
                with self.assertRaisesRegex(ValueError, 'ordered SID writes differ'):
                    self.check_writes()
        self.assertFalse(self.output.exists())

    def test_write_check_rejects_candidate_extra_calls_and_missing_call_in_both(self):
        self.candidate.write_text(json.dumps(writes(3)))
        with self.assertRaisesRegex(ValueError, 'outside declared'):
            self.check_writes()
        rows = [row for row in writes() if row['tick'] != 1]
        self.raw = json.dumps(rows).encode()
        self.source.write_bytes(gzip.compress(self.raw))
        self.pin = hashlib.sha256(self.raw).hexdigest()
        self.candidate.write_bytes(self.raw)
        with self.assertRaisesRegex(ValueError, 'complete play-call coverage'):
            self.check_writes()

    def test_candidate_prefix_compares_every_music_call_and_records_excluded_stores(self):
        self.candidate.write_text(json.dumps(writes(4)))
        originals = [path.read_bytes() for path in (self.source, self.candidate)]
        report = check_writes(self.source, self.candidate, source_sha256=self.pin, calls=2,
                              candidate_prefix=True, output=self.output)
        self.assertTrue(report['scope']['candidatePrefix'])
        self.assertEqual(7, report['matchedWrites'])
        self.assertEqual(6, report['excludedCandidateWrites'])
        self.assertEqual(self.pin, report['expectedSourceDecompressedSha256'])
        self.assertEqual(hashlib.sha256(originals[1]).hexdigest(), report['inputs'][1]['sha256'])
        self.assertEqual(report, json.loads(self.output.read_text()))
        self.assertEqual(originals, [path.read_bytes() for path in (self.source, self.candidate)])

    def test_candidate_prefix_rejects_invalid_or_unordered_excluded_rows(self):
        variants = []
        for change in ({'phase': 'host'}, {'tick': True}, {'address': 65536}, {'value': 256}):
            rows = writes(3)
            rows[-1].update(change)
            variants.append(rows)
        rows = writes(3)
        rows[-1]['tick'] = 1
        variants.append(rows)
        variants.append(writes(3) + [dict(phase='init', tick=None, address=0xd404, value=0)])
        for rows in variants:
            self.candidate.write_text(json.dumps(rows))
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                check_writes(self.source, self.candidate, source_sha256=self.pin, calls=2,
                              candidate_prefix=True, output=self.output)
        self.assertFalse(self.output.exists())

    def test_candidate_prefix_retains_source_pin_and_exact_init_complete_call_identity(self):
        variants = []
        rows = writes(3)
        rows[0]['value'] = 1
        variants.append(rows)
        rows = writes(3)
        rows[2]['value'] = 40
        variants.append(rows)
        variants.append(writes(3)[:3] + writes(3)[4:])
        variants.append([row for row in writes(3) if row['tick'] != 1])
        for rows in variants:
            self.candidate.write_text(json.dumps(rows))
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                check_writes(self.source, self.candidate, source_sha256=self.pin, calls=2,
                              candidate_prefix=True, output=self.output)
        self.candidate.write_text(json.dumps(writes(3)))
        with self.assertRaisesRegex(ValueError, 'source SHA-256'):
            check_writes(self.source, self.candidate, source_sha256='0' * 64, calls=2,
                          candidate_prefix=True, output=self.output)
        with self.assertRaisesRegex(ValueError, 'boolean'):
            check_writes(self.source, self.candidate, source_sha256=self.pin, calls=2,
                          candidate_prefix=1, output=self.output)
        self.assertFalse(self.output.exists())

    def test_write_check_rejects_invalid_phase_tick_address_value_and_no_init(self):
        for change in ({'phase': 'host'}, {'tick': True}, {'address': 65536}, {'value': 256}):
            rows = writes()
            rows[1].update(change)
            self.candidate.write_text(json.dumps(rows))
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.check_writes()
        self.candidate.write_text(json.dumps(writes()[1:]))
        with self.assertRaisesRegex(ValueError, 'initialization'):
            self.check_writes()

    def test_write_check_rejects_corrupt_gzip_and_json(self):
        self.source.write_bytes(b'bad gzip')
        with self.assertRaises(ValueError):
            self.check_writes()
        self.source.write_bytes(gzip.compress(b'bad json'))
        self.pin = hashlib.sha256(b'bad json').hexdigest()
        with self.assertRaises(ValueError):
            self.check_writes()

    def test_audio_check_retains_measurements_pins_and_originals_without_pcm_claim(self):
        reference, candidate = self.root / 'reference.wav', self.root / 'candidate.wav'
        write_wav(reference, [-100, 100, -100, 100])
        write_wav(candidate, [-200, 200, -200, 200])
        originals = [path.read_bytes() for path in (reference, candidate)]
        report = check_audio(reference, candidate, seconds=0.5, sample_rate=8, channels=1, output=self.output)
        self.assertEqual(4, report['expectedFrames'])
        self.assertEqual([100, 200], [row['acRms'] for row in report['inputs']])
        self.assertFalse(report['claims']['pcmIdentity'])
        self.assertFalse(report['claims']['perceptualAgreement'])
        self.assertEqual(originals, [path.read_bytes() for path in (reference, candidate)])
        self.assertEqual([hashlib.sha256(raw).hexdigest() for raw in originals], [row['sha256'] for row in report['inputs']])

    def test_optional_tail_checks_each_channel_and_retains_dc_separately(self):
        reference, candidate = self.root / 'reference.wav', self.root / 'candidate.wav'
        for path in (reference, candidate):
            write_wav(path, [-100, 100, -100, 100, 5, 5, 5, 5])
        report = check_audio(reference, candidate, seconds=1, sample_rate=8, output=self.output,
                             tail_seconds=0.5, max_tail_ac_rms=1)
        self.assertEqual(4, report['ending']['frames'])
        self.assertEqual('both', report['ending']['target'])
        self.assertEqual([0, 0], [row['acRms'] for row in report['ending']['measurements']])
        self.assertEqual([5, 5], [row['perChannel'][0]['dc'] for row in report['ending']['measurements']])
        self.output.unlink()
        for path in (reference, candidate):
            write_wav(path, [-100, 100, 100, -100, 0, -10, 0, 10, 0, -10, 0, 10], rate=6, channels=2)
        with self.assertRaisesRegex(ValueError, 'tail'):
            check_audio(reference, candidate, seconds=1, sample_rate=6, channels=2, output=self.output,
                        tail_seconds=0.5, max_tail_ac_rms=8)
        self.assertFalse(self.output.exists())

    def test_optional_tail_rejects_incomplete_or_invalid_contract(self):
        reference, candidate = self.root / 'reference.wav', self.root / 'candidate.wav'
        for path in (reference, candidate):
            write_wav(path, [-100, 100, -100, 100])
        for tail, limit in ((None, 1), (0.5, None), (0, 1), (1, 1), (0.001, 1), (0.25, -1), (float('nan'), 1)):
            with self.subTest(tail=tail, limit=limit), self.assertRaises(ValueError):
                check_audio(reference, candidate, seconds=0.5, sample_rate=8, output=self.output,
                            tail_seconds=tail, max_tail_ac_rms=limit)
        self.assertFalse(self.output.exists())

    def test_tail_target_limits_only_selected_tail_and_records_both_full_health_measurements(self):
        reference, candidate = self.root / 'reference.wav', self.root / 'candidate.wav'
        for target in ('reference', 'candidate'):
            selected = reference if target == 'reference' else candidate
            other = candidate if target == 'reference' else reference
            write_wav(selected, [-100, 100, -100, 100, 5, 5, 5, 5])
            write_wav(other, [-100, 100] * 4)
            with self.subTest(target=target):
                with self.assertRaisesRegex(ValueError, 'tail'):
                    check_audio(reference, candidate, seconds=1, sample_rate=8, output=self.output,
                                tail_seconds=0.5, max_tail_ac_rms=1)
                report = check_audio(reference, candidate, seconds=1, sample_rate=8, output=self.output,
                                     tail_seconds=0.5, max_tail_ac_rms=1, tail_target=target)
                self.assertEqual(['reference', 'candidate'], [row['label'] for row in report['inputs']])
                self.assertEqual(target, report['ending']['target'])
                self.assertEqual([target], [row['label'] for row in report['ending']['measurements']])
                self.assertEqual(0, report['ending']['measurements'][0]['acRms'])
                self.assertEqual(5, report['ending']['measurements'][0]['perChannel'][0]['dc'])
                self.assertEqual(report, json.loads(self.output.read_text()))
                self.output.unlink()

    def test_tail_target_requires_complete_tail_contract_and_rejects_unknown_target(self):
        reference, candidate = self.root / 'reference.wav', self.root / 'candidate.wav'
        for target, tail, limit in [('other', 0.5, 1)] + [
            (target, tail, limit) for target in ('reference', 'candidate')
            for tail, limit in ((None, None), (None, 1), (0.5, None))
        ]:
            with self.subTest(target=target, tail=tail, limit=limit), self.assertRaises(ValueError):
                check_audio(reference, candidate, seconds=1, sample_rate=8, output=self.output,
                            tail_seconds=tail, max_tail_ac_rms=limit, tail_target=target)
        self.assertFalse(self.output.exists())

    def test_tail_target_keeps_full_health_checks_on_unselected_input_and_per_channel_tail_limit(self):
        reference, candidate = self.root / 'reference.wav', self.root / 'candidate.wav'
        cases = [([128, 129] * 4, {'width': 1}, 'PCM16'),
                 ([-100, 100] * 4, {'rate': 16}, 'sample rate'),
                 ([-100, 100] * 4, {'channels': 2}, 'channels'),
                 ([-100, 100] * 2, {}, 'frame count'),
                 ([-32768, 100] + [5] * 6, {}, 'clipping'),
                 ([5] * 8, {}, 'AC energy')]
        for target in ('reference', 'candidate'):
            selected = reference if target == 'reference' else candidate
            other = candidate if target == 'reference' else reference
            for samples, options, message in cases:
                write_wav(selected, [-100, 100, -100, 100, 5, 5, 5, 5])
                write_wav(other, samples, **options)
                with self.subTest(target=target, options=options), self.assertRaisesRegex(ValueError, message):
                    check_audio(reference, candidate, seconds=1, sample_rate=8, output=self.output,
                                tail_seconds=0.5, max_tail_ac_rms=1, tail_target=target)
        write_wav(reference, [-100, 100, 100, -100] * 3, rate=6, channels=2)
        write_wav(candidate, [-100, 100, 100, -100, 0, -10, 0, 10, 0, -10, 0, 10], rate=6, channels=2)
        with self.assertRaisesRegex(ValueError, 'tail'):
            check_audio(reference, candidate, seconds=1, sample_rate=6, channels=2, output=self.output,
                        tail_seconds=0.5, max_tail_ac_rms=8, tail_target='candidate')
        self.assertFalse(self.output.exists())

    def test_audio_check_rejects_both_inputs_format_duration_clipping_and_silence(self):
        reference, candidate = self.root / 'reference.wav', self.root / 'candidate.wav'
        cases = [([-100, 100], {'width': 1}, 'PCM16'),
                 ([-100, 100, -100, 100], {'rate': 16}, 'sample rate'),
                 ([-100, 100, -100, 100], {'channels': 2}, 'channels'),
                 ([-100, 100], {}, 'frame count'),
                 ([-32768, 100, 0, 0], {}, 'clipping'),
                 ([32767, 100, 0, 0], {}, 'clipping'),
                 ([0, 0, 0, 0], {}, 'AC energy'),
                 ([50, 50, 50, 50], {}, 'AC energy')]
        for bad_path in (reference, candidate):
            for samples, options, message in cases:
                write_wav(reference, [-100, 100, -100, 100])
                write_wav(candidate, [-100, 100, -100, 100])
                if options.get('width') == 1:
                    samples = [128, 129, 128, 129]
                write_wav(bad_path, samples, **options)
                with self.subTest(path=bad_path, options=options, samples=samples), self.assertRaisesRegex(ValueError, message):
                    check_audio(reference, candidate, seconds=0.5, sample_rate=8, channels=1, output=self.output)
        self.assertFalse(self.output.exists())

    def test_audio_check_rounds_duration_to_sample_frames_and_rejects_invalid_options(self):
        reference, candidate = self.root / 'reference.wav', self.root / 'candidate.wav'
        write_wav(reference, [-100, 100, -100, 100])
        write_wav(candidate, [-100, 100, -100, 100])
        for options in ({'seconds': float('nan')}, {'seconds': -1}, {'sample_rate': 0}, {'channels': 3}):
            arguments = dict(seconds=0.5, sample_rate=8, channels=1, output=self.output)
            arguments.update(options)
            with self.subTest(options=options), self.assertRaises(ValueError):
                check_audio(reference, candidate, **arguments)
        report = check_audio(reference, candidate, seconds=0.51, sample_rate=8, channels=1, output=self.output)
        self.assertEqual(4, report['expectedFrames'])

    def test_receipts_refuse_existing_outputs_and_source_collisions(self):
        self.output.parent.mkdir()
        self.output.write_text('keep')
        with self.assertRaisesRegex(ValueError, 'exists'):
            self.check_writes()
        self.assertEqual('keep', self.output.read_text())
        before = self.candidate.read_bytes()
        with self.assertRaisesRegex(ValueError, 'source'):
            check_writes(self.source, self.candidate, source_sha256=self.pin, calls=2, output=self.candidate)
        self.assertEqual(before, self.candidate.read_bytes())

    def test_receipt_exclusive_creation_preserves_concurrent_evidence(self):
        original_open = Path.open

        def concurrent_open(path, mode='r', *args, **kwargs):
            if path == self.output and mode == 'x':
                with original_open(path, 'w') as concurrent:
                    concurrent.write('keep concurrent evidence')
            return original_open(path, mode, *args, **kwargs)

        with patch.object(Path, 'open', concurrent_open), self.assertRaises(FileExistsError):
            self.check_writes()
        self.assertEqual('keep concurrent evidence', self.output.read_text())

    def test_asset_check_verifies_hash_before_creating_receipt(self):
        source = self.root / 'source.sid'
        source.write_bytes(b'PSID example source')
        pin = hashlib.sha256(source.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            check_asset(source, sha256='0' * 64, output=self.output)
        self.assertFalse(self.output.exists())
        report = check_asset(source, sha256=pin, output=self.output)
        self.assertEqual(pin, report['inputs'][0]['sha256'])

    def test_cli_checks_writes_and_audio_with_explicit_contract(self):
        command = [sys.executable, str(ROOT / 'scripts/check-listening.py')]
        result = subprocess.run(command + ['writes', str(self.source), str(self.candidate), '--source-sha256', self.pin, '--calls', '2', '--output', str(self.output)], capture_output=True, text=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
        self.output.unlink()
        reference, candidate = self.root / 'reference.wav', self.root / 'candidate.wav'
        write_wav(reference, [-100, 100, -100, 100])
        write_wav(candidate, [-100, 100, -100, 100])
        result = subprocess.run(command + ['audio', str(reference), str(candidate), '--seconds', '.5', '--sample-rate', '8', '--output', str(self.output)], capture_output=True, text=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(1, json.loads(self.output.read_text())['expectedChannels'])

    def test_cli_records_explicit_candidate_prefix_and_candidate_tail_scope(self):
        command = [sys.executable, str(ROOT / 'scripts/check-listening.py')]
        self.candidate.write_text(json.dumps(writes(3)))
        result = subprocess.run(command + ['writes', str(self.source), str(self.candidate),
            '--source-sha256', self.pin, '--calls', '2', '--candidate-prefix', '--output', str(self.output)],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(self.output.read_text())
        self.assertTrue(report['scope']['candidatePrefix'])
        self.assertEqual(3, report['excludedCandidateWrites'])
        self.output.unlink()
        reference, candidate = self.root / 'reference.wav', self.root / 'candidate.wav'
        write_wav(reference, [-100, 100] * 4)
        write_wav(candidate, [-100, 100, -100, 100, 5, 5, 5, 5])
        arguments = ['audio', str(reference), str(candidate), '--seconds', '1', '--sample-rate', '8',
            '--tail-target', 'candidate', '--output', str(self.output)]
        result = subprocess.run(command + arguments + ['--tail-seconds', '.5', '--max-tail-ac-rms', '1'],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(self.output.read_text())
        self.assertEqual('candidate', report['ending']['target'])
        self.assertEqual(['candidate'], [row['label'] for row in report['ending']['measurements']])
        self.output.unlink()
        result = subprocess.run(command + arguments, capture_output=True, text=True, timeout=10)
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
