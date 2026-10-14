"""Prepare the twelve-beat Elise phrase with plain and native Billie Jean sounds."""

import argparse
from copy import deepcopy
from dataclasses import asdict
from fractions import Fraction
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sid_clock import PAL_CLOCK, PAL_FRAME_CYCLES
import billie_jean_player as player
import billie_jean_programs as programs
import billie_jean_score as score


CALL_SECONDS = Fraction(PAL_FRAME_CYCLES) / Fraction(str(PAL_CLOCK))
END_BEAT = Fraction(12)
SOURCE_SHA = '16d8eae4d22f368520589c44e9db399b64092664bee6e1e70ca4b21c60bf0c54'
ROLES = {'melody': 0, 'bass': 1, 'harmony': 2}
NATIVE_OFFSETS = {'melody': 88, 'bass': 32, 'harmony': 24}
PLAIN_OFFSETS = {'melody': 0, 'bass': 8, 'harmony': 16}
COUNTS = {'melody': 35, 'bass': 6, 'harmony': 12}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def semantic_sha(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def location(path):
    path = path.resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def load_palette(composition, directory=ROOT / 'evidence/billie-jean-sound'):
    paths = {name: directory / name for name in ('description.json', 'receipt.json', 'contexts.json')}
    if not paths['contexts.json'].exists():
        paths['contexts.json'] = directory / 'contexts.json.gz'
    originals = {name: path.read_bytes() for name, path in paths.items()}
    decoded = {name: gzip.decompress(raw) if paths[name].suffix == '.gz' else raw
        for name, raw in originals.items()}
    receipt = json.loads(decoded['receipt.json'])
    require(receipt['sourceSha256'] == composition['sourceEvidence']['sha256'] == SOURCE_SHA
        and receipt['playCalls'] == 7107 and receipt['boundaryComparisons'] == 49749,
        'Expected the verified complete Billie Jean sound proof')
    for name in ('description.json', 'contexts.json'):
        require(sha(decoded[name]) == receipt['outputHashes'][name], f'Palette evidence hash differs: {name}')
    require(json.loads(decoded['description.json']) == composition['sound'], 'Composition sound differs from its palette proof')
    require(sha(Path(programs.__file__).read_bytes()) == receipt['toolHashes']['billie_jean_programs.py'],
        'Sound helper differs from the verified palette')
    contexts = json.loads(decoded['contexts.json'])
    require(len(contexts) == receipt['boundaryComparisons'], 'Palette boundary count differs')
    selections = {}
    for role, offset in NATIVE_OFFSETS.items():
        setups = [item for item in contexts if item['stage'] == 'setup' and item['instrumentOffset'] == offset]
        require(setups, f'No verified native setups for {role}')
        notes = [item['before']['base_note'] & 127 for item in setups]
        selections[role] = dict(instrumentOffset=offset,
            observedPhysicalVoices=sorted({item['voice'] + 1 for item in setups}),
            observedSetupCount=len(setups), observedPitchIndexRange=[min(notes), max(notes)],
            exampleSetup=dict(call=setups[0]['call'], physicalVoice=setups[0]['voice'] + 1,
                baseNote=setups[0]['before']['base_note'], path=setups[0]['path']),
            pairedPitchStages=composition['sound']['programs']['pitches'][offset:offset + 8],
            pairedWaveformStages=composition['sound']['programs']['waveforms'][offset:offset + 8])
    return dict(roles=selections, sourceSha256=SOURCE_SHA, audibleRoleClaim=False,
        soundSemanticSha256=semantic_sha(composition['sound']),
        evidence={location(paths[name]): dict(sha256=sha(originals[name]), decodedSha256=sha(decoded[name])) for name in paths},
        selectionRationale={
            'melody': 'Offset 88 supplies relative root and two +24 attack stages, held pulse and delayed vibrato; it has no sync/ring bits or shared cutoff reset.',
            'bass': 'Offset 32 supplies a one-body +1 accent then held pulse; its fixed cutoff 32 and mode 48 are compatible with the harmony bank.',
            'harmony': 'Offset 24 supplies four +12 attack stages then root pulse under the same fixed filter settings. Moving it from source physical voice 2 to voice 3 is an explicit role adaptation.'},
        excludedAlternatives={'72': 'Its unfiltered setup resets shared cutoff to zero.',
            '96': 'Sync stages depend on the companion oscillator context.'})


def call_at(beat, bpm):
    units = beat * 60 / bpm / CALL_SECONDS / 3
    return 3 * ((2 * units.numerator + units.denominator) // (2 * units.denominator))


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


def required_indices(sound, events):
    required = set()
    for role, offset in NATIVE_OFFSETS.items():
        bases = {0} | {event['pitchIndex'] for event in events[role]}
        require(all(0 <= base <= 127 for base in bases), 'Required pitch exceeds the native table or 16-bit SID frequency range')
        required.update(bases)
        cursor, visited = 0, set()
        while True:
            index = (offset + cursor) & 255
            require(index not in visited, 'Selected native program must reach a hold')
            visited.add(index)
            value = sound['programs']['pitches'][index]
            if value == 126:
                break
            if value == 127:
                cursor = sound['instruments'][str(offset)]['wave_loop']
                continue
            pitches = {value & 127} if value >= 128 else {base + value for base in bases}
            require(all(0 <= pitch <= 127 for pitch in pitches), 'Required native attack exceeds the 16-bit SID frequency range')
            required.update(pitches)
            cursor = (cursor + 1) & 255
    return required


def retuned_table(sound, events):
    native = sound['programs']['frequencies']
    required = required_indices(sound, events)
    words, omitted = {}, []
    for key in native:
        index = int(key)
        target = 440 * 2 ** ((index + 12 - 69) / 12)
        word = round(target * 2**24 / PAL_CLOCK)
        if not 0 < word <= 65535:
            require(index not in required, 'Required native attack exceeds the 16-bit SID frequency range')
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
        palClockHz=PAL_CLOCK, nativeTableSha256=semantic_sha(native), retunedTableSha256=semantic_sha(words),
        tableHashEncoding='Sorted-key compact JSON without trailing newline',
        nativeFrequencyWords=deepcopy(native), requiredIndices=sorted(required),
        omittedUnusedIndices=omitted, pitchMapping=mapping,
        adaptation='Retune every supported bank index, including native attack stages; native nonuniform or special entries are not preserved as tuning.')


def numeric_score(events, offsets, end_call, *, hold=False):
    patterns, orders = {}, [None] * 3
    for role, voice in ROLES.items():
        rows, cursor = [], 0

        def append(duration, event=None):
            require(duration % 3 == 0 and duration > 0, 'Unrepresentable three-call row duration')
            if event is None:
                while duration > 96:
                    rows.append(dict(header=223))
                    duration -= 96
            require(duration <= 96, 'Unrepresentable three-call note duration')
            units = duration // 3 - 1
            row = dict(header=192 | units) if event is None else dict(header=128 | (32 if hold else 0) | units,
                instrument=offsets[role] // 8, note=event['pitchIndex'])
            rows.append(row)

        for event in events[role]:
            first, last = event['firstCall'], event['lastCallExclusive']
            if first > cursor:
                append(first - cursor)
            append(last - first, event)
            cursor = last
        if cursor < end_call:
            append(end_call - cursor)
        score.encode_rows(rows)
        patterns[str(voice)] = dict(rows=rows)
        orders[voice] = dict(bytes=[voice, 255])
    initial = [dict(orderCursor=0, patternCursor=0, remaining=0, transpose=0, baseNote=0,
        instrumentOffset=offsets[role], holdFlag=0, patternIndex=voice) for role, voice in ROLES.items()]
    return dict(schema='billie-jean-score-v1', orders=orders, patterns=patterns,
        initialVoices=initial, initialDivider=1, rowDividerReload=2)


def prepare_elise(source, composition, *, source_sha256, composition_sha256, palette):
    roles, events, bpm, boundaries = source_events(source)
    require(composition['schema'] == 'billie-jean-composition-v1', 'Expected the canonical Billie Jean composition')
    require(composition['target'] == dict(clock='pal', sidModel='MOS6581', sidBase=0xd400, frameCycles=19656),
        'Transfer requires the canonical PAL MOS6581 target')
    require(composition['sourceEvidence']['sha256'] == palette['sourceSha256'] == SOURCE_SHA
        and semantic_sha(composition['sound']) == palette['soundSemanticSha256'], 'Native palette binding differs')
    frequencies, tuning = retuned_table(composition['sound'], events)
    end_call = call_at(END_BEAT, bpm)
    audit_calls = end_call + 32 + 1 + 64
    fresh = asdict(programs.VoiceState())
    for field in player.SCORE_INPUTS:
        fresh.pop(field)
    adaptations = [
        'Retune both complete supported frequency banks to PAL A440; preserve native words and hashes in the tuning report.',
        'Quantize absolute onsets and ends to nearest three-call boundaries, preserving all 53 nominal source notes and gaps.',
        'Initialize divider 1 with reload 2 so the first score rows occur at call 0.',
        'Use complete fresh named sound/filter state rather than the incidental source cold image; score owns its four alias fields.',
        'Use melody/bass/harmony on physical voices 1/2/3; shared filter runs harmony, bass, melody. Filtered harmony and bass share cutoff 32 and mode 48.',
        'Native note headers do not hold GATE; native TEST restart, late gate release, attack pitch and vibrato behavior remain unchanged.',
        'Plain triangles use source AD/SR with GATE held across contiguous nominal notes; rests clear GATE and retain the releasing waveform.',
        'Both versions use the native master volume 11 instead of the Elise source volume 15.',
        'Intercept the global wrap at the twelve-beat boundary; freeze actual gate-low controls for 32 calls, then waveform/master stop with 64 confirmation calls.']
    provenance = dict(sourceScore='songs/fuer-elise.json', sourceScoreSha256=source_sha256,
        sourceComposition='evidence/billie-jean-player/composition.json', sourceCompositionSha256=composition_sha256,
        sha256=SOURCE_SHA, selectedSubtune=1, excerptBeats=[0, 12], quarterBpm=72,
        adaptations=adaptations, tuning=tuning, palette=deepcopy(palette), listeningReview=None)
    transfer = dict(schema='billie-jean-composition-v1', target=deepcopy(composition['target']),
        range=dict(auditCalls=audit_calls), ending=dict(startCall=end_call, releaseCalls=32),
        score=numeric_score(events, NATIVE_OFFSETS, end_call), sound=deepcopy(composition['sound']),
        initialSound=dict(voices=[deepcopy(fresh) for _ in range(3)], filter=asdict(programs.FilterState())),
        sourceEvidence=provenance)
    transfer['sound']['programs']['frequencies'] = frequencies
    reference = deepcopy(transfer)
    reference['score'] = numeric_score(events, PLAIN_OFFSETS, end_call, hold=True)
    pitches, waveforms, plain = [126] * 256, [0] * 256, {}
    for role, offset in PLAIN_OFFSETS.items():
        source_instrument = roles[role]['instrument']
        require(source_instrument['waveform'] == 16, 'Plain reference requires source triangles')
        plain[str(offset)] = asdict(programs.Instrument(attack_decay=source_instrument['attackDecay'],
            sustain_release=source_instrument['sustainRelease']))
        pitches[offset], waveforms[offset] = 0, 17
    reference['sound'] = dict(instruments=plain, programs=dict(frequencies=deepcopy(frequencies),
        pitches=pitches, waveforms=waveforms, routing_set=[241, 242, 244], routing_clear=[254, 253, 251]))
    validation = {}
    for label, value in (('reference', reference), ('transfer', transfer)):
        expanded = score.expand(value['score'], end_call + 1)
        require(not any(wrap['tick'] < end_call for wrap in expanded['wraps'])
            and expanded['wraps'] == [dict(tick=end_call, voice=2)], 'Ending does not intercept the first global wrap')
        computed = player.compute(value, contexts=True)
        setups = [item for item in computed['contexts'] if item['stage'] == 'setup']
        require(len(setups) == 53, f'{label} has unexpected note setups')
        stop = end_call + 32
        ending = computed['returns'][stop]['ending']
        require(ending['phase'] == 2 and ending['heldControls'] == [0, 0, 0]
            and ending['modeVolume'] & 15 == 0, f'{label} did not reach its final stop')
        require(not any(item['tick'] is not None and item['tick'] > stop for item in computed['writes']),
            f'{label} wrote after its final stop')
        validation[label] = dict(activeCalls=end_call, auditCalls=audit_calls, finalStopCall=stop,
            confirmationCalls=len(computed['returns']) - stop - 1, noteSetups=len(setups),
            orderedStores=len(computed['writes']), orderedStoresSha256=semantic_sha(computed['writes']))
    report = dict(schemaVersion=1, sourceScoreSha256=source_sha256, sourceCompositionSha256=composition_sha256,
        sourceSidSha256=SOURCE_SHA, sourceTitleUnchanged=True, retainedEvents={role: len(notes) for role, notes in events.items()},
        roleVoices=dict(ROLES), physicalRoleVoices={role: voice + 1 for role, voice in ROLES.items()},
        candidateInstrumentOffsets=dict(NATIVE_OFFSETS), referenceInstrumentOffsets=dict(PLAIN_OFFSETS),
        events=[event for notes in events.values() for event in notes], palette=deepcopy(palette), tuning=tuning,
        adaptations=adaptations, sourceEndCall=end_call, releaseCalls=32, finalStopCall=end_call + 32,
        confirmationCalls=64, auditCalls=audit_calls, renderSeconds=float(audit_calls * CALL_SECONDS),
        maximumBoundaryErrorSeconds=float(max(abs(call_at(beat, bpm) * CALL_SECONDS - beat * 60 / bpm) for beat in boundaries)),
        maximumDurationErrorSeconds=max(abs(event['durationErrorSeconds']) for notes in events.values() for event in notes),
        numericValidation=validation, referenceSha256=sha(encoded(reference)), transferSha256=sha(encoded(transfer)),
        toolHashes={location(path): sha(path.read_bytes()) for path in
            (Path(__file__).resolve(), Path(player.__file__), Path(programs.__file__), Path(score.__file__), ROOT / 'scripts/sid_clock.py')},
        limitations=[
            'The 53 matched pitches/onsets/durations are nominal score events. Native melody has two +24 attack bodies, bass one +1 body, harmony four +12 bodies; these are sound gestures, not extra authored score notes.',
            'Hard restart emits TEST/GATE on the nominal onset and supplies the first ordinary pitch on the next call. Native late release and plain held/legato articulation differ; 53 note setups do not imply 53 fresh envelope attacks.',
            'Rests gate off but keep the releasing waveform and ongoing native pitch/pulse/filter state; nominal gaps are not an acoustic-silence claim.',
            'Fresh numeric execution, score-wrap interception and final stop are checked. Compiled CPU/VICE and PCM checks remain separate; no rendered or listening acceptance.'])
    return reference, transfer, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'songs/fuer-elise.json')
    parser.add_argument('--composition', type=Path, default=ROOT / 'evidence/billie-jean-player/composition.json')
    parser.add_argument('--sound-proof', type=Path, default=ROOT / 'evidence/billie-jean-sound')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/billie-jean-elise/prepared')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    source, native = args.source.read_bytes(), args.composition.read_bytes()
    composition = json.loads(native)
    reference, transfer, report = prepare_elise(json.loads(source), composition, palette=load_palette(composition, args.sound_proof),
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
        raise SystemExit(f'Billie Jean transfer preparation failed: {error}')
