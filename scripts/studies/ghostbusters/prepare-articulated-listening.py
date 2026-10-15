"""Check bounded or complete articulated-support release and publish its phrase pair."""

import argparse
from array import array
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from audio_comparison import Pcm16, prepare_window_comparison, read_pcm16
from sid_clock import NTSC_CLOCK, NTSC_FRAME_CYCLES
from verify_player import require

spec = importlib.util.spec_from_file_location('ghostbusters_initial_listening', Path(__file__).with_name('prepare-stereo-listening.py'))
initial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(initial)


def difference(native, disabled, start, end):
    rate = native.sample_rate
    first, last = round(start * rate), round(end * rate)
    require(0 <= first < last <= native.frames, 'Release measurement window exceeds the initialized diagnostic')
    total = squares = peak = 0
    for frame in range(first, last):
        value = native.samples[frame * 2 + 1] - disabled.samples[frame * 2 + 1]
        total += value
        squares += value * value
        peak = max(peak, abs(value))
    count = last - first
    return dict(rms=math.sqrt(squares / count), acRms=math.sqrt((squares * count - total * total) / count ** 2),
                dc=total / count, peak=peak)


def check_release(native, disabled, ledger, proof, *, seconds=48):
    require(seconds in (48, 245), 'Choose the bounded 48-second or complete 245-second release check')
    require((native.channels, native.frames) == (2, seconds * native.sample_rate)
            and (native.sample_rate, native.channels, native.frames) == (disabled.sample_rate, disabled.channels, disabled.frames),
            f'Release control requires matching initialized {seconds}-second stereo renders')
    require(native.samples[::2] == disabled.samples[::2], 'Gate-off control changed the left PCM')
    require(len(ledger) >= 3 and all(row['endCall'] - row['startCall'] == 40 for row in ledger),
            'The bounded source-root-prefix trial requires complete 40-call gates')
    predicted = (proof['cpu']['musicEntryFromInit'] + ledger[0]['startCall'] * NTSC_FRAME_CYCLES) / NTSC_CLOCK
    first_difference = next((frame for frame in range(native.frames)
        if native.samples[frame * 2 + 1] != disabled.samples[frame * 2 + 1]), None)
    require(first_difference is not None, 'No support contribution was rendered')
    observed = first_difference / native.sample_rate
    offset = observed - predicted
    require(abs(offset) <= .025, 'Observed support alignment exceeds the bounded renderer/init offset')
    at = lambda call: (proof['cpu']['musicEntryFromInit'] + call * NTSC_FRAME_CYCLES) / NTSC_CLOCK + offset
    prefix = round((predicted - .025) * native.sample_rate) * 2
    require(native.samples[:prefix] == disabled.samples[:prefix], 'Gate-off control changed audio before support')
    rows = []
    for row in ledger:
        start, end, boundary = at(row['startCall']), at(row['endCall']), at(row['startCall'] + 128)
        if boundary > seconds:
            continue
        attack = difference(native, disabled, start + .025, start + .1)
        body = difference(native, disabled, start + .15, end - .05)
        release = difference(native, disabled, end + .015, end + .06)
        gap = difference(native, disabled, boundary - .3, boundary - .05)
        require(attack['acRms'] > 0 and body['acRms'] > 32, 'The articulated support lost its attack or body')
        require(0 < release['acRms'] < body['acRms'], 'The support has no decaying rendered release body')
        require(gap['rms'] <= 1 and gap['peak'] <= 2, 'Rendered support persists into the late gap')
        rows.append(dict(attack=attack, body=body, release=release, gap=gap))
    require(len(rows) >= 2, 'No complete retrigger gaps were checked')
    require(seconds != 245 or len(rows) == len(ledger), 'Complete release check excludes a capture-edge support gap')
    scope = ('Complete 245-second render; each prefix is checked before its own source-pattern boundary, including section exits and the final prefix'
             if seconds == 245 else 'First 48 seconds and first source support region only; final truncated release and later harmony exits are outside this render')
    return dict(passed=True, scope=scope,
                leftPcmIdentical=True, preSupportPcmIdentical=True, checkedCompleteGaps=len(rows),
                excludedCaptureEdgeGaps=len(ledger) - len(rows), sourcePatternCalls=128,
                gateCalls=40, gateSeconds=40 * NTSC_FRAME_CYCLES / NTSC_CLOCK,
                alignment=dict(predictedFirstGateSeconds=predicted, observedFirstContributionSeconds=observed,
                               rendererAndAttackOffsetSeconds=offset, maximumAbsoluteOffsetSeconds=.025),
                measurementClock='Native 17095-cycle call grid aligned to the first detected causal contribution; offset includes renderer startup and first attack latency. Windows exclude dispatch/onset margins.',
                windows=dict(attackAfterGate=[.025, .1], bodyAfterGate=.15, bodyBeforeOff=.05,
                             earlyReleaseAfterOff=[.015, .06], lateGapBeforePatternBoundary=[.3, .05]),
                minimumAttackAcRms=min(row['attack']['acRms'] for row in rows),
                minimumBodyAcRms=min(row['body']['acRms'] for row in rows),
                minimumEarlyReleaseAcRms=min(row['release']['acRms'] for row in rows),
                maximumEarlyReleaseToBodyRatio=max(row['release']['acRms'] / row['body']['acRms'] for row in rows),
                maximumLateGapRms=max(row['gap']['rms'] for row in rows),
                maximumLateGapPeak=max(row['gap']['peak'] for row in rows),
                limits=dict(lateGapRms=1, lateGapPeak=2), fullSongVerified=seconds == 245, musicalAcceptanceEstablished=False)


