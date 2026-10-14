"""Compute portable Billie Jean score and sound without original code or replay."""

from copy import deepcopy
from dataclasses import asdict, fields, replace

import billie_jean_programs as programs
import billie_jean_score as score


SCORE_INPUTS = dict(base_note='baseNote', remaining='remaining', hold='holdFlag',
    instrument_offset='instrumentOffset')
SOUND_FIELDS = frozenset(item.name for item in fields(programs.VoiceState)) - SCORE_INPUTS.keys()


def numbered(mapping, name):
    if not isinstance(mapping, dict):
        raise ValueError(f'{name} must be a numeric-key mapping')
    result = {}
    for key, value in mapping.items():
        if type(key) is int:
            index = key
        elif isinstance(key, str) and key.isdecimal():
            index = int(key)
        else:
            raise ValueError(f'{name} has a nonnumeric key')
        score.byte(index, f'{name} index')
        if index in result:
            raise ValueError(f'{name} has duplicate numeric keys')
        result[index] = value
    return result


def sound_data(description):
    if set(description) != {'instruments', 'programs'}:
        raise ValueError('Sound requires instruments and programs')
    instruments = {index: programs.Instrument(**value)
        for index, value in numbered(description['instruments'], 'instruments').items()}
    for instrument in instruments.values():
        programs.validate_state(instrument, programs.Instrument)
        score.byte(instrument.pulse_lower, 'Pulse lower high byte', 15)
        score.byte(instrument.pulse_upper, 'Pulse upper high byte', 15)
    values = deepcopy(description['programs'])
    values['frequencies'] = numbered(values['frequencies'], 'frequencies')
    for index, frequency in values['frequencies'].items():
        score.byte(index, 'Frequency index', 127)
        score.byte(frequency, 'Frequency word', 65535)
    for name in ('pitches', 'waveforms', 'routing_set', 'routing_clear'):
        length = 256 if name in ('pitches', 'waveforms') else 3
        if not isinstance(values[name], (list, tuple)) or len(values[name]) != length:
            raise ValueError(f'{name} requires {length} numeric bytes')
        for value in values[name]:
            score.byte(value, name)
    return instruments, programs.Programs(**values)


def bridge(state, score_state):
    """Refresh only score inputs; $128C/$12AB make glide step body-owned."""
    return replace(state, **{name: score_state[field] for name, field in SCORE_INPUTS.items()})


def compute(composition, *, calls=None, contexts=False):
    """Generate ordered stores and named state from editable numeric data.

    Ordinary row setters clear/set glide, and rest sets the gate mask before
    its continuing body. Those values then belong to sound until another row
    sets them. Setup/body already include the writer; $131F advances age after
    either path, and $132D emits the global register after descending voices.
    Source addresses are observation annotations and never drive synthesis.
    """
    if composition.get('schema') != 'billie-jean-composition-v1':
        raise ValueError('Expected billie-jean-composition-v1')
    unknown = set(composition) - {'schema', 'target', 'range', 'score', 'sound', 'initialSound', 'sourceEvidence'}
    if unknown:
        raise ValueError(f'Unknown composition fields: {sorted(unknown)}')
    target = composition['target']
    if target != dict(clock='pal', sidModel='MOS6581', sidBase=0xd400, frameCycles=19656):
        raise ValueError('Billie Jean requires explicit PAL MOS6581 at $D400 and 19656 cycles per call')
    if set(composition['range']) != {'auditCalls'}:
        raise ValueError('Range requires auditCalls')
    declared = composition['range']['auditCalls']
    if type(declared) is not int or not 1 <= declared <= 40000:
        raise ValueError('Declared audit range must be 1..40000 calls')
    calls = declared if calls is None else calls
    if type(calls) is not int or not 1 <= calls <= declared:
        raise ValueError('Choose calls within the declared audit range')
    numeric_score = composition['score']
    scheduled = score.expand(numeric_score, calls)
    rows = {(row['tick'], row['voice']): row for row in scheduled['rows']}
    instruments, bank = sound_data(composition['sound'])
    initial = composition['initialSound']
    if set(initial) != {'voices', 'filter'}:
        raise ValueError('Initial sound requires voices and filter')
    if len(initial['voices']) != 3:
        raise ValueError('Initial sound requires three voices')
    voices = []
    for voice, values in enumerate(initial['voices']):
        conflict = SCORE_INPUTS.keys() & values.keys()
        if conflict:
            raise ValueError(f'Initial sound duplicates a field: score owns {sorted(conflict)[0]}')
        if set(values) != SOUND_FIELDS:
            raise ValueError('Initial image requires complete named sound state')
        state = bridge(programs.VoiceState(**values), numeric_score['initialVoices'][voice])
        programs.validate_state(state, programs.VoiceState, programs.WORD_FIELDS)
        voices.append(state)
    if set(initial['filter']) != {item.name for item in fields(programs.FilterState)}:
        raise ValueError('Initial image requires complete named filter state')
    shared = programs.FilterState(**initial['filter'])
    programs.validate_state(shared, programs.FilterState)
    writes, records, returns = [], [], []

    def emit(items, tick):
        writes.extend(dict(phase='init' if tick is None else 'play', tick=tick,
            address=address, value=value) for address, value in items)

    emit([(0xd404, 0), (0xd40b, 0), (0xd412, 0)], None)
    for tick in range(calls):
        score_return = scheduled['returns'][tick]
        voices = [bridge(state, score_return['voices'][voice]) for voice, state in enumerate(voices)]
        for voice in (2, 1, 0):
            state = voices[voice]
            row = rows.get((tick, voice))
            onset = row is not None and row['kind'] == 'note'
            if onset:
                command = row['command']
                state = replace(state, glide_step=0)
                if command['header'] & 64:
                    state = replace(state, glide_step=command['glideStep'],
                        glide_target=(command['glideTarget'] + score_return['voices'][voice]['transpose']) & 255)
            elif row is not None:
                state = replace(state, gate_mask=254)
            offset = state.instrument_offset
            if offset not in instruments:
                raise ValueError(f'Missing instrument offset {offset}')
            before, filter_before = asdict(state), asdict(shared)
            result = (programs.note_setup(state, shared, instruments[offset], bank, voice) if onset else
                programs.body_step(state, shared, instruments[offset], bank, voice, score_return['divider']))
            shared = result.filter_state
            emit(result.writes, tick)
            if contexts:
                records.append(dict(stage='setup' if onset else 'body', call=tick, voice=voice,
                    instrumentOffset=offset, divider=score_return['divider'], before=before,
                    filterBefore=filter_before, after=asdict(result.state), filterAfter=asdict(shared),
                    writes=result.writes, path=result.path))
            voices[voice] = programs.advance_age(result.state)
            if contexts:
                records.append(dict(stage='age', call=tick, voice=voice,
                    before=asdict(result.state), filterBefore=asdict(shared),
                    after=asdict(voices[voice]), filterAfter=asdict(shared), writes=[], path='saturating'))
        output = programs.global_output(shared)
        emit(output, tick)
        if contexts:
            records.append(dict(stage='global-output', call=tick, filterBefore=asdict(shared),
                writes=output, path='mode-volume'))
        returns.append(dict(tick=tick, score=score_return, voices=[asdict(state) for state in voices],
            filter=asdict(shared)))
    return dict(writes=writes, returns=returns, contexts=records)
