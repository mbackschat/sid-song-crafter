from pathlib import Path
import random
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from cybernoid_output import (
    advance_arpeggio, advance_pulse_run, apply_wave_program, sweep_high_byte,
)
from cybernoid_programs import advance_filter, advance_pulse
from cybernoid_state import filter_ownership
from sid_assembler import assemble
from verify_player import cpu_type


SOURCE = ROOT / 'songs/players/cybernoid-effects.asm'
ARRAYS = (
    'arpeggio_counter', 'base_pitch', 'current_pitch', 'frequency_lo', 'frequency_hi',
    'held_frequency_lo', 'held_frequency_hi', 'held_high_copy', 'wave', 'base_wave',
    'gate_mask', 'pulse_accumulator_lo', 'pulse_accumulator_hi', 'pulse_output_lo',
    'pulse_output_hi', 'pulse_direction', 'note_age', 'packed_filter', 'filter_cutoff',
    'pulse_run_flag', 'pulse_run_low', 'pulse_run_high', 'sound_index', 'arpeggio_index',
)
SCALARS = ('fx1', 'fx2', 'fx3', 'filter_owner')
ROUTINE_FIELDS = {
    'cy_advance_arpeggio': ('arpeggio_counter', 'current_pitch', 'frequency_lo', 'frequency_hi'),
    'cy_advance_pulse': ('pulse_accumulator_lo', 'pulse_accumulator_hi', 'pulse_output_lo',
                         'pulse_output_hi', 'pulse_direction'),
    'cy_sweep_high': ('held_frequency_hi', 'frequency_hi'),
    'cy_filter': ('filter_cutoff',),
    'cy_pulse_run': ('pulse_run_flag', 'pulse_run_low', 'pulse_run_high', 'pulse_output_lo', 'pulse_output_hi'),
    'cy_wave': ('wave', 'frequency_lo', 'frequency_hi', 'gate_mask'),
}
FREQUENCIES = [(0xfedf + index * 797) & 65535 for index in range(257)]
DEFAULT_PULSE = [7, 13, 3, 0x70, 6, 0x60, 9, 0x50]
DEFAULT_FILTER = [0xa0, 0xfe, 1, 0xff, 0x62, 0x3f, 2, 0x22, 0x62, 0xa2]


def state_symbol(name):
    return 'cy_output_wave' if name == 'wave' else 'cy_' + name


class GuardedMemory(list):
    def __init__(self):
        super().__init__([0] * 65536)
        self.allowed_writes = None
        self.sid_writes = []

    def __setitem__(self, address, value):
        if self.allowed_writes is not None:
            if address not in self.allowed_writes:
                raise AssertionError(f'Effect writes outside selected state, scratch or SID at ${address:04x}')
            if address in (0xd416, 0xd418):
                self.sid_writes.append((address, value))
        super().__setitem__(address, value)


