"""Compute a Ghouls-family composition from editable score and sound state."""

from copy import deepcopy
from dataclasses import asdict, replace
from enum import Enum

from ghouls_programs import (FilterState, VoiceState, filter_step, frequency_step,
                            note_setup, note_step, onset_step, pulse_step,
                            validate_filter_state, validate_lookup, validate_voice_state)
from ghouls_score import ScoreCommand, ScoreRuntime


class Operation(str, Enum):
    GATE = 'gate'
    NOTE = 'note'
    REST = 'rest'
    COMMAND = 'command'


PROFILE = {'clock': 'PAL', 'sidModel': 'MOS6581', 'sidCount': 1, 'sidBase': 0xd400, 'frameCycles': 19656}
VOICE_ASSIGNMENTS = {
    'transpose': {'transpose': 'transpose'},
    'frequency-motion': {'frequencyDelayReload': 'frequency_delay_reload',
                         'frequencyStep': 'frequency_step',
                         'frequencyHalfReload': 'frequency_half_reload',
                         'frequencyDirectionDefault': 'frequency_direction_default'},
    'gate-time': {'gateTime': 'gate_time'},
    'note-motion': {'noteStep': 'note_step', 'notePositiveDuration': 'note_positive_duration',
                    'noteNegativeDuration': 'note_negative_duration'},
    'glide-rate': {'glideRate': 'glide_rate'},
}
NAVIGATION = frozenset(('repeat-start', 'repeat-end', 'call', 'return',
                        'disable-voice', 'duration-override'))


def _integers(values, length, maximum, name):
    if not isinstance(values, list) or len(values) != length or any(
            type(value) is not int or not 0 <= value <= maximum for value in values):
        raise ValueError(f'{name} requires {length} integers in 0..{maximum}')
    return list(values)


def _word(fields, prefix):
    return fields[prefix + 'Low'] | fields[prefix + 'High'] << 8


