"""Run hash-pinned PWM-freeze and filter-bypass experiments on DRAX's bass."""

import argparse
from collections import Counter
from enum import Enum
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from audio_comparison import inspect_wav, prepare_comparison
from psid_audit import audit_psid
from verify_player import require


SOURCE_SHA256 = "ea6b7eba46844d399e415368eae86c3ddf03bd9041ecba93e7bb53b384daa2a1"
PLAY_CALLS = 151
RENDER_SECONDS = 3
DEADLINE_SECONDS = 120


class Variant(str, Enum):
    ORIGINAL = "original"
    NO_PWM = "no-pwm"
    FILTER_BYPASS = "filter-bypass"


def native_helpers():
    spec = importlib.util.spec_from_file_location("drax_bass_native_helpers", ROOT / "scripts/native-song.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as output:
        output.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def payload_offset(data, address):
    require(len(data) >= 0x7c and data[:4] == b"PSID", "Patch requires a complete PSID payload")
    start = int.from_bytes(data[6:8], "big")
    require(0x7c <= start < len(data), "Invalid PSID payload offset")
    load = int.from_bytes(data[8:10], "big")
    if load == 0:
        require(start + 2 < len(data), "Missing embedded PSID payload load address")
        load = int.from_bytes(data[start:start + 2], "little")
        start += 2
    offset = start + address - load
    require(load <= address and start <= offset < len(data), "Patch address lies outside the PSID payload")
    return offset


def make_variant(data, variant):
    variant = Variant(variant)
    require(sha256(data) == SOURCE_SHA256, "DRAX source SHA-256 differs from the pinned reference")
    preconditions = {
        Variant.ORIGINAL: [],
        Variant.NO_PWM: [(0x126b, bytes.fromhex("b9a51a")), (0x1aa5, bytes.fromhex("5006"))],
        Variant.FILTER_BYPASS: [(0x124b, bytes.fromhex("a9f18d17d4"))],
    }
    patches = {
        Variant.ORIGINAL: [],
        Variant.NO_PWM: [(0x1aa5, 0x50, 0), (0x1aa6, 0x06, 0xa6)],
        Variant.FILTER_BYPASS: [(0x124c, 0xf1, 0xf0)],
    }
    for address, expected in preconditions[variant]:
        offset = payload_offset(data, address)
        require(data[offset:offset + len(expected)] == expected, f"Patch precondition failed at ${address:04x}")
    result = bytearray(data)
    receipt = []
    for address, expected, replacement in patches[variant]:
        offset = payload_offset(data, address)
        require(data[offset] == expected, f"Patch precondition failed at ${address:04x}")
        result[offset] = replacement
        receipt.append({"cpuAddress": address, "fileOffset": offset, "from": expected, "to": replacement})
    return bytes(result), {"variant": variant.value, "sourceSha256": sha256(data), "sidSha256": sha256(result), "patches": receipt}


def verify_experiment(original, candidate, variant):
    variant = Variant(variant)
    require(variant != Variant.ORIGINAL, "Counterfactual verification requires a changed variant")
    require(len(original) == len(candidate), "SID write count differs from the reference")
    structure = lambda row: (row["phase"], row["tick"], row["address"])
    require([structure(row) for row in original] == [structure(row) for row in candidate], "SID write order or per-call count differs from the reference")
    ticks = {row["tick"] for row in original if row["phase"] == "play"}
    require(ticks == set(range(PLAY_CALLS)), "Experiment requires exactly 151 observed play calls")
    frames = native_helpers().frame_states(original, PLAY_CALLS)
    for tick in range(102, 138):
        width = frames[tick][2] | frames[tick][3] << 8
        expected = 0x6a0 + 0x50 * (tick - 102) if tick <= 129 else 0xf10 - 0x50 * (tick - 129)
        require(width == expected, f"Pinned reference PWM trajectory differs at tick {tick}")
        require(frames[tick][0:2] == [0xa9, 3] and frames[tick][4] == (0x41 if tick == 102 else 0x40), f"Pinned reference bass pitch/release differs at tick {tick}")
    allowed = {0xd402, 0xd403} if variant == Variant.NO_PWM else {0xd417}
    changed, cycle_deltas = [], []
    for before, after in zip(original, candidate):
        if before["value"] != after["value"]:
            require(before["address"] in allowed, f"Register change outside the selected experiment at ${before['address']:04x}")
            changed.append(after)
        if variant == Variant.FILTER_BYPASS and before["address"] == 0xd417:
            expected = 0xf0 if before["value"] == 0xf1 else before["value"]
            require(after["value"] == expected, "Filter routing must change only $f1 to $f0")
        delta = after["instructionStartCycle"] - before["instructionStartCycle"]
        if delta:
            cycle_deltas.append(delta)
    require(changed, "Counterfactual produced no register differences")
    result = {
        "variant": variant.value,
        "playCalls": PLAY_CALLS,
        "unchangedWriteOrderAndCounts": True,
        "perCallWriteCounts": [{"phase": phase, "tick": tick, "writes": count} for (phase, tick), count in Counter((row["phase"], row["tick"]) for row in original).items()],
        "changedAddresses": sorted({row["address"] for row in changed}),
        "changedWriteCount": len(changed),
        "unchangedPitchGatesAdsrAndCompanionRegisters": True,
        "referencePulseWidthTrajectory": {"startTick": 102, "endTick": 137, "initial": 0x6a0, "peak": 0xf10, "peakTick": 129, "final": 0xc90},
        "instructionCycleShifts": {"count": len(cycle_deltas), "minimumDelta": min(cycle_deltas) if cycle_deltas else None, "maximumDelta": max(cycle_deltas) if cycle_deltas else None},
        "busExactTimingClaimed": False,
        "limitations": "Ordered address/value writes and instruction-start cycles from RAM-only py65 calls; no SID bus timestamps, analogue state equality or listening verdict.",
    }
    if variant == Variant.NO_PWM:
        frozen = native_helpers().frame_states(candidate, PLAY_CALLS)
        require(all(state[2:4] == [0xa0, 6] for state in frozen[102:]), "Bass pulse width is not frozen at $6a0 through the observed body/release")
        result.update(frozenPulseWidth=0x6a0, frozenStartTick=102, frozenEndTick=150)
    else:
        require(all(state[23] == 0xf1 for state in frames[100:]), "Reference filter routing is not exclusively bass at resonance $f")
        result["bassFilterBypassed"] = True
    return result


def checked_process(command, receipt_path, *, executable_sha256=None):
    receipt = {"command": command, "deadlineSeconds": DEADLINE_SECONDS}
    if executable_sha256 is not None:
        receipt["executableSha256"] = executable_sha256
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=DEADLINE_SECONDS, check=False)
    except subprocess.TimeoutExpired as error:
        decode = lambda value: value.decode(errors="replace") if isinstance(value, bytes) else value or ""
        receipt.update(timedOut=True, returnCode=None, stdout=decode(error.stdout), stderr=decode(error.stderr))
        write_json(receipt_path, receipt)
        raise
    receipt.update(timedOut=False, returnCode=result.returncode, stdout=result.stdout.strip(), stderr=result.stderr.strip())
    write_json(receipt_path, receipt)
    require(result.returncode == 0, f"Experiment subprocess failed: {command[0]} (see {receipt_path})")
    return receipt


