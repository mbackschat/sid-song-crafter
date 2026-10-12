#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from score_tools import arrange_score


def main():
    parser = argparse.ArgumentParser(description="Reduce a common score into a deterministic three-voice SID arrangement")
    parser.add_argument("input", type=Path)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        score = arrange_score(json.loads(args.input.read_text()), json.loads(args.recipe.read_text()))
    except ValueError as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(score, ensure_ascii=False, indent=2) + "\n")
    report = score["provenance"]["reduction"]
    print(json.dumps({key: value for key, value in report.items() if key not in ("omittedEvents", "shortenedEvents")}, sort_keys=True))


if __name__ == "__main__":
    main()
