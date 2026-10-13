"""Compute verified Deflektor programs from immutable named state and numeric tables.

The bounded original-routine and retained-context proofs live in
evidence/deflektor-{programs,caller,motion}; source addresses are not runtime
inputs. These primitives supply one independent player, without executing
original code or replaying observed register stores.
"""

from dataclasses import dataclass, replace
from collections.abc import Mapping


def require(ok, message):
    if not ok:
        raise ValueError(message)


def byte(value):
    require(type(value) is int and 0 <= value <= 255, 'Expected an unsigned byte')


def word(value):
    require(type(value) is int and 0 <= value <= 65535, 'Expected an unsigned word')


@dataclass(frozen=True)
class Stage:
    control_bits: int
    duration: int


@dataclass(frozen=True)
class WaveProgram:
    loop: bool
    stages: tuple[Stage, ...]


@dataclass(frozen=True)
class WaveState:
    countdown: int
    position: int
    control: int


def validate_wave(program, state):
    require(all(type(value) is int and 0 <= value <= 255
                for value in (state.countdown, state.position, state.control)), 'Wave state must contain bytes')
    if program is None:
        return
    require(type(program.loop) is bool and 2 <= len(program.stages) <= 7,
            'Supported waveform programs require 2..7 stages and an explicit loop flag')
    for stage in program.stages:
        require(type(stage.control_bits) is int and 0 <= stage.control_bits <= 255,
                'Control bits must be a byte')
        require(type(stage.duration) is int and 0 <= stage.duration <= 15,
                'Stage duration must fit its source nibble')


def initialize_wave(program, state):
    """Start an enabled program with the source's extra initial countdown call.

    C49E..C4C8 forces gate on, reads stage zero and starts position one;
    later body reloads use the stage duration without that extra call.
    A disabled program leaves existing waveform state unchanged.
    """
    validate_wave(program, state)
    if program is None:
        return state
    first = program.stages[0]
    return WaveState(first.duration + 1, 1, first.control_bits | 1)


def advance_wave(program, state):
    """Advance one actual macro invocation, retaining the caller's gate bit.

    C6CF..C726 decrements the byte countdown even after a finite program
    has stopped. A negative position suppresses stage lookup; countdown
    zero therefore wraps to 255 on the next invocation without restarting.
    """
    validate_wave(program, state)
    if program is None:
        return state
    countdown = (state.countdown - 1) & 255
    if countdown != 0 or state.position & 128:
        return replace(state, countdown=countdown)
    require(state.position < len(program.stages), 'Waveform lookup escapes the supplied program')
    stage = program.stages[state.position]
    position = state.position + 1
    if position == len(program.stages):
        position = 0 if program.loop else 255
    return WaveState(stage.duration, position, stage.control_bits | (state.control & 1))


def voice_writes(voice, *, frequency, pulse_word, control, attack_decay, sustain_release):
    """Generate the source writer's seven ordered stores from numeric caller context."""
    require(type(voice) is int and 0 <= voice <= 2, 'Voice index must be 0..2')
    require(all(type(value) is int and 0 <= value <= 65535 for value in (frequency, pulse_word)),
            'Frequency and pulse shadow must be words')
    require(all(type(value) is int and 0 <= value <= 255 for value in (control, attack_decay, sustain_release)),
            'Voice control/envelope values must be bytes')
    values = (frequency & 255, frequency >> 8, pulse_word & 255, pulse_word >> 8,
              control, attack_decay, sustain_release)
    return [(0xd400 + 7 * voice + offset, value) for offset, value in enumerate(values)]


@dataclass(frozen=True)
class BodyState:
    remaining: int
    rest: int
    control: int
    frequency: int
    release_threshold: int
    glide_wait: int
    glide_remaining: int
    glide_flags: int
    glide_step: int


