"""Verify Billie Jean's first global order wrap in the controlled VICE host."""

import argparse
import gzip
import importlib.util
import json
from pathlib import Path

from probe import HERE, ROOT, PINS, SOURCE_SHA, fingerprint, sha

TRACER_SHA = '18a21e373d7dcd679771c256fa6d930106718246cb3e0c7647329d985eb73352'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ledger', type=Path, default=HERE / 'complete14274/writes.json.gz')
    parser.add_argument('--vice', type=Path, default=ROOT / '.tools/vice-headless-3.9/build/src/x64sc')
    parser.add_argument('--data', type=Path, default=Path('/Applications/vice-arm64-gtk3-3.9/VICE.app/Contents/Resources/share/vice'))
    args = parser.parse_args()
    args.output, args.ledger, args.vice = (path.resolve() for path in (args.output, args.ledger, args.vice))
    if args.output.exists() or args.output.is_symlink():
        raise ValueError('Choose a fresh output directory')
    source = ROOT / '.local/research/billie-jean/Billie_Jean.sid'
    original = source.read_bytes()
    assert sha(original) == SOURCE_SHA
    for name, expected in PINS.items():
        assert sha((ROOT / 'scripts' / name).read_bytes()) == expected, name
    tracer_path = ROOT / 'scripts/trace-sid-vice.py'
    assert sha(tracer_path.read_bytes()) == TRACER_SHA
    raw = gzip.decompress(args.ledger.read_bytes())
    ledger = json.loads(raw)
    first, last = 7100, 7112
    projected = [row for row in ledger if row['phase'] == 'init' or first <= row['tick'] <= last]
    assert len({row['tick'] for row in ledger if row['phase'] == 'play'}) >= last + 1
    inputs = dict(source=fingerprint(source), ledger=fingerprint(args.ledger),
                  tracer=fingerprint(tracer_path), recipe=fingerprint(Path(__file__)),
                  vice=fingerprint(args.vice), tools=PINS)
    args.output.mkdir(parents=True)
    (args.output / 'preflight.json').write_text(json.dumps(inputs, indent=2) + '\n')
    (args.output / 'vice-wrap-executed.py').write_bytes(Path(__file__).read_bytes())
    oracle_path = args.output / 'oracle.json'
    oracle_path.write_text(json.dumps(projected, indent=2) + '\n')
    projection = dict(sourceLedger=inputs['ledger'], decodedSha256=sha(raw), firstCall=first,
        lastCallInclusive=last, records=len(projected), oracle=fingerprint(oracle_path),
        rule='All init plus the inclusive play window, retaining complete record fields and order.')
    (args.output / 'projection.json').write_text(json.dumps(projection, indent=2) + '\n')
    spec = importlib.util.spec_from_file_location('billie_vice_trace', tracer_path)
    tracer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tracer)
    result = tracer.run_trace(source, oracle_path, args.output / 'trace', first, last,
        args.vice, args.data, profile='pal-banked', subtune=1, timeout=180)
    assert source.read_bytes() == original
    provenance = dict(schemaVersion=1, inputs=inputs, firstCall=first, lastCallInclusive=last,
        sourceUnchanged=True, verification=result['verification'],
        artifacts={name: fingerprint(args.output / name) for name in ('projection.json', 'oracle.json',
            'trace/study.json', 'trace/trace.json')},
        limits='All preceding host calls execute; only init and selected wrap-window stores are compared. Parsed checkpoints do not establish exact SID bus cycles or original-game cadence. No audio or listening result.')
    (args.output / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(provenance, indent=2))


if __name__ == '__main__':
    main()
