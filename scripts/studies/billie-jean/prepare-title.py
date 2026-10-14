"""Select Billie Jean's complete first traversal and an explicit release tail."""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = 'evidence/billie-jean-player/composition.json'
SOURCE_SHA256 = '96d551545f6532b385efde01b8823045ed9b26d1fd2407d90d89783bdd9d1164'
DEFAULT_OUTPUT = ROOT / 'songs/studies/billie-jean-reconstruction'


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()


def prepare(raw):
    """Preserve verified musical data and replace the first loop restart.

    evidence/billie-jean-form/complete14274/returns.json.gz places the global
    wrap at call 7106. Its ordered ledger has all three gates low after 7105;
    a 32-call held release is a first rendering choice, not listening approval.
    """
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('Canonical composition fingerprint differs')
    title = json.loads(raw)
    title['title'] = 'Billie Jean independent title'
    title['author'] = 'J. Bjerregaard / SID Song Crafter'
    title['ending'] = dict(startCall=7106, releaseCalls=32)
    title['range'] = dict(auditCalls=7203)
    title['sourceEvidence']['titlePreparation'] = dict(
        composition=SOURCE, compositionSha256=SOURCE_SHA256,
        originalComposition='Michael Jackson: Billie Jean', sidArrangement='Johannes Bjerregaard',
        musicCalls=[0, 7106], authoredEnding=title['ending'],
        scope='Initialized first traversal; explicitly authored held release, then stop.')
    report = dict(schemaVersion=1, source=SOURCE, sourceSha256=SOURCE_SHA256,
        workingTarget=title['target'], musicCalls=7106, releaseCalls=32, stopCall=7138,
        confirmationCalls=64, auditCalls=7203, artificialFade=False,
        endingBasis='Preserve all source stores through call 7105; close any held gates before call 7106, freeze modulation for 32 calls, then zero controls and master volume while retaining filter mode. Later calls emit no stores.',
        sourcePrefixStores=138696,
        sourceBoundaryEvidence='evidence/billie-jean-form/complete14274/returns.json.gz',
        sourceStoreEvidence='evidence/billie-jean-form/complete14274/writes.json.gz',
        listeningStatus='Pending compiled execution, rendered tail measurement and human listening.',
        compositionSha256=hashlib.sha256(encoded(title)).hexdigest())
    return title, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    results = prepare((ROOT / SOURCE).read_bytes())
    if not args.check:
        args.output.mkdir(parents=True, exist_ok=False)
    for name, value in zip(('composition.json', 'preparation.json'), results):
        path = args.output / name
        if args.check:
            if path.read_bytes() != encoded(value):
                raise ValueError(f'{path} differs from deterministic preparation')
        else:
            path.write_bytes(encoded(value))
    print(json.dumps(dict(output=str(args.output), auditCalls=results[1]['auditCalls'],
                         stopCall=results[1]['stopCall'])))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f'Billie Jean preparation failed: {error}')
