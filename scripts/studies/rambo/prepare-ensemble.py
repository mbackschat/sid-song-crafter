"""Derive subordinate dual-SID support from the faithful Rambo score's harmony."""

import argparse
from copy import deepcopy
from enum import Enum
import gzip
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from rambo_player import LoaderPlayer, sound_state
from verify_player import require


class SectionKind(str, Enum):
    ANCHOR = 'anchor'
    CHORD = 'chord'


PAL_CALLS_PER_SECOND = (17734475 / 18) / 19656


def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def observe_source(source):
    notes, patches = [], {}

    class ObservedPlayer(LoaderPlayer):
        def note(self, event):
            data = deepcopy(self.data[event['voiceIndex']])
            notes.append(dict(event, patch=data))
            patches[event['voiceIndex'], event['call']] = data
            super().note(event)

    player = ObservedPlayer(source)
    for call in range(source['range']['auditCalls']):
        player.play(call)
    rows = {voice: [row for row in player.score.operations
                    if row['operation'] in ('row', 'topReturn') and row['voiceIndex'] == voice]
            for voice in range(3)}
    row_ends = {(voice, row['call'], row['nodeId']): following['call']
                for voice, timeline in rows.items() for row, following in zip(timeline, timeline[1:])}
    for note in notes:
        note['endCall'] = row_ends[note['voiceIndex'], note['call'], note['nodeId']]
    return notes, patches


def harmonic_regions(notes, sections):
    regions = []
    for section in sections:
        kind = SectionKind(section['kind'])
        selected = [note for note in notes if note['voiceIndex'] == section['voiceIndex']
                    and section['startCall'] <= note['call'] < section['endCall']]
        require(selected and selected[0]['call'] == section['startCall'], 'Section lacks its exact source entrance')
        for note in selected:
            patch = note['patch']
            if kind == SectionKind.CHORD:
                require(patch[13] & 8 and note['voiceIndex'] != 1, 'Chord section lacks an executed source chord program')
                require(0 <= patch[11] < 10, 'Source chord position escapes its ten-byte overlay')
                offsets = patch[:patch[11] + 1]
                pitch_classes = sorted({(note['pitchIndex'] + offset) % 12 for offset in offsets})
            elif kind == SectionKind.ANCHOR:
                require(not patch[13] & 8, 'Anchor section unexpectedly contains a chord program')
                pitch_classes = [note['pitchIndex'] % 12]
            start, end = note['call'], min(note['endCall'], section['endCall'])
            origin = dict(nodeId=note['nodeId'], call=start, endCall=end,
                          pitchIndex=note['pitchIndex'], chordOffsets=offsets if kind == SectionKind.CHORD else [0])
            if (regions and regions[-1]['endCall'] == start and regions[-1]['kind'] == kind.value
                    and regions[-1]['sourceVoiceIndex'] == section['voiceIndex']
                    and regions[-1]['pitchClasses'] == pitch_classes):
                regions[-1]['endCall'] = end
                regions[-1]['sourceRows'].append(origin)
            else:
                regions.append(dict(kind=kind.value, startCall=start, endCall=end,
                                    pitchClasses=pitch_classes, sourceVoiceIndex=section['voiceIndex'],
                                    sourceRows=[origin]))
        require(regions[-1]['endCall'] == section['endCall'], 'Section does not reach its exact source boundary')
    return regions


def validate_support(events, regions):
    """Check every sounding call, including the entire declared release lifetime."""
    for event in events:
        cursor, end = event['startCall'], event['endCall']
        require(type(cursor) is int and type(end) is int and cursor < end,
                'Support must have a positive bounded sounding span')
        for region in regions:
            if region['endCall'] <= cursor or region['startCall'] >= end:
                continue
            require(region['startCall'] <= cursor and event['pitchIndex'] % 12 in region['pitchClasses'],
                    'Support pitch is unsupported over its whole sounding span')
            cursor = min(end, region['endCall'])
            if cursor == end:
                break
        require(cursor == end, 'Support pitch lacks source evidence over its whole sounding span')


def choose_pitch(pitch_classes, pitch_range, previous, excluded=()):
    candidates = [pitch for pitch in range(pitch_range[0], pitch_range[1] + 1)
                  if pitch % 12 in pitch_classes and pitch % 12 not in excluded]
    require(candidates, 'No source chord tone fits the declared role register')
    return min(candidates, key=lambda pitch: (abs(pitch - previous), pitch))


