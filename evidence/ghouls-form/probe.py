"""Observe the pinned Ghouls selection-1 streams under the shared callable host."""

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid
from psid_profile import psid_profile
from sid_audit_host import harness

SOURCE_SHA = '265644a66d6043e6fe5ddeeb0d87e9b4269386a73c3e26457c8d96ce3d042df4'
DISPATCH = {0x6362: 0, 0x654f: 1, 0x673e: 2}
DISPATCH_JUMPS = {0x6374: 0, 0x6561: 1, 0x6750: 2}
TABLE_BASES = ((0x6c37, 0x6c76), (0x6c4c, 0x6c8b), (0x6c61, 0x6ca0))
COMMANDS = {
    0x80: 'pulse-parameters', 0x81: 'repeat-end', 0x82: 'repeat-start',
    0x83: 'rest-parameters', 0x84: 'duration-override', 0x85: 'sid-store-list',
    0x86: 'disable-voice', 0x87: 'absolute-jump', 0x88: 'filter-parameters',
    0x89: 'filter-owner', 0x8a: 'call', 0x8b: 'return', 0x8c: 'transpose',
    0x8d: 'waveform', 0x8e: 'frequency-motion', 0x8f: 'onset-parameters',
    0x90: 'gate-time', 0x91: 'note-motion', 0x92: 'glide-rate',
    0x93: 'pitch-index-mode', 0x94: 'pulse-default',
}
READ_RANGES = ((0x6356, 0x6421), (0x6543, 0x6610), (0x6732, 0x67ff), (0x6858, 0x6cb7))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source():
    registry = json.loads((ROOT / 'config/local-assets.json').read_text())
    entry = next(row for row in registry['references'] if row['id'] == 'ghouls-n-ghosts')
    assert entry['sha256'] == SOURCE_SHA
    path = ROOT / entry['path']
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == SOURCE_SHA
    return data, entry


def word(ram, address):
    return ram[address] | ram[address + 1] << 8


def score_state(ram):
    return {
        'streamPointers': [word(ram, 0x21 + 2 * voice) for voice in range(3)],
        'durationRemaining': ram[0x27:0x2a], 'repeatRemaining': ram[0x2d:0x30],
        'repeatPointers': [word(ram, 0x30 + 2 * voice) for voice in range(3)],
        'callDepth': ram[0x69:0x6c], 'enableFlags': ram[0x7b:0x7e],
        'transpose': ram[0x4e:0x51], 'noteIndex': ram[0x66:0x69],
    }


def fingerprint(cpu, ram, call, reason):
    state = {name: getattr(cpu, name) for name in ('a', 'x', 'y', 'sp', 'p', 'pc')}
    cpu_bytes = bytes((cpu.a, cpu.x, cpu.y, cpu.sp, cpu.p, cpu.pc & 255, cpu.pc >> 8))
    memory_bytes = bytes(ram)
    return dict(call=call, reason=reason, cpu=state, scoreState=score_state(ram),
        ramSha256=hashlib.sha256(memory_bytes).hexdigest(),
        ramCpuSha256=hashlib.sha256(memory_bytes + cpu_bytes).hexdigest())


