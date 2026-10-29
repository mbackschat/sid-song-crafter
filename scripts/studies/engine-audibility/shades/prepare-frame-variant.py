"""Derive the one-call-per-frame Shades variant of the accepted Für Elise transfer.

The score keeps every note, rest and hold of songs/shades-elise-transfer.json and
the pulse-trio instrument keeps its notes, envelopes and filter ownership. Only
cadence-dependent counts and steps change, by the rules in rescale.py.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))

import rescale  # noqa: E402
from verify_player import require  # noqa: E402


BLOCK = 'pulse-trio'
DEFAULT_SCORE = ROOT / 'songs/shades-elise-transfer.json'
DEFAULT_PROGRAMS = ROOT / 'songs/shades-transfer-programs.json'
DEFAULT_OUTPUT = ROOT / 'songs/studies/engine-audibility/shades'
NAMES = ('score.json', 'programs.json', 'rescaling.json')


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def prepare(score_bytes, programs_bytes):
    score, programs = json.loads(score_bytes), json.loads(programs_bytes)
    require(score.get('instrumentBlocks') == [BLOCK], 'The exact transfer must select only pulse-trio')
    require(programs.get('format') == 'sid-shades-programs-v1', 'Unsupported Shades programs format')
    exact_block = programs['programs']['blocks'][BLOCK]
    block, parameter_table = rescale.rescale_block(exact_block)
    frame_score, boundary_table = rescale.rescale_score(score)
    frame_programs = {
        'format': 'sid-shades-programs-v1',
        'programs': {'frequency_words': list(programs['programs']['frequency_words']),
                     'blocks': {BLOCK + '-frame': block}},
        'preloaded': programs['preloaded'],
        'sourceEvidence': {
            'identity': 'Frame-rate copy of the accepted Shades pulse-trio program; only call-counted fields differ.',
            'derivedFrom': 'songs/shades-transfer-programs.json',
            'derivedFromSha256': hashlib.sha256(programs_bytes).hexdigest(),
            'rules': 'rescaling.json',
        },
    }
    errors = [abs(row['startErrorMs']) for row in boundary_table]
    exact_stop, frame_stop = score['range']['stopCall'], frame_score['range']['stopCall']
    frame_score['sourceEvidence'] = {
        'identity': 'Frame-rate copy of the accepted Shades Für Elise transfer; the same 53 events and release.',
        'derivedFrom': 'songs/shades-elise-transfer.json',
        'derivedFromSha256': hashlib.sha256(score_bytes).hexdigest(),
        'rules': 'rescaling.json',
        'timing': {'driverCallPeriodCycles': rescale.FRAME, 'callRateHz': rescale.CLOCK_HZ / rescale.FRAME,
                   'boundaryRounding': 'Nearest frame to each exact boundary time, half up; absolute, no accumulation.',
                   'maximumBoundaryErrorMs': max(errors),
                   'finiteStopCall': frame_stop,
                   'finiteStopMs': rescale.milliseconds(rescale.frame_call_cycle(frame_stop)),
                   'exactFiniteStopMs': rescale.milliseconds(rescale.exact_call_cycle(exact_stop))},
        'listeningStatus': 'Pending; numeric preparation does not establish musical quality.',
    }
    rescaling = {
        'format': 'engine-audibility-shades-rescaling-v1',
        'purpose': 'Isolate the update-rate limit: the CIA-timed exact transfer versus one driver call per PAL video frame.',
        'clocks': {'cpuHz': rescale.CLOCK_HZ,
                   'exactCallCycles': rescale.EXACT_PERIOD, 'exactCallHz': rescale.CLOCK_HZ / rescale.EXACT_PERIOD,
                   'exactFirstIntervalCycles': rescale.EXACT_FIRST_INTERVAL,
                   'frameCallCycles': rescale.FRAME, 'frameCallHz': rescale.CLOCK_HZ / rescale.FRAME,
                   'framesPerExactCall': float(rescale.RHO)},
        'rules': rescale.RULES,
        'parameters': parameter_table,
        'rowBoundaries': boundary_table,
        'summary': {'maximumRowStartErrorMs': max(errors),
                    'orders': len(boundary_table), 'exactStopCall': exact_stop, 'frameStopCall': frame_stop,
                    'blockRenamed': {BLOCK: BLOCK + '-frame'}},
        'inputs': {'score': 'songs/shades-elise-transfer.json', 'scoreSha256': hashlib.sha256(score_bytes).hexdigest(),
                   'programs': 'songs/shades-transfer-programs.json', 'programsSha256': hashlib.sha256(programs_bytes).hexdigest()},
    }
    # The scheduler validates ranges and row timing; the programs loader validates every field.
    from shades_player import Player
    Player(frame_score, frame_programs)
    return dict(zip(NAMES, (frame_score, frame_programs, rescaling)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--score', type=Path, default=DEFAULT_SCORE)
    parser.add_argument('--programs', type=Path, default=DEFAULT_PROGRAMS)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--check', action='store_true', help='Check the saved description without changing files')
    args = parser.parse_args()
    outputs = prepare(args.score.read_bytes(), args.programs.read_bytes())
    paths = {name: args.output / name for name in NAMES}
    if args.check:
        for name, path in paths.items():
            require(path.is_file() and path.read_bytes() == encoded(outputs[name]),
                    f'Saved description differs from generated output: {path}')
        print(f'Checked {len(paths)} saved files in {args.output}')
        return
    require(all(not path.exists() and not path.is_symlink() for path in paths.values()),
            'Choose fresh outputs; use --check to verify existing files')
    args.output.mkdir(parents=True, exist_ok=True)
    for name, path in paths.items():
        with path.open('xb') as handle:
            handle.write(encoded(outputs[name]))
    print(f'Wrote {len(paths)} files to {args.output}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
