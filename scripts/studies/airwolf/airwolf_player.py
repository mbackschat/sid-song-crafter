"""Compute editable Airwolf rows and fixed patches without source code or replay."""

from copy import deepcopy


NATIVE_SOUND = dict(volume=15, pulseHigh=[40, 10], voices=[
    dict(attackDecay=10, sustainRelease=0, control=65),
    dict(attackDecay=10, sustainRelease=0, control=65),
    dict(attackDecay=9, sustainRelease=0, control=17)])
TARGET = dict(clock='pal', sidModel='MOS6581', sidBase=0xd400, frameCycles=19656)


def unsigned(value, maximum, name, minimum=0):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'{name} must be an integer in {minimum}..{maximum}')
    return value


def from_score(score, *, calls=2500):
    return dict(schema='airwolf-composition-v1', target=deepcopy(TARGET), range=dict(auditCalls=calls),
        rows=[{key: deepcopy(value) for key, value in row.items() if key in ('duration', 'notes', 'sourceAddress')}
            for row in score['rows']], sound=deepcopy(NATIVE_SOUND),
        sourceEvidence={key: score[field] for key, field in
            (('sha256', 'sourceSha256'), ('terminatorAddress', 'terminatorAddress')) if field in score})


def validate(composition):
    if composition.get('schema') != 'airwolf-composition-v1':
        raise ValueError('Expected airwolf-composition-v1')
    unknown = set(composition) - {'schema', 'target', 'range', 'rows', 'sound', 'ending',
        'title', 'author', 'released', 'sourceEvidence'}
    if unknown:
        raise ValueError(f'Unknown composition fields: {sorted(unknown)}')
    if composition['target'] != TARGET:
        raise ValueError('Airwolf requires one PAL MOS6581 at $D400 with 19656 cycles per call')
    if set(composition['range']) != {'auditCalls'}:
        raise ValueError('Range requires auditCalls')
    declared = unsigned(composition['range']['auditCalls'], 65535, 'auditCalls', 1)
    rows = composition['rows']
    if not isinstance(rows, list) or not 1 <= len(rows) <= 255:
        raise ValueError('Choose 1..255 rows')
    for row in rows:
        if set(row) - {'duration', 'notes', 'sourceAddress', 'sourceEvidence'}:
            raise ValueError('Unknown row fields')
        unsigned(row['duration'], 255, 'Duration', 1)
        if not isinstance(row['notes'], list) or len(row['notes']) != 3:
            raise ValueError('Each row requires three pitch/hold/off entries')
        for note in row['notes']:
            if note is not None and note != 'off':
                unsigned(note, 65535, 'Frequency word', 256)
    sound = composition['sound']
    if set(sound) != {'volume', 'pulseHigh', 'voices'} or len(sound['voices']) != 3 or len(sound['pulseHigh']) != 2:
        raise ValueError('Sound requires three patches, two raw pulse-high bytes and volume')
    unsigned(sound['volume'], 15, 'Volume')
    for value in sound['pulseHigh']:
        unsigned(value, 255, 'Raw pulse-high byte')
    for patch in sound['voices']:
        if set(patch) != {'attackDecay', 'sustainRelease', 'control'}:
            raise ValueError('Patch requires attackDecay, sustainRelease and control')
        unsigned(patch['attackDecay'], 255, 'Attack/decay')
        unsigned(patch['sustainRelease'], 255, 'Sustain/release')
        if type(patch['control']) is not int or patch['control'] not in (17, 33, 65, 129):
            raise ValueError('Control requires a single waveform plus GATE; no TEST, sync or ring')
    ending = composition.get('ending')
    if ending is not None:
        if not isinstance(ending, dict) or set(ending) != {'startCall', 'releaseCalls'}:
            raise ValueError('Ending requires startCall and releaseCalls')
        start = unsigned(ending['startCall'], 65535, 'Ending start', 1)
        release = unsigned(ending['releaseCalls'], 65535, 'Release calls', 1)
        if declared < start + release + 65:
            raise ValueError('Range must include 64 calls after the final stop')
    return declared


