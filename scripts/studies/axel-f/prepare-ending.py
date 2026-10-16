"""Prepare and check an ending-only release revision of the accepted Axel F form."""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from audio_comparison import Pcm16, measure_pcm, read_pcm16


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def project(score, native, config):
    bass = next(v for v in score['voices'] if v['name'] == 'bass')
    notes = [n for n in bass['events'] if n['midi'] is not None]
    beat = config['finalBassBeat']
    require(notes[-1]['startBeat'] == beat, 'Revision must start at the final bass note')
    require(native['instruments']['bass']['adsr'] == config['previousAdsr'] and score['tailTicks'] == config['previousTailTicks'], 'Accepted baseline changed')
    require(config['endingAdsr'][:3] == config['previousAdsr'][:3] and 0 < int(config['endingAdsr'][3], 16) < int(config['previousAdsr'][3], 16), 'Change only final bass release')
    require(0 < config['tailTicks'] < score['tailTicks'], 'Shorten only terminal padding')
    require('ending-bass' not in native['instruments'], 'Ending role already exists')
    score, native = deepcopy(score), deepcopy(native)
    score['tailTicks'] = config['tailTicks']
    native['instruments']['ending-bass'] = deepcopy(native['instruments']['bass'])
    native['instruments']['ending-bass']['adsr'] = config['endingAdsr']
    sections = []
    for section in native['sections']:
        start, end = section['startBeat'], section['endBeat']
        boundaries = sorted({start, end} | ({beat} if start < beat < end else set()))
        for a, b in zip(boundaries, boundaries[1:]):
            part = deepcopy(section)
            part.update(startBeat=a, endBeat=b)
            if a >= beat:
                require(part['voices']['bass'] == 'bass', 'Final bass uses another role')
                part['voices']['bass'] = 'ending-bass'
            sections.append(part)
    native['sections'] = sections
    native['score'] = 'candidate-score.json'
    return score, native


def import_accepted(run_path, output, config):
    receipt = read(run_path)
    require(receipt['status'] == 'completed', 'Accepted run is incomplete')
    mapping = [('full-input','trial/candidate.json','native.json'), ('full-input','trial/candidate-score.json','score.json')]
    mapping += [('candidate','song/'+name,'song/'+name) for name in ('native-song.wav','native-song.frames.json','native-song.writes.json','conversion.json','verification.json','export/candidate.sid','native-song.wav.registers.tsv')]
    retained = []
    for stage_id, relative, destination in mapping:
        stage = next(s for s in receipt['stages'] if s['id'] == stage_id)
        require(stage['status'] in ('completed','reused'), 'Incomplete input stage')
        source = Path(stage['attemptDirectory']) / relative
        require(source.resolve().is_relative_to(Path(run_path).resolve().parent / 'cache') and not source.is_symlink(), 'Input outside accepted cache')
        artifact = next(a for a in receipt['artifacts'] if a['stageId'] == stage_id and a['relativePath'] == relative)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        require(digest == artifact['sha256'], 'Accepted artifact changed: '+relative)
        if destination == 'song/native-song.wav':
            require(digest == config['acceptedWavSha256'], 'Different accepted performance')
        target = output / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        retained.append(dict(source=str(source), destination=destination, sha256=digest))
    write(output / 'retention.json', dict(sourceReceipt=str(run_path), files=retained))


def verify_frames(before, after, final_tick, stop_tick):
    require(len(before) >= stop_tick and len(after) > stop_tick, 'Incomplete execution')
    require(all(len(row) == 25 for row in before + after), 'Unexpected SID frame width')
    changes = []
    for tick, (a,b) in enumerate(zip(before[:stop_tick], after[:stop_tick])):
        for offset, (x,y) in enumerate(zip(a,b)):
            if x != y:
                require(tick >= final_tick and (offset,x,y) == (20,0x99,0x97), 'Change outside final bass release')
                changes.append(tick)
    require(changes, 'Final bass release did not change')
    return dict(firstChangedTick=min(changes), lastChangedTick=max(changes), registerOffset=20)


def portion(audio, start, end):
    first, last = round(start*audio.sample_rate), round(end*audio.sample_rate)
    return Pcm16(audio.sample_rate,audio.channels,last-first,audio.samples[first*audio.channels:last*audio.channels],'')


