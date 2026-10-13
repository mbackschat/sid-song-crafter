"""Verify separate pitch and duration edits against private in-memory SID copies."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid
from model import compute
from probe import SOURCE_SHA, PINS


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError('Choose a fresh output file')
    source = ROOT / '.local/research/airwolf/Airwolf.sid'
    original = source.read_bytes()
    assert digest(original) == SOURCE_SHA
    for name, expected in PINS.items():
        assert digest((ROOT/'scripts'/name).read_bytes()) == expected
    score = json.loads((HERE/'complete/score.json').read_text())
    baseline = compute(score, 128)
    cases = []
    for name, address, value in [('first-frequency-low',0x3c02,0x6c),('first-duration',0x3c00,4)]:
        changed = bytearray(original)
        offset = 126 + address - 0x3add
        before = changed[offset]
        changed[offset] = value
        edited = copy.deepcopy(score)
        if name == 'first-frequency-low':
            edited['rows'][0]['notes'][0] += 1
        else:
            edited['rows'][0]['duration'] = value
        expected = compute(edited,128)
        audit, writes = audit_psid(bytes(changed),128,profile='pal-banked',subtune=1)
        actual = [{key:row[key] for key in ('phase','tick','address','value')} for row in writes]
        assert expected['writes'] == actual and actual != baseline['writes']
        if name == 'first-frequency-low':
            differences = [(a,b) for a,b in zip(baseline['writes'],actual) if a!=b]
            assert len(actual)==len(baseline['writes']) and len(differences)==1
            assert differences[0][0]['address']==0xd400 and differences[0][0]['phase']=='init'
        cases.append(dict(name=name,address=address,before=before,after=value,
                          privateVariantSha256=digest(changed),matchedWrites=len(writes),
                          cpuAudit=audit,orderedWrites=writes))
    assert source.read_bytes() == original
    result = dict(schemaVersion=1,sourceSha256=SOURCE_SHA,callsPerCase=128,cases=cases,
                  modelSha256=digest((HERE/'model.py').read_bytes()),checkerSha256=digest(Path(__file__).read_bytes()),
                  tools=PINS,originalUnchanged=True,
                  limits='Separate in-memory source-data interventions; ordered phase/call/address/value equality, not instruction-cycle equality, synthesized audio, transfer composition or listening.')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=[dict(name=r['name'],matchedWrites=r['matchedWrites']) for r in cases],originalUnchanged=True)))


if __name__=='__main__':
    main()
