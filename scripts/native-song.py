"""Build and verify a complete native SID-Wizard arrangement without a display."""

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import wave

from audio_comparison import Pcm16, inspect_wav, measure_pcm, read_pcm16
from psid_audit import audit_psid
from verify_player import require


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as output:
        output.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def frame_states(writes, ticks):
    registers = [0] * 25
    for write in writes:
        if write["phase"] == "init":
            registers[write["address"] - 0xd400] = write["value"]
    frames, cursor = [], 0
    playback = [write for write in writes if write["phase"] == "play"]
    for tick in range(ticks):
        while cursor < len(playback) and playback[cursor]["tick"] == tick:
            write = playback[cursor]
            registers[write["address"] - 0xd400] = write["value"]
            cursor += 1
        frames.append(registers.copy())
    return frames


class NativeObserver:
    def __init__(self, labels):
        self.labels = {name: labels[f"extraPlayer:player:{name}"] for name in ("CHNOTEC", "CURPTN", "STRTSND", "DPITCH", "CURINS", "INIPTN", "SEQPOS", "SEQFXL2")}
        self.pointer = labels["PLAYERZP"]
        self.cells, self.starts, self.sequence_reads = [], [], []
        self.stopped = set()

    def __call__(self, cpu, memory):
        pc, labels = cpu.pc, self.labels
        if pc not in (labels["CHNOTEC"], labels["STRTSND"], labels["INIPTN"], labels["SEQFXL2"] + 3):
            return
        require(cpu.x in (0, 7, 14), "Native observer encountered an unsupported channel layout")
        voice = cpu.x // 7
        if pc == labels["INIPTN"] and memory.phase == "init":
            self.sequence_reads.append({"voice": voice, "tick": None, "entry": cpu.a})
        if memory.phase != "play":
            return
        if pc == labels["CHNOTEC"]:
            pointer = memory.data[self.pointer] | memory.data[self.pointer + 1] << 8
            address = (pointer + cpu.y) & 65535
            raw = memory.data[address]
            code = raw & 127
            if 1 <= code <= 0x5f or code == 0x7e:
                self.cells.append({"voice": voice, "tick": memory.tick, "pattern": memory.data[labels["CURPTN"] + cpu.x], "byteOffset": cpu.y, "noteCode": code, "instrument": memory.data[(address + 1) & 65535] & 127 if raw & 128 else None})
        elif pc == labels["STRTSND"]:
            self.starts.append({"voice": voice, "tick": memory.tick, "nativeNote": memory.data[labels["DPITCH"] + cpu.x], "instrument": memory.data[labels["CURINS"] + cpu.x]})
        elif pc == labels["SEQFXL2"] + 3:
            if cpu.a != 254 or voice not in self.stopped:
                self.sequence_reads.append({"voice": voice, "tick": memory.tick, "entry": cpu.a})
            if cpu.a == 254:
                self.stopped.add(voice)


