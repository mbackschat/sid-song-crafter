from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from sid_intake import inspect_sid


def fixture(*, magic=b'PSID', songs=3, speed=0, load=0, play=0x1003, flags=0x14):
    data = bytearray(124)
    data[:4] = magic
    for offset, value in ((4, 2), (6, 124), (8, load), (10, 0x1000),
                          (12, play), (14, songs), (16, 1), (118, flags)):
        data[offset:offset + 2] = value.to_bytes(2, 'big')
    data[18:22] = speed.to_bytes(4, 'big')
    data[22:26] = b'Tune'
    data[54:60] = b'Author'
    data.extend((b'\x00\x10' if not load else b'') + b'\x60' * 8)
    return bytes(data)


class SidIntakeTests(unittest.TestCase):
    def test_host_admission_is_explicit_and_never_changes_reference_bytes(self):
        raw = bytearray(fixture(load=0xc000, play=0xc003))
        raw[10:12] = (0xc000).to_bytes(2, 'big')
        original = bytes(raw)
        default = inspect_sid(raw, subtune=1)
        self.assertFalse(default['callableProfile']['accepted'])
        selected = inspect_sid(raw, subtune=1, host_base=0x0400)
        self.assertTrue(selected['callableProfile']['accepted'])
        self.assertEqual(0x0400, selected['callableProfile']['hostBase'])
        self.assertEqual(default['sha256'], selected['sha256'])
        self.assertEqual(0xc000, selected['loadAddress'])
        self.assertEqual(original, bytes(raw))

    def test_invalid_host_is_an_admission_failure_not_a_header_mutation(self):
        for host in (0x0300, 0x0401, 0x9f00, True):
            with self.subTest(host=host):
                report = inspect_sid(fixture(), subtune=1, host_base=host)
                self.assertFalse(report['callableProfile']['accepted'])
                self.assertEqual(host, report['callableProfile']['requestedHostBase'])
                self.assertEqual(0x1000, report['loadAddress'])

    def test_embedded_load_is_not_payload_and_report_excludes_original_bytes(self):
        raw = fixture()
        report = inspect_sid(raw, subtune=1)
        self.assertEqual((0, 0x1000, 8, 0x1008), tuple(report[k] for k in
                         ('headerLoadAddress', 'loadAddress', 'payloadBytes', 'endAddressExclusive')))
        self.assertEqual(('Tune', 'Author', 'PAL', 'MOS6581'), tuple(report[k] for k in
                         ('title', 'author', 'clockDeclaration', 'sidModelDeclaration')))
        self.assertEqual('VBI', report['selectedTimingDeclaration'])
        self.assertTrue(report['callableProfile']['accepted'])
        self.assertFalse(any(isinstance(value, (bytes, bytearray)) for value in report.values()))
        self.assertNotIn('payload', report)
        self.assertEqual(raw, fixture())

    def test_explicit_load_keeps_every_payload_byte(self):
        report = inspect_sid(fixture(load=0x1000), subtune=1)
        self.assertEqual((0x1000, 8), (report['loadAddress'], report['payloadBytes']))

    def test_cia_bit_and_subtune_above32_are_reported_without_relaxing_audit(self):
        for songs, selected, speed in ((3, 2, 2), (33, 33, 1 << 31)):
            report = inspect_sid(fixture(songs=songs, speed=speed), subtune=selected)
            self.assertEqual('CIA1 Timer A', report['selectedTimingDeclaration'])
            self.assertFalse(report['callableProfile']['accepted'])
            self.assertIn('CIA timing', report['callableProfile']['reason'])

    def test_rsid_reserved_speed_does_not_claim_vbi(self):
        report = inspect_sid(fixture(magic=b'RSID', play=0), subtune=1)
        self.assertEqual('machine-controlled', report['selectedTimingDeclaration'])
        self.assertFalse(report['callableProfile']['accepted'])
        self.assertEqual(0, report['playAddress'])

    def test_irq_and_model_declarations_remain_distinct_from_execution_support(self):
        report = inspect_sid(fixture(play=0, flags=0x28), subtune=1)
        self.assertEqual(('NTSC', 'MOS8580'), (report['clockDeclaration'], report['sidModelDeclaration']))
        self.assertFalse(report['callableProfile']['accepted'])

    def test_truncation_bad_offset_and_invalid_selection_reject(self):
        raw = fixture()
        offset = bytearray(raw)
        offset[6:8] = (500).to_bytes(2, 'big')
        for data, selection in ((raw[:100], 1), (bytes(offset), 1), (raw, 0), (raw, 4), (raw, True)):
            with self.subTest(selection=selection, length=len(data)), self.assertRaises(ValueError):
                inspect_sid(data, subtune=selection)


if __name__ == '__main__':
    unittest.main()
