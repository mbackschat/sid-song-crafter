"""Compare established banked references with their retained ordered ledgers."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid

cases = [
    ('ghouls', '.local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid', 'evidence/ghouls-sid-window/audit64.writes.json.gz'),
    ('monty', '.local/monty-source.sid', 'evidence/monty-intake/audit.writes.json.gz'),
    ('rambo', '.local/rambo-source.sid', 'evidence/rambo-intake/audit64.writes.json.gz'),
]
results = []
for name, source, oracle in cases:
    raw = (ROOT / source).read_bytes()
    stored = (ROOT / oracle).read_bytes()
    decoded = gzip.decompress(stored)
    expected = json.loads(decoded)
    report, actual = audit_psid(raw, 64, profile='pal-banked', subtune=1)
    assert actual == expected, name
    results.append(dict(name=name, source=source, sourceSha256=hashlib.sha256(raw).hexdigest(),
        oracle=oracle, oracleSha256=hashlib.sha256(stored).hexdigest(),
        decodedOracleSha256=hashlib.sha256(decoded).hexdigest(),
        matchedWrites=len(actual), playCalls=64, hostBase=report['hostBase'],
        initReturnAddress=report['initReturnAddress'], playReturnAddress=report['playReturnAddress']))
receipt = dict(schemaVersion=1, comparisons=results,
    scriptSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    tools={name: hashlib.sha256((ROOT / 'scripts' / name).read_bytes()).hexdigest()
           for name in ('psid_audit.py', 'psid_profile.py', 'sid_audit_host.py', 'verify_player.py')},
    scope='Exact bounded CPU-ledger equality, including phase, call, instruction-start cycle, address, value and order, after shared return-site correction. No new VICE, audio or full-form claim.')
with Path(__file__).with_name('regressions.json').open('x') as output:
    json.dump(receipt, output, indent=2)
    output.write('\n')
print(json.dumps(results, indent=2))
