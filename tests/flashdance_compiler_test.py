from copy import deepcopy
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from flashdance_pitch import PitchEffects
from flashdance_player import compute_writes
from flashdance_programs import (
    FilterRow, FilterState, Instrument, PitchMode, PreloadedState, Programs, PwmRow,
    PwmState, VoiceState, WaveRow,
)
from psid_audit import AuditMemory, audit_psid
from verify_player import cpu_type


spec = importlib.util.spec_from_file_location('compose_flashdance', ROOT / 'scripts/compose-flashdance.py')
compiler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compiler)
DESCRIPTION = ROOT / 'songs/flashdance-decoded.json'


def fixture():
    programs = Programs(
        pwm_rows={0: PwmRow(1, 15, 64, 0, 0x650, True),
                  1: PwmRow(10, 15, 112, 6, 0xd00), 2: PwmRow(10, 15, 16, 0, None, True),
                  3: PwmRow(0, 15, 13, 0, 64, True)},
        filter_rows={0: FilterRow(32, 224, 56, 0, 160, True)},
        wave_rows={0: WaveRow(90, 129, PitchMode.ABSOLUTE), 1: WaveRow(0, 65), 2: WaveRow(0, 64),
                   3: WaveRow(jump=2), 4: WaveRow(0, 17), 5: WaveRow(0, 33), 6: WaveRow(0, 65),
                   7: WaveRow(jump=6), 8: WaveRow(0, 65), 9: WaveRow(4, 65), 10: WaveRow(7, 65),
                   11: WaveRow(jump=8)},
        frequency_words=tuple(1000 + index * 317 for index in range(96)),
        instruments={0: Instrument(2, 95, 241, 0, 0, 0), 16: Instrument(3, 60, 0, 0, 1, 4),
                     24: Instrument(3, 52, 0, 0, 3, 8)}, filter_owner=0)
    roles = {}
    for voice, (role, instrument, note) in enumerate((('bass', 'bass', 11), ('lead', 'lead', 40), ('chord', 'chord', 30)), 1):
        roles[role] = {'voice': voice, 'fineTuneWord': voice - 1, 'commands': [
            {'call': 2, 'kind': 'instrument', 'instrument': instrument},
            {'call': 2, 'kind': 'note', 'sourceNote': note, 'transposeSemitones': 11, 'restart': True, 'durationCalls': 4},
            {'call': 8, 'kind': 'effect', 'effect': 'vibrato', 'parameters': {
                'remainingNotes': 1, 'reloadCounter': 4, 'initialCounter': 3,
                'pitchDeltaRightShifts': 2, 'deltaHighByteIncrement': 0}},
            {'call': 8, 'kind': 'hold', 'durationCalls': 4},
            {'call': 20, 'kind': 'effect', 'effect': 'sustainReleaseAhead',
             'parameters': {'callsBeforeNextRow': 2, 'sustainRelease': 0}},
            {'call': 20, 'kind': 'hold', 'durationCalls': 4},
            {'call': 24, 'kind': 'effect', 'effect': 'pitchOffset', 'parameters': {'remainingNotes': 1, 'stepWord': 40}},
            {'call': 24, 'kind': 'hold', 'durationCalls': 4},
            {'call': 258, 'kind': 'note', 'sourceNote': note + 1, 'transposeSemitones': 11,
             'restart': False, 'durationCalls': 4},
            {'call': 280, 'kind': 'off', 'durationCalls': 4},
        ]}
    initial = PreloadedState(tuple(VoiceState(PwmState(row=0, width=0x650), 2) for _ in range(3)),
                             FilterState(row=0, cutoff=32), 0)
    return {'format': 'sid-flashdance-composition-v1',
            'score': {'profile': {'clock': 'PAL', 'chip': 'MOS6581', 'callCycles': 19656},
                      'range': {'firstCall': 0, 'stopCall': 300}, 'roles': roles},
            'programs': programs.to_dict(), 'preloaded': initial.to_dict(),
            'initialEffects': [asdict(PitchEffects()) for _ in range(3)],
            'instrumentBindings': {'bass': 0, 'lead': 16, 'chord': 24},
            'initialVolume': 15, 'initialRouting': 241, 'ending': {'releaseCalls': 64, 'fadeStepCalls': 4}}


def identity(rows):
    return [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]


def run_twice(sid, calls):
    load, init, play = (int.from_bytes(sid[index:index + 2], 'big') for index in (8, 10, 12))
    memory = AuditMemory()
    memory.data[load:load + len(sid) - 124] = sid[124:]
    cpu = cpu_type()(memory=memory)
    runs = []

    def call(address):
        cpu.stPushWord(0x01ff)
        cpu.pc = address
        start = cpu.processorCycles
        while cpu.pc != 0x0200:
            if cpu.processorCycles - start > 19656:
                raise AssertionError('Compiled call exceeds one PAL frame')
            memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
            memory.instruction_cycle = cpu.processorCycles - start
            cpu.step()
        if cpu.sp != 255:
            raise AssertionError('Compiled call corrupts the stack')

    for _ in range(2):
        first_write = len(memory.writes)
        memory.phase, memory.tick = 'init', None
        call(init)
        memory.data[0xfb], memory.data[0xfc] = 0xa7, 0x5c
        memory.phase = 'play'
        for tick in range(calls):
            memory.tick = tick
            call(play)
            if memory.data[0xfb:0xfd] != [0xa7, 0x5c]:
                raise AssertionError('Play call fails to preserve zero-page $FB/$FC')
        runs.append(memory.writes[first_write:])
    return runs


