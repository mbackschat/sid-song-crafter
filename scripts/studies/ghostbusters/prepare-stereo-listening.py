"""Verify native stereo evidence and prepare matched Ghostbusters auditions."""

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
from audio_comparison import Pcm16, measure_pcm, prepare_window_comparison, read_pcm16
from verify_player import require


SID_BASES = [0xd400, 0xd420]
WINDOWS = (('opening', 0, 12), ('phrase', 16, 32), ('ending', 225, 245))


def window(audio, start, end):
    first, last = round(start * audio.sample_rate), round(end * audio.sample_rate)
    require(0 <= first < last <= audio.frames, 'Window exceeds the initialized render')
    return Pcm16(audio.sample_rate, audio.channels, last - first,
                 audio.samples[first * audio.channels:last * audio.channels], '')


def duplicate_mono(audio):
    return Pcm16(audio.sample_rate, 2, audio.frames,
                 array('h', (sample for value in audio.samples for sample in (value, value))), '')


def fold_down(audio):
    return Pcm16(audio.sample_rate, 1, audio.frames,
                 array('h', (round((left + right) / 2)
                             for left, right in zip(audio.samples[::2], audio.samples[1::2]))), '')


def require_native_proof(proof, calls):
    require(proof.get('header', {}).get('sidCount') == 2, 'A passing two-bank native proof is required')
    for name, budget in (('cpu', 'maximumNmiCyclesIncludingEntry'), ('vice', 'maximumObservedNmiCyclesIncludingEntry')):
        section = proof.get(name, {})
        counts = section.get('perBankStores', {})
        require(section.get('passed') is True and section.get('checkedMusicCalls') == calls
                and section.get('sidBases') == SID_BASES
                and all(type(counts.get(str(base))) is int and counts[str(base)] > 0 for base in SID_BASES)
                and type(section.get(budget)) is int and 0 < section[budget] < 102,
                f'A passing complete two-bank {name} native proof is required')
    cpu, vice = proof['cpu'], proof['vice']
    require(cpu.get('allOrderedStoresMatch') is True and cpu.get('noSpeechNmiDuringMusic') is True
            and all(type(cpu.get(field)) is int and cpu[field] > 0
                    for field in ('leadMirrorStores', 'sharedVolumeMirrorStores', 'supportStores'))
            and vice.get('completedMusicCalls') == calls,
            'A passing mirrored-lead/speech and added-support native proof is required')


def public_native_proof(proof, proof_bytes, sid_bytes):
    actual_sid_hash = hashlib.sha256(sid_bytes).hexdigest()
    require(proof['header'].get('sha256') == actual_sid_hash, 'Native proof must bind the actual SID bytes')

    def fields(record, names):
        return {name: record[name] for name in names if name in record}

    header = fields(proof['header'], ('format', 'version', 'bytes', 'sha256', 'dataOffset', 'loadAddress',
        'endAddressExclusive', 'initAddress', 'playAddress', 'subtunes', 'defaultSubtune', 'selectedSubtune',
        'speedWord', 'flags', 'clockDeclaration', 'sidModelDeclaration', 'selectedTimingDeclaration', 'sidCount', 'sidBases'))
    cpu_fields = ('passed', 'scope', 'bootstrap', 'checkedMusicCalls', 'namedMusicStates', 'checkedStores',
        'sidBases', 'perBankStores', 'leadMirrorStores', 'sharedVolumeMirrorStores', 'supportStores',
        'generatedSpeechTicks', 'maximumNmiCyclesIncludingEntry', 'timerSampleCycles', 'timerMusicCycles',
        'musicEntryFromInit', 'allOrderedStoresMatch', 'noSpeechNmiDuringMusic', 'decimalEntryCleared',
        'nativeCpuCycles', 'fastForwardedIdleIterations', 'timedStoreSequenceSha256')
    report = dict(schemaVersion=1, passed=True,
        scope='Allowlisted aggregate native execution evidence; complete source checkpoints and speech data remain private',
        privateNativeProof=dict(filename='verification.json', bytes=len(proof_bytes), sha256=hashlib.sha256(proof_bytes).hexdigest()),
        header=header,
        generatedSpeechMatchesRetainedSerializedOriginalCpu=proof.get('generatedSpeechMatchesRetainedSerializedOriginalCpu'))
    for section in ('cpu', 'prgBootstrap', 'poisonedInit'):
        if section not in proof:
            continue
        report[section] = fields(proof[section], cpu_fields)
        intervals = proof[section].get('musicIntervals', [])
        if intervals:
            report[section]['musicIntervals'] = dict(count=len(intervals), minimum=min(intervals), maximum=max(intervals))
    report['vice'] = fields(proof['vice'], ('passed', 'scope', 'checkedMusicCalls', 'completedMusicCalls',
        'sidBases', 'perBankStores', 'leadMirrorStores', 'sharedVolumeMirrorStores', 'supportStores',
        'terminalPlayExecuted', 'cycleLimit', 'processTimeoutSeconds', 'sidStores', 'sidReads', 'nmiEntries',
        'nestedNmi', 'samplePeriodCycles', 'sampleEntryJitter', 'maximumObservedNmiCyclesIncludingEntry',
        'musicPeriodCycles', 'musicIntervals', 'actualInitRelativeFirstNmi', 'actualInitRelativeMusicInit',
        'actualInitRelativeFirstMusic', 'tools'))
    if 'extendedSourceMusic' in proof:
        source = proof['extendedSourceMusic']
        report['sourceMusic'] = fields(source, ('sourceSha256', 'freshOriginalMusicCpu', 'checkedMusicCalls',
            'matchedStores', 'namedReturns', 'scope', 'speechOrFullMachineSourceIdentity'))
        report['sourceMusic']['independentCompiled'] = fields(source.get('fullIndependentCompiledMusic', {}),
            ('checkedPlayCalls', 'completeNumericRange', 'completeCompiledRange', 'maximumPlayCycles',
             'callableBoundaries', 'namedStateBoundaries'))
    return report


