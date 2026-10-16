"""Extend the selected Axel F lead and percussion into vacant full-score sections."""
import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
SPEC = importlib.util.spec_from_file_location('full_rhythm', Path(__file__).with_name('prepare-full-rhythm.py'))
FULL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FULL)
ROOT, read, require, fingerprint = (FULL.ROOT, FULL.read, FULL.require, FULL.fingerprint)

def drum(role):
    return role.startswith(('kick-', 'hat-', 'snare-'))

def project(score, palette, hook, selected, windows, release_beats):
    candidate, native = (deepcopy(score), deepcopy(palette))
    native['instruments']['lead'] = deepcopy(selected['instruments']['lead'])
    roles = {s['voices']['harmony'] for s in selected['sections']}
    require(roles and all((drum(r) and r in selected['instruments'] for r in roles)), 'Missing selected drum program')
    for role, program in selected['instruments'].items():
        if role in roles:
            require(role not in native['instruments'], 'Drum role collides with an existing tonal instrument')
            native['instruments'][role] = deepcopy(program)
    cycle = hook['totalBeats']
    require(cycle > 0 and 0 < release_beats < cycle, 'Invalid cycle or release reserve')
    events, omitted, reports = ([], [], [])
    previous_end = 0
    for start, end in windows:
        require(previous_end <= start < end <= score['totalBeats'], 'Overlapping or invalid percussion windows')
        previous_end = end
        require(not any((e['startBeat'] < end and start < e['startBeat'] + e['durationBeats'] for e in score['voices'][1]['events'])), 'Percussion window must be entirely vacant')
        count = len(events)
        offset = start
        while offset < end:
            for event in hook['voices'][1]['events']:
                onset = offset + event['startBeat']
                if onset >= end:
                    continue
                if onset >= end - release_beats:
                    omitted.append(dict(startBeat=onset, reason='Reserve release before returning tonal harmony'))
                    continue
                matches = [s for s in selected['sections'] if s['startBeat'] <= event['startBeat'] < s['endBeat']]
                require(len(matches) == 1, 'Ambiguous reviewed drum-role mapping')
                duration = min(event['durationBeats'], end - release_beats - onset)
                require(duration > 0, 'Empty projected drum body')
                events.append(dict(startBeat=onset, durationBeats=duration, midi=event['midi'], role=matches[0]['voices']['harmony'], sourceCycleBeat=event['startBeat']))
            offset += cycle
        reports.append(dict(startBeat=start, endBeat=end, onsets=len(events) - count))
    require(all((a['startBeat'] + a['durationBeats'] <= b['startBeat'] + 1e-09 for a, b in zip(events, events[1:]))), 'Overlapping projected drum notes')
    candidate['voices'][1]['events'] = sorted(deepcopy(score['voices'][1]['events']) + [{k: e[k] for k in ('startBeat', 'durationBeats', 'midi')} for e in events], key=lambda e: e['startBeat'])
    sections = []
    for section in palette['sections']:
        start, end = (section['startBeat'], section['endBeat'])
        boundaries = sorted({start, end} | {e['startBeat'] for e in events if start < e['startBeat'] < end} | {x for w in windows for x in w if start < x < end})
        for a, b in zip(boundaries, boundaries[1:]):
            part = deepcopy(section)
            part.update(startBeat=a, endBeat=b)
            window = next((w for w in windows if w[0] <= a < w[1]), None)
            if window:
                latest = next((e for e in reversed(events) if window[0] <= e['startBeat'] <= a), None)
                if latest:
                    part['voices']['harmony'] = latest['role']
            sections.append(part)
    native['sections'] = sections
    return (candidate, native, dict(schemaVersion=1, windows=reports, events=events, omittedForRelease=omitted, releaseReserveBeats=release_beats, cycleBeats=cycle))

def verify_notes(previous, candidate):
    ignored = {'eventIndex', 'pattern', 'row', 'byteOffset'}
    clean = lambda n: {k: v for k, v in n.items() if k not in ignored}
    require([[clean(n) for n in v['notes']] for v in previous] == [[clean(n) for n in v['notes'] if not drum(n['instrumentId'])] for v in candidate], 'A tonal pitch, gate, section or instrument changed')

def prepare(score, palette, hook, selected, config):
    require(config['format'] == 'axel-f-full-selected-v1', 'Unknown selected integration configuration')
    for value, key in ((score, 'baseScoreFingerprint'), (palette, 'basePaletteFingerprint'), (hook, 'hookScoreFingerprint'), (selected['instruments'], 'selectedInstrumentsFingerprint')):
        require(fingerprint(value) == config[key], 'Pinned score or selected palette changed')
    candidate, native, report = project(score, palette, hook, selected, config['windows'], config['releaseReserveBeats'])
    require(len(report['events']) == config['expectedDrumCount'], 'Projected drum count changed')
    reference = deepcopy(palette)
    reference['instruments'] = deepcopy(native['instruments'])
    reference['score'] = 'baseline-score.json'
    native['score'] = 'candidate-score.json'
    native['title'] = 'Axel F selected full'
    report['configurationFingerprint'] = fingerprint(config)
    report['expectedWeakDrumTicks'] = config['expectedWeakDrumTicks']
    report['scope'] = 'Repeat the reviewed master-derived 32-beat percussion cycle in two vacant harmony blocks; reserve the final half beat at each return. Preserve tonal notes and form; update only the main-lead program, not held support or upper lead.'
    return {'baseline-score.json': score, 'candidate-score.json': candidate, 'reference.json': reference, 'candidate.json': native, 'adaptation.json': report}

