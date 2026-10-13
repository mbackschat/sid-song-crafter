"""Schedule editable Rambo loader score instructions without executing its driver."""

from copy import deepcopy
from enum import Enum


class InstructionKind(str, Enum):
    ROW = 'row'
    RETURN = 'return'
    CALL = 'call'
    CALL_TRANSPOSED = 'call-transposed'
    TRANSPOSE = 'transpose'
    JUMP_TRANSPOSED = 'jump-transposed'
    LOOP = 'loop'
    NEXT = 'next'
    VOLUME = 'volume'
    WRITE_DATA = 'write-data'
    FREQUENCY = 'frequency'
    PULSE = 'pulse'
    CHORD = 'chord'
    POKE_DATA = 'poke-data'
    POKE_SOUND = 'poke-sound'
    CODE = 'code'


COPIES = {InstructionKind.VOLUME, InstructionKind.WRITE_DATA, InstructionKind.FREQUENCY,
          InstructionKind.PULSE, InstructionKind.CHORD}
UNAVAILABLE = ({InstructionKind.WRITE_DATA, InstructionKind.JUMP_TRANSPOSED},
               {InstructionKind.TRANSPOSE, InstructionKind.JUMP_TRANSPOSED,
                InstructionKind.CODE, InstructionKind.CHORD},
               {InstructionKind.PULSE, InstructionKind.CODE})


def require(ok, message):
    if not ok:
        raise ValueError(message)


def byte(value, name):
    require(type(value) is int and 0 <= value <= 255, f'{name} must be a byte')
    return value


def validate_program(program):
    require(isinstance(program, dict) and program, 'Program must be a nonempty instruction graph')
    require(all(isinstance(node_id, str) and node_id for node_id in program),
            'Instruction IDs must be nonempty strings')
    for node_id, node in program.items():
        require(isinstance(node, dict), f'Instruction {node_id} must be an object')
        try:
            kind = InstructionKind(node.get('kind'))
        except ValueError:
            raise ValueError(f'Unsupported instruction kind at {node_id}') from None
        references = []
        if kind not in (InstructionKind.RETURN, InstructionKind.JUMP_TRANSPOSED):
            references.append(node.get('next'))
        if kind in (InstructionKind.CALL, InstructionKind.CALL_TRANSPOSED,
                    InstructionKind.JUMP_TRANSPOSED):
            references.append(node.get('target'))
        require(all(isinstance(ref, str) and ref in program for ref in references),
                f'Instruction {node_id} has an unknown graph reference')
        if kind == InstructionKind.ROW:
            byte(node.get('sourceNote'), 'Row sourceNote')
            require(node['sourceNote'] < 192, 'Row sourceNote must be below 192')
            byte(node.get('duration'), 'Row duration')
        elif kind in (InstructionKind.TRANSPOSE, InstructionKind.CALL_TRANSPOSED,
                      InstructionKind.JUMP_TRANSPOSED):
            byte(node.get('transpose'), 'Transpose')
        elif kind == InstructionKind.LOOP:
            byte(node.get('repeat'), 'Loop repeat')
        elif kind in (InstructionKind.POKE_DATA, InstructionKind.POKE_SOUND):
            byte(node.get('offset'), 'Poke offset')
            byte(node.get('value'), 'Poke value')
        elif kind in COPIES or kind == InstructionKind.CODE:
            field = 'codeId' if kind == InstructionKind.CODE else 'dataId'
            require(isinstance(node.get(field), str) and node[field], f'{field} must be a nonempty string')


