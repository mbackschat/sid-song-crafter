"""Check stream-control transitions and retain the bounded Ghouls form proof."""

from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
from probe import COMMANDS, ROOT, SOURCE_SHA, TABLE_BASES, psid_profile, source

HERE = Path(__file__).resolve().parent
RUN = HERE / 'full40000'
observed_path = RUN / 'observations.json.gz'
writes_path = RUN / 'audit.writes.json.gz'
observed = json.load(gzip.open(observed_path, 'rt'))
writes = json.load(gzip.open(writes_path, 'rt'))
summary = json.loads((RUN / 'summary.json').read_text())
report = json.loads((RUN / 'audit.json').read_text())
run_receipt = json.loads((RUN / 'receipt.json').read_text())
data, entry = source()
profile = psid_profile(data, profile='pal-banked', subtune=1)
assert run_receipt['scriptSha256'] == hashlib.sha256((HERE / 'probe.py').read_bytes()).hexdigest()
assert report['playCalls'] == len(observed['bodies']) == 40000
assert report['sourceSha256'] == SOURCE_SHA and run_receipt['sourceBytesUnchanged']


def source_byte(address):
    assert profile['loadAddress'] <= address < profile['endAddress']
    return profile['payload'][address - profile['loadAddress']]


def original_address(address):
    copies = [row for row in observed['initializationCopies'] if row['destination'] <= address < row['destination'] + row['bytes']]
    assert len(copies) == 1
    return copies[0]['source'] + address - copies[0]['destination']


reads = [row for row in observed['events'] if row['kind'] != 'commandDispatch']
read_map = {}
for row in reads:
    origin = original_address(row['address'])
    assert row['value'] == source_byte(origin)
    read_map[row['address']] = (origin, row['value'])
map_bytes = (json.dumps(sorted((address, origin, value) for address, (origin, value) in read_map.items()), separators=(',', ':')) + '\n').encode()
dispatches = [[row for row in observed['events'] if row['kind'] == 'dispatchRead' and row['voice'] == voice] for voice in range(3)]
commands = [row for row in observed['events'] if row['kind'] == 'commandDispatch']
command_by_read = {(row['call'], row['voice'], row['consumedAddress']): row for row in commands}
control_counts = Counter()
examples = []
for voice, stream in enumerate(dispatches):
    stack, repeat_pointer = [], None
    for index, row in enumerate(stream):
        if row['value'] < 128:
            continue
        command = command_by_read[(row['call'], voice, row['address'])]
        low, high = TABLE_BASES[voice]
        assert command['targetPC'] == (source_byte(low + row['value']) | source_byte(high + row['value']) << 8)
        code = row['value']
        if code not in (0x81, 0x82, 0x86, 0x87, 0x8a, 0x8b):
            continue
        next_row = stream[index + 1] if index + 1 < len(stream) else None
        target, next_depth, next_repeat = None, row['callDepth'], row['repeatRemaining']
        if code == 0x82:
            next_repeat = source_byte(original_address(row['address'] + 1))
            repeat_pointer = target = (row['address'] + 2) & 65535
        elif code == 0x81:
            next_repeat = (row['repeatRemaining'] - 1) & 255
            target = repeat_pointer if next_repeat else (row['address'] + 1) & 65535
            assert target is not None
        elif code in (0x87, 0x8a):
            target = source_byte(original_address(row['address'] + 1)) | source_byte(original_address(row['address'] + 2)) << 8
            if code == 0x8a:
                stack.append((row['address'] + 3) & 65535)
                next_depth += 1
        elif code == 0x8b:
            target = stack.pop()
            next_depth -= 1
        else:
            assert next_row is None and row['callDepth'] == 0
        if code != 0x86:
            assert next_row['address'] == target and next_row['callDepth'] == next_depth
            assert next_row['repeatRemaining'] == next_repeat
            assert next_row['call'] == row['call']
        control_counts[(voice, code)] += 1
        if len(examples) < 20 or code == 0x86:
            examples.append(dict(voice=voice, call=row['call'], code=code, consumedAddress=row['address'],
                sourceAddress=original_address(row['address']), targetPC=command['targetPC'],
                nextStreamAddress=target, nextCallDepth=next_depth, nextRepeatRemaining=next_repeat))
    assert not stack

stop = summary['firstAllInactiveCall']
assert stop == 12995
assert summary['enableFlagChanges'] == [
    dict(call=12947, before=[255, 255, 255], after=[0, 255, 255]),
    dict(call=12971, before=[0, 255, 255], after=[0, 255, 0]),
    dict(call=12995, before=[0, 255, 0], after=[0, 0, 0])]
assert not any(row['call'] > stop for row in observed['events'])
assert all(row == dict(observed['bodies'][stop], call=row['call']) for row in observed['bodies'][stop:])
post = [row for row in writes if row['phase'] == 'play' and row['tick'] > stop]
groups = defaultdict(list)
for row in post:
    groups[row['tick']].append((row['address'], row['value']))
