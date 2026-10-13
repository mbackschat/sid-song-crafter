"""Check decoded score-stack arithmetic against the frozen executed event ledger."""

import argparse
from collections import Counter
import copy
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
FOLDER=ROOT/'build/rambo-form/complete40000'
EVENT_SHA='90f773d62e968292fb0e3fbe3d325d639d1850628222fb0ec24d8958ea4e01f7'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--events',type=Path,default=FOLDER/'events.json.gz')
    parser.add_argument('--output',type=Path,default=ROOT/'build/rambo-form/transition-verification.json')
    args=parser.parse_args()
    output=args.output.resolve()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError('Verification output already exists')
    raw=args.events.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EVENT_SHA:
        raise ValueError('Executed event ledger changed')
    events=json.loads(gzip.decompress(raw))
    counts=Counter()
    pending=[None]*3
    for index,event in enumerate(events):
        if event['kind']=='fetch':
            pending[event['voice']]=event
        if event['kind']=='row-duration-store':
            original=pending[event['voice']]
            note,duration=original['upcomingBytes'][:2]
            if note>=96:
                expected=duration
                counts['literal-duration']+=1
            else:
                if not 0<=duration<=16:
                    raise ValueError('Unverified duration-table index')
                expected=duration*4
                counts['table-duration']+=1
            if event['storedDuration']!=expected:
                raise ValueError(f'Duration disagreement at call {event["call"]}')
        if event['kind']!='dispatch' or event['command']not in ('return','call','call-transposed','loop','next','transpose','jump-transposed'):
            continue
        v=event['voice']
        original=pending[v]
        voice=copy.deepcopy(event['state']['voices'][v])
        expected={name:voice[name]for name in ('stream','stackIndex','transpose','stack')}
        command=event['command']
        parameter=original['upcomingBytes']
        slot=expected['stackIndex']
        ptr=event['stream']
        if command in ('call','call-transposed','loop'):
            size=2 if command=='loop' else 4 if command=='call-transposed' else 3
            expected['stack'][slot]['returnStream']=(ptr+size)&65535
            if command=='loop':
                expected['stack'][slot]['repeatRemaining']=parameter[1]
                expected['stream']=(ptr+2)&65535
            else:
                expected['stream']=parameter[1]|parameter[2]<<8
                if command=='call-transposed':
                    expected['transpose']=parameter[3]
            expected['stackIndex']=(slot-1)&255
        elif command=='return':
            expected['stackIndex']=(slot+1)&255
            if expected['stackIndex']!=8:
                expected['stream']=expected['stack'][expected['stackIndex']]['returnStream']
        elif command=='next':
            remaining=(expected['stack'][slot+1]['repeatRemaining']-1)&255
            expected['stack'][slot+1]['repeatRemaining']=remaining
            if remaining:
                expected['stream']=expected['stack'][slot+1]['returnStream']
            else:
                expected['stackIndex']=(slot+1)&255
                expected['stream']=(ptr+1)&65535
        elif command=='transpose':
            expected['transpose']=parameter[1]
            expected['stream']=(ptr+2)&65535
        elif command=='jump-transposed':
            expected['transpose']=parameter[3]
            expected['stream']=parameter[1]|parameter[2]<<8
        following=next(r for r in events[index+1:] if r.get('voice')==v and r['kind']in('fetch','top-level-return-clear'))
        actual=following['state']['voices'][v]
        if command=='return' and expected['stackIndex']==8:
            if following['kind']!='top-level-return-clear' or actual['stackIndex']!=8 or following['newActiveMask']!=event['state']['activeMask']&~(1<<v):
                raise ValueError('Top-level return disagreement')
        elif {name:actual[name]for name in expected}!=expected:
            raise ValueError(f'{command} disagreement at call {event["call"]}, voice {v}')
        counts[command]+=1
    result=dict(schemaVersion=1,sourceEventSha256=EVENT_SHA,
                checkerSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                checked=dict(counts),allMatched=True,
                limits='Offline independent byte/word arithmetic against every selected executed stack transition and duration store; no independently scheduled score, instrument model, synthetic edge proof or new source execution.')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x')as stream:
        stream.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
