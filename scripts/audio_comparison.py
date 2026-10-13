"""Measure PCM16 renders and prepare traceable unity-gain or level-matched A/B audio."""

from array import array
from dataclasses import dataclass
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import sys
import wave


@dataclass
class Pcm16:
    sample_rate: int
    channels: int
    frames: int
    samples: array
    sha256: str


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _dbfs(value):
    return 20 * math.log10(value / 32768) if value else None


def read_pcm16(path):
    path = Path(path)
    raw = path.read_bytes()
    try:
        with wave.open(BytesIO(raw), "rb") as source:
            _require(source.getcomptype() == "NONE" and source.getsampwidth() == 2 and source.getnchannels() in (1, 2), "WAV must be uncompressed PCM16 with one or two channels")
            rate, channels, frames = source.getframerate(), source.getnchannels(), source.getnframes()
            _require(rate > 0, "WAV sample rate must be positive")
            _require(frames > 0, "WAV is empty")
            data = source.readframes(frames)
            _require(len(data) == frames * channels * 2, "WAV PCM data is truncated")
    except (wave.Error, EOFError) as error:
        raise ValueError(f"Cannot read PCM16 WAV {path}: {error}") from error
    samples = array("h", data)
    if sys.byteorder != "little":
        samples.byteswap()
    return Pcm16(rate, channels, frames, samples, hashlib.sha256(raw).hexdigest())


def measure_pcm(audio):
    per_channel = []
    for channel in range(audio.channels):
        samples = audio.samples[channel::audio.channels]
        total = sum(samples)
        squares = sum(value * value for value in samples)
        # Integer central moments retain tiny AC signals atop a large DC offset.
        ac_power = (squares * audio.frames - total * total) / (audio.frames * audio.frames)
        per_channel.append({"dc": total / audio.frames, "rms": math.sqrt(squares / audio.frames), "acRms": math.sqrt(ac_power)})
    peak = max(abs(value) for value in audio.samples)
    ac_rms = math.sqrt(sum(channel["acRms"] ** 2 for channel in per_channel) / audio.channels)
    return {
        "format": "PCM16",
        "sampleRate": audio.sample_rate,
        "channels": audio.channels,
        "frames": audio.frames,
        "durationSeconds": audio.frames / audio.sample_rate,
        "peak": peak,
        "peakDbfs": _dbfs(peak),
        "clippedSamples": sum(value in (-32768, 32767) for value in audio.samples),
        "rms": math.sqrt(sum(channel["rms"] ** 2 for channel in per_channel) / audio.channels),
        "acRms": ac_rms,
        "acRmsDbfs": _dbfs(ac_rms),
        "perChannel": per_channel,
    }


def inspect_wav(path):
    path = Path(path).resolve()
    audio = read_pcm16(path)
    return {"path": str(path), "sha256": audio.sha256, **measure_pcm(audio)}


def _pcm_bytes(samples):
    if sys.byteorder == "little":
        return samples.tobytes()
    little_endian = array("h", samples)
    little_endian.byteswap()
    return little_endian.tobytes()


def _write_wav(path, audio, chunks, created):
    with path.open("xb") as file:
        created.append(path)
        with wave.open(file, "wb") as output:
            output.setparams((audio.channels, 2, audio.sample_rate, 0, "NONE", "not compressed"))
            for chunk in chunks:
                output.writeframesraw(_pcm_bytes(chunk))