class EffectsHarness:
    def __init__(self, *, pulse=None, filt=None, arp=None, waves=None, pitches=None):
        cpu_class = cpu_type()
        self.tables = {
            'cy_freq_lo': [word & 255 for word in FREQUENCIES],
            'cy_freq_hi': [word >> 8 for word in FREQUENCIES],
            'cy_onset_lengths': [2, 0xfe, 0xff],
            'cy_onset_waves': [0x81, 0x41, 0x7f],
            'cy_test_pulse': list(DEFAULT_PULSE if pulse is None else pulse),
            'cy_test_filter': list(DEFAULT_FILTER if filt is None else filt),
            'cy_test_arp': list([3, 0, 4, 7, 12] + [0] * 251 if arp is None else arp),
            'cy_test_waves': list([4, 0x81, 0x40, 0x21] + [0] * 252 if waves is None else waves),
            'cy_test_pitches': list([0xfa, 4, 0xff] + [0] * 253 if pitches is None else pitches),
        }
        source = SOURCE.read_text() + '\ncy_write_mode:\n  STA $D418\n  RTS\n'
        source += ''.join(f'{state_symbol(name)}:\n  .byte $00,$00,$00\n' for name in ARRAYS)
        source += ''.join(f'cy_{name}:\n  .byte $00\n' for name in SCALARS)
        pointers = {
            'cy_pulse_ptr': ('cy_test_pulse', 7),
            'cy_filter_ptr': ('cy_test_filter', 8),
            'cy_arp_ptr': ('cy_test_arp', 1),
            'cy_drum_wave_ptr': ('cy_test_waves', 16),
            'cy_drum_pitch_ptr': ('cy_test_pitches', 16),
        }
        for name, (_, count) in pointers.items():
            for suffix in ('lo', 'hi'):
                source += f'{name}_{suffix}:\n  .byte ' + ','.join('$00' for _ in range(count)) + '\n'
        for name, values in self.tables.items():
            source += f'{name}:\n  .byte ' + ','.join(f'${value:02x}' for value in values) + '\n'
        payload, self.symbols, self.listing = assemble(source, load=0x2000)
        self.memory = GuardedMemory()
        self.memory[0x2000:0x2000 + len(payload)] = payload
        for name, (target, count) in pointers.items():
            for index in range(count):
                self.memory[self.symbols[name + '_lo'] + index] = self.symbols[target] & 255
                self.memory[self.symbols[name + '_hi'] + index] = self.symbols[target] >> 8
        self.cpu = cpu_class(memory=self.memory)
        self.readonly = {address: self.memory[address]
                         for name in self.tables
                         for address in range(self.symbols[name], self.symbols[name] + len(self.tables[name]))}
        for voice in range(3):
            self.set_voice(voice, {name: ((index + 1) * (voice + 2)) & 255 for index, name in enumerate(ARRAYS)})
            self.set_voice(voice, {'sound_index': 0, 'arpeggio_index': 0})

    def set_voice(self, voice, values):
        self.memory.allowed_writes = None
        for name, value in values.items():
            self.memory[self.symbols[state_symbol(name)] + voice] = value

    def set_word(self, voice, name, value):
        self.set_voice(voice, {name + '_lo': value & 255, name + '_hi': value >> 8})

    def set_globals(self, **values):
        self.memory.allowed_writes = None
        for name, value in values.items():
            self.memory[self.symbols['cy_' + name]] = value

    def voice(self, voice):
        return {name: self.memory[self.symbols[state_symbol(name)] + voice] for name in ARRAYS}

    def word(self, voice, name):
        state = self.voice(voice)
        return state[name + '_lo'] | state[name + '_hi'] << 8

    def scalar(self, name):
        return self.memory[self.symbols['cy_' + name]]

    def call(self, label, voice):
        before = [self.voice(index) for index in range(3)]
        self.memory.allowed_writes = {self.symbols[state_symbol(name)] + voice for name in ROUTINE_FIELDS[label]}
        if label == 'cy_filter':
            self.memory.allowed_writes.update((self.symbols['cy_filter_owner'], 0xd416, 0xd418))
        self.memory.allowed_writes.update(self.symbols['cy_effect_' + name]
                                          for name in ('step', 'stage', 'limit', 'pitch'))
        self.memory.allowed_writes.update(range(0x100, 0x200))
        self.memory.allowed_writes.update((0xf8, 0xf9))
        self.memory.sid_writes.clear()
        self.cpu.x, self.cpu.a, self.cpu.y, self.cpu.p, self.cpu.sp = voice, 0xa5, 0x5a, 0x20, 255
        self.cpu.stPushWord(0x01ff)
        self.cpu.pc = self.symbols[label]
        first_cycle = self.cpu.processorCycles
        while self.cpu.pc != 0x0200:
            if self.cpu.processorCycles - first_cycle >= 1500:
                raise AssertionError('Effect failed to return within its bounded call')
            self.cpu.step()
        if self.cpu.x != voice or self.cpu.sp != 255:
            raise AssertionError('Effect failed to preserve voice X or the call stack')
        for index in range(3):
            if index != voice and self.voice(index) != before[index]:
                raise AssertionError('Effect altered another voice')
        if any(self.memory[address] != value for address, value in self.readonly.items()):
            raise AssertionError('Effect altered a parameter table')
        return list(self.memory.sid_writes)


