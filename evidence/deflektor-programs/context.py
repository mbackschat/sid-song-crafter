"""Locate waveform candidate contexts without treating loaded RAM shadows as SID state."""

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PINS = {
    'events.json.gz': '776c2aaa1effe25b1a70dc53630297b2d90961534db8f5febf4a232d59b4748a',
    'writes.json.gz': '7c1ccca95afc19175b4efc50674f8f1e23783b0dcad525d5955a9cf85523fa00',
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def observed_word(registers, offset):
    lo, hi = registers[offset:offset + 2]
    return None if lo is None or hi is None else lo | hi << 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.output.is_symlink(), 'Choose a fresh context output')
    base = ROOT / 'evidence/deflektor-form/full40000'
    inputs = {}
    for name, expected in PINS.items():
        raw = (base / name).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == expected, f'Canonical evidence pin differs: {name}')
        inputs[name] = json.loads(gzip.decompress(raw))
    events, writes = inputs['events.json.gz'], inputs['writes.json.gz']
    selections = [event for event in events if event['kind'] in ('instrumentSelection', 'noteSetup')]
    timeline = [(event['call'], event['instructionStartCycle'], 0, event) for event in selections]
    timeline += [(row['tick'], row['instructionStartCycle'], 1, row) for row in writes if row['phase'] == 'play']
    registers, selected = [None] * 32, [None] * 3
    onsets, coupled, counts = [], [], Counter()
    control_counts = Counter()
    for call, cycle, kind, item in sorted(timeline, key=lambda row: row[:3]):
        if kind == 0:
            voice = item['voiceIndex']
            if item['kind'] == 'instrumentSelection':
                selected[voice] = item['recordIndex']
                continue
            counts[(voice, selected[voice])] += 1
            if selected[voice] == 0:
                modulator = (voice - 1) % 3
                onsets.append(dict(call=call, instructionStartCycle=cycle, voiceIndex=voice,
                    pitchIndex=item['pitchIndex'], previousCarrierFrequency=observed_word(registers, 7 * voice),
                    previousModulatorVoice=modulator, previousModulatorFrequency=observed_word(registers, 7 * modulator)))
            continue
        offset = item['address'] - 0xd400
        registers[offset] = item['value']
        if offset in (4, 11, 18):
            voice = offset // 7
            control_counts[(selected[voice], item['value'])] += 1
            if selected[voice] == 0 and item['value'] & 0xf6 == 0x16:
                modulator = (voice - 1) % 3
                coupled.append(dict(call=call, instructionStartCycle=cycle, voiceIndex=voice,
                    control=item['value'], carrierFrequency=observed_word(registers, 7 * voice),
                    modulatorVoice=modulator, modulatorFrequency=observed_word(registers, 7 * modulator),
                    modulatorControl=registers[7 * modulator + 4]))
    globals = {f'{address:04x}': sorted({row['value'] for row in writes if row['address'] == address})
               for address in range(0xd415, 0xd419)}
    require(len(onsets) == 109 and coupled, 'Expected recurring record0 coverage missing')
    require(all(value & 15 == 0 for value in globals['d417']) and globals['d418'] == [15],
            'Selected source has unexpected active filter routing/mode writes')
    first = next(item for item in coupled if item['call'] == 644 and item['voiceIndex'] == 0)
    require(first['modulatorFrequency'] is None,
            'First coupled stage unexpectedly has a source-written modulator frequency')
    result = dict(schemaVersion=1, sourceSha256='606ad4cb19e29c060bb77a9b44253dee62d3d972724acb6cddf625fc2466d44d',
        toolSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), dependencies=PINS,
        recordNoteCounts=[dict(voiceIndex=voice, recordIndex=record, notes=count)
                          for (voice, record), count in sorted(counts.items())],
        candidateRecordIndex=0, candidateOnsets=onsets, coupledControlStores=coupled,
        candidateControlCounts=[dict(control=control, writes=count) for (record, control), count in sorted(control_counts.items(), key=lambda row: (row[0][0] if row[0][0] is not None else -1, row[0][1])) if record == 0],
        writtenSharedValues=globals,
        limits=['This is an offline census of retained executed selections/stores, not a synthesis implementation or playback input.',
                'Each frequency is the last pair of bytes written by this source before/at the stated point. Null means one or both bytes have never been written; loaded RAM oscillator shadows do not establish hardware frequency.',
                'No reset frequency is assumed. Last-written words and control bits omit oscillator phase, envelope/filter state and all external boot/game activity.',
                'Candidate control counts include score/rest/stop clear stores while record0 remains selected; they are not all waveform-macro transitions.',
                'Ring/sync bits and repeated zero-sustain staging identify a candidate for listening, not a cowbell or an accepted metallic sound.'])
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(candidateOnsets=len(onsets), coupledControlStores=len(coupled),
                          firstCoupledContext=first, sharedWrittenValues=globals)))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