assert sorted(groups) == list(range(stop + 1, 40000))
assert all(rows == [(0xd415, 0), (0xd416, 0)] for rows in groups.values())
last = observed['fingerprints'][-1]
terminal = next(row for row in observed['fingerprints'] if row['call'] == stop)
assert terminal['ramSha256'] == last['ramSha256'] and terminal['ramCpuSha256'] == last['ramCpuSha256']
assert terminal['cpu'] == last['cpu']

prefix = json.load(gzip.open(HERE / 'opening256/audit.writes.json.gz', 'rt'))
project = lambda rows: [(row['phase'], row['tick'], row['address'], row['value'], row['instructionStartCycle']) for row in rows]
assert project(prefix) == project([row for row in writes if row['phase'] == 'init' or row['tick'] < 256])
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
inputs = {str(path.relative_to(ROOT)): sha(path) for path in (observed_path, writes_path, RUN / 'audit.json', RUN / 'receipt.json', HERE / 'opening256/audit.writes.json.gz')}
form = dict(passed=True, sourceSha256=SOURCE_SHA, sourceURL=entry['url'], selectedSubtune=1, musicalRole='provisional',
    processedCalls=40000, initializationCopies=observed['initializationCopies'], initialState=observed['initialState'],
    outerReturn=dict(pc=0x6857, sp=0xfd, savedReturnWord=report['playReturnAddress'] - 1, hostBase=report['hostBase']),
    readProof=dict(totalReads=len(reads), distinctConsumedAddresses=len(read_map), allMatchInitializedSourceCopies=True,
        mapHashRecipe='UTF8 compact JSON sorted triples(consumed RAM address, original archive RAM address, byte value), newline',
        mapSha256=hashlib.sha256(map_bytes).hexdigest()),
    controlTransitionCounts=[dict(voice=voice, code=code, name=COMMANDS[code], visits=count) for (voice, code), count in sorted(control_counts.items())],
    examples=examples, maximumObservedCallDepth=max(max(row['callDepth']) for row in observed['bodies']),
    endChronology=[dict(row, originalSourceAddress=original_address(row['consumedAddress'])) for row in summary['disableCommands']],
    firstAllInactiveCall=stop, noStreamEventsAfterStop=True, allRemainingNamedScoreStatesUnchanged=True,
    postStop=dict(firstCall=stop + 1, lastCall=39999, calls=len(groups), stores=len(post), orderedPerCall=[[0xd415, 0], [0xd416, 0]]),
    sampledStateEquality=dict(calls=[stop, 39999], ramSha256=terminal['ramSha256'], ramCpuSha256=terminal['ramCpuSha256'],
        cpu=terminal['cpu'], scope='Equal sampled complete backing-RAM+CPU state; not a one-call fixed-point test or SID/audio recurrence'),
    originalOpeningPrefixStoresMatched=len(prefix), initStores=report['initWriteCount'], playStores=report['playWriteCount'],
    maximumPlayCycles=report['maximumPlayCycles'], inputHashes=inputs, checkerSha256=sha(Path(__file__)),
    limits='Observed finite stream traversal under the controlled callable host. Positive command names describe static native state writes; not a complete independent note/instrument decoder. No original-host, bus-cycle, SID-internal, acoustic-ending or listening claim.')
with (HERE / 'form.json').open('x') as output:
    json.dump(form, output, indent=2)
    output.write('\n')

first, last_call = 12989, 13002
selected = [row for row in writes if row['phase'] == 'init' or first <= row['tick'] <= last_call]
destination = HERE / 'vice-stop'
destination.mkdir()
raw = (json.dumps(selected, separators=(',', ':')) + '\n').encode()
with (destination / 'oracle.json').open('xb') as output:
    output.write(raw)
projection = dict(sourceSha256=SOURCE_SHA, selectedSubtune=1, profile='pal-banked', hostBase=0xc000,
    firstCall=first, lastCallInclusive=last_call, inputSha256=sha(writes_path),
    oracleSha256=hashlib.sha256(raw).hexdigest(), initStores=sum(row['phase'] == 'init' for row in selected),
    playStores=sum(row['phase'] == 'play' for row in selected), totalStores=len(selected),
    scriptSha256=sha(Path(__file__)), limits='All initialization stores plus selected stop-window playback; no other calls are part of the write comparison.')
with (destination / 'projection.json').open('x') as output:
    json.dump(projection, output, indent=2)
    output.write('\n')
print(json.dumps(dict(form=str(HERE / 'form.json'), reads=len(reads), controlTransitions=sum(control_counts.values()),
    stop=stop, postStopStores=len(post), projectionStores=len(selected))))
