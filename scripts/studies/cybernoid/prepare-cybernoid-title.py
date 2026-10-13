"""Prepare Cybernoid II's editable first title cycle from pinned numeric evidence."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CANONICAL_EVIDENCE = 'evidence/cybernoid-editable-data/title-runtime.json.gz'
CANONICAL_SHA256 = 'e56ed96c2a4dd6e9bacbbddf25253537c9d783b63dd986f2e7aaeb1b78179816'
CYCLE_CALLS = 17280
PLAY_CALLS = 17408


def read_source(path):
    """Load the pinned decompressed evidence bytes without opening the original SID."""
    raw = gzip.decompress(path.read_bytes())
    if hashlib.sha256(raw).hexdigest() != CANONICAL_SHA256:
        raise ValueError('Canonical Cybernoid evidence fingerprint differs from the pinned raw SHA-256')
    return json.loads(raw)


def without_evidence(value):
    if isinstance(value, dict):
        return {key: without_evidence(item) for key, item in value.items() if key != 'sourceEvidence'}
    if isinstance(value, list):
        return [without_evidence(item) for item in value]
    return value


def prepare_title(source):
    """Preserve calls [0, 17280) and append the declared release/fade contract.

    Numeric tables, commands and cold state are copied without interpretation.
    The first order cycle remains unchanged; the finite tail is a deliberate
    arrangement addition, and no second-cycle rows are retained.
    """
    if not isinstance(source, dict) or source.get('format') != 'cybernoid-editable-title-v1':
        raise ValueError('Source requires the Cybernoid editable-title format')
    declared = source.get('play_calls')
    if type(declared) is not int or declared < CYCLE_CALLS:
        raise ValueError('Source must contain the complete first title cycle')
    if not isinstance(source.get('rows'), list):
        raise ValueError('Source requires semantic rows')
    for row in source['rows']:
        tick = row.get('call') if isinstance(row, dict) else None
        if type(tick) is not int or not 0 <= tick < declared:
            raise ValueError('Source row call must be an integer inside the declared range')
    title = without_evidence(source)
    title['play_calls'] = PLAY_CALLS
    title['rows'] = [row for row in title['rows'] if row['call'] < CYCLE_CALLS]
    title['ending'] = {'start_call': CYCLE_CALLS, 'release_calls': 64, 'fade_step_calls': 4}
    evidence = source['sourceEvidence']
    title['sourceEvidence'] = {
        'identity': 'Cybernoid II title, first complete order cycle, with an added finite release/fade.',
        'canonicalEvidence': {'path': CANONICAL_EVIDENCE, 'rawSha256': CANONICAL_SHA256},
        'originalSid': {
            'sha256': evidence['source']['sha256'],
            'url': evidence['sourceUrl'],
            'title': 'Cybernoid II',
            'music': 'Jeroen Tel',
            'release': '1988 Hewson',
            'driver': 'Charles Deenen (recovered MUSICFILE driver)',
        },
        'selectedSubtune': evidence['selectedSubtune'],
        'profile': evidence['profile'],
        'preservedCalls': [0, CYCLE_CALLS],
        'deliberateChanges': ['Replace the order restart with 64 release calls followed by a four-call-step fade; stop after 128 tail calls.'],
    }
    return title


def encoded(value):
    """Encode editable tables normally and keep each semantic row on one line."""
    entries = []
    for name, item in value.items():
        if name == 'rows':
            rows = ',\n'.join('    ' + json.dumps(row, ensure_ascii=False, allow_nan=False) for row in item)
            text = '[\n' + rows + '\n  ]'
        else:
            text = json.dumps(item, indent=2, ensure_ascii=False, allow_nan=False).replace('\n', '\n  ')
        entries.append('  ' + json.dumps(name) + ': ' + text)
    return ('{\n' + ',\n'.join(entries) + '\n}\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / CANONICAL_EVIDENCE)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/title/cybernoid-title.json',
                        help='Fresh output path; defaults to build/title/cybernoid-title.json')
    parser.add_argument('--check', action='store_true', help='Verify an existing output without changing it')
    args = parser.parse_args()
    title = prepare_title(read_source(args.source))
    payload = encoded(title)
    if args.check:
        if args.output.read_bytes() != payload:
            raise ValueError(f'Saved title differs from the prepared canonical output: {args.output}')
    else:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError('Choose a fresh output; use --check to verify an existing title')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('xb') as handle:
            handle.write(payload)
    print(json.dumps({
        'canonicalEvidenceRawSha256': CANONICAL_SHA256,
        'titleSha256': hashlib.sha256(payload).hexdigest(),
        'selectedRows': len(title['rows']),
        'preservedCalls': [0, CYCLE_CALLS],
        'playCalls': PLAY_CALLS,
        'ending': title['ending'],
    }, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(str(error))