def run_study(source, output, renderer=ROOT / ".local/bin/render-sid"):
    source, output, renderer = Path(source).resolve(), Path(output), Path(renderer).resolve()
    require(not output.exists() and not output.is_symlink(), "Choose a fresh output directory; existing experiment evidence is preserved")
    data = source.read_bytes()
    variants = {variant: make_variant(data, variant) for variant in Variant}
    require(renderer.is_file(), "Configured SID renderer is required")
    renderer_sha = sha256(renderer.read_bytes())
    output = output.resolve()
    output.mkdir(parents=True)
    helpers = native_helpers()
    audits, writes, artifacts = {}, {}, {}
    print(f"Auditing three actual reference-program variants for {PLAY_CALLS} calls", flush=True)
    for variant, (sid_bytes, receipt) in variants.items():
        directory = output / variant.value
        directory.mkdir()
        sid = directory / "fuer-elise.sid"
        with sid.open("xb") as target:
            target.write(sid_bytes)
        write_json(directory / "patch.json", receipt)
        command = [sys.executable, str(ROOT / "scripts/psid_audit.py"), str(sid), "--ticks", str(PLAY_CALLS), "--output", str(directory / "audit.json")]
        checked_process(command, directory / "audit-command.json")
        audits[variant] = json.loads((directory / "audit.json").read_text())
        writes[variant] = json.loads((directory / "audit.writes.json").read_text())
        require(audits[variant]["sourceSha256"] == receipt["sidSha256"] and audits[variant]["sidModel"] == "MOS6581" and audits[variant]["playCalls"] == PLAY_CALLS, "Audit input/model/coverage differs from the variant contract")
        write_json(directory / "frames.json", helpers.frame_states(writes[variant], PLAY_CALLS))
        artifacts[variant.value] = {"sid": str(sid), "patch": receipt, "audit": audits[variant]}
    guards = {}
    for variant in (Variant.NO_PWM, Variant.FILTER_BYPASS):
        guards[variant.value] = verify_experiment(writes[Variant.ORIGINAL], writes[variant], variant)
        write_json(output / variant.value / "verification.json", guards[variant.value])
    print("Register experiment guards passed; rendering three-second bass solos", flush=True)
    for variant in Variant:
        directory = output / variant.value
        wav = directory / "bass.full.wav"
        command = [str(renderer), artifacts[variant.value]["sid"], str(wav), str(RENDER_SECONDS), "--voices", "1"]
        render = checked_process(command, directory / "render.json", executable_sha256=renderer_sha)
        require(sha256(renderer.read_bytes()) == renderer_sha, "Renderer changed during the controlled comparison")
        pcm = inspect_wav(wav)
        require(pcm["sampleRate"] == 44100 and pcm["channels"] == 1 and pcm["frames"] == RENDER_SECONDS * 44100, "Bass solo must contain the complete three-second mono PCM16 render")
        require(pcm["clippedSamples"] == 0 and pcm["acRms"] > 1, "Bass solo is clipped or silent")
        cuts = {}
        for label, start, seconds in (("context", 1.8, 1.2), ("exact", 2.02, 0.73)):
            cut = directory / f"bass.{label}.wav"
            cuts[label] = {**helpers.write_excerpt(wav, cut, start, seconds), "pcm": inspect_wav(cut)}
        sidecar = Path(str(wav) + ".registers.tsv")
        artifacts[variant.value].update(render=render, fullPcm=pcm, cuts=cuts, registerSidecarSha256=sha256(sidecar.read_bytes()) if sidecar.is_file() else None)
        write_json(directory / "audio.json", {key: artifacts[variant.value][key] for key in ("render", "fullPcm", "cuts", "registerSidecarSha256")})
    comparisons = {}
    for label in ("context", "exact"):
        metrics = [artifacts[variant.value]["cuts"][label]["pcm"] for variant in Variant]
        peak_limit = min(32766, math.floor(32767 * 10 ** (-1 / 20)))
        target = min([value["acRms"] for value in metrics] + [value["acRms"] * peak_limit / value["peak"] for value in metrics])
        target_dbfs = 20 * math.log10(target / 32768)
        comparisons[label] = {}
        for variant in (Variant.NO_PWM, Variant.FILTER_BYPASS):
            prefix = output / "comparisons" / f"{label}-{variant.value}"
            comparisons[label][variant.value] = prepare_comparison(artifacts[Variant.ORIGINAL.value]["cuts"][label]["path"], artifacts[variant.value]["cuts"][label]["path"], prefix, target_ac_rms_dbfs=target_dbfs, individual_copies=True)
        original_copies = [Path(comparisons[label][variant.value]["inputs"][0]["matchedCopy"]).read_bytes() for variant in (Variant.NO_PWM, Variant.FILTER_BYPASS)]
        require(original_copies[0] == original_copies[1], "Matched original differs between the two comparisons")
    require(source.read_bytes() == data, "Original archived source changed during the experiment")
    report = {
        "schemaVersion": 1,
        "evidenceLevel": "controlled reference-program experiment",
        "source": {"path": str(source), "sha256": SOURCE_SHA256, "preserved": True},
        "programBasis": {"pulseStepReadPc": 0x126b, "pulseStepAddress": 0x1aa5, "pulseStepShadow": 0x1553, "pulseAddPc": 0x12e3, "pulseSubtractPc": 0x12fc, "initialPulseAddress": 0x1aa6, "pulseShadowAddresses": [0x1559, 0x155c], "pulseSidStorePcs": [0x1421, 0x1427], "routingImmediateAddress": 0x124c, "routingSidStorePc": 0x124d},
        "playCalls": PLAY_CALLS,
        "renderSeconds": RENDER_SECONDS,
        "rendererSha256": renderer_sha,
        "toolSha256": {
            str(Path(__file__).resolve().relative_to(ROOT)): sha256(Path(__file__).read_bytes()),
            **{name: sha256((ROOT / "scripts" / name).read_bytes()) for name in ("psid_audit.py", "native-song.py", "audio_comparison.py", "render-sid.cpp")},
        },
        "variants": artifacts,
        "registerGuards": guards,
        "comparisons": comparisons,
        "listeningReview": None,
        "limitations": "Bass solos use diagnostic gate/waveform masking, not additive output stems. Muting other voices and bypassing the bass filter changes analogue input/state. Audits compare ordered register writes; PWM freeze can shift instruction-start cycles, so SID bus timing and analogue state are not held exact. The no-PWM intervention also changes bass pulse initialization before the selected body. Register sidecars retain original driver writes rather than internal diagnostic masks. Full initialization precedes every cut. No hardware fidelity or musical preference is claimed.",
    }
    write_json(output / "study.json", report)
    print(f"Verified experiment and retained audio: {output / 'study.json'}", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--renderer", type=Path, default=ROOT / ".local/bin/render-sid")
    args = parser.parse_args()
    run_study(args.source, args.output, args.renderer)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error))
