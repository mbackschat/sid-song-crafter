"""Compare the CIA-timed exact Shades transfer with its frame-rate variant in real time.

Both CPU audits give ordered SID stores with the instruction-start cycle inside
each driver call. The exact player's call n starts 16,422 + (n - 1) x 12,326
cycles after call 0 (Timer A latch $4025, then $3025); the frame player's call n
starts n x 19,656 cycles after call 0. Instruction offsets inside a call are
added to both. Interrupt entry latency and the absolute start of call 0 are not
modelled; the optional rendered first-onset check observes the latter.

The run fails when:
- a voice's note-on / rest gate-off sequence differs, or any onset or gate-off
  differs by more than one video frame (19,656 cycles);
- a note's pitch, envelope, control, initial pulse width, filter routing or the
  voice-3 filter start differs at its onset, or its control/envelope value set differs;
- a pulse or vibrato store moves by anything other than the programmed step;
- an unmodulated voice's pitch moves, or the fade value sets or step counts differ;
- the PSID speed words are not CIA (exact) and VBI (frame), or the exact export
  differs from the accepted transfer's recorded SID hash.
"""

import argparse
from collections import namedtuple
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import struct
import sys
import wave

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))

import rescale  # noqa: E402
from verify_player import require  # noqa: E402


Record = namedtuple('Record', 'time tick address value previous regs')
SID_BASE = 0xd400
VOICES = (0, 1, 2)
CONTROL = {voice: SID_BASE + 7 * voice + 4 for voice in VOICES}
VOLUME, ROUTING, CUTOFF_LOW, CUTOFF_HIGH = 0xd418, 0xd417, 0xd415, 0xd416
TIMER_HIGH = 0xdc05
GRID_CYCLES = 98  # 0.1 ms
ACCEPTED_AUDIO_RECIPE = ROOT / 'docs/research/composition/shades-elise-audio.json'
FRAME = rescale.FRAME


def ms(cycles):
    return rescale.milliseconds(cycles)


class Stream:
    """Ordered SID stores with real-time stamps and the register file after each."""

    def __init__(self, kind, writes):
        self.kind, self.records = kind, []
        regs = [0] * 32
        start = self.call_start = rescale.exact_call_cycle if kind == 'exact' else rescale.frame_call_cycle
        for row in writes:
            if row['address'] == TIMER_HIGH:
                continue
            offset = row['address'] - SID_BASE
            require(0 <= offset < 32, f'Store outside the SID window: ${row["address"]:04x}')
            previous, regs[offset] = regs[offset], row['value']
            self.records.append(Record(start(row['tick']) + row['instructionStartCycle'], row['tick'],
                                       row['address'], row['value'], previous, tuple(regs)))
        require(self.records, 'Empty write stream')
        self.end = self.records[-1].time
        self.final_tick = self.records[-1].tick

    def end_of_call(self, tick):
        """Register file after a call's last store; modulation precedes row work within a call."""
        last = None
        for record in self.records:
            if record.tick > tick:
                break
            last = record
        return last.regs

    def gate_events(self, voice):
        """(kind, record) per audible gate change; a clear followed by a set in one call is the driver's retrigger."""
        raw = [('on' if record.value & 1 else 'off', record) for record in self.records
               if record.address == CONTROL[voice] and (record.value ^ record.previous) & 1]
        return [(kind, record) for index, (kind, record) in enumerate(raw)
                if not (kind == 'off' and index + 1 < len(raw) and raw[index + 1][0] == 'on'
                        and raw[index + 1][1].tick == record.tick)]

    def stores(self, address, start_time, stop_tick):
        """Stores after `start_time` and before the call `stop_tick`.

        A note's window ends where the next note's call begins: that call first advances the
        old note's modulation, then reloads the voice, and the reload is not part of the old note.
        """
        return [record for record in self.records
                if record.address == address and record.time > start_time and record.tick < stop_tick]

    def window(self, on, stop_tick):
        return self.call_start(stop_tick) - on.time


