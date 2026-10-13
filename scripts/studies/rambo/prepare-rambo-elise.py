"""Prepare matched plain/Rambo versions of the preserved twelve-beat Elise phrase."""

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
from rambo_player import LoaderPlayer, compute_player


PAL_CLOCK = Fraction(17734475, 18)
CALL_SECONDS = Fraction(19656, 1) / PAL_CLOCK
ROLES = ('melody', 'bass', 'harmony')
PATCH_SOURCES = ((0, 1763), (1, 2354), (0, 5427))
END_BEAT = Fraction(12)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def call_at(beat, bpm):
    exact = beat * 60 / bpm / CALL_SECONDS
    return (2 * exact.numerator + exact.denominator) // (2 * exact.denominator)


def selected_patches(programs):
    """Read the actual note-entry data banks from the independent source model.

    The selected calls are documented tonal patches, avoiding intro sweeps,
    synchronization and chord pitch replacement in this same-note transfer.
    """
    selected = {}

    class Observer(LoaderPlayer):
        def note(self, event):
            key = event['voiceIndex'], event['call']
            if key in PATCH_SOURCES:
                selected[key] = deepcopy(self.data[event['voiceIndex']])
            super().note(event)

    player = Observer(programs)
    for call in range(max(call for _, call in PATCH_SOURCES) + 1):
        player.play(call)
    require(set(selected) == set(PATCH_SOURCES), 'Selected source note entries are absent')
    patches = [selected[key] for key in PATCH_SOURCES]
    for patch in patches:
        require(patch[24] in (17, 33, 65), 'Transfer requires an uncoupled tonal patch')
        require(not patch[13] & 8, 'Transfer excludes source chord pitch replacement')
    return patches


def source_events(source):
    require(isinstance(source, dict) and isinstance(source.get('voices'), list), 'Expected named source voices')
    roles = {v.get('name'): v for v in source['voices'] if isinstance(v, dict)}
    require(len(source['voices']) == len(roles) == 3 and set(roles) == set(ROLES), 'Expected melody, bass and harmony')
    require(source.get('totalBeats', 0) >= 12, 'Source must include twelve beats')
    bpm_value = source.get('quarterBpm')
    require(type(bpm_value) in (int, float) and math.isfinite(bpm_value) and bpm_value > 0, 'Expected positive finite tempo')
    bpm = Fraction(str(bpm_value))
    events = {}
    for role in ROLES:
        instrument = roles[role].get('instrument', {})
        require(instrument.get('waveform') == 16 and all(type(instrument.get(k)) is int and 0 <= instrument[k] <= 255
                for k in ('attackDecay', 'sustainRelease')), 'Plain reference requires source triangle/envelope values')
        selected = []
        for event in roles[role]['events']:
            require(type(event.get('startBeat')) in (int, float) and math.isfinite(event['startBeat']), 'Expected finite source onset')
            start = Fraction(str(event['startBeat']))
            require(start >= 0, 'Negative source onset')
            if start >= END_BEAT:
                continue
            require(set(event) == {'startBeat', 'durationBeats', 'midi'}, 'Unsupported source event fields')
            require(type(event['durationBeats']) in (int, float) and math.isfinite(event['durationBeats']), 'Expected finite source duration')
            end = start + Fraction(str(event['durationBeats']))
            require(start < end <= END_BEAT, 'Source event crosses phrase boundary or has no duration')
            require(type(event['midi']) is int and 0 <= event['midi'] <= 127, 'Expected MIDI pitch')
            selected.append(dict(start=start, end=end, midi=event['midi']))
        selected.sort(key=lambda e: e['start'])
        require(all(a['end'] <= b['start'] for a, b in zip(selected, selected[1:])), 'Source events overlap')
        events[role] = selected
    require(sum(map(len, events.values())) > 0, 'Source phrase has no notes')
    return roles, events, bpm