def support_events(notes, regions, roles):
    events, previous, chord_index = [], [29, 41, 48], 0
    bass_notes = [note for note in notes if note['voiceIndex'] == 1]
    for region_index, region in enumerate(regions):
        start, end = region['startCall'], region['endCall']
        pitches = region['pitchClasses']
        bass = next((note for note in reversed(bass_notes) if note['call'] <= start), None)
        anchor_classes = [bass['pitchIndex'] % 12] if (region['kind'] == 'chord' and bass
                          and bass['pitchIndex'] % 12 in pitches) else [pitches[0]]
        low = choose_pitch(anchor_classes, roles[0]['pitchRange'], previous[0])
        chosen = [low]
        if region['kind'] == 'chord':
            chosen.append(choose_pitch(pitches, roles[1]['pitchRange'], previous[1], [low % 12]))
        for voice, pitch in enumerate(chosen):
            events.append(dict(voiceIndex=voice, startCall=start, endCall=end, pitchIndex=pitch,
                               harmonicRegion=region_index, origin='sustained source anchor' if voice == 0 else 'source chord revoicing'))
            previous[voice] = pitch
        if region['kind'] == 'chord':
            role = roles[2]
            if chord_index % role['chordRegionStride'] == 0:
                threshold = start + (end - start) * role['entryFraction']
                onset = next((row['call'] for row in region['sourceRows'] if row['call'] >= threshold), None)
                if onset is not None and end - onset >= 48:
                    pitch = choose_pitch(pitches, role['pitchRange'], previous[2], [p % 12 for p in chosen])
                    events.append(dict(voiceIndex=2, startCall=onset,
                                       endCall=min(end, onset + role['maximumSpanCalls']), pitchIndex=pitch,
                                       harmonicRegion=region_index, origin='source chord-row accent'))
                    previous[2] = pitch
            chord_index += 1
    return sorted(events, key=lambda event: (event['voiceIndex'], event['startCall']))


def make_graph(events, roles, patches, end_call):
    graph, voices, initial = {}, [], []
    for voice, role in enumerate(roles):
        patch_key = role['patchSource']['voiceIndex'], role['patchSource']['noteCall']
        require(patch_key in patches, 'Selected source patch has no actual note entry')
        patch = deepcopy(patches[patch_key])
        for offset, value in role['dataOverrides'].items():
            require(0 <= int(offset) <= 28 and type(value) is int and 0 <= value <= 255, 'Invalid support patch override')
            patch[int(offset)] = value
        require(patch[13] == 0 and patch[24] & 6 == 0,
                'Pitched support requires no pitch sweep, arpeggio, sync or ring dependency')
        initial.append(patch)
        instructions, cursor = [], 0

        def hold(calls):
            while calls:
                duration = min(calls, 255)
                instructions.append(dict(kind='row', sourceNote=191, duration=duration))
                calls -= duration

        for event in [event for event in events if event['voiceIndex'] == voice]:
            first, last = event['startCall'], event['endCall']
            span, release = last - first, role['releaseCalls']
            gate = span - release
            require(first >= cursor and 1 <= gate <= 255 and release >= 2,
                    'Support span cannot fit the native gate/lifetime counters')
            hold(first - cursor)
            # Rambo SOUND decrements gate on entry and skips lifetime on that call;
            # gate+life therefore clears at start+gate+life-1 (rambo_programs.advance_lifetime).
            instructions.extend([dict(kind='poke-data', offset=27, value=gate),
                                 dict(kind='poke-data', offset=28, value=release + 1),
                                 dict(kind='row', sourceNote=96 + event['pitchIndex'], duration=min(span, 255))])
            if span > 255:
                hold(span - 255)
            cursor = last
            event.update(gateCountdown=gate, gateOffCall=first + gate - 1,
                         releaseLifetime=release + 1, lifetimeBoundaryCall=last)
        hold(end_call - cursor)
        instructions.append(dict(kind='return'))
        for index, instruction in enumerate(instructions):
            name = f'support-{voice + 1}-{index}'
            if instruction['kind'] != 'return':
                instruction['next'] = f'support-{voice + 1}-{index + 1}'
            graph[name] = instruction
        voices.append(dict(cursor=f'support-{voice + 1}-0', remaining=1, transpose=0, stackIndex=7,
                           stack=[dict(returnNode=None, repeatRemaining=0) for _ in range(8)]))
    return graph, voices, initial


