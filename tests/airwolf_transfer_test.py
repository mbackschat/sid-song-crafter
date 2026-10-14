"""Guard Airwolf's familiar transfer, including its init-consumed first row."""

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / 'scripts/studies/airwolf'
sys.path.insert(0, str(STUDY))
SPEC = importlib.util.spec_from_file_location('airwolf_elise_preparation', STUDY / 'prepare-elise.py')
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)
PAL_CLOCK = 17734475 / 18
CALL_SECONDS = 19656 / PAL_CLOCK
ROLE_VOICES = {'melody': 0, 'bass': 1, 'harmony': 2}
NATIVE_SOUND = dict(voices=[dict(attackDecay=10, sustainRelease=0, control=65),
    dict(attackDecay=10, sustainRelease=0, control=65), dict(attackDecay=9, sustainRelease=0, control=17)],
    volume=15, pulseHigh=[40, 10])


class AirwolfTransferTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = ROOT / 'songs/fuer-elise.json'
        native = ROOT / 'evidence/airwolf-form/complete/score.json'
        cls.source = json.loads(source.read_text())
        retained = json.loads(native.read_text())
        cls.composition = dict(schema='airwolf-composition-v1',
            target=dict(clock='pal', sidModel='MOS6581', sidBase=54272, frameCycles=19656),
            range=dict(auditCalls=2500), rows=retained['rows'], sound=deepcopy(NATIVE_SOUND),
            sourceEvidence=dict(sha256=retained['sourceSha256'], score='evidence/airwolf-form/complete/score.json',
                scoreSha256=hashlib.sha256(native.read_bytes()).hexdigest()))
        cls.native_bytes = (json.dumps(cls.composition, indent=2) + '\n').encode()
        cls.pins = dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            composition_sha256=hashlib.sha256(cls.native_bytes).hexdigest())

    def prepared(self, source=None, composition=None):
        return prepare.prepare_elise(self.source if source is None else source,
            self.composition if composition is None else composition, **self.pins)

    def expected_events(self):
        return sorted((ROLE_VOICES[voice['name']], event['midi'],
            round(event['startBeat'] * 60 / 72 / CALL_SECONDS),
            round((event['startBeat'] + event['durationBeats']) * 60 / 72 / CALL_SECONDS))
            for voice in self.source['voices'] for event in voice['events'] if event['startBeat'] < 12)

    def compute(self, value):
        import airwolf_player
        return airwolf_player.compute(value)

    def test_53_events_use_nearest_frame_boundaries_and_preserve_init_play_offset(self):
        reference, transfer, report = self.prepared()
        self.assertEqual({'melody': 35, 'bass': 6, 'harmony': 12}, report['retainedEvents'])
        expected = self.expected_events()
        self.assertEqual(expected, sorted((item['voice'], item['midi'], item['firstFrame'], item['lastFrameExclusive'])
            for item in report['events']))
        self.assertEqual(53, len(expected))
        self.assertLessEqual(report['maximumBoundaryErrorSeconds'], CALL_SECONDS / 2)
        for item in report['events']:
            self.assertEqual('init' if item['firstFrame'] == 0 else 'play', item['phase'])
            self.assertEqual(None if item['firstFrame'] == 0 else item['firstFrame'] - 1, item['tick'])
            self.assertAlmostEqual((item['lastFrameExclusive'] - item['firstFrame']) * CALL_SECONDS
                - item['durationBeats'] * 60 / 72, item['durationErrorSeconds'])
        for value in (reference, transfer):
            self.assertEqual({'startCall': 500, 'releaseCalls': 32}, value['ending'])
            self.assertEqual(597, value['range']['auditCalls'])
            result = self.compute(value)
            frequency_high = [item for item in result['writes'] if item['address'] in (0xd401, 0xd408, 0xd40f)]
            actual = sorted(((item['address'] - 0xd401) // 7,
                0 if item['phase'] == 'init' else item['tick'] + 1) for item in frequency_high)
            self.assertEqual(sorted((voice, first) for voice, _, first, _ in expected), actual)
            self.assertEqual(53, len(frequency_high))
            self.assertEqual([], result['restartCalls'])
            self.assertEqual([transfer['rows'][0]['notes'][0], 'off', 'off'], transfer['rows'][0]['notes'])

    def test_rows_use_null_for_holds_and_explicit_off_only_at_true_source_gaps(self):
        reference, transfer, _ = self.prepared()
        expected = self.expected_events()
        for value in (reference, transfer):
            cursor, pitched, off, boundaries = 0, [], [], []
            for row in value['rows']:
                boundaries.append(cursor)
                self.assertTrue(1 <= row['duration'] <= 255)
                for voice, note in enumerate(row['notes']):
                    if note == 'off':
                        off.append((voice, cursor))
                    elif note is not None:
                        pitched.append((voice, cursor, note))
                cursor += row['duration'] + 1
            self.assertEqual(501, cursor)
            self.assertEqual(sorted((voice, first) for voice, _, first, _ in expected),
                sorted((voice, first) for voice, first, _ in pitched))
            expected_off = [(1, 0), (2, 0)]
            for voice, _, _, last in expected:
                if last < 501 and not any(other_voice == voice and first == last for other_voice, _, first, _ in expected):
                    expected_off.append((voice, last))
            self.assertEqual(sorted(expected_off), sorted(off))
            self.assertTrue(any(note is None for row in value['rows'] for note in row['notes']))
            self.assertEqual(sorted(set(boundaries)), boundaries)
            held, by_frame = [0, 0, 0], {}
            for item in self.compute(value)['writes']:
                frame = 0 if item['phase'] == 'init' else item['tick'] + 1
                by_frame.setdefault(frame, []).append(item)
            for frame in range(501):
                for item in by_frame.get(frame, []):
                    if item['address'] in (0xd404, 0xd40b, 0xd412):
                        held[(item['address'] - 0xd404) // 7] = item['value']
                for voice in range(3):
                    if not any(other == voice and first <= frame < last for other, _, first, last in expected):
                        self.assertEqual(0, held[voice] & 1)

    def test_static_native_patches_and_raw_pulse_high_are_preserved_in_both(self):
        reference, transfer, report = self.prepared()
        self.assertEqual(NATIVE_SOUND, transfer['sound'])
        plain = deepcopy(NATIVE_SOUND)
        for voice in plain['voices']:
            voice['control'] = 17
        self.assertEqual(plain, reference['sound'])
        self.assertEqual(ROLE_VOICES, report['roleVoices'])
        self.assertEqual([8, 10], report['palette']['pulseHighSignificantNibbles'])
        self.assertEqual([2048, 2560], report['palette']['pulseWidthWordsAssumingResetLow'])
        self.assertFalse(report['palette']['hardwareInitializationClaim'])
        for value in (reference, transfer):
            writes = self.compute(value)['writes']
            self.assertFalse(any(item['address'] in (0xd402, 0xd409, 0xd410, 0xd411)
                or 0xd415 <= item['address'] <= 0xd417 for item in writes))
            self.assertEqual({40}, {item['value'] for item in writes if item['address'] == 0xd403})
            self.assertEqual({10}, {item['value'] for item in writes if item['address'] == 0xd40a})
            for voice in range(3):
                base = 0xd400 + voice * 7
                self.assertEqual({NATIVE_SOUND['voices'][voice]['attackDecay']},
                    {item['value'] for item in writes if item['address'] == base + 5})
                self.assertEqual({0}, {item['value'] for item in writes if item['address'] == base + 6})

    def test_each_frequency_word_matches_independent_a440_oracle_and_source_pins(self):
        reference, transfer, report = self.prepared()
        for event in report['events']:
            target = 440 * 2 ** ((event['midi'] - 69) / 12)
            word = round(target * 2**24 / PAL_CLOCK)
            self.assertEqual(word, event['frequencyWord'])
            self.assertTrue(256 <= word <= 65535)
            self.assertLess(abs(event['centsError']), 1)
        self.assertEqual([row['notes'] for row in reference['rows']], [row['notes'] for row in transfer['rows']])
        expected = sorted((voice, round(440 * 2 ** ((midi - 69) / 12) * 2**24 / PAL_CLOCK), first)
            for voice, midi, first, _ in self.expected_events())
        for value in (reference, transfer):
            writes = self.compute(value)['writes']
            pitches = []
            for index, item in enumerate(writes):
                if item['address'] in (0xd401, 0xd408, 0xd40f):
                    following = writes[index + 1]
                    self.assertEqual(item['address'] - 1, following['address'])
                    self.assertEqual((item['phase'], item['tick']), (following['phase'], following['tick']))
                    pitches.append(((item['address'] - 0xd401) // 7, item['value'] * 256 + following['value'],
                        0 if item['phase'] == 'init' else item['tick'] + 1))
            self.assertEqual(expected, sorted(pitches))
        self.assertEqual(self.pins['source_sha256'], report['sourceScoreSha256'])
        self.assertEqual(self.pins['composition_sha256'], report['sourceCompositionSha256'])
        self.assertEqual(self.composition['sourceEvidence']['sha256'], report['sourceSidSha256'])
        bad = deepcopy(self.composition)
        bad['sourceEvidence']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            self.prepared(composition=bad)
        bad = deepcopy(self.composition)
        bad['sound']['voices'][0]['attackDecay'] = 9
        with self.assertRaisesRegex(ValueError, 'native patches'):
            self.prepared(composition=bad)

    def test_ending_freezes_state_before_rewind_then_stops_for_64_calls(self):
        reference, transfer, report = self.prepared()
        for label, value in (('reference', reference), ('transfer', transfer)):
            self.assertEqual(532, report['numericValidation'][label]['finalStopCall'])
            self.assertEqual(64, report['numericValidation'][label]['confirmationCalls'])
            result = self.compute(value)
            at_end = [(item['address'], item['value']) for item in result['writes'] if item['tick'] == 500]
            self.assertEqual([0xd404, 0xd40b, 0xd412], [address for address, _ in at_end])
            self.assertTrue(all(control & 1 == 0 for _, control in at_end))
            self.assertEqual([(0xd404, 0), (0xd40b, 0), (0xd412, 0), (0xd418, 0)],
                [(item['address'], item['value']) for item in result['writes'] if item['tick'] == 532])
            self.assertFalse(any(item['tick'] is not None and item['tick'] > 532 for item in result['writes']))
            self.assertEqual(597, len(result['returns']))
            boundary = result['returns'][499]
            for state in result['returns'][500:]:
                self.assertEqual(boundary['nextRow'], state['nextRow'])
                self.assertEqual(boundary['countdown'], state['countdown'])
                self.assertEqual([40, 10], state['pulseHigh'])
                for voice in range(3):
                    for field in ('frequency', 'attackDecay', 'sustainRelease'):
                        self.assertEqual(boundary['voices'][voice][field], state['voices'][voice][field])
                    self.assertEqual(0, state['voices'][voice]['control'] & 1)
            self.assertEqual(2, result['returns'][532]['ending']['phase'])
            self.assertEqual(0, result['returns'][532]['volume'])
            self.assertEqual(64, len(result['returns'][533:]))
            unended = deepcopy(value)
            unended.pop('ending')
            unended['range']['auditCalls'] = 501
            self.assertEqual([500], self.compute(unended)['restartCalls'])

    def test_collapsed_notes_gaps_overlaps_and_out_of_range_pitches_reject(self):
        variants = []
        value = deepcopy(self.source)
        value['voices'][0]['events'][0]['durationBeats'] = 0.00001
        variants.append((value, 'collapsed'))
        value = deepcopy(self.source)
        value['voices'][0]['events'][1].update(startBeat=0.251, durationBeats=0.249)
        variants.append((value, 'collapsed'))
        value = deepcopy(self.source)
        value['voices'][0]['events'][0]['durationBeats'] = 0.5
        variants.append((value, 'overlap'))
        value = deepcopy(self.source)
        harmony = next(voice for voice in value['voices'] if voice['name'] == 'harmony')
        [event for event in harmony['events'] if event['startBeat'] < 12][-1]['durationBeats'] = 0.49999
        variants.append((value, 'collapsed'))
        value = deepcopy(self.source)
        value['voices'][0]['events'][0]['durationBeats'] = 0.03
        variants.append((value, 'row segment'))
        value = deepcopy(self.source)
        value['voices'][0]['events'][0]['midi'] = 107
        variants.append((value, '16-bit'))
        value = deepcopy(self.source)
        value['voices'][0]['events'][0]['midi'] = 0
        variants.append((value, 'high byte'))
        for value, message in variants:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.prepared(value)

    def test_preparation_and_initial_state_are_deterministic_and_preserve_inputs(self):
        original = deepcopy((self.source, self.composition))
        first = self.prepared()
        self.assertEqual(first, self.prepared())
        self.assertEqual(original, (self.source, self.composition))
        for value in first[:2]:
            retained = deepcopy(value)
            result = self.compute(value)
            self.assertEqual(result, self.compute(value))
            self.assertEqual(retained, value)
            self.assertEqual([(0xd418, 15), (0xd403, 40), (0xd40a, 10)],
                [(item['address'], item['value']) for item in result['writes'][:3]])
            init = [item for item in result['writes'] if item['phase'] == 'init']
            self.assertEqual(11, len(init))
            self.assertEqual([0xd40b, 0xd412], [item['address'] for item in init[-2:]])
            self.assertEqual(dict(frequency=value['rows'][0]['notes'][0], control=value['sound']['voices'][0]['control'],
                attackDecay=10, sustainRelease=0), result['initial']['voices'][0])
            self.assertEqual([dict(frequency=0, control=0, attackDecay=0, sustainRelease=0)] * 2,
                result['initial']['voices'][1:])
            self.assertEqual(result['initial'], first[2]['numericValidation']['reference' if value == first[0] else 'transfer']['initialState'])

    def test_cli_fresh_outputs_check_bytes_and_bind_actual_composition_path(self):
        with tempfile.TemporaryDirectory() as directory:
            composition = Path(directory) / 'native.json'
            composition.write_bytes(self.native_bytes)
            output = Path(directory) / 'prepared'
            command = [sys.executable, str(STUDY / 'prepare-elise.py'), '--composition', str(composition), '--output', str(output)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=20)
            self.assertEqual(0, result.returncode, result.stderr)
            paths = [output / name for name in ('reference.json', 'transfer.json', 'preparation.json')]
            original = [path.read_bytes() for path in paths]
            report = json.loads(original[-1])
            self.assertEqual(str(composition.resolve()), report['inputFiles']['composition']['path'])
            self.assertEqual(hashlib.sha256(original[0]).hexdigest(), report['referenceSha256'])
            self.assertEqual(hashlib.sha256(original[1]).hexdigest(), report['transferSha256'])
            self.assertEqual(0, subprocess.run(command + ['--check'], capture_output=True, timeout=20).returncode)
            self.assertNotEqual(0, subprocess.run(command, capture_output=True, timeout=20).returncode)
            self.assertEqual(original, [path.read_bytes() for path in paths])


if __name__ == '__main__':
    unittest.main()
