"""Check independent Take On Me synthesis against retained source execution."""

import argparse
from copy import deepcopy
from dataclasses import asdict
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence
from psid_audit import audit_psid
from psid_profile import psid_profile
from verify_player import require
import player
import programs
import score


SOURCE_SHA = 'c7e45037d20c3b85d18fc955a1cdfb70041f08dfc171e9b12d1c3327300101e6'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def save(path, value):
    data = (json.dumps(value, separators=(',', ':')) + '\n').encode()
    if path.suffix == '.gz':
        data = gzip.compress(data, mtime=0)
    with path.open('xb') as output:
        output.write(data)


def same(actual, expected, label):
    if actual != expected:
        if isinstance(actual, list) and isinstance(expected, list):
            index = next((index for index, pair in enumerate(zip(actual, expected)) if pair[0] != pair[1]),
                         min(len(actual), len(expected)))
            raise ValueError(f'{label} mismatch at {index}: computed={actual[index:index + 1]}, source={expected[index:index + 1]}')
        raise ValueError(f'{label} differs')


def projection(writes):
    return [{key: row[key] for key in ('phase', 'tick', 'address', 'value')} for row in writes]


def portable_score(description):
    return dict(schemaVersion=1, dividerReloads=description['dividerReloads'],
        initialDividers=description['initialDividers'], initialVoices=description['initialVoices'],
        orders=[dict(bytes=order['bytes']) for order in description['orders']],
        patterns={str(index): dict(rows=pattern['rows']) for index, pattern in description['patterns'].items()})


