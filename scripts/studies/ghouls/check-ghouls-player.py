"""Verify one complete independent Ghouls traversal and its continuing filter tail."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from ghouls_player import GhoulsPlayer
from listening_checks import check_writes


SOURCE_SHA = '265644a66d6043e6fe5ddeeb0d87e9b4269386a73c3e26457c8d96ce3d042df4'
LEDGER_SHA = 'addb073a5219e46d9c1bee8f9249b9d0e98936399d951ff2936a616f870dff14'
FINAL_STREAM_CALL = 12995


def fingerprint(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def verify(description):
    calls = description.get('range', {}).get('auditCalls')
    if type(calls) is not int or not 13060 <= calls <= 40000:
        raise ValueError('Primary verification requires 13060..40000 calls, including the complete stopped filter tail')
    player = GhoulsPlayer(description)
    checkpoints = {'initialized': player.state()}
    selected = {0, 39, 40, 256, 1000, 4000, 8191, 12947, 12971, FINAL_STREAM_CALL, calls - 1}
    stopped_state = None
    terminal_calls = []
    for call in range(calls):
        before = [voice.enabled for voice in player.score.voices]
        start = len(player.writes)
        player.play(call)
        after = [voice.enabled for voice in player.score.voices]
        terminal_calls.extend(dict(call=call, voice=index) for index, (left, right) in
                              enumerate(zip(before, after)) if left >= 128 and right < 128)
        if call in selected:
            checkpoints[str(call)] = player.state()
        if call == FINAL_STREAM_CALL:
            if after != [0, 0, 0]:
                raise ValueError('Numeric score does not stop at the source boundary')
            stopped_state = player.state()
        elif call > FINAL_STREAM_CALL:
            actual = [(row['address'], row['value']) for row in player.writes[start:]]
            if actual != [(0xd415, 0), (0xd416, 0)] or player.state() != stopped_state:
                raise ValueError(f'Numeric stopped state/filter writes differ at call {call}')
    if terminal_calls != [dict(call=12947, voice=0), dict(call=12971, voice=2), dict(call=12995, voice=1)]:
        raise ValueError('Numeric voice termination order differs from the source')
    return player.writes, dict(calls=calls, finalStreamCall=FINAL_STREAM_CALL,
                               terminalCalls=terminal_calls, checkpoints=checkpoints,
                               stoppedFilterCalls=calls - FINAL_STREAM_CALL - 1,
                               stoppedStatePreserved=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--description', type=Path, default=ROOT / 'songs/ghouls.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.absolute()
    if any(path.is_symlink() for path in (output, *output.parents)) or output.exists() \
            or not output.resolve().is_relative_to(ROOT / 'build') or output.resolve() == ROOT / 'build':
        raise ValueError('Choose a fresh output directory below build/')
    description = json.loads(args.description.read_text())
    ledger = ROOT / 'evidence/ghouls-form/full40000/audit.writes.json.gz'
    raw = ledger.read_bytes()
    if hashlib.sha256(raw).hexdigest() != LEDGER_SHA:
        raise ValueError('Canonical source ledger fingerprint changed')
    decoded_sha = hashlib.sha256(gzip.decompress(raw)).hexdigest()
    writes, measured = verify(description)
    output.mkdir(parents=True)
    written = output / 'writes.json'
    written.write_text(json.dumps(writes, separators=(',', ':')) + '\n')
    comparison = check_writes(ledger, written, source_sha256=decoded_sha,
                              calls=measured['calls'], output=output / 'ordered-store-comparison.json')
    components = [ROOT / 'scripts' / name for name in
                  ('ghouls_player.py', 'ghouls_programs.py', 'ghouls_score.py', 'listening_checks.py')]
    receipt = dict(passed=True, sourceSha256=SOURCE_SHA, selectedSubtune=1,
                   description=fingerprint(args.description.resolve()),
                   components=[fingerprint(path) for path in components],
                   verifier=fingerprint(Path(__file__).resolve()),
                   canonicalLedger=fingerprint(ledger), matchedOrderedStores=len(writes),
                   measurements=measured, comparison=comparison,
                   scope='Independently advancing numeric state and complete ordered register values from editable data; no source execution in the player.',
                   excluded='Instruction-cycle identity, compiled CPU/VICE execution, SID internals, rendered audio and musical acceptance.')
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(passed=True, calls=measured['calls'], matchedOrderedStores=len(writes),
                         stoppedFilterCalls=measured['stoppedFilterCalls'], output=str(output))))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        print(f'Ghouls verification failed: {error}', file=sys.stderr)
        sys.exit(1)
