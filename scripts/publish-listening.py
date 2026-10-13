#!/usr/bin/env python3
"""Copy selected verified listening WAVs into a fresh local audition folder."""

import argparse
from pathlib import Path
import sys

from listening_publish import PublishError, publish_listening


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", help="completed listening-package run.json")
    parser.add_argument("--selection", required=True, help="JSON mapping deliverable labels to friendly .wav filenames")
    parser.add_argument("--output", required=True, help="fresh directory below repository build/")
    args = parser.parse_args()
    try:
        manifest = publish_listening(args.run, args.selection, args.output)
    except PublishError as error:
        print(f"Listening publication failed: {error}", file=sys.stderr)
        return 1
    output = Path(args.output).absolute()
    for record in manifest["files"]:
        print(f'{record["label"]}: {output / record["filename"]}')
    print(f"Sources: {output / 'sources.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
