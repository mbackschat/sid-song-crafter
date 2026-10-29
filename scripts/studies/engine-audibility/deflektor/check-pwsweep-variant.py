"""Guard that the PWSWEEP variant differs from the exact Deflektor transfer only in pulse width.

Compares the CPU-captured ordered SID stores of both compiled players and the
renderer's register snapshots, confirms the exact build is the accepted one,
and states the mechanism-predicted pulse differences.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


PULSE_LOW = (0xd402, 0xd409, 0xd410)
PULSE_HIGH = (0xd403, 0xd40a, 0xd411)
PULSE = PULSE_LOW + PULSE_HIGH
PULSE_BYTES = {address - 0xd400 for address in PULSE}
VERIFIED = ('checkedPlayCalls', 'completeDeclaredRange', 'ending', 'orderedStoreComparison', 'coldInitializationStores')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def accepted(run_path, stage, relative):
    run = json.loads(Path(run_path).read_text())
    rows = [row['sha256'] for row in run['artifacts'] if row['stageId'] == stage and row['relativePath'] == relative]
    require(len(rows) == 1, f'Accepted run lacks {stage}/{relative}')
    return rows[0]


def pulse_words(writes):
    """Return {(tick, voice): 16-bit pulse word} from the ordered stores."""
    parts = {}
    for row in writes:
        for voice, (low, high) in enumerate(zip(PULSE_LOW, PULSE_HIGH)):
            if row['address'] == low:
                parts.setdefault((row['tick'], voice), {})['low'] = row['value']
            elif row['address'] == high:
                parts.setdefault((row['tick'], voice), {})['high'] = row['value']
    return {key: value['high'] << 8 | value['low'] for key, value in parts.items()}


def check(args):
    exact_dir, variant_dir = Path(args.exact), Path(args.variant)
    exact_writes = json.loads((exact_dir / 'writes.json').read_text())
    variant_writes = json.loads((variant_dir / 'writes.json').read_text())
    exact_report = json.loads((exact_dir / 'verification.json').read_text())
    variant_report = json.loads((variant_dir / 'verification.json').read_text())
    result = dict(schemaVersion=1)

    identity = dict(
        sid=sha256(exact_dir / 'reconstructed.sid') == accepted(args.accepted_run, 'candidate-build', 'candidate/reconstructed.sid'),
        writes=sha256(exact_dir / 'writes.json') == accepted(args.accepted_run, 'candidate-build', 'candidate/writes.json'),
        render=sha256(args.exact_render) == accepted(args.accepted_run, 'candidate-render', 'render.wav'))
    require(all(identity.values()), f'Exact build differs from the accepted transfer: {identity}')
    result['exactEqualsAccepted'] = dict(acceptedRun=str(args.accepted_run), **identity)

    for field in VERIFIED:
        require(exact_report[field] == variant_report[field], f'Verification field {field} differs')
    require('variant' in variant_report and 'variant' not in exact_report,
            'The variant report lacks PWSWEEP provenance or the exact report carries it')
    require(variant_report['variant']['playerAsmHasPwsweepTail'], 'The variant player lacks the PWSWEEP tail')
    require(variant_report['variant']['pwsweepSourceSha256'] == sha256(args.pwsweep_source), 'PWSWEEP source changed')
    for report in (exact_report, variant_report):
        require(report['standaloneBootstrapVerification']['passed'] and report['resetVerification']['passed']
                and report['completeDeclaredRange'], 'Audit did not complete')
    result['audit'] = dict(playCalls=exact_report['checkedPlayCalls'], storesPerPlayer=len(exact_writes),
        maximumPlayCycles=dict(exact=exact_report['maximumPlayCycles'], variant=variant_report['maximumPlayCycles']),
        sameCompleteRangeEndingAndStoreCounts=True)

    require(len(exact_writes) == len(variant_writes), 'Store counts differ')
    require(all((a['phase'], a['tick'], a['address']) == (b['phase'], b['tick'], b['address'])
                for a, b in zip(exact_writes, variant_writes)), 'Store order or addresses differ')
    differing = [(index, a, b) for index, (a, b) in enumerate(zip(exact_writes, variant_writes)) if a['value'] != b['value']]
    require(differing, 'The variant is identical to the exact transfer')
    outside = [(index, a['address']) for index, a, _ in differing if a['address'] not in PULSE]
    require(not outside, f'Non-pulse registers differ: {outside[:5]}')
    counts = Counter(a['address'] for _, a, _ in differing)
    require(not any(counts[address] for address in PULSE_LOW), 'Pulse low bytes differ; the borrow prediction failed')
    require(all(b['value'] == (a['value'] - 1) & 255 for _, a, b in differing),
            'A differing pulse high byte is not exactly one below the exact value')
    require(all(row['value'] <= 15 for row in variant_writes if row['address'] in PULSE_HIGH),
            'A variant pulse high byte leaves the 4-bit SID range')
    first_index, first_exact, first_variant = differing[0]
    result['storeComparison'] = dict(
        orderedStoresIdentical='phase, tick and address for every store',
        pulseWriteTotals={f'${address:04X}': sum(1 for row in exact_writes if row['address'] == address) for address in PULSE},
        differingWritesPerRegister={f'${address:04X}': counts[address] for address in PULSE},
        differingTotal=len(differing), nonPulseDifferences=0,
        firstDifference=dict(storeIndex=first_index, call=first_exact['tick'], register=f"${first_exact['address']:04X}",
                             exact=first_exact['value'], variant=first_variant['value']),
        everyDifferenceIsMinusOneOnAPulseHighByte=True)

    require(all(row['phase'] == 'play' for row in exact_writes), 'Pulse words assume play-phase stores only')
    exact_words, variant_words = pulse_words(exact_writes), pulse_words(variant_writes)
    moved = [key for key in sorted(exact_words) if exact_words[key] != variant_words[key]]
    require(all(exact_words[key] - variant_words[key] == 256 for key in moved), 'Pulse word offset is not 256')

    def example(key):
        call, voice = key
        return dict(call=call, voice=voice, exactWord=exact_words[key], variantWord=variant_words[key],
                    exactHex=f'${exact_words[key]:03X}', variantHex=f'${variant_words[key]:03X}')

    first_call, first_voice = moved[0]
    around = [call for call, voice in sorted(exact_words) if voice == first_voice and call >= first_call - 1][:7]
    moved_set = set(moved)
    runs = {voice: sum(1 for key in moved if key[1] == voice and (key[0] - 1, voice) not in moved_set) for voice in range(3)}
    # Direction read from the exact stream alone: a call that moves in the variant must sit in a
    # descending run, and no within-segment (|delta| < 256) descent may be left unchanged.
    descending_moved = ascending_moved = unchanged_descents = 0
    for (call, voice), word in exact_words.items():
        previous = exact_words.get((call - 1, voice))
        if previous is None or not 0 < abs(word - previous) < 256:
            continue
        if (call, voice) in moved_set and (call - 1, voice) in moved_set:
            descending_moved += word < previous
            ascending_moved += word > previous
        elif (call, voice) not in moved_set and (call - 1, voice) not in moved_set and word < previous:
            unchanged_descents += 1
    require(not unchanged_descents, 'A within-segment descent is identical in the variant')
    result['predictedMechanism'] = dict(
        rule='In a downward segment Deflektor wraps the low byte upward and keeps the high byte, while PWSWEEP borrows, so the variant pulse word is exactly 256 below (6.25 percent duty of the 4096-step range) on every call of the run; upward segments never reach 256 and are identical.',
        differingPulseWords={f'voice{voice}': sum(1 for key in moved if key[1] == voice) for voice in range(3)},
        pulseWordsPerVoice={f'voice{voice}': sum(1 for key in exact_words if key[1] == voice) for voice in range(3)},
        downwardRuns={f'voice{voice}': count for voice, count in runs.items()},
        directionCheckOnExactStream=dict(withinRunDescents=descending_moved, withinRunAscentsAtSegmentReload=ascending_moved,
                                         unchangedWithinSegmentDescents=unchanged_descents),
        firstExample=example((first_call, first_voice)),
        firstExamplePerVoice=[example(next(key for key in moved if key[1] == voice)) for voice in range(3)],
        sequenceAroundFirstExample=[dict(call=call, exact=exact_words[call, first_voice], variant=variant_words[call, first_voice])
                                    for call in around])

    if args.exact_registers:
        exact_rows, variant_rows = (
            [bytes.fromhex(line.split('\t')[1]) for line in Path(path).read_text().splitlines()[1:]]
            for path in (args.exact_registers, args.variant_registers))
        require(len(exact_rows) == len(variant_rows), 'Register snapshot counts differ')
        pulse_rows, shifted = 0, []
        for index, (left, right) in enumerate(zip(exact_rows, variant_rows)):
            pulse_rows += any(left[offset] != right[offset] for offset in PULSE_BYTES)
            for offset in range(len(left)):
                if offset not in PULSE_BYTES and left[offset] != right[offset]:
                    neighbours = [exact_rows[other][offset] for other in (index - 1, index + 1) if 0 <= other < len(exact_rows)]
                    require(right[offset] in neighbours, f'Snapshot {index} byte {offset} differs beyond a one-snapshot shift')
                    shifted.append(dict(snapshot=index, register=f'${0xd400 + offset:04X}', exact=left[offset], variant=right[offset]))
        result['renderedRegisterSnapshots'] = dict(snapshots=len(exact_rows), snapshotsWithPulseDifferences=pulse_rows,
            nonPulseSnapshotsShiftedByOneSnapshot=shifted,
            note='A non-pulse byte may differ only by landing one snapshot earlier or later: the variant changes the play routine by a few cycles, which moves write moments inside a call.')
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exact', type=Path, required=True, help='exact build directory (candidate/)')
    parser.add_argument('--variant', type=Path, required=True, help='variant build directory (candidate/)')
    parser.add_argument('--accepted-run', type=Path, required=True)
    parser.add_argument('--exact-render', type=Path, required=True)
    parser.add_argument('--exact-registers', type=Path)
    parser.add_argument('--variant-registers', type=Path)
    parser.add_argument('--pwsweep-source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(bool(args.exact_registers) == bool(args.variant_registers), 'Pass both register snapshots or neither')
    result = check(args)
    print(json.dumps({key: result[key] for key in ('storeComparison', 'predictedMechanism')}, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (KeyError, OSError, ValueError) as error:
        sys.exit(f'PWSWEEP variant guard failed: {error}')
