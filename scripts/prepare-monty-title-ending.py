"""Prepare the first complete Monty order cycle with a deliberate release/fade."""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DESCRIPTION_SHA256 = 'c1597b914360bc80d68323033423beb6286b95088e4d72f943bf53d8f89424fc'


def encoded(value):
    return (json.dumps(value, indent=2) + '\n').encode()


def prepare_title(source):
    """Retain the measured first cycle and append an explicit arranged ending.

    The source pin binds the fixed call 17536 boundary to the two observed
    traversals in evidence/monty-form/full40000/summary.json. Edit the returned
    description for new arrangements; this source-specific preparation does
    not infer the end of arbitrary modified scores.
    """
    if hashlib.sha256(encoded(source)).hexdigest() != SOURCE_DESCRIPTION_SHA256:
        raise ValueError('Expected the pinned Monty title source description')
    result = deepcopy(source)
    result.update(play_calls=17664, ending=dict(start_call=17536, release_calls=64, fade_step_calls=4))
    result['sourceEvidence']['arrangement'] = dict(
        sourceDescription='songs/monty-title-source.json', sourceDescriptionSha256=SOURCE_DESCRIPTION_SHA256,
        musicCalls=[0, 17536], formEvidence='evidence/monty-form/full40000/summary.json',
        endingDifference='The original restarts at call 17536; this arrangement freezes the score, closes output gates, continues 64 release calls and fades through 16 four-call levels.',
        listeningStatus='Pending; numeric preparation does not establish musical quality.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'songs/monty-title-source.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'songs/monty-title.json')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = encoded(prepare_title(json.loads(args.source.read_bytes())))
    if args.check:
        if args.output.read_bytes() != data:
            raise ValueError('Saved title differs from the prepared first cycle and ending')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('xb') as output:
            output.write(data)
    print(json.dumps(dict(path=str(args.output), sha256=hashlib.sha256(data).hexdigest(), checked=args.check)))


if __name__ == '__main__':
    main()
