#!/usr/bin/env python3
"""Census ordered CPU stores from a completed Deflektor/Trap source intake."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def marker(row):
    return {key: row[key] for key in ('phase', 'tick', 'instructionStartCycle')}


def voice_state(registers, voice):
    base = 0xd400 + voice * 7
    low, high = registers.get(base), registers.get(base + 1)
    return dict(voice=voice + 1, control=registers.get(base + 4),
                frequencyWord=None if low is None or high is None else low | high << 8)


def census(writes):
    registers = {}
    controls = [Counter() for _ in range(3)]
    transitions = [[] for _ in range(3)]
    rises = [[] for _ in range(3)]
    first_controls = [None] * 3
    filter_values = {address: set() for address in range(0xd415, 0xd419)}
    active_intervals = []
    active_key = None
    for row in writes:
        address, value = row['address'], row['value']
        if row['phase'] not in ('init', 'play') or not 0 <= value <= 255:
            raise ValueError('Expected ordered CPU init/play stores with byte values')
        previous = registers.get(address)
        registers[address] = value
        if address in (0xd404, 0xd40b, 0xd412):
            voice = (address - 0xd404) // 7
            controls[voice][value] += 1
            if first_controls[voice] is None:
                first_controls[voice] = dict(marker(row), value=value)
            if previous is not None and previous != value:
                transitions[voice].append(dict(marker(row), previous=previous, value=value))
                if row['phase'] == 'play' and not previous & 1 and value & 1:
                    rises[voice].append(dict(marker(row), previous=previous, value=value))
        if address in filter_values:
            filter_values[address].add(value)
        if address in (0xd417, 0xd418):
            routing, mode = registers.get(0xd417), registers.get(0xd418)
            key = None
            if routing is not None and mode is not None and routing & 7 and mode & 0x70:
                key = (routing & 7, mode & 0x70)
            if key != active_key:
                if active_key is not None:
                    active_intervals[-1]['end'] = marker(row)
                if key is not None:
                    active_intervals.append(dict(start=marker(row), end=None,
                                                 routing=key[0], modes=key[1],
                                                 routedVoicesAtStart=[voice_state(registers, voice)
                                                     for voice in range(3) if key[0] & (1 << voice)],
                                                 routedControlTransitions=[], cutoffTransitions=[]))
                active_key = key
        if active_key is not None and previous is not None and previous != value:
            if address in (0xd404, 0xd40b, 0xd412):
                voice = (address - 0xd404) // 7
                if active_key[0] & (1 << voice):
                    active_intervals[-1]['routedControlTransitions'].append(
                        dict(marker(row), previous=previous, **voice_state(registers, voice)))
            elif address in (0xd415, 0xd416):
                active_intervals[-1]['cutoffTransitions'].append(dict(marker(row), address=address,
                                                                    previous=previous, value=value))
    rise_calls = [{row['tick'] for row in voice} for voice in rises]
    pairs = []
    for left, right in ((0, 1), (0, 2), (1, 2)):
        pairs.append(dict(voices=[left + 1, right + 1],
                          sharedCalls=sorted(rise_calls[left] & rise_calls[right]),
                          leftOnlyCalls=sorted(rise_calls[left] - rise_calls[right]),
                          rightOnlyCalls=sorted(rise_calls[right] - rise_calls[left])))
    return dict(
        voices=[dict(voice=voice + 1, controlWriteCounts=dict(sorted(controls[voice].items())),
                     firstControl=first_controls[voice], controlTransitions=transitions[voice],
                     gateRises=rises[voice]) for voice in range(3)],
        filterRegisterValues={f'{address:04x}': sorted(values) for address, values in filter_values.items()},
        activeFilterIntervals=active_intervals,
        gateRisePairs=pairs,
        limits='Ordered software stores only. Unwritten registers remain unknown; gate rises are not a decoded note score. Pairwise articulation timing does not prove musical-role independence, oscillator phases, original-game cadence, acoustic quality or listening acceptance.')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify_trace(trace, source_hash, writes):
    if trace['sourceSha256'] != source_hash:
        raise ValueError('Trace and intake source fingerprints disagree')
    fields = ('phase', 'tick', 'instructionStartCycle', 'address', 'value')
    expected = [{key: row[key] for key in fields} for row in writes
                if row['phase'] == 'play' and trace['firstCall'] <= row['tick'] <= trace['lastCallInclusive']]
    observed = [{key: row[key] for key in fields} for row in trace['sidWrites']]
    if expected != observed:
        raise ValueError('Instruction-trace stores differ from the intake ledger')
    return dict(firstCall=trace['firstCall'], lastCallInclusive=trace['lastCallInclusive'],
                matchingStores=len(expected))


def probe(run_path, trace_paths=()):
    run_data = run_path.read_bytes()
    run = json.loads(run_data)
    if run.get('schemaVersion') != 1 or run.get('status') != 'completed':
        raise ValueError('Expected a completed version 1 reference-intake run')
    artifacts = {row['path']: row for row in run['artifacts']}

    def verified(deliverable=None, stage=None):
        path = (run['deliverables'][deliverable] if deliverable else
                next(row['path'] for row in run['artifacts'] if row['stageId'] == stage))
        data = Path(path).read_bytes()
        expected = artifacts[path]['sha256']
        if digest(data) != expected:
            raise ValueError(f'Changed intake artifact: {path}')
        return json.loads(data), dict(path=str(Path(path).relative_to(ROOT)), sha256=expected)

    selections = []
    trace_verifications = []
    for label in ('sourceA', 'sourceB'):
        selected, selection_input = verified(stage=label + '-selection')
        audited, audit_input = verified(label + 'CpuAudit')
        writes, writes_input = verified(label + 'OrderedStores')
        source_hash = selected['source']['sha256']
        if audited['sourceSha256'] != source_hash:
            raise ValueError('Selection and CPU source fingerprints disagree')
        for trace_path in trace_paths:
            trace_data = trace_path.read_bytes()
            trace = json.loads(trace_data)
            if trace['sourceSha256'] == source_hash:
                trace_verifications.append(dict(path=str(trace_path.relative_to(ROOT)),
                                                sha256=digest(trace_data), label=label,
                                                **verify_trace(trace, source_hash, writes)))
        selections.append(dict(label=label, sourceSha256=source_hash,
                               selectedSubtune=audited['selectedSubtune'],
                               calls=audited['playCalls'], callRateHz=audited['callRateHz'],
                               ledgerSeconds=audited['playCalls'] / audited['callRateHz'],
                               inputs=dict(selection=selection_input, audit=audit_input, writes=writes_input),
                               census=census(writes)))
    if len(trace_verifications) != len(trace_paths):
        raise ValueError('Every trace must match exactly one selected source')
    return dict(schemaVersion=1, run=dict(path=str(run_path.relative_to(ROOT)), sha256=digest(run_data)),
                probeSha256=digest(Path(__file__).read_bytes()), selections=selections,
                traceVerifications=trace_verifications,
                listeningReview=None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--trace', type=Path, action='append', default=[])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'build'):
        raise ValueError('Output must remain below ignored build/')
    report = probe(args.run.resolve(), tuple(path.resolve() for path in args.trace))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        stream.write(json.dumps(report, indent=2) + '\n')
    print(output.relative_to(ROOT))


if __name__ == '__main__':
    main()
