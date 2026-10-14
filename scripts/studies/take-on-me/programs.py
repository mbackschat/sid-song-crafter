"""Compute bounded Take On Me instrument state from editable numeric inputs.

Voice indices 0, 1 and 2 mean physical SID voices 1, 2 and 3. These pure
helpers model setup and continuing bodies, without source execution, a score
scheduler, SID synthesis or captured-event replay.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, replace


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unsigned(value, maximum, name):
    require(type(value) is int and 0 <= value <= maximum, f'{name} must be an unsigned value <= {maximum}')


@dataclass
class VoiceState:
    frequency: int = 0
    pulse: int = 0
    control: int = 0
    base_note: int = 0
    remaining: int = 0
    duration: int = 0
    glide_step: int = 0
    glide_target: int = 0
    glide_active: int = 0
    arpeggio: int = 0
    onset_initial: int = 0
    arpeggio_cursor: int = 0
    waveform_cursor: int = 0
    pitch_cursor: int = 0
    pulse_initial: int = 0
    pulse_direction: int = 0
    vibrato_initial: int = 0
    vibrato_delay: int = 0
    vibrato_direction: int = 0
    vibrato_remaining: int = 0
    vibrato_step: int = 0


@dataclass
class FilterState:
    word: int = 0
    initial: int = 0
    direction: int = 0


@dataclass(frozen=True)
class SweepProgram:
    initial_direction: int
    down_step: int
    lower: int
    lower_direction: int
    up_step: int
    upper: int
    upper_direction: int


@dataclass(frozen=True)
class VibratoProgram:
    delay: int
    direction: int
    duration: int
    shift: int


@dataclass(frozen=True)
class Instrument:
    pulse: int = 0
    onset_control: int = 0
    body_control: int = 0
    attack_decay: int = 0
    sustain_release: int = 0
    arpeggio_enabled: int = 0
    table_program: int = 0
    pulse_program: int = 0
    vibrato_program: int = 0
    filter_program: int = 0
    filter_word: int = 0
    gate_half: int = 0
    release_program: int = 0


@dataclass
class Programs:
    frequencies: Mapping = field(default_factory=dict)
    arpeggios: Mapping = field(default_factory=dict)
    waveforms: Mapping = field(default_factory=dict)
    pitches: Mapping = field(default_factory=dict)
    pulses: Mapping = field(default_factory=dict)
    vibratos: Mapping = field(default_factory=dict)
    filters: Mapping = field(default_factory=dict)
    releases: Mapping = field(default_factory=dict)


@dataclass
class SoundResult:
    state: VoiceState
    filter_state: FilterState
    writes: list


VOICE_WORDS = frozenset(('frequency', 'pulse', 'glide_step', 'vibrato_step'))
SWEEP_BYTES = frozenset(('initial_direction', 'lower_direction', 'upper_direction'))


def validate_state(state, expected_type, word_fields=()):
    require(isinstance(state, expected_type), f'Expected {expected_type.__name__}')
    for item in fields(expected_type):
        unsigned(getattr(state, item.name), 65535 if item.name in word_fields else 255, item.name)


def validate_voice(voice):
    unsigned(voice, 2, 'Voice index')


def validate_instrument(instrument):
    validate_state(instrument, Instrument, ('pulse', 'filter_word'))


def frequency(lookup, index):
    require(isinstance(lookup, Mapping), 'Frequency lookup must be a numeric mapping')
    require(index in lookup, f'Missing frequency index {index}')
    value = lookup[index]
    unsigned(value, 65535, f'Frequency at index {index}')
    return value


def selected(mapping, index, name):
    require(isinstance(mapping, Mapping) and index in mapping, f'Missing {name} program {index}')
    return mapping[index]


def table_step(program, cursor):
    """Consume a byte, a $FF cursor jump, or a $FE terminal hold."""
    require(isinstance(program, Sequence) and not isinstance(program, (str, bytes, bytearray)),
            'Table program must be an editable byte sequence')
    require(1 <= len(program) <= 256, 'Table program must contain 1..256 bytes')
    for value in program:
        unsigned(value, 255, 'Table byte')
    unsigned(cursor, 255, 'Table cursor')
    visited = set()
    while True:
        require(cursor < len(program), f'Table cursor {cursor} escapes its declared program')
        require(cursor not in visited, 'Table jump does not reach a value or hold')
        visited.add(cursor)
        value = program[cursor]
        if value == 254:
            return None, cursor
        if value != 255:
            return value, (cursor + 1) & 255
        target_cursor = (cursor + 1) & 255
        require(target_cursor < len(program), 'Table jump lacks its target cursor')
        cursor = program[target_cursor]


def sweep_step(word, initial, direction, program):
    """Advance the driver's full-word PWM/filter sweep and boundary phase.

    $1282/$1400 keep the overshooting word on a phase change. Resetting to
    the opposite bound occurs only for the corresponding zero/positive phase,
    so clamping every crossing would alter the executed trajectories.
    """
    unsigned(word, 65535, 'Sweep word')
    unsigned(initial, 255, 'Sweep initialization flag')
    unsigned(direction, 255, 'Sweep direction')
    require(isinstance(program, SweepProgram), 'Expected SweepProgram')
    for item in fields(SweepProgram):
        unsigned(getattr(program, item.name), 255 if item.name in SWEEP_BYTES else 65535, item.name)
    if initial < 128:
        initial = (initial - 1) & 255
        direction = program.initial_direction
    if direction >= 128:
        return word, initial, direction
    if direction == 0:
        word = (word - program.down_step) & 65535
        if word < program.lower:
            direction = program.lower_direction
            if direction == 0:
                word = program.upper
    else:
        word = (word + program.up_step) & 65535
        if word >= program.upper:
            direction = program.upper_direction
            if 0 < direction < 128:
                word = program.lower
    return word, initial, direction


def note_setup(state, filter_state, instrument, voice, frequencies):
    """Seed sound after the score's note reset; emit only onset ADSR stores."""
    validate_state(state, VoiceState, VOICE_WORDS)
    validate_state(filter_state, FilterState, ('word',))
    validate_instrument(instrument)
    validate_voice(voice)
    state, filter_state = replace(state), replace(filter_state)
    state.frequency = frequency(frequencies, state.base_note)
    state.pulse = instrument.pulse
    state.control = instrument.onset_control
    if voice == 0:
        filter_state.initial = 0
        filter_state.word = instrument.filter_word
    base = 0xd400 + 7 * voice
    return SoundResult(state, filter_state, [(base + 5, instrument.attack_decay), (base + 6, instrument.sustain_release)])


