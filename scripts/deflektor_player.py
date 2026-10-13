"""Compute Deflektor's finite numeric player without an original driver or store replay."""

from collections import defaultdict
from copy import deepcopy

from deflektor_score import expand_score
from deflektor_programs import (
    BodyState, Stage, WaveProgram, WaveState, PitchStage, ScorePitchProgram,
    ScorePitchState, PulseProgram, PulseState, PitchState, ResonanceState,
    advance_prelude, initialize_wave, advance_wave, initialize_pitch,
    advance_pitch, advance_pwm, initialize_score_pitch, advance_score_pitch,
    initialize_resonance, advance_resonance, voice_writes, byte, word, require,
    validate_wave, validate_score_pitch,
)


VOICE_FIELDS = (
    'frequency pulse_word control attack_decay sustain_release remaining rest '
    'release_threshold detune pitch_index pwm_interval pwm_base pwm_elapsed '
    'pwm_step pwm_position pitch_selector pitch_wait pitch_position wave_selector '
    'wave_countdown wave_position score_pitch_selector score_pitch_countdown '
    'score_pitch_position resonance_selector resonance_countdown resonance_position '
    'glide_wait glide_remaining glide_flags glide_step'
).split()
GLOBAL_FIELDS = ('play_flag', 'cutoff_low', 'cutoff_high', 'routing', 'mode_volume')


def numeric_table(values, maximum, name):
    require(isinstance(values, (list, tuple)) and 0 < len(values) <= maximum,
            f'{name} requires 1..{maximum} numeric entries')
    for value in values:
        (word if name == 'frequency_words' else byte)(value)
    return dict(enumerate(values))


def programs(description):
    waves, pitches = {}, {}
    for key, value in description['wave_programs'].items():
        selector = selector_id(key)
        require(selector != 0 and selector not in waves, 'Wave selectors must be unique and nonzero')
        waves[selector] = WaveProgram(value['loop'], tuple(Stage(**stage) for stage in value['stages']))
        validate_wave(waves[selector], WaveState(0, 0, 0))
    for key, value in description['score_pitch_programs'].items():
        selector = selector_id(key)
        require(selector != 0 and selector not in pitches, 'Score-pitch selectors must be unique and nonzero')
        pitches[selector] = ScorePitchProgram(value['initial_wait'], value['restart_wait'], value['loop'],
                                             tuple(PitchStage(**stage) for stage in value['stages']))
        validate_score_pitch(pitches[selector], ScorePitchState(0, 0, 0))
    return waves, pitches


def selector_id(key):
    require(type(key) is int or type(key) is str and key.isascii() and key.isdecimal(),
            'Program selector IDs must be plain integers or decimal strings')
    result = int(key)
    byte(result)
    return result


def selected(table, selector, name):
    require(selector == 0 or selector in table, f'Missing {name} program {selector}')
    return table.get(selector)


def initial_state(description):
    state = deepcopy(description['initial_state'])
    require(len(state['voices']) == 3, 'Initial state must contain three voices')
    for name in GLOBAL_FIELDS:
        byte(state['globals'][name])
    for voice in state['voices']:
        for name in VOICE_FIELDS:
            (word if name in ('frequency', 'pulse_word', 'glide_step') else byte)(voice[name])
        require(voice['remaining'] == voice['rest'] == 0,
                'Initial row/rest counters must be zero for a cold score start')
    return state['globals'], state['voices']


def setup_instrument(voice, record):
    fields = record['fields']
    voice.update(pulse_word=(fields[1] << 8) | (voice['pulse_word'] & 255),
                 control=fields[2], attack_decay=fields[3], sustain_release=fields[4],
                 release_threshold=fields[5], pwm_step=fields[6], pitch_selector=fields[7],
                 wave_selector=fields[8], resonance_selector=record['contextual_resonance_selector'],
                 pwm_interval=fields[0] & 15, pwm_base=fields[0] & 240,
                 pwm_elapsed=((fields[0] & 15) - 1) & 255, pwm_position=0,
                 resonance_position=0)