def verify_driver_events(manifest, observer, frames):
    counts, last_notes, stop_ticks, off_reads, volume_reads = [], [], [], [], []
    for voice, part in enumerate(manifest["voices"]):
        expected_ending = [(entry["tick"], entry["entry"]) for entry in part["expectedSequenceEnding"]]
        require(expected_ending and expected_ending[-1] == (manifest["stopTick"], 254), "Invalid expected native sequence completion")
        expected_sequence = [(entry["tick"], entry["pattern"]) for entry in part["expectedPatternEntries"]] + expected_ending
        actual_sequence = [(entry["tick"], entry["entry"]) for entry in observer.sequence_reads if entry["voice"] == voice]
        require(actual_sequence[:len(expected_sequence)] == expected_sequence, f"Voice {voice + 1} sequence completion differs from the retained stop orderlist")
        repeated_volume = actual_sequence[len(expected_sequence):]
        require(all(tick > manifest["stopTick"] and entry == 160 and expected_ending == [(manifest["stopTick"], 160), (manifest["stopTick"], 254)] for tick, entry in repeated_volume), f"Voice {voice + 1} post-stop sequence completion differs from the declared volume-zero ending")
        volume_reads.append(len(repeated_volume))
        cell_fields = ("tick", "pattern", "byteOffset", "noteCode", "instrument")
        expected = [tuple(cell.get(field) for field in cell_fields) for cell in manifest["cellMap"] if cell["voice"] == voice]
        actual = [tuple(cell.get(field) for field in cell_fields) for cell in observer.cells if cell["voice"] == voice]
        require(actual[:len(expected)] == expected, f"Voice {voice + 1} native cell consumption differs from conversion expectations")
        terminal = expected[-1]
        require(terminal[0] == manifest["stopTick"] and terminal[3:] == (126, None), f"Voice {voice + 1} terminal cell consumption must be a plain gate-off")
        repeats = actual[len(expected):]
        require(all(cell[0] > manifest["stopTick"] and cell[1:] == terminal[1:] for cell in repeats), f"Voice {voice + 1} post-stop cell consumption differs from its terminal gate-off")
        off_reads.append(len(repeats))
        expected_starts = [(note["startTick"], note["nativeNote"], note["instrument"]) for note in part["notes"]]
        starts = [note for note in observer.starts if note["voice"] == voice]
        require([(note["tick"], note["nativeNote"], note["instrument"]) for note in starts] == expected_starts, f"Voice {voice + 1} discrete note start differs from its converted source notes")
        counts.append(len(starts))
        last_notes.append(starts[-1] if starts else None)
        stop_ticks.append(expected_sequence[-1][0])
    require(len(frames) > manifest["stopTick"] + 1, "Audit does not include post-stop calls")
    volume_clear_tick = manifest["stopVolumeClearTick"]
    require(volume_clear_tick == manifest["stopTick"], "Native volume clear tick must match the proven sequence stop call")
    require(all(not state[voice * 7 + 4] & 1 for state in frames[manifest["stopTick"]:] for voice in range(3)) and all(state[24] & 15 == 0 for state in frames[volume_clear_tick:]), "Native driver retains an active gate or master volume in post-stop calls")
    critical = []
    for note in manifest["criticalNotes"]:
        voice, tick = note["voice"], note["audibleCheckTick"]
        require(0 <= voice < 3 and 0 <= tick < manifest["stopTick"], "Invalid critical short note check position")
        state, base = frames[tick], voice * 7
        control = state[base + 4]
        word = state[base] | state[base + 1] << 8
        expected_word = round(440 * 2 ** ((note["midi"] - 69) / 12) * 2**24 / manifest["clockHz"])
        require(control & 1 and control & 0x70 and not control & 0x88 and abs(word - expected_word) <= 1, f"Voice {voice + 1} critical short note at tick {tick} lacks a gated full-pitch waveform: frequency {word}, expected {expected_word}, control ${control:02x}")
        critical.append({"voice": voice, "tick": tick, "midi": note["midi"], "frequencyWord": word, "expectedFrequencyWord": expected_word, "wordTolerance": 1, "control": control})
    return {"method": "Pinned Extra driver note-column reads, discrete sound-start state and orderlist reads; exact ticks and instrument selections", "noteCounts": counts, "lastNotes": last_notes, "stopTicks": stop_ticks, "stopVolumeClearTick": volume_clear_tick, "postStopOffReads": off_reads, "postStopVolumeReads": volume_reads, "postStopGatesAndVolumeClear": True, "criticalNotes": critical, "limitations": "Discrete source-note scheduling and selected short-note full-pitch register frames are verified; ADSR reattacks, vibrato, per-voice PCM audibility and musical quality are not established by this check."}


