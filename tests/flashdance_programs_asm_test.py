from copy import deepcopy
from pathlib import Path
import random
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from flashdance_programs import (
    FilterRow, FilterState, Instrument, PitchMode, Programs, PwmRow, PwmState,
    VoiceState, WaveRow, advance_filter, advance_voice, decode_preloaded,
    decode_programs, initialize_filter, initialize_voice,
)
from sid_assembler import assemble
from verify_player import cpu_type


SOURCE = ROOT / 'songs/players/flashdance-programs.asm'
ARRAYS = (
    'pulse_lower', 'pulse_upper', 'pulse_step', 'pulse_direction', 'pulse_row', 'pulse_remaining',
    'pulse_lo', 'pulse_hi', 'wave_row', 'base_note', 'transpose', 'tuning', 'gate_mask',
    'frequency_lo', 'frequency_hi', 'wave_control', 'absolute_pitch', 'instrument',
)
SCALARS = ('filter_lower', 'filter_upper', 'filter_step', 'filter_direction',
           'filter_row', 'filter_remaining', 'filter_cutoff', 'fd_tmp_lo', 'fd_tmp_hi')


def packed_voice(state):
    pulse = state.pwm
    return {
        'pulse_lower': pulse.lower, 'pulse_upper': pulse.upper, 'pulse_step': pulse.step,
        'pulse_direction': pulse.direction, 'pulse_row': pulse.row, 'pulse_remaining': pulse.remaining,
        'pulse_lo': pulse.width & 255, 'pulse_hi': pulse.width >> 8, 'wave_row': state.wave_row,
    }


def packed_filter(state):
    return {'filter_' + name: getattr(state, name) for name in
            ('lower', 'upper', 'step', 'direction', 'row', 'remaining', 'cutoff')}


class GuardedMemory(list):
    def __init__(self):
        super().__init__([0] * 65536)
        self.allowed_writes = None

    def __setitem__(self, address, value):
        if self.allowed_writes is not None and address not in self.allowed_writes:
            raise AssertionError(f'Instrument routine writes outside declared state/stack at ${address:04x}')
        super().__setitem__(address, value)


