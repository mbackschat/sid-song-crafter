"""Independent numeric decoder for Ghostbusters' private speech descriptors."""

from enum import Enum, IntEnum
import hashlib


SOURCE_SHA = 'f7f05616972d7fd5ad31df91284edbf4e0917d39422f8d004d50b40501a0dcde'


class Handler(IntEnum):
    FORWARD = 0xf083
    REVERSE = 0xf0a4
    GAP_START = 0xf0c3
    GAP_WAIT = 0xf0d9
    STOP = 0xf0e1


class Encoding(Enum):
    NIBBLES = 'nibbles'
    TWO_BIT = 'two-bit'
    TWO_BIT_FIXED = 'two-bit-fixed'
    ONE_BIT = 'one-bit'


class Update(Enum):
    INTERPOLATE = 'interpolate'
    RAMP = 'ramp'
    NONE = 'none'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def private_source_memory(data):
    require(hashlib.sha256(data).hexdigest() == SOURCE_SHA, 'Ghostbusters speech source fingerprint differs')
    memory = bytearray(65536)
    memory[0x900d:0xa835] = data[126:]
    memory[0xf080:0xff9c] = memory[0x9124:0xa040]
    return bytes(memory)


def unpack_wave(data, count, encoding):
    """Decode one buffer, preserving the source format's duplicated first sample.

    Runtime $F267/$F2E4/$F372/$F3E2 use the first symbol as a scale or
    boundary marker. Scale zero aliases mutable code at $F2D4; reject it
    instead of inventing a portable amplitude table for that unsupported case.
    """
    require(isinstance(encoding, Encoding), 'Choose a supported speech encoding')
    groups = 2 if encoding is Encoding.NIBBLES else 8 if encoding is Encoding.ONE_BIT else 4
    require(type(count) is int and count > 0 and count % groups == 0, 'Wave block length is not aligned')
    needed = count // groups
    require(len(data) >= needed, 'Truncated speech wave block')
    if encoding in (Encoding.TWO_BIT, Encoding.TWO_BIT_FIXED):
        scale = 1 if encoding is Encoding.TWO_BIT_FIXED else data[0] & 3
        require(scale != 0, 'Speech scale zero aliases source code and is unsupported')
        levels = {1: (12, 14, 16, 18), 2: (8, 12, 16, 20), 3: (2, 10, 18, 26)}[scale]
    result = []
    for index, value in enumerate(data[:needed]):
        if encoding is Encoding.NIBBLES:
            samples = [(value & 15) * 2, (value >> 4) * 2]
        elif encoding is Encoding.ONE_BIT:
            samples = [16 if value & (1 << bit) else 14 for bit in range(8)]
        else:
            samples = [levels[(value >> shift) & 3] for shift in (0, 2, 4, 6)]
        if index == 0:
            samples[0] = samples[1]
        result.extend(samples)
    return result, needed


