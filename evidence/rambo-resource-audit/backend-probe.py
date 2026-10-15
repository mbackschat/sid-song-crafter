"""Audit source Rambo voice pressure against the retained complete write oracle."""

import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import sys


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(rows):
    return [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]


def run(root, output):
    sys.path.insert(0, str(root / 'scripts'))
    from rambo_player import LoaderPlayer, sound_state
    from rambo_programs import advance_voice
    from verify_player import require

    source_path = root / 'songs/rambo-loader.json'
    notes_path = root / 'evidence/rambo-ensemble/preparation/source-note-events.json.gz'
    writes_path = root / 'evidence/rambo-independent-full/writes.json.gz'
    bodies_path = root / 'evidence/rambo-sound-full/bodies.json.gz'
    source = json.loads(source_path.read_text())
    retained_notes = json.loads(gzip.decompress(notes_path.read_bytes()))
    retained_writes = json.loads(gzip.decompress(writes_path.read_bytes()))
    retained_bodies = json.loads(gzip.decompress(bodies_path.read_bytes()))
    bodies = {(row['call'], row['voice']): row for row in retained_bodies}

    class ObservedPlayer(LoaderPlayer):
        def __init__(self, description):
            self.shadow = {}
            self.notes = []
            self.previous = [None] * 3
            self.coupling = []
            super().__init__(description)

        def write(self, address, value):
            self.shadow[address] = value
            super().write(address, value)

        def note(self, event):
            voice = event['voiceIndex']
            self.notes.append(dict(event, patch=deepcopy(self.data[voice]),
                                   beforeSound=sound_state(self.sound[voice]),
                                   beforeSid=[self.shadow.get(0xd400 + voice * 7 + offset, 0) for offset in range(7)],
                                   priorNote=deepcopy(self.previous[voice])))
            self.previous[voice] = dict(event)
            super().note(event)

    player = ObservedPlayer(source)
    coupling = [[], [], []]
    body_comparisons = 0
    for call in range(source['range']['auditCalls']):
        player.play(call)
        for voice in range(3):
            flags = player.shadow.get(0xd404 + 7 * voice, 0) & 6
            rows = coupling[voice]
            if flags:
                if rows and rows[-1]['endCall'] == call and rows[-1]['flags'] == flags:
                    rows[-1]['endCall'] = call + 1
                else:
                    rows.append(dict(startCall=call, endCall=call + 1, flags=flags,
                                     recipientVoiceIndex=voice, modulatorVoiceIndex=(voice + 2) % 3))
            if (call, voice) in bodies:
                require(sound_state(player.sound[voice]) == bodies[call, voice]['after'],
                        f'Retained SOUND state differs at {call}/{voice}')
                body_comparisons += 1
    require(identity(player.writes) == identity(retained_writes), 'Full source ordered write oracle differs')
    note_identity = lambda rows: [(row['call'], row['voiceIndex'], row['pitchIndex'], row['nodeId'], row['patch']) for row in rows]
    require(note_identity(player.notes) == note_identity(retained_notes), 'Retained note ledger differs')

    replacements = [row for row in player.notes if row['priorNote'] and row['beforeSound']['life']]
    gate_off = [row for row in replacements if not row['beforeSid'][4] & 1]
    summaries = []
    for voice in range(3):
        selected = [row for row in player.notes if row['voiceIndex'] == voice]
        old = [row for row in replacements if row['voiceIndex'] == voice]
        released = [row for row in gate_off if row['voiceIndex'] == voice]
        summaries.append(dict(voiceIndex=voice, notes=len(selected), replacesLiveSoftwareState=len(old),
                              gateOffBeforeLiveReplacement=len(released),
                              changedPitchAfterGateOff=sum(row['priorNote']['pitchIndex'] != row['pitchIndex'] for row in released)))
    chords = [row for row in player.notes if row['voiceIndex'] == 2 and row['patch'][13] & 8]
    overlays = Counter(tuple(row['patch'][:row['patch'][11] + 1]) for row in chords)
    chord_examples = []
    previous = None
    for row in chords:
        key = row['pitchIndex'], tuple(row['patch'][:row['patch'][11] + 1])
        if key != previous and row['call'] < 3000:
            chord_examples.append(dict(call=row['call'], sourceAddress=row['sourceAddress'], nodeId=row['nodeId'],
                                       basePitch=row['pitchIndex'], offsets=list(key[1]),
                                       distinctPitchIndices=sorted({row['pitchIndex'] + step for step in key[1]})))
        previous = key
    percussive = []
    for row in player.notes:
        patch = row['patch']
        steps = [patch[offset] | patch[offset + 1] << 8 for offset in range(0, 8, 2)]
        if 65456 in steps:
            percussive.append(dict(call=row['call'], voiceIndex=row['voiceIndex'], pitchIndex=row['pitchIndex'],
                                   sourceAddress=row['sourceAddress'], nodeId=row['nodeId'],
                                   steps=[word if word < 32768 else word - 65536 for word in steps],
                                   durations=patch[8:12], delay=patch[12], frequencyFlags=patch[13],
                                   controlAdSrGateLife=patch[24:29]))
    examples = [row for row in gate_off if row['voiceIndex'] == 0 and row['call'] in (2483, 2611, 2739, 2867, 2995)]
    evidence_examples = []
    for row in examples:
        after = bodies[row['call'] - 1, 0]['after']
        require(row['beforeSound'] == after, 'Before-overwrite state differs from previous retained source SOUND')
        evidence_examples.append(dict(call=row['call'], priorCall=row['priorNote']['call'],
                                      priorPitch=row['priorNote']['pitchIndex'], newPitch=row['pitchIndex'],
                                      sourceAddress=row['sourceAddress'], nodeId=row['nodeId'],
                                      actualSidControl=row['beforeSid'][4], remainingSoftwareLife=after['life'],
                                      remainingReleaseCountdown=after['releaseCountdown'],
                                      sourcePatch=row['patch'][24:29]))
    arpeggio_sequence = [dict(call=row['call'], frequencyWord=row['after']['frequency'],
                             releaseCountdown=row['after']['releaseCountdown'], life=row['after']['life'],
                             writes=row['writes']) for row in retained_bodies if row['voice'] == 2 and 2354 <= row['call'] <= 2362]
    selected_lead = [dict(call=row['call'], pitchIndex=row['pitchIndex'], nodeId=row['nodeId'],
                          sourceAddress=row['sourceAddress'], patch=row['patch'])
                     for row in player.notes if row['voiceIndex'] == 0 and 2355 <= row['call'] <= 2611]
    counterfactuals = []
    for row in selected_lead:
        state = deepcopy(bodies[row['call'], 0]['before'])
        require(not state['control'] & 8, 'Counterfactual probe requires row-independent release timing')
        gate = None
        for call in range(row['call'], row['call'] + 512):
            state, writes = advance_voice(state, voice=0, row_remaining=0,
                                          frequency_words=dict(enumerate(source['frequencyWords'])))
            if gate is None and any(address == 0xd404 and not value & 1 for address,value in writes):
                gate = call
            if not state['life']:
                counterfactuals.append(dict(onsetCall=row['call'], gateOffCall=gate, terminalClearCall=call,
                                            scope='Counterfactual autonomous source program continuation without a later same-voice retrigger; numeric prediction, not an executed musical variant or amplitude measurement.'))
                break
        else:
            raise ValueError('Selected source program did not terminate within bounded continuation')
    inputs = [source_path, notes_path, writes_path, bodies_path,
              root / 'scripts/rambo_player.py', root / 'scripts/rambo_score.py', root / 'scripts/rambo_programs.py']
    report = dict(schemaVersion=1, question='Which actual one-oscillator state collisions can a second SID relieve without inventing notes?',
                  sourceProfile=source['profile'], calls=source['range']['auditCalls'],
                  inputs=[dict(path=str(path.relative_to(root)), sha256=sha256(path)) for path in inputs],
                  oracle=dict(orderedWrites=len(retained_writes), exactPhaseTickAddressValue=True,
                              sourceNotes=len(retained_notes), exactNotesAndEntryPatches=True,
                              retainedSoundStatesMatched=body_comparisons, retainedSoundInvocationRecords=len(retained_bodies),
                              stateComparisonBoundary='Last SOUND state per physical voice/call; three duplicate reentrant invocation keys collapse to their final call state.'),
                  perVoice=summaries, couplingIntervals=coupling,
                  releaseOverlapExamples=evidence_examples,
                  arpeggioCompression=dict(voiceIndex=2, noteEntries=len(chords), firstCall=chords[0]['call'],
                                           lastOnset=chords[-1]['call'], overlays=[dict(offsets=list(key), noteEntries=count) for key,count in overlays.items()],
                                           examples=chord_examples, executedFirstRow=arpeggio_sequence,
                                           mechanism='One SID oscillator emits one chord frequency per call; table pitches are serial, not simultaneous.'),
                  downwardPitchGesture=dict(noteEntries=len(percussive), observations=percussive,
                                             executedFirstAttacks=[dict(call=row['call'], frequencyWord=row['after']['frequency'], writes=row['writes'])
                                                                  for row in retained_bodies if row['voice'] == 0 and 2227 <= row['call'] <= 2231],
                                             claim='Tonal falling-pitch gesture. No percussion-role or composer-intent verdict follows from register shape.'),
                  candidate=dict(type='bounded original-lead release overlap', sourceOnsets=selected_lead,
                                 trialStartCall=2355, trialEndCall=2803, autonomousContinuation=counterfactuals,
                                 proposal='Keep the original attacks at2355/2611 on A1; move only the original2483 attack to B1 from its onset. Retain each original onset, pitch, entry patch and autonomous programs while the preceding oscillator continues its programmed release.',
                                 guard='Source-onset multiset across A1/B1 equals original. Per-note native pitch/PWM/program initialization is unchanged. Preserve A1/A3 coupling intervals; no new melody, harmony or drum attacks.',
                                 limitations=['Software life is a programmed resource horizon, not an amplitude or audibility measurement.',
                                              'Changing overlap changes harmony and texture; source note membership alone does not approve the concurrent interval.',
                                              'A two-slot allocator may still steal a tail when later source onsets are denser; restrict the first trial to this phrase and record every actual steal.',
                                              'SID envelope phase cannot be cloned at a later instant; allocate each attack to its eventual oscillator from onset.',
                                              'A new physical oscillator attacks from its own residual envelope level. Equal register programs do not imply the same envelope trajectory or PCM as the original same-voice retrigger.',
                                              'No Rambo-specific evidence establishes that Galway intended these tails to overlap or wanted extra drums.']),
                  negativeClaims=dict(noiseAndVolumeAbsenceDoesNotExcludeTonalPercussion=True,
                                      originalNotesAreNotMissing=True, musicalImprovementEstablished=False,
                                      originalAuthorIntentEstablished=False),
                  reproduction='python3 build/rambo-resource-audit/backend-probe.py --root . --output build/rambo-resource-audit-recheck')
    output.mkdir(parents=True, exist_ok=True)
    detail_path, report_path = output / 'backend-note-observations.json.gz', output / 'backend-audit.json'
    require(not detail_path.exists() and not report_path.exists(), 'Choose an output without backend audit files')
    encoded = (json.dumps(player.notes, separators=(',', ':'), allow_nan=False) + '\n').encode()
    detail_path.write_bytes(gzip.compress(encoded, mtime=0))
    report['detail'] = dict(path=detail_path.name, sha256=sha256(detail_path), uncompressedSha256=hashlib.sha256(encoded).hexdigest(), records=len(player.notes))
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(report=str(report_path), oracle=report['oracle'], perVoice=summaries,
                         couplingIntervals=coupling, releaseOverlapExamples=evidence_examples), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.root.resolve(), args.output)
