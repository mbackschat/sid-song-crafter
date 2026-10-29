#!/usr/bin/env python3
"""Measure an instrument's level and brightness with probe-level-v1.

The probe is defined in docs/proposals/instrument-library.md: one note at the
role pitch, gated for 100 PAL updates with the other voices silent, master
volume 15, MOS8580, converted, exported and rendered by the song pipeline.
Every library record is probed the same way, so the values compare between
candidates for one role.
"""

import argparse
import cmath
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audio_comparison import read_pcm16  # noqa: E402
from sid_clock import clock_spec  # noqa: E402

PROBE_ID = 'probe-level-v1'
START_UPDATE, GATE_UPDATES, TAIL_UPDATES = 10, 100, 100
ROLE_PITCH = {'bass': 45, 'lead': 69}   # A2, A4; every other role A3
OTHER_PITCH = 57
# Windows in seconds from the onset. The sustain window ends before the gate closes at 2.0 s.
ONSET, SUSTAIN, ONSET_SPECTRUM, BODY_SPECTRUM = (0.0, 0.25), (1.0, 1.9), (0.0, 0.06), (0.05, 0.55)
FFT_SIZE = 1 << 15


def role_pitch(role):
    return ROLE_PITCH.get(role, OTHER_PITCH)


def inputs(instrument, role, update_hz):
    """Score and sidwizard-arrangement-v1 recipe for one probe note (one beat per update)."""
    score = {
        'title': 'Level probe', 'composer': 'Probe', 'quarterBpm': 60 * update_hz,
        'totalBeats': START_UPDATE + GATE_UPDATES, 'tailTicks': TAIL_UPDATES, 'volume': 15,
        'voices': [{'name': 'probe', 'events': [{'startBeat': START_UPDATE, 'durationBeats': GATE_UPDATES, 'midi': role_pitch(role)}]},
                   {'name': 'idle-a', 'events': []}, {'name': 'idle-b', 'events': []}]}
    recipe = {
        'format': 'sidwizard-arrangement-v1', 'score': 'score.json', 'title': 'Level probe', 'author': 'Probe', 'released': '2026',
        'timingPolicy': 'retain-full-pitch', 'instruments': {'probe': instrument},
        'sections': [{'name': 'probe', 'startBeat': 0, 'endBeat': START_UPDATE + GATE_UPDATES,
                      'voices': {'probe': 'probe', 'idle-a': 'probe', 'idle-b': 'probe'}}]}
    return score, recipe


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / f'scripts/{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render(instrument, role, output, renderer=ROOT / '.local/bin/render-sid'):
    """Render the probe note into a fresh directory and return the WAV path."""
    output = Path(output)
    output.mkdir(parents=True)
    timing = clock_spec('pal')
    score, recipe = inputs(instrument, role, timing.ticks_per_second)
    (output / 'score.json').write_text(json.dumps(score, indent=1) + '\n')
    (output / 'recipe.json').write_text(json.dumps(recipe, indent=1) + '\n')
    manifest = load_script('arrange-sidwizard').arrange(output / 'recipe.json', output / 'conversion')
    exported = load_script('export-sidwizard').export_module(manifest['nativePath'], output / 'export', title='Level probe', author='Probe', sid_model='MOS8580', clock='pal')
    seconds = (START_UPDATE + GATE_UPDATES + TAIL_UPDATES + 1) / timing.ticks_per_second + 0.5
    wav = output / 'probe.wav'
    subprocess.run([str(renderer), exported['sid'], str(wav), f'{seconds:.3f}', '--clock', 'pal'], check=True, timeout=120, capture_output=True)
    return wav


