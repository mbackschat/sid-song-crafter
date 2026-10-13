"""Capture initialized ending-window inputs and outputs of the three SOUND routines."""

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from psid_audit import audit_psid
from py65.disassembler import Disassembler

SOURCE_SHA='88a2b538ee3d3d1d8b0b754bef77a63d9750812694786977ae8c539f6ecd000e'
PRIMARY_SHA='78e7927e6c2e8f7d42c18d2e02bec764a2911d2d8180cec789020bdd60cdbb75'
SB=(0x29b2,0x29d9,0x2a00)
ENTRY=(0x2231,0x24e0,0x2799)


def fingerprint(path):
    path=path.resolve(); raw=path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def decode_state(ram,v):
    b=SB[v]
    word=lambda offset:ram[b+offset]|ram[b+offset+1]<<8
    return dict(frequencySteps=[word(i)for i in (0,2,4,6)],
                frequencyDurations=[ram[b+i]for i in (8,9,10,11)],frequencyDelay=ram[b+12],frequencyFlags=ram[b+13],
                pulseDurations=[ram[b+i]for i in (14,15)],pulseDelay=ram[b+16],pulseFlags=ram[b+17],
                pulseSteps=[word(i)for i in (18,20)],pulseInitial=word(22),
                control=ram[b+26],releaseCountdown=ram[b+27],life=ram[b+28],frequency=word(29),
                frequencyRemaining=[ram[b+i]for i in (31,32,33,34)],pulse=word(35),
                pulseRemaining=[ram[b+i]for i in (37,38)])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--first',type=int,default=10540);p.add_argument('--last',type=int,default=10816)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    output=args.output.resolve()
    if not 0<=args.first<=args.last<20000 or args.last-args.first>=512 or output.exists()or not output.is_relative_to(ROOT/'build/rambo-programs'):
        raise ValueError('Choose a fresh owned directory and an inclusive window of at most512 calls')
    sid=ROOT/'.local/rambo-source.sid';data=sid.read_bytes()
    primary=ROOT/'.tools/martin-galway-c64/rambload.asm'
    canonical=ROOT/'evidence/rambo-form/complete40000/writes.json.gz'
    if hashlib.sha256(data).hexdigest()!=SOURCE_SHA or fingerprint(primary)['sha256']!=PRIMARY_SHA:
        raise ValueError('Pinned source changed')
    if fingerprint(canonical)['sha256']!='f9ef28f1a5a2b274236a3bc5513be1bfafdd897fbd6b600e0c705b12461a2c64':
        raise ValueError('Canonical complete write ledger changed')
    expected=[r for r in json.loads(gzip.decompress(canonical.read_bytes()))if r['phase']=='init'or r['tick']<=args.last]
    inputs=dict(source=fingerprint(sid),primarySource=fingerprint(primary),canonical=fingerprint(canonical),
                probe=fingerprint(Path(__file__)),tools={n:fingerprint(ROOT/'scripts'/n)['sha256']for n in
                  ('psid_audit.py','psid_profile.py','sid_audit_host.py','verify_player.py')})
    for name in ('preflight.json','probe-executed.py','bodies.json.gz','instructions.json.gz','writes.json.gz','audit.json','receipt.json'):
        (output/name).relative_to(ROOT)
    json.dumps(inputs);output.mkdir(parents=True)
    (output/'preflight.json').write_text(json.dumps(inputs,indent=2)+'\n')
    (output/'probe-executed.py').write_bytes(Path(__file__).read_bytes())
    bodies,instructions=[],[];pending={};counts=Counter();visits=Counter();disassembler=None

    def observe(cpu,memory):
        nonlocal disassembler
        if memory.phase!='play'or not args.first<=memory.tick<=args.last:return
        if disassembler is None:disassembler=Disassembler(cpu)
        if cpu.pc in ENTRY:
            v=ENTRY.index(cpu.pc)
            if v in pending:raise ValueError('Overlapping SOUND invocation')
            s=decode_state(memory.data,v); counts[v]+=1
            pending[v]=dict(call=memory.tick,voice=v,entryPc=cpu.pc,entryCycle=memory.instruction_cycle,
                            activeMask=memory.data[0x19],rowRemaining=memory.data[0x1a+v],before=s,
                            stackPointer=cpu.sp,writeStart=len(memory.writes),
                            detail=counts[v]<=4 or s['life']<=2 or not any(s['pulseRemaining']))
        for v,body in list(pending.items()):
            visits[v,cpu.pc]+=1
            if body['detail']:
                size,assembly=disassembler.instruction_at(cpu.pc)
                instructions.append(dict(call=memory.tick,voice=v,pc=cpu.pc,
                                          instructionStartCycle=memory.instruction_cycle,
                                          bytes=bytes(memory.data[cpu.pc:cpu.pc+size]).hex(),assembly=assembly,
                                          a=cpu.a,x=cpu.x,y=cpu.y,status=cpu.p,sp=cpu.sp))
            if memory.instruction=='RTS'and cpu.sp==body['stackPointer']:
                body.update(returnPc=cpu.pc,returnCycle=memory.instruction_cycle,after=decode_state(memory.data,v),
                            writes=[dict(address=r['address'],value=r['value'],instructionStartCycle=r['instructionStartCycle'])
                                    for r in memory.writes[body['writeStart']:]])
                del body['writeStart'];del body['stackPointer'];del body['detail']
                bodies.append(body);del pending[v]

    report,writes=audit_psid(data,args.last+1,subtune=1,profile='pal-banked',observer=observe)
    if pending or writes!=expected or sid.read_bytes()!=data:
        raise ValueError('Pending body, changed full prefix or source mutation')
    selected=[r for r in writes if r['phase']=='play'and args.first<=r['tick']<=args.last]
    artifacts={}
    for name,value in [('bodies.json.gz',bodies),('instructions.json.gz',instructions),('writes.json.gz',selected),
                       ('audit.json',report),('visits.json',[dict(voice=v,pc=pc,visits=n)for(v,pc),n in sorted(visits.items())])]:
        raw=(json.dumps(value,separators=(',',':'))+'\n').encode();path=output/name
        if name.endswith('.gz'):
            with path.open('wb')as stream:
                with gzip.GzipFile(filename='',mode='wb',fileobj=stream,mtime=0)as packed:packed.write(raw)
        else:path.write_bytes(raw)
        artifacts[name]=dict(fingerprint(path),uncompressedSha256=hashlib.sha256(raw).hexdigest(),uncompressedBytes=len(raw))
    result=dict(schemaVersion=1,inputs=inputs,artifacts=artifacts,firstCall=args.first,lastCall=args.last,
                matchedCompletePrefixRecords=len(writes),capturedBodies=len(bodies),perVoiceBodies=dict(counts),
                selectedWrites=len(selected),sourceUnchanged=True,
                limits=(f'Initialization and calls 0..{args.last} were executed normally; detailed SOUND capture is confined to calls {args.first}..{args.last}. '
                        'No 40000-call rerun, RAM/payload dump, independent scheduler, synthesis or audible-tail judgment.'))
    (output/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
