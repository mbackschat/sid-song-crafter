"""Verify Giana's bounded motion and freeze two executed PWM step parameters."""

import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from reference_intake import managed_output

spec = importlib.util.spec_from_file_location('giana_source_probe', Path(__file__).with_name('probe-contrast.py'))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
TARGET_REGISTERS = {0xd402, 0xd403, 0xd409, 0xd40a}
STEP_FIELDS = {0x8c29: 16, 0x8d78: 32}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def pulse_motion(rows):
    widths, controls, previous_widths = [0] * 3, [0] * 3, [0] * 3
    changes = []
    for row in rows:
        if row['operation'] != 'store' or not 0xd400 <= row['address'] <= 0xd414:
            continue
        voice, register = divmod(row['address'] - 0xd400, 7)
        value = row['value']
        if register == 2:
            widths[voice] = (widths[voice] & 0xf00) | value
        elif register == 3:
            widths[voice] = (widths[voice] & 255) | ((value & 15) << 8)
        elif register == 4:
            if (controls[voice] & 0x49) == 0x40 and (value & 0x49) == 0x40 and widths[voice] != previous_widths[voice]:
                changes.append(dict(voice=voice + 1, irqIndex=row['irqIndex'],
                                    before=previous_widths[voice], after=widths[voice],
                                    previousControl=controls[voice], control=value,
                                    writerPc=row['pc'], monitorCycle=row['monitorCycle']))
            previous_widths[voice], controls[voice] = widths[voice], value
    return changes


def filter_motion(rows):
    high, pending, updates = None, None, []
    for row in rows:
        if row['operation'] != 'store':
            continue
        if row['address'] == 0x4241:
            previous, high = high, row['value']
            if row['pc'] in (0x47ea, 0x4810):
                require(pending is None, 'Unpaired shared filter state update')
                pending = dict(voice=row['x'] + 1, irqIndex=row['irqIndex'], before=previous,
                               after=high, stateWriterPc=row['pc'], stateCycle=row['monitorCycle'])
        elif row['address'] == 0xd416 and row['pc'] in (0x47ed, 0x4813):
            if pending is None and row['phase'] == 'init':
                continue
            require(pending is not None and pending['after'] == row['value']
                    and pending['voice'] == row['x'] + 1 and pending['irqIndex'] == row['irqIndex'],
                    'SID cutoff disagrees with the executed shared filter state')
            require(row['pc'] == (0x47ed if pending['stateWriterPc'] == 0x47ea else 0x4813),
                    'Unexpected shared filter output owner')
            pending.update(sidWriterPc=row['pc'], sidCycle=row['monitorCycle'])
            updates.append(pending)
            pending = None
    require(pending is None, 'Missing SID output after shared filter state update')
    return updates


def parameter_map(rows, source):
    lows, highs, records = [None] * 3, [None] * 3, []
    for row in rows:
        if row['operation'] != 'store':
            continue
        address = row['address']
        if 0x4263 <= address <= 0x4265:
            lows[address - 0x4263] = row['value']
        elif 0x4266 <= address <= 0x4268:
            highs[address - 0x4266] = row['value']
        elif 0x4219 <= address <= 0x421b:
            voice = address - 0x4219
            require(row['pc'] == 0x44fe and row['x'] == voice
                    and lows[voice] is not None and highs[voice] is not None,
                    'PWM step lacks an executed macro pointer')
            macro = lows[voice] | highs[voice] << 8
            require(0x41c0 <= macro + 9 < 0x5fdd, 'Macro parameter is outside the verified relocation')
            original_address = macro + 9 + 0x3023
            offset = 126 + original_address - 0x71e3
            require(source[offset] == row['value'], 'Executed PWM step differs from its source byte')
            records.append(dict(voice=voice + 1, irqIndex=row['irqIndex'], macroAddress=macro,
                                fieldOffset=9, sourceAddress=original_address,
                                sourceFileOffset=offset, step=row['value'], writerPc=row['pc']))
    return records


