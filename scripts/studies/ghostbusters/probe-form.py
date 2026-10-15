"""Verify Ghostbusters' editable music score through native reset and restart."""

import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import AuditMemory
from sid_clock import NTSC_FRAME_CYCLES
from sid_intake import inspect_sid
from verify_player import cpu_type, require

spec = importlib.util.spec_from_file_location('ghostbusters_score', Path(__file__).with_name('score.py'))
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)
SOURCE_SHA = score.SOURCE_SHA
READS = {0x9405: ('orderPointerLow', 0xa2b7), 0x940a: ('orderPointerHigh', 0xa2ba),
         0x9422: ('order', None), 0x9436: ('patternPointerLow', 0xa75b),
         0x943b: ('patternPointerHigh', 0xa75b), 0x9446: ('rowHeader', None),
         0x945c: ('packedParameter', None), 0x9490: ('note', None),
         0x94f0: ('patternLookahead', None)}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as file:
        json.dump(value, file, indent=2)
        file.write('\n')


def decode_source(data):
    """Load the pinned layout; private data-only clones use the same component API."""
    header = inspect_sid(data, subtune=1)
    require(header['format'] == 'RSID' and header['flags'] == 0x18
            and header['loadAddress'] == header['initAddress'] == 0x900d
            and header['endAddressExclusive'] == 0xa835 and header['playAddress'] == 0,
            'Unexpected Ghostbusters component layout')
    ram = [0] * 65536
    ram[0:2] = [0x2f, 0x36]
    ram[header['loadAddress']:header['endAddressExclusive']] = data[126:]
    ram[0x93e2:0x9596] = ram[0xa040:0xa1f4]
    return header, ram, score.decode(ram)


def named_state(ram, *, idle=False):
    def get(address):
        if not idle:
            return ram[address]
        if 0x82 <= address <= 0x96:
            return ram[0x9104 + address - 0x82]
        return ram[0x9119 + address - 0xdc]
    return dict(phase=get(0xe2), voices=[{field: get(address + voice) for field, address in score.FIELDS.items()}
                                       for voice in range(3)])


def sound_caches(ram, *, idle=False):
    address = 0x9104 + score.CACHED_CONTROL - 0x82 if idle else score.CACHED_CONTROL
    return ram[address:address + 3]


def workspace(ram, *, idle=False):
    return ram[0x9104:0x9124] if idle else ram[0x82:0x97] + ram[0xdc:0xe7]


