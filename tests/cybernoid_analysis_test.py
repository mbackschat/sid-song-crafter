import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from sid_assembler import assemble

spec = importlib.util.spec_from_file_location('cybernoid_analysis', ROOT / 'scripts/analyze-cybernoid.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
SOURCE = ROOT / '.local/research/cybernoid-ii/Cybernoid_II.sid'
ORACLE = ROOT / 'evidence/cybernoid-title-instructions/opening.trace.json.gz'


STATE = dict(tempoReload=0x2000, tempoCountdown=0x2001, playFlag=0x2002,
             orderCursor=0x2010, patternCursor=0x2013, rowCountdown=0x2016,
             durationReload=0x2019, repeatCount=0x201c, transpose=0x201f,
             instrumentIndexOffset=0x2022, orderPointerLow=0x2025, orderPointerHigh=0x2028,
             patternScratch=0x46, patternTable=0)


def fixture(order=(1, 0xff), pattern=(0x10, 0xff), repeat=1):
    source = '''
init:
    LDA #order_low
    STA $2025
    LDA #order_high
    STA $2028
    LDA #initial_repeat
    STA $201C
    RTS
play:
    LDA $2002
    BNE stopped_return
    LDX #0
    LDY $2010
order_byte:
    LDA order_data,Y
    CMP #$FF
    BEQ order_wrap
    CMP #$FE
    BEQ global_stop
    LDY #2
    LDA pattern_table,Y
    STA $46
    LDA pattern_table_high,Y
pattern_pointer:
    STA $47
    LDY $2013
pattern_start:
    LDA ($46),Y
    CMP #$FF
    BEQ pattern_end
    INC $2013
    LDA #$41
    STA $D404
    JMP body_return
pattern_end:
    LDA #0
    STA $2013
    LDA $201C
    BEQ order_advance
pattern_repeat:
    DEC $201C,X
    JMP body_return
order_advance:
    INC $2010,X
    JMP body_return
order_wrap:
    LDA #0
    STA $2010
    JMP body_return
global_stop:
    LDA #1
    STA $2002
    LDA #0
    STA $D404
stop_return:
    RTS
stopped_return:
    RTS
body_return:
    RTS
pattern_table:
    .word pattern_data,pattern_data
order_data:
    .byte ORDER
pattern_data:
    .byte PATTERN
'''.replace('ORDER', ','.join(f'${value:02X}' for value in order)).replace('PATTERN', ','.join(f'${value:02X}' for value in pattern))
    constants = dict(order_low=0, order_high=0, initial_repeat=repeat, pattern_table_high=0x1000)
    _, symbols, _ = assemble(source, constants)
    constants.update(order_low=symbols['order_data'] & 255, order_high=symbols['order_data'] >> 8,
                     pattern_table_high=symbols['pattern_table'] + 1)
    code, symbols, _ = assemble(source, constants)
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 2), (6, 124), (8, 0x1000), (10, symbols['init']),
                          (12, symbols['play']), (14, 2), (16, 1), (118, 0x14)):
        header[offset:offset + 2] = value.to_bytes(2, 'big')
    hooks = {kind: symbols[label] for kind, label in (
        ('orderByte', 'order_byte'), ('patternPointer', 'pattern_pointer'),
        ('patternStart', 'pattern_start'), ('patternEnd', 'pattern_end'),
        ('patternRepeat', 'pattern_repeat'), ('orderAdvance', 'order_advance'),
        ('orderWrap', 'order_wrap'), ('globalStop', 'global_stop'))}
    returns = {symbols[label]: kind for label, kind in (('body_return', 'body'),
               ('stop_return', 'stopClearing'), ('stopped_return', 'stopped'))}
    state = {**STATE, 'patternTable': symbols['pattern_table']}
    return bytes(header) + code, hooks, state, returns


