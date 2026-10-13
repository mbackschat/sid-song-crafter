"""Compute the verified SOUND lifetime, two-stage PWM and sequential-pitch paths."""

from copy import deepcopy

BYTE_FIELDS=('frequencyDelay','frequencyFlags','pulseDelay','pulseFlags','control','releaseCountdown','life')
WORD_FIELDS=('pulseInitial','frequency','pulse')
ARRAY_FIELDS={'frequencySteps':(4,65535),'frequencyDurations':(4,255),'pulseDurations':(2,255),
              'pulseSteps':(2,65535),'frequencyRemaining':(4,255),'pulseRemaining':(2,255)}


def validated(state,voice,row_remaining):
    if type(voice)is not int or not 0<=voice<=2 or type(row_remaining)is not int or not 0<=row_remaining<=255:
        raise ValueError('Voice and row remaining must be finite decoded integers')
    if not isinstance(state,dict)or set(state)!=(set(BYTE_FIELDS+WORD_FIELDS)|set(ARRAY_FIELDS)):
        raise ValueError('Expected the named SOUND state fields')
    for key in BYTE_FIELDS+WORD_FIELDS:
        limit=255 if key in BYTE_FIELDS else 65535
        if type(state[key])is not int or not 0<=state[key]<=limit:
            raise ValueError(f'Invalid {key}')
    for key,(length,limit)in ARRAY_FIELDS.items():
        if not isinstance(state[key],(list,tuple))or len(state[key])!=length or any(type(x)is not int or not 0<=x<=limit for x in state[key]):
            raise ValueError(f'Invalid {key}')
    result=deepcopy(state)
    for key in ARRAY_FIELDS:
        result[key]=list(result[key])
    return result


def advance_lifetime(state,row_remaining,base):
    """Advance lifetime before programs; return false when SOUND returns early."""
    writes=[]
    if not state['life']:
        return writes,False
    if state['control']&8:
        if row_remaining>=state['releaseCountdown']:
            return writes,True
        state['releaseCountdown']=0
        state['control']&=0xf6
        if state['control']:
            return [(base+4,state['control'])],True
    if state['releaseCountdown']:
        state['releaseCountdown']-=1
        if not state['releaseCountdown']:
            writes.append((base+4,state['control']&0xf6))
        return writes,True
    state['life']-=1
    if not state['life']:
        return [(base+offset,0)for offset in range(6,-1,-1)],False
    return writes,True


def advance_pwm(state,base):
    """Advance two additive phases; bit7 reloads width, bit0 reloads counters."""
    if not state['pulseFlags']:
        return []
    if state['pulseDelay']:
        state['pulseDelay']-=1
        return []
    remaining=state['pulseRemaining']
    if not any(remaining)and state['pulseFlags']&0x81:
        remaining[:]=state['pulseDurations']
        if state['pulseFlags']&0x80:
            state['pulse']=state['pulseInitial']
        if not any(remaining):
            raise ValueError('Non-terminating zero-duration PWM loop is unsupported')
    phase=next((i for i,n in enumerate(remaining)if n),None)
    if phase is not None:
        remaining[phase]-=1
        state['pulse']=(state['pulse']+state['pulseSteps'][phase])&65535
    return [(base+2,state['pulse']&255),(base+3,state['pulse']>>8)]


def advance_frequency(state,voice,base):
    """Advance the four-phase path, or the physical second voice's three phases."""
    if not state['frequencyFlags']:
        return []
    if voice!=1 and state['frequencyFlags']&8:
        raise ValueError('Arpeggio frequency mode is outside this verified component')
    if state['frequencyDelay']:
        state['frequencyDelay']-=1
        if not state['frequencyFlags']&2:
            return []
        phase=3
    else:
        length=3 if voice==1 else 4
        if not any(state['frequencyRemaining'][:length]):
            state['frequencyRemaining'][:]=state['frequencyDurations']
        phase=next((i for i,n in enumerate(state['frequencyRemaining'][:length])if n),None)
        if phase is None:
            raise ValueError('Non-terminating zero-duration frequency loop is unsupported')
        state['frequencyRemaining'][phase]-=1
    state['frequency']=(state['frequency']+state['frequencySteps'][phase])&65535
    return [(base,state['frequency']&255),(base+1,state['frequency']>>8)]


def advance_voice(state,*,voice,row_remaining):
    """Compute one binary-mode SOUND invocation without source or score replay.

    The controlled PAL host clears decimal mode. Arpeggio pitch paths on the
    first/third physical voices remain unsupported; CPU flags are not outputs.
    """
    state=validated(state,voice,row_remaining)
    base=0xd400+voice*7
    writes,alive=advance_lifetime(state,row_remaining,base)
    if alive:
        writes+=advance_pwm(state,base)
        writes+=advance_frequency(state,voice,base)
    return state,writes
