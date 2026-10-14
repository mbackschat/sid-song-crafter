"""Prepare the twelve-beat Elise phrase with matched plain and Take On Me sounds."""

import argparse
from copy import deepcopy
from dataclasses import asdict
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sid_clock import PAL_CLOCK, PAL_FRAME_CYCLES
import player
import programs
import score


CALL_SECONDS = Fraction(PAL_FRAME_CYCLES) / Fraction(str(PAL_CLOCK))
END_BEAT = Fraction(12)
ROLES = {'melody': 2, 'bass': 0, 'harmony': 1}
NATIVE_INSTRUMENTS = {'melody': 1, 'bass': 3, 'harmony': 1}
PLAIN_INSTRUMENTS = {'melody': 1, 'bass': 3, 'harmony': 5}
COUNTS = {'melody': 35, 'bass': 6, 'harmony': 12}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def table_sha(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def call_at(beat, bpm):
    units = beat * 60 / bpm / CALL_SECONDS / 2
    return 2 * ((2 * units.numerator + units.denominator) // (2 * units.denominator))


def source_events(source):
    require(source.get('quarterBpm') == 72, 'The selected Elise source requires quarter-note BPM 72')
    roles = {voice['name']: voice for voice in source['voices']}
    require(len(source['voices']) == 3 and set(roles) == set(ROLES), 'Expected melody, bass and harmony')
    bpm, events, boundaries = Fraction(72), {}, {Fraction(0), END_BEAT}
    for role in ROLES:
        selected, cursor, last_call = [], Fraction(0), 0
        for event in roles[role]['events']:
            onset = event['startBeat']
            require(type(onset) in (int, float) and math.isfinite(onset) and onset >= 0, 'Expected a finite nonnegative onset')
            start = Fraction(str(onset))
            if start >= END_BEAT:
                continue
            require(set(event) == {'startBeat', 'durationBeats', 'midi'}, 'Unsupported source event fields')
            duration = event['durationBeats']
            require(type(duration) in (int, float) and math.isfinite(duration) and duration > 0, 'Expected a finite positive duration')
            end = start + Fraction(str(duration))
            require(cursor <= start < end <= END_BEAT, 'Source events overlap or cross the excerpt boundary')
            require(type(event['midi']) is int and 0 <= event['midi'] <= 127, 'Expected a MIDI pitch')
            first, last = call_at(start, bpm), call_at(end, bpm)
            require(last > first, 'Quantization collapsed a source note')
            require(first >= last_call, 'Quantized source events overlap')
            require(start == cursor or first > last_call, 'Quantization collapsed a source gap')
            selected.append(dict(role=role, voice=ROLES[role], midi=event['midi'], pitchIndex=event['midi'] - 12,
                startBeat=onset, durationBeats=duration, firstCall=first, lastCallExclusive=last,
                onsetErrorSeconds=float(first * CALL_SECONDS - start * 60 / bpm),
                endErrorSeconds=float(last * CALL_SECONDS - end * 60 / bpm),
                durationErrorSeconds=float((last - first) * CALL_SECONDS - (end - start) * 60 / bpm)))
            cursor, last_call = end, last
            boundaries.update((start, end))
        require(len(selected) == COUNTS[role], f'Expected {COUNTS[role]} retained {role} events')
        require(cursor == END_BEAT or last_call < call_at(END_BEAT, bpm), 'Quantization collapsed a final source gap')
        events[role] = selected
    return roles, events, bpm, boundaries


def retuned_table(native, events):
    required = {event['pitchIndex'] for notes in events.values() for event in notes}
    required |= {index + 1 for index in required}
    words, omitted = {}, []
    for key in native:
        index = int(key)
        target = 440 * 2 ** ((index + 12 - 69) / 12)
        word = round(target * 2**24 / PAL_CLOCK)
        if not 0 < word <= 65535:
            require(index not in required, 'Required pitch exceeds the 16-bit SID frequency range')
            omitted.append(dict(pitchIndex=index, a440FrequencyWord=word, nativeFrequencyWord=native[key]))
        else:
            words[str(index)] = word
    require(all(str(index) in words for index in required), 'Required pitch exceeds the native table or 16-bit SID frequency range')
    mapping = []
    for midi in sorted({event['midi'] for notes in events.values() for event in notes}):
        index = midi - 12
        target = 440 * 2 ** ((midi - 69) / 12)
        original, retuned = native[str(index)], words[str(index)]
        mapping.append(dict(midi=midi, pitchIndex=index, targetHz=target,
            nativeFrequencyWord=original, nativeCentsError=1200 * math.log2(original * PAL_CLOCK / 2**24 / target),
            retunedFrequencyWord=retuned, retunedCentsError=1200 * math.log2(retuned * PAL_CLOCK / 2**24 / target)))
    return words, dict(standard='A4 = 440 Hz, equal temperament', mappingRule='pitchIndex = MIDI - 12',
        palClockHz=PAL_CLOCK, nativeTableSha256=table_sha(native), retunedTableSha256=table_sha(words),
        tableHashEncoding='Sorted-key compact JSON without trailing newline',
        omittedUnusedIndices=omitted, pitchMapping=mapping)


def numeric_score(events, instruments, end_call):
    patterns, orders = {}, [None] * 3
    for role, voice in ROLES.items():
        rows, cursor = [], 0

        def append(duration, instrument, note):
            require(duration % 2 == 0 and 0 < duration <= 254, 'Unrepresentable even-call row duration')
            rows.append(dict(instrument=instrument, durationUnits=duration // 2, note=note))

        for event in events[role]:
            first, last = event['firstCall'], event['lastCallExclusive']
            if first > cursor:
                append(first - cursor, 0, 0)
            append(last - first, instruments[role], event['pitchIndex'])
            cursor = last
        if cursor < end_call:
            append(end_call - cursor, 0, 0)
        score.encode_rows(rows)
        patterns[str(voice)] = dict(rows=rows)
        orders[voice] = dict(bytes=[voice, 254])
    initial = dict(remaining=1, orderCursor=0, repeat=0, transpose=0, patternCursor=0,
        instrument=0, durationTicks=0, glideStepLow=0, glideStepHigh=0, baseNote=0, glideTarget=0, arpeggio=0)
    return dict(schemaVersion=1, dividerReloads=[0, 0], initialDividers=[0, 0],
        orders=orders, patterns=patterns, initialVoices=[deepcopy(initial) for _ in range(3)])


def prepare_elise(source, composition, *, source_sha256, composition_sha256):
    roles, events, bpm, boundaries = source_events(source)
    require(composition['schema'] == 'take-on-me-composition-v1', 'Expected the canonical Take On Me composition')
    require(composition['target']['clock'] == 'pal', 'Transfer requires the canonical PAL target')
    native = composition['sound']['programs']['frequencies']
    frequencies, tuning = retuned_table(native, events)
    end_call = call_at(END_BEAT, bpm)
    audit_calls = end_call + 32 + 1 + 64
    source_evidence = dict(sourceScore='songs/fuer-elise.json', sourceScoreSha256=source_sha256,
        sourceComposition='evidence/take-on-me-player/composition.json', sourceCompositionSha256=composition_sha256,
        sourceSidSha256=composition['sourceEvidence']['sha256'], excerptBeats=[0, 12], quarterBpm=72,
        tuning=tuning, listeningReview=None,
        adaptations=['Retune both banks to PAL A440 equal temperament; preserve native words separately in the tuning report.',
            'Quantize absolute onsets and ends to nearest even PAL calls; preserve all 53 nominal events and source gaps.',
            'Use fresh zero sound/modulation state rather than incidental initialized source data.',
            'Use native silent instrument 0 during gaps; candidate gate-half and release rules remain unchanged.',
            'The plain triangle retains GATE between contiguous note setups; its source AD/SR differs from native articulation.',
            'Author a 32-call gate-off release followed by waveform/master-volume stop and 64 confirmation calls.'])
    transfer = dict(schema='take-on-me-composition-v1', target=deepcopy(composition['target']),
        range=dict(auditCalls=audit_calls), ending=dict(startCall=end_call, releaseCalls=32),
        mix=deepcopy(composition['mix']), score=numeric_score(events, NATIVE_INSTRUMENTS, end_call),
        sound=deepcopy(composition['sound']), initialSound=dict(voices=[{}, {}, {}], filter={}),
        sourceEvidence=source_evidence)
    transfer['sound']['programs']['frequencies'] = frequencies
    reference = deepcopy(transfer)
    reference['mix'] = dict(routing=0, modeVolume=source['volume'])
    reference['score'] = numeric_score(events, PLAIN_INSTRUMENTS, end_call)
    plain = {'0': deepcopy(composition['sound']['instruments']['0'])}
    for role, index in PLAIN_INSTRUMENTS.items():
        source_instrument = roles[role]['instrument']
        require(source_instrument['waveform'] == 16, 'Plain reference requires source triangles')
        plain[str(index)] = asdict(programs.Instrument(onset_control=17, body_control=17,
            attack_decay=source_instrument['attackDecay'], sustain_release=source_instrument['sustainRelease']))
    reference['sound'] = dict(instruments=plain, programs=dict(frequencies=deepcopy(frequencies)))
    for label, value in (('reference', reference), ('transfer', transfer)):
        computed = player.compute(value)
        notes = [row for row in computed['rows'] if row['state']['instrument'] != 0]
        require(len(notes) == 53, f'{label} has unexpected note setups')
        require(all(voice['control'] == 0 for voice in computed['returns'][-1]['voices'])
                and computed['returns'][-1]['ending']['modeVolume'] & 15 == 0, f'{label} did not reach its final stop')
    report = dict(schemaVersion=1, sourceScoreSha256=source_sha256, sourceCompositionSha256=composition_sha256,
        sourceSidSha256=composition['sourceEvidence']['sha256'], sourceTitleUnchanged=True,
        retainedEvents={role: len(notes) for role, notes in events.items()}, roleVoices=dict(ROLES),
        candidateInstruments=dict(NATIVE_INSTRUMENTS), referenceInstruments=dict(PLAIN_INSTRUMENTS),
        events=[event for notes in events.values() for event in notes], tuning=tuning,
        sourceEndCall=end_call, releaseCalls=32, finalStopCall=end_call + 32, confirmationCalls=64,
        auditCalls=audit_calls, renderSeconds=float(audit_calls * CALL_SECONDS),
        maximumBoundaryErrorSeconds=float(max(abs(call_at(beat, bpm) * CALL_SECONDS - beat * 60 / bpm) for beat in boundaries)),
        maximumDurationErrorSeconds=max(abs(event['durationErrorSeconds']) for notes in events.values() for event in notes),
        referenceSha256=sha(encoded(reference)), transferSha256=sha(encoded(transfer)),
        toolHashes={str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in
            (Path(__file__).resolve(), Path(player.__file__), Path(programs.__file__), Path(score.__file__), ROOT / 'scripts/sid_clock.py')},
        limitations='Matched numeric score transfer and fresh-state verification. Note setups are nominal events, not a claim of 53 fresh envelope attacks. Native gate/release and pitch modulation remain distinct from the plain triangle. Final numeric silence requires compiled/PCM checks; no listening acceptance.')
    return reference, transfer, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'songs/fuer-elise.json')
    parser.add_argument('--composition', type=Path, default=ROOT / 'evidence/take-on-me-player/composition.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'songs/studies/take-on-me-elise')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    source, native = args.source.read_bytes(), args.composition.read_bytes()
    reference, transfer, report = prepare_elise(json.loads(source), json.loads(native),
        source_sha256=sha(source), composition_sha256=sha(native))
    paths = [args.output / name for name in ('reference.json', 'transfer.json', 'preparation.json')]
    values = [encoded(value) for value in (reference, transfer, report)]
    if args.check:
        require(all(path.read_bytes() == value for path, value in zip(paths, values)), 'Saved transfer preparation differs')
    else:
        require(all(not path.exists() and not path.is_symlink() for path in paths), 'Transfer outputs exist; use --check or choose fresh outputs')
        args.output.mkdir(parents=True, exist_ok=True)
        for path, value in zip(paths, values):
            with path.open('xb') as output:
                output.write(value)
    require(args.source.read_bytes() == source and args.composition.read_bytes() == native, 'A preparation input changed')
    print(json.dumps({key: report[key] for key in ('retainedEvents', 'sourceEndCall', 'auditCalls', 'maximumBoundaryErrorSeconds')}))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f'Take On Me transfer preparation failed: {error}')
