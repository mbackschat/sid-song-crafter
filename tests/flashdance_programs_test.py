import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from flashdance_programs import (
    FilterRow, FilterState, Instrument, PitchMode, PreloadedState, Programs, PwmRow, PwmState,
    VoiceState, WaveRow, advance_filter, advance_pwm, advance_voice, decode_preloaded,
    decode_programs, initialize_filter, initialize_voice, ram_image,
)


def fixture(pwm_rows=None, filter_rows=None, wave_rows=None):
    return Programs(
        pwm_rows=pwm_rows or {0: PwmRow(4, 15, 0x40, 15, hold=True)},
        filter_rows=filter_rows or {0: FilterRow(0, 0, 0, 63, 0x20, True)},
        wave_rows=wave_rows or {0: WaveRow(0, 0x40), 1: WaveRow(jump=0)},
        frequency_words=tuple(range(96)), instruments={}, filter_owner=0,
    )


class FlashdanceProgramTests(unittest.TestCase):
    def test_lead_row_change_preserves_width_and_direction(self):
        programs = fixture(pwm_rows={6: PwmRow(10, 15, 0x10, 15, hold=True)})
        state = VoiceState(PwmState(10, 15, 0x70, 1, 6, 0, 0xd70), 0)
        result = advance_voice(state, programs, base_note=3, transpose_bytes=22, fine_tune=1)
        self.assertEqual((state.pwm.width, state.pwm.step, state.pwm.direction), (0xd60, 0x10, 1))
        self.assertEqual((result.frequency_word, result.control), (15, 0x40))

    def test_pulse_reversal_uses_high_byte_equality_and_retains_overshoot(self):
        programs = fixture()
        state = VoiceState(PwmState(4, 15, 0x20, 0, 0, 1, 0xef0), 0)
        result = advance_voice(state, programs, base_note=0, transpose_bytes=0, fine_tune=0)
        self.assertEqual((result.pulse_width, state.pwm.direction), (0xf10, 1))
        state.pwm.width, state.pwm.direction, state.pwm.remaining = 0xff0, 0, 1
        advance_voice(state, programs, base_note=0, transpose_bytes=0, fine_tune=0)
        self.assertEqual((state.pwm.width, state.pwm.direction), (0x1010, 0))

    def test_initialization_resets_pulse_width_before_direction(self):
        programs = fixture(pwm_rows={0: PwmRow(4, 15, 0x40, 8, 0x100), 1: PwmRow(4, 15, 0x40, 15, hold=True)})
        instrument = Instrument(2, 0x5f, 0, 1, 0, 0)
        state = VoiceState(PwmState(1, 2, 1, 1, 1, 5, 0x888), 1)
        initialize_voice(state, instrument, programs)
        self.assertEqual((state.pwm.width, state.pwm.direction, state.pwm.remaining, state.wave_row), (0x100, 1, 0, 0))
        advance_voice(state, programs, base_note=0, transpose_bytes=0, fine_tune=0)
        self.assertEqual((state.pwm.width, state.pwm.direction, state.pwm.remaining, state.pwm.row), (0x140, 0, 8, 1))

    def test_row_countdown_keeps_pulse_moving(self):
        programs = fixture(pwm_rows={0: PwmRow(4, 15, 0x40, 8, 0x100), 1: PwmRow(4, 15, 0x10, 15, hold=True)})
        state = VoiceState(PwmState(row=0), 0)
        for _ in range(9):
            advance_voice(state, programs, base_note=0, transpose_bytes=0, fine_tune=0)
        self.assertEqual((state.pwm.width, state.pwm.remaining, state.pwm.step), (0x340, 0, 0x40))
        advance_voice(state, programs, base_note=0, transpose_bytes=0, fine_tune=0)
        self.assertEqual((state.pwm.width, state.pwm.remaining, state.pwm.step), (0x350, 15, 0x10))

    def test_absolute_attack_and_jump_preserve_release_control(self):
        programs = fixture(wave_rows={0: WaveRow(90, 0x81, PitchMode.ABSOLUTE), 1: WaveRow(0, 0x40), 2: WaveRow(jump=1)})
        state = VoiceState(PwmState(4, 15, 0x40, 0, 0, 10, 0x100), 0)
        attack = advance_voice(state, programs, base_note=11, transpose_bytes=22, fine_tune=2)
        release = advance_voice(state, programs, base_note=11, transpose_bytes=22, fine_tune=2)
        loop = advance_voice(state, programs, base_note=11, transpose_bytes=22, fine_tune=2)
        self.assertEqual((attack.note_index, attack.frequency_word, attack.absolute_pitch, attack.control), (90, 92, True, 0x81))
        self.assertEqual((release.frequency_word, release.control, loop.frequency_word, loop.control, state.wave_row), (24, 0x40, 24, 0x40, 2))

    def test_filter_upper_is_inclusive_and_lower_is_exclusive(self):
        programs = fixture()
        state = FilterState(row=0, remaining=1, lower=0x40, upper=0x80, step=1, cutoff=0x7f)
        self.assertEqual(advance_filter(state, programs), 0x80)
        self.assertEqual(state.direction, 1)
        state.cutoff, state.remaining = 0x41, 1
        self.assertEqual(advance_filter(state, programs), 0x40)
        self.assertEqual(state.direction, 1)
        state.remaining = 1
        self.assertEqual(advance_filter(state, programs), 0x3f)
        self.assertEqual(state.direction, 0)

    def test_filter_initialization_preserves_direction_until_row_consumption(self):
        programs = fixture(filter_rows={1: FilterRow(0, 0, 0, 0, 0xa0)})
        state = FilterState(direction=1, cutoff=0x20)
        instrument = Instrument(2, 0x5f, 0xf1, 1, 0, 0)
        self.assertTrue(initialize_filter(state, instrument, programs))
        self.assertEqual((state.row, state.remaining, state.cutoff, state.direction), (1, 0, 0xa0, 1))
        advance_filter(state, programs)
        self.assertEqual((state.row, state.cutoff, state.direction), (2, 0xa0, 1))

    def test_programs_round_trip_without_reference_dependency(self):
        programs = fixture()
        self.assertEqual(Programs.from_dict(json.loads(json.dumps(programs.to_dict()))), programs)

    def test_resolved_pitch_must_fit_table_before_voice_state_advances(self):
        for wave_offset, base_note, transpose in ((0, 95, 22), (40, 51, 22)):
            with self.subTest(wave_offset=wave_offset, base_note=base_note, transpose=transpose):
                programs = fixture(wave_rows={0: WaveRow(wave_offset, 0x41), 1: WaveRow(jump=0)})
                state = VoiceState(PwmState(4, 15, 0x40, 0, 0, 10, 0x100), 0)
                before = copy.deepcopy(state)
                with self.assertRaisesRegex(ValueError, 'frequency table'):
                    advance_voice(state, programs, base_note=base_note, transpose_bytes=transpose, fine_tune=0)
                self.assertEqual(before, state)

    def test_serialized_state_can_be_compared_directly_with_retained_json(self):
        state = PreloadedState(tuple(VoiceState() for _ in range(3)), FilterState(), 0)
        for description in (fixture().to_dict(), state.to_dict()):
            self.assertEqual(description, json.loads(json.dumps(description)))

    def test_invalid_semantic_rows_fail_even_when_unused(self):
        invalid = [('pwm_rows', 'step', -1), ('pwm_rows', 'duration', -1),
                   ('pwm_rows', 'step', True), ('pwm_rows', 'upper', 16),
                   ('pwm_rows', 'reset_width', 65536), ('pwm_rows', 'hold', 1),
                   ('filter_rows', 'step', 256), ('filter_rows', 'duration', 64),
                   ('filter_rows', 'reset_cutoff', -1), ('wave_rows', 'control', 256),
                   ('wave_rows', 'note', 127)]
        for bank, name, value in invalid:
            with self.subTest(bank=bank, name=name, value=value):
                description = fixture().to_dict()
                description[bank]['20'] = dict(description[bank]['0'], **{name: value})
                if bank == 'wave_rows':
                    description[bank]['21'] = dict(description[bank]['1'], jump=20)
                with self.assertRaises(ValueError):
                    Programs.from_dict(description)

    def test_missing_links_consecutive_jumps_and_unsupported_filter_mode_fail(self):
        for mutation in ('missing-pulse', 'missing-wave', 'consecutive-jump', 'filter-mode'):
            with self.subTest(mutation=mutation):
                description = fixture().to_dict()
                if mutation == 'missing-pulse':
                    description['pwm_rows']['0']['hold'] = False
                elif mutation == 'missing-wave':
                    description['wave_rows']['1']['jump'] = 3
                elif mutation == 'consecutive-jump':
                    description['wave_rows']['0'] = dict(description['wave_rows']['1'])
                else:
                    description['instruments']['0'] = {
                        'attack_decay': 2, 'sustain_release': 0x5f, 'filter_command': 8,
                        'filter_row': 0, 'pwm_row': 0, 'wave_row': 0,
                    }
                with self.assertRaises(ValueError):
                    Programs.from_dict(description)

    def test_preloaded_bounds_links_and_owner_are_checked_before_execution(self):
        programs = fixture()
        initial = PreloadedState(tuple(VoiceState(PwmState(row=0), 0) for _ in range(3)), FilterState(row=0), 0)
        for field, value in (('direction', 2), ('width', -1), ('remaining', 64), ('step', False), ('row', 1)):
            with self.subTest(field=field, value=value):
                description = initial.to_dict()
                description['voices'][2]['pwm'][field] = value
                with self.assertRaises(ValueError):
                    PreloadedState.from_dict(description, programs)
        description = initial.to_dict()
        description['filter_owner'] = 1
        with self.assertRaises(ValueError):
            PreloadedState.from_dict(description, programs)


class FlashdanceExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = ROOT / '.local/research/flashdance/drax-flashdance-conversion.sid'
        if not source.exists():
            raise unittest.SkipTest('Pinned Flashdance reference is not installed')
        cls.data = source.read_bytes()
        cls.programs = decode_programs(cls.data)
        cls.preloaded = decode_preloaded(cls.data)
        spec = importlib.util.spec_from_file_location('flashdance_program_reference', ROOT / 'scripts/study-drax-references.py')
        reference = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reference)
        reference.verify_reference('flashdance', cls.data)
        diagnostic = reference.load_script('psid_audit.py', 'flashdance_program_private_audit')
        diagnostic.AuditMemory = reference.FlashdanceDiagnosticMemory
        cls.records, cls.initializer_records = [], []
        pwm, wave, filt, initializing = {}, {}, None, {}

        def pulse(memory, x):
            return PwmState(*(memory[address + x] for address in (0x1731, 0x1734, 0x1737, 0x173a)),
                            memory[0x173d + x] // 4, memory[0x1740 + x], memory[0x1743 + x] | memory[0x1746 + x] << 8)

        def filter_state(memory):
            return FilterState(memory[0x174d] // 4, memory[0x174e], memory[0x1749], memory[0x174a], memory[0x174b], memory[0x174c], memory[0x174f])

        def observe(cpu, memory):
            nonlocal filt
            if memory.phase != 'play':
                return
            m, x, call = memory.data, cpu.x, memory.tick
            if cpu.pc == 0x12e0:
                initializing[x] = (call, m[0x101d + x], VoiceState(pulse(m, x), m[0x1750 + x]), filter_state(m))
            if cpu.pc == 0x1388:
                before = initializing.pop(x)
                cls.initializer_records.append((before, VoiceState(pulse(m, x), m[0x1750 + x]), filter_state(m)))
            if cpu.pc == 0x138b:
                pwm[x] = (call, VoiceState(pulse(m, x), m[0x1750 + x]))
            if cpu.pc == 0x1428:
                filt = (call, filter_state(m))
            if cpu.pc == 0x14a3 and filt is not None:
                cls.records.append(('filter', filt, filter_state(m)))
                filt = None
            if cpu.pc == 0x14ca:
                wave[x] = (m[0x1014 + x], m[0x1017 + x], m[0x1762 + x], m[0x101a + x])
            if cpu.pc == 0x1515:
                before = pwm.pop(x)
                cls.records.append(('voice', before, wave.pop(x), VoiceState(pulse(m, x), m[0x1750 + x]),
                                    m[0x100c + x] | m[0x100f + x] << 8, m[0x170a + x] & m[0x101a + x], m[0x100b] != 0))

        diagnostic.audit_psid(cls.data, 1538, observer=observe)

    def test_all_selected_voice_and_filter_transitions_match_original_execution(self):
        counts = {'voice': 0, 'filter': 0}
        for record in self.records:
            if record[0] == 'filter':
                _, (call, state), expected = record
                state = copy.deepcopy(state)
                advance_filter(state, self.programs)
                self.assertEqual(state, expected, f'Filter call {call}')
            else:
                _, (call, state), inputs, expected, frequency, control, absolute = record
                state = copy.deepcopy(state)
                result = advance_voice(state, self.programs, base_note=inputs[0], transpose_bytes=inputs[1], fine_tune=inputs[2], gate_mask=inputs[3])
                self.assertEqual(state, expected, f'Voice state call {call}')
                self.assertEqual((result.frequency_word, result.control, result.absolute_pitch), (frequency, control, absolute), f'Voice result call {call}')
            counts[record[0]] += 1
        self.assertGreater(counts['voice'], 4500)
        self.assertGreater(counts['filter'], 1500)

    def test_all_selected_initializers_match_original_state(self):
        seen = set()
        for (call, offset, voice, filt), expected_voice, expected_filter in self.initializer_records:
            voice, filt = copy.deepcopy(voice), copy.deepcopy(filt)
            instrument = self.programs.instruments[offset]
            initialize_voice(voice, instrument, self.programs)
            initialize_filter(filt, instrument, self.programs)
            self.assertEqual(voice, expected_voice, f'Initializer voice call {call}')
            self.assertEqual(filt, expected_filter, f'Initializer filter call {call}')
            seen.add(offset)
        self.assertEqual(seen, {0, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0x40})

    def test_preloaded_state_matches_first_body_entries(self):
        first = [record for record in self.records if record[0] == 'voice' and record[1][0] == 0]
        self.assertEqual(len(first), 3)
        for voice_index, record in zip((2, 1, 0), first):
            self.assertEqual(self.preloaded.voices[voice_index], record[1][1])
        initial_filter = next(record[1][1] for record in self.records if record[0] == 'filter' and record[1][0] == 0)
        self.assertEqual(self.preloaded.filter, initial_filter)
        self.assertEqual(self.preloaded.filter_owner, 0)

    def test_parameter_interventions_match_isolated_original_routines(self):
        from py65.devices.mpu6502 import MPU

        def execute(memory, start, end):
            cpu = MPU(memory=memory, pc=start)
            cpu.x = 0
            for _ in range(100):
                if cpu.pc == end:
                    return
                cpu.step()
            self.fail('Isolated original routine did not reach its declared boundary')

        for width, step, direction in ((0xef0, 0x20, 0), (0xff0, 0x20, 0),
                                       (0x500, 1, 1), (0x400, 1, 1),
                                       (0, 1, 1), (0xfff0, 0x20, 0)):
            with self.subTest(pulse=(width, step, direction)):
                memory = ram_image(self.data)
                state = PwmState(4, 15, step, direction, 1, 1, width)
                for address, value in zip((0x1731, 0x1734, 0x1737, 0x173a, 0x173d, 0x1740, 0x1743, 0x1746),
                                          (4, 15, step, direction, 4, 1, width & 255, width >> 8)):
                    memory[address] = value
                execute(memory, 0x138b, 0x141d)
                advance_pwm(state, self.programs.pwm_rows)
                self.assertEqual((state.width, state.direction, state.remaining),
                                 (memory[0x1743] | memory[0x1746] << 8, memory[0x173a], memory[0x1740]))
        for cutoff, direction in ((0x7f, 0), (0x41, 1), (0x40, 1), (0xff, 0), (0, 1)):
            with self.subTest(filter=(cutoff, direction)):
                memory = ram_image(self.data)
                state = FilterState(1, 1, 0x40, 0x80, 1, direction, cutoff)
                for address, value in zip((0x174d, 0x174e, 0x1749, 0x174a, 0x174b, 0x174c, 0x174f),
                                          (4, 1, 0x40, 0x80, 1, direction, cutoff)):
                    memory[address] = value
                execute(memory, 0x1428, 0x14a3)
                advance_filter(state, self.programs)
                self.assertEqual((state.cutoff, state.direction, state.remaining),
                                 (memory[0x174f], memory[0x174c], memory[0x174e]))


if __name__ == '__main__':
    unittest.main()
