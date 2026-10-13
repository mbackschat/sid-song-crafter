from collections import Counter
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('coverage_probe', HERE / 'probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
trace_path = ROOT / 'evidence/cybernoid-title-instructions/opening.trace.json.gz'
decoded = gzip.decompress(trace_path.read_bytes())
assert hashlib.sha256(decoded).hexdigest() == 'a2ac87f2b73424a27145eaef9c3720786f78ee4d4e83b6f4642891068413753e'
trace = json.loads(decoded)
smoke = json.loads((HERE / 'smoke64.json').read_bytes())
assert smoke['scope']['lastCallInclusive'] == 63
expected = Counter()
records = [0, 0, 0]
voice = None
for row in trace['instructions']:
    if row['pc'] == 0xA728:
        voice = row['x']
    name = probe.HOOKS.get(row['pc'])
    if name is None:
        continue
    assert voice in range(3)
    if name == 'recordAssignment':
        records[voice] = row['a']
    expected[voice, records[voice], name] += 1
observed = Counter()
for group in smoke['records']:
    observed[group['voiceIndex'], group['recordIndex'], group['observation']] += group['visits']
for group in smoke['mechanisms']:
    observed[group['voiceIndex'], group['recordIndex'], group['mechanism']] += group['visits']
assert observed == expected, (observed - expected, expected - observed)
assert smoke['orderedWriteComparison']['recordCount'] == len(trace['sidWrites']) + len(trace['initSidWrites'])
result = dict(equal=True, hookVisits=sum(expected.values()),
              traceSha256=hashlib.sha256(decoded).hexdigest(),
              smokeSha256=hashlib.sha256((HERE / 'smoke64.json').read_bytes()).hexdigest(),
              checkToolSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              command='python3 build/cybernoid-title-mechanism-coverage/check-opening.py',
              basis='Independent consumption of retained instruction rows and reconstructed instrument assignments; grouped visit counts include all three voices.',
              counts=[dict(voiceIndex=voice, recordIndex=record, mechanism=name, visits=count)
                      for (voice, record, name), count in sorted(expected.items())])
with (HERE / 'opening-crosscheck.json').open('x') as target:
    json.dump(result, target, indent=2)
    target.write('\n')
print(json.dumps(dict(equal=True, hookVisits=sum(expected.values()), groups=len(expected))))
