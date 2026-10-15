"""Compare complete Rambo primary execution while the secondary calendar changes."""

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path


FIELDS = ('phase', 'tick', 'address', 'value')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def json_input(path):
    raw = Path(path).read_bytes()
    decoded = gzip.decompress(raw) if str(path).endswith('.gz') else raw
    return json.loads(decoded), dict(path=str(Path(path).resolve()), sha256=digest(raw), decodedSha256=digest(decoded))


def identity(rows, *, cycles=False):
    keys = FIELDS + ('instructionStartCycle',) if cycles else FIELDS
    return [tuple(row[key] for key in keys) for row in rows]


def bank(rows, base):
    return [row for row in rows if base <= row['address'] <= base + 31]


def sid_payload(value):
    require(len(value) >= 124 and value[:4] == b'PSID', 'Expected a PSID with a complete header')
    offset = int.from_bytes(value[6:8], 'big')
    load = int.from_bytes(value[8:10], 'big')
    require(124 <= offset < len(value) and load != 0, 'Expected explicit PSID load and payload addresses')
    return load, value[offset:]


def compare(reference_build, reference_writes, reference_study, reference_trace,
            candidate_build, candidate_writes, candidate_study, candidate_trace,
            candidate_sid, primary_reference):
    calls = reference_build['checkedPlayCalls']
    require(type(calls) is int and 1 <= calls <= 100000 and candidate_build['checkedPlayCalls'] == calls,
            'Timing comparison requires matching complete call ranges')
    for built in (reference_build, candidate_build):
        require(built['playCalls'] == calls and built['sidBases'] == [0xd400, 0xd420],
                'Timing comparison requires complete declared dual-SID execution')
    require(reference_build['compositions'][0]['sha256'] == candidate_build['compositions'][0]['sha256'],
            'Primary source descriptions differ')
    require(reference_build['symbols'] == candidate_build['symbols'], 'Wrapper entry layout differs')
    old_primary, new_primary = reference_build['players'][0], candidate_build['players'][0]
    for key in ('loadAddress', 'payloadBytes', 'symbols', 'nodeLabels'):
        require(old_primary[key] == new_primary[key], f'Primary {key} layout differs')
    load, payload = sid_payload(candidate_sid)
    reference_load, faithful_payload = sid_payload(primary_reference)
    start = new_primary['loadAddress'] - load
    require(start >= 0 and reference_load == new_primary['loadAddress']
            and len(faithful_payload) == new_primary['payloadBytes'], 'Primary reference payload layout differs')
    actual_primary = payload[start:start + new_primary['payloadBytes']]
    require(actual_primary == faithful_payload, 'Primary payload differs from the faithful reference')
    require(digest(candidate_sid) == candidate_build['sidSha256'], 'Candidate SID hash differs from its build receipt')
    primary = [bank(rows, 0xd400) for rows in (reference_writes, candidate_writes)]
    require(identity(primary[0]) == identity(primary[1]), 'Primary ordered stores differ')
    require(identity(primary[0], cycles=True) == identity(primary[1], cycles=True),
            'Primary relative CPU store timing differs')
    secondary = [bank(rows, 0xd420) for rows in (reference_writes, candidate_writes)]
    require(identity([row for row in secondary[0] if row['phase'] == 'init'], cycles=True)
            == identity([row for row in secondary[1] if row['phase'] == 'init'], cycles=True),
            'Secondary SID initialization differs')
    grouped = [{call: [] for call in range(calls)} for _ in range(2)]
    for target, rows in zip(grouped, secondary):
        for row in rows:
            if row['phase'] == 'play':
                target[row['tick']].append(row)
    first_secondary = next((call for call in range(calls)
                            if identity(grouped[0][call], cycles=True) != identity(grouped[1][call], cycles=True)), None)
    require(first_secondary is not None, 'The secondary comparison has no executed intervention')
    old_profile, new_profile = reference_study['profile'], candidate_study['profile']
    for key in ('loadAddress', 'initAddress', 'playAddress', 'sidModel', 'sidBases', 'entryBank', 'profile', 'hostBase'):
        require(old_profile[key] == new_profile[key], f'Controlled VICE host {key} differs')
    for key in ('harnessSha256', 'viceSha256', 'harnessLabels'):
        require(reference_study[key] == candidate_study[key], f'Controlled VICE {key} differs')
    entries, vice_primary = [], []
    cadence = []
    for built, writes, study, trace in zip((reference_build, candidate_build),
                                         (reference_writes, candidate_writes),
                                         (reference_study, candidate_study), (reference_trace, candidate_trace)):
        verification = study['verification']
        require(study['sourceSha256'] == built['sidSha256'], 'VICE source hash differs from its build receipt')
        require(study['clock'] == trace['clock'] == 'pal', 'Expected the same declared PAL clock')
        require(verification['playCalls'] == calls and verification['firstCall'] == 0
                and verification['lastCall'] == calls - 1 and verification['matchedWrites'] == len(writes),
                'VICE receipt does not cover the complete CPU stream')
        require(identity(trace['writes']) == identity(writes), 'VICE writes differ from their complete CPU oracle')
        require([row['tick'] for row in trace['entries']] == list(range(calls)), 'VICE entry coverage is incomplete')
        require(all(row['writerPc'] == built['symbols']['entry_play'] for row in trace['entries']),
                'VICE entries do not identify the supplied play routine')
        times = [row['monitorCycle'] for row in trace['entries']]
        budget, tolerance = verification['frameCycles'], verification['cadenceTolerance']
        require(budget == 19656, 'Expected the declared shared PAL frame budget')
        errors = [cycle - times[0] - index * budget for index, cycle in enumerate(times)]
        maximum = max(map(abs, errors), default=0)
        require(maximum <= verification['maximumCadenceError'] <= tolerance,
                'VICE entries exceed their verified cadence contract')
        cadence.append(dict(maximumMeasuredPhaseError=maximum, declaredTolerance=tolerance))
        entries.append(times)
        vice_primary.append(bank(trace['writes'], 0xd400))
    deltas = []
    for index, (old, new) in enumerate(zip(*vice_primary)):
        require(tuple(old[key] for key in FIELDS) == tuple(new[key] for key in FIELDS),
                'Primary VICE ordered stores differ')
        old_entry = reference_trace['initEntry']['monitorCycle'] if old['phase'] == 'init' else entries[0][old['tick']]
        new_entry = candidate_trace['initEntry']['monitorCycle'] if new['phase'] == 'init' else entries[1][new['tick']]
        old_offset, new_offset = old['monitorCycle'] - old_entry, new['monitorCycle'] - new_entry
        require(old_offset == new_offset, 'Primary VICE store offset from its own entry differs')
        deltas.append(dict(index=index, phase=old['phase'], tick=old['tick'], address=old['address'], value=old['value'],
                           referenceEntryOffset=old_offset, candidateEntryOffset=new_offset,
                           absoluteMonitorCycleDelta=new['monitorCycle'] - old['monitorCycle']))
    entry_deltas = [dict(tick=tick, referenceMonitorCycle=old, candidateMonitorCycle=new, delta=new - old)
                    for tick, (old, new) in enumerate(zip(*entries))]
    first_host = next((row['tick'] for row in entry_deltas if row['delta']), None)
    require(first_host is None or first_host > first_secondary,
            'Host entry phase differs before the secondary intervention can affect the next call')
    init_duration = [trace['initReturn']['monitorCycle'] - trace['initEntry']['monitorCycle']
                     for trace in (reference_trace, candidate_trace)]
    require(init_duration[0] == init_duration[1], 'Controlled VICE initialization duration differs')
    report = dict(
        schemaVersion=1, passed=True, playCalls=calls,
        candidateSidSha256=candidate_build['sidSha256'], referenceDualSidSha256=reference_build['sidSha256'],
        primaryPayloadMatchesReference=True, primaryOrderedStoresIdentical=True,
        primaryRelativeCpuTimingIdentical=True, primaryViceOffsetsIdentical=True,
        primaryPayloadSha256=digest(actual_primary), matchedPrimaryStores=len(primary[0]),
        matchedPrimaryPlayStores=sum(row['phase'] == 'play' for row in primary[0]),
        firstSecondaryDifferenceCall=first_secondary, firstHostEntryDifferenceCall=first_host,
        primaryLayout=dict(loadAddress=new_primary['loadAddress'], payloadBytes=new_primary['payloadBytes'],
                           initAddress=new_primary['symbols']['entry_init'], playAddress=new_primary['symbols']['entry_play']),
        secondaryLayout=[dict(loadAddress=built['players'][1]['loadAddress'], payloadBytes=built['players'][1]['payloadBytes'],
                              stateBegin=built['players'][1]['symbols']['rb_state_begin'],
                              initialState=built['players'][1]['symbols']['rb_initial_state'],
                              restore=built['players'][1]['symbols']['rb_restore_state'])
                         for built in (reference_build, candidate_build)],
        hostTiming=dict(entryCount=calls, minimumEntryDelta=min(row['delta'] for row in entry_deltas),
                        maximumEntryDelta=max(row['delta'] for row in entry_deltas),
                        entryDeltaCounts=dict(sorted(Counter(row['delta'] for row in entry_deltas).items())),
                        initializationCycles=init_duration, cadence=cadence),
        claims=dict(pcmIdentity=False, exactBusTiming=False, rendererScheduleProven=False),
        interpretation='The complete primary payload and logical/relative execution are unchanged. Changed secondary work can alter the instruction phase at the next host wait-loop exit. VICE monitor checkpoints demonstrate that host-entry phase mechanism in this controlled harness; they are not SID bus timestamps or a trace of the renderer host. Independent deterministic renders may therefore differ in primary PCM without a score/program regression.',
    )
    return report, dict(entries=entry_deltas, primaryStores=deltas)


