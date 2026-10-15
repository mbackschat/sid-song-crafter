"""Compute Ghostbusters music from editable score and patches, without replay."""

from copy import deepcopy
from dataclasses import asdict, fields
import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from sid_clock import NTSC_FRAME_CYCLES


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


score = load_module('ghostbusters_player_score', 'score.py')
programs = load_module('ghostbusters_player_programs', 'programs.py')
TARGET = dict(clock='ntsc', sidModel='MOS6581', sidBase=0xd400, frameCycles=NTSC_FRAME_CYCLES)
VOLUME_POLICY = dict(autoNibble=15, subtractFrom=109, orderCursorVoice=0, halfVolume=False)


def numbered(values, name, maximum):
    if not isinstance(values, dict):
        raise ValueError(f'{name} requires a numeric-key mapping')
    result = {}
    for key, value in values.items():
        if type(key) is int:
            index = key
        elif isinstance(key, str) and key.isdecimal():
            index = int(key)
        else:
            raise ValueError(f'{name} has a nonnumeric key')
        score.byte(index, f'{name} index', maximum)
        if index in result:
            raise ValueError(f'{name} has duplicate numeric keys')
        result[index] = value
    return result


def sound_data(description):
    if description.get('schema') != 'ghostbusters-sound-v1':
        raise ValueError('Expected ghostbusters-sound-v1')
    if set(description) - {'schema', 'target', 'patches', 'frequencies', 'volumePolicy', 'sourceEvidence', 'limits'}:
        raise ValueError('Unknown sound fields')
    if description['target'] != TARGET or description['volumePolicy'] != VOLUME_POLICY:
        raise ValueError('Sound requires the declared NTSC target and native shared-volume policy')
    patches = {}
    expected = {field.name for field in fields(programs.Patch)}
    for index, values in numbered(description['patches'], 'patches', 8).items():
        if set(values) != expected:
            raise ValueError('Patch requires exactly its six numeric sound fields')
        for field, value in values.items():
            score.byte(value, field)
        patches[index] = programs.Patch(**values)
    frequencies = numbered(description['frequencies'], 'frequencies', 95)
    for index, value in frequencies.items():
        score.byte(value, f'frequency {index}', 65535)
    return patches, frequencies


def from_components(scored, sound, initial_cached_controls=(0, 0, 0), *, calls=13961):
    return dict(schema='ghostbusters-music-v1', target=deepcopy(TARGET), range=dict(auditCalls=calls),
                score=deepcopy(scored), sound=deepcopy(sound),
                initialSound=dict(cachedControls=list(initial_cached_controls)))


def validate(composition):
    if composition.get('schema') != 'ghostbusters-music-v1':
        raise ValueError('Expected ghostbusters-music-v1')
    if set(composition) - {'schema', 'target', 'range', 'score', 'sound', 'initialSound',
                           'sourceEvidence', 'title', 'author', 'released'}:
        raise ValueError('Unknown composition fields')
    if composition['target'] != TARGET:
        raise ValueError('Music component requires explicit 263-line NTSC MOS6581 at $D400')
    if set(composition['range']) != {'auditCalls'}:
        raise ValueError('Range requires auditCalls')
    declared = score.byte(composition['range']['auditCalls'], 'auditCalls', 16000)
    if not declared:
        raise ValueError('Choose 1..16000 declared music calls')
    score.validate(composition['score'])
    patches, frequencies = sound_data(composition['sound'])
    initial = composition['initialSound']
    if set(initial) != {'cachedControls'} or not isinstance(initial['cachedControls'], list) or len(initial['cachedControls']) != 3:
        raise ValueError('Initial sound owns only three cached controls; score owns note/header/remaining/instrument')
    for control in initial['cachedControls']:
        score.byte(control, 'Initial cached control')
    return declared, patches, frequencies


def context_frequencies(inputs, patch, bank, kind, phase):
    index = inputs.note & 127
    if kind == 'onset':
        needed = () if inputs.header & 64 else (index,)
    elif not patch.vibrato_shift or phase & 3 == 0 and inputs.remaining & 128:
        needed = ()
    else:
        needed = (index, index + 1)
    return {note: programs.frequency(bank, note) for note in needed}


def compute(composition, *, calls=None, contexts=False):
    """Consume descending score actions and keep sound-owned control caches separate.

    Native $942E reset skips all remaining voices but retains caches and phase;
    a forced per-voice sound loop would add stores that the source never makes.
    Volume uses the action's captured cursor, before later voice-zero updates.
    These emitted port shadows do not model the SID's analogue/internal state.
    Speech and full-machine interrupt scheduling are separate components.
    """
    declared, patches, frequencies = validate(composition)
    calls = declared if calls is None else score.byte(calls, 'Diagnostic calls', declared)
    scheduler = score.Scheduler(composition['score'])
    cached = list(composition['initialSound']['cachedControls'])
    initial = dict(score=deepcopy(composition['score']['initialState']), cachedControls=list(cached))
    writes, returns, records, reset_calls = [], [], [], []
    last_controls = [0, 0, 0]

    def emit(items, tick):
        for address, value in items:
            writes.append(dict(phase='init' if tick is None else 'play', tick=tick, address=address, value=value))
            if address in (0xd404, 0xd40b, 0xd412):
                last_controls[(address - 0xd404) // 7] = value

    emit(((address, 0) for address in range(0xd417, 0xd3ff, -1)), None)
    for tick in range(calls):
        current = scheduler.step()
        row_states = {row['voice']: row['state'] for row in current['rows']}
        reset_calls.extend(reset['tick'] for reset in current['resets'])
        for action in current['actions']:
            voice, stage = action['voice'], action['stage']
            if stage == 'volume':
                output = programs.volume_write(action['nibble'], action['voice0OrderCursor'])
                emit(output, tick)
                if contexts:
                    records.append(dict(kind='volume', call=tick, voice=voice, physicalVoice=voice + 1,
                        packed=action['nibble'] << 4 | row_states[voice]['instrument'],
                        orderCursorVoice0=action['voice0OrderCursor'], half=False, writes=output, path='volume'))
                continue
            state = action['state']
            instrument = state['instrument']
            if instrument not in patches:
                raise ValueError(f'Missing selected patch {instrument}')
            patch = patches[instrument]
            inputs = programs.VoiceInputs(state['note'], state['header'], state['remaining'], cached[voice])
            kind = 'onset' if stage == 'onset' else 'body'
            before_control = last_controls[voice]
            result = (programs.onset(inputs, patch, frequencies, voice) if kind == 'onset' else
                      programs.body(inputs, patch, frequencies, voice, action['phase']))
            emit(result.writes, tick)
            cached[voice] = result.cached_control
            if contexts:
                records.append(dict(kind=kind, call=tick, voice=voice, physicalVoice=voice + 1,
                    inputs=asdict(inputs), instrument=instrument, patch=asdict(patch),
                    frequencies=context_frequencies(inputs, patch, frequencies, kind, action['phase']),
                    phase=action['phase'], mute=0, lastWrittenControlBefore=before_control,
                    cachedControl=result.cached_control, writes=result.writes, path=result.path))
        returns.append(dict(tick=tick, score=current['returned'], cachedControls=list(cached)))
    return dict(initial=initial, writes=writes, returns=returns, contexts=records, resetCalls=reset_calls)


def initial_state(composition):
    return compute(composition, calls=0)['initial']
