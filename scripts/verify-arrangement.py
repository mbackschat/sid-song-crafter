import argparse
from array import array
import bisect
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import wave

from verify_player import verify_callable


ROOT = Path(__file__).resolve().parents[1]
RATE = 44100
# MOS 6581 specification Table 2 defines release times at 1 MHz; skills/c64-sid/references/sid-chip-spec.md preserves the table.
RELEASE_SECONDS = (0.006, 0.024, 0.048, 0.072, 0.114, 0.168, 0.204, 0.240, 0.300, 0.750, 1.5, 2.4, 3, 9, 15, 24)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def expected_frequency(midi):
    return 440 * 2 ** ((midi - 69) / 12)


def ac_rms(samples):
    mean = sum(samples) / len(samples)
    return math.sqrt(max(0, sum(value * value for value in samples) / len(samples) - mean * mean))


def read_pcm(path):
    with wave.open(str(path), "rb") as wav:
        require((wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, RATE), "WAV must be mono PCM16 at 44100 Hz")
        samples = array("h", wav.readframes(wav.getnframes()))
    if sys.byteorder != "little":
        samples.byteswap()
    return samples


def verify_pcm_health(samples, rate, ending_rms_limit=10):
    require(len(samples) >= round(0.2 * rate), "WAV is too short to check its ending")
    peak = max(abs(value) for value in samples)
    clipped = sum(value in (-32768, 32767) for value in samples)
    active_rms = ac_rms(samples)
    ending_rms = ac_rms(samples[-round(0.2 * rate):])
    require(active_rms > 100, "PCM contains no substantial audio")
    require(clipped == 0, "PCM contains hard clipping")
    require(ending_rms < ending_rms_limit, f"PCM ending is not silent: AC RMS {ending_rms:.3f}")
    return {"samples": len(samples), "sampleRate": rate, "durationSeconds": len(samples) / rate, "peak": peak, "clippedSamples": clipped, "acRms": active_rms, "endingAcRms": ending_rms, "endingAcRmsLimit": ending_rms_limit}


def verify_register_trace(manifest, path):
    rows = [(int(line.split("\t")[0]) / 1000, bytes.fromhex(line.split("\t")[1])) for line in path.read_text().splitlines()[1:]]
    require(rows and all(len(state) >= 25 for _, state in rows), "SID register trace is missing or truncated")
    voices = manifest["voices"]
    notes = [[event for event in voice["events"] if event["midi"] is not None] for voice in voices]
    require(any(notes), "Arrangement contains no pitched events")
    observed = [[] for _ in voices]
    previous = bytes(32)
    for timestamp, state in rows:
        for voice in range(len(voices)):
            base = voice * 7
            word = state[base] | state[base + 1] << 8
            if state[base + 4] & 1 and (not previous[base + 4] & 1 or state[base:base + 2] != previous[base:base + 2]):
                observed[voice].append((timestamp, word))
        previous = state
    starts = [timestamp for part in observed for timestamp, _ in part]
    require(starts, "SID trace contains no voice onsets")
    first_tick = min(event["startTick"] for part in notes for event in part)
    offset = min(starts) - first_tick / manifest["ticksPerSecond"]
    initial = bytearray(25)
    initial[24] = manifest["volume"]
    for voice, part in enumerate(voices):
        instrument = part["instrument"]
        base = voice * 7
        width = instrument.get("pulseWidth", 0x800)
        initial[base + 2:base + 7] = bytes((width & 255, width >> 8, instrument["waveform"], instrument["attackDecay"], instrument["sustainRelease"]))
        for event in notes[voice]:
            word = round(expected_frequency(event["midi"]) * 2**24 / manifest["clockHz"])
            require(event["frequencyWord"] == word, f"voice {voice + 1} manifest frequency disagrees with MIDI {event['midi']}")
    ticks, states, prefixes = [-1], [bytes(initial)], [[bytes(initial)]]
    state = initial
    for write in manifest["writes"]:
        address = write["address"] - 0xd400
        require(0 <= address <= 24, "Manifest write is outside SID registers")
        if ticks[-1] == write["tick"]:
            state[address] = write["value"]
            states[-1] = bytes(state)
            prefixes[-1].append(bytes(state))
        else:
            ticks.append(write["tick"])
            prefixes.append([bytes(state)])
            state[address] = write["value"]
            states.append(bytes(state))
            prefixes[-1].append(bytes(state))
    for timestamp, actual in rows:
        tick = round((timestamp - offset) * manifest["ticksPerSecond"])
        # A cycle-bounded libsidplayfp call can stop between stores; docs/fuer-elise-validation.md records the observed tick-783 example.
        candidates = []
        for candidate in (tick - 1, tick, tick + 1):
            index = max(0, bisect.bisect_right(ticks, candidate) - 1)
            candidates.extend(prefixes[index] if ticks[index] == candidate else [states[index]])
        if actual[:25] not in candidates:
            expected = states[max(0, bisect.bisect_right(ticks, tick) - 1)]
            for voice in range(len(voices)):
                base = voice * 7
                require(actual[base:base + 2] == expected[base:base + 2], f"voice {voice + 1} frequency disagrees with scheduled SID writes near tick {tick}")
                require(actual[base + 2:base + 7] == expected[base + 2:base + 7], f"voice {voice + 1} control or instrument disagrees with scheduled SID writes near tick {tick}")
            raise ValueError(f"SID global registers disagree with scheduled writes near tick {tick}")
    require(all(not rows[-1][1][voice * 7 + 4] & 1 for voice in range(len(voices))), "SID trace ends with an active gate")
    require(rows[-1][1][24] & 15 == 0, "SID trace ends with nonzero master volume")
    return {"snapshots": len(rows), "noteCounts": [len(part) for part in notes], "observableOnsetCounts": [len(part) for part in observed], "startOffsetSeconds": offset, "frameTolerance": 1}


