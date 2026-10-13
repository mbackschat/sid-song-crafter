"""Check independently assembled Ghouls sound against executed input contexts."""

from dataclasses import asdict, replace
import gzip
import hashlib
import json
from pathlib import Path
import random
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import ghouls_programs as programs
from ghouls_layout import (FILTER_FIELD_LABELS, SOUND_SCRATCH_STORAGE, SOUND_STATE_STORAGE, SOUND_STORAGE,
                           SOUND_TABLE_STORAGE,
                           VOICE_FIELD_LABELS, read_filter_state, read_voice_state,
                           sound_declarations, store_filter_state, store_voice_state)
from psid_audit import AuditMemory
from sid_assembler import assemble
from verify_player import cpu_type


SOURCE = ROOT / 'songs/players/ghouls-sound.asm'
EVIDENCE = ROOT / 'evidence/ghouls-components/sound'
STAGES = {'onset': programs.onset_step, 'frequency': programs.frequency_step,
          'note': programs.note_step, 'pulse': programs.pulse_step}


class GuardedMemory(AuditMemory):
    def __init__(self):
        super().__init__()
        self.allowed = None

    def __setitem__(self, address, value):
        if self.allowed is not None and address not in self.allowed:
            raise AssertionError(f'Sound writes outside declared mutable state at ${address:04x}')
        super().__setitem__(address, value)


class SoundHarness:
    def __init__(self):
        payload, self.symbols, _ = assemble(SOURCE.read_text() + '\n' + sound_declarations(), load=0x2000)
        self.memory = GuardedMemory()
        self.memory.data[0x2000:0x2000 + len(payload)] = payload
        self.cpu = cpu_type()(memory=self.memory)
        self.max_cycles = 0

    def set_lookup(self, lookup):
        self.memory.allowed = None
        for index in range(256):
            word = lookup.get(index, 0) if isinstance(lookup, dict) else lookup[index]
            self.memory.data[self.symbols['gh_frequency_lo'] + index] = word & 255
            self.memory.data[self.symbols['gh_frequency_hi'] + index] = word >> 8

    def prepare(self, state, shared, voice):
        self.memory.allowed = None
        for other in range(3):
            store_voice_state(self.memory, self.symbols, other, programs.VoiceState(
                waveform=0xa5, pulse_word=0x5aa5, current_frequency=0xa55a, onset_remaining=7))
        store_voice_state(self.memory, self.symbols, voice, state)
        store_filter_state(self.memory, self.symbols, shared)
        self.memory.writes.clear()
        self.memory.allowed = {self.symbols[label] + voice for labels in VOICE_FIELD_LABELS.values() for label in labels}
        self.memory.allowed.update(self.symbols[label] for labels in FILTER_FIELD_LABELS.values() for label in labels)
        self.memory.allowed.update(self.symbols[label] for label, _ in SOUND_SCRATCH_STORAGE)
        self.memory.allowed.update(range(0x100, 0x200))
        self.memory.allowed.update(range(0xd400 + 7 * voice, 0xd407 + 7 * voice))
        self.memory.allowed.update((0xd415, 0xd416))
        self.before_memory = list(self.memory.data)

    def call(self, stage, voice, raw_note=0, decimal=False):
        self.cpu.a, self.cpu.x, self.cpu.y = raw_note, voice, 0x5a
        self.cpu.p, self.cpu.sp = (0x28 if decimal else 0x20), 255
        self.cpu.stPushWord(0x01ff)
        entry = {'advance': 'gh_advance_sound', 'setup': 'gh_note_setup', 'filter': 'gh_advance_filter'}.get(stage, f'gh_step_{stage}')
        self.cpu.pc = self.symbols[entry]
        start = self.cpu.processorCycles
        while self.cpu.pc != 0x0200:
            if self.cpu.processorCycles - start >= 50000:
                raise AssertionError('Sound did not return within its bounded invocation')
            self.memory.instruction = self.cpu.disassemble[self.memory[self.cpu.pc]][0]
            self.cpu.step()
        self.max_cycles = max(self.max_cycles, self.cpu.processorCycles - start)
        if self.cpu.x != voice or self.cpu.sp != 255:
            raise AssertionError('Sound must preserve the selected voice and caller stack')
        for index, (before, after) in enumerate(zip(self.before_memory, self.memory.data)):
            if before != after and index not in self.memory.allowed:
                raise AssertionError(f'Sound changed undeclared memory at ${index:04x}')
        writes = [(row['address'], row['value']) for row in self.memory.writes]
        return read_voice_state(self.memory, self.symbols, voice), read_filter_state(self.memory, self.symbols), writes