def compare_stores(original, candidate):
    sid = lambda rows: [row for row in rows if row['operation'] == 'store' and 0xd400 <= row['address'] <= 0xd7ff]
    first, second = sid(original), sid(candidate)
    position = lambda row: (row['phase'], row['irqIndex'], row['pc'], row['address'])
    require([position(row) for row in first] == [position(row) for row in second],
            'Diagnostic changed source SID writer/address/order or IRQ attribution')
    protected = lambda rows: [(row['phase'], row['irqIndex'], row['address'], row['value'])
                              for row in rows if row['address'] not in TARGET_REGISTERS]
    require(protected(first) == protected(second), 'Diagnostic changed protected non-target SID behavior')
    differences = [dict(irqIndex=a['irqIndex'], address=a['address'], writerPc=a['pc'],
                        original=a['value'], candidate=b['value'])
                   for a, b in zip(first, second) if a['value'] != b['value']]
    require(differences and all(row['address'] in TARGET_REGISTERS for row in differences),
            'Expected changed values only in voice 1/2 pulse registers')
    return differences


def validate_baseline(log, saved_rows, receipt):
    raw_rows = probe.parse_records(log)
    contract = probe.validate_monitor_contract(log, raw_rows)
    retained, derived = probe.summarize(raw_rows, receipt['capture']['requestedPostIdleRefreshes'], receipt['header'])
    require(retained == saved_rows, 'Saved trace rows disagree with the guarded monitor reparse')
    for key in ('capture', 'sid', 'volume', 'initialization'):
        require(derived[key] == receipt[key], f'Saved receipt {key} disagrees with monitor evidence')
    require(json.loads(json.dumps(contract)) == receipt['monitorContract'],
            'Saved monitor coverage receipt disagrees')
    return retained


