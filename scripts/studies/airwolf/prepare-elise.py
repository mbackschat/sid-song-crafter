"""Prepare the twelve-beat Elise phrase with plain and native Airwolf patches."""

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
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sid_clock import PAL_CLOCK, PAL_FRAME_CYCLES
import airwolf_player as player


CALL_SECONDS = Fraction(PAL_FRAME_CYCLES) / Fraction(str(PAL_CLOCK))
END_BEAT = Fraction(12)
SOURCE_SHA = '03c602da9182759c78ca4d90ad3bd5b223b3eb61f34ea31c2205fffc589bf89f'
ROLES = {'melody': 0, 'bass': 1, 'harmony': 2}
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


def frame_at(beat, bpm):
    frames = beat * 60 / bpm / CALL_SECONDS
    return (2 * frames.numerator + frames.denominator) // (2 * frames.denominator)


def source_events(source):
    require(source.get('quarterBpm') == 72, 'The selected Elise source requires quarter-note BPM 72')
    roles = {voice['name']: voice for voice in source['voices']}
    require(len(source['voices']) == 3 and set(roles) == set(ROLES), 'Expected melody, bass and harmony')
    bpm, events, boundaries = Fraction(72), {}, {Fraction(0), END_BEAT}
    for role in ROLES:
        selected, cursor, last_frame = [], Fraction(0), 0
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
            midi = event['midi']
            require(type(midi) is int and 0 <= midi <= 127, 'Expected a MIDI pitch')
            target = 440 * 2 ** ((midi - 69) / 12)
            word = round(target * 2**24 / PAL_CLOCK)
            require(word <= 65535, 'Required pitch exceeds the 16-bit SID frequency range')
            require(word >= 256, 'Required pitch needs a nonzero frequency high byte')
            first, last = frame_at(start, bpm), frame_at(end, bpm)
            require(last > first, 'Quantization collapsed a source note')
            require(first >= last_frame, 'Quantized source events overlap')
            require(start == cursor or first > last_frame, 'Quantization collapsed a source gap')
            selected.append(dict(role=role, voice=ROLES[role], midi=midi, frequencyWord=word, targetHz=target,
                actualHz=word * PAL_CLOCK / 2**24, centsError=1200 * math.log2(word * PAL_CLOCK / 2**24 / target),
                startBeat=onset, durationBeats=duration, firstFrame=first, lastFrameExclusive=last,
                phase='init' if first == 0 else 'play', tick=None if first == 0 else first - 1,
                onsetErrorSeconds=float(first * CALL_SECONDS - start * 60 / bpm),
                endErrorSeconds=float(last * CALL_SECONDS - end * 60 / bpm),
                durationErrorSeconds=float((last - first) * CALL_SECONDS - (end - start) * 60 / bpm)))
            cursor, last_frame = end, last
            boundaries.update((start, end))
        require(len(selected) == COUNTS[role], f'Expected {COUNTS[role]} retained {role} events')
        require(cursor == END_BEAT or last_frame < frame_at(END_BEAT, bpm), 'Quantization collapsed a final source gap')
        events[role] = selected
    return events, bpm, boundaries


def numeric_rows(events, end_frame):
    points = sorted({0, end_frame} | {boundary for notes in events.values() for event in notes
        for boundary in (event['firstFrame'], event['lastFrameExclusive'])})
    rows = []
    for first, last in zip(points, points[1:]):
        require(2 <= last - first <= 256, 'Native duration bytes cannot represent this row segment')
        notes = [None] * 3
        for role, voice in ROLES.items():
            onset = next((event for event in events[role] if event['firstFrame'] == first), None)
            if onset is not None:
                notes[voice] = onset['frequencyWord']
            elif first == 0 or any(event['lastFrameExclusive'] == first for event in events[role]):
                notes[voice] = 'off'
        rows.append(dict(duration=last - first - 1, notes=notes))
    require(1 <= len(rows) <= 255, 'Transfer rows exceed the native row cursor')
    return rows


