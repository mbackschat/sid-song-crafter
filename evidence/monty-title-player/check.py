"""Verify complete numeric Monty output and bounded private-source edits."""

import argparse
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
SOURCE_SHA = '528a7330817e4a0a0f75a505e9fe2444e07c5072ce5383ceaa89f183f0eee3ab'
LEDGER_SHA = 'f78899ef13bb54345ec4192fc7a9aa0306ce701df8862c42d02aa11cc54606fe'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def project(records):
    return [{key: row[key] for key in ('phase', 'tick', 'address', 'value')} for row in records]


def compare(actual, expected, name):
    for index, (computed, source) in enumerate(zip(actual, expected)):
        assert computed == source, f'{name} differs at store {index}: computed={computed}, source={source}'
    assert len(actual) == len(expected), f'{name} store count differs: {len(actual)} != {len(expected)}'


def compute(description, calls, *, state=False):
    from monty_title_player import compute_player
    before = deepcopy(description)
    with patch('builtins.open', side_effect=AssertionError('Runtime file access')), \
            patch('io.open', side_effect=AssertionError('Runtime file access')):
        result = compute_player(description, calls=calls)
    assert description == before, 'Input description was mutated'
    return result if state else result['writes']


def save(path, value, compressed=False):
    raw = (json.dumps(value, separators=(',', ':') if compressed else None,
                      indent=None if compressed else 2) + '\n').encode()
    stored = gzip.compress(raw, mtime=0) if compressed else raw
    with path.open('xb') as stream:
        stream.write(stored)
    return dict(path=path.name, sha256=sha(stored), bytes=len(stored),
                originalSha256=sha(raw), originalBytes=len(raw))


def by_call(records):
    result = {}
    for row in records:
        result.setdefault((row['phase'], row['tick']), []).append((row['address'], row['value']))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('description', type=Path, nargs='?', default=ROOT / 'songs/monty-title-source.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Use a fresh output directory'
    names = ('monty_title_player.py', 'monty_title_programs.py', 'monty_title_score.py', 'psid_profile.py',
             'psid_audit.py', 'sid_audit_host.py', 'verify_player.py')
    dependencies = {name: sha((ROOT / 'scripts' / name).read_bytes()) for name in names}
    checker_sha = sha(Path(__file__).read_bytes())
    from psid_audit import audit_psid
    source_path = ROOT / '.local/monty-source.sid'
    source = source_path.read_bytes()
    assert sha(source) == SOURCE_SHA and source[0x7c:0x7e] == bytes((0, 128))
    description_raw = args.description.read_bytes()
    description = json.loads(description_raw)
    ledger = (ROOT / 'evidence/monty-form/full40000/audit.writes.json.gz').read_bytes()
    assert sha(ledger) == LEDGER_SHA
    original = json.loads(gzip.decompress(ledger))
    expected = project(original)
    complete = compute(description, 40000, state=True)
    actual = complete['writes']
    compare(actual, expected, 'Full 40000-call player')
    assert len(actual) == 373739, 'Complete retained ledger count differs'
    cap_checks = []
    for calls in (0, 1, 64, 192):
        bounded = compute(description, calls)
        prefix = [row for row in expected if row['phase'] == 'init' or row['tick'] < calls]
        compare(bounded, prefix, f'Exclusive cap {calls}')
        cap_checks.append(dict(calls=calls, stores=len(bounded)))
    cases = []
    baseline = by_call([row for row in expected if row['phase'] == 'init' or row['tick'] < 192])
    for name, address, old, new in (
            ('note', 0x8beb, 19, 20),
            ('pulse_step', 0x941a, 231, 199),
            ('prior_control_alias', 0x84d1, 65, 129),
            ('late_octave_alias', 0x941b, 2, 6)):
        changed = deepcopy(description)
        if name == 'note':
            target = next(row['bytes'] for row in changed['score']['patterns'] if row['pattern_id'] == 19)
            key = 2
        elif name == 'prior_control_alias':
            target, key = changed['initial_state']['voices'][1], 'voice_control'
        else:
            target = changed['instruments'][12]
            key = 'pulse_value' if name == 'pulse_step' else 'effects'
        assert target[key] == old, f'Numeric edit input changed: {name}'
        target[key] = new
        private = bytearray(source)
        offset = 0x7e + address - 0x8000
        assert private[offset] == old
        private[offset] = new
        report, source_writes = audit_psid(bytes(private), 192, profile='pal-banked', subtune=1)
        computed = compute(changed, 192)
        compare(computed, project(source_writes), f'Edited source/model {name}')
        edited = by_call(computed)
        differences = [tick for tick in range(192) if baseline.get(('play', tick)) != edited.get(('play', tick))]
        assert len(differences) >= 2, f'Edit lacks two changing contexts: {name}'
        cases.append(dict(name=name, sourceAddress=address, before=old, after=new,
                          privateSourceSha256=sha(private), changedCalls=differences,
                          report=report, computed=computed, sourceWrites=source_writes))
    assert sha(source_path.read_bytes()) == SOURCE_SHA
    assert checker_sha == sha(Path(__file__).read_bytes())
    assert dependencies == {name: sha((ROOT / 'scripts' / name).read_bytes()) for name in names}
    args.output.mkdir(parents=True)
    artifacts = [save(args.output / 'computed-writes.json.gz', actual, True),
                 save(args.output / 'edited-cases.json.gz', cases, True)]
    receipt = dict(schemaVersion=1, sourceSha256=SOURCE_SHA, referenceLedgerSha256=LEDGER_SHA,
        descriptionSha256=sha(description_raw), checkerSha256=checker_sha, dependencies=dependencies,
        complete=dict(calls=40000, stores=len(actual), initStores=3, playStores=373736,
                      noRuntimeFileIO=True, inputUnchanged=True,
                      finalState=complete['finalState'], instruments=complete['instruments'],
                      stopped=complete['stopped']), capChecks=cap_checks,
        edits=[{key: value for key, value in case.items() if key not in ('report', 'computed', 'sourceWrites')}
               for case in cases], artifacts=artifacts,
        limits=['Complete equality uses phase/call/address/value/order; instruction and bus cycles are excluded.',
                'The complete original ledger is retained evidence. Four private source edits execute only 192 calls each using the guarded CPU; no full original run or new VICE comparison.',
                'The late-octave alias case enables a source path absent from the selected title; it is synthetic coverage, not a claim about the original arrangement.',
                'No original SID, payload, full RAM or audio is exported. Numeric equality does not establish acoustic similarity or listening approval.'])
    save(args.output / 'verification.json', receipt)
    print(json.dumps(dict(stores=len(actual), capChecks=cap_checks,
                          edits={case['name']:len(case['changedCalls']) for case in cases})))


if __name__ == '__main__':
    main()