class CybernoidEffectsAssemblyTests(unittest.TestCase):
    def test_reverse_arpeggio_order_signed_reload_and_byte_pitch_wrap(self):
        harness = EffectsHarness()
        harness.set_globals(fx3=4)
        harness.set_voice(2, {'arpeggio_counter': 0, 'base_pitch': 250})
        pitches = []
        for _ in range(9):
            state = harness.voice(2)
            expected = advance_arpeggio(state['arpeggio_counter'], 250, harness.tables['cy_test_arp'], FREQUENCIES)
            self.assertEqual([], harness.call('cy_advance_arpeggio', 2))
            actual = harness.voice(2)
            self.assertEqual((expected.counter, expected.pitch_index, expected.frequency_word),
                             (actual['arpeggio_counter'], actual['current_pitch'], harness.word(2, 'frequency')))
            pitches.append(actual['current_pitch'])
        self.assertEqual([6, 1, 254, 250, 6, 1, 254, 250, 6], pitches)
        for counter in (128, 129, 255):
            harness.set_voice(2, {'arpeggio_counter': counter})
            expected = advance_arpeggio(counter, 250, harness.tables['cy_test_arp'], FREQUENCIES)
            harness.call('cy_advance_arpeggio', 2)
            self.assertEqual(expected.counter, harness.voice(2)['arpeggio_counter'])
        arp = [255] + list(range(1, 256))
        harness = EffectsHarness(arp=arp)
        harness.set_globals(fx3=4)
        harness.set_voice(0, {'arpeggio_counter': 0, 'base_pitch': 2})
        expected = advance_arpeggio(0, 2, arp, FREQUENCIES)
        harness.call('cy_advance_arpeggio', 0)
        self.assertEqual((255, 1, FREQUENCIES[1]),
                         (harness.voice(0)['arpeggio_counter'], harness.voice(0)['current_pitch'],
                          harness.word(0, 'frequency')))
        self.assertEqual(expected.frequency_word, harness.word(0, 'frequency'))

    def test_arpeggio_self_gates_and_drum_has_priority(self):
        harness = EffectsHarness()
        for fx3 in (0, 0x10, 0x14, 0x80):
            with self.subTest(fx3=fx3):
                harness.set_globals(fx3=fx3)
                before = harness.voice(0)
                self.assertEqual([], harness.call('cy_advance_arpeggio', 0))
                self.assertEqual(before, harness.voice(0))

    def assert_pulse(self, harness, voice, width, direction, age, fx2):
        harness.set_word(voice, 'pulse_accumulator', width)
        harness.set_word(voice, 'pulse_output', width ^ 0xffff)
        harness.set_voice(voice, {'pulse_direction': direction, 'note_age': age})
        harness.set_globals(fx2=fx2)
        expected = advance_pulse(width, direction, age, fx2, harness.tables['cy_test_pulse'])
        self.assertEqual([], harness.call('cy_advance_pulse', voice))
        self.assertEqual(expected, (harness.word(voice, 'pulse_accumulator'), harness.voice(voice)['pulse_direction']))
        self.assertEqual(expected[0], harness.word(voice, 'pulse_output'))

    def test_pwm_stage_boundaries_overshoot_wrap_and_output_copy(self):
        for slot, vectors in (
            (DEFAULT_PULSE, [(0x500, 1, 1, 0x64), (0xcc0, 1, 22, 0x64), (0x700, 0, 10, 0x64),
                             (0x9999, 255, 99, 0x80)]),
            ([0x87, 13, 3, 0x70, 6, 0x60, 9, 0x50], [(0xcc0, 8, 22, 0x64)]),
            ([7, 13, 0x83, 0x70, 6, 0x60, 9, 0x50], [(0x900, 255, 3, 0x64), (0x900, 255, 4, 0x64)]),
            ([0, 255, 127, 2, 127, 2, 127, 2], [(1, 0, 2, 1), (0xfffe, 1, 2, 1)]),
        ):
            harness = EffectsHarness(pulse=slot)
            for index, vector in enumerate(vectors):
                with self.subTest(slot=slot, vector=vector):
                    self.assert_pulse(harness, index % 3, *vector)
        harness = EffectsHarness()
        width, direction = 0x500, 1
        for age in range(1, 64):
            self.assert_pulse(harness, 1, width, direction, age, 0x64)
            width, direction = advance_pulse(width, direction, age, 0x64, DEFAULT_PULSE)

    def test_saved_high_sweep_wraps_and_retains_all_low_bytes_and_copy(self):
        harness = EffectsHarness()
        for voice, base, output in ((0, 0x12ab, 0x3478), (1, 0x00ff, 0xff00), (2, 0xff01, 0x00fe)):
            harness.set_word(voice, 'held_frequency', base)
            harness.set_word(voice, 'frequency', output)
            copy = harness.voice(voice)['held_high_copy']
            harness.set_globals(fx3=0x20)
            self.assertEqual([], harness.call('cy_sweep_high', voice))
            self.assertEqual(sweep_high_byte(base, output),
                             (harness.word(voice, 'held_frequency'), harness.word(voice, 'frequency')))
            self.assertEqual(copy, harness.voice(voice)['held_high_copy'])
            harness.set_globals(fx3=0)
            before = harness.voice(voice)
            harness.call('cy_sweep_high', voice)
            self.assertEqual(before, harness.voice(voice))

    def test_filter_ownership_fallback_repeats_and_preserves_store_order(self):
        harness = EffectsHarness()
        for voice, fx2, fx3, owner in ((2, 8, 1, 0), (1, 0, 0, 2), (2, 8, 0, 2),
                                        (2, 0, 0, 2), (2, 0, 0, 2), (0, 8, 0, 255)):
            harness.set_globals(fx2=fx2, fx3=fx3, filter_owner=owner)
            harness.set_voice(voice, {'filter_cutoff': 73, 'note_age': 1, 'packed_filter': 7})
            expected_owner, cutoff, active, stores = filter_ownership(voice, fx2, fx3, owner, 73)
            if active:
                mode, cutoff = advance_filter(cutoff, 1, DEFAULT_FILTER)
                stores = [(0xd418, mode), (0xd416, cutoff)]
            self.assertEqual(stores, harness.call('cy_filter', voice))
            self.assertEqual((expected_owner, cutoff), (harness.scalar('filter_owner'), harness.voice(voice)['filter_cutoff']))

    def test_filter_threshold_priority_initial_terminal_and_byte_wrap(self):
        for program, vectors in (
            (DEFAULT_FILTER, [(99, 1), (1, 2), (255, 0x22), (0, 0x62), (0, 0xa2), (3, 255)]),
            ([7, 1, 2, 3, 9, 0x1f, 30, 20, 10, 100], [(10, 15), (10, 5), (255, 30), (1, 100)]),
        ):
            harness = EffectsHarness(filt=program)
            harness.set_globals(fx3=1)
            for index, (cutoff, age) in enumerate(vectors):
                voice = index % 3
                harness.set_voice(voice, {'filter_cutoff': cutoff, 'note_age': age, 'packed_filter': 0})
                mode, expected = advance_filter(cutoff, age, program)
                self.assertEqual([(0xd418, mode), (0xd416, expected)], harness.call('cy_filter', voice))
                self.assertEqual(expected, harness.voice(voice)['filter_cutoff'])

    def test_pulse_run_activation_reactivation_carry_wrap_and_exact_fifteen(self):
        harness = EffectsHarness()
        for voice, active, flag, low, high, pwm_high in (
            (0, False, 0, 17, 14, 7), (0, True, 1, 17, 14, 7), (0, True, 0, 200, 14, 2),
            (1, True, 0, 200, 255, 8), (2, True, 0, 0, 15, 2), (2, True, 255, 2, 3, 14),
            (0, False, 0, 201, 8, 14), (0, True, 1, 201, 8, 14),
        ):
            with self.subTest(voice=voice, active=active, flag=flag, low=low, high=high):
                harness.set_globals(fx3=2 if active else 0)
                harness.set_word(voice, 'pulse_output', 0x1234)
                harness.set_voice(voice, {'pulse_run_flag': flag, 'pulse_run_low': low, 'pulse_run_high': high,
                                          'pulse_accumulator_hi': pwm_high})
                expected = advance_pulse_run(active, flag, low, high, pwm_high)
                self.assertEqual([], harness.call('cy_pulse_run', voice))
                actual = harness.voice(voice)
                self.assertEqual((expected.needs_initialization, expected.low, expected.high),
                                 (actual['pulse_run_flag'], actual['pulse_run_low'], actual['pulse_run_high']))
                self.assertEqual(0x1234 if expected.pulse_override is None else expected.pulse_override,
                                 harness.word(voice, 'pulse_output'))

    def assert_wave(self, harness, voice, fx3, fx1, age, *, sound=0, pitch=253):
        harness.set_globals(fx3=fx3, fx1=fx1)
        harness.set_voice(voice, {'note_age': age, 'sound_index': sound, 'current_pitch': pitch,
                                 'base_wave': 0x21, 'wave': 0x41, 'gate_mask': 0xaa})
        harness.set_word(voice, 'held_frequency', 0x3456)
        harness.set_word(voice, 'frequency', 0x9876)
        expected = apply_wave_program(fx3, age, fx1, pitch, harness.tables['cy_test_waves'],
            harness.tables['cy_test_pitches'], FREQUENCIES, harness.tables['cy_onset_lengths'][sound],
            harness.tables['cy_onset_waves'][sound], 0x21, 0x3456, 0x41, 0x9876, 0xaa)
        self.assertEqual([], harness.call('cy_wave', voice))
        self.assertEqual((expected.wave, expected.frequency_word, expected.gate_mask),
                         (harness.voice(voice)['wave'], harness.word(voice, 'frequency'), harness.voice(voice)['gate_mask']))
        return expected

    def test_onset_noise_restore_expiry_and_byte_restore_limit(self):
        harness = EffectsHarness()
        for sound, ages in ((0, (0, 1, 2, 3, 4, 255)), (1, (0, 253, 254, 255)), (2, (0, 254, 255))):
            for age in ages:
                with self.subTest(sound=sound, age=age):
                    self.assert_wave(harness, sound, 0x80, 0, age, sound=sound)
        self.assert_wave(harness, 0, 0, 0, 1)

    def test_drum_relative_absolute_gate_mask_and_expired_onset_priority(self):
        harness = EffectsHarness()
        for fx1 in (0, 0x10, 0x1f):
            for age in (0, 1, 2, 3, 4, 255):
                with self.subTest(fx1=fx1, age=age):
                    self.assert_wave(harness, age % 3, 0x90, fx1, age)
        self.assertEqual('expiredDrum', self.assert_wave(harness, 0, 0x90, 0, 4).phase)

    def test_seeded_parameter_edits_and_state_boundaries_match_numeric_helpers(self):
        rng = random.Random(8388001)
        for iteration in range(24):
            pulse = [rng.randrange(256) for _ in range(8)]
            filt = [rng.randrange(256) for _ in range(10)]
            arp = [rng.randrange(256) for _ in range(256)]
            waves = [rng.randrange(256) for _ in range(256)]
            pitches = [rng.randrange(256) for _ in range(256)]
            harness = EffectsHarness(pulse=pulse, filt=filt, arp=arp, waves=waves, pitches=pitches)
            voice, age = iteration % 3, rng.randrange(256)
            self.assert_pulse(harness, voice, rng.randrange(65536), rng.randrange(256), age, rng.randrange(256))
            harness.set_voice(voice, {'filter_cutoff': rng.randrange(256), 'note_age': age, 'packed_filter': 7})
            harness.set_globals(fx3=1)
            cutoff = harness.voice(voice)['filter_cutoff']
            mode, cutoff = advance_filter(cutoff, age, filt)
            self.assertEqual([(0xd418, mode), (0xd416, cutoff)], harness.call('cy_filter', voice))
            counter, base = rng.randrange(256), rng.randrange(256)
            harness.set_voice(voice, {'arpeggio_counter': counter, 'base_pitch': base})
            harness.set_globals(fx3=4)
            expected = advance_arpeggio(counter, base, arp, FREQUENCIES)
            harness.call('cy_advance_arpeggio', voice)
            self.assertEqual((expected.counter, expected.pitch_index, expected.frequency_word),
                             (harness.voice(voice)['arpeggio_counter'], harness.voice(voice)['current_pitch'],
                              harness.word(voice, 'frequency')))
            self.assert_wave(harness, voice, 0x90, rng.randrange(256), age, pitch=rng.randrange(256))


if __name__ == '__main__':
    unittest.main()
