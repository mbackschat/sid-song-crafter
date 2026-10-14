"""Guard score/sound ownership and complete Billie Jean stage ordering."""

from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/studies/billie-jean'))
import billie_jean_player as player
import billie_jean_programs as programs


def example(rows=None, calls=16):
    score_voice = dict(orderCursor=0, patternCursor=0, remaining=0, transpose=0,
        baseNote=20, instrumentOffset=8, holdFlag=0, patternIndex=0)
    sound_voice = asdict(programs.VoiceState(frequency=2000, waveform=65, age=1))
    for field in player.SCORE_INPUTS:
        del sound_voice[field]
    return dict(schema='billie-jean-composition-v1',
        target=dict(clock='pal', sidModel='MOS6581', sidBase=0xd400, frameCycles=19656),
        range=dict(auditCalls=calls),
        score=dict(schema='billie-jean-score-v1', rowDividerReload=2, initialDivider=0,
            initialVoices=[deepcopy(score_voice) for _ in range(3)],
            orders=[dict(bytes=[0, 255]) for _ in range(3)],
            patterns={'0': dict(rows=rows or [dict(header=131, instrument=1, note=20)])}),
        sound=dict(instruments={'8': asdict(programs.Instrument(attack_decay=3, sustain_release=88))},
            programs=dict(frequencies={str(index): index * 100 for index in range(96)},
                pitches=[126] * 256, waveforms=[65] * 256,
                routing_set=[241, 242, 244], routing_clear=[254, 253, 251])),
        initialSound=dict(voices=[deepcopy(sound_voice) for _ in range(3)],
            filter=asdict(programs.FilterState())))


