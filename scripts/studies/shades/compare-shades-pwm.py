"""Reproduce the pinned Shades one-byte PWM intervention and its bounded proof."""

import argparse
from array import array
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import sys
import wave


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))

from audio_comparison import Pcm16, measure_pcm, read_pcm16
from verify_player import require


TRACE_PATH = ROOT / 'scripts/trace-shades-vice.py'
spec = importlib.util.spec_from_file_location('shades_cia_trace', TRACE_PATH)
cia = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cia)
SOURCE_SHA = cia.SOURCE_PINS['Shades_filter_corrected.sid']
PATCH_ADDRESS = 0x562f
PLAY_CALLS = 1280
PULSE_ADDRESSES = {0xd402, 0xd403}
RENDER_SECONDS = 16
WINDOW_SECONDS = (5, 12)
GAP_SECONDS = 0.5


def digest(data):
    return hashlib.sha256(data).hexdigest()


def patch_source(data):
    """Copy the pinned corrected source and replace its opening voice-1 PWM step."""
    require(digest(data) == SOURCE_SHA, 'Intervention requires the pinned corrected Shades source')
    profile = cia.source_profile(data)
    offset = int.from_bytes(data[6:8], 'big') + (2 if int.from_bytes(data[8:10], 'big') == 0 else 0)
    offset += PATCH_ADDRESS - profile['loadAddress']
    require(data[offset] == 0x10, 'Opening PWM step differs from the inspected $10 value')
    patched = bytearray(data)
    patched[offset] = 0
    return bytes(patched), dict(ramAddress=PATCH_ADDRESS, fileOffset=offset, **{'from': 16, 'to': 0},
                                purpose='Freeze voice 1 PWM movement in combined block $5600, retaining its reset width')


def verify_comparison(original_report, original_writes, frozen_report, frozen_writes):
    fields = ('playCalls', 'initCycles', 'playCycles', 'portWrites', 'executedPcs', 'ioReads')
    require(all(original_report[field] == frozen_report[field] for field in fields),
            'PWM intervention changed source call execution, cycle costs or hardware dependencies')
    require(len(original_writes) == len(frozen_writes), 'PWM intervention changed ordered source write count')
    changed = []
    for original, frozen in zip(original_writes, frozen_writes):
        require({key: value for key, value in original.items() if key != 'value'} ==
                {key: value for key, value in frozen.items() if key != 'value'},
                'PWM intervention changed ordered write context, source PC or instruction timing')
        if original['value'] != frozen['value']:
            require(original['address'] in PULSE_ADDRESSES, 'PWM intervention changed a non-pulse register value')
            changed.append(dict(original=original, frozen=frozen))
    require(changed, 'Intervention did not change pulse register values in the bounded span')
    return dict(playCalls=original_report['playCalls'], sourceWriteCount=len(original_writes),
                ciaWriteCount=sum(row['address'] in (0xdc04, 0xdc05) for row in original_writes),
                changedWrites=len(changed), changedAddresses=sorted({row['original']['address'] for row in changed}),
                firstChangedCall=changed[0]['original']['tick'], lastChangedCall=changed[-1]['original']['tick'],
                orderedContextIdentical=True, nonPulseWritesAndTimingIdentical=True, ciaWritesIdentical=True,
                callCyclesIdentical=True, firstChangedWrites=changed[:12])


def compare_source(data):
    """Return patched bytes, the proof receipt and both 1,280-call ordered oracles."""
    patched, change = patch_source(data)
    original_report, original_writes = cia.shades_oracle(data, PLAY_CALLS)
    frozen_report, frozen_writes = cia.bounded_oracle(patched, PLAY_CALLS)
    verification = verify_comparison(original_report, original_writes, frozen_report, frozen_writes)
    receipt = dict(schemaVersion=1, classification='Single-parameter reference-program intervention',
                   sourceSha256=digest(data), patchedSha256=digest(patched), change=change,
                   oracleToolSha256=digest(TRACE_PATH.read_bytes()),
                   cpuTimingToolSha256=digest((ROOT / 'scripts/verify_player.py').read_bytes()),
                   verification=verification,
                   sourceCallCosts=dict(initCycles=original_report['initCycles'],
                                        minimumPlayCycles=min(original_report['playCycles']),
                                        maximumPlayCycles=max(original_report['playCycles'])),
                   listeningReview=None,
                   limitations='Callable source execution establishes ordered-value isolation, source PCs and instruction costs. It does not emulate CIA counters or IRQ timing, reconstruct an independent player, establish whole-song isolation or supply a listening verdict.')
    return patched, receipt, original_writes, frozen_writes


