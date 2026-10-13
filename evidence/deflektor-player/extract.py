"""Extract editable numeric title data, excluding original code and captured runtime events."""

import argparse
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_profile import psid_profile
from deflektor_player import VOICE_FIELDS
from deflektor_programs import ScorePitchProgram, PitchStage

SOURCE_SHA = '606ad4cb19e29c060bb77a9b44253dee62d3d972724acb6cddf625fc2466d44d'
INPUTS = {
    'evidence/deflektor-form/full40000/tables.json': '25a5604436d8b332fc749eb09dc9fea8431e76149bc41e78b276cf9b74ccc309',
    'evidence/deflektor-form/full40000/initial-state.json': 'd64b226588ada0b67b4408c7d6f000037408193dade2f08665ef8cffc1cd595d',
    'evidence/deflektor-programs/verified-final/lookup.json': 'ea736f857906e629c34792e4981bb4279c3954695dd885cf6aaa69ee4a5d6feb',
}
STATE_FIELDS = {
    'remaining': 'rowCountdown', 'rest': 'restCountdown', 'release_threshold': 'releaseThreshold',
    'detune': 'orderParameterC0C0', 'pitch_index': 'pitchIndex',
    'pwm_interval': 'driverC0BA', 'pwm_base': 'driverC0BD', 'pwm_elapsed': 'driverC0F0',
    'pwm_step': 'driverC0F3', 'pwm_position': 'driverC0F6',
    'pitch_selector': 'driverC0C6', 'pitch_wait': 'driverC0C3', 'pitch_position': 'driverC0C9',
    'wave_selector': 'driverC0CC', 'wave_countdown': 'driverC0D2', 'wave_position': 'driverC0CF',
    'score_pitch_selector': 'driverC0D5', 'score_pitch_countdown': 'driverC0ED',
    'score_pitch_position': 'driverC0EA', 'resonance_selector': 'driverC0FF',
    'resonance_countdown': 'driverC0FC', 'resonance_position': 'driverC0F9',
    'glide_wait': 'driverC0E1', 'glide_remaining': 'driverC0D8', 'glide_flags': 'driverC0E4',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sid', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError('Choose a fresh numeric description path')
    raw = args.sid.read_bytes()
    if sha(raw) != SOURCE_SHA:
        raise ValueError('Reference does not match pinned Deflektor')
    profile = psid_profile(raw, profile='pal-banked', subtune=1, host_base=0x0400)
    ram = [0] * 65536
    ram[profile['loadAddress']:profile['endAddress']] = profile['payload']
    inputs = {}
    hashes = {}
    for name, pin in INPUTS.items():
        data = (ROOT / name).read_bytes()
        hashes[name] = sha(data)
        if hashes[name] != pin:
            raise ValueError(f'Retained numeric input changed: {name}')
        inputs[name] = json.loads(data)
    original_tables = inputs['evidence/deflektor-form/full40000/tables.json']
    cold = inputs['evidence/deflektor-form/full40000/initial-state.json']
    lookup = inputs['evidence/deflektor-programs/verified-final/lookup.json']
    score = dict(orders=[dict(voiceIndex=row['voiceIndex'], pointer=0, bytes=list(row['bytes']))
                         for row in original_tables['orders']],
                 patterns=[dict(patternId=row['patternId'], pointer=0, bytes=list(row['bytes']))
                           for row in original_tables['patterns']],
                 initMappingDefaults=dict(bytes=list(original_tables['initMappingDefaults']['bytes'])),
                 recordTable=dict(records=[]))
    for record in original_tables['recordTable']['records']:
        offset = record['recordOffset']
        score['recordTable']['records'].append(dict(recordOffset=offset, fields=list(record['fields']),
            contextual_resonance_selector=ram[0xc010 + offset]))
    voices = []
    for source in cold['voices']:
        shadow = source['sidShadow']
        voice = {key: source[value] for key, value in STATE_FIELDS.items()}
        voice.update(frequency=shadow[0] | shadow[1] << 8, pulse_word=shadow[2] | shadow[3] << 8,
                     control=shadow[4], attack_decay=shadow[5], sustain_release=shadow[6],
                     glide_step=source['driverC0DB'] | source['driverC0DE'] << 8)
        assert set(voice) == set(VOICE_FIELDS)
        voices.append(voice)
    globals_ = cold['globals']
    waves = {str(program['sourceEvidence']['offset']): dict(loop=program['loop'],
             stages=deepcopy(program['stages'])) for program in lookup['wavePrograms'].values()}
    pitches = {}
    for selector in (8, 16, 24, 32, 40):
        header = ram[0xc9d1 + selector]
        stages = tuple(PitchStage(value >> 3, value & 7)
                       for value in ram[0xc9d2 + selector:0xc9d2 + selector + (header & 7)])
        pitches[str(selector)] = asdict(ScorePitchProgram(((header & 0x78) >> 3) + 1,
                                    (header & 0x38) >> 3, bool(header & 128), stages))
    description = dict(schemaVersion='sid-deflektor-player-v1', play_calls=40000,
        initial_state=dict(globals=dict(play_flag=globals_['playFlag'], cutoff_low=globals_['filterCutoffLow'],
            cutoff_high=globals_['filterCutoffHigh'], routing=globals_['filterRouting'],
            mode_volume=globals_['modeVolume']), voices=voices),
        score=score, frequency_words=[ram[0xc8cd + i] | ram[0xc92d + i] << 8 for i in range(256)],
        motion_table=ram[0xc98d:0xcaa5], resonance_table=ram[0xca11:0xcb12],
        wave_programs=waves, score_pitch_programs=pitches,
        sourceEvidence=dict(sourceSha256=SOURCE_SHA,
            sourceUrl='https://www.hvsc.de/download/C64Music/MUSICIANS/D/Daglish_Ben/Deflektor.sid',
            credit='Ben Daglish', originalBytes=len(raw), selectedSubtune=1, hostBase=0x0400,
            inputSha256=hashes, extractorSha256=sha(Path(__file__).read_bytes()),
            dependencies={name: sha((ROOT / 'scripts' / name).read_bytes()) for name in
                          ('psid_profile.py', 'deflektor_score.py', 'deflektor_player.py', 'deflektor_programs.py')},
            scorePointers=dict(orders=[dict(voiceIndex=row['voiceIndex'], pointer=row['pointer'])
                                      for row in original_tables['orders']],
                               patterns=[dict(patternId=row['patternId'], pointer=row['pointer'])
                                         for row in original_tables['patterns']]),
            tableRanges=dict(frequencyLowBase=0xc8cd, frequencyHighBase=0xc92d, frequencyWords=256,
                             motionBase=0xc98d, motionBytes=280, resonanceBase=0xca11, resonanceBytes=257),
            limits=['Numeric table extents retain opaque adjacent values in the source byte-index domain; they are not a claim of chromatic pitches or musical use of all entries. Frequency/motion/resonance are independently editable views: initial extraction preserves source overlaps, but editing one view does not implicitly edit another.',
                    'Cold software shadows survive native init; they do not establish SID hardware state before the first store. Init itself emits no SID stores.',
                    'Original SID/payload/CPU code, raw RAM images and captured runtime events/register ledgers are excluded from this editable description.']))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as output:
        json.dump(description, output, indent=2)
        output.write('\n')
    print(json.dumps(dict(path=str(args.output), sha256=sha(args.output.read_bytes()), bytes=args.output.stat().st_size)))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(str(error))
