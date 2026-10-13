from copy import deepcopy
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('prepare_shades_elise', ROOT / 'scripts/studies/shades/prepare-shades-elise.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
from shades_player import Player, compute, score_module
from shades_programs import State


def read_song(name):
    return json.loads((ROOT / 'songs' / name).read_text())


def source_call(beat, bpm):
    exact = Fraction(str(beat)) * 60 * 985248 / (Fraction(str(bpm)) * 12326)
    return 1 + (2 * exact.numerator + exact.denominator) // (2 * exact.denominator)


class ShadesEliseTransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = read_song('fuer-elise.json')
        cls.programs = read_song('shades-transfer-programs.json')
        cls.score, cls.reference, cls.receipt = adapter.prepare_elise(cls.source, cls.programs)

    def test_every_preserved_event_has_the_same_pitch_onset_and_note_end(self):
        expanded = score_module.expand_score(self.score)
        role_by_voice = {1: 'bass', 2: 'harmony', 3: 'melody'}
        voices = {voice['name']: voice for voice in self.source['voices']}
        counts = {}
        for number, role in role_by_voice.items():
            expected = [event for event in voices[role]['events'] if 0 <= event['startBeat'] < 12]
            counts[role] = len(expected)
            commands = [row for row in expanded['commands'] if row['voice'] == number]
            notes = [row for row in commands if row['kind'] == 'note']
            self.assertEqual([(source_call(event['startBeat'], 72), event['midi'] - 12, 'on')
                              for event in expected],
                             [(row['call'], row['pitchTableIndex'], row['gate']) for row in notes])
            for event in expected:
                start = source_call(event['startBeat'], 72)
                end = source_call(event['startBeat'] + event['durationBeats'], 72)
                following = next(row for row in commands if row['call'] > start and row['kind'] != 'hold')
                self.assertEqual(end, following['call'], (role, event))
                next_note = any(other['startBeat'] == event['startBeat'] + event['durationBeats']
                                for other in expected)
                self.assertEqual('note' if next_note else 'rest', following['kind'])
            for row in commands:
                if row['kind'] == 'hold':
                    self.assertTrue(any(source_call(event['startBeat'], 72) < row['call'] <
                                        source_call(event['startBeat'] + event['durationBeats'], 72)
                                        for event in expected), (role, row))
        self.assertEqual({'melody': 35, 'bass': 6, 'harmony': 12}, counts)

    def test_absolute_calendar_does_not_accumulate_quarter_beat_rounding_error(self):
        phrase_orders = self.score['orders'][:-1]
        self.assertEqual(48, len(phrase_orders))
        self.assertEqual({16, 17}, {row['rowDurationCalls'] for row in phrase_orders})
        self.assertTrue(all(row['rowCount'] == 1 for row in phrase_orders))
        expected_calls = [source_call(Fraction(index, 4), 72) for index in range(49)]
        expanded = score_module.expand_score(self.score)
        actual_calls = sorted({row['call'] for row in expanded['commands'] if row['orderIndex'] < 48})
        self.assertEqual(expected_calls[:-1], actual_calls)
        release = expanded['selections'][-1]
        self.assertEqual(expected_calls[-1], release['firstRowCall'])
        self.assertEqual(800, release['firstRowCall'])
        self.assertEqual(1, self.score['range']['firstRowCall'])
        self.assertLess(max(abs(float((call - 1) * Fraction(12326, 985248) -
                                     Fraction(index, 4) * Fraction(5, 6)))
                            for index, call in enumerate(expected_calls)), 12326 / 985248 / 2)

    def test_plain_reference_reuses_only_the_score_cadence_and_pitch_table(self):
        self.assertEqual({'clock': 'PAL', 'chip': 'MOS6581', 'timing': 'CIA1 Timer A'}, self.score['profile'])
        self.assertEqual(['pulse-trio'], self.score['instrumentBlocks'])
        self.assertTrue(all(order['instrument'] == 'pulse-trio' and order['timerHigh'] == 0x30
                            and order['transposeSemitones'] == [0, 0, 0]
                            and not order['voice1HighNotesAbsolute'] for order in self.score['orders']))
        self.assertEqual(self.programs['programs']['frequency_words'], self.reference['programs']['frequency_words'])
        self.assertEqual(State().to_dict(), self.reference['preloaded'])
        self.assertEqual(self.programs['preloaded'], self.reference['preloaded'])
        self.assertEqual({'pulse-trio'}, set(self.reference['programs']['blocks']))
        block = self.reference['programs']['blocks']['pulse-trio']
        originals = {voice['name']: voice['instrument'] for voice in self.source['voices']}
        for role, patch in zip(('bass', 'harmony', 'melody'), block['voices']):
            self.assertEqual((16, originals[role]['attackDecay'], originals[role]['sustainRelease']),
                             (patch['control'], patch['attack_decay'], patch['sustain_release']))
            for key in ('pulse_width', 'pulse_up_calls', 'pulse_down_calls', 'pulse_step',
                        'portamento_step', 'vibrato_delay', 'vibrato_extent', 'vibrato_step', 'fine_tune'):
                self.assertEqual(0, patch[key], (role, key))
        self.assertEqual((0, 15, 0), (block['filter']['routing'], block['filter']['mode_volume'],
                                     block['filter']['trigger_mask']))
        self.assertTrue(all(value == 0 for value in block['filter']['contour'].values()))
        self.assertTrue(all(value == 0 for value in block['filter']['percussion_contour'].values()))
        self.assertIn('generated score reference', self.reference['sourceEvidence']['identity'].lower())
        self.assertIn('not an original performance', self.reference['sourceEvidence']['identity'].lower())
        player = Player(self.score, self.reference)
        commands = score_module.expand_score(self.score)['commands']
        while player.tick < self.score['range']['stopCall']:
            player.step()
            for command in (row for row in commands if row['call'] == player.tick and row['kind'] == 'note'):
                voice = player.state.voices[command['voice'] - 1]
                self.assertEqual(self.reference['programs']['frequency_words'][command['pitchTableIndex']],
                                 voice.frequency)
                self.assertEqual(1, voice.control & 1)

    def test_both_banks_release_at_the_source_end_and_fade_before_the_finite_stop(self):
        expanded = score_module.expand_score(self.score)
        self.assertEqual(['rest'] * 3, [row['kind'] for row in expanded['commands'] if row['call'] == 800])
        self.assertEqual(960, self.score['range']['stopCall'])
        self.assertLess(self.score['range']['stopCall'] * 12326 / 985248, 13)
        for bank in (self.programs, self.reference):
            writes = compute(self.score, bank, include_stop=True)
            at_release = [row for row in writes if row['tick'] == 800 and row['address'] == 0xd412]
            self.assertEqual(0, at_release[-1]['value'] & 1)
            fades = [row for row in writes if row['address'] == 0xd418 and 800 < row['tick'] < 960]
            self.assertEqual(list(range(14, -1, -1)), [row['value'] & 15 for row in fades])
            self.assertEqual(950, fades[-1]['tick'])
            self.assertEqual([(0xd404, 0), (0xd40b, 0), (0xd412, 0), (0xd418, 0)],
                             [(row['address'], row['value']) for row in writes if row['tick'] == 960])

    def test_unsupported_collisions_pitch_ranges_and_boundaries_fail(self):
        mutations = [
            ('overlap', lambda source: source['voices'][0]['events'][0].update(durationBeats=0.5)),
            ('pitch', lambda source: source['voices'][0]['events'][0].update(midi=12)),
            ('pitch', lambda source: source['voices'][0]['events'][0].update(midi=108)),
            ('quarter-beat', lambda source: source['voices'][0]['events'][0].update(durationBeats=0.125)),
            ('excerpt', lambda source: source['voices'][0]['events'][34].update(durationBeats=1.25)),
            ('duration', lambda source: source['voices'][0]['events'][0].update(durationBeats=0)),
            ('calendar', lambda source: source.update(quarterBpm=100000)),
        ]
        for message, mutate in mutations:
            with self.subTest(message=message):
                source = deepcopy(self.source)
                mutate(source)
                with self.assertRaisesRegex(ValueError, message):
                    adapter.prepare_elise(source, self.programs)

    def test_unsupported_source_or_target_configuration_fails(self):
        source = deepcopy(self.source)
        source['voices'][0]['instrument']['waveform'] = 32
        with self.assertRaisesRegex(ValueError, 'triangle'):
            adapter.prepare_elise(source, self.programs)
        source = deepcopy(self.source)
        source['voices'][2]['name'] = 'extra'
        with self.assertRaisesRegex(ValueError, 'roles'):
            adapter.prepare_elise(source, self.programs)
        programs = deepcopy(self.programs)
        programs['format'] = 'unsupported'
        with self.assertRaisesRegex(ValueError, 'format'):
            adapter.prepare_elise(self.source, programs)
        programs = deepcopy(self.programs)
        programs['programs']['blocks']['pulse-trio']['voices'][2]['portamento_step'] = 96
        with self.assertRaisesRegex(ValueError, 'glide'):
            adapter.prepare_elise(self.source, programs)
        programs = deepcopy(self.programs)
        programs['preloaded']['voices'][0]['frequency'] = 1
        with self.assertRaisesRegex(ValueError, 'cold'):
            adapter.prepare_elise(self.source, programs)

    def test_saved_fixtures_are_reproducible_and_check_detects_a_modified_fixture(self):
        self.assertEqual(self.score, read_song('shades-elise-transfer.json'))
        self.assertEqual(self.reference, read_song('shades-elise-reference-programs.json'))
        command = [sys.executable, str(ROOT / 'scripts/studies/shades/prepare-shades-elise.py')]
        checked = subprocess.run(command + ['--check'], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(0, checked.returncode, checked.stderr)
        receipt = json.loads(checked.stdout)
        self.assertEqual({'melody': 35, 'bass': 6, 'harmony': 12}, receipt['retainedEvents'])
        self.assertEqual(53, receipt['totalRetainedEvents'])
        self.assertEqual(0, receipt['omittedExcerptEvents'])
        with tempfile.TemporaryDirectory() as temporary:
            score_path = Path(temporary) / 'score.json'
            reference_path = Path(temporary) / 'programs.json'
            options = ['--score-output', str(score_path), '--reference-programs-output', str(reference_path)]
            generated = subprocess.run(command + options, capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(0, generated.returncode, generated.stderr)
            data = json.loads(score_path.read_text())
            data['orders'][0]['rowDurationCalls'] += 1
            score_path.write_text(json.dumps(data))
            checked = subprocess.run(command + options + ['--check'], capture_output=True, text=True, cwd=ROOT)
            self.assertNotEqual(0, checked.returncode)
            self.assertIn('differs', checked.stderr)


if __name__ == '__main__':
    unittest.main()
