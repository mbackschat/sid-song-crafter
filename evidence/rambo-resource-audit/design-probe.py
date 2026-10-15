"""Bounded Rambo resource audit; compute source mechanisms without rendering music."""

import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def fingerprint(path, root):
    raw = path.read_bytes()
    return dict(path=str(path.resolve().relative_to(root.resolve())), bytes=len(raw),
                sha256=hashlib.sha256(raw).hexdigest())


def signed(word):
    return word if word < 32768 else word - 65536


def identity(writes):
    return [(row['phase'], row['tick'], row['address'], row['value']) for row in writes]


def spans(values, minimum=16):
    result, first = [], None
    for call, value in enumerate(values + [True]):
        if not value and first is None:
            first = call
        elif value and first is not None:
            if call - first >= minimum:
                result.append(dict(firstCall=first, endExclusive=call, calls=call - first))
            first = None
    return result


def run(root, output):
    sys.path.insert(0, str(root / 'scripts'))
    from rambo_player import LoaderPlayer
    from verify_player import require
    require(not output.exists(), 'Choose a fresh audit output path')
    source_path = root / 'songs/rambo-loader.json'
    primary_path = root / '.tools/martin-galway-c64/rambload.asm'
    canonical_path = root / 'evidence/rambo-form/complete40000/writes.json.gz'
    checker_path = root / 'scripts/studies/rambo/check-published-score.py'
    spec = importlib.util.spec_from_file_location('rambo_published_checker', checker_path)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    require(fingerprint(source_path, root)['sha256'] == '3a59937b1e3c1c9b95872bc262330dfaa97649ef78f5a8ad3fa01cc47e3b809b',
            'Retained faithful description changed')
    require(fingerprint(primary_path, root)['sha256'] == checker.SOURCE_SHA256, 'Published source changed')
    source = json.loads(source_path.read_text())
    symbols, data, unresolved = checker.read_data(primary_path.read_text())
    published_check = checker.compare(source, symbols, data, unresolved)
    notes, live, trajectories = [], [[], [], []], []

    class ObservedPlayer(LoaderPlayer):
        def __init__(self, description):
            self.controls = [0, 0, 0]
            super().__init__(description)

        def write(self, address, value):
            if address in (0xd404, 0xd40b, 0xd412):
                self.controls[(address - 0xd404) // 7] = value
            super().write(address, value)

        def note(self, event):
            voice = event['voiceIndex']
            notes.append(dict(event, patch=deepcopy(self.data[voice]),
                              priorSound=deepcopy(self.sound[voice]),
                              priorLastWrittenControl=self.controls[voice]))
            super().note(event)

    player = ObservedPlayer(source)
    for call in range(11000):
        player.play(call)
        for voice in range(3):
            live[voice].append(player.sound[voice][28] > 0)
        if 2226 <= call <= 2315:
            block = player.sound[0]
            trajectories.append(dict(call=call, voiceIndex=0,
                                     frequencyWord=block[29] | block[30] << 8,
                                     control=player.controls[0], releaseCountdown=block[27], life=block[28],
                                     frequencyPhaseRemaining=block[31:35]))
    original = json.loads(gzip.decompress(canonical_path.read_bytes()))
    expected = [row for row in original if row['tick'] is None or row['tick'] < 11000]
    require(identity(player.writes) == identity(expected), 'Numeric audit differs from retained original CPU stores')
    rows = {voice: [event for event in player.score.operations if event['voiceIndex'] == voice
                   and event['operation'] in ('row', 'topReturn')] for voice in range(3)}
    successors = {(voice, row['call'], row['nodeId']): following['call']
                  for voice, timeline in rows.items() for row, following in zip(timeline, timeline[1:])}
    row_values = {(row['voiceIndex'], row['call'], row['nodeId']): row
                  for timeline in rows.values() for row in timeline if row['operation'] == 'row'}
    for note in notes:
        key = note['voiceIndex'], note['call'], note['nodeId']
        note.update(nextExecutedRowCall=successors[key], nominalRowCalls=row_values[key]['value'] or 256)
    groups = []
    for voice in range(3):
        voice_groups = []
        for note in [note for note in notes if note['voiceIndex'] == voice]:
            patch = note['patch']
            signature = dict(control=patch[24], attackDecay=patch[25], sustainRelease=patch[26],
                             gateCountdown=patch[27], lifetime=patch[28],
                             frequencyFlags=patch[13], pulseFlags=patch[17])
            if voice_groups and voice_groups[-1]['patchSignature'] == signature:
                voice_groups[-1]['lastNoteCall'] = note['call']
                voice_groups[-1]['noteCount'] += 1
            else:
                voice_groups.append(dict(voiceIndex=voice, firstNoteCall=note['call'], lastNoteCall=note['call'],
                                         noteCount=1, firstNodeId=note['nodeId'], patchSignature=signature))
        groups.extend(voice_groups)
    chords = [note for note in notes if note['voiceIndex'] == 2 and note['patch'][13] & 8]
    drop_notes = []
    for note in notes:
        patch = note['patch']
        steps = [signed(patch[offset] | patch[offset + 1] << 8) for offset in (0, 2, 4, 6)]
        if -80 in steps:
            drop_notes.append(dict(voiceIndex=note['voiceIndex'], call=note['call'], nodeId=note['nodeId'],
                                   pitchIndex=note['pitchIndex'], sourceFrequencyWord=source['frequencyWords'][note['pitchIndex']],
                                   nextExecutedRowCall=note['nextExecutedRowCall'], signedSteps=steps,
                                   durations=patch[8:12], delay=patch[12], flags=patch[13],
                                   control=patch[24], attackDecay=patch[25], sustainRelease=patch[26],
                                   gateCountdown=patch[27], lifetime=patch[28]))
    require(len(drop_notes) == 11 and [note['call'] for note in drop_notes] ==
            [2227, 2231, 2235, 2239, 2243, 2251, 2259, 2267, 2283, 2291, 2299], 'Descending candidate landmarks changed')
    starts = {note['call']: note for note in drop_notes}
    for row in trajectories:
        if row['call'] in starts:
            require(row['frequencyWord'] == (starts[row['call']]['sourceFrequencyWord'] - 80) & 65535,
                    'Descending onset does not execute the -80 step')
        elif 2228 <= row['call'] < 2315:
            previous = trajectories[trajectories.index(row) - 1]
            require(row['frequencyWord'] == (previous['frequencyWord'] - 80) & 65535,
                    'Descending body does not continue -80 per call')
    primary_lines = primary_path.read_text().splitlines()
    coupled_controls = [row for row in player.writes
                        if row['address'] in (0xd404, 0xd40b, 0xd412) and row['value'] & 6]
    sync_controls = [row for row in coupled_controls if row['value'] & 2]
    ring_controls = [row for row in coupled_controls if row['value'] & 4]
    require(min(row['tick'] for row in sync_controls) == 4915, 'First sync landmark changed')
    require(min(row['tick'] for row in ring_controls) == 10035, 'First ring landmark changed')
    inputs = [source_path, primary_path, canonical_path, checker_path,
              root / 'scripts/rambo_player.py', root / 'scripts/rambo_programs.py', root / 'scripts/rambo_score.py',
              root / 'scripts/verify_player.py', Path(__file__).resolve()]
    report = dict(
        schemaVersion=1, status='pass', auditedCalls=11000, profile=source['profile'],
        reproduction='python3 build/rambo-resource-audit/design-probe.py --output build/rambo-resource-audit/design-audit-fresh.json',
        inputs=[fingerprint(path, root) for path in inputs],
        sourceIdentity=dict(publishedRevision=checker.REVISION, publishedUrl=checker.SOURCE_URL,
                            publishedDataComparison=published_check,
                            retainedOriginalCpuLedger=dict(matchedStores=len(expected), fields=['phase', 'tick', 'address', 'value'],
                                                           freshOriginalCpuExecution=False)),
        counts=dict(notesByVoice=[sum(note['voiceIndex'] == voice for note in notes) for voice in range(3)],
                    completeSourceNoteRecords=len(notes)),
        chordCompression=dict(
            voiceIndex=2, firstCall=chords[0]['call'], lastOnsetCall=chords[-1]['call'], noteCount=len(chords),
            rowSpanCalls=dict(sorted(Counter(note['nextExecutedRowCall'] - note['call'] for note in chords).items())),
            onsetReplacingLiveReleasedState=sum(note['priorSound'][28] > 0 and not note['priorLastWrittenControl'] & 1 for note in chords),
            onsetReplacingStillGatedState=sum(bool(note['priorLastWrittenControl'] & 1) for note in chords),
            patchSignature=chords[0]['patch'][24:29],
            observation='One oscillator/envelope cycles chord pitches; next onsets replace prior state. It cannot supply independent simultaneous chord-note tails.',
            authorIntent='Not established; compression is executed, not proof Galway preferred held polyphonic chords.'),
        tonalPitchDrop=dict(
            primarySourceLines=[dict(lineNumber=index, text=primary_lines[index - 1]) for index in range(909, 918)],
            noteEntries=drop_notes, postSoundTrajectory=trajectories,
            verified='Pulse waveform with a -80 frequency-word step on every SOUND call, short repeated note rows and a 10-call gate countdown.',
            musicalRole='Unsettled: compatible with pitched percussion, but source data directives do not label this passage as drums and no new listening isolation was performed.',
            correction='Absence of noise waveform or D418 volume playback does not establish absence of drums; percussion is a musical role and can use tonal waveforms.'),
        patchRoleTransitions=groups,
        publishedNamedProgramLines=[dict(lineNumber=index, text=primary_lines[index - 1])
                                   for index in range(809, 820)],
        zeroSoftwareLifetimeSpans=[dict(voiceIndex=voice, spans=spans(values)) for voice, values in enumerate(live)],
        zeroLifetimeCaveat='Voice 1 Morse writes occur outside SOUND while software lifetime is zero; zero lifetime is not a universal silence test. Later recorded clear examples use all seven zero register stores.',
        selectedClears=[dict(voiceIndex=voice, call=call,
                             writes=[row for row in player.writes if row['tick'] == call and 0xd400 + voice * 7 <= row['address'] <= 0xd406 + voice * 7])
                        for voice, call in ((0, 4670), (2, 7514))],
        sharedGlobals=dict(nonzeroWrites=[row for row in player.writes if row['address'] >= 0xd415 and row['value']],
                           controlWaveformMasks=sorted({row['value'] & 240 for row in player.writes if row['address'] in (0xd404, 0xd40b, 0xd412)}),
                           interpretation='Filter controls stay zero and D418 has only initialization volume15. Waveforms observed are triangle, saw and pulse; these facts do not settle percussion roles.'),
        coupling=dict(firstSyncCall=min(row['tick'] for row in sync_controls), syncRecipientVoice=0, syncModulatorVoice=2,
                      finalRingCall=min(row['tick'] for row in ring_controls), ringRecipientVoice=0, ringModulatorVoice=2,
                      sourceBassIndependent=not any(row['address'] == 0xd40b for row in coupled_controls),
                      allCoupledControlWrites=coupled_controls,
                      consequence='Keep source physical voices 1 and 3 together and preserve their frequency programs when maintaining the faithful sync/ring timbres.'),
        proposedRevision=dict(status='unimplemented hypothesis',
                              action='After width isolation, test sustaining B3 as a remaining actual source chord tone across source chord-body spans while retaining the primary arpeggio/rhythm.',
                              basis='Expands explicit one-oscillator chord compression, adds no new melody, and does not assume a missing noise drum.',
                              limits='Three B voices cannot unfold all four distinct pitches of every dominant set; declare reductions and preserve source arpeggio colors. Greater sustain is not proven preferable.'),
        observations=notes,
        limits=['This run independently computes the unchanged description and compares its complete ordered stores with retained original CPU evidence; it does not execute a fresh original SID CPU trace.',
                'Published data correspondence does not identify musical instrument roles beyond explicit labels.',
                'No arrangement edit, compilation, rendering, new audition or preference decision occurs.',
                'Counter lifetimes and gate states are execution facts; PCM and musical release remain distinct.'])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(output=str(output), matchedOriginalStores=len(expected), chordNoteCount=len(chords),
                          descendingPulseNotes=len(drop_notes), role='unsettled'), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.root.resolve(), args.output)


if __name__ == '__main__':
    main()
