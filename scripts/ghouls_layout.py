"""Declare the independent Ghouls sound module's named byte-array ABI."""

from collections.abc import Mapping
from dataclasses import fields

from ghouls_programs import (FILTER_WORD_FIELDS, VOICE_WORD_FIELDS, FilterState,
                            VoiceState, validate_filter_state, validate_lookup,
                            validate_voice, validate_voice_state)


def _field_labels(state_type, prefix, word_fields):
    return {field.name: ((prefix + field.name + '_lo', prefix + field.name + '_hi')
                        if field.name in word_fields else (prefix + field.name,))
            for field in fields(state_type)}


VOICE_FIELD_LABELS = _field_labels(VoiceState, 'gh_', VOICE_WORD_FIELDS)
FILTER_FIELD_LABELS = _field_labels(FilterState, 'gh_filter_', FILTER_WORD_FIELDS)
SOUND_STATE_STORAGE = (
    tuple((label, 3) for labels in VOICE_FIELD_LABELS.values() for label in labels)
    + tuple((label, 1) for labels in FILTER_FIELD_LABELS.values() for label in labels)
    + (('gh_filter_restart_phase', 3), ('gh_pulse_fallback_lo', 3), ('gh_pulse_fallback_hi', 3)))
SOUND_TABLE_STORAGE = (('gh_frequency_lo', 256), ('gh_frequency_hi', 256), ('gh_sid_offsets', 3))
SOUND_SCRATCH_STORAGE = (('gh_sound_tmp', 1), ('gh_filter_attempts', 1), ('gh_filter_failed', 1))
SOUND_STORAGE = SOUND_STATE_STORAGE + SOUND_TABLE_STORAGE + SOUND_SCRATCH_STORAGE


def _three(values, maximum, name):
    if values is None:
        return [0, 0, 0]
    values = list(values)
    if len(values) != 3 or any(type(value) is not int or not 0 <= value <= maximum for value in values):
        raise ValueError(f'{name} requires three unsigned values in 0..{maximum}')
    return values


def sound_values(voice_states=None, filter_state=None, frequency_words=None,
                 filter_restart_phases=None, pulse_fallbacks=None):
    """Return numeric state, immutable tables and scratch by their ABI labels.

    Missing numeric frequency words encode as zero; the composition compiler
    must validate every accessed index before admitting the compiled player.
    SOUND_STATE_STORAGE identifies the cold image to restore on initialization.
    """
    states = [VoiceState() for _ in range(3)] if voice_states is None else list(voice_states)
    if len(states) != 3:
        raise ValueError('Sound initialization requires three voice states')
    states = [VoiceState(**state) if isinstance(state, dict) else state for state in states]
    for state in states:
        validate_voice_state(state)
    shared = FilterState() if filter_state is None else filter_state
    if isinstance(shared, dict):
        shared = FilterState(**shared)
    validate_filter_state(shared)
    lookup = {} if frequency_words is None else frequency_words
    validate_lookup(lookup)
    values = {}
    for field, labels in VOICE_FIELD_LABELS.items():
        for half, label in enumerate(labels):
            values[label] = [(getattr(state, field) >> (8 * half)) & 255 for state in states]
    for field, labels in FILTER_FIELD_LABELS.items():
        for half, label in enumerate(labels):
            values[label] = [(getattr(shared, field) >> (8 * half)) & 255]
    values['gh_filter_restart_phase'] = _three(filter_restart_phases, 255, 'Filter restart phases')
    fallbacks = _three(pulse_fallbacks, 65535, 'Pulse fallbacks')
    values['gh_pulse_fallback_lo'] = [word & 255 for word in fallbacks]
    values['gh_pulse_fallback_hi'] = [word >> 8 for word in fallbacks]
    if isinstance(lookup, Mapping):
        words = [lookup.get(index, 0) for index in range(256)]
    else:
        words = list(lookup) + [0] * (256 - len(lookup))
    for half, label in enumerate(('gh_frequency_lo', 'gh_frequency_hi')):
        values[label] = [(word >> (8 * half)) & 255 for word in words]
    values['gh_sid_offsets'] = [0, 7, 14]
    for label, size in SOUND_STORAGE:
        values.setdefault(label, [0] * size)
    return values


def sound_declarations(voice_states=None, filter_state=None, frequency_words=None,
                       filter_restart_phases=None, pulse_fallbacks=None):
    """Emit the numeric sound ABI in its declared storage order."""
    values = sound_values(voice_states, filter_state, frequency_words, filter_restart_phases, pulse_fallbacks)
    return ''.join(label + ':\n  .byte ' + ','.join(f'${value:02x}' for value in values[label]) + '\n'
                   for label, size in SOUND_STORAGE)


def _read_state(memory, symbols, field_labels, state_type, index):
    return state_type(**{field: sum(memory[symbols[label] + index] << (8 * half)
                                   for half, label in enumerate(labels))
                         for field, labels in field_labels.items()})


def _store_state(memory, symbols, field_labels, state, index):
    for field, labels in field_labels.items():
        for half, label in enumerate(labels):
            memory[symbols[label] + index] = (getattr(state, field) >> (8 * half)) & 255


def read_voice_state(memory, symbols, voice):
    validate_voice(voice)
    return _read_state(memory, symbols, VOICE_FIELD_LABELS, VoiceState, voice)


def store_voice_state(memory, symbols, voice, state):
    validate_voice(voice)
    validate_voice_state(state)
    _store_state(memory, symbols, VOICE_FIELD_LABELS, state, voice)


def read_filter_state(memory, symbols):
    return _read_state(memory, symbols, FILTER_FIELD_LABELS, FilterState, 0)


def store_filter_state(memory, symbols, state):
    validate_filter_state(state)
    _store_state(memory, symbols, FILTER_FIELD_LABELS, state, 0)