def setup_note(row):
    before, after = row['before'], row['after']
    index = after['target_note_index'] if before['glide_rate'] else after['note_index']
    return index if before['pitch_index_mode'] == 255 else (index - before['transpose']) & 255


class GhoulsSoundAssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = SoundHarness()
        receipt = json.loads((EVIDENCE / 'receipt.json').read_text())
        encoded = (EVIDENCE / 'proofs.json.gz').read_bytes()
        if hashlib.sha256(encoded).hexdigest() != receipt['outputHashes']['proofs.json.gz']['sha256']:
            raise AssertionError('Retained original execution contexts changed')
        cls.proof = json.loads(gzip.decompress(encoded))
        cls.controls = json.loads((EVIDENCE / 'controls.json').read_text())

    def compare(self, stage, state=None, shared=None, voice=0, lookup=None, raw_note=21, decimal=False):
        state = programs.VoiceState() if state is None else state
        shared = programs.FilterState() if shared is None else shared
        lookup = {index: (index * 317 + 0x80ff) & 65535 for index in range(256)} if lookup is None else lookup
        if stage == 'setup':
            expected_state, expected_filter, expected_writes = programs.note_setup(state, shared, voice, raw_note, lookup)
        elif stage == 'filter':
            expected_filter, expected_writes, _ = programs.filter_step(shared)
            expected_state = state
        elif stage == 'advance':
            expected_state, expected_filter, expected_writes = state, shared, []
            for operation in STAGES.values():
                result = operation(expected_state, voice, lookup) if operation is programs.note_step else operation(expected_state, voice)
                expected_state = result.state
                expected_writes.extend(result.writes)
        else:
            result = STAGES[stage](state, voice, lookup) if stage == 'note' else STAGES[stage](state, voice)
            expected_state, expected_filter, expected_writes = result.state, shared, result.writes
        self.harness.set_lookup(lookup)
        self.harness.prepare(state, shared, voice)
        actual = self.harness.call(stage, voice, raw_note, decimal)
        self.assertEqual((expected_state, expected_filter, expected_writes), actual)
        if stage == 'filter':
            self.assertEqual(self.harness.memory[self.harness.symbols['gh_filter_failed']], 0)
            self.assertFalse(self.harness.cpu.p & self.harness.cpu.CARRY)
        return actual

    def test_retained_representatives_cover_each_executed_stage_path_and_voice(self):
        representatives = {}
        for row in self.proof['comparisons']:
            representatives.setdefault((row['stage'], row['path'], row['voice']), row)
        self.assertEqual(len(representatives), 47)
        for key, row in representatives.items():
            with self.subTest(stage=key[0], path=key[1], voice=key[2], call=row['call']):
                stage = row['stage']
                voice = 0 if stage == 'filter' else row['voice']
                state = programs.VoiceState(**row['before']) if stage != 'filter' else programs.VoiceState()
                shared = programs.FilterState(**row['before']) if stage == 'filter' else programs.FilterState()
                actual = self.compare(stage, state, shared, voice, self.proof['lookup'], setup_note(row) if stage == 'setup' else 21)
                self.assertEqual(asdict(actual[1] if stage == 'filter' else actual[0]), row['after'])
                self.assertEqual(actual[2], [tuple(write) for write in row['writes']])

    def test_retained_isolated_original_execution_controls_match(self):
        self.assertGreaterEqual(len(self.controls), 18)
        for row in self.controls:
            with self.subTest(purpose=row['purpose']):
                stage = row['stage']
                voice = 0 if stage == 'filter' else row['voice']
                state = programs.VoiceState(**row['before']) if stage != 'filter' else programs.VoiceState()
                shared = programs.FilterState(**row['before']) if stage == 'filter' else programs.FilterState()
                actual = self.compare(stage, state, shared, voice, self.proof['lookup'], setup_note(row) if stage == 'setup' else 21)
                self.assertEqual(asdict(actual[1] if stage == 'filter' else actual[0]), row['after'])
                self.assertEqual(actual[2], [tuple(write) for write in row['writes']])

    def test_edited_onset_and_frequency_boundaries_preserve_word_wrap_and_countdown(self):
        for voice in range(3):
            for remaining, gate in ((0, 0), (1, 0), (1, 255), (2, 1), (255, 1)):
                self.compare('onset', programs.VoiceState(onset_remaining=remaining, gate_enabled=gate,
                                                        waveform=0xfe, current_frequency=0xffff), voice=voice, decimal=True)
            for word, step, direction in ((0, 1, 0), (0xffff, 1, 255), (0xfffe, 2, 1), (0x10ff, 255, 255), (0, 0, 0)):
                for delay, half, reload in ((0, 0, 0), (1, 1, 128), (2, 1, 255), (255, 255, 1)):
                    self.compare('frequency', programs.VoiceState(current_frequency=word, frequency_step=step,
                                 frequency_direction=direction, frequency_delay_reload=1,
                                 frequency_delay_remaining=delay, frequency_half_remaining=half,
                                 frequency_half_reload=reload), voice=voice, decimal=True)

    def test_edited_note_motion_wraps_and_glide_uses_unsigned_candidate_clamps(self):
        for voice in range(3):
            for index, step, direction in ((255, 1, 0), (0, 255, 255), (0, 1, 255), (128, 0, 0)):
                self.compare('note', programs.VoiceState(note_index=index, note_step=step, note_remaining=1,
                             note_direction=direction, note_positive_duration=255, note_negative_duration=0,
                             glide_rate=99, target_note_index=80), voice=voice, decimal=True)
            for index, target, rate, remaining in ((250, 251, 10, 0), (3, 2, 10, 0), (30, 20, 255, 2),
                                                   (255, 255, 1, 255), (20, 30, 0, 0), (20, 30, 10, 2)):
                self.compare('note', programs.VoiceState(note_index=index, target_note_index=target,
                             glide_rate=rate, note_remaining=remaining), voice=voice)

    def test_edited_pulse_boundaries_preserve_full_words_and_disabled_sentinel(self):
        for voice in range(3):
            for word, step, direction in ((100, 1, 0), (99, 0, 0), (0, 255, 0), (0x8001, 1, 0),
                                          (3994, 1, 255), (0xffff, 1, 255), (0, 1, 1), (3996, 0, 255)):
                self.compare('pulse', programs.VoiceState(pulse_word=word, pulse_step=step,
                                                         pulse_direction=direction), voice=voice, decimal=True)

    def test_edited_note_setup_resets_owner_state_and_preserves_disabled_motion(self):
        for voice in range(3):
            for mode, glide, onset, gate, default, reload in ((255, 0, 2, 1, 0x8000, 1), (1, 7, 0, 1, 0, 0),
                                                            (0, 0, 255, 0, 0xffff, 255), (254, 1, 1, 255, 1, 0)):
                for owner in range(3):
                    state = programs.VoiceState(pitch_index_mode=mode, glide_rate=glide, transpose=250,
                            note_index=255, onset_delay=onset, gate_enabled=gate, waveform=0xfe,
                            onset_control=0x88, onset_frequency=0xff01, pulse_default=default,
                            pulse_restart=255, pulse_direction=1, pulse_word=123,
                            frequency_delay_reload=reload, frequency_delay_remaining=9,
                            frequency_direction_default=0xa5, frequency_direction=0x5a,
                            frequency_half_reload=128, frequency_half_remaining=99,
                            note_positive_duration=255, rest_reload=255, onset_remaining=9)
                    shared = programs.FilterState(owner=owner, word=0x1234, default=default,
                                                   direction=0x5a, reset_direction=0xa5)
                    self.compare('setup', state, shared, voice, raw_note=127, decimal=True)

    def test_edited_filter_word_encoding_borrow_and_bytewise_thresholds(self):
        cases = ((0x8001, 1, 0, 0, 0xffff), (0x8100, 1, 0, 0, 0xffff),
                 (0x127f, 1, 0, 0x1200, 0xffff), (0x1100, 1, 0, 0x1200, 0xffff),
                 (0x0100, 1, 0, 0x0100, 0x0300), (0x02fe, 1, 1, 0, 0x01ff),
                 (0x02ff, 1, 255, 0, 0x0300), (0xffff, 1, 255, 0, 0xffff),
                 (0xfedc, 0, 0, 0, 0xffff), (0x08ab, 0, 1, 0, 0xffff))
        for word, step, direction, lower, upper in cases:
            self.compare('filter', shared=programs.FilterState(word=word, step=step, direction=direction,
                                                              lower=lower, upper=upper), voice=2, decimal=True)

    def test_nonterminating_filter_returns_a_bounded_failure_without_sid_output(self):
        state = programs.FilterState(word=1, step=1, lower=2, upper=1)
        with self.assertRaisesRegex(ValueError, 'output boundary'):
            programs.filter_step(state)
        self.harness.prepare(programs.VoiceState(), state, 1)
        _, _, writes = self.harness.call('filter', 1, decimal=True)
        self.assertEqual(writes, [])
        self.assertEqual(self.harness.memory[self.harness.symbols['gh_filter_failed']], 1)
        self.assertTrue(self.harness.cpu.p & self.harness.cpu.CARRY)
        self.compare('filter', shared=replace(state, lower=0, upper=65535), voice=1)

    def test_advance_preserves_onset_frequency_note_pulse_store_order(self):
        state = programs.VoiceState(onset_remaining=1, gate_enabled=1, waveform=0x40,
                current_frequency=0x10ff, frequency_delay_reload=1, frequency_step=1,
                frequency_direction=255, frequency_half_remaining=1, frequency_half_reload=128,
                note_index=255, note_step=1, note_remaining=1, note_positive_duration=2,
                pulse_word=3994, pulse_step=1, pulse_direction=255)
        for voice in range(3):
            _, _, writes = self.compare('advance', state, voice=voice, decimal=True)
            self.assertEqual([address - voice * 7 for address, _ in writes],
                             [0xd400, 0xd401, 0xd404, 0xd400, 0xd401, 0xd400, 0xd401, 0xd402, 0xd403])

    def test_seeded_edited_native_state_covers_full_byte_and_word_ranges(self):
        randomizer = random.Random(8388001)
        for case in range(120):
            values = {field: randomizer.randrange(65536 if field in programs.VOICE_WORD_FIELDS else 256)
                      for field in VOICE_FIELD_LABELS}
            values.update(pulse_direction=randomizer.choice((0, 1, 255)), pulse_restart=randomizer.choice((0, 1, 255)))
            state = programs.VoiceState(**values)
            self.compare('advance', state, voice=case % 3, decimal=bool(case % 2))
            self.compare('setup', state, programs.FilterState(word=randomizer.randrange(65536),
                         default=randomizer.randrange(65536), owner=case % 3,
                         direction=randomizer.randrange(256), reset_direction=randomizer.randrange(256)),
                         voice=case % 3, raw_note=randomizer.randrange(1, 128), decimal=bool(case % 2))

    def test_layout_round_trips_every_field_and_keeps_tables_out_of_cold_state(self):
        labels = [label for label, _ in SOUND_STORAGE]
        self.assertEqual(len(labels), len(set(labels)))
        states = [programs.VoiceState(**{field: (0xffff if field in programs.VOICE_WORD_FIELDS else
                      255 if field not in ('pulse_direction', 'pulse_restart') else 1)
                      for field in VOICE_FIELD_LABELS}) for _ in range(3)]
        shared = programs.FilterState(word=65535, default=32768, step=255, owner=2, direction=255,
                                      reset_direction=128, lower=256, upper=65535)
        declarations, symbols, _ = assemble('RTS\n' + sound_declarations(states, shared, {255: 65535}, [0, 1, 255], [0, 32768, 65535]))
        memory = [0] * 65536
        memory[0x1000:0x1000 + len(declarations)] = declarations
        for voice in range(3):
            self.assertEqual(states[voice], read_voice_state(memory, symbols, voice))
        self.assertEqual(shared, read_filter_state(memory, symbols))
        self.assertEqual(memory[symbols['gh_frequency_hi'] + 255], 255)
        cold_end = symbols[SOUND_STATE_STORAGE[-1][0]] + SOUND_STATE_STORAGE[-1][1]
        self.assertEqual(cold_end, symbols[SOUND_TABLE_STORAGE[0][0]])
        self.assertTrue(all(symbols[label] >= cold_end for label, _ in SOUND_TABLE_STORAGE + SOUND_SCRATCH_STORAGE))
        self.assertEqual(memory[symbols['gh_filter_restart_phase']:symbols['gh_filter_restart_phase'] + 3], [0, 1, 255])
        self.assertEqual(memory[symbols['gh_pulse_fallback_hi']:symbols['gh_pulse_fallback_hi'] + 3], [0, 128, 255])


if __name__ == '__main__':
    unittest.main()
