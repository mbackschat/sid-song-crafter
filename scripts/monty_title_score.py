"""Expand editable Monty title orders and rows without a source driver."""

from copy import deepcopy
from enum import Enum


SEQUENCE_FIELDS = ('order_cursor', 'pattern_cursor', 'remaining', 'control',
                   'note', 'instrument_index', 'portamento')
GLOBAL_FIELDS = ('tempo_countdown', 'tempo_reload', 'counter', 'status')


class RowKind(Enum):
    NOTE = 0
    PARAMETER = 1
    APPEND = 2


def require(ok, message):
    if not ok:
        raise ValueError(message)


def integer(value, limit, name):
    require(type(value) is int and 0 <= value <= limit,
            f'{name} must be an integer in 0..{limit}')
    return value


def row_kind(control):
    if control & 0x40:
        return RowKind.APPEND
    return RowKind.PARAMETER if control & 0x80 else RowKind.NOTE


def numeric_bytes(row, name):
    values = row.get('bytes')
    require(isinstance(values, (list, tuple)) and 0 < len(values) <= 256,
            f'{name} requires 1..256 bytes')
    return tuple(integer(value, 255, name) for value in values)


def numeric_tables(score):
    require(isinstance(score, dict), 'Score must contain numeric orders and patterns')
    patterns = {}
    for row in score.get('patterns', ()):
        pattern_id = integer(row.get('pattern_id'), 253, 'Pattern ID')
        require(pattern_id not in patterns, f'Duplicate pattern {pattern_id}')
        values = numeric_bytes(row, f'Pattern {pattern_id}')
        offset = 0
        while offset < len(values) and values[offset] != 255:
            kind = row_kind(values[offset])
            size = {RowKind.APPEND: 1, RowKind.PARAMETER: 3, RowKind.NOTE: 2}[kind]
            require(offset + size < len(values),
                    f'Pattern {pattern_id} row at {offset} has missing operands or end peek')
            offset += size
        require(offset > 0 and offset == len(values) - 1 and values[offset] == 255,
                f'Pattern {pattern_id} requires rows followed by one terminal FF')
        patterns[pattern_id] = values
    require(patterns, 'Score requires numeric patterns')
    orders = {}
    for row in score.get('orders', ()):
        voice = integer(row.get('voice_index'), 2, 'Order voice')
        require(voice not in orders, f'Duplicate order voice {voice}')
        values = numeric_bytes(row, f'Order voice {voice}')
        require(254 not in values, 'Unsupported FE transport exit in title orders')
        for value in values:
            require(value == 255 or value in patterns,
                    f'Order voice {voice} selects absent pattern {value}')
        orders[voice] = values
    require(set(orders) == {0, 1, 2}, 'Score requires exactly three voice orders')
    return orders, patterns


def numeric_state(initial_state):
    require(isinstance(initial_state, dict), 'Initial state must be a mapping')
    state = deepcopy(initial_state)
    globals_, voices = state.get('globals'), state.get('voices')
    require(isinstance(globals_, dict), 'Initial state requires named globals')
    require(isinstance(voices, (list, tuple)) and len(voices) == 3,
            'Initial state requires three voices')
    state['voices'] = list(voices)
    for name in GLOBAL_FIELDS:
        integer(globals_.get(name), 255, name)
    require(not globals_['status'] & 0x80, 'Unsupported negative status transport path')
    if 'output_enable' in globals_:
        integer(globals_['output_enable'], 255, 'output_enable')
        require(globals_['output_enable'] & 0x80,
                'Only the title negative output context is supported')
    for name, expected in (('sfx_priority', 0), ('sfx_flags', 255)):
        if name in globals_:
            require(type(globals_[name]) is int and globals_[name] == expected,
                    'Unsupported title sound overlay context')
    for voice in state['voices']:
        require(isinstance(voice, dict), 'Voice state must be a mapping')
        for name in SEQUENCE_FIELDS:
            integer(voice.get(name), 255, name)
    return state


