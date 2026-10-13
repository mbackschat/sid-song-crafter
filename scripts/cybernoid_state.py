"""Compute note setup and caller gate/filter decisions without source-file I/O."""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class CallerState:
    row_remaining: int
    row_duration: int
    arpeggio_counter: int
    base_pitch: int
    current_pitch: int
    frequency: int
    held_frequency: int
    held_high_copy: int
    base_wave: int
    wave: int
    pulse_flags: int
    pulse_accumulator: int
    pulse_output: int
    pulse_direction: int
    packed_filter: int
    gate_mask: int
    note_age: int
    vibrato_age: int
    glide_enabled: int
    glide_active: int
    vibrato_direction: int
    vibrato_position: int
    filter_cutoff: int
    pulse_run_flag: int
    pulse_run_low: int
    pulse_run_high: int


def bounded(value, maximum, name):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError(f'{name} must be in 0..{maximum}')


def validate(state):
    for name, value in vars(state).items():
        bounded(value, 65535 if name in ('frequency', 'held_frequency', 'pulse_accumulator', 'pulse_output') else 255, name)


def begin_row(state):
    """A7AF..A7BA runs before score prefixes; subsequent glide commands may enable glide."""
    validate(state)
    return replace(state, glide_enabled=0, glide_active=0, note_age=0, vibrato_age=0)


def begin_voice_call(state):
    """A72A increments age before score dispatch; a selected row subsequently resets it."""
    validate(state)
    return replace(state, note_age=(state.note_age + 1) & 255)


def initialize_note(state, voice, pitch_index, frequency, record, preserve_patch=False):
    """A874..A8EF always writes frequency high then low; patch setup is conditional.

    Current effective pitch A63C is retained here. A96D/A970 later assigns the
    base pitch before arpeggio. The caller handles score peek/end transitions,
    then finishes the row with FF gate mask and skips the synthesis body.
    """
    validate(state)
    bounded(voice, 2, 'voice')
    bounded(pitch_index, 255, 'pitch index')
    bounded(frequency, 65535, 'frequency')
    if type(preserve_patch) is not bool:
        raise ValueError('preserve_patch must be boolean')
    if not isinstance(record, (list, tuple)) or len(record) != 8:
        raise ValueError('record must have eight bytes')
    for value in record:
        bounded(value, 255, 'record byte')
    state = replace(state, row_remaining=state.row_duration, arpeggio_counter=0,
                    base_pitch=pitch_index, frequency=frequency, held_frequency=frequency,
                    held_high_copy=frequency >> 8)
    base = 0xd400 + voice * 7
    writes = [(base + 1, frequency >> 8), (base, frequency & 255)]
    if not preserve_patch:
        state = replace(state, base_wave=record[1], wave=record[1],
                        pulse_flags=record[0], pulse_accumulator=(record[0] & 15) << 8,
                        pulse_output=(record[0] & 15) << 8, pulse_direction=1,
                        packed_filter=record[4])
        writes += [(base + 5, record[2]), (base + 6, record[3])]
    return state, writes


def finish_row(state):
    """A90E/A910 sets the mask after the score-owned peek and goes straight to writer."""
    validate(state)
    return replace(state, gate_mask=255)


def body_prelude(state, voice, record, tempo_countdown, scheduled):
    """Model A916..A977 with the already-decremented remaining count.

    Gate masking runs only on a scheduled non-new row. SR02 eligibility uses
    retained raw pulse flags; gate threshold instead reads current record4.
    Nonscheduled bodies retain the mask. Later drum/onset code may override it.
    """
    validate(state)
    bounded(voice, 2, 'voice')
    bounded(tempo_countdown, 255, 'tempo countdown')
    if type(scheduled) is not bool:
        raise ValueError('scheduled must be boolean')
    if not isinstance(record, (list, tuple)) or len(record) != 8:
        raise ValueError('record must have eight bytes')
    for value in record:
        bounded(value, 255, 'record byte')
    if scheduled:
        threshold = (record[4] & 240) >> 2
        mask = 255 if state.row_remaining > threshold else 254
        state = replace(state, gate_mask=mask)
    writes = [(0xd406 + voice * 7, 2)] if state.pulse_flags & 16 and state.row_remaining == 0 and tempo_countdown == 1 else []
    return replace(state, current_pitch=state.base_pitch), tuple(record[5:8]), writes


def filter_ownership(voice, fx2, fx3, owner, cutoff):
    """Separate AC68..ACE1 owner dispatch from the selected filter arithmetic.

    Fallback retains the remembered owner and D417/D415. It can run again on
    later bodies; it is not a one-shot release. An initialized row skips it.
    """
    bounded(voice, 2, 'voice')
    for value, name in [(fx2, 'fx2'), (fx3, 'fx3'), (owner, 'owner'), (cutoff, 'cutoff')]:
        bounded(value, 255, name)
    if fx3 & 1:
        return voice, cutoff, True, []
    if voice == owner and not fx2 & 8:
        return owner, 128, False, [(0xd418, 31), (0xd416, 128)]
    return owner, cutoff, False, []
