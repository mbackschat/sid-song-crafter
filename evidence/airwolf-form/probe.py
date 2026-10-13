"""Verify complete Airwolf score traversals and an independent numeric model."""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid
from model import compute

SOURCE_SHA = '03c602da9182759c78ca4d90ad3bd5b223b3eb61f34ea31c2205fffc589bf89f'
PINS = {
    'psid_audit.py': '4446a19a325e625e59f100aac0b186478fb1633f65886b260db2ad3da11419a5',
    'psid_profile.py': 'edc1109d1b393541a1df1c8d678923faab1d5240996c2eaee63db8691e9ea0ff',
    'sid_audit_host.py': 'ea1949d711126b5150225f0d68a3462dbbfe9fffe094e448f9b758889808b0ed',
    'verify_player.py': 'c69317c5d781c175ef0cef39a6e2713187b17e1de5b3f144ad69d49e6a271aab',
}
READS = {0x3b1b:'duration', 0x3b37:'voice0High', 0x3b55:'voice0Low',
         0x3b62:'voice1High', 0x3b80:'voice1Low', 0x3b87:'voice2High', 0x3bae:'voice2Low'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError('Choose a fresh output directory')
    source = ROOT / '.local/research/airwolf/Airwolf.sid'
    raw = source.read_bytes()
    assert sha(raw) == SOURCE_SHA
    assert len(raw) == 1280 and raw[124:126] == b'\xdd\x3a'
    for name, digest in PINS.items():
        assert sha((ROOT / 'scripts' / name).read_bytes()) == digest, name
    memory = [0] * 65536
    memory[0x3add:0x3f5f] = raw[126:]
    assert memory[0x3bd0] == 3
    address, rows = 0x3c00, []
    while memory[address] != 0:
        start, duration = address, memory[address]
        address += 1
        notes = []
        for voice in range(3):
            high = memory[address]
            address += 1
            if high:
                notes.append(high * 256 + memory[address])
                address += 1
            else:
                notes.append(None)
        rows.append(dict(sourceAddress=start, duration=duration, notes=notes))
        assert address < 0x3f5f
    score = dict(schemaVersion=1, sourceSha256=SOURCE_SHA, rows=rows, terminatorAddress=address,
                 limits='Exact selected three-voice data grammar; addresses label provenance, not runtime RAM.')
    cycle = sum(row['duration'] + 1 for row in rows)
    calls = 2 * cycle + 16
    predicted = compute(score, calls)
    reads, restarts, states = [], [], []

    def observe(cpu, mem):
        ram = mem.data
        if cpu.pc in READS:
            assert ram[cpu.pc:cpu.pc+2] == [0xb1, 0x1f]
            source_address = ((ram[0x1f] | ram[0x20] << 8) + cpu.y) & 65535
            reads.append(dict(phase=mem.phase, tick=mem.tick, address=source_address,
                              value=ram[source_address], field=READS[cpu.pc]))
        if mem.phase == 'play' and cpu.pc == 0x3b25:
            assert cpu.a == 0 and reads[-1]['field'] == 'duration' and reads[-1]['value'] == 0
            restarts.append(mem.tick)
        if cpu.pc == 0x3bc6:
            expected_return = 0xc039 if mem.phase == 'init' else 0xc04c
            assert cpu.sp == 253 and (ram[0x1fe] | ram[0x1ff] << 8) == expected_return
            snapshot = bytes(ram) + bytes([cpu.a, cpu.x, cpu.y, cpu.sp, cpu.p]) + cpu.pc.to_bytes(2, 'little')
            states.append(dict(phase=mem.phase, tick=mem.tick, ramSha256=sha(bytes(ram)),
                               machineSha256=sha(snapshot), rowPointer=ram[0x3bcd] | ram[0x3bce] << 8,
                               countdown=ram[0x3bcf], cpu=dict(a=cpu.a,x=cpu.x,y=cpu.y,sp=cpu.sp,p=cpu.p,pc=cpu.pc)))

    audit, writes = audit_psid(raw, calls, profile='pal-banked', subtune=1, observer=observe)
    projected = [{key:row[key] for key in ('phase','tick','address','value')} for row in writes]
    assert predicted['writes'] == projected
    assert predicted['reads'] == reads
    assert predicted['restartCalls'] == restarts == [cycle - 1, 2 * cycle - 1]
    assert len(states) == calls + 1
    baseline = json.loads(gzip.decompress((ROOT / 'evidence/pop-theme-intake/airwolf.audit64.writes.json.gz').read_bytes()))
    assert [row for row in writes if row['phase'] == 'init' or row['tick'] < 64] == baseline
    changed = copy.deepcopy(score)
    changed['rows'][0]['notes'][0] += 1
    assert compute(changed, calls)['writes'] != projected
    args.output.mkdir(parents=True)
    results = dict(score=score, audit=audit, reads=reads, states=states, writes=writes)
    artifacts = {}
    for name, value in results.items():
        logical = (json.dumps(value, separators=(',', ':')) + '\n').encode()
        compressed = name in ('reads','states','writes')
        stored = gzip.compress(logical, mtime=0) if compressed else logical
        filename = name + '.json' + ('.gz' if compressed else '')
        (args.output / filename).write_bytes(stored)
        artifacts[filename] = dict(sha256=sha(stored), bytes=len(stored), decodedSha256=sha(logical), decodedBytes=len(logical))
    first, second = [next(state for state in states if state['phase']=='play' and state['tick']==call) for call in restarts]
    receipt = dict(schemaVersion=1, sourceSha256=SOURCE_SHA,
        sourceUrl='https://www.hvsc.de/download/C64Music/MUSICIANS/C/Cooksey_Mark/Airwolf.sid',
        tools=PINS, probeSha256=sha(Path(__file__).read_bytes()), modelSha256=sha(Path(__file__).with_name('model.py').read_bytes()),
        calls=calls, scoreRows=len(rows), cycleCalls=cycle, restartCalls=restarts,
        matchedWrites=len(writes), matchedReads=len(reads), matchedOpeningWrites=len(baseline),
        noteMutationRejected=True, restartMachineStatesEqual=first['machineSha256']==second['machineSha256'],
        artifacts=artifacts,
        hashRecipe='SHA256(all65536RAMbytes+A/X/Y/SP/P+little-endianPC) immediately before validated callable RTS; absolute CPU cycles excluded; no physical SID/CIA/VIC state.',
        limits='Independent score/read/store computation under the fixed three-voice callable host, not synthesis, compiled reconstruction, original-game cadence, exact bus timing or listening. Instruction-start cycles retained only in source ledger; model comparison excludes cycles. No original executable payload or full RAM dump is retained.')
    (args.output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({key:receipt[key] for key in ('calls','scoreRows','cycleCalls','restartCalls','matchedWrites','matchedReads','restartMachineStatesEqual')}))


if __name__ == '__main__':
    main()
