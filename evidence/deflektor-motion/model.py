"""Compute Deflektor's pulse, delayed signed-pitch and shared-resonance motion."""

from dataclasses import dataclass, replace
from collections.abc import Mapping


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


def byte(value):
    if type(value) is not int or not 0 <= value <= 255:
        raise ValueError('Expected an unsigned byte')


def word(value):
    if type(value) is not int or not 0 <= value <= 65535:
        raise ValueError('Expected an unsigned word')


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
