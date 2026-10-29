"""Read a SID-Wizard 1.97 .swi instrument into the JSON instrument form of sidwizard-arrangement-v1 recipes."""

import argparse
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
# The editor's saveins routine writes this KERNAL load address before the packed instrument.
LOAD_ADDRESS = b"\xa1\x04"
# A waveform-table row whose arpeggio column holds this value calls the song chord table (SWM-spec.src / manual).
CHORD_CALL = 0x7F


def instrument_module():
    spec = importlib.util.spec_from_file_location("native_instrument_codec", ROOT / "scripts/generate-native-instruments.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def instrument_from_swi(identity, data):
    if data[:2] != LOAD_ADDRESS:
        raise ValueError(f"{identity}: not a SID-Wizard instrument file (expected load address $04A1)")
    return instrument_module().instrument_from_bytes(identity, data[2:])


def read_swi(path):
    path = Path(path)
    return instrument_from_swi(path.stem, path.read_bytes())


def uses_song_chord_table(instrument):
    """True when a waveform row calls the song chord table.

    The recipe converter writes no chord table, so such an instrument imports but does not play as designed.
    """
    octet = instrument_module().octet
    return any(not isinstance(row, dict) and octet(row[1]) == CHORD_CALL for row in instrument["wave"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("swi", type=Path)
    args = parser.parse_args()
    instrument = read_swi(args.swi)
    if uses_song_chord_table(instrument):
        print(f"{args.swi.name} calls the song chord table, which the recipe converter does not write: its chord rows will not play as designed.", file=sys.stderr)
    print(json.dumps(instrument, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
