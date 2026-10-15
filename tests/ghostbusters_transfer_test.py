"""Guard the matched Elise transfer's pitches, native timing and rest ending."""

from copy import deepcopy
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ghostbusters_transfer_preparation',
    ROOT / 'scripts/studies/ghostbusters/prepare-elise.py')
prepare = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prepare
spec.loader.exec_module(prepare)
from sid_clock import NTSC_CLOCK, NTSC_FRAME_CYCLES


def inputs():
    return (json.loads((ROOT / 'songs/fuer-elise.json').read_text()),
        json.loads((ROOT / 'evidence/ghostbusters-player/composition.json').read_text()))


def prepared():
    source, composition = inputs()
    return prepare.prepare_elise(source, composition, source_sha256='source-test',
        composition_sha256='composition-test')


class GhostbustersTransferTest(unittest.TestCase):
    def assert_source_matches_emitted_notes(self, source, composition):
        rate = Fraction(str(NTSC_CLOCK)) / NTSC_FRAME_CYCLES
        bpm = Fraction(str(source['quarterBpm']))

        def source_call(beat):
            quarters = Fraction(str(beat)) * 60 * rate / bpm / 4
            rounded = quarters + Fraction(1, 2)
            return 4 * (rounded.numerator // rounded.denominator)

        expected = []
        for part in source['voices']:
            voice = {'melody': 0, 'bass': 1, 'harmony': 2}[part['name']]
            for event in part['events']:
                if event['startBeat'] >= 12:
                    continue
                midi = event['midi']
                first = source_call(event['startBeat'])
                end_beat = Fraction(str(event['startBeat'])) + Fraction(str(event['durationBeats']))
                word = round(440 * 2 ** ((midi - 69) / 12) * 2**24 / NTSC_CLOCK)
                expected.append((first, source_call(end_beat), voice, midi - 12, word))
        expected.sort(key=lambda row: (row[0], -row[2]))

        computed = prepare.player.compute(composition, contexts=True)
        onsets = [context for context in computed['contexts'] if context['kind'] == 'onset']
        successors = {}
        for voice in range(3):
            selected = [context for context in onsets if context['voice'] == voice]
            for current, following in zip(selected, selected[1:]):
                successors[current['call'], voice] = following['call']
        actual = []
        for context in onsets:
            if context['inputs']['header'] & 64:
                continue
            call, voice = context['call'], context['voice']
            base = 0xd400 + 7 * voice
            emitted = [(row['address'], row['value']) for row in computed['writes']
                if row['phase'] == 'play' and row['tick'] == call and row['address'] in (base, base + 1)]
            self.assertEqual([address for address, _ in emitted], [base + 1, base])
            word = emitted[0][1] << 8 | emitted[1][1]
            actual.append((call, successors[call, voice], voice, context['inputs']['note'], word))
        self.assertEqual(len(actual), 53)
        self.assertEqual(len(expected), 53)
        for ordinal, (emitted, original) in enumerate(zip(actual, expected)):
            self.assertEqual(emitted, original, f'Source pitch/timing differs at note {ordinal}')

    def test_actual_output_matches_source_indices_a440_words_and_note_boundaries(self):
        source, _ = inputs()
        reference, transfer, _ = prepared()
        for label, composition in (('reference', reference), ('transfer', transfer)):
            with self.subTest(version=label):
                self.assert_source_matches_emitted_notes(source, composition)

    def test_independent_source_check_rejects_consistent_midi_minus_eleven(self):
        source, _ = inputs()
        reference, transfer, _ = prepared()
        for composition in (reference, transfer):
            for pattern in composition['score']['patterns'].values():
                for row in pattern['rows']:
                    if 'note' in row:
                        row['note'] += 1
            with self.assertRaisesRegex(AssertionError, 'Source pitch/timing differs'):
                self.assert_source_matches_emitted_notes(source, composition)

    def test_same_ntsc_score_and_a440_bank_preserve_all_53_notes(self):
        reference, transfer, report = prepared()
        self.assertEqual(reference['score'], transfer['score'])
        self.assertEqual(reference['sound']['frequencies'], transfer['sound']['frequencies'])
        self.assertEqual(transfer['target'], prepare.player.TARGET)
        self.assertEqual(report['retainedEvents'], dict(melody=35, bass=6, harmony=12))
        self.assertEqual(len(report['events']), 53)
        source, _ = inputs()
        for role, voice in prepare.ROLES.items():
            expected = [event['midi'] for part in source['voices'] if part['name'] == role
                for event in part['events'] if event['startBeat'] < 12]
            observed = [event['midi'] for event in report['events'] if event['role'] == role]
            self.assertEqual(observed, expected)
        self.assertTrue(all(value['noteSetups'] == 53 for value in report['numericValidation'].values()))

    def test_palette_keeps_native_programs_and_plain_triangles_are_explicit(self):
        reference, transfer, report = prepared()
        _, canonical = inputs()
        for role, index in prepare.NATIVE_INSTRUMENTS.items():
            self.assertEqual(transfer['sound']['patches'][str(index)], canonical['sound']['patches'][str(index)])
            plain = reference['sound']['patches'][str(index)]
            self.assertEqual((plain['control'], plain['vibrato_shift']), (17, 0))
        self.assertEqual(report['physicalRoleVoices'], dict(melody=1, bass=2, harmony=3))
        self.assertFalse(report['palette']['audibleRoleClaim'])

    def test_quarter_grid_quantization_and_native_gate_limits_are_quantified(self):
        _, _, report = prepared()
        self.assertTrue(all(event['firstCall'] % 4 == event['lastCallExclusive'] % 4 == 0
            for event in report['events']))
        self.assertLessEqual(report['maximumBoundaryErrorSeconds'], float(2 * prepare.CALL_SECONDS))
        self.assertLessEqual(report['maximumDurationErrorSeconds'], float(4 * prepare.CALL_SECONDS))
        self.assertTrue(all(event['gateOffCall'] == event['firstCall'] + 4
            for event in report['events']))
        self.assertTrue(all(event['envelopeZeroCall'] == event['lastCallExclusive'] - 4
            for event in report['events']))

    def test_rest_tail_does_not_restart_or_add_notes_inside_render(self):
        reference, transfer, report = prepared()
        for value in (reference, transfer):
            computed = prepare.player.compute(value)
            self.assertFalse(computed['resetCalls'])
            self.assertEqual(len(computed['returns']), report['auditCalls'])
            controls = {address: 0 for address in (0xd404, 0xd40b, 0xd412)}
            for row in computed['writes']:
                if row['address'] in controls:
                    controls[row['address']] = row['value']
                if row['tick'] is not None and row['tick'] >= report['sourceEndCall'] and row['address'] in controls:
                    self.assertFalse(row['value'] & 1)
            self.assertTrue(all(not value & 1 for value in controls.values()))
        self.assertGreater(report['firstPossibleResetCall'], report['auditCalls'])
        self.assertGreater(report['auditCalls'] * float(prepare.CALL_SECONDS), report['renderSeconds'])
        self.assertFalse(report['ending']['waveformStop'])
        self.assertFalse(report['ending']['masterVolumeStop'])

    def test_preparation_is_pure_and_rejects_collapsed_or_overlapping_source_notes(self):
        source, composition = inputs()
        before = deepcopy((source, composition))
        prepare.prepare_elise(source, composition, source_sha256='source-test', composition_sha256='composition-test')
        self.assertEqual((source, composition), before)
        source['voices'][0]['events'][0]['durationBeats'] = 0.001
        with self.assertRaisesRegex(ValueError, 'collapsed'):
            prepare.source_events(source)
        source, _ = inputs()
        source['voices'][0]['events'][1]['startBeat'] = 0.1
        with self.assertRaisesRegex(ValueError, 'overlap'):
            prepare.source_events(source)


if __name__ == '__main__':
    unittest.main()
