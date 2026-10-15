"""Compute Ghostbusters patch setup, gate release, vibrato and shared volume.

Voice indices 0..2 mean physical SID voices 1..3. The score owns note, header,
remaining duration and instrument selection; these helpers own only the cached
control returned by onset. The caller processes voices 2→0, emits a flagged
row's volume before onset, and advances the shared phase after the whole body.
No source executable, speech bytes, captured stores or analogue state is used.
"""

from collections.abc import Mapping
from dataclasses import dataclass, fields


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unsigned(value, maximum, name):
    require(type(value) is int and 0 <= value <= maximum,
        f'{name} must be an unsigned integer <= {maximum}')


@dataclass(frozen=True)
class Patch:
    pulse_low: int = 0
    pulse_high: int = 0
    control: int = 0
    attack_decay: int = 0
    sustain_release: int = 0
    vibrato_shift: int = 0


@dataclass(frozen=True)
class VoiceInputs:
    note: int = 0
    header: int = 0
    remaining: int = 0
    cached_control: int = 0


@dataclass(frozen=True)
class SoundResult:
    cached_control: int
    writes: list
    path: str


def validate(inputs, patch, frequencies, voice, mute):
    require(isinstance(inputs, VoiceInputs), 'Expected VoiceInputs')
    require(isinstance(patch, Patch), 'Expected Patch')
    for value in (inputs, patch):
        for item in fields(value):
            unsigned(getattr(value, item.name), 255, item.name)
    require(isinstance(frequencies, Mapping), 'Frequency lookup must be a numeric mapping')
    unsigned(voice, 2, 'Voice index')
    unsigned(mute, 255, 'Mute byte')


def frequency(frequencies, index):
    require(index in frequencies, f'Missing frequency index {index}')
    value = frequencies[index]
    unsigned(value, 65535, 'Frequency word')
    return value


def onset(inputs, patch, frequencies, voice, mute=0):
    """Set the gated control cache even when a rest/mute suppresses its gate.

    Source $94EA stores the unmasked patch control; $94CB masks only the SID
    store. Frequency is written high/low before control/PW/AD/SR, with no
    separate control-zero retrigger. The routine at $9593 loads its immediate
    mute operand at $9594 (source $A1F2).
    """
    validate(inputs, patch, frequencies, voice, mute)
    base = 0xd400 + voice * 7
    rest = bool(inputs.header & 64)
    writes = []
    if not rest:
        word = frequency(frequencies, inputs.note & 127)
        if not mute:
            writes.extend(((base + 1, word >> 8), (base, word & 255)))
    if not mute:
        writes.extend(((base + 4, patch.control & (254 if rest else 255)),
            (base + 2, patch.pulse_low), (base + 3, patch.pulse_high),
            (base + 5, patch.attack_decay), (base + 6, patch.sustain_release)))
    path = 'rest' if rest else 'note'
    return SoundResult(patch.control, writes, 'muted-' + path if mute else path)


def body(inputs, patch, frequencies, voice, phase, mute=0):
    """Apply quarter-step release before continuing pitch, preserving the cache.

    Source $9411 bypasses an inactive voice only on quarter steps. $9510 leaves
    the software control unchanged; $9519/$951C zero envelopes at remaining
    zero. $9562 tests original header duration, not pitch, for displacement.
    """
    validate(inputs, patch, frequencies, voice, mute)
    unsigned(phase, 255, 'Shared phase')
    quarter = phase & 3 == 0
    if quarter and inputs.remaining & 128:
        return SoundResult(inputs.cached_control, [], 'inactive-quarter')
    base = 0xd400 + voice * 7
    writes = []
    release = quarter and not inputs.header & 32
    if release and not mute:
        writes.append((base + 4, inputs.cached_control & 254))
        if inputs.remaining == 0:
            writes.extend(((base + 5, 0), (base + 6, 0)))
    if patch.vibrato_shift:
        index = inputs.note & 127
        word = frequency(frequencies, index)
        adjacent = frequency(frequencies, index + 1)
        # $954E branches on signed DEC: shifts 129..255 exit after one shift.
        shifts = patch.vibrato_shift + 1 if patch.vibrato_shift <= 128 else 1
        step = ((adjacent - word) & 65535) >> shifts
        multiplier = phase & 7
        if multiplier >= 4:
            multiplier ^= 7
        if inputs.header & 31 >= 5:
            word = (word + multiplier * step) & 65535
        if not mute:
            writes.extend(((base, word & 255), (base + 1, word >> 8)))
    path = 'release' if release else 'steady'
    if patch.vibrato_shift:
        path = 'release-vibrato' if release else 'vibrato'
    return SoundResult(inputs.cached_control, writes, 'muted-body' if mute else path)


def volume_write(nibble, voice0_order_cursor, half=False):
    """Compute the row's shared volume using voice zero's current order cursor.

    Source $946E/$9471 subtracts from $6D before clamping; cursor overflow uses
    byte arithmetic. $947F halves the resulting value only in the optional
    nonzero mode. The caller preserves descending-voice ordering at $9486.
    """
    unsigned(nibble, 15, 'Volume nibble')
    unsigned(voice0_order_cursor, 255, 'Voice-zero order cursor')
    require(type(half) is bool, 'Half-volume flag must be boolean')
    volume = min(15, (109 - voice0_order_cursor) & 255) if nibble == 15 else nibble
    return [(0xd418, volume >> 1 if half else volume)]
