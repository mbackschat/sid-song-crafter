import hashlib
import importlib.util
from pathlib import Path
import unittest


class StilEntryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / 'scripts/inspect-stil.py'
        spec = importlib.util.spec_from_file_location('stil_entry', path)
        cls.tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.tool)

    def test_comment_cross_reference_is_not_an_entry_header(self):
        data = b'/DEMOS/A.sid\nCOMMENT: /MUSICIANS/H/Example.sid\n\n/MUSICIANS/H/Example.sid\n ARTIST: Name\n\n/NEXT.sid\n'
        entry, receipt = self.tool.extract(data, 'MUSICIANS/H/Example.sid')
        self.assertEqual(entry, b'/MUSICIANS/H/Example.sid\n ARTIST: Name\n\n')
        self.assertEqual(receipt['firstLine'], 4)

    def test_crlf_and_latin1_are_preserved_byte_for_byte(self):
        entry = b'/MUSICIANS/H/Example.sid\r\n ARTIST: H\xfclsbeck\r\n'
        extracted, receipt = self.tool.extract(b'Header\r\n' + entry, '/MUSICIANS/H/Example.sid')
        self.assertEqual(extracted, entry)
        self.assertEqual(receipt['entrySha256'], hashlib.sha256(entry).hexdigest())
        self.assertEqual(receipt['lastLine'], 3)

    def test_missing_duplicate_and_prefix_only_matches_are_rejected(self):
        for data in (b'/OTHER.sid\n', b'/A.sid.extra\n', b'/A.sid\n\n/A.sid\n'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.tool.extract(data, '/A.sid')

    def test_multiline_entry_selector_is_rejected(self):
        with self.assertRaises(ValueError):
            self.tool.extract(b'/A.sid\n', '/A.sid\n')


if __name__ == '__main__':
    unittest.main()