def check_support_control(native, disabled, *, gain, sample_rate=44100):
    require((disabled.sample_rate, disabled.channels, disabled.frames) == (sample_rate, 2, 245 * sample_rate),
            'Support gate-off diagnostic must retain the complete 245-second raw stereo format')
    require((native.sample_rate, native.channels, native.frames) == (disabled.sample_rate, disabled.channels, disabled.frames),
            'Support gate-off diagnostic must match the native render format')
    require(0 < gain <= 1 and math.isfinite(gain), 'Support gate-off diagnostic requires the native whole-file gain')
    require(measure_pcm(disabled)['clippedSamples'] == 0, 'Support gate-off diagnostic contains PCM rail samples')
    require(native.samples[::2] == disabled.samples[::2], 'Support gate-off diagnostic changed the left chip PCM')
    require(native.samples[:15 * sample_rate * 2] == disabled.samples[:15 * sample_rate * 2],
            'Support gate-off diagnostic changed audio before the first support onset')
    total = squares = count = peak = 0
    for frame in range(16 * sample_rate, 32 * sample_rate):
        value = native.samples[frame * 2 + 1] - disabled.samples[frame * 2 + 1]
        total += value
        squares += value * value
        peak = max(peak, abs(value))
        count += 1
    ac_rms = math.sqrt((squares * count - total * total) / (count * count))
    require(ac_rms > 0, 'Support gate-off diagnostic has no right-channel AC contribution in the selected phrase')
    return dict(scope='Same native image with only the held-support gate-on immediate masked; a controlled whole-mix diagnostic, not a stem',
                candidateSha256=native.sha256, supportDisabledSha256=disabled.sha256,
                leftPcmIdentical=True, preSupportPcmIdentical=True, preSupportSeconds=[0, 15],
                gain=gain, normalization='Same candidate full-file scalar on both diagnostic channels; no independent matching',
                phrase=dict(seconds=[16, 32], rightDifferenceAcRms=ac_rms, rightDifferencePeak=peak,
                            matchedRightDifferenceAcRms=ac_rms * gain),
                audibleUsefulnessEstablished=False, musicalAcceptanceEstablished=False)