def prepare_elise(source, composition, *, source_sha256, composition_sha256,
                  source_path='songs/fuer-elise.json', composition_path='evidence/airwolf-player/composition.json'):
    require(composition['schema'] == 'airwolf-composition-v1', 'Expected the canonical Airwolf composition')
    require(composition['sourceEvidence']['sha256'] == SOURCE_SHA, 'Airwolf source fingerprint differs')
    require(composition['target'] == dict(clock='pal', sidModel='MOS6581', sidBase=54272, frameCycles=19656),
        'Transfer requires explicit PAL MOS6581')
    require(composition['sound'] == player.NATIVE_SOUND, 'Canonical Airwolf native patches differ')
    player.validate(composition)
    events, bpm, boundaries = source_events(source)
    end_frame = frame_at(END_BEAT, bpm)
    end_call = end_frame - 1
    stop = end_call + 32
    audit_calls = stop + 1 + 64
    rows = numeric_rows(events, end_frame)
    input_files = dict(source=dict(path=source_path, sha256=source_sha256),
        composition=dict(path=composition_path, sha256=composition_sha256))
    adaptations = [
        'Use the two native pulse patches for physical melody/bass voices 1/2 and the native triangle for harmony voice 3; retain all AD/SR, master-volume and raw pulse-high writes.',
        'Both versions use direct A440 equal-tempered frequency words at the explicit PAL clock; the source uses direct words rather than an indexed tuning table.',
        'Quantize absolute event boundaries to the nearest PAL update; preserve all 53 nominal notes and source gaps.',
        'Consume the opening melody during init and explicitly gate off initially unused voices. Grid frame q>0 maps to play tick q-1.',
        'At true gaps use authored off commands that clear GATE; null means hold without voice writes. Preserve the waveform during release.',
        'Use plain triangle control on all reference voices, retaining native AD/SR/volume/pulse-high settings rather than the Elise source envelopes.',
        'Intercept the first score rewind at the phrase boundary; hold gate-low controls for 32 calls, then controls/master-volume zero and 64 write-free confirmation calls.']
    source_evidence = dict(sha256=SOURCE_SHA, selectedSubtune=1, inputFiles=deepcopy(input_files),
        sourceCompositionEvidence=deepcopy(composition['sourceEvidence']), excerptBeats=[0, 12], quarterBpm=72,
        adaptations=adaptations, listeningReview=None)
    transfer = dict(schema='airwolf-composition-v1', target=deepcopy(composition['target']),
        range=dict(auditCalls=audit_calls), rows=rows, sound=deepcopy(composition['sound']),
        ending=dict(startCall=end_call, releaseCalls=32), sourceEvidence=source_evidence)
    reference = deepcopy(transfer)
    for voice in reference['sound']['voices']:
        voice['control'] = 17
    validation = {}
    for label, value in (('reference', reference), ('transfer', transfer)):
        computed = player.compute(value)
        pitches = [item for item in computed['writes'] if item['address'] in (0xd401, 0xd408, 0xd40f)]
        require(len(pitches) == 53 and not computed['restartCalls'], f'{label} has unexpected note setups or rewind')
        stopping = [(item['address'], item['value']) for item in computed['writes'] if item['tick'] == stop]
        require(stopping == [(0xd404, 0), (0xd40b, 0), (0xd412, 0), (0xd418, 0)], f'{label} did not reach its final stop')
        require(not any(item['tick'] is not None and item['tick'] > stop for item in computed['writes']),
            f'{label} wrote after its final stop')
        validation[label] = dict(auditCalls=audit_calls, noteSetups=len(pitches), finalStopCall=stop,
            confirmationCalls=len(computed['returns']) - stop - 1, initialState=computed['initial'],
            orderedStores=len(computed['writes']), orderedStoresSha256=semantic_sha(computed['writes']))
    native_words = sorted({note for row in composition['rows'] for note in row['notes'] if type(note) is int})
    observed = []
    for word in native_words:
        frequency = word * PAL_CLOCK / 2**24
        nearest_midi = round(69 + 12 * math.log2(frequency / 440))
        target = 440 * 2 ** ((nearest_midi - 69) / 12)
        observed.append(dict(frequencyWord=word, frequencyHz=frequency, nearestA440Midi=nearest_midi,
            centsFromNearestA440=1200 * math.log2(frequency / target)))
    report = dict(schemaVersion=1, inputFiles=input_files, sourceScoreSha256=source_sha256,
        sourceCompositionSha256=composition_sha256, sourceSidSha256=SOURCE_SHA, sourceTitleUnchanged=True,
        retainedEvents={role: len(notes) for role, notes in events.items()}, roleVoices=dict(ROLES),
        physicalRoleVoices={role: voice + 1 for role, voice in ROLES.items()},
        events=[event for notes in events.values() for event in notes], adaptations=adaptations,
        palette=dict(nativePatches=deepcopy(composition['sound']), referenceControls=[17, 17, 17],
            pulseHighSignificantNibbles=[value & 15 for value in composition['sound']['pulseHigh']],
            pulseWidthWordsAssumingResetLow=[(value & 15) << 8 for value in composition['sound']['pulseHigh']],
            sourcePatchProvenance=deepcopy(composition['sourceEvidence']), hardwareInitializationClaim=False,
            audibleRoleClaim=False,
            selectionRationale='The selected source has two static pulse patches and one static triangle. Reuse the entire native palette in physical order 1, 2, 3; only the plain reference substitutes triangle controls.'),
        tuning=dict(standard='A4 = 440 Hz, equal temperament', palClockHz=PAL_CLOCK,
            formula='round(440 * 2**((MIDI - 69)/12) * 2**24 / PAL_CLOCK)',
            mappingRule='Direct 16-bit frequency words, no MIDI-to-native-index conversion',
            sourceObservedFrequencyWords=observed, sourceFrequencyWordsSha256=semantic_sha(native_words),
            a440WordsSha256=semantic_sha({str(event['midi']): event['frequencyWord']
                for notes in events.values() for event in notes}),
            tableHashEncoding='Sorted-key compact JSON without trailing newline'),
        timing=dict(firstRow='init at grid frame 0', playMapping='play tick t is grid frame t+1',
            nativeDuration='row duration N spans N+1 update frames', endFrame=end_frame),
        sourceEndCall=end_call, releaseCalls=32, finalStopCall=stop, confirmationCalls=64, auditCalls=audit_calls,
        lastAuditFrame=audit_calls, lastAuditTimeFromInitSeconds=float(audit_calls * CALL_SECONDS),
        maximumBoundaryErrorSeconds=float(max(abs(frame_at(beat, bpm) * CALL_SECONDS - beat * 60 / bpm) for beat in boundaries)),
        maximumDurationErrorSeconds=max(abs(event['durationErrorSeconds']) for notes in events.values() for event in notes),
        numericValidation=validation, referenceSha256=sha(encoded(reference)), transferSha256=sha(encoded(transfer)),
        toolHashes={location(path): sha(path.read_bytes()) for path in
            (Path(__file__).resolve(), Path(player.__file__), ROOT / 'scripts/sid_clock.py')},
        limitations=[
            'The selected sound contract has no modulation, instrument changes or shared filter. Do not import other studies’ sound effects.',
            'The native duration byte requires row segments of 2..256 frames. Collapsed notes/gaps, overlaps and unrepresentable segments reject.',
            'Each retained pitch uses a nonzero frequency high byte and fits 16 bits. Unsupported pitches reject rather than clamp.',
            'Only PW-high registers for voices 1/2 are written; low PW and filter registers remain unwritten. A renderer reset supplies their zero state; no physical hardware-state equivalence is claimed.',
            'Off commands preserve releasing waveforms, so numeric gaps do not establish instantaneous acoustic silence. AD/SR are native in both versions; pitched rows explicitly retrigger GATE.',
            'Fresh numeric init/play state and ending are checked. CPU/VICE compilation, PCM and listening remain separate gates.'])
    return reference, transfer, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'songs/fuer-elise.json')
    parser.add_argument('--composition', type=Path, default=ROOT / 'evidence/airwolf-player/composition.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/airwolf-elise/prepared')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    source, native = args.source.read_bytes(), args.composition.read_bytes()
    reference, transfer, report = prepare_elise(json.loads(source), json.loads(native),
        source_sha256=sha(source), composition_sha256=sha(native),
        source_path=location(args.source), composition_path=location(args.composition))
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
        raise SystemExit(f'Airwolf transfer preparation failed: {error}')
