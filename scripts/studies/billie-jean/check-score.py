"""Prepare portable Billie Jean rows and recheck the pinned retained score proof."""

import argparse
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import evidence
import billie_jean_score as score


SOURCE_SHA = '16d8eae4d22f368520589c44e9db399b64092664bee6e1e70ca4b21c60bf0c54'
EVIDENCE = ROOT / 'evidence/billie-jean-form'
INPUT_NAMES = (
    'score.py', 'probe.py', 'contract.json', 'summary.json',
    'complete14274/receipt.json', 'complete14274/preflight.json', 'complete14274/score.json',
    'complete14274/audit.json', 'complete14274/hooks.json', 'complete14274/reads.json.gz',
    'complete14274/rows.json.gz', 'complete14274/returns.json.gz', 'complete14274/writes.json.gz',
    'edit128/receipt.json', 'edit128/cases.json.gz',
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def raw_json(path):
    raw = path.read_bytes()
    return gzip.decompress(raw) if path.suffix == '.gz' else raw


def read(path):
    return json.loads(raw_json(path))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def same(actual, expected, label):
    if actual != expected:
        index = next((index for index, pair in enumerate(zip(actual, expected)) if pair[0] != pair[1]),
                     min(len(actual), len(expected)))
        raise ValueError(f'{label} differs at {index}: computed={actual[index:index + 1]}, retained={expected[index:index + 1]}')


def source_ram(data):
    """Decode the fingerprinted payload; this performs no callable CPU admission."""
    offset = int.from_bytes(data[6:8], 'big')
    load = int.from_bytes(data[8:10], 'big')
    payload = data[offset:]
    if load == 0:
        load = int.from_bytes(payload[:2], 'little')
        payload = payload[2:]
    require(load == 0x1000 and load + len(payload) == 0x1ead, 'Pinned payload extent differs')
    ram = [0] * 65536
    ram[load:load + len(payload)] = payload
    return ram


def legacy_description(value):
    return dict(schema='billie-jean-score-v1', initialDivider=0,
        rowDividerReload=value['rowDividerReload'], initialVoices=value['initialVoices'],
        orders=[dict(sourceAddress=order['address'], bytes=order['bytes']) for order in value['orders']],
        patterns={str(index): dict(sourceAddress=pattern['address'],
            rows=[{field: value for field, value in row.items()
                   if field in ('header', 'instrument', 'glideStep', 'glideTarget', 'note')}
                  for row in pattern['rows']]) for index, pattern in value['patterns'].items()})


def verify(source):
    data = source.read_bytes()
    require(sha(data) == SOURCE_SHA, 'Pinned Billie Jean source fingerprint differs')
    paths = [EVIDENCE / name for name in INPUT_NAMES]
    evidence.verify(paths=tuple(str(path.relative_to(ROOT)) for path in paths))
    archived = read(EVIDENCE / 'complete14274/receipt.json')
    contract = read(EVIDENCE / 'contract.json')
    require(archived['passed'] and archived['calls'] == 14274 and contract['sourceSha256'] == SOURCE_SHA,
            'Expected the complete pinned Billie Jean score proof')
    require(archived['inputs']['source']['sha256'] == SOURCE_SHA, 'Retained source identity differs')
    for name, key in (('score.py', 'model'), ('probe.py', 'probe')):
        require(sha((EVIDENCE / name).read_bytes()) == archived['inputs'][key]['sha256'],
                f'Frozen {name} bytes differ from the executed proof')
    for name, fingerprint in archived['artifacts'].items():
        require(sha(raw_json(EVIDENCE / 'complete14274' / name)) == fingerprint['decodedSha256'],
                f'Frozen decoded artifact differs: {name}')
    description = score.decode(source_ram(data))
    retained_score = read(EVIDENCE / 'complete14274/score.json')
    require(description == legacy_description(retained_score), 'Portable source decode differs from retained numeric data')
    description['sourceEvidence'] = dict(sha256=SOURCE_SHA, selectedSubtune=1,
        declaredClock='pal', declaredSidModel='MOS6581', sourceFlags=20,
        retainedCalls=archived['calls'], retainedScoreSha256=sha((EVIDENCE / 'complete14274/score.json').read_bytes()),
        scope='Pinned selected score only; source addresses label observations. No sound programs, stores or musical ending.')
    computed = score.expand(description, archived['calls'])
    wanted_reads = read(EVIDENCE / 'complete14274/reads.json.gz')
    wanted_rows = read(EVIDENCE / 'complete14274/rows.json.gz')
    wanted_returns = [{field: value[field] for field in ('tick', 'divider', 'voices')}
                      for value in read(EVIDENCE / 'complete14274/returns.json.gz')]
    row_projection = [{field: row[field] for field in ('tick', 'voice', 'address', 'header', 'kind', 'state')}
                      for row in computed['rows']]
    same(computed['reads'], wanted_reads, 'Full score reads')
    same(row_projection, wanted_rows, 'Full score rows')
    same(computed['returns'], wanted_returns, 'Full score return states')
    same(computed['wraps'], archived['globalWraps'], 'Global order wraps')
    edit_receipt = read(EVIDENCE / 'edit128/receipt.json')
    require(edit_receipt['passed'] and edit_receipt['sourceSha256'] == SOURCE_SHA, 'Pinned duration intervention differs')
    cases = read(EVIDENCE / 'edit128/cases.json.gz')
    require(sha(raw_json(EVIDENCE / 'edit128/cases.json.gz')) == edit_receipt['artifact']['decodedSha256'],
            'Retained duration observations differ')
    edits = []
    for case in cases:
        offset = 126 + case['address'] - 0x1000
        require(data[offset] == case['originalByte'], 'Duration source address differs')
        changed = bytearray(data)
        changed[offset] = case['variantByte']
        require(sha(changed) == case['sourceVariantSha256'], 'Private duration-copy fingerprint differs')
        edited = deepcopy(description)
        edited['patterns']['1']['rows'][0] = score.set_duration(edited['patterns']['1']['rows'][0], case['variantByte'] & 31)
        decoded = score.decode(source_ram(changed))
        same([edited[key] for key in ('orders', 'patterns', 'initialVoices')],
             [decoded[key] for key in ('orders', 'patterns', 'initialVoices')], 'Source-data duration edit')
        result = score.expand(edited, edit_receipt['callsPerCase'])
        same(result['reads'], case['scoreReads'], 'Retained duration score reads')
        onsets = [row['tick'] for row in result['rows'] if row['voice'] == 0 and row['kind'] == 'note']
        same(onsets, case['noteCallsVoice0'], 'Retained duration note calendar')
        edits.append(dict(name=case['name'], sourceVariantSha256=case['sourceVariantSha256'],
            headerAddress=case['address'], header=case['variantByte'],
            matchedReads=len(result['reads']), noteCallsVoice0=onsets))
    require(source.read_bytes() == data, 'Original source changed')
    receipt = dict(schemaVersion=1, sourceSha256=SOURCE_SHA, sourceUnchanged=True,
        retainedExecutionRecheck=True, freshCPUExecution=False, freshSourceDataDecode=True,
        playCalls=archived['calls'], matchedReads=len(computed['reads']), matchedRows=len(computed['rows']),
        matchedReturnStates=len(computed['returns']), globalWraps=computed['wraps'], durationControls=edits,
        frozenModelSha256=sha((EVIDENCE / 'score.py').read_bytes()),
        frozenProbeSha256=sha((EVIDENCE / 'probe.py').read_bytes()),
        inputs={str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in paths},
        tools={str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in
               (Path(__file__), Path(score.__file__), ROOT / 'scripts/evidence.py')},
        limits='New portable header-owned numeric score matches pinned retained source reads/rows/returns and two128-call source-copy calendars. Frozen evidence and historical execution-tool pins are preserved. No new CPU/VICE execution, sound/store synthesis, compiled export, acoustic recurrence, finite musical ending or listening verdict.')
    return description, computed, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/research/billie-jean/Billie_Jean.sid')
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument('--output', type=Path, help='Fresh score proof directory')
    destination.add_argument('--check', type=Path, help='Check exact prepared score bytes without writing')
    args = parser.parse_args()
    if args.output is not None:
        require(not args.output.exists() and not args.output.is_symlink(), 'Score output exists; choose a fresh directory')
    description, computed, receipt = verify(args.source)
    prepared = (json.dumps(description, indent=2) + '\n').encode()
    if args.check is not None:
        require(args.check.read_bytes() == prepared, 'Prepared score differs; regenerate from the pinned source')
    else:
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / 'score.json').write_bytes(prepared)
        for name in ('reads', 'rows', 'returns'):
            with (args.output / f'{name}.json').open('x') as output:
                json.dump(computed[name], output, separators=(',', ':'))
                output.write('\n')
        (args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({key: receipt[key] for key in ('playCalls', 'matchedReads', 'matchedRows',
        'matchedReturnStates', 'globalWraps', 'retainedExecutionRecheck', 'freshCPUExecution')}))


if __name__ == '__main__':
    try:
        main()
    except (KeyError, OSError, ValueError, IndexError) as error:
        raise SystemExit(f'Billie Jean score preparation failed: {error}')
