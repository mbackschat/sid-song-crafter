"""Observe pinned loader score dispatch before choosing a whole-form oracle."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid
from psid_profile import psid_profile
from py65.disassembler import Disassembler

SID = ROOT / '.local/rambo-source.sid'
SID_SHA = '88a2b538ee3d3d1d8b0b754bef77a63d9750812694786977ae8c539f6ecd000e'
SOURCE = ROOT / '.tools/martin-galway-c64/rambload.asm'
SOURCE_SHA = '78e7927e6c2e8f7d42c18d2e02bec764a2911d2d8180cec789020bdd60cdbb75'
PRIMARY_REVISION = 'a458a3687e27a63647bbe41968094f0e6d0965a0'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(path):
    path = path.resolve()
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def state(ram):
    return dict(activeMask=ram[0x19], mainTarget=ram[0x2001] | ram[0x2002] << 8,
                voices=[dict(voice=voice, stream=ram[0x10 + voice * 2] | ram[0x11 + voice * 2] << 8,
                             remaining=ram[0x1a + voice], stackIndex=ram[0x1d + voice]) for voice in range(3)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--calls', type=int, default=64)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output = args.output.resolve()
    if not 1 <= args.calls <= 512 or args.output.exists() or not args.output.is_relative_to(ROOT / 'build/rambo-form'):
        raise ValueError('Use 1..512 calls and a fresh output directory')
    data = SID.read_bytes()
    if sha(data) != SID_SHA or sha(SOURCE.read_bytes()) != SOURCE_SHA:
        raise ValueError('Pinned SID or primary source changed')
    profile = psid_profile(data, subtune=1, profile='pal-banked')
    mapping, selected, dispatches, call_states = {}, [], [], []
    visits = Counter()
    details = {0, 1, 49, 50, 51, 63}
    disassembler = None

    def instruction(cpu, memory):
        size, assembly = disassembler.instruction_at(cpu.pc)
        return dict(call=memory.tick, instructionStartCycle=memory.instruction_cycle, pc=cpu.pc,
                    bytes=bytes(memory.data[cpu.pc:cpu.pc + size]).hex(), assembly=assembly,
                    a=cpu.a, x=cpu.x, y=cpu.y, status=cpu.p, sp=cpu.sp)

    def listing(cpu, ram, begin, count):
        original = cpu.pc
        records = []
        try:
            cursor = begin
            for _ in range(count):
                size, assembly = disassembler.instruction_at(cursor)
                records.append(dict(pc=cursor, bytes=bytes(ram[cursor:cursor + size]).hex(), assembly=assembly))
                cursor += size
        finally:
            assert cpu.pc == original
        return records

    def discover(cpu, memory):
        ram = memory.data
        refresh = ram[0x2001] | ram[0x2002] << 8
        if [ram[refresh + offset] for offset in (0, 3, 6)] != [0x20, 0x20, 0x4c]:
            raise ValueError('Unexpected refresh dispatcher')
        mapping.update(refresh=refresh, refreshInstructions=listing(cpu, ram, refresh, 3), voices=[])
        for voice in range(3):
            entry = ram[refresh + 1 + voice * 3] | ram[refresh + 2 + voice * 3] << 8
            zero_page = 0x10 + voice * 2
            prefix = bytes(ram[entry:entry + 128])
            relative = prefix.find(bytes((0xa0, 0, 0xb1, zero_page, 0xc9, 0xc0)))
            if relative < 0:
                raise ValueError(f'No source-like score fetch for voice {voice}')
            read = entry + relative
            instructions = listing(cpu, ram, read, 18)
            lookup = next(row for row in instructions if row['bytes'].startswith('bd'))
            table = int.from_bytes(bytes.fromhex(lookup['bytes'])[1:], 'little')
            jump = next(row for row in instructions if row['bytes'].startswith('4c'))['pc']
            mapping['voices'].append(dict(voice=voice, entry=entry, read=read, fetch=read + 2,
                                           dispatch=jump, controlTable=table,
                                           slots=[dict(opcode=0xc0 + index * 2,
                                                       target=ram[table + index * 2] | ram[table + index * 2 + 1] << 8)
                                                  for index in range(15)],
                                           initialStream=ram[zero_page] | ram[zero_page + 1] << 8,
                                           entryInstructions=listing(cpu, ram, entry, 9),
                                           readInstructions=instructions))

    def observe(cpu, memory):
        nonlocal disassembler
        if memory.phase != 'play':
            return
        if disassembler is None:
            disassembler = Disassembler(cpu)
            discover(cpu, memory)
        visits[cpu.pc] += 1
        if memory.instruction_cycle == 0:
            call_states.append(dict(call=memory.tick, **state(memory.data)))
        if memory.tick in details:
            selected.append(instruction(cpu, memory))
        for voice in mapping['voices']:
            if cpu.pc == voice['fetch']:
                ram = memory.data
                pointer = ram[0x10 + voice['voice'] * 2] | ram[0x11 + voice['voice'] * 2] << 8
                dispatches.append(dict(kind='fetch', voice=voice['voice'], stream=pointer,
                                       upcomingBytes=list(ram[pointer:pointer + 4]),
                                       state=state(ram), **instruction(cpu, memory)))
            elif cpu.pc == voice['dispatch']:
                ram = memory.data
                target = ram[cpu.pc + 1] | ram[cpu.pc + 2] << 8
                dispatches.append(dict(kind='control-dispatch', voice=voice['voice'], target=target,
                                       state=state(ram), **instruction(cpu, memory)))

    report, writes = audit_psid(data, args.calls, subtune=1, profile='pal-banked', observer=observe)
    if SID.read_bytes() != data:
        raise ValueError('Original SID changed')
    args.output.mkdir(parents=True)
    artifacts = {}
    for name, value in [('mapping.json', mapping), ('selected-instructions.json', selected),
                        ('dispatches.json', dispatches), ('call-states.json', call_states),
                        ('visits.json', [dict(pc=pc, visits=count) for pc, count in sorted(visits.items())]),
                        ('audit.json', report), ('writes.json', writes)]:
        path = args.output / name
        path.write_text(json.dumps(value, indent=2) + '\n')
        artifacts[name] = fingerprint(path)
    receipt = dict(schemaVersion=1, source=fingerprint(SID), primarySource=fingerprint(SOURCE),
                   primaryRevision=PRIMARY_REVISION, profile='pal-banked', selectedSubtune=1,
                   probe=fingerprint(Path(__file__)), sourceUnchanged=True,
                   tools={name: fingerprint(ROOT / 'scripts' / name)['sha256'] for name in
                          ('psid_audit.py', 'psid_profile.py', 'sid_audit_host.py', 'verify_player.py')},
                   artifacts=artifacts, calls=args.calls,
                   limits='Bounded score-dispatch mapping only. Selected executed instructions and named state; no full RAM, relocation-copy values, payload, sound model, measured dispatch cadence or complete-form claim.')
    (args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(mapping=mapping, fetches=sum(row['kind'] == 'fetch' for row in dispatches),
                          controlDispatches=sum(row['kind'] == 'control-dispatch' for row in dispatches),
                          playCalls=args.calls, maximumPlayCycles=report['maximumPlayCycles'],
                          initWrites=report['initWriteCount'], playWrites=report['playWriteCount']), indent=2))


if __name__ == '__main__':
    main()
