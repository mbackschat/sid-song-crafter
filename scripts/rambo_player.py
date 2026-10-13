"""Compute the editable Rambo loader graph, Morse hooks and sound programs."""

from copy import deepcopy
from enum import Enum

from rambo_programs import advance_voice
from rambo_score import ScoreRuntime


class MorsePhase(str, Enum):
    READ = 'read'
    SHIFT = 'shift'
    TONE = 'tone'
    SPACE = 'space'
    GAP = 'gap'


WORD_FIELDS = {'pulseInitial': 22, 'frequency': 29, 'pulse': 35}
BYTE_FIELDS = {'frequencyDelay': 12, 'frequencyFlags': 13, 'pulseDelay': 16,
               'pulseFlags': 17, 'control': 26, 'releaseCountdown': 27, 'life': 28}
ARRAY_FIELDS = {'frequencySteps': ((0, 2, 4, 6), 2),
                'frequencyDurations': ((8, 9, 10, 11), 1),
                'pulseDurations': ((14, 15), 1), 'pulseSteps': ((18, 20), 2),
                'frequencyRemaining': ((31, 32, 33, 34), 1),
                'pulseRemaining': ((37, 38), 1)}


def numeric_array(values, length, limit, name):
    if not isinstance(values, list) or len(values) != length or any(
            type(value) is not int or not 0 <= value <= limit for value in values):
        raise ValueError(f'{name} requires {length} integers in 0..{limit}')


def validate_description(description):
    for name, width in (('initialData', 49), ('initialSound', 39)):
        blocks = description.get(name)
        if not isinstance(blocks, list) or len(blocks) != 3:
            raise ValueError(f'{name} requires three physical voice blocks')
        for block in blocks:
            numeric_array(block, width, 255, name)
    frequencies = description.get('frequencyWords')
    if not isinstance(frequencies, list) or not 1 <= len(frequencies) <= 256:
        raise ValueError('Frequency table requires 1..256 words')
    numeric_array(frequencies, len(frequencies), 65535, 'frequencyWords')
    volume = description.get('initialization', {}).get('volume')
    numeric_array([volume], 1, 15, 'Initial volume')
    morse = description.get('morse', {})
    letters = morse.get('letters')
    if not isinstance(letters, list) or not letters or letters[-1] != 0:
        raise ValueError('Morse letters require a terminal zero')
    if any(type(letter) is not int or letter % 2 or not 130 <= letter <= 180 for letter in letters[:-1]):
        raise ValueError('Morse letters require doubled uppercase ASCII codes')
    numeric_array(morse.get('codes'), 26, 255, 'Morse code table')
    numeric_array(morse.get('pitchChanges'), 2, 65535, 'Morse pitch changes')
    numeric_array([morse.get('initialFrequency')], 1, 65535, 'Morse initial frequency')
    banks = description.get('dataBanks')
    if not isinstance(banks, dict):
        raise ValueError('Expected numeric data banks')
    for node in description.get('program', {}).values():
        kind = node.get('kind')
        if kind == 'row' and node.get('sourceNote', 192) < 96:
            if type(node.get('duration')) is not int or not 0 <= node['duration'] <= 16:
                raise ValueError('Duration table selectors cannot enter stack aliases')
        elif kind == 'poke-data':
            offset = node.get('offset')
            if type(offset) is not int or not (0 <= offset <= 48 or offset == 73):
                raise ValueError('Data poke into a stack alias is unsupported')
        elif kind == 'poke-sound':
            if type(node.get('offset')) is not int or not 0 <= node['offset'] <= 38:
                raise ValueError('Sound poke must remain within its 39-byte block')
        elif kind in ('volume', 'frequency', 'pulse', 'chord', 'write-data'):
            values = banks.get(node.get('dataId'))
            widths = {'volume': (5,), 'frequency': (14,), 'pulse': (10,), 'chord': (10,), 'write-data': (29,)}
            if not isinstance(values, list) or len(values) not in widths[kind]:
                raise ValueError(f'Invalid {kind} data-bank width')
            numeric_array(values, len(values), 255, kind)
        elif kind == 'code' and node.get('codeId') not in (
                'increment-transpose', 'morse-pitch-one', 'morse-pitch-two', 'start-morse'):
            raise ValueError('Unknown code hook')


