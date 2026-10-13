"""Compare compact hook observations with the independently retained 512-call trace."""

import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
trace_path = ROOT / 'boundary.trace.json.gz'
observations_path = ROOT / 'hook-check512-final/observations.json.gz'
ledger_path = ROOT / 'hook-check512-final/audit.writes.json.gz'
trace = json.load(gzip.open(trace_path, 'rt'))
observed = json.load(gzip.open(observations_path, 'rt'))
pcs = {int(pc, 16) for pc in observed['hooks']}
expected = [row for row in trace['instructions'] if row['pc'] in pcs]
actual = observed['events']
assert len(expected) == len(actual)
for left, right in zip(expected, actual):
    assert (left['tick'], left['pc'], left['instructionStartCycle'], left['a'], left['x'], left['y'], left['status'], left['sp'], left['bytes']) == (
        right['call'], right['pc'], right['instructionStartCycle'], right['a'], right['x'], right['y'], right['status'], right['sp'], right['instructionBytes'])
    if 'sourceAddress' in right:
        assert (left['operandAddress'], left['operandValueBefore']) == (right['sourceAddress'], right['value'])
ledger = json.load(gzip.open(ledger_path, 'rt'))
assert [dict((key, value) for key, value in row.items() if key != 'instructionPc') for row in trace['sidWrites']] == [row for row in ledger if row['phase'] == 'play']
assert trace['initSidWrites'] == [row for row in ledger if row['phase'] == 'init']
receipt = dict(passed=True, calls=512, matchedHookEvents=len(actual), matchedOrderedStores=len(ledger),
    sourceSha256=trace['sourceSha256'], probeSha256=observed['provenance']['probeSha256'],
    inputs={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in
            (trace_path, observations_path, ledger_path)},
    checkerSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    limits='Hook fidelity and ordered ledger equality only; shared CPU execution is not an independent machine or audio oracle.')
with (ROOT / 'hook-validation.json').open('x') as output:
    json.dump(receipt, output, indent=2)
    output.write('\n')
print(json.dumps(receipt))