def audit_native(manifest_path, export_path, prefix, ticks):
    manifest = json.loads(Path(manifest_path).read_text())
    exported = json.loads(Path(export_path).read_text())
    native = Path(manifest["nativePath"])
    require(hashlib.sha256(native.read_bytes()).hexdigest() == manifest["nativeSha256"] == exported["sourceSha256"], "Native source differs from the conversion/export evidence")
    sid = Path(exported["sid"]).read_bytes()
    require(hashlib.sha256(sid).hexdigest() == exported["sidSha256"], "Exported SID differs from its retained report")
    require((exported["player"], exported["loadAddress"], exported["initAddress"], exported["playAddress"]) == ("Extra", 0x1000, 0x1000, 0x1003), "Native observer supports the pinned Extra player at $1000 only")
    label_bytes = (ROOT / ".tools/sid-wizard-exporter/exporter.labels").read_bytes()
    require(hashlib.sha256(label_bytes).hexdigest() == exported["build"]["labelsSha256"], "Native observer labels differ from the exporter build")
    labels = {name: int(value, 16) for value, name in re.findall(r"^al ([\da-fA-F]+) \.(.+)$", label_bytes.decode(), re.MULTILINE)}
    observer = NativeObserver(labels)
    audited, writes = audit_psid(sid, ticks, observer=observer)
    frames = frame_states(writes, ticks)
    paths = {key: Path(str(prefix) + suffix) for key, suffix in (("audit", ".audit.json"), ("writes", ".writes.json"), ("frames", ".frames.json"), ("nativeEvents", ".native-events.json"), ("schedule", ".schedule.json"))}
    for key, value in (("audit", audited), ("writes", writes), ("frames", frames), ("nativeEvents", {"cells": observer.cells, "starts": observer.starts, "sequenceReads": observer.sequence_reads})):
        write_json(paths[key], value)
    verified = verify_driver_events(manifest, observer, frames)
    write_json(paths["schedule"], verified)
    return verified


def write_excerpt(source, destination, start_seconds, seconds):
    require(math.isfinite(start_seconds) and start_seconds >= 0 and math.isfinite(seconds) and seconds > 0, "Excerpt position/duration must be finite, nonnegative and positive respectively")
    audio = read_pcm16(source)
    start, count = round(start_seconds * audio.sample_rate), round(seconds * audio.sample_rate)
    require(count > 0 and start + count <= audio.frames, "Excerpt must fit wholly inside the full render")
    samples = audio.samples[start * audio.channels:(start + count) * audio.channels]
    if sys.byteorder != "little":
        samples.byteswap()
    with Path(destination).open("xb") as file:
        with wave.open(file, "wb") as output:
            output.setparams((audio.channels, 2, audio.sample_rate, 0, "NONE", "not compressed"))
            output.writeframes(samples.tobytes())
    return {"path": str(Path(destination).resolve()), "sourceStartFrame": start, "frames": count, "durationSeconds": count / audio.sample_rate, "sha256": hashlib.sha256(Path(destination).read_bytes()).hexdigest(), "gain": 1}


