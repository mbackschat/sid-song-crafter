"""Prepare Airwolf's verified first traversal with a separate authored release."""

import argparse
import hashlib
import json
from pathlib import Path

import airwolf_player as player


ROOT = Path(__file__).resolve().parents[3]
SOURCE = 'evidence/airwolf-form/complete/score.json'
SOURCE_SHA256 = '1d658def8d8219c359b32f1ea2497def3e3d20e0526d34ac207f187e6981e3c6'
DEFAULT_OUTPUT = ROOT / 'songs/studies/airwolf-reconstruction'


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()


def prepare(raw):
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('Pinned Airwolf score fingerprint differs')
    source = json.loads(raw)
    cycle = sum(row['duration'] + 1 for row in source['rows'])
    if cycle != 1242 or len(source['rows']) != 138:
        raise ValueError('Pinned first traversal differs')
    title = player.from_score(source, calls=1338)
    title.update(title='Airwolf independent title', author='M. Cooksey / SID Song Crafter',
        ending=dict(startCall=1241, releaseCalls=32))
    title['sourceEvidence']['titlePreparation'] = dict(score=SOURCE, scoreSha256=SOURCE_SHA256,
        originalComposition='Sylvester Levay: Airwolf Theme', sidArrangement='Mark Cooksey',
        musicPlayCalls=[0, 1241], authoredEnding=title['ending'])
    report = dict(schemaVersion=1, source=SOURCE, sourceSha256=SOURCE_SHA256, workingTarget=title['target'],
        cycleUpdatesIncludingInit=1242, musicPlayCalls=1241, releaseCalls=32, stopCall=1273,
        confirmationCalls=64, auditCalls=1338, sourcePrefixStores=5586, artificialFade=False,
        initTiming='Init consumes row0 at grid frame0; play call t is grid frame t+1.',
        endingBasis='Preserve init and calls0..1240. Before the internal restart at1241, close held gates and freeze row processing/fixed writes for32calls; zero controls/master volume at1273, then verify64 write-free calls.',
        hardwareInitialization='Only observed source ports are written; pulse-low/filter and SID internal state depend on the caller or renderer reset.',
        listeningStatus='Pending compiled verification, rendered tail measurement and human listening.',
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
    print(json.dumps(dict(output=str(args.output), auditCalls=results[1]['auditCalls'], stopCall=results[1]['stopCall'])))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f'Airwolf title preparation failed: {error}')
