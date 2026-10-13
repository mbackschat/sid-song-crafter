"""Prepare preserved Für Elise beats [0, 12) as packed Monty rows and a plain pair."""

import argparse
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))

from monty_title_player import compute_writes
from verify_player import require


PAL_CLOCK = Fraction(17734475, 18)
FRAME_CYCLES = 19656
CALL_SECONDS = FRAME_CYCLES / PAL_CLOCK
SCHEDULE_CALLS = 2
END_BEAT = Fraction(12)
ROLE_PROGRAMS = (('bass', 2), ('harmony', 6), ('melody', 15))
REST_INDEX = 20
RUNTIME_FIELDS = ('format', 'frequency_words', 'frequency_alias_bindings', 'instruments')


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def description_hash(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def rational(value, name):
    require(type(value) in (int, float), f'{name} must be a finite number')
    try:
        return Fraction(str(value))
    except ValueError:
        raise ValueError(f'{name} must be a finite number') from None


def call_at(beat, bpm):
    exact = beat * 60 * PAL_CLOCK / (bpm * FRAME_CYCLES * SCHEDULE_CALLS)
    return SCHEDULE_CALLS * ((2 * exact.numerator + exact.denominator) // (2 * exact.denominator))


def excerpt_voices(source):
    require(isinstance(source, dict) and isinstance(source.get('voices'), list), 'Source requires three named roles')
    roles = {voice.get('name'): voice for voice in source['voices'] if isinstance(voice, dict)}
    require(len(source['voices']) == len(roles) == 3 and set(roles) == {role for role, _ in ROLE_PROGRAMS},
            'Source requires exactly melody, bass and harmony roles')
    require(rational(source.get('totalBeats'), 'Source totalBeats') >= END_BEAT, 'Source must contain the complete excerpt')
    events = {}
    for role, _ in ROLE_PROGRAMS:
        voice = roles[role]
        patch = voice.get('instrument')
        require(isinstance(patch, dict) and set(patch) == {'waveform', 'attackDecay', 'sustainRelease'}
                and patch['waveform'] == 16, 'Plain reference requires source triangle instruments')
        for name in ('attackDecay', 'sustainRelease'):
            require(type(patch[name]) is int and 0 <= patch[name] <= 255, f'Source {name} must be a byte')
        require(isinstance(voice.get('events'), list), f'Source {role} requires events')
        selected = []
        for event in voice['events']:
            require(isinstance(event, dict), f'Source {role} event must be an object')
            start = rational(event.get('startBeat'), 'Event startBeat')
            require(start >= 0, 'Events must not begin before the excerpt')
            if start >= END_BEAT:
                continue
            require(set(event) == {'startBeat', 'durationBeats', 'midi'}, 'Unsupported excerpt event fields')
            duration = rational(event['durationBeats'], 'Event duration')
            require(duration > 0, 'Event duration must be positive')
            end = start + duration
            require(end <= END_BEAT, 'An event crosses the excerpt boundary; clipping is unsupported')
            require((start * 4).denominator == (end * 4).denominator == 1, 'Excerpt requires quarter-beat boundaries')
            require(type(event['midi']) is int and 0 <= event['midi'] <= 127, 'Source pitch must be a MIDI integer')
            selected.append(dict(start=start, end=end, midi=event['midi']))
        selected.sort(key=lambda event: event['start'])
        require(all(previous['end'] <= following['start'] for previous, following in zip(selected, selected[1:])),
                f'Unsupported {role} event overlap')
        events[role] = selected
    return roles, events


def pitch_mapping(events, words):
    require(isinstance(words, list) and len(words) == 96 and
            all(type(word) is int and 0 < word <= 65535 for word in words), 'Programs require 96 positive frequency words')
    realized = [69 + 12 * math.log2(word * float(PAL_CLOCK) / 2**24 / 440) for word in words]
    entries = []
    for midi in sorted({event['midi'] for values in events.values() for event in values}):
        index = min(range(96), key=lambda value: abs(realized[value] - midi))
        cents = (realized[index] - midi) * 100
        require(abs(cents) < 50, f'Source pitch {midi} has no matching lookup word within half a semitone')
        require(index < 95, 'Transfer vibrato requires an adjacent word inside the 96-word table')
        entries.append(dict(midi=midi, pitchIndex=index, frequencyWord=words[index], centsError=cents))
    return {entry['midi']: entry['pitchIndex'] for entry in entries}, dict(
        method='Nearest PAL sounding pitch among the original 96 words; retain those exact words in both descriptions.',
        entries=entries, maximumAbsoluteCentsError=max((abs(entry['centsError']) for entry in entries), default=0))


def pack_patterns(rows, first_id):
    patterns, selected = [], []
    values = []
    for row in rows:
        if len(values) + len(row) + 1 > 256:
            pattern_id = first_id + len(patterns)
            patterns.append(dict(pattern_id=pattern_id, bytes=values + [255]))
            selected.append(pattern_id)
            values = []
        values.extend(row)
    require(values, 'A transfer voice requires rows')
    pattern_id = first_id + len(patterns)
    patterns.append(dict(pattern_id=pattern_id, bytes=values + [255]))
    selected.append(pattern_id)
    require(pattern_id <= 253 and len(selected) < 256, 'Packed score exceeds native pattern/order domains')
    return patterns, selected + [255]


def prepare_elise(source, programs):
    """Preserve the source phrase on Monty's two-call score calendar.

    Native duration fields retain their scheduled gate release two calls
    before row end. Long gaps use consecutive silent rows; notes do not
    acquire octave, drum, descent or portamento pitch replacements. PWM and
    vibrato remain the decoded programs, with an explicit fresh phase for
    this different material. Original source events remain annotations only.
    """
    require(isinstance(programs, dict) and programs.get('format') == 'monty-editable-title-v1',
            'Unsupported Monty programs format')
    require(len(programs['instruments']) == REST_INDEX, 'Transfer requires the twenty-record native bank')
    for _, index in ROLE_PROGRAMS:
        patch = programs['instruments'][index]
        require(patch['effects'] == 0, 'Transfer excludes native drum, descent and octave pitch replacement')
        require(patch['waveform'] in (17, 33, 65), 'Transfer requires an uncoupled tonal waveform with gate')
    roles, events = excerpt_voices(source)
    bpm = rational(source.get('quarterBpm'), 'Source quarterBpm')
    require(bpm > 0, 'Source quarterBpm must be positive')
    pitches, pitch_report = pitch_mapping(events, programs['frequency_words'])
    end_call = call_at(END_BEAT, bpm)
    require(end_call > 0, 'Unsupported calendar: excerpt has no scheduled interval')
    patterns, orders = [], []
    boundaries = {Fraction(0), END_BEAT}
    gate_end_errors, gate_duration_errors = [], []

    for voice, (role, instrument) in enumerate(ROLE_PROGRAMS):
        rows = []
        def append_segment(index, start, end, note):
            first, last = call_at(start, bpm), call_at(end, bpm)
            ticks = (last - first) // SCHEDULE_CALLS
            require(ticks >= 1, 'Unsupported calendar: a row has no scheduled interval')
            require(index == REST_INDEX or 2 <= ticks <= 32,
                    'Unsupported calendar: notes require 2..32 scheduled intervals')
            while ticks:
                count = min(ticks, 32)
                rows.append([0x80 | (count - 1), index, note])
                ticks -= count
            boundaries.update((start, end))
        cursor = Fraction(0)
        for event in events[role]:
            if cursor < event['start']:
                append_segment(REST_INDEX, cursor, event['start'], 0)
            append_segment(instrument, event['start'], event['end'], pitches[event['midi']])
            first, last = call_at(event['start'], bpm), call_at(event['end'], bpm)
            gate_end_errors.append(abs((last - SCHEDULE_CALLS) * CALL_SECONDS - event['end'] * 60 / bpm))
            gate_duration_errors.append(abs((last - first - SCHEDULE_CALLS) * CALL_SECONDS
                                           - (event['end'] - event['start']) * 60 / bpm))
            cursor = event['end']
        if cursor < END_BEAT:
            append_segment(REST_INDEX, cursor, END_BEAT, 0)
        packed, order = pack_patterns(rows, len(patterns))
        patterns.extend(packed)
        orders.append(dict(voice_index=voice, bytes=order))
    counts = {role: len(events[role]) for role, _ in ROLE_PROGRAMS}
    require(sum(counts.values()) > 0, 'Excerpt requires source notes')
    timing = dict(clockHz=float(PAL_CLOCK), frameCycles=FRAME_CYCLES, tempoReload=1,
                  scheduledCalls=SCHEDULE_CALLS, sourceQuarterBpm=source['quarterBpm'],
                  boundaryRounding='Nearest scheduled two-call boundary, half up, from each absolute source beat; call zero selects every first row.',
                  maximumBoundaryErrorBoundSeconds=float(SCHEDULE_CALLS * CALL_SECONDS / 2),
                  maximumMeasuredBoundaryErrorSeconds=float(max(abs(call_at(beat, bpm) * CALL_SECONDS - beat * 60 / bpm)
                                                               for beat in boundaries)),
                  nativeGateLeadCalls=SCHEDULE_CALLS, nativeGateLeadSeconds=float(SCHEDULE_CALLS * CALL_SECONDS),
                  maximumMeasuredGateEndErrorSeconds=float(max(gate_end_errors, default=0)),
                  maximumMeasuredGateDurationErrorSeconds=float(max(gate_duration_errors, default=0)),
                  sourceEndCall=end_call, finiteStopCall=end_call + 128,
                  finiteStopSeconds=float((end_call + 128) * CALL_SECONDS))
    provenance = dict(identity='Preserved Für Elise arrangement, first repeat body and complete first ending, transferred to Monty timbres.',
                      source='songs/fuer-elise.json', sourceDescriptionSha256=description_hash(source),
                      sourceEdition=source.get('provenance', {}).get('edition'),
                      programSource='songs/monty-title-source.json', programDescriptionSha256=description_hash(programs),
                      excerptBeats=[0, 12], retainedEvents=counts,
                      voiceMapping={role: voice for voice, (role, _) in enumerate(ROLE_PROGRAMS)},
                      programMapping=dict(ROLE_PROGRAMS), pitchMapping=pitch_report, timing=timing,
                      programSelection={'bass': 'Record2: narrow tonal pulse with fast envelope and no pitch replacement.',
                                        'harmony': 'Record6: tonal pulse and native vibrato, without PWM or pitch replacement.',
                                        'melody': 'Record15: moving pulse with native vibrato and no pitch replacement.'},
                      deliberateChanges=['Monty tonal records replace source triangle/envelope patches; preserve their native PWM and vibrato.',
                                         'Quantize absolute source beat boundaries to the two-call calendar; gates release two calls before row ends.',
                                         'Use an added silent record for real source gaps and reset PWM delay/direction and held state for this different phrase.',
                                         'Keep native lookup tuning and append 64 release calls followed by sixteen four-call fade levels after beat12.'],
                      modulationLimit='Native vibrato displacement is suppressed for duration fields below eight; quarter-beat notes retain this behavior, while longer melody notes allow displacement.',
                      restLimit='A silent record replaces the previous envelope at gap onset and can shorten its release.',
                      listeningStatus='Pending; source preservation and numeric execution do not establish musical quality.')
    transfer = {key: deepcopy(programs[key]) for key in RUNTIME_FIELDS}
    transfer['instruments'].append(dict.fromkeys(transfer['instruments'][0], 0))
    voice_state = dict(order_cursor=0, pattern_cursor=0, remaining=0, control=0, note=0,
                       instrument_index=REST_INDEX, portamento=0, held_frequency=0,
                       voice_control=0, pulse_delay=0, pulse_direction=0)
    transfer.update(play_calls=end_call + 128,
                    initial_state=dict(globals=dict(tempo_countdown=0, tempo_reload=1, counter=0, status=64,
                                                    mode_volume=15, sfx_priority=0, sfx_flags=255, output_enable=255),
                                       voices=[dict(voice_state) for _ in range(3)]),
                    score=dict(orders=orders, patterns=patterns),
                    ending=dict(start_call=end_call, release_calls=64, fade_step_calls=4), sourceEvidence=provenance)
    reference = deepcopy(transfer)
    for role, index in ROLE_PROGRAMS:
        patch = roles[role]['instrument']
        reference['instruments'][index] = dict(pulse_word=0, waveform=17, attack_decay=patch['attackDecay'],
                                             sustain_release=patch['sustainRelease'], vibrato_depth=0, pulse_value=0, effects=0)
    reference['sourceEvidence']['identity'] = 'Generated plain triangle reference from the preserved Für Elise arrangement; not an original performance.'
    reference['sourceEvidence']['programSelection'] = {role: 'Source triangle waveform with its original AD/SR envelope and no modulation.'
                                                     for role, _ in ROLE_PROGRAMS}
    reference['sourceEvidence']['modulationLimit'] = 'Selected plain reference records disable modulation; preserve transfer calendar and gate articulation.'
    reference['sourceEvidence']['deliberateChanges'] = [
        'Retain transfer notes, gaps, calendar, native gate articulation, ending and exact pitch words; use source triangle/envelope patches without modulation.',
    ]
    compute_writes(transfer)
    compute_writes(reference)
    receipt = dict(evidenceLevel='Deterministic packed-score preparation and whole pure-model execution; no compiled CPU, render or listening claim.',
                   retainedEvents=counts, totalRetainedEvents=sum(counts.values()), omittedExcerptEvents=0,
                   timing=timing, pitchMapping=pitch_report,
                   transferSha256=description_hash(transfer), referenceSha256=description_hash(reference),
                   limits=['First12 source beats only; monophonic quarter-beat boundaries without clipping.',
                           'Boundaries are quantized and native gates release two calls before row ends.',
                           'Silent rest rows can shorten the preceding release; the compared plain reference uses the same row semantics.',
                           'Original lookup tuning is retained; no octave/drum/descent/portamento pitch replacement or invented ending notes.'])
    return transfer, reference, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'songs/fuer-elise.json')
    parser.add_argument('--programs', type=Path, default=ROOT / 'songs/monty-title-source.json')
    parser.add_argument('--transfer-output', type=Path, default=ROOT / 'songs/monty-elise-transfer.json')
    parser.add_argument('--reference-output', type=Path, default=ROOT / 'songs/monty-elise-reference.json')
    parser.add_argument('--check', action='store_true', help='Check both saved fixtures without changing files')
    args = parser.parse_args()
    require(args.transfer_output.resolve() != args.reference_output.resolve(), 'Choose distinct output paths')
    if not args.check:
        require(all(not path.exists() and not path.is_symlink() for path in (args.transfer_output, args.reference_output)),
                'Choose fresh outputs; use --check to verify existing fixtures')
    source_bytes, program_bytes = args.source.read_bytes(), args.programs.read_bytes()
    transfer, reference, receipt = prepare_elise(json.loads(source_bytes), json.loads(program_bytes))
    for path, description in ((args.transfer_output, transfer), (args.reference_output, reference)):
        if args.check:
            require(path.read_bytes() == encoded(description), f'Saved fixture differs from generated output: {path}')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as target:
                target.write(encoded(description))
    receipt.update(sourceFileSha256=hashlib.sha256(source_bytes).hexdigest(),
                   programFileSha256=hashlib.sha256(program_bytes).hexdigest())
    print(json.dumps(receipt, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(str(error))
