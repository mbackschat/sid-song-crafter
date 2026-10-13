import json
from copy import deepcopy
import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from flashdance_player import compute_writes


def register_states(writes, calls):
    by_call = [[] for _ in range(calls)]
    registers, states = {}, []
    for row in writes:
        if row['phase'] == 'init':
            registers[row['address']] = row['value']
        else:
            by_call[row['tick']].append(row)
    for rows in by_call:
        registers.update((row['address'], row['value']) for row in rows)
        states.append(registers.copy())
    return states


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
        cls.states = register_states(cls.writes, cls.end + 1)

    def notes(self, role):
        return [row for row in self.secondary['score']['roles'][role]['commands'] if row['kind'] == 'note']

    def primary_chord_classes(self, call):
        part = self.primary['score']['roles']['chord']
        selected = active = None
        for command in part['commands']:
            if command['call'] > call:
                break
            if command['kind'] == 'instrument':
                selected = self.primary['instrumentBindings'][command['instrument']]
            elif command['kind'] == 'note' and command['call'] + int(command['restart']) <= call:
                active = selected, command['sourceNote'] + command['transposeSemitones']
        if active is None:
            return set()
        selected, note = active
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

    def pitched_span_conflicts(self, states):
        words = self.secondary['programs']['frequency_words']
        conflicts = []
        for call, state in enumerate(states):
            for role in ('bass', 'chord'):
                base = 0xd400 + (self.secondary['score']['roles'][role]['voice'] - 1) * 7
                control = state[base + 4]
                if control & 0xf0 and not control & 8 and (control & 1 or call >= self.secondary['score']['range']['stopCall']):
                    note = words.index(state[base] | state[base + 1] << 8)
                    if note % 12 not in self.primary_chord_classes(call):
                        conflicts.append((role, call, note))
        return conflicts

    def test_entire_pitched_bodies_and_release_tails_fit_primary_harmony(self):
        conflicts = self.pitched_span_conflicts(self.states)
        self.assertTrue(not conflicts, f'{len(conflicts)} held-note conflicts; first: {conflicts[:8]}')

    def test_delaying_a_legato_change_reintroduces_the_stale_chord_tail(self):
        delayed = deepcopy(self.secondary)
        notes = [row for row in delayed['score']['roles']['bass']['commands'] if row['kind'] == 'note']
        notes[1]['call'] += 8
        writes = compute_writes(delayed, calls=self.end + 1)
        conflicts = self.pitched_span_conflicts(register_states(writes, self.end + 1))
        self.assertTrue(('bass', 131, 34) in conflicts, f'Expected stale B-flat at call131; first conflicts: {conflicts[:8]}')

    def test_quiet_preload_and_three_distinct_waveform_roles(self):
        families = {'bass': 0x10, 'lead': 0x80, 'chord': 0x40}
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

    def test_low_roots_and_fifths_follow_primary_chord_body_onsets(self):
        words = self.secondary['programs']['frequency_words']
        roots = [34, 29, 36, 31, 34, 29, 36, 31, 27, 34, 32, 29]
        calls = [2] + [131 + bar * 128 for bar in range(11)]
        for role, offset in (('bass', 0), ('chord', 7)):
            voice = self.secondary['score']['roles'][role]['voice'] - 1
            base = 0xd400 + voice * 7
            notes = self.notes(role)
            self.assertEqual(calls, [note['call'] for note in notes])
            self.assertEqual([root + offset for root in roots], [note['sourceNote'] for note in notes])
            self.assertEqual([True] + [False] * 11, [note['restart'] for note in notes])
            for i, note in enumerate(notes):
                index = note['sourceNote'] + note['transposeSemitones']
                self.assertEqual(0, note['transposeSemitones'])
                body = note['call'] + int(note['restart'])
                end = notes[i + 1]['call'] if i + 1 < len(notes) else self.secondary['score']['range']['stopCall']
                self.assertEqual(end - note['call'], note['durationCalls'])
                for state in self.states[body:end]:
                    self.assertEqual(words[index], state[base] | state[base + 1] << 8)
                    self.assertEqual(0x11 if role == 'bass' else 0x41, state[base + 4])
            part = self.secondary['score']['roles'][role]
            self.assertEqual(0, part['fineTuneWord'])
            self.assertFalse(any(row['kind'] == 'effect' for row in part['commands']))

    def test_primary_description_is_unchanged(self):
        self.assertEqual('839251c75b3fa12e1b70abb4b0838662e42701b182ae85ca3c539863025cbdba',
                         hashlib.sha256((ROOT / 'songs/flashdance-decoded.json').read_bytes()).hexdigest())

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

    def test_support_pads_have_moderate_sustain_and_the_backbeat_is_preserved(self):
        self.assertEqual(12, next(row['value'] for row in reversed(self.writes)
                                  if row['phase'] == 'init' and row['address'] == 0xd418))
        for role, ad, sr in (('bass', 0x48, 0x47), ('lead', 0x04, 0x04), ('chord', 0x48, 0x37)):
            part = self.secondary['score']['roles'][role]
            base = 0xd400 + (part['voice'] - 1) * 7
            first = self.notes(role)[0]['call']
            self.assertEqual(ad, self.states[first][base + 5])
            self.assertEqual(sr, self.states[first][base + 6])

    def test_legato_pads_retain_static_width_and_share_one_filter_owner(self):
        for address in (0xd405, 0xd413):
            initializers = [row for row in self.writes if row['phase'] == 'play'
                            and row['address'] == address and row['value'] == 0]
            self.assertEqual([2], [row['tick'] for row in initializers])
        self.assertEqual(0, self.secondary['programs']['filter_owner'])
        for state in self.states[3:self.end]:
            self.assertEqual(0x600, state[0xd402] | state[0xd403] << 8)
            self.assertEqual(0x600, state[0xd410] | state[0xd411] << 8)
            self.assertEqual(0x60, state[0xd416])
            self.assertEqual(0x25, state[0xd417])

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