def setup_note(voice, note, duration, waves, pitches, frequencies, motion, resonance, routing):
    index = (note['sourceNote'] + note['transpose'] + 20) & 255
    require(index in frequencies, f'Missing note frequency {index}')
    voice.update(pitch_index=index, frequency=(frequencies[index] + voice['detune']) & 65535,
                 control=voice['control'] | 1, remaining=duration)
    state = initialize_pitch(voice['pitch_selector'],
                             PitchState(voice['pitch_wait'], voice['pitch_position'], voice['frequency']), motion)
    voice.update(pitch_wait=state.wait, pitch_position=state.position)
    state = initialize_wave(selected(waves, voice['wave_selector'], 'wave'),
                            WaveState(voice['wave_countdown'], voice['wave_position'], voice['control']))
    voice.update(wave_countdown=state.countdown, wave_position=state.position, control=state.control)
    state, routing = initialize_resonance(voice['resonance_selector'],
        ResonanceState(voice['resonance_countdown'], voice['resonance_position']), resonance, routing)
    voice.update(resonance_countdown=state.countdown, resonance_position=state.position)
    # C4F0 tests the unshifted table base, so base-zero notes retain PWM phase.
    if voice['pwm_base']:
        voice.update(pwm_elapsed=(voice['pwm_interval'] - 1) & 255, pwm_position=0)
    state = initialize_score_pitch(selected(pitches, voice['score_pitch_selector'], 'score pitch'),
        ScorePitchState(voice['score_pitch_countdown'], voice['score_pitch_position'], voice['frequency']))
    voice.update(score_pitch_countdown=state.countdown, score_pitch_position=state.position,
                 glide_wait=voice['glide_flags'] & 31)
    return routing


def advance_body(voice, *, global_skip, waves, pitches, frequencies, motion, resonance, routing):
    state, run = advance_prelude(BodyState(voice['remaining'], voice['rest'], voice['control'],
        voice['frequency'], voice['release_threshold'], voice['glide_wait'], voice['glide_remaining'],
        voice['glide_flags'], voice['glide_step']), global_skip=global_skip)
    voice.update(remaining=state.remaining, rest=state.rest, control=state.control,
                 frequency=state.frequency, glide_wait=state.glide_wait, glide_remaining=state.glide_remaining)
    if not run:
        return routing
    state = advance_pwm(PulseProgram(voice['pwm_interval'], voice['pwm_base'], voice['pwm_step']),
                        PulseState(voice['pwm_elapsed'], voice['pwm_position'], voice['pulse_word']), motion)
    voice.update(pwm_elapsed=state.elapsed, pwm_position=state.position, pulse_word=state.word)
    state = advance_pitch(voice['pitch_selector'],
                          PitchState(voice['pitch_wait'], voice['pitch_position'], voice['frequency']), motion)
    voice.update(pitch_wait=state.wait, pitch_position=state.position, frequency=state.word)
    state = advance_wave(selected(waves, voice['wave_selector'], 'wave'),
                         WaveState(voice['wave_countdown'], voice['wave_position'], voice['control']))
    voice.update(wave_countdown=state.countdown, wave_position=state.position, control=state.control)
    state = advance_score_pitch(selected(pitches, voice['score_pitch_selector'], 'score pitch'),
        ScorePitchState(voice['score_pitch_countdown'], voice['score_pitch_position'], voice['frequency']),
        pitch_index=voice['pitch_index'], detune=voice['detune'], frequency_words=frequencies)
    voice.update(score_pitch_countdown=state.countdown, score_pitch_position=state.position,
                 frequency=state.frequency)
    state, routing = advance_resonance(voice['resonance_selector'],
        ResonanceState(voice['resonance_countdown'], voice['resonance_position']), resonance, routing)
    voice.update(resonance_countdown=state.countdown, resonance_position=state.position)
    return routing


def command(voice, globals_, action):
    kind = action['kind']
    if kind == 'parameterC0C0':
        voice['detune'] = action['value']
    elif kind == 'modeVolume':
        globals_['mode_volume'] = action['value']
    elif kind == 'opaqueSingleByteEffect' and 0x90 <= action['sourceCommand'] <= 0x95:
        voice['score_pitch_selector'] = (action['sourceCommand'] & 15) << 3
    elif kind not in ('transpose', 'repeatTotal', 'instrumentMapping'):
        raise ValueError(f'Unsupported synthesis command {kind}')