def run(paths, output):
    output = Path(output)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh timing output directory')
    parsed, inputs = {}, {}
    for name, path in paths.items():
        if name in ('candidate_sid', 'primary_reference'):
            parsed[name] = Path(path).read_bytes()
            inputs[name] = dict(path=str(Path(path).resolve()), sha256=digest(parsed[name]))
        else:
            parsed[name], inputs[name] = json_input(path)
    for prefix in ('reference', 'candidate'):
        require(parsed[prefix + '_study']['oracleSha256'] == inputs[prefix + '_writes']['decodedSha256'],
                'VICE oracle hash differs from the supplied CPU writes')
    report, deltas = compare(**parsed)
    compressed = gzip.compress((json.dumps(deltas, separators=(',', ':'), allow_nan=False) + '\n').encode(), mtime=0)
    report['inputs'] = inputs
    report['toolSha256'] = digest(Path(__file__).read_bytes())
    report['deltas'] = dict(path='timing-deltas.json.gz', sha256=digest(compressed),
                            entryRecords=len(deltas['entries']), primaryStoreRecords=len(deltas['primaryStores']))
    output.mkdir(parents=True)
    (output / 'timing-deltas.json.gz').write_bytes(compressed)
    (output / 'timing-proof.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(f'Primary timing matches for {report["matchedPrimaryStores"]} stores; host entry deltas '
          f'{report["hostTiming"]["minimumEntryDelta"]}..{report["hostTiming"]["maximumEntryDelta"]} cycles')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('reference_build', 'reference_writes', 'reference_study', 'reference_trace',
                 'candidate_build', 'candidate_writes', 'candidate_study', 'candidate_trace',
                 'candidate_sid', 'primary_reference'):
        parser.add_argument('--' + name.replace('_', '-'), required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = vars(parser.parse_args())
    output = args.pop('output')
    run(args, output)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, IndexError) as error:
        raise SystemExit(f'Rambo primary timing check failed: {error}')
