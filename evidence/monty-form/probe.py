"""Observe pinned Monty score consumption and order wraps without decoding sound."""

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid
from psid_profile import psid_profile
from sid_audit_host import harness

SOURCE_SHA = '528a7330817e4a0a0f75a505e9fe2444e07c5072ce5383ceaa89f183f0eee3ab'
LISTING_SHA = '52dbbf891b1a1d0f8750842ef91ebaf1fc62d65d7b46497ae6951576ece3ae6c'
HOOKS = {0x8089: 'orderRead', 0x8099: 'orderRestart', 0x8096: 'orderFEExit',
         0x80ab: 'patternPointerLow', 0x80b0: 'patternPointerHigh',
         0x80c2: 'rowControlRead', 0x80dd: 'instrumentOrPortamentoRead',
         0x80e7: 'instrumentSet', 0x80ee: 'pitchRead', 0x8118: 'appendBranch',
         0x811e: 'initializerInstrument', 0x8163: 'patternEndPeek',
         0x8169: 'patternReset', 0x816e: 'orderAdvance'}
STATE_ARRAYS = {'orderCursor': 0x84c4, 'patternCursor': 0x84c7, 'remaining': 0x84ca,
                'savedControl': 0x84cd, 'voiceControl': 0x84d0, 'note': 0x84d3,
                'instrument': 0x84d6, 'portamento': 0x84f5}
TOOL_PATHS = ('scripts/psid_audit.py', 'scripts/psid_profile.py', 'scripts/sid_audit_host.py', 'scripts/verify_player.py')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def named_state(memory):
    return {name: memory.data[address:address + 3] for name, address in STATE_ARRAYS.items()} | {
        'tempo': memory.data[0x84eb], 'tempoReload': memory.data[0x84ec],
        'status': memory.data[0x84ee], 'counter': memory.data[0x84fa],
        'sfxFlags': memory.data[0x84fb:0x84fe]}


def listing_comparison(text, parsed):
    comparisons = []
    for label, boundary in (('montymaintr1 =*', ';track2'), ('montymaintr2 =*', ';track3'),
                            ('montymaintr3 =*', ';patterns')):
        block = text.split(label, 1)[1].split(boundary, 1)[0]
        values = bytes(int(value, 16) for line in block.splitlines() if line.lstrip().startswith('!by')
                       for value in re.findall(r'\$([0-9a-fA-F]{2})', line.split(';')[0]))
        matches = [parsed['loadAddress'] + index for index in range(len(parsed['payload']) - len(values) + 1)
                   if parsed['payload'][index:index + len(values)] == values]
        if len(matches) != 1:
            raise ValueError('Expected one complete title-order match for ' + label)
        comparisons.append(dict(listingLabel=label, bytes=len(values), sha256=sha(values), archiveAddress=matches[0]))
    return comparisons