def observe_source(data, description, calls, observer=None):
    """Execute original RAM-only music fragments with the existing CPU/audit memory.

    The real RSID init/speech/IRQ epilogue is not executed here. Original music
    init and both context swaps plus native NTSC phase increment are retained.
    A read-only instruction observer can inspect cpu/memory.phase/memory.tick
    and ordered writes, sharing this adapter with the independent sound proof.
    """
    require(type(calls) is int and 1 <= calls <= 16000, 'Choose 1..16000 isolated music calls')
    _, ram, _ = decode_source(data)
    memory = AuditMemory()
    memory.data[:] = ram
    cpu = cpu_type()(memory=memory, pc=0x9066)
    cpu.a, cpu.x, cpu.y, cpu.sp, cpu.p = 0, 0, 0, 0xff, cpu.UNUSED
    reads, rows, resets, returns, contexts, reset_caches, cycles = [], [], [], [], [], [], []
    patterns = [None] * 3
    row_addresses = [None] * 3
    row_offsets = {int(key): score.encode_rows(value['rows'])[1] for key, value in description['patterns'].items()}
    pending_reset, phase_before, active_after = None, None, None

    def observe():
        nonlocal pending_reset, phase_before, active_after
        pc, voice, tick, values = cpu.pc, cpu.x, memory.tick, memory.data
        if memory.phase == 'play':
            if pc in READS:
                field, table = READS[pc]
                if field.startswith('orderPointer'):
                    offset, pattern = voice, None
                    address = table + voice
                elif field.startswith('patternPointer'):
                    offset, pattern = cpu.y + int(pc == 0x943b), cpu.y // 2
                    address = table + offset
                    patterns[voice] = pattern
                else:
                    pointer = 0xe3 if field == 'order' else 0xe5
                    address = ((values[pointer] | values[pointer + 1] << 8) + cpu.y) & 65535
                    offset, pattern = cpu.y, None if field == 'order' else patterns[voice]
                    if field == 'rowHeader':
                        row_addresses[voice] = address
                reads.append(dict(tick=tick, voice=voice, field=field, pattern=pattern,
                                  offset=offset, value=values[address], address=address, pc=pc))
            elif pc == 0x94fc:
                pattern = patterns[voice]
                base = description['patterns'][str(pattern)]['sourceEvidence']['address']
                state = named_state(values)['voices'][voice]
                rows.append(dict(tick=tick, voice=voice, pattern=pattern,
                                 row=row_offsets[pattern].index(row_addresses[voice] - base),
                                 kind='rest' if state['header'] & 64 else 'note', state=state))
            elif pc == 0x942e:
                before = named_state(values)
                caches = [{field: state[field] for field in ('note', 'header', 'instrument')}
                          for state in before['voices']]
                resets.append(dict(tick=tick, voice=voice, phase=values[0xe2], retainedCaches=caches))
                pending_reset = dict(tick=tick, before=before, cachedControlsBefore=sound_caches(values))
            elif pc == 0x9431 and pending_reset is not None:
                after = named_state(values)
                require(all(state[field] == 0 for state in after['voices']
                            for field in ('orderCursor', 'patternCursor', 'remaining')), 'Native reset did not clear scheduling state')
                for before, current in zip(pending_reset['before']['voices'], after['voices']):
                    require(all(before[field] == current[field] for field in ('note', 'header', 'instrument')),
                            'Native reset did not retain score caches')
                require(sound_caches(values) == pending_reset['cachedControlsBefore'], 'Native reset changed sound-owned cached controls')
                require(after['phase'] == pending_reset['before']['phase'], 'Native reset changed wrapper-owned phase')
                pending_reset.update(after=after, cachedControlsAfter=sound_caches(values))
                reset_caches.append(pending_reset)
                pending_reset = None
            elif pc == 0x90e3:
                phase_before = values[0xe2]
            elif pc == 0x90e6:
                contexts.append(dict(tick=tick, state=named_state(values), cachedControls=sound_caches(values)))
            elif pc == 0x90f5:
                current = named_state(values)
                require(current['phase'] == (phase_before + 1) & 255, 'Native NTSC wrapper did not increment phase exactly once')
                returns.append(dict(tick=tick, phaseBefore=phase_before, phaseAfter=current['phase'], voices=current['voices']))
                active_after = workspace(values)
        if observer is not None:
            observer(cpu, memory)

    def fragment(first, stop, budget):
        cpu.pc = first
        start = cpu.processorCycles
        while cpu.pc != stop:
            require(cpu.processorCycles - start < budget, 'Original music fragment exceeded its bounded CPU budget')
            opcode = memory[cpu.pc]
            memory.instruction = cpu.disassemble[opcode][0]
            require(memory.instruction not in ('???', 'BRK', 'RTI'), 'Unsupported opcode in isolated music fragment')
            memory.instruction_cycle = cpu.processorCycles - start
            before_writes, pc = len(memory.writes), cpu.pc
            observe()
            cpu.step()
            for write in memory.writes[before_writes:]:
                write['writerPc'] = pc
        require(cpu.sp == 0xff, 'Original fragment did not restore isolated caller stack')
        return cpu.processorCycles - start

    clear_cycles = fragment(0x9066, 0x9070, 1000)
    init_cycles = fragment(0x9075, 0x9080, 3000)
    initialized = named_state(memory.data, idle=True)
    require(initialized == description['initialState'], 'Source-defined buffer/init seed differs from portable score')
    initial_controls = sound_caches(memory.data, idle=True)
    host_workspace = workspace(memory.data)
    memory.phase = 'play'
    for tick in range(calls):
        memory.tick = tick
        cycles.append(fragment(0x90e0, 0x90f8, NTSC_FRAME_CYCLES))
        require(workspace(memory.data) == host_workspace, 'Context swap did not restore isolated host workspace')
        require(workspace(memory.data, idle=True) == active_after, 'Context swap did not retain the entire active music workspace')
        require(named_state(memory.data, idle=True) == dict(phase=returns[-1]['phaseAfter'], voices=returns[-1]['voices']),
                'Named active and swapped-out return state disagree')
    require(pending_reset is None and len(returns) == len(contexts) == calls, 'Incomplete source context/reset boundary')
    return dict(reads=reads, rows=rows, resets=resets, returns=returns, contexts=contexts,
                resetCaches=reset_caches, writes=memory.writes, initialState=initialized,
                initialCachedControls=initial_controls,
                audit=dict(cpu='py65 NMOS 6502', environment='Isolated original relocated music RAM fragments; no RSID speech/init/interrupt emulation',
                           initClearCycles=clear_cycles, musicInitCycles=init_cycles, musicCalls=calls,
                           minimumWrapperCycles=min(cycles), maximumWrapperCycles=max(cycles),
                           frameCycleBudget=NTSC_FRAME_CYCLES, contextSwapVerifiedCalls=calls))


def check(description, observed, calls):
    computed = score.expand(description, calls)
    for field in ('reads', 'rows', 'resets', 'returns'):
        actual, expected = observed[field], computed[field]
        if actual != expected:
            first = next((index for index, pair in enumerate(zip(actual, expected)) if pair[0] != pair[1]), min(len(actual), len(expected)))
            raise ValueError(f'{field} mismatch at {first}: source={actual[first:first + 1]}, model={expected[first:first + 1]}')
    return computed