class ScoreRuntime:
    """Run the loader's regular REFRESH score grammar from a symbolic graph.

    The graph contains row, call/return, loop/next, transpose, copy, poke and code
    instructions. References are opaque node IDs. Optional sourceAddress and
    sourceOpcode fields are emitted as provenance only. Three named voice states
    supply cursor, remaining, transpose, stackIndex and eight stack slots with
    returnNode/repeatRemaining; they are copied on construction. A normal init
    uses remaining=1 and stackIndex=7. active_mask supplies the three active bits.

    refresh(call) visits physical voices 0/1/2. Every active entry decrements its
    row byte, including 0->255, and fetches only when the result is zero. Timed
    rows emit note initialization unless sourceNote is 95/191, then a row event
    and a sound event. A top-level return clears the active bit and skips SOUND
    for that entry; later inactive entries still emit sound. The implementation
    retains the voice-specific command availability of the pinned loader.

    duration_lookup(voiceIndex, selector) must read the live owning data bank
    for table rows. on_operation(runtime, event) runs synchronously after each
    event is retained, receiving a detached event. Copy/poke effects and SOUND
    belong to that handler. Code requires a handler and runs before cursor
    advancement, allowing the STARTMC handler to re-enter refresh(call) while
    the current row byte is zero. Morse dispatch, chip writes and sound-life
    completion are outside this scheduler; a caller must schedule the outer
    refresh invocations itself. voices and active_mask remain live for handlers
    that preserve the shared data-bank/stack/Morse aliases.
    """

    def __init__(self, program, voices, *, active_mask=7, duration_lookup=None,
                 on_operation=None, command_limit=4096, refresh_depth_limit=8):
        validate_program(program)
        require(isinstance(voices, (list, tuple)) and len(voices) == 3,
                'Score must define three physical voices')
        byte(active_mask, 'Active mask')
        require(active_mask <= 7, 'Active mask may only select three physical voices')
        require(duration_lookup is None or callable(duration_lookup), 'Duration lookup must be callable')
        require(on_operation is None or callable(on_operation), 'Operation handler must be callable')
        require(type(command_limit) is int and command_limit > 0, 'Command limit must be positive')
        require(type(refresh_depth_limit) is int and refresh_depth_limit > 0,
                'Refresh depth limit must be positive')
        for voice in voices:
            require(isinstance(voice, dict) and voice.get('cursor') in program,
                    'Voice cursor must reference a retained instruction')
            byte(voice.get('remaining'), 'Remaining row duration')
            byte(voice.get('transpose'), 'Voice transpose')
            require(type(voice.get('stackIndex')) is int and voice['stackIndex'] in (*range(9), 255),
                    'Voice stack index must be in 0..8 or 255 after the eighth call')
            stack = voice.get('stack')
            require(isinstance(stack, list) and len(stack) == 8, 'Voice stack must have eight slots')
            for slot in stack:
                require(isinstance(slot, dict) and (slot.get('returnNode') is None or
                                                    slot['returnNode'] in program),
                        'Stack return must reference a retained instruction or be None')
                byte(slot.get('repeatRemaining'), 'Stack repeat count')
        self.program = deepcopy(program)
        self.voices = deepcopy(list(voices))
        self.active_mask = active_mask
        self.duration_lookup = duration_lookup
        self.on_operation = on_operation
        self.command_limit = command_limit
        self.refresh_depth_limit = refresh_depth_limit
        self.operations = []
        self._refresh_depth = 0

    def _emit(self, operation, call, voice, node_id=None, **fields):
        event = dict(operation=operation, call=call, voiceIndex=voice, **fields)
        if node_id is not None:
            event['nodeId'] = node_id
            node = self.program[node_id]
            for field in ('sourceAddress', 'sourceOpcode'):
                if field in node:
                    event[field] = deepcopy(node[field])
        self.operations.append(deepcopy(event))
        if self.on_operation is not None:
            self.on_operation(self, deepcopy(event))

    def refresh(self, call):
        """Visit voices in physical order, allowing bounded synchronous recursion."""
        require(type(call) is int and call >= 0, 'Call must be a nonnegative integer')
        require(self._refresh_depth < self.refresh_depth_limit, 'Recursive refresh exceeds bounded depth')
        start = len(self.operations)
        self._refresh_depth += 1
        try:
            for voice in range(3):
                self.step_voice(voice, call)
        finally:
            self._refresh_depth -= 1
        return deepcopy(self.operations[start:])

    def step_voice(self, voice_index, call):
        """Consume one physical voice entry and emit its ordered semantic operations."""
        require(type(voice_index) is int and 0 <= voice_index < 3, 'Voice index must be in 0..2')
        require(type(call) is int and call >= 0, 'Call must be a nonnegative integer')
        voice = self.voices[voice_index]
        if not self.active_mask & (1 << voice_index):
            self._emit('sound', call, voice_index, remaining=voice['remaining'])
            return
        voice['remaining'] = (voice['remaining'] - 1) & 255
        if voice['remaining']:
            self._emit('sound', call, voice_index, remaining=voice['remaining'])
            return
        for _ in range(self.command_limit):
            node_id = voice['cursor']
            require(node_id in self.program, 'Voice cursor escapes retained instruction graph')
            node = self.program[node_id]
            kind = InstructionKind(node['kind'])
            require(kind not in UNAVAILABLE[voice_index],
                    f'{kind.value} is unavailable on physical voice {voice_index + 1}')
            self._emit('fetch', call, voice_index, node_id, kind=kind.value)
            if kind == InstructionKind.ROW:
                raw_note = node['sourceNote']
                note = raw_note % 96
                hold = note == 95
                if not hold:
                    self._emit('note', call, voice_index, node_id, sourceNote=raw_note,
                               note=note, transpose=voice['transpose'],
                               pitchIndex=(note + voice['transpose']) & 255)
                literal = raw_note >= 96
                if literal:
                    duration = node['duration']
                else:
                    require(self.duration_lookup is not None, 'Table row requires a live duration lookup')
                    duration = byte(self.duration_lookup(voice_index, node['duration']), 'Looked-up duration')
                voice['remaining'] = duration
                self._emit('row', call, voice_index, node_id, rowKind='hold' if hold else 'note',
                           sourceNote=raw_note, durationSelector=node['duration'],
                           durationKind='literal' if literal else 'table', value=duration)
                voice['cursor'] = node['next']
                self._emit('sound', call, voice_index, remaining=voice['remaining'])
                return
            fields = {key: deepcopy(value) for key, value in node.items()
                      if key not in ('kind', 'sourceAddress', 'sourceOpcode')}
            self._emit('command', call, voice_index, node_id, kind=kind.value, **fields)
            if kind == InstructionKind.RETURN:
                index = (voice['stackIndex'] + 1) & 255
                require(index <= 8, 'Return escapes the eight-slot stack')
                voice['stackIndex'] = index
                if index == 8:
                    self.active_mask &= ~(1 << voice_index)
                    self._emit('topReturn', call, voice_index, node_id, activeMask=self.active_mask)
                    return
                target = voice['stack'][index]['returnNode']
                require(target in self.program, 'Return reads an uninitialized stack slot')
                voice['cursor'] = target
            elif kind in (InstructionKind.CALL, InstructionKind.CALL_TRANSPOSED, InstructionKind.LOOP):
                index = voice['stackIndex']
                require(0 <= index <= 7, 'Push escapes the eight-slot stack')
                slot = voice['stack'][index]
                slot['returnNode'] = node['next']
                if kind == InstructionKind.LOOP:
                    slot['repeatRemaining'] = node['repeat']
                    voice['cursor'] = node['next']
                else:
                    voice['cursor'] = node['target']
                    if kind == InstructionKind.CALL_TRANSPOSED:
                        voice['transpose'] = node['transpose']
                voice['stackIndex'] = (index - 1) & 255
            elif kind == InstructionKind.NEXT:
                index = voice['stackIndex'] + 1
                require(0 <= index <= 7, 'Next escapes the eight-slot stack')
                slot = voice['stack'][index]
                slot['repeatRemaining'] = (slot['repeatRemaining'] - 1) & 255
                if slot['repeatRemaining']:
                    require(slot['returnNode'] in self.program, 'Next reads an uninitialized stack slot')
                    voice['cursor'] = slot['returnNode']
                else:
                    voice['stackIndex'] = index
                    voice['cursor'] = node['next']
            elif kind in (InstructionKind.TRANSPOSE, InstructionKind.JUMP_TRANSPOSED):
                voice['transpose'] = node['transpose']
                voice['cursor'] = node['target'] if kind == InstructionKind.JUMP_TRANSPOSED else node['next']
            else:
                require(kind != InstructionKind.CODE or self.on_operation is not None,
                        'A code instruction requires an explicit handler')
                voice['cursor'] = node['next']
        raise ValueError('Score commands do not reach a timed row/return within bounded expansion')
