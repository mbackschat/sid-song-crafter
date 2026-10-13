"""Compute the numeric Monty title player independently of its original driver."""

from copy import deepcopy
from dataclasses import asdict

from monty_title_score import expand_score
from monty_title_programs import Instrument, VoiceState, PitchLookups, initialize_note, advance_body


SOUND_FIELDS = ('note', 'control', 'remaining', 'held_frequency', 'voice_control',
                'pulse_delay', 'pulse_direction', 'portamento')
SEQUENCE_FIELDS = ('note', 'control', 'remaining', 'portamento', 'instrument_index',
                   'order_cursor', 'pattern_cursor')
GLOBAL_FIELDS = ('tempo_countdown', 'tempo_reload', 'counter', 'status', 'mode_volume',
                 'sfx_priority', 'sfx_flags', 'output_enable')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def integer(value, limit, name):
    require(type(value) is int and 0 <= value <= limit, f'{name} must be in 0..{limit}')


def voice_state(voice):
    return VoiceState(**{name: voice[name] for name in SOUND_FIELDS})


def alias_bindings(rows):
    result = {}
    for row in rows:
        offset, voice, field = row['offset'], row['voice_index'], row['field']
        integer(offset, 257, 'Alias offset')
        integer(voice, 2, 'Alias voice')
        require(offset >= 192 and offset not in result, 'Alias offsets must be unique and beyond the 96-word table')
        require(field in SOUND_FIELDS and field != 'held_frequency', 'Alias must name a per-voice byte field')
        result[offset] = (voice, field)
    return result