def match_full_files(audio, measurements):
    peak_limit = math.floor(32767 * 10 ** (-1 / 20))
    target = min(*(metrics['acRms'] for metrics in measurements),
                 *(metrics['acRms'] * peak_limit / metrics['peak'] for metrics in measurements))
    matched, inputs = [], []
    for label, original, metrics in zip(('reference', 'native'), audio, measurements):
        gain = target / metrics['acRms']
        value = Pcm16(original.sample_rate, 2, original.frames,
                      array('h', (round(sample * gain) for sample in original.samples)), '')
        result = measure_pcm(value)
        require(result['peak'] <= peak_limit and result['clippedSamples'] == 0 and result['acRms'] > 0,
                'Whole-file gain exceeds headroom or removes the signal')
        matched.append(value)
        inputs.append(dict(label=label, gain=gain, gainDb=20 * math.log10(gain), original=metrics, matched=result))
    return matched, dict(method='Complete-file pooled channel AC power, including speech, silence and continuation',
                         scopeSeconds=[0, audio[0].frames / audio[0].sample_rate],
                         gainPolicy='One attenuation-only scalar per full file, applied equally to both channels; all windows retain that gain',
                         peakHeadroomDb=1, peakLimit=peak_limit, targetAcRms=target, inputs=inputs)


def check_audio(reference, native, *, proof, sample_rate=44100, seconds=245, calls=14389):
    require(seconds in (48, 245), 'Only the 48-second diagnostic or complete 245-second audition is supported')
    require_native_proof(proof, calls)
    require((reference.channels, reference.sample_rate) == (1, sample_rate)
            and reference.frames in ({48 * sample_rate, 245 * sample_rate} if seconds == 48 else {245 * sample_rate}),
            f'The faithful mono reference must cover exactly {seconds} seconds or the complete accepted diagnostic source')
    require((native.channels, native.sample_rate, native.frames) == (2, sample_rate, seconds * sample_rate),
            f'The raw native stereo render must cover exactly {seconds} seconds')
    duplicated = duplicate_mono(window(reference, 0, seconds))
    measurements = [measure_pcm(value) for value in (duplicated, native)]
    for label, metrics in zip(('reference', 'native'), measurements):
        require(metrics['clippedSamples'] == 0, f'{label} contains PCM rail samples')
        require(all(channel['acRms'] > 0 for channel in metrics['perChannel']), f'{label} has an empty chip channel')
    phrase_audio = window(native, 16, 32)
    side = Pcm16(sample_rate, 1, phrase_audio.frames,
                 array('h', (round((left - right) / 2)
                             for left, right in zip(phrase_audio.samples[::2], phrase_audio.samples[1::2]))), '')
    side_level = measure_pcm(side)['acRms']
    require(side_level > 0, 'The phrase has no stereo difference signal')
    matched, matching = match_full_files((duplicated, native), measurements)
    mono = fold_down(native)
    mono_metrics = measure_pcm(mono)
    require(mono_metrics['acRms'] > 0 and mono_metrics['clippedSamples'] == 0, 'Native mono fold-down is empty or clipped')
    report = dict(schemaVersion=1, passed=True,
                  scope='Complete 245-second initialized speech/music continuation' if seconds == 245 else '48-second initialized diagnostic',
                  sourceFiles=[dict(label=label, sha256=audio.sha256, **measure_pcm(audio))
                               for label, audio in (('accepted mono', reference), ('native stereo', native))],
                  referenceMatrix=[[1], [1]], nativeMatrix=[[1, 0], [0, 1]],
                  routing='Raw SID A left and SID B right; no external stereo crossfeed or per-channel normalization',
                  matching=matching, phrase=dict(seconds=[16, 32], sideAcRms=side_level, metrics=measure_pcm(phrase_audio)),
                  monoFoldDown=dict(matrix=[[.5, .5]], metrics=mono_metrics),
                  claims=dict(bothSidBanksExecuted=True, primaryPcmIdentity=False,
                              phaseCoherentCenterEstablished=False, musicalAcceptanceEstablished=False),
                  listeningVerdict=None)
    if seconds == 245:
        continuation = measure_pcm(window(native, 225, 245))
        require(all(channel['acRms'] >= 32 for channel in continuation['perChannel']),
                'Native continuation lost its final body; no fade or silent substitute is expected')
        report['continuation'] = dict(seconds=[225, 245], metrics=continuation,
                                      meaning='Source restart/continuation retained; the capture boundary is not a composed ending')
    return report, duplicated, *matched


def write_pcm(path, audio, created):
    values = array('h', audio.samples)
    if sys.byteorder != 'little':
        values.byteswap()
    with path.open('xb') as handle:
        created.append(path)
        with wave.open(handle, 'wb') as output:
            output.setparams((audio.channels, 2, audio.sample_rate, 0, 'NONE', 'not compressed'))
            output.writeframes(values.tobytes())


