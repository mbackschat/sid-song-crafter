import gzip
import json
from pathlib import Path
import random
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from rambo_player import sound_state, store_sound
from rambo_programs import advance_voice
from sid_assembler import assemble
from verify_player import cpu_type


SOURCE = ROOT / 'songs/players/rambo-sound.asm'
EVIDENCE = ROOT / 'evidence/rambo-sound-full'
MUTABLE_OFFSETS = (12, 16, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38)


def state_fixture(**changes):
    state = dict(frequencySteps=[0, 0, 0, 0], frequencyDurations=[0, 0, 0, 0],
                 frequencyDelay=0, frequencyFlags=0, pulseDurations=[0, 0],
                 pulseDelay=0, pulseFlags=0, pulseSteps=[0, 0], pulseInitial=0,
                 control=0x41, releaseCountdown=0, life=100, frequency=0x1000,
                 frequencyRemaining=[0, 0, 0, 0], pulse=0x0800, pulseRemaining=[0, 0])
    state.update(changes)
    return state


class GuardedMemory(list):
    def __init__(self):
        super().__init__([0] * 65536)
        self.allowed = None
        self.writes = []

    def __setitem__(self, address, value):
        if self.allowed is not None:
            if address not in self.allowed:
                raise AssertionError(f'SOUND writes outside its declared state at ${address:04x}')
            if 0xd400 <= address <= 0xd414:
                self.writes.append((address, value))
        super().__setitem__(address, value)


class SoundHarness:
    def __init__(self):
        declarations = ''.join(f'rb_sound_{voice}:\n .byte ' + ','.join('0' for _ in range(39)) + '\n'
                               for voice in range(3))
        declarations += 'rb_sound_ptr_lo:\n .byte rb_sound_0_lo,rb_sound_1_lo,rb_sound_2_lo\n'
        declarations += 'rb_sound_ptr_hi:\n .byte rb_sound_0_hi,rb_sound_1_hi,rb_sound_2_hi\n'
        declarations += 'rb_remaining:\n .byte 0,0,0\nrb_sid_offsets:\n .byte $00,$07,$0e\n'
        for label in ('rb_frequency_lo', 'rb_frequency_hi'):
            declarations += label + ':\n .byte ' + ','.join('0' for _ in range(256)) + '\n'
        constants = {f'rb_sound_{voice}_{half}': 0 for voice in range(3) for half in ('lo', 'hi')}
        payload, symbols, _ = assemble(SOURCE.read_text() + '\n' + declarations, constants, load=0x2000)
        constants = {f'rb_sound_{voice}_{half}': (symbols[f'rb_sound_{voice}'] >> shift) & 255
                     for voice in range(3) for half, shift in (('lo', 0), ('hi', 8))}
        payload, self.symbols, _ = assemble(SOURCE.read_text() + '\n' + declarations, constants, load=0x2000)
        self.memory = GuardedMemory()
        self.memory[0x2000:0x2000 + len(payload)] = payload
        self.cpu = cpu_type()(memory=self.memory)
        self.max_cycles = 0

    def set_frequencies(self, frequencies):
        self.memory.allowed = None
        for pitch in range(256):
            value = frequencies.get(pitch, 0)
            self.memory[self.symbols['rb_frequency_lo'] + pitch] = value & 255
            self.memory[self.symbols['rb_frequency_hi'] + pitch] = value >> 8

    def prepare(self, state, voice, remaining):
        self.memory.allowed = None
        block = [0] * 39
        block[24:26] = [0xa5, 0x5a]
        store_sound(block, state)
        base = self.symbols[f'rb_sound_{voice}']
        self.memory[base:base + 39] = block
        self.memory[self.symbols['rb_remaining'] + voice] = remaining
        self.memory.allowed = {base + offset for offset in MUTABLE_OFFSETS}
        self.memory.allowed.update(range(0xf0, 0xfc))
        self.memory.allowed.update(range(0x100, 0x200))
        self.memory.allowed.update(range(0xd400 + 7 * voice, 0xd407 + 7 * voice))
        self.memory.writes = []

    def call(self, voice, decimal=False):
        self.cpu.a, self.cpu.x, self.cpu.y = 0xa5, voice, 0x5a
        self.cpu.p, self.cpu.sp = (0x28 if decimal else 0x20), 255
        self.cpu.stPushWord(0x01ff)
        self.cpu.pc = self.symbols['rb_advance_sound']
        start = self.cpu.processorCycles
        while self.cpu.pc != 0x0200:
            if self.cpu.processorCycles - start >= 4000:
                raise AssertionError('SOUND did not return within its bounded invocation')
            self.cpu.step()
        cycles = self.cpu.processorCycles - start
        self.max_cycles = max(self.max_cycles, cycles)
        if self.cpu.x != voice or self.cpu.sp != 255:
            raise AssertionError('SOUND does not preserve X and stack')
        base = self.symbols[f'rb_sound_{voice}']
        if self.memory[base + 24:base + 26] != [0xa5, 0x5a]:
            raise AssertionError('SOUND changed the unused state bytes')
        return sound_state(self.memory[base:base + 39]), self.memory.writes


class RamboSoundAssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = SoundHarness()

    def compare(self, state, voice=0, remaining=0, frequencies=None, decimal=False):
        frequencies = {} if frequencies is None else frequencies
        expected = advance_voice(state, voice=voice, row_remaining=remaining, frequency_words=frequencies)
        self.harness.set_frequencies(frequencies)
        self.harness.prepare(state, voice, remaining)
        actual = self.harness.call(voice, decimal=decimal)
        self.assertEqual(expected, actual)
        return actual

    def test_full_initialized_sound_capture_matches_all_states_and_ordered_stores(self):
        self.harness.set_frequencies({int(k): v for k, v in json.loads((EVIDENCE / 'frequency-words.json').read_text()).items()})
        with gzip.open(EVIDENCE / 'bodies.json.gz', 'rt') as stream:
            bodies = json.load(stream)
        stores = 0
        for body in bodies:
            self.harness.prepare(body['before'], body['voice'], body['rowRemaining'])
            actual = self.harness.call(body['voice'])
            expected = (body['after'], [tuple(write) for write in body['writes']])
            if actual != expected:
                self.fail(f"SOUND mismatch at call {body['call']}, voice {body['voice']}: {actual!r} != {expected!r}")
            stores += len(actual[1])
        self.assertEqual(32448, len(bodies))
        self.assertEqual(57498, stores)

    def test_retained_isolated_original_execution_cases_match(self):
        with gzip.open(EVIDENCE / 'isolated.json.gz', 'rt') as stream:
            cases = json.load(stream)
        for case in cases:
            with self.subTest(label=case['label'], voice=case['voice']):
                frequencies = {int(k): v for k, v in (case['frequencyWords'] or {}).items()}
                actual = self.compare(case['before'], case['voice'], case['rowRemaining'], frequencies)
                self.assertEqual((case['after'], [tuple(write) for write in case['orderedWrites']]), actual)

    def test_lifetime_release_and_row_threshold_do_not_advance_suppressed_programs(self):
        for voice in range(3):
            for life, control, release, remaining in ((0, 0x49, 7, 0), (1, 0x41, 0, 0),
                                                     (2, 0x49, 7, 7), (2, 0x49, 7, 6),
                                                     (2, 0x09, 7, 6), (2, 0x41, 1, 0),
                                                     (2, 0x41, 2, 255)):
                with self.subTest(voice=voice, life=life, control=control, release=release, remaining=remaining):
                    self.compare(state_fixture(life=life, control=control, releaseCountdown=release,
                                               pulseFlags=1, pulseDurations=[1, 1], pulseSteps=[1, 65535],
                                               frequencyFlags=1, frequencyDurations=[1, 1, 1, 1],
                                               frequencySteps=[1, 2, 3, 4]), voice, remaining)

    def test_word_carry_wrap_phase_reload_delay_and_three_phase_voice_restriction(self):
        for voice in range(3):
            for frequency, step in ((0, 65535), (255, 1), (65535, 1), (0x10ff, 0xff01)):
                for phase in range(4):
                    with self.subTest(voice=voice, frequency=frequency, step=step, phase=phase):
                        remaining = [0] * 4
                        remaining[phase] = 1
                        self.compare(state_fixture(frequency=frequency, frequencySteps=[step] * 4,
                                                   frequencyRemaining=remaining, frequencyFlags=1,
                                                   frequencyDurations=[1, 0, 0, 7],
                                                   pulse=frequency, pulseSteps=[step, step], pulseFlags=1,
                                                   pulseRemaining=[int(phase % 2 == 0), int(phase % 2 == 1)],
                                                   pulseDurations=[1, 1]), voice, decimal=True)
            for flags in (1, 2, 8):
                with self.subTest(voice=voice, flags=flags):
                    self.compare(state_fixture(frequencyFlags=flags, frequencyDelay=1,
                                               frequencySteps=[1, 2, 3, 65535],
                                               frequencyRemaining=[1, 2, 3, 4], frequencyDurations=[1, 0, 2, 1]),
                                 voice, frequencies={2: 0x1234, 3: 0x5678})

    def test_pwm_repeat_bits_distinguish_counter_reload_and_initial_width_reset(self):
        for flags in (0, 2, 1, 0x80, 0x81):
            for delay in (0, 1, 255):
                for phase in (None, 0, 1):
                    with self.subTest(flags=flags, delay=delay, phase=phase):
                        remaining = [0, 0]
                        if phase is not None:
                            remaining[phase] = 1
                        self.compare(state_fixture(pulseFlags=flags, pulseDelay=delay, pulse=0xffff,
                                                   pulseInitial=0x80ff, pulseSteps=[1, 65535],
                                                   pulseDurations=[1, 2], pulseRemaining=remaining), voice=2)

    def test_edited_arpeggio_overlay_and_numeric_table_wrap_and_restart(self):
        frequencies = {pitch: (pitch * 317 + 0x80ff) & 65535 for pitch in range(256)}
        for voice in (0, 2):
            state = state_fixture(frequencyFlags=10, frequencySteps=[0x0109, 0xff80, 0x4321, 0x7f00],
                                  frequencyDurations=[127, 255, 250, 9], frequencyDelay=255)
            for _ in range(23):
                with self.subTest(voice=voice, position=state['frequencyDelay']):
                    state, _ = self.compare(state, voice, frequencies=frequencies)
        self.compare(state_fixture(frequencyFlags=8, frequencySteps=[7, 0, 0, 0],
                                   frequencyRemaining=[1, 0, 0, 0]), voice=1)

    def test_seeded_edited_state_cases_agree_without_changing_tables_or_other_voices(self):
        randomizer = random.Random(8388001)
        frequencies = {pitch: randomizer.randrange(65536) for pitch in range(256)}
        for case in range(180):
            voice = case % 3
            state = state_fixture(
                frequencySteps=[randomizer.randrange(65536) for _ in range(4)],
                frequencyDurations=[randomizer.randrange(1, 256) for _ in range(4)],
                frequencyDelay=randomizer.randrange(256), frequencyFlags=randomizer.choice((0, 1, 2, 5, 7)),
                pulseSteps=[randomizer.randrange(65536) for _ in range(2)],
                pulseDurations=[randomizer.randrange(1, 256) for _ in range(2)],
                pulseDelay=randomizer.choice((0, 0, 1, 255)), pulseFlags=randomizer.choice((0, 1, 2, 0x80, 0xff)),
                pulseInitial=randomizer.randrange(65536), pulse=randomizer.randrange(65536),
                control=randomizer.randrange(256), releaseCountdown=randomizer.randrange(256),
                life=randomizer.randrange(256), frequency=randomizer.randrange(65536),
                frequencyRemaining=[randomizer.choice((0, 0, 1, 255)) for _ in range(4)],
                pulseRemaining=[randomizer.choice((0, 0, 1, 255)) for _ in range(2)])
            with self.subTest(case=case, voice=voice):
                self.compare(state, voice, randomizer.randrange(256), frequencies)


if __name__ == '__main__':
    unittest.main()
