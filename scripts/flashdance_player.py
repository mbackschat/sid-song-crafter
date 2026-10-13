"""Schedule editable Flashdance instruments into computed, ordered SID writes."""

from copy import deepcopy
from dataclasses import asdict
from enum import Enum

from flashdance_pitch import PitchEffects, SlideState, VibratoState, advance_pitch, note_changed
from flashdance_programs import (
    PreloadedState, Programs, advance_filter, advance_voice, decode_preloaded,
    decode_programs, initialize_filter, initialize_voice, ram_image,
)
from verify_player import require


class CommandKind(str, Enum):
    INSTRUMENT = 'instrument'
    NOTE = 'note'
    HOLD = 'hold'
    OFF = 'off'
    EFFECT = 'effect'


class EffectKind(str, Enum):
    VIBRATO = 'vibrato'
    PITCH_OFFSET = 'pitchOffset'
    SUSTAIN_RELEASE_AHEAD = 'sustainReleaseAhead'


def _integer(value, label, maximum=255, minimum=0):
    require(type(value) is int and minimum <= value <= maximum,
            f'{label} must be an integer in {minimum}..{maximum}')


def _fields(value, required, label, *, annotations=False):
    allowed = set(required) | ({'sourceEvidence'} if annotations else set())
    require(isinstance(value, dict) and set(required) <= set(value) <= allowed,
            f'Invalid {label} fields')


def _validate_command(command):
    require(isinstance(command, dict), 'Score command must be an object')
    try:
        kind = CommandKind(command['kind'])
    except (KeyError, ValueError) as error:
        raise ValueError(f'Unsupported score command: {command}') from error
    fields = {
        CommandKind.INSTRUMENT: {'instrument'},
        CommandKind.NOTE: {'sourceNote', 'transposeSemitones', 'restart', 'durationCalls'},
        CommandKind.HOLD: {'durationCalls'}, CommandKind.OFF: {'durationCalls'},
        CommandKind.EFFECT: {'effect', 'parameters'},
    }
    _fields(command, {'call', 'kind'} | fields[kind], 'command', annotations=True)
    if kind == CommandKind.INSTRUMENT:
        require(isinstance(command['instrument'], str), 'Instrument name must be a string')
    elif kind == CommandKind.NOTE:
        _integer(command['sourceNote'], 'sourceNote', 95)
        _integer(command['transposeSemitones'], 'transposeSemitones', 127)
        require(type(command['restart']) is bool, 'restart must be boolean')
    elif kind == CommandKind.EFFECT:
        try:
            effect = EffectKind(command['effect'])
        except (KeyError, ValueError) as error:
            raise ValueError(f'Unsupported effect command: {command}') from error
        params = command['parameters']
        if effect == EffectKind.VIBRATO:
            _fields(params, {'remainingNotes', 'reloadCounter', 'initialCounter',
                             'pitchDeltaRightShifts', 'deltaHighByteIncrement'}, 'vibrato parameters')
            for key, limit in (('remainingNotes', 2), ('reloadCounter', 15), ('initialCounter', 15),
                               ('pitchDeltaRightShifts', 15), ('deltaHighByteIncrement', 15)):
                _integer(params[key], key, limit)
        elif effect == EffectKind.PITCH_OFFSET:
            _fields(params, {'remainingNotes', 'stepWord'}, 'pitch-offset parameters')
            _integer(params['remainingNotes'], 'remainingNotes', 2)
            _integer(params['stepWord'], 'stepWord', 65535)
        elif effect == EffectKind.SUSTAIN_RELEASE_AHEAD:
            _fields(params, {'callsBeforeNextRow', 'sustainRelease'}, 'envelope parameters')
            _integer(params['callsBeforeNextRow'], 'callsBeforeNextRow', 255, 1)
            _integer(params['sustainRelease'], 'sustainRelease')
    if 'durationCalls' in command:
        _integer(command['durationCalls'], 'durationCalls', 256, 1)
    return kind


