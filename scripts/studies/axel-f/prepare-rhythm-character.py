#!/usr/bin/env python3
"""Prepare and verify a falling-triangle alternative to Axel F's maracas."""

import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('axel_rhythm_projection', Path(__file__).with_name('prepare-rhythm-trial.py'))
TRIAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRIAL)
fingerprint, read, require = TRIAL.fingerprint, TRIAL.read, TRIAL.require
from audio_comparison import Pcm16, measure_pcm, read_pcm16


def prepare(common, score, palette, projection, config):
    require(config['format'] == 'axel-f-rhythm-character-v1', 'Unsupported character trial')
    require(fingerprint(projection) == config['projectionFingerprint'] and
            fingerprint(palette) == config['paletteFingerprint'], 'Projection or accepted palette fingerprint changed')
    instrument = config['instrument']
    wave = instrument['wave']
    require(instrument['control'] == '0a' and instrument['frame1'] == '09' and
            instrument['hard_restart_adsr'] == '0f00' and not instrument['pulse'] and not instrument['filter'] and
            not instrument.get('vibrato', 0) and not instrument.get('vibrato_delay', 0),
            'Use an uncoupled, unfiltered triangle with native TEST onset')
    require(len(wave) >= 2 and all(row[0] == '11' and row[2] == '00' and 0x80 <= int(row[1], 16) < 0xe0 for row in wave)
            and all(int(a[1], 16) > int(b[1], 16) for a, b in zip(wave, wave[1:])),
            'Use a strictly falling absolute-pitch triangle table')
    projection = deepcopy(projection)
    projection['basePaletteFingerprint'] = config['paletteFingerprint']
    projection['instrument']['adsr'] = '1300'
    results = TRIAL.prepare(common, score, palette, projection)
    results['maracas.json'] = deepcopy(results['candidate.json'])
    results['maracas.json']['title'] = 'Axel F retained maracas'
    results['reference.json']['title'] = 'Axel F no percussion'
    candidate = results['candidate.json']
    candidate['title'] = 'Axel F falling triangle'
    candidate['instruments']['rhythm'] = deepcopy(instrument)
    for name in ('reference.json', 'maracas.json', 'candidate.json'):
        results[name]['sections'][0]['name'] = 'Source hook rhythm character comparison'
    results['adaptation.json'].update(instrumentFingerprint=fingerprint(instrument),
        sourceBasis=config['sourceBasis'], paletteFingerprint=fingerprint(palette),
        scope='Same source rhythm, durations and tonal palette; only the native percussion instrument changes.')
    return results


def verify_boundary(before, after, before_writes, after_writes):
    require(len(before) == len(after) and all(len(row) == 25 for row in before + after), 'Frame banks differ')
    changed = {i for a, b in zip(before, after) for i, (x, y) in enumerate(zip(a, b)) if x != y}
    require(changed and changed <= set(range(7, 14)), 'Percussion changed tonal voices or shared controls')
    ledgers = [[row for row in rows if not 0xd407 <= row['address'] <= 0xd40d] for rows in (before_writes, after_writes)]
    identity = lambda rows: [(r['phase'], r['tick'], r['address'], r['value']) for r in rows]
    require(identity(ledgers[0]) == identity(ledgers[1]), 'Ordered non-percussion stores changed')
    return dict(changedOffsets=sorted(changed), matchedOrderedNonPercussionStores=len(ledgers[0]),
        maximumInstructionStartDifferenceCycles=max(abs(a['instructionStartCycle'] - b['instructionStartCycle'])
                                                   for a, b in zip(*ledgers)))


def window(audio, first, last):
    require(audio.channels == 1 and 0 <= first < last <= audio.frames, 'Invalid mono diagnostic window')
    return measure_pcm(Pcm16(audio.sample_rate, 1, last - first, audio.samples[first:last], ''))


