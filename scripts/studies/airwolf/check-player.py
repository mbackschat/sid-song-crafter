"""Recheck retained Airwolf source records using the new editable numeric player."""

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
import airwolf_player as player


SOURCE_SHA = '03c602da9182759c78ca4d90ad3bd5b223b3eb61f34ea31c2205fffc589bf89f'
ARCHIVE = ROOT / 'evidence/airwolf-form'
INPUT_NAMES = ('model.py', 'probe.py', 'check-edits.py', 'edits.json.gz',
    'complete/receipt.json', 'complete/score.json', 'complete/audit.json',
    'complete/reads.json.gz', 'complete/states.json.gz', 'complete/writes.json.gz')


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


def stores(records):
    return [{key: item[key] for key in ('phase', 'tick', 'address', 'value')} for item in records]


def verify(source):
    source_bytes = source.read_bytes()
    require(sha(source_bytes) == SOURCE_SHA, 'Pinned Airwolf source fingerprint differs')
    paths = [ARCHIVE / name for name in INPUT_NAMES]
    evidence.verify(paths=tuple(str(path.relative_to(ROOT)) for path in paths))
    retained = read(ARCHIVE / 'complete/receipt.json')
    require(retained['sourceSha256'] == SOURCE_SHA and retained['calls'] == 2500
        and retained['cycleCalls'] == 1242 and retained['scoreRows'] == 138
        and retained['restartCalls'] == [1241, 2483], 'Expected complete selected Airwolf proof')
    for name, field in (('model.py', 'modelSha256'), ('probe.py', 'probeSha256')):
        require(sha((ARCHIVE / name).read_bytes()) == retained[field], f'Frozen {name} bytes differ')
    for name, meta in retained['artifacts'].items():
        raw = (ARCHIVE / 'complete' / name).read_bytes()
        require(sha(raw) == meta['sha256'] and sha(raw_json(ARCHIVE / 'complete' / name)) == meta['decodedSha256'],
            f'Frozen source record differs: {name}')
    score = read(ARCHIVE / 'complete/score.json')
    require(score['sourceSha256'] == SOURCE_SHA, 'Retained score source identity differs')
    composition = player.from_score(score, calls=retained['calls'])
    composition['sourceEvidence'].update(score='evidence/airwolf-form/complete/score.json',
        scoreSha256=sha((ARCHIVE / 'complete/score.json').read_bytes()),
        sourceFlags=20, selectedSubtune=1, scope='Selected native rows and fixed patches; addresses label observations only.')
    computed = player.compute(composition)
    original_writes = read(ARCHIVE / 'complete/writes.json.gz')
    same(computed['writes'], stores(original_writes), 'Complete original ordered stores')
    same(computed['reads'], read(ARCHIVE / 'complete/reads.json.gz'), 'Complete consumed source fields')
    same(computed['restartCalls'], retained['restartCalls'], 'Internal restart calls')
    pointers = [row['sourceAddress'] for row in score['rows']] + [score['terminatorAddress']]
    named = [computed['initial'], *computed['returns']]
    source_states = read(ARCHIVE / 'complete/states.json.gz')
    same([dict(phase='init' if item['tick'] is None else 'play', tick=item['tick'],
        rowPointer=pointers[item['nextRow']], countdown=item['countdown']) for item in named],
        [{key: item[key] for key in ('phase', 'tick', 'rowPointer', 'countdown')} for item in source_states],
        'Named source pointer/countdown states')
    edits = read(ARCHIVE / 'edits.json.gz')
    require(edits['sourceSha256'] == SOURCE_SHA and edits['originalUnchanged'] and edits['callsPerCase'] == 128,
        'Expected retained private-copy controls')
    require(sha((ARCHIVE / 'check-edits.py').read_bytes()) == edits['checkerSha256']
        and sha((ARCHIVE / 'model.py').read_bytes()) == edits['modelSha256'] and edits['tools'] == retained['tools'],
        'Frozen control tool pins differ')
    controls = []
    for case in edits['cases']:
        offset = 126 + case['address'] - 0x3add
        require(source_bytes[offset] == case['before'], f'{case["name"]} source byte differs')
        changed = bytearray(source_bytes)
        changed[offset] = case['after']
        require(sha(changed) == case['privateVariantSha256'], f'{case["name"]} private-copy fingerprint differs')
        edited = deepcopy(composition)
        if case['name'] == 'first-frequency-low':
            word = edited['rows'][0]['notes'][0]
            edited['rows'][0]['notes'][0] = (word & 65280) | case['after']
        elif case['name'] == 'first-duration':
            edited['rows'][0]['duration'] = case['after']
        else:
            raise ValueError(f'Unexpected retained intervention {case["name"]}')
        result = player.compute(edited, calls=128)
        same(result['writes'], stores(case['orderedWrites']), f'{case["name"]} edited stores')
        baseline = [item for item in computed['writes'] if item['tick'] is None or item['tick'] < 128]
        require(result['writes'] != baseline, f'{case["name"]} is inactive')
        if case['name'] == 'first-frequency-low':
            differences = [(a, b) for a, b in zip(result['writes'], baseline) if a != b]
            require(len(result['writes']) == len(baseline) and len(differences) == 1
                and differences[0][0]['phase'] == 'init' and differences[0][0]['address'] == 0xd400,
                'Pitch intervention changed another port or call')
        controls.append(dict(name=case['name'], calls=128, sourceVariantSha256=case['privateVariantSha256'],
            matchedWrites=len(result['writes'])))
    require(source.read_bytes() == source_bytes, 'Original source changed')
    receipt = dict(schemaVersion=1, sourceSha256=SOURCE_SHA, sourceUnchanged=True,
        retainedExecutionRecheck=True, freshCPUExecution=False, freshNumericComputation=True,
        playCalls=2500, matchedWrites=len(computed['writes']), matchedReads=len(computed['reads']),
        matchedPointerCountdownStates=len(named), derivedRegisterShadowStates=len(named),
        initialState=computed['initial'], restartCalls=computed['restartCalls'], controls=controls,
        producerToolPins=retained['tools'], frozenModelSha256=retained['modelSha256'], frozenProbeSha256=retained['probeSha256'],
        inputs={str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in paths},
        tools={str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in
            (Path(__file__), Path(player.__file__), ROOT / 'scripts/evidence.py')},
        limits='Independent editable numeric player matches retained2500-call source stores/reads, explicit pointer/countdown states and both128-call private-copy interventions. Register shadows describe emitted ports only; unwritten pulse-low/filter and SID internal state depend on caller/reset state. No original CPU/VICE execution in this checker, compiled export, bus timing, audio identity, indefinite playback or listening verdict. Authored off/ending and editable fixed parameters are separate numeric/compiled contracts.')
    return composition, computed, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/research/airwolf/Airwolf.sid')
    parser.add_argument('--output', type=Path, required=True, help='Fresh retained numeric proof directory')
    args = parser.parse_args()
    require(not args.output.exists() and not args.output.is_symlink(), 'Output exists; choose a fresh directory')
    composition, computed, receipt = verify(args.source)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'composition.json').write_text(json.dumps(composition, indent=2) + '\n')
    for name in ('writes', 'returns', 'reads'):
        with (args.output / f'{name}.json').open('x') as output:
            json.dump(computed[name], output, separators=(',', ':'))
            output.write('\n')
    receipt['outputHashes'] = {path.name: sha(path.read_bytes()) for path in args.output.iterdir()}
    (args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({key: receipt[key] for key in ('playCalls', 'matchedWrites', 'matchedReads',
        'matchedPointerCountdownStates', 'restartCalls', 'retainedExecutionRecheck', 'freshCPUExecution')}))


if __name__ == '__main__':
    try:
        main()
    except (KeyError, OSError, ValueError, TypeError, IndexError) as error:
        raise SystemExit(f'Airwolf retained numeric check failed: {error}')