class SpeechSynth:
    """Compute NMI handler/output order without replaying a captured amplitude stream.

    The input memory contains private encoded speech data. This oracle models
    descriptor and buffer semantics, not CPU execution time or CIA scheduling.
    Keep its output local because it can reconstruct the reference speech.
    """

    def __init__(self, memory):
        require(len(memory) == 65536, 'Speech memory must contain 65536 bytes')
        self.memory = bytes(memory)
        self.buffer = [0] * 128
        self.dictionary = self.read_word(0xf4e7)
        self.next_handler = Handler.FORWARD
        self.current_base = self.memory[0xf4db]
        self.length = self.memory[0xf4dc]
        self.gap = self.memory[0xf4dd]
        self.block_count = self.memory[0xf4de]
        self.repeat_reload = self.memory[0xf4df]
        self.repeat_count = self.memory[0xf4e0]
        self.ramp_length = self.memory[0xf4e1]
        self.ramp_step = self.memory[0xf4e2]
        self.previous_base = self.memory[0xf4e3]
        self.pitch_count = self.memory[0xf4e4]
        self.pitch_value = self.memory[0xf4e5]
        self.pitch_delta = 0
        self.header = 0
        self.wave_pointer = self.pitch_pointer = self.sample_pointer = 0
        self.encoding = Encoding.NIBBLES
        self.update = Update.INTERPOLATE
        self.special_wave = None
        self.handler = Handler.STOP
        self.finished = True
        self.forward_pointer = self.reverse_pointer = 0
        self.forward_count = self.reverse_count = self.gap_count = 0

    def read_word(self, address):
        require(0 <= address < 65535, 'Speech pointer is outside memory')
        return self.memory[address] | self.memory[address + 1] << 8

    def start(self, command):
        require(command in (1, 3), 'This source study supports opening commands 1 and 3')
        require(self.finished, 'Finish the current speech command before starting another')
        descriptor = self.dictionary + 4 * command
        self.pitch_pointer = (self.dictionary + self.read_word(descriptor)) & 65535
        self.wave_pointer = (self.dictionary + self.read_word(descriptor + 2)) & 65535
        self.pitch_count, self.header, self.current_base = 255, 0, 0
        self.handler, self.gap_count = Handler.GAP_START, 1
        self.finished = False
        self.load_block()
        self.new_wave()

    def load_block(self):
        if self.header & 0x20:
            self.special_wave = 'stop'
            return
        address = self.wave_pointer
        require(address + 4 <= len(self.memory), 'Truncated speech descriptor')
        self.header, timing = self.memory[address:address + 2]
        self.repeat_reload = self.header | 0xf0
        self.block_count = (timing >> 3) | 0xe0
        self.special_wave = None
        if timing & 4:
            self.update, self.special_wave = Update.NONE, 'silence'
        else:
            self.sample_pointer = (self.dictionary + self.read_word(address + 2)) & 65535
            self.next_handler = Handler.FORWARD
            mode = timing & 3
            if mode < 2:
                self.ramp_length = (self.header & 0x40) or 0x20
                self.ramp_step = self.ramp_length >> 3
                self.update, self.gap = Update.RAMP, 0
                self.encoding = Encoding.ONE_BIT if mode == 1 else Encoding.TWO_BIT_FIXED
            else:
                self.length = (8, 16, 24, 32)[self.header >> 6]
                self.update = Update.INTERPOLATE
                self.encoding = Encoding.TWO_BIT if mode == 3 else Encoding.NIBBLES
        self.wave_pointer = (address + 4) & 65535

    def new_wave(self):
        self.repeat_count = self.repeat_reload
        base = (self.current_base & 0x40) ^ 0x40
        if self.special_wave == 'stop':
            self.next_handler = Handler.STOP
        elif self.special_wave == 'silence':
            self.next_handler, self.gap = Handler.GAP_START, 0x80
        else:
            if self.update is Update.RAMP:
                self.current_base = base
                self.length = self.ramp_length
            else:
                self.previous_base = base
            values, consumed = unpack_wave(self.memory[self.sample_pointer:], self.length, self.encoding)
            require(base + len(values) <= len(self.buffer), 'Speech buffer write would overlap executable code')
            self.buffer[base:base + len(values)] = values
            self.sample_pointer = (self.sample_pointer + consumed) & 65535
        # $F18F/$F192 are tail jumps: ramp decoders return directly, bypassing
        # $F19E interpolation/pitch work. Other decode modes pass through it.
        if self.update is Update.RAMP and self.special_wave is None:
            return
        if self.special_wave is not None:
            return
        if self.header & 0x10:
            self.header ^= 0x10
            self.current_base = self.previous_base
        else:
            self.interpolate()
        self.update_pitch()

    def interpolate(self):
        destination = ((self.current_base & 0x40) ^ 0x40) | 0x20
        require(max(self.previous_base, self.current_base, destination) + self.length <= len(self.buffer),
                'Speech interpolation would overlap executable code')
        for index in range(self.length):
            self.buffer[destination + index] = (self.buffer[self.previous_base + index] + self.buffer[self.current_base + index] + 1) // 2
        self.current_base = destination

    def update_pitch(self):
        self.pitch_count = (self.pitch_count + 1) & 255
        if self.pitch_count == 0:
            require(self.pitch_pointer + 2 <= len(self.memory), 'Truncated speech pitch descriptor')
            first, second = self.memory[self.pitch_pointer:self.pitch_pointer + 2]
            self.pitch_value = first & 0xfe
            self.pitch_count = 0xe0 | ((first & 1) << 4) | (second >> 4)
            self.pitch_delta = (-12, -10, -8, -6, -4, -2, -1, 0, 1, 2, 4, 6, 8, 10, 12, 14)[second & 15]
            self.pitch_pointer += 2
        else:
            self.pitch_value = (self.pitch_value + self.pitch_delta) & 255
        self.gap = self.pitch_value >> 1

    def complete_period(self):
        self.handler = self.next_handler
        self.forward_pointer = self.current_base
        self.forward_count = self.reverse_count = self.length
        self.gap_count = self.gap
        self.repeat_count = (self.repeat_count + 1) & 255
        if self.repeat_count == 0:
            self.block_count = (self.block_count + 1) & 255
            if self.block_count == 0:
                self.load_block()
            self.new_wave()
        elif self.update is Update.INTERPOLATE:
            if self.previous_base != self.current_base:
                self.interpolate()
            self.update_pitch()
        elif self.update is Update.RAMP:
            if self.length != 16:
                self.length = (self.length - self.ramp_step) & 255
                self.current_base = (self.current_base + self.ramp_step) & 255
            else:
                self.current_base &= 0x40
                self.length = self.ramp_length

    def tick(self):
        require(not self.finished, 'Speech command has already stopped')
        value = None
        if self.handler is Handler.FORWARD:
            value = self.buffer[self.forward_pointer] >> 1
            self.forward_count = (self.forward_count - 1) & 255
            if self.forward_count:
                self.forward_pointer += 1
            else:
                self.handler, self.reverse_pointer = Handler.REVERSE, self.forward_pointer
        elif self.handler is Handler.REVERSE:
            value = self.buffer[self.reverse_pointer] >> 1
            self.reverse_count = (self.reverse_count - 1) & 255
            if self.reverse_count:
                self.reverse_pointer -= 1
            elif self.gap_count:
                self.handler = Handler.GAP_START
            else:
                self.complete_period()
        elif self.handler in (Handler.GAP_START, Handler.GAP_WAIT):
            value = 7 if self.handler is Handler.GAP_START else None
            self.gap_count = (self.gap_count - 1) & 255
            if self.gap_count:
                self.handler = Handler.GAP_WAIT
            else:
                self.complete_period()
        else:
            value, self.finished = 7, True
        return value
