"""Check the held-third-tone trial against the prior raw two-SID ensemble."""

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
from sid_clock import clock_spec
from verify_player import require


def window(audio, start, end):
    first, last = round(start * audio.sample_rate), round(end * audio.sample_rate)
    require(0 <= first < last <= audio.frames, 'Window exceeds the initialized render')
    return Pcm16(audio.sample_rate, audio.channels, last - first,
                 audio.samples[first * audio.channels:last * audio.channels], '')


def residual_rms(a, b):
    require((a.channels, a.sample_rate, a.frames) == (b.channels, b.sample_rate, b.frames),
            'Residual inputs must have matching formats and durations')
    count = len(a.samples)
    total = sum(left - right for left, right in zip(a.samples, b.samples))
    squares = sum((left - right) ** 2 for left, right in zip(a.samples, b.samples))
    return ((squares * count - total * total) / count ** 2) ** .5


def pcm_comparison(a, b):
    first = next((index for index, pair in enumerate(zip(a.samples, b.samples)) if pair[0] != pair[1]), None)
    return dict(identical=first is None, firstDifferenceFrame=first // a.channels if first is not None else None,
                unequalSamples=sum(left != right for left, right in zip(a.samples, b.samples)),
                peakAbsoluteDifference=max(abs(left - right) for left, right in zip(a.samples, b.samples)),
                residualAcRmsPerChannel=[residual_rms(Pcm16(a.sample_rate, 1, a.frames, a.samples[channel::a.channels], ''),
                                                    Pcm16(b.sample_rate, 1, b.frames, b.samples[channel::b.channels], ''))
                                        for channel in range(a.channels)])


def fold_down(audio):
    return Pcm16(audio.sample_rate, 1, audio.frames,
                 array('h', (round((left + right) / 2) for left, right in zip(audio.samples[::2], audio.samples[1::2]))), '')


def check_audio(previous, expanded, support, omitted, *, timing, sample_rate=44100):
    claims = ('passed', 'primaryPayloadMatchesReference', 'primaryOrderedStoresIdentical',
              'primaryRelativeCpuTimingIdentical', 'primaryViceOffsetsIdentical')
    require(all(timing.get(claim) is True for claim in claims), 'A complete passing source/timing proof is required')
    inputs, tails = [], []
    for label, value in (('previous', previous), ('expanded', expanded)):
        require((value.channels, value.sample_rate, value.frames) == (2, sample_rate, 225 * sample_rate),
                f'{label} must be the complete 225-second raw stereo render')
        metrics = measure_pcm(value)
        require(metrics['clippedSamples'] == 0, f'{label} contains PCM rail samples')
        require(all(row['acRms'] > 0 for row in metrics['perChannel']), f'{label} has an empty chip channel')
        inputs.append(dict(label=label, sha256=value.sha256, **metrics))
        tail = measure_pcm(window(value, 224, 225))
        require(all(row['acRms'] <= 1 for row in tail['perChannel']), f'{label} has an unsettled tail')
        tails.append(dict(label=label, seconds=[224, 225], metrics=tail))
    primary = [Pcm16(value.sample_rate, 1, value.frames, value.samples[::2], '') for value in (previous, expanded)]
    primary_comparison = pcm_comparison(*primary)
    prefix_call = timing['firstSecondaryDifferenceCall']
    require(type(prefix_call) is int and prefix_call > 0, 'Timing proof lacks its first secondary difference')
    prefix_seconds = prefix_call / clock_spec('pal').ticks_per_second
    prefix = [window(value, 0, prefix_seconds) for value in primary]
    require(prefix[0].samples == prefix[1].samples, 'The primary PCM prefix changed before the intervention')
    ending_comparison = pcm_comparison(window(previous, 205, 225), window(expanded, 205, 225))
    ending_comparison['seconds'] = [205, 225]
    closing = measure_pcm(window(expanded, 205, 211))
    require(closing['perChannel'][0]['acRms'] >= 32, 'The faithful primary lost its closing body')
    for label, value in (('support', support), ('omitted', omitted)):
        require((value.channels, value.sample_rate, value.frames) == (1, sample_rate, 104 * sample_rate),
                f'{label} must cover exactly 104 initialized mono seconds')
        require(measure_pcm(value)['clippedSamples'] == 0, f'{label} contains PCM rail samples')
    baseline, diagnostic = window(support, 88, 104), window(omitted, 88, 104)
    baseline_level = measure_pcm(baseline)['acRms']
    contribution = residual_rms(baseline, diagnostic)
    require(baseline_level > 0 and contribution > 0, 'The expanded third voice has no rendered contribution')
    phrase = window(expanded, 88, 104)
    previous_phrase = window(previous, 88, 104)
    change = residual_rms(Pcm16(sample_rate, 1, phrase.frames, phrase.samples[1::2], ''),
                          Pcm16(sample_rate, 1, previous_phrase.frames, previous_phrase.samples[1::2], ''))
    require(change > 0, 'The changed chord calendar has no main-phrase PCM effect')
    mono = fold_down(expanded)
    mono_metrics = measure_pcm(mono)
    mono_tail = measure_pcm(window(mono, 224, 225))
    mono_closing = measure_pcm(window(mono, 205, 211))
    require(mono_metrics['clippedSamples'] == 0 and mono_metrics['acRms'] > 0, 'Mono fold-down is clipped or empty')
    require(mono_tail['acRms'] <= 1 and mono_closing['acRms'] >= 32, 'Mono fold-down lost the complete natural ending')
    return dict(schemaVersion=1, passed=True, inputs=inputs,
                routing='Raw SID A left and SID B right in both versions; no centered remix or chip normalization.',
                primaryPcmComparison=primary_comparison, endingPcmComparison=ending_comparison,
                primaryPrefixIdentity=dict(throughSourceCallExclusive=prefix_call, seconds=[0, prefix_seconds],
                                           matchedFrames=prefix[0].frames, exact=True),
                sourceTimingClaims={claim: timing[claim] for claim in claims},
                timingLimits=timing.get('claims', {}),
                closingBody=dict(seconds=[205, 211], metrics=closing), finalTail=tails,
                monoFoldDown=dict(matrix=[[.5, .5]], normalization='none', metrics=mono_metrics,
                                  closingBody=mono_closing, finalTail=mono_tail, purpose='Internal compatibility diagnostic'),
                mainPhrase=dict(seconds=[88, 104], changedSupportAcRms=change,
                                primaryPcmComparison=pcm_comparison(window(primary[0], 88, 104),
                                                                   window(primary[1], 88, 104))),
                thirdVoiceContribution=dict(seconds=[88, 104], residualAcRms=contribution,
                                            residualToSupportAcRmsRatio=contribution / baseline_level,
                                            supportSha256=support.sha256, omissionSha256=omitted.sha256,
                                            scope='B3 control-mask omission residual; not an exact stem or a musical audibility verdict.'),
                listeningVerdict=None)