def summarize(events, bodies, fingerprints, initial):
    root_reads = [[] for _ in range(3)]
    command_counts = Counter()
    disabled = []
    for row in events:
        if row['kind'] == 'dispatchRead' and row['address'] == initial['streamPointers'][row['voice']] and row['callDepth'] == 0:
            root_reads[row['voice']].append(row['call'])
        if row['kind'] == 'commandDispatch':
            command_counts[(row['voice'], row['command'])] += 1
            if row['command'] == 0x86:
                disabled.append(row)
    all_inactive = [row['call'] for row in bodies if all(value < 128 for value in row['enableFlags'])]
    previous = initial['enableFlags']
    changes = []
    for row in bodies:
        if row['enableFlags'] != previous:
            changes.append(dict(call=row['call'], before=previous, after=row['enableFlags']))
            previous = row['enableFlags']
    hashes = defaultdict(list)
    for row in fingerprints:
        hashes[row['ramCpuSha256']].append(row['call'])
    return dict(processedCalls=len(bodies), firstBody=bodies[0], lastBody=bodies[-1],
        eventCounts=dict(Counter(row['kind'] for row in events)),
        commandCounts=[dict(voice=voice, command=command, name=COMMANDS.get(command, 'unclassified'), visits=count)
                       for (voice, command), count in sorted(command_counts.items())],
        initialStreamDispatchCalls=root_reads, disableCommands=disabled, enableFlagChanges=changes,
        firstAllInactiveCall=all_inactive[0] if all_inactive else None,
        allInactiveCalls=len(all_inactive), wholeBackingStateRepeats=[calls for calls in hashes.values() if len(calls) > 1],
        limits='Root-pointer reads and enable flags are score observations, not proof of musical sections, oscillator/envelope state or PCM recurrence. A sampled whole backing-RAM/CPU repeat excludes SID internals and cycle count.')


def collect(data, ticks):
    profile = psid_profile(data, profile='pal-banked', subtune=1)
    _, labels = harness(profile, 1)
    events, bodies, fingerprints, copies = [], [], [], []
    initial = None
    pending = {}
    root_voices = set()
    previous_flags = None
    last_tick = None
    started = False

    def observe(cpu, memory):
        nonlocal initial, previous_flags, last_tick, started
        ram, pc = memory.data, cpu.pc
        if memory.phase == 'init':
            if pc == 0x29b6:
                copies.append(dict(pc=pc, source=word(ram, 0xfc), destination=word(ram, 0xfa),
                                   bytes=(cpu.x << 8) | cpu.y, bankBefore=ram[1]))
            return
        call = memory.tick
        if initial is None:
            initial = score_state(ram)
            previous_flags = initial['enableFlags']
        if call != last_tick:
            if call % 2048 == 0:
                print(f'Ghouls audit call {call}/{ticks}, events={len(events)}, SID stores={len(memory.writes)}', flush=True)
            last_tick = call
            root_voices.clear()
        if pc in DISPATCH_JUMPS:
            voice = DISPATCH_JUMPS[pc]
            row = pending.pop(voice)
            low, high = TABLE_BASES[voice]
            target = word(ram, pc + 1)
            assert target == (ram[low + row['value']] | ram[high + row['value']] << 8)
            events.append(dict(kind='commandDispatch', call=call, pc=pc, voice=voice, command=row['value'],
                name=COMMANDS.get(row['value'], 'unclassified'), consumedAddress=row['address'], targetPC=target,
                lowTableAddress=low + row['value'], highTableAddress=high + row['value'],
                tableBytes=[ram[low + row['value']], ram[high + row['value']]],
                callDepth=ram[0x69 + voice], repeatRemaining=ram[0x2d + voice],
                enableFlag=ram[0x7b + voice]))
        if any(first <= pc < end for first, end in READ_RANGES) and ram[pc] == 0xb1 and ram[pc + 1] in (0x21, 0x23, 0x25):
            pointer_byte = ram[pc + 1]
            voice = (pointer_byte - 0x21) // 2
            pointer = word(ram, pointer_byte)
            address = (pointer + cpu.y) & 65535
            row = dict(kind='dispatchRead' if pc in DISPATCH else 'streamOperandRead', call=call,
                pc=pc, voice=voice, pointer=pointer, y=cpu.y, address=address, value=ram[address],
                callDepth=ram[0x69 + voice], repeatRemaining=ram[0x2d + voice])
            events.append(row)
            if pc in DISPATCH:
                assert DISPATCH[pc] == voice and cpu.y == 0
                if row['value'] >= 128:
                    pending[voice] = row
                if address == initial['streamPointers'][voice] and row['callDepth'] == 0:
                    root_voices.add(voice)
        if pc == 0x6857 and cpu.sp == 0xfd:
            assert word(ram, 0x1fe) == labels['play_return'] - 1
            assert not pending
            state = score_state(ram)
            bodies.append(dict(call=call, **state))
            inactive = all(value < 128 for value in state['enableFlags'])
            before_active = any(value >= 128 for value in previous_flags)
            reasons = []
            if call == 0:
                reasons.append('first-body')
            if root_voices == {0, 1, 2}:
                reasons.append('all-initial-streams-dispatched')
            if inactive and before_active:
                reasons.append('first-all-voices-inactive')
            if call == ticks - 1:
                reasons.append('last-requested-body')
            if reasons:
                fingerprints.append(fingerprint(cpu, ram, call, reasons))
            previous_flags = state['enableFlags']
            started = True

    report, writes = audit_psid(data, ticks, observer=observe, profile='pal-banked', subtune=1)
    assert started and len(bodies) == ticks and [row['call'] for row in bodies] == list(range(ticks))
    return dict(initialState=initial, initializationCopies=copies, events=events, bodies=bodies,
                fingerprints=fingerprints), report, writes