def verify_machine_seed(observed, receipt_path, trace_path=None):
    receipt = json.loads(receipt_path.read_text())
    require(receipt['sourceSha256'] == SOURCE_SHA and receipt['capture']['completedBodies'] == 128,
            'Retained machine receipt source/bound differs')
    expected_tools = {'probeSha256': Path(__file__).with_name('probe-machine.py'),
                      'traceGrammarSha256': ROOT / 'scripts/trace-sid-vice.py',
                      'clockSha256': ROOT / 'scripts/sid_clock.py', 'inspectorSha256': ROOT / 'scripts/sid_intake.py'}
    for key, path in expected_tools.items():
        require(sha(path.read_bytes()) == receipt['tools'][key], f'Retained machine tool pin differs: {path}')
    command = json.loads(receipt_path.with_name('command.json').read_text())
    if trace_path is None:
        trace_path = Path(command[command.index('-monlogname') + 1]).with_name('trace.json.gz')
    raw = trace_path.read_bytes()
    require(sha(raw) == receipt['privateArtifacts']['trace.json.gz']['sha256'], 'Retained private machine trace fingerprint differs')
    records = json.loads(gzip.decompress(raw))
    machine = [dict(tick=row['bodyIndex'], address=row['address'], value=row['value'])
               for row in records if row['phase'] == 'play' and row['operation'] == 'store' and 'sidAddress' in row]
    isolated = [dict(tick=row['tick'], address=row['address'], value=row['value'])
                for row in observed['writes'] if row['phase'] == 'play' and row['tick'] < 128]
    require(isolated == machine, 'Isolated original music seed differs from retained machine128 tonal stores')
    machine_clear = [(row['address'], row['value']) for row in records
                     if row['phase'] == 'init' and row['operation'] == 'store' and row['pc'] == 0x906a]
    isolated_clear = [(row['address'], row['value']) for row in observed['writes'] if row['phase'] == 'init']
    require(machine_clear == isolated_clear and len(machine_clear) == 24, 'Isolated source register clear differs from retained machine init')
    return dict(receiptSha256=sha(receipt_path.read_bytes()), privateTraceSha256=sha(raw),
                machineBodies=128, matchedTonalStores=len(machine), matchedInitClearStores=24,
                namedMachineRamVerified=False,
                basis='Source-defined zero buffers plus executed music init; first128 ordered tonal stores and24 init clears match retained NTSC machine capture. Active music RAM was not sampled by that capture; isolated named state is not relabelled machine state.')


