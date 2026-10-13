"""Compute editable Flashdance waveform, pulse and shared-filter programs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path


class PitchMode(str, Enum):
    RELATIVE = 'relative'
    ABSOLUTE = 'absolute'


def _integer(value, label, maximum, minimum=0):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'{label} must be an integer in {minimum}..{maximum}')


def _fields(value, model, required=None):
    allowed = set(model.__dataclass_fields__)
    required = allowed if required is None else required
    if type(value) is not dict or set(value) - allowed or required - set(value):
        raise ValueError(f'Invalid {model.__name__} fields')


def _bank(value, label, maximum):
    if type(value) is not dict:
        raise ValueError(f'{label} must be a row mapping')
    result = {}
    for key, row in value.items():
        if type(key) is str and key.isdecimal():
            index = int(key)
        elif type(key) is int:
            index = key
        else:
            raise ValueError(f'Invalid {label} index')
        _integer(index, f'{label} index', maximum)
        if index in result:
            raise ValueError(f'Duplicate {label} index')
        result[index] = row
    return result


def _link(index, rows, label):
    if index not in rows:
        raise ValueError(f'{label} references missing row {index}')


def _pulse_state(value):
    _fields(value, PwmState)
    for name, maximum in (('lower', 15), ('upper', 15), ('step', 255), ('direction', 1),
                          ('row', 63), ('remaining', 63), ('width', 65535)):
        _integer(value[name], f'PWM {name}', maximum)
    return PwmState(**value)


def _filter_state(value):
    _fields(value, FilterState)
    for name, maximum in (('row', 63), ('remaining', 63), ('lower', 255), ('upper', 255),
                          ('step', 255), ('direction', 1), ('cutoff', 255)):
        _integer(value[name], f'Filter {name}', maximum)
    return FilterState(**value)


@dataclass(frozen=True)
class PwmRow:
    lower: int
    upper: int
    step: int
    duration: int
    reset_width: int | None = None
    hold: bool = False


@dataclass
class PwmState:
    lower: int = 0
    upper: int = 0
    step: int = 0
    direction: int = 0
    row: int = 0
    remaining: int = 0
    width: int = 0


@dataclass(frozen=True)
class FilterRow:
    lower: int
    upper: int
    step: int
    duration: int
    reset_cutoff: int | None = None
    hold: bool = False


@dataclass
class FilterState:
    row: int = 0
    remaining: int = 0
    lower: int = 0
    upper: int = 0
    step: int = 0
    direction: int = 0
    cutoff: int = 0


@dataclass(frozen=True)
class WaveRow:
    note: int = 0
    control: int = 0
    mode: PitchMode = PitchMode.RELATIVE
    jump: int | None = None


@dataclass
class VoiceState:
    pwm: PwmState = field(default_factory=PwmState)
    wave_row: int = 0


@dataclass(frozen=True)
class Instrument:
    attack_decay: int
    sustain_release: int
    filter_command: int
    filter_row: int
    pwm_row: int
    wave_row: int


@dataclass(frozen=True)
class VoiceOutput:
    pulse_width: int
    frequency_word: int
    control: int
    absolute_pitch: bool
    note_index: int


@dataclass(frozen=True)
class Programs:
    pwm_rows: dict[int, PwmRow]
    filter_rows: dict[int, FilterRow]
    wave_rows: dict[int, WaveRow]
    frequency_words: tuple[int, ...]
    instruments: dict[int, Instrument]
    filter_owner: int

    def to_dict(self):
        return {
            'pwm_rows': {str(key): asdict(row) for key, row in self.pwm_rows.items()},
            'filter_rows': {str(key): asdict(row) for key, row in self.filter_rows.items()},
            'wave_rows': {str(key): {**asdict(row), 'mode': row.mode.value} for key, row in self.wave_rows.items()},
            'frequency_words': list(self.frequency_words),
            'instruments': {str(key): asdict(value) for key, value in self.instruments.items()},
            'filter_owner': self.filter_owner,
        }

    @classmethod
    def from_dict(cls, value):
        _fields(value, cls)
        _integer(value['filter_owner'], 'Filter owner', 2)
        words = value['frequency_words']
        if type(words) not in (list, tuple) or len(words) != 96:
            raise ValueError('Frequency table must contain 96 words')
        for word in words:
            _integer(word, 'Frequency word', 65535)
        banks = {}
        for name, model, reset_name, bound_maximum, reset_maximum in (
            ('pwm_rows', PwmRow, 'reset_width', 15, 65535),
            ('filter_rows', FilterRow, 'reset_cutoff', 255, 255),
        ):
            bank = {}
            for index, data in _bank(value[name], name, 63).items():
                _fields(data, model, {'lower', 'upper', 'step', 'duration'})
                row = model(**data)
                for field_name, maximum in (('lower', bound_maximum), ('upper', bound_maximum), ('step', 255), ('duration', 63)):
                    _integer(getattr(row, field_name), f'{name} {field_name}', maximum)
                initial = getattr(row, reset_name)
                if initial is not None:
                    _integer(initial, f'{name} {reset_name}', reset_maximum)
                if type(row.hold) is not bool:
                    raise ValueError(f'{name} hold must be a boolean')
                bank[index] = row
            for index, row in bank.items():
                if not row.hold:
                    _link((index + 1) & 63, bank, name)
            banks[name] = bank
        waves = {}
        for index, data in _bank(value['wave_rows'], 'wave_rows', 255).items():
            _fields(data, WaveRow, set())
            row = WaveRow(**{**data, 'mode': PitchMode(data.get('mode', PitchMode.RELATIVE))})
            _integer(row.note, 'Wave note', 126 if row.mode == PitchMode.RELATIVE else 95)
            _integer(row.control, 'Wave control', 255)
            if row.jump is not None:
                _integer(row.jump, 'Wave jump', 255)
                if row.note or row.control or row.mode != PitchMode.RELATIVE:
                    raise ValueError('Wave jumps cannot also select pitch or control')
            waves[index] = row
        for index, row in waves.items():
            target = row.jump if row.jump is not None else (index + 1) & 255
            _link(target, waves, 'Wave program')
            if row.jump is not None and waves[target].jump is not None:
                raise ValueError('Selected Flashdance wave programs cannot contain consecutive jumps')
        instruments = {}
        for index, data in _bank(value['instruments'], 'instruments', 248).items():
            _fields(data, Instrument)
            if index % 8:
                raise ValueError('Instrument keys must be source offsets divisible by eight')
            for name, maximum in (('attack_decay', 255), ('sustain_release', 255), ('filter_command', 255),
                                  ('filter_row', 63), ('pwm_row', 63), ('wave_row', 255)):
                _integer(data[name], f'Instrument {name}', maximum)
            instrument = Instrument(**data)
            if instrument.filter_command & 15 not in (0, 1):
                raise ValueError('Selected Flashdance instruments support only filter command modes zero/one')
            _link(instrument.pwm_row, banks['pwm_rows'], 'Instrument PWM')
            _link(instrument.wave_row, waves, 'Instrument wave')
            if instrument.filter_command & 15:
                _link(instrument.filter_row, banks['filter_rows'], 'Instrument filter')
            instruments[index] = instrument
        return cls(banks['pwm_rows'], banks['filter_rows'], waves, tuple(words), instruments, value['filter_owner'])


@dataclass(frozen=True)
class PreloadedState:
    voices: tuple[VoiceState, ...]
    filter: FilterState
    filter_owner: int

    def to_dict(self):
        return {'voices': [asdict(voice) for voice in self.voices],
                'filter': asdict(self.filter), 'filter_owner': self.filter_owner}

    @classmethod
    def from_dict(cls, value, programs=None):
        _fields(value, cls)
        _integer(value['filter_owner'], 'Preloaded filter owner', 2)
        if type(value['voices']) not in (list, tuple) or len(value['voices']) != 3:
            raise ValueError('Preloaded state must contain three voices')
        voices = []
        for data in value['voices']:
            _fields(data, VoiceState)
            _integer(data['wave_row'], 'Preloaded wave row', 255)
            voice = VoiceState(_pulse_state(data['pwm']), data['wave_row'])
            if programs is not None:
                _link(voice.pwm.row, programs.pwm_rows, 'Preloaded PWM')
                _link(voice.wave_row, programs.wave_rows, 'Preloaded wave')
            voices.append(voice)
        filt = _filter_state(value['filter'])
        if programs is not None:
            _link(filt.row, programs.filter_rows, 'Preloaded filter')
            if value['filter_owner'] != programs.filter_owner:
                raise ValueError('Preloaded and program filter owners disagree')
        return cls(tuple(voices), filt, value['filter_owner'])


def initialize_voice(state: VoiceState, instrument: Instrument, programs: Programs) -> None:
    """Select an instrument without advancing its body or resetting direction.

    PCs $12E9–$130A set the row, countdown and optional packed width. Direction,
    bounds and rate belong to the subsequent row consumption at $1399–$13D1.
    """
    state.wave_row = instrument.wave_row
    state.pwm.row = instrument.pwm_row
    state.pwm.remaining = 0
    initial = programs.pwm_rows[state.pwm.row].reset_width
    if initial is not None:
        state.pwm.width = initial


def advance_pwm(state: PwmState, rows: dict[int, PwmRow]) -> int:
    """Advance row timing and one unsigned 16-bit pulse-width step."""
    if state.remaining:
        state.remaining -= 1
    else:
        row = rows[state.row]
        state.lower, state.upper, state.step, state.remaining = row.lower, row.upper, row.step, row.duration
        if row.reset_width is not None:
            state.width, state.direction = row.reset_width, 0
        if not row.hold:
            state.row = (state.row + 1) & 63
    state.width = (state.width + state.step * (1 if state.direction == 0 else -1)) & 65535
    bound = state.upper if state.direction == 0 else state.lower
    # The original $13F7/$1410 compare only the updated high byte for equality.
    if state.width >> 8 == bound:
        state.direction ^= 1
    return state.width


def advance_voice(state: VoiceState, programs: Programs, *, base_note: int,
                  transpose_bytes: int, fine_tune: int, gate_mask: int = 255) -> VoiceOutput:
    """Compute pulse, unmodulated frequency and control for one body call.

    Fine tuning precedes score-owned vibrato/slide, matching $14FB–$1506.
    Absolute pitch rows bypass score transposition. Gate masks apply after the
    waveform program, so an instrument's release control remains authoritative.
    """
    if transpose_bytes & 1:
        raise ValueError('Selected Flashdance programs require even transpose bytes')
    wave_row = state.wave_row
    row = programs.wave_rows[wave_row]
    if row.jump is not None:
        wave_row = row.jump
        row = programs.wave_rows[wave_row]
        if row.jump is not None:
            raise ValueError('Selected Flashdance waveform programs have no consecutive jumps')
    if row.mode == PitchMode.ABSOLUTE:
        byte_index = (row.note * 2) & 255
    elif row.mode == PitchMode.RELATIVE:
        byte_index = (((row.note + base_note) & 255) * 2 + transpose_bytes) & 255
    else:
        raise ValueError(f'Unsupported pitch mode: {row.mode}')
    note_index = byte_index // 2
    _integer(note_index, 'Resolved frequency table index', len(programs.frequency_words) - 1)
    frequency = (programs.frequency_words[note_index] + fine_tune) & 65535
    width = advance_pwm(state.pwm, programs.pwm_rows)
    state.wave_row = (wave_row + 1) & 255
    return VoiceOutput(width, frequency, row.control & gate_mask, row.mode == PitchMode.ABSOLUTE, note_index)


def initialize_filter(state: FilterState, instrument: Instrument, programs: Programs) -> bool:
    """Select shared-filter rows only when the instrument issues a filter command."""
    if instrument.filter_command & 15 == 0:
        return False
    state.row, state.remaining = instrument.filter_row, 0
    initial = programs.filter_rows[state.row].reset_cutoff
    if initial is not None:
        state.cutoff = initial
    return True


def advance_filter(state: FilterState, programs: Programs) -> int:
    """Advance the shared cutoff once for its declared owner voice.

    Unlike PWM equality, $1485–$1499 reverses at cutoff >= upper when ascending
    and cutoff < lower when descending. Byte wrap occurs before the comparison.
    """
    if state.remaining:
        state.remaining -= 1
    else:
        row = programs.filter_rows[state.row]
        state.lower, state.upper, state.step, state.remaining = row.lower, row.upper, row.step, row.duration
        if row.reset_cutoff is not None:
            state.cutoff, state.direction = row.reset_cutoff, 0
        if not row.hold:
            state.row = (state.row + 1) & 63
    ascending = state.direction == 0
    state.cutoff = (state.cutoff + state.step * (1 if ascending else -1)) & 255
    if (ascending and state.cutoff >= state.upper) or (not ascending and state.cutoff < state.lower):
        state.direction ^= 1
    return state.cutoff


def ram_image(data: bytes) -> list[int]:
    """Load hash-checked reference RAM for research importers and oracle tests."""
    assets = json.loads((Path(__file__).resolve().parents[1] / 'config/local-assets.json').read_text())
    pinned = next(row['sha256'] for row in assets['references'] if row['id'] == 'flashdance')
    if hashlib.sha256(data).hexdigest() != pinned:
        raise ValueError('Flashdance reference differs from the pinned archive')
    load = int.from_bytes(data[8:10], 'big')
    payload = data[int.from_bytes(data[6:8], 'big'):]
    if load == 0:
        load, payload = int.from_bytes(payload[:2], 'little'), payload[2:]
    memory = [0] * 65536
    memory[load:load + len(payload)] = payload
    return memory


def decode_programs(data: bytes) -> Programs:
    """Extract editable table semantics for the selected 1,538-call score form.

    This research importer reads table data, never executes or retains the
    original driver. Serialize its result to remove the reference dependency.
    Instrument $08's unselected high-byte frequency path is outside this scope.
    """
    memory = ram_image(data)
    instruments = {}
    for offset in (0, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0x40):
        ad, sr, frequency_mode, command, filt, pwm, wave = memory[0x1c7b + offset:0x1c82 + offset]
        if frequency_mode:
            raise ValueError('Selected Flashdance instruments require pitch-table frequency mode')
        instruments[offset] = Instrument(ad, sr, command, filt // 4, pwm // 4, wave)
    pwm_rows, filter_rows, wave_rows = {}, {}, {}
    for instrument in instruments.values():
        index = instrument.pwm_row
        while index not in pwm_rows:
            bounds, step, flags, initial = memory[0x1b7b + index * 4:0x1b7f + index * 4]
            width = (initial & 240) | (initial & 15) << 8 if flags & 128 else None
            pwm_rows[index] = PwmRow(bounds >> 4, bounds & 15, step, flags & 63, width, bool(flags & 64))
            if flags & 64:
                break
            index = (index + 1) & 63
        if instrument.filter_command & 15:
            index = instrument.filter_row
            while index not in filter_rows:
                bounds, step, flags, initial = memory[0x1a7b + index * 4:0x1a7f + index * 4]
                filter_rows[index] = FilterRow(bounds & 240, (bounds & 15) << 4, step, flags & 63,
                                               initial if flags & 128 else None, bool(flags & 64))
                if flags & 64:
                    break
                index = (index + 1) & 63
        index = instrument.wave_row
        while index not in wave_rows:
            pitch, control = memory[0x187b + index], memory[0x197b + index]
            if pitch == 127:
                wave_rows[index] = WaveRow(jump=control)
                index = control
            else:
                mode = PitchMode.ABSOLUTE if pitch & 128 else PitchMode.RELATIVE
                wave_rows[index] = WaveRow(pitch & 127, control, mode)
                index = (index + 1) & 255
    frequency_words = tuple(memory[address] | memory[address + 1] << 8 for address in range(0x1628, 0x16e8, 2))
    return Programs(pwm_rows, filter_rows, wave_rows, frequency_words, instruments, memory[0x1a7e])


def decode_preloaded(data: bytes) -> PreloadedState:
    """Decode static body state retained by initialization before calls zero/one."""
    memory = ram_image(data)
    voices = tuple(VoiceState(
        PwmState(*(memory[address + x] for address in (0x1731, 0x1734, 0x1737, 0x173a)),
                 memory[0x173d + x] // 4, memory[0x1740 + x], memory[0x1743 + x] | memory[0x1746 + x] << 8),
        memory[0x1750 + x]) for x in range(3))
    filt = FilterState(memory[0x174d] // 4, memory[0x174e], memory[0x1749], memory[0x174a],
                       memory[0x174b], memory[0x174c], memory[0x174f])
    return PreloadedState(voices, filt, memory[0x1a7e])