def publish(path, data, *, compressed=False):
    raw = (json.dumps(data, separators=(',', ':')) + '\n').encode() if compressed else (json.dumps(data, indent=2) + '\n').encode()
    stored = gzip.compress(raw, mtime=0) if compressed else raw
    with path.open('xb') as output:
        output.write(stored)
    return dict(bytes=len(stored), sha256=hashlib.sha256(stored).hexdigest(),
                decodedBytes=len(raw), decodedSha256=hashlib.sha256(raw).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ticks', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists() and not args.output.is_symlink(), 'Choose a fresh output directory'
    assert type(args.ticks) is int and 1 <= args.ticks <= 100000
    data, entry = source()
    observations, report, writes = collect(data, args.ticks)
    summary = summarize(observations['events'], observations['bodies'], observations['fingerprints'], observations['initialState'])
    args.output.mkdir(parents=True)
    outputs = {}
    for name, value, compressed in [('observations.json.gz', observations, True), ('audit.writes.json.gz', writes, True),
            ('audit.json', report, False), ('summary.json', summary, False)]:
        outputs[name] = publish(args.output / name, value, compressed=compressed)
    receipt = dict(sourceSha256=SOURCE_SHA, sourceURL=entry['url'], selectedSubtune=1, musicalRole='provisional',
        executionProfile='pal-banked', hostBase=0xc000, requestedCalls=args.ticks, processedCalls=len(observations['bodies']),
        sourceBytesUnchanged=(ROOT / entry['path']).read_bytes() == data,
        scriptSha256=sha(Path(__file__)), registrySha256=sha(ROOT / 'config/local-assets.json'),
        tools={name: sha(ROOT / 'scripts' / name) for name in ('psid_audit.py', 'psid_profile.py', 'sid_audit_host.py', 'verify_player.py')},
        outputHashes=outputs, stateHashRecipe='At pre-RTS $6857/SP$FD with verified host return word: SHA256(bytes(AuditMemory.data)), and SHA256(the same 65536 bytes || A || X || Y || SP || P || PClo || PChi); no normalization, no cycle count, no memory dump retained.',
        limits='Shared guarded CPU callable host, not original interrupt host. Source copied numeric stream data during init; no source SID/payload/RAM image published. No sound, bus timing or listening claim.')
    publish(args.output / 'receipt.json', receipt)
    print(json.dumps(dict(output=str(args.output), processedCalls=args.ticks, playWrites=report['playWriteCount'],
        firstAllInactiveCall=summary['firstAllInactiveCall'], initialStreamDispatchCalls=summary['initialStreamDispatchCalls'],
        maximumPlayCycles=report['maximumPlayCycles'])), flush=True)


if __name__ == '__main__':
    main()
