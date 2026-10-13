"""Compose explicit semantic rows and numeric programs into ordered SID stores."""

from dataclasses import asdict, replace
from enum import Enum
import cybernoid_pitch as pitch
import cybernoid_output as output
import cybernoid_state as caller
import cybernoid_programs as programs


RECORD_FIELDS = ('pulse_flags', 'wave', 'attack_decay', 'sustain_release', 'packed_gate_filter', 'fx1', 'fx2', 'fx3')


class CommandKind(str, Enum):
    ROUTING = 'routing'
    SOUND = 'sound'
    DURATION = 'duration'
    EXTEND_DURATION = 'extendDuration'
    ARPEGGIO = 'arpeggio'
    GLIDE = 'glide'
    NOTE = 'note'


def integer(value, maximum, name):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError(f'{name} must be an integer in 0..{maximum}')
    return value


def selected(values, index, name):
    if not isinstance(values, (list, tuple)) or type(index) is not int or not 0 <= index < len(values):
        raise ValueError(f'{name} lacks selection {index}')
    return values[index]


def frequency(description, index, *, adjacent=False):
    integer(index, 256 if adjacent else 255, 'Frequency index')
    return integer(selected(description['frequency_words'], index, 'Frequency table'), 65535, 'Frequency word')


def record_bytes(description, index):
    record = selected(description['records'], index, 'Record table')
    return [integer(record[name], 255, name) for name in RECORD_FIELDS]


def pitch_from_caller(state, saved):
    return replace(saved, base_note=state.base_pitch, frequency=state.frequency,
                   held_frequency=state.held_frequency, vibrato_direction=state.vibrato_direction,
                   vibrato_position=state.vibrato_position, vibrato_age=state.vibrato_age,
                   glide_enabled=state.glide_enabled, glide_active=state.glide_active)


def caller_from_pitch(state, computed):
    return replace(state, base_pitch=computed.base_note, frequency=computed.frequency,
                   held_frequency=computed.held_frequency, vibrato_direction=computed.vibrato_direction,
                   vibrato_position=computed.vibrato_position, vibrato_age=computed.vibrato_age,
                   glide_enabled=computed.glide_enabled, glide_active=computed.glide_active)


def ending_parameters(description):
    """Validate the optional arranged release/fade, which follows unchanged music.

    The source loops. This explicit arrangement freezes its row calendar,
    continues sound programs with saturating note age, and forces every gate
    low. Every mode/volume store uses the current fade level so filter updates
    cannot briefly restore full volume. The final level is zero.
    """
    ending = description.get('ending')
    if ending is None:
        return None
    start = integer(ending['start_call'], 100000, 'Ending start')
    release = integer(ending['release_calls'], 65535, 'Ending release')
    step = integer(ending['fade_step_calls'], 255, 'Ending fade step')
    if start == 0 or step == 0 or start + release + 16 * step != description['play_calls']:
        raise ValueError('Ending must follow music and exactly fill declared calls with release and sixteen fade levels')
    return start, release, step


def compute_writes(description, *, calls=None):
    """Compute the declared row schedule; sourceEvidence never controls synthesis.

    Rows contain generated absolute calls and ordered editable commands. Editing
    notes/programs needs no source; timing edits must keep row calls consistent
    with the retained countdowns. Source note is an unsigned byte: executed
    A87F/A881/A882 loads it and adds transpose without masking. Adding
    transpose and glide-target arithmetic wraps bytes;
    vibrato adjacency shifts the source table bases and therefore uses index+1
    without byte wrap (A9FE/AA07). This model has no source-file or CPU dependency.
    """
    return _compute_writes(description, calls=calls)


