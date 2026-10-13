"""Compute the selected three-voice Airwolf score's ordered writes, without a CPU."""

FIXED_WRITES = [(0xd418, 15), (0xd403, 40), (0xd40a, 10)]


def compute(score, calls):
    """Return stores, consumed fields and restarts; zero pitch fields mean hold.

    Duration N lasts N+1 callable updates because the original decrements
    before testing FF. Initialization consumes row zero. The terminal duration
    zero re-enters initialization within the same play call, repeating the
    fixed writes before the next first row. This models no analogue SID state.
    """
    if type(calls) is not int or calls < 0 or not score['rows']:
        raise ValueError('Expected a nonnegative call cap and nonempty score')
    writes, reads, restarts = [], [], []
    rows = score['rows']
    phase, tick = 'init', None

    def write(address, value):
        writes.append(dict(phase=phase, tick=tick, address=address, value=value))

    def fixed():
        for address, value in FIXED_WRITES:
            write(address, value)

    def read(address, value, field):
        reads.append(dict(phase=phase, tick=tick, address=address, value=value, field=field))

    def consume(row):
        duration = row['duration']
        if type(duration) is not int or not 1 <= duration <= 255 or len(row['notes']) != 3:
            raise ValueError('Rows need a nonzero duration byte and three note/hold entries')
        address = row['sourceAddress']
        read(address, duration, 'duration')
        address += 1
        for voice, note in enumerate(row['notes']):
            if note is None:
                read(address, 0, f'voice{voice}High')
                address += 1
                continue
            if type(note) is not int or not 256 <= note <= 65535:
                raise ValueError('A pitched row needs a nonzero high byte')
            read(address, note >> 8, f'voice{voice}High')
            read(address + 1, note & 255, f'voice{voice}Low')
            address += 2
            base = 0xd400 + voice * 7
            for register, value in [(5, 9 if voice == 2 else 10), (6, 0), (4, 0),
                                    (4, 0x11 if voice == 2 else 0x41),
                                    (1, note >> 8), (0, note & 255)]:
                write(base + register, value)
        return duration

    fixed()
    countdown = consume(rows[0])
    index = 1
    for tick in range(calls):
        phase = 'play'
        fixed()
        countdown = (countdown - 1) & 255
        if countdown != 255:
            continue
        if index == len(rows):
            read(score['terminatorAddress'], 0, 'duration')
            restarts.append(tick)
            index = 0
            fixed()
        countdown = consume(rows[index])
        index += 1
    return dict(writes=writes, reads=reads, restartCalls=restarts)
