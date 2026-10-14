"""Select one complete Take On Me traversal and declare an authored release tail."""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = 'evidence/take-on-me-player/composition.json'
SOURCE_SHA256 = 'b9c8756a86a151cf7c23ec8ff9547a6f8512f103a4eb0168a1aba63247471df3'
DEFAULT_OUTPUT = ROOT / 'songs/studies/take-on-me-reconstruction'


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()


def prepare(raw):
    """Keep the verified musical inputs exact; add only form and ending metadata.

    The first wrap at call 4864 is established by evidence/take-on-me-form/receipt.json.
    All three gates are already closed at call 4863 in its ordered ledger; a
    32-call held release is an initial rendering choice, not listening approval.
    """
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('Canonical composition fingerprint differs')
    title = json.loads(raw)
    title['title'] = 'Take On Me independent title'
    title['author'] = 'PVL / SID Song Crafter'
    title['ending'] = dict(startCall=4864, releaseCalls=32)
    title['range'] = dict(auditCalls=4961)
    title['sourceEvidence']['titlePreparation'] = dict(
        composition=SOURCE, compositionSha256=SOURCE_SHA256,
        originalComposition='a-ha: Take On Me', sidArrangement='Pascal van Loosbroek (PVL)',
        musicCalls=[0, 4864], authoredEnding=title['ending'],
        scope='Original introduction and first loop; explicitly authored held release, then stop.')
    report = dict(schemaVersion=1, source=SOURCE, sourceSha256=SOURCE_SHA256,
        originalSourceModel='unknown', workingTarget=title['target'],
        musicCalls=4864, releaseCalls=32, stopCall=4896, confirmationCalls=64,
        auditCalls=4961, artificialFade=False,
        endingBasis='Explicitly authored gate closure with frozen modulation for 32 calls, then controls and master volume zero; later calls emit no stores.',
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
        raise SystemExit(f'Take On Me preparation failed: {error}')
