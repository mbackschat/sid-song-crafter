#!/usr/bin/env python3
"""Audition source kick/snare roles with explicit one-voice collision handling."""

import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('axel_character_checks', Path(__file__).with_name('prepare-rhythm-character.py'))
CHARACTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHARACTER)
SPEC = importlib.util.spec_from_file_location('axel_kick_projection', Path(__file__).with_name('prepare-kick-trial.py'))
KICK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(KICK)
read, require, fingerprint, rational = KICK.read, KICK.require, KICK.fingerprint, KICK.rational
from audio_comparison import read_pcm16


def prepare(common, score, palette, projection, config):
    require(config['format'] == 'axel-f-drum-pair-v1', 'Unsupported drum pair')
    require(fingerprint(projection) == config['projectionFingerprint'] and fingerprint(palette) == config['paletteFingerprint'],
            'Projection or palette fingerprint changed')
    require(set(config['roles']) == {'kick', 'snare'} and config['collisionPriority'] == 'snare', 'Expected kick/snare with snare priority')
    for role, settings in config['roles'].items():
        instrument = settings['instrument']
        require(settings['sourceMidi'] == {'kick': 36, 'snare': 38}[role] and 0 < settings['durationSeconds'] <= .3,
                'Expected bounded source kick/snare roles')
        require(instrument['control'] == '0a' and instrument['frame1'] == '09' and instrument['hard_restart_adsr'] == '0f00'
                and not instrument['pulse'] and not instrument['filter'] and not instrument.get('vibrato', 0)
                and not instrument.get('vibrato_delay', 0), 'Expected uncoupled and unfiltered drum programs')
        require(instrument['wave'] and all(row[0] in ('11', '81') and row[2] == '00' and 0x80 <= int(row[1], 16) < 0xe0
                                          for row in instrument['wave']), 'Expected absolute triangle/noise drum tables')
    kick_config = dict(projection, format='axel-f-kick-trial-v1', basePaletteFingerprint=fingerprint(palette),
        kickMidi=36, expectedKickOnsets=config['expectedSourceCounts']['kick'], kickDurationSeconds=config['roles']['kick']['durationSeconds'],
        kickFingerprint=fingerprint(config['roles']['kick']['instrument']))
    results = KICK.prepare(common, score, palette, {'instruments': {'kick-fall': config['roles']['kick']['instrument']}}, kick_config)
    source_start, source_end = map(rational, projection['sourceWindowBeats'])
    seconds_per_beat = 60 / rational(score['quarterBpm'])
    drums = next(part['events'] for part in common['parts'] if part['id'] == 'drums')
    selected = {}
    counts = {}
    for role, settings in config['roles'].items():
        notes = [(i, e) for i, e in enumerate(drums) if e['midi'] == settings['sourceMidi'] and source_start <= rational(e['startBeat']) < source_end]
        counts[role] = len(notes)
        require(len({rational(e['startBeat']) for _, e in notes}) == len(notes), 'Duplicate same-role source onset')
        for i, event in notes:
            selected.setdefault(rational(event['startBeat']), {})[role] = (i, event)
    require(counts == config['expectedSourceCounts'], 'Source drum counts changed')
    onsets = sorted(selected)
    collisions = [onset for onset in onsets if len(selected[onset]) > 1]
    require(len(collisions) == config['expectedSharedOnsets'], 'Source collision count changed')
    events, origins, sections = [], [], []
    for onset, next_onset in zip(onsets, onsets[1:] + [source_end]):
        role = 'snare' if 'snare' in selected[onset] else 'kick'
        index, event = selected[onset][role]
        duration = min(rational(config['roles'][role]['durationSeconds']) / seconds_per_beat, next_onset - onset)
        events.append(dict(startBeat=float(onset - source_start), durationBeats=float(duration), midi=event['midi']))
        origins.append(dict(role=role, sourceEventIndex=index, sourceStartBeat=event['startBeat'], sourceDurationBeats=event['durationBeats'],
                            outputDurationBeats=float(duration), cappedByNextOnset=duration == next_onset - onset))
        sections.append(dict(name='Source percussion ' + role, startBeat=float(onset - source_start), endBeat=float(next_onset - source_start),
                             voices=dict(melody='lead', harmony=role, bass='bass')))
    require(sections and sections[0]['startBeat'] == 0, 'Expected source drum onset at hook entrance')
    output_counts = {role: sum(row['role'] == role for row in origins) for role in config['roles']}
    require(output_counts == config['expectedOutputCounts'], 'Output role counts changed')
    results['candidate-score.json']['voices'][1]['events'] = events
    for name in ('reference.json', 'candidate.json'):
        native = results[name]
        native['title'] = 'Axel F drum-role comparison'
        native['instruments']['snare'] = deepcopy(config['roles']['snare']['instrument'])
        native['sections'] = deepcopy(sections)
    results['adaptation.json'] = dict(schemaVersion=1, sourceSha256=projection['sourceSha256'], sourceWindowBeats=projection['sourceWindowBeats'],
        sourceCounts=counts, outputCounts=output_counts, sourceDurationAdaptation=True, origins=origins,
        omittedCollisions=[dict(sourceBeat=float(onset), omittedRole='kick', selectedRole='snare') for onset in collisions],
        sourceBasis=config['sourceBasis'], scope=config['scope'])
    return results


def verify_tonal_notes(before, after):
    # arrange-sidwizard.py assigns pattern IDs globally; added drum patterns renumber unchanged bass patterns.
    notes = lambda voice: [{key: value for key, value in note.items() if key != 'pattern'} for note in voice['notes']]
    require(notes(before) == notes(after), 'Native tonal notes changed')


