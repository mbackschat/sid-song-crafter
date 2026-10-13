"""Compute the pitch effects decoded from the pinned Flashdance player."""

from dataclasses import dataclass, field


@dataclass
class SlideState:
    enabled: int = 0
    step: int = 0
    subtract: bool = False
    offset: int = 0


@dataclass
class VibratoState:
    """Retain the reload counter separately from its initial partial cycle.

    PCs $1593–$15A3 decrement before testing the sign bit and then reload the
    interval, so subsequent direction changes span interval + 1 body calls.
    """

    enabled: int = 0
    interval: int = 0
    remaining: int = 0
    direction: int = 0
    shift: int = 0
    growth: int = 0
    depth: int = 0
    offset: int = 0


@dataclass
class PitchEffects:
    slide: SlideState = field(default_factory=SlideState)
    vibrato: VibratoState = field(default_factory=VibratoState)


def note_changed(state):
    """Consume the note-scoped enable count without resetting effect history."""
    for effect in (state.slide, state.vibrato):
        if effect.enabled:
            effect.enabled -= 1


def advance_pitch(state, frequency, source_note, frequency_table, *, absolute=False):
    """Advance one body call using editable effect state and a pitch table.

    The pinned driver computes vibrato depth from the untransposed score note
    at $1568, while slide accumulation precedes its absolute-pitch check at
    $1548. Its byte counters and word accumulators wrap independently.
    """
    slide, vibrato = state.slide, state.vibrato
    if slide.enabled:
        signed_step = -slide.step if slide.subtract else slide.step
        slide.offset = (slide.offset + signed_step) & 65535
        return frequency if absolute else (frequency + slide.offset) & 65535
    if not vibrato.enabled:
        return frequency

    delta = (frequency_table[source_note + 1] - frequency_table[source_note]) & 65535
    delta = ((delta + (vibrato.depth << 8)) & 65535) >> vibrato.shift
    vibrato.remaining = (vibrato.remaining - 1) & 255
    if vibrato.remaining & 128:
        vibrato.direction ^= 1
        vibrato.remaining = vibrato.interval
    signed_step = -delta if vibrato.direction else delta
    vibrato.offset = (vibrato.offset + signed_step) & 65535
    vibrato.depth = (vibrato.depth + vibrato.growth) & 255
    return (frequency + vibrato.offset) & 65535