def verify_support_calendar(description, events):
    player = LoaderPlayer(description)
    timelines = [[event for event in events if event['voiceIndex'] == voice] for voice in range(3)]
    positions, controls = [0, 0, 0], [0, 0, 0]
    write_cursor = len(player.writes)
    for call in range(description['range']['auditCalls']):
        player.play(call)
        for write in player.writes[write_cursor:]:
            if write['address'] in (0xd404, 0xd40b, 0xd412):
                controls[(write['address'] - 0xd404) // 7] = write['value']
        write_cursor = len(player.writes)
        for voice, timeline in enumerate(timelines):
            while positions[voice] < len(timeline) and timeline[positions[voice]]['endCall'] <= call:
                positions[voice] += 1
            expected = timeline[positions[voice]] if positions[voice] < len(timeline) else None
            expected = expected if expected and expected['startCall'] <= call else None
            block = player.sound[voice]
            require(bool(block[28]) == bool(expected), 'Actual support lifetime calendar crosses its declared source span')
            if expected:
                require(block[29] | block[30] << 8 == description['frequencyWords'][expected['pitchIndex']],
                        'Actual support pitch differs from its source-backed sounding calendar')
                life = expected['releaseLifetime'] - max(0, call - expected['gateOffCall'])
                require(block[28] == life, 'Actual support lifetime calendar differs from its declared articulation')
                gate_on = call < expected['startCall'] + expected['gateCountdown'] - 1
                require(bool(controls[voice] & 1) == gate_on, 'Actual support gate calendar differs from its declared articulation')
    return player


def prepare(source, config, *, arrangement_path='songs/studies/rambo-ensemble/arrangement.json'):
    require(config.get('format') == 'rambo-ensemble-v1', 'Expected Rambo ensemble arrangement config')
    require(digest(source) == config['sourceSha256'], 'Retained source fingerprint changed')
    roles = config['roles']
    require([role['voiceIndex'] for role in roles] == [0, 1, 2], 'Declare all three physical support roles in order')
    notes, patches = observe_source(source)
    regions = harmonic_regions(notes, config['sections'])
    events = support_events(notes, regions, roles)
    validate_support(events, regions)
    end_call = max(event['endCall'] for event in events) + 1
    graph, voices, initial = make_graph(events, roles, patches, end_call)
    secondary = dict(format=source['format'], profile=deepcopy(source['profile']),
                     initialization=deepcopy(source['initialization']), frequencyWords=deepcopy(source['frequencyWords']),
                     initialData=initial, initialSound=[[0] * 39 for _ in range(3)],
                     program=graph, voices=voices, dataBanks={}, morse=deepcopy(source['morse']),
                     range=deepcopy(source['range']),
                     sourceEvidence=dict(source=config['source'], sourceSha256=config['sourceSha256'],
                                         arrangement=arrangement_path,
                                         arrangementSha256=digest(config), originalSource=deepcopy(source['sourceEvidence']),
                                         changes=['Derive pitched support only from contemporaneous source chord programs or source bass-anchor classes.',
                                                  'Give all support roles the onset, gate and lifetime calendars declared by the arrangement config.',
                                                  'Keep the initial sweep/Morse passage, late bass figure and final long-release gesture exposed.'],
                                         listeningStatus='Pending human review; secondary arrangement, not a source reconstruction.'))
    player = verify_support_calendar(secondary, events)
    played = [event for event in player.score.operations if event['operation'] == 'note']
    wanted = [(event['voiceIndex'], event['startCall'], event['pitchIndex']) for event in events]
    actual = [(event['voiceIndex'], event['call'], event['pitchIndex']) for event in played]
    require(sorted(wanted) == sorted(actual), 'Generated support graph disagrees with its exact note ledger')
    sounds = [sound_state(block) for block in player.sound]
    require(player.score.active_mask == 0 and all(sound['life'] == 0 for sound in sounds), 'Support does not stop naturally')
    last_writes = [max(row['tick'] for row in player.writes if row['phase'] == 'play'
                       and 0xd400 + voice * 7 <= row['address'] < 0xd407 + voice * 7) for voice in range(3)]
    require(max(last_writes) < source['range']['auditCalls'] - 64, 'Support lacks quiet confirmation calls')
    phrase_start, phrase_end = [round(seconds * PAL_CALLS_PER_SECOND) for seconds in config['mainPhraseSeconds']]
    coverage = [dict(voiceIndex=voice, role=roles[voice]['role'],
                     soundingCalls=sum(max(0, min(event['endCall'], phrase_end) - max(event['startCall'], phrase_start))
                                       for event in events if event['voiceIndex'] == voice)) for voice in range(3)]
    report = dict(schemaVersion=1, checkedCalls=source['range']['auditCalls'], sourceSha256=digest(source),
                  configSha256=digest(config), secondarySha256=digest(secondary), harmonicRegions=regions,
                  supportNoteCounts=[sum(event['voiceIndex'] == voice for event in events) for voice in range(3)],
                  mainPhraseSeconds=config['mainPhraseSeconds'], mainPhraseRoleCoverage=coverage,
                  exactGeneratedNoteLedger=True, exactEveryCallGatePitchAndLifetimeCalendar=True,
                  ending=dict(activeMask=player.score.active_mask, remainingLifetimes=[sound['life'] for sound in sounds],
                              lastVoiceWriteTicks=last_writes, supportScoreReturnCall=end_call,
                              sourceEndingExposedFromCall=max(event['endCall'] for event in events)),
                  roles=roles, modelAssistance=config['modelAssistance'],
                  scope='Whole-lifetime pitch-class membership in executed source harmony, exact support-note calendar and numeric stop; rendered articulation, balance and musical acceptance require separate checks and human listening.')
    return secondary, report, notes, events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('arrangement', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.arrangement.read_text())
    source = json.loads((ROOT / config['source']).read_text())
    secondary, report, notes, events = prepare(source, config, arrangement_path=str(args.arrangement))
    require(not args.output.exists(), 'Choose a fresh preparation output directory')
    args.output.mkdir(parents=True)
    (args.output / 'secondary.json').write_bytes(encoded(secondary))
    (args.output / 'arrangement-proof.json').write_bytes(encoded(report))
    for name, values in (('source-note-events', notes), ('support-note-events', events)):
        (args.output / f'{name}.json.gz').write_bytes(gzip.compress(encoded(values), mtime=0))
    print(f'Prepared source-derived support {report["supportNoteCounts"]}: {args.output / "secondary.json"}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(str(error))