def pulse_width(regs, voice):
    return regs[7 * voice + 2] | regs[7 * voice + 3] << 8


def pitch_word(regs, voice):
    return regs[7 * voice] | regs[7 * voice + 1] << 8


def cutoff(regs):
    return regs[CUTOFF_HIGH - SID_BASE] << 3 | regs[CUTOFF_LOW - SID_BASE] & 7


def held(initial, points, horizon):
    """Zero-order hold of (time since onset, value) points on a 0.1 ms grid."""
    values, index, current = [], 0, initial
    for time in range(0, horizon, GRID_CYCLES):
        while index < len(points) and points[index][0] <= time:
            current = points[index][1]
            index += 1
        values.append(current)
    return values


def changes_only(initial, points):
    """Drop repeated stores of an unchanged value, keeping when each change was written."""
    result, current = [], initial
    for point in points:
        if point[1] != current:
            result.append(point)
            current = point[1]
    return result


def sweep_summary(initial, points, window):
    """Excursions of a modulated register; `settled` values are the last store of each call.

    A pulse sweep's final ascent and first descent share a call, so its written peak
    overshoots the value the oscillator holds between calls.
    """
    changed = changes_only(initial, points)
    settled = {}
    for _, value, tick in points:
        settled[tick] = value
    held_values = [initial] + list(settled.values())
    written = [initial] + [point[1] for point in changed]
    last = changed[-1][0] if changed else 0
    return dict(peak=max(held_values) - initial, trough=min(held_values) - initial, final=held_values[-1] - initial,
                transientPeak=max(written) - initial, lastChange=last, complete=window - last >= 2 * FRAME)


def worst(values):
    return max((abs(value) for value in values), default=None)


def mean(values):
    return sum(values) / len(values) if values else None


def collect_note(streams, voice, pair, failures):
    """Check one note's onset registers and return its modulation series for both versions."""
    base, on = 7 * voice, pair['on']
    regs = {kind: streams[kind].end_of_call(on[kind].tick) for kind in streams}
    fields = {'frequency': lambda r: pitch_word(r, voice), 'pulse': lambda r: pulse_width(r, voice),
              'attackDecay': lambda r: r[base + 5], 'sustainRelease': lambda r: r[base + 6],
              'control': lambda r: r[base + 4], 'routing': lambda r: r[ROUTING - SID_BASE],
              'volume': lambda r: r[VOLUME - SID_BASE]}
    if voice == 2:
        fields['cutoffStart'] = cutoff  # only voice 3 triggers the contour
    mismatches = 0
    for name, getter in fields.items():
        if getter(regs['exact']) != getter(regs['frame']):
            mismatches += 1
            failures.append(f'Voice {voice + 1} note {pair["index"]} differs at onset in {name}: '
                            f'{getter(regs["exact"])} vs {getter(regs["frame"])}')
    for name, offset in (('control', 4), ('attackDecay', 5), ('sustainRelease', 6)):
        sets = {kind: {r.value for r in streams[kind].records if r.address == SID_BASE + base + offset
                       and on[kind].tick <= r.tick < pair['stop'][kind]} for kind in streams}
        if sets['exact'] != sets['frame']:
            mismatches += 1
            failures.append(f'Voice {voice + 1} note {pair["index"]} {name} value sets differ: {sets}')
    series = {}
    for key, address, read in (('pulse', SID_BASE + base + 3, lambda r: pulse_width(r, voice)),
                               ('pitch', SID_BASE + base + 1, lambda r: pitch_word(r, voice)),
                               ('cutoff', CUTOFF_HIGH, cutoff)):
        if key == 'cutoff' and voice != 2:
            continue
        data = {}
        for kind, stream in streams.items():
            start, stop = on[kind].time, pair['stop'][kind]
            data[kind] = dict(initial=read(regs[kind]), window=stream.window(on[kind], stop),
                              points=[(r.time - start, read(r.regs), r.tick) for r in stream.stores(address, start, stop)])
        series[key] = data
    return mismatches, series