def _load_effects(values):
    require(isinstance(values, list) and len(values) == 3, 'Expected initial effects for three voices')
    result = []
    for value in values:
        _fields(value, {'slide', 'vibrato'}, 'pitch effects')
        slide, vibrato = value['slide'], value['vibrato']
        _fields(slide, asdict(SlideState()), 'slide state')
        _fields(vibrato, asdict(VibratoState()), 'vibrato state')
        for key in ('step', 'offset'):
            _integer(slide[key], 'slide ' + key, 65535)
        _integer(slide['enabled'], 'slide enabled', 2)
        require(type(slide['subtract']) is bool, 'slide subtract must be boolean')
        for key in ('interval', 'remaining', 'growth', 'depth'):
            _integer(vibrato[key], 'vibrato ' + key)
        _integer(vibrato['enabled'], 'vibrato enabled', 2)
        _integer(vibrato['direction'], 'vibrato direction', 1)
        _integer(vibrato['shift'], 'vibrato shift', 15)
        _integer(vibrato['offset'], 'vibrato offset', 65535)
        result.append(PitchEffects(SlideState(**slide), VibratoState(**vibrato)))
    return result


def describe_player(data, score):
    """Import musical parameters once; playback needs only the returned data."""
    memory = ram_image(data)
    programs = decode_programs(data)
    score = deepcopy(score)
    require(tuple(score.pop('frequencyTable')) == programs.frequency_words,
            'Score and instrument frequency tables disagree')
    instruments = score.pop('instruments')
    bindings = {f'record-{index:02x}': index for index in programs.instruments}
    require(set(instruments) == set(bindings), 'Score and instrument banks disagree')
    effects = []
    for x in range(3):
        word = lambda address: memory[address + x] | memory[address + x + 3] << 8
        effects.append(asdict(PitchEffects(
            slide=SlideState(memory[0x1704 + x], word(0x1753), bool(memory[0x1759 + x]), word(0x175c)),
            vibrato=VibratoState(memory[0x1701 + x], memory[0x171c + x], memory[0x1719 + x],
                                memory[0x1725 + x], memory[0x172e + x], memory[0x171f + x],
                                memory[0x1722 + x], word(0x1728)))))
    return {
        'format': 'sid-flashdance-composition-v1', 'score': score,
        'programs': programs.to_dict(), 'preloaded': decode_preloaded(data).to_dict(),
        'initialEffects': effects, 'instrumentBindings': bindings,
        'initialVolume': memory[0x1009], 'initialRouting': memory[0x100a],
        'ending': {'releaseCalls': 64, 'fadeStepCalls': 4},
        'sourceEvidence': {'instruments': instruments},
    }