def advance_prelude(state, *, global_skip):
    """Advance an entered body, returning whether later programs must run.

    C529..C59A checks release before rest, decrements row/rest counters even
    when output is suppressed, and skips all motion after a global row edge.
    The caller has already performed the C10C..C139 remaining=1 preparation.
    """
    for key, value in vars(state).items():
        (word if key in ('frequency', 'glide_step') else byte)(value)
    if type(global_skip) is not bool or state.remaining == 0:
        raise ValueError('A body requires nonzero remaining and an explicit global skip')
    if state.remaining == state.release_threshold:
        state = replace(state, control=state.control & 254)
    state = replace(state, remaining=(state.remaining - 1) & 255)
    if state.rest:
        return replace(state, rest=(state.rest - 1) & 255), False
    if global_skip:
        return state, False
    if state.glide_wait:
        return replace(state, glide_wait=state.glide_wait - 1), True
    if state.glide_remaining:
        amount = -state.glide_step if state.glide_flags & 32 else state.glide_step
        state = replace(state, frequency=(state.frequency + amount) & 65535,
                        glide_remaining=state.glide_remaining if state.glide_remaining == 255
                        else state.glide_remaining - 1)
    return state, True


@dataclass(frozen=True)
class PitchStage:
    offset: int
    duration: int


@dataclass(frozen=True)
class ScorePitchProgram:
    initial_wait: int
    restart_wait: int
    loop: bool
    stages: tuple[PitchStage, ...]


@dataclass(frozen=True)
class ScorePitchState:
    countdown: int
    position: int
    frequency: int


def validate_score_pitch(program, state):
    byte(state.countdown)
    byte(state.position)
    word(state.frequency)
    if program is None:
        return
    if type(program.loop) is not bool or not 1 <= len(program.stages) <= 7:
        raise ValueError('Score pitch requires 1..7 stages and an explicit loop flag')
    if type(program.initial_wait) is not int or not 1 <= program.initial_wait <= 16:
        raise ValueError('Initial wait must be 1..16')
    if type(program.restart_wait) is not int or not 1 <= program.restart_wait <= 7:
        raise ValueError('Zero header restart delay is outside the decoded title contract')
    for stage in program.stages:
        if type(stage.offset) is not int or not 0 <= stage.offset <= 31 \
                or type(stage.duration) is not int or not 0 <= stage.duration <= 7:
            raise ValueError('Stage must contain a five-bit pitch offset and three-bit duration')


def initialize_score_pitch(program, state):
    """Reset the enabled program's position and first delay at C503..C51C."""
    validate_score_pitch(program, state)
    return state if program is None else replace(state, countdown=program.initial_wait, position=1)


def advance_score_pitch(program, state, *, pitch_index, detune, frequency_words):
    """Advance C726..C7C3 from editable stages and caller-supplied numeric pitches.

    A finite program restores the base frequency on its first expired FF
    position, changes that position to FE, then keeps decrementing its byte
    counter without more lookups. The original's zero-delay restart-header
    special case is not selected by this title and is explicitly unsupported.
    """
    validate_score_pitch(program, state)
    byte(pitch_index)
    byte(detune)
    if program is None:
        return state
    countdown = (state.countdown - 1) & 255
    state = replace(state, countdown=countdown)
    if countdown:
        return state
    position = state.position
    if position & 128:
        if position != 255:
            return state
        offset, position = 0, 254
    else:
        if position > len(program.stages):
            raise ValueError('Score pitch lookup escapes supplied stages')
        stage = PitchStage(0, program.restart_wait) if position == 0 else program.stages[position - 1]
        offset, countdown = stage.offset, stage.duration
        position += 1
        if position == len(program.stages) + 1:
            position = 0 if program.loop else 255
    index = (pitch_index + offset) & 255
    if index not in frequency_words:
        raise ValueError('Missing numeric frequency lookup; adjacent source bytes are not guessed')
    frequency = frequency_words[index]
    word(frequency)
    return ScorePitchState(countdown, position, (frequency + detune) & 65535)


@dataclass(frozen=True)
class PulseProgram:
    interval: int
    table_base: int
    low_step: int


@dataclass(frozen=True)
class PulseState:
    elapsed: int
    position: int
    word: int


@dataclass(frozen=True)
class PitchState:
    wait: int
    position: int
    word: int


@dataclass(frozen=True)
class ResonanceState:
    countdown: int
    position: int


def cell(table, index):
    if not isinstance(table, Mapping) or index not in table:
        raise ValueError(f'Missing numeric table lookup at index {index}')
    value = table[index]
    byte(value)
    return value


