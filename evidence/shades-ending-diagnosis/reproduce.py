"""Reproduce the transfer's final pitch gestures and finite ending from editable inputs."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))

from shades_player import Player


INPUTS = (
    'songs/shades-transfer.json',
    'songs/shades-transfer-programs.json',
    'scripts/shades_player.py',
    'scripts/shades_programs.py',
    'scripts/describe-shades-score.py',
    'scripts/verify_player.py',
)


def simulate(score, programs):
    player = Player(score, programs)
    records = []
    for tick in range(player.stop_call + 1):
        before = len(player.writes)
        player.step()
        voice = player.state.voices[2]
        records.append({
            'tick': tick, 'word': voice.frequency, 'target': voice.target_frequency,
            'delay': voice.vibrato_delay, 'phase': voice.vibrato_phase,
            'control': voice.control, 'portamento': voice.portamento_step,
            'volume': (player.fade_volume if player.fade_interval
                       else player.state.filter.mode_volume) & 15,
            'commands': player.rows.get(tick), 'state': player.state.to_dict(),
            'fade': {'interval': player.fade_interval, 'countdown': player.fade_countdown,
                     'modeVolume': player.fade_volume},
            'writes': player.writes[before:],
        })
    return records


def pitch_stores(records):
    return [write for row in records for write in row['writes']
            if write['address'] in (0xd40e, 0xd40f)]


def main():
    score = json.loads((ROOT / INPUTS[0]).read_bytes())
    programs = json.loads((ROOT / INPUTS[1]).read_bytes())
    variants = {'baseline': score, 'final-bar-and-release-pulse': deepcopy(score),
                'release-pulse': deepcopy(score)}
    for order in (7, 8):
        variants['final-bar-and-release-pulse']['orders'][order]['instrument'] = 'pulse-trio'
    variants['release-pulse']['orders'][8]['instrument'] = 'pulse-trio'
    states = {name: simulate(value, programs) for name, value in variants.items()}
    baseline = states['baseline']

    glides = []
    for onset, expected_calls, label in ((1121, 2, 'F4 to E4'), (1161, 11, 'E4 to G4'),
                                       (1201, 10, 'G4 to E4'), (1221, 5, 'E4 to D4'),
                                       (1241, 4, 'D4 to C4')):
        command = next(row for row in baseline[onset]['commands'] if row['voice'] == 3)
        target = baseline[onset]['target']
        reached = next(row['tick'] for row in baseline[onset:]
                       if row['word'] == target)
        assert reached - onset == expected_calls, (onset, reached, expected_calls)
        glides.append({'gesture': label, 'onsetCall': onset, 'sourceNote': command['sourceNote'],
                       'onsetWord': baseline[onset]['word'], 'targetWord': target,
                       'firstTargetCall': reached, 'callsToTarget': reached - onset,
                       'nominalMilliseconds': (reached - onset) * 12326 / 985248 * 1000})

    assert baseline[1280]['control'] == 0x41 and baseline[1281]['control'] == 0x40
    assert baseline[1245]['word'] == 0x1171
    assert all(row['control'] == 0x40 for row in baseline[1281:1521])
    assert baseline[1430]['volume'] == 1 and baseline[1431]['volume'] == 0
    assert all(row['volume'] == 0 for row in baseline[1431:1521])
    tail_words = [row['word'] for row in baseline[1281:1431]]
    assert (min(tail_words), max(tail_words)) == (0x1151, 0x11d1)
    assert baseline[1521]['writes'] == [
        {'phase': 'play', 'tick': 1521, 'address': address, 'value': 0}
        for address in (0xd404, 0xd40b, 0xd412, 0xd418)]
    assert pitch_stores(baseline) == pitch_stores(states['release-pulse'])
    assert all(a['word'] == b['word'] and a['target'] == b['target']
               for a, b in zip(baseline, states['release-pulse']))
    for glide in glides:
        row = states['final-bar-and-release-pulse'][glide['onsetCall']]
        assert row['word'] == glide['targetWord']

    states_path = OUTPUT / 'states.json'
    states_path.write_text(json.dumps(states, separators=(',', ':')) + '\n')
    summary = {
        'kind': 'bounded-shades-transfer-ending-diagnosis',
        'evidenceLevel': 'Computed semantic states and ordered stores; no new compiled/audio/listening claim',
        'reproduce': 'python3 build/shades-ending-diagnosis/reproduce.py',
        'inputSha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                        for name in INPUTS},
        'reproducerSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'states': {'path': 'states.json', 'sha256': hashlib.sha256(states_path.read_bytes()).hexdigest(),
                   'bytes': states_path.stat().st_size, 'callsPerVariant': len(baseline),
                   'contents': 'Full named state, fade state, commands and ordered stores after every call'},
        'interventions': {'final-bar-and-release-pulse': {'orders': [7, 8], 'instrument': 'pulse-trio'},
                          'release-pulse': {'orders': [8], 'instrument': 'pulse-trio'}},
        'glides': glides,
        'ending': {'finalTargetWord': 0x1171, 'finalTargetReachedCall': 1245,
                   'releaseCall': 1281, 'releaseControl': 0x40,
                   'audibleFadePitchMinimum': min(tail_words), 'audibleFadePitchMaximum': max(tail_words),
                   'firstZeroVolumeCall': 1431, 'terminalSilenceCall': 1521},
        'verified': {'releaseOnlyPitchStoresUnchanged': True, 'releaseOnlyPitchStatesUnchanged': True,
                     'finalBarPulseAttacksWrittenTargets': True},
        'finding': 'The last bar deliberately attacks at the preceding pitch and slides to each target; no corrupt or runaway fade pitch was observed.',
        'interpretationLimit': 'The glide is a plausible contributor to the wrong-note impression; these checks do not establish subjective causation.',
    }
    (OUTPUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({'verified': summary['verified'], 'ending': summary['ending'],
                      'statesBytes': summary['states']['bytes']}, indent=2))


if __name__ == '__main__':
    main()