def _schedule(description, calls):
    _fields(description, {'format', 'score', 'programs', 'preloaded', 'initialEffects',
                          'instrumentBindings', 'initialVolume', 'initialRouting', 'ending'}, 'composition', annotations=True)
    require(description['format'] == 'sid-flashdance-composition-v1', 'Unsupported composition format')
    score = description['score']
    require(isinstance(score, dict) and {'profile', 'range', 'roles'} <= set(score),
            'Score must contain profile, range and roles')
    require(score['profile'] == {'clock': 'PAL', 'chip': 'MOS6581', 'callCycles': 19656},
            'Unsupported Flashdance profile')
    require(isinstance(score['range'], dict) and {'stopCall', 'firstCall'} <= set(score['range']),
            'Score range must contain firstCall and stopCall')
    require(isinstance(description['instrumentBindings'], dict) and
            all(isinstance(name, str) for name in description['instrumentBindings']),
            'Instrument bindings must map string names to programs')
    stop = score['range']['stopCall']
    _integer(stop, 'stopCall', 65535, 1)
    ending = description['ending']
    _fields(ending, {'releaseCalls', 'fadeStepCalls'}, 'ending')
    _integer(ending['releaseCalls'], 'ending releaseCalls', 65535)
    _integer(ending['fadeStepCalls'], 'ending fadeStepCalls', 255, 1)
    require(stop + ending['releaseCalls'] + 16 * ending['fadeStepCalls'] <= 65535,
            'The ending must fit the compiled word counter')
    calls = stop if calls is None else calls
    require(type(calls) is int and 1 <= calls <= 100000, 'Select a bounded execution of 1..100000 calls')
    require(score['range']['firstCall'] == 0, 'Preserve initialization and startup calls')
    require(isinstance(score['roles'], dict) and set(score['roles']) == {'bass', 'lead', 'chord'},
            'Expected three declared roles')
    schedules, tuning = [], []
    for voice, role in enumerate(('bass', 'lead', 'chord'), 1):
        part = score['roles'][role]
        require(isinstance(part, dict) and {'voice', 'commands', 'fineTuneWord'} <= set(part),
                'Score role must contain voice, commands and fineTuneWord')
        require(isinstance(part['commands'], list), 'Score commands must be a list')
        require(part['voice'] == voice, 'Voice assignment differs from the selected profile')
        by_call = {}
        previous = -1
        for command in part['commands']:
            kind = _validate_command(command)
            call = command['call']
            require(type(call) is int and 0 <= call < stop and previous <= call,
                    'Score commands must be ordered within the call range')
            if kind == CommandKind.INSTRUMENT:
                require(command['instrument'] in description['instrumentBindings'], 'Unknown instrument name')
            by_call.setdefault(call, []).append(command)
            previous = call
        for commands in by_call.values():
            envelope = [command for command in commands if command.get('effect') == EffectKind.SUSTAIN_RELEASE_AHEAD]
            if not envelope:
                continue
            row = next((command for command in commands if 'durationCalls' in command), None)
            require(row is not None, 'Scheduled envelope effect requires a same-call score duration')
            for command in envelope:
                require(row['durationCalls'] > command['parameters']['callsBeforeNextRow'],
                        'Scheduled envelope change must precede the next score row')
        schedules.append(by_call)
        _integer(part['fineTuneWord'], 'fineTuneWord')
        tuning.append(part['fineTuneWord'])
    return calls, schedules, tuning


