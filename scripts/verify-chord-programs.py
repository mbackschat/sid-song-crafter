"""Check sustained Extra chord cycles and their release in supplied native frames."""

import argparse
import hashlib
import json
from pathlib import Path

from verify_player import PAL_CLOCK, require


def verify_chords(manifest, frames, profiles, *, waveform, dwell):
    """Verify the explicit tempo-1 chord profile through held notes and rests.

    SID-Wizard 1.97 include/player.asm WFAJUMP enters SEWFARP directly: a jump
    target is written as waveform/control even when it is a delay row. The
    corrected profile therefore uses explicit waveform rows at its loop anchor.
    NGATEOF's PTNGATE=$fe must continue masking gate during every release cycle.
    """
    require(manifest.get("format") == "sidwizard-arrangement-manifest-v1" and manifest.get("clockHz") == PAL_CLOCK and manifest.get("rowTicks") == 1 and manifest.get("frameSpeed") == 1, "Unsupported chord study timing; require PAL Extra tempo-1 rows")
    require(len(manifest["voices"]) == 3 and frames and all(len(state) == 25 and all(type(value) is int and 0 <= value <= 255 for value in state) for state in frames), "Require complete single-SID 25-register frames")
    stop, clear = manifest["stopTick"], manifest["stopVolumeClearTick"]
    require(type(stop) is int and type(clear) is int and 0 <= stop <= clear < len(frames), "Frames must include the complete stop and volume-clear interval")
    require(waveform in (0x41, 0x51) and type(dwell) is int and 1 <= dwell <= 16, "Chord profile requires pulse or triangle+pulse and explicit dwell 1..16")
    require(profiles and all(intervals and all(type(interval) is int and -32 <= interval <= 32 for interval in intervals) for intervals in profiles.values()), "Provide selected instrument IDs and explicit relative pitch sequences")
    observed = {identity: 0 for identity in profiles}
    checked = []
    for voice, part in enumerate(manifest["voices"]):
        base, notes = voice * 7, part["notes"]
        for index, note in enumerate(notes):
            identity = note["instrumentId"]
            if identity not in profiles:
                continue
            observed[identity] += 1
            start, off = note["startTick"], note["nativeGateOffTick"]
            following = notes[index + 1]["startTick"] if index + 1 < len(notes) else len(frames)
            require(type(start) is int and type(off) is int and 0 <= start < off < following <= len(frames) and off < stop, f"{identity}: incomplete or overlapping chord interval")
            body = start + 1
            intervals = profiles[identity]
            cycle = len(intervals) * dwell
            require(off - body >= 2 * cycle, f"{identity}: need at least two complete held cycles")
            require(frames[start][base + 4] == 0x09, f"{identity}: unsupported onset profile; require TEST09 before the full-pitch body")
            for tick in range(body, following):
                state = frames[tick]
                control = state[base + 4]
                released = tick >= off
                require(not released or not control & 1, f"{identity}: gate reopened during release/rest at tick {tick}")
                if tick >= stop:
                    continue
                expected_control = waveform & 0xfe if released else waveform
                require(control == expected_control, f"{identity}: waveform differs at tick {tick}: ${control:02x}, expected ${expected_control:02x}")
                midi = note["midi"] + intervals[((tick - body) // dwell) % len(intervals)]
                require(type(midi) is int and 12 <= midi <= 106, f"{identity}: chord pitch is outside the native note range")
                expected = round(440 * 2 ** ((midi - 69) / 12) * 2**24 / PAL_CLOCK)
                actual = state[base] | state[base + 1] << 8
                require(abs(actual - expected) <= 1, f"{identity}: pitch/order/dwell differs at tick {tick}: word {actual}, expected {expected} +/-1")
            checked.append({"instrumentId": identity, "voice": voice + 1, "noteIndex": index, "carrierMidi": note["midi"], "startTick": start, "bodyStartTick": body, "gateOffTick": off, "heldFrames": off - body, "completeHeldCycles": (off - body) // cycle, "releaseAndRestFrames": following - off})
    require(all(count for count in observed.values()), "No observed notes for selected instruments: " + ", ".join(identity for identity, count in observed.items() if not count))
    require(all(not state[voice * 7 + 4] & 1 for state in frames[stop:] for voice in range(3)), "Gate remains active after stop")
    require(all(state[24] & 15 == 0 for state in frames[clear:]), "Master volume is not zero after the declared volume-clear tick")
    return {"schemaVersion": 1, "profile": "Single-SID PAL Extra tempo-1 sustained chord; TEST09 onset, body +1, explicit waveform loop anchor", "waveform": waveform, "dwellTicks": dwell, "relativePitchSequences": profiles, "wordTolerance": 1, "checkedNotes": len(checked), "notes": checked, "postStopGatesClear": True, "postStopVolumeZero": True, "limitations": "Checks supplied final-per-call register frames, not binary/frame provenance, bus timing, ADSR amplitude, PCM audibility or musical quality. Requires two complete held cycles per selected note; intentionally finite bursts and other onset profiles need different checks."}


def parse_profiles(values):
    profiles = {}
    for value in values:
        identity, separator, pitches = value.partition("=")
        require(separator and identity and identity not in profiles, "Use unique --instrument ID=0,3,7 arguments")
        profiles[identity] = [int(pitch) for pitch in pitches.split(",")]
    return profiles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("frames", type=Path)
    parser.add_argument("--instrument", action="append", required=True, help="selected instrument ID and ordered relative pitch sequence, e.g. chord-minor=0,3,7")
    parser.add_argument("--waveform", type=lambda value: int(value, 16), required=True, help="41 or 51 hexadecimal, including gate")
    parser.add_argument("--dwell", type=int, required=True, help="PAL calls per tone")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(args.output.resolve() not in (args.manifest.resolve(), args.frames.resolve()), "Output must not overwrite an input")
    require(not args.output.exists() and not args.output.is_symlink(), "Choose a fresh verification output")
    manifest_data, frame_data = args.manifest.read_bytes(), args.frames.read_bytes()
    report = verify_chords(json.loads(manifest_data), json.loads(frame_data), parse_profiles(args.instrument), waveform=args.waveform, dwell=args.dwell)
    report["inputs"] = {name: {"path": str(path.resolve()), "sha256": hashlib.sha256(data).hexdigest()} for name, path, data in (("manifest", args.manifest, manifest_data), ("frames", args.frames, frame_data))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2, allow_nan=False)
        file.write("\n")
    print(f"Verified {report['checkedNotes']} sustained chord notes: {args.output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f"Chord verification failed: {error}")
