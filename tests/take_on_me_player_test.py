"""Guard source-free Take On Me score/sound integration and state ownership."""

from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/studies/take-on-me'))
import programs
import player


def example(calls=5):
    instruments = {index: asdict(programs.Instrument(pulse=512, onset_control=65,
        body_control=17, attack_decay=2, sustain_release=100, filter_word=49152,
        gate_half=1)) for index in range(2)}
    initial_score = dict(remaining=1, orderCursor=0, repeat=0, transpose=0,
        patternCursor=0, instrument=0, durationTicks=0, glideStepLow=0,
        glideStepHigh=0, baseNote=0, glideTarget=0, arpeggio=0)
    return dict(schema='take-on-me-composition-v1',
        target=dict(clock='pal', sidModel='MOS8580', sidBase=0xd400, frameCycles=19656),
        range=dict(auditCalls=calls), mix=dict(routing=241, modeVolume=31),
        score=dict(schemaVersion=1, dividerReloads=[0, 0], initialDividers=[0, 0],
            initialVoices=[deepcopy(initial_score) for _ in range(3)],
            orders=[dict(bytes=[0, 255, 0]) for _ in range(3)],
            patterns={'0': dict(rows=[dict(instrument=1, durationUnits=1, note=24)])}),
        sound=dict(instruments=instruments, programs=asdict(programs.Programs(frequencies={24: 0x1234}))),
        initialSound=dict(voices=[{} for _ in range(3)], filter={}))


def project(writes, omitted=()):
    return [row for row in writes if row['address'] not in omitted]


