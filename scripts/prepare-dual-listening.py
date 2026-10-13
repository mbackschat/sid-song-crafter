"""Prepare fixed-gain mixes from raw stereo: independent SID A left, SID B right."""

import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import sys
import wave

from audio_comparison import Pcm16, measure_pcm, read_pcm16
from verify_player import require


def _audio(rate, channels, samples):
    return Pcm16(rate, channels, len(samples) // channels, samples, '')


def _tail(audio):
    frames = min(audio.frames, max(1, round(.5 * audio.sample_rate)))
    return measure_pcm(Pcm16(audio.sample_rate, audio.channels, frames,
                             audio.samples[-frames * audio.channels:], ''))


def _write_wav(path, audio, created):
    samples = array('h', audio.samples)
    if sys.byteorder != 'little':
        samples.byteswap()
    with path.open('xb') as file:
        created.append(path)
        with wave.open(file, 'wb') as target:
            target.setparams((audio.channels, 2, audio.sample_rate, 0, 'NONE', 'not compressed'))
            target.writeframes(samples.tobytes())


def prepare_listening(input_path, output, *, start=8.0, stop=16.0):
    """Preserve equal primary gain across excerpts without normalizing either chip.

    The input contract is independent chip outputs, not a conventional stereo
    mix. Window endpoints and the half-second gap are rounded to PCM frames;
    tail measurements report health without imposing silence on other phrases.
    The separate second-chip diagnostic retains raw gain 1.0; its comparison
    contribution uses gain 0.5.
    """
    source = Path(input_path).expanduser().resolve()
    output = Path(output).expanduser().absolute()
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh output directory')
    require(type(start) in (int, float) and type(stop) in (int, float) and
            math.isfinite(start) and math.isfinite(stop), 'Listening window must be finite seconds')
    audio = read_pcm16(source)
    require(audio.channels == 2, 'Input must be stereo PCM16: independent chip A left, chip B right')
    original = measure_pcm(audio)
    require(original['clippedSamples'] == 0, 'Input contains PCM rail samples indicating clipping')
    require(0 <= start < stop <= audio.frames / audio.sample_rate, 'Listening window must fit the input')
    first, last = round(start * audio.sample_rate), round(stop * audio.sample_rate)
    require(0 <= first < last <= audio.frames, 'Listening window must contain complete PCM frames')

    mono, stereo = array('h'), array('h')
    for a, b in zip(audio.samples[::2], audio.samples[1::2]):
        values = (round(.5 * a + .5 * b), round(.5 * a + .35 * b), round(.5 * a + .65 * b))
        require(all(-32768 < value < 32767 for value in values), 'Mixed samples would overflow or clip PCM16')
        mono.append(values[0])
        stereo.extend(values[1:])
    gap = round(.5 * audio.sample_rate)
    comparison = array('h', (round(.5 * value) for value in audio.samples[2 * first:2 * last:2]))
    comparison.extend(array('h', [0]) * gap)
    comparison.extend(mono[first:last])
    outputs = {
        'mono': ('dual-mono.wav', _audio(audio.sample_rate, 1, mono)),
        'stereo': ('dual-listening-stereo.wav', _audio(audio.sample_rate, 2, stereo)),
        'comparison': ('three-then-six-voices.wav', _audio(audio.sample_rate, 1, comparison)),
        'secondChipDiagnostic': ('second-chip-only.wav', _audio(audio.sample_rate, 1, audio.samples[1::2])),
    }
    report = {
        'schemaVersion': 1,
        'inputContract': 'Raw independent SID chip outputs: A left, B right; not arbitrary stereo audio.',
        'input': {'path': str(source), 'sha256': audio.sha256, **original, 'tail': _tail(audio)},
        'matrices': {'mono': [[.5, .5]], 'listeningStereo': [[.5, .35], [.5, .65]],
                     'comparisonPrimary': [[.5, 0]], 'secondChipDiagnostic': [[0, 1.0]]},
        'normalization': 'none',
        'window': {'startSeconds': start, 'stopSeconds': stop, 'startFrame': first, 'stopFrame': last},
        'gapFrames': gap, 'gapSeconds': gap / audio.sample_rate,
        'segments': [
            {'label': 'Chip A: three voices at gain 0.5', 'startFrame': 0, 'stopFrame': last - first},
            {'label': 'Silence', 'startFrame': last - first, 'stopFrame': last - first + gap},
            {'label': 'Chips A+B: six voices at gain 0.5 each', 'startFrame': last - first + gap, 'stopFrame': 2 * (last - first) + gap},
        ],
        'outputs': {}, 'listeningVerdict': None,
    }
    output.mkdir(parents=True)
    created = []
    try:
        for label, (name, mixed) in outputs.items():
            path = output / name
            _write_wav(path, mixed, created)
            report['outputs'][label] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                        **measure_pcm(mixed), 'tail': _tail(mixed)}
            if label == 'secondChipDiagnostic':
                report['outputs'][label].update(label='Diagnostic second-chip solo at raw gain 1.0; comparison contribution uses gain 0.5.',
                                                normalization='none')
        require(hashlib.sha256(source.read_bytes()).hexdigest() == audio.sha256,
                'Input WAV changed during preparation')
        path = output / 'listening.json'
        with path.open('x', encoding='utf-8') as receipt:
            created.append(path)
            json.dump(report, receipt, indent=2, allow_nan=False)
            receipt.write('\n')
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        try:
            output.rmdir()
        except OSError:
            pass
        raise
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='Raw stereo PCM16 WAV with independent chip A left / chip B right')
    parser.add_argument('--output', type=Path, required=True, help='Fresh output directory')
    parser.add_argument('--start', type=float, default=8.0, help='Comparison window start in seconds (default: 8)')
    parser.add_argument('--stop', type=float, default=16.0, help='Comparison window stop in seconds (default: 16)')
    args = parser.parse_args()
    prepare_listening(args.input, args.output, start=args.start, stop=args.stop)
    print(f'Prepared dual-SID listening mixes: {args.output / "listening.json"}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f'Dual-SID listening preparation failed: {error}')
