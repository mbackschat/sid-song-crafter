"""Compute Rambo's named-state SOUND programs without source execution or replay.

Inputs describe one actual SOUND invocation, after score/note initialization.
Binary arithmetic, voice order and invocation scheduling belong to the caller.
Arpeggio pitch words are editable numeric lookup inputs, not source addresses.
"""

from collections.abc import Mapping
from copy import deepcopy


BYTE_FIELDS = ('frequencyDelay', 'frequencyFlags', 'pulseDelay', 'pulseFlags',
               'control', 'releaseCountdown', 'life')
WORD_FIELDS = ('pulseInitial', 'frequency', 'pulse')
ARRAY_FIELDS = {
    'frequencySteps': (4, 65535), 'frequencyDurations': (4, 255),
    'pulseDurations': (2, 255), 'pulseSteps': (2, 65535),
    'frequencyRemaining': (4, 255), 'pulseRemaining': (2, 255),
}


def validated(state, voice, row_remaining):
    if type(voice) is not int or not 0 <= voice <= 2 \
            or type(row_remaining) is not int or not 0 <= row_remaining <= 255:
        raise ValueError('Voice and row remaining must be finite decoded integers')
    if not isinstance(state, dict) or set(state) != set(BYTE_FIELDS + WORD_FIELDS) | set(ARRAY_FIELDS):
        raise ValueError('Expected the named SOUND state fields')
    for key in BYTE_FIELDS + WORD_FIELDS:
        limit = 255 if key in BYTE_FIELDS else 65535
        if type(state[key]) is not int or not 0 <= state[key] <= limit:
            raise ValueError(f'Invalid {key}')
    for key, (length, limit) in ARRAY_FIELDS.items():
        if not isinstance(state[key], (list, tuple)) or len(state[key]) != length \
                or any(type(value) is not int or not 0 <= value <= limit for value in state[key]):
            raise ValueError(f'Invalid {key}')
    result = deepcopy(state)
    for key in ARRAY_FIELDS:
        result[key] = list(result[key])
    return result


def advance_lifetime(state, row_remaining, base):
    """Advance lifetime before programs; false means SOUND returns immediately."""
    if not state['life']:
        return [], False
    if state['control'] & 8:
        if row_remaining >= state['releaseCountdown']:
            return [], True
        state['releaseCountdown'] = 0
        state['control'] &= 0xf6
        if state['control']:
            return [(base + 4, state['control'])], True
    if state['releaseCountdown']:
        state['releaseCountdown'] -= 1
        writes = [(base + 4, state['control'] & 0xf6)] if not state['releaseCountdown'] else []
        return writes, True
    state['life'] -= 1
    if not state['life']:
        return [(base + offset, 0) for offset in range(6, -1, -1)], False
    return [], True


def advance_pwm(state, base):
    """Advance two additive phases; bit 7 reloads width, bit 0 only counters."""
    if not state['pulseFlags']:
        return []
    if state['pulseDelay']:
        state['pulseDelay'] -= 1
        return []
    remaining = state['pulseRemaining']
    if not any(remaining) and state['pulseFlags'] & 0x81:
        remaining[:] = state['pulseDurations']
        if state['pulseFlags'] & 0x80:
            state['pulse'] = state['pulseInitial']
        if not any(remaining):
            raise ValueError('Non-terminating zero-duration PWM loop is unsupported')
    phase = next((i for i, value in enumerate(remaining) if value), None)
    if phase is not None:
        remaining[phase] -= 1
        state['pulse'] = (state['pulse'] + state['pulseSteps'][phase]) & 65535
    return [(base + 2, state['pulse'] & 255), (base + 3, state['pulse'] >> 8)]


def advance_arpeggio(state, base, frequency_words):
    """Resolve the descending byte position through the ten-byte chord overlay.

    Archive $22F5..$230F/$285D..$2877 uses offsets 0..9 of the sounding
    block as chord bytes, aliasing the four step words and two durations.
    The position's high bit selects restart; decrement wraps zero to FF.
    """
    position = state['frequencyDelay']
    if position & 128:
        position = state['frequencyDurations'][3]
    if not 0 <= position < 10:
        raise ValueError('Arpeggio position escapes the supported ten-byte chord')
    if position < 8:
        offset = (state['frequencySteps'][position // 2] >> (8 * (position & 1))) & 255
    else:
        offset = state['frequencyDurations'][position - 8]
    pitch = (state['frequencyDurations'][2] + offset) & 255
    if not isinstance(frequency_words, Mapping) or pitch not in frequency_words:
        raise ValueError(f'Missing numeric arpeggio frequency at pitch {pitch}')
    frequency = frequency_words[pitch]
    if type(frequency) is not int or not 0 <= frequency <= 65535:
        raise ValueError('Arpeggio frequency must be an unsigned word')
    state['frequencyDelay'] = (position - 1) & 255
    state['frequency'] = frequency
    return [(base, frequency & 255), (base + 1, frequency >> 8)]


def advance_frequency(state, voice, base, frequency_words=None):
    """Advance sequential pitch or the first/third physical voice's arpeggio.

    Archive $28A3..$28CE reloads physical voice 3 after its third phase;
    its fourth step, like physical voice 2's, applies only during delay.
    """
    if not state['frequencyFlags']:
        return []
    if voice != 1 and state['frequencyFlags'] & 8:
        return advance_arpeggio(state, base, frequency_words)
    if state['frequencyDelay']:
        state['frequencyDelay'] -= 1
        if not state['frequencyFlags'] & 2:
            return []
        phase = 3
    else:
        length = 4 if voice == 0 else 3
        if not any(state['frequencyRemaining'][:length]):
            state['frequencyRemaining'][:] = state['frequencyDurations']
        phase = next((i for i, value in enumerate(state['frequencyRemaining'][:length]) if value), None)
        if phase is None:
            raise ValueError('Non-terminating zero-duration frequency loop is unsupported')
        state['frequencyRemaining'][phase] -= 1
    state['frequency'] = (state['frequency'] + state['frequencySteps'][phase]) & 65535
    return [(base, state['frequency'] & 255), (base + 1, state['frequency'] >> 8)]


def advance_voice(state, *, voice, row_remaining, frequency_words=None):
    """Return new named state and ordered stores for one binary SOUND invocation.

    State uses the field contract in evidence/rambo-programs/contract.json.
    Arpeggios alias frequencySteps' eight encoded bytes, the first two
    frequencyDurations as chord bytes, duration 2 as base pitch, duration 3
    as restart position, and frequencyDelay as the descending position.
    Supply numeric frequency_words by byte pitch only when that path runs.

    This component includes lifetime, release, PWM and pitch. It requires
    a terminating program and arpeggio positions inside the ten-byte chord;
    note/score setup, shared filter and CPU register/flag outputs belong to
    other components. Inputs remain unchanged, including supplied arrays.
    """
    state = validated(state, voice, row_remaining)
    base = 0xd400 + voice * 7
    writes, alive = advance_lifetime(state, row_remaining, base)
    if alive:
        writes += advance_pwm(state, base)
        writes += advance_frequency(state, voice, base, frequency_words)
    return state, writes
