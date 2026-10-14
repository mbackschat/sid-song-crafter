"""Prepare numeric Billie Jean and recheck pinned source execution records."""

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
import billie_jean_player as player
import billie_jean_programs as programs
import billie_jean_score as score


SOURCE_SHA = '16d8eae4d22f368520589c44e9db399b64092664bee6e1e70ca4b21c60bf0c54'
SCORE_DIRECTORY = ROOT / 'evidence/billie-jean-score'
FORM_DIRECTORY = ROOT / 'evidence/billie-jean-form'
SOUND_DIRECTORY = ROOT / 'evidence/billie-jean-sound'


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


def record_path(directory, name):
    plain = directory / name
    return plain if plain.exists() else directory / (name + '.gz')


def stores(records):
    return [{key: item[key] for key in ('phase', 'tick', 'address', 'value')} for item in records]


def contexts(records):
    return [{key: value for key, value in item.items() if key not in ('entryPc', 'exitPc')}
        for item in records]


def verify_contexts(computed, retained, calls, label):
    actual = [item for item in computed['contexts'] if item['call'] < calls]
    same(json.loads(json.dumps(actual)), contexts(retained), f'{label} named boundaries')
    states = {}
    for item in retained:
        if item['stage'] == 'age':
            states.setdefault(item['call'], {})[item['voice']] = item['after']
        elif item['stage'] == 'global-output':
            record = computed['returns'][item['call']]
            same(record['voices'], [states[item['call']][voice] for voice in range(3)], f'{label} return voices')
            require(record['filter'] == item['filterBefore'], f'{label} return filter differs at {item["call"]}')


def sound_edit(description, name):
    edited = deepcopy(description)
    if name == 'pulse-step':
        edited['instruments']['24']['pulse_step'] = 8
    elif name == 'vibrato-step':
        edited['instruments']['72']['vibrato_step'] = 16
    elif name == 'attack-pitch':
        edited['programs']['pitches'][8] = 212
    elif name == 'cutoff-start-and-step':
        edited['instruments']['24'].update(filter_start=33, filter_step=1)
    else:
        raise ValueError(f'Unexpected retained sound control: {name}')
    return edited