def intervention(data, description, observed, kind):
    edited = deepcopy(description)
    row = edited['patterns']['1']['rows'][0]
    original = deepcopy(row)
    if kind == 'note':
        row['note'] += 1
    else:
        edited['patterns']['1']['rows'][0] = score.set_duration(row, (row['header'] & 31) + 1)
    before, _ = score.encode_rows(description['patterns']['1']['rows'])
    after, _ = score.encode_rows(edited['patterns']['1']['rows'])
    changes = [index for index, pair in enumerate(zip(before, after)) if pair[0] != pair[1]]
    require(len(changes) == 1, 'Score control must edit exactly one source data byte')
    address = description['patterns']['1']['sourceEvidence']['address'] + changes[0]
    offset = address - 0x900d + 126
    private = bytearray(data)
    require(private[offset] == before[changes[0]], 'Score edit address differs from pinned data')
    private[offset] = after[changes[0]]
    actual = observe_source(bytes(private), edited, 128)
    check(edited, actual, 128)
    projection = lambda writes, companion: [dict(tick=row['tick'], address=row['address'], value=row['value'])
        for row in writes if row['phase'] == 'play' and row['tick'] < 128
        and (not companion or not 0xd400 <= row['address'] <= 0xd406)]
    require(projection(observed['writes'], True) == projection(actual['writes'], True), 'Score control altered companion/global stores')
    require(projection(observed['writes'], False) != projection(actual['writes'], False), 'Score control has no ordered-store consequence')
    before_rows = [value for value in observed['rows'] if value['tick'] < 128]
    require([value for value in before_rows if value['voice'] != 0] == [value for value in actual['rows'] if value['voice'] != 0],
            'Score control altered companion rows')
    before_onsets = [value['tick'] for value in before_rows if value['voice'] == 0]
    after_onsets = [value['tick'] for value in actual['rows'] if value['voice'] == 0]
    if kind == 'duration':
        require(before_onsets[1] == 16 and after_onsets[1] == 20, 'Duration+1 did not move the next onset by four calls')
    else:
        require(before_onsets == after_onsets, 'Note control changed row timing')
    receipt = dict(kind=kind, calls=128, sourceDataAddress=address, originalByte=before[changes[0]], editedByte=after[changes[0]],
                   privateCopySha256=sha(private), originalRow=original, editedRow=edited['patterns']['1']['rows'][0],
                   beforeVoice0Onsets=before_onsets, afterVoice0Onsets=after_onsets,
                   matchedScoreReads=len(actual['reads']), matchedRows=len(actual['rows']), matchedReturnStates=len(actual['returns']),
                   companionRowsEqual=True, companionGlobalStoresEqual=True, changedVoiceStores=True,
                   limits='One source-data byte changed in memory, with independent edited-score/source agreement and scoped ordered-store consequences; no audio or modelled sound claim.')
    return edited, actual, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/research/ghostbusters/Ghostbusters.sid')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calls', type=int, default=13961)
    parser.add_argument('--machine-receipt', type=Path, default=ROOT / 'evidence/ghostbusters-machine/verification.json')
    parser.add_argument('--machine-trace', type=Path)
    args = parser.parse_args()
    data = args.source.read_bytes()
    require(sha(data) == SOURCE_SHA, 'Pinned Ghostbusters source fingerprint differs')
    require(13957 <= args.calls <= 16000, 'Full form proof requires reset plus first restart, within16000 calls')
    require(not args.output.exists(), 'Choose a fresh output directory')
    header, _, description = decode_source(data)
    observed = observe_source(data, description, args.calls)
    check(description, observed, args.calls)
    require(len(observed['resets']) == 1 and observed['resets'][0]['tick'] == 13952,
            'Executed first global reset differs from predicted form')
    restarted = [row for row in observed['rows'] if row['tick'] > 13952]
    require(restarted and restarted[0]['tick'] == 13956 and [row['voice'] for row in restarted[:3]] == [2, 1, 0],
            'First post-reset score rows differ from predicted restart')
    machine_seed = verify_machine_seed(observed, args.machine_receipt.resolve(), args.machine_trace)
    controls = {kind: intervention(data, description, observed, kind) for kind in ('note', 'duration')}
    require(args.source.read_bytes() == data, 'Original source changed')
    paths = {Path(__file__).resolve(), Path(score.__file__).resolve()}
    paths.update(Path(module.__file__).resolve() for name, module in sys.modules.items()
                 if name in ('psid_audit', 'psid_profile', 'sid_audit_host', 'sid_clock', 'sid_intake', 'verify_player')
                 or name == 'py65' or name.startswith('py65.'))
    receipt = dict(schemaVersion=1, sourceSha256=SOURCE_SHA, selectedSubtune=1, clock='NTSC', sidModel='MOS6581',
        originalSourceUnchanged=True, musicCalls=args.calls, independentScoreEqual=True,
        matchedScoreReads=len(observed['reads']), matchedSemanticRows=len(observed['rows']), matchedReturnStates=len(observed['returns']),
        rowsPerVoice=dict(Counter(row['voice'] for row in observed['rows'] if row['tick'] < 13952)),
        patterns=len(description['patterns']), distinctPatternRows=sum(len(value['rows']) for value in description['patterns'].values()),
        firstResetCall=13952, firstRestartCall=13956, resetCaches=observed['resetCaches'],
        retainedMachineSeedCheck=machine_seed, audit=observed['audit'],
        controls={kind: value[2] for kind, value in controls.items()},
        tools={str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in sorted(paths)},
        python=dict(executable=sys.executable, version=sys.version),
        limits='Independent editable music score versus isolated original RAM-only music CPU through first reset/restart. Native context exchange/NTSC E2 phase and reset-retained score/sound caches checked; cached control remains sound-owned. Opening stores corroborated by retained machine128, not new fullmachineRSID/form/ROM/SID synthesis evidence. No speech bytes, decoder, complete machine recurrence, compiled runtime, selected finite ending or listening verdict.')
    args.output.mkdir(parents=True)
    save(args.output / 'score.json', description)
    save(args.output / 'receipt.json', receipt)
    for field in ('reads', 'rows', 'returns', 'resets', 'contexts', 'writes'):
        save(args.output / f'{field}.json', observed[field])
    for kind, (edited, actual, control_receipt) in controls.items():
        save(args.output / 'controls' / kind / 'score.json', edited)
        save(args.output / 'controls' / kind / 'receipt.json', control_receipt)
        for field in ('reads', 'rows', 'returns', 'writes'):
            save(args.output / 'controls' / kind / f'{field}.json', actual[field])
    print(json.dumps({key: receipt[key] for key in ('musicCalls', 'matchedScoreReads', 'matchedSemanticRows',
                      'matchedReturnStates', 'firstResetCall', 'firstRestartCall', 'retainedMachineSeedCheck')}))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, IndexError) as error:
        raise SystemExit(f'Ghostbusters form proof: {error}')
