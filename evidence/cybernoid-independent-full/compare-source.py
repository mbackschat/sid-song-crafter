"""Compare the compiled title's music prefix with a pinned source-write oracle."""

import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_LEDGER = ROOT / 'evidence/cybernoid-form-36000/audit.writes.json.gz'
SOURCE_RAW_SHA256 = '268846b70fdd415e2ece14e9ddba99dfab8bed476396aae9cdf9901d5202a038'
MUSIC_CALLS = 17280
PREFIX_STORES = 310586
TOTAL_CALLS = 17408
CONTROL_ADDRESSES = (0xd412, 0xd40b, 0xd404)
CODE_PATHS = (
    'scripts/compose-cybernoid.py', 'scripts/prepare-cybernoid-title.py',
    'scripts/cybernoid_player.py', 'scripts/cybernoid_pitch.py',
    'scripts/cybernoid_state.py', 'scripts/cybernoid_programs.py',
    'scripts/cybernoid_output.py', 'scripts/sid_assembler.py',
    'scripts/verify_player.py', 'scripts/psid_audit.py',
    'scripts/psid_profile.py', 'scripts/sid_audit_host.py',
    'songs/players/cybernoid.asm', 'songs/players/cybernoid-pitch.asm',
    'songs/players/cybernoid-effects.asm',
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def portable(path):
    path = path.resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def fingerprint(path):
    raw = path.read_bytes()
    return dict(path=portable(path), sha256=digest(raw), bytes=len(raw))


def identity(row):
    return row['phase'], row['tick'], row['address'], row['value']


def prefix(rows):
    return [row for row in rows if row['phase'] == 'init' or
            row['phase'] == 'play' and 0 <= row['tick'] < MUSIC_CALLS]


def compare_prefix(source, candidate, expected_count=PREFIX_STORES):
    source, candidate = prefix(source), prefix(candidate)
    require(len(source) == expected_count, f'Source prefix requires {expected_count} stores; observed {len(source)}')
    require(len(candidate) == expected_count, f'Candidate prefix requires {expected_count} stores; observed {len(candidate)}')
    for index, (wanted, actual) in enumerate(zip(source, candidate)):
        require(identity(wanted) == identity(actual),
                f'Music prefix differs at store {index}: expected {identity(wanted)}, observed {identity(actual)}')
    init_count = sum(row['phase'] == 'init' for row in source)
    return dict(firstCall=0, lastCallInclusive=MUSIC_CALLS - 1, playCalls=MUSIC_CALLS,
                initStores=init_count, playStores=expected_count - init_count,
                matchedStores=expected_count, fields=['phase', 'tick', 'address', 'value'],
                orderPreserved=True, repeatedStoresPreserved=True,
                instructionStartCyclesCompared=False)


def check_tail(rows, ending):
    require(ending == dict(start_call=MUSIC_CALLS, release_calls=64, fade_step_calls=4),
            'This receipt requires the retained 64-release/four-call-step ending')
    calls = defaultdict(list)
    for row in rows:
        if row['phase'] == 'play' and MUSIC_CALLS <= row['tick'] < TOTAL_CALLS:
            calls[row['tick']].append(row)
    require(set(calls) == set(range(MUSIC_CALLS, TOTAL_CALLS)), 'Candidate ending does not cover every declared tail call')
    observed = []
    control_count, volume_count = 0, 0
    for tick in range(MUSIC_CALLS, TOTAL_CALLS):
        group = calls[tick]
        age = tick - MUSIC_CALLS
        volume = 15 if age < ending['release_calls'] else 15 - (age - ending['release_calls']) // ending['fade_step_calls']
        controls = [dict(address=row['address'], value=row['value']) for row in group
                    if row['address'] in CONTROL_ADDRESSES]
        require(tuple(row['address'] for row in controls) == CONTROL_ADDRESSES,
                f'Ending controls must retain voice order 2,1,0 at call {tick}')
        require(all(row['value'] & 1 == 0 for row in controls), f'Ending gate reopens at call {tick}')
        volumes = [row['value'] for row in group if row['address'] == 0xd418]
        require(volumes and all(value & 15 == volume for value in volumes),
                f'Ending volume store differs from the declared level at call {tick}')
        require(group[-1]['address'] == 0xd418, f'Ending call {tick} lacks its final mode/volume store')
        control_count += len(controls)
        volume_count += len(volumes)
        observed.append(dict(call=tick, expectedVolume=volume, controlWrites=controls,
                             modeVolumeWrites=volumes, finalModeVolume=group[-1]['value'],
                             orderedStores=len(group)))
    require(observed[-1]['finalModeVolume'] & 15 == 0, 'Ending does not finish at volume zero')
    return dict(classification='Deliberate finite arrangement tail; excluded from source equivalence',
                firstCall=MUSIC_CALLS, lastCallInclusive=TOTAL_CALLS - 1,
                playCalls=TOTAL_CALLS - MUSIC_CALLS, contract=ending,
                matchedSourceStores=None, sourceComparisonApplied=False,
                controlStoresChecked=control_count, modeVolumeStoresChecked=volume_count,
                everyControlGateClear=True, everyModeVolumeLowNibbleMatchesFade=True,
                lastFourCallsVolumeZero=True, observations=observed,
                contractNotes=[
                    'The original order restart is replaced; source calls at and after 17280 are not a tail oracle.',
                    'The runtime freezes row/tempo countdowns and saturates note age at 255 while sound programs continue.',
                    'Gate masking occurs after effects; all mode/volume stores combine their mode high nibble with the current tail volume.',
                    'This ledger check observes gates and volume, not internal note age, later callable state or rendered silence.',
                ])


def compare(candidate_root, description_path, source_path):
    source_stored = source_path.read_bytes()
    source_raw = gzip.decompress(source_stored)
    require(digest(source_raw) == SOURCE_RAW_SHA256, 'Pinned source ledger raw SHA-256 differs')
    source = json.loads(source_raw)
    description_raw = description_path.read_bytes()
    description = json.loads(description_raw)
    require(description['play_calls'] == TOTAL_CALLS, 'Description must declare the complete retained title and ending')
    require(all(row['call'] < MUSIC_CALLS for row in description['rows']), 'Description contains tail score rows')
    paths = {name: candidate_root / name for name in
             ('reconstructed.sid', 'writes.json', 'build.json', 'audit.json', 'player.asm', 'player.listing')}
    candidate_raw = paths['writes.json'].read_bytes()
    candidate = json.loads(candidate_raw)
    build = json.loads(paths['build.json'].read_bytes())
    audit = json.loads(paths['audit.json'].read_bytes())
    sid_sha = digest(paths['reconstructed.sid'].read_bytes())
    require(build['sidSha256'] == audit['sourceSha256'] == sid_sha, 'Candidate SID differs from its CPU/build receipts')
    require(build['descriptionSha256'] == digest(description_raw), 'Description differs from its build receipt')
    require(build['checkedPlayCalls'] == audit['playCalls'] == TOTAL_CALLS, 'Candidate receipt does not cover the complete declared title')
    require(build['originalDriverIncluded'] is False and build['registerDumpPlayback'] is False,
            'Candidate build must declare independent semantic computation')
    require(build['finiteMusicalEnding'] is True, 'Candidate build must declare the arranged ending')
    require(build['orderedStoreComparison']['matchedStores'] == len(candidate), 'Candidate store count differs from its model comparison receipt')
    require(audit['initWriteCount'] + audit['playWriteCount'] == len(candidate), 'Candidate store count differs from its CPU audit')
    require(all(row['phase'] == 'init' and row['tick'] is None or
                row['phase'] == 'play' and type(row['tick']) is int and 0 <= row['tick'] < TOTAL_CALLS
                for row in candidate), 'Candidate ledger contains calls outside the declared span')
    comparison = compare_prefix(source, candidate)
    require(comparison['initStores'] == 25, 'Retained initialization must contain 25 SID stores')
    tail = check_tail(candidate, description['ending'])
    source_pin = dict(path=portable(source_path), sha256=digest(source_stored), bytes=len(source_stored),
                      rawSha256=digest(source_raw), rawBytes=len(source_raw), stores=len(source),
                      use='Comparison oracle only; not a compiler or player input')
    return dict(schemaVersion=1, passed=True,
                classification='Ordered source-write prefix equivalence plus separately checked arranged tail',
                preservedMusic=comparison, deliberateEnding=tail,
                provenance=dict(reproducer=fingerprint(Path(__file__)),
                                description=dict(path=portable(description_path), sha256=digest(description_raw), bytes=len(description_raw)),
                                sourceLedger=source_pin,
                                candidate={name: fingerprint(path) for name, path in paths.items()},
                                code={path: fingerprint(ROOT / path) for path in CODE_PATHS}),
                limitations=[
                    'Phase/call/address/value and store order are compared; instruction-start cycles are retained but not equated.',
                    'Existing final candidate CPU/build receipts bind the ledger to the SID and editable description; this reproducer does not execute either player.',
                    'The tail is deliberately different from the looping source; its internal-state contract is covered by the player tests and model comparison.',
                    'No original SID payload, reference audio, VICE timing, PCM identity, rendered-silence or listening claim is produced.',
                ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--candidate-root', type=Path, help='Defaults to OUTPUT_ROOT/candidate')
    parser.add_argument('--description', type=Path, default=ROOT / 'songs/cybernoid-title.json')
    parser.add_argument('--source-ledger', type=Path, default=SOURCE_LEDGER)
    parser.add_argument('--receipt-name', default='source-comparison.json', help='Fresh JSON filename inside OUTPUT_ROOT')
    args = parser.parse_args()
    require(Path(args.receipt_name).name == args.receipt_name and args.receipt_name.endswith('.json'),
            'Receipt name must be a JSON filename without directories')
    output = args.output_root / args.receipt_name
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh receipt name')
    candidate_root = args.candidate_root or args.output_root / 'candidate'
    receipt = compare(candidate_root, args.description, args.source_ledger)
    receipt['reproduction'] = dict(argv=[
        'python3', portable(Path(__file__)), '--output-root', portable(args.output_root),
        '--candidate-root', portable(candidate_root), '--description', portable(args.description),
        '--source-ledger', portable(args.source_ledger), '--receipt-name', args.receipt_name,
    ], output=portable(output), freshReceiptRequired=True)
    args.output_root.mkdir(parents=True, exist_ok=True)
    with output.open('x') as handle:
        json.dump(receipt, handle, indent=2, allow_nan=False)
        handle.write('\n')
    print(json.dumps(dict(output=portable(output), sha256=digest(output.read_bytes()),
                          matchedMusicStores=receipt['preservedMusic']['matchedStores'],
                          checkedTailCalls=receipt['deliberateEnding']['playCalls']), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f'Cybernoid source comparison failed: {error}')