class TakeOnMePlayerTest(unittest.TestCase):
    def test_setup_and_output_follow_voice_order_without_same_call_body(self):
        result = player.compute(example(), calls=2, contexts=True)
        first = [(row['address'], row['value']) for row in result['writes'] if row['tick'] == 0]
        expected = []
        for voice in (2, 1, 0):
            base = 0xd400 + voice * 7
            expected.extend([(base + 5, 2), (base + 6, 100), (base + 4, 65),
                (base + 3, 2), (base + 2, 0), (base + 1, 0x12), (base, 0x34)])
        expected.extend([(0xd415, 0), (0xd416, 192)])
        self.assertEqual(first, expected)
        self.assertEqual([entry['stage'] for entry in result['contexts'][:7]],
            ['setup', 'voice-output', 'setup', 'voice-output', 'setup', 'voice-output', 'filter-output'])
        second = next(entry for entry in result['contexts'] if entry['call'] == 1 and entry['stage'] == 'body')
        self.assertEqual(second['before']['remaining'], 1)
        self.assertEqual(second['after']['control'], 16)

    def test_initial_sound_cannot_duplicate_a_score_owned_field(self):
        value = example()
        value['initialSound']['voices'][0]['base_note'] = 10
        with self.assertRaisesRegex(ValueError, 'score owns base_note'):
            player.compute(value)

    def test_provenance_and_source_addresses_do_not_affect_synthesis(self):
        value = example()
        edited = deepcopy(value)
        edited['sourceEvidence'] = dict(originalSha256='unrelated annotation')
        edited['score']['orders'][0]['address'] = 0xffff
        edited['score']['patterns']['0']['address'] = 0xffff
        self.assertEqual(player.compute(value)['writes'], player.compute(edited)['writes'])

    def test_glide_completion_is_owned_by_sound_across_score_holds(self):
        value = example()
        value['score']['patterns']['0']['rows'] = [dict(instrument=1, durationUnits=4,
            glide=dict(stepWord=8, note=24, target=25))]
        value['sound']['programs']['frequencies'] = {24: 0x1000, 25: 0x1010}
        result = player.compute(value)
        voice = [entry['voices'][0] for entry in result['returns']]
        self.assertEqual([entry['glide_active'] for entry in voice], [1, 1, 0, 0, 0])
        self.assertEqual([entry['frequency'] for entry in voice], [0x1000, 0x1008, 0x1010, 0x1010, 0x1010])

    def test_duration_edit_changes_one_voice_schedule_and_preserves_companions(self):
        value = example()
        changed = deepcopy(value)
        changed['score']['patterns']['1'] = dict(rows=[dict(instrument=1, durationUnits=2, note=24)])
        changed['score']['orders'][0]['bytes'][0] = 1
        original, edited = player.compute(value), player.compute(changed)
        self.assertEqual(project(original['writes'], range(0xd400, 0xd407)),
            project(edited['writes'], range(0xd400, 0xd407)))
        self.assertEqual([entry['tick'] for entry in edited['rows'] if entry['voice'] == 0], [0, 4])

    def test_pulse_parameter_edit_has_only_pulse_store_consequences(self):
        value = example()
        value['sound']['instruments'][1]['pulse'] = 0x1000
        value['sound']['instruments'][1]['pulse_program'] = 1
        value['sound']['programs']['pulses'] = {1: asdict(programs.SweepProgram(0, 16, 0xf00, 255, 0, 0, 0))}
        changed = deepcopy(value)
        changed['sound']['programs']['pulses'][1]['down_step'] = 32
        original, edited = player.compute(value), player.compute(changed)
        ports = (0xd402, 0xd403, 0xd409, 0xd40a, 0xd410, 0xd411)
        self.assertEqual(project(original['writes'], ports), project(edited['writes'], ports))
        self.assertNotEqual(original['writes'], edited['writes'])

    def test_stop_preserves_prior_voice_output_and_skips_filter_and_lower_voice(self):
        value = example()
        value['score']['orders'][1]['bytes'] = [254]
        result = player.compute(value, contexts=True)
        played = [entry for entry in result['writes'] if entry['phase'] == 'play']
        self.assertEqual([entry['tick'] for entry in played], [0] * 10)
        self.assertEqual([(entry['address'], entry['value']) for entry in played[-3:]],
            [(0xd404, 0), (0xd40b, 0), (0xd412, 0)])
        self.assertEqual([entry['stage'] for entry in result['contexts']], ['setup', 'voice-output'])

    def test_middle_voice_stop_keeps_lower_voice_score_projection_current(self):
        value = example()
        value['score']['orders'][1]['bytes'] = [254]
        result = player.compute(value)
        for returned in result['returns']:
            self.assertEqual([voice['remaining'] for voice in returned['voices']],
                [voice['remaining'] for voice in returned['score']['voices']])

    def test_highest_voice_stop_updates_every_global_countdown_projection(self):
        value = example()
        value['score']['orders'][2]['bytes'] = [254]
        result = player.compute(value)
        self.assertEqual([voice['remaining'] for voice in result['returns'][0]['score']['voices']], [0, 0, 0])
        self.assertTrue(all([voice['remaining'] for voice in returned['voices']] == [0, 0, 0]
            for returned in result['returns']))

    def test_reinitialization_and_computation_leave_the_editable_input_unchanged(self):
        value = example()
        initial = deepcopy(value)
        first = player.compute(value)
        self.assertEqual(value, initial)
        self.assertEqual(first, player.compute(value))

    def test_authored_release_freezes_score_and_modulation_then_stops_once(self):
        value = example(calls=69)
        value['ending'] = dict(startCall=2, releaseCalls=2)
        value['sound']['instruments'][1]['body_control'] = 65
        value['sound']['instruments'][1]['gate_half'] = 0
        result = player.compute(value)
        release = [(row['address'], row['value']) for row in result['writes'] if row['tick'] == 2]
        self.assertEqual(release, [(0xd404, 64), (0xd40b, 64), (0xd412, 64)])
        self.assertEqual([row for row in result['writes'] if row['tick'] == 3], [])
        stop = [(row['address'], row['value']) for row in result['writes'] if row['tick'] == 4]
        self.assertEqual(stop, [(0xd404, 0), (0xd40b, 0), (0xd412, 0), (0xd418, 16)])
        self.assertEqual([row for row in result['writes'] if row['tick'] is not None and row['tick'] > 4], [])
        self.assertEqual(result['returns'][2]['voices'], result['returns'][3]['voices'])
        frozen = lambda row: {key: field for key, field in row.items() if key != 'tick'}
        self.assertEqual(frozen(result['returns'][4]), frozen(result['returns'][68]))
        self.assertEqual(result['returns'][4]['ending'], dict(phase=2, nextCall=4, modeVolume=16))

    def test_authored_ending_requires_64_observed_calls_after_the_final_stop(self):
        value = example(calls=68)
        value['ending'] = dict(startCall=2, releaseCalls=2)
        with self.assertRaisesRegex(ValueError, '64 calls after'):
            player.compute(value)


if __name__ == '__main__':
    unittest.main()
