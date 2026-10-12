#!/usr/bin/env python3
"""Build, render, and verify a three-voice SID arrangement without a display."""

import argparse
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arrangement", type=Path, help="SID arrangement JSON, not an unarranged common score")
    parser.add_argument("--output", type=Path, default=ROOT / "build")
    parser.add_argument("--name", help="output basename; defaults to the arrangement filename stem")
    parser.add_argument("--vice-audio", action="store_true", help="also record VICE audio at normal emulation speed")
    parser.add_argument("--renderer", type=Path)
    parser.add_argument("--vice", type=Path)
    parser.add_argument("--vice-data", type=Path)
    args = parser.parse_args()
    name = args.name or args.arrangement.stem
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        parser.error("name must contain only letters, numbers, underscores or hyphens")
    source, output = args.arrangement.resolve(), args.output.resolve()
    subprocess.run(
        ["bun", str(ROOT / "scripts/build-arrangement.ts"), str(source), str(output), name],
        check=True, timeout=120,
    )
    command = [sys.executable, str(ROOT / "scripts/verify-arrangement.py"),
               str(output / f"{name}.events.json"), "--score", str(source)]
    for option in ("renderer", "vice", "vice_data"):
        value = getattr(args, option)
        if value is not None:
            command.extend(["--" + option.replace("_", "-"), str(value.resolve())])
    if args.vice_audio:
        command.append("--vice-audio")
    # The verifier owns renderer/VICE deadlines, including duration-bound real-time capture.
    subprocess.run(command, check=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.SubprocessError) as error:
        print(f"Song workflow failed: {error}", file=sys.stderr)
        sys.exit(1)