def pulse_interpolation(program, elapsed, position, value, table):
    target_high = cell(table, (program.table_base + (position & 127)) & 255) & 15
    high, low = value >> 8, value & 255
    if target_high < high:
        low = (low - program.low_step) & 255
    elif target_high > high:
        low = (low + program.low_step) & 255
    return PulseState(elapsed, position, high << 8 | low)


def advance_pwm(program, state, motion_table):
    """Advance the elapsed byte, marker traversal and low-only pulse movement.

    C59A..C640 overwrites a high target and clears the low byte at each
    interval, then handles direction markers and interpolates in the same
    invocation. High-nibble table bases remain unshifted. Repeated marker
    states reject instead of approximating an original infinite loop.
    """
    for value in (program.interval, program.table_base, program.low_step, state.elapsed, state.position):
        byte(value)
    word(state.word)
    if not program.interval:
        return state
    elapsed = (state.elapsed + 1) & 255
    position, value = state.position, state.word
    if elapsed == program.interval:
        elapsed = 0
        visited = set()
        while True:
            if position in visited:
                raise ValueError('Non-terminating pulse marker loop is unsupported')
            visited.add(position)
            entry = cell(motion_table, (program.table_base + (position & 127)) & 255)
            value = (entry & 15) << 8
            control = entry & 240
            if control == 0x10:
                if position & 128:
                    position = ((position & 127) + 1) & 255
                    continue
            elif control == 0x20:
                position = ((position | 128) - 1) & 255
                continue
            elif control:
                position = 0
                break
            if position & 128:
                position = (position - 1) & 255
                if not position & 128:
                    position = (position + 1) & 255
            else:
                position = (position + 1) & 255
            break
    return pulse_interpolation(program, elapsed, position, value, motion_table)


def initialize_pitch(selector, state, motion_table):
    """Initialize wait and forward position while retaining the newly set note word."""
    for value in (selector, state.wait, state.position):
        byte(value)
    word(state.word)
    if not selector:
        return state
    return PitchState(cell(motion_table, 24 + selector), 1, state.word)


def advance_pitch(selector, state, motion_table):
    """Advance C640..C6CF using signed byte steps and byte-phase reversal.

    Positive wait bytes count down without stepping. Negative waits run the
    sequence until their low seven bits reach zero on a full return to phase
    one; $80 then holds. The extra logical base24 is applied after the
    original byte-index addition, preserving the shared table aliases.
    """
    for value in (selector, state.wait, state.position):
        byte(value)
    word(state.word)
    if not selector:
        return state
    if state.wait and not state.wait & 128:
        return replace(state, wait=state.wait - 1)
    if state.wait == 128:
        return state
    value = cell(motion_table, 24 + ((selector + (state.position & 127)) & 255))
    step = value if value < 128 else value - 256
    if state.position & 128:
        step = -step
    position = (state.position + 1) & 255
    wait = state.wait
    if position & 127 == 8:
        position ^= 0x89
        if position == 1 and wait:
            wait -= 1
    return PitchState(wait, position, (state.word + step) & 65535)


def initialize_resonance(selector, state, resonance_table, shared_shadow):
    """Set the first resonance entry with its extra initial countdown invocation."""
    for value in (selector, state.countdown, state.position, shared_shadow):
        byte(value)
    if not selector:
        return state, shared_shadow
    entry = cell(resonance_table, 1 + selector)
    return ResonanceState((entry & 15) + 1, 1), (entry & 240) | (shared_shadow & 15)


def advance_resonance(selector, state, resonance_table, shared_shadow):
    """Advance a voice's timer and shared resonance in the caller's voice order.

    C7C3..C80F retains literal header low bits, including zero, and literal
    zero durations. Disabled/stopped lookups preserve the shared shadow;
    enabled stages replace its high nibble while preserving routing.
    """
    for value in (selector, state.countdown, state.position, shared_shadow):
        byte(value)
    if not selector:
        return state, shared_shadow
    countdown = (state.countdown - 1) & 255
    if countdown or state.position & 128:
        return replace(state, countdown=countdown), shared_shadow
    entry = cell(resonance_table, 1 + ((selector + state.position) & 255))
    position = (state.position + 1) & 255
    header = cell(resonance_table, selector)
    if position == header & 7:
        position = 0 if header & 128 else 255
    return ResonanceState(entry & 15, position), (entry & 240) | (shared_shadow & 15)