def vibrato_step(state, program, frequencies):
    """Return a delayed note-relative vibrato step without mutating its input."""
    validate_state(state, VoiceState, VOICE_WORDS)
    require(isinstance(program, VibratoProgram), 'Expected VibratoProgram')
    validate_state(program, VibratoProgram)
    require(program.shift <= 16, 'Vibrato shift must be <= 16')
    state = replace(state)
    if state.vibrato_initial < 128:
        state.vibrato_initial = (state.vibrato_initial - 1) & 255
        state.vibrato_delay = program.delay
        state.vibrato_direction = program.direction
        state.vibrato_remaining = (program.duration + 1) // 2
        difference = (frequency(frequencies, (state.base_note + 1) & 255) -
                      frequency(frequencies, state.base_note)) & 65535
        state.vibrato_step = difference >> program.shift
    if state.vibrato_delay:
        state.vibrato_delay = (state.vibrato_delay - 1) & 255
    elif state.vibrato_remaining:
        state.vibrato_remaining = (state.vibrato_remaining - 1) & 255
        sign = 1 if state.vibrato_direction else -1
        state.frequency = (state.frequency + sign * state.vibrato_step) & 65535
    else:
        state.vibrato_remaining = program.duration
        state.vibrato_direction ^= 1
    return state


def body_step(state, filter_state, instrument, programs, voice):
    """Advance one continuing body in the executed stage order.

    Glide consumes the pitch stage in preference to vibrato ($12EA–$1347).
    Natural selected-source rows have no glide; that branch has unit guards
    but is excluded from the probe's natural execution-coverage claim.
    """
    validate_state(state, VoiceState, VOICE_WORDS)
    validate_state(filter_state, FilterState, ('word',))
    validate_instrument(instrument)
    validate_voice(voice)
    require(isinstance(programs, Programs), 'Expected Programs')
    state, filter_state = replace(state), replace(filter_state)
    if state.onset_initial < 128:
        state.onset_initial = (state.onset_initial - 1) & 255
        state.control = instrument.body_control
    if instrument.arpeggio_enabled:
        value, state.arpeggio_cursor = table_step(selected(programs.arpeggios, state.arpeggio, 'arpeggio'),
                                                state.arpeggio_cursor)
        if value is not None:
            state.frequency = frequency(programs.frequencies, (state.base_note + value) & 255)
    if instrument.table_program:
        value, state.waveform_cursor = table_step(selected(programs.waveforms, instrument.table_program, 'waveform'),
                                                 state.waveform_cursor)
        if value is not None:
            state.control = value
        value, state.pitch_cursor = table_step(selected(programs.pitches, instrument.table_program, 'pitch'),
                                              state.pitch_cursor)
        if value is not None:
            state.frequency = (frequency(programs.frequencies, state.base_note) + (value << 8)) & 65535
    if instrument.pulse_program:
        state.pulse, state.pulse_initial, state.pulse_direction = sweep_step(
            state.pulse, state.pulse_initial, state.pulse_direction,
            selected(programs.pulses, instrument.pulse_program, 'pulse'))
    if state.glide_active:
        target = frequency(programs.frequencies, state.glide_target)
        down = state.base_note >= state.glide_target
        state.frequency = (state.frequency + (-state.glide_step if down else state.glide_step)) & 65535
        if (down and state.frequency < target) or (not down and state.frequency >= target):
            state.glide_active = 0
            state.frequency = target
    elif instrument.vibrato_program:
        state = vibrato_step(state, selected(programs.vibratos, instrument.vibrato_program, 'vibrato'), programs.frequencies)
    if voice == 0 and instrument.filter_program:
        filter_state.word, filter_state.initial, filter_state.direction = sweep_step(
            filter_state.word, filter_state.initial, filter_state.direction,
            selected(programs.filters, instrument.filter_program, 'filter'))
    if instrument.gate_half and state.remaining <= state.duration // 2:
        state.control &= 254
    writes = []
    if instrument.release_program:
        release = selected(programs.releases, instrument.release_program, 'release')
        require(isinstance(release, Sequence) and len(release) == 2, 'Release program must contain gate and SR-zero thresholds')
        gate, sr_zero = release
        unsigned(gate, 255, 'Release gate threshold')
        unsigned(sr_zero, 255, 'Release SR-zero threshold')
        if state.remaining <= gate:
            state.control &= 254
        if state.remaining == sr_zero:
            writes.append((0xd406 + 7 * voice, 0))
    return SoundResult(state, filter_state, writes)


def voice_output(state, voice):
    """Emit control, pulse high/low and frequency high/low in source order."""
    validate_state(state, VoiceState, VOICE_WORDS)
    validate_voice(voice)
    base = 0xd400 + 7 * voice
    return [(base + 4, state.control), (base + 3, state.pulse >> 8), (base + 2, state.pulse & 255),
            (base + 1, state.frequency >> 8), (base, state.frequency & 255)]


def filter_output(state):
    validate_state(state, FilterState, ('word',))
    return [(0xd415, state.word & 255), (0xd416, state.word >> 8)]
