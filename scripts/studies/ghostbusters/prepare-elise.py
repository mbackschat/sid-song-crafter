"""Prepare a matched NTSC Elise phrase with plain and Ghostbusters patches."""

import argparse
from copy import deepcopy
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from sid_clock import NTSC_CLOCK, NTSC_FRAME_CYCLES

spec = importlib.util.spec_from_file_location('ghostbusters_transfer_numeric_player',
    Path(__file__).with_name('player.py'))
player = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = player
spec.loader.exec_module(player)

CALL_SECONDS = Fraction(NTSC_FRAME_CYCLES) / Fraction(str(NTSC_CLOCK))
END_BEAT = Fraction(12)
RENDER_SECONDS = 12
SOURCE_SHA = 'f7f05616972d7fd5ad31df91284edbf4e0917d39422f8d004d50b40501a0dcde'
ROLES = {'melody': 0, 'bass': 1, 'harmony': 2}
NATIVE_INSTRUMENTS = {'melody': 2, 'bass': 1, 'harmony': 7}
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


def call_at(beat, bpm):
    units = beat * 60 / bpm / CALL_SECONDS / 4
    return 4 * ((2 * units.numerator + units.denominator) // (2 * units.denominator))


def source_events(source):
    require(source.get('quarterBpm') == 72, 'The selected Elise source requires quarter-note BPM 72')
    roles = {voice['name']: voice for voice in source['voices']}
    require(len(source['voices']) == 3 and set(roles) == set(ROLES), 'Expected melody, bass and harmony')
    bpm, events, boundaries = Fraction(72), {}, {Fraction(0), END_BEAT}
    for role, voice in ROLES.items():
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
            midi = event['midi']
            require(type(midi) is int and 12 <= midi <= 107, 'Source pitch does not fit the native note-index range')
            first, last = call_at(start, bpm), call_at(end, bpm)
            require(last > first, 'Quantization collapsed a source note')
            require(first >= last_call, 'Quantized source events overlap')
            require(start == cursor or first > last_call, 'Quantization collapsed a source gap')
            require(last - first >= 8, 'Native release requires at least one body quarter before the next onset')
            selected.append(dict(role=role, voice=voice, physicalVoice=voice + 1, midi=midi,
                pitchIndex=midi - 12, startBeat=onset, durationBeats=duration,
                firstCall=first, lastCallExclusive=last, gateOffCall=first + 4,
                envelopeZeroCall=last - 4,
                onsetErrorSeconds=float(first * CALL_SECONDS - start * 60 / bpm),
                endErrorSeconds=float(last * CALL_SECONDS - end * 60 / bpm),
                durationErrorSeconds=float((last - first) * CALL_SECONDS - (end - start) * 60 / bpm),
                gateHighSeconds=float(4 * CALL_SECONDS),
                gateShorteningSeconds=float((last - first - 4) * CALL_SECONDS)))
            cursor, last_call = end, last
            boundaries.update((start, end))
        require(len(selected) == COUNTS[role], f'Expected {COUNTS[role]} retained {role} events')
        require(cursor == END_BEAT or last_call < call_at(END_BEAT, bpm), 'Quantization collapsed a final source gap')
        events[role] = selected
    return roles, events, bpm, boundaries


def retuned_bank(native, events):
    required = {event['pitchIndex'] for notes in events.values() for event in notes}
    required |= {index + 1 for index in required}
    words, omitted = {}, []
    for key in native:
        index = int(key)
        target = 440 * 2 ** ((index + 12 - 69) / 12)
        word = round(target * 2**24 / NTSC_CLOCK)
        if not 0 < word <= 65535:
            require(index not in required, 'Required A440 pitch exceeds the 16-bit SID frequency range')
            omitted.append(index)
        else:
            words[str(index)] = word
    require(all(str(index) in words for index in required), 'Required adjacent vibrato pitch is absent')
    mappings = []
    for midi in sorted({event['midi'] for notes in events.values() for event in notes}):
        index, target = midi - 12, 440 * 2 ** ((midi - 69) / 12)
        original, retuned = native[str(index)], words[str(index)]
        mappings.append(dict(midi=midi, pitchIndex=index, targetHz=target,
            nativeFrequencyWord=original, nativeCentsError=1200 * math.log2(original * NTSC_CLOCK / 2**24 / target),
            retunedFrequencyWord=retuned, retunedCentsError=1200 * math.log2(retuned * NTSC_CLOCK / 2**24 / target)))
    return words, dict(standard='A4 = 440 Hz, equal temperament', clockHz=NTSC_CLOCK,
        mappingRule='pitchIndex = MIDI - 12', nativeTableSha256=semantic_sha(native),
        retunedTableSha256=semantic_sha(words), omittedUnusedIndices=omitted,
        tableHashEncoding='Sorted-key compact JSON without trailing newline', pitchMapping=mappings,
        maximumRetunedPitchErrorCents=max(abs(item['retunedCentsError']) for item in mappings))


def numeric_score(events, end_call):
    patterns, orders = {}, [None] * 3
    for role, voice in ROLES.items():
        rows, cursor = [], 0

        def rest(span):
            require(span > 0 and span % 4 == 0, 'Rest must fit the quarter-call grid')
            units = span // 4
            while units:
                portion = min(32, units)
                rows.append(dict(header=0x40 | portion - 1))
                units -= portion

        for event in events[role]:
            first, last = event['firstCall'], event['lastCallExclusive']
            if first > cursor:
                rest(first - cursor)
            span = last - first
            require(span % 4 == 0 and 8 <= span <= 128, 'Note exceeds the native header duration')
            rows.append(dict(header=0x80 | span // 4 - 1, note=event['pitchIndex'],
                parameter=dict(volume=15, instrument=NATIVE_INSTRUMENTS[role])))
            cursor = last
        if cursor < end_call:
            rest(end_call - cursor)
        # The source body clears AD/SR on the next quarter of this short rest;
        # padded gate-low rows postpone the native reset beyond the render.
        rest(8)
        rest(256)
        player.score.encode_rows(rows)
        patterns[str(voice)] = dict(rows=rows)
        orders[voice] = dict(patterns=[voice])
    initial = dict(orderCursor=0, patternCursor=0, remaining=0, note=0, header=0, instrument=0)
    return dict(schemaVersion=1, orders=orders, patterns=patterns,
        initialState=dict(phase=0, voices=[deepcopy(initial) for _ in range(3)]))


def verify_notes(composition, events):
    computed = player.compute(composition, contexts=True)
    onsets = [context for context in computed['contexts']
        if context['kind'] == 'onset' and not context['inputs']['header'] & 64]
    for role, voice in ROLES.items():
        actual = [(context['call'], context['inputs']['note']) for context in onsets if context['voice'] == voice]
        expected = [(event['firstCall'], event['pitchIndex']) for event in events[role]]
        require(actual == expected, f'{role} pitch/order differs from the preserved source phrase')
    require(len(onsets) == 53 and not computed['resetCalls'], 'Transfer added notes or reset within the excerpt')
    return computed, dict(auditCalls=len(computed['returns']), noteSetups=len(onsets),
        pitchOrderMatchesSource=True, resetCalls=computed['resetCalls'], orderedStores=len(computed['writes']),
        orderedStoresSha256=semantic_sha(computed['writes']), initialState=computed['initial'])


def prepare_elise(source, composition, *, source_sha256, composition_sha256):
    player.validate(composition)
    require(composition['sound']['sourceEvidence']['sha256'] == SOURCE_SHA, 'Native sound provenance differs')
    roles, events, bpm, boundaries = source_events(source)
    frequencies, tuning = retuned_bank(composition['sound']['frequencies'], events)
    for notes in events.values():
        for event in notes:
            event['frequencyWord'] = frequencies[str(event['pitchIndex'])]
    end_call = call_at(END_BEAT, bpm)
    audit_calls = 4 * math.ceil(Fraction(RENDER_SECONDS) / CALL_SECONDS / 4)
    scored = numeric_score(events, end_call)
    adaptations = [
        'Reuse native patch 2 for melody, 1 for bass and 7 for harmony in physical voices 1, 2, 3; preserve their six numeric fields.',
        'Retune the same frequency bank in both versions to NTSC A440 equal temperament; preserve original words separately in the tuning report.',
        'Round absolute source note/gap boundaries to the nearest four-call grid; retain all 53 nominal pitches and their per-voice order.',
        'Header duration N-1 spans 4*N calls. Clear header $20 so native gate release occurs one quarter after onset and AD/SR clear one quarter before the nominal end.',
        'The plain reference uses source-score triangle AD/SR, GATE-on control and zero vibrato; it shares the native scheduler and score.',
        'Use a gate-low rest at the phrase end, then padded rests beyond the 12-second render. Keep releasing waveforms and master volume; do not add an ending engine or speech.']
    evidence = dict(sourceScore='songs/fuer-elise.json', sourceScoreSha256=source_sha256,
        sourceComposition='evidence/ghostbusters-player/composition.json', sourceCompositionSha256=composition_sha256,
        sourceSidSha256=SOURCE_SHA, excerptBeats=[0, 12], quarterBpm=72, adaptations=adaptations,
        listeningReview=None)
    transfer = player.from_components(scored, composition['sound'], calls=audit_calls)
    transfer['sound']['frequencies'] = frequencies
    transfer['sourceEvidence'] = deepcopy(evidence)
    transfer.update(title='Elise with Ghostbusters patches', author='SID Song Crafter', released='2026 familiar transfer')
    reference = deepcopy(transfer)
    reference['title'] = 'Elise plain triangle reference'
    reference['sound']['patches'] = {'0': dict(pulse_low=0, pulse_high=0, control=16,
        attack_decay=0, sustain_release=0, vibrato_shift=0)}
    for role, index in NATIVE_INSTRUMENTS.items():
        instrument = roles[role]['instrument']
        require(instrument['waveform'] == 16, 'Plain source reference requires triangle instruments')
        plain = deepcopy(composition['sound']['patches'][str(index)])
        plain.update(control=17, attack_decay=instrument['attackDecay'],
            sustain_release=instrument['sustainRelease'], vibrato_shift=0)
        reference['sound']['patches'][str(index)] = plain
    validation = {}
    for label, value in (('reference', reference), ('transfer', transfer)):
        computed, validation[label] = verify_notes(value, events)
        require(all(not row['value'] & 1 for row in computed['writes'] if row['tick'] is not None
            and row['tick'] >= end_call and row['address'] in (0xd404, 0xd40b, 0xd412)), 'Ending reasserted GATE')
    report = dict(schemaVersion=1, sourceScoreSha256=source_sha256, sourceCompositionSha256=composition_sha256,
        sourceSidSha256=SOURCE_SHA, sourceTitleUnchanged=True,
        retainedEvents={role: len(notes) for role, notes in events.items()}, roleVoices=dict(ROLES),
        physicalRoleVoices={role: voice + 1 for role, voice in ROLES.items()},
        events=[event for notes in events.values() for event in notes], tuning=tuning, adaptations=adaptations,
        palette=dict(nativeInstrumentIds=dict(NATIVE_INSTRUMENTS),
            nativePatches={role: deepcopy(composition['sound']['patches'][str(index)]) for role, index in NATIVE_INSTRUMENTS.items()},
            referencePatches=deepcopy(reference['sound']['patches']), volume=15, audibleRoleClaim=False,
            selectionRationale='Verified tonal pulse/vibrato, saw bass and static pulse records; roles remain an audition hypothesis.'),
        timing=dict(firstNote='play call 0, after the original-style 24 init clears', quantumCalls=4,
            quantumSeconds=float(4 * CALL_SECONDS), nativeDuration='Header low five bits N spans 4*(N+1) calls',
            maximumGateShorteningSeconds=max(event['gateShorteningSeconds'] for notes in events.values() for event in notes)),
        sourceEndCall=end_call, auditCalls=audit_calls, renderSeconds=RENDER_SECONDS,
        firstPossibleResetCall=end_call + 264,
        maximumBoundaryErrorSeconds=float(max(abs(call_at(beat, bpm) * CALL_SECONDS - beat * 60 / bpm) for beat in boundaries)),
        maximumDurationErrorSeconds=max(abs(event['durationErrorSeconds']) for notes in events.values() for event in notes),
        ending=dict(gateLowRestStartCall=end_call, restEnvelopeZeroCall=end_call + 4,
            paddedRestEndCall=end_call + 264, waveformStop=False, masterVolumeStop=False),
        numericValidation=validation, referenceSha256=sha(encoded(reference)), transferSha256=sha(encoded(transfer)),
        toolHashes={str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in
            (Path(__file__).resolve(), Path(player.__file__), Path(player.score.__file__), Path(player.programs.__file__), ROOT / 'scripts/sid_clock.py')},
        limitations=[
            'All 53 pitch setups and source gaps are retained on a coarser grid; nominal durations are not full GATE-high durations or guarantees of 53 acoustically distinct attacks.',
            'Native early gate-off and later AD/SR zeroing alter body/tail timing. SID envelope rate changes and release do not imply instantaneous silence; compiled/PCM/listening checks remain separate.',
            'Only patch 2 vibrato is active; its displacement requires encoded duration at least 5. Both base and adjacent frequencies are explicitly retuned.',
            'Padded rest rows delay native reset beyond the render/audit range; this is a bounded release ending, not a permanent stop or an indefinite playback contract.',
            'Music-only reuse: no source executable, captured replay, speech, IRQ context swaps, model/hardware equivalence or listening acceptance.'])
    return reference, transfer, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'songs/fuer-elise.json')
    parser.add_argument('--composition', type=Path, default=ROOT / 'evidence/ghostbusters-player/composition.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'songs/studies/ghostbusters-elise')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    source, native = args.source.read_bytes(), args.composition.read_bytes()
    values = prepare_elise(json.loads(source), json.loads(native), source_sha256=sha(source), composition_sha256=sha(native))
    paths = [args.output / name for name in ('reference.json', 'transfer.json', 'preparation.json')]
    contents = [encoded(value) for value in values]
    if args.check:
        require(all(path.read_bytes() == content for path, content in zip(paths, contents)), 'Saved transfer preparation differs')
    else:
        require(all(not path.exists() and not path.is_symlink() for path in paths), 'Transfer outputs exist; use --check or choose fresh outputs')
        args.output.mkdir(parents=True, exist_ok=True)
        for path, content in zip(paths, contents):
            with path.open('xb') as output:
                output.write(content)
    require(args.source.read_bytes() == source and args.composition.read_bytes() == native, 'A preparation input changed')
    print(json.dumps({key: values[2][key] for key in ('retainedEvents', 'sourceEndCall', 'auditCalls', 'maximumBoundaryErrorSeconds', 'maximumDurationErrorSeconds')}))


if __name__ == '__main__':
    main()
