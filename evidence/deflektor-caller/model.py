"""Compute Deflektor's body admission, row glide and score-selected pitch stages."""

from dataclasses import dataclass, replace


def byte(value):
    if type(value) is not int or not 0 <= value <= 255:
        raise ValueError('Expected an unsigned byte')


def word(value):
    if type(value) is not int or not 0 <= value <= 65535:
        raise ValueError('Expected an unsigned word')


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


def validate(program, state):
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
    validate(program, state)
    return state if program is None else replace(state, countdown=program.initial_wait, position=1)


def advance_score_pitch(program, state, *, pitch_index, detune, frequency_words):
    """Advance C726..C7C3 from editable stages and caller-supplied numeric pitches.

    A finite program restores the base frequency on its first expired FF
    position, changes that position to FE, then keeps decrementing its byte
    counter without more lookups. The original's zero-delay restart-header
    special case is not selected by this title and is explicitly unsupported.
    """
    validate(program, state)
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