class FlashdanceCompilerTest(unittest.TestCase):
    def test_compiled_music_and_finite_ending_match_every_ordered_model_write(self):
        description = fixture()
        sid, built = compiler.build(description)
        report, writes = audit_psid(sid, 431)
        self.assertEqual(identity(compute_writes(description, calls=431)), identity(writes))
        self.assertLessEqual(report['maximumPlayCycles'], 19656)
        self.assertEqual((2, 0x14, 1), tuple(int.from_bytes(sid[index:index + 2], 'big') for index in (4, 118, 14)))
        self.assertIn('entry_init', built['symbols'])
        self.assertIn('entry_play', built['symbols'])
        muted = [row for row in writes if row['phase'] == 'play' and row['tick'] == 428]
        self.assertEqual([(0xd404, 0), (0xd40b, 0), (0xd412, 0), (0xd418, 0)],
                         [(row['address'], row['value']) for row in muted])

    def test_source_annotations_are_not_compiler_inputs(self):
        description = fixture()
        description['sourceEvidence'] = {'path': '/absent/original.sid', 'sha256': 'annotation'}
        description['score']['source'] = {'path': '/absent/original.sid'}
        for role in description['score']['roles'].values():
            for command in role['commands']:
                command['sourceEvidence'] = {'address': 65535, 'frequencyWord': 1}
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('Compiler reads source binary')):
            sid, built = compiler.build(description)
        clean, _ = compiler.build(fixture())
        self.assertEqual(clean, sid)
        self.assertNotIn('sidWrites', built)
        self.assertNotIn('originalDriver', built)

    def test_editable_pitch_and_pwm_change_computed_runtime_behavior(self):
        for edit in ('pitch', 'pwm'):
            with self.subTest(edit=edit):
                description = fixture()
                if edit == 'pitch':
                    description['score']['roles']['lead']['commands'][1]['sourceNote'] += 2
                else:
                    description['programs']['pwm_rows']['1']['step'] += 3
                sid, _ = compiler.build(description)
                _, actual = audit_psid(sid, 12)
                self.assertEqual(identity(compute_writes(description, calls=12)), identity(actual))
                self.assertNotEqual(identity(compute_writes(fixture(), calls=12)), identity(actual))

    def test_repeated_initialization_restores_score_effects_and_program_state(self):
        description = fixture()
        sid, _ = compiler.build(description)
        first, second = run_twice(sid, 32)
        expected = identity(compute_writes(description, calls=32))
        self.assertEqual(expected, identity(first))
        self.assertEqual(expected, identity(second))

    def test_envelope_schedule_uses_first_duration_when_a_call_has_multiple_score_events(self):
        for kind in ('note', 'off'):
            with self.subTest(kind=kind):
                description = fixture()
                commands = description['score']['roles']['lead']['commands']
                extra = {'call': 20, 'kind': kind, 'durationCalls': 8 if kind == 'note' else 12}
                if kind == 'note':
                    extra.update(sourceNote=42, transposeSemitones=11, restart=False)
                commands.insert(6, extra)
                sid, _ = compiler.build(description)
                _, writes = audit_psid(sid, 32)
                self.assertEqual(identity(compute_writes(description, calls=32)), identity(writes))

    def test_frequency_bounds_are_checked_through_the_authored_tail(self):
        description = fixture()
        description['score']['range']['stopCall'] = 1
        for role in description['score']['roles'].values():
            role['commands'] = []
        for voice in description['preloaded']['voices']:
            voice['wave_row'] = 20
        description['programs']['wave_rows'].update({
            '20': asdict(WaveRow(0, 65)), '21': asdict(WaveRow(100, 65)), '22': asdict(WaveRow(jump=20)),
        })
        with self.assertRaisesRegex(ValueError, 'frequency table'):
            compiler.build(description)

    def test_invalid_commands_and_parameters_fail_before_assembly(self):
        description = fixture()
        description['score']['roles']['lead']['commands'][0]['kind'] = 'capturedWrites'
        with self.assertRaisesRegex(ValueError, 'command'):
            compiler.build(description)
        description = fixture()
        description['programs']['pwm_rows']['1']['step'] = 256
        with self.assertRaisesRegex(ValueError, 'step'):
            compiler.build(description)


@unittest.skipUnless(DESCRIPTION.exists(), 'Requires the retained Flashdance composition description')
class FlashdanceCompleteCompilerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.description = json.loads(DESCRIPTION.read_text())
        cls.sid, cls.built = compiler.build(cls.description)

    def test_complete_selected_score_and_authored_tail_match_all_registers(self):
        stop = self.description['score']['range']['stopCall']
        ending = self.description['ending']
        calls = stop + ending['releaseCalls'] + 16 * ending['fadeStepCalls'] + 2
        report, actual = audit_psid(self.sid, calls)
        self.assertEqual(identity(compute_writes(self.description, calls=calls)), identity(actual))
        self.assertLessEqual(report['maximumPlayCycles'], 19656)
        self.assertEqual(1538, stop)


if __name__ == '__main__':
    unittest.main()
