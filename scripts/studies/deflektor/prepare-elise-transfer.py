"""Prepare matched plain/Deflektor programs on the preserved twelve-beat Elise score."""

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
from deflektor_score import expand_score


PAL_CLOCK = Fraction(17734475, 18)
CALL_SECONDS = Fraction(19656) / PAL_CLOCK
ROLES = ('melody', 'bass', 'harmony')
STUDY = ROOT / 'songs/studies/deflektor-elise-transfer'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def call_at(beat, bpm):
    exact = beat * 60 / bpm / CALL_SECONDS
    return (2 * exact.numerator + exact.denominator) // (2 * exact.denominator)


def number(value, name):
    require(type(value) in (int, float) and math.isfinite(value), f'{name} must be finite')
    return Fraction(str(value))


def source_events(source, mapping):
    require(mapping['schemaVersion'] == 'sid-deflektor-transfer-map-v1', 'Unsupported transfer mapping')
    require(mapping['excerptBeats'] == [0, 12], 'This familiar example covers beats [0,12)')
    require([row['role'] for row in mapping['roles']] == list(ROLES), 'Expected ordered melody/bass/harmony mapping')
    roles = {row['name']: row for row in source['voices']}
    require(len(source['voices']) == len(roles) == 3 and set(roles) == set(ROLES), 'Expected three distinct source roles')
    require(number(source['totalBeats'], 'Source extent') >= 12, 'Source does not cover the excerpt')
    bpm = number(source['quarterBpm'], 'Tempo')
    require(bpm > 0, 'Tempo must be positive')
    events = {}
    for role in ROLES:
        plain = roles[role]['instrument']
        require(plain['waveform'] == 16 and all(type(plain[name]) is int and 0 <= plain[name] <= 255
                for name in ('attackDecay', 'sustainRelease')), 'Plain reference requires source triangles/envelopes')
        selected = []
        for event in roles[role]['events']:
            start = number(event['startBeat'], 'Onset')
            require(start >= 0, 'Negative source onset')
            if start >= 12:
                continue
            require(set(event) == {'startBeat', 'durationBeats', 'midi'}, 'Unsupported source event fields')
            end = start + number(event['durationBeats'], 'Duration')
            require(start < end <= 12, 'Source event crosses the excerpt or has no duration')
            midi = event['midi']
            require(type(midi) is int and 32 <= midi <= 127, 'Pitch cannot be encoded as a native note token')
            first, last = call_at(start, bpm), call_at(end, bpm)
            require(2 <= last - first <= 255, 'Native articulation requires 2..255 calls per note')
            selected.append(dict(startBeat=float(start), endBeat=float(end), startCall=first, endCall=last, midi=midi))
        require(selected and all(a['endBeat'] <= b['startBeat'] and a['endCall'] <= b['startCall']
                for a, b in zip(selected, selected[1:])), 'Source notes must be ordered without overlap')
        events[role] = selected
    return roles, events, bpm