class CybernoidAnalysisTests(unittest.TestCase):
    def observe_fixture(self, ticks, **kwargs):
        data, hooks, state, returns = fixture(**kwargs)
        return probe._observe_form(data, ticks, hooks=hooks, state_addresses=state, returns=returns)

    def test_pattern_end_repeat_and_voice_order_wrap_are_distinct_executed_events(self):
        report, events, states, writes = self.observe_fixture(8)
        summary = probe.summarize(events, states, 8)
        self.assertEqual([1, 3, 6], [row['call'] for row in events if row['kind'] == 'patternEnd'])
        self.assertEqual([1], [row['call'] for row in events if row['kind'] == 'patternRepeat'])
        self.assertEqual([4, 7], summary['orderWrapCalls']['0'])
        self.assertEqual([], summary['globalStopCalls'])
        self.assertEqual(list(range(8)), [row['call'] for row in states])
        self.assertEqual(8, report['playCalls'])
        pointers = [row for row in events if row['kind'] == 'patternPointer']
        self.assertTrue(all(row['patternId'] == 1 and row['patternPointer'] > 0x1000 for row in pointers))
        reads = [row for row in events if row['kind'] == 'pointerRead']
        self.assertEqual([0x10, 0xff, 0x10, 0xff, 0x10, 0xff], [row['sourceValue'] for row in reads])

    def test_global_stop_records_transition_and_all_requested_silent_calls(self):
        report, events, states, writes = self.observe_fixture(10, order=(0xfe,))
        self.assertEqual([0], probe.summarize(events, states, 10)['globalStopCalls'])
        self.assertEqual(['stopClearing'] + ['stopped'] * 9, [row['returnKind'] for row in states])
        self.assertEqual(10, report['playCalls'])
        self.assertEqual([('play', 0, 0xd404, 0)],
                         [(row['phase'], row['tick'], row['address'], row['value']) for row in writes])
        self.assertTrue(all(row['cpu']['sp'] == 253 for row in states))
        self.assertTrue(all(row['globals']['playFlag'] == 1 for row in states))

    def test_machine_hash_keeps_unmapped_ram_and_exact_cpu_state_without_normalization(self):
        code, symbols, _ = assemble('init:\nRTS\nplay:\nINC $2050\nLDX #0\nLDY #0\nLDA #$41\nfinished:\nRTS')
        data = bytearray(fixture()[0][:124])
        data[10:14] = symbols['init'].to_bytes(2, 'big') + symbols['play'].to_bytes(2, 'big')
        _, events, states, _ = probe._observe_form(bytes(data) + code, 3, hooks={},
                                                   state_addresses=STATE, returns={symbols['finished']: 'body'})
        self.assertEqual(states[0]['voices'], states[1]['voices'])
        self.assertEqual(states[0]['globals'], states[1]['globals'])
        self.assertEqual(states[0]['cpu'], states[1]['cpu'])
        self.assertEqual(3, len({row['ramSha256'] for row in states}))
        self.assertEqual([], probe.summarize(events, states, 3)['wholeStateRepeats'])
        body = bytes(data) + code
        stable = body[:124] + code[:1] + bytes((0x60,))
        stable = bytearray(stable)
        stable[12:14] = (0x1001).to_bytes(2, 'big')
        _, events, states, _ = probe._observe_form(stable, 3, hooks={}, state_addresses=STATE, returns={0x1001: 'body'})
        self.assertEqual([1, 2], [row['repeatCall'] for row in probe.summarize(events, states, 3)['wholeStateRepeats']])

    def test_source_pin_precedes_execution_and_finite_bounds_are_enforced(self):
        with patch.object(probe, '_observe_form', side_effect=AssertionError('Execution before source pin')):
            with self.assertRaisesRegex(ValueError, 'pinned'):
                probe.analyze_source(fixture()[0], 2)
        for ticks in (0, 100001, True, 1.5):
            with self.subTest(ticks=ticks), self.assertRaises(ValueError):
                self.observe_fixture(ticks)

    def test_unowned_zero_page_reuse_is_retained_without_a_pattern_or_voice_claim(self):
        code, symbols, _ = assemble('init:\nLDA #$50\nSTA $46\nLDA #$20\nSTA $47\nRTS\n'
                                    'play:\nLDX #7\nLDY #0\nLDA ($46),Y\nfinished:\nRTS')
        data = bytearray(fixture()[0][:124])
        data[10:14] = symbols['init'].to_bytes(2, 'big') + symbols['play'].to_bytes(2, 'big')
        _, events, _, _ = probe._observe_form(bytes(data) + code, 1, hooks={},
                                              state_addresses=STATE, returns={symbols['finished']: 'body'})
        self.assertEqual(1, len(events))
        self.assertEqual(('pointerRead', 'unclassified', None, 0x2050, 0),
                         tuple(events[0][key] for key in ('kind', 'context', 'voiceIndex', 'sourceAddress', 'sourceValue')))
        self.assertIsNone(events[0]['selectedPatternPointerEventIndex'])
        self.assertEqual(7, events[0]['cpu']['x'])

    def test_output_preflight_preserves_existing_directories_and_cli_creates_separate_ledgers(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'exists'
            output.mkdir()
            with self.assertRaisesRegex(ValueError, 'fresh'):
                probe.run_analysis(Path(temporary) / 'missing.sid', output, 2)
            if not SOURCE.exists():
                return
            output = Path(temporary) / 'fresh'
            data = SOURCE.read_bytes()
            argv = ['analyze-cybernoid.py', str(SOURCE), '--ticks', '4', '--output', str(output)]
            with patch.object(sys, 'argv', argv), patch('builtins.print'):
                probe.main()
            self.assertEqual(data, SOURCE.read_bytes())
            receipt = json.loads((output / 'receipt.json').read_text())
            self.assertEqual(4, receipt['playCalls'])
            self.assertEqual({'events.json', 'call-state.json', 'audit.json', 'audit.writes.json'}, set(receipt['artifacts']))
            for name, identity in receipt['artifacts'].items():
                self.assertEqual(identity['sha256'], hashlib.sha256((output / name).read_bytes()).hexdigest())

    @unittest.skipUnless(SOURCE.exists() and ORACLE.exists(), 'Requires installed source and canonical64-call trace')
    def test_real_hook_consumption_and_ordered_writes_match_the_canonical_64_call_trace(self):
        with gzip.open(ORACLE, 'rt') as file:
            oracle = json.load(file)
        result, events, states, writes = probe.analyze_source(SOURCE.read_bytes(), 64)
        names = {0xa754: 'order', 0xa7c0: 'start', 0xa936: 'helper', 0xa8f6: 'peek'}
        expected = [(names.get(row['pc'], 'continuation'), row['tick'], row['pc'], row['instructionStartCycle'],
                     row['x'], row['operandAddress'], row['operandValueBefore'], row['bytes'])
                    for row in oracle['instructions'] if row['pc'] == 0xa754 or row['bytes'] == 'b146']
        actual = [(row['context'], row['call'], row['pc'], row['instructionStartCycle'],
                   row['voiceIndex'], row['sourceAddress'], row['sourceValue'], row['bytes'])
                  for row in events if row['kind'] in ('orderByte', 'pointerRead')]
        self.assertEqual(expected, actual)
        self.assertTrue(all(row['selectedPatternPointerEventIndex'] is not None for row in events if row['kind'] == 'pointerRead'))
        reference_writes = oracle['initSidWrites'] + [{key: value for key, value in row.items() if key != 'instructionPc'}
                                                     for row in oracle['sidWrites']]
        self.assertEqual(reference_writes, writes)
        self.assertEqual(64, len(states))
        self.assertTrue(all(row['returnPc'] == 0xae2c for row in states))
        self.assertEqual([], result['summary']['orderWrapCalls']['0'])
        self.assertEqual([], result['summary']['globalStopCalls'])


if __name__ == '__main__':
    unittest.main()