def expand_score(score, *, calls, initial_state):
    """Return ordered score operations, numeric reads, restarts and final state.

    Duration bytes count score ticks remaining after initialization. The title
    dispatches voices 2, 1, 0; each append initializes the current instrument
    without reading a parameter or pitch. Sequence restart preserves control,
    instrument and modulation state. Source annotations are ignored.

    This computes score state only. Sound programs own mutable instrument and
    synthesis state. Negative status, FE transport and overlays are excluded.
    """
    integer(calls, 100000, 'calls')
    orders, patterns = numeric_tables(score)
    state = numeric_state(initial_state)
    globals_, voices = state['globals'], state['voices']
    operations, reads, restarts = [], [], []

    def emit(operation, call, index, **fields):
        row = dict(operation=operation, call=call, voice_index=index)
        row.update({name: voices[index][name] for name in SEQUENCE_FIELDS})
        row.update(fields)
        operations.append(row)

    def read(kind, call, index, offset, value, pattern_id=None):
        row = dict(kind=kind, call=call, voice_index=index, offset=offset, value=value)
        if pattern_id is not None:
            row['pattern_id'] = pattern_id
        reads.append(row)
        return value

    for call in range(calls):
        globals_['counter'] = (globals_['counter'] + 1) & 255
        reset = bool(globals_['status'] & 0x40)
        if reset:
            globals_.update(counter=0, status=0)
            for voice in voices:
                voice.update(order_cursor=0, pattern_cursor=0, remaining=0, note=0)
        countdown = (globals_['tempo_countdown'] - 1) & 255
        globals_['tempo_countdown'] = globals_['tempo_reload'] if countdown & 128 else countdown
        score_tick = globals_['tempo_countdown'] == globals_['tempo_reload']
        operations.append(dict(operation='call', call=call, counter=globals_['counter'],
                               status=globals_['status'], tempo_countdown=globals_['tempo_countdown'],
                               tempo_reload=globals_['tempo_reload'], score_tick=score_tick,
                               reset_sequence=reset))

        for index in (2, 1, 0):
            voice = voices[index]
            if score_tick:
                voice['remaining'] = (voice['remaining'] - 1) & 255
            if not score_tick or not voice['remaining'] & 128:
                emit('body', call, index, score_tick=score_tick,
                     release_check=bool(score_tick and voice['remaining'] == 0
                                        and not voice['control'] & 0x20))
                continue

            restarted = False
            while True:
                cursor = voice['order_cursor']
                require(cursor < len(orders[index]), f'Voice {index} order cursor {cursor} exceeds its table')
                pattern_id = read('orderRead', call, index, cursor, orders[index][cursor])
                if pattern_id != 255:
                    break
                require(not restarted, f'Voice {index} order restart loop')
                voice.update(order_cursor=0, pattern_cursor=0, remaining=0)
                restarts.append(dict(call=call, voice_index=index))
                emit('navigation', call, index, order_restart=True)
                restarted = True

            pattern = patterns[pattern_id]
            cursor = voice['pattern_cursor']
            require(cursor < len(pattern) and pattern[cursor] != 255,
                    f'Voice {index} pattern {pattern_id} cursor {cursor} must select a row')
            control = read('rowControlRead', call, index, cursor, pattern[cursor], pattern_id)
            voice.update(control=control, remaining=control & 31, portamento=0)
            emit('row', call, index, pattern_id=pattern_id)
            kind = row_kind(control)
            if kind != RowKind.APPEND:
                voice['pattern_cursor'] = (cursor + 1) & 255
                if kind == RowKind.PARAMETER:
                    cursor += 1
                    parameter = read('instrumentOrPortamentoRead', call, index, cursor,
                                     pattern[cursor], pattern_id)
                    if parameter & 128:
                        voice['portamento'] = parameter
                        emit('portamento', call, index)
                    else:
                        voice['instrument_index'] = parameter
                        emit('instrument', call, index)
                    voice['pattern_cursor'] = (voice['pattern_cursor'] + 1) & 255
                cursor += 1
                voice['note'] = read('pitchRead', call, index, cursor, pattern[cursor], pattern_id)
                emit('note', call, index)

            emit('initialize', call, index, append=kind == RowKind.APPEND)
            voice['pattern_cursor'] = (voice['pattern_cursor'] + 1) & 255
            cursor = voice['pattern_cursor']
            require(cursor < len(pattern), f'Pattern {pattern_id} has no end peek at {cursor}')
            end = read('patternEndPeek', call, index, cursor, pattern[cursor], pattern_id) == 255
            if end:
                voice['pattern_cursor'] = 0
                voice['order_cursor'] = (voice['order_cursor'] + 1) & 255
            emit('navigation', call, index, pattern_end=end)

    return dict(operations=operations, reads=reads, orderRestarts=restarts, finalState=state)
