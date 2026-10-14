"""Compare source-free assembled sound against the frozen numeric helpers."""

from copy import deepcopy
from dataclasses import asdict, fields
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'scripts/studies/take-on-me'))
import programs
import effects_asm as layout
from psid_audit import AuditMemory
from sid_assembler import assemble
from verify_player import cpu_type


def description():
    bank = programs.Programs(
        frequencies={index: (index * 257 + 0x10ff) & 65535 for index in range(256)},
        arpeggios={0: [8, 0, 255, 0]}, waveforms={1: [129, 65, 16, 254]},
        pitches={1: [192, 14, 12, 254]},
        pulses={1: programs.SweepProgram(0, 0x301, 0x200, 1, 0x201, 0xe00, 0)},
        vibratos={1: programs.VibratoProgram(9, 0, 3, 2)},
        filters={1: programs.SweepProgram(1, 0x101, 0x100, 255, 0x101, 0x8000, 0)},
        releases={1: [2, 1]})
    instrument = programs.Instrument(pulse=0x9c0, onset_control=9, body_control=65,
        attack_decay=2, sustain_release=92, arpeggio_enabled=1, table_program=1,
        pulse_program=1, vibrato_program=1, filter_program=1, filter_word=0xc000,
        gate_half=1, release_program=1)
    return dict(instruments={0: asdict(programs.Instrument()), 1: asdict(instrument)}, programs=asdict(bank))


class GuardedMemory(AuditMemory):
    allowed = None

    def __setitem__(self, address, value):
        if self.allowed is not None and address not in self.allowed:
            raise AssertionError(f'Effects changed undeclared memory at ${address:04x}')
        super().__setitem__(address, value)


class Harness:
    def __init__(self, sound):
        tables, references = layout.sound_tables(sound)
        states = layout.sound_state_values([programs.VoiceState() for _ in range(3)], programs.FilterState())
        source = (ROOT / 'songs/players/take-on-me-effects.asm').read_text()
        source += '\ntm_test_all_outputs:\n  LDX #$02\ntm_test_next_output:\n  JSR tm_voice_output\n  DEX\n  BPL tm_test_next_output\n  JSR tm_filter_output\n  RTS\n'
        source += '\n' + layout.declarations(states) + layout.declarations({label: [0] * size for label, size in layout.SCRATCH_STORAGE}) + tables
        constants = {name: 0 for name in references}
        _, preliminary, _ = assemble(source, constants, load=0x2000)
        constants.update({name: (preliminary[label] >> shift) & 255 for name, (label, shift) in references.items()})
        payload, self.symbols, _ = assemble(source, constants, load=0x2000)
        self.memory = GuardedMemory()
        self.memory.data[0x2000:0x2000 + len(payload)] = payload
        self.cpu = cpu_type()(memory=self.memory)
        self.maximum_cycles = 0

    def prepare(self, state, shared, voice, instrument):
        voices = [programs.VoiceState(frequency=0xa55a, pulse=0x5aa5, control=0xa5) for _ in range(3)]
        voices[voice] = state
        values = layout.sound_state_values(voices, shared)
        values['tm_instrument'] = [0, 0, 0]
        values['tm_instrument'][voice] = instrument
        for label, items in values.items():
            self.memory.data[self.symbols[label]:self.symbols[label] + len(items)] = items
        self.memory.writes.clear()
        self.memory.allowed = {self.symbols[label] + voice for labels in layout.VOICE_FIELD_LABELS.values() for label in labels}
        self.memory.allowed.update(self.symbols[label] for labels in layout.FILTER_FIELD_LABELS.values() for label in labels)
        self.memory.allowed.update(self.symbols[label] + index for label, size in layout.SCRATCH_STORAGE for index in range(size))
        self.memory.allowed.update(range(0xe0, 0xf0))
        self.memory.allowed.update(range(0x100, 0x200))
        self.memory.allowed.update(range(0xd400 + 7 * voice, 0xd407 + 7 * voice))
        self.memory.allowed.update((0xd415, 0xd416))
        self.before = list(self.memory.data)

    def call(self, entry, voice, decimal=False, expected_x=None):
        self.cpu.a, self.cpu.x, self.cpu.y, self.cpu.sp = 0xa5, voice, 0x5a, 255
        self.cpu.p = 0x28 if decimal else 0x20
        self.cpu.stPushWord(0x01ff)
        self.cpu.pc = self.symbols[entry]
        start = self.cpu.processorCycles
        while self.cpu.pc != 0x0200:
            if self.cpu.processorCycles - start >= 19656:
                raise AssertionError('Effects exceed one PAL frame or fail to return')
            self.memory.instruction = self.cpu.disassemble[self.memory[self.cpu.pc]][0]
            self.cpu.step()
        self.maximum_cycles = max(self.maximum_cycles, self.cpu.processorCycles - start)
        if self.cpu.x != (voice if expected_x is None else expected_x) or self.cpu.sp != 255:
            raise AssertionError('Effects must preserve voice index and caller stack')
        for index, (before, after) in enumerate(zip(self.before, self.memory.data)):
            if before != after and index not in self.memory.allowed:
                raise AssertionError(f'Effects changed undeclared byte ${index:04x}')
        return (layout.read_voice(self.memory, self.symbols, voice), layout.read_filter(self.memory, self.symbols),
                [(row['address'], row['value']) for row in self.memory.writes])


