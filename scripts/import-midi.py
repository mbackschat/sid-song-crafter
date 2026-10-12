#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from score_tools import import_midi


def main():
    parser = argparse.ArgumentParser(description="Normalize a MIDI performance into an exact, polyphonic common score")
    parser.add_argument("input", type=Path)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        score = import_midi(args.input, json.loads(args.recipe.read_text()))
    except ValueError as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(score, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(score["provenance"]["importReport"], sort_keys=True))


if __name__ == "__main__":
    main()
