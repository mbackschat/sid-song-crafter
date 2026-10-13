#!/usr/bin/env python3
"""Build a listening package from a trusted sequential project recipe."""

import argparse
import sys

from listening_package import PackageError, run_recipe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recipe', help='schemaVersion 1 JSON recipe')
    parser.add_argument('--output', required=True, help='cache and listening index beneath repository build/')
    arguments = parser.parse_args()
    try:
        run_recipe(arguments.recipe, arguments.output, progress=lambda message: print(message, flush=True))
    except PackageError as error:
        print(f'Listening package failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