def selected_records(programs, mapping):
    records = {row['recordOffset'] // 9: row for row in programs['score']['recordTable']['records']}
    contexts = {(row['sourceVoiceIndex'], row['sourceNoteCall']): row['recordIndex'] for row in mapping['roles']}
    require(len(contexts) == len(mapping['roles']), 'Source note contexts must be distinct')
    require(all(type(row['recordIndex']) is int and row['recordIndex'] in records for row in mapping['roles']),
            'Selected source record is absent')
    current = [None] * 3
    found = {}
    for operation in expand_score(programs['score'], calls=max(call for _, call in contexts) + 1)['operations']:
        voice = operation['voiceIndex']
        if operation['operation'] == 'instrument':
            current[voice] = operation['recordOffset'] // 9
        elif operation['operation'] == 'note' and (voice, operation['call']) in contexts:
            found[voice, operation['call']] = current[voice]
    require(found == contexts, 'Selected record does not match its declared source note context')
    result = [deepcopy(records[row['recordIndex']]) for row in mapping['roles']]
    for record in result:
        fields = record['fields']
        require(fields[2] & 254 == 64 and fields[8] == 0, 'Transfer requires an uncoupled pulse body')
        require(fields[5] == 2, 'This example preserves the verified native release threshold 2')
    return result


def prepare(source, programs, mapping):
    roles, events, bpm = source_events(source, mapping)
    selected = selected_records(programs, mapping)
    release_seconds = number(mapping['ending']['releaseSeconds'], 'Release seconds')
    confirmation = mapping['ending']['confirmationCalls']
    require(release_seconds > 0 and type(confirmation) is int and confirmation >= 64,
            'Require positive release duration and at least 64 confirmation calls')
    source_end = call_at(Fraction(12), bpm)
    release_calls = math.ceil(release_seconds / CALL_SECONDS)
    stop = source_end + release_calls
    play_calls = stop + 1 + confirmation
    require(play_calls <= 65535, 'Transfer exceeds the compiler call bound')
    records, patterns, orders, slots, adaptations = [], [], [], [], []
    for voice, role in enumerate(ROLES):
        ordinary = deepcopy(selected[voice])
        ordinary['recordOffset'] = voice * 9
        final = deepcopy(ordinary)
        final['recordOffset'] = (voice + 3) * 9
        last_event = events[role][-1]
        extension = stop - last_event['endCall']
        final['fields'][5] += extension
        require(final['fields'][5] <= 255 and stop - last_event['startCall'] <= 255,
                'Final release row/threshold exceeds one byte')
        records.append(ordinary)
        records.append(final)
        slots.extend([voice * 9, (voice + 3) * 9] + [voice * 9] * 6)
        pattern = [0x80]
        cursor = 0

        def rest(duration):
            while duration:
                piece = min(duration, 255)
                pattern.extend((0xa0, piece))
                duration -= piece

        for index, event in enumerate(events[role]):
            rest(event['startCall'] - cursor)
            end = event['endCall']
            if index == len(events[role]) - 1:
                pattern.append(0x81)
                end = stop
            pattern.extend((event['midi'] - 32, end - event['startCall']))
            cursor = end
        pattern.append(255)
        require(len(pattern) <= 256, 'Transfer pattern exceeds native byte cursor')
        patterns.append(dict(patternId=voice, pointer=0, bytes=pattern))
        orders.append(dict(voiceIndex=voice, pointer=0, bytes=[voice, 255]))
        adaptations.append(dict(role=role, sourceRecordIndex=mapping['roles'][voice]['recordIndex'],
            originalEndCall=last_event['endCall'], gateOffCall=last_event['endCall'] - 1,
            extendedRowEndCall=stop, extensionCalls=extension, finalReleaseThreshold=final['fields'][5],
            finalPatchSelectionRestartsPWM=ordinary['fields'][0] & 240 == 0))
    records.sort(key=lambda record: record['recordOffset'])
    score = dict(orders=orders, patterns=patterns, initMappingDefaults=dict(bytes=slots), recordTable=dict(records=records))
    transfer = deepcopy(programs)
    transfer.update(title='Fur Elise with Deflektor tonal programs', author='Beethoven / SID Song Crafter',
        score=score, play_calls=play_calls, score_pitch_programs={})
    for voice in transfer['initial_state']['voices']:
        voice.update(detune=0, score_pitch_selector=0, glide_wait=0, glide_remaining=0, glide_flags=0, glide_step=0)
    transfer['initial_state']['globals'].update(cutoff_low=0, cutoff_high=10, routing=0, mode_volume=15, play_flag=15)
    tuning = []
    for midi in sorted({event['midi'] for notes in events.values() for event in notes}):
        word = programs['frequency_words'][midi - 12]
        cents = 1200 * math.log2((word * float(PAL_CLOCK) / 2**24) / (440 * 2**((midi - 69) / 12)))
        require(abs(cents) < 50, 'Selected native lookup does not match the familiar pitch')
        tuning.append(dict(midi=midi, pitchIndex=midi - 12, sourceNote=midi - 32, frequencyWord=word, centsFromA440=cents))
    boundaries = {0., 12.} | {event[key] for notes in events.values() for event in notes for key in ('startBeat', 'endBeat')}
    maximum_error = max(abs(float(call_at(Fraction(str(beat)), bpm) * CALL_SECONDS - Fraction(str(beat)) * 60 / bpm))
                        for beat in boundaries)
    provenance = dict(source=mapping['source'], sourceSha256=digest(source), programs=mapping['programs'],
        programsSha256=digest(programs), mapping='songs/studies/deflektor-elise-transfer/mapping.json',
        mappingSha256=digest(mapping), sourcePatches=deepcopy(mapping['roles']),
        originalSource=deepcopy(programs['sourceEvidence']), excerptBeats=[0, 12],
        endingAdaptations=adaptations, listeningStatus='Pending; generated familiar transfer, not an original performance.',
        limits=[
            'Absolute source note/gap boundaries round to PAL calls. Gate closes one call before each original note end; global row-boundary suppression can defer audible onset by one call.',
            'Source pulse target/marker arithmetic, low-byte-only wrap, base-zero phase retention, raw-word delayed pitch and contextual shared resonance remain computed native programs.',
            'Score pitch replacements, detune and glide are disabled for this same-note experiment; selected records are uncoupled pulses. Filter modes and routing remain clear.',
            'Each final row extends to a shared stop; its copied patch raises release threshold to preserve the original gate-off. Selecting that final copy restarts base-zero bass/harmony PWM at the final onset.',
            'Continuing programs run during final release. The proposed three-second tail requires rendered verification and human listening; software stop does not establish a natural acoustic ending.',
            'Cold software shadows are explicit inputs, not a claim of source oscillator phase or on-chip state. Destination voices and fresh patch-entry phases differ from the selected title contexts.'])
    transfer['sourceEvidence'] = provenance
    reference = deepcopy(transfer)
    reference.update(title='Fur Elise plain triangle reference')
    reference['sourceEvidence']['listeningStatus'] = 'Pending; generated plain reference from the same score, not a recording.'
    for voice, role in enumerate(ROLES):
        plain = roles[role]['instrument']
        for index in (voice, voice + 3):
            record = reference['score']['recordTable']['records'][index]
            threshold = record['fields'][5]
            record['fields'] = [0, 8, 16, plain['attackDecay'], plain['sustainRelease'], threshold, 0, 0, 0]
            record['contextual_resonance_selector'] = 0
    report = dict(schemaVersion=1, sourceEndCall=source_end, stopCall=stop, play_calls=play_calls,
        renderSeconds=float(play_calls * CALL_SECONDS), cadenceSeconds=float(CALL_SECONDS),
        releaseCalls=release_calls, confirmationCalls=confirmation,
        releaseTailSeconds=[float(source_end * CALL_SECONDS), float(stop * CALL_SECONDS)],
        postStopSeconds=[float((stop + 1) * CALL_SECONDS), float(play_calls * CALL_SECONDS)],
        retainedEvents={role: len(events[role]) for role in ROLES}, events=events, tuning=tuning,
        maximumBoundaryErrorSeconds=maximum_error, endingAdaptations=adaptations,
        inputSha256={mapping['source']: digest(source), mapping['programs']: digest(programs),
                     'songs/studies/deflektor-elise-transfer/mapping.json': digest(mapping)},
        outputSha256={'transfer.json': digest(transfer), 'reference.json': digest(reference)},
        listeningStatus='Pending; execution preparation does not establish musical acceptance.')
    for description in (transfer, reference):
        require(expand_score(description['score'], calls=play_calls)['firstStopCall'] == stop,
                'Every voice must reach the shared ending without an earlier global stop')
    return transfer, reference, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mapping', type=Path, default=STUDY / 'mapping.json')
    parser.add_argument('--output', type=Path, default=STUDY)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    mapping = json.loads(args.mapping.read_text())
    source = json.loads((ROOT / mapping['source']).read_text())
    programs = json.loads((ROOT / mapping['programs']).read_text())
    results = prepare(source, programs, mapping)
    for name, value in zip(('transfer.json', 'reference.json', 'preparation.json'), results):
        path = args.output / name
        if args.check:
            require(path.read_bytes() == encoded(value), f'{path} differs from deterministic preparation')
        else:
            args.output.mkdir(parents=True, exist_ok=True)
            path.write_bytes(encoded(value))
    print(json.dumps(dict(output=str(args.output), retainedEvents=results[2]['retainedEvents'],
                         play_calls=results[2]['play_calls'], renderSeconds=results[2]['renderSeconds'])))


if __name__ == '__main__':
    try:
        main()
    except (KeyError, OSError, ValueError) as error:
        raise SystemExit(f'Deflektor transfer preparation failed: {error}')
