#!/usr/bin/env python3
"""Run an explicit source intake spec or its cached receipt stages."""

import argparse
import json
from pathlib import Path
import sys

from listening_package import PackageError
from reference_intake import (managed_output, measure_source,
                              ROOT, run_intake, selection_receipt, source_window, write_receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('run', help='execute a spec below build/ with verified stage reuse')
    run.add_argument('spec', type=Path)
    run.add_argument('--output', type=Path, required=True)
    selection = commands.add_parser('selection', help='write a verified selection receipt')
    selection.add_argument('selection', help='validated selection JSON from the immutable generated recipe')
    selection.add_argument('--registry-sha256', required=True)
    selection.add_argument('--output', type=Path, required=True)
    measure = commands.add_parser('measure', help='check a source render and its snapshot file')
    measure.add_argument('selection', type=Path)
    measure.add_argument('wav', type=Path)
    measure.add_argument('--output', type=Path, required=True)
    window = commands.add_parser('window', help='extract original excerpts or a labelled source contrast')
    window.add_argument('first', type=Path)
    window.add_argument('--second', type=Path)
    window.add_argument('--start', type=float, required=True)
    window.add_argument('--end', type=float, required=True)
    window.add_argument('--gap', type=float, required=True)
    window.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    managed_output(args.output, ROOT)
    if args.command == 'run':
        run_intake(args.spec, args.output, progress=lambda message: print(message, flush=True))
    elif args.command == 'selection':
        write_receipt(args.output, selection_receipt(json.loads(args.selection), registry_sha256=args.registry_sha256))
    elif args.command == 'measure':
        measure_source(args.selection, args.wav, args.output)
    else:
        source_window(args.first, args.second, start=args.start, end=args.end, gap=args.gap, output=args.output)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, PackageError) as error:
        print(f'Reference intake failed: {error}', file=sys.stderr)
        raise SystemExit(1)
