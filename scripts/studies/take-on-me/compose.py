"""Build and verify an independent editable Take On Me PAL/8580 SID and PRG."""

import argparse
import json
from pathlib import Path

from compiler import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('composition', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calls', type=int)
    args = parser.parse_args()
    checked = run(args.composition, args.output, args.calls)
    print(json.dumps(dict(calls=checked['checkedPlayCalls'],
        stores=checked['orderedStoreComparison']['matchedStores'], maximumPlayCycles=checked['maximumPlayCycles'],
        bootstrap=checked['standaloneBootstrapVerification']['passed'])))


if __name__ == '__main__':
    try:
        main()
    except (KeyError, OSError, ValueError) as error:
        raise SystemExit(f'Take On Me compilation failed: {error}')
