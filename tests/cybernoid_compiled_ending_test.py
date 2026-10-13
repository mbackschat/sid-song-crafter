import unittest

from cybernoid_compiler_test import compiler, identity
from cybernoid_ending_test import finite_fixture
from cybernoid_player import compute_writes
from psid_audit import audit_psid


class CybernoidCompiledEndingTests(unittest.TestCase):
    def test_release_fade_saturation_and_silent_stop_match_the_numeric_contract(self):
        for release, step in ((2, 1), (260, 2)):
            description = finite_fixture(release, step)
            with self.subTest(release=release, step=step):
                sid, report = compiler().build(description)
                audit, writes = audit_psid(sid, description['play_calls'] + 2)
                self.assertEqual(identity(compute_writes(description)), identity(writes))
                self.assertTrue(report['finiteMusicalEnding'])
                self.assertLess(audit['maximumPlayCycles'], audit['frameCycleBudget'])
                self.assertEqual(description['play_calls'] - 1, writes[-1]['tick'])
                self.assertEqual(0, writes[-1]['value'] & 15)


if __name__ == '__main__':
    unittest.main()