def compute_writes(description, *, calls=None):
    """Compute initialization and the declared musical span without reference I/O.

    This model emits every store, including repeated shared cutoff writes, in
    hardware-voice order. Its output is an execution oracle for our independent
    player, not a register-replay export or a within-frame timing claim.
    """
    calls, schedules, tuning = _schedule(description, calls)
    programs = Programs.from_dict(description['programs'])
    initial = PreloadedState.from_dict(description['preloaded'], programs)
    voices, filt = initial.voices, initial.filter
    effects = _load_effects(description['initialEffects'])
    bindings = description['instrumentBindings']
    require(all(type(index) is int and index in programs.instruments for index in bindings.values()),
            'Instrument name refers to a missing program')
    selected, notes, transpose, gate = [0] * 3, [0] * 3, [0] * 3, [0] * 3
    delayed_sr = [None] * 3
    volume, routing = description['initialVolume'], description['initialRouting']
    _integer(volume, 'initialVolume', 15)
    _integer(routing, 'initialRouting')
    stop = description['score']['range']['stopCall']
    release_calls, fade_step = description['ending']['releaseCalls'], description['ending']['fadeStepCalls']
    end = stop + release_calls + 16 * fade_step
    filter_mode = 0
    writes = []

    def emit(address, value, tick=None):
        require(type(value) is int and 0 <= value <= 255, 'SID store must fit a byte')
        writes.append({'phase': 'init' if tick is None else 'play', 'tick': tick,
                       'address': address, 'value': value})

    for address in range(0xd400, 0xd419):
        emit(address, 0)
    emit(0xd418, volume)
    for tick in range(calls):
        if tick >= end:
            for address in (0xd404, 0xd40b, 0xd412, 0xd418):
                emit(address, 0, tick)
            continue
        if tick >= stop:
            gate = [254] * 3
            delayed_sr = [None] * 3
            fade_age = tick - stop - release_calls
            if fade_age >= 0 and fade_age % fade_step == 0:
                emit(0xd418, filter_mode | max(0, volume - 1 - fade_age // fade_step), tick)
        for voice in (2, 1, 0):
            base = 0xd400 + voice * 7
            pending = delayed_sr[voice]
            if pending is not None and pending[0] == tick:
                emit(base + 6, pending[1], tick)
                delayed_sr[voice] = None
            restart = False
            commands = schedules[voice].get(tick, ())
            for command in commands:
                kind = CommandKind(command['kind'])
                if kind == CommandKind.INSTRUMENT:
                    selected[voice] = bindings[command['instrument']]
                elif kind == CommandKind.NOTE:
                    notes[voice] = command['sourceNote']
                    transpose[voice] = command['transposeSemitones'] * 2
                    gate[voice] = 255
                    note_changed(effects[voice])
                    restart = command['restart']
                elif kind == CommandKind.HOLD:
                    gate[voice] = 255
                elif kind == CommandKind.OFF:
                    gate[voice] = 254
                elif kind == CommandKind.EFFECT:
                    effect = EffectKind(command['effect'])
                    params = command['parameters']
                    if effect == EffectKind.VIBRATO:
                        effects[voice].vibrato = VibratoState(
                            enabled=params['remainingNotes'], interval=params['reloadCounter'],
                            remaining=params['initialCounter'], shift=params['pitchDeltaRightShifts'],
                            growth=params['deltaHighByteIncrement'])
                    elif effect == EffectKind.PITCH_OFFSET:
                        effects[voice].slide = SlideState(enabled=params['remainingNotes'], step=params['stepWord'])
                    elif effect == EffectKind.SUSTAIN_RELEASE_AHEAD:
                        row = next(item for item in commands if 'durationCalls' in item)
                        delay = row['durationCalls'] - params['callsBeforeNextRow']
                        require(delay > 0, 'Scheduled envelope change must precede the next score row')
                        delayed_sr[voice] = tick + delay, params['sustainRelease']
            if restart:
                instrument = programs.instruments[selected[voice]]
                emit(base + 5, 0, tick)
                emit(base + 6, 15, tick)
                emit(base + 4, 8, tick)
                initialize_voice(voices[voice], instrument, programs)
                command = instrument.filter_command
                mode = command & 15
                if mode:
                    filter_mode = mode << 4
                    emit(0xd418, filter_mode | volume, tick)
                    routing = (routing & 15) | (1 << voice) | (command & 240)
                else:
                    routing &= 255 ^ (1 << voice)
                emit(0xd417, routing, tick)
                initialize_filter(filt, instrument, programs)
                emit(base + 5, instrument.attack_decay, tick)
                emit(base + 6, instrument.sustain_release, tick)
                emit(base + 4, 9, tick)
                continue
            if voice == programs.filter_owner:
                advance_filter(filt, programs)
            output = advance_voice(voices[voice], programs, base_note=notes[voice],
                                   transpose_bytes=transpose[voice], fine_tune=tuning[voice], gate_mask=gate[voice])
            frequency = advance_pitch(effects[voice], output.frequency_word, notes[voice],
                                      programs.frequency_words, absolute=output.absolute_pitch)
            emit(base + 2, output.pulse_width & 255, tick)
            emit(base + 3, output.pulse_width >> 8, tick)
            emit(0xd416, filt.cutoff, tick)
            emit(base, frequency & 255, tick)
            emit(base + 1, frequency >> 8, tick)
            emit(base + 4, output.control, tick)
    return writes
