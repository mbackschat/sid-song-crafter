from copy import deepcopy
from pathlib import Path
import random
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from flashdance_pitch import PitchEffects, SlideState, VibratoState, advance_pitch, note_changed
from sid_assembler import assemble
from verify_player import cpu_type


SOURCE = ROOT / 'songs/players/flashdance-pitch.asm'
ARRAYS = (
    'slide_enabled', 'slide_step_lo', 'slide_step_hi', 'slide_subtract', 'slide_offset_lo', 'slide_offset_hi',
    'vibrato_enabled', 'vibrato_interval', 'vibrato_remaining', 'vibrato_direction', 'vibrato_shift',
    'vibrato_growth', 'vibrato_depth', 'vibrato_offset_lo', 'vibrato_offset_hi',
    'base_note', 'frequency_lo', 'frequency_hi', 'absolute_pitch',
)


def packed(state):
    slide, vibrato = state.slide, state.vibrato
    return {
        'slide_enabled': slide.enabled, 'slide_step_lo': slide.step & 255, 'slide_step_hi': slide.step >> 8,
        'slide_subtract': int(slide.subtract), 'slide_offset_lo': slide.offset & 255, 'slide_offset_hi': slide.offset >> 8,
        'vibrato_enabled': vibrato.enabled, 'vibrato_interval': vibrato.interval,
        'vibrato_remaining': vibrato.remaining, 'vibrato_direction': vibrato.direction,
        'vibrato_shift': vibrato.shift, 'vibrato_growth': vibrato.growth, 'vibrato_depth': vibrato.depth,
        'vibrato_offset_lo': vibrato.offset & 255, 'vibrato_offset_hi': vibrato.offset >> 8,
    }


class GuardedMemory(list):
    def __init__(self):
        super().__init__([0] * 65536)
        self.allowed_writes = None

    def __setitem__(self, address, value):
        if self.allowed_writes is not None and address not in self.allowed_writes:
            raise AssertionError(f'Pitch routine writes outside its state/stack at ${address:04x}')
        super().__setitem__(address, value)


class PitchHarness:
    def __init__(self, states, table):
        declarations = ''.join(f'{name}:\n  .byte $00,$00,$00\n' for name in ARRAYS)
        declarations += 'fd_tmp_lo:\n  .byte $00\nfd_tmp_hi:\n  .byte $00\n'
        for name, values in (('frequency_table_lo', [word & 255 for word in table]),
                             ('frequency_table_hi', [word >> 8 for word in table])):
            declarations += name + ':\n  .byte ' + ','.join(f'${value:02x}' for value in values) + '\n'
        payload, self.symbols, _ = assemble(SOURCE.read_text() + '\n' + declarations, load=0x2000)
        self.memory = GuardedMemory()
        self.memory[0x2000:0x2000 + len(payload)] = payload
        self.cpu = cpu_type()(memory=self.memory)
        for voice, state in enumerate(states):
            for name, value in packed(state).items():
                self.memory[self.symbols[name] + voice] = value

    def write_inputs(self, voice, frequency, note, absolute):
        self.memory.allowed_writes = None
        for name, value in (('frequency_lo', frequency & 255), ('frequency_hi', frequency >> 8),
                            ('base_note', note), ('absolute_pitch', int(absolute))):
            self.memory[self.symbols[name] + voice] = value

    def call(self, label, voice):
        self.memory.allowed_writes = {self.symbols[name] + voice for name in ARRAYS
                                     if name not in ('base_note', 'absolute_pitch')}
        self.memory.allowed_writes.update((self.symbols['fd_tmp_lo'], self.symbols['fd_tmp_hi']))
        self.memory.allowed_writes.update(range(0x100, 0x200))
        self.cpu.x = voice
        self.cpu.a, self.cpu.y = 0xa5, 0x5a
        self.cpu.p = 0x28
        self.cpu.sp = 255
        self.cpu.stPushWord(0x01ff)
        self.cpu.pc = self.symbols[label]
        first_cycle = self.cpu.processorCycles
        while self.cpu.pc != 0x0200:
            if self.cpu.processorCycles - first_cycle >= 10000:
                raise AssertionError('Pitch routine fails to return within its bounded call')
            self.cpu.step()
        if self.cpu.x != voice or self.cpu.sp != 255:
            raise AssertionError('Pitch routine does not preserve X or the call stack')

    def values(self, voice):
        return {name: self.memory[self.symbols[name] + voice] for name in packed(PitchEffects())}

    def frequency(self, voice):
        return self.memory[self.symbols['frequency_lo'] + voice] | self.memory[self.symbols['frequency_hi'] + voice] << 8


