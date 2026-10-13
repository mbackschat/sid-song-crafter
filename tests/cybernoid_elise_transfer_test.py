from copy import deepcopy
from fractions import Fraction
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/studies/cybernoid/prepare-cybernoid-elise.py'
sys.path.insert(0, str(ROOT / 'scripts'))
from cybernoid_player import compute_writes


def source_call(beat, bpm):
    exact = Fraction(str(beat)) * 60 * Fraction(17734475, 18) / (Fraction(str(bpm)) * 19656 * 3)
    return 3 * ((2 * exact.numerator + exact.denominator) // (2 * exact.denominator))


def row_sound(row):
    return next(command['index'] for command in row['commands'] if command['kind'] == 'sound')


def row_pitch(row):
    return next(command['sourceNote'] for command in row['commands'] if command['kind'] == 'note')


class CybernoidEliseTransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('prepare_cybernoid_elise', SCRIPT)
        cls.adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.adapter)
        cls.source = json.loads((ROOT / 'songs/fuer-elise.json').read_text())
        cls.programs = json.loads((ROOT / 'songs/cybernoid-title.json').read_text())
        cls.transfer, cls.reference, cls.receipt = cls.adapter.prepare_elise(cls.source, cls.programs)

    def test_all_fifty_three_events_keep_their_raw_pitch_onset_and_row_end(self):
        voices = {voice['name']: voice for voice in self.source['voices']}
        counts = {}
        clock = Fraction(17734475, 18)
        for number, role, record in ((0, 'bass', 1), (1, 'harmony', 5), (2, 'melody', 17)):
            events = [event for event in voices[role]['events'] if 0 <= event['startBeat'] < 12]
            counts[role] = len(events)
            rows = [row for row in self.transfer['rows'] if row['voiceIndex'] == number]
            notes = [row for row in rows if row_sound(row)]
            self.assertEqual(len(events), len(notes))
            self.assertEqual(0, rows[0]['call'])
            for event, row in zip(events, notes):
                index = min(range(87), key=lambda value: abs(69 + 12 * math.log2(
                    self.transfer['frequency_words'][value] * float(clock) / 2**24 / 440) - event['midi']))
                self.assertEqual((source_call(event['startBeat'], 72), index, record),
                                 (row['call'], row_pitch(row), row_sound(row)))
                end = source_call(event['startBeat'] + event['durationBeats'], 72)
                following = next((other['call'] for other in rows if other['call'] > row['call']),
                                 self.transfer['ending']['start_call'])
                self.assertEqual(end, following, (role, event))
                reload = next(command['reload'] for command in row['commands'] if command['kind'] == 'duration')
                self.assertEqual(end - row['call'], 3 * (reload + 1))
                self.assertTrue(all(command['kind'] not in ('glide', 'arpeggio') for command in row['commands']))
        self.assertEqual({'bass': 6, 'harmony': 12, 'melody': 35}, counts)
        self.assertEqual(53, self.receipt['totalRetainedEvents'])
        self.assertEqual(0, self.receipt['omittedExcerptEvents'])

    def test_rests_cover_source_gaps_without_adding_notes_or_reinitializing_held_notes(self):
        roles = {0: 'bass', 1: 'harmony', 2: 'melody'}
        source = {voice['name']: voice for voice in self.source['voices']}
        for number, role in roles.items():
            events = [event for event in source[role]['events'] if event['startBeat'] < 12]
            rows = [row for row in self.transfer['rows'] if row['voiceIndex'] == number]
            for index, row in enumerate(rows):
                end = rows[index + 1]['call'] if index + 1 < len(rows) else self.transfer['ending']['start_call']
                if row_sound(row) == 0:
                    self.assertEqual(0, row_pitch(row))
                    self.assertFalse(any(source_call(event['startBeat'], 72) < end and
                                         source_call(event['startBeat'] + event['durationBeats'], 72) > row['call']
                                         for event in events), (role, row))
                else:
                    self.assertTrue(any(source_call(event['startBeat'], 72) == row['call'] and
                                        source_call(event['startBeat'] + event['durationBeats'], 72) == end
                                        for event in events), (role, row))

    def test_absolute_pal_calendar_and_native_articulation_have_separate_error_bounds(self):
        timing = self.receipt['timing']
        call_seconds = Fraction(19656, 1) / Fraction(17734475, 18)
        boundaries = {0.0, 12.0}
        for voice in self.source['voices']:
            for event in voice['events']:
                if event['startBeat'] < 12:
                    boundaries.update((event['startBeat'], event['startBeat'] + event['durationBeats']))
        maximum = max(abs(float(source_call(beat, 72) * call_seconds - Fraction(str(beat)) * Fraction(5, 6)))
                      for beat in boundaries)
        self.assertAlmostEqual(maximum, timing['maximumMeasuredBoundaryErrorSeconds'])
        self.assertLessEqual(maximum, float(3 * call_seconds / 2))
        self.assertAlmostEqual(float(3 * call_seconds), timing['nativeGateLeadSeconds'])
        self.assertEqual(501, self.transfer['ending']['start_call'])
        self.assertEqual(629, self.transfer['play_calls'])
        self.assertTrue(all(row['call'] % 3 == 0 for row in self.transfer['rows']))
        self.assertGreater(timing['maximumMeasuredGateEndErrorSeconds'], maximum)

    def test_plain_reference_has_identical_score_calendar_and_lookup_with_neutral_triangles(self):
        for key in ('rows', 'frequency_words', 'initial_state', 'ending', 'play_calls'):
            self.assertEqual(self.transfer[key], self.reference[key], key)
        self.assertEqual(self.programs['frequency_words'], self.transfer['frequency_words'])
        sources = {voice['name']: voice['instrument'] for voice in self.source['voices']}
        for role, index in (('bass', 1), ('harmony', 5), ('melody', 17)):
            self.assertEqual(self.programs['records'][index], self.transfer['records'][index])
            record = self.reference['records'][index]
            self.assertEqual((17, sources[role]['attackDecay'], sources[role]['sustainRelease']),
                             (record['wave'], record['attack_decay'], record['sustain_release']))
            self.assertTrue(all(record[key] == 0 for key in ('pulse_flags', 'packed_gate_filter', 'fx1', 'fx2', 'fx3')))
        self.assertEqual((0x82, 0), (self.transfer['sid_init']['routing'], self.reference['sid_init']['routing']))
        self.assertIn('not an original performance', self.reference['sourceEvidence']['identity'].lower())
        mapping = self.receipt['pitchMapping']
        self.assertGreater(mapping['maximumAbsoluteCentsError'], 30)
        self.assertLess(mapping['maximumAbsoluteCentsError'], 40)

    def test_whole_numeric_models_release_and_finish_silent_without_source_files(self):
        for name, description in (('transfer', self.transfer), ('reference', self.reference)):
            with self.subTest(name=name), patch('builtins.open', side_effect=AssertionError('Model opens a file')), \
                    patch.object(Path, 'read_bytes', side_effect=AssertionError('Model reads a file')):
                writes = compute_writes(description)
            controls = [row for row in writes if row['address'] in (0xd404, 0xd40b, 0xd412)]
            control_at = {(row['tick'], row['address']): row['value'] for row in controls}
            values_at = {(row['tick'], row['address']): row['value'] for row in writes}
            for voice in range(3):
                rows = [row for row in description['rows'] if row['voiceIndex'] == voice]
                for index, row in enumerate(rows):
                    if row_sound(row) == 0:
                        continue
                    end = rows[index + 1]['call'] if index + 1 < len(rows) else description['ending']['start_call']
                    address = 0xd404 + 7 * voice
                    self.assertEqual(1, control_at[end - 4, address] & 1)
                    self.assertEqual(0, control_at[end - 3, address] & 1)
                    frequency = values_at[row['call'], address - 4] | values_at[row['call'], address - 3] << 8
                    self.assertEqual(description['frequency_words'][row_pitch(row)], frequency)
            self.assertTrue(all(row['value'] & 1 == 0 for row in controls
                                if row['tick'] is not None and row['tick'] >= description['ending']['start_call']))
            fades = [row['value'] & 15 for row in writes if row['address'] == 0xd418 and
                     row['tick'] is not None and row['tick'] >= description['ending']['start_call'] + 64]
            self.assertEqual(set(range(16)), set(fades))
            self.assertEqual(0, fades[-1])
            self.assertTrue(all(row['call'] < description['ending']['start_call'] for row in description['rows']))

    def test_preparation_preserves_inputs_and_saved_fixtures_are_deterministic(self):
        source, programs = deepcopy(self.source), deepcopy(self.programs)
        before = deepcopy((source, programs))
        transfer, reference, _ = self.adapter.prepare_elise(source, programs)
        self.assertEqual(before, (source, programs))
        self.assertEqual(self.adapter.encoded(transfer), (ROOT / 'songs/cybernoid-elise-transfer.json').read_bytes())
        self.assertEqual(self.adapter.encoded(reference), (ROOT / 'songs/cybernoid-elise-reference.json').read_bytes())
        transfer['rows'][0]['commands'][-1]['sourceNote'] = 0
        reference['frequency_words'][0] = 0
        self.assertEqual(before, (source, programs))

    def test_unsupported_overlap_boundary_and_calendar_inputs_fail(self):
        mutations = (
            ('overlap', lambda value: value['voices'][0]['events'][0].update(durationBeats=0.5)),
            ('pitch', lambda value: value['voices'][0]['events'][0].update(midi=0)),
            ('quarter-beat', lambda value: value['voices'][0]['events'][0].update(durationBeats=0.125)),
            ('excerpt', lambda value: value['voices'][0]['events'][34].update(durationBeats=1.25)),
            ('duration', lambda value: value['voices'][0]['events'][0].update(durationBeats=0)),
            ('calendar', lambda value: value.update(quarterBpm=100000)),
            ('calendar', lambda value: value.update(quarterBpm=1)),
        )
        for message, mutate in mutations:
            source = deepcopy(self.source)
            mutate(source)
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.adapter.prepare_elise(source, self.programs)

    def test_cli_checks_existing_pair_and_rejects_overwriting_either_output(self):
        checked = subprocess.run([sys.executable, str(SCRIPT), '--check'], capture_output=True, text=True)
        self.assertEqual(0, checked.returncode, checked.stderr)
        with TemporaryDirectory() as folder:
            transfer = Path(folder) / 'transfer.json'
            reference = Path(folder) / 'reference.json'
            reference.write_bytes(b'existing user edit\n')
            command = [sys.executable, str(SCRIPT), '--transfer-output', str(transfer),
                       '--reference-output', str(reference)]
            blocked = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(0, blocked.returncode)
            self.assertIn('fresh', blocked.stderr.lower())
            self.assertFalse(transfer.exists())
            self.assertEqual(b'existing user edit\n', reference.read_bytes())


if __name__ == '__main__':
    unittest.main()
