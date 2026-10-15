"""Guard new serialized speech data, native timer ownership and music handoff."""

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ghostbusters_title_test_backend',
    ROOT / 'scripts/studies/ghostbusters/compile-title.py')
title = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = title
spec.loader.exec_module(title)


def fixture():
    player = title.compiler.player
    scored = dict(schemaVersion=1, orders=[dict(patterns=[0])] * 3,
        patterns={'0': dict(rows=[dict(header=0x87, note=24,
            parameter=dict(volume=15, instrument=0)), dict(header=0x41)])},
        initialState=dict(phase=0, voices=[dict(orderCursor=0, patternCursor=0,
            remaining=0, note=0, header=0, instrument=0) for _ in range(3)]))
    sound = dict(schema='ghostbusters-sound-v1', target=deepcopy(player.TARGET),
        patches={'0': dict(pulse_low=0x23, pulse_high=8, control=65,
            attack_decay=0x2f, sustain_release=0xff, vibrato_shift=2)},
        frequencies={'0': 0x0100, '1': 0x0140, '24': 0x1234, '25': 0x12b4},
        volumePolicy=deepcopy(player.VOLUME_POLICY))
    composition = player.from_components(scored, sound, calls=48)
    alignment = dict(clockHz=title.NTSC_CLOCK,
        commands=[dict(command=1, firstNmi=2000), dict(command=3, firstNmi=4000)],
        internalMusicInit=6000, firstMusicBody=8500)
    commands = [bytes([7, 255, 12, 4, 7]), bytes([7, 13, 255, 3, 7])]
    return composition, alignment, commands


def native():
    composition, alignment, commands = fixture()
    with patch.object(title, 'decode_commands', return_value=(commands, [])):
        return title.build(composition, bytes(65536), alignment, seconds=5)


