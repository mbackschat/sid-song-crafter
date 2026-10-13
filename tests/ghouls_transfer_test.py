"""Guard the familiar Ghouls transfer's score, tuning and source-free release."""

from copy import deepcopy
from dataclasses import asdict
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('prepare_ghouls_elise', ROOT / 'scripts/studies/ghouls/prepare-ghouls-elise.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
from ghouls_player import GhoulsPlayer


SOURCE = json.loads((ROOT / 'songs/fuer-elise.json').read_text())
PROGRAMS = json.loads((ROOT / 'songs/ghouls.json').read_text())


class Observation(GhoulsPlayer):
    def __init__(self, description):
        self.operations = []
        self.first_note_states = {}
        super().__init__(description)

    def operation(self, voice, operation, state):
        self.operations.append((voice, deepcopy(operation)))
        if operation['kind'] == 'note':
            self.first_note_states.setdefault(voice, asdict(state))
        return super().operation(voice, operation, state)


class GhoulsTransferTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.transfer, cls.reference, cls.report = prepare.prepare_elise(SOURCE, PROGRAMS)

    def observe(self, description):
        player = Observation(description)
        for call in range(description['range']['auditCalls']):
            player.play(call)
        return player

    def test_all_53_source_notes_and_source_gaps_keep_absolute_pal_boundaries(self):
        roles = ('melody', 'bass', 'harmony')
        expected = []
        words = {int(index): word for index, word in PROGRAMS['frequencyWords'].items() if 1 <= int(index) <= 96 and word}
        for voice, role in enumerate(roles):
            for event in next(row['events'] for row in SOURCE['voices'] if row['name'] == role):
                if event['startBeat'] >= 12:
                    continue
                start = math.floor(event['startBeat'] * 60 / SOURCE['quarterBpm'] * (17734475 / 18) / 19656 + 0.5)
                end = math.floor((event['startBeat'] + event['durationBeats']) * 60 / SOURCE['quarterBpm'] * (17734475 / 18) / 19656 + 0.5)
                note = min(words, key=lambda index: abs(69 + 12 * math.log2(words[index] * (17734475 / 18) / 2**24 / 440) - event['midi']))
                expected.append((voice, start, end, note))
        for description in (self.transfer, self.reference):
            player = self.observe(description)
            actual = [(voice, operation['call'], operation['call'] + operation['duration'], operation['rawNote'])
                      for voice, operation in player.operations if operation['kind'] == 'note']
            self.assertEqual(53, len(actual))
            self.assertEqual(sorted(expected), sorted(actual))
            for voice, start, end, _ in expected:
                gate = 0xd404 + 7 * voice
                writes = [row for row in player.writes if row['phase'] == 'play' and row['address'] == gate]
                self.assertTrue(any(row['tick'] == end and row['value'] & 1 == 0 for row in writes))
                for tick in range(start + 1, end):
                    self.assertFalse(any(row['tick'] == tick and row['value'] & 1 == 0 for row in writes), (voice, start, end, tick))

    def test_versions_share_musical_graph_tuning_and_release_calendar(self):
        for field in ('voices', 'frequencyWords', 'range', 'profile'):
            self.assertEqual(self.transfer[field], self.reference[field], field)
        left, right = self.transfer['program']['nodes'], self.reference['program']['nodes']
        self.assertEqual(set(left), set(right))
        for node, operation in left.items():
            if '-setup-' not in node:
                plain = deepcopy(right[node])
                native = deepcopy(operation)
                if '-gateoff-' in node or node.endswith('-end-gate'):
                    for wrapper in (plain, native):
                        wrapper['variants']['stream']['fields']['stores'][0]['value'] &= 1
                if node.endswith('-final-release'):
                    for wrapper in (plain, native):
                        wrapper['variants']['stream']['fields']['stores'][0]['value'] = 0
                self.assertEqual(native, plain, node)
        self.assertEqual({'melody': 35, 'bass': 6, 'harmony': 12}, self.report['retainedEvents'])
        for voice, role in enumerate(('melody', 'bass', 'harmony')):
            reference = self.reference['initialSound'][voice]
            self.assertEqual(reference['waveform'], 16)
            self.assertEqual((reference['pulse_step'], reference['onset_delay'], reference['frequency_delay_reload'], reference['note_step']), (0, 0, 0, 0))
            stores = right[f'{role}-setup-envelope']['variants']['stream']['fields']['stores']
            source = next(row['instrument'] for row in SOURCE['voices'] if row['name'] == role)
            self.assertEqual([(store['address'], store['value']) for store in stores[:2]],
                             [(0xd405 + 7 * voice, source['attackDecay']), (0xd406 + 7 * voice, source['sustainRelease'])])

    def test_selected_named_patch_preserves_phase_and_excludes_pitch_replacement(self):
        patches = prepare.selected_patches(PROGRAMS)
        for voice, state in enumerate(self.transfer['initialSound']):
            patch_state = patches[voice]['state']
            self.assertEqual((state['pulse_word'], state['pulse_default'], state['pulse_step'], state['pulse_restart']),
                             tuple(patch_state[key] for key in ('pulse_word', 'pulse_default', 'pulse_step', 'pulse_restart')))
            self.assertEqual(self.transfer['pulseFallbacks'][voice], patches[voice]['pulseFallback'])
            self.assertEqual(state['waveform'] & 0x86, 0)
            self.assertEqual((state['frequency_delay_reload'], state['note_step'], state['glide_rate']), (0, 0, 0))
            self.assertEqual((state['transpose'], state['pitch_index_mode']), (0, 0))
        self.assertEqual([patch['ad'] for patch in patches], [12, 5, 12])
        self.assertEqual([patch['sr'] for patch in patches], [15, 15, 15])
        self.assertEqual(self.transfer['initialSound'][1]['onset_delay'], 1)
        player = self.observe(self.transfer)
        for voice, entry in player.first_note_states.items():
            captured = patches[voice]['state']
            self.assertEqual((entry['pulse_word'], entry['pulse_direction']),
                             (captured['pulse_word'], captured['pulse_direction']))

    def test_stop_keeps_all_gates_off_and_state_fixed_through_complete_release_range(self):
        for description in (self.transfer, self.reference):
            player = Observation(description)
            end = self.report['sourceEndCall']
            for call in range(end + 1):
                player.play(call)
            self.assertEqual([voice.enabled for voice in player.score.voices], [0, 0, 0])
            stopped = player.state()
            for call in range(end + 1, description['range']['auditCalls']):
                first = len(player.writes)
                player.play(call)
                self.assertEqual(player.state(), stopped)
                self.assertEqual([(row['address'], row['value']) for row in player.writes[first:]], [(0xd415, 0), (0xd416, 0)])
            shadows = {row['address']: row['value'] for row in player.writes}
            self.assertTrue(all(shadows[0xd404 + 7 * voice] & 1 == 0 for voice in range(3)))
            self.assertGreaterEqual(description['range']['auditCalls'] - end - 1,
                                    math.ceil(3 / float(prepare.CALL_SECONDS)) + 64)

    def test_native_onset_restoration_finishes_before_each_short_note_rest(self):
        player = self.observe(self.transfer)
        notes = [(voice, operation) for voice, operation in player.operations if operation['kind'] == 'note']
        for voice, operation in notes:
            delay = self.transfer['initialSound'][voice]['onset_delay']
            self.assertLess(delay, operation['duration'])
            if delay:
                self.assertTrue(any(row['tick'] == operation['call'] + delay and row['address'] == 0xd404 + 7 * voice
                                    and row['value'] == 17 for row in player.writes))

    def test_only_last_note_changes_native_release_immediately_before_gate_off(self):
        for description in (self.transfer, self.reference):
            player = self.observe(description)
            for voice, role in enumerate(('melody', 'bass', 'harmony')):
                notes = [operation for selected, operation in player.operations if selected == voice and operation['kind'] == 'note']
                last = notes[-1]['call'] + notes[-1]['duration']
                address = 0xd406 + 7 * voice
                releases = [row for row in player.writes if row['phase'] == 'play' and row['address'] == address]
                plain_sr = next(row['instrument']['sustainRelease'] for row in SOURCE['voices'] if row['name'] == role)
                expected = [(notes[0]['call'], 15), (last, 9)] if description is self.transfer else [(notes[0]['call'], plain_sr), (last, plain_sr)]
                self.assertEqual([(row['tick'], row['value']) for row in releases], expected)
                final_write = releases[-1]
                index = player.writes.index(final_write)
                gate = player.writes[index + 1]
                self.assertEqual((gate['tick'], gate['address'], gate['value'] & 1), (last, 0xd404 + 7 * voice, 0))

    def test_saved_descriptions_reproduce_and_runtime_needs_no_source_assets(self):
        for filename, description in (('ghouls-elise-transfer.json', self.transfer), ('ghouls-elise-reference.json', self.reference)):
            self.assertEqual((ROOT / 'songs' / filename).read_bytes(), prepare.encoded(description))
            stripped = deepcopy(description)
            stripped.pop('sourceEvidence')
            with patch('builtins.open', side_effect=AssertionError('Transfer runtime accessed a source file')):
                actual = self.observe(stripped)
            self.assertEqual(actual.writes, self.observe(description).writes)

    def test_rejects_overlap_crossing_unrepresentable_tempo_and_late_onset(self):
        for edit in ('overlap', 'crossing', 'tempo', 'late-onset'):
            source = deepcopy(SOURCE)
            melody = next(row for row in source['voices'] if row['name'] == 'melody')
            programs = deepcopy(PROGRAMS)
            if edit == 'overlap':
                melody['events'].insert(1, deepcopy(melody['events'][0]))
            elif edit == 'crossing':
                melody['events'][0]['durationBeats'] = 13
            elif edit == 'tempo':
                source['quarterBpm'] = 100000
            else:
                next(row for row in source['voices'] if row['name'] == 'bass')['events'][0]['durationBeats'] = 0.024
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                prepare.prepare_elise(source, programs)


if __name__ == '__main__':
    unittest.main()