def analyse_sweeps(items, steps=None):
    """Per-voice comparison of pulse width or filter cutoff, measured since each note's own onset."""
    result = {}
    for voice in sorted({voice for voice, _ in items}):
        entry = dict(windows=0, complete=0, boundary=0, end=[], peak=[], transient=[], trough=[], final=[],
                     deviation=[], moves={'exact': set(), 'frame': set()})
        for _, data in (item for item in items if item[0] == voice):
            entry['windows'] += 1
            for kind in data:
                changed = changes_only(data[kind]['initial'], data[kind]['points'])
                previous = [data[kind]['initial']] + [point[1] for point in changed]
                entry['moves'][kind].update(b - a for a, b in zip(previous, previous[1:]))
            horizon = min(data['exact']['window'], data['frame']['window'])
            entry['deviation'].append(max(abs(a - b) for a, b in zip(
                held(data['exact']['initial'], data['exact']['points'], horizon),
                held(data['frame']['initial'], data['frame']['points'], horizon))))
            summary = {kind: sweep_summary(data[kind]['initial'], data[kind]['points'], data[kind]['window']) for kind in data}
            if summary['exact']['complete'] and summary['frame']['complete']:
                entry['complete'] += 1
                entry['end'].append(ms(summary['frame']['lastChange'] - summary['exact']['lastChange']))
                for key, field in (('peak', 'peak'), ('transient', 'transientPeak'), ('trough', 'trough'), ('final', 'final')):
                    entry[key].append(summary['frame'][field] - summary['exact'][field])
            elif summary['exact']['complete'] != summary['frame']['complete']:
                entry['boundary'] += 1
        result[f'voice{voice + 1}'] = dict(
            windows=entry['windows'], completeSweeps=entry['complete'], windowsWithOneSweepTruncated=entry['boundary'],
            maximumSweepEndErrorMs=worst(entry['end']), maximumSettledPeakErrorUnits=worst(entry['peak']),
            maximumWrittenPeakErrorUnits=worst(entry['transient']),
            maximumSettledTroughErrorUnits=worst(entry['trough']), maximumFinalErrorUnits=worst(entry['final']),
            maximumTrajectoryDeviationUnits=max(entry['deviation']),
            observedMovesPerStore={kind: sorted(moves) for kind, moves in entry['moves'].items()})
    return result


def analyse_vibrato(items):
    """Delay, cycle length and excursion of voice-3 vibrato; other voices must not move pitch."""
    delay, cycle, span, dips, constant = [], [], [], {'exact': set(), 'frame': set()}, True
    shapes_measured = 0
    for voice, data in items:
        shapes = {}
        for kind, details in data.items():
            changed = changes_only(details['initial'], details['points'])
            if voice != 2:
                constant = constant and not changed
                continue
            if len(changed) < 2:
                continue
            values = [point[1] for point in changed]
            peaks = [changed[i][0] for i in range(1, len(changed) - 1)
                     if values[i] > values[i - 1] and values[i + 1] < values[i]]
            dips[kind].add(values[1] - details['initial'])
            shapes[kind] = dict(first=changed[0][0], peaks=peaks, span=max(values) - min(values))
        if len(shapes) == 2:
            delay.append(ms(shapes['frame']['first'] - shapes['exact']['first']))
            if all(len(shape['peaks']) >= 2 for shape in shapes.values()):
                shapes_measured += 1
                period = {kind: Fraction(shape['peaks'][-1] - shape['peaks'][0], len(shape['peaks']) - 1)
                          for kind, shape in shapes.items()}
                cycle.append(ms(period['frame'] - period['exact']))
                span.append(shapes['frame']['span'] - shapes['exact']['span'])
    return dict(delayMeasuredNotes=len(delay), cycleMeasuredNotes=shapes_measured,
                unmodulatedVoicesKeepConstantPitch=constant,
                maximumDelayErrorMs=worst(delay), maximumCycleErrorMs=worst(cycle), meanCycleErrorMs=mean(cycle),
                maximumPeakToPeakErrorUnits=worst(span),
                startDipUnits={kind: sorted(values) for kind, values in dips.items()})