def compute(composition, *, calls=None):
    """Emit native init/update order and named state, plus an optional authored tail.

    The source $3B02/$3B08 decrement/CMP establishes duration+1 and accepts high
    duration bytes. $3B25 resets score state then jumps into the same updater;
    the terminal zero therefore repeats fixed stores within one host call.
    SID shadows describe emitted ports, not oscillator/envelope/filter state.
    Unwritten pulse lows and filter registers retain caller/reset state.
    """
    declared = validate(composition)
    calls = declared if calls is None else unsigned(calls, declared, 'Diagnostic calls')
    rows, sound = composition['rows'], composition['sound']
    state = dict(tick=None, nextRow=0, countdown=0,
        voices=[dict(frequency=0, control=0, attackDecay=0, sustainRelease=0) for _ in range(3)],
        pulseHigh=[0, 0], volume=0)
    ending = composition.get('ending')
    if ending:
        state['ending'] = dict(phase=0, nextCall=0)
    writes, reads, returns, restarts = [], [], [], []
    phase, tick = 'init', None

    def emit(address, value):
        writes.append(dict(phase=phase, tick=tick, address=address, value=value))
        if address == 0xd418:
            state['volume'] = value
        elif address in (0xd403, 0xd40a):
            state['pulseHigh'][(address - 0xd403) // 7] = value
        else:
            voice, register = divmod(address - 0xd400, 7)
            named = state['voices'][voice]
            if register == 0:
                named['frequency'] = (named['frequency'] & 65280) | value
            elif register == 1:
                named['frequency'] = (named['frequency'] & 255) | value << 8
            elif register == 4:
                named['control'] = value
            elif register == 5:
                named['attackDecay'] = value
            elif register == 6:
                named['sustainRelease'] = value

    def fixed():
        for address, value in ((0xd418, sound['volume']), (0xd403, sound['pulseHigh'][0]), (0xd40a, sound['pulseHigh'][1])):
            emit(address, value)

    def read(address, value, field):
        reads.append(dict(phase=phase, tick=tick, address=address, value=value, field=field))

    def consume(index):
        row = rows[index]
        address = row.get('sourceAddress', 0)
        read(address, row['duration'], 'duration')
        address += 1
        for voice, note in enumerate(row['notes']):
            read(address, 0 if note is None else 'off' if note == 'off' else note >> 8, f'voice{voice}High')
            address += 1
            base = 0xd400 + voice * 7
            if note is None:
                continue
            if note == 'off':
                emit(base + 4, state['voices'][voice]['control'] & 254)
                continue
            read(address, note & 255, f'voice{voice}Low')
            address += 1
            patch = sound['voices'][voice]
            for register, value in ((5, patch['attackDecay']), (6, patch['sustainRelease']),
                (4, 0), (4, patch['control']), (1, note >> 8), (0, note & 255)):
                emit(base + register, value)
        state['countdown'], state['nextRow'] = row['duration'], index + 1

    fixed()
    consume(0)
    initial = deepcopy(state)
    for tick in range(calls):
        phase, state['tick'] = 'play', tick
        if ending and tick >= ending['startCall']:
            stop = ending['startCall'] + ending['releaseCalls']
            if tick == ending['startCall']:
                state['ending']['phase'] = 1
                for voice in range(3):
                    emit(0xd404 + voice * 7, state['voices'][voice]['control'] & 254)
            elif tick == stop:
                state['ending']['phase'] = 2
                for voice in range(3):
                    emit(0xd404 + voice * 7, 0)
                emit(0xd418, 0)
            if state['ending']['phase'] != 2:
                state['ending']['nextCall'] += 1
            returns.append(deepcopy(state))
            continue
        fixed()
        state['countdown'] = (state['countdown'] - 1) & 255
        if state['countdown'] == 255:
            index = state['nextRow']
            if index == len(rows):
                read(composition.get('sourceEvidence', {}).get('terminatorAddress', 0), 0, 'duration')
                restarts.append(tick)
                state['nextRow'], state['countdown'] = 0, 0
                fixed()
                index = 0
            consume(index)
        if ending:
            state['ending']['nextCall'] += 1
        returns.append(deepcopy(state))
    return dict(initial=initial, writes=writes, reads=reads, returns=returns, restartCalls=restarts)


def initial_state(composition):
    return compute(composition, calls=0)['initial']