def verify(previous, candidate, config, control):
    before, after = [read(p/'conversion.json') for p in (previous,candidate)]
    final = before['voices'][2]['notes'][-1]
    require(final['startBeat'] == config['finalBassBeat'], 'Unexpected final note')
    ignored = {'pattern','row','byteOffset'}
    require(len(before['voices']) == len(after['voices']) == 3, 'Voice allocation changed')
    count = 0
    for voice, (a,b) in enumerate(zip(before['voices'],after['voices'])):
        require(len(a['notes']) == len(b['notes']), 'Note count changed')
        for index,(x,y) in enumerate(zip(a['notes'],b['notes'])):
            y = dict(y)
            if voice == 2 and index == len(a['notes'])-1:
                require(y['instrumentId'] == 'ending-bass', 'Final role missing')
                y.update(instrumentId=x['instrumentId'],instrument=x['instrument'])
            require({k:v for k,v in x.items() if k not in ignored} == {k:v for k,v in y.items() if k not in ignored}, 'Score or gate changed')
            count += 1
    for key in ('scoreTicks','clock','sidModel','sidCount','ticksPerSecond'):
        require(before[key] == after[key], 'Score form or target changed')
    frames = verify_frames(*[read(p/'native-song.frames.json') for p in (previous,candidate)],final['startTick'],after['stopTick'])
    audio = [read_pcm16(p/'native-song.wav') for p in (previous,candidate)]
    rate = after['ticksPerSecond']
    end = final['nativeGateOffTick']/rate
    metrics = [measure_pcm(portion(a,end+.4,end+.9)) for a in audio]
    require(metrics[1]['acRms'] < metrics[0]['acRms']*.6, 'Final release has no meaningful reduction')
    stop = after['stopTick']/rate
    settled = measure_pcm(portion(audio[1],stop-.5,stop-.1))
    require(settled['acRms'] <= 16, 'Final release is cut off by stop')
    require(measure_pcm(audio[1])['clippedSamples'] == 0, 'Candidate clips')
    first_change = round(final['startTick']/rate*audio[0].sample_rate)
    matched = read_pcm16(control / 'native-song.wav')
    same = matched.samples[:first_change] == audio[1].samples[:first_change]
    require(same, 'Matched-control PCM before the final bass note changed')
    control_frames = read(control / 'native-song.frames.json')
    verify_frames(control_frames, read(candidate / 'native-song.frames.json'), final['startTick'], after['stopTick'])
    ledgers = [read(p / 'native-song.writes.json') for p in (control, candidate)]
    require(len(ledgers[0]) == len(ledgers[1]), 'Matched store counts changed')
    for a, b in zip(*ledgers):
        require({k:v for k,v in a.items() if k != 'value'} == {k:v for k,v in b.items() if k != 'value'}, 'Matched instruction timing changed')
        if a['value'] != b['value']:
            require(a['phase'] == 'play' and a['tick'] >= final['startTick'] and (a['address'],a['value'],b['value']) == (0xd414,0x99,0x97), 'Matched store changed outside final release')
    return dict(schemaVersion=1,preservedNotes=count,registerBoundary=frames,finalBassGateOffSeconds=end,releaseWindows=metrics,preStopRelease=settled,matchedControlPrefixPcmIdentical=same,prefixSeconds=first_change/audio[0].sample_rate,oldDuration=audio[0].frames/audio[0].sample_rate,newDuration=audio[1].frames/audio[1].sample_rate,scope='Final bass release and terminal wait only; ending preference remains for human listening.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','verify'))
    parser.add_argument('source',type=Path)
    parser.add_argument('config',type=Path)
    parser.add_argument('--candidate',type=Path)
    parser.add_argument('--control',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    require(args.output.resolve().is_relative_to(ROOT/'build') and not args.output.exists(), 'Use fresh private output')
    config = read(args.config)
    if args.command == 'prepare':
        args.output.mkdir(parents=True)
        import_accepted(args.source,args.output/'previous',config)
        score,native = project(read(args.output/'previous/score.json'),read(args.output/'previous/native.json'),config)
        write(args.output/'candidate-score.json',score)
        write(args.output/'candidate.json',native)
        control = deepcopy(native)
        control['instruments']['ending-bass']['adsr'] = config['previousAdsr']
        write(args.output/'control.json',control)
    else:
        write(args.output,verify(args.source,args.candidate,config,args.control))


if __name__ == '__main__':
    main()
