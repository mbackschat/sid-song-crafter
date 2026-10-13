"""Compute Ghouls sound from editable numeric state and frequency lookups.

These primitives cover the executed selection-1 sound contract retained in
``evidence/ghouls-components/sound``. They do not execute the original driver,
read source assets or replay captured stores. Validate description state and
lookups on admission; explicit lookup aliases remain editable numeric words.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, replace


def require(condition, message):
    if not condition:
        raise ValueError(message)


@dataclass
class VoiceState:
    waveform: int = 0
    gate_enabled: int = 0
    rest_reload: int = 0
    rest_remaining: int = 0
    pulse_word: int = 0
    pulse_default: int = 0
    pulse_step: int = 0
    transpose: int = 0
    onset_delay: int = 0
    onset_control: int = 0
    onset_frequency: int = 0
    frequency_delay_reload: int = 0
    note_positive_duration: int = 0
    note_negative_duration: int = 0
    note_remaining: int = 0
    glide_rate: int = 0
    note_index: int = 0
    target_note_index: int = 0
    current_frequency: int = 0
    frequency_delay_remaining: int = 0
    frequency_direction_default: int = 0
    frequency_half_remaining: int = 0
    frequency_half_reload: int = 0
    frequency_step: int = 0
    onset_remaining: int = 0
    gate_time: int = 0
    note_step: int = 0
    frequency_direction: int = 0
    note_direction: int = 0
    pulse_direction: int = 0
    pulse_restart: int = 0
    pitch_index_mode: int = 0


@dataclass
class FilterState:
    word: int = 0
    default: int = 0
    step: int = 0
    owner: int = 0
    direction: int = 0
    reset_direction: int = 0
    lower: int = 0
    upper: int = 0


@dataclass
class VoiceResult:
    state: VoiceState
    writes: list
    path: str


VOICE_WORD_FIELDS = frozenset(('pulse_word', 'pulse_default', 'onset_frequency', 'current_frequency'))
FILTER_WORD_FIELDS = frozenset(('word', 'default', 'lower', 'upper'))


def unsigned(value, maximum, name):
    require(type(value) is int and 0 <= value <= maximum,
            f'{name} must be an unsigned {"byte" if maximum == 255 else "word"}')


def validate_voice_state(state):
    """Reject malformed byte/word state and unsupported pulse phase values."""
    require(isinstance(state, VoiceState), 'Expected VoiceState')
    for field in fields(VoiceState):
        unsigned(getattr(state, field.name), 65535 if field.name in VOICE_WORD_FIELDS else 255, field.name)
    require(state.pulse_direction in (0, 1, 255) and state.pulse_restart in (0, 1, 255),
            'Pulse direction/restart must be 0, 1 or 255 within the verified contract')


def validate_filter_state(state):
    """Reject malformed filter byte/word state and undeclared voice owners."""
    require(isinstance(state, FilterState), 'Expected FilterState')
    for field in fields(FilterState):
        unsigned(getattr(state, field.name), 65535 if field.name in FILTER_WORD_FIELDS else 255, field.name)
    require(0 <= state.owner <= 2, 'Filter owner must be voice 0..2')


def validate_lookup(lookup):
    """Admit a numeric index mapping or a sequence of unsigned frequency words.

    A mapping may be sparse. Missing indices are rejected when a program uses
    them; adjacent original bytes are never inferred from the supplied notes.
    """
    require(isinstance(lookup, (Mapping, Sequence)) and not isinstance(lookup, (str, bytes, bytearray)),
            'Frequency lookup must be a numeric mapping or sequence')
    if isinstance(lookup, Mapping):
        for index, value in lookup.items():
            unsigned(index, 255, 'Frequency lookup index')
            unsigned(value, 65535, f'Frequency lookup value at index {index}')
    else:
        require(len(lookup) <= 256, 'Frequency lookup sequence must contain at most 256 words')
        for index, value in enumerate(lookup):
            unsigned(value, 65535, f'Frequency lookup value at index {index}')


def frequency_word(lookup, index):
    require(isinstance(lookup, (Mapping, Sequence)) and not isinstance(lookup, (str, bytes, bytearray)),
            'Frequency lookup must be a numeric mapping or sequence')
    if isinstance(lookup, Mapping):
        require(index in lookup, f'Missing numeric frequency lookup for index {index}')
    else:
        require(index < len(lookup), f'Missing numeric frequency lookup for index {index}')
    value = lookup[index]
    unsigned(value, 65535, f'Frequency lookup value at index {index}')
    return value


def validate_voice(voice):
    require(type(voice) is int and 0 <= voice <= 2, 'Voice index must be 0..2')


def frequency_writes(voice, word):
    base = 0xd400 + 7 * voice
    return [(base, word & 255), (base + 1, word >> 8)]


def onset_step(state, voice):
    """Restore the current body pitch when the delayed onset countdown expires."""
    validate_voice_state(state)
    validate_voice(voice)
    state = replace(state)
    if not state.onset_remaining:
        return VoiceResult(state, [], 'idle')
    state.onset_remaining = (state.onset_remaining - 1) & 255
    if state.onset_remaining:
        return VoiceResult(state, [], 'waiting')
    writes = frequency_writes(voice, state.current_frequency)
    if state.gate_enabled:
        writes.append((0xd404 + 7 * voice, state.waveform | 1))
    return VoiceResult(state, writes, 'restore')


def frequency_step(state, voice):
    """Advance byte-step pitch motion, retaining its native countdown and phase."""
    validate_voice_state(state)
    validate_voice(voice)
    state = replace(state)
    if not state.frequency_delay_reload:
        return VoiceResult(state, [], 'disabled')
    if state.frequency_delay_remaining:
        state.frequency_delay_remaining = (state.frequency_delay_remaining - 1) & 255
        if state.frequency_delay_remaining:
            return VoiceResult(state, [], 'delay')
    low, high = state.current_frequency & 255, state.current_frequency >> 8
    if state.frequency_direction:
        total = low + state.frequency_step
        low = total & 255
        if total > 255:
            high = (high + 1) & 255
        if total > 255 and high == 0:
            # $6271's BNE falls into subtraction on a high-byte wrap; the pinned
            # routine therefore preserves the old word in this boundary case.
            low = (low - state.frequency_step) & 255
            high = 255
        path = 'up'
    else:
        difference = low - state.frequency_step
        low = difference & 255
        high = (high - int(difference < 0)) & 255
        path = 'down'
    state.current_frequency = low | high << 8
    state.frequency_half_remaining = (state.frequency_half_remaining - 1) & 255
    if state.frequency_half_remaining == 0 and state.frequency_half_reload:
        state.frequency_half_remaining = (state.frequency_half_reload * 2) & 255
        state.frequency_direction ^= 255
        path += '-reverse'
    return VoiceResult(state, frequency_writes(voice, state.current_frequency), path)


def note_step(state, voice, lookup):
    """Apply alternating note-index motion before the competing glide stage."""
    validate_voice_state(state)
    validate_voice(voice)
    state = replace(state)
    if state.note_remaining:
        state.note_remaining = (state.note_remaining - 1) & 255
        if state.note_remaining == 0:
            state.note_direction ^= 255
            if state.note_direction:
                state.note_remaining = state.note_positive_duration
                state.note_index = (state.note_index + state.note_step) & 255
                path = 'alternate-up'
            else:
                state.note_remaining = state.note_negative_duration
                state.note_index = (state.note_index - state.note_step) & 255
                path = 'alternate-down'
            state.current_frequency = frequency_word(lookup, state.note_index)
            return VoiceResult(state, frequency_writes(voice, state.current_frequency), path)
    if not state.glide_rate or state.note_index == state.target_note_index:
        return VoiceResult(state, [], 'hold')
    if state.note_index > state.target_note_index:
        candidate = (state.note_index - state.glide_rate) & 255
        state.note_index = candidate if candidate >= state.target_note_index else state.target_note_index
        path = 'glide-down'
    else:
        candidate = (state.note_index + state.glide_rate) & 255
        state.note_index = candidate if candidate < state.target_note_index else state.target_note_index
        path = 'glide-up'
    state.current_frequency = frequency_word(lookup, state.note_index)
    return VoiceResult(state, frequency_writes(voice, state.current_frequency), path)


def pulse_step(state, voice):
    """Compute pulse motion between native word bounds 100 and 3995."""
    validate_voice_state(state)
    validate_voice(voice)
    state = replace(state)
    if state.pulse_direction not in (0, 255):
        return VoiceResult(state, [], 'disabled')
    if state.pulse_direction == 0:
        state.pulse_word = (state.pulse_word - state.pulse_step) & 65535
        if state.pulse_word >= 32768 or state.pulse_word < 100:
            state.pulse_direction = 255
            state.pulse_word = (state.pulse_word + state.pulse_step) & 65535
            path = 'lower-reverse'
        else:
            path = 'down'
    else:
        state.pulse_word = (state.pulse_word + state.pulse_step) & 65535
        path = 'up'
    if state.pulse_direction == 255 and state.pulse_word >= 3995:
        state.pulse_direction = 0
        state.pulse_word = (state.pulse_word - state.pulse_step) & 65535
        path += '-upper-reverse'
    base = 0xd402 + 7 * voice
    return VoiceResult(state, [(base, state.pulse_word & 255), (base + 1, state.pulse_word >> 8)], path)


def filter_step(state):
    """Advance shared cutoff state using the driver's bytewise reversal tests."""
    validate_filter_state(state)
    state = replace(state)
    path = []
    down = state.direction == 0
    for _ in range(256):
        if down:
            low_borrow = (state.word & 255) < state.step
            state.word = (state.word - state.step) & 65535
            high, low = state.word >> 8, state.word & 255
            # Native $680A's carry branch bypasses the sign test unless the low
            # subtraction borrows; a negative high byte alone cannot reverse.
            below = low_borrow and high >= 128 or (high == state.lower >> 8 and low < (state.lower & 255))
            if below:
                state.direction = (state.direction - 1) & 255
                path.append('lower-reverse')
                down = False
                continue
            path.append('down')
            break
        state.word = (state.word + state.step) & 65535
        high, low = state.word >> 8, state.word & 255
        above = high >= state.upper >> 8 and low >= (state.upper & 255)
        if above:
            state.direction = (state.direction + 1) & 255
            path.append('upper-reverse')
            down = True
            continue
        path.append('up')
        break
    else:
        raise ValueError('Filter parameters do not reach the output boundary')
    low, high = state.word & 255, state.word >> 8
    # Native $6848..$684B folds high bits 4..7 into the low output nibble;
    # reducing the state to an 11-bit cutoff would erase that emitted value.
    cutoff_high = ((high & 7) << 5) | (high >> 4) | (low >> 3)
    writes = [(0xd415, low), (0xd416, cutoff_high)]
    return state, writes, '/'.join(path)