def verify_pitch_anchors(manifest, samples, offset):
    anchors = []
    sounding = []
    for part in manifest["voices"]:
        release = RELEASE_SECONDS[part["instrument"]["sustainRelease"] & 15] * 1_000_000 / manifest["clockHz"]
        sounding.append([
            (event["startTick"] / manifest["ticksPerSecond"], event["gateOffTick"] / manifest["ticksPerSecond"] + release + 0.1)
            for event in part["events"] if event["midi"] is not None
        ])
    for voice, part in enumerate(manifest["voices"]):
        for event in part["events"]:
            if event["midi"] is None:
                continue
            start = event["startTick"] / manifest["ticksPerSecond"] + 0.08
            end = event["gateOffTick"] / manifest["ticksPerSecond"] - 0.04
            if end - start < 0.1:
                continue
            overlap = any(
                other_start < end and other_end > start
                for other_voice, intervals in enumerate(sounding) if other_voice != voice
                for other_start, other_end in intervals
            )
            if overlap:
                continue
            window = samples[round((offset + start) * RATE):round((offset + end) * RATE)]
            mean = sum(window) / len(window)
            crossings = [index for index in range(1, len(window)) if window[index - 1] <= mean < window[index]]
            require(len(crossings) >= 2, "Isolated pitch anchor contains no oscillation")
            measured = (len(crossings) - 1) * RATE / (crossings[-1] - crossings[0])
            expected = expected_frequency(event["midi"])
            require(abs(measured - expected) <= 3, f"voice {voice + 1} PCM pitch {measured:.2f} Hz disagrees with MIDI {event['midi']} ({expected:.2f} Hz)")
            anchors.append({"voice": voice, "midi": event["midi"], "startTick": event["startTick"], "expectedHz": expected, "measuredHz": measured})
            if len(anchors) == 12:
                return anchors
    return anchors


def memory_bytes(log, address, length):
    match = re.search(rf"^>C:{address:04x}\s+([^\n]+)", log, re.MULTILINE | re.IGNORECASE)
    require(match is not None, f"VICE did not inspect ${address:04x}")
    return bytes(int(value, 16) for value in match.group(1).split()[:length])


