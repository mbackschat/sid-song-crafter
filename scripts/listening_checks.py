"""Check listening-package inputs without changing them or claiming audibility."""

import gzip
import hashlib
import json
import math
from pathlib import Path
import re

from audio_comparison import Pcm16, measure_pcm, read_pcm16


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _hash_pin(value):
    _require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value),
             'Expected SHA-256 must contain 64 lowercase hexadecimal characters')


def _receipt(report, output, sources):
    output = Path(output)
    _require(output.resolve() not in sources, f'Receipt would overwrite a source: {output}')
    _require(not output.exists() and not output.is_symlink(), f'Receipt already exists: {output}')
    payload = json.dumps(report, indent=2, allow_nan=False) + '\n'
    output.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with output.open('x', encoding='utf-8') as receipt:
            created = True
            receipt.write(payload)
    except Exception:
        if created:
            output.unlink(missing_ok=True)
        raise
    return report


def check_asset(source, *, sha256, output):
    _hash_pin(sha256)
    source = Path(source).resolve()
    raw = source.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    _require(actual == sha256, f'Asset SHA-256 does not match expected pin: {source}')
    report = {'schemaVersion': 1, 'check': 'asset', 'passed': True,
              'expectedSha256': sha256,
              'inputs': [{'path': str(source), 'sha256': actual, 'bytes': len(raw)}]}
    return _receipt(report, output, [source])