def lookup_word(offset, frequencies, aliases, voices):
    def byte_at(index):
        if index < 192:
            return (frequencies[index // 2] >> (8 if index & 1 else 0)) & 255
        require(index in aliases, f'Unsupported unmapped frequency alias byte {index}')
        voice, field = aliases[index]
        return voices[voice][field]

    return byte_at(offset) | byte_at(offset + 1) << 8


def synchronize(voice, action):
    for name in SEQUENCE_FIELDS:
        if name in action:
            voice[name] = action[name]


def ending_contract(description, declared_calls):
    if 'ending' not in description:
        return None
    ending = description['ending']
    require(isinstance(ending, dict), 'Ending must contain named numeric timing')
    start = ending.get('start_call')
    integer(start, declared_calls, 'Ending start_call')
    require(start > 0, 'Ending requires a nonempty music prefix')
    for name, expected in (('release_calls', 64), ('fade_step_calls', 4)):
        require(type(ending.get(name)) is int and ending[name] == expected,
                f'Ending {name} must be {expected}')
    require(declared_calls == start + 128, 'Ending total must equal start_call + 128')
    return ending


def compute_player(description, *, calls=None):
    """Return ordered SID stores, named final state and shared instrument records.

    Numeric order/pattern expansion owns score timing and voice order. Shared
    mutable instrument widths and per-voice synthesis state survive note,
    append and order restarts. Typed aliases resolve current named fields at
    each pitch stage; unmapped adjacent bytes reject rather than becoming
    guessed pitches. Source annotations and captured events are ignored.

    The optional call cap is exclusive and cannot exceed declared play_calls.
    An optional ending freezes score and tempo at start_call, clears actual
    control gates, advances continuing programs for 64 release calls, then
    fades volume 15..0 with four calls per level. Saved control bytes retain
    pitch-alias semantics; tail output masks every control gate. The declared
    limit is start_call+128 and stopped is true only after that finite tail.
    Only the title's enabled negative output context is supported. Sound
    overlays and FE/negative-status transport exits reject. This models
    ordered values, not CPU cycles, SID internals or audible recurrence.
    """
    require(description['format'] == 'monty-editable-title-v1', 'Unsupported Monty description')
    declared_calls = description['play_calls']
    integer(declared_calls, 100000, 'play_calls')
    ending = ending_contract(description, declared_calls)
    calls = declared_calls if calls is None else calls
    integer(calls, declared_calls, 'calls')
    initial = deepcopy(description['initial_state'])
    globals_, voices = initial['globals'], initial['voices']
    require(len(voices) == 3, 'Initial state requires three voices')
    for name in GLOBAL_FIELDS:
        integer(globals_[name], 255, name)
    require(globals_['sfx_priority'] == 0 and globals_['sfx_flags'] == 255
            and globals_['output_enable'] & 128, 'Unsupported sound overlay/output context')
    if ending is not None:
        require(globals_['mode_volume'] & 15 == 15, 'Finite ending requires initial volume 15')
    bank = [Instrument(**{name: row[name] for name in Instrument.__dataclass_fields__})
            for row in description['instruments']]
    require(0 < len(bank) <= 32, 'Instrument bank requires 1..32 records')
    for instrument in bank:
        for name, value in asdict(instrument).items():
            integer(value, 65535 if name == 'pulse_word' else 255, name)
    for voice in voices:
        for name in set(SOUND_FIELDS) | set(SEQUENCE_FIELDS):
            integer(voice[name], 65535 if name == 'held_frequency' else 255, name)
        require(voice['instrument_index'] < len(bank), 'Initial instrument is outside the numeric bank')
    frequencies = description['frequency_words']
    require(isinstance(frequencies, (list, tuple)) and len(frequencies) == 96,
            'The declared frequency table requires 96 words')
    for value in frequencies:
        integer(value, 65535, 'Frequency')
    aliases = alias_bindings(description['frequency_alias_bindings'])
    score_calls = calls if ending is None else min(calls, ending['start_call'])
    expanded = expand_score(description['score'], calls=score_calls, initial_state=initial)
    writes = [dict(phase='init', tick=None, address=address, value=0)
              for address in (0xd404, 0xd40b, 0xd412)]
    counter = globals_['counter']
    actual_controls = [0, 0, 0]

    def emit(call, index, relative_writes, *, release=False):
        for offset, value in relative_writes:
            if offset == 4:
                value &= 254 if release else 255
                actual_controls[index] = value
            writes.append(dict(phase='play', tick=call, address=0xd400 + 7 * index + offset, value=value))

    def program(index, *, initialize=False, append=False, release_check=False):
        voice = voices[index]
        record_index = voice['instrument_index']
        require(record_index < len(bank), 'Selected instrument is outside the numeric bank')
        instrument, state = bank[record_index], voice_state(voice)
        offset = (state.note * 2) & 255
        if initialize:
            if append:
                step = initialize_note(state, instrument, append=True)
            else:
                frequency = lookup_word(offset, frequencies, aliases, voices)
                step = initialize_note(state, instrument, note=state.note, frequency_word=frequency)
        else:
            base = lookup_word(offset, frequencies, aliases, voices) if instrument.vibrato_depth else 0
            adjacent = lookup_word(offset + 2, frequencies, aliases, voices) if instrument.vibrato_depth else 0

            def octave_resolver(current, updated_record):
                voice.update(asdict(current))
                bank[record_index] = updated_record
                note = (current.note + (12 if counter & 1 else 0)) & 255
                return lookup_word((note * 2) & 255, frequencies, aliases, voices)

            step = advance_body(state, instrument, PitchLookups(base, adjacent, 0),
                                counter=counter, release_check=release_check,
                                octave_resolver=octave_resolver)
        voice.update(asdict(step.state))
        bank[record_index] = step.instrument
        return step.writes

    for action in expanded['operations']:
        call, kind = action['call'], action['operation']
        if kind == 'call':
            writes.append(dict(phase='play', tick=call, address=0xd418, value=globals_['mode_volume']))
            counter = action['counter']
            for name in ('counter', 'tempo_countdown', 'status'):
                globals_[name] = action[name]
            if action['reset_sequence']:
                for voice in voices:
                    voice.update(note=0, remaining=0, order_cursor=0, pattern_cursor=0)
            continue
        if kind == 'tail':
            continue
        index = action['voice_index']
        voice = voices[index]
        synchronize(voice, action)
        if kind in ('row', 'instrument', 'portamento', 'note', 'navigation', 'orderRestart'):
            continue
        require(kind in ('initialize', 'body'), f'Unsupported numeric score operation {kind}')
        emit(call, index, program(index, initialize=kind == 'initialize',
                                 append=action.get('append', False),
                                 release_check=action.get('score_tick', False)))

    if ending is not None:
        start = ending['start_call']
        mode = globals_['mode_volume'] & 240
        for call in range(start, calls):
            counter = (counter + 1) & 255
            globals_['counter'] = counter
            volume = 15 if call < start + 64 else 15 - (call - start - 64) // 4
            globals_['mode_volume'] = mode | volume
            writes.append(dict(phase='play', tick=call, address=0xd418, value=globals_['mode_volume']))
            if call == start:
                for index in (2, 1, 0):
                    emit(call, index, ((4, actual_controls[index]),), release=True)
            for index in (2, 1, 0):
                emit(call, index, program(index), release=True)
    return dict(writes=writes, finalState=initial, instruments=[asdict(row) for row in bank],
                stopped=ending is not None and calls == declared_calls)


def compute_writes(description, *, calls=None):
    """Return the ordered init/play stores from the numeric title player."""
    return compute_player(description, calls=calls)['writes']
