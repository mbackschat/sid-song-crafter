"""Prepare the fixed Rambo chip-mapping diagnostic without changing synthesis."""

import argparse
from array import array
import hashlib, json, math, sys, wave
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from audio_comparison import Pcm16, read_pcm16
from verify_player import require


def width(audio):
    left, right = audio.samples[::2], audio.samples[1::2]
    n = audio.frames
    sl, sr = sum(left), sum(right)
    vl = sum(value * value for value in left) * n - sl * sl
    vr = sum(value * value for value in right) * n - sr * sr
    covariance = sum(a * b for a, b in zip(left, right)) * n - sl * sr
    mid = vl + vr + 2 * covariance
    side = vl + vr - 2 * covariance
    return dict(midAcRms=math.sqrt(mid / (4 * n * n)), sideAcRms=math.sqrt(side / (4 * n * n)), sideToMidAcRmsRatio=math.sqrt(side / mid) if mid else None, leftRightCorrelation=covariance / math.sqrt(vl * vr) if vl and vr else None, definitions='DC removed per channel; M=(L+R)/2; S=(L-R)/2; normalized zero-lag L/R covariance')


def prepare(centered, raw, output):
    sources = [('current', centered, 'current-centered'), ('raw', raw, 'raw-hard-split')]
    report = dict(schemaVersion=1, status='internal diagnostic; no listening verdict', sourceSidSha256='c909f2d02c82e06291af8b33fb9618d9e576ced319c25a89fca17e8f48adb807', target=dict(clock='PAL', sidModels=['MOS6581', 'MOS6581'], sidBases=[54272, 54304]), phraseSeconds=[88, 104], mappings=dict(current=[[.5, .35], [.5, .65]], raw=[[1, 0], [0, 1]]), sources=[], scope='Same six-voice render, changed chip-output mapping only. Raw hard split places all faithful voices left and all added support right; it cannot pan individual voices within either chip. Width statistics do not establish stereo perception or musical usefulness.')
    for label, path, name in sources:
        audio = read_pcm16(path)
        require((audio.sample_rate, audio.channels, audio.frames) == (44100, 2, 9922500), 'Expected full initialized 225-second PCM16 stereo render')
        first, last = 88 * audio.sample_rate, 104 * audio.sample_rate
        clip = Pcm16(audio.sample_rate, 2, last - first, audio.samples[first * 2:last * 2], '')
        full = output / (name + '-full.wav')
        with full.open('xb') as target:
            target.write(path.read_bytes())
        values = array('h', clip.samples)
        if sys.byteorder != 'little':
            values.byteswap()
        excerpt = output / (name + '-phrase.wav')
        with excerpt.open('xb') as handle:
            with wave.open(handle, 'wb') as target:
                target.setparams((2, 2, audio.sample_rate, 0, 'NONE', 'not compressed'))
                target.writeframes(values.tobytes())
        require(hashlib.sha256(full.read_bytes()).hexdigest() == audio.sha256, 'Full copy changed source bytes')
        report['sources'].append(dict(label=label, path=str(path.resolve()), sha256=audio.sha256, fullCopySha256=audio.sha256, phraseSha256=hashlib.sha256(excerpt.read_bytes()).hexdigest(), originalGain=1, full=width(audio), phrase=width(clip)))
    with (output / 'width.json').open('x') as target:
        json.dump(report, target, indent=2, allow_nan=False)
        target.write('\n')
    with (output / 'audition.json').open('x') as target:
        json.dump(dict(mappingComparison='current-then-hard-split-phrase.ab.wav', fullCurrent='current-centered-full.wav', fullRaw='raw-hard-split-full.wav'), target, indent=2)
        target.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('centered', type=Path, help='Pinned current centered six-voice WAV')
    parser.add_argument('raw', type=Path, help='Pinned raw chip A left / chip B right WAV')
    parser.add_argument('output', type=Path, help='Existing output directory; output files must be new')
    args = parser.parse_args()
    prepare(args.centered, args.raw, args.output)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f'Rambo width diagnostic failed: {error}')
