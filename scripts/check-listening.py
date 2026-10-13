"""Write exclusive receipts for source pins, ordered SID writes and WAV health."""

import argparse
from pathlib import Path
import sys

from listening_checks import check_asset, check_audio, check_writes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    asset = commands.add_parser('asset', help='verify an input file SHA-256 pin')
    asset.add_argument('source', type=Path)
    asset.add_argument('--sha256', required=True)
    asset.add_argument('--output', type=Path, required=True)
    writes = commands.add_parser('writes', help='compare initialization and every declared play call in order')
    writes.add_argument('source', type=Path)
    writes.add_argument('candidate', type=Path)
    writes.add_argument('--source-sha256', required=True, help='SHA-256 of the decompressed source JSON bytes')
    writes.add_argument('--calls', type=int, required=True)
    writes.add_argument('--output', type=Path, required=True)
    audio = commands.add_parser('audio', help='check complete PCM16 renders without a listening or PCM-identity claim')
    audio.add_argument('reference', type=Path)
    audio.add_argument('candidate', type=Path)
    audio.add_argument('--seconds', type=float, required=True)
    audio.add_argument('--sample-rate', type=int, default=44100)
    audio.add_argument('--channels', type=int, default=1)
    audio.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'asset':
        check_asset(args.source, sha256=args.sha256, output=args.output)
    elif args.command == 'writes':
        check_writes(args.source, args.candidate, source_sha256=args.source_sha256, calls=args.calls, output=args.output)
    else:
        check_audio(args.reference, args.candidate, seconds=args.seconds, sample_rate=args.sample_rate, channels=args.channels, output=args.output)
    print(f'{args.command} check passed: {args.output}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        print(f'Listening input check failed: {error}', file=sys.stderr)
        sys.exit(1)
