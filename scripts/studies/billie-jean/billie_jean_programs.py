"""Compute editable Billie Jean sound without source execution or event replay.

Voice indices 0..2 mean physical SID voices 1..3. Software waveform and gate
mask are distinct from the hardware control written during a hard restart.
The caller consumes score rows, advances age after each voice, and writes
global volume after processing voices 2, 1 and 0.
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
    waveform: int = 0
    pulse: int = 0
    frequency: int = 0
    base_note: int = 0
    remaining: int = 0
    hold: int = 0
    instrument_offset: int = 0
    gate_mask: int = 254
    glide_step: int = 0
    glide_target: int = 0
    pulse_direction: int = 0
    age: int = 0
    vibrato_phase: int = 1
    wave_cursor: int = 0


@dataclass
class FilterState:
    cutoff: int = 0
    mode: int = 0
    routing: int = 0


@dataclass(frozen=True)
class Instrument:
    attack_decay: int = 0
    sustain_release: int = 0
    pulse_initial: int = 0
    pulse_step: int = 0
    pulse_lower: int = 0
    pulse_upper: int = 0
    vibrato_delay: int = 0
    vibrato_step: int = 0
    vibrato_half: int = 0
    vibrato_period: int = 0
    vibrato_seed: int = 1
    filter_initialize: int = 0
    filter_start: int = 0
    filter_enabled: int = 0
    filter_step: int = 0
    filter_mode: int = 0
    wave_loop: int = 0


@dataclass
class Programs:
    frequencies: Mapping = field(default_factory=dict)
    pitches: Sequence = field(default_factory=list)
    waveforms: Sequence = field(default_factory=list)
    routing_set: Sequence = (241, 242, 244)
    routing_clear: Sequence = (254, 253, 251)


@dataclass
class SoundResult:
    state: VoiceState
    filter_state: FilterState
    writes: list
    path: str


WORD_FIELDS = frozenset(('pulse', 'frequency'))


def validate_state(state, state_type, word_fields=()):
    require(isinstance(state, state_type), f'Expected {state_type.__name__}')
    for item in fields(state_type):
        unsigned(getattr(state, item.name), 65535 if item.name in word_fields else 255, item.name)


def validate_inputs(state, shared, instrument, voice):
    validate_state(state, VoiceState, WORD_FIELDS)
    validate_state(shared, FilterState)
    validate_state(instrument, Instrument)
    unsigned(instrument.pulse_lower, 15, 'Pulse lower high byte')
    unsigned(instrument.pulse_upper, 15, 'Pulse upper high byte')
    unsigned(voice, 2, 'Voice index')


def frequency(lookup, note):
    index = note & 127
    require(isinstance(lookup, Mapping), 'Frequency lookup must be a numeric mapping')
    require(index in lookup, f'Missing frequency index {index}')
    value = lookup[index]
    unsigned(value, 65535, 'Frequency word')
    return value


def voice_output(state, voice):
    validate_state(state, VoiceState, WORD_FIELDS)
    unsigned(voice, 2, 'Voice index')
    base = 0xd400 + voice * 7
    return [(base + 4, state.waveform & state.gate_mask), (base, state.frequency & 255),
            (base + 1, state.frequency >> 8), (base + 2, state.pulse & 255), (base + 3, state.pulse >> 8)]


def note_setup(state, shared, instrument, programs, voice):
    """Apply legato or hard-restart setup after the score-owned setters.

    The original $10E6 gate-mask test chooses these paths. Hard restart writes
    TEST/GATE but retains the cached frequency, waveform and PWM direction;
    its next body supplies the first ordinary voice output.
    """
    validate_inputs(state, shared, instrument, voice)
    require(isinstance(programs, Programs), 'Expected Programs')
    state, shared = replace(state), replace(shared)
    state.vibrato_phase = instrument.vibrato_seed
    if state.gate_mask & 1:
        state.frequency = frequency(programs.frequencies, state.base_note)
        return SoundResult(state, shared, voice_output(state, voice), 'legato')
    base = 0xd400 + voice * 7
    writes = [(base + 4, 0), (base + 5, instrument.attack_decay),
              (base + 6, instrument.sustain_release), (base + 4, 9)]
    state.gate_mask = 255
    state.pulse = instrument.pulse_initial * 257
    if instrument.filter_initialize:
        shared.cutoff = instrument.filter_start
    state.wave_cursor = 0
    state.age = 0
    return SoundResult(state, shared, writes, 'hard-restart')


def pitch_stage(state, instrument, programs):
    require(len(programs.pitches) == 256 and len(programs.waveforms) == 256,
            'Paired pitch/waveform banks must each contain 256 numeric bytes')
    visited = set()
    while True:
        index = (state.instrument_offset + state.wave_cursor) & 255
        require(index not in visited, 'Pitch loop does not reach a value or hold')
        visited.add(index)
        value = programs.pitches[index]
        unsigned(value, 255, 'Pitch-program byte')
        if value == 126:
            return False
        if value == 127:
            state.wave_cursor = instrument.wave_loop
            continue
        state.waveform = programs.waveforms[index]
        unsigned(state.waveform, 255, 'Waveform-program byte')
        note = value & 127 if value >= 128 else (value + state.base_note) & 255
        state.frequency = frequency(programs.frequencies, note)
        state.wave_cursor = (state.wave_cursor + 1) & 255
        return True


def body_step(state, shared, instrument, programs, voice, divider):
    """Advance PWM, paired tables, conditional pitch, filter/gate and writer.

    $128C/$12AB bypass filter/gate after an upward clamp and every downward
    glide. Preserving this branch ownership matters to shared-filter order.
    """
    validate_inputs(state, shared, instrument, voice)
    require(isinstance(programs, Programs), 'Expected Programs')
    unsigned(divider, 255, 'Score divider')
    state, shared = replace(state), replace(shared)
    if not state.pulse_direction:
        state.pulse = (state.pulse + instrument.pulse_step) & 4095
        if state.pulse >> 8 >= instrument.pulse_upper:
            state.pulse_direction = (state.pulse_direction + 1) & 255
    else:
        state.pulse = (state.pulse - instrument.pulse_step) & 4095
        if state.pulse >> 8 < instrument.pulse_lower:
            state.pulse_direction = (state.pulse_direction - 1) & 255
    filter_allowed, path = True, 'table'
    if not pitch_stage(state, instrument, programs):
        path = 'hold'
        if state.age and state.glide_step:
            target = frequency(programs.frequencies, state.glide_target)
            if state.glide_target >= state.base_note:
                state.frequency = (state.frequency + state.glide_step) & 65535
                path = 'glide-up'
                if state.frequency > target:
                    state.frequency, state.glide_step = target, 0
                    filter_allowed, path = False, 'glide-up-clamp'
            else:
                state.frequency = (state.frequency - state.glide_step) & 65535
                filter_allowed, path = False, 'glide-down'
                if state.frequency <= target:
                    state.frequency, state.glide_step = target, 0
                    path = 'glide-down-clamp'
        elif state.age and (state.base_note >= 128 or
                           (instrument.vibrato_delay and instrument.vibrato_delay < state.age)):
            direction = -1 if instrument.vibrato_half >= state.vibrato_phase else 1
            state.frequency = (state.frequency + direction * instrument.vibrato_step) & 65535
            state.vibrato_phase = (state.vibrato_phase + 1) & 255
            if instrument.vibrato_period < state.vibrato_phase:
                state.vibrato_phase = 1
            path = 'vibrato'
    writes = []
    if filter_allowed:
        require(len(programs.routing_set) == len(programs.routing_clear) == 3, 'Routing masks require three voices')
        set_mask, clear_mask = programs.routing_set[voice], programs.routing_clear[voice]
        unsigned(set_mask, 255, 'Routing set mask')
        unsigned(clear_mask, 255, 'Routing clear mask')
        if instrument.filter_enabled:
            shared.mode = instrument.filter_mode
            shared.cutoff = (shared.cutoff - instrument.filter_step) & 255
            writes.append((0xd416, shared.cutoff))
            shared.routing |= set_mask
        else:
            shared.routing &= clear_mask
        writes.append((0xd417, shared.routing))
        if state.remaining == 0 and divider == 1 and state.hold == 0:
            state.gate_mask = 254
    writes.extend(voice_output(state, voice))
    return SoundResult(state, shared, writes, path)


def advance_age(state):
    validate_state(state, VoiceState, WORD_FIELDS)
    state = replace(state)
    if state.age < 128:
        state.age += 1
    return state


def global_output(shared, volume=11):
    validate_state(shared, FilterState)
    unsigned(volume, 15, 'Master volume')
    return [(0xd418, shared.mode | volume)]