def compute_writes(description, *, calls=None):
    """Generate ordered phase/call/address/value stores from editable numeric data.

    The score starts cold with zero row/rest counters; cursor-based warm
    resume is unsupported. Cold init generates no SID stores; loaded shadows are explicit
    inputs rather than presumed hardware state. Calls are an exclusive cap in
    0..100000. A consumed score stop emits three control-zero stores once;
    all later calls retain stopped state without writes. Source annotations
    are ignored, and no original code, file or observed ledger is read.

    The supported grammar is the decoded title path. Unknown synthesis
    commands reject rather than receiving guessed behavior. This predicts
    register values/order, not instruction cycles, SID synthesis or audio.
    """
    require(description['schemaVersion'] == 'sid-deflektor-player-v1', 'Unsupported player schema')
    calls = description['play_calls'] if calls is None else calls
    require(type(calls) is int and 0 <= calls <= 100000, 'calls must be an integer in 0..100000')
    globals_, voices = initial_state(description)
    frequencies = numeric_table(description['frequency_words'], 256, 'frequency_words')
    motion = numeric_table(description['motion_table'], 280, 'motion_table')
    resonance = numeric_table(description['resonance_table'], 257, 'resonance_table')
    waves, pitches = programs(description)
    expanded = expand_score(description['score'], calls=calls)
    records = {record['recordOffset']: record for record in description['score']['recordTable']['records']}
    for record in records.values():
        byte(record['contextual_resonance_selector'])
        selected(waves, record['fields'][8], 'wave')
    for voice in voices:
        selected(waves, voice['wave_selector'], 'wave')
        selected(pitches, voice['score_pitch_selector'], 'score pitch')
    actions = defaultdict(list)
    for action in expanded['operations']:
        actions[action['call'], action['voiceIndex']].append(action)
    writes = []

    def emit(call, address, value):
        writes.append(dict(phase='play', tick=call, address=address, value=value))

    for call in range(calls):
        if not globals_['play_flag']:
            break
        skip = False
        for voice in voices:
            if voice['remaining'] == 1:
                voice.update(remaining=0, rest=0)
                skip = True
        for index, voice in enumerate(voices):
            if voice['remaining']:
                globals_['routing'] = advance_body(voice, global_skip=skip, waves=waves, pitches=pitches,
                    frequencies=frequencies, motion=motion, resonance=resonance, routing=globals_['routing'])
                continue
            if voice['glide_remaining'] != 255:
                voice['glide_remaining'] = 0
            note = None
            timed = False
            for action in actions.get((call, index), ()):
                kind = action['operation']
                if kind == 'stop':
                    globals_['play_flag'] = 0
                    for address in (0xd404, 0xd40b, 0xd412):
                        emit(call, address, 0)
                    break
                if kind == 'command':
                    command(voice, globals_, action)
                elif kind == 'instrument':
                    setup_instrument(voice, records[action['recordOffset']])
                elif kind == 'note':
                    note = action
                elif kind == 'row':
                    duration = action['value']
                    if action['rowKind'] == 'note':
                        require(note is not None, 'Note row lacks a source note')
                        globals_['routing'] = setup_note(voice, note, duration, waves, pitches,
                            frequencies, motion, resonance, globals_['routing'])
                    else:
                        voice.update(remaining=duration, rest=duration)
                        emit(call, 0xd404 + 7 * index, 0)
                    timed = True
                else:
                    raise ValueError(f'Unsupported score operation {kind}')
            if not globals_['play_flag']:
                break
            require(timed, 'Expanded score and numeric row countdown disagree')
        if not globals_['play_flag']:
            break
        if skip:
            continue
        for index, voice in enumerate(voices):
            if not voice['rest']:
                for address, value in voice_writes(index, frequency=voice['frequency'],
                    pulse_word=voice['pulse_word'], control=voice['control'],
                    attack_decay=voice['attack_decay'], sustain_release=voice['sustain_release']):
                    emit(call, address, value)
        for address, name in ((0xd415, 'cutoff_low'), (0xd416, 'cutoff_high'),
                              (0xd417, 'routing'), (0xd418, 'mode_volume')):
            emit(call, address, globals_[name])
    return writes
