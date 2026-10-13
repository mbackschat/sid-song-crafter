import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from flashdance_player import compute_writes


class FlashdanceSecondaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.secondary = json.loads((ROOT / 'songs/flashdance-secondary.json').read_text())
        cls.primary = json.loads((ROOT / 'songs/flashdance-decoded.json').read_text())
        stop = cls.secondary['score']['range']['stopCall']
        ending = cls.secondary['ending']
        cls.end = stop + ending['releaseCalls'] + 16 * ending['fadeStepCalls']
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('Unexpected source read')), \
                patch.object(Path, 'read_text', side_effect=AssertionError('Unexpected source read')):
            cls.writes = compute_writes(cls.secondary, calls=cls.end + 1)
        cls.by_call = [[] for _ in range(cls.end + 1)]
        registers = {}
        cls.states = []
        for row in cls.writes:
            if row['phase'] == 'init':
                registers[row['address']] = row['value']
            else:
                cls.by_call[row['tick']].append(row)
        for rows in cls.by_call:
            registers.update((row['address'], row['value']) for row in rows)
            cls.states.append(registers.copy())

    def notes(self, role):
        return [row for row in self.secondary['score']['roles'][role]['commands'] if row['kind'] == 'note']

    def primary_chord_classes(self, call):
        part = self.primary['score']['roles']['chord']
        selected = note = None
        for command in part['commands']:
            if command['call'] > call:
                break
            if command['kind'] == 'instrument':
                selected = self.primary['instrumentBindings'][command['instrument']]
            elif command['kind'] == 'note':
                note = command['sourceNote'] + command['transposeSemitones']
        bank = self.primary['programs']
        index = bank['instruments'][str(selected)]['wave_row']
        seen, classes = set(), set()
        while index not in seen:
            seen.add(index)
            row = bank['wave_rows'][str(index)]
            if row['jump'] is not None:
                index = row['jump']
                continue
            if row['control'] & 0xf0:
                classes.add((row['note'] + note if row['mode'] == 'relative' else row['note']) % 12)
            index = (index + 1) & 255
        return classes

    def test_quiet_preload_and_three_distinct_waveform_roles(self):
        families = {'bass': 0x40, 'lead': 0x80, 'chord': 0x10}
        for role, family in families.items():
            part = self.secondary['score']['roles'][role]
            base = 0xd400 + (part['voice'] - 1) * 7
            notes = self.notes(role)
            first = notes[0]['call']
            self.assertTrue(all(state[base + 4] == 0 for state in self.states[:first]))
            self.assertEqual(9, self.states[first][base + 4])
            self.assertEqual(family | 1, self.states[first + 1][base + 4])
            controls = {state[base + 4] for state in self.states[first + 1:self.end]}
            self.assertTrue(controls <= {family, family | 1, 9})
        self.assertEqual(self.primary['programs']['frequency_words'],
                         self.secondary['programs']['frequency_words'])
        self.assertEqual('independently-authored-secondary-arrangement',
                         self.secondary['sourceEvidence']['relationship'])

    def test_pitched_parts_fit_primary_harmony_and_answers_use_a_melody_gap(self):
        words = self.secondary['programs']['frequency_words']
        for role in ('bass', 'chord'):
            voice = self.secondary['score']['roles'][role]['voice'] - 1
            base = 0xd400 + voice * 7
            for note in self.notes(role):
                index = note['sourceNote'] + note['transposeSemitones']
                self.assertIn(index % 12, self.primary_chord_classes(note['call']))
                body = note['call'] + int(note['restart'])
                state = self.states[body]
                self.assertEqual(words[index], state[base] | state[base + 1] << 8)
        lead = self.primary['score']['roles']['lead']['commands']
        opening_end = self.primary['score']['range']['firstScoreCall'] + 512
        for note in self.notes('chord'):
            for body in range(note['call'] + 1, note['call'] + 9):
                self.assertEqual(0x11, self.states[body][0xd412])
                if note['call'] < opening_end:
                    row = next(command for command in reversed(lead)
                               if command['call'] <= body and command['kind'] in ('note', 'hold', 'off'))
                    self.assertEqual('off', row['kind'])
            self.assertEqual(0x10, self.states[note['call'] + 9][0xd412])

    def test_backbeats_land_on_verse_beats_and_release_after_four_body_calls(self):
        verse = self.primary['score']['range']['firstScoreCall'] + 512
        notes = self.notes('lead')
        body_calls = {note['call'] + 1 for note in notes}
        self.assertEqual({verse + bar * 128 + beat for bar in range(8) for beat in (32, 96)}, body_calls)
        expected_pitch = self.secondary['programs']['frequency_words'][90]
        for body in body_calls:
            for call in range(body, body + 4):
                state = self.states[call]
                self.assertEqual(0x81, state[0xd40b])
                self.assertEqual(expected_pitch, state[0xd407] | state[0xd408] << 8)
            self.assertEqual(0x80, self.states[body + 4][0xd40b])

    def test_audibility_revision_emits_higher_level_and_longer_envelopes(self):
        self.assertEqual(12, next(row['value'] for row in reversed(self.writes)
                                  if row['phase'] == 'init' and row['address'] == 0xd418))
        for role, ad, sr in (('bass', 0x48, 0x57), ('lead', 0x04, 0x04), ('chord', 0x03, 0x62)):
            part = self.secondary['score']['roles'][role]
            base = 0xd400 + (part['voice'] - 1) * 7
            first = self.notes(role)[0]['call']
            self.assertEqual(ad, self.states[first][base + 5])
            self.assertEqual(sr, self.states[first][base + 6])

    def test_legato_pad_retains_static_pulse_and_exclusive_filter_ownership(self):
        notes = self.notes('bass')
        self.assertTrue(notes[0]['restart'])
        self.assertTrue(all(not note['restart'] for note in notes[1:]))
        initializers = [row for row in self.writes if row['phase'] == 'play'
                        and row['address'] == 0xd405 and row['value'] == 0]
        self.assertEqual([notes[0]['call']], [row['tick'] for row in initializers])
        self.assertEqual(0, self.secondary['programs']['filter_owner'])
        for state in self.states[notes[0]['call'] + 1:self.end]:
            self.assertEqual(0x600, state[0xd402] | state[0xd403] << 8)
            self.assertEqual(0x60, state[0xd416])
            self.assertEqual(0x21, state[0xd417])

    def test_source_free_ending_matches_primary_scope_and_finishes_silent(self):
        self.assertEqual(self.primary['score']['profile'], self.secondary['score']['profile'])
        self.assertEqual(self.primary['score']['range']['stopCall'], self.secondary['score']['range']['stopCall'])
        self.assertEqual(self.primary['ending'], self.secondary['ending'])
        stop = self.secondary['score']['range']['stopCall']
        for state in self.states[stop:]:
            self.assertTrue(all(state[address] & 1 == 0 for address in (0xd404, 0xd40b, 0xd412)))
        self.assertEqual([0, 0, 0, 0], [self.states[self.end][address] for address in (0xd404, 0xd40b, 0xd412, 0xd418)])


if __name__ == '__main__':
    unittest.main()
