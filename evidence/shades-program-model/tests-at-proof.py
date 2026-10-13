from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import shades_programs as programs
from psid_audit import AuditMemory
from verify_player import cpu_type


DESCRIPTION = ROOT / 'songs/shades-programs.json'
SOURCE = ROOT / '.local/research/shades/Shades_filter_corrected.sid'


class ShadesProgramsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.description = json.loads(DESCRIPTION.read_text())
        cls.programs = programs.Programs.from_dict(cls.description['programs'])

    def test_json_roundtrip_and_source_free_editable_runtime(self):
        self.assertEqual(self.description['programs'], self.programs.to_dict())
        state = programs.State.from_dict(self.description['preloaded'])
        self.assertEqual(self.description['preloaded'], json.loads(json.dumps(state.to_dict())))
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('Source read')), \
                patch.object(Path, 'read_text', side_effect=AssertionError('Source read')):
            block = self.programs.blocks['opening-pulse']
            programs.load_block(state, block)
            result = programs.consume_row(state, block, 0, programs.RowKind.NOTE,
                                          note_index=20, programs=self.programs)
            self.assertEqual(programs.RowResult(True, 0x40), result)
            self.assertEqual(0x0374, state.voices[0].frequency)
            self.assertEqual([(0, 0xe0f)], programs.advance_pulse(state))

    def test_pulse_counter_crossing_keeps_all_ascents_before_first_descents(self):
        state = programs.State()
        for voice in state.voices[:2]:
            voice.pulse_width, voice.pulse_step = 0xdff, 0x10
            voice.pulse_up_calls, voice.pulse_down_calls = 1, 2
        self.assertEqual([(0, 0xe0f), (1, 0xe0f), (0, 0xdff), (1, 0xdff)],
                         programs.advance_pulse(state))
        self.assertEqual([0, 0, 0], [voice.pulse_up_calls for voice in state.voices])
        self.assertEqual([1, 1, 0], [voice.pulse_down_calls for voice in state.voices])

    def test_pulse_below_step_stalls_without_consuming_the_down_counter(self):
        state = programs.State()
        voice = state.voices[0]
        voice.pulse_width, voice.pulse_step, voice.pulse_down_calls = 7, 8, 3
        self.assertEqual([], programs.advance_pulse(state))
        self.assertEqual(3, voice.pulse_down_calls)
        voice.pulse_width = 8
        self.assertEqual([(0, 0)], programs.advance_pulse(state))
        self.assertEqual([], programs.advance_pulse(state))
        self.assertEqual(2, voice.pulse_down_calls)

    def test_filter_uses_seven_threshold_and_retains_borrow_without_high_wrap(self):
        state = programs.State(filter=programs.FilterState(cutoff_low=5, cutoff_high=255,
                                                           up_calls=1, fine_step=2, coarse_step=1))
        self.assertTrue(programs.advance_filter(state))
        self.assertEqual((7, 0), (state.filter.cutoff_low, state.filter.cutoff_high))
        state.filter.down_calls, state.filter.fine_step = 1, 8
        self.assertTrue(programs.advance_filter(state))
        self.assertEqual((7, 0), (state.filter.cutoff_low, state.filter.cutoff_high))

    def test_delayed_vibrato_emits_two_subtractions_then_restarts_ascending(self):
        state = programs.State()
        voice = state.voices[1]
        voice.frequency, voice.target_frequency = 1000, 2000
        voice.vibrato_extent, voice.vibrato_step, voice.vibrato_delay = 8, 16, 1
        self.assertEqual([(1, 984), (1, 968)], programs.advance_vibrato(state))
        self.assertEqual((968, 0, 0), (voice.target_frequency, voice.vibrato_phase, voice.vibrato_delay))
        self.assertEqual([(1, 984)], programs.advance_vibrato(state))

    def test_voice_specific_rests_and_holds_preserve_gate_writer_contract(self):
        state = programs.State()
        block = self.programs.blocks['opening-pulse']
        self.assertEqual([False, True, False],
                         [programs.consume_row(state, block, voice, programs.RowKind.REST).write_voice
                          for voice in range(3)])
        current = state.voices[0]
        current.control, current.pulse_width = 0x41, 0xdff
        self.assertEqual(programs.RowResult(False), programs.consume_row(state, block, 0, programs.RowKind.HOLD))
        self.assertEqual(0x41, current.control)
        self.assertTrue(programs.consume_row(state, block, 0, programs.RowKind.REST).write_voice)
        self.assertEqual(0x40, current.control)

    def test_unsupported_modes_and_invalid_unused_parameters_fail_before_runtime(self):
        for key, value in (('portamento_mode', 'other'), ('pulse_step', True), ('pulse_width', -1),
                           ('vibrato_delay', 256), ('fine_tune', '3')):
            invalid = deepcopy(self.description['programs'])
            invalid['blocks']['silent']['voices'][2][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                programs.Programs.from_dict(invalid)
        invalid = deepcopy(self.description['programs'])
        invalid['blocks']['silent']['filter']['trigger_mask'] = 3
        with self.assertRaises(ValueError):
            programs.Programs.from_dict(invalid)
        with self.assertRaisesRegex(ValueError, 'frequency table'):
            programs.consume_row(programs.State(), self.programs.blocks['silent'], 0, programs.RowKind.NOTE,
                                 note_index=96, programs=self.programs)


class ShadesSourceTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE.is_file():
            raise unittest.SkipTest('Pinned Shades source is not installed')
        cls.data = SOURCE.read_bytes()
        cls.programs = programs.decode_programs(cls.data)

    def test_imported_parameters_and_preloaded_state_match_portable_description(self):
        description = json.loads(DESCRIPTION.read_text())
        self.assertEqual(description['programs'], self.programs.to_dict())
        self.assertEqual(description['preloaded'], programs.decode_preloaded(self.data).to_dict())
        self.assertEqual(14, len(self.programs.blocks))
        self.assertEqual(0x16ad, self.programs.frequency_words[95])
        invalid = bytearray(self.data)
        invalid[-1] ^= 1
        with self.assertRaisesRegex(ValueError, 'pinned corrected'):
            programs.decode_programs(invalid)

    def test_portamento_downward_low_byte_comparison_and_upward_delay_flag_match_source(self):
        for current, target, step, mode, expected in (
            (0x1020, 0x1000, 0x10, programs.PortamentoMode.TARGET, 0x1000),
            (0x1008, 0x1000, 0x10, programs.PortamentoMode.TARGET, 0x0ff8),
            (0x1100, 0x1000, 0x10, programs.PortamentoMode.TARGET, 0x10f0),
            (0xffff, 0, 2, programs.PortamentoMode.UP, 1),
            (0x1020, 0x1000, 0x100, programs.PortamentoMode.TARGET, 0x1020),
        ):
            memory = AuditMemory()
            memory.data = programs.ram_image(self.data)
            memory.data[:2] = [0x2f, 0x37]
            memory.data[0x733e:0x7340] = [current & 255, current >> 8]
            memory.data[0x7357:0x7359] = [target & 255, target >> 8]
            memory.data[0x0346:0x0348] = [step & 255, step >> 8]
            memory.data[0x0374] = list(programs.PortamentoMode).index(mode)
            before = programs.state_from_memory(memory.data)
            computed = deepcopy(before)
            programs.advance_portamento(computed)
            cpu = cpu_type()(memory=memory, pc=0x7012)
            cpu.stPushWord(0x01ff)
            while cpu.pc != 0x0200:
                memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
                cpu.step()
            observed = programs.state_from_memory(memory.data)
            self.assertEqual(expected, observed.voices[0].frequency)
            self.assertEqual(observed, computed, (current, target, step, mode))

    def check_transitions(self, calls, evidence_output=None):
        spec = importlib.util.spec_from_file_location('shades_model_source_oracle', ROOT / 'scripts/trace-shades-vice.py')
        tracer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tracer)
        starts = {0x7012: (0x7449, programs.advance_portamento, 'portamento'),
                  0x7132: (0x744c, programs.advance_vibrato, 'vibrato'),
                  0x71c7: (0x744f, programs.advance_filter, 'filter'),
                  0x72a0: (0x7452, programs.advance_pulse, 'pulse')}
        row_starts = {0x748b: (0, 0x7550), 0x7550: (1, 0x75ec), 0x75ec: (2, 0x7690)}
        row_writers = (0x76dd, 0x7739, 0x778f)
        pending, counts, active = {}, {}, None
        active_name, last_state = None, None

        def state_changes(before, after):
            changed = {}
            voices = {}
            for index, voice in enumerate(after['voices']):
                previous = before['voices'][index] if before else {}
                delta = {key: value for key, value in voice.items() if previous.get(key) != value}
                if delta:
                    voices[str(index)] = delta
            if voices:
                changed['voices'] = voices
            previous = before['filter'] if before else {}
            delta = {key: value for key, value in after['filter'].items() if previous.get(key) != value}
            if delta:
                changed['filter'] = delta
            if before is None or before['percussion_active'] != after['percussion_active']:
                changed['percussion_active'] = after['percussion_active']
            return changed

        def observe(cpu, memory):
            nonlocal active, active_name, last_state
            if memory.phase != 'play':
                return
            pc, tick, raw = cpu.pc, memory.tick, memory.data
            if pc in pending:
                state, output, first_write, label, voice, before, inputs = pending.pop(pc)
                observed = programs.state_from_memory(raw)
                self.assertEqual(observed, state, (tick, hex(pc), label))
                writes = memory.writes[first_write:]
                if label in ('portamento', 'vibrato', 'pulse'):
                    offset = 2 if label == 'pulse' else 0
                    expected = [(0xd400 + index * 7 + offset + byte, word >> (8 * byte) & 255)
                                for index, word in output for byte in (0, 1)]
                    self.assertEqual(expected, [(row['address'], row['value']) for row in writes], (tick, label))
                elif label == 'filter':
                    expected = [(0xd415, state.filter.cutoff_low), (0xd416, state.filter.cutoff_high)] if output else []
                    self.assertEqual(expected, [(row['address'], row['value']) for row in writes], (tick, label))
                elif label == 'row':
                    self.assertEqual(output.write_voice, any(row['writerPc'] == row_writers[voice] for row in writes))
                    if output.initial_control is not None:
                        self.assertEqual((0xd404 + 7 * voice, output.initial_control),
                                         (writes[0]['address'], writes[0]['value']))
                if evidence_output is not None:
                    after = state.to_dict()
                    transition = vars(output) if isinstance(output, programs.RowResult) else output
                    record = {'call': tick, 'stage': label, 'exitPc': pc, 'inputs': inputs,
                              'entryChanges': state_changes(last_state, before),
                              'exitChanges': state_changes(before, after),
                              'computedTransitions': transition, 'sourceSidWrites': writes}
                    evidence_output.write(json.dumps(record, separators=(',', ':')) + '\n')
                    last_state = after
                counts[label] = counts.get(label, 0) + 1
            if pc == 0x7816:
                address = raw[0xab] | raw[0xac] << 8
                active_name = programs.SOURCE_BLOCK_NAMES[address]
                active = self.programs.blocks[active_name]
                state = programs.state_from_memory(raw)
                before = state.to_dict()
                programs.load_block(state, active)
                pending[0x7855] = state, None, len(memory.writes), 'block', None, before, {'block': active_name}
            if pc in starts:
                end, function, label = starts[pc]
                state = programs.state_from_memory(raw)
                before = state.to_dict()
                output = function(state)
                pending[end] = state, output, len(memory.writes), label, None, before, {}
            if pc in row_starts:
                voice, end = row_starts[pc]
                pointer = raw[0xa5 + 2 * voice] | raw[0xa6 + 2 * voice] << 8
                code = raw[pointer + raw[0x0340]]
                kind = programs.RowKind.REST if code == 0 else programs.RowKind.HOLD if code == 128 else programs.RowKind.NOTE
                note = code & 127
                if voice or not active.percussion_control or note < 48:
                    note = (note + raw[0x0343 + voice]) & 255
                state = programs.state_from_memory(raw)
                before = state.to_dict()
                gate = programs.Gate.OFF if kind == programs.RowKind.NOTE and code & 128 else programs.Gate.ON
                result = programs.consume_row(state, active, voice, kind,
                                              note_index=note if kind == programs.RowKind.NOTE else None,
                                              gate=gate, programs=self.programs)
                pending[end] = state, result, len(memory.writes), 'row', voice, before, {
                    'block': active_name, 'voice': voice, 'kind': kind, 'noteIndex': note if kind == programs.RowKind.NOTE else None,
                    'gate': gate}

        tracer.shades_oracle(self.data, calls, observer=observe)
        self.assertFalse(pending)
        self.assertGreater(counts['row'], 0)
        return counts

    def test_all_opening_program_transitions_match_executed_instructions(self):
        counts = self.check_transitions(1280)
        self.assertEqual(1279, counts['pulse'])

    def test_all_full_form_program_transitions_match_executed_instructions(self):
        counts = self.check_transitions(24385)
        self.assertEqual(24384, counts['pulse'])
        self.assertEqual(24384, counts['row'])


if __name__ == '__main__':
    unittest.main()