def write_pcm(path, audio, created):
    values = array('h', audio.samples)
    if sys.byteorder != 'little':
        values.byteswap()
    with path.open('xb') as handle:
        created.append(path)
        with wave.open(handle, 'wb') as target:
            target.setparams((audio.channels, 2, audio.sample_rate, 0, 'NONE', 'not compressed'))
            target.writeframes(values.tobytes())


def prepare(previous_path, expanded_path, support_path, omitted_path, output, *, timing_path, sample_rate=44100):
    output = Path(output)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh preparation directory')
    paths = (previous_path, expanded_path, support_path, omitted_path)
    previous, expanded, support, omitted = [read_pcm16(path) for path in paths]
    timing = json.loads(Path(timing_path).read_text())
    report = check_audio(previous, expanded, support, omitted, timing=timing, sample_rate=sample_rate)
    report['timingProof'] = dict(path=str(Path(timing_path).resolve()), sha256=hashlib.sha256(Path(timing_path).read_bytes()).hexdigest())
    report['sourcePaths'] = [str(Path(path).resolve()) for path in paths]
    report['outputs'] = {}
    created = []
    output.mkdir(parents=True)
    try:
        full = output / 'previous-raw-full.wav'
        with full.open('xb') as target:
            created.append(full)
            target.write(Path(previous_path).read_bytes())
        require(hashlib.sha256(full.read_bytes()).hexdigest() == previous.sha256, 'Full reference copy changed')
        mono_path = output / 'expanded-mono-diagnostic.wav'
        write_pcm(mono_path, fold_down(expanded), created)
        report['monoFoldDown']['sha256'] = hashlib.sha256(mono_path.read_bytes()).hexdigest()
        for label, audio in (('previous', previous), ('expanded', expanded)):
            filename = f'{label}-raw-phrase.wav'
            target = output / filename
            write_pcm(target, window(audio, 88, 104), created)
            report['outputs'][filename] = dict(sha256=hashlib.sha256(target.read_bytes()).hexdigest(), gain=1)
        receipt = output / 'audio.json'
        with receipt.open('x') as target:
            created.append(receipt)
            json.dump(report, target, indent=2, allow_nan=False)
            target.write('\n')
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        output.rmdir()
        raise
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('previous', 'expanded', 'support', 'omitted', 'timing', 'output'):
        parser.add_argument(f'--{name}', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.previous, args.expanded, args.support, args.omitted, args.output, timing_path=args.timing)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f'Rambo chord-expansion listening preparation failed: {error}')
