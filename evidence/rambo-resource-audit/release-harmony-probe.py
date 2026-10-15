"""Reject unsafe release-overlap examples using source harmony and pitch programs."""

import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys


def fingerprint(path, root):
    raw = path.read_bytes()
    return dict(path=str(path.resolve().relative_to(root)), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def signed(word):
    return word if word < 32768 else word - 65536


def run(root, output):
    sys.path.insert(0, str(root / 'scripts'))
    from rambo_player import LoaderPlayer, sound_state
    from rambo_programs import advance_voice
    from verify_player import require
    require(not output.exists(), 'Choose a fresh audit output')
    audit_path = root / 'build/rambo-resource-audit/design-audit.json'
    source_path = root / 'songs/rambo-loader.json'
    audit, source = json.loads(audit_path.read_text()), json.loads(source_path.read_text())
    require(fingerprint(source_path, root)['sha256'] == audit['inputs'][0]['sha256'], 'Source differs from resource audit')
    observations = audit['observations']
    chord_rows = [note for note in observations if note['voiceIndex'] == 2 and 2354 <= note['call'] < 7474]
    regions = []
    for note in chord_rows:
        patch = note['patch']
        pcs = sorted({(note['pitchIndex'] + offset) % 12 for offset in patch[:patch[11] + 1]})
        if regions and regions[-1]['endCall'] == note['call'] and regions[-1]['pitchClasses'] == pcs:
            regions[-1]['endCall'] = note['nextExecutedRowCall']
        else:
            regions.append(dict(startCall=note['call'], endCall=note['nextExecutedRowCall'], pitchClasses=pcs))
    notes = [note for note in observations if note['voiceIndex'] == 0 and 2355 <= note['call'] < 4915]

    def nominal_overlap(a, b, start, end):
        selected = [region for region in regions if start < region['endCall'] and region['startCall'] < end]
        return dict(startCall=start, endExclusive=end,
                    carriedPitchIndex=a['pitchIndex'], arrivingPitchIndex=b['pitchIndex'],
                    intervalSemitones=abs(a['pitchIndex'] - b['pitchIndex']),
                    sourceRegions=selected,
                    nominalPitchClassesFit=bool(selected) and all(a['pitchIndex'] % 12 in region['pitchClasses']
                                                                 and b['pitchIndex'] % 12 in region['pitchClasses'] for region in selected))

    def detached(note):
        require(not note['patch'][24] & 14, 'Detached counter model requires no TEST/sync/ring')
        player = LoaderPlayer(source)
        player.data[0] = deepcopy(note['patch'])
        player.sound[0] = [0] * 39
        player.call = note['call']
        player.note(note)
        state = sound_state(player.sound[0])
        result = []
        for call in range(note['call'], note['call'] + note['patch'][27] + note['patch'][28] + 1):
            state, _ = advance_voice(state, voice=0, row_remaining=0, frequency_words=player.frequencies)
            result.append(dict(call=call, frequencyWord=state['frequency'], life=state['life'],
                               releaseCountdown=state['releaseCountdown'],
                               semitonesFromNominal=(12 * math.log2(state['frequency'] / player.frequencies[note['pitchIndex']])
                                                     if state['frequency'] else None)))
            if state['life'] == 0:
                break
        return result

    candidates = []
    for a, b, c in zip(notes, notes[1:], notes[2:]):
        end_a = a['call'] + a['patch'][27] + a['patch'][28] - 1
        end_b = b['call'] + b['patch'][27] + b['patch'][28] - 1
        if not b['call'] < end_a <= c['call']:
            continue
        first = nominal_overlap(a, b, b['call'], end_a)
        second = nominal_overlap(b, c, c['call'], end_b) if c['call'] < end_b else None
        first_safe = first['nominalPitchClassesFit']
        second_safe = second is None or second['nominalPitchClassesFit']
        details = []
        for note in (a, b, c):
            patch = note['patch']
            details.append(dict(call=note['call'], nodeId=note['nodeId'], pitchIndex=note['pitchIndex'],
                                signedFrequencySteps=[signed(patch[offset] | patch[offset + 1] << 8) for offset in (0, 2, 4, 6)],
                                frequencyDurations=patch[8:12], frequencyDelay=patch[12], frequencyFlags=patch[13],
                                gateCountdown=patch[27], lifetime=patch[28]))
        candidates.append(dict(sourceNotes=details, previousClearCall=end_a, middleClearCall=end_b,
                               firstOverlap=first, secondOverlap=second,
                               nominalBothOverlapsSafe=first_safe and second_safe,
                               verdict='reject', reason='A carried or arriving nominal pitch class leaves the source harmonic set.'
                               if not first_safe or not second_safe else
                               'Nominal F/G membership passes, but the third source note executes a deep BEND01 descent against the carried G; no robust consonance claim.'))
    require(len(candidates) == 6, 'Bounded triple count changed')
    nominal = [candidate for candidate in candidates if candidate['nominalBothOverlapsSafe']]
    require(len(nominal) == 1 and nominal[0]['sourceNotes'][0]['call'] == 4019, 'Nominally safe candidate changed')
    selected_calls = {2355, 2483, 2611, 4019, 4147, 4371}
    trajectories = [dict(noteCall=note['call'], pitchIndex=note['pitchIndex'], postSound=detached(note))
                    for note in notes if note['call'] in selected_calls]
    bend = next(row for row in trajectories if row['noteCall'] == 4371)
    first_32 = bend['postSound'][:32]
    require(min(row['semitonesFromNominal'] for row in first_32) < -12, 'Expected deep bend no longer executes')
    result = dict(
        schemaVersion=1, status='pass', supportedRange=dict(firstCall=2355, endExclusive=4915),
        reproduction='python3 build/rambo-resource-audit/release-harmony-probe.py --output build/rambo-resource-audit/release-harmony-audit-fresh.json',
        inputs=[fingerprint(path, root) for path in (source_path, audit_path,
                 root / 'scripts/rambo_player.py', root / 'scripts/rambo_programs.py', Path(__file__).resolve())],
        selectionContract=['One middle source attack moves to B1; previous A1 note releases through its original software lifetime.',
                           'Next original A1 attack must follow the previous note lifetime clear, avoiding a third overlapping slot.',
                           'Both prospective overlap pairs must remain in the actual source chord pitch classes.',
                           'Actual source pitch programs, rather than nominal note names alone, must support a robust candidate.'],
        sourceHarmony=regions, candidateTriples=candidates, detachedPitchTrajectories=trajectories,
        finding='No robust contrasting-pitch release candidate in this bounded uncoupled lead region.',
        rejectedInitialTrial='2355 Bb4 / 2483 A4 introduces a minor second over F-major source harmony; 2483 A4 / 2611 G4 carries A into the source F/G/C suspended set.',
        lastNominalCandidate=dict(calls=[4019,4147,4371], noteIndices=[65,67,67],
                                  first32BendSemitoneRange=[min(row['semitonesFromNominal'] for row in first_32),
                                                          max(row['semitonesFromNominal'] for row in first_32)],
                                  steps=[30,-30,30,-308], delay=32, flags=7),
        recommendation='Stop this release example search; test existing B3 as a held remaining source chord tone, retaining primary arpeggio/rhythm and the current native PAUL PWM patch.',
        limits=['Source harmonic-set membership is a conservative addition guard; original melody passing tones can intentionally leave that set.',
                'Detached trajectories retain note-entry source parameters and SOUND arithmetic; they are not a composed or rendered candidate.',
                'No new original CPU execution, render, listening claim or musical acceptance is made.',
                'This is a bounded region scan, not a claim that no safe release experiment exists elsewhere in the tune.'])
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(output=str(output), scannedCandidateTriples=len(candidates),
                          nominalPasses=len(nominal), robustCandidates=0,
                          finalBendSemitones=first_32[-1]['semitonesFromNominal']), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.root.resolve(), args.output)
