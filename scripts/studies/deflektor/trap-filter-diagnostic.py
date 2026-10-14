#!/usr/bin/env python3
"""Execute a private Trap voice-2 filter bypass and measure its contextual signal."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from audio_comparison import read_pcm16
from psid_audit import audit_psid
from sid_intake import inspect_sid
from verify_player import require


SOURCE_SHA = 'c8954d2020bbd3b3d7dd75a6e376057e36816591042275ae864ea8ff2c034e20'
PATCH_ADDRESS = 0xc936
CALLS = 1600


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    with path.open('x') as output:
        output.write(json.dumps(value, indent=2, allow_nan=False) + '\n')


def patch_source(data, header):
    prefix = header['dataOffset'] + (2 if header['headerLoadAddress'] == 0 else 0)
    offset = prefix + PATCH_ADDRESS - header['loadAddress']
    require(prefix <= offset < len(data), 'Routing data address escapes the source payload')
    require(data[offset] == 0x82, 'Expected verified routing source byte $82')
    result = bytearray(data)
    result[offset] = data[offset] & ~2
    return bytes(result), dict(address=PATCH_ADDRESS, fileOffset=offset, original=0x82,
                               candidate=0x80, clearedBit=2,
                               basis='Executed C080 parameter read -> C394 setter -> C5B6 shadow -> C017/C01A SID writer.')


def execute(data):
    reads, setters, commands = [], [], []
    latest_parameter = None

    def observe(cpu, memory):
        nonlocal latest_parameter
        if memory.phase != 'play':
            return
        ram, pc = memory.data, cpu.pc
        if pc in (0xc067, 0xc080):
            require(bytes(ram[pc:pc + 2]) == b'\xb1\xaa', 'Expected source stream reader changed')
            address = ((ram[0xaa] | ram[0xab] << 8) + cpu.y) & 65535
            record = dict(call=memory.tick, instructionStartCycle=memory.instruction_cycle,
                          pc=pc, voiceIndex=cpu.x, address=address, value=ram[address])
            if pc == 0xc067:
                commands.append(record)
            else:
                latest_parameter = record
                if address == PATCH_ADDRESS:
                    reads.append(record)
        elif pc == 0xc394:
            require(bytes(ram[pc:pc + 3]) == b'\x8d\xb6\xc5', 'Expected routing-shadow setter changed')
            require(latest_parameter is not None and latest_parameter['value'] == cpu.a,
                    'Routing setter lacks a matching executed parameter read')
            setters.append(dict(call=memory.tick, instructionStartCycle=memory.instruction_cycle,
                                pc=pc, shadowAddress=0xc5b6, value=cpu.a,
                                parameterRead=dict(latest_parameter)))

    audit, writes = audit_psid(data, CALLS, observer=observe, profile='pal-banked',
                               subtune=1, host_base=0x0400)
    require(reads and setters, 'Bounded execution did not consume the routing parameter')
    require(all(row['parameterRead']['address'] == PATCH_ADDRESS for row in setters),
            'Another source byte supplies routing within this diagnostic scope')
    return dict(audit=audit, writes=writes, patchReads=reads, routingSetters=setters,
                scoreCommands=commands)


def compare_ledgers(original, bypass):
    require(len(original) == len(bypass), 'Bypass changed the number of ordered SID stores')
    changed = []
    identity = ('phase', 'tick', 'instructionStartCycle', 'address')
    for index, (left, right) in enumerate(zip(original, bypass)):
        require(all(left[key] == right[key] for key in identity),
                'Bypass changed store order, address, call or instruction timing')
        if left['value'] == right['value']:
            continue
        require(left['address'] == 0xd417, 'Bypass changed a value outside $D417')
        require(left['value'] & 2 and right['value'] == left['value'] & ~2,
                'Bypass changed more than the voice-2 route bit')
        changed.append(dict(index=index, phase=left['phase'], call=left['tick'],
                            instructionStartCycle=left['instructionStartCycle'],
                            address=left['address'], original=left['value'], candidate=right['value']))
    require(changed, 'Bypass did not change the intended routing stores')
    return changed


def run_execution(source, output):
    raw = source.read_bytes()
    require(sha(raw) == SOURCE_SHA, 'Trap source does not match the preserved original pin')
    registry = json.loads((ROOT / 'config/local-assets.json').read_text())
    asset = next(row for row in registry['references'] if row['id'] == 'trap')
    require(asset['sha256'] == SOURCE_SHA, 'Registry and diagnostic source pins disagree')
    header = inspect_sid(raw, subtune=1, host_base=0x0400)
    require(header['callableProfile']['accepted'], 'Trap requires its admitted callable profile')
    patched, change = patch_source(raw, header)
    original, bypass = execute(raw), execute(patched)
    changed = compare_ledgers(original['writes'], bypass['writes'])
    require(original['scoreCommands'] == bypass['scoreCommands'],
            'Bypass changed score command addresses, values, order or instruction timing')
    require([row['call'] for row in original['routingSetters']] == [601] and
            [row['call'] for row in bypass['routingSetters']] == [601],
            'Routing setup moved outside the identified call-601 event')
    require(original['routingSetters'][0]['value'] == 0x82 and
            bypass['routingSetters'][0]['value'] == 0x80,
            'Executed source-data intervention did not reach its routing setter')
    require(changed[0]['call'] == 601 and all(row['phase'] == 'play' for row in changed),
            'Routing intervention changed initialization or began at another call')
    require(source.read_bytes() == raw, 'Original Trap source changed during the diagnostic')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'trap-voice2-filter-bypass.sid').write_bytes(patched)
    write_json(output / 'original.json', original)
    write_json(output / 'bypass.json', bypass)
    write_json(output / 'changed-routing.json', changed)
    receipt = dict(schemaVersion=1, source=dict(path=str(source.relative_to(ROOT)),
                    sha256=SOURCE_SHA, url=asset['url'], bytes=len(raw), unchanged=True),
                   selection=dict(subtune=1, model='MOS6581', clock='PAL', profile='pal-banked',
                                  hostBase=0x0400, calls=CALLS),
                   patch=dict(change, patchedSha256=sha(patched), changedSourceBytes=1),
                   proof=dict(matchedStorePositions=len(original['writes']),
                              changedRoutingStores=len(changed), firstChangedCall=changed[0]['call'],
                              lastChangedCall=changed[-1]['call'], scoreCommandIdentity=True,
                              unchangedPorts='Every port except the cleared $D417 voice-2 routing bit, including all voice frequency, pulse, control, ADSR and filter cutoff/mode/volume stores.',
                              timingIdentity='Phase, play call, store order and instruction-start cycles; not bus cycles.'),
                   tools={name: sha((ROOT / name).read_bytes()) for name in
                          ('scripts/studies/deflektor/trap-filter-diagnostic.py', 'scripts/psid_audit.py',
                           'scripts/psid_profile.py', 'scripts/sid_audit_host.py', 'scripts/sid_clock.py',
                           'scripts/sid_intake.py', 'scripts/verify_player.py')},
                   listeningReview=None,
                   limits='Private source-data intervention and controlled callable execution. No original-host cadence, physical-chip equivalence, full-form, filter portability or musical-preference claim.')
    write_json(output / 'receipt.json', receipt)
    print(f"Verified {len(changed)} route-only changes across {len(original['writes'])} ordered stores")


def signal_delta(original, bypass, start, end):
    require((original.sample_rate, original.channels, original.frames) ==
            (bypass.sample_rate, bypass.channels, bypass.frames), 'Source render formats or duration differ')
    require(original.channels == 1, 'Trap diagnostic requires mono source renders')
    require(math.isfinite(start) and math.isfinite(end) and 0 <= start < end,
            'Choose a finite nonempty same-material window')
    first, last = round(start * original.sample_rate), round(end * original.sample_rate)
    require(0 <= first < last <= original.frames, 'Window escapes the source renders')
    left = original.samples[first * original.channels:last * original.channels]
    right = bypass.samples[first * bypass.channels:last * bypass.channels]
    differences = [candidate - reference for reference, candidate in zip(left, right)]
    count, total, squares = len(differences), sum(differences), sum(value * value for value in differences)
    variance_numerator = squares * count - total * total
    require(variance_numerator > 0, 'Selected passage has no nonzero AC difference')
    return dict(schemaVersion=1, startSeconds=start, endSeconds=end, frames=last - first,
                changedSamples=sum(value != 0 for value in differences), totalSamples=count,
                firstChangedFrame=first + next(index for index, value in enumerate(differences) if value) // original.channels,
                peakDelta=max(abs(value) for value in differences), rmsDelta=math.sqrt(squares / count),
                acRmsDelta=math.sqrt(variance_numerator / (count * count)),
                commonGain=1, normalization=False, listeningReview=None,
                limits='Nonzero contextual AC signal difference, not an audibility or musical-preference verdict.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    execute_command = commands.add_parser('execute')
    execute_command.add_argument('--source', type=Path, default=Path('.local/research/trap/Trap.sid'))
    execute_command.add_argument('--output', type=Path, required=True)
    signal_command = commands.add_parser('signal')
    signal_command.add_argument('original', type=Path)
    signal_command.add_argument('bypass', type=Path)
    signal_command.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / 'build'), 'Diagnostic output must remain below ignored build/')
    if args.command == 'execute':
        run_execution(args.source.resolve(), output)
    else:
        report = signal_delta(read_pcm16(args.original), read_pcm16(args.bypass), 16, 28)
        report.update(inputs=[dict(label=label, path=str(path.resolve()), sha256=sha(path.read_bytes()))
                              for label, path in (('original', args.original), ('bypass', args.bypass))])
        output.parent.mkdir(parents=True, exist_ok=True)
        write_json(output, report)
        print(f"16–28s AC difference: {report['acRmsDelta']:.3f} PCM16 units")


if __name__ == '__main__':
    main()