def note_setup(state, filter_state, voice, raw_note, lookup):
    """Set a positive score note, preserving native motion/reset/output ordering."""
    validate_voice_state(state)
    validate_filter_state(filter_state)
    validate_voice(voice)
    require(type(raw_note) is int and 1 <= raw_note <= 127, 'note_setup requires a positive native note byte')
    state, filter_state = replace(state), replace(filter_state)
    if state.pitch_index_mode:
        state.pitch_index_mode = (state.pitch_index_mode + 1) & 255
        index = raw_note if state.pitch_index_mode == 0 else (raw_note + state.transpose) & 255
    else:
        index = (raw_note + state.transpose) & 255
    if state.glide_rate:
        state.target_note_index = index
        index = state.note_index
    state.note_index = index
    state.current_frequency = frequency_word(lookup, index)
    writes = frequency_writes(voice, state.current_frequency)
    state.note_remaining = state.note_positive_duration
    if state.frequency_delay_reload:
        state.frequency_delay_remaining = state.frequency_delay_reload
        state.frequency_direction = state.frequency_direction_default
        state.frequency_half_remaining = state.frequency_half_reload
    state.note_direction = 0
    state.rest_remaining = state.rest_reload
    if state.pulse_default:
        state.pulse_word = state.pulse_default
        state.pulse_direction = state.pulse_restart
    if filter_state.owner == voice and filter_state.default:
        filter_state.word = filter_state.default
        filter_state.direction = filter_state.reset_direction
    if state.gate_enabled:
        control = state.waveform
        if state.onset_delay:
            state.onset_remaining = state.onset_delay
            writes.extend(frequency_writes(voice, state.onset_frequency))
            control = state.onset_control
        writes.append((0xd404 + 7 * voice, control | 1))
    return state, filter_state, writes


