"""Adapt the executed master percussion's phrase contrast to the retained MIDI hook."""

import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('axel_drum_checks', Path(__file__).with_name('prepare-drum-pair.py'))
PAIR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PAIR)
read, require = PAIR.read, PAIR.require
SOURCE_RATE = 985248 / 17921
NATIVE_RATE = 985248 / 19656
PROGRAMS = {'2050': 'kick', '2020': 'hat', '2090': 'snare'}


def program(adsr, initial_word):
    require(adsr in PROGRAMS, 'Unknown percussion program')
    wave = []
    body_calls = {'2050': 16, '2020': 4, '2090': 12}[adsr]
    for update in range(math.ceil(body_calls * NATIVE_RATE / SOURCE_RATE)):
        age = math.floor(update * SOURCE_RATE / NATIVE_RATE)
        match adsr:
            case '2050':
                word, control, transpose = max(258, initial_word - 511 * age), '81' if age < 4 else '11', -4
            case '2020':
                word, control, transpose = initial_word, '81', 0
            case '2090':
                word, control, transpose = max(2, initial_word - 3071 * age), '81', 0
        midi = round(69 + 12 * math.log2(word * 985248 / 2 ** 24 / 440)) + transpose
        if midi < 12:
            break
        require(midi < 107, 'Native absolute pitch outside supported range')
        wave.append([control, f'{midi - 11 + 0x80:02x}', '00'])
    # SID-Wizard player.asm WFARPTB treats 00..0F as speed commands; finish with gate-off, not source control 01. Pitch 80 is also NOP, so 81 is the floor.
    wave.append([f'{int(wave[-1][0], 16) & 0xfe:02x}', '81' if adsr == '2090' else wave[-1][1], '00'])
    return dict(name=PROGRAMS[adsr].upper(), control='0a', hard_restart_adsr='0f00',
                adsr=adsr[:3] + '2', frame1='09', wave=wave, pulse=[], filter=[])


def extract(writes, snapshots, start, end):
    events = []
    for row in writes:
        if row['writerPc'] != 0xc8cf or not start <= row['tick'] < end:
            continue
        tick = row['tick']
        require((tick - start) % 8 == 0, 'Percussion onset left the verified eight-call grid')
        registers = bytes.fromhex(snapshots[tick]['sid'])
        adsr = registers[19:21].hex()
        require(adsr in PROGRAMS, 'Unknown source percussion program')
        word = int.from_bytes(registers[14:16], 'little')
        events.append(dict(beat=(tick - start) / 32, sourceTick=tick, adsr=adsr, initialWord=word,
                           role=f'{PROGRAMS[adsr]}-{word:04x}'))
    require(events and len({e['sourceTick'] for e in events}) == len(events), 'Missing or duplicate source onsets')
    return events


def prepare(common, score, palette, projection, pair_config, snapshots_path, writes_path, config):
    require(config['format'] == 'axel-f-master-rhythm-v1', 'Unknown master rhythm configuration')
    for path, key in ((snapshots_path, 'snapshotsContentSha256'), (writes_path, 'writesContentSha256')):
        require(hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest() == config[key], 'Master execution fingerprint changed')
    snapshots, writes = [json.loads(gzip.decompress(path.read_bytes())) for path in (snapshots_path, writes_path)]
    start, end = config['calls']
    events = extract(writes, snapshots, start, end)
    require(Counter(PROGRAMS[e['adsr']] for e in events) == config['expectedCounts'], 'Master role counts changed')
    require([sum(first <= e['beat'] < first + 8 for e in events) for first in (0, 8, 16, 24)] == [19, 22, 19, 22],
            'Master phrase contrast changed')
    results = PAIR.prepare(common, score, palette, projection, pair_config)
    # The lead's first 14 attacks settle the 32-call beat mapping against the independent MIDI hook.
    master_lead = [(r['tick'] - start) / 32 for r in writes if r['writerPc'] == 0xc775 and start <= r['tick'] < start + 256]
    midi_lead = [e['startBeat'] for e in results['baseline-score.json']['voices'][0]['events'] if e['startBeat'] < 8]
    require(master_lead == midi_lead, 'Master beat mapping disagrees with the first MIDI lead phrase')
    lead_word = int.from_bytes(bytes.fromhex(snapshots[start]['sid'])[7:9], 'little')
    lead_midi = round(69 + 12 * math.log2(lead_word * 985248 / 2 ** 24 / 440))
    require(results['baseline-score.json']['voices'][0]['events'][0]['midi'] - lead_midi == -4, 'Tonal transposition changed')
    roles = {}
    origins, notes, sections = [], [], []
    seconds_per_beat = 60 / float(score['quarterBpm'])
    for event, next_beat in zip(events, [e['beat'] for e in events[1:]] + [32]):
        role = event['role']
        if role not in roles:
            roles[role] = dict(sourceMidi={'2050': 36, '2020': 42, '2090': 38}[event['adsr']],
                               instrument=program(event['adsr'], event['initialWord']))
        duration = min((len(roles[role]['instrument']['wave']) + 1) / NATIVE_RATE / seconds_per_beat, next_beat - event['beat'])
        notes.append(dict(startBeat=event['beat'], durationBeats=duration, midi=roles[role]['sourceMidi']))
        origins.append(dict(**event, sourceStartBeat=event['beat'], outputDurationBeats=duration))
        sections.append(dict(name='Master-derived percussion', startBeat=event['beat'], endBeat=next_beat,
                             voices=dict(melody='lead', harmony=role, bass='bass')))
    results['candidate-score.json']['voices'][1]['events'] = notes
    for name in ('reference.json', 'candidate.json'):
        results[name]['title'] = 'Axel F varied percussion'
        results[name]['instruments'].update({role: settings['instrument'] for role, settings in roles.items()})
        results[name]['sections'] = deepcopy(sections)
    results['runtime-config.json'] = dict(roles=roles)
    results['adaptation.json'] = dict(schemaVersion=1, sourceWindowBeats=[0, 32], origins=origins,
        sourceCounts=config['expectedCounts'], outputCounts=dict(Counter(e['role'] for e in events)), omittedCollisions=[],
        sourceCalls=[start, end], callsPerBeat=32, leadOnsetMappingVerified=True, pitchedDrumTranspose=-4,
        sourceDurationAdaptation=True, scope=config['scope'])
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('common', 'score', 'palette', 'projection', 'pair_config', 'snapshots', 'writes', 'config'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(args.output.resolve().is_relative_to(ROOT / 'build') and not args.output.exists(), 'Choose fresh output under build/')
    results = prepare(*(read(getattr(args, name)) for name in ('common', 'score', 'palette', 'projection', 'pair_config')),
                      args.snapshots, args.writes, read(args.config))
    args.output.mkdir(parents=True)
    for name, value in results.items():
        (args.output / name).write_text(json.dumps(value, indent=2) + '\n')


if __name__ == '__main__':
    main()
