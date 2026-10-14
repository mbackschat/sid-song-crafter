"""Lower numeric sound data into the independent Take On Me assembly ABI."""

from collections.abc import Sequence
from dataclasses import fields

import programs
from player import sound_data as numeric_sound


def field_labels(state_type, prefix, words):
    return {item.name: ((prefix + item.name + '_lo', prefix + item.name + '_hi') if item.name in words else
                       (prefix + item.name,)) for item in fields(state_type)}


VOICE_FIELD_LABELS = field_labels(programs.VoiceState, 'tm_', programs.VOICE_WORDS)
FILTER_FIELD_LABELS = field_labels(programs.FilterState, 'tm_filter_', ('word',))
STATE_STORAGE = (tuple((label, 3) for labels in VOICE_FIELD_LABELS.values() for label in labels)
                 + tuple((label, 1) for labels in FILTER_FIELD_LABELS.values() for label in labels)
                 + (('tm_instrument', 3),))
SCRATCH_STORAGE = tuple((label, 1) for label in (
    'tm_sound_failed', 'tm_table_cursor', 'tm_table_hops',
    'tm_sweep_word_lo', 'tm_sweep_word_hi', 'tm_sweep_initial', 'tm_sweep_direction'))


def sound_state_values(voices, shared):
    """Return three voice arrays and shared filter state for a cold image.

    Score-owned fields use these same arrays. The compiler supplies instrument
    selectors and initial score projections, avoiding a second mutable copy.
    """
    programs.require(len(voices) == 3, 'Sound state requires three voices')
    for voice in voices:
        programs.validate_state(voice, programs.VoiceState, programs.VOICE_WORDS)
    programs.validate_state(shared, programs.FilterState, ('word',))
    values = {label: [(getattr(voice, name) >> (8 * half)) & 255 for voice in voices]
              for name, labels in VOICE_FIELD_LABELS.items() for half, label in enumerate(labels)}
    values.update({label: [(getattr(shared, name) >> (8 * half)) & 255]
                   for name, labels in FILTER_FIELD_LABELS.items() for half, label in enumerate(labels)})
    values['tm_instrument'] = [0, 0, 0]
    return values


def read_state(memory, symbols, labels, state_type, index):
    ram = memory.data if hasattr(memory, 'data') else memory
    return state_type(**{name: sum(ram[symbols[label] + index] << (8 * half) for half, label in enumerate(parts))
                         for name, parts in labels.items()})


def read_voice(memory, symbols, voice):
    programs.validate_voice(voice)
    return read_state(memory, symbols, VOICE_FIELD_LABELS, programs.VoiceState, voice)


def read_filter(memory, symbols):
    return read_state(memory, symbols, FILTER_FIELD_LABELS, programs.FilterState, 0)


def declarations(values):
    result = ''
    for label, items in values.items():
        programs.require(bool(items), f'{label} requires data')
        for value in items:
            if type(value) is int:
                programs.unsigned(value, 255, label)
            else:
                programs.require(type(value) is str, f'{label} requires bytes or pointer tokens')
        result += label + ':\n  .byte ' + ','.join(f'${value:02x}' if type(value) is int else value for value in items) + '\n'
    return result


def sound_tables(description):
    """Return immutable tables and two-pass pointer tokens, without source assets."""
    instruments, bank = numeric_sound(description)
    references, values = {}, {'tm_sid_offsets': [0, 7, 14]}

    def pointer(label, half):
        if label is None:
            return 0
        token = f'TM_SOUND_POINTER_{len(references)}'
        references[token] = label, half * 8
        return token

    size = max(instruments, default=0) + 1
    for item in fields(programs.Instrument):
        for half, suffix in ((0, '_lo'), (1, '_hi')) if item.name in ('pulse', 'filter_word') else ((0, ''),):
            values['tm_i_' + item.name + suffix] = [((getattr(instruments[index], item.name) >> (8 * half)) & 255)
                if index in instruments else 0 for index in range(size)]
    for index, word in bank.frequencies.items():
        programs.unsigned(index, 255, 'Frequency index')
        programs.unsigned(word, 65535, 'Frequency word')
    values['tm_frequency_table_lo'] = [bank.frequencies.get(index, 0) & 255 for index in range(256)]
    values['tm_frequency_table_hi'] = [bank.frequencies.get(index, 0) >> 8 for index in range(256)]
    for prefix, mapping in (('arpeggio', bank.arpeggios), ('waveform', bank.waveforms), ('pitch', bank.pitches),
                            ('pulse', bank.pulses), ('filter', bank.filters)):
        for half, suffix in ((0, 'lo'), (1, 'hi')):
            values[f'tm_{prefix}_ptr_{suffix}'] = [pointer(f'tm_{prefix}_program_{index}' if index in mapping else None, half)
                for index in range(256)]
        for index, program in mapping.items():
            programs.unsigned(index, 255, prefix + ' selector')
            if prefix in ('pulse', 'filter'):
                programs.sweep_step(0, 255, 255, program)
                packed = []
                for item in fields(programs.SweepProgram):
                    value = getattr(program, item.name)
                    packed.extend([value] if item.name in programs.SWEEP_BYTES else [value & 255, value >> 8])
            else:
                programs.require(1 <= len(program) <= 256, 'Sound table requires 1..256 bytes')
                packed = list(program)
                for value in packed:
                    programs.unsigned(value, 255, prefix + ' byte')
            values[f'tm_{prefix}_program_{index}'] = packed
    size = max(bank.vibratos, default=0) + 1
    for item in fields(programs.VibratoProgram):
        values['tm_v_' + item.name] = [getattr(bank.vibratos[index], item.name) if index in bank.vibratos else 0
            for index in range(size)]
    for program in bank.vibratos.values():
        programs.validate_state(program, programs.VibratoProgram)
        programs.require(program.shift <= 16, 'Vibrato shift must be <= 16')
    for program in bank.releases.values():
        programs.require(isinstance(program, Sequence) and len(program) == 2,
                         'Release program must contain gate and SR-zero thresholds')
        for value in program:
            programs.unsigned(value, 255, 'Release threshold')
    size = max(bank.releases, default=0) + 1
    for half, field in ((0, 'gate'), (1, 'sr_zero')):
        values['tm_r_' + field] = [bank.releases[index][half] if index in bank.releases else 0 for index in range(size)]
    return declarations(values), references
