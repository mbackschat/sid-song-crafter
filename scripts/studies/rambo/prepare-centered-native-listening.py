"""Check and excerpt the native two-chip lead-duplication trial without remixing it."""

import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import sys
import wave


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from audio_comparison import Pcm16, measure_pcm, read_pcm16
from verify_player import require


def window(audio, start, end):
    first, last = round(start * audio.sample_rate), round(end * audio.sample_rate)
    require(0 <= first < last <= audio.frames, 'Window exceeds the initialized render')
    return Pcm16(audio.sample_rate, audio.channels, last - first,
                 audio.samples[first * audio.channels:last * audio.channels], '')


def fold_down(audio):
    return Pcm16(audio.sample_rate, 1, audio.frames,
                 array('h', (round((left + right) / 2) for left, right in zip(audio.samples[::2], audio.samples[1::2]))), '')


def lead_metrics(source, secondary):
    source_level, secondary_level = (measure_pcm(audio)['acRms'] for audio in (source, secondary))
    require(source_level > 0 and secondary_level > 0, 'An isolated lead diagnostic is empty')
    ratio = secondary_level / source_level
    return dict(sourceAcRms=source_level, secondaryAcRms=secondary_level,
                secondaryToSourceAcRmsRatio=ratio, secondaryMinusSourceDb=20 * math.log10(ratio),
                summedStereoLeadEnergyChangeDb=10 * math.log10(1 + ratio ** 2))


def check_audio(previous, native, source_lead, secondary_lead, *, proof, sample_rate=44100):
    require(proof.get('passed') is True and proof.get('primaryUnchanged') is True
            and all(proof.get('lead', {}).get(key) is True
                    for key in ('orderedStoresIdentical', 'dataAndSoundIdentical', 'morseIdentical'))
            and all(proof.get('inner', {}).get(key) is True
                    for key in ('orderedStoresIdentical', 'noteLedgerIdentical')),
            'A passing source-preservation proof is required')
    inputs, tails = [], []
    for label, audio in (('previous', previous), ('native', native)):
        require((audio.channels, audio.sample_rate, audio.frames) == (2, sample_rate, 225 * sample_rate),
                f'{label} must be the complete 225-second raw stereo render')
        metrics = measure_pcm(audio)
        require(metrics['clippedSamples'] == 0, f'{label} contains PCM rail samples')
        require(all(row['acRms'] > 0 for row in metrics['perChannel']), f'{label} has an empty chip channel')
        inputs.append(dict(label=label, sha256=audio.sha256, **metrics))
        tail = measure_pcm(window(audio, 224, 225))
        require(all(row['acRms'] <= 1 for row in tail['perChannel']), f'{label} has an unsettled tail')
        tails.append(dict(label=label, seconds=[224, 225], metrics=tail))
    closing = measure_pcm(window(native, 205, 211))
    require(all(row['acRms'] >= 32 for row in closing['perChannel']), 'A native chip bus lost its closing body')
    for label, audio in (('source lead', source_lead), ('secondary lead', secondary_lead)):
        require((audio.channels, audio.sample_rate, audio.frames) == (1, sample_rate, 104 * sample_rate),
                f'{label} must cover exactly 104 initialized mono seconds')
        require(measure_pcm(audio)['clippedSamples'] == 0, f'{label} contains PCM rail samples')
    lead = lead_metrics(window(source_lead, 88, 104), window(secondary_lead, 88, 104))
    warnings = []
    if abs(lead['secondaryMinusSourceDb']) > 3:
        warnings.append('Isolated lead levels differ by more than 3 dB in the main phrase; review without automatic gain changes.')
    mono = fold_down(native)
    mono_metrics = measure_pcm(mono)
    mono_closing = measure_pcm(window(mono, 205, 211))
    mono_tail = measure_pcm(window(mono, 224, 225))
    require(mono_metrics['clippedSamples'] == 0 and mono_metrics['acRms'] > 0, 'The mono fold-down is clipped or empty')
    require(mono_closing['acRms'] >= 32 and mono_tail['acRms'] <= 1, 'The mono fold-down lost its closing body or natural tail')
    phrase = measure_pcm(window(native, 88, 104))
    return dict(schemaVersion=1, passed=True, normalization='none', inputs=inputs,
                routing='Native SID A left and SID B right; source lead on A1 and its copy on B1; no external pan matrix.',
                claims=dict(sourceExecutionPreserved=True, primaryPcmIdentity=False,
                            phaseCoherentCenterEstablished=False, perceivedCenterEstablished=False),
                mainPhrase=dict(seconds=[88, 104], metrics=phrase),
                closingBody=dict(seconds=[205, 211], metrics=closing), finalTail=tails,
                leadDiagnostic=dict(mainPhrase=dict(seconds=[88, 104], **lead),
                                    initializedPrefix=dict(seconds=[0, 104], **lead_metrics(source_lead, secondary_lead)),
                                    warnings=warnings,
                                    scope='Independently initialized one-chip voice-1 control-mask diagnostics, not exact dual-render stems or phase proof. The energy change sums separate channel powers, not a coherent mono sum.'),
                monoFoldDown=dict(matrix=[[.5, .5]], normalization='none', metrics=mono_metrics,
                                  closingBody=mono_closing, finalTail=mono_tail, purpose='Internal compatibility diagnostic'),
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


def prepare(previous_path, native_path, source_lead_path, secondary_lead_path, output, *, proof_path, sample_rate=44100):
    output = Path(output)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh preparation directory')
    paths = (previous_path, native_path, source_lead_path, secondary_lead_path)
    previous, native, source_lead, secondary_lead = [read_pcm16(path) for path in paths]
    proof = json.loads(Path(proof_path).read_text())
    report = check_audio(previous, native, source_lead, secondary_lead, proof=proof, sample_rate=sample_rate)
    report['arrangementProof'] = dict(path=str(Path(proof_path).resolve()), sha256=hashlib.sha256(Path(proof_path).read_bytes()).hexdigest())
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
        mono_path = output / 'native-mono-diagnostic.wav'
        write_pcm(mono_path, fold_down(native), created)
        report['monoFoldDown']['sha256'] = hashlib.sha256(mono_path.read_bytes()).hexdigest()
        for label, audio in (('previous', previous), ('native', native)):
            for role, start, end in (('phrase', 88, 104), ('ending', 205, 225)):
                filename = f'{label}-raw-{role}.wav'
                target = output / filename
                write_pcm(target, window(audio, start, end), created)
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
    for name in ('previous', 'native', 'source-lead', 'secondary-lead', 'proof', 'output'):
        parser.add_argument(f'--{name}', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.previous, args.native, args.source_lead, args.secondary_lead, args.output, proof_path=args.proof)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f'Rambo centered-native listening preparation failed: {error}')