def verify(source, sound_receipt_path):
    source_bytes = source.read_bytes()
    require(sha(source_bytes) == SOURCE_SHA, 'Pinned Billie Jean source fingerprint differs')
    score_path = SCORE_DIRECTORY / 'score.json'
    score_receipt_path = SCORE_DIRECTORY / 'receipt.json'
    form_receipt_path = FORM_DIRECTORY / 'complete14274/receipt.json'
    return_path = FORM_DIRECTORY / 'complete14274/returns.json.gz'
    write_path = FORM_DIRECTORY / 'complete14274/writes.json.gz'
    edit_receipt_path = FORM_DIRECTORY / 'edit128/receipt.json'
    case_path = FORM_DIRECTORY / 'edit128/cases.json.gz'
    archived_paths = [score_path, score_receipt_path, form_receipt_path, return_path,
        write_path, edit_receipt_path, case_path]
    evidence.verify(paths=tuple(str(path.relative_to(ROOT)) for path in archived_paths))
    prepared_score = read(score_path)
    score_receipt, form_receipt = read(score_receipt_path), read(form_receipt_path)
    require(score_receipt['sourceSha256'] == SOURCE_SHA and score_receipt['playCalls'] == 14274
        and score_receipt['retainedExecutionRecheck'] and not score_receipt['freshCPUExecution'],
        'Expected verified portable retained score')
    require(form_receipt['passed'] and form_receipt['calls'] == 14274
        and form_receipt['inputs']['source']['sha256'] == SOURCE_SHA, 'Expected pinned complete original ledger')
    require(sha(Path(score.__file__).read_bytes()) == score_receipt['tools'][str(Path(score.__file__).relative_to(ROOT))],
        'Runtime score tool differs from its frozen proof')
    for name, path in (('returns.json.gz', return_path), ('writes.json.gz', write_path)):
        require(sha(raw_json(path)) == form_receipt['artifacts'][name]['decodedSha256'], f'Original {name} hash differs')
    sound_receipt = read(sound_receipt_path)
    require(sound_receipt['sourceSha256'] == SOURCE_SHA and sound_receipt['selectedSubtune'] == 1
        and sound_receipt['sidModel'] == 'MOS6581' and sound_receipt['clock'] == 'pal'
        and sound_receipt['playCalls'] == 7107 and sound_receipt['boundaryComparisons'] == 49749,
        'Expected complete selected sound proof through the first order wrap')
    require(sha(Path(programs.__file__).read_bytes()) == sound_receipt['toolHashes']['billie_jean_programs.py'],
        'Runtime sound tool differs from its frozen proof')
    sound_paths = {name: record_path(sound_receipt_path.parent, name) for name in sound_receipt['outputHashes']}
    for name, fingerprint in sound_receipt['outputHashes'].items():
        require(sha(raw_json(sound_paths[name])) == fingerprint, f'Retained sound output differs: {name}')
    if sound_receipt_path.resolve().is_relative_to(ROOT / 'evidence'):
        evidence.verify(paths=tuple(str(path.relative_to(ROOT)) for path in [sound_receipt_path, *sound_paths.values()]))
    initial = read(sound_paths['initialSound.json'])
    for voice, values in enumerate(initial['voices']):
        for name, score_field in player.SCORE_INPUTS.items():
            require(values.pop(name) == prepared_score['initialVoices'][voice][score_field],
                f'Captured cold score/sound alias differs: voice {voice} {name}')
    composition = dict(schema='billie-jean-composition-v1',
        target=dict(clock='pal', sidModel='MOS6581', sidBase=0xd400, frameCycles=19656),
        range=dict(auditCalls=14274), score=prepared_score, sound=read(sound_paths['description.json']),
        initialSound=initial, sourceEvidence=dict(sha256=SOURCE_SHA, selectedSubtune=1,
            sourceFlags=20, score='evidence/billie-jean-score/score.json',
            scoreSha256=sha(score_path.read_bytes()), sound='evidence/billie-jean-sound/description.json',
            soundSha256=sha(raw_json(sound_paths['description.json'])),
            initialSound='evidence/billie-jean-sound/initialSound.json',
            initialSoundSha256=sha(raw_json(sound_paths['initialSound.json'])),
            coldBoundary=0x14a5, scope='Numeric score, sound programs and cold named image; annotations never execute.'))
    computed = player.compute(composition, contexts=True)
    same(computed['writes'], stores(read(write_path)), 'Complete ordered original stores')
    original_returns = [{key: item[key] for key in ('tick', 'divider', 'voices')} for item in read(return_path)]
    same([item['score'] for item in computed['returns']], original_returns, 'Complete score return state')
    verify_contexts(computed, read(sound_paths['contexts.json']), sound_receipt['playCalls'], 'Original')
    duration_receipt = read(edit_receipt_path)
    require(duration_receipt['passed'] and duration_receipt['sourceSha256'] == SOURCE_SHA,
        'Expected pinned duration source-copy evidence')
    require(sha(raw_json(case_path)) == duration_receipt['artifact']['decodedSha256'], 'Duration archive differs')
    controls = []
    for case in read(case_path):
        offset = 126 + case['address'] - 0x1000
        require(source_bytes[offset] == case['originalByte'], 'Duration intervention source byte differs')
        changed = bytearray(source_bytes)
        changed[offset] = case['variantByte']
        require(sha(changed) == case['sourceVariantSha256'], 'Duration private-copy fingerprint differs')
        edited = deepcopy(composition)
        row = edited['score']['patterns']['1']['rows'][0]
        edited['score']['patterns']['1']['rows'][0] = score.set_duration(row, case['variantByte'] & 31)
        result = player.compute(edited, calls=duration_receipt['callsPerCase'])
        same(result['writes'], stores(case['orderedWrites']), 'Duration intervention stores')
        controls.append(dict(name=case['name'], kind='duration', calls=duration_receipt['callsPerCase'],
            sourceVariantSha256=case['sourceVariantSha256'], matchedWrites=len(result['writes']),
            noteCallsVoice0=case['noteCallsVoice0']))
    for control in sound_receipt['controls']:
        name, calls = control['name'], control['calls']
        offset = 126 + control['address'] - 0x1000
        require(source_bytes[offset] == control['original'], f'{name} source byte differs')
        changed = bytearray(source_bytes)
        changed[offset] = control['candidate']
        require(sha(changed) == control['candidateSha256'], f'{name} private-copy fingerprint differs')
        edited = deepcopy(composition)
        edited['sound'] = sound_edit(composition['sound'], name)
        require(edited['sound'] == read(sound_paths[f'{name}.description.json']), f'{name} portable edit differs')
        result = player.compute(edited, calls=calls, contexts=True)
        same(result['writes'], stores(read(sound_paths[f'{name}.writes.json'])), f'{name} intervention stores')
        verify_contexts(result, read(sound_paths[f'{name}.contexts.json']), calls, name)
        ports = set(control['declaredPorts'])
        baseline = [item for item in computed['writes'] if item['phase'] == 'init' or item['tick'] < calls]
        same([item for item in result['writes'] if item['address'] not in ports],
            [item for item in baseline if item['address'] not in ports], f'{name} outside declared ports')
        require(result['writes'] != baseline, f'{name} intervention is inactive')
        controls.append(dict(name=name, kind='sound', calls=calls, sourceVariantSha256=control['candidateSha256'],
            matchedWrites=len(result['writes']), matchedBoundaries=len(result['contexts']),
            declaredPorts=control['declaredPorts'], onlyDeclaredPortsChanged=True))
    require(source.read_bytes() == source_bytes, 'Original source changed')
    tools = [Path(__file__), Path(player.__file__), Path(programs.__file__), Path(score.__file__), ROOT / 'scripts/evidence.py']
    receipt = dict(schemaVersion=1, sourceSha256=SOURCE_SHA, sourceUnchanged=True,
        retainedExecutionRecheck=True, freshCPUExecution=False, freshNumericComputation=True,
        playCalls=14274, matchedWrites=len(computed['writes']), matchedScoreReturns=len(computed['returns']),
        matchedSoundCalls=sound_receipt['playCalls'], matchedBoundaries=sound_receipt['boundaryComparisons'],
        coldStateSourceBoundary=0x14a5, controls=controls,
        inputs={str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in archived_paths},
        soundReceiptSha256=sha(sound_receipt_path.read_bytes()), soundOutputHashes=sound_receipt['outputHashes'],
        producerSoundToolHashes=sound_receipt['toolHashes'], producerOracleToolHashes=sound_receipt['oracleToolHashes'],
        tools={str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in tools},
        limits='Independent numeric integration matches all retained original init/play stores and score returns across 14,274 calls, plus 7,107-call named sound boundaries and six retained source-copy cases. Runtime consumes numeric score/sound/cold state only. No new CPU/VICE traversal in this checker, compiled export, bus timing, acoustic recurrence, authored ending or listening verdict.')
    return composition, computed, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/research/billie-jean/Billie_Jean.sid')
    parser.add_argument('--sound-receipt', type=Path, default=SOUND_DIRECTORY / 'receipt.json')
    parser.add_argument('--output', type=Path, required=True, help='Fresh numeric proof directory')
    args = parser.parse_args()
    require(not args.output.exists() and not args.output.is_symlink(), 'Output exists; choose a fresh directory')
    composition, computed, receipt = verify(args.source, args.sound_receipt)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'composition.json').write_text(json.dumps(composition, indent=2) + '\n')
    for name in ('writes', 'returns', 'contexts'):
        with (args.output / f'{name}.json').open('x') as output:
            json.dump(computed[name], output, separators=(',', ':'))
            output.write('\n')
    receipt['outputHashes'] = {path.name: sha(path.read_bytes()) for path in args.output.iterdir()}
    (args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({key: receipt[key] for key in ('playCalls', 'matchedWrites', 'matchedScoreReturns',
        'matchedSoundCalls', 'matchedBoundaries', 'retainedExecutionRecheck', 'freshCPUExecution')}))


if __name__ == '__main__':
    try:
        main()
    except (KeyError, OSError, ValueError, IndexError, TypeError) as error:
        raise SystemExit(f'Billie Jean numeric integration failed: {error}')