def run_song(recipe, output, renderer=ROOT / ".local/bin/render-sid", excerpt_start=0, excerpt_seconds=20):
    require(math.isfinite(excerpt_start) and excerpt_start >= 0 and math.isfinite(excerpt_seconds) and excerpt_seconds > 0, "Excerpt position/duration must be finite, nonnegative and positive respectively")
    recipe, output, renderer = Path(recipe).resolve(), Path(output).resolve(), Path(renderer).resolve()
    require(not output.exists(), "Native song output already exists; choose a fresh directory to preserve evidence")
    require(recipe.is_file() and renderer.is_file(), "Recipe and documented SID renderer must exist")
    output.mkdir(parents=True)
    converter = load_script("arrange-sidwizard")
    manifest = converter.arrange(recipe, output / "conversion")
    manifest_path = output / "conversion.json"
    write_json(manifest_path, manifest)
    exporter = load_script("export-sidwizard")
    exported = exporter.export_module(manifest["nativePath"], output / "export", title=manifest["title"], author=manifest["author"], released=manifest["released"])
    export_path = output / "export.json"
    write_json(export_path, exported)
    prefix = output / "native-song"
    seconds = (manifest["totalTicks"] + 1) / manifest["ticksPerSecond"] + 1
    require(0 < seconds <= 600, "Native song plus verification tail must fit the renderer's 600-second limit")
    require(excerpt_start + excerpt_seconds <= seconds, "Excerpt must fit wholly inside the planned full render")
    ticks = math.ceil(seconds * manifest["ticksPerSecond"]) + 1
    print(f"Checking {ticks} native player calls and the complete converted schedule", flush=True)
    subprocess.run([sys.executable, str(Path(__file__).resolve()), "audit", str(manifest_path), str(export_path), str(prefix), "--ticks", str(ticks)], check=True, timeout=120)
    wav = Path(str(prefix) + ".wav")
    command = [str(renderer), exported["sid"], str(wav), str(seconds)]
    print(f"Rendering complete native song: {seconds:.3f} seconds", flush=True)
    renderer_report = {"command": command, "executableSha256": hashlib.sha256(renderer.read_bytes()).hexdigest(), "deadlineSeconds": 120}
    try:
        rendered = subprocess.run(command, check=False, timeout=120, capture_output=True, text=True)
    except subprocess.TimeoutExpired as error:
        renderer_report.update(timedOut=True, returnCode=None, stdout=error.stdout.decode(errors="replace") if isinstance(error.stdout, bytes) else error.stdout or "", stderr=error.stderr.decode(errors="replace") if isinstance(error.stderr, bytes) else error.stderr or "")
        write_json(Path(str(prefix) + ".render.json"), renderer_report)
        raise
    renderer_report.update(timedOut=False, returnCode=rendered.returncode, stdout=rendered.stdout.strip(), stderr=rendered.stderr.strip())
    write_json(Path(str(prefix) + ".render.json"), renderer_report)
    if rendered.returncode != 0:
        raise subprocess.CalledProcessError(rendered.returncode, command, rendered.stdout, rendered.stderr)
    pcm = inspect_wav(wav)
    require(pcm["sampleRate"] == 44100 and pcm["channels"] == 1 and pcm["frames"] == round(seconds * 44100), "Renderer did not produce the complete mono PCM16 duration at 44100 Hz")
    require(pcm["clippedSamples"] == 0 and pcm["acRms"] > 1, "Full native render is clipped or silent")
    audio = read_pcm16(wav)
    tail_frames = round(audio.sample_rate * 0.5)
    tail = Pcm16(audio.sample_rate, audio.channels, tail_frames, audio.samples[-tail_frames * audio.channels:], "")
    ending = measure_pcm(tail)
    require(ending["acRms"] < 16, "Full native render does not have a quiet ending")
    excerpt = write_excerpt(wav, output / "native-song.excerpt.wav", excerpt_start, excerpt_seconds)
    report = {"schemaVersion": 1, "evidenceLevel": "rendered experiment", "listeningReview": None, "conversionManifest": str(manifest_path), "exportReport": str(export_path), "audit": json.loads(Path(str(prefix) + ".audit.json").read_text()), "schedule": json.loads(Path(str(prefix) + ".schedule.json").read_text()), "pcm": pcm, "endingAcRms": ending["acRms"], "excerpt": excerpt, "renderer": renderer_report, "evidenceFiles": {key: str(Path(str(prefix) + suffix)) for key, suffix in (("writes", ".writes.json"), ("frames", ".frames.json"), ("nativeEvents", ".native-events.json"))}, "limitations": "RAM-only CPU scheduling evidence and emulated PCM health; first-frame audible pitch and ADSR equivalence are limited by the native driver, no hardware or listening approval is claimed."}
    write_json(output / "verification.json", report)
    print(f"Verified full native schedule and render: {output / 'verification.json'}", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="convert, export, audit and render a native song in a fresh directory")
    build.add_argument("recipe", type=Path)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--renderer", type=Path, default=ROOT / ".local/bin/render-sid")
    build.add_argument("--excerpt-start", type=float, default=0)
    build.add_argument("--excerpt-seconds", type=float, default=20)
    audit = commands.add_parser("audit", help="verify native note/pattern consumption from a conversion and export manifest")
    audit.add_argument("manifest", type=Path)
    audit.add_argument("export", type=Path)
    audit.add_argument("prefix", type=Path)
    audit.add_argument("--ticks", type=int, required=True)
    args = parser.parse_args()
    if args.command == "build":
        run_song(args.recipe, args.output, args.renderer, args.excerpt_start, args.excerpt_seconds)
    else:
        audit_native(args.manifest, args.export, args.prefix, args.ticks)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Native song workflow failed: {error}", file=sys.stderr)
        raise SystemExit(1)
