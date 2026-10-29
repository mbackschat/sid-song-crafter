#!/usr/bin/env python3
"""Generate the original SID-Wizard 1.97 SWM1/SWI sound-design fixtures.

`instrument_bytes` encodes the JSON instrument form used by repertoire banks and `sidwizard-arrangement-v1` recipes;
`instrument_from_bytes` is its exact inverse for packed `.swi` data.
"""

import argparse
import json
from pathlib import Path
import re


def octet(value):
    number = int(value, 16) if isinstance(value, str) else value
    if isinstance(number, bool) or not isinstance(number, int) or not 0 <= number <= 255:
        raise ValueError(f"Not a byte: {value!r}")
    return number


HEADER_SIZE = 16
WAVE_TABLE_START = 16
NAME_SIZE = 8
# Jump pointers at or above this value make the waveform table rest on its jump row (player.asm WFAJUMP, `BMIauto ENDWFTB`).
# Upstream examples use them as halts, so they are raw pointers instead of row indexes. The pulse table has no such
# rest branch (player.asm PWTJUMP indexes the instrument with the pointer); its one upstream use, tamburin, is kept byte-exact.
REST_POINTER = 0x80
MAX_OCTAVE_SHIFT = 10


def _jump_row(row, start, row_count, label):
    if "jump_pointer" in row:
        try:
            pointer = octet(row["jump_pointer"])
        except ValueError:
            pointer = None
        if "jump" in row or pointer is None or pointer < REST_POINTER:
            raise ValueError(f"{label}: jump_pointer must be a byte of at least 80 and cannot be combined with jump")
        return (0xFE, pointer, 0)
    target = row.get("jump")
    if isinstance(target, bool) or not isinstance(target, int) or not 0 <= target < row_count:
        raise ValueError(f"{label}: invalid table jump {target!r}")
    return (0xFE, start + 3 * target, 0)


def _table(rows, start, label):
    encoded = bytearray()
    for row in rows:
        if isinstance(row, dict):
            encoded.extend(_jump_row(row, start, len(rows), label))
        else:
            if len(row) != 3 or octet(row[0]) >= 0xFE:
                raise ValueError(f"{label}: use three-byte rows and explicit jump targets")
            encoded.extend(octet(value) for value in row)
    encoded.append(0xFF)
    return encoded


def _header_byte(identity, instrument, key, default):
    try:
        return octet(instrument.get(key, default))
    except ValueError:
        raise ValueError(f"{identity}: {key} must be a byte") from None


def _octave_shift_byte(identity, instrument):
    octaves = instrument.get("octave_shift", 0)
    if isinstance(octaves, bool) or not isinstance(octaves, int) or abs(octaves) > MAX_OCTAVE_SHIFT:
        raise ValueError(f"{identity}: octave_shift must be a whole number of octaves within +-{MAX_OCTAVE_SHIFT}")
    # SWM-spec.src SWI_OCTAVE_POS: two's-complement semitones, which the editor steps in twelves.
    return (12 * octaves) & 0xFF


def _gate_off_pointer(identity, instrument, key, start, row_count, *, may_name_terminator):
    row = instrument.get(key)
    if row is None:
        return 0
    # The pointer is an instrument-relative table position, so row 0 is a real pointer and absence is zero.
    # A wave or pulse pointer may name the $FF terminator (upstream flute-ocarin does); the filter terminator byte
    # is replaced by the instrument size, so naming it would run that size as a table row.
    limit = row_count + (1 if may_name_terminator else 0)
    if isinstance(row, bool) or not isinstance(row, int) or not 0 <= row < limit:
        raise ValueError(f"{identity}: {key} must name a row of its table" + (" or its end" if may_name_terminator else ""))
    return start + 3 * row


def instrument_bytes(identity, instrument):
    name = instrument["name"].encode("ascii")
    if len(name) > 8 or not name or instrument["name"] != instrument["name"].upper():
        raise ValueError(f"{identity}: name must contain 1..8 uppercase ASCII characters")
    hard_restart = bytes.fromhex(instrument["hard_restart_adsr"])
    adsr = bytes.fromhex(instrument["adsr"])
    if len(hard_restart) != 2 or len(adsr) != 2:
        raise ValueError(f"{identity}: ADSR must contain two bytes")
    # Bytes 10-14 (table and gate-off pointers) are filled in once the table positions are known.
    header = bytearray((
        octet(instrument["control"]), *hard_restart, *adsr,
        octet(instrument.get("vibrato", 0)), octet(instrument.get("vibrato_delay", 0)),
        _header_byte(identity, instrument, "arp_speed", 0), _header_byte(identity, instrument, "default_chord", 1),
        _octave_shift_byte(identity, instrument),
        0, 0, 0, 0, 0, octet(instrument.get("frame1", "09")),
    ))
    wave = _table(instrument["wave"], WAVE_TABLE_START, f"{identity} wave")
    header[10] = WAVE_TABLE_START + len(wave)
    pulse = _table(instrument["pulse"], header[10], f"{identity} pulse")
    header[11] = header[10] + len(pulse)
    filtr = _table(instrument["filter"], header[11], f"{identity} filter")
    for position, key, start, rows, terminator in (
        (12, "gate_off_wave", WAVE_TABLE_START, instrument["wave"], True),
        (13, "gate_off_pulse", header[10], instrument["pulse"], True),
        (14, "gate_off_filter", header[11], instrument["filter"], False),
    ):
        header[position] = _gate_off_pointer(identity, instrument, key, start, len(rows), may_name_terminator=terminator)
    encoded = header + wave + pulse + filtr
    if len(encoded) > 120:
        raise ValueError(f"{identity}: instrument exceeds the native 120-byte table area")
    # SID-Wizard 1.97 packinst replaces the final filter delimiter with its offset.
    encoded[-1] = len(encoded) - 1
    return bytes(encoded + name.ljust(8, b" "))


