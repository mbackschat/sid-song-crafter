"""Verify Turbo's pulse-to-saw onset and compare a duration-only source edit."""

import argparse
from collections import defaultdict
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from reference_intake import managed_output

spec = importlib.util.spec_from_file_location('turbo_probe', Path(__file__).with_name('probe-contrast.py'))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def compare_stores(original, candidate):
    sid = lambda rows: [r for r in rows if r['operation'] == 'store' and 'sidAddress' in r]
    first, second = sid(original), sid(candidate)
    oscillator = lambda rows: [r for r in rows if r['sidAddress'] != 0xd418]
    a, b = oscillator(first), oscillator(second)
    schedule = lambda r: (r['phase'], r['irqIndex'], r['pc'], r['address'])
    require([schedule(r) for r in a] == [schedule(r) for r in b], 'Oscillator/filter write schedule changed')
    changes = []
    for before, after in zip(a, b):
        if before['value'] == after['value']:
            continue
        require(before['address'] == 0xd404 and before['value'] in (0x40, 0x41)
                and after['value'] == before['value'] - 0x20,
                'Changed a protected pitch, gate, filter, other voice or unexpected waveform')
        changes.append(dict(irqIndex=before['irqIndex'], original=before['value'], candidate=after['value']))
    require(changes, 'Diagnostic produced no target control changes')
    volume = lambda rows: [(r['pc'], r['address'], r['value']) for r in rows if r['sidAddress'] == 0xd418]
    original_volume, candidate_volume = volume(first), volume(second)
    require(original_volume == candidate_volume, 'Protected volume writer/value sequence changed')
    return dict(verified=True, oscillatorAndFilterStores=len(a), protectedVolumeStores=len(original_volume),
                protectedVolumeSequenceSha256=digest(json.dumps(original_volume, separators=(',', ':')).encode()),
                changedControlWrites=len(changes), changedControls=changes,
                limits='Oscillator/filter writer order and IRQ attribution preserved; volume writer/value sequence preserved separately. Cross-stream interleaving and exact checkpoint/bus timing are not asserted equal. Volume amplitudes remain private.')


def onset_ledger(rows, source):
    source_byte = lambda address: source[126 + address - 0x810]
    require((source_byte(0x1039), source_byte(0x10f7), source_byte(0x1107)) == (0x21, 24, 0x41),
            'Unexpected record-1 body/onset parameters')
    by_irq = defaultdict(list)
    for row in rows:
        by_irq[row['irqIndex']].append(row)
    ledger = []
    for row in rows:
        if row['operation'] != 'exec' or row['pc'] != 0xe08:
            continue
        require(row['bytes'] == 'd9f610' and row['x'] == 0 and row['y'] == 1,
                'Selected onset probe no longer refers exclusively to voice 1 record 1')
        age = row['a']
        selected = [r for r in by_irq[row['irqIndex']] if r['operation'] == 'exec' and r['pc'] == 0xe39 and r['x'] == 0]
        expected = 0x41 if age < 24 else 0x21 if age < 26 else None
        require(len(selected) == (0 if expected is None else 1), 'Missing or repeated onset waveform assignment')
        if expected is not None:
            require(selected[0]['a'] == expected and selected[0]['bytes'] == '9d5a08', 'Onset assignment disagrees with source parameters')
        output = [r for r in by_irq[row['irqIndex']] if r['operation'] == 'store' and r.get('sidAddress') == 0xd404]
        require(len(output) == 1 and output[0]['pc'] == 0xe46, 'Missing or repeated final voice-1 control write')
        require(output[0]['value'] & 0xfe == (0x41 if age < 24 else 0x21) & 0xfe,
                'Final control waveform disagrees with staged onset')
        ledger.append(dict(irqIndex=row['irqIndex'], voice=1, record=1, age=age,
                           assignedWaveform=expected, finalControl=output[0]['value']))
    require(ledger and any(r['age'] < 24 for r in ledger) and any(r['age'] >= 26 for r in ledger),
            'Window does not cover both pulse onset and held saw body')
    return ledger


def verify_removal(comparison, ledger):
    expected = [(r['irqIndex'], r['finalControl'], r['finalControl'] - 0x20)
                for r in ledger if r['assignedWaveform'] == 0x41]
    observed = [(r['irqIndex'], r['original'], r['candidate']) for r in comparison['changedControls']]
    require(expected and observed == expected, 'Diagnostic must remove the complete onset and change no other IRQ')