def prepare_comparison(a_path, b_path, prefix, *, target_ac_rms_dbfs=None, peak_headroom_db=1.0, gap_seconds=0.5, individual_copies=False):
    _require(math.isfinite(peak_headroom_db) and peak_headroom_db >= 0, "Peak headroom must be a finite nonnegative dB value")
    _require(math.isfinite(gap_seconds) and 0 <= gap_seconds <= 60, "Gap must be finite and between zero and 60 seconds")
    if target_ac_rms_dbfs is not None:
        _require(math.isfinite(target_ac_rms_dbfs) and target_ac_rms_dbfs <= 0, "AC RMS target must be a finite dBFS value no greater than zero")
    peak_limit = min(32766, math.floor(32767 * 10 ** (-peak_headroom_db / 20)))
    _require(peak_limit > 0, "Peak headroom leaves no usable PCM16 range")

    sources = [Path(path).resolve() for path in (a_path, b_path)]
    prefix = Path(prefix).resolve()
    comparison_path = Path(str(prefix) + ".ab.wav")
    manifest_path = Path(str(prefix) + ".comparison.json")
    matched_paths = [Path(str(prefix) + f".{label}.matched.wav") for label in ("a", "b")] if individual_copies else []
    outputs = [comparison_path, manifest_path, *matched_paths]
    for path in outputs:
        _require(path.resolve() not in sources, f"Output would overwrite a source WAV: {path}")
        _require(not path.exists() and not path.is_symlink(), f"Output already exists: {path}")

    audio = [read_pcm16(path) for path in sources]
    _require((audio[0].sample_rate, audio[0].channels, audio[0].frames) == (audio[1].sample_rate, audio[1].channels, audio[1].frames), "A and B must have the same sample rate, channels, and frame count; render aligned phrases rather than resampling or padding them")
    measurements = [measure_pcm(value) for value in audio]
    for label, metrics in zip(("A", "B"), measurements):
        _require(metrics["clippedSamples"] == 0, f"{label} contains PCM rail samples indicating possible hard clipping; retain it and rerender without clipping")
        _require(metrics["acRms"] > 0, f"{label} contains no AC energy (silence or DC only)")

    safe_target = min(metrics["acRms"] * peak_limit / metrics["peak"] for metrics in measurements)
    if target_ac_rms_dbfs is None:
        target = min(safe_target, *(metrics["acRms"] for metrics in measurements))
    else:
        target = 32768 * 10 ** (target_ac_rms_dbfs / 20)
        _require(target > 0, "AC RMS target is too small to represent")
        _require(target <= safe_target + 1e-9, f"Requested AC RMS target exceeds peak headroom; use at most {_dbfs(safe_target):.3f} dBFS")

    gains = [target / metrics["acRms"] for metrics in measurements]
    matched = []
    matched_metrics = []
    for original, gain in zip(audio, gains):
        values = array("h", (round(value * gain) for value in original.samples))
        value = Pcm16(original.sample_rate, original.channels, original.frames, values, "")
        metrics = measure_pcm(value)
        _require(metrics["peak"] <= peak_limit and metrics["clippedSamples"] == 0, "Quantized output would exceed peak headroom")
        _require(metrics["acRms"] > 0, "Level matching quantized away all AC energy; use a less extreme comparison")
        matched.append(value)
        matched_metrics.append(metrics)

    frames, rate = audio[0].frames, audio[0].sample_rate
    gap_frames = round(gap_seconds * rate)
    silence = array("h", [0]) * (gap_frames * audio[0].channels)
    report = {
        "schemaVersion": 1,
        "method": "full-file AC RMS, pooled channel power after subtracting each channel mean; silence and tails included",
        "matching": "attenuation only" if target_ac_rms_dbfs is None else "explicit AC RMS target",
        "requestedAcRmsDbfs": target_ac_rms_dbfs,
        "targetAcRms": target,
        "targetAcRmsDbfs": _dbfs(target),
        "peakHeadroomDb": peak_headroom_db,
        "peakLimit": peak_limit,
        "sampleRate": rate,
        "channels": audio[0].channels,
        "gapFrames": gap_frames,
        "gapSeconds": gap_frames / rate,
        "comparison": {"path": str(comparison_path), "frames": 2 * frames + gap_frames, "durationSeconds": (2 * frames + gap_frames) / rate},
        "segments": [
            {"label": "A", "startFrame": 0, "endFrame": frames},
            {"label": "silence", "startFrame": frames, "endFrame": frames + gap_frames},
            {"label": "B", "startFrame": frames + gap_frames, "endFrame": 2 * frames + gap_frames},
        ],
        "inputs": [],
        "listeningReview": None,
    }
    for index, label in enumerate(("A", "B")):
        report["inputs"].append({
            "label": label,
            "path": str(sources[index]),
            "sha256": audio[index].sha256,
            "original": measurements[index],
            "gain": gains[index],
            "gainDb": 20 * math.log10(gains[index]),
            "matched": matched_metrics[index],
            "matchedCopy": str(matched_paths[index]) if individual_copies else None,
        })

    prefix.parent.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        # Exclusive creation preserves prior evidence even if a file appears after preflight.
        _write_wav(comparison_path, audio[0], [matched[0].samples, silence, matched[1].samples], created)
        report["comparison"]["sha256"] = hashlib.sha256(comparison_path.read_bytes()).hexdigest()
        for path, value in zip(matched_paths, matched):
            _write_wav(path, value, [value.samples], created)
        with manifest_path.open("x") as output:
            created.append(manifest_path)
            output.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return report


