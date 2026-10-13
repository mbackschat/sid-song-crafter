from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('prepare_monty_elise', ROOT / 'scripts/prepare-monty-elise.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
from monty_title_player import compute_player, compute_writes
from monty_title_score import expand_score
SOURCE = json.loads((ROOT / 'songs/fuer-elise.json').read_text())
PROGRAMS = json.loads((ROOT / 'songs/monty-title-source.json').read_text())


class MontyEliseTransferTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.transfer, cls.reference, cls.receipt = prepare.prepare_elise(SOURCE, PROGRAMS)

    def test_packed_rows_preserve_every_source_onset_and_native_pitch_identity(self):
        transfer = self.transfer
        operations = expand_score(transfer['score'], calls=transfer['ending']['start_call'],
                                  initial_state=transfer['initial_state'])['operations']
        actual = [(row['call'], row['voice_index'], row['note'], row['instrument_index'])
                  for row in operations if row['operation'] == 'initialize'
                  and row['instrument_index'] != prepare.REST_INDEX]
        expected = []
        for voice, (role, index) in enumerate(prepare.ROLE_PROGRAMS):
            source_voice = next(row for row in SOURCE['voices'] if row['name'] == role)
            for event in source_voice['events']:
                if event['startBeat'] >= 12:
                    continue
                exact = event['startBeat'] * 60 / SOURCE['quarterBpm'] / (19656 / (17734475 / 18)) / 2
                call = 2 * math.floor(exact + 0.5)
                midi = event['midi']
                words = PROGRAMS['frequency_words']
                note = min(range(96), key=lambda i: abs(69 + 12 * math.log2(words[i] * (17734475 / 18) / 2**24 / 440) - midi))
                expected.append((call, voice, note, index))
        self.assertEqual(sorted(expected), sorted(actual))
        self.assertEqual(53, len(actual))
        self.assertEqual({'bass': 6, 'harmony': 12, 'melody': 35}, self.receipt['retainedEvents'])
        self.assertEqual(PROGRAMS['frequency_words'], transfer['frequency_words'])
        self.assertLess(self.receipt['pitchMapping']['maximumAbsoluteCentsError'], 50)
        self.assertTrue(all(row['bytes'][-1] == 255 and len(row['bytes']) <= 256
                            for row in transfer['score']['patterns']))
        self.assertEqual({0, 1, 2}, {row['voice_index'] for row in transfer['score']['orders']})

    def test_plain_pair_shares_score_calendar_pitch_state_and_ending(self):
        for key in ('score', 'frequency_words', 'frequency_alias_bindings', 'initial_state', 'ending', 'play_calls'):
            self.assertEqual(self.transfer[key], self.reference[key], key)
        for role, index in prepare.ROLE_PROGRAMS:
            patch = self.transfer['instruments'][index]
            self.assertEqual(PROGRAMS['instruments'][index], patch)
            self.assertEqual(0, patch['effects'])
            plain = self.reference['instruments'][index]
            source_patch = next(v['instrument'] for v in SOURCE['voices'] if v['name'] == role)
            self.assertEqual((17, source_patch['attackDecay'], source_patch['sustainRelease'], 0, 0, 0),
                             tuple(plain[name] for name in ('waveform', 'attack_decay', 'sustain_release',
                                                           'vibrato_depth', 'pulse_value', 'effects')))
        self.assertEqual(0, self.transfer['instruments'][prepare.REST_INDEX]['waveform'])
        self.assertEqual(self.transfer['instruments'][prepare.REST_INDEX], self.reference['instruments'][prepare.REST_INDEX])

    def test_full_pair_computes_without_file_access_and_ends_in_actual_silence(self):
        for description in (self.transfer, self.reference):
            original = deepcopy(description)
            with patch('builtins.open', side_effect=AssertionError('No runtime source read')), \
                    patch('io.open', side_effect=AssertionError('No runtime source read')):
                writes = compute_writes(description)
            self.assertEqual(original, description)
            self.assertEqual(description['play_calls'] - 1, writes[-1]['tick'])
            volumes = [row['value'] for row in writes if row['phase'] == 'play' and row['address'] == 0xd418]
            self.assertEqual(0, volumes[-1])
            self.assertEqual([level for level in range(15, -1, -1) for _ in range(4)], volumes[-64:])
            self.assertTrue(compute_player(description)['stopped'])
            start = description['ending']['start_call']
            tail_controls = [row for row in writes if row['phase'] == 'play' and row['tick'] >= start
                             and row['address'] in (0xd404, 0xd40b, 0xd412)]
            self.assertTrue(tail_controls)
            self.assertTrue(all(row['value'] & 1 == 0 for row in tail_controls))
        self.assertNotEqual(compute_writes(self.transfer), compute_writes(self.reference))

    def test_native_gate_lead_and_absolute_calendar_error_are_reported_separately(self):
        timing = self.receipt['timing']
        self.assertEqual((1, 2, 2), (timing['tempoReload'], timing['scheduledCalls'], timing['nativeGateLeadCalls']))
        self.assertLessEqual(timing['maximumMeasuredBoundaryErrorSeconds'], timing['maximumBoundaryErrorBoundSeconds'])
        self.assertGreater(timing['maximumMeasuredGateEndErrorSeconds'], timing['maximumMeasuredBoundaryErrorSeconds'])
        self.assertEqual(timing['sourceEndCall'] + 128, self.transfer['play_calls'])
        self.assertEqual(dict(start_call=timing['sourceEndCall'], release_calls=64, fade_step_calls=4), self.transfer['ending'])

    def test_every_note_emits_its_base_pitch_and_native_gate_release_in_both_pairs(self):
        bpm = prepare.Fraction(str(SOURCE['quarterBpm']))
        for description in (self.transfer, self.reference):
            writes = compute_writes(description)
            stores = {}
            for row in writes:
                if row['phase'] == 'play':
                    stores.setdefault((row['tick'], row['address']), []).append(row['value'])
            for voice, (role, index) in enumerate(prepare.ROLE_PROGRAMS):
                base = 0xd400 + 7 * voice
                patch = description['instruments'][index]
                source_voice = next(row for row in SOURCE['voices'] if row['name'] == role)
                pitches = {entry['midi']: entry['frequencyWord']
                           for entry in description['sourceEvidence']['pitchMapping']['entries']}
                for event in source_voice['events']:
                    if event['startBeat'] >= 12:
                        continue
                    start = prepare.Fraction(str(event['startBeat']))
                    end = start + prepare.Fraction(str(event['durationBeats']))
                    first, last = prepare.call_at(start, bpm), prepare.call_at(end, bpm)
                    word = pitches[event['midi']]
                    self.assertEqual([word & 255], stores[(first, base)])
                    self.assertEqual([word >> 8], stores[(first, base + 1)])
                    self.assertEqual([patch['waveform']], stores[(first, base + 4)])
                    self.assertEqual([patch['waveform'] & 254], stores[(last - 2, base + 4)])

    def test_invalid_source_overlap_boundary_tuning_and_pitch_replacement_reject(self):
        changed = deepcopy(SOURCE)
        changed['voices'][0]['events'][1]['startBeat'] = 0
        with self.assertRaisesRegex(ValueError, 'overlap'):
            prepare.prepare_elise(changed, PROGRAMS)
        changed = deepcopy(SOURCE)
        changed['voices'][0]['events'][34]['durationBeats'] = 2
        with self.assertRaisesRegex(ValueError, 'boundary'):
            prepare.prepare_elise(changed, PROGRAMS)
        changed = deepcopy(PROGRAMS)
        changed['instruments'][prepare.ROLE_PROGRAMS[-1][1]]['effects'] = 4
        with self.assertRaisesRegex(ValueError, 'pitch replacement'):
            prepare.prepare_elise(SOURCE, changed)
        changed = deepcopy(PROGRAMS)
        changed['frequency_words'] = [1] * 96
        with self.assertRaisesRegex(ValueError, 'half a semitone'):
            prepare.prepare_elise(SOURCE, changed)

    def test_long_gaps_split_at_native_duration_limit_and_keep_full_time(self):
        operations = expand_score(self.transfer['score'], calls=self.transfer['ending']['start_call'],
                                  initial_state=self.transfer['initial_state'])['operations']
        bass = [row for row in operations if row['operation'] == 'initialize' and row['voice_index'] == 0]
        self.assertEqual((0, prepare.REST_INDEX), (bass[0]['call'], bass[0]['instrument_index']))
        self.assertEqual((64, prepare.REST_INDEX), (bass[1]['call'], bass[1]['instrument_index']))
        self.assertEqual(prepare.call_at(prepare.Fraction(2), prepare.Fraction(72)), bass[2]['call'])

    def test_cli_check_reproduces_pair_and_fresh_outputs_prevent_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            transfer = Path(directory) / 'transfer.json'
            reference = Path(directory) / 'reference.json'
            command = [sys.executable, str(ROOT / 'scripts/prepare-monty-elise.py'),
                       '--transfer-output', str(transfer), '--reference-output', str(reference)]
            built = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, built.returncode, built.stderr)
            before = (transfer.read_bytes(), reference.read_bytes())
            checked = subprocess.run(command + ['--check'], capture_output=True, text=True)
            self.assertEqual(0, checked.returncode, checked.stderr)
            rejected = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(0, rejected.returncode)
            self.assertIn('fresh', rejected.stderr)
            self.assertEqual(before, (transfer.read_bytes(), reference.read_bytes()))


if __name__ == '__main__':
    unittest.main()