def _compute_writes(description, *, calls=None, observer=None):
    declared = integer(description['play_calls'], 100000, 'Declared calls')
    ending = ending_parameters(description)
    music_calls = ending[0] if ending else declared
    calls = declared if calls is None else calls
    if type(calls) is not int or not 1 <= calls <= declared:
        raise ValueError('Calls must be in 1..declared play_calls')
    initial = description['initial_state']
    globals_ = dict(initial['globals'])
    for name in ('tempo_reload', 'tempo_countdown', 'play_flag', 'filter_owner'):
        integer(globals_[name], 255, name)
    if globals_['play_flag']:
        raise ValueError('Stopped initialization is outside the selected title contract')
    if len(initial['voices']) != 3:
        raise ValueError('Three initial voices required')
    voices = []
    for value in initial['voices']:
        state = caller.CallerState(**value['caller'])
        caller.validate(state)
        pitch_state = pitch.PitchState(**value['pitch'])
        for name, parameter in vars(pitch_state).items():
            integer(parameter, 65535 if name in ('frequency', 'held_frequency') else 255, f'Initial pitch {name}')
        if pitch_from_caller(state, pitch_state) != pitch_state:
            raise ValueError('Initial caller and pitch fields must agree')
        record_bytes(description, value['sound_index'])
        if value['arpeggio_index'] is not None:
            selected(description['arpeggios'], value['arpeggio_index'], 'Initial arpeggio table')
        voices.append(dict(state=state, pitch=pitch_state,
                           sound_index=value['sound_index'], arpeggio_index=value['arpeggio_index']))
    rows = {}
    for row in description['rows']:
        tick, voice = integer(row['call'], music_calls - 1, 'Row call'), integer(row['voiceIndex'], 2, 'Row voice')
        if (tick, voice) in rows:
            raise ValueError('Only one selected row per voice/call')
        integer(row['transpose'], 255, 'Transpose')
        if row['patchSetup'] not in ('initialize', 'preserve'):
            raise ValueError('Unknown patchSetup')
        rows[tick, voice] = row
    writes = []
    tail_volume = None
    mode_volume = 0

    def emit(phase, tick, group):
        nonlocal mode_volume
        for address, value in group:
            if address == 0xD418:
                if tail_volume is not None:
                    value = (value & 0xf0) | tail_volume
                mode_volume = value
            writes.append(dict(phase=phase, tick=tick, address=address, value=value))

    sid = description['sid_init']
    init_group = [(0xD416, integer(sid['cutoff_high'], 255, 'Initial cutoff high')),
                  (0xD417, integer(sid['routing'], 255, 'Initial routing')),
                  (0xD418, integer(sid['mode_volume'], 255, 'Initial mode/volume'))]
    init_group.extend((address, 0) for address in range(0xD415, 0xD3FF, -1))
    emit('init', None, init_group)
    for tick in range(calls):
        tail = tick >= music_calls
        if tail:
            age = tick - music_calls
            tail_volume = 15 if age < ending[1] else 15 - (age - ending[1]) // ending[2]
        else:
            globals_['tempo_countdown'] = (globals_['tempo_countdown'] - 1) & 255
            if globals_['tempo_countdown'] & 128:
                globals_['tempo_countdown'] = globals_['tempo_reload']
        scheduled = not tail and globals_['tempo_countdown'] == globals_['tempo_reload']
        for voice in (2, 1, 0):
            runtime = voices[voice]
            state = runtime['state']
            state = replace(state, note_age=min(255, state.note_age + 1)) if tail else caller.begin_voice_call(state)
            if scheduled:
                state = replace(state, row_remaining=(state.row_remaining - 1) & 255)
            row = rows.get((tick, voice))
            new_row = scheduled and bool(state.row_remaining & 128)
            if new_row != (row is not None):
                raise ValueError(f'Row/countdown mismatch at call {tick} voice {voice}')
            stages = {}
            if row is not None:
                state = caller.begin_row(state)
                note_seen = False
                for command in row['commands']:
                    kind = CommandKind(command['kind'])
                    if note_seen:
                        raise ValueError('Note must be the final row command')
                    if kind is CommandKind.ROUTING:
                        emit('play', tick, [(0xD417, integer(command['value'], 255, 'Routing'))])
                    elif kind is CommandKind.SOUND:
                        runtime['sound_index'] = command['index']
                        record_bytes(description, runtime['sound_index'])
                    elif kind in (CommandKind.DURATION, CommandKind.EXTEND_DURATION):
                        state = replace(state, row_duration=integer(command['reload'], 255, 'Duration reload'))
                    elif kind is CommandKind.ARPEGGIO:
                        selected(description['arpeggios'], command['index'], 'Arpeggio table')
                        runtime['arpeggio_index'] = command['index']
                    elif kind is CommandKind.GLIDE:
                        control = integer(command['control'], 255, 'Glide control')
                        target = (integer(command['targetNote'], 255, 'Glide target note') + row['transpose']) & 255
                        runtime['pitch'] = replace(runtime['pitch'], glide_control=control, glide_target=target)
                        state = replace(state, glide_enabled=1)
                    elif kind is CommandKind.NOTE:
                        index = (integer(command['sourceNote'], 255, 'Source note') + row['transpose']) & 255
                        state, group = caller.initialize_note(state, voice, index, frequency(description, index),
                            record_bytes(description, runtime['sound_index']), row['patchSetup'] == 'preserve')
                        emit('play', tick, group)
                        note_seen = True
                if not note_seen:
                    raise ValueError('Selected row requires a note')
                state = caller.finish_row(state)
                stages['initializer'] = True
            else:
                record = record_bytes(description, runtime['sound_index'])
                state, effects, group = caller.body_prelude(state, voice, record, globals_['tempo_countdown'], scheduled)
                emit('play', tick, group)
                fx1, fx2, fx3 = effects
                if not fx3 & 0x10 and fx3 & 4:
                    if runtime['arpeggio_index'] is None:
                        raise ValueError('Tone arpeggio active without a selected program')
                    result = output.advance_arpeggio(state.arpeggio_counter, state.base_pitch,
                        selected(description['arpeggios'], runtime['arpeggio_index'], 'Arpeggio table'), description['frequency_words'])
                    state = replace(state, arpeggio_counter=result.counter, current_pitch=result.pitch_index, frequency=result.frequency_word)
                    stages['arpeggio'] = asdict(result)
                effective = state.current_pitch
                ps = pitch_from_caller(state, runtime['pitch'])
                inputs = pitch.PitchInputs(frequency(description, effective),
                    frequency(description, effective + 1, adjacent=True), frequency(description, state.base_pitch),
                    frequency(description, ps.glide_target), state.note_age, state.row_remaining,
                    state.row_duration, globals_['tempo_reload'])
                parameters = pitch.PitchParameters(fx1, selected(description['vibrato_wait'], runtime['sound_index'], 'Vibrato wait'), bool(fx3 & 0x10))
                result = pitch.advance_pitch(ps, parameters, inputs)
                runtime['pitch'] = result.state
                state = caller_from_pitch(state, result.state)
                stages['pitch'] = asdict(result)
                selector = fx2 & 7
                pulse, direction = programs.advance_pulse(state.pulse_accumulator, state.pulse_direction,
                    state.note_age, fx2, selected(description['pulse_slots'], selector - 1, 'Pulse slot') if selector else None)
                state = replace(state, pulse_accumulator=pulse, pulse_direction=direction, pulse_output=pulse)
                if fx3 & 0x20:
                    base, current = output.sweep_high_byte(state.held_frequency, state.frequency)
                    state = replace(state, held_frequency=base, frequency=current)
                owner, cutoff, active, group = caller.filter_ownership(voice, fx2, fx3, globals_['filter_owner'], state.filter_cutoff)
                globals_['filter_owner'] = owner
                state = replace(state, filter_cutoff=cutoff)
                if active:
                    mode, cutoff = programs.advance_filter(cutoff, state.note_age,
                        selected(description['filter_programs'], state.packed_filter & 7, 'Filter program'))
                    state = replace(state, filter_cutoff=cutoff)
                    group = [(0xD418, mode), (0xD416, cutoff)]
                emit('play', tick, group)
                result = output.advance_pulse_run(bool(fx3 & 2), state.pulse_run_flag,
                    state.pulse_run_low, state.pulse_run_high, state.pulse_accumulator >> 8)
                state = replace(state, pulse_run_flag=result.needs_initialization, pulse_run_low=result.low, pulse_run_high=result.high,
                    pulse_output=state.pulse_output if result.pulse_override is None else result.pulse_override)
                if state.packed_filter & 8:
                    state = replace(state, frequency=(state.frequency + 12) & 65535)
                drum = selected(description['drums'], fx1 & 15, 'Drum program') if fx3 & 0x10 else dict(waves=[], pitch_values=[])
                record_index = runtime['sound_index']
                onset_length = selected(description['onset_lengths'], record_index, 'Onset length') if fx3 & 0x80 and not fx3 & 0x10 else 0
                onset_wave = selected(description['onset_waves'], record_index, 'Onset wave') if fx3 & 0x80 and not fx3 & 0x10 else 0
                result = output.apply_wave_program(fx3, state.note_age, fx1, state.current_pitch,
                    drum['waves'], drum['pitch_values'], description['frequency_words'], onset_length, onset_wave,
                    state.base_wave, state.held_frequency, state.wave, state.frequency, state.gate_mask)
                state = replace(state, wave=result.wave, frequency=result.frequency_word, gate_mask=result.gate_mask)
                stages['wave'] = asdict(result)
            if tail:
                state = replace(state, gate_mask=state.gate_mask & 254)
            group = output.voice_writes(voice, state.wave, state.gate_mask, state.frequency, state.pulse_output)
            emit('play', tick, group)
            runtime['state'] = state
            runtime['pitch'] = pitch_from_caller(state, runtime['pitch'])
            if observer is not None:
                observer(dict(call=tick, voiceIndex=voice, globals=dict(globals_), state=asdict(state),
                              pitch=asdict(runtime['pitch']), sound_index=runtime['sound_index'],
                              arpeggio_index=runtime['arpeggio_index'], row=row, stages=stages))
        if tail:
            emit('play', tick, [(0xD418, mode_volume)])
    return writes
