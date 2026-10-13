"""Retain bounded loader command/stack consumption and an executed stop oracle."""

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid
from py65.disassembler import Disassembler

SID = ROOT / '.local/rambo-source.sid'
SID_SHA = '88a2b538ee3d3d1d8b0b754bef77a63d9750812694786977ae8c539f6ecd000e'
SOURCE = ROOT / '.tools/martin-galway-c64/rambload.asm'
SOURCE_SHA = '78e7927e6c2e8f7d42c18d2e02bec764a2911d2d8180cec789020bdd60cdbb75'
MAPPING_FOLDER = ROOT / 'build/rambo-form/mapping64-complete'
DB = (0x28d4, 0x291e, 0x2968)
SB = (0x29b2, 0x29d9, 0x2a00)
ROW_STORE = (0x216d, 0x2432, 0x26de)
NAMES = {0xc0:'return', 0xc2:'volume', 0xc4:'write-data', 0xc6:'frequency', 0xc8:'pulse',
         0xca:'call', 0xcc:'transpose', 0xce:'call-transposed', 0xd0:'poke-data', 0xd2:'jump-transposed',
         0xd4:'code', 0xd6:'poke-sound', 0xd8:'chord', 0xda:'loop', 0xdc:'next'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(path):
    path = path.resolve()
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def named_state(ram):
    return dict(activeMask=ram[0x19], mainTarget=ram[0x2001] | ram[0x2002] << 8,
                morse=dict(letterIndex=ram[0x2915], shiftedCode=ram[0x2916],
                           elementCounter=ram[0x2917], wait=ram[0x2918], phaseDisplacement=ram[0x310e]),
                voices=[dict(voice=v, stream=ram[0x10+v*2] | ram[0x11+v*2] << 8,
                             remaining=ram[0x1a+v], stackIndex=ram[0x1d+v], transpose=ram[DB[v]+73],
                             soundLife=ram[SB[v]+28], releaseCountdown=ram[SB[v]+27],
                             stack=[dict(returnStream=ram[DB[v]+49+i] | ram[DB[v]+57+i] << 8,
                                         repeatRemaining=ram[DB[v]+65+i]) for i in range(8)])
                        for v in range(3)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--calls', type=int, default=40000)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not 65 <= args.calls <= 40000 or output.exists() or not output.is_relative_to(ROOT/'build/rambo-form'):
        raise ValueError('Use 65..40000 calls and a fresh directory below build/rambo-form')
    data = SID.read_bytes()
    if sha(data) != SID_SHA or sha(SOURCE.read_bytes()) != SOURCE_SHA:
        raise ValueError('Pinned source changed')
    mapping_raw = (MAPPING_FOLDER/'mapping.json').read_bytes()
    mapping = json.loads(mapping_raw)
    verification = json.loads((MAPPING_FOLDER/'mapping-verification.json').read_text())
    if not verification['completeLedgerExact'] or verification['sourceSha256'] != SID_SHA:
        raise ValueError('Require the closed source-pinned opening map')
    baseline_path=ROOT/'build/rambo-intake/audit64.writes.json'
    baseline_raw=baseline_path.read_bytes()
    if sha(baseline_raw)!='25b08f2edc0f700cc0d29dc2ec6aebc8472324613b4199ad1ba6aa75ea6f5653':
        raise ValueError('Canonical opening ledger changed')
    baseline=json.loads(baseline_raw)
    if len(baseline)!=577 or {r['tick']for r in baseline if r['phase']=='play'}!=set(range(64)):
        raise ValueError('Canonical opening ledger has incomplete coverage')
    tool_pins = {name:fingerprint(ROOT/'scripts'/name) for name in
                 ('psid_audit.py','psid_profile.py','sid_audit_host.py','verify_player.py')}
    inputs = dict(source=fingerprint(SID), primarySource=fingerprint(SOURCE),
                  mapping=fingerprint(MAPPING_FOLDER/'mapping.json'),
                  mappingVerification=fingerprint(MAPPING_FOLDER/'mapping-verification.json'),
                  openingLedger=fingerprint(baseline_path),
                  executedProbe=fingerprint(Path(__file__)), tools=tool_pins)
    for filename in ('preflight.json','probe-executed.py','events.json.gz','writes.json.gz',
                     'static-command-instructions.json','status-changes.json','audit.json','form.json','receipt.json'):
        (output/filename).relative_to(ROOT)
    json.dumps(inputs)
    output.mkdir(parents=True)
    (output/'preflight.json').write_text(json.dumps(inputs,indent=2)+'\n')
    (output/'probe-executed.py').write_bytes(Path(__file__).read_bytes())
    events, controls, status_changes, top_returns, morse_returns = [], Counter(), [], [], []
    pending = [None]*3
    first_zero_test = None
    test_counts = Counter()
    last_status = None
    disassembler = None
    static = {}
    top_store = {}
    finish_target = mapping['refresh']

    def row(cpu, memory, kind, **extra):
        size, assembly = disassembler.instruction_at(cpu.pc)
        return dict(kind=kind, call=memory.tick, instructionStartCycle=memory.instruction_cycle,
                    pc=cpu.pc, bytes=bytes(memory.data[cpu.pc:cpu.pc+size]).hex(), assembly=assembly,
                    a=cpu.a,x=cpu.x,y=cpu.y,status=cpu.p,sp=cpu.sp,
                    state=named_state(memory.data),**extra)

    def initialize(cpu, memory):
        nonlocal disassembler
        disassembler = Disassembler(cpu)
        ram = memory.data
        for voice in mapping['voices']:
            v = voice['voice']
            for slot in voice['slots']:
                addr = voice['controlTable'] + slot['opcode'] - 0xc0
                actual = ram[addr] | ram[addr+1] << 8
                if actual != slot['target']:
                    raise ValueError('Control table changed after opening mapping')
                if actual < 0x2000:
                    continue
                count = 12 if slot['opcode'] in (0xc0,0xca,0xce,0xda,0xdc,0xd4) else 6
                listing=[]
                pc=actual
                for _ in range(count):
                    size, assembly = disassembler.instruction_at(pc)
                    listing.append(dict(pc=pc,bytes=bytes(ram[pc:pc+size]).hex(),assembly=assembly))
                    pc+=size
                static[f'{v}:{slot["opcode"]:02x}']=listing
            ret=voice['slots'][0]['target']
            if ram[ret:ret+7] != [0xe6,0x1d+v,0xa4,0x1d+v,0xc0,8,0xf0]:
                raise ValueError('Unexpected top-level return prefix')
            clear=ret+8+ram[ret+7]
            if ram[clear:clear+6] != [0xa5,0x19,0x29,255^(1<<v),0x85,0x19]:
                raise ValueError('Unexpected active-bit clear')
            top_store[v]=clear+4
        if ram[0x25fa:0x2606] != [0xa5,0x19,0x0d,0xce,0x29,0x0d,0xf5,0x29,0x0d,0x1c,0x2a,0x60]:
            raise ValueError('Unexpected music-complete test')

    def observe(cpu,memory):
        nonlocal first_zero_test,last_status
        if memory.phase!='play':
            return
        ram=memory.data
        if disassembler is None:
            initialize(cpu,memory)
        if memory.instruction_cycle==0:
            if memory.tick%1000==0:
                print(json.dumps(dict(progressCall=memory.tick,activeMask=ram[0x19],events=len(events))),flush=True)
            status=(ram[0x19],ram[0x2001]|ram[0x2002]<<8)
            if status!=last_status:
                status_changes.append(dict(call=memory.tick,state=named_state(ram)))
                last_status=status
        if cpu.pc==0x2605:
            test_counts['zero' if cpu.a==0 else 'nonzero']+=1
            if cpu.a==0 and first_zero_test is None:
                first_zero_test=memory.tick
                events.append(row(cpu,memory,'first-zero-music-test'))
        if cpu.pc==0x3100:
            morse_returns.append(row(cpu,memory,'morse-dispatch-return'))
            events.append(morse_returns[-1])
        for voice in mapping['voices']:
            v=voice['voice']
            if cpu.pc==voice['fetch']:
                ptr=ram[0x10+v*2]|ram[0x11+v*2]<<8
                opcode=ram[ptr]
                event=row(cpu,memory,'fetch',voice=v,stream=ptr,upcomingBytes=list(ram[ptr:ptr+4]))
                if opcode>=0xc0:
                    if opcode not in NAMES:
                        raise ValueError(f'Unverified score command ${opcode:02x}')
                    event['command']=NAMES[opcode]
                    controls[v,opcode]+=1
                else:
                    event['rowKind']='hold' if opcode in (95,191) else 'note'
                pending[v]=event
                events.append(event)
            elif cpu.pc==voice['dispatch']:
                target=ram[cpu.pc+1]|ram[cpu.pc+2]<<8
                event=pending[v]
                if event is None or event['upcomingBytes'][0]<0xc0:
                    raise ValueError('Control dispatch without a preceding command fetch')
                expected=next(s['target'] for s in voice['slots'] if s['opcode']==event['upcomingBytes'][0])
                if expected!=target:
                    raise ValueError('Selected command target disagrees with table')
                events.append(row(cpu,memory,'dispatch',voice=v,stream=event['stream'],command=event['command'],target=target))
            elif cpu.pc==ROW_STORE[v]:
                events.append(row(cpu,memory,'row-duration-store',voice=v,storedDuration=cpu.a,
                                  precedingFetchStream=pending[v]['stream'] if pending[v] else None))
            elif cpu.pc==top_store[v]:
                if ram[0x1d+v]!=8 or cpu.a!=ram[0x19]&~(1<<v):
                    raise ValueError('Top-level return invariant failed')
                event=row(cpu,memory,'top-level-return-clear',voice=v,newActiveMask=cpu.a)
                top_returns.append(event)
                events.append(event)

    try:
        report,writes=audit_psid(data,args.calls,subtune=1,profile='pal-banked',observer=observe)
    except ValueError as error:
        (output/'failure.json').write_text(json.dumps(dict(error=str(error),inputs=inputs,
                                         lastEvents=events[-12:],scope='Incomplete execution; no completed form or ordered-write equality claim.'),indent=2)+'\n')
        raise
    if SID.read_bytes()!=data:
        raise ValueError('Original changed')
    prefix=[r for r in writes if r['phase']=='init' or r['tick']<64]
    if prefix!=baseline:
        raise ValueError('Complete opening write prefix changed')
    terminal=next((r for r in events if r['kind']=='first-zero-music-test'),None)
    if report['playCalls']!=args.calls or sum(test_counts.values())!=args.calls:
        raise ValueError('Outer call/test coverage disagrees with requested cap')
    stopped=bool(terminal and terminal['state']['activeMask']==0 and
                 terminal['state']['mainTarget']==finish_target and
                 len(morse_returns)==1 and morse_returns[0]['call']<first_zero_test and
                 all(v['stackIndex']==8 and v['soundLife']==0 for v in terminal['state']['voices']) and
                 {r['voice'] for r in top_returns}=={0,1,2} and
                 args.calls-first_zero_test>=64 and
                 not any(r['phase']=='play' and r['tick']>=first_zero_test for r in writes))
    result=dict(schemaVersion=1,sourceUnchanged=True,requestedCap=args.calls,executedCalls=args.calls,
                firstZeroMusicTestCall=first_zero_test,completeStoppedLoader=stopped,
                confirmationCalls=args.calls-first_zero_test if first_zero_test is not None else 0,
                topLevelReturns=[dict(call=r['call'],voice=r['voice'],pc=r['pc'],newActiveMask=r['newActiveMask'])for r in top_returns],
                topLevelStarts=[dict(call=r['call'],voice=r['voice'],stream=r['stream'])for r in events
                                if r['kind']=='fetch' and r['stream']==mapping['voices'][r['voice']]['initialStream']
                                and r['state']['voices'][r['voice']]['stackIndex']==7],
                morseDispatchReturnCalls=[r['call']for r in morse_returns],musicTestCounts=dict(test_counts),
                commands=[dict(voice=v,opcode=op,command=NAMES[op],executions=n)for(v,op),n in sorted(controls.items())],
                matchedOpeningRecords=len(prefix),openingLedgerExact=True,
                lastPlayStoreCall=max((r['tick']for r in writes if r['phase']=='play'),default=None),
                limits='Executed command/row/stack form evidence. Stop requires all top-level returns, ordinary dispatcher, zero active/sound-life test and post-end no stores. No assumed PCM recurrence, VICE cadence, sound synthesis or musical/listening judgment.')
    artifacts={}
    for filename,value in [('events.json.gz',events),('writes.json.gz',writes),('static-command-instructions.json',static),
                           ('status-changes.json',status_changes),('audit.json',report),('form.json',result)]:
        path=output/filename
        raw=(json.dumps(value,separators=(',',':'))+'\n').encode()
        if filename.endswith('.gz'):
            with path.open('wb')as stream:
                with gzip.GzipFile(filename='',mode='wb',fileobj=stream,mtime=0)as compressed:
                    compressed.write(raw)
        else:
            path.write_bytes(raw)
        artifacts[filename]=dict(fingerprint(path),uncompressedBytes=len(raw),uncompressedSha256=sha(raw))
    (output/'receipt.json').write_text(json.dumps(dict(schemaVersion=1,inputs=inputs,artifacts=artifacts,
                                                     executionScope=result),indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
