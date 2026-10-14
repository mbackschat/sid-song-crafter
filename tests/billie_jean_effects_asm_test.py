"""Compare independently generated sound assembly with pure Billie Jean helpers."""

from dataclasses import fields, replace
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'scripts/studies/billie-jean'))
import billie_jean_programs as sound
import billie_jean_effects_asm as effects
from psid_audit import AuditMemory
from sid_assembler import assemble
from verify_player import cpu_type


def example():
    pitches, waves = [126] * 256, [65] * 256
    pitches[8:12] = [148, 2, 127, 126]
    waves[8:12] = [129, 65, 0, 0]
    bank = sound.Programs(frequencies={index: (index * 257 + 0x10ff) & 65535 for index in range(128)},
        pitches=pitches, waveforms=waves)
    instrument = sound.Instrument(attack_decay=3, sustain_release=88, pulse_initial=207,
        pulse_step=120, pulse_lower=8, pulse_upper=14, vibrato_delay=12,
        vibrato_step=240, vibrato_half=5, vibrato_period=10, vibrato_seed=4,
        filter_initialize=1, filter_start=32, filter_enabled=1, filter_step=1,
        filter_mode=48, wave_loop=1)
    return {0: sound.Instrument(), 8: instrument}, bank


class GuardedMemory(AuditMemory):
    allowed = None

    def __setitem__(self, address, value):
        if self.allowed is not None and address not in self.allowed:
            raise AssertionError(f'Effects changed undeclared memory at ${address:04x}')
        super().__setitem__(address, value)


class Harness:
    def __init__(self, instruments, bank):
        values = effects.sound_state_values([sound.VoiceState() for _ in range(3)], sound.FilterState())
        values.update({name: [0] * size for name, size in effects.SCRATCH_STORAGE})
        values['bj_divider'] = [0]
        source = effects.generate(instruments, bank) + effects.declarations(values)
        source += '\nbj_test_frame:\n  LDX #$02\n  JSR bj_note_setup\n  JSR bj_advance_age\n  DEX\n  JSR bj_body\n  JSR bj_advance_age\n  DEX\n  JSR bj_body\n  JSR bj_advance_age\n  JSR bj_global_output\n  RTS\n'
        cpu_class = cpu_type()
        payload, self.symbols, _ = assemble(source, load=0x2000)
        self.memory = GuardedMemory()
        self.memory.data[0x2000:0x2000 + len(payload)] = payload
        self.cpu = cpu_class(memory=self.memory)

    def prepare(self, state, shared, voice, divider):
        states = [sound.VoiceState(frequency=0xa55a, pulse=0x5aa5, waveform=0xa5) for _ in range(3)]
        states[voice] = state
        for label, values in effects.sound_state_values(states, shared).items():
            self.memory.data[self.symbols[label]:self.symbols[label] + len(values)] = values
        self.memory.data[self.symbols['bj_divider']] = divider
        self.memory.writes.clear()
        self.memory.allowed = {self.symbols[label] + voice for labels in effects.VOICE_FIELD_LABELS.values() for label in labels}
        self.memory.allowed.update(self.symbols[label] for labels in effects.FILTER_FIELD_LABELS.values() for label in labels)
        self.memory.allowed.update(self.symbols[label] + index for label, size in effects.SCRATCH_STORAGE for index in range(size))
        self.memory.allowed.update(range(0xe0, 0xf0))
        self.memory.allowed.update(range(0x100, 0x200))
        self.memory.allowed.update(range(0xd400 + 7 * voice, 0xd407 + 7 * voice))
        self.memory.allowed.update((0xd416, 0xd417, 0xd418))
        self.before = list(self.memory.data)

    def call(self, entry, voice, expected_x=None):
        self.cpu.a, self.cpu.x, self.cpu.y, self.cpu.sp, self.cpu.p = 0xa5, voice, 0x5a, 255, 0x28
        self.cpu.stPushWord(0x01ff)
        self.cpu.pc = self.symbols[entry]
        start = self.cpu.processorCycles
        while self.cpu.pc != 0x0200:
            if self.cpu.processorCycles - start >= 19656:
                raise AssertionError('Effects exceed one PAL frame or fail to return')
            self.memory.instruction = self.cpu.disassemble[self.memory[self.cpu.pc]][0]
            self.cpu.step()
        if self.cpu.x != (voice if expected_x is None else expected_x) or self.cpu.sp != 255:
            raise AssertionError('Effects must preserve X and the caller stack')
        for index, (before, after) in enumerate(zip(self.before, self.memory.data)):
            if before != after and index not in self.memory.allowed:
                raise AssertionError(f'Effects changed undeclared byte ${index:04x}')
        return (effects.read_voice(self.memory, self.symbols, voice), effects.read_filter(self.memory, self.symbols),
                [(row['address'], row['value']) for row in self.memory.writes])


