"""Numeric note setup and continuing sound programs for the pinned Monty variant."""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Instrument:
    pulse_word: int
    waveform: int
    attack_decay: int
    sustain_release: int
    vibrato_depth: int
    pulse_value: int
    effects: int


@dataclass(frozen=True)
class VoiceState:
    note: int
    control: int
    remaining: int
    held_frequency: int
    voice_control: int
    pulse_delay: int
    pulse_direction: int
    portamento: int


@dataclass(frozen=True)
class PitchLookups:
    base_word: int
    next_word: int
    octave_word: int


@dataclass(frozen=True)
class Step:
    state: VoiceState
    instrument: Instrument
    writes: tuple


def _validate(state, instrument, lookups=None):
    for name, value in vars(state).items():
        limit = 65535 if name == 'held_frequency' else 255
        if type(value) is not int or not 0 <= value <= limit:
            raise ValueError(f'{name} must be an integer in 0..{limit}')
    for name, value in vars(instrument).items():
        limit = 65535 if name == 'pulse_word' else 255
        if type(value) is not int or not 0 <= value <= limit:
            raise ValueError(f'{name} must be an integer in 0..{limit}')
    if lookups is not None:
        for name, value in vars(lookups).items():
            if type(value) is not int or not 0 <= value <= 65535:
                raise ValueError(f'{name} must be an integer in 0..65535')


def initialize_note(state, instrument, *, note=None, frequency_word=None, append=False):
    """Compute enabled note/setup stores, retaining per-voice PWM delay/direction.

    Caller resolves the frequency before updating voice_control: native note
    lookups can alias that array beyond the declared frequency table. This
    helper covers the selected title's negative $84FD output-enable flag.
    Row decoding, cursor advances and the positive sound-overlay flag are
    outside this component; initializer calls skip continuing programs.
    """
    _validate(state, instrument)
    writes = []
    if type(append) is not bool:
        raise ValueError('append must be boolean')
    if append:
        if note is not None or frequency_word is not None:
            raise ValueError('Append retains the note and held frequency')
    else:
        if type(note) is not int or not 0 <= note <= 255 or type(frequency_word) is not int or not 0 <= frequency_word <= 65535:
            raise ValueError('A new note requires a byte note and word frequency')
        state = replace(state, note=note, held_frequency=frequency_word)
        writes.extend(((1, frequency_word >> 8), (0, frequency_word & 255)))
    state = replace(state, voice_control=instrument.waveform)
    writes.extend(((4, instrument.waveform & (254 if append else 255)),
                   (2, instrument.pulse_word & 255), (3, instrument.pulse_word >> 8),
                   (5, instrument.attack_decay), (6, instrument.sustain_release)))
    return Step(state, instrument, tuple(writes))


def advance_body(state, instrument, lookups, *, counter, release_check=False):
    """Compute ordered relative SID stores and numeric state for one enabled body.

    The caller shares the returned instrument record between voices and keeps
    voice states separate. Pitch words are editable lookup inputs resolved at
    the corresponding stages; raw-note doubling wraps at byte width, while
    the vibrato adjacent load uses the shifted table base. No register trace,
    source file or CPU is consulted by this helper.
    """
    _validate(state, instrument, lookups)
    if type(counter) is not int or not 0 <= counter <= 255 or type(release_check) is not bool:
        raise ValueError('Counter must be a byte and release_check boolean')
    writes = []
    if release_check and not state.control & 32 and state.remaining == 0:
        writes.extend(((4, state.voice_control & 254), (5, 0), (6, 0)))
    if instrument.vibrato_depth:
        position = counter & 7
        if position >= 4:
            position ^= 7
        # $81E4..$81EB shifts before a signed DEC/BPL test, including the
        # depth128 rollover; a depth129..255 consequently takes only one shift.
        shifts = instrument.vibrato_depth + 1 if instrument.vibrato_depth <= 128 else 1
        difference = ((lookups.next_word - lookups.base_word) & 65535) >> shifts
        frequency = (lookups.base_word + (position if state.control & 31 >= 8 else 0) * difference) & 65535
        writes.extend(((0, frequency & 255), (1, frequency >> 8)))
    if instrument.pulse_value:
        delay = (state.pulse_delay - 1) & 255
        state = replace(state, pulse_delay=delay)
        if delay & 128:
            step = instrument.pulse_value & 224
            direction = state.pulse_direction
            width = (instrument.pulse_word + (-step if direction else step)) & 4095
            high = width >> 8
            if not direction and high == 14:
                direction = (direction + 1) & 255
            elif direction and high == 8:
                direction = (direction - 1) & 255
            state = replace(state, pulse_delay=instrument.pulse_value & 31, pulse_direction=direction)
            instrument = replace(instrument, pulse_word=width)
            writes.extend(((3, high), (2, width & 255)))
    if state.portamento:
        step = state.portamento & 126
        word = (state.held_frequency + (-step if state.portamento & 1 else step)) & 65535
        state = replace(state, held_frequency=word)
        writes.extend(((0, word & 255), (1, word >> 8)))
    high = state.held_frequency >> 8
    if instrument.effects & 1 and high and state.remaining:
        first = ((state.control & 31) - 1) & 255 < state.remaining
        if first:
            writes.extend(((1, high), (4, 128)))
        else:
            state = replace(state, held_frequency=(((high - 1) & 255) << 8) | (state.held_frequency & 255))
            writes.append((1, high))
            waveform = state.voice_control & 254
            if waveform == 0:
                writes.append((1, state.held_frequency >> 8))
                waveform = 128
            writes.append((4, waveform))
    high = state.held_frequency >> 8
    if instrument.effects & 2 and counter & 1 and high:
        state = replace(state, held_frequency=(((high - 1) & 255) << 8) | (state.held_frequency & 255))
        # $8328 LDA precedes $832D DEC: the SID receives the old high byte.
        writes.append((1, high))
    if instrument.effects & 4:
        writes.extend(((1, lookups.octave_word >> 8), (0, lookups.octave_word & 255)))
    return Step(state, instrument, tuple(writes))
