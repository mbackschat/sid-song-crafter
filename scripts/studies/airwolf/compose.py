"""Build and verify independent editable Airwolf PAL/MOS6581 exports."""

import argparse
import json
from pathlib import Path

from airwolf_compiler import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('composition', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calls', type=int, help='Bounded CPU diagnostic; numeric admission still covers the full range')
    args = parser.parse_args()
    checked = run(args.composition, args.output, args.calls)
    print(json.dumps(dict(calls=checked['checkedPlayCalls'],
        stores=checked['orderedStoreComparison']['matchedStores'], maximumPlayCycles=checked['maximumPlayCycles'],
        bootstrap=checked['standaloneBootstrapVerification']['passed'])))


if __name__ == '__main__':
    try:
        main()
    except (KeyError, OSError, ValueError, TypeError) as error:
        raise SystemExit(f'Airwolf compilation failed: {error}')