def sound_state(block):
    result = {name: block[offset] for name, offset in BYTE_FIELDS.items()}
    result.update({name: block[offset] | block[offset + 1] << 8 for name, offset in WORD_FIELDS.items()})
    for name, (offsets, size) in ARRAY_FIELDS.items():
        result[name] = [block[offset] if size == 1 else block[offset] | block[offset + 1] << 8 for offset in offsets]
    return result


def store_sound(block, state):
    for name, offset in BYTE_FIELDS.items():
        block[offset] = state[name]
    for name, offset in WORD_FIELDS.items():
        block[offset:offset + 2] = [state[name] & 255, state[name] >> 8]
    for name, (offsets, size) in ARRAY_FIELDS.items():
        for offset, value in zip(offsets, state[name]):
            block[offset:offset + size] = [value] if size == 1 else [value & 255, value >> 8]


class LoaderPlayer:
    def __init__(self, description):
        if description.get('format') != 'rambo-loader-composition-v1':
            raise ValueError('Expected editable Rambo loader composition')
        if description.get('profile') != {'clock': 'PAL', 'sidModel': 'MOS6581', 'sidBase': 0xd400, 'callCycles': 19656}:
            raise ValueError('Loader requires its declared PAL/6581 profile')
        validate_description(description)
        self.description = deepcopy(description)
        self.data = deepcopy(description['initialData'])
        self.sound = deepcopy(description['initialSound'])
        self.frequencies = dict(enumerate(description['frequencyWords']))
        self.writes = []
        self.call = None
        self.morse_active = False
        self.morse_phase = MorsePhase.READ
        self.score = ScoreRuntime(description['program'], description['voices'],
                                  duration_lookup=lambda voice, selector: self.data[voice][32 + selector],
                                  on_operation=self.operation)
        self.write(0xd418, description['initialization']['volume'])
        for offset in range(23, -1, -1):
            self.write(0xd400 + offset, 0)

    def write(self, address, value):
        self.writes.append({'phase': 'init' if self.call is None else 'play',
                            'tick': self.call, 'address': address, 'value': value})

    def write_frequency(self, voice, frequency):
        self.write(0xd400 + voice * 7, frequency & 255)
        self.write(0xd401 + voice * 7, frequency >> 8)

    def note(self, event):
        voice = event['voiceIndex']
        data, sound = self.data[voice], self.sound[voice]
        for offset in range(4, -1, -1):
            address = 0xd402 + 7 * voice + offset
            self.write(address, 0)
            self.write(address, data[22 + offset])
        sound[26] = data[24]
        frequency = self.frequencies[event['pitchIndex']]
        sound[29:31] = [frequency & 255, frequency >> 8]
        self.write_frequency(voice, frequency)
        sound[17] = data[17]
        if sound[17]:
            sound[14:24] = data[14:24]
            sound[35:37] = sound[22:24]
            sound[37:39] = sound[14:16]
        sound[13] = data[13]
        if sound[13]:
            sound[:14] = data[:14]
            if voice != 1 and sound[13] & 8:
                sound[10] = (event['sourceNote'] + event['transpose']) & 255
                sound[12] = 255
            sound[31:35] = sound[8:12]
        sound[27:29] = data[27:29]

    def operation(self, runtime, event):
        voice = event['voiceIndex']
        operation = event['operation']
        if operation == 'note':
            self.note(event)
        elif operation == 'sound':
            state, writes = advance_voice(sound_state(self.sound[voice]), voice=voice,
                                           row_remaining=runtime.voices[voice]['remaining'],
                                           frequency_words=self.frequencies)
            store_sound(self.sound[voice], state)
            for address, value in writes:
                self.write(address, value)
        elif operation == 'command':
            kind = event['kind']
            if kind in ('volume', 'write-data', 'frequency', 'pulse', 'chord'):
                values = self.description['dataBanks'][event['dataId']]
                offset = 24 if kind == 'volume' else 14 if kind == 'pulse' else 0
                self.data[voice][offset:offset + len(values)] = values
            elif kind == 'poke-data':
                if event['offset'] == 73:
                    runtime.voices[voice]['transpose'] = event['value']
                else:
                    self.data[voice][event['offset']] = event['value']
            elif kind == 'poke-sound':
                self.sound[voice][event['offset']] = event['value']
            elif kind == 'code':
                self.code(event['codeId'])

    def code(self, code_id):
        if code_id == 'increment-transpose':
            self.score.voices[0]['transpose'] = (self.score.voices[0]['transpose'] + 1) & 255
        elif code_id in ('morse-pitch-one', 'morse-pitch-two'):
            index = 0 if code_id == 'morse-pitch-one' else 1
            self.write_frequency(0, self.description['morse']['pitchChanges'][index])
        elif code_id == 'start-morse':
            self.write(0xd406, 0xa0)
            self.write_frequency(0, self.description['morse']['initialFrequency'])
            self.morse_active = True
            self.score.voices[0]['stack'][0]['repeatRemaining'] = 0
            self.write(0xd405, 0)
            self.sound[0][28] = 0
            self.write(0xd404, 0)
            self.morse_phase = MorsePhase.READ
            self.score.refresh(self.call)
        else:
            raise ValueError(f'Unsupported score code hook: {code_id}')

    def morse(self):
        # rambload.asm MWK=DB0+65 aliases the first four score repeat counters.
        slots = self.score.voices[0]['stack']
        phase = self.morse_phase
        if phase in (MorsePhase.TONE, MorsePhase.SPACE, MorsePhase.GAP):
            slots[3]['repeatRemaining'] = (slots[3]['repeatRemaining'] - 1) & 255
            if not slots[3]['repeatRemaining'] & 128:
                self.score.refresh(self.call)
                return
            if phase == MorsePhase.TONE:
                self.write(0xd404, 32)
                slots[3]['repeatRemaining'] = 2
                phase = MorsePhase.SPACE
            elif phase == MorsePhase.GAP:
                phase = MorsePhase.READ
            else:
                slots[2]['repeatRemaining'] = (slots[2]['repeatRemaining'] - 1) & 255
                if slots[2]['repeatRemaining'] & 128:
                    slots[3]['repeatRemaining'] = 6
                    phase = MorsePhase.GAP
                else:
                    phase = MorsePhase.SHIFT
        if phase == MorsePhase.READ:
            letter = self.description['morse']['letters'][slots[0]['repeatRemaining']]
            if not letter:
                self.morse_active = False
                return
            slots[0]['repeatRemaining'] = (slots[0]['repeatRemaining'] + 1) & 255
            slots[1]['repeatRemaining'] = self.description['morse']['codes'][(letter >> 1) - 65]
            slots[2]['repeatRemaining'] = slots[1]['repeatRemaining'] & 3
            phase = MorsePhase.SHIFT
        elif phase == MorsePhase.SHIFT:
            carry = slots[1]['repeatRemaining'] & 128
            slots[1]['repeatRemaining'] = (slots[1]['repeatRemaining'] << 1) & 255
            slots[3]['repeatRemaining'] = 6 if carry else 2
            self.write(0xd404, 33)
            phase = MorsePhase.TONE
        self.morse_phase = phase
        self.score.refresh(self.call)

    def play(self, call):
        self.call = call
        if self.morse_active:
            self.morse()
        else:
            self.score.refresh(call)


def compute_player(description, *, calls=None):
    calls = description['range']['auditCalls'] if calls is None else calls
    if type(calls) is not int or not 1 <= calls <= 100000:
        raise ValueError('Expected a bounded positive call count')
    player = LoaderPlayer(description)
    for call in range(calls):
        player.play(call)
    return {'writes': player.writes, 'activeMask': player.score.active_mask,
            'sounds': [sound_state(block) for block in player.sound],
            'score': deepcopy(player.score.voices), 'morseActive': player.morse_active}
