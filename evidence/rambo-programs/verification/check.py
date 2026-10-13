"""Verify the pure helper in context and against bounded original-body interventions."""

import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from psid_audit import BankedAuditMemory
from psid_profile import psid_profile
from verify_player import cpu_type
from model import advance_voice,ARRAY_FIELDS
from probe import SB,ENTRY,decode_state,fingerprint,SOURCE_SHA

BODY_SHA='9548536988bdb4eca34024c505504e5b4cfbacb193ba30fec366b8f678a8276f'


def original(data,state,voice,row_remaining):
    profile=psid_profile(data,subtune=1,profile='pal-banked')
    ram=BankedAuditMemory((0xd400,))
    ram.data[0x2000:0x2000+len(profile['payload'])]=profile['payload']
    b=SB[voice]
    def byte(offset,value):ram.data[b+offset]=value
    def word(offset,value):byte(offset,value&255);byte(offset+1,value>>8)
    for key,offsets,writer in [('frequencySteps',(0,2,4,6),word),('frequencyDurations',(8,9,10,11),byte),
                              ('pulseDurations',(14,15),byte),('pulseSteps',(18,20),word),
                              ('frequencyRemaining',(31,32,33,34),byte),('pulseRemaining',(37,38),byte)]:
        for offset,value in zip(offsets,state[key]):writer(offset,value)
    for key,offset in [('frequencyDelay',12),('frequencyFlags',13),('pulseDelay',16),('pulseFlags',17),
                       ('control',26),('releaseCountdown',27),('life',28)]:byte(offset,state[key])
    for key,offset in [('pulseInitial',22),('frequency',29),('pulse',35)]:word(offset,state[key])
    ram.data[0x1a+voice]=row_remaining
    ram.phase='play';ram.tick=None
    cpu=cpu_type()(memory=ram,pc=ENTRY[voice]);cpu.p=cpu.UNUSED|cpu.INTERRUPT
    cpu.stPushWord(0x01ff)
    pcs=[]
    while cpu.pc!=0x0200:
        if cpu.processorCycles>=4096:raise ValueError('Isolated SOUND exceeded4096 cycles')
        ram.instruction=cpu.disassemble[ram[cpu.pc]][0]
        if ram.instruction in('???','BRK','RTI'):raise ValueError('Unsupported isolated instruction')
        ram.instruction_cycle=cpu.processorCycles
        pcs.append(cpu.pc);cpu.step()
    if cpu.sp!=255:raise ValueError('Isolated body stack did not return')
    return decode_state(ram.data,voice),[(w['address'],w['value'])for w in ram.writes],pcs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bodies',type=Path,default=ROOT/'build/rambo-programs/ending/bodies.json.gz')
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();output=args.output.resolve()
    if output.exists()or not output.is_relative_to(ROOT/'build/rambo-programs'):
        raise ValueError('Choose a fresh directory below build/rambo-programs')
    packed=args.bodies.read_bytes()
    if hashlib.sha256(packed).hexdigest()!=BODY_SHA:raise ValueError('Captured body proof changed')
    bodies=json.loads(gzip.decompress(packed));source=ROOT/'.local/rambo-source.sid';data=source.read_bytes()
    if hashlib.sha256(data).hexdigest()!=SOURCE_SHA:raise ValueError('Pinned original changed')
    inputs=dict(source=fingerprint(source),bodies=fingerprint(args.bodies),checker=fingerprint(Path(__file__)),
                model=fingerprint(Path(__file__).with_name('model.py')),
                tools={n:fingerprint(ROOT/'scripts'/n)['sha256']for n in('psid_audit.py','psid_profile.py','sid_audit_host.py','verify_player.py')})
    json.dumps(inputs);output.mkdir(parents=True)
    (output/'preflight.json').write_text(json.dumps(inputs,indent=2)+'\n')
    for filename in('check.py','model.py'):(output/filename).write_bytes(Path(__file__).with_name(filename).read_bytes())
    context=[];negative=0
    for r in bodies:
        before=deepcopy(r['before']);after,writes=advance_voice(before,voice=r['voice'],row_remaining=r['rowRemaining'])
        if before!=r['before']or after!=r['after']or writes!=[(w['address'],w['value'])for w in r['writes']]:
            raise ValueError(f'Context mismatch call{r["call"]},voice{r["voice"]}')
        context.append(dict(call=r['call'],voice=r['voice'],stateMatched=True,orderedWrites=len(writes)))
        if r['activeMask']==0 and writes:negative+=1
    seeds=[next(r for r in bodies if r['call']==10561 and r['voice']==v)for v in range(3)]
    cases=[]
    for v,seed in enumerate(seeds):
        candidates=[('control',deepcopy(seed['before']),seed['rowRemaining'])]
        for label,changes,row in [
            ('life-one',{'life':1},0),('life-zero',{'life':0},0),('pulse-disabled',{'pulseFlags':0},0),
            ('release-expiry',{'releaseCountdown':1},0),('row-controlled-release',{'control':0x49,'releaseCountdown':3},0),
            ('row-controlled-hold',{'control':0x49,'releaseCountdown':3},3),
            ('zero-control-fallthrough',{'control':9,'releaseCountdown':3},0),
            ('pulse-delay',{'pulseDelay':1},0),
            ('pulse-word-wrap',{'pulse':65535,'pulseRemaining':[1,0],'pulseSteps':[1,65535],'pulseFlags':1},0),
            ('pulse-counter-only-loop',{'pulseFlags':1,'pulseRemaining':[0,0]},0),
            ('pulse-full-reset',{'pulseFlags':0x80,'pulseRemaining':[0,0]},0),
            ('pulse-no-repeat',{'pulseFlags':4,'pulseRemaining':[0,0]},0),
            ('frequency-disabled',{'frequencyFlags':0},0),
            ('frequency-delay-hold',{'frequencyFlags':1,'frequencyDelay':1},0),
            ('frequency-delay-last-step',{'frequencyFlags':2,'frequencyDelay':1},0),
            ('frequency-word-wrap',{'frequency':0,'frequencySteps':[65535]*4,'frequencyRemaining':[1,0,0,0]},0),
            ('frequency-counter-reload',{'frequencyRemaining':[0,0,0,0]},0)]:
            state=deepcopy(seed['before']);state.update(changes);candidates.append((label,state,row))
        for label,state,row_remaining in candidates:
            predicted,predicted_writes=advance_voice(state,voice=v,row_remaining=row_remaining)
            actual,writes,pcs=original(data,state,v,row_remaining)
            if predicted!=actual or predicted_writes!=writes:raise ValueError(f'Isolated mismatch {label},voice{v}')
            cases.append(dict(label=label,voice=v,rowRemaining=row_remaining,before=state,after=actual,
                              orderedWrites=writes,executedPcs=pcs,stateMatched=True,writesMatched=True))
    tuple_state={k:tuple(v)if k in ARRAY_FIELDS else v for k,v in seeds[0]['before'].items()}
    if advance_voice(tuple_state,voice=0,row_remaining=0)!=advance_voice(seeds[0]['before'],voice=0,row_remaining=0):
        raise ValueError('Finite tuple input normalization disagrees')
    if source.read_bytes()!=data:raise ValueError('Original source changed')
    result=dict(schemaVersion=1,inputs=inputs,contextBodies=len(context),contextOrderedWrites=sum(r['orderedWrites']for r in context),
                isolatedCases=len(cases),allStatesAndOrderedWritesMatched=True,
                negativeControl=dict(model='Stop when score activeMask==0',mismatchingBodyInvocations=negative,detected=negative>0),
                supported='Binary lifetime/control flow; two additive PWM phases with delay/counter-only/full reload; sequential3/4-phase pitch with delay and last-step delay mode. No CPU flags or scheduler outputs.',
                untested='Arpeggio pitch on physical voices1/3 is rejected when reached; all-zero repeating durations are rejected as non-terminating. No waveform/note initializer, full-title component proof, synthesis or listening result.')
    artifacts={}
    for name,value in [('context.json',context),('isolated.json',cases)]:
        raw=(json.dumps(value,separators=(',',':'))+'\n').encode();path=output/(name+'.gz')
        with path.open('wb')as f:
            with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0)as g:g.write(raw)
        artifacts[name+'.gz']=dict(fingerprint(path),uncompressedSha256=hashlib.sha256(raw).hexdigest())
    result['artifacts']=artifacts;(output/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
