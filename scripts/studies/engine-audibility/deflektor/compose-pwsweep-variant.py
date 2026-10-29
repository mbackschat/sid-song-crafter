"""Build and verify the Deflektor transfer with SID-Wizard PWSWEEP pulse arithmetic."""

import argparse
import json
from pathlib import Path

from pwsweep_variant import build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('variant', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = build(args.variant, args.output)
    print(json.dumps(dict(output=str(args.output), calls=report['checkedPlayCalls'],
                         stores=report['orderedStoreComparison']['matchedStores'],
                         maximumPlayCycles=report['maximumPlayCycles'])))


if __name__ == '__main__':
    try:
        main()
    except (KeyError, OSError, ValueError) as error:
        raise SystemExit(f'Deflektor PWSWEEP variant compilation failed: {error}')