def _read_writes(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    try:
        decompressed = gzip.decompress(raw) if path.suffix == '.gz' else raw
    except (OSError, EOFError) as error:
        raise ValueError(f'Cannot decompress SID writes: {path}') from error
    fingerprint = {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(),
                   'decompressedSha256': hashlib.sha256(decompressed).hexdigest()}
    return decompressed, fingerprint


def _scoped_writes(raw, calls, label, *, allow_extra_calls):
    try:
        rows = json.loads(raw)
    except ValueError as error:
        raise ValueError(f'{label} SID writes are not valid JSON') from error
    _require(isinstance(rows, list), f'{label} SID writes must be a JSON array')
    selected, seen_calls = [], set()
    init_count, previous_tick = 0, -1
    for index, row in enumerate(rows):
        _require(isinstance(row, dict) and all(key in row for key in ('phase', 'tick', 'address', 'value')),
                 f'{label} write {index} lacks phase, tick, address or value')
        phase, tick, address, value = (row[key] for key in ('phase', 'tick', 'address', 'value'))
        _require(type(address) is int and 0 <= address <= 0xffff and type(value) is int and 0 <= value <= 255,
                 f'{label} write {index} has an invalid address or value')
        if phase == 'init':
            _require(tick is None and previous_tick == -1, f'{label} initialization must precede play writes and use a null tick')
            init_count += 1
        elif phase == 'play':
            _require(type(tick) is int and tick >= 0, f'{label} write {index} has an invalid play tick')
            _require(tick >= previous_tick, f'{label} play ticks must be ordered')
            previous_tick = tick
            _require(allow_extra_calls or tick < calls, f'{label} play tick {tick} is outside declared play-call scope')
            if tick >= calls:
                continue
            seen_calls.add(tick)
        else:
            raise ValueError(f'{label} write {index} has an invalid phase')
        selected.append((phase, tick, address, value))
    _require(init_count > 0, f'{label} has no initialization writes')
    _require(seen_calls == set(range(calls)), f'{label} lacks complete play-call coverage 0..{calls - 1}')
    return selected, init_count


def check_writes(source, candidate, *, source_sha256, calls, output):
    _hash_pin(source_sha256)
    _require(type(calls) is int and calls > 0, 'Play-call count must be a positive integer')
    source_raw, source_pin = _read_writes(source)
    _require(source_pin['decompressedSha256'] == source_sha256,
             'Decompressed source SHA-256 does not match expected source SHA-256 pin')
    candidate_raw, candidate_pin = _read_writes(candidate)
    expected, init_count = _scoped_writes(source_raw, calls, 'Source', allow_extra_calls=True)
    actual, _ = _scoped_writes(candidate_raw, calls, 'Candidate', allow_extra_calls=False)
    _require(expected == actual, 'Source and candidate ordered SID writes differ (phase, tick, address, value; duplicates retained)')
    report = {
        'schemaVersion': 1, 'check': 'writes', 'passed': True,
        'inputs': [dict(label='source', **source_pin), dict(label='candidate', **candidate_pin)],
        'expectedSourceDecompressedSha256': source_sha256,
        'scope': {'initialization': True, 'playCalls': calls, 'firstCall': 0, 'lastCallInclusive': calls - 1},
        'identityFields': ['phase', 'tick', 'address', 'value'],
        'matchedWrites': len(expected), 'matchedInitWrites': init_count,
        'matchedPlayWrites': len(expected) - init_count,
        'claims': {'orderedRegisterWriteIdentity': True, 'busCycleIdentity': False, 'perceptualAgreement': False},
    }
    return _receipt(report, output, [Path(source_pin['path']), Path(candidate_pin['path'])])


def check_audio(reference, candidate, *, seconds, output, sample_rate=44100, channels=1,
                tail_seconds=None, max_tail_ac_rms=None):
    _require(type(sample_rate) is int and sample_rate > 0, 'Expected sample rate must be a positive integer')
    _require(type(channels) is int and channels in (1, 2), 'Expected channels must be one or two')
    _require(math.isfinite(seconds) and seconds > 0 and math.isfinite(seconds * sample_rate),
             'Expected duration must be finite and positive')
    frames = round(seconds * sample_rate)
    _require(frames > 0, 'Expected duration rounds to zero sample frames')
    tail_frames = None
    if tail_seconds is not None or max_tail_ac_rms is not None:
        _require(type(tail_seconds) in (int, float) and math.isfinite(tail_seconds)
                 and 0 < tail_seconds <= seconds, 'Expected tail duration within the full render')
        _require(type(max_tail_ac_rms) in (int, float) and math.isfinite(max_tail_ac_rms)
                 and max_tail_ac_rms >= 0, 'Expected nonnegative finite tail AC RMS limit')
        tail_frames = round(tail_seconds * sample_rate)
        _require(tail_frames > 0, 'Expected tail duration of at least one sample frame')
    measurements, endings = [], []
    for label, path in (('reference', reference), ('candidate', candidate)):
        path = Path(path).resolve()
        audio = read_pcm16(path)
        metrics = dict(path=str(path), sha256=audio.sha256, **measure_pcm(audio))
        _require(metrics['sampleRate'] == sample_rate, f'{label} sample rate differs from expected {sample_rate}')
        _require(metrics['channels'] == channels, f'{label} channels differ from expected {channels}')
        _require(metrics['frames'] == frames, f'{label} frame count differs from expected {frames}')
        _require(metrics['clippedSamples'] == 0, f'{label} has PCM rail samples indicating possible clipping')
        _require(metrics['acRms'] > 0, f'{label} has no AC energy (silence or DC only)')
        measurements.append(dict(label=label, **metrics))
        if tail_frames is not None:
            tail = Pcm16(sample_rate, channels, tail_frames, audio.samples[-tail_frames * channels:], '')
            ending = measure_pcm(tail)
            _require(all(row['acRms'] <= max_tail_ac_rms for row in ending['perChannel']),
                     f'{label} tail exceeds the per-channel AC RMS limit')
            endings.append(dict(label=label, **ending))
    report = {
        'schemaVersion': 1, 'check': 'audio', 'passed': True,
        'requestedSeconds': seconds, 'expectedFrames': frames,
        'expectedSampleRate': sample_rate, 'expectedChannels': channels,
        'durationRule': 'round(seconds * sampleRate) sample frames',
        'inputs': measurements,
        'claims': {'pcmIdentity': False, 'perceptualAgreement': False},
    }
    if tail_frames is not None:
        report['ending'] = dict(requestedSeconds=tail_seconds, frames=tail_frames,
                                maximumChannelAcRms=max_tail_ac_rms, measurements=endings,
                                scope='Final PCM window only; DC reported separately. A settled tail does not establish a musically complete ending.')
    return _receipt(report, output, [Path(row['path']) for row in measurements])
