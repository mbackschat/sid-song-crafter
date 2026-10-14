"""Build and verify independent editable Deflektor PAL/6581 SID and PRG exports."""

import argparse
import json
from pathlib import Path

from deflektor_compiler import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('description', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calls', type=int)
    args = parser.parse_args()
    report = run(args.description, args.output, args.calls)
    print(json.dumps(dict(output=str(args.output), calls=report['checkedPlayCalls'],
                         stores=report['orderedStoreComparison']['matchedStores'],
                         maximumPlayCycles=report['maximumPlayCycles'])))


if __name__ == '__main__':
    try:
        main()
    except (KeyError, OSError, ValueError) as error:
        raise SystemExit(f'Deflektor compilation failed: {error}')
