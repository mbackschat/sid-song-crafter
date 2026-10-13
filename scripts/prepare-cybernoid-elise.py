"""Prepare preserved Für Elise beats [0, 12) for Cybernoid timbres and a plain pair."""

import argparse
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

from cybernoid_player import compute_writes
from verify_player import require


ROOT = Path(__file__).resolve().parents[1]
PAL_CLOCK = Fraction(17734475, 18)
FRAME_CYCLES = 19656
CALL_SECONDS = FRAME_CYCLES / PAL_CLOCK
SCHEDULE_CALLS = 3
END_BEAT = Fraction(12)
CHROMATIC_WORDS = 87
ROLE_PROGRAMS = (('bass', 1), ('harmony', 5), ('melody', 17))
RUNTIME_FIELDS = ('format', 'frequency_words', 'records', 'vibrato_wait', 'onset_lengths', 'onset_waves',
                  'pulse_slots', 'filter_programs', 'arpeggios', 'drums', 'initial_state', 'sid_init')


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
        instrument = voice.get('instrument')
        require(isinstance(instrument, dict) and set(instrument) == {'waveform', 'attackDecay', 'sustainRelease'}
                and instrument['waveform'] == 16, 'Plain reference requires source triangle instruments')
        for key in ('attackDecay', 'sustainRelease'):
            require(type(instrument[key]) is int and 0 <= instrument[key] <= 255, f'Source {key} must be a byte')
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
            selected.append({'start': start, 'end': end, 'midi': event['midi']})
        selected.sort(key=lambda value: value['start'])
        require(all(previous['end'] <= following['start'] for previous, following in zip(selected, selected[1:])),
                f'Unsupported {role} event overlap')
        events[role] = selected
    return roles, events


def pitch_mapping(events, words):
    require(isinstance(words, list) and len(words) == 257 and
            all(type(word) is int and 0 <= word <= 65535 for word in words), 'Programs require 257 frequency words')
    require(all(word > 0 for word in words[:CHROMATIC_WORDS]), 'Chromatic pitch words must be positive')
    realized = [69 + 12 * math.log2(word * float(PAL_CLOCK) / 2**24 / 440) for word in words[:CHROMATIC_WORDS]]
    entries = []
    for midi in sorted({event['midi'] for values in events.values() for event in values}):
        index = min(range(CHROMATIC_WORDS), key=lambda value: abs(realized[value] - midi))
        cents = (realized[index] - midi) * 100
        require(abs(cents) < 50, f'Source pitch {midi} has no matching chromatic lookup word within half a semitone')
        entries.append({'midi': midi, 'pitchIndex': index, 'frequencyWord': words[index], 'centsError': cents})
    return {entry['midi']: entry['pitchIndex'] for entry in entries}, {
        'method': 'Nearest PAL sounding pitch among the original 87 chromatic lookup entries; retain the original words in both banks.',
        'entries': entries,
        'maximumAbsoluteCentsError': max((abs(entry['centsError']) for entry in entries), default=0),
    }