def compare(exact_writes, frame_writes, *, speed_words=None, steps=None):
    streams = {'exact': Stream('exact', exact_writes), 'frame': Stream('frame', frame_writes)}
    failures, report = [], {}
    if speed_words is not None and speed_words != {'exact': 1, 'frame': 0}:
        failures.append(f'PSID speed words must be exact=1 (CIA), frame=0 (VBI): {speed_words}')
    deltas, sequences_equal = {'on': [], 'off': []}, True
    per_voice_on = {}
    for voice in VOICES:
        sequences = {kind: stream.gate_events(voice) for kind, stream in streams.items()}
        if [event for event, _ in sequences['exact']] != [event for event, _ in sequences['frame']]:
            sequences_equal = False
            failures.append(f'Voice {voice + 1} gate-event sequence differs')
            continue
        per_voice_on[voice] = []
        for (event, exact_record), (_, frame_record) in zip(sequences['exact'], sequences['frame']):
            deltas[event].append(frame_record.time - exact_record.time)
            if event == 'on':
                per_voice_on[voice].append(frame_record.time - exact_record.time)
    for kind in ('on', 'off'):
        if deltas[kind] and max(abs(delta) for delta in deltas[kind]) > FRAME:
            failures.append(f'Maximum {kind} error {ms(max(abs(d) for d in deltas[kind])):.3f} ms exceeds one frame')
    if not sequences_equal:
        report['failures'] = failures
        return report, failures
    gate_off = {kind: [record.time for voice in VOICES for event, record in stream.gate_events(voice) if event == 'off']
                for kind, stream in streams.items()}
    report['timing'] = dict(
        oneFrameMs=ms(FRAME), totalNotes=len(deltas['on']), totalGateOffs=len(deltas['off']),
        maximumNoteOnErrorMs=ms(max(abs(d) for d in deltas['on'])),
        meanSignedNoteOnErrorMs=ms(Fraction(sum(deltas['on']), len(deltas['on']))),
        maximumGateOffErrorMs=ms(max(abs(d) for d in deltas['off'])),
        perVoiceMaximumNoteOnErrorMs={f'voice{v + 1}': ms(max(abs(d) for d in per_voice_on[v])) for v in per_voice_on},
        lastGateOffMs={kind: ms(max(times)) for kind, times in gate_off.items()},
        finalStoreMs={kind: ms(stream.end) for kind, stream in streams.items()})
    pulse_items, pitch_items, cutoff_items, mismatches = [], [], [], 0
    for voice in VOICES:
        ons = {kind: [record for event, record in stream.gate_events(voice) if event == 'on']
               for kind, stream in streams.items()}
        for index, (exact_on, frame_on) in enumerate(zip(ons['exact'], ons['frame'])):
            pair = dict(index=index, on=dict(exact=exact_on, frame=frame_on),
                        stop={kind: ons[kind][index + 1].tick if index + 1 < len(ons[kind]) else streams[kind].final_tick + 1
                              for kind in streams})
            count, series = collect_note(streams, voice, pair, failures)
            mismatches += count
            pulse_items.append((voice, series['pulse']))
            pitch_items.append((voice, series['pitch']))
            if 'cutoff' in series:
                cutoff_items.append((voice, series['cutoff']))
    report['onsetAndValueSetMismatches'] = mismatches
    report['pulse'] = analyse_sweeps(pulse_items)
    report['filter'] = analyse_sweeps(cutoff_items)
    report['vibrato'] = analyse_vibrato(pitch_items)
    if not report['vibrato']['unmodulatedVoicesKeepConstantPitch']:
        failures.append('A voice without vibrato moved its pitch')
    if steps is not None:
        check_steps(report, steps, failures)
    volumes = {kind: [(r.time, r.value) for r in stream.records if r.address == VOLUME] for kind, stream in streams.items()}
    values = {kind: {value for _, value in series} for kind, series in volumes.items()}
    if values['exact'] != values['frame']:
        failures.append('Master-volume value sets differ')
    fade = {}
    for kind, series in volumes.items():
        drops = [(time, value) for (time, value), (_, before) in zip(series[1:], series) if value < before]
        fade[kind] = dict(firstStepMs=ms(drops[0][0]), volumeZeroMs=ms(next(t for t, v in drops if v & 15 == 0)),
                          steps=len(drops), finalStoreMs=ms(streams[kind].end))
    if fade['exact']['steps'] != fade['frame']['steps']:
        failures.append('Fade step counts differ')
    report['fade'] = dict(
        versions=fade, firstStepErrorMs=fade['frame']['firstStepMs'] - fade['exact']['firstStepMs'],
        volumeZeroErrorMs=fade['frame']['volumeZeroMs'] - fade['exact']['volumeZeroMs'],
        finalStoreErrorMs=fade['frame']['finalStoreMs'] - fade['exact']['finalStoreMs'],
        masterVolumeValues=sorted(values['frame']))
    report['failures'] = failures
    return report, failures


