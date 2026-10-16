"""Separate chip response from native envelope contour on the preferred varied rhythm."""

import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('axel_timbre_checks', Path(__file__).with_name('prepare-drum-pair.py'))
PAIR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PAIR)
read, require = PAIR.read, PAIR.require
from audio_comparison import read_pcm16, measure_pcm


def variants(base):
    require((base['sidModel'], base['sidCount'], base['clock']) == ('MOS8580', 1, 'pal'), 'Expected current PAL mono palette')
    require(base['instruments']['lead']['adsr'] == '0a49', 'Current lead envelope changed')
    baseline, chip, contour = (deepcopy(base) for _ in range(3))
    chip['sidModel'] = 'MOS6581'
    contour['instruments']['lead']['adsr'] = '0847'
    drums = {role: instrument for role, instrument in contour['instruments'].items()
             if role.startswith(('kick-', 'hat-', 'snare-'))}
    require(drums, 'No master-derived drums')
    for instrument in drums.values():
        require(instrument['adsr'] in ('2052', '2022', '2092'), 'Current drum envelope changed')
        instrument['adsr'] = '4' + instrument['adsr'][1:]
    return dict(baseline=baseline, chip=chip, contour=contour)


def store_boundary(before, after, allowed):
    identity = lambda row: (row['phase'], row['tick'], row['address'])
    require([identity(row) for row in before] == [identity(row) for row in after], 'Store timing or order changed')
    changed = {a['address'] for a, b in zip(before, after) if a['value'] != b['value']}
    require(changed <= allowed, 'A protected register changed')
    return dict(changedAddresses=[f'{a:04x}' for a in sorted(changed)], orderedStores=len(before))


def verify(baseline, chip, contour, diagnostics):
    paths = dict(baseline=baseline, chip=chip, contour=contour)
    manifests = {name: read(path / 'conversion.json') for name, path in paths.items()}
    writes = {name: read(path / 'native-song.writes.json') for name, path in paths.items()}
    checks = {}
    for name, allowed in (('chip', set()), ('contour', {0xd405, 0xd406, 0xd40c})):
        for voice in range(3):
            PAIR.verify_tonal_notes(manifests['baseline']['voices'][voice], manifests[name]['voices'][voice])
        checks[name] = store_boundary(writes['baseline'], writes[name], allowed)
    require(checks['contour']['changedAddresses'] == ['d405', 'd406', 'd40c'], 'Expected envelope changes are absent')
    require(manifests['chip']['sidModel'] == 'MOS6581' and manifests['contour']['sidModel'] == 'MOS8580', 'Chip targets changed')
    pcm = {name: read_pcm16(path / 'native-song.wav') for name, path in paths.items()}
    require(len({(a.frames, a.channels, a.sample_rate) for a in pcm.values()}) == 1, 'Audio layouts differ')
    metrics = {name: measure_pcm(audio) for name, audio in pcm.items()}
    require(all(m['acRms'] > 1 and m['clippedSamples'] == 0 for m in metrics.values()), 'Silent or clipped audio')
    for name in ('chip', 'contour'):
        require(pcm[name].samples != pcm['baseline'].samples, 'No rendered difference')
    observations = {}
    for name in ('baseline', 'contour'):
        solo_path = diagnostics / f'{name}-drums.wav'
        require(Path(str(solo_path) + '.registers.tsv').read_bytes() == (paths[name] / 'native-song.wav.registers.tsv').read_bytes(),
                'Diagnostic and full render snapshots differ')
        solo = read_pcm16(solo_path)
        bodies = []
        notes = manifests[name]['voices'][1]['notes']
        for index, note in enumerate(notes):
            start = note['startTick']
            end = notes[index + 1]['startTick'] if index + 1 < len(notes) else manifests[name]['scoreTicks']
            rate = manifests[name]['ticksPerSecond']
            first, last = [round(t / rate * solo.sample_rate) for t in (start + 1, end)]
            metric = PAIR.CHARACTER.window(solo, first, last)
            require(metric['acRms'] > 1 and metric['clippedSamples'] == 0, 'Silent or clipped drum body')
            bodies.append(dict(startTick=start, instrumentId=note['instrumentId'], acRms=metric['acRms'], peak=metric['peak']))
        observations[name] = dict(whole=measure_pcm(solo), bodies=bodies)
    return dict(schemaVersion=1, boundaries=checks, pcm=metrics, drumDiagnostics=observations,
                scope='Same source notes, rhythm, note/gate schedule and bass program. Chip-only versus envelope-only interventions; measurable output differences do not establish snap, punch or preference.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('recipe', type=Path)
    prep.add_argument('score', type=Path)
    check = sub.add_parser('verify')
    for name in ('baseline', 'chip', 'contour', 'diagnostics'):
        check.add_argument(name, type=Path)
    for command in (prep, check):
        command.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(args.output.resolve().is_relative_to(ROOT / 'build') and not args.output.exists(), 'Choose fresh private output')
    if args.command == 'prepare':
        recipes = variants(read(args.recipe))
        args.output.mkdir(parents=True)
        shutil.copyfile(args.score, args.output / 'score.json')
        for name, recipe in recipes.items():
            recipe['score'] = 'score.json'
            (args.output / f'{name}.json').write_text(json.dumps(recipe, indent=2) + '\n')
    else:
        report = verify(args.baseline, args.chip, args.contour, args.diagnostics)
        args.output.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