def prepare_window_comparison(a_path, b_path, prefix, *, start_seconds, end_seconds, gap_seconds=0.5):
    """Copy one common PCM window at unity gain, rounding endpoints to frames.

    Full input lengths may differ; both must contain the complete selected frame
    range. Start is inclusive; end is exclusive. Rail samples, DC and silence remain intact.
    """
    _require(math.isfinite(start_seconds) and math.isfinite(end_seconds) and 0 <= start_seconds < end_seconds,
             "Window bounds must be finite, nonnegative and increasing")
    _require(math.isfinite(gap_seconds) and 0 <= gap_seconds <= 60,
             "Gap must be finite and between zero and 60 seconds")
    sources = [Path(path).resolve() for path in (a_path, b_path)]
    prefix = Path(prefix).resolve()
    comparison_path = Path(str(prefix) + ".ab.wav")
    manifest_path = Path(str(prefix) + ".comparison.json")
    for path in (comparison_path, manifest_path):
        _require(path.resolve() not in sources, f"Output would overwrite a source WAV: {path}")
        _require(not path.exists() and not path.is_symlink(), f"Output already exists: {path}")
    audio = [read_pcm16(path) for path in sources]
    rate, channels = audio[0].sample_rate, audio[0].channels
    _require((rate, channels) == (audio[1].sample_rate, audio[1].channels),
             "A and B must have the same sample rate and channels")
    scaled_bounds = [seconds * rate for seconds in (start_seconds, end_seconds)]
    _require(all(math.isfinite(value) for value in scaled_bounds), "Window exceeds the source frame range")
    first, last = map(round, scaled_bounds)
    _require(first < last, "Selected window is empty after rounding to frames")
    _require(all(last <= value.frames for value in audio), "Both sources must contain the complete selected window")
    frames = last - first
    windows = [Pcm16(rate, channels, frames, value.samples[first * channels:last * channels], "") for value in audio]
    gap_frames = round(gap_seconds * rate)
    silence = array("h", [0]) * (gap_frames * channels)
    report = {
        "schemaVersion": 1,
        "method": "same frame window from each input; original PCM preserved at unity gain",
        "matching": "none",
        "normalization": False,
        "requestedWindowSeconds": [start_seconds, end_seconds],
        "window": {"startFrame": first, "endFrame": last, "frames": frames,
                   "startSeconds": first / rate, "endSeconds": last / rate, "durationSeconds": frames / rate},
        "sampleRate": rate,
        "channels": channels,
        "gapFrames": gap_frames,
        "gapSeconds": gap_frames / rate,
        "comparison": {"path": str(comparison_path), "frames": 2 * frames + gap_frames,
                       "durationSeconds": (2 * frames + gap_frames) / rate},
        "segments": [
            {"label": "A", "startFrame": 0, "endFrame": frames},
            {"label": "silence", "startFrame": frames, "endFrame": frames + gap_frames},
            {"label": "B", "startFrame": frames + gap_frames, "endFrame": 2 * frames + gap_frames},
        ],
        "inputs": [{"label": label, "path": str(path), "sha256": original.sha256,
                    "originalFrames": original.frames, "window": measure_pcm(window), "gain": 1, "gainDb": 0}
                   for label, path, original, window in zip(("A", "B"), sources, audio, windows)],
        "listeningReview": None,
    }
    prefix.parent.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        _write_wav(comparison_path, audio[0], [windows[0].samples, silence, windows[1].samples], created)
        report["comparison"]["sha256"] = hashlib.sha256(comparison_path.read_bytes()).hexdigest()
        with manifest_path.open("x") as output:
            created.append(manifest_path)
            output.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return report
