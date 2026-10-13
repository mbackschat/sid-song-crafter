import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from sid_assembler import assemble
from verify_player import cpu_type

spec = importlib.util.spec_from_file_location('shades_vice_trace', ROOT / 'scripts/trace-shades-vice.py')
trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace)


def fixture(source=None):
    source = source or '''
init:
RTS
play:
INC $2000
LDA $2000
STA $D400
CMP #$01
BNE later
LDA #$30
STA $DC05
later:
LDA $2000
CMP #$04
BNE done
LDA #$20
STA $DC05
done:
RTS
'''
    payload, labels, _ = assemble(source)
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 2), (6, 124), (8, 0x1000), (10, labels['init']),
                          (12, labels['play']), (14, 1), (16, 1), (118, 0x14)):
        header[offset:offset + 2] = value.to_bytes(2, 'big')
    header[21] = 1
    return bytes(header) + payload


class ShadesViceTraceTest(unittest.TestCase):
    def test_rejects_fixed_pal_dual_unknown_model_and_payload_host_overlap(self):
        for offset, value in ((21, 0), (5, 3), (119, 0x24), (15, 2), (9, 0x00)):
            invalid = bytearray(fixture())
            invalid[offset] = value
            if offset == 9:
                invalid[8] = 8
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                trace.psid_profile(invalid)

    def test_public_source_pin_rejects_independent_fixture(self):
        with self.assertRaisesRegex(ValueError, 'pinned Shades'):
            trace.source_profile(fixture())

    def test_bounded_oracle_tracks_changing_latch_and_rejects_other_dependencies(self):
        report, writes = trace.bounded_oracle(fixture(), 7)
        self.assertEqual([(0, 0x30), (3, 0x20)],
                         [(row['tick'], row['value']) for row in writes if row['address'] == 0xdc05])
        self.assertEqual(7, report['playCalls'])
        for instruction in ('LDA $DC04', 'STA $DC0E', 'LDA $D41B', 'LDA $E000', 'INC $DC05'):
            with self.subTest(instruction=instruction), self.assertRaises(ValueError):
                trace.bounded_oracle(fixture(f'init:\nRTS\nplay:\n{instruction}\nRTS\n'), 2)

    def test_real_cia_irq_keeps_current_counter_then_reloads_changed_high_latch(self):
        vice = ROOT / '.tools/vice-headless-3.9/build/src/x64sc'
        data_directory = Path('/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice')
        if not vice.is_file() or not data_directory.is_dir():
            self.skipTest('Local headless VICE and ROMs are required')
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'trace'
            data = fixture()
            result = trace.run_profile(data, output, 7, vice, data_directory)
            parsed = json.loads((output / 'trace.json').read_text())
            oracle_report, oracle = trace.bounded_oracle(data, 7)
            parsed['entries'][2]['monitorCycle'] += 20
            with self.assertRaisesRegex(ValueError, 'cadence'):
                trace.verify_trace(parsed, oracle, 7, oracle_report)
            parsed = json.loads((output / 'trace.json').read_text())
            parsed['writes'][-1]['source'] = True
            with self.assertRaisesRegex(ValueError, 'ordered source stores'):
                trace.verify_trace(parsed, oracle, 7, oracle_report)
        cadence = result['verification']['cadence']
        self.assertEqual([0x4026, 0x3026, 0x3026, 0x3026, 0x2026, 0x2026], cadence['expectedIntervals'])
        self.assertLessEqual(cadence['maximumIntervalError'], 4)
        self.assertLessEqual(cadence['maximumAccumulatedPhaseError'], 4)
        self.assertEqual(9, result['verification']['matchedSourceWrites'])
        self.assertEqual(7, result['verification']['acknowledgedInterrupts'])
        self.assertEqual(0x81, result['verification']['ciaAcknowledgementValue'])
        self.assertEqual(26, result['verification']['irqHandlerToPlayCycles'])
        self.assertEqual('MOS6526A (new)', result['host']['ciaModel'])
        self.assertGreater(result['verification']['firstPlayAfterTimerStartCycles'], 0x4025)

    def test_absolute_decrement_instruction_duration_matches_executed_vice(self):
        vice = ROOT / '.tools/vice-headless-3.9/build/src/x64sc'
        data_directory = Path('/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice')
        if not vice.is_file() or not data_directory.is_dir():
            self.skipTest('Local headless VICE and ROMs are required')
        data = fixture('init:\nRTS\nplay:\nLDA #$03\nSTA $2000\nDEC $2000\nLDA $2000\nSTA $D400\nRTS\n')
        with tempfile.TemporaryDirectory() as temporary:
            result = trace.run_profile(data, Path(temporary) / 'trace', 2, vice, data_directory)
        self.assertEqual(26, result['oracle']['maximumPlayCycles'])
        self.assertEqual(26, result['verification']['maximumSourceCallCycles'])

    def test_irq_wrapper_restores_bank_without_clobbering_source_zero_page(self):
        vice = ROOT / '.tools/vice-headless-3.9/build/src/x64sc'
        data_directory = Path('/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice')
        if not vice.is_file() or not data_directory.is_dir():
            self.skipTest('Local headless VICE and ROMs are required')
        data = fixture('init:\nLDA #$55\nSTA $A5\nRTS\nplay:\nLDA $01\nSTA $D401\nINC $A5\nLDA $A5\nSTA $D400\nLDA #$36\nSTA $01\nRTS\n')
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'trace'
            trace.run_profile(data, output, 3, vice, data_directory)
            parsed = json.loads((output / 'trace.json').read_text())
        source_writes = [(row['tick'], row['address'], row['value']) for row in parsed['writes'] if row['source']]
        self.assertEqual([(tick, address, value) for tick in range(3)
                          for address, value in ((0xd401, 0x37), (0xd400, 0x56 + tick))], source_writes)

    def test_host_counter_supports_last_16_bit_call_without_running_the_whole_range(self):
        data = fixture()
        profile = trace.psid_profile(data)
        program, labels, _ = trace.harness(profile, 65535)
        self.assertEqual((255, 255), (labels['count_lo'], labels['count_hi']))
        self.assertLess(trace.HOST_BASE + len(program) - 2, trace.COUNTER)
        memory = [0] * 65536
        memory[profile['loadAddress']:profile['endAddress']] = profile['payload']
        memory[trace.HOST_BASE:trace.HOST_BASE + len(program) - 2] = program[2:]
        memory[1] = 0x37
        memory[trace.COUNTER:trace.COUNTER + 2] = [0xfe, 0xff]
        cpu = cpu_type()(memory=memory, pc=labels['irq'])
        cpu.stPushWord(0x0200)
        for value in (cpu.p, 0, 0, 0):
            cpu.stPush(value)
        for _ in range(100):
            if cpu.pc == 0x0200:
                break
            cpu.step()
        self.assertEqual(0x0200, cpu.pc)
        self.assertEqual([255, 255, 1], memory[trace.COUNTER:trace.FINISHED + 1])
        self.assertEqual((0, 0x7f, 255), (memory[0xdc0e], memory[0xdc0d], cpu.sp))
        for count in (0, 65536, True):
            with self.subTest(count=count), self.assertRaises(ValueError):
                trace.harness(profile, count)

    def test_pinned_sources_match_bounded_store_oracle_across_pattern_reloads(self):
        vice = ROOT / '.tools/vice-headless-3.9/build/src/x64sc'
        data_directory = Path('/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice')
        sources = [ROOT / '.local/research/shades' / name for name in trace.SOURCE_PINS]
        if not vice.is_file() or not data_directory.is_dir() or not all(path.is_file() for path in sources):
            self.skipTest('Pinned local Shades inputs and headless VICE are required')
        for source in sources:
            with self.subTest(source=source.name), tempfile.TemporaryDirectory() as temporary:
                result = trace.run_trace(source, Path(temporary) / 'trace', 400, vice, data_directory)
                self.assertEqual([0, 193, 385], [row['tick'] for row in result['timerWrites']])
                self.assertEqual({0x30}, {row['value'] for row in result['timerWrites']})
                self.assertEqual(400, result['verification']['playCalls'])
                self.assertLessEqual(result['verification']['cadence']['maximumIntervalError'], 4)
                self.assertLessEqual(result['verification']['cadence']['maximumAccumulatedPhaseError'], 4)


if __name__ == '__main__':
    unittest.main()