def prepare_listening(a_path, b_path, output):
    """Join seconds 5–12 at unity gain with a half-second gap, preserving levels."""
    require(not output.exists() and not output.is_symlink(), 'Listening output already exists')
    audio = [read_pcm16(path) for path in (a_path, b_path)]
    require((audio[0].sample_rate, audio[0].channels) == (audio[1].sample_rate, audio[1].channels),
            'Listening inputs require the same sample rate and channel count')
    rate, channels = audio[0].sample_rate, audio[0].channels
    first, last = (round(second * rate) for second in WINDOW_SECONDS)
    require(all(value.frames >= last for value in audio), 'Listening inputs do not contain the complete 5–12 second window')
    windows = [Pcm16(rate, channels, last - first, value.samples[first * channels:last * channels], '') for value in audio]
    metrics = [measure_pcm(value) for value in windows]
    require(all(row['clippedSamples'] == 0 and row['acRms'] > 0 for row in metrics),
            'Listening windows require unclipped AC audio')
    gap = round(GAP_SECONDS * rate)
    samples = windows[0].samples + array('h', [0]) * (gap * channels) + windows[1].samples
    if sys.byteorder != 'little':
        samples.byteswap()
    with output.open('xb') as file:
        with wave.open(file, 'wb') as wav:
            wav.setparams((channels, 2, rate, 0, 'NONE', 'not compressed'))
            wav.writeframes(samples.tobytes())
    return dict(windowSeconds=list(WINDOW_SECONDS), gain=1, normalization=False, gapSeconds=GAP_SECONDS,
                order=['Corrected reference with moving PWM', 'Same reference with voice 1 PWM step zeroed'],
                inputs=[dict(path=str(path), sha256=value.sha256, window=measure)
                        for path, value, measure in zip((a_path, b_path), audio, metrics)],
                output=str(output), sha256=digest(output.read_bytes()), listeningReview=None)


def verify_baseline_prefix(reference_path, current_path):
    """Check that the short initialization render retains the longer render's PCM."""
    reference, current = (read_pcm16(path) for path in (reference_path, current_path))
    require((reference.sample_rate, reference.channels) == (current.sample_rate, current.channels),
            'Baseline prefix formats differ')
    frames = RENDER_SECONDS * current.sample_rate
    require(current.frames == frames and reference.frames >= frames, 'Baseline prefix requires a complete 16-second render')
    require(reference.samples[:frames * current.channels] == current.samples, 'Baseline PCM prefix differs')
    samples = array('h', current.samples)
    if sys.byteorder != 'little':
        samples.byteswap()
    return dict(referencePath=str(reference_path), referenceSha256=reference.sha256,
                shortenedPath=str(current_path), shortenedSha256=current.sha256,
                frames=frames, pcmSha256=digest(samples.tobytes()), identicalPcmPrefix=True)


def render_comparison(output, renderer):
    require(renderer.is_file(), 'Documented SID renderer does not exist')
    commands = []
    for sid_name, wav_name in (('reference.sid', 'reference.wav'), ('zero-pwm-step.sid', 'zero-pwm-step.wav')):
        command = [str(renderer), str(output / sid_name), str(output / wav_name), str(RENDER_SECONDS)]
        rendered = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
        result = dict(command=command, executableSha256=digest(renderer.read_bytes()), returnCode=rendered.returncode,
                      stdout=rendered.stdout.strip(), stderr=rendered.stderr.strip())
        with (output / f'{wav_name}.render.json').open('x') as file:
            file.write(json.dumps(result, indent=2) + '\n')
        if rendered.returncode:
            raise subprocess.CalledProcessError(rendered.returncode, command, rendered.stdout, rendered.stderr)
        audio = read_pcm16(output / wav_name)
        require((audio.sample_rate, audio.channels, audio.frames) == (44100, 1, RENDER_SECONDS * 44100),
                'Renderer output must be 16 seconds of mono 44.1 kHz PCM16')
        commands.append(result)
    return dict(renderer=commands,
                comparison=prepare_listening(output / 'reference.wav', output / 'zero-pwm-step.wav', output / 'original-then-static-pulse.wav'))