def verify(reference, candidate, original, adaptation, diagnostics):
    before, after, old = [read(p / 'conversion.json') for p in (reference, candidate, original)]
    verify_notes(before['voices'], after['voices'])
    verify_notes(old['voices'], after['voices'])
    require(all((before[k] == after[k] == old[k] for k in ('stopTick', 'scoreTicks', 'totalTicks', 'ticksPerSecond', 'clock', 'sidModel', 'sidCount'))), 'Native form or target changed')
    notes = after['voices'][1]['notes']
    rhythm = [n for n in notes if drum(n['instrumentId'])]
    require(len(rhythm) == len(adaptation['events']), 'Projected rhythm count changed')
    for note, event in zip(rhythm, adaptation['events']):
        require(all((note[k] == event[k] for k in ('startBeat', 'durationBeats', 'midi'))) and note['instrumentId'] == event['role'], 'Projected rhythm or selected role changed')
    frames = [read(p / 'native-song.frames.json') for p in (reference, candidate)]
    intervals = []
    boundaries = []
    for window in adaptation['windows']:
        selected = [n for n in rhythm if window['startBeat'] <= n['startBeat'] < window['endBeat']]
        incoming = next((n for n in before['voices'][1]['notes'] if n['startBeat'] >= window['endBeat']))
        intervals.append((selected[0]['startTick'], incoming['startTick']))
        boundaries.append(dict(firstDrumTick=selected[0]['startTick'], incomingTonalTick=incoming['startTick']))
    incoming = [b['incomingTonalTick'] for b in boundaries]
    offsets = FULL.verify_frames(*frames, intervals, incoming)
    lows = {t: (frames[0][t][7], frames[1][t][7]) for t in incoming}
    ledgers = [read(p / 'native-song.writes.json') for p in (reference, candidate)]
    stores, shift = FULL.verify_ordered_writes(*ledgers, intervals, lows)
    old_frames = read(original / 'native-song.frames.json')
    protected = []
    lead = after['voices'][0]['notes']
    for i, n in enumerate(lead):
        if n['instrumentId'] not in ('held-support', 'upper-lead'):
            continue
        end = lead[i + 1]['startTick'] if i + 1 < len(lead) else after['totalTicks']
        start = n['startTick']
        require(old_frames[start][1:7] == frames[1][start][1:7] and old_frames[start][4] == 9, 'Protected-role onset changed')
        require(all((a[:7] == b[:7] for a, b in zip(old_frames[start + 1:end], frames[1][start + 1:end]))), 'Protected lead-role body or release changed')
        protected.append(dict(startTick=start, endTick=end, role=n['instrumentId']))
    audio = [FULL.read_pcm16(diagnostics / (name + '-harmony.wav')) for name in ('reference', 'candidate')]
    for folder, name in zip((reference, candidate), ('reference', 'candidate')):
        FULL.verify_diagnostic_snapshots((folder / 'native-song.wav.registers.tsv').read_bytes(), (diagnostics / (name + '-harmony.wav.registers.tsv')).read_bytes())
    for b in boundaries:
        b['releaseChecks'] = [dict(tick=t, measurements=[FULL.measure_handover(a, t / after['ticksPerSecond']) for a in audio]) for t in (b['firstDrumTick'], b['incomingTonalTick'])]
    hits = []
    for n in rhythm:
        end = next((x['startTick'] for x in notes if x['startTick'] > n['startTick']), after['scoreTicks'])
        first, last = [round(t / after['ticksPerSecond'] * audio[1].sample_rate) for t in (n['startTick'] + 1, min(end, n['startTick'] + 10))]
        metric = FULL.measure_pcm(FULL.BALANCE.portion(audio[1], first, last))
        require(metric['clippedSamples'] == 0, 'Clipped full-form drum contribution')
        hits.append(dict(startTick=n['startTick'], role=n['instrumentId'], acRms=metric['acRms']))
    nonzero_hits, weak_ticks = FULL.verify_rendered_hits(hits, adaptation['expectedWeakDrumTicks'])
    full = FULL.read_pcm16(candidate / 'native-song.wav')
    stop = after['stopVolumeClearTick'] / after['ticksPerSecond']
    tail = FULL.measure_pcm(FULL.BALANCE.portion(full, round((stop - 0.5) * full.sample_rate), round((stop - 0.1) * full.sample_rate)))
    require(tail['acRms'] <= 16 and FULL.measure_pcm(full)['clippedSamples'] == 0, 'Full performance clips or has an unsettled ending')
    return dict(schemaVersion=1, preservedTonalNotes=sum((len(v['notes']) for v in before['voices'])), drumCount=len(hits), nonzeroDrumWindows=nonzero_hits, weakDrumTicks=weak_ticks, changedHarmonyOffsets=offsets, preservedStores=stores, maximumInstructionStartDifferenceCycles=shift, protectedRoles=protected, boundaries=boundaries, renderedHits=hits, preStopReleaseAcRms=tail['acRms'], scope='Complete score, selected role, register, contribution and ending checks; musical acceptance remains separate.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    for name in ('score', 'palette', 'hook', 'selected', 'config'):
        prep.add_argument(name, type=Path)
    check = sub.add_parser('verify')
    for name in ('reference', 'candidate', 'original', 'adaptation', 'diagnostics'):
        check.add_argument(name, type=Path)
    for p in (prep, check):
        p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(args.output.resolve().is_relative_to(ROOT / 'build') and (not args.output.exists()), 'Choose fresh private output')
    if args.command == 'prepare':
        results = prepare(*(read(getattr(args, k)) for k in ('score', 'palette', 'hook', 'selected', 'config')))
        args.output.mkdir(parents=True)
        for name, value in results.items():
            (args.output / name).write_text(json.dumps(value, indent=2) + '\n')
    else:
        result = verify(args.reference, args.candidate, args.original, read(args.adaptation), args.diagnostics)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
if __name__ == '__main__':
    main()
