"""Assemble the Shades update-rate listening files with one shared gain for both Shades versions.

compare-audio.py normalizes each input independently or copies at unity gain, so it cannot present
two Shades renders at the same level while keeping the plain reference at the level accepted for
the earlier reference/Shades pair. This assembler applies gain 1 to the reference and one common
attenuation to the exact and frame-rate renders, derived from the full-file AC RMS of the reference
and the exact render (the attenuation-only rule of compare-audio.py prepare). The frame-rate render
is never level-matched on its own, so any loudness difference caused by the variant stays audible.
"""

import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import sys
import wave

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))

from audio_comparison import measure_pcm, read_pcm16  # noqa: E402
from verify_player import require  # noqa: E402


ACCEPTED_AUDIO_RECIPE = ROOT / 'docs/research/composition/shades-elise-audio.json'
PHRASE = (0.0, 13.0)
ENDING = (8.0, 13.0)
GAP_SECONDS = 0.5


def scaled(samples, gain):
    return array('h', (round(value * gain) for value in samples))


def write_wav(path, rate, channels, chunks):
    with path.open('xb') as file:
        with wave.open(file, 'wb') as output:
            output.setparams((channels, 2, rate, 0, 'NONE', 'not compressed'))
            for chunk in chunks:
                data = array('h', chunk)
                if sys.byteorder == 'big':
                    data.byteswap()
                output.writeframesraw(data.tobytes())


def assemble(name, clips, audio, window, gains, output, gap_seconds):
    """Concatenate windows of the named clips in order, separated by silence; return the receipt."""
    rate, channels = audio[clips[0]].sample_rate, audio[clips[0]].channels
    first, last = (round(seconds * rate) for seconds in window)
    require(0 <= first < last and all(last <= audio[clip].frames for clip in clips), f'{name}: window outside the renders')
    gap = array('h', [0]) * (round(gap_seconds * rate) * channels)
    chunks, segments, cursor = [], [], 0
    for index, clip in enumerate(clips):
        if index:
            chunks.append(gap)
            segments.append(dict(label='silence', startSeconds=cursor / rate, endSeconds=(cursor + len(gap) // channels) / rate))
            cursor += len(gap) // channels
        part = scaled(audio[clip].samples[first * channels:last * channels], gains[clip])
        require(max(map(abs, part), default=0) <= 32767, f'{name}: gain would clip {clip}')
        chunks.append(part)
        frames = len(part) // channels
        segments.append(dict(label=clip, startSeconds=cursor / rate, endSeconds=(cursor + frames) / rate,
                             gain=gains[clip], gainDb=20 * math.log10(gains[clip])))
        cursor += frames
    path = output / name
    write_wav(path, rate, channels, chunks)
    receipt = dict(file=name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), durationSeconds=cursor / rate,
                   sourceWindowSeconds=list(window), order=list(clips), segments=segments)
    stem = name[:-len('.ab.wav')] if name.endswith('.ab.wav') else name[:-len('.abc.wav')]
    with (output / (stem + '.comparison.json')).open('x') as handle:
        json.dump(receipt, handle, indent=2, allow_nan=False)
        handle.write('\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--exact', type=Path, required=True)
    parser.add_argument('--frame', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='Fresh directory')
    args = parser.parse_args()
    require(not args.output.exists(), 'Choose a fresh output directory')
    paths = dict(reference=args.reference, exact=args.exact, frame=args.frame)
    audio = {label: read_pcm16(path) for label, path in paths.items()}
    require(len({(value.sample_rate, value.channels, value.frames) for value in audio.values()}) == 1,
            'The three renders must have the same rate, channels and length')
    metrics = {label: measure_pcm(value) for label, value in audio.items()}
    for label, measured in metrics.items():
        require(measured['clippedSamples'] == 0 and measured['acRms'] > 0, f'{label} render is clipped or silent')
    shared = metrics['reference']['acRms'] / metrics['exact']['acRms']
    require(shared <= 1, 'The exact render is quieter than the reference; choose an explicit gain policy')
    gains = dict(reference=1.0, exact=shared, frame=shared)
    accepted = json.loads(ACCEPTED_AUDIO_RECIPE.read_text())['comparison']['gainDb'][1]
    args.output.mkdir(parents=True)
    receipts = [
        assemble('phrase-exact-then-frame.ab.wav', ('exact', 'frame'), audio, PHRASE, gains, args.output, GAP_SECONDS),
        assemble('ending-exact-then-frame.ab.wav', ('exact', 'frame'), audio, ENDING, gains, args.output, GAP_SECONDS),
        assemble('phrase-reference-exact-frame.abc.wav', ('reference', 'exact', 'frame'), audio, PHRASE, gains, args.output, GAP_SECONDS),
    ]
    summary = dict(
        schemaVersion=1, kind='engine-audibility-shades-listening',
        gainPolicy='Reference at unity gain; exact and frame-rate renders share one attenuation so the reference/exact level match accepted on 2026-10-13 is kept and the variant is not normalized on its own.',
        sharedShadesGainDb=20 * math.log10(shared), acceptedReferenceExactGainDb=accepted,
        matchesAcceptedGain=abs(20 * math.log10(shared) - accepted) < 1e-6,
        sources={label: dict(path=str(paths[label].resolve()), sha256=audio[label].sha256, acRms=metrics[label]['acRms'],
                             peak=metrics[label]['peak']) for label in paths},
        comparisons=receipts)
    with (args.output / 'listening-summary.json').open('x') as handle:
        json.dump(summary, handle, indent=2, allow_nan=False)
        handle.write('\n')
    for receipt in receipts:
        print(f"{receipt['file']}: {receipt['durationSeconds']:.3f} s, order {' -> '.join(receipt['order'])}")
    print(f"Shared Shades gain {summary['sharedShadesGainDb']:.3f} dB (accepted pair {accepted:.3f} dB)")


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f'Listening assembly failed: {error}')