def prepare_elise(source, programs):
    roles, events, bpm = source_events(source)
    end_call = call_at(END_BEAT, bpm)
    require(1 <= end_call <= 65000, 'Phrase calendar exceeds supported range')
    patches = selected_patches(programs)
    words = programs['frequencyWords']
    tuning = []
    pitches = {}
    for midi in sorted({e['midi'] for notes in events.values() for e in notes}):
        candidates = [(abs((69 + 12 * math.log2(word * float(PAL_CLOCK) / 2**24 / 440) - midi) * 100), index)
                      for index, word in enumerate(words[:95]) if word > 0]
        require(bool(candidates), 'Missing tonal frequency words')
        cents, index = min(candidates)
        require(cents < 50, 'Source pitch has no lookup match within half a semitone')
        pitches[midi] = index
        tuning.append(dict(midi=midi, pitchIndex=index, frequencyWord=words[index], absoluteCentsError=cents))
    graph, voices = {}, []
    boundaries = {Fraction(0), END_BEAT}
    for voice, role in enumerate(ROLES):
        instructions = []

        def hold(calls):
            while calls:
                size = min(calls, 255)
                instructions.append(dict(kind='row', sourceNote=191, duration=size))
                calls -= size

        cursor = 0
        for event in events[role]:
            first, last = call_at(event['start'], bpm), call_at(event['end'], bpm)
            duration = last - first
            require(first >= cursor and 1 <= duration <= 255, 'Unrepresentable note duration or rounded overlap')
            hold(first - cursor)
            # SOUND decrements this counter on the onset call (rambo_programs.advance_lifetime);
            # duration releases the gate one call before the following absolute boundary.
            instructions.extend([dict(kind='poke-data', offset=27, value=duration),
                                 dict(kind='row', sourceNote=96 + pitches[event['midi']], duration=duration)])
            cursor = last
            boundaries.update((event['start'], event['end']))
        hold(end_call - cursor)
        instructions.append(dict(kind='return'))
        for index, node in enumerate(instructions):
            name = f'{role}-{index}'
            if node['kind'] != 'return':
                node['next'] = f'{role}-{index + 1}'
            graph[name] = node
        voices.append(dict(cursor=f'{role}-0', remaining=1, transpose=0, stackIndex=7,
                           stack=[dict(returnNode=None, repeatRemaining=0) for _ in range(8)]))
    tail_calls = max(patch[28] for patch in patches) + 66
    provenance = dict(source='songs/fuer-elise.json', sourceSha256=digest(source),
                      sourceEdition=source.get('provenance', {}).get('edition'),
                      programs='songs/rambo-loader.json', programsSha256=digest(programs),
                      excerptBeats=[0, 12], roleOrder=list(ROLES),
                      patchSources=[dict(role=role, physicalVoice=voice + 1, noteCall=call)
                                    for role, (voice, call) in zip(ROLES, PATCH_SOURCES)],
                      changes=['Preserve all excerpt notes and source gaps; quantize absolute beat boundaries to single PAL calls.',
                               'Reuse tonal source patch data with fresh sound state; move the later short pulse patch to harmony voice 3.',
                               'Set each note release countdown to its row duration; native gate closure precedes the next boundary by one call.',
                               'Allow native lifetime/PWM/pitch to continue through rests and the tail; do not add ending notes or a master-volume fade.'],
                      listeningStatus='Pending; generated familiar transfer, not an original performance.')
    transfer = dict(format='rambo-loader-composition-v1', profile=deepcopy(programs['profile']),
                    initialization=deepcopy(programs['initialization']), frequencyWords=deepcopy(words),
                    initialData=patches, initialSound=[[0] * 39 for _ in ROLES], dataBanks={},
                    program=graph, voices=voices, morse=deepcopy(programs['morse']),
                    range=dict(auditCalls=end_call + tail_calls), sourceEvidence=provenance)
    reference = deepcopy(transfer)
    for voice, role in enumerate(ROLES):
        patch = reference['initialData'][voice]
        patch[:24] = [0] * 24
        patch[24:27] = [17, roles[role]['instrument']['attackDecay'], roles[role]['instrument']['sustainRelease']]
    reference['sourceEvidence']['listeningStatus'] = 'Generated plain score reference on the same Rambo calendar; not an original recording.'
    reference['sourceEvidence']['changes'] = [
        'Retain the transfer graph, all source notes and gaps, absolute calendar, exact pitch words and native lifetime/gate schedule.',
        'Replace the selected tonal patches with the source triangle waveform and envelopes; disable frequency and pulse modulation.',
        'Patch-source entries identify the retained lifetime values only; this reference does not reuse their timbres.',
    ]
    for candidate in (transfer, reference):
        result = compute_player(candidate)
        require(result['activeMask'] == 0 and all(s['life'] == 0 for s in result['sounds']), 'Transfer did not reach its natural stopped state')
        last = max(w['tick'] for w in result['writes'] if w['phase'] == 'play')
        require(last < candidate['range']['auditCalls'] - 64, 'Transfer lacks quiet confirmation calls')
    report = dict(retainedEvents={role: len(events[role]) for role in ROLES}, pitchMapping=tuning,
                  sourceEndCall=end_call, auditCalls=transfer['range']['auditCalls'],
                  maximumBoundaryErrorSeconds=float(max(abs(call_at(b, bpm) * CALL_SECONDS - b * 60 / bpm) for b in boundaries)),
                  nativeGateLeadSeconds=float(CALL_SECONDS), transferSha256=digest(transfer), referenceSha256=digest(reference),
                  evidenceLevel='Deterministic source-note transfer and numeric stop verification; compilation and listening remain separate.')
    return transfer, reference, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'songs/fuer-elise.json')
    parser.add_argument('--programs', type=Path, default=ROOT / 'songs/rambo-loader.json')
    parser.add_argument('--transfer-output', type=Path, default=ROOT / 'songs/rambo-elise-transfer.json')
    parser.add_argument('--reference-output', type=Path, default=ROOT / 'songs/rambo-elise-reference.json')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    require(args.transfer_output.resolve() != args.reference_output.resolve(), 'Choose distinct outputs')
    outputs = (args.transfer_output, args.reference_output)
    if not args.check:
        require(all(not p.exists() and not p.is_symlink() for p in outputs), 'Choose fresh outputs')
    transfer, reference, report = prepare_elise(json.loads(args.source.read_text()), json.loads(args.programs.read_text()))
    for path, description in zip(outputs, (transfer, reference)):
        if args.check:
            require(path.read_bytes() == encoded(description), f'Saved fixture differs: {path}')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as target:
                target.write(encoded(description))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(str(error))
