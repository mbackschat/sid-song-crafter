from dataclasses import replace
from pathlib import Path
import random
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from cybernoid_pitch import GlideAction, PitchInputs, PitchParameters, PitchState, advance_pitch
from sid_assembler import assemble
from verify_player import cpu_type


SOURCE = ROOT / 'songs/players/cybernoid-pitch.asm'
STATE_FIELDS = (
    'base_pitch', 'frequency_lo', 'frequency_hi', 'held_frequency_lo', 'held_frequency_hi',
    'vibrato_extent', 'vibrato_direction', 'vibrato_position', 'vibrato_age',
    'glide_enabled', 'glide_active', 'glide_control', 'glide_target',
)
INPUT_FIELDS = ('current_pitch', 'note_age', 'row_remaining', 'row_duration', 'sound_index')
GLOBALS = ('fx1', 'fx3', 'tempo_reload')


def default_state(**changes):
    return replace(PitchState(30, 0x1234, 0x5678, 6, 0, 0, 0, 0, 0, 0x42, 90), **changes)


def packed(state):
    values = vars(state).copy()
    values['base_pitch'] = values.pop('base_note')
    for field in ('frequency', 'held_frequency'):
        word = values.pop(field)
        values[field + '_lo'], values[field + '_hi'] = word & 255, word >> 8
    return values


class GuardedMemory(list):
    def __init__(self):
        super().__init__([0] * 65536)
        self.allowed_writes = None

    def __setitem__(self, address, value):
        if self.allowed_writes is not None and address not in self.allowed_writes:
            raise AssertionError(f'Pitch routine writes outside its voice state, scratch or stack at ${address:04x}')
        super().__setitem__(address, value)


class PitchHarness:
    def __init__(self):
        declarations = ''.join(f'cy_{name}:\n  .byte $00,$00,$00\n' for name in STATE_FIELDS + INPUT_FIELDS)
        declarations += ''.join(f'cy_{name}:\n  .byte $00\n' for name in GLOBALS)
        for name, size in (('freq_lo', 257), ('freq_hi', 257), ('vibrato_wait', 256)):
            declarations += f'cy_{name}:\n  .byte ' + ','.join('$00' for _ in range(size)) + '\n'
        cpu = cpu_type()
        payload, self.symbols, _ = assemble(SOURCE.read_text() + '\n' + declarations, load=0x2000)
        self.memory = GuardedMemory()
        self.memory[0x2000:0x2000 + len(payload)] = payload
        self.cpu = cpu(memory=self.memory)
        self.scratch = {address for name, address in self.symbols.items()
                        if name.startswith('cy_pitch_') and address >= self.symbols['cy_pitch_scratch']}

    def prepare(self, states, table, voice, parameters, timing):
        self.memory.allowed_writes = None
        for channel, state in enumerate(states):
            for name, value in packed(state).items():
                self.memory[self.symbols['cy_' + name] + channel] = value
        for index, word in enumerate(table):
            self.memory[self.symbols['cy_freq_lo'] + index] = word & 255
            self.memory[self.symbols['cy_freq_hi'] + index] = word >> 8
        for name, value in timing.items():
            if name == 'speed':
                self.memory[self.symbols['cy_tempo_reload']] = value
            else:
                self.memory[self.symbols['cy_' + name] + voice] = value
        self.memory[self.symbols['cy_sound_index'] + voice] = 255
        self.memory[self.symbols['cy_vibrato_wait'] + 255] = parameters.vibrato_wait
        self.memory[self.symbols['cy_fx1']] = parameters.vibrato_control
        self.memory[self.symbols['cy_fx3']] = 0x10 if parameters.drum_mode else 0

    def call(self, voice):
        self.memory.allowed_writes = {self.symbols['cy_' + name] + voice for name in STATE_FIELDS}
        self.memory.allowed_writes.update(self.scratch)
        self.memory.allowed_writes.update(range(0x100, 0x200))
        self.cpu.x, self.cpu.a, self.cpu.y = voice, 0xa5, 0x5a
        self.cpu.p, self.cpu.sp = 0x28, 255
        self.cpu.stPushWord(0x01ff)
        self.cpu.pc = self.symbols['cy_advance_pitch']
        first_cycle = self.cpu.processorCycles
        while self.cpu.pc != 0x0200:
            if self.cpu.processorCycles - first_cycle >= 20000:
                raise AssertionError('Pitch routine fails to return within its bounded call')
            self.cpu.step()
        if self.cpu.x != voice or self.cpu.sp != 255:
            raise AssertionError('Pitch routine does not preserve X or the call stack')
        return self.cpu.processorCycles - first_cycle

    def values(self, voice):
        return {name: self.memory[self.symbols['cy_' + name] + voice] for name in STATE_FIELDS}


class CybernoidPitchAssemblyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = PitchHarness()

    def compare(self, state, *, control=0x53, wait=12, drum=False, current_pitch=60,
                note_age=255, row_remaining=7, row_duration=12, speed=2, table=None, voice=1):
        table = table if table is not None else [(700 + index * 197) & 65535 for index in range(257)]
        parameters = PitchParameters(control, wait, drum)
        inputs = PitchInputs(table[current_pitch], table[current_pitch + 1], table[state.base_note],
                             table[state.glide_target], note_age, row_remaining, row_duration, speed)
        result = advance_pitch(state, parameters, inputs)
        states = [default_state(base_note=17, vibrato_direction=0x80),
                  default_state(base_note=18, vibrato_age=255),
                  default_state(base_note=19, vibrato_position=255)]
        states[voice] = state
        timing = dict(current_pitch=current_pitch, note_age=note_age, row_remaining=row_remaining,
                      row_duration=row_duration, speed=speed)
        self.harness.prepare(states, table, voice, parameters, timing)
        self.harness.call(voice)
        states[voice] = result.state
        for channel, expected in enumerate(states):
            self.assertEqual(packed(expected), self.harness.values(channel),
                             (channel, state, parameters, inputs, result))
        return result

    def test_bypass_preserves_nondefault_buffers_and_all_other_voices(self):
        state = default_state(vibrato_age=47, vibrato_direction=0x80, vibrato_position=128)
        for voice in range(3):
            for control, drum, active in ((0, False, 0), (0x53, True, 0), (0xff, False, 255)):
                with self.subTest(voice=voice, control=control, drum=drum, active=active):
                    self.compare(replace(state, glide_active=active), control=control, drum=drum, voice=voice)

    def test_phase_signed_fallthrough_centered_wait_and_wrapping_positions(self):
        for extent in (0, 1, 2, 5, 7):
            for direction in (0, 127, 128, 129, 255):
                for position in (0, 1, 127, 128, 129, 255):
                    for note_age in (0, 12):
                        with self.subTest(extent=extent, direction=direction, position=position, age=note_age):
                            self.compare(default_state(vibrato_direction=direction, vibrato_position=position),
                                         control=(extent << 4) | 3, note_age=note_age)

    def test_growth_retains_word_subtraction_carry_and_saturates_age(self):
        table = [0] * 257
        for effective, adjacent in ((0, 65535), (65535, 0), (0xfffe, 0x0010),
                                    (0x1234, 0x1234), (0x1234, 0x1334)):
            table[60], table[61] = effective, adjacent
            for age in (0, 47, 48, 128, 255):
                for shift in (0, 1, 7, 15):
                    with self.subTest(effective=effective, adjacent=adjacent, age=age, shift=shift):
                        self.compare(default_state(vibrato_age=age), control=0xf0 | shift, table=table)

    def test_effective_index_255_reads_adjacent_index_256_without_wrapping(self):
        table = [0x7000] * 257
        table[255], table[256], table[0] = 1000, 1256, 50000
        result = self.compare(default_state(vibrato_direction=255, vibrato_position=2),
                              control=0x03, current_pitch=255, table=table)
        self.assertEqual(32, result.vibrato_delta)
        self.assertEqual(1032, result.state.frequency)

    def test_glide_wait_and_completion_use_byte_timing_and_replace_base_note(self):
        state = default_state(glide_enabled=255, glide_control=0x40)
        waiting = self.compare(state, control=0, row_remaining=13, row_duration=12)
        self.assertEqual(GlideAction.WAIT, waiting.glide_action)
        completed = self.compare(state, control=0, row_remaining=1, row_duration=12)
        self.assertEqual(GlideAction.COMPLETE, completed.glide_action)
        self.assertEqual(90, completed.state.base_note)
        self.assertEqual((0, 0), (completed.state.glide_enabled, completed.state.glide_active))
        self.compare(replace(state, glide_control=0xff), control=0, row_remaining=250, row_duration=10)

    def test_glide_divisor_carry_signed_speed_and_fifteen_bit_rounding_edges(self):
        table = [0] * 257
        for distance in (0, 1, 199, 200, 32767, 32768, 32769, 65535):
            for subtract in (False, True):
                table[30], table[90] = (distance, 0) if subtract else (0, distance)
                for length, speed in ((1, 0), (2, 0), (2, 99), (2, 127), (15, 17), (15, 128), (15, 129), (15, 255)):
                    with self.subTest(distance=distance, subtract=subtract, length=length, speed=speed):
                        state = default_state(glide_enabled=1, glide_active=1, glide_control=length << 4 | 1,
                                              held_frequency=0 if subtract else 65535)
                        result = self.compare(state, control=0xff, row_remaining=12, row_duration=13,
                                              speed=speed, table=table)
                        self.assertEqual(GlideAction.INTERPOLATE, result.glide_action)

    def test_vibrato_then_waiting_or_starting_glide_keeps_the_new_held_buffer(self):
        for control, remaining in ((0x42, 7), (0x42, 10), (0x43, 9)):
            self.compare(default_state(glide_enabled=1, glide_control=control, vibrato_position=3),
                         row_remaining=remaining, row_duration=12)

    def test_seeded_nondefault_state_and_parameter_matrix_matches_numeric_model(self):
        randomizer = random.Random(8388001)
        table = [randomizer.randrange(65536) for _ in range(257)]
        for case in range(384):
            state = PitchState(randomizer.randrange(256), randomizer.randrange(65536),
                               randomizer.randrange(65536), randomizer.randrange(256),
                               randomizer.randrange(256), randomizer.randrange(256),
                               randomizer.randrange(256), case % 2, (case // 2) % 2,
                               randomizer.randrange(256), randomizer.randrange(256))
            with self.subTest(case=case):
                self.compare(state, control=randomizer.randrange(256), wait=randomizer.randrange(256),
                             drum=case % 3 == 0, current_pitch=randomizer.randrange(256),
                             note_age=randomizer.randrange(256), row_remaining=randomizer.randrange(256),
                             row_duration=randomizer.randrange(256), speed=randomizer.randrange(256),
                             table=table, voice=case % 3)


if __name__ == '__main__':
    unittest.main()