def verify(reference, candidate, solo_path, muted_path, config, adaptation):
    reference, candidate = Path(reference), Path(candidate)
    before, after = [read(p / 'native-song.frames.json') for p in (reference, candidate)]
    boundary = CHARACTER.verify_boundary(before, after, read(reference / 'native-song.writes.json'), read(candidate / 'native-song.writes.json'))
    base, manifest = [read(p / 'conversion.json') for p in (reference, candidate)]
    for voice in (0, 2):
        verify_tonal_notes(base['voices'][voice], manifest['voices'][voice])
    notes = manifest['voices'][1]['notes']
    require(len(notes) == len(adaptation['origins']), 'Native drum count changed')
    samples_per_tick = 44100 / manifest['ticksPerSecond']
    bodies = []
    for i, (note, origin) in enumerate(zip(notes, adaptation['origins'])):
        role = origin['role']
        start = note['startTick']
        end = notes[i + 1]['startTick'] if i + 1 < len(notes) else manifest['scoreTicks']
        require(note['instrumentId'] == role and note['midi'] == config['roles'][role]['sourceMidi'], 'Native drum role changed')
        require(abs(note['startBeat'] - (float(rational(origin['sourceStartBeat'])) - adaptation['sourceWindowBeats'][0])) < 1e-9
                and note['durationBeats'] == origin['outputDurationBeats'], 'Source onset or declared duration adaptation changed')
        require(after[start][11] == 9 and note['gateOffTick'] > start + 1, 'Missing TEST or gated drum body')
        instrument = config['roles'][role]['instrument']
        adsr = [int(instrument['adsr'][j:j + 2], 16) for j in (0, 2)]
        for age, state in enumerate(after[start + 1:end]):
            row = instrument['wave'][min(age, len(instrument['wave']) - 1)]
            word = round(440 * 2 ** ((int(row[1], 16) - 0x80 + 11 - 69) / 12) * 2 ** 24 / manifest['clockHz'])
            control = int(row[0], 16) if start + 1 + age < note['gateOffTick'] else int(row[0], 16) & 0xfe
            require(state[11] == control and state[12:14] == adsr and abs(state[7] + 256 * state[8] - word) <= 1,
                    'Executed drum waveform, pitch, envelope or gate changed')
        bodies.append(dict(role=role, startTick=start, gateOffTick=note['gateOffTick'], nextOnsetTick=end))
    for p in (solo_path, muted_path):
        require(Path(str(p) + '.registers.tsv').read_bytes() == (candidate / 'native-song.wav.registers.tsv').read_bytes(),
                'Diagnostic snapshot does not match full SID')
    full, solo, muted = [read_pcm16(p) for p in (candidate / 'native-song.wav', solo_path, muted_path)]
    require(len({(a.frames, a.sample_rate, a.channels) for a in (full, solo, muted)}) == 1 and full.sample_rate == 44100, 'PCM layout changed')
    phrase_end = round(manifest['scoreTicks'] * samples_per_tick)
    metrics = {name: CHARACTER.window(a, 0, phrase_end) for name, a in (('full', full), ('drumsOnly', solo), ('muted', muted))}
    require(all(m['clippedSamples'] == 0 and m['acRms'] > 1 for m in metrics.values()), 'Silent or clipped phrase')
    for body in bodies:
        first, last = [round(t * samples_per_tick) for t in (body['startTick'] + 1, body['nextOnsetTick'])]
        body['diagnosticAcRms'] = CHARACTER.window(solo, first, last)['acRms']
        require(body['diagnosticAcRms'] > 1, 'Silent drum attack')
        body['beforeNextOnsetAcRms'] = CHARACTER.window(solo, max(first, last - 882), last)['acRms']
    stop = manifest['stopTick'] / manifest['ticksPerSecond']
    release = CHARACTER.window(full, round((stop - .5) * full.sample_rate), round((stop - .1) * full.sample_rate))
    require(release['acRms'] <= 16, 'Release does not settle before volume clear')
    difference = [b - a for a, b in zip(muted.samples, full.samples)]
    require(any(difference), 'Drums have no signal contribution')
    return dict(schemaVersion=1, boundary=boundary, sourceDurationAdaptation=True, outputCounts=adaptation['outputCounts'],
        sourceCounts=adaptation['sourceCounts'], sharedOnsets=len(adaptation['omittedCollisions']), bodies=bodies, phrasePcm=metrics,
        preStopReleaseAcRms=release['acRms'], sameSidContributionRms=(sum(v * v for v in difference) / len(difference)) ** .5,
        diagnosticSnapshotsMatch=True, scope='Source-role reduction, declared durations, native body and unchanged tonal controls; not musical acceptance.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    preparation = commands.add_parser('prepare')
    for name in ('common', 'score', 'palette', 'projection', 'config'):
        preparation.add_argument(name, type=Path)
    checking = commands.add_parser('verify')
    for name in ('reference', 'candidate', 'solo', 'muted', 'config', 'adaptation'):
        checking.add_argument(name, type=Path)
    for sub in (preparation, checking):
        sub.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    require(args.output.resolve().is_relative_to(ROOT / 'build') and not args.output.exists(), 'Choose fresh private output under build/')
    if args.command == 'prepare':
        results = prepare(*(read(getattr(args, n)) for n in ('common', 'score', 'palette', 'projection', 'config')))
        args.output.mkdir(parents=True)
        for name, value in results.items():
            (args.output / name).write_text(json.dumps(value, indent=2) + '\n')
    else:
        result = verify(args.reference, args.candidate, args.solo, args.muted, read(args.config), read(args.adaptation))
        args.output.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