def _decode_table(identity, table, start, label):
    rows_data = table[:-1]
    if len(rows_data) % 3:
        raise ValueError(f"{identity}: {label} table is not a whole number of three-byte rows")
    count = len(rows_data) // 3
    rows = []
    for index in range(count):
        first, second, third = rows_data[3 * index:3 * index + 3]
        if first == 0xFE:
            offset = second - start
            if third:
                raise ValueError(f"{identity}: {label} jump row {index} has a nonzero third byte")
            if 0 <= offset < 3 * count and offset % 3 == 0:
                rows.append({"jump": offset // 3})
            elif second >= REST_POINTER:
                rows.append({"jump_pointer": f"{second:02x}"})
            else:
                raise ValueError(f"{identity}: {label} jump row {index} points to ${second:02x}, which is neither a row nor a rest pointer")
        elif first == 0xFF:
            raise ValueError(f"{identity}: {label} row {index} starts with the table terminator")
        else:
            rows.append([f"{value:02x}" for value in (first, second, third)])
    return rows


def _decode_gate_off(identity, pointer, key, start, rows, *, may_name_terminator):
    if pointer == 0:
        return None
    offset = pointer - start
    if offset % 3 or not 0 <= offset // 3 < rows + (1 if may_name_terminator else 0):
        raise ValueError(f"{identity}: {key} pointer ${pointer:02x} does not name a row of its table")
    return offset // 3


def instrument_from_bytes(identity, data):
    """Decode packed instrument bytes (no load address) into the JSON form `instrument_bytes` accepts.

    Fields equal to their encoder default are omitted. The result is re-encoded and compared with `data`, so an
    instrument the form cannot hold is rejected instead of silently losing bytes.
    """
    if len(data) < HEADER_SIZE + 3 + NAME_SIZE:
        raise ValueError(f"{identity}: instrument is truncated")
    body, raw_name = data[:-NAME_SIZE], data[-NAME_SIZE:]
    header = body[:HEADER_SIZE]
    if body[-1] != len(body) - 1:
        raise ValueError(f"{identity}: size marker ${body[-1]:02x} does not match the instrument length {len(body)}")
    wave_end, pulse_end = header[10], header[11]
    if not WAVE_TABLE_START < wave_end < pulse_end < len(body):
        raise ValueError(f"{identity}: table pointers ${wave_end:02x}/${pulse_end:02x} are inconsistent")
    wave, pulse, filtr = body[WAVE_TABLE_START:wave_end], body[wave_end:pulse_end], body[pulse_end:]
    if wave[-1] != 0xFF or pulse[-1] != 0xFF:
        raise ValueError(f"{identity}: wave and pulse tables must end with $FF")
    try:
        name = raw_name.decode("ascii").rstrip(" ")
    except UnicodeDecodeError:
        raise ValueError(f"{identity}: name is not ASCII") from None
    if not name or name != name.upper():
        raise ValueError(f"{identity}: name must contain 1..8 uppercase ASCII characters")
    shift = header[9] - 256 if header[9] >= 128 else header[9]
    if shift % 12 or abs(shift) > 12 * MAX_OCTAVE_SHIFT:
        raise ValueError(f"{identity}: octave shift of {shift} semitones is not a whole number of octaves")
    instrument = {
        "name": name, "control": f"{header[0]:02x}", "hard_restart_adsr": header[1:3].hex(), "adsr": header[3:5].hex(),
        "vibrato": header[5], "vibrato_delay": header[6], "frame1": f"{header[15]:02x}",
        "wave": _decode_table(identity, wave, WAVE_TABLE_START, "wave"),
        "pulse": _decode_table(identity, pulse, wave_end, "pulse"),
        "filter": _decode_table(identity, filtr, pulse_end, "filter"),
    }
    optional = {"arp_speed": header[7], "default_chord": header[8], "octave_shift": shift // 12}
    defaults = {"arp_speed": 0, "default_chord": 1, "octave_shift": 0}
    instrument.update({key: value for key, value in optional.items() if value != defaults[key]})
    for pointer, key, start, rows, terminator in (
        (header[12], "gate_off_wave", WAVE_TABLE_START, instrument["wave"], True),
        (header[13], "gate_off_pulse", wave_end, instrument["pulse"], True),
        (header[14], "gate_off_filter", pulse_end, instrument["filter"], False),
    ):
        row = _decode_gate_off(identity, pointer, key, start, len(rows), may_name_terminator=terminator)
        if row is not None:
            instrument[key] = row
    if instrument_bytes(identity, instrument) != data:
        raise ValueError(f"{identity}: instrument is not representable in the JSON form")
    return instrument


# A waveform-table row whose arpeggio column holds this value calls the song chord table (SID-Wizard manual, waveform table
# values; player.asm PLYCHRD). Repeat rows ($00..$0F) take the same path, so the test is on the column alone.
CHORD_CALL = 0x7F


def calls_chord_table(instrument):
    """True when a waveform row of the JSON instrument form calls the song chord table."""
    return any(not isinstance(row, dict) and octet(row[1]) == CHORD_CALL for row in instrument["wave"])


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
