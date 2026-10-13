#!/usr/bin/env python3
"""Run a bounded, offline SongBench research trial on CPU or Apple Metal."""

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import time
import wave


ROOT = Path(__file__).resolve().parents[3]
DIMENSIONS = ("melody", "arrangement", "musicality", "vocal", "instrumental", "mixing", "structure")


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audio_info(path):
    with wave.open(str(path), "rb") as audio:
        frames, sample_rate, channels = audio.getnframes(), audio.getframerate(), audio.getnchannels()
        duration = frames / sample_rate
        if not 0 < duration <= 10:
            raise ValueError("Each WAV must contain more than zero and at most 10 seconds")
        if audio.getsampwidth() != 2 or channels not in (1, 2) or audio.getcomptype() != "NONE":
            raise ValueError("Expected mono or stereo 16-bit PCM WAV")
        if len(audio.readframes(frames)) != frames * channels * 2:
            raise ValueError("WAV PCM is truncated")
        return {"duration_seconds": duration, "frames": frames, "sample_rate": sample_rate, "channels": channels, "sha256": fingerprint(path)}


def verify_decoded_frames(frames, sample_rate, input_info):
    numerator = input_info["frames"] * sample_rate
    denominator = input_info["sample_rate"]
    minimum = numerator // denominator
    maximum = (numerator + denominator - 1) // denominator
    # Librosa 0.11.0 core/audio.py:633–635,681 applies fix_length to the
    # floating ratio's ceiling, which can exceed the rational ceiling by one.
    librosa_frames = math.ceil(input_info["frames"] * (float(sample_rate) / denominator))
    maximum = max(maximum, librosa_frames)
    if frames <= 0 or not minimum <= frames <= maximum:
        raise ValueError("Unexpected decoded frame count after resampling")


def load_cases(manifest):
    cases = json.loads(manifest.read_text())["cases"]
    if not 1 <= len(cases) <= 8:
        raise ValueError("Trial must contain between one and eight cases")
    ids = [case["id"] for case in cases]
    if len(set(ids)) != len(ids) or any(not re.fullmatch(r"[A-Za-z0-9_-]+", ident) for ident in ids):
        raise ValueError("Case ids must be unique and contain only letters, digits, underscores or hyphens")
    prepared = []
    for case in cases:
        path = (manifest.parent / case["wav"]).resolve()
        info = audio_info(path)
        if "audio_sha256" in case and case["audio_sha256"] != info["sha256"]:
            raise ValueError(f"Manifest audio fingerprint mismatch: {case['id']}")
        prepared.append({"id": case["id"], "wav": path, "input": info})
    return prepared


def worker(args):
    started = time.monotonic()
    input_info = audio_info(args.wav)
    os.environ["HF_HOME"] = str(args.muq.parent / "hf-cache")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ.pop("PYTORCH_ENABLE_MPS_FALLBACK", None)
    import librosa
    import torch
    from muq import MuQ
    from safetensors.torch import load_file

    torch.set_num_threads(4)
    torch.manual_seed(0)
    if args.device == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("PyTorch cannot access Apple Metal in this process")
    model_source = args.source / "model.py"
    spec = importlib.util.spec_from_file_location("songbench_upstream", model_source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    head = module.Generator(in_features=1024, ffd_hidden_size=4096, num_classes=7, attn_layer_num=4)
    head.load_state_dict(load_file(str(args.source / "ckpt/songbench.safetensors")), strict=True)
    head.to(args.device).eval()
    backbone = MuQ(json.loads((args.muq / "config.json").read_text()))
    backbone.load_state_dict(load_file(str(args.muq / "model.safetensors")), strict=True)
    backbone.to(args.device).eval()
    loaded = time.monotonic()
    waveform, sample_rate = librosa.load(args.wav, sr=24000, mono=True)
    verify_decoded_frames(len(waveform), sample_rate, input_info)
    with torch.inference_mode():
        features = backbone(torch.tensor(waveform).unsqueeze(0).to(args.device), output_hidden_states=True)["hidden_states"][6]
        values = head(features).squeeze(0).cpu().tolist()
    if len(values) != 7 or not all(1 <= value <= 10 for value in values):
        raise ValueError("SongBench returned invalid dimension scores")
    result = {"input": input_info, "device": args.device, "scores": dict(zip(DIMENSIONS, values)), "model_loading_seconds": loaded - started, "total_seconds": time.monotonic() - started, "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024), "preprocessing": {"loader": "librosa.load", "sample_rate": sample_rate, "decoded_frames": len(waveform), "mono": True, "gain": 1, "crop": None, "muq_hidden_layer": 6}, "wrapper_sha256": fingerprint(Path(__file__).resolve()), "model_source_sha256": fingerprint(model_source), "head_sha256": fingerprint(args.source / "ckpt/songbench.safetensors"), "muq_config_sha256": fingerprint(args.muq / "config.json"), "muq_sha256": fingerprint(args.muq / "model.safetensors")}
    if args.device == "mps":
        result["metal_memory_after_inference_bytes"] = {"current_allocated": torch.mps.current_allocated_memory(), "driver_allocated": torch.mps.driver_allocated_memory()}
    args.result.write_text(json.dumps(result, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, nargs="?")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--device", choices=("cpu", "mps"), default="cpu")
    parser.add_argument("--source", type=Path, default=ROOT / ".tools/songbench")
    parser.add_argument("--muq", type=Path, default=ROOT / ".local/audio-models/muq")
    parser.add_argument("--wav", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--result", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.wav:
        worker(args)
        return
    if not args.manifest or not args.output:
        parser.error("manifest and --output are required")
    cases = load_cases(args.manifest)
    args.output.mkdir(parents=True, exist_ok=False)
    for case in cases:
        result = args.output / (case["id"] + ".json")
        command = [sys.executable, str(Path(__file__).resolve()), "--wav", str(case["wav"]), "--result", str(result), "--device", args.device, "--source", str(args.source.resolve()), "--muq", str(args.muq.resolve())]
        with (args.output / (case["id"] + ".log")).open("w") as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=180, check=True)
        print(json.dumps({"id": case["id"], **json.loads(result.read_text())}), flush=True)


if __name__ == "__main__":
    main()
