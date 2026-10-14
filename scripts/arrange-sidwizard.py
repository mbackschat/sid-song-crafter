"""Project a retained three- or six-voice score onto an editable SID-Wizard tick grid."""

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re

from sid_clock import PAL_CLOCK, clock_spec


ROOT = Path(__file__).resolve().parents[1]
TICKS_PER_SECOND = PAL_CLOCK / (312 * 63)
PATTERN_ROWS = 248


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rounded(value):
    return math.floor(value + 0.5)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def instrument_encoder():
    specification = importlib.util.spec_from_file_location("native_instrument_encoder", ROOT / "scripts/generate-native-instruments.py")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module.instrument_bytes


def pack_pattern(cells):
    # SID-Wizard 1.97 depkptseq needs the decoded size to walk backwards through compressed data.
    unpacked_size = sum(len(cell) for cell in cells) + 1
    require(unpacked_size <= 249, "Tick pattern exceeds SID-Wizard's native unpacked byte limit")
    body = bytearray()
    offsets = {}
    index = 0
    while index < len(cells):
        if cells[index] != b"\x00":
            offsets[index] = len(body)
            body.extend(cells[index])
            index += 1
            continue
        end = index + 1
        while end < len(cells) and cells[end] == b"\x00":
            end += 1
        # SID-Wizard's packdepack.inc recognizes packed NOPs after a literal zero or another packed NOP.
        body.append(0)
        remaining = end - index - 1
        while remaining:
            count = min(9, remaining)
            body.append(0 if count == 1 else 0x70 + count - 2)
            remaining -= count
        index = end
    return bytes(body + bytes((unpacked_size, len(cells)))), offsets


def pattern_chunks(cells):
    start = 0
    while start < len(cells):
        end, unpacked_bytes = start, 0
        while end < len(cells) and end - start < PATTERN_ROWS and unpacked_bytes + len(cells[end]) <= 248:
            unpacked_bytes += len(cells[end])
            end += 1
        require(end > start, "Native row exceeds the editable pattern byte limit")
        yield start, cells[start:end]
        start = end


def select_sections(recipe, score):
    sections = recipe["sections"]
    require(sections, "Recipe requires a complete section schedule")
    names = {voice["name"] for voice in score["voices"]}
    previous = 0
    for section in sections:
        start, end = section["startBeat"], section["endBeat"]
        require(isinstance(start, (int, float)) and isinstance(end, (int, float)) and math.isfinite(start) and math.isfinite(end), "Section boundaries must be finite beats")
        require(math.isclose(start, previous, abs_tol=1e-9) and end > start, "Sections must cover the score without overlap or gaps")
        require(set(section["voices"]) == names, "Every section must select an instrument for each source voice")
        require(all(identity in recipe["instruments"] for identity in section["voices"].values()), "Section references an unknown instrument")
        previous = end
    require(math.isclose(previous, score["totalBeats"], abs_tol=1e-9), "Sections must cover the full source score")
    return sections


def gate_off_tick(start, duration):
    gap = 0 if duration == 1 else min(2, max(1, rounded(duration * 0.1)))
    return start + duration - gap


def retain_short_pitch(notes, voice, score_ticks):
    changes = []
    for index, note in enumerate(notes):
        if note["sourceDurationTicks"] != 1:
            continue
        end = note["startTick"] + 1
        following = notes[index + 1] if index + 1 < len(notes) else None
        if following is not None and following["startTick"] == end:
            require(following["durationTicks"] >= 3, "Cannot preserve the short note's full pitch without exceeding the following note's timing budget")
            following["startTick"] += 1
            following["durationTicks"] -= 1
        else:
            require(end + 1 <= (following["startTick"] if following else score_ticks), "Cannot preserve the short note's full pitch within the source phrase endpoint")
        note["durationTicks"] = 2
        adjusted = [note] + ([following] if following is not None and following["startTick"] == end + 1 and following["sourceStartTick"] == end else [])
        for item in adjusted:
            changes.append({
                "voice": voice, "eventIndex": item["eventIndex"], "midi": item["midi"],
                "sourceStartTick": item["sourceStartTick"], "startTick": item["startTick"],
                "sourceDurationTicks": item["sourceDurationTicks"], "durationTicks": item["durationTicks"],
                "startTickDelta": item["startTick"] - item["sourceStartTick"], "durationTicksDelta": item["durationTicks"] - item["sourceDurationTicks"],
                "reason": "The stock Extra player reaches the full note frequency on the second frame; reserve that sounding frame while retaining the following endpoint.",
            })
    return changes


