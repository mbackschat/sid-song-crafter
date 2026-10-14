"""Guard the Billie Jean transfer against an independent note/timing oracle."""

from copy import deepcopy
from dataclasses import asdict
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
STUDY = ROOT / 'scripts/studies/billie-jean'
sys.path.insert(0, str(STUDY))
import billie_jean_player as player
import billie_jean_programs as programs
import billie_jean_score as score

SPEC = importlib.util.spec_from_file_location('billie_jean_elise_preparation', STUDY / 'prepare-elise.py')
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)
PAL_CLOCK = 17734475 / 18
CALL_SECONDS = 19656 / PAL_CLOCK
ROLE_VOICES = {'melody': 0, 'bass': 1, 'harmony': 2}


class BillieJeanTransferTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = ROOT / 'songs/fuer-elise.json'
        composition = ROOT / 'evidence/billie-jean-player/composition.json'
        cls.source = json.loads(source.read_text())
        cls.composition = json.loads(composition.read_text())
        cls.pins = dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            composition_sha256=hashlib.sha256(composition.read_bytes()).hexdigest())
        cls.palette = prepare.load_palette(cls.composition)

    def prepared(self, source=None):
        return prepare.prepare_elise(self.source if source is None else source, self.composition,
            palette=self.palette, **self.pins)

    def expected_events(self):
        return sorted((ROLE_VOICES[voice['name']], event['midi'] - 12,
            3 * round(event['startBeat'] * 60 / 72 / CALL_SECONDS / 3),
            3 * round((event['startBeat'] + event['durationBeats']) * 60 / 72 / CALL_SECONDS / 3))
            for voice in self.source['voices'] for event in voice['events'] if event['startBeat'] < 12)

    def active(self, composition, contexts=False):
        value = deepcopy(composition)
        value['range']['auditCalls'] = value.pop('ending')['startCall']
        return player.compute(value, contexts=contexts)

    def test_all_53_nominal_notes_and_gaps_match_independent_three_call_oracle(self):
        reference, transfer, report = self.prepared()
        self.assertEqual({'melody': 35, 'bass': 6, 'harmony': 12}, report['retainedEvents'])
        expected = self.expected_events()
        self.assertEqual(expected, sorted((event['voice'], event['pitchIndex'], event['firstCall'],
            event['lastCallExclusive']) for event in report['events']))
        self.assertEqual(53, len(expected))
        self.assertLessEqual(report['maximumBoundaryErrorSeconds'], 1.5 * CALL_SECONDS)
        for event in report['events']:
            self.assertAlmostEqual((event['lastCallExclusive'] - event['firstCall']) * CALL_SECONDS
                - event['durationBeats'] * 60 / 72, event['durationErrorSeconds'])
        for value in (reference, transfer):
            expanded = score.expand(value['score'], value['ending']['startCall'])
            actual = sorted((row['voice'], row['state']['baseNote'], row['tick'],
                row['tick'] + 3 * ((row['header'] & 31) + 1))
                for row in expanded['rows'] if row['kind'] == 'note')
            self.assertEqual(expected, actual)
            self.assertEqual([], expanded['wraps'])
            self.assertTrue(all(first % 3 == last % 3 == 0 for _, _, first, last in actual))
            self.assertEqual(1, value['score']['initialDivider'])
            self.assertEqual(2, value['score']['rowDividerReload'])
            self.assertEqual([0, 0, 0], [row['tick'] for row in expanded['rows'][:3]])
            self.assertEqual({'startCall': 501, 'releaseCalls': 32}, value['ending'])
            self.assertEqual(598, value['range']['auditCalls'])
            restarted = score.expand(value['score'], 502)
            self.assertEqual([{'tick': 501, 'voice': 2}], restarted['wraps'])

    def test_candidate_preserves_native_bank_and_shared_filter_ownership(self):
        _, transfer, report = self.prepared()
        self.assertEqual(self.composition['sound']['instruments'], transfer['sound']['instruments'])
        for key, value in self.composition['sound']['programs'].items():
            if key != 'frequencies':
                self.assertEqual(value, transfer['sound']['programs'][key])
        self.assertEqual({'melody': 88, 'bass': 32, 'harmony': 24}, report['candidateInstrumentOffsets'])
        result = self.active(transfer, contexts=True)
        setups = [item for item in result['contexts'] if item['stage'] == 'setup']
        self.assertEqual(53, len(setups))
        self.assertTrue(all(item['path'] == 'hard-restart' for item in setups))
        for item in result['contexts']:
            if item['stage'] in ('setup', 'body') and item['voice'] == 0:
                self.assertEqual(item['filterBefore']['cutoff'], item['filterAfter']['cutoff'])
                self.assertEqual(item['filterBefore']['mode'], item['filterAfter']['mode'])
            if item['stage'] == 'body' and item['voice'] in (1, 2):
                self.assertEqual(48, item['filterAfter']['mode'])
        first = [item for item in result['contexts'] if item['call'] == 0 and item['stage'] in ('setup', 'body')]
        self.assertEqual([2, 1, 0], [item['voice'] for item in first])
        self.assertEqual(6, result['returns'][-1]['filter']['routing'] & 7)
        for role, offset in report['candidateInstrumentOffsets'].items():
            selected = report['palette']['roles'][role]
            self.assertEqual(offset, selected['instrumentOffset'])
            self.assertGreater(selected['observedSetupCount'], 0)
        self.assertFalse(report['palette']['audibleRoleClaim'])

    def test_plain_is_stable_triangle_with_source_envelopes_and_shared_master11(self):
        reference, _, report = self.prepared()
        roles = {voice['name']: voice for voice in self.source['voices']}
        for role, offset in report['referenceInstrumentOffsets'].items():
            instrument = reference['sound']['instruments'][str(offset)]
            self.assertEqual(roles[role]['instrument']['attackDecay'], instrument['attack_decay'])
            self.assertEqual(roles[role]['instrument']['sustainRelease'], instrument['sustain_release'])
            for field in ('pulse_step', 'vibrato_step', 'vibrato_delay', 'filter_enabled', 'filter_initialize'):
                self.assertEqual(0, instrument[field])
            self.assertEqual([0, 126], reference['sound']['programs']['pitches'][offset:offset + 2])
            self.assertEqual(17, reference['sound']['programs']['waveforms'][offset])
        result = self.active(reference, contexts=True)
        for item in result['contexts']:
            if item['stage'] == 'body':
                self.assertEqual(17, item['after']['waveform'])
                self.assertEqual(reference['sound']['programs']['frequencies'][str(item['after']['base_note'])],
                    item['after']['frequency'])
            if item['stage'] == 'global-output':
                self.assertEqual([(0xd418, 11)], item['writes'])
        self.assertEqual({'cutoff': 0, 'mode': 0, 'routing': 0}, result['returns'][-1]['filter'])

    def test_retuning_covers_native_attack_pitches_and_omits_unused_overflow(self):
        reference, transfer, report = self.prepared()
        words = transfer['sound']['programs']['frequencies']
        self.assertEqual(words, reference['sound']['programs']['frequencies'])
        self.assertNotIn('95', words)
        self.assertEqual([95], [item['pitchIndex'] for item in report['tuning']['omittedUnusedIndices']])
        for index, word in words.items():
            target = 440 * 2 ** ((int(index) + 12 - 69) / 12)
            self.assertEqual(round(target * 2**24 / PAL_CLOCK), word)
            self.assertTrue(0 < word <= 65535)
        self.assertAlmostEqual(440, words['57'] * PAL_CLOCK / 2**24, delta=0.04)
        for role, offsets in (('melody', (0, 24)), ('bass', (0, 1)), ('harmony', (0, 12))):
            for event in report['events']:
                if event['role'] == role:
                    self.assertTrue(all(event['pitchIndex'] + offset in report['tuning']['requiredIndices'] for offset in offsets))
        for item in report['tuning']['pitchMapping']:
            target = 440 * 2 ** ((item['midi'] - 69) / 12)
            self.assertAlmostEqual(1200 * math.log2(item['retunedFrequencyWord'] * PAL_CLOCK / 2**24 / target),
                item['retunedCentsError'])
            self.assertLess(abs(item['retunedCentsError']), 1)
        self.assertEqual(self.pins['source_sha256'], report['sourceScoreSha256'])
        self.assertEqual(self.pins['composition_sha256'], report['sourceCompositionSha256'])

    def test_authored_ending_freezes_before_wrap_then_stops_for_64_calls(self):
        reference, transfer, report = self.prepared()
        for label, value in (('reference', reference), ('transfer', transfer)):
            self.assertEqual(533, report['numericValidation'][label]['finalStopCall'])
            self.assertEqual(64, report['numericValidation'][label]['confirmationCalls'])
            result = player.compute(value, contexts=True)
            boundary = result['returns'][500]
            held = [control & 254 for control in boundary['ending']['heldControls']]
            self.assertEqual(held, result['returns'][501]['ending']['heldControls'])
            self.assertEqual([(0xd404 + voice * 7, control) for voice, control in enumerate(held)],
                [(item['address'], item['value']) for item in result['writes'] if item['tick'] == 501])
            for record in result['returns'][501:]:
                self.assertEqual(boundary['score'], record['score'])
                self.assertEqual(boundary['voices'], record['voices'])
                self.assertEqual(boundary['filter'], record['filter'])
            self.assertEqual(2, result['returns'][533]['ending']['phase'])
            self.assertEqual([0, 0, 0], result['returns'][533]['ending']['heldControls'])
            self.assertEqual(0, result['returns'][533]['ending']['modeVolume'] & 15)
            self.assertEqual(64, len(result['returns'][534:]))
            self.assertFalse(any(item['tick'] is not None and item['tick'] > 533 for item in result['writes']))
            self.assertEqual(53, sum(item['stage'] == 'setup' for item in result['contexts']))

    def test_fresh_named_sound_image_has_no_score_aliases_and_preserves_inputs(self):
        original = deepcopy((self.source, self.composition, self.palette))
        first = self.prepared()
        self.assertEqual(first, self.prepared())
        self.assertEqual(original, (self.source, self.composition, self.palette))
        fresh = asdict(programs.VoiceState())
        for key in player.SCORE_INPUTS:
            fresh.pop(key)
        for value in first[:2]:
            self.assertEqual([fresh] * 3, value['initialSound']['voices'])
            self.assertEqual(asdict(programs.FilterState()), value['initialSound']['filter'])
            retained = deepcopy(value)
            self.assertEqual(self.active(value), self.active(value))
            self.assertEqual(retained, value)

    def test_collapsed_notes_gaps_overlap_and_required_attack_overflow_reject(self):
        variants = []
        value = deepcopy(self.source)
        value['voices'][0]['events'][0]['durationBeats'] = 0.00001
        variants.append((value, 'collapsed'))
        value = deepcopy(self.source)
        value['voices'][0]['events'][1].update(startBeat=0.251, durationBeats=0.249)
        variants.append((value, 'collapsed'))
        value = deepcopy(self.source)
        harmony = next(voice for voice in value['voices'] if voice['name'] == 'harmony')
        [event for event in harmony['events'] if event['startBeat'] < 12][-1]['durationBeats'] = 0.49999
        variants.append((value, 'collapsed'))
        value = deepcopy(self.source)
        value['voices'][0]['events'][0]['durationBeats'] = 0.5
        variants.append((value, 'overlap'))
        value = deepcopy(self.source)
        value['voices'][0]['events'][0]['midi'] = 83
        variants.append((value, '16-bit'))
        for value, message in variants:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.prepared(value)

    def test_cli_writes_only_fresh_outputs_and_checks_exact_saved_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'prepared'
            command = [sys.executable, str(STUDY / 'prepare-elise.py'), '--output', str(output)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=20)
            self.assertEqual(0, result.returncode, result.stderr)
            paths = [output / name for name in ('reference.json', 'transfer.json', 'preparation.json')]
            original = [path.read_bytes() for path in paths]
            report = json.loads(original[-1])
            self.assertEqual(hashlib.sha256(original[0]).hexdigest(), report['referenceSha256'])
            self.assertEqual(hashlib.sha256(original[1]).hexdigest(), report['transferSha256'])
            self.assertEqual(0, subprocess.run(command + ['--check'], capture_output=True, timeout=20).returncode)
            self.assertNotEqual(0, subprocess.run(command, capture_output=True, timeout=20).returncode)
            self.assertEqual(original, [path.read_bytes() for path in paths])


if __name__ == '__main__':
    unittest.main()
