"""Guard the familiar Take On Me transfer's score, tuning and voice ownership."""

from copy import deepcopy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / 'scripts/studies/take-on-me'
sys.path.insert(0, str(STUDY))
import player

SPEC = importlib.util.spec_from_file_location('take_on_me_elise_preparation', STUDY / 'prepare-elise.py')
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)
PAL_CLOCK = 17734475 / 18
CALL_SECONDS = 19656 / PAL_CLOCK
ROLE_VOICES = {'melody': 2, 'bass': 0, 'harmony': 1}


class TakeOnMeTransferTest(unittest.TestCase):
    def setUp(self):
        source = ROOT / 'songs/fuer-elise.json'
        composition = ROOT / 'evidence/take-on-me-player/composition.json'
        self.source = json.loads(source.read_text())
        self.composition = json.loads(composition.read_text())
        self.pins = dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                        composition_sha256=hashlib.sha256(composition.read_bytes()).hexdigest())

    def prepared(self, source=None):
        return prepare.prepare_elise(self.source if source is None else source, self.composition, **self.pins)

    def expected_events(self):
        return sorted((ROLE_VOICES[voice['name']], event['midi'] - 12,
                       2 * round(event['startBeat'] * 60 / 72 / CALL_SECONDS / 2),
                       2 * round((event['startBeat'] + event['durationBeats']) * 60 / 72 / CALL_SECONDS / 2))
                      for voice in self.source['voices'] for event in voice['events'] if event['startBeat'] < 12)

    def test_both_versions_keep_all_53_pitches_even_call_boundaries_and_source_gaps(self):
        reference, transfer, report = self.prepared()
        self.assertEqual({'melody': 35, 'bass': 6, 'harmony': 12}, report['retainedEvents'])
        expected = self.expected_events()
        recorded = sorted((event['voice'], event['pitchIndex'], event['firstCall'], event['lastCallExclusive'])
                          for event in report['events'])
        self.assertEqual(expected, recorded)
        self.assertEqual(53, len(recorded))
        self.assertLessEqual(report['maximumBoundaryErrorSeconds'], CALL_SECONDS)
        for event in report['events']:
            actual = (event['lastCallExclusive'] - event['firstCall']) * CALL_SECONDS
            self.assertAlmostEqual(actual - event['durationBeats'] * 60 / 72, event['durationErrorSeconds'])
        for composition in (reference, transfer):
            result = player.compute(composition)
            notes = sorted((row['voice'], row['state']['baseNote'], row['tick'],
                            row['tick'] + row['state']['durationTicks'])
                           for row in result['rows'] if row['state']['instrument'] != 0)
            self.assertEqual(expected, notes)
            self.assertTrue(all(first % 2 == last % 2 == 0 for _, _, first, last in notes))
            self.assertEqual({'startCall': 502, 'releaseCalls': 32}, composition['ending'])
            self.assertEqual(599, composition['range']['auditCalls'])
            self.assertTrue(all(voice['control'] == 0 for voice in result['returns'][-1]['voices']))
            self.assertEqual(0, result['returns'][-1]['ending']['modeVolume'] & 15)

    def test_candidate_preserves_native_programs_and_assigns_shared_filter_to_bass(self):
        reference, transfer, report = self.prepared()
        self.assertEqual(self.composition['sound']['instruments'], transfer['sound']['instruments'])
        for name, value in self.composition['sound']['programs'].items():
            if name != 'frequencies':
                self.assertEqual(value, transfer['sound']['programs'][name])
        self.assertEqual(self.composition['mix'], transfer['mix'])
        self.assertEqual({'routing': 0, 'modeVolume': 15}, reference['mix'])
        self.assertEqual({'melody': 1, 'bass': 3, 'harmony': 1}, report['candidateInstruments'])
        computed = player.compute(transfer, contexts=True)
        for entry in computed['contexts']:
            if entry['stage'] == 'setup' and entry['instrument'] != 0:
                self.assertEqual(3 if entry['voice'] == 0 else 1, entry['instrument'])
            if entry['stage'] in ('setup', 'body') and entry['voice'] != 0:
                self.assertEqual(entry['filterBefore'], entry['filterAfter'])
        self.assertEqual([{}, {}, {}], transfer['initialSound']['voices'])
        self.assertEqual({}, transfer['initialSound']['filter'])
        self.assertTrue(all(voice['transpose'] == 0 and voice['arpeggio'] == 0
                            for voice in transfer['score']['initialVoices']))

    def test_plain_uses_source_triangles_and_envelopes_without_modulation_or_filter(self):
        reference, _, report = self.prepared()
        roles = {voice['name']: voice for voice in self.source['voices']}
        for role, index in report['referenceInstruments'].items():
            instrument = reference['sound']['instruments'][str(index)]
            self.assertEqual(17, instrument['onset_control'])
            self.assertEqual(17, instrument['body_control'])
            self.assertEqual(roles[role]['instrument']['attackDecay'], instrument['attack_decay'])
            self.assertEqual(roles[role]['instrument']['sustainRelease'], instrument['sustain_release'])
            for field in ('arpeggio_enabled', 'table_program', 'pulse_program', 'vibrato_program',
                          'filter_program', 'filter_word', 'gate_half', 'release_program'):
                self.assertEqual(0, instrument[field])

    def test_a440_retuning_matches_independent_pitch_oracle_and_omits_unused_overflow(self):
        reference, transfer, report = self.prepared()
        words = transfer['sound']['programs']['frequencies']
        self.assertEqual(words, reference['sound']['programs']['frequencies'])
        self.assertNotIn('95', words)
        self.assertEqual([95], [row['pitchIndex'] for row in report['tuning']['omittedUnusedIndices']])
        for index, word in words.items():
            expected = round(440 * 2 ** ((int(index) + 12 - 69) / 12) * 2**24 / PAL_CLOCK)
            self.assertEqual(expected, word)
            self.assertTrue(0 < word <= 65535)
        self.assertAlmostEqual(440, words['57'] * PAL_CLOCK / 2**24, delta=0.04)
        for row in report['tuning']['pitchMapping']:
            target = 440 * 2 ** ((row['midi'] - 69) / 12)
            cents = 1200 * math.log2(row['retunedFrequencyWord'] * PAL_CLOCK / 2**24 / target)
            self.assertAlmostEqual(cents, row['retunedCentsError'])
            self.assertLess(abs(cents), 1)
            self.assertLess(row['nativeCentsError'], -40)
        self.assertEqual(self.pins['source_sha256'], report['sourceScoreSha256'])
        self.assertEqual(self.pins['composition_sha256'], report['sourceCompositionSha256'])

    def test_unrepresentable_notes_collapsed_notes_gaps_and_overlaps_are_rejected(self):
        variants = []
        value = deepcopy(self.source)
        value['voices'][0]['events'][0]['durationBeats'] = 0.00001
        variants.append((value, 'collapsed'))
        value = deepcopy(self.source)
        value['voices'][0]['events'][1].update(startBeat=0.251, durationBeats=0.249)
        variants.append((value, 'collapsed'))
        value = deepcopy(self.source)
        harmony = next(voice for voice in value['voices'] if voice['name'] == 'harmony')
        selected = [event for event in harmony['events'] if event['startBeat'] < 12]
        selected[-1]['durationBeats'] = 0.49999
        variants.append((value, 'collapsed'))
        value = deepcopy(self.source)
        value['voices'][0]['events'][0]['durationBeats'] = 0.5
        variants.append((value, 'overlap'))
        value = deepcopy(self.source)
        value['voices'][0]['events'][0]['midi'] = 107
        variants.append((value, '16-bit'))
        for value, message in variants:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.prepared(value)

    def test_preparation_and_numeric_execution_are_deterministic_and_preserve_inputs(self):
        original = deepcopy((self.source, self.composition))
        first = self.prepared()
        self.assertEqual(first, self.prepared())
        self.assertEqual(original, (self.source, self.composition))
        for composition in first[:2]:
            before = deepcopy(composition)
            self.assertEqual(player.compute(composition), player.compute(composition))
            self.assertEqual(before, composition)

    def test_cli_prepares_fresh_files_and_checks_saved_bytes_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'prepared'
            command = [sys.executable, str(STUDY / 'prepare-elise.py'), '--output', str(output)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=20)
            self.assertEqual(0, result.returncode, result.stderr)
            paths = [output / name for name in ('reference.json', 'transfer.json', 'preparation.json')]
            originals = [path.read_bytes() for path in paths]
            report = json.loads(paths[-1].read_text())
            self.assertEqual(hashlib.sha256(originals[0]).hexdigest(), report['referenceSha256'])
            self.assertEqual(hashlib.sha256(originals[1]).hexdigest(), report['transferSha256'])
            result = subprocess.run(command + ['--check'], capture_output=True, text=True, timeout=20)
            self.assertEqual(0, result.returncode, result.stderr)
            result = subprocess.run(command, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(0, result.returncode)
            self.assertEqual(originals, [path.read_bytes() for path in paths])


if __name__ == '__main__':
    unittest.main()