def source_adapter():
    path = Path(__file__).with_name('sound-probe.py')
    spec = importlib.util.spec_from_file_location('take_on_me_source_sound', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_ram(data):
    parsed = psid_profile(data, profile='pal-banked', subtune=1, assume_sid_model='MOS8580')
    ram = [0] * 65536
    ram[parsed['loadAddress']:parsed['endAddress']] = parsed['payload']
    return ram


def decoded_sound(adapter, ram):
    instruments, bank = adapter.description(ram)
    value = dict(instruments={index: asdict(instrument) for index, instrument in instruments.items()},
                 programs=asdict(bank))
    return json.loads(json.dumps(value))


def initialized_image(data, adapter):
    captured = None

    def observe(cpu, memory):
        nonlocal captured
        if memory.phase == 'init' and cpu.pc == 0x1b05:
            require(captured is None, 'Repeated initialization return')
            captured = dict(voices=[asdict(adapter.voice_state(memory.data, voice)) for voice in range(3)],
                filter=asdict(adapter.filter_state(memory.data)))

    report, writes = audit_psid(data, 1, observer=observe, profile='pal-banked', subtune=1,
                               assume_sid_model='MOS8580')
    require(captured is not None, 'Initialization image was not observed')
    for voice in captured['voices']:
        for name in player.SCORE_OWNED:
            del voice[name]
    return captured, report, projection([row for row in writes if row['phase'] == 'init'])


def compare_contexts(computed, expected, calls):
    selected = [row for row in computed if row['call'] < calls]
    normalized = json.loads(json.dumps(selected))
    expected = [{key: value for key, value in row.items() if key not in ('entryPc', 'exitPc')} for row in expected]
    same(normalized, expected, 'Named sound contexts')
    return len(expected)


def named_ram(result, adapter):
    ram = {}
    for voice, values in enumerate(result['score']['voices']):
        ram.update({address + voice: values[name] for name, address in score.FIELDS.items()})
    for voice, values in enumerate(result['voices']):
        ram.update({address + voice: values[name] for name, address in adapter.BYTE_FIELDS.items()})
        for name, low, high in (('frequency', 0x12, 0x15), ('pulse', 0x18, 0x1b),
                               ('glide_step', 0x1aae, 0x1ab1), ('vibrato_step', 0x1adf, 0x1ae2)):
            ram[low + voice], ram[high + voice] = values[name] & 255, values[name] >> 8
    shared = result['filter']
    ram.update({0x21: shared['word'] & 255, 0x22: shared['word'] >> 8,
                0x1ae5: shared['initial'], 0x1ae6: shared['direction']})
    return ram


def compare_recurrence(computed, receipt, adapter):
    checks = []
    checkpoints = receipt['recurrenceCheckpoints']
    for before, after in zip(checkpoints, checkpoints[1:]):
        earlier = named_ram(computed['returns'][before['tick']], adapter)
        later = named_ram(computed['returns'][after['tick']], adapter)
        actual = [dict(address=address, before=value, after=later[address])
                  for address, value in sorted(earlier.items()) if value != later[address]]
        expected = [change for change in after['ramChangesFromPrevious'] if change['address'] in earlier]
        same(actual, expected, 'Observed recurrence field changes')
        require(len(expected) == len(after['ramChangesFromPrevious']), 'Source recurrence changes escape the named model state')
        checks.append(dict(firstCall=before['tick'], repeatedCall=after['tick'],
                           matchedChanges=actual))
    return checks


def patch(data, address, original, candidate):
    parsed = psid_profile(data, profile='pal-banked', subtune=1, assume_sid_model='MOS8580')
    offset = len(data) - len(parsed['payload']) + address - parsed['loadAddress']
    require(data[offset] == original, 'Source intervention byte differs')
    changed = bytearray(data)
    changed[offset] = candidate
    return bytes(changed)


def verify_controls(composition, original, form_dir, sound_dir, sound_receipt, adapter, source):
    duration = read_json(form_dir / 'intervention.json.gz')
    private = patch(source, duration['address'], duration['originalByte'], duration['editedByte'])
    require(sha(private) == duration['privateCopySha256'], 'Duration-copy fingerprint differs')
    edited = deepcopy(composition)
    edited['score']['patterns']['2']['rows'][0]['durationUnits'] = 5
    same(edited['score'], portable_score(score.decode(source_ram(private))), 'Source-data duration edit')
    result = player.compute(edited, calls=duration['calls'], contexts=True)
    same(result['writes'], projection(duration['executed']['writes']), 'Duration-copy ordered stores')
    same([row['score'] for row in result['returns']], duration['executed']['returns'], 'Duration-copy score states')
    baseline = [row for row in original['writes'] if row['tick'] is None or row['tick'] < duration['calls']]
    companion = lambda rows: [row for row in rows if not 0xd407 <= row['address'] <= 0xd40d]
    same(companion(result['writes']), companion(baseline), 'Duration-copy companion/global stores')
    require(result['writes'] != baseline, 'Duration edit has no output consequence')
    duration_result = dict(name='duration', sourceCopySha256=sha(private),
        changedAddress=duration['address'], calls=duration['calls'], matchedWrites=len(result['writes']),
        companionAndGlobalStoresEqual=True, computed=result)

    control = next(row for row in sound_receipt['controls'] if row['name'] == 'pulse-down-step')
    private = patch(source, control['address'], control['original'], control['candidate'])
    require(sha(private) == control['candidateSha256'], 'Pulse-copy fingerprint differs')
    edited = deepcopy(composition)
    edited['sound']['programs']['pulses']['1']['down_step'] = control['candidate']
    same(edited['sound'], decoded_sound(adapter, source_ram(private)), 'Source-data pulse edit')
    calls = control['audit']['playCalls']
    result = player.compute(edited, calls=calls, contexts=True)
    expected_writes = read_json(sound_dir / 'pulse-down-step.writes.json.gz')
    same(result['writes'], projection(expected_writes), 'Pulse-copy ordered stores')
    context_count = compare_contexts(result['contexts'], read_json(sound_dir / 'pulse-down-step.contexts.json.gz'), calls)
    baseline = [row for row in original['writes'] if row['tick'] is None or row['tick'] < calls]
    unaffected = lambda rows: [row for row in rows if row['address'] not in control['declaredPorts']]
    same(unaffected(result['writes']), unaffected(baseline), 'Pulse-copy unmodified-port stores')
    require(result['writes'] != baseline, 'Pulse edit has no output consequence')
    pulse_result = dict(name='pulse-down-step', sourceCopySha256=sha(private),
        changedAddress=control['address'], calls=calls, matchedWrites=len(result['writes']),
        matchedNamedContexts=context_count, onlyDeclaredPortsChanged=True,
        declaredPorts=control['declaredPorts'], computed=result)
    return [duration_result, pulse_result]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/research/take-on-me/Take_on_Me.sid')
    parser.add_argument('--form-dir', type=Path, default=ROOT / 'evidence/take-on-me-form')
    parser.add_argument('--sound-dir', type=Path, default=ROOT / 'evidence/take-on-me-sound')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'Player output exists; choose a fresh directory')
    source = args.source.read_bytes()
    require(sha(source) == SOURCE_SHA, 'Pinned Take On Me source fingerprint differs')
    require(source[118:120] == b'\x00\x04', 'Original unknown-model declaration changed')
    form_paths = [args.form_dir / name for name in ('receipt.json', 'score.json', 'writes.json.gz', 'returns.json.gz', 'intervention.json.gz')]
    sound_paths = [args.sound_dir / name for name in ('receipt.json', 'sound-description.json', 'contexts.json.gz', 'pulse-down-step.contexts.json.gz', 'pulse-down-step.writes.json.gz')]
    checked_paths = form_paths + sound_paths
    evidence.verify(paths=tuple(str(path.resolve().relative_to(ROOT)) for path in checked_paths))
    form = read_json(args.form_dir / 'receipt.json')
    sound = read_json(args.sound_dir / 'receipt.json')
    require(form['sourceSha256'] == sound['sourceSha256'] == SOURCE_SHA, 'Retained source identities differ')
    require(form['numericScoreEqual'] and form['selectedSubtune'] == 1 and form['playCalls'] == 8961,
            'Expected the complete pinned score proof')
    require(sound['activeGlideBodyInputs'] == 0, 'Natural source coverage changed')
    for name, expected in form['tools'].items():
        require(sha((ROOT / name).read_bytes()) == expected, f'Retained form tool differs: {name}')
    for name, expected in sound['toolHashes'].items():
        require(sha((Path(__file__).parent / name).read_bytes()) == expected, f'Retained sound tool differs: {name}')
    for name, expected in sound['oracleToolHashes'].items():
        require(sha((ROOT / 'scripts' / name).read_bytes()) == expected, f'Retained sound oracle tool differs: {name}')
    adapter = source_adapter()
    score_description = read_json(args.form_dir / 'score.json')
    sound_description = read_json(args.sound_dir / 'sound-description.json')
    ram = source_ram(source)
    same(portable_score(score_description), portable_score(score.decode(ram)), 'Pinned editable score')
    same(sound_description, decoded_sound(adapter, ram), 'Pinned editable sound bank')
    initial, init_audit, init_writes = initialized_image(source, adapter)
    composition = dict(schema='take-on-me-composition-v1',
        target=dict(clock='pal', sidModel='MOS8580', sidBase=0xd400, frameCycles=19656),
        range=dict(auditCalls=form['playCalls']), mix=dict(routing=241, modeVolume=31),
        score=portable_score(score_description), sound=sound_description, initialSound=initial,
        sourceEvidence=dict(sha256=SOURCE_SHA, declaredSidModel='unknown', selectedSubtune=1,
            formReceipt=str(args.form_dir / 'receipt.json'), soundReceipt=str(args.sound_dir / 'receipt.json'),
            scope='Introduction and two observed score-loop traversals plus the next wrap; no selected finite ending.'))
    started = time.perf_counter()
    computed = player.compute(composition, contexts=True)
    compute_seconds = time.perf_counter() - started
    expected_writes = projection(read_json(args.form_dir / 'writes.json.gz'))
    same(computed['writes'], expected_writes, 'Complete ordered SID stores')
    same([row for row in computed['writes'] if row['phase'] == 'init'], init_writes, 'Fresh initialization stores')
    same([row['score'] for row in computed['returns']], read_json(args.form_dir / 'returns.json.gz'), 'Complete named score return states')
    context_count = compare_contexts(computed['contexts'], read_json(args.sound_dir / 'contexts.json.gz'), sound['playCalls'])
    recurrence = compare_recurrence(computed, form, adapter)
    controls = verify_controls(composition, computed, args.form_dir, args.sound_dir, sound, adapter, source)
    require(args.source.read_bytes() == source, 'Original source changed')
    imported = {Path(module.__file__).resolve() for module in sys.modules.values()
                if getattr(module, '__file__', None) and str(Path(module.__file__).resolve()).startswith(str(ROOT) + '/')}
    tools = {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in sorted(imported | {Path(__file__).resolve()})}
    receipt = dict(schemaVersion=1, sourceSha256=SOURCE_SHA, sourceUnchanged=True,
        declaredSidModel='unknown', experimentalCompositionModel='MOS8580', selectedSubtune=1,
        playCalls=form['playCalls'], matchedOrderedWrites=len(expected_writes),
        matchedInitWrites=len(init_writes), matchedScoreReturnStates=len(computed['returns']),
        namedSoundContextCalls=sound['playCalls'], matchedNamedSoundContexts=context_count,
        recurrenceFieldChecks=recurrence, completeComputeSeconds=compute_seconds,
        freshInitializationAudit=init_audit, retainedExecutionRecheck=True,
        inputs={str(path.resolve().relative_to(ROOT)): sha(path.read_bytes()) for path in checked_paths},
        tools=tools, python=dict(executable=sys.executable, version=sys.version),
        controls=[{key: value for key, value in row.items() if key != 'computed'} for row in controls],
        limitations='Independent score/sound integration, complete ordered-store comparison against pinned retained RAM-only execution, named sound contexts over calls 0..1023, and later observed recurrence field changes. Source-copy controls are retained-execution rechecks with reproduced copy hashes. Fresh source execution captures initialization only. No compiled player, VICE candidate, exact instruction/bus timing, acoustic recurrence, selected finite ending or musical acceptance.')
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / 'composition.json', composition)
    save(args.output / 'writes.json', computed['writes'])
    save(args.output / 'returns.json.gz', computed['returns'])
    save(args.output / 'contexts.json.gz', computed['contexts'])
    save(args.output / 'controls.json.gz', controls)
    save(args.output / 'receipt.json', receipt)
    print(json.dumps({key: receipt[key] for key in ('playCalls', 'matchedOrderedWrites', 'matchedScoreReturnStates', 'matchedNamedSoundContexts', 'completeComputeSeconds', 'controls')}))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f'Take On Me player check failed: {error}')