class TakeOnMeEffectsAssemblyTest(unittest.TestCase):
    def compare(self, entry, state=None, shared=None, voice=0, sound=None, instrument_id=1):
        sound = description() if sound is None else sound
        state = programs.VoiceState() if state is None else state
        shared = programs.FilterState() if shared is None else shared
        instruments, bank = layout.numeric_sound(sound)
        if entry == 'tm_note_setup':
            result = programs.note_setup(state, shared, instruments[instrument_id], voice, bank.frequencies)
            expected = result.state, result.filter_state, result.writes
        elif entry == 'tm_body':
            result = programs.body_step(state, shared, instruments[instrument_id], bank, voice)
            expected = result.state, result.filter_state, result.writes
        elif entry == 'tm_voice_output':
            expected = state, shared, programs.voice_output(state, voice)
        else:
            expected = state, shared, programs.filter_output(shared)
        harness = Harness(sound)
        harness.prepare(state, shared, voice, instrument_id)
        actual = harness.call(entry, voice, decimal=True)
        self.assertEqual(actual, expected)
        self.assertEqual(harness.memory.data[harness.symbols['tm_sound_failed']], 0)
        return harness

    def test_setup_and_output_preserve_owner_and_exact_store_order(self):
        for voice in range(3):
            state = programs.VoiceState(base_note=20, frequency=0x1234, pulse=0xabc, control=65)
            shared = programs.FilterState(word=0x2345, initial=255, direction=255)
            self.compare('tm_note_setup', state, shared, voice)
            self.compare('tm_voice_output', state, shared, voice)
            self.compare('tm_filter_output', state, shared, voice)

    def test_table_loops_terminal_holds_and_body_stage_priority(self):
        for cursor in range(4):
            self.compare('tm_body', programs.VoiceState(frequency=0xffff, pulse=0x210,
                base_note=24, arpeggio_cursor=cursor, waveform_cursor=cursor,
                pitch_cursor=cursor, remaining=1, duration=8), voice=cursor % 3)

    def test_word_glide_direction_crossing_and_vibrato_exclusion(self):
        for note, target, word, step in ((20, 21, 0x25fe, 0x101), (21, 20, 0x2600, 0x101),
                                       (20, 20, 0, 1), (255, 0, 0, 65535)):
            for voice in range(3):
                state = programs.VoiceState(frequency=word, base_note=note, glide_target=target,
                    glide_step=step, glide_active=1, vibrato_delay=7, onset_initial=255,
                    pulse_initial=255, pulse_direction=255, waveform_cursor=3, pitch_cursor=3)
                sound = description()
                sound['instruments'][1]['arpeggio_enabled'] = 0
                self.compare('tm_body', state, voice=voice, sound=sound)

    def test_sweep_word_wrap_phase_crossings_and_disabled_sentinels(self):
        for direction in (0, 1, 127, 128, 255):
            for word in (0, 0x200, 0xe00, 0xffff):
                state = programs.VoiceState(pulse=word, pulse_initial=255, pulse_direction=direction,
                    base_note=10, waveform_cursor=3, pitch_cursor=3)
                shared = programs.FilterState(word=word, initial=255, direction=direction)
                self.compare('tm_body', state, shared, voice=0)

    def test_vibrato_initial_rounding_delay_and_stationary_reversals(self):
        sound = description()
        for key in ('arpeggio_enabled', 'table_program', 'pulse_program', 'filter_program', 'gate_half', 'release_program'):
            sound['instruments'][1][key] = 0
        for duration, shift in ((0, 0), (3, 2), (255, 16)):
            sound['programs']['vibratos'][1].update(duration=duration, shift=shift)
            for initial, delay, remaining in ((0, 0, 0), (255, 1, 1), (255, 0, 0), (255, 0, 2)):
                for voice in range(3):
                    state = programs.VoiceState(frequency=0x10ff, base_note=255,
                        vibrato_initial=initial, vibrato_delay=delay, vibrato_remaining=remaining,
                        vibrato_step=65535, vibrato_direction=voice, onset_initial=255)
                    self.compare('tm_body', state, voice=voice, sound=sound)

    def test_seeded_admitted_state_checks_memory_and_all_word_bytes(self):
        randomizer = random.Random(8388001)
        for case in range(24):
            state = programs.VoiceState(**{item.name: randomizer.randrange(65536 if item.name in programs.VOICE_WORDS else 256)
                for item in fields(programs.VoiceState)})
            state.arpeggio = 0
            state.arpeggio_cursor = randomizer.randrange(4)
            state.waveform_cursor = randomizer.randrange(4)
            state.pitch_cursor = randomizer.randrange(4)
            shared = programs.FilterState(word=randomizer.randrange(65536), initial=randomizer.randrange(256),
                direction=randomizer.randrange(256))
            self.compare('tm_body', state, shared, case % 3)

    def test_data_lowering_is_numeric_source_free_and_nonmutating(self):
        sound = description()
        original = deepcopy(sound)
        tables, references = layout.sound_tables(sound)
        self.assertEqual(sound, original)
        self.assertIn('tm_pulse_ptr_lo:', tables)
        self.assertTrue(references)
        with self.assertRaises(ValueError):
            layout.sound_state_values([programs.VoiceState()], programs.FilterState())

    def test_descending_voice_output_places_shared_filter_last(self):
        voices = [programs.VoiceState(frequency=0x1234 + voice, pulse=0xabc + voice, control=65 + voice)
            for voice in range(3)]
        shared = programs.FilterState(word=0xc000)
        harness = Harness(description())
        harness.prepare(voices[2], shared, 2, 0)
        for label, items in layout.sound_state_values(voices, shared).items():
            harness.memory.data[harness.symbols[label]:harness.symbols[label] + len(items)] = items
        harness.before = list(harness.memory.data)
        harness.memory.allowed.update(range(0xd400, 0xd417))
        actual = harness.call('tm_test_all_outputs', 2, expected_x=255)
        expected = [write for voice in (2, 1, 0) for write in programs.voice_output(voices[voice], voice)]
        self.assertEqual(actual[2], expected + programs.filter_output(shared))

    def test_nonterminating_table_sets_failure_without_sid_stores(self):
        sound = description()
        sound['programs']['arpeggios'][0] = [255, 0]
        instrument_bank, bank = layout.numeric_sound(sound)
        with self.assertRaisesRegex(ValueError, 'does not reach a value or hold'):
            programs.body_step(programs.VoiceState(), programs.FilterState(), instrument_bank[1], bank, 0)
        harness = Harness(sound)
        harness.prepare(programs.VoiceState(), programs.FilterState(), 0, 1)
        actual = harness.call('tm_body', 0)
        self.assertEqual(actual[2], [])
        self.assertEqual(harness.memory.data[harness.symbols['tm_sound_failed']], 1)

    def test_release_table_rejects_missing_threshold(self):
        sound = description()
        sound['programs']['releases'][1] = [2]
        with self.assertRaisesRegex(ValueError, 'Release program'):
            layout.sound_tables(sound)


if __name__ == '__main__':
    unittest.main()
