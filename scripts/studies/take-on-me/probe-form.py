"""Prove the pinned Take On Me form and editable score against executed source."""

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid
from psid_profile import psid_profile
from verify_player import require
import score


SOURCE_SHA = 'c7e45037d20c3b85d18fc955a1cdfb70041f08dfc171e9b12d1c3327300101e6'
INDIRECT_FIELDS = {
    0x10a5: 'order', 0x10b8: 'orderJumpTarget', 0x10be: 'orderAfterJump',
    0x10cc: 'orderAfterRepeat', 0x10dc: 'patternAfterCommands',
    0x10ec: 'rowHeader', 0x10f5: 'arpeggio', 0x10fb: 'afterArpeggio',
    0x1107: 'afterInstrument', 0x1114: 'afterDuration',
    0x111b: 'glideStepLow', 0x1121: 'glideStepHigh', 0x1127: 'glideNote',
    0x1131: 'glideTarget', 0x114e: 'followingByte',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    encoded = (json.dumps(value, indent=2) + '\n').encode()
    if path.suffix == '.gz':
        encoded = gzip.compress(encoded, mtime=0)
    with path.open('xb') as output:
        output.write(encoded)


def observe_source(data, description, calls, model, checkpoints=()):
    """Use the shared read-only instruction observer; no emulator or tracer is added."""
    reads, rows, wraps, stops, returns, state_hashes, texture = [], [], [], [], [], [], []
    current_patterns, current_addresses = [None] * 3, [None] * 3
    row_offsets = {int(key): score.encode_rows(pattern['rows'])[1] for key, pattern in description['patterns'].items()}
    previous_ram = None

    def named(memory, voice):
        return {name: memory.data[address + voice] for name, address in score.FIELDS.items()}

    def observer(cpu, memory):
        nonlocal previous_ram
        if memory.phase != 'play':
            return
        pc, tick, voice = cpu.pc, memory.tick, cpu.x
        if pc in INDIRECT_FIELDS:
            address = ((memory.data[0xe0] | memory.data[0xe1] << 8) + cpu.y) & 65535
            reads.append(dict(tick=tick, voice=voice, pc=pc, address=address,
                              value=memory.data[address], field=INDIRECT_FIELDS[pc]))
            if pc == 0x10ec:
                current_addresses[voice] = address
        elif pc in (0x10df, 0x10e4):
            address = (0x15ad if pc == 0x10df else 0x15bf) + cpu.y
            reads.append(dict(tick=tick, voice=voice, pc=pc, address=address,
                              value=memory.data[address], field='patternPointerLow' if pc == 0x10df else 'patternPointerHigh'))
            if pc == 0x10df:
                current_patterns[voice] = cpu.y
        elif pc == 0x10ab:
            stops.append(dict(tick=tick, voice=voice))
        elif pc == 0x1168:
            pattern = current_patterns[voice]
            address = current_addresses[voice]
            base = description['patterns'][str(pattern)]['address']
            rows.append(dict(tick=tick, voice=voice, pattern=pattern,
                             row=row_offsets[pattern].index(address - base), address=address,
                             glideActive=memory.data[0x1aba + voice], state=named(memory, voice)))
        if pc == 0x10be:
            wraps.append(dict(tick=tick, voice=voice, target=cpu.y))
        if pc in (0x14d8, 0x1054, 0x104a):
            require(cpu.sp == 0xfd, 'Unexpected callable return stack')
            returns.append(dict(tick=tick, active=bool(memory.data[0x1a96]),
                                dividers=memory.data[0x1a97:0x1a99],
                                voices=[named(memory, index) for index in range(3)]))
            controls = [memory.data[0xd404 + index * 7] for index in range(3)]
            texture.append(dict(tick=tick, controls=controls,
                                cutoffWord=(memory.data[0xd415] & 7) | memory.data[0xd416] << 3,
                                routing=memory.data[0xd417]))
            if tick in checkpoints:
                ram = bytes(memory.data)
                cpu_state = dict(a=cpu.a, x=cpu.x, y=cpu.y, p=cpu.p, sp=cpu.sp, pc=cpu.pc)
                changes = None if previous_ram is None else [dict(address=address, before=before, after=after)
                    for address, (before, after) in enumerate(zip(previous_ram, ram)) if before != after]
                state_hashes.append(dict(tick=tick, ramSha256=sha(ram), cpu=cpu_state,
                                         ramAndCpuSha256=sha(ram + bytes(cpu_state[key] for key in ('a', 'x', 'y', 'p', 'sp')) + cpu.pc.to_bytes(2, 'little')),
                                         ramChangesFromPrevious=changes))
                previous_ram = ram

    audit, writes = audit_psid(data, calls, observer=observer, profile='pal-banked',
                               subtune=1, assume_sid_model=model)
    return dict(reads=reads, rows=rows, wraps=wraps, stops=stops, returns=returns,
                stateHashes=state_hashes, texture=texture, audit=audit, writes=writes)


def check(description, observed, calls):
    computed = score.expand(description, calls)
    for key in ('reads', 'rows', 'wraps', 'stops', 'returns'):
        actual, expected = observed[key], computed[key]
        if actual != expected:
            first = next((index for index, pair in enumerate(zip(actual, expected)) if pair[0] != pair[1]), min(len(actual), len(expected)))
            raise ValueError(f'{key} mismatch at {first}: executed={actual[first:first + 1]}, computed={expected[first:first + 1]}')
    return computed


def score_recurrence(returns):
    seen = {}
    for row in returns:
        value = {key: item for key, item in row.items() if key != 'tick'}
        encoded = json.dumps(value, sort_keys=True, separators=(',', ':'))
        if encoded in seen:
            return dict(firstReturnCall=seen[encoded], repeatedReturnCall=row['tick'], periodCalls=row['tick'] - seen[encoded])
        seen[encoded] = row['tick']
    return None


def texture_window(texture, length=400):
    eligible = [sum(bool(control & 1 and control & 0xf0) for control in row['controls']) == 3
                and row['cutoffWord'] > 0 and row['routing'] & 7 != 0 for row in texture]
    if len(eligible) < length:
        return None
    count, best = sum(eligible[:length]), None
    for start in range(len(eligible) - length + 1):
        if best is None or count > best['fullTextureFilterCalls']:
            best = dict(firstCall=start, lastCallExclusive=start + length, fullTextureFilterCalls=count)
        if count == length:
            break
        if start + length < len(eligible):
            count += eligible[start + length] - eligible[start]
    return best


def intervention(data, description, baseline, model):
    changed = json.loads(json.dumps(description))
    pattern = changed['patterns']['2']
    row = pattern['rows'][0]
    require(row['durationUnits'] == 4, 'Pinned opening duration changed')
    row['durationUnits'] = 5
    original, _ = score.encode_rows(description['patterns']['2']['rows'])
    edited, _ = score.encode_rows(pattern['rows'])
    offsets = [index for index, pair in enumerate(zip(original, edited)) if pair[0] != pair[1]]
    require(len(offsets) == 1, 'Duration intervention is not one byte')
    address = pattern['address'] + offsets[0]
    offset = address - 0x1000 + 126
    private = bytearray(data)
    require(private[offset] == original[offsets[0]], 'Mutation address does not match the source')
    private[offset] = edited[offsets[0]]
    calls = 128
    observed = observe_source(bytes(private), changed, calls, model)
    check(changed, observed, calls)
    before_rows = [entry for entry in baseline['rows'] if entry['tick'] < calls]
    require([entry for entry in before_rows if entry['voice'] != 1] == [entry for entry in observed['rows'] if entry['voice'] != 1], 'Duration edit changed companion score rows')
    before_onsets = [entry['tick'] for entry in before_rows if entry['voice'] == 1]
    after_onsets = [entry['tick'] for entry in observed['rows'] if entry['voice'] == 1]
    require(before_onsets[1] == 8 and after_onsets[1] == 10, 'Duration edit did not move the second onset as predicted')

    def projection(writes, companions):
        return [{key: entry[key] for key in ('phase', 'tick', 'address', 'value')}
                for entry in writes if (entry['tick'] is None or entry['tick'] < calls)
                and ((not 0xd407 <= entry['address'] <= 0xd40d) if companions else True)]

    require(projection(baseline['writes'], True) == projection(observed['writes'], True), 'Duration edit changed companion/global SID values or order')
    require(projection(baseline['writes'], False) != projection(observed['writes'], False), 'Duration edit has no SID-store consequence')
    return dict(sourceUnchanged=True, privateCopySha256=sha(private), address=address,
                originalByte=original[offsets[0]], editedByte=edited[offsets[0]], calls=calls,
                beforeVoice1Onsets=before_onsets, afterVoice1Onsets=after_onsets,
                companionScoreRowsEqual=True, companionAndGlobalOrderedStoresEqual=True,
                changedScore=changed, executed=observed,
                limits='One-byte duration edit on an in-memory source copy. Score/model agreement and scoped ordered-store consequences; no sound-model or listening claim.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sid', type=Path, default=ROOT / '.local/research/take-on-me/Take_on_Me.sid')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calls', type=int, default=8961)
    parser.add_argument('--assume-sid-model', choices=('MOS6581', 'MOS8580'), default='MOS8580')
    args = parser.parse_args()
    data = args.sid.read_bytes()
    require(sha(data) == SOURCE_SHA, 'Pinned Take On Me source fingerprint differs')
    parsed = psid_profile(data, profile='pal-banked', subtune=1, assume_sid_model=args.assume_sid_model)
    ram = [0] * 65536
    ram[parsed['loadAddress']:parsed['endAddress']] = parsed['payload']
    description = score.decode(ram)
    description['sourceEvidence'] = dict(sha256=SOURCE_SHA, declaredSidModel='unknown', flags=4,
                                        selectedSubtune=1, experimentalSidModel=args.assume_sid_model)
    predicted = score.expand(description, args.calls)
    recurrence = score_recurrence(predicted['returns'])
    require(recurrence is not None and len(predicted['wraps']) >= 6, 'Select calls covering two complete score-loop traversals and the next wrap')
    start, period = recurrence['firstReturnCall'], recurrence['periodCalls']
    checkpoints = tuple(start + period * cycle for cycle in range(3))
    observed = observe_source(data, description, args.calls, args.assume_sid_model, checkpoints)
    check(description, observed, args.calls)
    edited = intervention(data, description, observed, args.assume_sid_model)
    require(args.sid.read_bytes() == data, 'Original source changed')
    opening = json.loads(gzip.decompress((ROOT / 'evidence/take-on-me-model/checked/MOS6581/writes.json.gz').read_bytes()))
    require(opening == [entry for entry in observed['writes'] if entry['phase'] == 'init' or entry['tick'] < 64], 'Retained opening ledger differs')
    count = Counter(row['voice'] for row in observed['rows'])
    hashes = observed['stateHashes']
    imported = {Path(module.__file__).resolve() for name, module in sys.modules.items()
                if name in ('score', 'psid_audit', 'psid_profile', 'sid_audit_host', 'sid_clock', 'verify_player')
                or name == 'py65' or name.startswith('py65.')}
    tools = {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in sorted(imported | {Path(__file__).resolve()})}
    receipt = dict(schemaVersion=1, sourceSha256=SOURCE_SHA, declaredSidModel='unknown',
                   experimentalSidModel=args.assume_sid_model, selectedSubtune=1, playCalls=args.calls,
                   sourceUnchanged=True, retainedOpening64Equal=True, numericScoreEqual=True,
                   matchedScoreReads=len(observed['reads']), matchedRows=len(observed['rows']),
                   matchedReturnStates=len(observed['returns']), rowsPerVoice=dict(count),
                   patterns=len(description['patterns']), semanticRows=sum(len(p['rows']) for p in description['patterns'].values()),
                   scoreRecurrence=recurrence, wraps=observed['wraps'], stops=observed['stops'],
                   recurrenceCheckpoints=hashes,
                   ramAndCpuCheckpointsEqual=len({row['ramAndCpuSha256'] for row in hashes}) == 1,
                   settledRamAndCpuRecurrence=hashes[-2]['ramAndCpuSha256'] == hashes[-1]['ramAndCpuSha256'],
                   textureWindow=texture_window(observed['texture']),
                   tools=tools, python=dict(executable=sys.executable, version=sys.version),
                   limits='Executed RAM-only score form and independent numeric score expansion. Return hashes cover backing RAM and A/X/Y/P/SP/PC before RTS, excluding absolute cycles and physical SID/CIA/VIC state. No sound synthesis, compiled player, VICE whole-form proof, chosen finite ending, acoustic recurrence or listening verdict.')
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / 'score.json', description)
    save(args.output / 'audit.json', observed['audit'])
    for key in ('reads', 'rows', 'returns', 'texture'):
        save(args.output / f'{key}.json.gz', observed[key])
    save(args.output / 'writes.json', observed['writes'])
    save(args.output / 'intervention.json.gz', edited)
    save(args.output / 'receipt.json', receipt)
    print(json.dumps({key: receipt[key] for key in ('playCalls', 'matchedScoreReads', 'matchedRows', 'scoreRecurrence', 'wraps', 'stops', 'ramAndCpuCheckpointsEqual', 'textureWindow')}))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, IndexError) as error:
        raise SystemExit(f'Take On Me form probe failed: {error}')
