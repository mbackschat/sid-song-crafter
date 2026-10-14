"""Compute a portable Take On Me composition from numeric score and sound data."""

from copy import deepcopy
from dataclasses import asdict, replace

import programs
import score


SCORE_INPUTS = {
    'remaining': 'remaining', 'duration': 'durationTicks', 'base_note': 'baseNote',
    'glide_target': 'glideTarget', 'arpeggio': 'arpeggio',
}
SCORE_OWNED = frozenset(SCORE_INPUTS) | {'glide_step'}
NOTE_RESETS = dict(glide_active=0, onset_initial=0, arpeggio_cursor=0,
    waveform_cursor=0, pitch_cursor=0, pulse_initial=0, vibrato_initial=0)


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
    instruments = {index: programs.Instrument(**value)
        for index, value in numbered(description['instruments'], 'instruments').items()}
    for instrument in instruments.values():
        programs.validate_instrument(instrument)
    values = {name: numbered(value, name) for name, value in description['programs'].items()}
    for name in ('pulses', 'filters'):
        if name in values:
            values[name] = {index: programs.SweepProgram(**value) for index, value in values[name].items()}
    if 'vibratos' in values:
        values['vibratos'] = {index: programs.VibratoProgram(**value) for index, value in values['vibratos'].items()}
    return instruments, programs.Programs(**values)


def bridge(state, score_state):
    """Project score-owned inputs; body effects own all other VoiceState fields.

    The source's paired SBC/ADC at $12FD/$1304 and $131F/$1326 establish
    glide_step as a word. Sound changes glide_active, so score holds must not
    overwrite it after a target crossing.
    """
    values = {name: score_state[field] for name, field in SCORE_INPUTS.items()}
    values['glide_step'] = score_state['glideStepLow'] | score_state['glideStepHigh'] << 8
    return replace(state, **values)


def compute(composition, *, calls=None, contexts=False):
    """Generate ordered stores and named state without source execution or replay.

    The score expander owns score parameters and countdowns. Its derived input
    projection is refreshed before each sound stage; initialSound cannot define
    those same values. Sound owns pitch/pulse/control and modulation state.
    Source addresses and provenance are optional, nonexecuting annotations.
    The declared audit range bounds computation and does not compose an ending.
    """
    if composition.get('schema') != 'take-on-me-composition-v1':
        raise ValueError('Expected take-on-me-composition-v1')
    target = composition['target']
    if target.get('clock') != 'pal' or target.get('sidBase') != 0xd400 or target.get('frameCycles') != 19656:
        raise ValueError('Take On Me numeric player requires one PAL SID at $D400 and 19656 cycles per call')
    if target.get('sidModel') not in ('MOS6581', 'MOS8580'):
        raise ValueError('Composition requires an explicit SID model')
    declared = composition['range']['auditCalls']
    if type(declared) is not int or not 1 <= declared <= 100000:
        raise ValueError('Declared audit range must be 1..100000 calls')
    calls = declared if calls is None else calls
    if type(calls) is not int or not 1 <= calls <= declared:
        raise ValueError('Choose calls within the declared audit range')
    numeric_score = deepcopy(composition['score'])
    for order in numeric_score['orders']:
        order['address'] = 0
    for pattern in numeric_score['patterns'].values():
        pattern['address'] = 0
    scheduled = score.expand(numeric_score, calls)
    onsets = {(row['tick'], row['voice']): row for row in scheduled['rows']}
    stops = {row['tick']: row['voice'] for row in scheduled['stops']}
    instruments, bank = sound_data(composition['sound'])
    initial = composition['initialSound']
    if len(initial['voices']) != 3:
        raise ValueError('Initial sound image requires three voices')
    voices = []
    for voice, values in enumerate(initial['voices']):
        conflict = SCORE_OWNED.intersection(values)
        if conflict:
            raise ValueError(f'Initial sound duplicates a field: score owns {sorted(conflict)[0]}')
        state = programs.VoiceState(**values)
        programs.validate_state(state, programs.VoiceState, programs.VOICE_WORDS)
        voices.append(bridge(state, numeric_score['initialVoices'][voice]))
    shared = programs.FilterState(**initial['filter'])
    programs.validate_state(shared, programs.FilterState, ('word',))
    routing = score.byte(composition['mix']['routing'], 'routing')
    mode_volume = score.byte(composition['mix']['modeVolume'], 'modeVolume')
    writes, records, returns = [], [], []

    def emit(items, tick):
        writes.extend(dict(phase='init' if tick is None else 'play', tick=tick,
            address=address, value=value) for address, value in items)

    emit([(0xd404, 0), (0xd40b, 0), (0xd412, 0), (0xd417, routing), (0xd418, mode_volume)], None)
    active = True
    for tick, score_return in enumerate(scheduled['returns']):
        if active:
            voices = [bridge(state, score_return['voices'][voice]) for voice, state in enumerate(voices)]
            for voice in (2, 1, 0):
                state = voices[voice]
                if stops.get(tick) == voice:
                    voices[voice] = replace(state, **NOTE_RESETS)
                    emit([(0xd404, 0), (0xd40b, 0), (0xd412, 0)], tick)
                    active = False
                    break
                onset = onsets.get((tick, voice))
                instrument_id = score_return['voices'][voice]['instrument']
                if instrument_id not in instruments:
                    raise ValueError(f'Missing instrument {instrument_id}')
                instrument = instruments[instrument_id]
                if onset:
                    state = replace(state, **dict(NOTE_RESETS, glide_active=onset['glideActive']))
                before, filter_before = asdict(state), asdict(shared)
                result = (programs.note_setup(state, shared, instrument, voice, bank.frequencies) if onset else
                    programs.body_step(state, shared, instrument, bank, voice))
                voices[voice], shared = result.state, result.filter_state
                emit(result.writes, tick)
                if contexts:
                    records.append(dict(stage='setup' if onset else 'body', call=tick, voice=voice,
                        instrument=instrument_id, before=before, filterBefore=filter_before,
                        after=asdict(result.state), filterAfter=asdict(shared), writes=result.writes))
                output = programs.voice_output(result.state, voice)
                emit(output, tick)
                if contexts:
                    records.append(dict(stage='voice-output', call=tick, voice=voice, writes=output))
            if active:
                output = programs.filter_output(shared)
                emit(output, tick)
                if contexts:
                    records.append(dict(stage='filter-output', call=tick, voice=0, writes=output))
        returns.append(dict(tick=tick, score=score_return,
            voices=[asdict(state) for state in voices], filter=asdict(shared)))
    rows = [{key: value for key, value in row.items() if key != 'address'} for row in scheduled['rows']]
    return dict(writes=writes, rows=rows, wraps=scheduled['wraps'], stops=scheduled['stops'],
        returns=returns, contexts=records)