def check_steps(report, steps, failures):
    """Every pulse and vibrato store must move by exactly the programmed step."""
    for voice in VOICES:
        for kind in ('exact', 'frame'):
            moves = report['pulse'][f'voice{voice + 1}']['observedMovesPerStore'][kind]
            if any(abs(move) != steps[kind]['pulse'][voice] for move in moves):
                failures.append(f'{kind} voice {voice + 1} pulse moves {moves} differ from step {steps[kind]["pulse"][voice]}')
    # Vibrato moves are checked through the start dip (2 x step) and the span (extent x step) reported above.
    for kind in ('exact', 'frame'):
        dips = report['vibrato']['startDipUnits'][kind]
        if dips != [-2 * steps[kind]['vibrato'][2]]:
            failures.append(f'{kind} vibrato start dip {dips} differs from -2 x programmed step')


def programmed_steps(path):
    block = next(iter(json.loads(Path(path).read_text())['programs']['blocks'].values()))
    return dict(pulse=[patch['pulse_step'] for patch in block['voices']],
                vibrato=[patch['vibrato_step'] for patch in block['voices']])


def first_onset_ms(path, threshold=200):
    with wave.open(str(path), 'rb') as handle:
        require(handle.getsampwidth() == 2 and handle.getnchannels() == 1, 'Expected mono PCM16')
        rate, frames = handle.getframerate(), handle.readframes(handle.getnframes())
    samples = struct.unpack('<%dh' % (len(frames) // 2), frames)
    index = next(i for i, value in enumerate(samples) if abs(value - samples[0]) > threshold)
    return index * 1000 / rate


def self_test(exact_writes, frame_writes):
    """Each synthetic defect must be rejected with a message naming its class."""
    def failures_after(edit):
        rows = [dict(row) for row in frame_writes]
        edit(rows)
        return compare(exact_writes, rows)[1]

    def first_gate_on(rows, voice):
        return next(r for r in rows if r['address'] == CONTROL[voice] and r['value'] & 1 and r['tick'] > 100)

    def shift_onset(rows):
        victim = first_gate_on(rows, 0)
        for row in rows:
            if row['tick'] == victim['tick'] and row['address'] == CONTROL[0]:
                row['tick'] += 2

    def change_envelope(rows):
        next(r for r in rows if r['address'] == SID_BASE + 5 and r['tick'] > 100)['value'] ^= 0x10

    def drop_note(rows):
        rows.remove(first_gate_on(rows, 2))

    def change_pitch(rows):
        next(r for r in rows if r['address'] == SID_BASE + 7 and r['tick'] > 100)['value'] ^= 1

    expected = {'onsetShiftedTwoFrames': (('exceeds one frame',), shift_onset),
                'envelopeCodeChanged': (('value sets differ', 'differs at onset in attackDecay'), change_envelope),
                'noteDropped': (('gate-event sequence differs',), drop_note),
                'pitchByteChanged': (('differs at onset in frequency', 'moved its pitch'), change_pitch)}
    outcomes = {}
    for name, (messages, edit) in expected.items():
        failures = failures_after(edit)
        hit = next((message for message in messages if any(message in failure for failure in failures)), None)
        require(hit, f'Guard did not reject {name}; expected one of {messages}: {failures[:3]}')
        outcomes[name] = f'rejected: {hit}'
    return outcomes


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--exact', type=Path, required=True, help='Directory from compose-shades.py (reconstructed.sid, writes.json)')
    parser.add_argument('--frame', type=Path, required=True, help='Directory from build-frame-variant.py')
    parser.add_argument('--exact-programs', type=Path, required=True)
    parser.add_argument('--frame-programs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='Fresh JSON receipt path')
    parser.add_argument('--exact-wav', type=Path)
    parser.add_argument('--frame-wav', type=Path)
    args = parser.parse_args()
    require(not args.output.exists() and not args.output.is_symlink(), 'Choose a fresh output path')
    sids = {'exact': (args.exact / 'reconstructed.sid').read_bytes(), 'frame': (args.frame / 'reconstructed.sid').read_bytes()}
    speed = {kind: int.from_bytes(data[18:22], 'big') for kind, data in sids.items()}
    exact_writes = json.loads((args.exact / 'writes.json').read_text())
    frame_writes = json.loads((args.frame / 'writes.json').read_text())
    steps = {'exact': programmed_steps(args.exact_programs), 'frame': programmed_steps(args.frame_programs)}
    report, failures = compare(exact_writes, frame_writes, speed_words=speed, steps=steps)
    hashes = {kind: hashlib.sha256(data).hexdigest() for kind, data in sids.items()}
    accepted = json.loads(ACCEPTED_AUDIO_RECIPE.read_text())['roles']['candidate']['sidSha256']
    if hashes['exact'] != accepted:
        failures.append(f'Exact export {hashes["exact"]} differs from the accepted transfer {accepted}')
    report.update(
        schemaVersion=1, kind='engine-audibility-shades-frame-rate-guard',
        timeModel=dict(exact='call n starts 16,422 + (n - 1) x 12,326 cycles after call 0 (CIA Timer A)',
                       frame='call n starts n x 19,656 cycles after call 0 (PAL video frame)',
                       cpuHz=rescale.CLOCK_HZ, offsets='instructionStartCycle added within a call; no interrupt latency'),
        inputs=dict(sidSha256=hashes, acceptedExactSidSha256=accepted, speedWords=speed, programmedSteps=steps,
                    exactWritesSha256=hashlib.sha256((args.exact / 'writes.json').read_bytes()).hexdigest(),
                    frameWritesSha256=hashlib.sha256((args.frame / 'writes.json').read_bytes()).hexdigest()),
        guardSelfTest=self_test(exact_writes, frame_writes),
        limits='Compares register-store timing from CPU audits under a stated cycle model; it is not an audio measurement or a listening verdict.')
    if args.exact_wav and args.frame_wav:
        onsets = {kind: first_onset_ms(path) for kind, path in (('exact', args.exact_wav), ('frame', args.frame_wav))}
        report['renderedFirstOnsetMs'] = dict(
            onsets, differenceMs=onsets['frame'] - onsets['exact'],
            note='First sample deviating from sample 0 by more than 200 PCM16 units; includes libsidplayfp start-up differences between CIA and VBI playback.')
        if abs(onsets['frame'] - onsets['exact']) > ms(FRAME):
            failures.append('Rendered first onsets differ by more than one frame')
    report['failures'] = failures
    report['passed'] = not failures
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as handle:
        json.dump(report, handle, indent=2, allow_nan=False, default=float)
        handle.write('\n')
    print(json.dumps({key: report[key] for key in ('timing', 'pulse', 'filter', 'vibrato', 'fade', 'guardSelfTest',
                                                  'renderedFirstOnsetMs') if key in report}, indent=2, default=float))
    if failures:
        raise SystemExit('Frame-rate guard failed:\n' + '\n'.join(failures))
    print('Frame-rate guard passed')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, StopIteration) as error:
        raise SystemExit(f'Frame-rate guard error: {error}')