def observe(data, ticks, listing):
    parsed = psid_profile(data, profile='pal-banked', subtune=1)
    _, labels = harness(parsed, 1)
    events, checkpoints, restart_ticks = [], [], set()
    completed = 0

    def observer(cpu, memory):
        nonlocal completed
        if memory.phase != 'play':
            return
        tick, pc = memory.tick, cpu.pc
        if pc == parsed['playAddress'] and tick % 1024 == 0:
            print(json.dumps({'heartbeatCall': tick, 'completedCalls': completed, 'events': len(events)}), flush=True)
        if pc in HOOKS:
            state = named_state(memory)
            row = dict(call=tick, pc=pc, kind=HOOKS[pc], instructionStartCycle=memory.instruction_cycle,
                       a=cpu.a, x=cpu.x, y=cpu.y, status=cpu.p, sp=cpu.sp, state=state,
                       instructionBytes=bytes(memory.data[pc:pc + (2 if pc in
                           (0x8089, 0x8099, 0x80c2, 0x80dd, 0x80ee, 0x8163, 0x8169) else 3)]).hex())
            if pc in (0x8089, 0x80c2, 0x80dd, 0x80ee, 0x8163):
                pointer = 2 if pc == 0x8089 else 4
                address = ((memory.data[pointer] | memory.data[pointer + 1] << 8) + cpu.y) & 65535
                row.update(sourceAddress=address, value=memory.data[address])
            elif pc in (0x80ab, 0x80b0):
                address = (0x857e if pc == 0x80ab else 0x85cb) + cpu.y
                row.update(sourceAddress=address, value=memory.data[address])
            if pc == 0x811e:
                index = memory.data[0x84d6 + cpu.x]
                address = 0x93b4 + ((index * 8) & 255)
                row.update(instrumentIndex=index, recordAddress=address,
                           recordValues=memory.data[address:address + 8])
            if pc == 0x8099:
                restart_ticks.add(tick)
            events.append(row)
        if pc == 0x838c and cpu.sp == 0xfd:
            saved = memory.data[0x1fe] | memory.data[0x1ff] << 8
            if saved != labels['play_return'] - 1:
                raise ValueError('Outer return stack word differs from the shared host')
            completed += 1
            if tick == 0 or tick == ticks - 1 or tick in restart_ticks:
                cpu_state = dict(pc=cpu.pc, a=cpu.a, x=cpu.x, y=cpu.y, sp=cpu.sp, status=cpu.p)
                ram_digest = sha(bytes(memory.data))
                combined = json.dumps(dict(ramSha256=ram_digest, cpu=cpu_state), sort_keys=True, separators=(',', ':')).encode()
                checkpoints.append(dict(call=tick, boundary='before outer RTS $838C with SP=$FD',
                    state=named_state(memory), ramSha256=ram_digest, cpu=cpu_state, stateSha256=sha(combined)))

    report, writes = audit_psid(data, ticks, profile='pal-banked', subtune=1, observer=observer)
    if completed != ticks:
        raise ValueError(f'Observed {completed} outer returns for {ticks} calls')
    wrap_events = [row for row in events if row['kind'] == 'orderRestart']
    return dict(schemaVersion=1, actualProcessedCalls=completed, audit=report,
        hooks={f'{pc:04x}': kind for pc, kind in HOOKS.items()},
        staticTitleOrderMatches=listing_comparison(listing, parsed),
        events=events, boundaryCheckpoints=checkpoints,
        summary=dict(eventCounts=dict(Counter(row['kind'] for row in events)),
            orderRestartsByVoice={str(voice): [row['call'] for row in wrap_events if row['x'] == voice] for voice in range(3)},
            jointOrderRestartCalls=sorted(tick for tick in restart_ticks if {row['x'] for row in wrap_events if row['call'] == tick} == {0, 1, 2}),
            repeatedStateFingerprints={key: [row['call'] for row in checkpoints if row['stateSha256'] == key]
                for key, count in Counter(row['stateSha256'] for row in checkpoints).items() if count > 1}),
        hashRecipe='RAM: SHA-256 of all 65536 backing-memory bytes. State: SHA-256 of sorted-key compact JSON {ramSha256,cpu:{pc,a,x,y,sp,status}} at pre-RTS $838C/SP=$FD; no normalization. Absolute processorCycles omitted; no SID internal state is modeled.',
        limits='Order restart is per voice. Joint order wraps do not establish whole sound-state or PCM recurrence. FE is retained as an exit branch, not assumed to mute/set a global stop flag. Only hook instructions are retained; no complete source payload or RAM dump.'), writes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ticks', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if type(args.ticks) is not int or not 1 <= args.ticks <= 100000:
        raise ValueError('Select 1..100000 complete play calls')
    if args.output.exists() or args.output.is_symlink():
        raise ValueError('Choose a fresh output directory')
    data = (ROOT / '.local/monty-source.sid').read_bytes()
    listing_path = Path(__file__).with_name('Hubbard_Rob_Monty_on_the_Run.asm')
    listing_bytes = listing_path.read_bytes()
    if sha(data) != SOURCE_SHA or sha(listing_bytes) != LISTING_SHA:
        raise ValueError('Intact source/listing pin mismatch')
    tools = {name: sha((ROOT / name).read_bytes()) for name in TOOL_PATHS}
    report, writes = observe(data, args.ticks, listing_bytes.decode())
    report['provenance'] = dict(sourceSha256=SOURCE_SHA, listingSha256=LISTING_SHA,
        listingGitBlobSha1='332b81b5ddd21d1ab20c7cd37c32ac786760a267', tools=tools,
        probeSha256=sha(Path(__file__).read_bytes()))
    ledger = (json.dumps(writes, separators=(',', ':')) + '\n').encode()
    report['orderedLedger'] = dict(records=len(writes), decodedSha256=sha(ledger), path='audit.writes.json.gz')
    args.output.mkdir(parents=True)
    for name, content in (('observations.json.gz', (json.dumps(report, separators=(',', ':')) + '\n').encode()),
                          ('audit.writes.json.gz', ledger)):
        with (args.output / name).open('xb') as target:
            target.write(gzip.compress(content, mtime=0))
    with (args.output / 'summary.json').open('x') as target:
        json.dump({key: report[key] for key in ('actualProcessedCalls', 'audit', 'summary', 'provenance', 'orderedLedger', 'hashRecipe', 'limits')}, target, indent=2)
        target.write('\n')
    print(json.dumps({'complete': args.ticks, 'output': str(args.output), 'summary': report['summary']}), flush=True)


if __name__ == '__main__':
    main()