class GhoulsPlayer:
    def __init__(self, description):
        if description.get('format') != 'ghouls-composition-v1':
            raise ValueError('Expected a Ghouls-family editable composition')
        if description.get('profile') != PROFILE:
            raise ValueError('Ghouls player requires the declared PAL/6581 profile')
        self.description = deepcopy(description)
        self.pulse_fallbacks = _integers(description.get('pulseFallbacks'), 3, 65535, 'pulseFallbacks')
        self.filter_restarts = _integers(description.get('filterRestartPhases'), 3, 255, 'filterRestartPhases')
        initial = description.get('initialSound')
        if not isinstance(initial, list) or len(initial) != 3:
            raise ValueError('initialSound requires three named voice states')
        try:
            self.sounds = [VoiceState(**row) for row in initial]
            self.filter = FilterState(**description['initialFilter'])
        except (KeyError, TypeError) as error:
            raise ValueError('Invalid named sound initialization') from error
        for state in self.sounds:
            validate_voice_state(state)
        validate_filter_state(self.filter)
        if self.filter.reset_direction != self.filter_restarts[self.filter.owner]:
            raise ValueError('Initial shared-filter restart phase differs from its owner')
        words = description.get('frequencyWords')
        if not isinstance(words, dict) or not words or any(
                not isinstance(key, str) or not key.isdecimal() or str(int(key)) != key
                or not 0 <= int(key) <= 255 for key in words):
            raise ValueError('frequencyWords requires canonical decimal index strings in 0..255')
        self.frequencies = {int(key): value for key, value in words.items()}
        validate_lookup(self.frequencies)
        self.score = ScoreRuntime(self.description)
        self.writes = []
        self.call = None
        # Ghouls intake proves this descending full-window reset, including
        # readback-port bus stores; see evidence/ghouls-sid-window/audit64.writes.json.gz.
        for offset in range(28, -1, -1):
            self.write(0xd400 + offset, 8)
            self.write(0xd400 + offset, 0)

    def write(self, address, value):
        if type(address) is not int or not 0xd400 <= address <= 0xd41f:
            raise ValueError('Store lies outside the declared SID window')
        if type(value) is not int or not 0 <= value <= 255:
            raise ValueError('SID store value must be an unsigned byte')
        self.writes.append(dict(phase='init' if self.call is None else 'play', tick=self.call,
                                address=address, value=value))

    def _emit(self, writes):
        for address, value in writes:
            self.write(address, value)

    def _select_filter_restart(self):
        self.filter = replace(self.filter, reset_direction=self.filter_restarts[self.filter.owner])

    def operation(self, voice, operation, state):
        kind = Operation(operation['kind'])
        if kind == Operation.GATE:
            self.write(operation['address'], operation['value'])
        elif kind == Operation.NOTE:
            self._select_filter_restart()
            state, self.filter, writes = note_setup(state, self.filter, voice,
                                                    operation['rawNote'], self.frequencies)
            self._emit(writes)
        elif kind == Operation.REST:
            state = replace(state, rest_remaining=state.rest_reload)
        else:
            state = self.command(voice, operation['command'], operation['fields'], state)
        return state

    def command(self, voice, command, fields, state):
        command = ScoreCommand(command)
        if command in VOICE_ASSIGNMENTS:
            return replace(state, **{target: fields[source]
                                     for source, target in VOICE_ASSIGNMENTS[command].items()})
        if command in NAVIGATION:
            return state
        if command == ScoreCommand.PULSE_PARAMETERS:
            default = _word(fields, 'pulseDefault')
            return replace(state, pulse_step=fields['pulseStep'], pulse_default=default,
                           pulse_word=default or self.pulse_fallbacks[voice])
        if command == ScoreCommand.REST_PARAMETERS:
            return replace(state, gate_enabled=1, rest_reload=fields['restReload'])
        if command == ScoreCommand.SID_STORE_LIST:
            for store in fields['stores']:
                self.write(store['address'], store['value'])
        elif command == ScoreCommand.WAVEFORM:
            waveform = fields['waveform']
            phase = 255 if waveform & 64 else 1
            self.write(0xd404 + 7 * voice, waveform)
            return replace(state, waveform=waveform, pulse_direction=phase, pulse_restart=phase)
        elif command == ScoreCommand.ONSET_PARAMETERS:
            return replace(state, onset_delay=fields['onsetDelay'], onset_control=fields['onsetControl'],
                           onset_frequency=_word(fields, 'onsetFrequency'))
        elif command == ScoreCommand.FILTER_PARAMETERS:
            self.filter_restarts[voice] = fields['filterRestartPhase']
            default = _word(fields, 'filterDefault')
            self.filter = replace(self.filter, step=fields['filterStep'], word=default, default=default,
                                  lower=_word(fields, 'filterLower'), upper=_word(fields, 'filterUpper'))
            self._select_filter_restart()
        elif command == ScoreCommand.FILTER_OWNER:
            self.filter = replace(self.filter, owner=voice)
            self._select_filter_restart()
        else:
            raise ValueError(f'Unsupported sound command: {command}')
        return state

    def play(self, call):
        if type(call) is not int or call != (0 if self.call is None else self.call + 1):
            raise ValueError('Play calls must advance consecutively from zero')
        self.call = call
        for voice in range(3):
            if self.score.voices[voice].enabled < 128:
                continue
            state = self.sounds[voice]
            for function in (onset_step, frequency_step, note_step, pulse_step):
                result = function(state, voice, self.frequencies) if function is note_step else function(state, voice)
                state = result.state
                self._emit(result.writes)
            self.sounds[voice] = self.score.begin_voice(voice, call, state, self.operation)
        self._select_filter_restart()
        self.filter, writes, _ = filter_step(self.filter)
        self._emit(writes)

    def state(self):
        return dict(score=[asdict(voice) for voice in self.score.voices],
                    sounds=[asdict(state) for state in self.sounds],
                    filter=asdict(self.filter), filterRestartPhases=list(self.filter_restarts))


def compute_player(description, *, calls):
    if type(calls) is not int or not 1 <= calls <= 100000:
        raise ValueError('Expected 1..100000 consecutive play calls')
    player = GhoulsPlayer(description)
    for call in range(calls):
        player.play(call)
    return dict(writes=player.writes, calls=calls, state=player.state())