def verify_vice(manifest, prg, wav, prefix, executable, data, capture_audio):
    symbols = manifest["symbols"]
    monitor = Path(str(prefix) + ".vice.mon")
    monitor_log = Path(str(prefix) + ".vice-monitor.log")
    process_log = Path(str(prefix) + ".vice-run.log")
    monitor_log.unlink(missing_ok=True)
    require('"' not in str(prg) and "\n" not in str(prg), "PRG path cannot contain a quote or newline")
    monitor.write_text(f'loadbasic "{prg}" 0\nkeybuf run\\n\nuntil ${symbols["standalone"]:04x}\nr\nuntil ${symbols["standalone_return"]:04x}\nr\nm $0000 $0001\nm ${symbols["finished"]:04x} ${symbols["finished"]:04x}\nm ${symbols["ticks_left_low"]:04x} ${symbols["ticks_left_high"]:04x}\nm ${symbols["stream_read"] + 1:04x} ${symbols["stream_read"] + 2:04x}\nbank io\nm $d400 $d418\nbank cpu\nnext\nreturn\nr\nquit\n')
    command = [str(executable), "-config", "/dev/null", "-directory", str(data), "-pal", "+logcolorize", "-initbreak", "ready", "-monlogname", str(monitor_log), "-monlog", "-moncommands", str(monitor), "-limitcycles", str(math.ceil((manifest["durationSeconds"] + 10) * manifest["clockHz"]))]
    if capture_audio:
        command += ["+warp", "-sounddev", "wav", "-soundarg", str(wav), "-sidenginemodel", "resid8580", "-soundrate", str(RATE)]
    else:
        command += ["-warp", "+sound"]
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    env["XDG_CONFIG_HOME"] = str(prefix.parent / ".vice-config")
    env["XDG_STATE_HOME"] = str(prefix.parent / ".vice-state")
    for variable in ("XDG_CONFIG_HOME", "XDG_STATE_HOME"):
        (Path(env[variable]) / "vice").mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with process_log.open("w") as output:
        subprocess.run(command, env=env, stdout=output, stderr=subprocess.STDOUT, check=True, timeout=manifest["durationSeconds"] + 20 if capture_audio else 60)
    log = monitor_log.read_text(errors="replace")
    registers = [line.split() for line in log.splitlines() if line.startswith(".;")]
    require(len(registers) >= 3, "VICE did not reach the entry, return and caller")
    entry, returned, caller = registers[0], registers[1], registers[-1]
    require(int(entry[0][2:], 16) == symbols["standalone"] and int(returned[0][2:], 16) == symbols["standalone_return"], "VICE did not run the complete standalone wrapper")
    require(entry[4:7] == returned[4:7], "Standalone wrapper did not restore stack or CPU memory ports")
    require(0xa000 <= int(caller[0][2:], 16) < 0xc000, "Standalone RTS did not return to BASIC ROM")
    require(memory_bytes(log, symbols["finished"], 1) == b"\x01", "VICE player did not finish")
    require(memory_bytes(log, symbols["ticks_left_low"], 2) == b"\0\0", "VICE delay counter did not finish")
    require(int.from_bytes(memory_bytes(log, symbols["stream_read"] + 1, 2), "little") == symbols["event_stream_end"], "VICE stream cursor did not reach the complete arrangement ending")
    final_sid = memory_bytes(log, 0xd400, 25)
    require(all(final_sid[voice * 7 + 4] & 1 == 0 for voice in range(3)) and final_sid[24] & 15 == 0, "VICE SID did not finish silently")
    cycles = int(returned[-1]) - int(entry[-1])
    duration = cycles / manifest["clockHz"]
    require(abs(duration - manifest["durationSeconds"]) <= 0.06, f"VICE wrapper duration {duration:.3f}s disagrees with score duration {manifest['durationSeconds']:.3f}s")
    evidence = {"command": command, "elapsedWallSeconds": time.monotonic() - started, "playCycles": cycles, "playSeconds": duration, "finished": True, "returnedToBasic": True, "finalSidRegistersHex": final_sid.hex(), "monitorLog": str(monitor_log), "processLog": str(process_log)}
    if capture_audio:
        evidence["pcm"] = verify_pcm_health(read_pcm(wav), RATE, ending_rms_limit=32)
        require(abs(evidence["pcm"]["durationSeconds"] - (int(returned[-1]) / manifest["clockHz"])) <= 0.2, "VICE capture length disagrees with executed CPU cycles")
    return evidence


def main():
    parser = argparse.ArgumentParser(description="Render and verify an exported PAL three-voice SID arrangement and its standalone PRG.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--score", type=Path)
    parser.add_argument("--vice-audio", action="store_true", help="also capture the full PRG with VICE/reSID at normal emulation speed")
    parser.add_argument("--renderer", type=Path, default=ROOT / ".local/bin/render-sid")
    parser.add_argument("--vice", type=Path, default=ROOT / ".tools/vice-headless-3.9/build/src/x64sc")
    parser.add_argument("--vice-data", type=Path, default=Path("/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice"))
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    require(manifest_path.name.endswith(".events.json"), "Manifest filename must end with .events.json")
    prefix = manifest_path.with_name(manifest_path.name[:-len(".events.json")])
    verification_path = Path(str(prefix) + ".verification.json")
    verification_path.unlink(missing_ok=True)
    manifest = json.loads(manifest_path.read_text())
    sid, prg, wav = (Path(str(prefix) + extension) for extension in (".sid", ".prg", ".wav"))
    for path in (sid, prg, args.renderer, args.vice, args.vice_data):
        require(path.exists(), f"Required prerequisite is missing: {path}")
    seconds = manifest["durationSeconds"] + 1
    require(1 < seconds <= 600, "Arrangement plus verification tail must fit the renderer's 600-second limit")
    print(f"Rendering {sid.name}: {seconds:.3f} seconds", flush=True)
    callable_evidence = verify_callable(manifest, sid)
    subprocess.run([str(args.renderer), str(sid), str(wav), str(seconds)], check=True, timeout=60)
    samples = read_pcm(wav)
    require(len(samples) == round(seconds * RATE), "Renderer did not produce the exact requested sample count")
    registers = verify_register_trace(manifest, Path(str(wav) + ".registers.tsv"))
    evidence = {"manifest": str(manifest_path), "target": manifest["target"], "callablePlayer": callable_evidence, "pcm": verify_pcm_health(samples, RATE), "registers": registers, "pitchAnchors": verify_pitch_anchors(manifest, samples, registers["startOffsetSeconds"])}
    if args.score:
        source = args.score.resolve()
        evidence["score"] = {"path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
    print("Checking full PRG execution in headless VICE" + (" and capturing reSID audio" if args.vice_audio else " in warp mode"), flush=True)
    evidence["vice"] = verify_vice(manifest, prg, Path(str(prefix) + ".vice.wav"), prefix, args.vice.resolve(), args.vice_data.resolve(), args.vice_audio)
    verification_path.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"Verified {sum(registers['noteCounts'])} notes across three voices; evidence: {verification_path}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"Verification failed: {error}", file=sys.stderr)
        sys.exit(1)