def arrange(recipe_path, output_dir, *, clock=None):
    recipe_path = Path(recipe_path).resolve()
    output = Path(output_dir).resolve()
    require(not output.exists(), "Choose a fresh output directory; existing native workfiles are preserved")
    recipe_bytes = recipe_path.read_bytes()
    recipe = json.loads(recipe_bytes)
    require(recipe["format"] == "sidwizard-arrangement-v1", "Unsupported native arrangement recipe format")
    target = clock_spec(recipe.get("clock", "pal") if clock is None else clock)
    sid_model = recipe.get("sidModel", "MOS8580")
    require(sid_model in ("MOS6581", "MOS8580"), "Native SID model must be MOS6581 or MOS8580")
    sid_count = recipe.get("sidCount", 1)
    require(type(sid_count) is int and sid_count in (1, 2), "SID count must be 1 or 2")
    voice_count = sid_count * 3
    pattern_limit, instrument_limit = (100, 36) if sid_count == 1 else (105, 29)
    require(recipe.get("timingPolicy") == "retain-full-pitch", "Recipe must explicitly select the supported retain-full-pitch timing policy")
    require(all(re.fullmatch(r"[a-z][a-z0-9-]*", identity) for identity in recipe["instruments"]), "Native instrument id must be a simple lowercase alphanumeric/hyphen name")
    source = (recipe_path.parent / recipe["score"]).resolve()
    source_bytes = source.read_bytes()
    score = json.loads(source_bytes)
    require(len(score["voices"]) == voice_count and len({voice["name"] for voice in score["voices"]}) == voice_count, f"Native arrangement requires {voice_count} distinctly named source voices")
    bpm, total_beats = score["quarterBpm"], score["totalBeats"]
    require(isinstance(bpm, (int, float)) and math.isfinite(bpm) and bpm > 0 and isinstance(total_beats, (int, float)) and math.isfinite(total_beats) and total_beats > 0, "Source tempo and duration must be positive and finite")
    require(score.get("volume", 15) == 15, "Native trial currently retains the full-volume source contract only")
    source_tail = score.get("tailTicks", 25)
    require(type(source_tail) is int and source_tail > 0, "Source must include a positive PAL release tail")
    tail = max(1, rounded(source_tail * target.ticks_per_second / TICKS_PER_SECOND))
    rate = 60 / bpm * target.ticks_per_second
    pal_rate = 60 / bpm * TICKS_PER_SECOND
    score_ticks = rounded(total_beats * rate)
    total_ticks = score_ticks + tail
    row_count = total_ticks + 1
    sections = select_sections(recipe, score)
    encode_instrument = instrument_encoder()
    require(1 <= len(recipe["instruments"]) <= instrument_limit, f"Native recipe requires 1..{instrument_limit} instruments")
    identities = list(recipe["instruments"])
    instrument_numbers = {identity: index + 1 for index, identity in enumerate(identities)}
    instruments = {identity: encode_instrument(identity, recipe["instruments"][identity]) for identity in identities}
    short_limit = recipe.get("shortNoteMaxTicks", 0)
    require(type(short_limit) is int and short_limit >= 0, "shortNoteMaxTicks must be a nonnegative integer")
    short_instruments = recipe.get("shortNoteInstruments", {})
    require(all(identity in instruments for identity in short_instruments.values()), "Short-note mapping references an unknown instrument")
    patterns = []
    pattern_numbers = {}
    cell_map = []
    voices = []
    changes = []
    timing_changes = []
    for voice_index, voice in enumerate(score["voices"]):
        cells = [b"\x00"] * row_count
        notes = []
        events = voice["events"]
        previous_end = 0
        for event_index, event in enumerate(events):
            start_beat, duration_beats = event["startBeat"], event["durationBeats"]
            require(isinstance(start_beat, (int, float)) and isinstance(duration_beats, (int, float)) and math.isfinite(start_beat) and math.isfinite(duration_beats) and start_beat >= 0 and duration_beats > 0, "Source events require finite nonnegative onsets and positive durations")
            start = rounded(start_beat * rate)
            end = rounded((start_beat + duration_beats) * rate)
            require(start >= previous_end and end <= score_ticks and end > start, "Source voice has a note overlap, collision, or unrepresentable duration")
            previous_end = end
            if event["midi"] is None:
                continue
            midi = event["midi"]
            require(type(midi) is int and 12 <= midi <= 106, "Source pitch lies outside SID-Wizard's native note range")
            section = next(section for section in sections if section["startBeat"] <= start_beat < section["endBeat"])
            identity = section["voices"][voice["name"]]
            duration = end - start
            number = instrument_numbers[identity]
            native_note = midi - 11
            off = gate_off_tick(start, duration)
            notes.append({
                "eventIndex": event_index, "startBeat": start_beat, "durationBeats": duration_beats,
                "sourceStartTick": start, "sourceDurationTicks": duration, "sourceGateOffTick": off,
                "sourcePalDurationTicks": rounded((start_beat + duration_beats) * pal_rate) - rounded(start_beat * pal_rate),
                "startTick": start, "durationTicks": duration, "gateOffTick": off, "nativeGateOffTick": off,
                "midi": midi, "nativeNote": native_note, "instrument": number, "instrumentId": identity, "section": section["name"],
            })
        timing_changes.extend(retain_short_pitch(notes, voice_index, score_ticks))
        for note in notes:
            start, duration = note["startTick"], note["durationTicks"]
            short_duration = duration if target.name == "pal" else note["sourcePalDurationTicks"]
            if short_duration <= short_limit:
                note["instrumentId"] = short_instruments.get(voice["name"], note["instrumentId"])
                note["instrument"] = instrument_numbers[note["instrumentId"]]
            require(cells[start] == b"\x00", "Source note collision on the native tick grid")
            cells[start] = bytes((note["nativeNote"] | 0x80, note["instrument"]))
            off = start + duration if duration <= 2 else gate_off_tick(start, duration)
            note["gateOffTick"] = note["nativeGateOffTick"] = off
            if off != note["sourceGateOffTick"]:
                changes.append({"kind": "short-note-release-after-body", "voice": voice_index, "eventIndex": note["eventIndex"], "sourceTick": note["sourceGateOffTick"], "tick": off, "reason": "The second frame must remain gated to sound the native full-frequency body."})
        for note in notes:
            off = note["gateOffTick"]
            if cells[off] != b"\x00":
                note["nativeGateOffTick"] = None
                changes.append({"kind": "same-tick-release-replaced-by-note", "voice": voice_index, "eventIndex": note["eventIndex"], "tick": off})
            else:
                cells[off] = b"\x7e"
        # The native PTN_SEQ/SEQFXL2 stop path can reread the terminal byte; an effect column would become a note.
        cells[total_ticks] = b"\x7e"
        sequence = []
        entries = []
        for chunk_start, chunk in pattern_chunks(cells):
            packed, offsets = pack_pattern(chunk)
            if packed not in pattern_numbers:
                number = len(patterns) + 1
                pattern_numbers[packed] = number
                patterns.append({"number": number, "rows": len(chunk), "packedBytes": len(packed) - 1, "unpackedBytes": packed[-2], "bytes": packed})
            number = pattern_numbers[packed]
            sequence.append(number)
            entries.append({"pattern": number, "tick": None if chunk_start == 0 else chunk_start - 1})
            for row, value in enumerate(chunk):
                note_code = value[0] & 0x7f
                if 1 <= note_code <= 0x5f or note_code == 0x7e:
                    cell_map.append({"voice": voice_index, "tick": chunk_start + row, "pattern": number, "row": row, "byteOffset": offsets[row], "noteCode": note_code, "nativeByte": value[0], "instrument": value[1] & 0x7f if len(value) > 1 else None, "kind": "note" if note_code < 0x60 else "gate-off"})
        require(len(sequence) + 2 <= 128, "Native orderlist exceeds the 128-byte sequence limit")
        for note in notes:
            cell = next(cell for cell in cell_map if cell["voice"] == voice_index and cell["tick"] == note["startTick"])
            note.update({key: cell[key] for key in ("pattern", "row", "byteOffset")})
        voices.append({"name": voice["name"], "sidIndex": voice_index // 3, "sidVoice": voice_index % 3, "notes": notes, "sequence": sequence, "expectedPatternEntries": entries, "expectedSequenceEnding": [{"tick": total_ticks, "entry": 0xa0}, {"tick": total_ticks, "entry": 0xfe}]})
    require(len(patterns) <= pattern_limit, f"Native arrangement exceeds SID-Wizard's {pattern_limit}-pattern limit")
    header = bytearray(64)
    header[:4] = b"SWM1" if sid_count == 1 else b"SWMS"
    header[4] = 1
    header[5 if sid_count == 1 else 21] = 4
    header[8 if sid_count == 1 else 5:11] = b"\xff" * voice_count
    header[11:15] = bytes((64, voice_count, len(patterns), len(instruments)))
    header[19] = 3
    authorinfo = recipe.get("authorinfo", f"{recipe['author']}:{recipe['title']}").upper().encode("ascii")
    require(len(authorinfo) <= 40, "Native author/title header must fit 40 ASCII characters")
    header[24:64] = authorinfo.ljust(40, b" ")
    sequences = b"".join(bytes(voice["sequence"] + [0xa0, 0xfe, len(voice["sequence"]) + 2]) for voice in voices)
    data = b"\x33\x33" + header + sequences + b"".join(pattern["bytes"] for pattern in patterns) + b"".join(instruments.values()) + b"\x81\x81"
    output.mkdir(parents=True)
    native = output / f"{recipe_path.stem}.{'swm' if sid_count == 1 else 'sws'}"
    native.write_bytes(data)
    for identity, instrument in instruments.items():
        path = output / "instruments" / f"{identity}.swi"
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"\xa1\x04" + instrument)
    changes.append({"kind": "native-first-frame-and-envelope", "scope": "Every native note selection", "basis": "SID-Wizard 1.97 player.asm STRTSND/SETWFR1 and tempo-1 FASTSPEEDBIND", "effect": "First frame initializes only frequency high byte and the chosen frame1 waveform; full frequency and table body follow on the next tick. Tempo 1 bypasses hard restart; adjacent notes without a gate-off cell do not retrigger the envelope."})
    manifest = {
        "format": "sidwizard-arrangement-manifest-v1", "sourcePath": str(source), "sourceSha256": digest(source_bytes), "recipePath": str(recipe_path), "recipeSha256": digest(recipe_bytes),
        "nativePath": str(native), "nativeSha256": digest(data), "title": recipe["title"], "author": recipe["author"], "released": recipe.get("released", "2026"),
        "timingPolicy": recipe["timingPolicy"], "nativeHeaderText": authorinfo.decode("ascii"),
        "sidModel": sid_model, "sidCount": sid_count, "sids": [{"baseAddress": 0xd400 + index * 0x20, "model": sid_model} for index in range(sid_count)],
        "clock": target.name.upper(), "clockHz": target.clock_hz, "frameCycles": target.frame_cycles,
        "ticksPerSecond": target.ticks_per_second, "frameSpeed": 1, "rowTicks": 1,
        "effectTimingPolicy": "target-vbi", "effectUpdateRateHz": target.ticks_per_second, "envelopeTimingPolicy": "retain-sid-adsr-codes",
        "regionalDifferences": "Instrument programs retain their bytes and advance once per target video frame. NTSC modulation/first-frame durations follow its faster VBI; SID ADSR codes and retrigger rules stay unchanged, so envelope times follow the target SID clock. Register-unit detune and modulation amplitudes are not rescaled.",
        "shortNoteThreshold": {"palTicks": short_limit, "policy": "PAL retains historical adjusted-note classification; NTSC uses original absolute PAL-grid source durations."},
        "sourceTailPalTicks": source_tail,
        "scoreTicks": score_ticks, "tailTicks": tail, "totalTicks": total_ticks, "rowCount": row_count, "stopTick": total_ticks, "stopVolumeClearTick": total_ticks,
        "renderSeconds": (total_ticks + 1) / target.ticks_per_second + 1, "patterns": [{key: value for key, value in pattern.items() if key != "bytes"} for pattern in patterns],
        "instruments": [{"id": identity, "number": instrument_numbers[identity], "name": recipe["instruments"][identity]["name"]} for identity in identities],
        "voices": voices, "cellMap": cell_map, "timingChanges": timing_changes, "articulationChanges": changes, "endPolicy": "stop with gates closed and main volume zero",
        "criticalNotes": [dict(note, voice=index, audibleCheckTick=note["startTick"] + 1) for index, voice in enumerate(voices) for note in voice["notes"] if note["sourceDurationTicks"] <= 2 or note["durationTicks"] <= 2],
    }
    (output / f"{recipe_path.stem}.native.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--clock", choices=("pal", "ntsc"), help="Composition target override; otherwise use the recipe clock or legacy PAL")
    args = parser.parse_args()
    manifest = arrange(args.recipe, args.output_dir, clock=args.clock)
    print(f"Wrote {manifest['nativePath']}; retained {sum(len(voice['notes']) for voice in manifest['voices'])} notes in {len(manifest['patterns'])} native patterns")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(str(error))