def fft(values):
    """Iterative radix-2 transform; the project runtime has no numpy."""
    size = len(values)
    if size & (size - 1):
        raise ValueError('FFT size must be a power of two')
    data = list(values)
    j = 0
    for i in range(1, size):
        bit = size >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            data[i], data[j] = data[j], data[i]
    span = 2
    while span <= size:
        step = cmath.exp(-2j * math.pi / span)
        for start in range(0, size, span):
            twiddle = 1
            for k in range(span // 2):
                even, odd = data[start + k], data[start + k + span // 2] * twiddle
                data[start + k], data[start + k + span // 2] = even + odd, even - odd
                twiddle *= step
        span <<= 1
    return data


def window(samples, rate, onset, bounds):
    return samples[int((onset + bounds[0]) * rate):int((onset + bounds[1]) * rate)]


def ac_rms_db(values):
    mean = sum(values) / len(values)
    power = sum((value - mean) ** 2 for value in values) / len(values)
    return round(10 * math.log10(power), 1) if power > 1e-12 else None


def centroid_ratio(values, rate, f0):
    # Remove the mean (renderer DC offset, envelope drift) and ignore bins under half the fundamental,
    # which would otherwise pull the centroid below the note.
    mean = sum(values) / len(values)
    last = len(values) - 1
    windowed = [complex((value - mean) * (0.5 - 0.5 * math.cos(2 * math.pi * n / last))) for n, value in enumerate(values)]
    spectrum = fft(windowed + [0j] * (FFT_SIZE - len(windowed)))
    weighted = total = 0.0
    for k in range(FFT_SIZE // 2 + 1):
        frequency = k * rate / FFT_SIZE
        if frequency >= f0 / 2:
            power = abs(spectrum[k]) ** 2
            weighted += power * frequency
            total += power
    return round(weighted / total / f0, 1)


def measure(samples, rate, midi, update_hz):
    """Level (AC RMS dBFS) and brightness of a mono full-scale-normalised probe render."""
    onset = START_UPDATE / update_hz
    f0 = 440 * 2 ** ((midi - 69) / 12)
    return {
        'onsetDb': ac_rms_db(window(samples, rate, onset, ONSET)),
        'sustainDb': ac_rms_db(window(samples, rate, onset, SUSTAIN)),
        'onsetCentroidRatio': centroid_ratio(window(samples, rate, onset, ONSET_SPECTRUM), rate, f0),
        'bodyCentroidRatio': centroid_ratio(window(samples, rate, onset, BODY_SPECTRUM), rate, f0),
    }


def read_mono(path):
    audio = read_pcm16(path)
    channels = audio.channels
    return [sum(audio.samples[n * channels:(n + 1) * channels]) / channels / 32768 for n in range(audio.frames)], audio.sample_rate


def claims(measured, midi):
    where = f'{PROBE_ID}: one note at MIDI {midi} gated {GATE_UPDATES} PAL updates, MOS8580, master volume 15, song pipeline render'
    return {
        'level': {'value': {'onsetDb': measured['onsetDb'], 'sustainDb': measured['sustainDb']}, 'basis': 'measured',
                  'detail': f'{where}; AC RMS dBFS over the first 250 ms and over 1.0-1.9 s of the note'},
        'brightness': {'value': {'onset': measured['onsetCentroidRatio'], 'body': measured['bodyCentroidRatio']}, 'basis': 'measured',
                       'detail': f'{where}; spectral centroid divided by the fundamental over 0-60 ms and 50-550 ms (pure triangle about 1.0)'},
    }


def probe_record(path, output):
    record = json.loads(Path(path).read_text())
    program = record['program']
    value = json.loads((ROOT / program['file']).read_text())
    for key in program['record'].split('.'):
        value = value[key]
    role = record['fit']['roles'][0]
    wav = render(value, role, Path(output) / f'{record["id"]}@{record["version"]}')
    samples, rate = read_mono(wav)
    return record, claims(measure(samples, rate, role_pitch(role), clock_spec('pal').ticks_per_second), role_pitch(role))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('records', nargs='+', type=Path, help='library records whose SID-Wizard program to probe')
    parser.add_argument('--output', type=Path, required=True, help='fresh directory for probe renders')
    parser.add_argument('--write', action='store_true', help='store the measured claims in each record; the program itself never changes')
    args = parser.parse_args()
    if args.output.exists():
        sys.exit('Probe output already exists; choose a fresh directory to preserve evidence')
    for path in args.records:
        record, measured = probe_record(path, args.output)
        print(json.dumps({f'{record["id"]}@{record["version"]}': {key: value['value'] for key, value in measured.items()}}))
        if args.write:
            record['character'].update(measured)
            path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
