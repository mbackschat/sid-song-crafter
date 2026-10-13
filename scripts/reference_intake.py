"""Prepare explicitly selected source excerpts through the existing cached runner."""

from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import wave

from audio_comparison import inspect_wav, prepare_window_comparison, read_pcm16
from listening_package import run_recipe
from sid_intake import inspect_sid


ROOT = Path(__file__).resolve().parents[1]
RENDERER = '.local/bin/render-sid'
RENDER_LIBRARY = '.local/tools/libsidplayfp/3.1.1/lib/libsidplayfp.a'
HEADER_DEPENDENCIES = ['scripts/sid_intake.py', 'scripts/psid_profile.py',
                       'scripts/sid_audit_host.py', 'scripts/verify_player.py']
OWN_DEPENDENCIES = ['scripts/reference-intake.py', 'scripts/reference_intake.py',
                    'scripts/audio_comparison.py', 'scripts/listening_package.py',
                    'scripts/listening-package.py']
CODE_DEPENDENCIES = list(dict.fromkeys(OWN_DEPENDENCIES + HEADER_DEPENDENCIES +
                                     ['scripts/psid_audit.py', 'scripts/render-sid.cpp']))


class ExecutionRoute(str, Enum):
    CALLABLE = 'pal-banked'
    MACHINE_RENDER = 'full-machine-render'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fingerprint(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def managed_output(output, root):
    supplied = Path(output)
    require('..' not in supplied.parts, 'Output traversal is unsupported')
    path = Path(os.path.abspath(supplied if supplied.is_absolute() else root / supplied))
    require(root / 'build' in path.parents, 'Outputs must be beneath build/')
    current = root
    for part in path.relative_to(root).parts:
        current /= part
        require(not current.is_symlink(), 'Output symlink paths are unsupported')
    return path


def _relative(path, root):
    path = Path(path).resolve()
    require(path.is_relative_to(root), 'Specification must be inside the repository')
    return path.relative_to(root).as_posix()


def _number(value, low, high, label, *, integer=False):
    require(type(value) in ((int,) if integer else (int, float)) and math.isfinite(value)
            and low <= value <= high, f'Invalid {label}; expected {low}–{high}')


def validate_selection(selection):
    required = {'assetId', 'role', 'subtune', 'route', 'renderSeconds'}
    require(isinstance(selection, dict) and required <= set(selection)
            and set(selection) <= required | {'calls', 'hostBase'}, 'Invalid selection fields')
    for field in ('assetId', 'role'):
        value = selection[field]
        require(isinstance(value, str) and value.strip() and not any(c in value for c in '\r\n\0'),
                f'Invalid {field}')
    _number(selection['subtune'], 1, 256, 'subtune', integer=True)
    _number(selection['renderSeconds'], 1 / 44100, 600, 'renderSeconds')
    route = ExecutionRoute(selection['route'])
    if route is ExecutionRoute.CALLABLE:
        _number(selection.get('calls'), 1, 40000, 'calls', integer=True)
    else:
        require('calls' not in selection and 'hostBase' not in selection,
                'Machine renders have no callable calls or hostBase')
    if 'hostBase' in selection:
        value = selection['hostBase']
        require(type(value) is int and 0x0400 <= value <= 0x9e00 and value % 256 == 0, 'Invalid hostBase')


def load_spec(path):
    spec = json.loads(Path(path).read_text())
    require(isinstance(spec, dict) and type(spec.get('schemaVersion')) is int
            and spec['schemaVersion'] == 1, 'Expected reference intake schemaVersion 1')
    require(set(spec) <= {'schemaVersion', 'selections', 'windows', 'gapSeconds'}, 'Unknown specification fields')
    selections = spec.get('selections')
    require(isinstance(selections, list) and 1 <= len(selections) <= 2, 'Choose one or two source selections')
    for selection in selections:
        validate_selection(selection)
    windows = spec.get('windows')
    require(isinstance(windows, list) and 1 <= len(windows) <= 8, 'Choose one to eight bounded windows')
    names = set()
    for window in windows:
        require(isinstance(window, dict) and set(window) == {'id', 'startSeconds', 'endSeconds'}, 'Invalid window fields')
        name = window['id']
        require(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', name)
                and name not in names, 'Window IDs must be unique path-safe names')
        names.add(name)
        _number(window['startSeconds'], 0, 600, 'window start')
        _number(window['endSeconds'], 1 / 44100, min(s['renderSeconds'] for s in selections), 'window end')
        require(round(window['endSeconds'] * 44100) > round(window['startSeconds'] * 44100), 'Window must contain PCM frames')
    _number(spec.get('gapSeconds', 0.5), 0, 60, 'gapSeconds')
    return spec


def selection_receipt(selection, *, root=ROOT, registry_sha256=None):
    validate_selection(selection)
    registry = root / 'config/local-assets.json'
    registry_raw = registry.read_bytes()
    registry_sha = hashlib.sha256(registry_raw).hexdigest()
    if registry_sha256 is not None:
        require(registry_sha == registry_sha256, 'Registry fingerprint changed after recipe generation')
    entries = json.loads(registry_raw)['references']
    matching = [entry for entry in entries if entry['id'] == selection['assetId']]
    require(len(matching) == 1, 'assetId must identify exactly one registered reference')
    asset = matching[0]
    relative = Path(asset['path'])
    require(not relative.is_absolute() and '..' not in relative.parts and relative.parts[0] == '.local', 'Reference must remain under .local/')
    source = root / relative
    require(not any((root / Path(*relative.parts[:n])).is_symlink() for n in range(1, len(relative.parts) + 1)),
            'Reference symlink paths are unsupported')
    require(source.is_file(), f'Missing reference; use scripts/setup-project.py --only references --include {asset["id"]}')
    raw = source.read_bytes()
    source_sha = hashlib.sha256(raw).hexdigest()
    require(source_sha == asset['sha256'], 'Reference fingerprint differs from registry')
    header = inspect_sid(raw, subtune=selection['subtune'], host_base=selection.get('hostBase'))
    require(header['clockDeclaration'] == 'PAL', 'Initial renderer contract requires declared PAL')
    require(header['sidModelDeclaration'] in ('MOS6581', 'MOS8580'), 'Initial renderer contract requires one declared SID model')
    require(raw[122:124] == bytes(2) and header['flags'] in (0x14, 0x24), 'Initial intake contract requires one SID and standard PAL/model flags')
    route = ExecutionRoute(selection['route'])
    if route is ExecutionRoute.CALLABLE:
        require(header['callableProfile']['accepted'], f'Unsupported callable selection: {header["callableProfile"]["reason"]}')
    return dict(schemaVersion=1, kind='selected-original-source', selection=selection,
                source={**asset, 'path': str(source), 'bytes': len(raw), 'sha256': source_sha},
                registry=dict(path=str(registry), bytes=len(registry_raw), sha256=registry_sha), header=header,
                rendering=dict(renderer=RENDERER, library='libsidplayfp 3.1.1 / SIDLite',
                               clock='PAL', clockForced=True, sidModel=header['sidModelDeclaration'],
                               subtune=selection['subtune'], powerOnDelay=0, sampleRate=44100,
                               channels=1, format='PCM16', seconds=selection['renderSeconds'],
                               gain=1, normalization=False, initialized=True),
                evidence=dict(route=route.value, cpuOrderedStoresRequested=route is ExecutionRoute.CALLABLE,
                              cpuCausalProof=False, registerObservation='renderer-iteration register snapshots, not a bus-write trace',
                              limitations='Header admission, optional controlled callable CPU stores and modeled source audio; no original-host equivalence, causal corroboration or listening verdict.'),
                listeningReview=None)


def _stage(identity, command, inputs, outputs, timeout=120):
    return dict(id=identity, command=command, inputs=list(dict.fromkeys(inputs)), outputs=outputs,
                timeoutSeconds=timeout, env=dict(PYTHONPATH='{root}/.tools/test-deps', PYTHONDONTWRITEBYTECODE='1'))


def make_recipe(spec_path, *, root=ROOT):
    root = Path(root).resolve()
    spec_path = root / spec_path if not Path(spec_path).is_absolute() else Path(spec_path)
    spec = load_spec(spec_path)
    _relative(spec_path, root)
    stages, deliverables = [], {}
    for index, selection in enumerate(spec['selections']):
        receipt = selection_receipt(selection, root=root)
        label = ('sourceA', 'sourceB')[index]
        source = receipt['source']['path']
        base = ['config/local-assets.json', source]
        selected = label + '-selection'
        measured = label + '-measure'
        selection_json = json.dumps(selection, sort_keys=True, separators=(',', ':')).replace('{', '{{').replace('}', '}}')
        stages.append(_stage(selected, ['{python}', 'scripts/reference-intake.py', 'selection',
                                       selection_json,
                                       '--registry-sha256', receipt['registry']['sha256'], '--output', '{out}/selection.json'],
                             base + OWN_DEPENDENCIES + HEADER_DEPENDENCIES, ['selection.json']))
        if ExecutionRoute(selection['route']) is ExecutionRoute.CALLABLE:
            command = ['{python}', 'scripts/psid_audit.py', source, '--profile', 'pal-banked', '--subtune',
                       str(selection['subtune']), '--ticks', str(selection['calls']), '--output', '{out}/audit.json']
            if 'hostBase' in selection:
                command += ['--host-base', str(selection['hostBase'])]
            audited = label + '-audit'
            stages.append(_stage(audited, command,
                                 base + HEADER_DEPENDENCIES + ['scripts/psid_audit.py', '.tools/test-deps/py65',
                                                               '{stage:' + selected + '}/selection.json'],
                                 ['audit.json', 'audit.writes.json'], 600))
            deliverables[label + 'CpuAudit'] = '{stage:' + audited + '}/audit.json'
            deliverables[label + 'OrderedStores'] = '{stage:' + audited + '}/audit.writes.json'
        rendered = label + '-render'
        stages.append(_stage(rendered, ['{root}/' + RENDERER, source, '{out}/source.wav',
                                       str(selection['renderSeconds']), '--subtune', str(selection['subtune'])],
                             base + [RENDERER, RENDER_LIBRARY, 'scripts/render-sid.cpp',
                                     '{stage:' + selected + '}/selection.json'], ['source.wav', 'source.wav.registers.tsv']))
        stages.append(_stage(measured, ['{python}', 'scripts/reference-intake.py', 'measure',
                                       '{stage:' + selected + '}/selection.json', '{stage:' + rendered + '}/source.wav',
                                       '--output', '{out}/source.json'],
                             OWN_DEPENDENCIES + HEADER_DEPENDENCIES + ['{stage:' + selected + '}/selection.json',
                               '{stage:' + rendered + '}/source.wav', '{stage:' + rendered + '}/source.wav.registers.tsv'], ['source.json']))
        deliverables[label + 'Render'] = '{stage:' + rendered + '}/source.wav'
        deliverables[label + 'Receipt'] = '{stage:' + measured + '}/source.json'
    pair = len(spec['selections']) == 2
    for window in spec['windows']:
        identity = 'window-' + window['id']
        command = ['{python}', 'scripts/reference-intake.py', 'window', '{stage:sourceA-measure}/source.json']
        inputs = OWN_DEPENDENCIES + HEADER_DEPENDENCIES + ['{stage:sourceA-measure}/source.json', '{stage:sourceA-render}/source.wav']
        if pair:
            command += ['--second', '{stage:sourceB-measure}/source.json']
            inputs += ['{stage:sourceB-measure}/source.json', '{stage:sourceB-render}/source.wav']
        command += ['--start', str(window['startSeconds']), '--end', str(window['endSeconds']),
                    '--gap', str(spec.get('gapSeconds', 0.5)), '--output', '{out}']
        outputs = ['sources.ab.wav', 'sources.comparison.json', 'window.json'] if pair else ['source.wav', 'window.json']
        stages.append(_stage(identity, command, inputs, outputs))
        deliverables[('sourceContrast-' if pair else 'sourceWindow-') + window['id']] = '{stage:' + identity + '}/' + outputs[0]
        deliverables['windowReceipt-' + window['id']] = '{stage:' + identity + '}/window.json'
    return dict(schemaVersion=1, stages=stages, deliverables=deliverables)


def write_receipt(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + '\n')


def run_intake(spec_path, output, *, root=ROOT, progress=print):
    root = Path(root).resolve()
    output = managed_output(output, root)
    recipe = make_recipe(spec_path, root=root)
    raw = (json.dumps(recipe, indent=2, allow_nan=False) + '\n').encode()
    recipe_path = output / 'recipes' / (hashlib.sha256(raw).hexdigest() + '.json')
    managed_output(recipe_path, root)
    recipe_path.parent.mkdir(parents=True, exist_ok=True)
    if recipe_path.exists():
        require(recipe_path.read_bytes() == raw, 'Generated recipe changed')
    else:
        with recipe_path.open('xb') as stream:
            stream.write(raw)
    return run_recipe(recipe_path, output, root=root, progress=progress)


def measure_source(selection_path, wav_path, output):
    receipt = json.loads(Path(selection_path).read_text())
    measured = inspect_wav(wav_path)
    settings = receipt['rendering']
    frames = math.floor(settings['seconds'] * settings['sampleRate'] + 0.5)
    require(measured['sampleRate'] == 44100 and measured['channels'] == 1 and measured['frames'] == frames,
            'Source render format or bounded duration differs from selection')
    require(measured['acRms'] > 0 and measured['clippedSamples'] == 0, 'Source render is silent or has PCM rail samples')
    snapshot = Path(str(wav_path) + '.registers.tsv')
    with snapshot.open() as stream:
        require(stream.readline().rstrip() == 'time_ms\tregisters_hex' and bool(stream.readline()), 'Missing renderer register snapshots')
    receipt.update(render=measured, registerSnapshots=fingerprint(snapshot))
    write_receipt(output, receipt)
    return receipt


def source_window(first_path, second_path, *, start, end, gap, output):
    output = Path(output)
    first = json.loads(Path(first_path).read_text())
    sources = [first]
    if second_path is not None:
        sources.append(json.loads(Path(second_path).read_text()))
    for source in sources:
        require(fingerprint(source['render']['path'])['sha256'] == source['render']['sha256'], 'Source render fingerprint changed')
    if len(sources) == 2:
        comparison = prepare_window_comparison(sources[0]['render']['path'], sources[1]['render']['path'], output / 'sources',
                                              start_seconds=start, end_seconds=end, gap_seconds=gap)
        rendered = comparison['comparison']
        kind = 'source-contrast'
    else:
        audio = read_pcm16(first['render']['path'])
        begin, stop = round(start * audio.sample_rate), round(end * audio.sample_rate)
        require(0 <= begin < stop <= audio.frames, 'Source window must fit the bounded render')
        samples = audio.samples[begin:stop]
        if sys.byteorder != 'little':
            samples.byteswap()
        path = output / 'source.wav'
        with path.open('xb') as stream:
            with wave.open(stream, 'wb') as wav:
                wav.setparams((audio.channels, 2, audio.sample_rate, 0, 'NONE', 'not compressed'))
                wav.writeframes(samples.tobytes())
        rendered = inspect_wav(path)
        kind = 'source-excerpt'
    report = dict(schemaVersion=1, kind=kind, order=['sourceA', 'sourceB'][:len(sources)],
                  sources=[dict(label=('sourceA', 'sourceB')[index], role=source['selection']['role'],
                                selection=source['selection'], source=source['source'], rendering=source['rendering'],
                                inputRender=source['render']) for index, source in enumerate(sources)],
                  windowSeconds=[start, end], gain=1, normalization=False, clip=rendered,
                  limitations='Original source excerpts; a source contrast is not reconstruction fidelity or causal corroboration.', listeningReview=None)
    write_receipt(output / 'window.json', report)
    return report
