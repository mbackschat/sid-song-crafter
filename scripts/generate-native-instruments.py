#!/usr/bin/env python3
"""Generate the original SID-Wizard 1.97 SWM1/SWI sound-design fixtures."""

import argparse
import json
from pathlib import Path
import re


def octet(value):
    number = int(value, 16) if isinstance(value, str) else value
    if isinstance(number, bool) or not isinstance(number, int) or not 0 <= number <= 255:
        raise ValueError(f"Not a byte: {value!r}")
    return number


def _table(rows, start, label):
    encoded = bytearray()
    for row in rows:
        if isinstance(row, dict):
            target = row.get("jump")
            if isinstance(target, bool) or not isinstance(target, int) or not 0 <= target < len(rows):
                raise ValueError(f"{label}: invalid table jump {target!r}")
            encoded.extend((0xFE, start + 3 * target, 0))
        else:
            if len(row) != 3 or octet(row[0]) >= 0xFE:
                raise ValueError(f"{label}: use three-byte rows and explicit jump targets")
            encoded.extend(octet(value) for value in row)
    encoded.append(0xFF)
    return encoded


def instrument_bytes(identity, instrument):
    name = instrument["name"].encode("ascii")
    if len(name) > 8 or not name or instrument["name"] != instrument["name"].upper():
        raise ValueError(f"{identity}: name must contain 1..8 uppercase ASCII characters")
    hard_restart = bytes.fromhex(instrument["hard_restart_adsr"])
    adsr = bytes.fromhex(instrument["adsr"])
    if len(hard_restart) != 2 or len(adsr) != 2:
        raise ValueError(f"{identity}: ADSR must contain two bytes")
    header = bytearray((
        octet(instrument["control"]), *hard_restart, *adsr,
        octet(instrument.get("vibrato", 0)), octet(instrument.get("vibrato_delay", 0)),
        0, 1, 0, 0, 0, 0, 0, 0, octet(instrument.get("frame1", "09")),
    ))
    wave = _table(instrument["wave"], 16, f"{identity} wave")
    header[10] = 16 + len(wave)
    pulse = _table(instrument["pulse"], header[10], f"{identity} pulse")
    header[11] = header[10] + len(pulse)
    filtr = _table(instrument["filter"], header[11], f"{identity} filter")
    encoded = header + wave + pulse + filtr
    if len(encoded) > 120:
        raise ValueError(f"{identity}: instrument exceeds the native 120-byte table area")
    # SID-Wizard 1.97 packinst replaces the final filter delimiter with its offset.
    encoded[-1] = len(encoded) - 1
    return bytes(encoded + name.ljust(8, b" "))


def note_value(note):
    if note == "off":
        return 0x7E
    match = re.fullmatch(r"([A-G])([#b]?)([0-7])", note)
    if not match:
        raise ValueError(f"Invalid scientific pitch: {note!r}")
    letter, accidental, octave = match.groups()
    semitone = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[letter]
    semitone += {"": 0, "#": 1, "b": -1}[accidental]
    value = 1 + 12 * int(octave) + semitone
    if not 1 <= value <= 0x5F:
        raise ValueError(f"Pitch outside SWM1's note range: {note!r}")
    return value


def pattern_bytes(identity, phrase, roles):
    row_count = phrase["rows"]
    if not isinstance(row_count, int) or not 1 <= row_count <= 248:
        raise ValueError(f"{identity}: rows must be in 1..248")
    events = {}
    for event in phrase["events"]:
        row = event["row"]
        if not isinstance(row, int) or not 0 <= row < row_count or row in events:
            raise ValueError(f"{identity}: invalid or duplicate row {row!r}")
        events[row] = event
    encoded = bytearray()
    for row in range(row_count):
        event = events.get(row)
        if event is None:
            encoded.append(0)
            continue
        note = note_value(event["note"])
        role = event.get("instrument")
        if role is None:
            encoded.append(note)
        else:
            if role == "tie":
                selected = 0x3F
            elif role in roles:
                selected = roles.index(role) + 1
            else:
                raise ValueError(f"{identity}: unknown instrument role {role!r}")
            encoded.extend((note | 0x80, selected))
    if len(encoded) + 1 > 249:
        raise ValueError(f"{identity}: encoded pattern exceeds the native 249-byte limit")
    # SWM-spec.src counts the replaced $FF end marker in the pattern size.
    encoded.extend((len(encoded) + 1, row_count))
    return bytes(encoded)


def _workfile(bank, study):
    roles = list(study["instruments"])
    if not 1 <= len(roles) <= 36:
        raise ValueError("A trial must use 1..36 instruments")
    if len(study["tracks"]) != 3:
        raise ValueError("The trial bank targets one three-voice SID")
    header = bytearray(64)
    header[:4] = b"SWM1"
    header[4:6] = bytes((1, 4))
    header[8:15] = bytes((0xFF, 0xFF, 0xFF, 64, 3, 3, len(roles)))
    header[19] = 3
    author = bank["authorinfo"].encode("ascii")
    if len(author) > 40:
        raise ValueError("authorinfo exceeds the native 40-byte field")
    header[24:] = author.ljust(40, b" ")
    sequences = bytes((1, 0xFE, 2, 2, 0xFE, 2, 3, 0xFE, 2))
    patterns = b"".join(
        pattern_bytes(name, bank["phrases"][name], roles) for name in study["tracks"]
    )
    prefix = b"\x33\x33" + header + sequences + patterns
    instruments = b"".join(
        instrument_bytes(name, bank["instruments"][name]) for name in study["instruments"].values()
    )
    tempo = bank["row_ticks"]
    if not isinstance(tempo, int) or not 3 <= tempo <= 127:
        raise ValueError("row_ticks must be in 3..127")
    return prefix, instruments + bytes((tempo | 0x80, tempo | 0x80))


def instrument_data_offset(bank, study_name):
    return len(_workfile(bank, bank["studies"][study_name])[0])


def generate(bank):
    if bank["format"] != "original-sidwizard-repertoire-v1":
        raise ValueError("Unsupported repertoire source format")
    outputs = {}
    for name, instrument in bank["instruments"].items():
        # The editor's saveins routine writes a KERNAL load address, then packinst data.
        outputs[f"instruments/{name}.swi"] = b"\xA1\x04" + instrument_bytes(name, instrument)
    for name, study in bank["studies"].items():
        prefix, instruments = _workfile(bank, study)
        outputs[f"{name}.swm"] = prefix + instruments
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    outputs = generate(json.loads(args.source.read_text()))
    for relative, data in outputs.items():
        destination = args.output_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    print(f"Wrote {len(outputs)} native SID-Wizard files to {args.output_dir}")


if __name__ == "__main__":
    main()