class BillieJeanEffectsAssemblyTest(unittest.TestCase):
    def compare(self, entry, state=None, shared=None, voice=0, divider=1, instruments=None, bank=None):
        defaults, default_bank = example()
        instruments = defaults if instruments is None else instruments
        bank = default_bank if bank is None else bank
        state = sound.VoiceState(instrument_offset=8, base_note=24) if state is None else state
        shared = sound.FilterState(cutoff=32, routing=242, mode=48) if shared is None else shared
        instrument = instruments[state.instrument_offset]
        if entry == 'bj_note_setup':
            result = sound.note_setup(state, shared, instrument, bank, voice)
            expected = result.state, result.filter_state, result.writes
        elif entry == 'bj_body':
            result = sound.body_step(state, shared, instrument, bank, voice, divider)
            expected = result.state, result.filter_state, result.writes
        elif entry == 'bj_advance_age':
            expected = sound.advance_age(state), shared, []
        else:
            expected = state, shared, sound.global_output(shared)
        harness = Harness(instruments, bank)
        harness.prepare(state, shared, voice, divider)
        actual = harness.call(entry, voice)
        self.assertEqual(actual, expected)
        self.assertEqual(harness.memory.data[harness.symbols['bj_sound_failed']], 0)
        return harness

    def test_setup_paths_preserve_cache_motion_and_native_write_order(self):
        for voice in range(3):
            for gate in (0, 254, 1, 255):
                self.compare('bj_note_setup', sound.VoiceState(instrument_offset=8,
                    base_note=182, gate_mask=gate, frequency=0xffff, pulse=0x1234,
                    pulse_direction=17, age=128, wave_cursor=3, waveform=65), voice=voice)

    def test_pwm_masks_high_byte_carry_borrow_and_retains_crossing_word(self):
        for direction in (0, 1, 127, 255):
            for word in (0, 0x800, 0xeff, 0xcfff, 0xffff):
                self.compare('bj_body', sound.VoiceState(instrument_offset=8, pulse=word,
                    pulse_direction=direction, wave_cursor=3, base_note=24), voice=direction % 3)

    def test_paired_table_jump_relative_absolute_and_hold_paths(self):
        for cursor in range(4):
            for note in (24, 182, 255):
                self.compare('bj_body', sound.VoiceState(instrument_offset=8,
                    wave_cursor=cursor, base_note=note, age=1, gate_mask=255), voice=cursor % 3)

    def test_glide_branch_bypass_and_asymmetric_equal_target(self):
        instruments, bank = example()
        target = bank.frequencies[20]
        for note, target_note, word, step in ((24, 20, target + 100, 100),
                                            (19, 20, target - 100, 100),
                                            (19, 20, target - 99, 100),
                                            (24, 20, 0, 255), (19, 20, 65535, 255)):
            for voice in range(3):
                self.compare('bj_body', sound.VoiceState(instrument_offset=8, wave_cursor=3,
                    base_note=note, glide_target=target_note, glide_step=step,
                    frequency=word, age=1, gate_mask=255, remaining=0), voice=voice, bank=bank, instruments=instruments)

    def test_vibrato_delay_high_note_flag_phase_direction_and_word_wrap(self):
        for note, age in ((24, 0), (24, 12), (24, 13), (182, 1)):
            for phase in (0, 5, 6, 10, 255):
                self.compare('bj_body', sound.VoiceState(instrument_offset=8,
                    wave_cursor=3, base_note=note, age=age, frequency=65535,
                    vibrato_phase=phase), voice=phase % 3)

    def test_gate_hold_rest_and_shared_filter_wrap_are_independent(self):
        for voice in range(3):
            for remaining, hold, divider in ((0, 0, 1), (0, 32, 1), (0, 0, 2), (1, 0, 1)):
                self.compare('bj_body', sound.VoiceState(instrument_offset=8, base_note=24,
                    wave_cursor=3, remaining=remaining, hold=hold, gate_mask=255),
                    sound.FilterState(cutoff=0, routing=242, mode=48), voice, divider)

    def test_age_saturation_and_final_mode_volume_write_preserve_state(self):
        for age in (0, 127, 128, 255):
            for voice in range(3):
                self.compare('bj_advance_age', sound.VoiceState(age=age), voice=voice)
                self.compare('bj_global_output', voice=voice)

    def test_seeded_admitted_arithmetic_preserves_neighbor_and_table_memory(self):
        randomizer = random.Random(8388001)
        for case in range(18):
            state = sound.VoiceState(**{item.name: randomizer.randrange(65536 if item.name in sound.WORD_FIELDS else 256)
                for item in fields(sound.VoiceState)})
            state.instrument_offset, state.wave_cursor = 8, randomizer.randrange(4)
            self.compare('bj_body', state, sound.FilterState(cutoff=randomizer.randrange(256),
                mode=randomizer.randrange(256), routing=randomizer.randrange(256)), case % 3,
                randomizer.randrange(3))

    def test_invalid_jump_returns_bounded_failure_without_sid_writes(self):
        instruments, bank = example()
        bank.pitches[9] = 127
        with self.assertRaises(ValueError):
            sound.body_step(sound.VoiceState(instrument_offset=8, wave_cursor=2), sound.FilterState(), instruments[8], bank, 0, 1)
        harness = Harness(instruments, bank)
        harness.prepare(sound.VoiceState(instrument_offset=8, wave_cursor=2), sound.FilterState(), 0, 1)
        actual = harness.call('bj_body', 0)
        self.assertEqual(actual[2], [])
        self.assertEqual(harness.memory.data[harness.symbols['bj_sound_failed']], 1)

    def test_descending_mixed_stages_age_and_final_global_write(self):
        instruments, bank = example()
        target = bank.frequencies[20]
        voices = [sound.VoiceState(instrument_offset=8, base_note=24, wave_cursor=3,
                    frequency=target + 100, glide_target=20, glide_step=100,
                    age=1, waveform=65, gate_mask=255),
                  sound.VoiceState(instrument_offset=8, base_note=24, wave_cursor=3,
                    age=13, waveform=65, frequency=0x10ff, gate_mask=255),
                  sound.VoiceState(instrument_offset=8, base_note=24, gate_mask=254)]
        shared = sound.FilterState(cutoff=0, routing=242, mode=48)
        expected_states, expected_writes, expected_filter = list(voices), [], shared
        for voice in (2, 1, 0):
            result = (sound.note_setup(voices[voice], expected_filter, instruments[8], bank, voice) if voice == 2 else
                      sound.body_step(voices[voice], expected_filter, instruments[8], bank, voice, 1))
            expected_states[voice], expected_filter = sound.advance_age(result.state), result.filter_state
            expected_writes.extend(result.writes)
        expected_writes.extend(sound.global_output(expected_filter))
        harness = Harness(instruments, bank)
        harness.prepare(voices[2], shared, 2, 1)
        for label, values in effects.sound_state_values(voices, shared).items():
            harness.memory.data[harness.symbols[label]:harness.symbols[label] + len(values)] = values
        harness.before = list(harness.memory.data)
        harness.memory.allowed.update(harness.symbols[label] + voice
            for labels in effects.VOICE_FIELD_LABELS.values() for label in labels for voice in range(3))
        harness.memory.allowed.update(range(0xd400, 0xd419))
        actual = harness.call('bj_test_frame', 2, expected_x=0)
        self.assertEqual(actual[2], expected_writes)
        self.assertEqual([effects.read_voice(harness.memory, harness.symbols, voice) for voice in range(3)], expected_states)
        self.assertEqual(actual[1], expected_filter)


if __name__ == '__main__':
    unittest.main()
