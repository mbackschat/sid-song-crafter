"""Editable waveform stages with Deflektor's initializer and body timing."""

from dataclasses import dataclass, replace


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


def require(ok, message):
    if not ok:
        raise ValueError(message)


def validate(program, state):
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
    validate(program, state)
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
    validate(program, state)
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
