"""Validate and excerpt a centered six-voice Rambo listening presentation."""

import argparse
from array import array
import hashlib
import json
from pathlib import Path
import sys
import wave


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from audio_comparison import Pcm16, measure_pcm, read_pcm16
from verify_player import require


MATRIX = [[.5, .35], [.5, .65]]
WINDOWS = (('phrase', 88, 104), ('early', 32, 48), ('ending', 205, 225))


def window(audio, start, end):
    first, last = round(start * audio.sample_rate), round(end * audio.sample_rate)
    require(0 <= first < last <= audio.frames, 'Window exceeds initialized audio')
    return Pcm16(audio.sample_rate, audio.channels, last - first,
                 audio.samples[first * audio.channels:last * audio.channels], '')


def contribution(raw):
    require(raw.channels == 2, 'Contribution review requires independent chip stereo')
    primary, support = measure_pcm(raw)['perChannel']
    require(primary['acRms'] > 0, 'Contribution review has no primary signal')
    ratio = support['acRms'] / primary['acRms']
    position = 'below' if ratio < .2 else 'above' if ratio > .8 else 'inside'
    return dict(primaryAcRms=primary['acRms'], supportAcRms=support['acRms'],
                supportToPrimaryAcRmsRatio=ratio, reviewBand=[.2, .8],
                reviewBandPosition=position, normalization='none', audibilityEstablished=False,
                scope='Raw chip-level warning band for human review; no automatic gain change or musical verdict.')


def support_roles(baseline, omissions):
    require(baseline.channels == 1 and len(omissions) == 3,
            'Support role checks require a mono baseline and three omission diagnostics')
    selected = window(baseline, 88, 104)
    baseline_level = measure_pcm(selected)['acRms']
    require(baseline_level > 0, 'Support baseline has no phrase signal')
    roles = []
    for voice, omitted in enumerate(omissions, 1):
        require((omitted.channels, omitted.sample_rate, omitted.frames) ==
                (baseline.channels, baseline.sample_rate, baseline.frames),
                'Support omission format/duration differs from its baseline')
        require(measure_pcm(omitted)['clippedSamples'] == 0, 'Support omission contains PCM rail samples')
        omitted_clip = window(omitted, 88, 104)
        total = sum(a - b for a, b in zip(selected.samples, omitted_clip.samples))
        squares = sum((a - b) ** 2 for a, b in zip(selected.samples, omitted_clip.samples))
        rms = ((squares * selected.frames - total * total) / selected.frames ** 2) ** .5
        require(rms > 0, f'Added support voice {voice} has no rendered contribution in seconds 88–104')
        roles.append(dict(voice=voice, seconds=[88, 104], baselineSha256=baseline.sha256,
                          omissionSha256=omitted.sha256, residualAcRms=rms,
                          residualToSupportAcRmsRatio=rms / baseline_level,
                          scope='Control-mask omission residual, not an exact independent stem or an audibility verdict.'))
    return roles


def check_signal(faithful, raw, centered, *, sample_rate=44100):
    require((faithful.channels, raw.channels, centered.channels) == (1, 2, 2),
            'Expected faithful mono, raw chip stereo and centered presentation stereo')
    inputs, tails = [], []
    for label, value in (('faithful', faithful), ('raw', raw), ('centered', centered)):
        require(value.sample_rate == sample_rate and value.frames == 225 * sample_rate,
                f'{label} must contain exactly 225 seconds at {sample_rate} Hz')
        metrics = measure_pcm(value)
        require(metrics['clippedSamples'] == 0, f'{label} contains PCM rail samples')
        require(all(channel['acRms'] > 0 for channel in metrics['perChannel']),
                f'{label} has a silent or DC-only channel')
        inputs.append(dict(label=label, sha256=value.sha256, **metrics))
        tail = measure_pcm(window(value, 224, 225))
        require(all(channel['acRms'] <= 1 for channel in tail['perChannel']),
                f'{label} has an unsettled final tail')
        tails.append(dict(label=label, seconds=[224, 225], metrics=tail))
    unequal = {}
    for label, value in (('raw', raw), ('centered', centered)):
        unequal[label] = sum(a != b for a, b in zip(value.samples[::2], value.samples[1::2]))
        require(unequal[label] > 0, f'{label} has identical channels')
    closing = {label: measure_pcm(window(value, 205, 211))
               for label, value in (('faithful', faithful), ('raw', raw), ('centered', centered))}
    require(closing['faithful']['acRms'] >= 32 and closing['raw']['perChannel'][0]['acRms'] >= 32,
            'The faithful primary lost its closing body')
    require(all(channel['acRms'] >= 32 for channel in closing['centered']['perChannel']),
            'The centered presentation lost its closing body')
    levels = [dict(name='full', seconds=[0, 225], **contribution(raw))]
    levels.extend(dict(name=name, seconds=[start, end], **contribution(window(raw, start, end)))
                  for name, start, end in WINDOWS if name != 'ending')
    return dict(schemaVersion=1, passed=True, inputs=inputs, unequalChannelFrames=unequal,
                matrix=MATRIX, normalization='none', closingBody=dict(seconds=[205, 211], metrics=closing),
                finalTail=dict(maximumChannelAcRms=1, measurements=tails),
                supportContribution=levels,
                contributionWarnings=[dict(name=row['name'], position=row['reviewBandPosition'],
                                           supportToPrimaryAcRmsRatio=row['supportToPrimaryAcRmsRatio'])
                                      for row in levels if row['reviewBandPosition'] != 'inside'],
                claims=dict(pcmIdentity=False, audibilityEstablished=False, musicalAcceptance=False),
                listeningVerdict=None)


