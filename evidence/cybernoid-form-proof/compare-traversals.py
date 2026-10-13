"""Compare the two recorded Cybernoid II title-order traversals from analysis JSON only."""

import argparse
from collections import Counter
import difflib
import gzip
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, separators=(',', ':')) + '\n').encode()


def compare_sequences(first, second, fields):
    result = dict(fields=fields, firstCount=len(first), secondCount=len(second), equal=first == second,
                  firstSha256=sha(encoded(first)), secondSha256=sha(encoded(second)))
    for index in range(max(len(first), len(second))):
        a = first[index] if index < len(first) else None
        b = second[index] if index < len(second) else None
        if a != b:
            result['firstDifference'] = dict(index=index, first=a, second=b)
            break
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists() and not args.output.is_symlink(), 'Choose a fresh output file'
    receipt = json.loads((args.input / 'receipt.json').read_text())
    entry = next(row for row in json.loads(Path('config/local-assets.json').read_text())['references'] if row['id'] == 'cybernoid-ii')
    assert receipt['sourceSha256'] == entry['sha256'] and receipt['profile'] == 'pal-banked' and receipt['selectedSubtune'] == 1
    inputs = {}

    def load(name):
        path = args.input / name
        if not path.exists():
            path = path.with_suffix(path.suffix + '.gz')
        stored = path.read_bytes()
        raw = gzip.decompress(stored) if path.suffix == '.gz' else stored
        assert sha(raw) == receipt['artifacts'][name]['sha256'], f'Changed input {name}'
        inputs[name] = dict(path=str(path), storedSha256=sha(stored), decodedSha256=sha(raw))
        return json.loads(raw)

    events, states, writes = load('events.json'), load('call-state.json'), load('audit.writes.json')
    period = 17280
    assert [row['call'] for row in states[:2 * period]] == list(range(2 * period)), 'Incomplete traversal coverage'
    selected = lambda kind, start: [(index, row) for index, row in enumerate(events) if row['kind'] == kind and start <= row['call'] < start + period]
    fields = {'orderByte': ['relativeCall', 'voiceIndex', 'sourceAddress', 'sourceValue'],
              'patternPointer': ['relativeCall', 'voiceIndex', 'patternId', 'patternPointer'],
              'pointerRead': ['relativeCall', 'voiceIndex', 'pc', 'context', 'sourceAddress', 'sourceValue']}
    comparisons = {}
    for kind, names in fields.items():
        project = lambda rows, start: [[row['call'] - start] + [row[name] for name in names[1:]] for _, row in rows]
        first, second = selected(kind, 0), selected(kind, period)
        comparisons[kind] = compare_sequences(project(first, 0), project(second, period), names)
        if kind == 'orderByte':
            removed = [(index, row) for index, row in second if row['call'] == period and row['sourceValue'] == 255]
            assert len(removed) == 3 and {row['voiceIndex'] for _, row in removed} == {0, 1, 2}
            indices = {index for index, _ in removed}
            wraps = [row for row in events if row['kind'] == 'orderWrap' and row['call'] == period]
            assert len(wraps) == 3 and {row['causedByEventIndex'] for row in wraps} == indices
            adjusted = [(index, row) for index, row in second if index not in indices]
            comparison = compare_sequences(project(first, 0), project(adjusted, period), names)
            comparison.update(rule='Remove only the three second-traversal initial order FF reads linked to executed orderWrap paths; preserve the raw comparison separately.',
                              removedRecords=[dict(eventIndex=index, event=row) for index, row in removed])
            comparisons['orderByteWithoutInitialTerminalFF'] = comparison

    groups = [[] for _ in range(2 * period)]
    for row in writes:
        if row['phase'] == 'play' and 0 <= row['tick'] < 2 * period:
            groups[row['tick']].append(row)
    length_calls, address_calls, value_calls, timing_calls, pure_timing_calls, both_calls = [], [], [], [], [], []
    value_rows, timing_rows = [], []
    value_registers, timing_registers, categories = Counter(), Counter(), Counter()
    for call in range(period):
        a, b = groups[call], groups[call + period]
        if len(a) != len(b):
            length_calls.append(call)
        if [row['address'] for row in a] != [row['address'] for row in b]:
            address_calls.append(call)
            continue
        value_changed, timing_changed = False, False
        for index in range(len(a)):
            first, second = a[index], b[index]
            value = first['value'] != second['value']
            timing = first['instructionStartCycle'] != second['instructionStartCycle']
            if value:
                value_changed = True
                value_rows.append([call, index, first['address'], first['value'], second['value']])
                value_registers[f'{first["address"]:04x}'] += 1
            if timing:
                timing_changed = True
                timing_rows.append([call, index, first['address'], first['instructionStartCycle'], second['instructionStartCycle'], first['value'], second['value']])
                timing_registers[f'{first["address"]:04x}'] += 1
            if value or timing:
                categories['valueAndTiming' if value and timing else 'valueOnly' if value else 'timingOnly'] += 1
        if value_changed:
            value_calls.append(call)
        if timing_changed:
            timing_calls.append(call)
        if timing_changed and not value_changed:
            pure_timing_calls.append(call)
        if timing_changed and value_changed:
            both_calls.append(call)

    proof = Path(__file__).with_name('analyze-cybernoid.py')
    proof_raw = proof.read_bytes()
    current = Path('scripts/analyze-cybernoid.py').read_bytes()
    diff = list(difflib.unified_diff(proof_raw.decode().splitlines(), current.decode().splitlines(), fromfile=str(proof), tofile='scripts/analyze-cybernoid.py', lineterm=''))
    changes = [line for line in diff if line[:1] in ('+', '-') and not line.startswith(('+++', '---'))]
    assert sha(proof_raw) == receipt['toolSha256']
    assert changes and all(line[1:].lstrip().startswith('#') for line in changes), 'Observer changed beyond comments'
    structural = not length_calls and not address_calls
    frequencies = {'d400', 'd401', 'd407', 'd408', 'd40e', 'd40f'}
    result = dict(schemaVersion=2, classification='Field-scoped comparison of two recorded title-order traversals',
                  sourceSha256=receipt['sourceSha256'], profile=receipt['profile'], selectedSubtune=1,
                  periodCalls=period, firstTraversal=[0, period - 1], secondTraversal=[period, 2 * period - 1],
                  inputs=inputs, projectionHashRecipe='SHA256((json.dumps(projected_records,separators=(",",":"))+"\\n").encode())',
                  consumptionComparisons=comparisons,
                  sidComparison=dict(firstWriteCount=sum(len(rows) for rows in groups[:period]), secondWriteCount=sum(len(rows) for rows in groups[period:]),
                                     allCallLengthsEqual=not length_calls, callLengthDifferenceCalls=length_calls,
                                     allPerCallAddressOrdersEqual=not address_calls, addressOrderDifferenceCalls=address_calls,
                                     alignedCallCount=period - len(address_calls), valueDifferenceCallCount=len(value_calls), valueDifferenceCalls=value_calls,
                                     timingDifferenceCallCount=len(timing_calls), timingDifferenceCalls=timing_calls,
                                     timingOnlyCallCount=len(pure_timing_calls), timingOnlyCalls=pure_timing_calls,
                                     bothValueAndTimingCallCount=len(both_calls), bothValueAndTimingCalls=both_calls,
                                     writeDifferenceCategories=dict(categories), valueDifferencesByRegister=dict(sorted(value_registers.items())),
                                     timingDifferencesByRegister=dict(sorted(timing_registers.items())),
                                     valueDifferencesConfinedToFrequency=structural and bool(value_rows) and set(value_registers) <= frequencies,
                                     valueDifferenceFields=['relativeCall', 'writeIndex', 'address', 'firstValue', 'secondValue'],
                                     valueDifferenceRows=value_rows, valueDifferenceRowsSha256=sha(encoded(value_rows)),
                                     timingDifferenceFields=['relativeCall', 'writeIndex', 'address', 'firstCycle', 'secondCycle', 'firstValue', 'secondValue'],
                                     timingDifferenceRowCount=len(timing_rows), timingDifferenceRowsSha256=sha(encoded(timing_rows)),
                                     firstTimingDifferences=timing_rows[:8]),
                  pairedRamHashEqualCalls=[call for call in range(period) if states[call]['ramSha256'] == states[call + period]['ramSha256']],
                  pairedMachineStateEqualCalls=[call for call in range(period) if states[call]['machineStateSha256'] == states[call + period]['machineStateSha256']],
                  observerProof=dict(path=str(proof), sha256=sha(proof_raw), matchesRecordedRunTool=True,
                                     currentPath='scripts/analyze-cybernoid.py', currentSha256=sha(current), currentChangesAreCommentsOnly=True, diff=diff),
                  comparisonScript=dict(path=str(Path(__file__)), sha256=sha(Path(__file__).read_bytes())),
                  limits='Pattern comparisons cover only the listed fields: instruction timing, CPU registers, ownership-event IDs and synthesis state are excluded. Raw order comparison remains false. Boundary FF removal is explicit and affects no other events. SID values are compared only after complete per-call count/address-order checks; value differences and timing-only differences are distinct. Timing means instruction-start cycles, not SID bus cycles. No RAM/CPU, SID-state, PCM, original-host or musical equivalence claim.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as file:
        file.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(output=str(args.output), rawOrderEqual=comparisons['orderByte']['equal'], adjustedOrderEqual=comparisons['orderByteWithoutInitialTerminalFF']['equal'],
                          allCallLengthsEqual=not length_calls, allAddressOrdersEqual=not address_calls, valueDifferenceCalls=len(value_calls), timingDifferenceCalls=len(timing_calls),
                          timingOnlyCalls=len(pure_timing_calls), bothValueAndTimingCalls=len(both_calls), writeCategories=dict(categories), valueRegisters=dict(value_registers)), indent=2))


if __name__ == '__main__':
    main()
