"""Prepare matched plain/Ghouls sounds on the preserved twelve-beat Elise score."""

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
from ghouls_player import GhoulsPlayer


PAL_CLOCK = Fraction(17734475, 18)
CALL_SECONDS = Fraction(19656) / PAL_CLOCK
ROLES = ('melody', 'bass', 'harmony')
PATCH_SOURCES = ((2, 1413), (1, 1413), (2, 1413))
END_BEAT = Fraction(12)
RELEASE_SECONDS = 3
CONFIRMATION_CALLS = 64


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


def selected_patches(programs):
    """Capture full pre-note state and envelope stores from the numeric player."""
    selected = {}

    class Observer(GhoulsPlayer):
        def __init__(self, description):
            self.shadow = {}
            super().__init__(description)

        def write(self, address, value):
            super().write(address, value)
            self.shadow[address] = value

        def operation(self, voice, operation, state):
            key = voice, operation['call']
            if operation['kind'] == 'note' and key in PATCH_SOURCES:
                self._select_filter_restart()
                selected[key] = dict(state=asdict(state), filter=asdict(self.filter),
                    pulseFallback=self.pulse_fallbacks[voice], filterRestartPhase=self.filter_restarts[voice],
                    ad=self.shadow[0xd405 + 7 * voice], sr=self.shadow[0xd406 + 7 * voice],
                    filterRouting=self.shadow[0xd417], filterMode=self.shadow[0xd418])
            return super().operation(voice, operation, state)

    player = Observer(programs)
    for call in range(max(call for _, call in PATCH_SOURCES) + 1):
        player.play(call)
    require(set(selected) == set(PATCH_SOURCES), 'Selected Ghouls note entries are absent')
    patches = [deepcopy(selected[key]) for key in PATCH_SOURCES]
    for patch in patches:
        state = patch['state']
        require(state['waveform'] in (16, 32, 64, 80), 'Transfer requires an uncoupled tonal body')
        require(not state['onset_control'] & 6, 'Transfer excludes coupled onsets')
        require(not state['frequency_delay_reload'] and not state['note_step'] and not state['glide_rate'],
                'Transfer excludes pitch sweeps, note alternation and glide')
        require(patch['filterRouting'] == 0 and patch['filter']['step'] == 0,
                'Selected transfer requires an unfiltered tonal patch')
    return patches


def source_events(source):
    require(isinstance(source, dict) and isinstance(source.get('voices'), list), 'Expected source voices')
    roles = {row.get('name'): row for row in source['voices'] if isinstance(row, dict)}
    require(len(source['voices']) == len(roles) == 3 and set(roles) == set(ROLES), 'Expected melody, bass and harmony')
    require(source.get('totalBeats', 0) >= 12, 'Source must include twelve beats')
    tempo = source.get('quarterBpm')
    require(type(tempo) in (int, float) and math.isfinite(tempo) and tempo > 0, 'Expected positive finite tempo')
    bpm = Fraction(str(tempo))
    events = {}
    for role in ROLES:
        instrument = roles[role].get('instrument', {})
        require(instrument.get('waveform') == 16 and all(type(instrument.get(name)) is int and 0 <= instrument[name] <= 255
                for name in ('attackDecay', 'sustainRelease')), 'Plain reference requires source triangle/envelopes')
        selected = []
        for event in roles[role]['events']:
            require(type(event.get('startBeat')) in (int, float) and math.isfinite(event['startBeat']), 'Expected finite onset')
            start = Fraction(str(event['startBeat']))
            require(start >= 0, 'Negative source onset')
            if start >= END_BEAT:
                continue
            require(set(event) == {'startBeat', 'durationBeats', 'midi'}, 'Unsupported source event fields')
            require(type(event['durationBeats']) in (int, float) and math.isfinite(event['durationBeats']), 'Expected finite duration')
            end = start + Fraction(str(event['durationBeats']))
            require(start < end <= END_BEAT, 'Source event crosses the phrase boundary or has no duration')
            require(type(event['midi']) is int and 0 <= event['midi'] <= 127, 'Expected MIDI pitch')
            selected.append(dict(start=start, end=end, midi=event['midi']))
        selected.sort(key=lambda event: event['start'])
        require(all(a['end'] <= b['start'] for a, b in zip(selected, selected[1:])), 'Source events overlap')
        events[role] = selected
    require(sum(map(len, events.values())) > 0, 'Source phrase has no notes')
    return roles, events, bpm