def verify_matrix(raw, centered):
    for frame, (primary, support) in enumerate(zip(raw.samples[::2], raw.samples[1::2])):
        expected = (round(.5 * primary + .35 * support), round(.5 * primary + .65 * support))
        if (centered.samples[2 * frame], centered.samples[2 * frame + 1]) != expected:
            raise ValueError(f'Centered PCM differs from the declared matrix at frame {frame}')
    return dict(checkedFrames=raw.frames, exactQuantizedPcm=True,
                rounding='nearest integer, ties to even',
                scope='Every presentation frame matches the declared two-monobus WAV matrix; no PSID per-voice pan is implied.')


def write_pcm(path, audio, created):
    samples = array('h', audio.samples)
    if sys.byteorder != 'little':
        samples.byteswap()
    with path.open('xb') as handle:
        created.append(path)
        with wave.open(handle, 'wb') as target:
            target.setparams((audio.channels, 2, audio.sample_rate, 0, 'NONE', 'not compressed'))
            target.writeframes(samples.tobytes())


def prepare(faithful_path, raw_path, presentation, output, *, support_path=None, omissions=None, sample_rate=44100):
    presentation, output = Path(presentation), Path(output)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh preparation directory')
    faithful, raw, centered = (read_pcm16(path) for path in
                               (faithful_path, raw_path, presentation / 'dual-listening-stereo.wav'))
    mix = json.loads((presentation / 'listening.json').read_text())
    require(mix['matrices']['listeningStereo'] == MATRIX and mix['normalization'] == 'none',
            'The presentation matrix must center the faithful primary without independent normalization')
    require(mix['input']['sha256'] == raw.sha256 and mix['outputs']['stereo']['sha256'] == centered.sha256,
            'The presentation receipt does not match the raw input and centered output')
    report = check_signal(faithful, raw, centered, sample_rate=sample_rate)
    report['matrixVerification'] = verify_matrix(raw, centered)
    require((support_path is None) == (omissions is None), 'Supply support baseline and omissions together')
    if support_path is not None:
        support = read_pcm16(support_path)
        require(support.sample_rate == sample_rate and support.frames == 104 * sample_rate,
                'Support diagnostics must cover exactly 104 initialized seconds')
        require(measure_pcm(support)['clippedSamples'] == 0, 'Support baseline contains PCM rail samples')
        report['supportRoles'] = support_roles(support, [read_pcm16(path) for path in omissions])
    report['mixReceiptSha256'] = hashlib.sha256((presentation / 'listening.json').read_bytes()).hexdigest()
    report['sourcePaths'] = dict(faithful=str(Path(faithful_path).resolve()), raw=str(Path(raw_path).resolve()),
                                 centered=str((presentation / 'dual-listening-stereo.wav').resolve()))
    reference = Pcm16(faithful.sample_rate, 2, faithful.frames,
                      array('h', (round(.5 * value) for sample in faithful.samples for value in (sample, sample))), '')
    report['referenceMatrix'] = [[.5], [.5]]
    report['windows'], report['outputs'] = [], {}
    output.mkdir(parents=True)
    created = []
    try:
        audio_outputs = [('faithful-dual-mono.wav', reference)]
        for name, start, end in WINDOWS:
            audio_outputs.extend((f'{label}-{name}.wav', window(value, start, end))
                                 for label, value in (('faithful', reference), ('ensemble', centered)))
            report['windows'].append(dict(name=name, seconds=[start, end],
                                           startFrame=start * sample_rate, endFrame=end * sample_rate))
        for filename, value in audio_outputs:
            path = output / filename
            write_pcm(path, value, created)
            report['outputs'][filename] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                               channels=value.channels, frames=value.frames,
                                               sourceGain=.5 if filename.startswith('faithful-') else 1)
        with (output / 'signal.json').open('x') as handle:
            created.append(output / 'signal.json')
            json.dump(report, handle, indent=2, allow_nan=False)
            handle.write('\n')
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        output.rmdir()
        raise
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--faithful', type=Path, required=True)
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--presentation', type=Path, required=True)
    parser.add_argument('--support', type=Path, required=True)
    parser.add_argument('--omissions', type=Path, nargs=3, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = prepare(args.faithful, args.raw, args.presentation, args.output,
                     support_path=args.support, omissions=args.omissions)
    print(f"Prepared centered ensemble; {len(report['contributionWarnings'])} raw contribution warnings for review")


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f'Rambo ensemble listening preparation failed: {error}')
