"""Check and prepare the faithful three-part Rambo split across two SID chips."""

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


def dual_mono(audio):
    require(audio.channels == 1, 'The faithful reference must be mono')
    return Pcm16(audio.sample_rate, 2, audio.frames,
                 array('h', (value for sample in audio.samples for value in (sample, sample))), '')


def mono_sum(audio):
    require(audio.channels == 2, 'The candidate must be stereo')
    return Pcm16(audio.sample_rate, 1, audio.frames,
                 array('h', (round((left + right) / 2)
                             for left, right in zip(audio.samples[::2], audio.samples[1::2]))), '')


def window(audio, start, end):
    first, last = round(start * audio.sample_rate), round(end * audio.sample_rate)
    require(0 <= first < last <= audio.frames, 'Window exceeds the initialized render')
    return Pcm16(audio.sample_rate, audio.channels, last - first,
                 audio.samples[first * audio.channels:last * audio.channels], '')


def check_signal(faithful, candidate, *, sample_rate=44100):
    require(faithful.channels == 1 and candidate.channels == 2,
            'Expected faithful mono and raw candidate stereo')
    metrics = []
    endings = []
    for label, value in (('faithful', faithful), ('stereo', candidate)):
        require(value.sample_rate == sample_rate and value.frames == 225 * sample_rate,
                f'{label} must contain the complete 225-second initialized render at {sample_rate} Hz')
        measured = measure_pcm(value)
        require(measured['clippedSamples'] == 0, f'{label} contains clipped PCM rail samples')
        require(all(channel['acRms'] > 0 for channel in measured['perChannel']),
                f'{label} has a silent or DC-only channel')
        metrics.append(dict(label=label, sha256=value.sha256, **measured))
        tail = measure_pcm(window(value, 224, 225))
        require(all(channel['acRms'] <= 1 for channel in tail['perChannel']),
                f'{label} final tail exceeds one PCM16 AC RMS unit')
        endings.append(dict(label=label, seconds=[224, 225], metrics=tail))
    unequal = sum(left != right for left, right in zip(candidate.samples[::2], candidate.samples[1::2]))
    require(unequal > 0, 'Stereo candidate collapsed to identical channels')
    closing = measure_pcm(window(candidate, 205, 211))
    require(all(channel['acRms'] >= 32 for channel in closing['perChannel']),
            'Stereo candidate lost a chip\'s closing body at seconds 205–211')
    return dict(schemaVersion=1, passed=True, durationSeconds=225, inputs=metrics,
                unequalChannelFrames=unequal,
                closingBody=dict(seconds=[205, 211], metrics=closing, minimumAcRms=32),
                finalTail=dict(maximumChannelAcRms=1, measurements=endings),
                claims=dict(pcmIdentity=False, perceptualAgreement=False, musicalAcceptance=False),
                listeningReview=None)


def write_pcm(path, audio, created):
    samples = array('h', audio.samples)
    if sys.byteorder != 'little':
        samples.byteswap()
    with path.open('xb') as handle:
        created.append(path)
        with wave.open(handle, 'wb') as output:
            output.setparams((audio.channels, 2, audio.sample_rate, 0, 'NONE', 'not compressed'))
            output.writeframes(samples.tobytes())


def prepare(faithful_path, candidate_path, output, *, sample_rate=44100):
    output = Path(output)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh preparation directory')
    faithful, candidate = (read_pcm16(path) for path in (faithful_path, candidate_path))
    report = check_signal(faithful, candidate, sample_rate=sample_rate)
    reference, summed = dual_mono(faithful), mono_sum(candidate)
    summed_metrics = measure_pcm(summed)
    require(summed_metrics['clippedSamples'] == 0 and summed_metrics['acRms'] > 0,
            'The arithmetic mono sum is clipped or has no AC signal')
    total = sum(left - right for left, right in zip(summed.samples, faithful.samples))
    squares = sum((left - right) ** 2 for left, right in zip(summed.samples, faithful.samples))
    ac_rms = ((squares * faithful.frames - total * total) / faithful.frames ** 2) ** 0.5
    report['sourcePaths'] = dict(faithful=str(Path(faithful_path).resolve()),
                                 stereo=str(Path(candidate_path).resolve()))
    report['routing'] = dict(rawStereo='SID A at $D400 left; SID B at $D420 right',
                             sourceVoices=dict(left=[1, 3], right=[2]),
                             sourceParts=3, sidChips=2, crossfeed=False)
    report['matrices'] = dict(faithfulDualMono=[[1], [1]], stereoMonoSum=[[0.5, 0.5]])
    report['monoSumDiagnostic'] = dict(metrics=summed_metrics,
                                       residualToFaithfulAcRms=ac_rms,
                                       normalization='none',
                                       rounding='nearest integer, ties to even',
                                       scope='Arithmetic fold-down only; separate SID analog paths need not match the mono chip PCM.')
    report['windows'] = []
    report['outputs'] = {}
    created = []
    output.mkdir(parents=True)
    try:
        for name, value in (('faithful-dual-mono.wav', reference), ('stereo-mono-sum.wav', summed)):
            path = output / name
            write_pcm(path, value, created)
            report['outputs'][name] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                          channels=value.channels, frames=value.frames, gain=1)
        for name, start, end in (('phrase', 32, 48), ('ending', 205, 225)):
            for label, value in (('faithful', reference), ('stereo', candidate)):
                clip = window(value, start, end)
                filename = f'{label}-{name}.wav'
                path = output / filename
                write_pcm(path, clip, created)
                report['outputs'][filename] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                                   channels=clip.channels, frames=clip.frames, gain=1)
            report['windows'].append(dict(name=name, seconds=[start, end],
                                           startFrame=start * sample_rate, endFrame=end * sample_rate))
        receipt = output / 'signal.json'
        with receipt.open('x') as handle:
            created.append(receipt)
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
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = prepare(args.faithful, args.candidate, args.output)
    print(f"Prepared faithful dual mono, raw stereo windows and mono-sum diagnostic; {report['unequalChannelFrames']} unequal channel frames")


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f'Rambo stereo listening preparation failed: {error}')
