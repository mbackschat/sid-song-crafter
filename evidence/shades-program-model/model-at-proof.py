"""Compute editable Shades voice modulation and shared-filter state."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path


SOURCE_SHA256 = 'ac7c91d0c4fef41bbc9d9e50840492269151075727efa7182a68dc1a26f1d708'
SOURCE_BLOCK_NAMES = {
    0x56c0: 'silent', 0x5600: 'opening-pulse', 0x5640: 'program-02',
    0x5680: 'program-03', 0x5740: 'program-04', 0x5700: 'program-05',
    0x5780: 'program-06', 0x57c0: 'program-07', 0x4f00: 'program-08',
    0x4f40: 'program-09', 0x4fc0: 'program-10', 0x4f80: 'program-11',
    0x4ec0: 'program-12', 0x6700: 'fade-pulse',
}


class RowKind(str, Enum):
    NOTE = 'note'
    REST = 'rest'
    HOLD = 'hold'


class Gate(str, Enum):
    ON = 'on'
    OFF = 'off'


class PortamentoMode(str, Enum):
    TARGET = 'target'
    DOWN = 'down'
    UP = 'up'


def _integer(value, label, maximum=255):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError(f'{label} must be an integer in 0..{maximum}')


def _fields(value, model):
    if type(value) is not dict or set(value) != set(model.__dataclass_fields__):
        raise ValueError(f'Invalid {model.__name__} fields')


def _enum(value, model):
    if not isinstance(value, str):
        raise ValueError(f'Invalid {model.__name__}')
    return model(value)


def _three(values, label):
    if type(values) not in (list, tuple) or len(values) != 3:
        raise ValueError(f'{label} requires three voices')


@dataclass(frozen=True)
class VoicePatch:
    control: int
    attack_decay: int
    sustain_release: int
    pulse_width: int
    pulse_up_calls: int
    pulse_down_calls: int
    pulse_step: int
    portamento_step: int
    portamento_mode: PortamentoMode
    vibrato_delay: int
    vibrato_extent: int
    vibrato_step: int
    fine_tune: int


@dataclass(frozen=True)
class FilterContour:
    cutoff_low: int
    cutoff_high: int
    up_calls: int
    down_calls: int
    fine_step: int
    coarse_step: int


@dataclass(frozen=True)
class FilterPatch:
    routing: int
    mode_volume: int
    trigger_mask: int
    contour: FilterContour
    percussion_contour: FilterContour
    percussion_mode_volume: int


@dataclass(frozen=True)
class ProgramBlock:
    voices: tuple[VoicePatch, VoicePatch, VoicePatch]
    filter: FilterPatch
    percussion_control: int


def _voice_patch(value):
    _fields(value, VoicePatch)
    for key in set(value) - {'portamento_mode'}:
        _integer(value[key], f'Voice patch {key}', 65535 if key in ('pulse_width', 'portamento_step') else 255)
    return VoicePatch(**{**value, 'portamento_mode': _enum(value['portamento_mode'], PortamentoMode)})


def _contour(value):
    _fields(value, FilterContour)
    for key, item in value.items():
        _integer(item, f'Filter contour {key}')
    return FilterContour(**value)


def _filter_patch(value):
    _fields(value, FilterPatch)
    for key in ('routing', 'mode_volume', 'percussion_mode_volume', 'trigger_mask'):
        _integer(value[key], f'Filter patch {key}')
    if value['trigger_mask'] not in (0, 1, 2, 4):
        raise ValueError('Shades filter trigger must select zero or one voice')
    return FilterPatch(**{**value, 'contour': _contour(value['contour']),
                          'percussion_contour': _contour(value['percussion_contour'])})


@dataclass(frozen=True)
class Programs:
    frequency_words: tuple[int, ...]
    blocks: dict[str, ProgramBlock]

    def to_dict(self):
        return {'frequency_words': list(self.frequency_words),
                'blocks': {name: {**asdict(block), 'voices': [asdict(voice) for voice in block.voices]}
                           for name, block in self.blocks.items()}}

    @classmethod
    def from_dict(cls, value):
        _fields(value, cls)
        words = value['frequency_words']
        if type(words) not in (list, tuple) or len(words) != 96:
            raise ValueError('Shades frequency table requires 96 words')
        for word in words:
            _integer(word, 'Frequency word', 65535)
        if type(value['blocks']) is not dict or not value['blocks']:
            raise ValueError('Shades programs require named blocks')
        blocks = {}
        for name, block in value['blocks'].items():
            if type(name) is not str or not name:
                raise ValueError('Program block name must be a nonempty string')
            _fields(block, ProgramBlock)
            _three(block['voices'], 'Program block')
            _integer(block['percussion_control'], 'Percussion control')
            blocks[name] = ProgramBlock(tuple(_voice_patch(voice) for voice in block['voices']),
                                        _filter_patch(block['filter']), block['percussion_control'])
        return cls(tuple(words), blocks)


@dataclass
class VoiceState:
    frequency: int = 0
    target_frequency: int = 0
    control: int = 0
    attack_decay: int = 0
    sustain_release: int = 0
    pulse_width: int = 0
    pulse_up_calls: int = 0
    pulse_down_calls: int = 0
    pulse_step: int = 0
    portamento_step: int = 0
    portamento_mode: PortamentoMode = PortamentoMode.TARGET
    vibrato_delay: int = 0
    vibrato_extent: int = 0
    vibrato_step: int = 0
    vibrato_phase: int = 0
    last_row: RowKind = RowKind.REST


@dataclass
class FilterState:
    cutoff_low: int = 0
    cutoff_high: int = 0
    up_calls: int = 0
    down_calls: int = 0
    fine_step: int = 0
    coarse_step: int = 0
    routing: int = 0
    mode_volume: int = 0


@dataclass
class State:
    voices: tuple[VoiceState, VoiceState, VoiceState] = field(default_factory=lambda: tuple(VoiceState() for _ in range(3)))
    filter: FilterState = field(default_factory=FilterState)
    percussion_active: bool = False

    def to_dict(self):
        return {**asdict(self), 'voices': [asdict(voice) for voice in self.voices]}

    @classmethod
    def from_dict(cls, value):
        _fields(value, cls)
        _three(value['voices'], 'State')
        if type(value['percussion_active']) is not bool:
            raise ValueError('Percussion active state must be boolean')
        voices = []
        for voice in value['voices']:
            _fields(voice, VoiceState)
            for key in set(voice) - {'portamento_mode', 'last_row'}:
                _integer(voice[key], f'Voice state {key}',
                         65535 if key in ('frequency', 'target_frequency', 'pulse_width', 'portamento_step') else 255)
            voices.append(VoiceState(**{**voice, 'portamento_mode': _enum(voice['portamento_mode'], PortamentoMode),
                                         'last_row': _enum(voice['last_row'], RowKind)}))
        _fields(value['filter'], FilterState)
        for key, item in value['filter'].items():
            _integer(item, f'Filter state {key}')
        return cls(tuple(voices), FilterState(**value['filter']), value['percussion_active'])


@dataclass(frozen=True)
class RowResult:
    write_voice: bool
    initial_control: int | None = None


def load_block(state: State, block: ProgramBlock):
    """Load shared settings and envelope bytes without restarting voice programs."""
    for voice, patch in zip(state.voices, block.voices):
        voice.attack_decay, voice.sustain_release = patch.attack_decay, patch.sustain_release
    state.filter.routing = block.filter.routing
    state.filter.mode_volume = block.filter.mode_volume


def _trigger_filter(state, patch, voice):
    if not patch.trigger_mask & (1 << voice):
        return
    alternate = state.percussion_active and patch.trigger_mask & 1
    contour = patch.percussion_contour if alternate else patch.contour
    for key in ('cutoff_low', 'cutoff_high', 'up_calls', 'down_calls', 'fine_step', 'coarse_step'):
        setattr(state.filter, key, getattr(contour, key))
    state.filter.mode_volume = patch.percussion_mode_volume if alternate else patch.mode_volume


def _reload_modulation(voice, patch):
    for key in ('pulse_step', 'portamento_step', 'portamento_mode', 'vibrato_extent', 'vibrato_step'):
        setattr(voice, key, getattr(patch, key))


def consume_row(state: State, block: ProgramBlock, voice: int, kind: RowKind, *,
                note_index: int | None = None, gate: Gate = Gate.ON,
                programs: Programs | None = None) -> RowResult:
    """Consume a resolved score row; return onset control and deferred writer intent."""
    _integer(voice, 'Voice', 2)
    kind, gate = _enum(kind, RowKind), _enum(gate, Gate)
    if kind == RowKind.NOTE:
        _integer(note_index, 'Resolved frequency table index', 95)
        if not isinstance(programs, Programs):
            raise ValueError('A note requires frequency programs')
    elif note_index is not None or gate != Gate.ON:
        raise ValueError('Rest and hold rows cannot select pitch or gate')
    current, patch = state.voices[voice], block.voices[voice]
    previous = current.last_row
    current.last_row = kind
    if kind == RowKind.HOLD:
        return RowResult(False)
    if kind == RowKind.NOTE:
        word = programs.frequency_words[note_index]
        frequency = (word & 0xff00) | ((word + patch.fine_tune) & 255)
        portamento_enabled = bool(patch.portamento_step & 255)
        if portamento_enabled:
            current.target_frequency = frequency
        if not portamento_enabled or previous != RowKind.HOLD:
            current.frequency = frequency
    if kind == RowKind.REST or gate == Gate.OFF:
        if voice != 1 and previous == RowKind.REST:
            return RowResult(False)
        current.control &= 254
        _reload_modulation(current, patch)
        return RowResult(True)
    if voice == 0:
        state.percussion_active = bool(block.percussion_control and note_index >= 48)
    control = block.percussion_control if voice == 0 and state.percussion_active else patch.control
    current.control = control | 1
    current.pulse_width = patch.pulse_width
    current.pulse_up_calls, current.pulse_down_calls = patch.pulse_up_calls, patch.pulse_down_calls
    current.vibrato_delay = patch.vibrato_delay
    _trigger_filter(state, block.filter, voice)
    _reload_modulation(current, patch)
    return RowResult(True, control)


def advance_portamento(state: State) -> list[tuple[int, int]]:
    """Move current pitch toward its target or through the selected one-way mode."""
    output = []
    for index, voice in enumerate(state.voices):
        step = voice.portamento_step
        if not step & 255:
            continue
        if voice.portamento_mode == PortamentoMode.TARGET:
            if voice.frequency == voice.target_frequency:
                continue
            difference = abs(voice.frequency - voice.target_frequency)
            downward = voice.frequency > voice.target_frequency
            # $70AC–$70BC reverses the equal-high-byte low comparison on descent.
            # The executed source fixture in shades_programs_test.py retains it.
            snap = difference < step
            if downward:
                difference_high, step_high = difference >> 8, step >> 8
                snap = (difference_high < step_high or
                        difference_high == step_high and (difference & 255) >= (step & 255))
            if snap:
                voice.frequency = voice.target_frequency
                voice.vibrato_delay &= 253
            else:
                direction = 1 if voice.frequency < voice.target_frequency else -1
                voice.frequency = (voice.frequency + direction * step) & 65535
                voice.vibrato_delay |= 2
        elif voice.portamento_mode == PortamentoMode.DOWN:
            voice.frequency = (voice.frequency - step) & 65535
            voice.vibrato_delay |= 2
        elif voice.portamento_mode == PortamentoMode.UP:
            voice.frequency = (voice.frequency + step) & 65535
            voice.vibrato_delay |= 2
        else:
            raise ValueError('Unsupported portamento mode')
        output.append((index, voice.frequency))
    return output


def advance_vibrato(state: State) -> list[tuple[int, int]]:
    """Advance byte-phase vibrato, retaining both delayed-return pitch writes."""
    output = []

    def move(index, voice, direction):
        voice.frequency = (voice.frequency + direction * voice.vibrato_step) & 65535
        voice.target_frequency = voice.frequency
        voice.vibrato_phase = (voice.vibrato_phase + 1) & 255
        output.append((index, voice.frequency))

    for index, voice in enumerate(state.voices):
        if not voice.vibrato_extent:
            continue
        if voice.vibrato_delay:
            voice.vibrato_delay = (voice.vibrato_delay - 1) & 255
            if not voice.vibrato_delay:
                move(index, voice, -1)
                move(index, voice, -1)
                voice.vibrato_phase = 0
        elif voice.vibrato_phase & 128:
            move(index, voice, -1)
        elif voice.vibrato_phase < voice.vibrato_extent:
            move(index, voice, 1)
        else:
            voice.vibrato_phase = (-voice.vibrato_extent) & 255
    return output


def advance_filter(state: State) -> bool:
    """Advance the single shared contour; its low-byte carry threshold is seven."""
    filt = state.filter
    if filt.up_calls:
        filt.up_calls -= 1
        filt.cutoff_low = (filt.cutoff_low + filt.fine_step) & 255
        if filt.cutoff_low >= 7:
            filt.cutoff_low &= 7
            filt.cutoff_high = (filt.cutoff_high + filt.coarse_step) & 255
    elif filt.down_calls:
        filt.down_calls -= 1
        difference = filt.cutoff_low - filt.fine_step
        filt.cutoff_low = difference & 255
        if difference < 0:
            filt.cutoff_low &= 7
            if filt.cutoff_high >= filt.coarse_step:
                filt.cutoff_high -= filt.coarse_step
    else:
        return False
    return True


def advance_pulse(state: State) -> list[tuple[int, int]]:
    """Emit all ascents before descents, including the same-call counter crossing."""
    output = []
    for index, voice in enumerate(state.voices):
        if voice.pulse_up_calls:
            voice.pulse_width = (voice.pulse_width + voice.pulse_step) & 65535
            voice.pulse_up_calls -= 1
            output.append((index, voice.pulse_width))
    for index, voice in enumerate(state.voices):
        if not voice.pulse_up_calls and voice.pulse_down_calls and voice.pulse_width >= voice.pulse_step:
            voice.pulse_width = (voice.pulse_width - voice.pulse_step) & 65535
            voice.pulse_down_calls -= 1
            output.append((index, voice.pulse_width))
    return output


def ram_image(data: bytes) -> list[int]:
    """Load the hash-pinned source for importing parameters, never for playback."""
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('Shades importer requires the pinned corrected source')
    offset = int.from_bytes(data[6:8], 'big')
    base = int.from_bytes(data[offset:offset + 2], 'little')
    memory = [0] * 65536
    payload = data[offset + 2:]
    memory[base:base + len(payload)] = payload
    return memory


def _word(memory, address):
    return memory[address] | memory[address + 1] << 8


def _source_mode(value):
    try:
        return (PortamentoMode.TARGET, PortamentoMode.DOWN, PortamentoMode.UP)[value]
    except (IndexError, TypeError) as error:
        raise ValueError('Unsupported source portamento mode') from error


def decode_programs(data: bytes) -> Programs:
    memory, blocks = ram_image(data), {}
    for address, name in SOURCE_BLOCK_NAMES.items():
        row = memory[address:address + 64]
        voices = tuple(VoicePatch(row[voice], row[3 + voice * 2], row[4 + voice * 2],
                                  row[35 + voice * 2] | row[36 + voice * 2] << 8,
                                  row[41 + voice], row[44 + voice], row[47 + voice],
                                  row[15 + voice * 2] | row[16 + voice * 2] << 8,
                                  _source_mode(row[60 + voice]), row[27 + voice], row[24 + voice],
                                  row[21 + voice], row[57 + voice] if voice else 0)
                       for voice in range(3))
        filt = FilterPatch(row[9], row[10], row[32],
                           FilterContour(row[12], row[13], row[30], row[31], row[33], row[34]),
                           FilterContour(row[51], row[52], row[53], row[54], row[55], row[56]), row[57])
        blocks[name] = ProgramBlock(voices, filt, row[11])
    programs = Programs(tuple(memory[0x73cf + index] | memory[0x7370 + index] << 8 for index in range(96)), blocks)
    return Programs.from_dict(programs.to_dict())


def state_from_memory(memory: list[int]) -> State:
    """Translate diagnostic RAM to named state for independent transition oracles."""
    voices = []
    for index in range(3):
        base = 0x733e + index * 7
        raw_row = memory[0x0371 + index]
        kind = RowKind.REST if raw_row == 0 else RowKind.HOLD if raw_row == 128 else RowKind.NOTE
        voices.append(VoiceState(_word(memory, base), _word(memory, 0x7357 + index * 7), memory[base + 4],
                                 memory[base + 5], memory[base + 6], _word(memory, base + 2),
                                 memory[0x0361 + index], memory[0x0364 + index], memory[0x0367 + index],
                                 _word(memory, 0x0346 + index * 2), _source_mode(memory[0x0374 + index]),
                                 memory[0x0351 + index], memory[0x0354 + index], memory[0x0357 + index],
                                 memory[0x035a + index], kind))
    filt = FilterState(memory[0x7353], memory[0x7354], memory[0x035d], memory[0x035e],
                       memory[0x035f], memory[0x0360], memory[0x7355], memory[0x7356])
    return State(tuple(voices), filt, bool(memory[0x0370]))


def decode_preloaded(data: bytes) -> State:
    return State.from_dict(state_from_memory(ram_image(data)).to_dict())


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sid', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = args.sid.read_bytes()
    description = {'format': 'sid-shades-programs-v1', 'programs': decode_programs(data).to_dict(),
                   'preloaded': decode_preloaded(data).to_dict(),
                   'sourceEvidence': {'sha256': SOURCE_SHA256,
                                      'archiveUrl': 'https://www.hvsc.de/download/C64Music/MUSICIANS/H/Huelsbeck_Chris/Shades_filter_corrected.sid',
                                      'blockNamesByImportAddress': {f'{address:04x}': name for address, name in SOURCE_BLOCK_NAMES.items()},
                                      'scope': 'Executed selected 24385-call traversal; source addresses are import provenance only.'}}
    with args.output.open('x') as output:
        json.dump(description, output, indent=2)
        output.write('\n')


if __name__ == '__main__':
    main()