def prepare_elise(source, programs, release_seconds=RELEASE_SECONDS):
    roles, events, bpm = source_events(source)
    require(type(release_seconds) in (int, float) and math.isfinite(release_seconds) and release_seconds > 0,
            'Expected positive finite release duration')
    end_call = call_at(END_BEAT, bpm)
    release_calls = math.ceil(Fraction(str(release_seconds)) / CALL_SECONDS)
    audit_calls = end_call + 1 + release_calls + CONFIRMATION_CALLS
    require(1 <= end_call and audit_calls <= 100000, 'Transfer calendar exceeds supported range')
    patches = selected_patches(programs)
    words = {int(index): word for index, word in programs['frequencyWords'].items() if 1 <= int(index) <= 96 and word}
    tuning, pitches = [], {}
    for midi in sorted({event['midi'] for notes in events.values() for event in notes}):
        cents, index = min((abs((69 + 12 * math.log2(word * float(PAL_CLOCK) / 2**24 / 440) - midi) * 100), index)
                           for index, word in words.items())
        require(cents < 50, 'Source pitch has no native lookup match within half a semitone')
        pitches[midi] = index
        tuning.append(dict(midi=midi, pitchIndex=index, frequencyWord=words[index], absoluteCentsError=cents))
    graph, voices, initial_sound = {}, [], []
    boundaries = {Fraction(0), END_BEAT}
    patch_metadata = []
    for voice, role in enumerate(ROLES):
        patch = patches[voice]
        state = deepcopy(patch['state'])
        # Continuing sound precedes the first score row (ghouls_player.play).
        # Clear prior-note transients and defer PWM admission to the waveform setter.
        transients = ('current_frequency', 'note_index', 'target_note_index', 'onset_remaining', 'note_remaining',
                      'note_direction', 'frequency_delay_remaining', 'frequency_half_remaining')
        for name in transients:
            state[name] = 0
        state.update(transpose=0, pitch_index_mode=0, gate_time=255, rest_reload=255, rest_remaining=255,
                     pulse_direction=1)
        initial_sound.append(state)
        entries = []

        def append(name, operation):
            entries.append((name, operation))

        def command(name, kind, fields):
            append(name, dict(kind='command', command=kind, fields=fields))

        base = 0xd400 + 7 * voice
        stores = [dict(address=base + 5, value=patch['ad']), dict(address=base + 6, value=patch['sr']),
                  dict(address=base + 2, value=state['pulse_word'] & 255), dict(address=base + 3, value=state['pulse_word'] >> 8)]
        if voice == 0:
            stores += [dict(address=0xd417, value=patch['filterRouting']), dict(address=0xd418, value=patch['filterMode'])]
        cursor = 0
        gap_index = 0

        def rest(calls):
            nonlocal gap_index
            while calls:
                duration = min(calls, 255)
                append(f'{role}-rest-{gap_index}', dict(kind='rest', duration=duration))
                gap_index += 1
                calls -= duration

        first_note = call_at(events[role][0]['start'], bpm) if events[role] else 0
        rest(first_note)
        cursor = first_note
        command(f'{role}-setup-envelope', 'sid-store-list', dict(stores=stores))
        command(f'{role}-setup-waveform', 'waveform', dict(waveform=state['waveform']))
        for index, event in enumerate(events[role]):
            first, last = call_at(event['start'], bpm), call_at(event['end'], bpm)
            duration = last - first
            require(first >= cursor and 1 <= duration <= 255, 'Unrepresentable note duration or rounded overlap')
            require(state['onset_delay'] < duration, 'Native onset restoration would reach the following rest')
            rest(first - cursor)
            append(f'{role}-note-{index}', dict(kind='note', rawNote=pitches[event['midi']], duration=duration))
            if index == len(events[role]) - 1:
                command(f'{role}-final-release', 'sid-store-list', dict(stores=[dict(address=base + 6, value=patch['sr'] & 240 | 9)]))
            command(f'{role}-gateoff-{index}', 'sid-store-list', dict(stores=[dict(address=base + 4, value=state['waveform'] & 254)]))
            cursor = last
            boundaries.update((event['start'], event['end']))
        rest(end_call - cursor)
        command(f'{role}-end-gate', 'sid-store-list', dict(stores=[dict(address=base + 4, value=state['waveform'] & 254)]))
        command(f'{role}-disable', 'disable-voice', {})
        for index, (name, operation) in enumerate(entries):
            if operation.get('command') != 'disable-voice':
                operation['next'] = entries[index + 1][0]
            graph[name] = dict(variants=dict(stream=operation))
        voices.append(dict(cursor=entries[0][0], duration_remaining=1, repeat_remaining=0,
                           repeat_cursor=None, stack=[], enabled=255, duration_override=0))
        patch_metadata.append(dict(role=role, physicalVoice=PATCH_SOURCES[voice][0] + 1, noteCall=PATCH_SOURCES[voice][1],
            captured=deepcopy(patch), clearedTransientFields=list(transients),
            articulation=dict(gateTime=255, restReload=255, noteEnd='Explicit gate-off at the absolute source boundary'),
            finalRelease=dict(capturedNativeSR=patch['sr'], initialSR=patch['sr'], finalSR=patch['sr'] & 240 | 9,
                              call=call_at(events[role][-1]['end'], bpm) if events[role] else None),
            pulseAdmission='Initial sentinel 1 defers motion until the first waveform setter restores the native phase'))
    provenance = dict(source='songs/fuer-elise.json', sourceSha256=digest(source), sourceEdition=source.get('provenance', {}).get('edition'),
        programs='songs/ghouls.json', programsSha256=digest(programs), excerptBeats=[0, 12], roleOrder=list(ROLES),
        patchSources=patch_metadata, changes=[
            'Preserve all excerpt notes and source gaps; quantize absolute beat boundaries to single PAL calls.',
            'Relocate the uncoupled voice-3 moving-pulse body to melody and harmony; retain voice-2 triangle and one-call noise onset for bass.',
            'Retain named patch parameters, pulse word/default/restart/fallback and filter phases; clear previous-note pitch and countdown transients.',
            'Use native positive-note setup and continuing PWM/onset; disable pitch replacement and set zero transpose for the familiar score.',
            'Adapt gate-time 1 to 255 and emit explicit gate-offs at exact source note ends, preserving waveform and PWM phase.',
            'Change only each final note release nibble from native 15 to 9 immediately before its gate-off; retain the sustain nibble and every earlier source envelope setting.',
            'The 2026-10-13 forty-second native-release diagnostic stayed audible through 14 seconds and became quiet around 33 seconds; use the bounded final-release adaptation for this short phrase.',
            'End with gate-off then stream disable; add no ending note or master-volume fade.',
            'Plain and native versions share musical notes, durations, gaps and navigation; setup envelope/waveform values and gate-off waveform bits differ.'],
        listeningStatus='Pending; generated familiar transfer, not an original performance.',
        release=dict(provisionalSeconds=release_seconds, releaseCalls=release_calls, confirmationCalls=CONFIRMATION_CALLS,
                     limitation='The rendered tail must confirm acoustic release; numeric disabled score and gates do not prove silence.'))
    transfer = dict(format='ghouls-composition-v1', profile=deepcopy(programs['profile']),
        initialSound=initial_sound, initialFilter=deepcopy(patches[1]['filter']),
        pulseFallbacks=[patch['pulseFallback'] for patch in patches], filterRestartPhases=[patch['filterRestartPhase'] for patch in patches],
        frequencyWords=deepcopy(programs['frequencyWords']), program=dict(nodes=graph), voices=voices,
        range=dict(auditCalls=audit_calls), sourceEvidence=provenance)
    reference = deepcopy(transfer)
    for voice, role in enumerate(ROLES):
        plain = reference['initialSound'][voice]
        plain.update(waveform=16, onset_delay=0, onset_control=0, onset_frequency=0, pulse_step=0,
                     pulse_direction=1, pulse_restart=1)
        nodes = reference['program']['nodes']
        nodes[f'{role}-setup-waveform']['variants']['stream']['fields']['waveform'] = 16
        stores = nodes[f'{role}-setup-envelope']['variants']['stream']['fields']['stores']
        stores[0]['value'], stores[1]['value'] = roles[role]['instrument']['attackDecay'], roles[role]['instrument']['sustainRelease']
        if events[role]:
            source_sr = roles[role]['instrument']['sustainRelease']
            nodes[f'{role}-final-release']['variants']['stream']['fields']['stores'][0]['value'] = source_sr
            reference['sourceEvidence']['patchSources'][voice]['finalRelease'].update(initialSR=source_sr, finalSR=source_sr)
        for name, wrapper in nodes.items():
            if name.startswith(role + '-gateoff-') or name == role + '-end-gate':
                wrapper['variants']['stream']['fields']['stores'][0]['value'] = 16
    reference['sourceEvidence']['listeningStatus'] = 'Generated plain score reference with source triangle/envelopes; not an original recording.'
    reference['sourceEvidence']['changes'] = [
        'Retain all transfer notes, source gaps, pitch words, absolute boundaries, gate-off schedule and stream disable.',
        'Use the source triangle waveform and envelopes; disable staged onset and PWM for the plain reference.',
        'Keep the matching final-release node at each last note end, retaining the plain source release nibble 0.',
        'Setup envelope/waveform values and gate-off waveform bits differ; the musical score and release calendar are identical.']
    for description in (transfer, reference):
        player = GhoulsPlayer(description)
        for call in range(audit_calls):
            player.play(call)
            if call == end_call:
                stopped = player.state()
                require([voice.enabled for voice in player.score.voices] == [0, 0, 0], 'Transfer did not disable all streams at the phrase end')
            elif call > end_call:
                require(player.state() == stopped, 'Transfer changed disabled state during its release tail')
    report = dict(retainedEvents={role: len(events[role]) for role in ROLES}, pitchMapping=tuning,
        sourceEndCall=end_call, auditCalls=audit_calls, renderSeconds=float(audit_calls * CALL_SECONDS),
        provisionalReleaseSeconds=release_seconds, releaseCalls=release_calls, confirmationCalls=CONFIRMATION_CALLS,
        maximumBoundaryErrorSeconds=float(max(abs(call_at(beat, bpm) * CALL_SECONDS - beat * 60 / bpm) for beat in boundaries)),
        transferSha256=digest(transfer), referenceSha256=digest(reference),
        evidenceLevel='Source-note transfer, exact native lookup tuning and numeric stopped-state verification; compiled/audio/listening checks are separate.')
    return transfer, reference, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'songs/fuer-elise.json')
    parser.add_argument('--programs', type=Path, default=ROOT / 'songs/ghouls.json')
    parser.add_argument('--transfer-output', type=Path, default=ROOT / 'songs/ghouls-elise-transfer.json')
    parser.add_argument('--reference-output', type=Path, default=ROOT / 'songs/ghouls-elise-reference.json')
    parser.add_argument('--release-seconds', type=float, default=RELEASE_SECONDS)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = args.transfer_output, args.reference_output
    require(outputs[0].resolve() != outputs[1].resolve(), 'Choose distinct outputs')
    if not args.check:
        require(all(not path.exists() and not path.is_symlink() for path in outputs), 'Choose fresh outputs')
    transfer, reference, report = prepare_elise(json.loads(args.source.read_text()), json.loads(args.programs.read_text()), args.release_seconds)
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
