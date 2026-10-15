"""Recheck independent numeric music against hash-bound retained source records."""

import argparse
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import evidence
import listening_package

spec = importlib.util.spec_from_file_location('ghostbusters_checked_player', Path(__file__).with_name('player.py'))
player = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = player
spec.loader.exec_module(player)
SOURCE_SHA = player.score.SOURCE_SHA
SOURCE_PATH = '.local/research/ghostbusters/Ghostbusters.sid'
SCORE_TOOLS = {'scripts/studies/ghostbusters/score.py', 'scripts/studies/ghostbusters/probe-form.py', 'scripts/sid_clock.py'}
SOUND_TOOLS = SCORE_TOOLS | {'scripts/studies/ghostbusters/programs.py', 'scripts/studies/ghostbusters/sound-probe.py'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def record_path(path):
    return path if path.exists() else path.with_suffix(path.suffix + '.gz')


def raw_json(path):
    raw = record_path(path).read_bytes()
    return gzip.decompress(raw) if record_path(path).suffix == '.gz' else raw


def read(path):
    return json.loads(raw_json(path))


def same(actual, expected, label):
    if actual != expected:
        index = next((index for index, pair in enumerate(zip(actual, expected)) if pair[0] != pair[1]),
                     min(len(actual), len(expected)))
        raise ValueError(f'{label} differs at {index}: computed={actual[index:index + 1]}, retained={expected[index:index + 1]}')


def verify_dependencies(stage, required, *, root=ROOT):
    """Check current numeric/probe compatibility; preserve historical CPU pins.

    Original source and private traces need not exist for a retained recheck.
    Their fingerprints remain bound by the producer stage and canonical archive.
    """
    inputs = stage['fingerprint']['inputs']
    by_path = {item['path']: item for item in inputs}
    require(len(by_path) == len(inputs) and required <= by_path.keys(), 'Required numeric dependencies were not declared')
    checked = {}
    for name in sorted(required):
        expected = {key: value for key, value in by_path[name].items() if key != 'path'}
        actual = listening_package._fingerprint_path(root / name)
        require(actual == expected, f'Current numeric/probe fingerprint differs: {name}')
        checked[name] = actual['sha256']
    return checked


def verify_stage_outputs(stage, base):
    checked = {}
    for output in stage['outputs']:
        relative = Path(output['relativePath'])
        require(not relative.is_absolute() and '..' not in relative.parts and output['type'] == 'file',
                'Unsupported retained stage output path/type')
        raw = raw_json(base / relative)
        require(sha(raw) == output['sha256'], f'Retained stage output hash differs: {relative}')
        checked[relative.as_posix()] = sha(raw)
    return checked


def stage_record(base, name, required):
    stage = read(base / 'stages' / f'{name}.json')
    require(stage['schemaVersion'] == 1 and stage['inputs'] == stage['fingerprint']['inputs'], 'Producer stage inputs differ')
    require(sha(listening_package._json_bytes(stage['fingerprint'])) == stage['key'], 'Producer stage fingerprint key differs')
    source = next((item for item in stage['fingerprint']['inputs'] if item['path'] == SOURCE_PATH), None)
    require(source is not None and source['type'] == 'file' and source['sha256'] == SOURCE_SHA,
            'Producer stage lacks the pinned source fingerprint')
    return stage, verify_dependencies(stage, required), verify_stage_outputs(stage, base)


def stores(records):
    return [{key: row[key] for key in ('phase', 'tick', 'address', 'value')} for row in records]


def normalized(value):
    return json.loads(json.dumps(value))


def context_stores(contexts):
    return [dict(phase='play', tick=row['call'], address=address, value=value)
            for row in contexts for address, value in row['writes']]


def numeric_sound(description):
    return {key: value for key, value in description.items() if key not in ('sourceEvidence', 'limits')}


def verify(components, source=None):
    components = components.resolve()
    require(components.is_relative_to(ROOT / 'evidence'), 'Choose canonical retained components under evidence/')
    prefix = components.relative_to(ROOT).as_posix() + '/'
    entries = [item for item in evidence.load_manifest()['files'] if item['path'].startswith(prefix)]
    require(entries, 'Canonical components are not in the evidence manifest')
    verified = evidence.verify(paths=tuple(item['path'] for item in entries))
    score_stage, score_tools, score_outputs = stage_record(components, 'score-form', SCORE_TOOLS)
    sound_stage, sound_tools, sound_outputs = stage_record(components, 'sound-programs', SOUND_TOOLS)
    form, sound = read(components / 'form/receipt.json'), read(components / 'sound/receipt.json')
    require(form['sourceSha256'] == sound['sourceSha256'] == SOURCE_SHA
            and form['musicCalls'] == sound['playCalls'] == 13961
            and form['independentScoreEqual'] and form['originalSourceUnchanged'], 'Retained component source/scope differs')
    require(sound['originalInitStores'] == 24 and sound['musicStores'] == 41506
            and sound['boundaryComparisons'] == 42083, 'Retained sound coverage differs')
    require(form['tools']['scripts/studies/ghostbusters/score.py'] == score_tools['scripts/studies/ghostbusters/score.py'],
            'Score receipt and producer numeric tool pin differ')
    for name, fingerprint in sound['outputs'].items():
        require(sound_outputs[f'sound/{name}'] == fingerprint, 'Sound receipt and producer output hash differ')
    machine_raw = raw_json(components / 'machine/verification.json')
    machine = json.loads(machine_raw)
    seed = form['retainedMachineSeedCheck']
    require(machine['sourceSha256'] == SOURCE_SHA and seed['receiptSha256'] == sha(machine_raw)
            and seed['privateTraceSha256'] == machine['privateArtifacts']['trace.json.gz']['sha256'],
            'Form seed check is not bound to the retained initialized machine receipt')
    upstream = {item['path']: item['sha256'] for item in score_stage['inputs'] if item['path'].startswith('{stage:')}
    require(upstream.get('{stage:initialized-census}/capture/verification.json') == sha(machine_raw)
            and upstream.get('{stage:initialized-census}/capture/trace.json.gz') == seed['privateTraceSha256'],
            'Producer machine dependency pins differ from retained cross-receipt evidence')
    optional_source = None
    if source is not None:
        optional_source = source.read_bytes()
        require(sha(optional_source) == SOURCE_SHA, 'Optional original source fingerprint differs')
    scored = read(components / 'form/score.json')
    described = read(components / 'sound/description.json')
    source_contexts = read(components / 'sound/contexts.json')
    initial_controls = []
    for voice in range(3):
        first = next(row for row in source_contexts if row['kind'] in ('onset', 'body') and row['voice'] == voice)
        require(first['call'] == 0 and first['kind'] == 'onset', 'Retained initial sound boundary differs')
        initial_controls.append(first['inputs']['cached_control'])
    composition = player.from_components(scored, described, initial_controls, calls=form['musicCalls'])
    composition['sourceEvidence'] = dict(sha256=SOURCE_SHA, selectedSubtune=1,
        score=dict(path=(components / 'form/score.json').relative_to(ROOT).as_posix(), sha256=score_outputs['form/score.json']),
        sound=dict(path=(components / 'sound/description.json').relative_to(ROOT).as_posix(), sha256=sound_outputs['sound/description.json']),
        initialCacheBasis='Retained isolated-source call0 pre-onset cached controls; no named machine RAM capture.',
        scope='Independent numeric music only. Full speech/machine integration remains a separate reconstruction requirement.')
    computed = player.compute(composition, contexts=True)
    same(computed['writes'], stores(read(components / 'form/writes.json')), 'All original init/play stores')
    same([row['score'] for row in computed['returns']], read(components / 'form/returns.json'), 'All score returns')
    original_contexts = read(components / 'form/contexts.json')
    require(len(original_contexts) == len(computed['returns']), 'Original named music context count differs')
    for original, result in zip(original_contexts, computed['returns']):
        require(original['tick'] == result['tick'] and original['cachedControls'] == result['cachedControls'],
                f'Cached controls differ at call {result["tick"]}')
        require(original['state'] == dict(phase=result['score']['phaseBefore'], voices=result['score']['voices']),
                f'Pre-increment music state differs at call {result["tick"]}')
    same(normalized(computed['contexts']), source_contexts, 'All named sound boundaries')
    same(computed['resetCalls'], [13952], 'Native reset calls')
    controls = []
    for kind in ('note', 'duration'):
        directory = components / 'form/controls' / kind
        control = read(directory / 'receipt.json')
        require(control['kind'] == kind and control['calls'] == 128, 'Retained score-control scope differs')
        edited = deepcopy(composition)
        row = edited['score']['patterns']['1']['rows'][0]
        if kind == 'note':
            row['note'] += 1
        else:
            edited['score']['patterns']['1']['rows'][0] = player.score.set_duration(row, (row['header'] & 31) + 1)
        require(edited['score'] == read(directory / 'score.json'), 'Independent score edit differs from retained data')
        before, _ = player.score.encode_rows(composition['score']['patterns']['1']['rows'])
        after, _ = player.score.encode_rows(edited['score']['patterns']['1']['rows'])
        changed = [index for index, pair in enumerate(zip(before, after)) if pair[0] != pair[1]]
        require(len(changed) == 1 and before[changed[0]] == control['originalByte'] and after[changed[0]] == control['editedByte'],
                'Numeric score control differs from the producer one-byte edit')
        result = player.compute(edited, calls=128)
        same(result['writes'], stores(read(directory / 'writes.json')), f'{kind} source-control stores')
        same([row['score'] for row in result['returns']], read(directory / 'returns.json'), f'{kind} source-control score returns')
        same([row['cachedControls'] for row in result['returns']], [row['cachedControls'] for row in computed['returns'][:128]],
             f'{kind} unaffected cached controls')
        controls.append(dict(kind=kind, calls=128, producerPrivateCopySha256=control['privateCopySha256'],
                             matchedStores=len(result['writes']), matchedScoreReturns=128,
                             independentNumericEdit=True, freshOriginalCPUExecution=False))
    pulse = next(row for row in sound['controls'] if row['name'] == 'pulse-low')
    require(pulse['before'] == 64 and pulse['after'] == 32 and pulse['calls'] == 1700, 'Retained pulse-control scope differs')
    edited = deepcopy(composition)
    edited['sound']['patches']['0']['pulse_low'] = 32
    expected_sound = read(components / 'sound/control-pulse-low.description.json')
    require(numeric_sound(edited['sound']) == numeric_sound(expected_sound), 'Independent patch edit differs from retained numeric bank')
    result = player.compute(edited, calls=pulse['calls'], contexts=True)
    original_pulse = read(components / 'sound/control-pulse-low.contexts.json')
    same(normalized(result['contexts']), original_pulse, 'Pulse control named source boundaries')
    original_init = [row for row in computed['writes'] if row['phase'] == 'init']
    same(result['writes'], original_init + context_stores(original_pulse), 'Pulse control original ordered stores')
    baseline = [row for row in computed['writes'] if row['phase'] == 'init' or row['tick'] < pulse['calls']]
    allowed = set(pulse['allowedPorts'])
    same([row for row in result['writes'] if row['address'] not in allowed],
         [row for row in baseline if row['address'] not in allowed], 'Pulse edit outside selected ports')
    require(result['writes'] != baseline, 'Pulse control has no store consequence')
    same(result['returns'], computed['returns'][:pulse['calls']], 'Pulse control unchanged score/cache state')
    controls.append(dict(kind='pulse-low', calls=pulse['calls'], producerPrivateCopySha256=pulse['changedSourceSha256'],
                         matchedStores=len(result['writes']), matchedSoundBoundaries=len(result['contexts']),
                         allowedPorts=pulse['allowedPorts'], independentNumericEdit=True, freshOriginalCPUExecution=False))
    if source is not None:
        require(source.read_bytes() == optional_source, 'Optional original source changed')
    tools = [Path(__file__), Path(player.__file__), Path(player.score.__file__), Path(player.programs.__file__),
             ROOT / 'scripts/sid_clock.py', ROOT / 'scripts/evidence.py', ROOT / 'scripts/listening_package.py']
    receipt = dict(schemaVersion=1, sourceSha256=SOURCE_SHA, clock='ntsc', sidModel='MOS6581',
        retainedSourceOracleRecheck=True, freshNumericComputation=True, freshCPUExecution=False,
        sourceBinaryRequired=False, privateMachineTraceRequired=False, optionalOriginalHashChecked=source is not None,
        musicCalls=form['musicCalls'], matchedInitPlayStores=len(computed['writes']), matchedScoreReturns=len(computed['returns']),
        matchedCachedControlReturns=len(computed['returns']), matchedSoundBoundaries=len(computed['contexts']),
        resetCalls=computed['resetCalls'], firstRestartCall=form['firstRestartCall'], initialCachedControls=initial_controls,
        controls=controls, verifiedCanonicalFiles=len(verified),
        canonicalInputHashes={item['path']: item['sha256'] for item in entries},
        currentNumericAndProbeToolPins=score_tools | sound_tools,
        producerStageKeys=dict(score=score_stage['key'], sound=sound_stage['key']),
        producerDependencyPins={name: {row['path']: row['sha256'] for row in stage['inputs']}
                                for name, stage in (('score', score_stage), ('sound', sound_stage))},
        tools={path.relative_to(ROOT).as_posix(): sha(path.read_bytes()) for path in tools},
        limits='Fresh independent numeric music matches all retained isolated original init/play stores, score/control state and sound boundaries through13961 calls, including reset/restart and three source-data controls. Producer fingerprints bind original source/CPU dependencies; this checker opens no source executable or private machine trace by default and performs no new CPU/VICE capture. Numeric runtime reads no original SID or captured stores. Full speech/machine integration, compiled playback, analogue state, acoustic recurrence and listening acceptance remain separate.')
    return composition, computed, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--components', type=Path, default=ROOT / 'evidence/ghostbusters-components')
    parser.add_argument('--source', type=Path, help='Optional additional original source SHA check; never required for retained recheck')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / 'build') and not output.exists(), 'Choose a fresh ignored build/ output directory')
    composition, computed, receipt = verify(args.components, args.source)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'composition.json').write_text(json.dumps(composition, indent=2) + '\n')
    for name in ('writes', 'returns', 'contexts'):
        (output / f'{name}.json').write_text(json.dumps(computed[name], separators=(',', ':')) + '\n')
    receipt['outputHashes'] = {path.name: sha(path.read_bytes()) for path in sorted(output.iterdir())}
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({key: receipt[key] for key in ('musicCalls', 'matchedInitPlayStores', 'matchedScoreReturns',
        'matchedCachedControlReturns', 'matchedSoundBoundaries', 'retainedSourceOracleRecheck', 'freshCPUExecution')}))


if __name__ == '__main__':
    try:
        main()
    except (KeyError, OSError, ValueError, IndexError, TypeError) as error:
        raise SystemExit(f'Ghostbusters numeric music proof: {error}')