def prepare_elise(source, programs):
    """Preserve source notes and gaps on the Cybernoid three-call row calendar.

    Source beat boundaries round independently to the nearest scheduled PAL
    call. Notes retain their nearest chromatic lookup identities, including the
    native PAL tuning offset. Native gates lead row ends by three calls; this
    articulation and envelope/onset changes are reported separately from the
    bounded row-calendar error. No glide or tone arpeggio is introduced.
    """
    require(isinstance(programs, dict) and programs.get('format') == 'cybernoid-editable-title-v1',
            'Unsupported Cybernoid programs format')
    require(programs['initial_state']['globals'] ==
            {'tempo_reload': 2, 'tempo_countdown': 0, 'play_flag': 0, 'filter_owner': 0},
            'Transfer requires the cold tempo-two Cybernoid globals')
    for _, index in ROLE_PROGRAMS:
        record = programs['records'][index]
        require(record['packed_gate_filter'] & 0xf0 == 0, 'Transfer requires zero native gate threshold')
        require(record['fx3'] & 0x34 == 0, 'Transfer excludes drum, sweep and tone-arpeggio pitch substitution')
    require(all(value == 0 for value in programs['records'][0].values()), 'Rest record zero must be silent')
    roles, events = excerpt_voices(source)
    bpm = rational(source.get('quarterBpm'), 'Source quarterBpm')
    require(bpm > 0, 'Source quarterBpm must be positive')
    indices, pitch_report = pitch_mapping(events, programs['frequency_words'])
    stop_music = call_at(END_BEAT, bpm)
    require(stop_music > 0, 'Unsupported calendar: the excerpt has no scheduled interval')
    rows = []
    boundaries = {Fraction(0), END_BEAT}
    gate_end_errors, gate_duration_errors = [], []

    def append_row(voice, record, start, end, pitch):
        first, last = call_at(start, bpm), call_at(end, bpm)
        intervals = (last - first) // SCHEDULE_CALLS
        require(1 <= intervals <= 128 and (record == 0 or intervals >= 2),
                'Unsupported calendar: rows require 1..128 scheduled intervals, notes at least two')
        rows.append({'call': first, 'voiceIndex': voice, 'transpose': 0, 'patchSetup': 'initialize',
                     'commands': [{'kind': 'sound', 'index': record},
                                  {'kind': 'duration', 'reload': intervals - 1},
                                  {'kind': 'note', 'sourceNote': pitch}]})
        boundaries.update((start, end))

    for voice, (role, record) in enumerate(ROLE_PROGRAMS):
        cursor = Fraction(0)
        for event in events[role]:
            if cursor < event['start']:
                append_row(voice, 0, cursor, event['start'], 0)
            append_row(voice, record, event['start'], event['end'], indices[event['midi']])
            start, end = call_at(event['start'], bpm), call_at(event['end'], bpm)
            gate_end_errors.append(abs((end - 3) * CALL_SECONDS - event['end'] * 60 / bpm))
            gate_duration_errors.append(abs((end - start - 3) * CALL_SECONDS -
                                           (event['end'] - event['start']) * 60 / bpm))
            cursor = event['end']
        if cursor < END_BEAT:
            append_row(voice, 0, cursor, END_BEAT, 0)
    rows.sort(key=lambda row: (row['call'], -row['voiceIndex']))
    counts = {role: len(events[role]) for role, _ in ROLE_PROGRAMS}
    timing = {
        'clockHz': float(PAL_CLOCK), 'frameCycles': FRAME_CYCLES, 'tempoReload': 2,
        'scheduledCalls': SCHEDULE_CALLS, 'sourceQuarterBpm': source['quarterBpm'],
        'boundaryRounding': 'Nearest scheduled three-call boundary, half up, from each absolute source beat; call zero selects every first row.',
        'maximumBoundaryErrorBoundSeconds': float(SCHEDULE_CALLS * CALL_SECONDS / 2),
        'maximumMeasuredBoundaryErrorSeconds': float(max(abs(call_at(beat, bpm) * CALL_SECONDS - beat * 60 / bpm)
                                                         for beat in boundaries)),
        'nativeGateLeadCalls': SCHEDULE_CALLS,
        'nativeGateLeadSeconds': float(SCHEDULE_CALLS * CALL_SECONDS),
        'maximumMeasuredGateEndErrorSeconds': float(max(gate_end_errors, default=0)),
        'maximumMeasuredGateDurationErrorSeconds': float(max(gate_duration_errors, default=0)),
        'sourceEndCall': stop_music, 'finiteStopCall': stop_music + 128,
        'finiteStopSeconds': float((stop_music + 128) * CALL_SECONDS),
    }
    provenance = {
        'identity': 'Preserved Für Elise arrangement, first repeat body and complete first ending, transferred to Cybernoid timbres.',
        'source': 'songs/fuer-elise.json', 'sourceDescriptionSha256': description_hash(source),
        'sourceEdition': source.get('provenance', {}).get('edition'),
        'programSource': 'songs/cybernoid-title.json', 'programDescriptionSha256': description_hash(programs),
        'excerptBeats': [0, 12], 'retainedEvents': counts,
        'voiceMapping': {role: voice for voice, (role, _) in enumerate(ROLE_PROGRAMS)},
        'programMapping': dict(ROLE_PROGRAMS), 'pitchMapping': pitch_report, 'timing': timing,
        'deliberateChanges': ['Cybernoid records replace the source triangle/envelope timbres; retain their PWM, vibrato, onset and harmony-filter programs.',
                              'Quantize source beat boundaries to the native three-call calendar, retaining its early gate release and PAL lookup tuning.',
                              'Explicit silent-record rows cover source gaps; append 64 release calls and sixteen four-call fade levels after beat 12.'],
        'listeningStatus': 'Pending; deterministic numeric preparation does not establish musical quality.',
    }
    transfer = {key: deepcopy(programs[key]) for key in RUNTIME_FIELDS}
    transfer.update(play_calls=stop_music + 128, rows=rows,
                    ending={'start_call': stop_music, 'release_calls': 64, 'fade_step_calls': 4},
                    sourceEvidence=provenance)
    transfer['sid_init'].update(routing=0x82, mode_volume=15)
    reference = deepcopy(transfer)
    reference['records'] = [dict.fromkeys(record, 0) for record in reference['records']]
    for role, index in ROLE_PROGRAMS:
        instrument = roles[role]['instrument']
        reference['records'][index].update(wave=0x11, attack_decay=instrument['attackDecay'],
                                           sustain_release=instrument['sustainRelease'])
    reference['sid_init'].update(routing=0, mode_volume=15)
    reference['sourceEvidence']['identity'] = 'Generated plain triangle reference from the preserved Für Elise arrangement; not an original performance.'
    reference['sourceEvidence']['deliberateChanges'] = [
        'Retain the transfer score, calendar, native gate articulation, ending and pitch lookup; use the source triangle/envelope patches with no modulation or routed filter.',
    ]
    compute_writes(transfer)
    compute_writes(reference)
    receipt = {
        'evidenceLevel': 'Deterministic source-free score preparation and whole numeric-model execution; no CPU, render or listening claim.',
        'retainedEvents': counts, 'totalRetainedEvents': sum(counts.values()), 'omittedExcerptEvents': 0,
        'timing': timing, 'pitchMapping': pitch_report,
        'transferSha256': description_hash(transfer), 'referenceSha256': description_hash(reference),
        'limits': ['First 12 source beats only; monophonic quarter-beat boundaries without clipping.',
                   'Calendar boundaries are quantized; native gates release three calls before row ends.',
                   'Original chromatic lookup words retain their PAL tuning offset; transient onset pitch is part of the transferred bass program.',
                   'Silent rest records replace the previous patch and can shorten its envelope release.',
                   'No glide or tone arpeggio, and no invented ending notes.'],
    }
    return transfer, reference, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'songs/fuer-elise.json')
    parser.add_argument('--programs', type=Path, default=ROOT / 'songs/cybernoid-title.json')
    parser.add_argument('--transfer-output', type=Path, default=ROOT / 'songs/cybernoid-elise-transfer.json')
    parser.add_argument('--reference-output', type=Path, default=ROOT / 'songs/cybernoid-elise-reference.json')
    parser.add_argument('--check', action='store_true', help='Verify both saved fixtures without changing files')
    args = parser.parse_args()
    source_data, program_data = args.source.read_bytes(), args.programs.read_bytes()
    transfer, reference, receipt = prepare_elise(json.loads(source_data), json.loads(program_data))
    outputs = ((args.transfer_output, transfer), (args.reference_output, reference))
    require(args.transfer_output.resolve() != args.reference_output.resolve(), 'Choose distinct output paths')
    if args.check:
        for path, value in outputs:
            require(path.read_bytes() == encoded(value), f'Saved fixture differs from generated output: {path}')
    else:
        require(all(not path.exists() and not path.is_symlink() for path, _ in outputs),
                'Choose fresh outputs; use --check to verify existing fixtures')
        for path, value in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as handle:
                handle.write(encoded(value))
    receipt.update(sourceFileSha256=hashlib.sha256(source_data).hexdigest(),
                   programFileSha256=hashlib.sha256(program_data).hexdigest())
    print(json.dumps(receipt, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(str(error))
