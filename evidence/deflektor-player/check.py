"""Independently check numeric playback and bounded editable source comparisons."""

import argparse
import ast
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))

SOURCE_SHA = '606ad4cb19e29c060bb77a9b44253dee62d3d972724acb6cddf625fc2466d44d'
LEDGER_SHA = '7c1ccca95afc19175b4efc50674f8f1e23783b0dcad525d5955a9cf85523fa00'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def project(records):
    return [{key: row[key] for key in ('phase', 'tick', 'address', 'value')} for row in records]


def verify_promoted_components():
    class Normalize(ast.NodeTransformer):
        def visit_FunctionDef(self, node):
            node.name = {'validate_wave': 'validate', 'validate_score_pitch': 'validate'}.get(node.name, node.name)
            return self.generic_visit(node)

        def visit_Name(self, node):
            node.id = {'validate_wave': 'validate', 'validate_score_pitch': 'validate'}.get(node.id, node.id)
            return node

    promoted = ast.parse((ROOT / 'scripts/deflektor_programs.py').read_text())
    lookup = {node.name: node for node in promoted.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    checks = []
    for family in ('programs', 'caller', 'motion'):
        original = ast.parse((ROOT / f'evidence/deflektor-{family}/model.py').read_text())
        for node in original.body:
            if not isinstance(node, (ast.FunctionDef, ast.ClassDef)) or node.name in ('require', 'byte', 'word'):
                continue
            target = {('programs', 'validate'): 'validate_wave', ('caller', 'validate'): 'validate_score_pitch'}.get((family, node.name), node.name)
            expected = ast.dump(Normalize().visit(node), include_attributes=False)
            actual = ast.dump(Normalize().visit(lookup[target]), include_attributes=False)
            assert expected == actual, f'Promoted component changed: {family}/{target}'
            checks.append(dict(family=family, definition=target))
    return checks


def independent_compute(description, calls):
    from deflektor_player import compute_writes
    before = deepcopy(description)
    with patch('builtins.open', side_effect=AssertionError('Runtime attempted file I/O')), \
            patch('io.open', side_effect=AssertionError('Runtime attempted file I/O')):
        result = compute_writes(description, calls=calls)
    assert description == before, 'Runtime changed editable input data'
    return result


def save(path, value, compressed=False):
    raw = (json.dumps(value, separators=(',', ':') if compressed else None,
                      indent=None if compressed else 2) + '\n').encode()
    stored = gzip.compress(raw, mtime=0) if compressed else raw
    with path.open('xb') as stream:
        stream.write(stored)
    return dict(path=path.name, bytes=len(stored), sha256=sha(stored),
                originalBytes=len(raw), originalSha256=sha(raw))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('description', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Use a fresh output directory'
    tools = ('deflektor_player.py', 'deflektor_programs.py', 'deflektor_score.py',
             'psid_audit.py', 'psid_profile.py', 'sid_audit_host.py', 'verify_player.py')
    dependencies = {name: sha((ROOT / 'scripts' / name).read_bytes()) for name in tools}
    checker_sha = sha(Path(__file__).read_bytes())
    promoted_components = verify_promoted_components()
    from psid_audit import audit_psid
    source_path = ROOT / '.local/research/deflektor/Deflektor.sid'
    source = source_path.read_bytes()
    assert sha(source) == SOURCE_SHA
    description_raw = args.description.read_bytes()
    description = json.loads(description_raw)
    archive = (ROOT / 'evidence/deflektor-form/full40000/writes.json.gz').read_bytes()
    assert sha(archive) == LEDGER_SHA
    reference = json.loads(gzip.decompress(archive))
    expected = project(reference)
    actual = independent_compute(description, 40000)
    assert actual == expected, 'Complete numeric output differs from source ledger'
    assert len(actual) == 166845 and actual[-1]['tick'] == 8480
    cap_checks = []
    for calls in (0, 1, 64, 8480, 8481):
        bounded = independent_compute(description, calls)
        prefix = [row for row in expected if row['tick'] < calls]
        assert bounded == prefix, f'Exclusive call cap differs at {calls}'
        cap_checks.append(dict(calls=calls, stores=len(bounded)))
    assert actual[-3:] == [dict(phase='play', tick=8480, address=address, value=0)
                           for address in (0xd404, 0xd40b, 0xd412)]

    cases = []
    for name, address, old, new, field, index in (
            ('note', 0xcb3d, 18, 19, 'pattern', 1),
            ('duration', 0xcb3e, 10, 12, 'pattern', 2),
            ('pulse_step', 0xc028, 21, 22, 'instrument', 6)):
        changed = deepcopy(description)
        if field == 'pattern':
            values = next(row['bytes'] for row in changed['score']['patterns'] if row['patternId'] == 2)
        else:
            values = next(row['fields'] for row in changed['score']['recordTable']['records']
                          if row['recordOffset'] == 27)
        assert values[index] == old
        values[index] = new
        private_source = bytearray(source)
        offset = 0x7e + address - 0xc000
        assert private_source[offset] == old
        private_source[offset] = new
        report, source_writes = audit_psid(bytes(private_source), 192,
                                         profile='pal-banked', subtune=1, host_base=0x0400)
        computed = independent_compute(changed, 192)
        assert computed == project(source_writes), f'Edited source/model differ: {name}'
        baseline = [row for row in expected if row['tick'] < 192]
        by_tick = lambda records: {tick: [(row['address'], row['value']) for row in records
                                         if row['tick'] == tick] for tick in range(192)}
        changed_calls, original_calls = by_tick(computed), by_tick(baseline)
        different = [tick for tick in range(192) if changed_calls[tick] != original_calls[tick]]
        assert len(different) >= 2, f'Edit did not change two distinct source contexts: {name}'
        cases.append(dict(name=name, sourceAddress=address, before=old, after=new,
                          privateSourceSha256=sha(private_source), report=report,
                          changedCalls=different, computed=computed, sourceWrites=source_writes))
    assert sha(source_path.read_bytes()) == SOURCE_SHA, 'Original source changed'
    assert dependencies == {name: sha((ROOT / 'scripts' / name).read_bytes()) for name in tools}, 'Dependencies changed during verification'
    assert checker_sha == sha(Path(__file__).read_bytes()), 'Checker changed during verification'
    args.output.mkdir(parents=True)
    artifacts = [save(args.output / 'computed-writes.json.gz', actual, True),
                 save(args.output / 'edited-cases.json.gz', cases, True)]
    receipt = dict(schemaVersion=1, sourceSha256=SOURCE_SHA, referenceLedgerSha256=LEDGER_SHA,
                   descriptionSha256=sha(description_raw), checkerSha256=checker_sha,
                   dependencies=dependencies,
                   complete=dict(calls=40000, matchedStores=len(actual), firstStopCall=8480,
                                 stoppedCallsWithoutWrites=31519, noRuntimeFileIO=True,
                                 inputUnchanged=True),
                   capChecks=cap_checks,
                   unchangedComponentDefinitions=promoted_components,
                   edits=[{key: value for key, value in case.items()
                           if key not in ('computed', 'sourceWrites', 'report')} for case in cases],
                   artifacts=artifacts,
                   limits=['Equality compares phase, exclusive call index, address, value and order; instruction/bus cycles are excluded.',
                           'The complete original ledger is retained evidence, not a new source run. Three edited sources execute 192 calls each through the shared guarded CPU.',
                           'No original SID, executable payload, complete RAM or audio is exported. Numeric equality does not establish acoustic equivalence, musical attribution or listening approval.'])
    save(args.output / 'verification.json', receipt)
    print(json.dumps(dict(stores=len(actual), capChecks=cap_checks,
                          editDifferences={case['name']:len(case['changedCalls']) for case in cases})))


if __name__ == '__main__':
    main()