class ProgramsHarness:
    def __init__(self, programs, states, filt):
        source = SOURCE.read_text() + '\n'
        source += ''.join(f'{name}:\n  .byte $00,$00,$00\n' for name in ARRAYS)
        source += ''.join(f'{name}:\n  .byte $00\n' for name in SCALARS)
        tables = {}

        def columns(rows, fields, prefix, suffix=''):
            for name, read in fields.items():
                tables[prefix + name + suffix] = [read(rows[index]) if index in rows else 0
                                                  for index in range(max(rows) + 1)]

        instruments = {index // 8: row for index, row in programs.instruments.items()}
        columns(instruments, {
            'ad': lambda row: row.attack_decay, 'sr': lambda row: row.sustain_release,
            'filter_command': lambda row: row.filter_command, 'filter_row': lambda row: row.filter_row,
            'pwm_row': lambda row: row.pwm_row, 'wave_row': lambda row: row.wave_row,
        }, 'instrument_')
        columns(programs.pwm_rows, {
            'lower': lambda row: row.lower, 'upper': lambda row: row.upper, 'step': lambda row: row.step,
            'duration': lambda row: row.duration, 'reset_lo': lambda row: (row.reset_width or 0) & 255,
            'reset_hi': lambda row: (row.reset_width or 0) >> 8,
            'reset': lambda row: int(row.reset_width is not None), 'hold': lambda row: int(row.hold),
        }, 'pwm_')
        columns(programs.filter_rows, {
            'lower': lambda row: row.lower, 'upper': lambda row: row.upper, 'step': lambda row: row.step,
            'duration': lambda row: row.duration, 'reset_cutoff': lambda row: row.reset_cutoff or 0,
            'reset': lambda row: int(row.reset_cutoff is not None), 'hold': lambda row: int(row.hold),
        }, 'filter_', '_table')
        columns(programs.wave_rows, {
            'note': lambda row: row.note, 'control_table': lambda row: row.control,
            'mode': lambda row: int(row.mode == PitchMode.ABSOLUTE),
            'jump': lambda row: row.jump or 0, 'is_jump': lambda row: int(row.jump is not None),
        }, 'wave_')
        tables['frequency_table_lo'] = [word & 255 for word in programs.frequency_words]
        tables['frequency_table_hi'] = [word >> 8 for word in programs.frequency_words]
        for name, values in tables.items():
            source += name + ':\n  .byte ' + ','.join(f'${value:02x}' for value in values) + '\n'
        payload, self.symbols, _ = assemble(source, load=0x2000)
        self.memory = GuardedMemory()
        self.memory[0x2000:0x2000 + len(payload)] = payload
        self.cpu = cpu_type()(memory=self.memory)
        for voice, state in enumerate(states):
            self.set_voice(voice, packed_voice(state))
        for name, value in packed_filter(filt).items():
            self.memory[self.symbols[name]] = value

    def set_voice(self, voice, values):
        self.memory.allowed_writes = None
        for name, value in values.items():
            self.memory[self.symbols[name] + voice] = value

    def call(self, label, voice):
        self.memory.allowed_writes = {self.symbols[name] + voice for name in ARRAYS
                                     if name not in ('base_note', 'transpose', 'tuning', 'gate_mask', 'instrument')}
        self.memory.allowed_writes.update(self.symbols[name] for name in SCALARS)
        self.memory.allowed_writes.update(range(0x100, 0x200))
        self.cpu.x, self.cpu.a, self.cpu.y, self.cpu.p, self.cpu.sp = voice, 0xa5, 0x5a, 0x28, 255
        self.cpu.stPushWord(0x01ff)
        self.cpu.pc = self.symbols[label]
        start = self.cpu.processorCycles
        while self.cpu.pc != 0x0200:
            if self.cpu.processorCycles - start >= 10000:
                raise AssertionError('Instrument routine did not return within its bounded call')
            self.cpu.step()
        if self.cpu.x != voice or self.cpu.sp != 255:
            raise AssertionError('Instrument routine did not preserve X or stack')

    def voices(self):
        return [{name: self.memory[self.symbols[name] + voice] for name in packed_voice(VoiceState())}
                for voice in range(3)]

    def filter(self):
        return {name: self.memory[self.symbols[name]] for name in packed_filter(FilterState())}

    def output(self, voice):
        read = lambda name: self.memory[self.symbols[name] + voice]
        return (read('pulse_lo') | read('pulse_hi') << 8,
                read('frequency_lo') | read('frequency_hi') << 8, read('wave_control'), bool(read('absolute_pitch')))


def programs_fixture():
    return Programs(
        pwm_rows={0: PwmRow(4, 15, 0x40, 8, 0x100), 1: PwmRow(4, 15, 0x40, 15, hold=True),
                  2: PwmRow(10, 15, 0x70, 8, 0xd00), 3: PwmRow(10, 15, 0x10, 15, hold=True)},
        filter_rows={0: FilterRow(0, 0, 0, 0, 0xa0), 1: FilterRow(0x40, 0x80, 1, 15, hold=True)},
        wave_rows={0: WaveRow(90, 0x81, PitchMode.ABSOLUTE), 1: WaveRow(0, 0x41),
                   2: WaveRow(0, 0x40), 3: WaveRow(jump=2),
                   4: WaveRow(0, 0x11), 5: WaveRow(0, 0x21), 6: WaveRow(0, 0x41), 7: WaveRow(jump=6)},
        frequency_words=tuple((1000 + index * 316) & 65535 for index in range(96)),
        instruments={0: Instrument(2, 0x5f, 0xf1, 0, 0, 0), 16: Instrument(3, 0x3c, 0, 0, 2, 4)},
        filter_owner=0,
    )


class FlashdanceProgramsAssemblyTests(unittest.TestCase):
    def assert_states(self, harness, states, filt):
        self.assertEqual([packed_voice(state) for state in states], harness.voices())
        self.assertEqual(packed_filter(filt), harness.filter())

    def step(self, harness, states, filt, programs, voice, note=11, transpose=22, tuning=0, gate=255):
        harness.set_voice(voice, {'base_note': note, 'transpose': transpose, 'tuning': tuning, 'gate_mask': gate})
        expected = advance_voice(states[voice], programs, base_note=note, transpose_bytes=transpose, fine_tune=tuning, gate_mask=gate)
        harness.call('fd_step_pwm', voice)
        if voice == programs.filter_owner:
            advance_filter(filt, programs)
            harness.call('fd_step_filter', voice)
        harness.call('fd_step_wave', voice)
        self.assert_states(harness, states, filt)
        self.assertEqual((expected.pulse_width, expected.frequency_word, expected.control, expected.absolute_pitch), harness.output(voice))

    def test_initialization_separates_width_reset_from_first_body_direction_reset(self):
        programs = programs_fixture()
        states = [VoiceState(PwmState(7, 8, 2, 1, 1, 5, 0x888), 3) for _ in range(3)]
        filt = FilterState(1, 5, 1, 2, 3, 1, 0x20)
        harness = ProgramsHarness(programs, states, filt)
        for voice, offset in ((0, 0), (1, 16), (2, 0)):
            harness.set_voice(voice, {'instrument': offset // 8})
            initialize_voice(states[voice], programs.instruments[offset], programs)
            harness.call('fd_init_voice', voice)
            self.assert_states(harness, states, filt)
            initialize_filter(filt, programs.instruments[offset], programs)
            harness.call('fd_init_filter', voice)
            self.assert_states(harness, states, filt)
        self.assertEqual([1, 1, 1], [state.pwm.direction for state in states])
        for _ in range(12):
            for voice in (2, 1, 0):
                self.step(harness, states, filt, programs, voice)

    def test_pwm_carry_borrow_equality_overshoot_and_word_wrap(self):
        programs = programs_fixture()
        for width, step, direction in ((0xef0, 0x20, 0), (0xff0, 0x20, 0),
                                       (0x500, 1, 1), (0x400, 1, 1),
                                       (0, 1, 1), (0xfff0, 0x20, 0), (0xf00, 0, 0)):
            with self.subTest(width=width, step=step, direction=direction):
                states = [VoiceState(PwmState(4, 15, step, direction, 1, 4, width), 2) for _ in range(3)]
                filt = FilterState(row=1, remaining=15, lower=0x40, upper=0x80, step=1, cutoff=0x7f)
                harness = ProgramsHarness(programs, states, filt)
                for voice in (2, 1, 0):
                    self.step(harness, states, filt, programs, voice)

    def test_filter_comparison_inclusivity_and_byte_wrap(self):
        programs = programs_fixture()
        for cutoff, direction in ((0x7f, 0), (0x41, 1), (0x40, 1), (0xff, 0), (0, 1)):
            with self.subTest(cutoff=cutoff, direction=direction):
                states = [VoiceState(PwmState(row=1, remaining=10), 2) for _ in range(3)]
                filt = FilterState(1, 1, 0x40, 0x80, 1, direction, cutoff)
                harness = ProgramsHarness(programs, states, filt)
                advance_filter(filt, programs)
                harness.call('fd_step_filter', 2)
                self.assert_states(harness, states, filt)

    def test_wave_absolute_attack_relative_transposition_jump_and_word_carry(self):
        programs = programs_fixture()
        words = list(programs.frequency_words)
        words[90] = 65535
        programs = Programs(programs.pwm_rows, programs.filter_rows, programs.wave_rows, tuple(words), programs.instruments, 0)
        states = [VoiceState(PwmState(row=1, remaining=15), 0) for _ in range(3)]
        filt = FilterState(row=1, remaining=15)
        harness = ProgramsHarness(programs, states, filt)
        for _ in range(5):
            for voice in (2, 1, 0):
                self.step(harness, states, filt, programs, voice, tuning=1, gate=254)

    def test_seeded_state_interventions_preserve_other_voices_and_readonly_tables(self):
        randomizer = random.Random(8388001)
        programs = programs_fixture()
        for _ in range(20):
            states = [VoiceState(PwmState(randomizer.randrange(16), randomizer.randrange(16),
                                         randomizer.randrange(256), randomizer.randrange(2),
                                         1, randomizer.randrange(1, 16), randomizer.randrange(65536)), 2)
                      for _ in range(3)]
            filt = FilterState(1, randomizer.randrange(1, 16), randomizer.randrange(256), randomizer.randrange(256),
                               randomizer.randrange(256), randomizer.randrange(2), randomizer.randrange(256))
            harness = ProgramsHarness(programs, states, filt)
            for voice in (2, 1, 0):
                self.step(harness, states, filt, programs, voice, note=randomizer.randrange(70),
                          transpose=randomizer.randrange(13) * 2, tuning=randomizer.randrange(256))

    @unittest.skipUnless((ROOT / '.local/research/flashdance/drax-flashdance-conversion.sid').exists(), 'Requires pinned local Flashdance reference')
    def test_preloaded_state_and_all_selected_instruments_match_decoded_python_programs(self):
        data = (ROOT / '.local/research/flashdance/drax-flashdance-conversion.sid').read_bytes()
        programs, initial = decode_programs(data), decode_preloaded(data)
        states, filt = deepcopy(initial.voices), deepcopy(initial.filter)
        harness = ProgramsHarness(programs, states, filt)
        for _ in range(2):
            for voice in (2, 1, 0):
                self.step(harness, states, filt, programs, voice, note=0, transpose=0, tuning=voice, gate=0)
        for offset, instrument in programs.instruments.items():
            for voice in range(3):
                harness.set_voice(voice, {'instrument': offset // 8})
                initialize_voice(states[voice], instrument, programs)
                harness.call('fd_init_voice', voice)
                initialize_filter(filt, instrument, programs)
                harness.call('fd_init_filter', voice)
                self.assert_states(harness, states, filt)
            for _ in range(160):
                for voice in (2, 1, 0):
                    self.step(harness, states, filt, programs, voice, note=23, transpose=22, tuning=voice)


if __name__ == '__main__':
    unittest.main()
