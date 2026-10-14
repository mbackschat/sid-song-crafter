"""Guard preserved Elise notes, native patch behavior and explicit release rows."""

from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('prepare_deflektor_elise',
    ROOT / 'scripts/studies/deflektor/prepare-elise-transfer.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
from deflektor_player import compute_writes
from deflektor_score import expand_score


STUDY = ROOT / 'songs/studies/deflektor-elise-transfer'
SOURCE = json.loads((ROOT / 'songs/fuer-elise.json').read_text())
PROGRAMS = json.loads((ROOT / 'songs/studies/deflektor-reconstruction/title.json').read_text())
MAPPING = json.loads((STUDY / 'mapping.json').read_text())


class DeflektorTransferTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.transfer, cls.reference, cls.report = prepare.prepare(SOURCE, PROGRAMS, MAPPING)

    def expected_notes(self):
        result = []
        for voice, role in enumerate(('melody', 'bass', 'harmony')):
            part = next(row for row in SOURCE['voices'] if row['name'] == role)
            for event in part['events']:
                if event['startBeat'] >= 12:
                    continue
                start = math.floor(event['startBeat'] * 60 / SOURCE['quarterBpm'] * (17734475 / 18) / 19656 + 0.5)
                end = math.floor((event['startBeat'] + event['durationBeats']) * 60 / SOURCE['quarterBpm'] * (17734475 / 18) / 19656 + 0.5)
                result.append((voice, start, end, event['midi']))
        return result

    def test_both_versions_preserve_all_53_source_onsets_pitches_and_gate_ends(self):
        expected = self.expected_notes()
        self.assertEqual(53, len(expected))
        for description in (self.transfer, self.reference):
            expanded = expand_score(description['score'], calls=description['play_calls'])
            actual = [(note['voiceIndex'], note['call'], note['sourceNote'] + 32) for note in expanded['notes']]
            self.assertEqual(sorted((voice, start, midi) for voice, start, _, midi in expected), sorted(actual))
            writes = compute_writes(description)
            for voice, start, end, midi in expected:
                control = 0xd404 + 7 * voice
                gate_writes = [row for row in writes if row['address'] == control]
                sounding = [row for row in gate_writes if start <= row['tick'] <= start + 1 and row['value'] & 1]
                self.assertTrue(sounding, (voice, start))
                first = sounding[0]['tick']
                stores = {row['address']: row['value'] for row in writes if row['tick'] == first}
                word = stores[control - 4] | stores[control - 3] << 8
                actual_midi = 69 + 12 * math.log2(word * (17734475 / 18) / 2**24 / 440)
                self.assertEqual(midi, round(actual_midi))
                self.assertLess(abs((actual_midi - midi) * 100), 1)
                self.assertTrue(any(row['tick'] == end - 1 and row['value'] & 1 == 0 for row in gate_writes), (voice, end))
                self.assertFalse(any(start + 1 <= row['tick'] < end - 1 and row['value'] & 1 == 0
                                     for row in gate_writes), (voice, start, end))

    def test_native_records_and_contextual_selectors_are_preserved(self):
        records = {row['recordOffset']: row for row in self.transfer['score']['recordTable']['records']}
        for voice, record_index in enumerate((6, 3, 7)):
            source = PROGRAMS['score']['recordTable']['records'][record_index]
            ordinary = records[voice * 9]
            self.assertEqual(source['fields'], ordinary['fields'])
            self.assertEqual(source['contextual_resonance_selector'], ordinary['contextual_resonance_selector'])
            final = records[(voice + 3) * 9]
            self.assertEqual(ordinary['fields'][:5] + ordinary['fields'][6:], final['fields'][:5] + final['fields'][6:])
            self.assertGreater(final['fields'][5], ordinary['fields'][5])
            self.assertEqual(ordinary['contextual_resonance_selector'], final['contextual_resonance_selector'])
        for name in ('frequency_words', 'motion_table', 'resonance_table', 'wave_programs'):
            self.assertEqual(PROGRAMS[name], self.transfer[name], name)
        self.assertEqual(self.transfer['score_pitch_programs'], {})

    def test_plain_reference_has_source_triangles_and_same_score_calendar(self):
        for name in ('score', 'play_calls', 'frequency_words', 'profile'):
            if name != 'score':
                self.assertEqual(self.transfer[name], self.reference[name], name)
        for name in ('orders', 'patterns', 'initMappingDefaults'):
            self.assertEqual(self.transfer['score'][name], self.reference['score'][name])
        records = self.reference['score']['recordTable']['records']
        for voice, role in enumerate(('melody', 'bass', 'harmony')):
            source = next(row['instrument'] for row in SOURCE['voices'] if row['name'] == role)
            for index in (voice, voice + 3):
                fields = records[index]['fields']
                self.assertEqual(fields[2:5], [16, source['attackDecay'], source['sustainRelease']])
                self.assertEqual((fields[0], fields[6], fields[7], fields[8]), (0, 0, 0, 0))
                self.assertEqual(records[index]['contextual_resonance_selector'], 0)

    def test_final_rows_keep_modulation_during_release_and_stop_once(self):
        stop = self.report['stopCall']
        for description in (self.transfer, self.reference):
            expanded = expand_score(description['score'], calls=description['play_calls'])
            self.assertEqual(stop, expanded['firstStopCall'])
            for voice in range(3):
                rows = [row for row in expanded['rows'] if row['voiceIndex'] == voice]
                self.assertEqual('note', rows[-1]['rowKind'])
                self.assertEqual(stop, rows[-1]['call'] + rows[-1]['value'])
            writes = compute_writes(description)
            self.assertEqual([(stop, address, 0) for address in (0xd404, 0xd40b, 0xd412)],
                             [(row['tick'], row['address'], row['value']) for row in writes if row['tick'] >= stop])
            self.assertGreaterEqual(description['play_calls'] - stop - 1, 64)
        candidate = compute_writes(self.transfer)
        self.assertGreater(len({(row['address'], row['value']) for row in candidate
            if self.report['sourceEndCall'] < row['tick'] < stop and row['address'] in (0xd400, 0xd401, 0xd402, 0xd403)}), 4)

    def test_saved_data_are_reproducible_and_runtime_is_source_free(self):
        inputs = deepcopy((SOURCE, PROGRAMS, MAPPING))
        prepare.prepare(SOURCE, PROGRAMS, MAPPING)
        self.assertEqual(inputs, (SOURCE, PROGRAMS, MAPPING))
        for name, description in (('transfer.json', self.transfer), ('reference.json', self.reference)):
            self.assertEqual((STUDY / name).read_bytes(), prepare.encoded(description))
            stripped = deepcopy(description)
            stripped.pop('sourceEvidence')
            with patch('builtins.open', side_effect=AssertionError('Runtime opened a file')):
                self.assertEqual(compute_writes(description), compute_writes(stripped))
        self.assertEqual((STUDY / 'preparation.json').read_bytes(), prepare.encoded(self.report))

    def test_invalid_mapping_score_and_unrepresentable_release_reject(self):
        for kind in ('coupled', 'missing-record', 'overlap', 'crossing', 'short', 'long-tail'):
            source, programs, mapping = deepcopy(SOURCE), deepcopy(PROGRAMS), deepcopy(MAPPING)
            if kind == 'coupled':
                programs['score']['recordTable']['records'][6]['fields'][2] |= 6
            elif kind == 'missing-record':
                mapping['roles'][0]['recordIndex'] = 19
            elif kind == 'overlap':
                source['voices'][0]['events'].insert(1, deepcopy(source['voices'][0]['events'][0]))
            elif kind == 'crossing':
                source['voices'][0]['events'][0]['durationBeats'] = 13
            elif kind == 'short':
                source['quarterBpm'] = 100000
            else:
                mapping['ending']['releaseSeconds'] = 10
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                prepare.prepare(source, programs, mapping)


if __name__ == '__main__':
    unittest.main()