def common_gain(audio):
    peak = max(max(abs(value) for value in item.samples) for item in audio)
    require(0 < peak < 32767 and not any(-32768 in item.samples for item in audio), 'An audition is empty or contains PCM rail samples')
    return min(1, math.floor(32767 * 10 ** (-1 / 20)) / peak)


def scaled(audio, gain):
    return Pcm16(audio.sample_rate, audio.channels, audio.frames,
                 array('h', (round(value * gain) for value in audio.samples)), '')


def prepare(old_path, native_path, disabled_path, proof_path, sid_path, ledger_path, output, *, seconds=48, calls=2600):
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh listening preparation directory')
    old, native, disabled = (read_pcm16(path) for path in (old_path, native_path, disabled_path))
    require(old.channels == native.channels == 2 and old.sample_rate == native.sample_rate == 44100
            and old.frames >= seconds * 44100, 'The old/new audition requires initialized matching stereo inputs')
    proof_bytes, ledger_bytes = proof_path.read_bytes(), ledger_path.read_bytes()
    proof, ledger = json.loads(proof_bytes), json.loads(ledger_bytes)
    require(calls == (2600 if seconds == 48 else 14389), 'Calls must cover the selected bounded or complete verification target')
    initial.require_native_proof(proof, calls)
    public = initial.public_native_proof(proof, proof_bytes, sid_path.read_bytes())
    release = check_release(native, disabled, ledger, proof, seconds=seconds)
    old_prefix = initial.window(old, 0, seconds)
    gain = common_gain((old_prefix, native, disabled))
    scope = ('Complete 245-second initialized native/control render; phrase comparison is 16–32 seconds; complete musical review remains separate'
             if seconds == 245 else '48-second initialized diagnostic; old/new audition is 16–32 seconds; no complete revised performance claim')
    report = dict(schemaVersion=1, passed=True, scope=scope,
        commonGain=gain, matching='One common attenuation scalar for old, articulated and control audio, identical on left/right; no independent RMS matching',
        release=release, privateLedgerSha256=hashlib.sha256(ledger_bytes).hexdigest(),
        inputs=[dict(path=str(path.resolve()), sha256=audio.sha256) for path, audio in
                ((old_path, old), (native_path, native), (disabled_path, disabled))],
        musicalAcceptance=None, fullSongPending=seconds != 245)
    created = []
    output.mkdir(parents=True)
    try:
        for name, audio in (('initial-held-phrase.wav', old), ('articulated-phrase.wav', native)):
            initial.write_pcm(output / name, scaled(initial.window(audio, 16, 32), gain), created)
        comparison = prepare_window_comparison(output / 'initial-held-phrase.wav', output / 'articulated-phrase.wav',
            output / 'initial-then-articulated-phrase', start_seconds=0, end_seconds=16)
        created.extend((output / 'initial-then-articulated-phrase.ab.wav', output / 'initial-then-articulated-phrase.comparison.json'))
        report['comparisonSha256'] = comparison['comparison']['sha256']
        for name, value in (('audio.json', report), ('native-proof.json', public)):
            with (output / name).open('x') as target:
                created.append(output / name)
                json.dump(value, target, indent=2, allow_nan=False)
                target.write('\n')
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        output.rmdir()
        raise
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('old', 'native', 'disabled', 'proof', 'sid', 'ledger', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--seconds', type=int, choices=(48, 245), default=48)
    parser.add_argument('--calls', type=int, default=2600)
    args = parser.parse_args()
    prepare(args.old, args.native, args.disabled, args.proof, args.sid, args.ledger, args.output,
            seconds=args.seconds, calls=args.calls)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f'Ghostbusters articulated audition: {error}')
