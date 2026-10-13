"""Cross-check the compact observer against the independently retained opening trace."""

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
from probe import DISPATCH, DISPATCH_JUMPS, READ_RANGES, summarize

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
trace_path = HERE / 'opening.trace.json'
observed_path = HERE / 'opening256/observations.json.gz'
ledger_path = HERE / 'opening256/audit.writes.json.gz'
trace = json.loads(trace_path.read_text())
observed = json.load(gzip.open(observed_path, 'rt'))
ledger = json.load(gzip.open(ledger_path, 'rt'))
reads, commands, pending = [], [], {}
for row in trace['instructions']:
    pc = row['pc']
    encoded = bytes.fromhex(row['bytes'])
    if any(first <= pc < end for first, end in READ_RANGES) and encoded[0] == 0xb1 and encoded[1] in (0x21, 0x23, 0x25):
        voice = (encoded[1] - 0x21) // 2
        address = row['operandAddress']
        event = dict(kind='dispatchRead' if pc in DISPATCH else 'streamOperandRead', call=row['tick'],
            pc=pc, voice=voice, pointer=(address - row['y']) & 65535, y=row['y'], address=address,
            value=row['operandValueBefore'])
        reads.append(event)
        if pc in DISPATCH and event['value'] >= 128:
            pending[voice] = event
    if pc in DISPATCH_JUMPS:
        voice = DISPATCH_JUMPS[pc]
        event = pending.pop(voice)
        commands.append(dict(kind='commandDispatch', call=row['tick'], pc=pc, voice=voice,
            command=event['value'], consumedAddress=event['address'], targetPC=int.from_bytes(encoded[1:], 'little')))
actual_reads = [{key: row[key] for key in reads[0]} for row in observed['events'] if row['kind'] != 'commandDispatch']
actual_commands = [{key: row[key] for key in commands[0]} for row in observed['events'] if row['kind'] == 'commandDispatch']
assert reads == actual_reads and commands == actual_commands and not pending
project = lambda rows: [(row['phase'], row['tick'], row['address'], row['value'], row['instructionStartCycle']) for row in rows]
assert project(ledger) == project(trace['initSidWrites'] + trace['sidWrites'])
old_path = ROOT / 'evidence/ghouls-sid-window/audit64.writes.json.gz'
old = json.load(gzip.open(old_path, 'rt'))
assert project([row for row in ledger if row['phase'] == 'init' or row['tick'] < 64]) == project(old)
returns = [row for row in trace['instructions'] if row['pc'] == 0x6857 and row['sp'] == 0xfd]
assert [row['tick'] for row in returns] == list(range(256))

# The pure fixture locks partial deactivation and nested calls against a global-stop claim.
initial = dict(streamPointers=[100, 200, 300], enableFlags=[255, 255, 255])
fixture_events = [dict(kind='dispatchRead', call=0, voice=0, address=100, callDepth=0),
                  dict(kind='dispatchRead', call=1, voice=0, address=100, callDepth=1),
                  dict(kind='commandDispatch', call=1, voice=0, command=0x86)]
fixture_bodies = [dict(call=0, enableFlags=[255, 255, 255]), dict(call=1, enableFlags=[0, 255, 255]),
                  dict(call=2, enableFlags=[0, 0, 0]), dict(call=3, enableFlags=[0, 0, 0])]
fixture = summarize(fixture_events, fixture_bodies, [], initial)
assert fixture['firstAllInactiveCall'] == 2 and fixture['allInactiveCalls'] == 2
assert fixture['initialStreamDispatchCalls'][0] == [0]
assert len(fixture['enableFlagChanges']) == 2

sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
result = dict(passed=True, traceInstructions=len(trace['instructions']), streamReads=len(reads), commandDispatches=len(commands),
    outerReturns=len(returns), orderedInitPlayStores=len(ledger), historicalFirst64Stores=len(old),
    pureSummaryGuards=['Nested root-pointer read excluded', 'Partial voice disable is not global score stop',
                       'First all-inactive call and complete processed inactive span retained'],
    inputHashes={str(path.relative_to(ROOT)): sha(path) for path in (trace_path, observed_path, ledger_path, old_path)},
    checkerSha256=sha(Path(__file__)), limits='Matches observed hook/read fields and ordered stores, not an independently implemented score decoder or full machine-state reconstruction.')
with (HERE / 'opening-validation.json').open('x') as output:
    json.dump(result, output, indent=2)
    output.write('\n')
print(json.dumps(result))