class GhostbustersTitleTest(unittest.TestCase):
    def test_decoder_no_write_ticks_are_retained_in_stream_and_oracle_hash(self):
        class Synth:
            def __init__(self):
                self.finished = True
                self.handler = title.speech.Handler.GAP_START

            def start(self, command):
                self.finished, self.cursor = False, 0
                self.handler = title.speech.Handler.GAP_START

            def tick(self):
                values = [7, None, 7]
                value = values[self.cursor]
                self.cursor += 1
                self.handler = title.speech.Handler.STOP if self.cursor == 2 else title.speech.Handler.GAP_WAIT
                self.finished = self.cursor == 3
                return value

        with patch.object(title.speech, 'SpeechSynth', return_value=Synth()):
            streams, aggregates = title.decode_commands(bytes(65536))
        self.assertEqual(streams, [bytes([7, 255, 7])] * 2)
        self.assertEqual([row['ticks'] for row in aggregates], [3, 3])
        self.assertEqual([row['volumeStores'] for row in aggregates], [2, 2])
        expected = title.hashlib.sha256()
        for command in (1, 3):
            for index, handler, stores in ((0, 0xf0c3, [[0xd418, 7]]), (1, 0xf0d9, []), (2, 0xf0e1, [[0xd418, 7]])):
                expected.update(title.json.dumps([command, index, handler, stores], separators=(',', ':')).encode())
        self.assertEqual(aggregates[-1]['cumulativeOracleSequenceSha256'], expected.hexdigest())

    def test_packing_preserves_gaps_quantizes_starts_and_emits_unique_markers(self):
        _, alignment, commands = fixture()
        stream, placements = title.pack_timeline(commands, alignment, 400)
        for values, placement in zip(commands, placements):
            self.assertEqual(stream[placement['tick']:placement['tick'] + len(values)], values)
        self.assertEqual(stream.count(title.INIT_MARKER), 1)
        self.assertEqual(stream[-1], title.MUSIC_MARKER)
        self.assertTrue(all(abs(row['quantizationCycles']) <= 51 for row in placements))
        self.assertNotEqual(stream.count(255), 0)

    def test_overlapping_commands_and_invalid_volume_tokens_are_rejected(self):
        _, alignment, commands = fixture()
        commands[0] = bytes([7] * 100)
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            title.pack_timeline(commands, alignment, 400)
        _, alignment, commands = fixture()
        commands[0] = bytes([7, 128, 7])
        with self.assertRaisesRegex(ValueError, 'sample token'):
            title.pack_timeline(commands, alignment, 400)

    def test_native_ordered_stores_named_state_and_nonoverlapping_timers(self):
        checked = title.verify_native(native(), 16)
        self.assertTrue(checked['allOrderedStoresMatch'])
        self.assertTrue(checked['noSpeechNmiDuringMusic'])
        self.assertEqual(checked['namedMusicStates'], 17)
        self.assertLess(checked['maximumNmiCyclesIncludingEntry'], 102)
        self.assertEqual(checked['timerSampleCycles'], 102)
        self.assertEqual(checked['timerMusicCycles'], 17095)

    def test_idle_fast_forward_preserves_timed_stores_and_handoff_with_page_carry(self):
        composition, alignment, commands = fixture()
        alignment.update(internalMusicInit=32000, firstMusicBody=35000)
        with patch.object(title, 'decode_commands', return_value=(commands, [])):
            built = title.build(composition, bytes(65536), alignment, seconds=5)
        self.assertGreater(len(built['stream']), 256)
        skipped = title.verify_native(built, 16)
        stepped = title.verify_native(built, 16, fast_forward=False)
        self.assertGreater(skipped['fastForwardedIdleIterations'], 0)
        self.assertEqual(stepped['fastForwardedIdleIterations'], 0)
        for field in ('timedStoreSequenceSha256', 'nativeCpuCycles', 'musicEntryFromInit', 'musicIntervals',
                      'maximumNmiCyclesIncludingEntry', 'checkedStores', 'generatedSpeechTicks'):
            self.assertEqual(skipped[field], stepped[field], field)

    def test_full_native_range_is_admitted_and_overrun_rejected(self):
        built = native()
        self.assertGreater(built['info']['musicCalls'], 128)
        checked = title.verify_native(built, built['info']['musicCalls'])
        self.assertEqual(checked['checkedMusicCalls'], built['info']['musicCalls'])
        for calls in (True, 0, built['info']['musicCalls'] + 1):
            with self.subTest(calls=calls), self.assertRaisesRegex(ValueError, 'declared music range'):
                title.verify_native(built, calls)

    def test_sys2061_executes_new_entry_and_decimal_mode_is_cleared(self):
        built = native()
        self.assertEqual(built['prg'][2:14], bytes.fromhex('0b080a009e32303631000000'))
        result = title.verify_native(built, 2, bootstrap=True)
        self.assertTrue(result['decimalEntryCleared'])
        self.assertEqual(result['bootstrap'], 'Executed SYS2061 machine entry')

    def test_poisoned_score_caches_and_wrapper_state_are_restored(self):
        result = title.verify_native(native(), 2, poisoned=True)
        self.assertTrue(result['allOrderedStoresMatch'])
        self.assertEqual(result['namedMusicStates'], 3)

    def test_wrong_sample_period_is_rejected_even_when_sample_values_match(self):
        built = native()
        damaged = bytearray(built['prg'])
        instruction = built['wrapperListing'].split('LDA #$65')[0].splitlines()[-1]
        address = int(instruction.split()[0], 16)
        damaged[2 + address - title.LOAD + 1] = 0x64
        built['prg'] = bytes(damaged)
        with self.assertRaisesRegex(ValueError, 'timer periods'):
            title.verify_native(built, 2)

    def test_corrupt_runtime_data_is_detected_by_native_store_oracle(self):
        built = native()
        corrupted = bytearray(built['prg'])
        offset = 2 + built['info']['streamAddress'] - title.LOAD
        index = built['info']['alignment'][0]['tick']
        corrupted[offset + index] = 6
        built['prg'] = bytes(corrupted)
        with self.assertRaisesRegex(ValueError, 'ordered speech/music stores'):
            title.verify_native(built, 2)

    def test_rsid_reserved_fields_and_private_memory_budget_are_admitted(self):
        built = native()
        header = title.admit_rsid(built['rsid'])
        self.assertEqual(header['format'], 'RSID')
        self.assertEqual(header['clockDeclaration'], 'NTSC')
        self.assertEqual(header['sidModelDeclaration'], 'MOS6581')
        self.assertLess(built['info']['payloadEndAddress'], 0xd000)
        for offset in (8, 12, 18, 120):
            damaged = bytearray(built['rsid'])
            damaged[offset] = 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                title.admit_rsid(bytes(damaged))

    def test_target_duration_and_metadata_do_not_expand_native_contract(self):
        composition, alignment, commands = fixture()
        for seconds in (True, float('nan'), 261):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                title.build(composition, bytes(65536), alignment, seconds=seconds)
        with patch.object(title, 'decode_commands', return_value=(commands, [])):
            first = title.build(composition, bytes(65536), alignment, seconds=5)
            composition['sourceEvidence'] = dict(sourceInstructions=[0xea], capturedSamples=[12, 3])
            second = title.build(composition, bytes(65536), alignment, seconds=5)
        self.assertEqual(first['prg'], second['prg'])


if __name__ == '__main__':
    unittest.main()
