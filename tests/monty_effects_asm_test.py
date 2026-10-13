from dataclasses import replace
from pathlib import Path
import random
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from monty_title_programs import Instrument, PitchLookups, VoiceState, advance_body, initialize_note
from sid_assembler import assemble
from verify_player import cpu_type


VOICE_FIELDS = ('note', 'control', 'remaining', 'held_frequency_lo', 'held_frequency_hi',
                'voice_control', 'pulse_delay', 'pulse_direction', 'portamento', 'instrument_index')
INSTRUMENT_FIELDS = ('pulse_lo', 'pulse_hi', 'waveform', 'attack_decay', 'sustain_release',
                     'vibrato_depth', 'pulse_value', 'effects')


def packed_state(state):
    values = vars(state).copy()
    word = values.pop('held_frequency')
    values.update(held_frequency_lo=word & 255, held_frequency_hi=word >> 8)
    return values


def packed_instrument(instrument):
    values = vars(instrument).copy()
    word = values.pop('pulse_word')
    values.update(pulse_lo=word & 255, pulse_hi=word >> 8)
    return values


class GuardedMemory(list):
    def __init__(self):
        super().__init__([0] * 65536)
        self.allowed = None
        self.writes = []

    def __setitem__(self, address, value):
        if self.allowed is not None:
            if address not in self.allowed:
                raise AssertionError(f'Unexpected memory write ${address:04x}')
            if 0xd400 <= address <= 0xd418:
                self.writes.append((address, value))
        super().__setitem__(address, value)


class EffectsHarness:
    def __init__(self):
        declarations = ''.join(f'mo_{name}:\n .byte 0,0,0\n' for name in VOICE_FIELDS)
        declarations += ''.join(f'mo_inst_{name}:\n .byte 0,0,0,0\n' for name in INSTRUMENT_FIELDS)
        declarations += ''.join(f'mo_{name}:\n .byte 0\n' for name in
                                ('counter', 'score_tick', 'append', 'lookup_lo', 'lookup_hi', 'test_alias'))
        declarations += 'mo_sid_offsets:\n .byte $00,$07,$0e\n'
        for name in ('test_freq_lo', 'test_freq_hi'):
            declarations += f'mo_{name}:\n .byte ' + ','.join('0' for _ in range(129)) + '\n'
        stubs = '''
mo_lookup_base:
  CMP #$74
  BNE mo_test_normal
  LDY mo_test_alias
  BEQ mo_test_normal
  LDA mo_pulse_direction,X
  STA mo_lookup_lo
  LDY mo_instrument_index,X
  LDA mo_inst_pulse_hi,Y
  STA mo_lookup_hi
  RTS
mo_test_normal:
  AND #$7f
  TAY
  JMP mo_test_lookup
mo_lookup_adjacent:
  AND #$7f
  TAY
  INY
mo_test_lookup:
  LDA mo_test_freq_lo,Y
  STA mo_lookup_lo
  LDA mo_test_freq_hi,Y
  STA mo_lookup_hi
  RTS
mo_write_control:
  LDY mo_sid_offsets,X
  STA $d404,Y
  RTS
'''
        cpu = cpu_type()
        payload, self.symbols, _ = assemble((ROOT / 'songs/players/monty-effects.asm').read_text()
                                            + stubs + declarations, load=0x2000)
        self.memory = GuardedMemory()
        self.memory[0x2000:0x2000 + len(payload)] = payload
        self.cpu = cpu(memory=self.memory)
        self.scratch = {address for name, address in self.symbols.items()
                        if name.startswith('mo_fx_') and address >= self.symbols['mo_fx_scratch']}

    def prepare(self, state, instrument, table, voice, counter, release, append, alias):
        self.memory.allowed = None
        for channel in range(3):
            for field, value in packed_state(state).items():
                self.memory[self.symbols['mo_' + field] + channel] = value
            self.memory[self.symbols['mo_instrument_index'] + channel] = 3
        for index in range(4):
            for field, value in packed_instrument(instrument).items():
                self.memory[self.symbols['mo_inst_' + field] + index] = value
        for index, word in enumerate(table):
            self.memory[self.symbols['mo_test_freq_lo'] + index] = word & 255
            self.memory[self.symbols['mo_test_freq_hi'] + index] = word >> 8
        for field, value in dict(counter=counter, score_tick=int(release), append=int(append), test_alias=int(alias)).items():
            self.memory[self.symbols['mo_' + field]] = value
        self.memory.allowed = {self.symbols['mo_' + name] + voice for name in VOICE_FIELDS}
        self.memory.allowed.update(self.symbols['mo_inst_' + name] + 3 for name in ('pulse_lo', 'pulse_hi'))
        self.memory.allowed.update(self.scratch)
        self.memory.allowed.update(self.symbols['mo_lookup_' + name] for name in ('lo', 'hi'))
        self.memory.allowed.update(range(0x100, 0x200))
        self.memory.allowed.update(range(0xd400 + 7 * voice, 0xd407 + 7 * voice))
        self.memory.writes = []

    def call(self, voice, entry):
        self.cpu.x, self.cpu.a, self.cpu.y = voice, 0xa5, 0x5a
        self.cpu.p, self.cpu.sp = 0x20, 255
        self.cpu.stPushWord(0x01ff)
        self.cpu.pc = self.symbols[entry]
        start = self.cpu.processorCycles
        while self.cpu.pc != 0x0200:
            if self.cpu.processorCycles - start >= 19656:
                raise AssertionError('Sound program exceeds a PAL call')
            self.cpu.step()
        if self.cpu.x != voice or self.cpu.sp != 255:
            raise AssertionError('Sound program corrupts voice index or stack')


class MontyEffectsAssemblyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = EffectsHarness()

    def compare(self, state=None, instrument=None, *, voice=1, counter=7, release=True,
                initialize=False, append=False, table=None, alias=False):
        state = state or VoiceState(30, 31, 5, 0x4567, 0x41, 0, 0, 0)
        instrument = instrument or Instrument(0xdc0, 0x41, 0x12, 0x98, 2, 0xe7, 0)
        table = table or [(197 * index + 65500) & 65535 for index in range(129)]
        index = state.note & 127
        octave_index = ((state.note + (12 if counter & 1 else 0)) & 255) & 127
        lookups = PitchLookups(table[index], table[index + 1], table[octave_index])
        if initialize:
            expected = initialize_note(state, instrument, append=True) if append else initialize_note(
                state, instrument, note=state.note, frequency_word=lookups.base_word)
        else:
            resolver = (lambda current, patch: current.pulse_direction | ((patch.pulse_word >> 8) << 8)) if alias else None
            expected = advance_body(state, instrument, lookups, counter=counter, release_check=release,
                                    octave_resolver=resolver)
        harness = self.harness
        harness.prepare(state, instrument, table, voice, counter, release, append, alias)
        harness.call(voice, 'mo_initialize_note' if initialize else 'mo_advance_body')
        actual = [(address - 0xd400 - 7 * voice, value) for address, value in harness.memory.writes]
        self.assertEqual(list(expected.writes), actual, (state, instrument, counter, release))
        for channel in range(3):
            for field, value in packed_state(expected.state if channel == voice else state).items():
                self.assertEqual(value, harness.memory[harness.symbols['mo_' + field] + channel], (channel, field))
        for patch in range(4):
            for field, value in packed_instrument(expected.instrument if patch == 3 else instrument).items():
                self.assertEqual(value, harness.memory[harness.symbols['mo_inst_' + field] + patch], (patch, field))
        return expected

    def test_new_note_and_append_preserve_pwm_phase_and_store_order(self):
        for voice in range(3):
            for append in (False, True):
                self.compare(VoiceState(255, 0xff, 15, 0xffff, 0x81, 217, 255, 126),
                             voice=voice, initialize=True, append=append)

    def test_release_and_all_effects_keep_ordered_overwrites(self):
        for control in (0, 1, 7, 8, 31, 32, 63, 255):
            for remaining in (0, 1, 2, 31, 255):
                for waveform in (0, 1, 0x41):
                    self.compare(VoiceState(30, control, remaining, 0x0167, waveform, 0, 0, 127),
                                 Instrument(0xdc0, waveform, 0, 0, 1, 0xe0, 7))

    def test_vibrato_signed_shift_depth_and_adjacent_lookup_boundaries(self):
        for depth in (0, 1, 2, 15, 16, 127, 128, 129, 255):
            for counter in range(8):
                for note in (0, 127, 128, 255):
                    self.compare(VoiceState(note, 31, 1, 0x1234, 0x41, 0, 0, 0),
                                 Instrument(0x800, 0x41, 0, 0, depth, 0, 0), counter=counter)

    def test_pwm_wrap_delay_direction_and_exact_turning_limits(self):
        for width in (0, 0x7ff, 0x820, 0x8e0, 0xdc0, 0xe00, 0xfff, 0xffff):
            for delay in (0, 1, 127, 128, 129, 255):
                for direction in (0, 1, 2, 255):
                    self.compare(VoiceState(30, 7, 1, 0x1234, 0x41, delay, direction, 0),
                                 Instrument(width, 0x41, 0, 0, 0, 0xe7, 0))

    def test_octave_alias_observes_mutated_shared_width_and_voice_direction(self):
        result = self.compare(VoiceState(104, 31, 8, 0x4141, 0x41, 0, 0, 0),
                              Instrument(0xdc0, 0x41, 0, 0, 0, 0xe0, 4), alias=True)
        self.assertEqual(((1, 14), (0, 1)), result.writes[-2:])

    def test_seeded_combined_programs_cover_unsigned_state_and_shared_patch(self):
        rng = random.Random(8388001)
        table = [rng.randrange(65536) for _ in range(129)]
        for case in range(512):
            state = VoiceState(rng.randrange(256), rng.randrange(256), rng.randrange(256), rng.randrange(65536),
                               rng.randrange(256), rng.randrange(256), rng.randrange(256), rng.randrange(256))
            patch = Instrument(rng.randrange(65536), rng.randrange(256), rng.randrange(256), rng.randrange(256),
                               rng.randrange(256), rng.randrange(256), case % 8)
            with self.subTest(case=case):
                self.compare(state, patch, voice=case % 3, counter=rng.randrange(256), release=case % 2 == 0, table=table)


if __name__ == '__main__':
    unittest.main()
