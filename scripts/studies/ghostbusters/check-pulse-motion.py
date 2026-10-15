"""Retain a note-free aggregate of numeric moving-pulse isolation."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('ghostbusters_motion_numeric_compiler', Path(__file__).with_name('compiler.py'))
compiler = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = compiler
spec.loader.exec_module(compiler)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compare(composition, baseline, candidate):
    compiler.require('pulseMotion' not in baseline['support'] and candidate['support'].get('pulseMotion') == 'triangle-600-a00', 'Compare static support with the selected moving-pulse mode')
    plain = compiler.numeric(composition, baseline)
    moving = compiler.numeric(composition, candidate)
    ports = (0xd429, 0xd42a)
    retained = [row for row in plain['writes'] if row['address'] not in ports]
    actual = [row for row in moving['writes'] if row['address'] not in ports]
    compiler.require(compiler.identity(retained) == compiler.identity(actual), 'Moving pulse changed a non-pulse store')
    compiler.require(plain['supportLedger'] == moving['supportLedger'], 'Moving pulse changed source-root gate phrasing')
    calls = len(moving['returns'])
    added = len(moving['writes']) - len(plain['writes'])
    compiler.require(calls == composition['range']['auditCalls'] and added == 2 * calls, 'Moving pulse did not add exactly two stores per declared call')
    ledger = moving['supportLedger']
    return dict(schemaVersion=1, passed=True,
        scope='Complete declared independent numeric store and gate-ledger comparison; no complete native execution, PCM identity or musical-acceptance claim',
        checkedMusicCalls=calls, matchedNonPulseStores=len(retained), excludedPulseAddresses=list(ports),
        nonPulseStoresIdentical=True, supportGateLedgerIdentical=True, supportPhrases=len(ledger),
        supportGateCalls=sum(row['endCall'] - row['startCall'] for row in ledger),
        addedPulseStores=added,
        gateLedgerSha256=sha(json.dumps(ledger, sort_keys=True, separators=(',', ':')).encode()))


def run(composition_path, baseline_path, candidate_path, output):
    compiler.require(not output.exists(), 'Choose a fresh numeric summary output')
    paths = dict(composition=composition_path, baseline=baseline_path, candidate=candidate_path)
    result = compare(*(json.loads(paths[name].read_text()) for name in ('composition', 'baseline', 'candidate')))
    result['inputs'] = {name: dict(path=str(path.relative_to(ROOT)), sha256=sha(path.read_bytes())) for name,path in paths.items()}
    result['tools'] = {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in
        (Path(__file__), *(Path(__file__).with_name(name) for name in ('compiler.py','player.py','score.py','programs.py','stereo.py')))}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--composition', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.composition.resolve(), args.baseline.resolve(), args.candidate.resolve(), args.output.resolve())))


if __name__ == '__main__':
    main()
