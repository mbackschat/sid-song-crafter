import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import shades_audit
from psid_audit import audit_psid
from sid_assembler import assemble


def fixture(play='LDA #$30\nSTA $DC05\nLDA #$41\nSTA $D404\nRTS', init='RTS'):
    code, symbols, _ = assemble(f'init:\n{init}\nplay:\n{play}\n')
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 2), (6, 124), (8, 0x1000), (10, symbols['init']), (12, symbols['play']),
                          (14, 1), (16, 1), (118, 0x14)):
        header[offset:offset + 2] = value.to_bytes(2, 'big')
    header[21] = 1
    return bytes(header) + code


class ShadesAuditTest(unittest.TestCase):
    def test_candidate_records_only_declared_sid_and_high_latch_stores(self):
        report, writes = shades_audit.audit_candidate(fixture(), 3)
        self.assertEqual([(tick, address, value) for tick in range(3)
                          for address, value in ((0xdc05, 0x30), (0xd404, 0x41))],
                         [(row['tick'], row['address'], row['value']) for row in writes])
        self.assertEqual(12326, report['minimumTimerPeriodCycles'])
        self.assertLess(report['maximumPlayCycles'] + report['irqHostAllowanceCycles'], report['minimumTimerPeriodCycles'])
        self.assertTrue(all('writerPc' in row and 'instructionStartCycle' in row for row in writes))
        with self.assertRaisesRegex(ValueError, 'CIA timing'):
            audit_psid(fixture(), 3)

    def test_candidate_rejects_short_timer_even_when_body_alone_would_fit(self):
        with self.assertRaisesRegex(ValueError, 'IRQ'):
            shades_audit.audit_candidate(fixture('LDA #$02\nSTA $DC05\n' + 'NOP\n' * 200 + 'RTS'), 2)
        with self.assertRaisesRegex(ValueError, 'IRQ'):
            shades_audit.audit_candidate(fixture('LDA #$00\nSTA $DC05\nRTS'), 1)

    def test_candidate_rejects_unsupported_hardware_and_irq_changes(self):
        for code in ('STA $DC04', 'STA $DC0E', 'LDA $DC05', 'LDA $D41B', 'LDA $E000',
                     'STA $0314', 'STA $0800', 'CLI', 'INC $DC05'):
            with self.subTest(code=code), self.assertRaises(ValueError):
                shades_audit.audit_candidate(fixture(code + '\nRTS'), 1)
        with self.assertRaises(ValueError):
            shades_audit.audit_candidate(fixture(init='LDA #$30\nSTA $DC05\nRTS'), 1)

    def test_init_flags_match_the_real_irq_host_dispatch(self):
        init = 'BNE invalid\nPHP\nPLA\nAND #$04\nBEQ invalid\nLDA #$0F\nSTA $D418\nRTS\ninvalid:\nBRK'
        report, writes = shades_audit.audit_candidate(fixture(play='RTS', init=init), 1)
        self.assertEqual([('init', None, 0xd418, 15)],
                         [(row['phase'], row['tick'], row['address'], row['value']) for row in writes])
        self.assertLess(report['initCycles'] + report['initHostAllowanceCycles'], report['initialTimerPeriodCycles'])

    def test_init_must_finish_before_first_underflow_and_requested_counts_are_explicit(self):
        with self.assertRaisesRegex(ValueError, 'init.*budget'):
            shades_audit.audit_candidate(fixture(play='RTS', init='NOP\n' * 8200 + 'RTS'), 1)
        for count in (0, 100001, True, 1.0):
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, '1..100000'):
                shades_audit.audit_candidate(fixture(), count)

    def test_vbi_ntsc_other_models_and_unsupported_headers_are_rejected(self):
        for offset, value in ((21, 0), (119, 0x18), (119, 0x24), (5, 3), (15, 2), (122, 0x42)):
            data = bytearray(fixture())
            data[offset] = value
            with self.subTest(offset=offset, value=value), self.assertRaises(ValueError):
                shades_audit.audit_candidate(data, 1)
