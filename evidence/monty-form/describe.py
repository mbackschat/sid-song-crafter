"""Retain bounded listing correspondence and compare two executed Monty order cycles."""

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_profile import psid_profile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    with (HERE / name).open('x') as output:
        json.dump(value, output, indent=2)
        output.write('\n')


data = (ROOT / '.local/monty-source.sid').read_bytes()
assert hashlib.sha256(data).hexdigest() == '528a7330817e4a0a0f75a505e9fe2444e07c5072ce5383ceaa89f183f0eee3ab'
parsed = psid_profile(data, profile='pal-banked', subtune=1)
listing = HERE / 'Hubbard_Rob_Monty_on_the_Run.asm'
assert sha(listing) == '52dbbf891b1a1d0f8750842ef91ebaf1fc62d65d7b46497ae6951576ece3ae6c'
text = listing.read_text()
frequency_block = text.split('\nnotefreqsl\n', 1)[1].split('\nregoffsets', 1)[0]
words = [int(value, 16) for line in frequency_block.splitlines() if line.lstrip().startswith('!wo')
         for value in re.findall(r'\$([0-9a-fA-F]{4})', line)]
frequency_bytes = b''.join(word.to_bytes(2, 'little') for word in words)
offset = 0x8400 - parsed['loadAddress']
assert parsed['payload'][offset:offset + len(frequency_bytes)] == frequency_bytes
instrument_block = text.split('\ninstr =*', 1)[1].split('\n}', 1)[0]
instrument_values = bytes(int(value, 16) for line in instrument_block.splitlines() if line.lstrip().startswith('!by')
                          for value in re.findall(r'\$([0-9a-fA-F]{2})', line.split(';')[0]))
