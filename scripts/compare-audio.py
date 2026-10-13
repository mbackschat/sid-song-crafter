import argparse
import json
from pathlib import Path
import sys

from audio_comparison import inspect_wav, prepare_comparison, prepare_window_comparison


def main():
    parser = argparse.ArgumentParser(description="Inspect PCM16 WAVs or prepare documented unity-gain windows and level-matched A/B auditions.")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="print duration, peak/clipping, DC and RMS measurements as JSON")
    inspect.add_argument("wav", type=Path)
    prepare = commands.add_parser("prepare", help="write PREFIX.ab.wav and PREFIX.comparison.json, preserving the originals")
    prepare.add_argument("a", type=Path)
    prepare.add_argument("b", type=Path)
    prepare.add_argument("prefix", type=Path)
    prepare.add_argument("--target-ac-rms-dbfs", type=float, help="explicit full-file AC RMS target; default safely attenuates to a shared level")
    prepare.add_argument("--peak-headroom-db", type=float, default=1.0, help="minimum peak headroom in dB (default: 1)")
    prepare.add_argument("--gap-seconds", type=float, default=0.5, help="silence between A and B, from 0 to 60 seconds (default: 0.5)")
    prepare.add_argument("--individual-copies", action="store_true", help="also write PREFIX.a.matched.wav and PREFIX.b.matched.wav")
    window = commands.add_parser("window", help="copy the same selected window at unity gain, then silence, then B")
    window.add_argument("a", type=Path)
    window.add_argument("b", type=Path)
    window.add_argument("prefix", type=Path)
    window.add_argument("--start-seconds", type=float, required=True, help="window start, rounded to a sample frame")
    window.add_argument("--end-seconds", type=float, required=True, help="exclusive window end, rounded to a sample frame")
    window.add_argument("--gap-seconds", type=float, default=0.5, help="silence between A and B, from 0 to 60 seconds (default: 0.5)")
    args = parser.parse_args()
    if args.command == "inspect":
        print(json.dumps(inspect_wav(args.wav), indent=2, allow_nan=False))
    else:
        if args.command == "window":
            report = prepare_window_comparison(args.a, args.b, args.prefix, start_seconds=args.start_seconds, end_seconds=args.end_seconds, gap_seconds=args.gap_seconds)
        else:
            report = prepare_comparison(args.a, args.b, args.prefix, target_ac_rms_dbfs=args.target_ac_rms_dbfs, peak_headroom_db=args.peak_headroom_db, gap_seconds=args.gap_seconds, individual_copies=args.individual_copies)
        print(f"A then B: {report['comparison']['path']}")
        print(f"Evidence: {args.prefix.resolve()}.comparison.json")
        print("Gain: " + ", ".join(f"{value['label']} {value['gainDb']:+.3f} dB" for value in report["inputs"]))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        print(f"Audio comparison failed: {error}", file=sys.stderr)
        sys.exit(1)