def run(baseline, source, output, vice):
    original = source.read_bytes()
    require(sha(original) == probe.SOURCE_SHA, 'Original Giana source fingerprint mismatch')
    receipt_path, trace_path = baseline / 'verification.json', baseline / 'trace.json.gz'
    receipt = json.loads(receipt_path.read_text())
    require(receipt['sourceSha256'] == sha(original), 'Baseline source pin differs')
    require(receipt['header'] == probe.inspect_sid(original, subtune=3), 'Baseline source header differs')
    require(receipt['tools']['probeSha256'] == sha(Path(probe.__file__).read_bytes())
            and receipt['tools']['viceSha256'] == sha(vice.read_bytes()), 'Baseline probe/VICE dependency differs')
    monitor_path = baseline / 'monitor.log'
    rows = validate_baseline(monitor_path.read_text(encoding='latin-1'),
                             json.load(gzip.open(trace_path, 'rt')), receipt)
    output = managed_output(output, ROOT)
    require(not output.exists(), 'Choose a fresh diagnostic output directory')
    parameters, pulses, filters = parameter_map(rows, original), pulse_motion(rows), filter_motion(rows)
    selected = {row['sourceAddress']: row['step'] for row in parameters if row['voice'] in (1, 2) and row['irqIndex'] >= 383}
    require(selected == STEP_FIELDS, 'Executed active pulse fields no longer match the selected diagnostic')
    reads = [row for row in rows if row['operation'] == 'load' and row['address'] == 0x41ec]
    require(reads and {row['pc'] for row in reads} == {0x4a39, 0x43cb}
            and all(row['a'] == 0 for row in reads), 'Sample/volume branch state is not proven inactive')
    volume = [row for row in rows if row['operation'] == 'store' and row['address'] == 0xd418]
    require(volume and all(row['pc'] == 0x43d8 and row['value'] == 0x1f for row in volume),
            'Expected ordinary bounded mode/volume writes')
    output.mkdir(parents=True)
    write_json(output / 'parameter-map.json', parameters)
    write_json(output / 'pulse-through-gate-off.json', pulses)
    write_json(output / 'shared-filter-updates.json', filters)
    grouped = {}
    for update in filters:
        grouped.setdefault(update['irqIndex'], []).append(update)
    multi = {str(irq): group for irq, group in grouped.items() if len({row['voice'] for row in group}) > 1}
    analysis = dict(schemaVersion=1, sourceSha256=sha(original),
        baselineReceiptSha256=sha(receipt_path.read_bytes()), baselineTraceSha256=sha(trace_path.read_bytes()),
        baselineMonitorSha256=sha(monitor_path.read_bytes()),
        sampleEnableReads=len(reads), sampleEnableValues=[0], sampleEnableReadSites=['4a39', '43cb'],
        volume=dict(writes=len(volume), writerPc=0x43d8, values=[31],
                    interpretation='Executed sample-enable zero and constant ordinary filter-mode/master-volume stores; no rapid D418 stream in this bounded passage.'),
        pulse=dict(changesBetweenPulseGateOffWrites=dict(Counter(str(row['voice']) for row in pulses)),
                   firstIrq=min(row['irqIndex'] for row in pulses), lastIrq=max(row['irqIndex'] for row in pulses),
                   limitation='GATE is clear before and after the observed width change; score-rest decoding and audible release quality are unverified.'),
        sharedFilter=dict(verifiedRamToSidUpdates=len(filters), stateAddress=0x4241,
                          voiceCounts=dict(Counter(str(row['voice']) for row in filters)),
                          irqsWithMultipleVoiceAdvances=len(multi),
                          firstMultipleVoiceExample=next(group for group in multi.values()
                                                        if all(row['before'] is not None for row in group)),
                          limitation='Global high-byte state is updated by opted-in voice passes; trigger/reset policy and initial state before first captured RAM write are not fully decoded.'),
        listeningReview=None)
    write_json(output / 'baseline-analysis.json', analysis)
    candidate = bytearray(original)
    patches = []
    for address, value in STEP_FIELDS.items():
        offset = 126 + address - 0x71e3
        require(candidate[offset] == value, 'PWM diagnostic source parameter differs')
        candidate[offset] = 0
        patches.append(dict(sourceAddress=address, fileOffset=offset, original=value, candidate=0,
                            meaning='Macro field 9 PWM increment; retain reset width and stage counters.'))
    candidate = bytes(candidate)
    candidate_path = output / 'frozen-pwm.sid'
    candidate_path.write_bytes(candidate)
    write_json(output / 'patch.json', dict(originalSha256=sha(original), candidateSha256=sha(candidate), patches=patches))
    changed_receipt = probe.probe(candidate_path, output / 'candidate', vice,
                                 receipt['capture']['requestedPostIdleRefreshes'], expected_sha=sha(candidate))
    changed_rows = json.load(gzip.open(output / 'candidate/trace.json.gz', 'rt'))
    differences = compare_stores(rows, changed_rows)
    require(receipt['capture']['completedIrqRefreshes'] == changed_receipt['capture']['completedIrqRefreshes'],
            'Diagnostic changed bounded refresh coverage')
    result = dict(schemaVersion=1, sourceSha256=sha(original), candidateSha256=sha(candidate),
        helperSha256=sha(Path(__file__).read_bytes()), patches=patches,
        baselineCapture=receipt['capture'], candidateCapture=changed_receipt['capture'],
        protectedNonTargetSidBehaviorEqual=True, sidWriterAddressOrderAndIrqAttributionEqual=True,
        protectedScope='Initialization and captured refreshes, including frequency, controls, envelopes, filter, volume, voice 3 PWM and any SID mirrors.',
        changedPulseWrites=len(differences), changedPulseAddressCounts=dict(Counter(f'{row["address"]:04x}' for row in differences)),
        firstChangedIrq=min(row['irqIndex'] for row in differences), lastChangedIrq=max(row['irqIndex'] for row in differences),
        baselineAnalysis=analysis, listeningReview=None,
        limitations='Two source-data bytes changed on an ignored copy. No independent reconstruction, original-host/PCM identity, exact instruction-cycle equality, complete form, human listening verdict or new transferable instrument claim.')
    write_json(output / 'changed-pulse-values.json', differences)
    write_json(output / 'verification.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/research/giana/Great_Giana_Sisters.sid')
    parser.add_argument('--vice', type=Path, default=ROOT / '.tools/vice-headless-3.9/build/src/x64sc')
    args = parser.parse_args()
    result = run(args.baseline.resolve(), args.source.resolve(), args.output.resolve(), args.vice.resolve())
    print(json.dumps(dict(verification=str(args.output.resolve() / 'verification.json'),
                          changedPulseWrites=result['changedPulseWrites'],
                          protectedNonTargetSidBehaviorEqual=result['protectedNonTargetSidBehaviorEqual']), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f'Giana bounded analysis: {error}')