class FlashdancePitchAssemblyTest(unittest.TestCase):
    def compare_run(self, initial, actions, table=None):
        table = table or [((1000 + index * 316) & 65535) for index in range(96)]
        states = deepcopy(initial)
        harness = PitchHarness(states, table)
        outputs = []
        for voice, action, frequency, note, absolute in actions:
            harness.write_inputs(voice, frequency, note, absolute)
            if action == 'note':
                note_changed(states[voice])
                expected = frequency
                harness.call('fd_note_changed', voice)
            else:
                expected = advance_pitch(states[voice], frequency, note, table, absolute=absolute)
                harness.call('fd_step_pitch', voice)
            self.assertEqual(expected, harness.frequency(voice), (voice, action, note, absolute))
            for channel, state in enumerate(states):
                self.assertEqual(packed(state), harness.values(channel), (voice, channel, action))
            outputs.append(expected)
        return outputs

    def test_vibrato_first_reversal_and_subsequent_intervals_match_ten_body_calls(self):
        state = PitchEffects(vibrato=VibratoState(enabled=1, interval=4, remaining=3, shift=2))
        actions = [(1, 'step', 10000, 0, False)] * 10
        result = self.compare_run([PitchEffects(), state, PitchEffects()], actions)
        self.assertEqual([10079, 10158, 10237, 10158, 10079, 10000, 9921, 9842, 9921, 10000], result)

    def test_absolute_slide_accumulates_and_has_priority_over_vibrato(self):
        state = PitchEffects(slide=SlideState(enabled=1, step=40),
                             vibrato=VibratoState(enabled=1, interval=4, remaining=3, shift=2))
        result = self.compare_run([state, PitchEffects(), PitchEffects()],
                                  [(0, 'step', 50000, 0, True), (0, 'step', 1000, 0, False),
                                   (0, 'note', 1000, 0, False), (0, 'step', 1000, 0, False)])
        self.assertEqual([50000, 1080, 1000, 1000], result)

    def test_note_change_consumes_counts_without_erasing_phase_or_offsets(self):
        states = [PitchEffects(slide=SlideState(enabled=255, step=40, offset=80),
                               vibrato=VibratoState(enabled=2, interval=4, remaining=2, offset=158)),
                  PitchEffects(vibrato=VibratoState(enabled=1, interval=4, remaining=3, shift=2)),
                  PitchEffects()]
        self.compare_run(states, [(0, 'note', 1000, 0, False), (1, 'step', 1000, 4, True),
                                  (0, 'note', 1000, 0, False), (1, 'note', 1000, 4, False),
                                  (2, 'note', 1000, 0, False)])

    def test_slide_add_subtract_and_frequency_arithmetic_wrap_at_word_boundaries(self):
        states = [PitchEffects(slide=SlideState(enabled=1, step=40, offset=65520)),
                  PitchEffects(slide=SlideState(enabled=1, step=0x1234, subtract=True, offset=5)),
                  PitchEffects(slide=SlideState(enabled=1, step=65535, offset=65535))]
        actions = [(voice, 'step', frequency, 0, False) for frequency in (10, 65535, 1, 0)
                   for voice in range(3)]
        self.compare_run(states, actions)

    def test_vibrato_subtraction_growth_shift_and_counter_wrap_match_binary_model(self):
        table = [((index * 797 + 50000) & 65535) for index in range(96)]
        table[20], table[21] = 1000, 1256
        states = [PitchEffects(vibrato=VibratoState(enabled=1, interval=4, remaining=3,
                                                   shift=2, depth=255, growth=2)),
                  PitchEffects(vibrato=VibratoState(enabled=1, interval=0, remaining=0,
                                                   shift=0, direction=1, offset=65535, growth=255, depth=128)),
                  PitchEffects(vibrato=VibratoState(enabled=1, interval=255, remaining=128,
                                                   shift=16, direction=1, offset=65535, growth=1, depth=255))]
        actions = [(voice, 'step', 10000 if voice == 0 else 65535, 20 if voice == 0 else 94, bool(step & 1))
                   for step in range(12) for voice in range(3)]
        result = self.compare_run(states, actions, table)
        self.assertEqual(10000, result[0])
        self.assertEqual(10128, result[3])

    def test_seeded_state_interventions_match_across_all_voices(self):
        randomizer = random.Random(8388001)
        for shift in (0, 1, 2, 7, 15, 16, 255):
            with self.subTest(shift=shift):
                states = [PitchEffects(
                    slide=SlideState(enabled=int(voice == 0), step=randomizer.randrange(65536),
                                     subtract=bool(shift & 1), offset=randomizer.randrange(65536)),
                    vibrato=VibratoState(enabled=2, interval=randomizer.randrange(256),
                                         remaining=randomizer.randrange(256), direction=voice & 1,
                                         shift=shift, growth=randomizer.randrange(256),
                                         depth=randomizer.randrange(256), offset=randomizer.randrange(65536)))
                    for voice in range(3)]
                actions = [(voice, 'step', randomizer.randrange(65536), randomizer.randrange(95), bool(step & 1))
                           for step in range(4) for voice in range(3)]
                actions += [(voice, 'note', 1000, 0, False) for voice in range(3)]
                actions += [(voice, 'step', 65535, 94, False) for voice in range(3)]
                self.compare_run(states, actions)


if __name__ == '__main__':
    unittest.main()