def prepare(reference_path, native_path, output, *, proof_path, sid_path, support_disabled_path=None,
            sample_rate=44100, seconds=245, calls=14389):
    output = Path(output)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh preparation directory')
    reference, native = (read_pcm16(path) for path in (reference_path, native_path))
    proof_bytes = Path(proof_path).read_bytes()
    proof = json.loads(proof_bytes)
    report, duplicated, matched_reference, matched_native = check_audio(
        reference, native, proof=proof, sample_rate=sample_rate, seconds=seconds, calls=calls)
    public_proof = public_native_proof(proof, proof_bytes, Path(sid_path).read_bytes())
    disabled = read_pcm16(support_disabled_path) if support_disabled_path is not None else None
    if disabled is not None:
        report['supportControl'] = check_support_control(native, disabled,
            gain=report['matching']['inputs'][1]['gain'], sample_rate=sample_rate)
    report['nativeProof'] = dict(path=str(Path(proof_path).resolve()), sha256=hashlib.sha256(proof_bytes).hexdigest())
    report['sourcePaths'] = [str(Path(path).resolve()) for path in (reference_path, native_path)]
    report['outputs'] = {}
    created = []
    output.mkdir(parents=True)
    try:
        for name, audio in (('reference-duplicated-full.wav', duplicated),
                            ('reference-matched-full.wav', matched_reference), ('native-matched-full.wav', matched_native),
                            ('native-mono-diagnostic.wav', fold_down(native))):
            write_pcm(output / name, audio, created)
        for role, start, end in WINDOWS:
            if end > seconds:
                continue
            prefix = output / f'{role}-mono-then-stereo'
            comparison = prepare_window_comparison(output / 'reference-matched-full.wav', output / 'native-matched-full.wav',
                                                   prefix, start_seconds=start, end_seconds=end)
            created.extend((Path(str(prefix) + '.ab.wav'), Path(str(prefix) + '.comparison.json')))
            report.setdefault('comparisons', {})[role] = dict(seconds=[start, end],
                order=['Accepted faithful mono, duplicated equally to left and right', 'Native two-SID candidate'],
                matching='The complete-file scalar gains above; no additional window matching',
                comparisonSha256=comparison['comparison']['sha256'])
        if disabled is not None:
            gain = report['supportControl']['gain']
            original_window = window(disabled, 16, 32)
            matched_disabled = Pcm16(sample_rate, 2, original_window.frames,
                array('h', (round(value * gain) for value in original_window.samples)), '')
            write_pcm(output / 'support-disabled-matched-phrase.wav', matched_disabled, created)
            write_pcm(output / 'support-enabled-matched-phrase.wav', window(matched_native, 16, 32), created)
            prefix = output / 'support-enabled-then-disabled-diagnostic'
            comparison = prepare_window_comparison(output / 'support-enabled-matched-phrase.wav',
                output / 'support-disabled-matched-phrase.wav', prefix, start_seconds=0, end_seconds=16)
            created.extend((Path(str(prefix) + '.ab.wav'), Path(str(prefix) + '.comparison.json')))
            report['supportControl']['comparisonSha256'] = comparison['comparison']['sha256']
        with (output / 'native-proof.json').open('x') as target:
            created.append(output / 'native-proof.json')
            json.dump(public_proof, target, indent=2, allow_nan=False)
            target.write('\n')
        for path in created:
            report['outputs'][path.name] = dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        with (output / 'audio.json').open('x') as target:
            created.append(output / 'audio.json')
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
    for name in ('reference', 'native', 'proof', 'sid', 'output'):
        parser.add_argument(f'--{name}', type=Path, required=True)
    parser.add_argument('--support-disabled-render', type=Path)
    parser.add_argument('--seconds', type=int, default=245, choices=(48, 245))
    parser.add_argument('--calls', type=int, default=14389)
    args = parser.parse_args()
    prepare(args.reference, args.native, args.output, proof_path=args.proof, sid_path=args.sid,
            support_disabled_path=args.support_disabled_render, seconds=args.seconds, calls=args.calls)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(f'Ghostbusters stereo listening preparation failed: {error}')
