"""Execute the pinned Hülsbeck opening through its bounded high-register contrast."""

import argparse
from collections import Counter
import csv
import gzip
import importlib.util
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('axel_role_host', Path(__file__).with_name('study-huelsbeck.py'))
HOST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOST)
CALLS = 3900
BASS_STEP_ADDRESS = 0xae1f
BASS_STEP_OFFSET = 126 + BASS_STEP_ADDRESS - HOST.LOAD_ADDRESS


def load_gzip(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def stats(values):
    return dict(minimum=min(values), maximum=max(values), counts={str(value): count for value, count in sorted(Counter(values).items())})


def analyze(data, writes, snapshots, observations):
    rate = HOST.PAL_CLOCK / 0x4601
    registers = [bytes.fromhex(row['sid']) for row in snapshots]
    onsets = {voice: [row['tick'] for row in writes if row['writerPc'] == pc]
              for voice, pc in enumerate((0xc61b, 0xc775, 0xc8cf))}
    copies = []
    for row in observations:
        if row['pc'] == 0xcb21 and row['y'] == 15:
            pointer = bytes.fromhex(row['zeroPage'])[-2:]
            address = pointer[0] + 256 * pointer[1]
            HOST.require(0xae00 <= address < 0xae90 and (address - 0xae00) % 24 == 0, 'Unexpected instrument record')
            copies.append(dict(tick=row['tick'], voice=(row['x'] - 15) // 24 + 1, recordIndex=(address - 0xae00) // 24))
    windows = []
    for name, start, end in [('lead-entry', 519, 1031), ('bass-entry', 1543, 2055),
                             ('high-register-phrase', 3111, 3559), ('lower-hook-return', 3591, 3890)]:
        voices = []
        for voice in range(3):
            base = voice * 7
            notes = [tick for tick in onsets[voice] if start <= tick < end]
            onset_words = [registers[tick][base] + 256 * registers[tick][base + 1] for tick in notes]
            onset_pitches = [round(69 + 12 * math.log2(word * HOST.PAL_CLOCK / 2 ** 24 / 440)) for word in onset_words]
            bodies, widths, ages, pitch_only = [], [], [], 0
            for tick in notes:
                next_start = next((other for other in onsets[voice] if other > tick), len(registers))
                off = next((position for position in range(tick, next_start) if not registers[position][base + 4] & 1), next_start)
                bodies.append(off - tick)
                widths.extend(registers[position][base + 2] + 256 * registers[position][base + 3] for position in range(tick, off))
                ages.append(min(off, next_start) - tick - 1)
            active = [row for row in registers[start:end] if row[base + 4] & 0xf0]
            pitch_only = len({row['tick'] for row in writes if start <= row['tick'] < end
                              and row['writerPc'] == (0xc62a, 0xc784, -1)[voice]})
            voices.append(dict(voice=voice + 1, programOnsets=len(notes), pitchOnlyRowCalls=pitch_only,
                               programRecords=dict(Counter(row['recordIndex'] for row in copies if row['voice'] == voice + 1 and start <= row['tick'] < end)),
                               controls=dict(Counter(f'{row[base + 4]:02x}' for row in registers[start:end])),
                               adsr=dict(Counter(f'{row[base + 5]:02x}{row[base + 6]:02x}' for row in registers[start:end])),
                               gatedBodyCalls=stats(bodies) if bodies else None,
                               onsetMidiRange=[min(onset_pitches), max(onset_pitches)] if onset_pitches else None,
                               gatedPulseWidths=stats(widths) if widths and voice < 2 else None,
                               activeFrequencyWordRange=[min(row[base] + 256 * row[base + 1] for row in active),
                                                         max(row[base] + 256 * row[base + 1] for row in active)] if active else None))
        windows.append(dict(name=name, firstCall=start, endCallExclusive=end,
                            nominalSeconds=[start / rate, end / rate], voices=voices))
    # The shared PWM routine at C364/C39B updates full words; record 1 owns its counters and step.
    width, ascending, descending = 0x500, 32, 16
    checked, gate_off_moving = 0, 0
    for tick in range(1543, len(registers)):
        if tick in onsets[0]:
            width, ascending, descending = 0x500, 32, 16
        else:
            if ascending:
                width = (width + 37) & 65535
                ascending -= 1
            if not ascending:
                if descending:
                    width = (width - 37) & 65535
                    descending -= 1
                else:
                    ascending, descending = 32, 16
        HOST.require(registers[tick][2] + 256 * registers[tick][3] == width, f'Independent bass PWM mismatch at call {tick}')
        checked += 1
        if tick and not registers[tick][4] & 1 and registers[tick][2:4] != registers[tick - 1][2:4]:
            gate_off_moving += 1
    gate_gaps = {}
    for voice, (clear_pc, set_pc) in enumerate(((0xc5f3, 0xc61b), (0xc74d, 0xc775))):
        gaps = []
        for onset in (row for row in writes if row['writerPc'] == set_pc):
            clear = next(row for row in writes if row['tick'] == onset['tick'] and row['writerPc'] == clear_pc)
            if not clear['value'] & 8:
                gaps.append(onset['instructionStartCycle'] - clear['instructionStartCycle'])
        gate_gaps[str(voice + 1)] = stats(gaps)
    program_fields = {}
    for name, identity in (('bass', 1), ('lead', 2)):
        offset = 126 + 0xae00 + identity * 24 - HOST.LOAD_ADDRESS
        record = data[offset:offset + 16]
        program_fields[name] = dict(recordIndex=identity, waveform=record[0], attackDecay=record[1], sustainRelease=record[2],
                                   initialPulseWidth=record[4] << 4, ascendingCalls=record[5], descendingCalls=record[6],
                                   pulseStep=record[7], releaseControl=record[8], repeatPulse=bool(record[9] & 0x10))
    return dict(updateRateHz=rate, windows=windows, programFields=program_fields,
                instrumentSelectionsByVoice={str(voice): dict(Counter(row['recordIndex'] for row in copies if row['voice'] == voice)) for voice in (1, 2, 3)},
                leadPulseModel=HOST.verify_pulse_model(writes, snapshots),
                bassPwmModel=dict(initialWidth=0x500, ascendingCalls=32, descendingCalls=16, step=37,
                                  comparedCallStates=checked, movingStatesWithGateOff=gate_off_moving,
                                  nominalNetWidthChangePerUninterruptedCycle=592),
                gateRetriggerInstructionStartGapsCycles=gate_gaps,
                filterRouteCounts=dict(Counter(f'{row[23]:02x}' for row in registers)))


def study(source, output, render_snapshots, vice, rom_data):
    data = source.read_bytes()
    header = HOST.admit_source(data)
    HOST.require(not output.exists() and output.is_relative_to(ROOT / 'build'), 'Choose fresh private study output')
    output.mkdir(parents=True)
    rendered_rows = list(csv.DictReader(render_snapshots.open(), delimiter='\t'))
    HOST.require(len(rendered_rows) > 3500 and float(rendered_rows[-1]['time_ms']) >= 69800,
                 'The declared renderer capture does not cover the 60–70-second question')
    HOST.WATCHED_PCS |= {0xc4ef, 0xc572, 0xc61b, 0xc636}
    report, writes, snapshots = HOST.execute(data, CALLS, output / 'original')
    observations = load_gzip(output / 'original/observations.json.gz')
    analysis = analyze(data, writes, snapshots, observations)
    HOST.require(all(row['value'] == (0 if row['address'] == 0xdc04 else 0x46) for row in report['timerWrites']),
                 'The source changed its established CIA update period')
    HOST.require(data[BASS_STEP_OFFSET] == 37, 'Pinned bass-step byte differs')
    frozen = bytearray(data)
    frozen[BASS_STEP_OFFSET] = 0
    frozen = bytes(frozen)
    (output / 'frozen-bass-pwm.sid').write_bytes(frozen)
    frozen_report, frozen_writes, _ = HOST.execute(frozen, CALLS, output / 'frozen-bass')
    HOST.require(len(writes) == len(frozen_writes), 'Bass intervention changed store count')
    changes = []
    for before, after in zip(writes, frozen_writes):
        HOST.require(all(before[key] == after[key] for key in ('phase', 'tick', 'writerPc', 'address')),
                     'Bass intervention changed store identity')
        if before['value'] != after['value']:
            HOST.require(before['address'] in (0xd402, 0xd403), 'Bass intervention changed another control')
            changes.append(dict(tick=before['tick'], address=before['address'], before=before['value'], after=after['value']))
    HOST.require(changes and report['playCycles'] == frozen_report['playCycles'], 'Bass intervention had no effect or changed callable costs')
    HOST.write_gzip(output / 'bass-intervention-differences.json.gz', changes)
    verification, harness_sha = HOST.run_vice(data, CALLS, output / 'vice-original', vice, rom_data, report, writes)
    result = dict(schemaVersion=1, sourceSha256=HOST.SOURCE_SHA256, calls=CALLS, header=header,
                  steadyTimerPeriodCycles=0x4601, maximumPlayCycles=report['maximumPlayCycles'],
                  analysis=analysis, rendererSnapshotSha256=HOST.digest(render_snapshots.read_bytes()),
                  rendererCapture=dict(rows=len(rendered_rows), firstSeconds=float(rendered_rows[0]['time_ms']) / 1000,
                                       lastSeconds=float(rendered_rows[-1]['time_ms']) / 1000),
                  bassIntervention=dict(changedRamAddress=BASS_STEP_ADDRESS, changedFileOffset=BASS_STEP_OFFSET,
                                        before=37, after=0, changedStoreValues=len(changes),
                                        changedAddresses=sorted({row['address'] for row in changes}),
                                        allOtherOrderedStoreValuesAndIdentitiesEqual=True, identicalCallableCosts=True),
                  vice=verification, harnessSha256=harness_sha,
                  scope='Pinned source initialization through3900calls (~70.94seconds), with ordered callable stores, controlled CIA VICE host and a bass-step intervention. Renderer snapshots are a distinct observation; no source-score export, PCM identity, hardware equivalence or musical acceptance follows.')
    HOST.write_json(output / 'verification.json', result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--render-snapshots', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--vice', type=Path, default=ROOT / '.tools/vice-headless-3.9/build/src/x64sc')
    parser.add_argument('--data', type=Path, default=ROOT / '.tools/vice-headless-3.9/source/data')
    args = parser.parse_args()
    study(args.source.resolve(), args.output.resolve(), args.render_snapshots.resolve(), args.vice.resolve(), args.data.resolve())


if __name__ == '__main__':
    main()
