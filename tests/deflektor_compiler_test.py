"""Compare independently compiled Deflektor computation with the numeric oracle."""

from copy import deepcopy
import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from deflektor_player import compute_writes
from deflektor_compiler import build, verify, run, standalone_prg, bootstrap_verification


def identity(rows):
    return [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]


def title():
    return json.loads((ROOT / 'songs/studies/deflektor-reconstruction/title.json').read_text())


class DeflektorCompilerTests(unittest.TestCase):
    def check(self, description, calls=None):
        sid, built = build(description)
        report, writes = verify(description, sid, built, calls=calls)
        self.assertEqual(identity(compute_writes(description, calls=calls)), identity(writes))
        self.assertLess(report['maximumPlayCycles'], 19656)
        self.assertTrue(report['resetVerification']['passed'])
        self.assertFalse(built['originalDriverIncluded'])
        self.assertFalse(built['registerDumpPlayback'])
        self.assertTrue(built['runtimeScoreScheduler'])
        self.assertEqual(sid[:4], b'PSID')
        return sid, built, report, writes

    def test_full_title_ordered_stores_natural_stop_and_stopped_tail(self):
        data = title()
        _, _, report, writes = self.check(data)
        with gzip.open(ROOT / 'evidence/deflektor-player/verified/computed-writes.json.gz', 'rt') as source:
            self.assertEqual(identity(json.load(source)), identity(writes))
        self.assertEqual(40000, report['checkedPlayCalls'])
        self.assertEqual(166845, len(writes))
        self.assertEqual(0, report['coldInitializationStores'])
        self.assertTrue(report['completeDeclaredRange'])
        self.assertTrue(report['ending']['naturalControlZeroStop'])
        self.assertEqual(8480, report['ending']['firstStopCall'])
        self.assertEqual(31519, report['ending']['followingCallsWithoutStores'])
        self.assertEqual([(0xd404, 0), (0xd40b, 0), (0xd412, 0)],
                         [(row['address'], row['value']) for row in writes if row['tick'] == 8480])
        self.assertFalse(any(row['tick'] > 8480 for row in writes))

    def test_edited_note_duration_and_patch_compute_new_outputs(self):
        baseline = title()
        baseline_writes = identity(compute_writes(baseline, calls=192))
        changes = []
        for kind in ('note', 'duration', 'pulse'):
            changed = deepcopy(baseline)
            pattern = next(row for row in changed['score']['patterns'] if row['patternId'] == 2)
            if kind == 'note':
                pattern['bytes'][1] = 19
            elif kind == 'duration':
                pattern['bytes'][2] = 12
            else:
                record = next(row for row in changed['score']['recordTable']['records'] if row['recordOffset'] == 27)
                record['fields'][6] = 22
            before = deepcopy(changed)
            with self.subTest(edit=kind):
                _, _, _, writes = self.check(changed, calls=192)
                self.assertNotEqual(baseline_writes, identity(writes))
                self.assertEqual(before, changed)
                changes.append(identity(writes))
        self.assertEqual(3, len(changes))

    def test_export_restores_poisoned_state_and_standalone_bootstrap(self):
        data = title()
        sid, built, _, _ = self.check(data, calls=64)
        prg, labels = standalone_prg(sid, built, data['play_calls'])
        bootstrap = bootstrap_verification(prg, labels, data, built)
        self.assertTrue(bootstrap['passed'])
        self.assertTrue(bootstrap['restoredPoisonedState'])
        self.assertEqual(prg[:2], b'\x01\x08')
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.json'
            source.write_text(json.dumps(data))
            output = Path(directory) / 'compiled'
            report = run(source, output, calls=64)
            self.assertEqual(64, report['checkedPlayCalls'])
            self.assertEqual(sid, (output / 'reconstructed.sid').read_bytes())
            self.assertEqual(prg, (output / 'reconstructed.prg').read_bytes())
            self.assertTrue((output / 'player.asm').exists())
            self.assertTrue((output / 'verification.json').exists())

    def test_unsupported_schema_cold_state_and_zero_duration_reject(self):
        for kind in ('schema', 'profile', 'cold', 'duration', 'effect'):
            data = title()
            if kind == 'schema':
                data['schemaVersion'] = 'unknown'
            elif kind == 'profile':
                data['profile']['clock'] = 'ntsc'
            elif kind == 'cold':
                data['initial_state']['voices'][0]['remaining'] = 4
            else:
                pattern = next(row for row in data['score']['patterns'] if row['patternId'] == 2)
                if kind == 'duration':
                    pattern['bytes'][2] = 0
                else:
                    pattern['bytes'].insert(1, 0xb0)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                build(data)

    def test_optional_title_and_author_use_bounded_latin1_without_changing_payload(self):
        data = title()
        data['play_calls'] = 1
        baseline, _ = build(data)
        self.assertEqual(b'Deflektor independent title'.ljust(32, b'\0'), baseline[22:54])
        self.assertEqual(b'SID Song Crafter'.ljust(32, b'\0'), baseline[54:86])
        data['title'] = 'Für Elise with Deflektor tonal programs'
        data['author'] = 'Ludwig van Beethoven / SID Song Crafter'
        before = deepcopy(data)
        changed, _ = build(data)
        self.assertEqual(data['title'].encode('latin-1')[:31].ljust(32, b'\0'), changed[22:54])
        self.assertEqual(data['author'].encode('latin-1')[:31].ljust(32, b'\0'), changed[54:86])
        self.assertEqual(baseline[:22], changed[:22])
        self.assertEqual(baseline[86:], changed[86:])
        self.assertEqual(before, data)

    def test_header_metadata_rejects_non_text_embedded_nul_and_non_latin1(self):
        for field in ('title', 'author'):
            for value in (None, True, 1, b'text', 'hidden\0label', 'Unsupported \u266b'):
                data = title()
                data['play_calls'] = 1
                data[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    build(data)


if __name__ == '__main__':
    unittest.main()
