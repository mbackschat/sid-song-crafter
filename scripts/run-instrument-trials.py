"""Export, audit, render and compare the original SID-Wizard instrument bank."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from audio_comparison import Pcm16, inspect_wav, measure_pcm, prepare_comparison, read_pcm16
from psid_audit import audit_psid
from verify_player import require


ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "songs/studies/sidwizard-repertoire/repertoire.json"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frame_states(writes, ticks):
    states = []
    registers = [0] * 25
    for row in writes:
        if row["phase"] == "init":
            registers[row["address"] - 0xd400] = row["value"]
    cursor = 0
    playback = [row for row in writes if row["phase"] == "play"]
    for tick in range(ticks):
        while cursor < len(playback) and playback[cursor]["tick"] == tick:
            row = playback[cursor]
            registers[row["address"] - 0xd400] = row["value"]
            cursor += 1
        states.append(registers.copy())
    return states


def check_technique(identity, reference, candidate):
    if identity == "pulse":
        widths = [sorted({state[2] | (state[3] & 15) << 8 for state in frames[12:84]}) for frames in (reference, candidate)]
        require(len(widths[0]) == 1 and len(widths[1]) > 1, "Pulse trial did not produce static versus moving pulse width")
        require([state[:2] for state in reference] == [state[:2] for state in candidate], "Pulse comparison unexpectedly changed the pitch trajectory")
        return {"pulseMotionObserved": True, "referenceWidths": widths[0], "candidateWidths": widths[1], "pitchTrajectoryUnchanged": True}
    if identity == "pluck":
        active = [tick for tick, state in enumerate(candidate[:24]) if state[4] & 0xf0 and state[4] & 1]
        require(len(active) > 1, "Pluck trial has no sustained attack/body window")
        attack = active[0]
        require(candidate[attack][4] == 0x21 and all(candidate[tick][4] == 0x11 for tick in active[1:]), "Pluck attack must be saw first, then triangle body")
        require(all(reference[tick][4] == 0x11 for tick in active), "Reference pluck must remain triangle through the attack/body window")
        require([state[:2] for state in reference[:24]] == [state[:2] for state in candidate[:24]], "Pluck attack unexpectedly changed pitch")
        return {"attackTransitionObserved": True, "attackTick": attack, "bodyTick": active[1], "checkedThroughTick": active[-1], "referenceWaveforms": [16], "candidateWaveforms": [32, 16]}
    if identity == "bass":
        active = [tick for tick, state in enumerate(candidate[:24]) if state[18] & 0xf0 and state[18] & 1]
        require(len(active) >= 5, "Bass trial has no recovery window")
        attack, body = active[:3], active[3:]
        require(all(candidate[tick][18] == 0x11 for tick in attack) and all(candidate[tick][18] == 0x41 for tick in body), "Bass attack must precede pulse recovery")
        words = [candidate[tick][14] | candidate[tick][15] << 8 for tick in attack]
        require(words[0] > words[1] > words[2], "Bass attack pitch must fall before recovery")
        for tick in body:
            actual = candidate[tick][14] | candidate[tick][15] << 8
            expected = reference[tick][14] | reference[tick][15] << 8
            require(abs(actual - expected) <= 1 and candidate[tick][18] == reference[tick][18], "Bass body did not recover the reference pitch and gate")
        return {"bassRecoveryObserved": True, "attackFrequencyWords": words, "bodyTick": body[0], "checkedThroughTick": body[-1], "bodyFrequencyToleranceWords": 1}
    return {"scope": "Combined arrangement comparison; isolated pulse, pluck and bass trials identify mechanisms."}


def run_trials(output, pair=None, renderer=ROOT / ".local/bin/render-sid"):
    output = Path(output).resolve()
    require(not output.exists(), "Trial output already exists; use a new directory to preserve previous evidence")
    bank = json.loads(BANK.read_text())
    pairs = [item for item in bank["pairs"] if pair is None or item["id"] == pair]
    require(pairs, f"Unknown trial pair: {pair}")
    selected = set(bank["studies"]) if pair is None else {item[key] for item in pairs for key in ("reference", "candidate")}
    require(Path(renderer).is_file(), "Build the documented SID renderer before running trials")
    exporter = load_script("export-sidwizard")
    generator = load_script("generate-native-instruments")
    native = BANK.parent / "native"
    for name, data in generator.generate(bank).items():
        require((native / name).read_bytes() == data, f"Native fixture differs from its retained recipe: {name}; regenerate explicitly or keep edits as a separate study")
    output.mkdir(parents=True)
    report = {"schemaVersion": 1, "bankSha256": hashlib.sha256(BANK.read_bytes()).hexdigest(), "evidenceLevel": "rendered experiment", "listeningReview": None, "studies": {}, "comparisons": {}, "techniques": {}}
    states = {}
    for name in sorted(selected):
        print(f"Export, audit and render: {name}", flush=True)
        exported = exporter.export_module(native / f"{name}.swm", output / name, title=name, author="Original SID study", released="2026")
        sid = Path(exported["sid"])
        audited, writes = audit_psid(sid.read_bytes(), bank["playTicks"])
        prefix = output / name / name
        Path(str(prefix) + ".audit.json").write_text(json.dumps(audited, indent=2) + "\n")
        Path(str(prefix) + ".writes.json").write_text(json.dumps(writes, separators=(",", ":")) + "\n")
        wav = Path(str(prefix) + ".wav")
        command = [str(Path(renderer).resolve()), str(sid), str(wav), str(bank["renderSeconds"])]
        subprocess.run(command, check=True, timeout=60, capture_output=True, text=True)
        pcm = inspect_wav(wav)
        require(pcm["frames"] == round(bank["renderSeconds"] * pcm["sampleRate"]), f"Incomplete render: {name}")
        require(pcm["clippedSamples"] == 0 and pcm["acRms"] > 1, f"Clipped or silent render: {name}")
        audio = read_pcm16(wav)
        tail_frames = round(audio.sample_rate * 0.5)
        tail = Pcm16(audio.sample_rate, audio.channels, tail_frames, audio.samples[-tail_frames * audio.channels:], "")
        ending = measure_pcm(tail)
        require(ending["acRms"] < 16, f"Trial has not reached a quiet ending: {name}")
        states[name] = frame_states(writes, bank["playTicks"])
        require(all(states[name][-1][voice * 7 + 4] & 1 == 0 for voice in range(3)), f"Trial ended with an open gate: {name}")
        report["studies"][name] = {"export": exported, "audit": audited, "pcm": pcm, "endingAcRms": ending["acRms"], "renderCommand": command}
    for comparison in pairs:
        identity, a, b = (comparison[key] for key in ("id", "reference", "candidate"))
        report["techniques"][identity] = check_technique(identity, states[a], states[b])
        report["comparisons"][identity] = prepare_comparison(report["studies"][a]["pcm"]["path"], report["studies"][b]["pcm"]["path"], output / "comparisons" / identity, individual_copies=True)
    (output / "trial.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Completed rendered experiments: {output / 'trial.json'}", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pair", choices=("pulse", "pluck", "bass", "mix"))
    parser.add_argument("--renderer", type=Path, default=ROOT / ".local/bin/render-sid")
    args = parser.parse_args()
    run_trials(args.output, args.pair, args.renderer)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Instrument trial failed: {error}", file=sys.stderr)
        raise SystemExit(1)