def run_comparison(source, output, *, render=False, renderer=ROOT / '.local/bin/render-sid', baseline_reference=None):
    source, output, renderer = (Path(path).resolve() for path in (source, output, renderer))
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh comparison output directory')
    if baseline_reference is not None:
        baseline_reference = Path(baseline_reference).resolve()
        require(render and baseline_reference.is_file(), 'Baseline comparison requires rendering and an existing reference WAV')
    data = source.read_bytes()
    patched, receipt, original_writes, frozen_writes = compare_source(data)
    if render:
        require(renderer.is_file(), 'Documented SID renderer does not exist')
    output.mkdir(parents=True)
    for name, content in (('reference.sid', data), ('zero-pwm-step.sid', patched)):
        with (output / name).open('xb') as file:
            file.write(content)
    for name, value in (('reference.writes.json', original_writes), ('zero-pwm-step.writes.json', frozen_writes)):
        with (output / name).open('x') as file:
            file.write(json.dumps(value, indent=2) + '\n')
    commands = [[str(renderer), str(output / sid), str(output / wav), str(RENDER_SECONDS)]
                for sid, wav in (('reference.sid', 'reference.wav'), ('zero-pwm-step.sid', 'zero-pwm-step.wav'))]
    recipe = '\n'.join(shlex.join(command) for command in commands)
    listening = f'''# Shades moving-pulse comparison

These are ignored reference-program diagnostics. The one-byte copy is not an independent player. Render both from initialization with the existing default-subtune PAL/6581 renderer:

```sh
{recipe}
```

The tool's `--render` option also joins seconds 5–12, corrected reference first and static pulse second, with a 0.5-second gap. Both excerpts retain unity gain and their original level difference; no individual normalization is applied. Use a fresh output directory for a new `--render` run. The reusable `prepare_listening(a_path, b_path, output_path)` function can assemble already rendered copies.

Compare vibrancy and level over the pulse phrase. Retain any listening verdict with these exact inputs and settings. The callable 1,280-call proof establishes register-value isolation; elapsed-time CIA evidence and musical judgments remain separate.
'''
    with (output / 'listening.md').open('x') as file:
        file.write(listening)
    receipt.update(sourcePath=str(source), output=str(output), renderCommands=commands,
                   listeningRecipe=dict(renderSeconds=RENDER_SECONDS, windowSeconds=list(WINDOW_SECONDS), gain=1,
                                        normalization=False, gapSeconds=GAP_SECONDS),
                   audio=render_comparison(output, renderer) if render else None)
    if baseline_reference is not None:
        receipt['audio']['baselinePrefix'] = verify_baseline_prefix(baseline_reference, output / 'reference.wav')
    with (output / 'comparison.json').open('x') as file:
        file.write(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sid', type=Path)
    parser.add_argument('--output', type=Path, required=True, help='fresh ignored output directory')
    parser.add_argument('--render', action='store_true', help='render both 16-second copies and join the unity-gain A/B window')
    parser.add_argument('--renderer', type=Path, default=ROOT / '.local/bin/render-sid')
    parser.add_argument('--baseline-reference', type=Path, help='with --render, prove the baseline16s PCM matches this longer initialization render')
    args = parser.parse_args()
    result = run_comparison(args.sid, args.output, render=args.render, renderer=args.renderer, baseline_reference=args.baseline_reference)
    print(json.dumps(dict(receipt=str(Path(result['output']) / 'comparison.json'),
                          patchedSha256=result['patchedSha256'], playCalls=result['verification']['playCalls'],
                          changedWrites=result['verification']['changedWrites'],
                          changedAddresses=result['verification']['changedAddresses'],
                          audio=result['audio']['comparison']['output'] if result['audio'] else None), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error))