def validate_baseline(directory):
    receipt = json.loads((directory / 'verification.json').read_text())
    require(receipt['sourceSha256'] == probe.SOURCE_SHA, 'Baseline source fingerprint mismatch')
    require(receipt['tools']['probeSha256'] == digest(Path(probe.__file__).read_bytes()), 'Baseline probe changed; refresh recipe capture')
    for name, expected in receipt['privateArtifacts'].items():
        data = (directory / name).read_bytes()
        require(len(data) == expected['bytes'] and digest(data) == expected['sha256'], 'Private baseline artifact fingerprint mismatch')
    require(receipt['capture']['completedSkippedRefreshes'] == 1120
            and receipt['capture']['retainedIrqCount'] == 192, 'Unexpected onset window')
    log = gzip.decompress((directory / 'monitor.log.gz').read_bytes()).decode('latin-1')
    parsed = probe.parse_records(log)
    contract = probe.validate_monitor_contract(log, parsed, 1120)
    retained, recomputed = probe.summarize(parsed, 192, receipt['header'], 1120)
    require(json.loads(json.dumps(contract)) == receipt['monitorContract'], 'Baseline monitor contract mismatch')
    for name in ('capture', 'sid', 'volume', 'initialization'):
        require(recomputed[name] == receipt[name], 'Baseline summary mismatch: ' + name)
    require(retained == json.loads(gzip.decompress((directory / 'trace.json.gz').read_bytes())), 'Baseline decoded trace mismatch')
    return retained, receipt


def run(baseline, source, output, vice):
    data = source.read_bytes()
    require(digest(data) == probe.SOURCE_SHA, 'Original source fingerprint mismatch')
    rows, baseline_receipt = validate_baseline(baseline)
    require(baseline_receipt['tools']['viceSha256'] == digest(vice.read_bytes()), 'Baseline VICE binary changed')
    ledger = onset_ledger(rows, data)
    output = managed_output(output, ROOT)
    require(not output.exists(), 'Choose a fresh output directory')
    output.mkdir(parents=True)
    changed = bytearray(data)
    offset = 126 + 0x10f7 - 0x810
    require(changed[offset] == 24, 'Onset-duration source byte changed')
    changed[offset] = 0
    variant = output / 'without-pulse-onset.sid'
    variant.write_bytes(changed)
    candidate_receipt = probe.probe(variant, output / 'candidate', vice, 192,
                                    skip_refreshes=1120, expected_sha=digest(changed))
    candidate_rows = json.loads(gzip.decompress((output / 'candidate/trace.json.gz').read_bytes()))
    comparison = compare_stores(rows, candidate_rows)
    verify_removal(comparison, ledger)
    write_json(output / 'onset-ledger.json', ledger)
    write_json(output / 'patch.json', dict(sourceSha256=digest(data), candidateSha256=digest(changed),
        changes=[dict(sourceAddress=0x10f7, fileOffset=offset, before=24, after=0)],
        meaning='Record 1 onset duration only: omit its age-1..23 pulse phase, retaining saw body, note schedule and other instrument parameters.'))
    comparison.update(sourceSha256=digest(data), candidateSha256=digest(changed),
        baselineVerificationSha256=digest((baseline / 'verification.json').read_bytes()),
        candidateVerificationSha256=digest((output / 'candidate/verification.json').read_bytes()),
        onsetComparisons=len(ledger), pulseAssignments=sum(r['assignedWaveform'] == 0x41 for r in ledger),
        bodyRestorations=sum(r['assignedWaveform'] == 0x21 for r in ledger),
        hostLimits=baseline_receipt['limitations'], listeningReview=None)
    write_json(output / 'verification.json', comparison)
    return comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/research/turbo-outrun/Turbo_Outrun.sid')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--vice', type=Path, default=ROOT / '.tools/vice-headless-3.9/build/src/x64sc')
    args = parser.parse_args()
    result = run(args.baseline.resolve(), args.source.resolve(), args.output.resolve(), args.vice.resolve())
    print(json.dumps({k: result[k] for k in ('verified', 'changedControlWrites', 'protectedVolumeStores', 'onsetComparisons')}))


if __name__ == '__main__':
    main()