class BillieJeanPlayerTest(unittest.TestCase):
    def test_init_and_hard_restart_have_only_their_native_stores(self):
        result = player.compute(example(), calls=3, contexts=True)
        self.assertEqual([(item['address'], item['value']) for item in result['writes'] if item['phase'] == 'init'],
            [(0xd404, 0), (0xd40b, 0), (0xd412, 0)])
        last = [item for item in result['writes'] if item['tick'] == 2]
        self.assertEqual([item['address'] for item in last],
            [0xd412, 0xd413, 0xd414, 0xd412, 0xd40b, 0xd40c, 0xd40d, 0xd40b,
             0xd404, 0xd405, 0xd406, 0xd404, 0xd418])
        self.assertEqual([state['age'] for state in result['returns'][2]['voices']], [1, 1, 1])
        self.assertEqual([item['stage'] for item in result['contexts'][-7:]],
            ['setup', 'age', 'setup', 'age', 'setup', 'age', 'global-output'])

    def test_legato_uses_retained_phase_without_adsr_or_restart(self):
        value = example([dict(header=35, note=21)])
        for initial in value['score']['initialVoices']:
            initial['holdFlag'] = 32
        for initial in value['initialSound']['voices']:
            initial.update(gate_mask=255, wave_cursor=4, pulse=1234, age=5)
        result = player.compute(value, calls=3, contexts=True)
        setups = [item for item in result['contexts'] if item['stage'] == 'setup']
        self.assertEqual([item['path'] for item in setups], ['legato'] * 3)
        self.assertTrue(all(len(item['writes']) == 5 for item in setups))
        self.assertEqual(result['returns'][2]['voices'][0]['frequency'], 2100)
        self.assertEqual(result['returns'][2]['voices'][0]['age'], 8)
        self.assertEqual(result['returns'][2]['voices'][0]['wave_cursor'], 4)

    def test_completed_glide_stays_cleared_on_later_hold_calls(self):
        value = example([dict(header=99, glideStep=200, glideTarget=21, note=20)])
        for initial in value['score']['initialVoices']:
            initial['holdFlag'] = 32
        for initial in value['initialSound']['voices']:
            initial['gate_mask'] = 255
        result = player.compute(value, calls=5)
        self.assertEqual(result['returns'][2]['voices'][0]['glide_step'], 200)
        self.assertEqual(result['returns'][3]['voices'][0]['glide_step'], 0)
        self.assertEqual(result['returns'][4]['voices'][0]['frequency'], 2100)
        self.assertEqual(result['returns'][4]['voices'][0]['glide_step'], 0)

    def test_rest_uses_body_and_retains_active_glide(self):
        value = example([dict(header=195)])
        for initial in value['initialSound']['voices']:
            initial.update(glide_step=10, glide_target=21)
        result = player.compute(value, calls=3, contexts=True)
        final = result['returns'][2]['voices'][0]
        self.assertEqual((final['frequency'], final['glide_step'], final['gate_mask']), (2030, 10, 254))
        self.assertFalse(any(item['stage'] == 'setup' for item in result['contexts']))

    def test_glide_target_setter_uses_retained_transpose_and_new_plain_note_clears_step(self):
        value = example([dict(header=64, glideStep=20, glideTarget=25, note=20), dict(header=0, note=21)])
        for order in value['score']['orders']:
            order['bytes'] = [135, 0, 255]
        result = player.compute(value, calls=6)
        self.assertEqual(result['returns'][2]['voices'][0]['glide_target'], 32)
        self.assertEqual(result['returns'][2]['voices'][0]['base_note'], 27)
        self.assertEqual(result['returns'][5]['voices'][0]['glide_step'], 0)
        self.assertEqual(result['returns'][5]['voices'][0]['glide_target'], 32)

    def test_initial_sound_cannot_duplicate_score_inputs_or_omit_cold_fields(self):
        for field in player.SCORE_INPUTS:
            value = example()
            value['initialSound']['voices'][0][field] = 0
            with self.assertRaisesRegex(ValueError, 'score owns'):
                player.compute(value)
        value = example()
        del value['initialSound']['voices'][0]['age']
        with self.assertRaisesRegex(ValueError, 'complete named sound state'):
            player.compute(value)

    def test_unsupported_mix_cannot_become_a_silent_edit(self):
        value = example()
        value['mix'] = {}
        with self.assertRaisesRegex(ValueError, 'Unknown composition fields'):
            player.compute(value)

    def test_ending_closes_actual_restart_control_and_freezes_until_bounded_stop(self):
        value = example(calls=68)
        value['score']['initialDivider'] = 1
        value['initialSound']['filter']['mode'] = 48
        value['ending'] = dict(startCall=1, releaseCalls=2)
        result = player.compute(value)
        self.assertEqual([(item['address'], item['value']) for item in result['writes'] if item['tick'] == 1],
            [(0xd404, 8), (0xd40b, 8), (0xd412, 8)])
        self.assertEqual(result['returns'][1]['voices'], result['returns'][0]['voices'])
        self.assertEqual(result['returns'][2]['score'], result['returns'][0]['score'])
        self.assertEqual([(item['address'], item['value']) for item in result['writes'] if item['tick'] == 3],
            [(0xd404, 0), (0xd40b, 0), (0xd412, 0), (0xd418, 48)])
        self.assertFalse(any(item['tick'] is not None and item['tick'] > 3 for item in result['writes']))
        self.assertEqual(result['returns'][-1]['ending'], dict(phase=2, nextCall=3,
            modeVolume=48, heldControls=[0, 0, 0]))

    def test_ending_preserves_the_music_prefix_and_requires_quiet_confirmation_range(self):
        value = example(calls=72)
        baseline = player.compute(value, calls=5)
        value['ending'] = dict(startCall=5, releaseCalls=2)
        result = player.compute(value)
        self.assertEqual([item for item in result['writes'] if item['tick'] is None or item['tick'] < 5],
            baseline['writes'])
        for actual, expected in zip(result['returns'][:5], baseline['returns']):
            self.assertEqual({key: data for key, data in actual.items() if key != 'ending'}, expected)
        value['range']['auditCalls'] = 71
        with self.assertRaisesRegex(ValueError, '64 calls after'):
            player.compute(value)

    def test_all_voice_inputs_match_score_returns_and_age_saturates(self):
        value = example()
        for initial in value['initialSound']['voices']:
            initial['age'] = 128
        result = player.compute(value, calls=2)
        for record in result['returns']:
            for voice, state in enumerate(record['voices']):
                self.assertEqual(state['age'], 128)
                for sound_field, score_field in player.SCORE_INPUTS.items():
                    self.assertEqual(state[sound_field], record['score']['voices'][voice][score_field])

    def test_shared_filter_updates_follow_voice_order_and_global_output_is_last(self):
        value = example()
        instrument = value['sound']['instruments']['8']
        instrument.update(filter_enabled=1, filter_step=1, filter_mode=48)
        value['initialSound']['filter']['cutoff'] = 10
        result = player.compute(value, calls=1)
        self.assertEqual([item['value'] for item in result['writes'] if item['address'] == 0xd416], [9, 8, 7])
        self.assertEqual(result['writes'][-1]['address'], 0xd418)
        self.assertEqual(result['writes'][-1]['value'], 59)

    def test_numeric_inputs_reinitialize_and_source_annotations_do_not_execute(self):
        value = example()
        retained = deepcopy(value)
        first = player.compute(value)
        self.assertEqual(value, retained)
        self.assertEqual(player.compute(value), first)
        value['sourceEvidence'] = {'arbitrary': 'unused'}
        for order in value['score']['orders']:
            order['sourceAddress'] = 0x6000
        value['score']['patterns']['0']['sourceAddress'] = 0x7000
        self.assertEqual(player.compute(value), first)


if __name__ == '__main__':
    unittest.main()