def verify(reference, maracas, candidate, triangle_only, triangle_muted, maracas_only, config, projection):
    reference, maracas, candidate = map(Path, (reference, maracas, candidate))
    frames = [read(p / 'native-song.frames.json') for p in (reference, maracas, candidate)]
    writes = [read(p / 'native-song.writes.json') for p in (reference, maracas, candidate)]
    boundaries = [verify_boundary(frames[i], frames[2], writes[i], writes[2]) for i in (0, 1)]
    manifests = [read(p / 'conversion.json') for p in (reference, maracas, candidate)]
    require(manifests[1]['voices'] == manifests[2]['voices'], 'Native rhythm or tonal schedule changed')
    manifest = manifests[2]
    notes = manifest['voices'][1]['notes']
    require(len(notes) == projection['expectedOnsets'], 'Source attack count changed')
    instrument = config['instrument']
    adsr = [int(instrument['adsr'][i:i + 2], 16) for i in (0, 2)]
    pitch_words = [round(440 * 2 ** ((int(row[1], 16) - 0x80 + 11 - 69) / 12) * 2 ** 24 / manifest['clockHz'])
                   for row in instrument['wave']]
    bodies = []
    for i, note in enumerate(notes):
        start = note['startTick']
        end = notes[i + 1]['startTick'] if i + 1 < len(notes) else manifest['scoreTicks']
        require(frames[2][start][11] == 9 and note['durationTicks'] == note['sourceDurationTicks'],
                'Native TEST onset or source duration changed')
        require(note['gateOffTick'] > start + 1, 'No full-pitch gated body')
        for age, state in enumerate(frames[2][start + 1:end]):
            tick = start + 1 + age
            require(state[11] == (0x11 if tick < note['gateOffTick'] else 0x10) and state[12:14] == adsr,
                    'Triangle body, release or ADSR changed')
            require(abs(state[7] + 256 * state[8] - pitch_words[min(age, len(pitch_words) - 1)]) <= 1,
                    'Falling triangle pitch trajectory changed')
        bodies.append(dict(startTick=start, gateOffTick=note['gateOffTick'], nextOnsetTick=end))
    for diagnostic, full in ((triangle_only, candidate), (triangle_muted, candidate), (maracas_only, maracas)):
        require(Path(str(diagnostic) + '.registers.tsv').read_bytes() == (full / 'native-song.wav.registers.tsv').read_bytes(),
                'Diagnostic renderer snapshots differ from its full SID')
    full, solo, muted, prior = [read_pcm16(p) for p in (candidate / 'native-song.wav', triangle_only, triangle_muted, maracas_only)]
    require(len({(a.frames, a.sample_rate, a.channels) for a in (full, solo, muted, prior)}) == 1, 'PCM layouts differ')
    phrase_end = round(manifest['scoreTicks'] / manifest['ticksPerSecond'] * full.sample_rate)
    metrics = {name: window(a, 0, phrase_end) for name, a in (('full', full), ('triangleOnly', solo), ('muted', muted), ('maracasOnly', prior))}
    require(all(m['clippedSamples'] == 0 and m['acRms'] > 1 for m in metrics.values()), 'Silent or clipped phrase')
    ratio = metrics['triangleOnly']['acRms'] / metrics['maracasOnly']['acRms']
    require(ratio <= config['maximumSoloRmsRatio'], 'New percussion exceeds the declared RMS screen')
    for body in bodies:
        first, last = [round(tick / manifest['ticksPerSecond'] * full.sample_rate) for tick in (body['startTick'] + 1, body['nextOnsetTick'])]
        body['diagnosticAcRms'] = window(solo, first, last)['acRms']
        require(body['diagnosticAcRms'] > 1, 'A scheduled percussion body is silent')
        body['beforeNextOnsetAcRms'] = window(solo, max(first, last - round(.02 * full.sample_rate)), last)['acRms']
    difference = [b - a for a, b in zip(muted.samples, full.samples)]
    require(any(difference), 'Candidate has no contribution in context')
    stop = manifest['stopTick'] / manifest['ticksPerSecond']
    release = window(full, round((stop - .5) * full.sample_rate), round((stop - .1) * full.sample_rate))
    require(release['acRms'] <= 16, 'Release fails to settle before volume clear')
    return dict(schemaVersion=1, boundaries=boundaries, sourceOnsets=len(notes), sourceDurationAdaptation=False,
        pitchWords=pitch_words, bodies=bodies, phrasePcm=metrics, triangleToMaracasSoloRmsRatio=ratio,
        sameSidDiagnosticSnapshotsIdentical=True, preStopReleaseAcRms=release['acRms'],
        sameSidContributionRms=(sum(v * v for v in difference) / len(difference)) ** .5,
        scope='Native scheduling, ordered tonal-store preservation and signal checks; not musical acceptance or linear audio stems.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    preparation = commands.add_parser('prepare')
    for name in ('common', 'score', 'palette', 'projection', 'config'):
        preparation.add_argument(name, type=Path)
    checking = commands.add_parser('verify')
    for name in ('reference', 'maracas', 'candidate', 'triangle_only', 'triangle_muted', 'maracas_only', 'config', 'projection'):
        checking.add_argument(name, type=Path)
    for sub in (preparation, checking):
        sub.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    require(args.output.resolve().is_relative_to(ROOT / 'build') and not args.output.exists(), 'Choose fresh private output under build/')
    if args.command == 'prepare':
        result = prepare(*(read(getattr(args, n)) for n in ('common', 'score', 'palette', 'projection', 'config')))
        args.output.mkdir(parents=True)
        for name, value in result.items():
            (args.output / name).write_text(json.dumps(value, indent=2) + '\n')
    else:
        result = verify(*(getattr(args, n) for n in ('reference', 'maracas', 'candidate', 'triangle_only', 'triangle_muted', 'maracas_only')),
                        read(args.config), read(args.projection))
        args.output.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
