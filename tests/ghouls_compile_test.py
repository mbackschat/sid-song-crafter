"""Check independent graph compilation against the numeric Ghouls player."""

from copy import deepcopy
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from ghouls_player import PROFILE
from ghouls_layout import SOUND_STORAGE, sound_values
from ghouls_programs import FilterState, VoiceState

spec = importlib.util.spec_from_file_location('compose_ghouls', ROOT / 'scripts/compose-ghouls.py')
compiler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compiler)


def command(name, fields, next_node=None, **links):
    node = dict(kind='command', command=name, fields=fields, **links)
    if next_node is not None:
        node['next'] = next_node
    return dict(variants=dict(stream=node, override=deepcopy(node)))


def description(nodes, entry='first', calls=16):
    voice = dict(cursor=entry, duration_remaining=1, repeat_remaining=0,
                 repeat_cursor=None, stack=[], enabled=255, duration_override=0)
    sound = asdict(VoiceState(gate_enabled=1, rest_reload=255, rest_remaining=255,
                             waveform=64, pulse_direction=1, pulse_restart=1, gate_time=1))
    return dict(format='ghouls-composition-v1', title='Ghouls compiler fixture', profile=PROFILE,
                range=dict(auditCalls=calls), program=dict(nodes=nodes),
                voices=[voice, dict(voice, enabled=0), dict(voice, enabled=0)],
                initialSound=[sound, deepcopy(sound), deepcopy(sound)],
                initialFilter=asdict(FilterState(lower=50, upper=1229)),
                filterRestartPhases=[0, 0, 0], pulseFallbacks=[768, 768, 768],
                frequencyWords={'21': 902, '22': 956, '23': 1013})


class GhoulsCompileTest(unittest.TestCase):
    def check(self, composition):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'composition.json'
            path.write_text(json.dumps(composition))
            output = Path(directory) / 'compiled'
            report = compiler.run(path, output)
            self.assertLess(report['maximumPlayCycles'], 19656)
            self.assertTrue(report['resetVerification']['passed'])
            self.assertTrue(report['standaloneBootstrapVerification']['restoredPoisonedState'])
            self.assertFalse(report['originalDriverIncluded'])
            self.assertFalse(report['registerDumpPlayback'])
            self.assertEqual(report['stateComparison']['matchedBoundaries'], composition['range']['auditCalls'] + 1)
            self.assertEqual((output / 'reconstructed.sid').read_bytes()[:4], b'PSID')
            self.assertEqual((output / 'reconstructed.prg').read_bytes()[:2], b'\x01\x08')
            return report, json.loads((output / 'writes.json').read_text())

    def test_complete_primary_compiled_stores_state_and_reset(self):
        report, writes = self.check(json.loads((ROOT / 'songs/ghouls.json').read_text()))
        self.assertEqual(report['checkedPlayCalls'], 13060)
        self.assertEqual(len(writes), 86442)

    def test_live_override_variants_call_repeat_and_zero_duration_rest(self):
        nodes = {
            'first': command('duration-override', {'durationOverride': 2}, 'note'),
            'note': dict(variants=dict(
                stream=dict(kind='note', rawNote=21, duration=3, next='call'),
                override=dict(kind='note', rawNote=22, next='call'))),
            'call': command('call', {}, 'normal', target='repeat'),
            'repeat': command('repeat-start', {'count': 2}, 'inner'),
            'inner': dict(variants=dict(override=dict(kind='note', rawNote=23, next='repeat_end'))),
            'repeat_end': command('repeat-end', {}, 'return'),
            'return': command('return', {}),
            'normal': command('duration-override', {'durationOverride': 0}, 'rest'),
            'rest': dict(variants=dict(stream=dict(kind='rest', duration=0, next='stop'))),
            'stop': command('disable-voice', {}),
        }
        report, writes = self.check(description(nodes, calls=270))
        first_pitch = [row['value'] for row in writes if row['phase'] == 'play' and row['tick'] == 0
                       and row['address'] in (0xd400, 0xd401)]
        self.assertEqual(first_pitch, [956 & 255, 956 >> 8])
        self.assertEqual(report['compilerContract']['maximumObservedStackDepth'], 1)

    def test_nested_score_call_stack_is_independent_of_cpu_return_stack(self):
        nodes = {
            'first': command('call', {}, 'stop', target='second'),
            'second': command('call', {}, 'return', target='note'),
            'note': dict(variants=dict(stream=dict(kind='note', rawNote=21, duration=1, next='return'))),
            'return': command('return', {}),
            'stop': command('disable-voice', {}),
        }
        report, _ = self.check(description(nodes, calls=4))
        self.assertEqual(report['compilerContract']['maximumObservedStackDepth'], 2)

    def test_compile_admission_rejects_missing_lookup_initial_stack_and_filter_loop(self):
        nodes = {'first': dict(variants=dict(stream=dict(kind='note', rawNote=23, duration=1, next='stop'))),
                 'stop': command('disable-voice', {})}
        missing = description(nodes)
        del missing['frequencyWords']['23']
        with self.assertRaisesRegex(ValueError, 'Missing numeric frequency lookup'):
            compiler.build(missing)
        stack = description(nodes)
        stack['voices'][0]['stack'] = ['stop'] * 9
        with self.assertRaisesRegex(ValueError, 'stack.*8'):
            compiler.build(stack)
        bad_filter = description(nodes)
        bad_filter['initialFilter'].update(word=1, step=1, lower=2, upper=1)
        with self.assertRaisesRegex(ValueError, 'Filter parameters do not reach'):
            compiler.build(bad_filter)

    def test_numeric_sound_storage_keeps_explicit_pitch_alias_and_cold_bytes(self):
        voices = [VoiceState(current_frequency=0x1234, onset_frequency=0xffff),
                  VoiceState(pulse_word=0x8100), VoiceState(note_step=12)]
        values = sound_values(voices, FilterState(word=256, owner=1), {97: 8961},
                              [0, 255, 0], [768, 240, 500])
        self.assertEqual(set(values), {label for label, _ in SOUND_STORAGE})
        self.assertEqual(values['gh_current_frequency_lo'], [0x34, 0, 0])
        self.assertEqual(values['gh_current_frequency_hi'], [0x12, 0, 0])
        self.assertEqual(values['gh_onset_frequency_hi'], [255, 0, 0])
        self.assertEqual(values['gh_filter_restart_phase'], [0, 255, 0])
        self.assertEqual((values['gh_frequency_lo'][97], values['gh_frequency_hi'][97]), (1, 35))

    def test_partial_voice_descriptions_lower_numeric_defaults(self):
        nodes = {'first': dict(variants=dict(stream=dict(kind='note', rawNote=21, duration=1, next='stop'))),
                 'stop': command('disable-voice', {})}
        composition = description(nodes, calls=4)
        composition['voices'][0] = {'cursor': 'first'}
        composition['voices'][1] = {'cursor': 'first', 'enabled': 0}
        self.check(composition)

    def test_runtime_stack_overflow_and_oversized_sid_store_list_are_rejected(self):
        recursion = description({'first': command('call', {}, 'first', target='first')}, calls=1)
        with self.assertRaisesRegex(ValueError, 'Observed score stack.*8'):
            compiler.build(recursion)
        nodes = {'first': command('sid-store-list', {'stores': [{'address': 0xd41f, 'value': 3}] * 256}, 'stop'),
                 'stop': command('disable-voice', {})}
        with self.assertRaisesRegex(ValueError, 'SID-store list exceeds 255'):
            compiler.build(description(nodes, calls=2))


if __name__ == '__main__':
    unittest.main()
