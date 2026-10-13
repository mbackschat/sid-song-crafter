"""Compute the archive's pitch buffers from named caller state, without source I/O."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class GlideAction(str, Enum):
    DISABLED = 'disabled'
    WAIT = 'wait'
    INTERPOLATE = 'interpolate'
    COMPLETE = 'complete'


@dataclass(frozen=True)
class PitchState:
    base_note: int
    frequency: int
    held_frequency: int
    vibrato_extent: int
    vibrato_direction: int
    vibrato_position: int
    vibrato_age: int
    glide_enabled: int
    glide_active: int
    glide_control: int
    glide_target: int


@dataclass(frozen=True)
class PitchInputs:
    effective_frequency: int
    adjacent_frequency: int
    base_frequency: int
    target_frequency: int
    note_age: int
    row_remaining: int
    row_duration: int
    speed: int


@dataclass(frozen=True)
class PitchParameters:
    vibrato_control: int
    vibrato_wait: int
    drum_mode: bool = False


@dataclass(frozen=True)
class PitchStep:
    state: PitchState
    vibrato_ran: bool
    vibrato_delta: int | None
    glide_action: GlideAction
    glide_divisor: int | None = None
    glide_step: int | None = None


def _bounded(value, maximum, name):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError(f'{name} must be an integer in 0..{maximum}')


def advance_phase(direction, position, extent):
    """Keep the signed branches and byte wrapping at archive $AA20–$AA42."""
    for name, value in [('direction', direction), ('position', position), ('extent', extent)]:
        _bounded(value, 255, name)
    if direction & 128:
        position = (position - 1) & 255
        if position:
            return direction, position
        direction = (direction + 1) & 255
        if not direction & 128:
            return direction, position
    position = (position + 1) & 255
    if position > extent:
        direction = (direction - 1) & 255
        position = (extent - 1) & 255
    return direction, position


def centered_pitch(base, delta, extent, position, note_age, wait):
    """Compute the separate subtract/add loops at $AA43–$AA84."""
    for name, value in [('base', base), ('delta', delta)]:
        _bounded(value, 65535, name)
    for name, value in [('extent', extent), ('position', position), ('note_age', note_age), ('wait', wait)]:
        _bounded(value, 255, name)
    center = extent // 2
    if center and note_age < wait:
        return base
    additions = position if position <= 128 else 0
    return (base + (additions - center) * delta) & 65535


def glide_divisor(length, speed):
    """Retain carry between the byte additions and signed DEY at $AB0D–$AB18."""
    _bounded(length, 15, 'length')
    _bounded(speed, 255, 'speed')
    iterations = speed + 1 if speed <= 128 else 1
    total, carry = 0, 0
    for _ in range(iterations):
        summed = total + length + carry
        total, carry = summed & 255, int(summed > 255)
    return total


def rounded_glide_step(distance, divisor):
    """Compute the 15-round divider at $AB1A–$AB42, including its byte rounding."""
    _bounded(distance, 65535, 'distance')
    _bounded(divisor, 255, 'divisor')
    high_bit = distance & 32768
    if divisor == 0:
        return (high_bit + 32768) & 65535
    quotient, remainder = divmod(distance & 32767, divisor)
    rounded = int(((2 * remainder) & 255) >= divisor)
    return (high_bit + quotient + rounded) & 65535


def advance_pitch(state, parameters, inputs):
    """Advance vibrato then glide; caller owns row changes, arpeggio and later overrides.

    Archive $A9C1–$AB8C updates buffers rather than emitting SID stores. Input
    frequency may already contain a tone-arpeggio result; held_frequency is a
    separate persistent buffer. The drum dispatch bypasses vibrato but reaches
    glide. All indices are opaque byte identities; caller supplies lookup words.
    """
    for name, value in vars(state).items():
        _bounded(value, 65535 if name in ('frequency', 'held_frequency') else 255, name)
    for name, value in vars(inputs).items():
        _bounded(value, 65535 if name.endswith('frequency') else 255, name)
    _bounded(parameters.vibrato_control, 255, 'vibrato_control')
    _bounded(parameters.vibrato_wait, 255, 'vibrato_wait')
    if type(parameters.drum_mode) is not bool:
        raise ValueError('drum_mode must be a boolean')

    control = parameters.vibrato_control
    ran = not parameters.drum_mode and control != 0 and state.glide_active == 0
    delta = None
    if ran:
        extent = (control >> 4) & 7
        age = state.vibrato_age + 1 if state.vibrato_age < 48 else state.vibrato_age
        difference = (inputs.adjacent_frequency - inputs.effective_frequency) & 65535
        if control & 128:
            high = ((difference >> 8) + age + int(inputs.adjacent_frequency >= inputs.effective_frequency)) & 255
            difference = (high << 8) | (difference & 255)
        delta = difference >> (control & 15)
        direction, position = advance_phase(state.vibrato_direction, state.vibrato_position, extent)
        frequency = centered_pitch(inputs.effective_frequency, delta, extent, position,
                                   inputs.note_age, parameters.vibrato_wait)
        state = replace(state, frequency=frequency, held_frequency=frequency,
                        vibrato_extent=extent, vibrato_age=age,
                        vibrato_direction=direction, vibrato_position=position)

    if state.glide_enabled == 0:
        return PitchStep(state, ran, delta, GlideAction.DISABLED)
    length = state.glide_control >> 4
    offset = ((state.glide_control & 15) - 1) & 255
    timing = (inputs.row_remaining + offset) & 255
    if timing >= inputs.row_duration:
        return PitchStep(state, ran, delta, GlideAction.WAIT)
    state = replace(state, glide_active=1)
    if ((timing + length) & 255) < inputs.row_duration:
        state = replace(state, base_note=state.glide_target, frequency=inputs.target_frequency,
                        held_frequency=inputs.target_frequency, glide_enabled=0, glide_active=0)
        return PitchStep(state, ran, delta, GlideAction.COMPLETE)
    divisor = glide_divisor(length, inputs.speed)
    step = rounded_glide_step(abs(inputs.base_frequency - inputs.target_frequency), divisor)
    frequency = (state.held_frequency + (step if inputs.base_frequency < inputs.target_frequency else -step)) & 65535
    state = replace(state, frequency=frequency, held_frequency=frequency)
    return PitchStep(state, ran, delta, GlideAction.INTERPOLATE, divisor, step)