offset = 0x93b4 - parsed['loadAddress']
archive_records = parsed['payload'][offset:offset + len(instrument_values)]
assert all(instrument_values[i + 2:i + 8] == archive_records[i + 2:i + 8] for i in range(0, len(instrument_values), 8))
observed_path = HERE / 'full40000/observations.json.gz'
ledger_path = HERE / 'full40000/audit.writes.json.gz'
observed = json.load(gzip.open(observed_path, 'rt'))
write('navigation.json', dict(schemaVersion=1, sourceSha256=hashlib.sha256(data).hexdigest(),
    sourceAsset='monty-on-the-run', sourcePath='.local/monty-source.sid',
    sourceURL='https://www.hvsc.de/download/C64Music/MUSICIANS/H/Hubbard_Rob/Monty_on_the_Run.sid',
    listingSha256=sha(listing), listingGitBlobSha1='332b81b5ddd21d1ab20c7cd37c32ac786760a267',
    listingURL='https://raw.githubusercontent.com/realdmx/c64_6581_sid_players/f215174fc4c983674808fcd47bc506f96b3d2d04/Hubbard_Rob/Hubbard_Rob_Monty_on_the_Run.asm',
    listingPrivateCachePath='build/monty-form/Hubbard_Rob_Monty_on_the_Run.asm',
    listingAttribution='Original disassembly/commenting Anthony McSweeney; ACME port dmx87',
    toolHashes=observed['provenance']['tools'], probeSha256=observed['provenance']['probeSha256'],
    titleOrders=observed['staticTitleOrderMatches'],
    frequency=dict(address=0x8400, declaredWords=len(words), bytes=len(frequency_bytes), sha256=hashlib.sha256(frequency_bytes).hexdigest(),
        limit='Executed raw note104 on voice1 call0 doubles to byte-offset208, reading voiceControl state at84D0/84D1 beyond the declared96-word table; do not infer a chromatic extension.'),
    instruments=dict(address=0x93b4, records=len(instrument_values) // 8, fields2Through7Match=True,
        pulseFieldsDifferInitially=[i // 8 for i in range(0, len(instrument_values), 8) if instrument_values[i:i + 2] != archive_records[i:i + 2]],
        executedMutablePulseFieldStorePCs=[0x8287, 0x828e],
        limit='Pulse bytes are shared mutable instrument data. No whole-player or initialized-sound equivalence follows from the remaining field matches.'),
    hooks=observed['hooks'], stateArrays={'orderCursor': 0x84c4, 'patternCursor': 0x84c7, 'remaining': 0x84ca,
        'savedControl': 0x84cd, 'voiceControl': 0x84d0, 'note': 0x84d3, 'instrument': 0x84d6, 'portamento': 0x84f5},
    tempo={'countdown': 0x84eb, 'reload': 0x84ec, 'openingReload': 1}, outerReturnPC=0x838c,
    boundedValidation={'calls': 512, 'rowConsumptions': 24, 'appendBranches': 7,
        'firstPatternAdvanceCallByVoice': [448, 448, 448], 'orderRestarts': 0},
    limits='Archive PCs are observed or statically identified, not listing offsets. Listing forces one song and removes/omits the archive SFX tail838D..83FD; SFX behavior is unstudied. FE early exit is static and not executed in40000 titlecalls. No complete payload/RAM/source listing is exported.',
    checkerSha256=sha(Path(__file__))))

period = 17536
assert observed['summary']['jointOrderRestartCalls'] == [period, 2 * period]


def event_stream(start, kinds, drop_initial_terminal=False):
    result = []
    for row in observed['events']:
        if start <= row['call'] < start + period and row['kind'] in kinds:
            if drop_initial_terminal and row['kind'] == 'orderRead' and row['call'] == start and row['value'] == 255:
                continue
            result.append((row['call'] - start, row['kind'], row['pc'], row['x'], row.get('sourceAddress'), row.get('value'), row.get('instrumentIndex')))
    return result


raw_first = event_stream(0, {'orderRead'})
raw_second = event_stream(period, {'orderRead'})
normalized = event_stream(period, {'orderRead'}, True)
removed = [row for row in observed['events'] if row['call'] == period and row['kind'] == 'orderRead' and row['value'] == 255]
assert len(removed) == 3 and {row['x'] for row in removed} == {0, 1, 2}
kinds = {'patternPointerLow', 'patternPointerHigh', 'rowControlRead', 'instrumentOrPortamentoRead', 'pitchRead', 'patternEndPeek', 'initializerInstrument'}
first, second = event_stream(0, kinds), event_stream(period, kinds)
ledger = json.load(gzip.open(ledger_path, 'rt'))
banks = [dict() for _ in range(2)]
for row in ledger:
    if row['phase'] == 'play' and 0 <= row['tick'] < 2 * period:
        bank, tick = divmod(row['tick'], period)
        banks[bank].setdefault(tick, []).append(row)
shape_differences, value_difference_addresses, timing_only = [], Counter(), 0
for tick in range(period):
    left, right = banks[0][tick], banks[1][tick]
    if [row['address'] for row in left] != [row['address'] for row in right]:
        shape_differences.append(tick)
        continue
    for a, b in zip(left, right):
        if a['value'] != b['value']:
            value_difference_addresses[f"{a['address']:04x}"] += 1
        elif a['instructionStartCycle'] != b['instructionStartCycle']:
            timing_only += 1
write('traversal-comparison.json', dict(schemaVersion=1, sourceSha256=observed['provenance']['sourceSha256'],
    inputs={str(path.relative_to(HERE)): sha(path) for path in (observed_path, ledger_path)},
    firstCallsInclusive=[0, period - 1], secondCallsInclusive=[period, 2 * period - 1],
    rawOrderReadComparisonEqual=raw_first == raw_second,
    excludedSecondInitialTerminalReads=[{'call': row['call'], 'voice': row['x'], 'pc': row['pc'], 'address': row['sourceAddress'], 'value': row['value']} for row in removed],
    orderReadComparisonAfterExactlyThreeExclusions=raw_first == normalized,
    comparedPatternFields=['relativeCall', 'kind', 'pc', 'voiceIndex', 'sourceAddress', 'value', 'instrumentIndex'],
    patternConsumptionEqual=first == second, comparedPatternEventsPerTraversal=[len(first), len(second)],
    orderedSIDShapeMismatchCalls=shape_differences, comparedOrderedStoresPerTraversal=[sum(map(len, bank.values())) for bank in banks],
    valueDifferenceAddressesOnMatchingShapeCalls=dict(value_difference_addresses), timingOnlyDifferingPairsOnMatchingShapeCalls=timing_only,
    selectedFullStateFingerprintsEqual=len({row['stateSha256'] for row in observed['boundaryCheckpoints']
        if row['call'] in (0, period, 2 * period)}) == 1,
    limits='Pattern equality excludes CPU registers/state, instruction cycles and mutable instrument record values. SID values/timing are compared only when the full per-call address lists agree; mismatching-shape calls are never zipped. No physical SID/audio recurrence or musical judgment follows.',
    checkerSha256=sha(Path(__file__))))
print(json.dumps({'rawOrderEqual': raw_first == raw_second, 'normalizedOrderEqual': raw_first == normalized,
                  'patternEqual': first == second, 'shapeMismatchCalls': len(shape_differences),
                  'valueDifferenceAddressesOnMatchingShapes': dict(value_difference_addresses)}))
