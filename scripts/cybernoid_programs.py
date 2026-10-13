"""Compute editable PWM and filter programs from the pinned Cybernoid II driver."""


def _integer(value, maximum, name):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError(f'{name} must be an integer in 0..{maximum}')


def _table(values, size, name):
    if not isinstance(values, (list, tuple)) or len(values) != size:
        raise ValueError(f'{name} must contain {size} bytes')
    for value in values:
        _integer(value, 255, name)


def advance_pulse(width: int, direction: int, age: int, fx2: int, slot=None) -> tuple[int, int]:
    """Advance one eligible PWM body, returning accumulator width and direction.

    The caller supplies the selected eight-byte slot and handles patch setup,
    output copying and later pulse overrides. Selector zero skips arithmetic.
    Archive $AB8D–$AC45 compares only high bytes and retains overshoot; its
    wrap header resets low to one at $AC34, not zero. Direction zero descends;
    any nonzero byte ascends until a boundary or stage changes it.
    """
    _integer(width, 65535, 'Pulse width')
    for value, name in ((direction, 'Pulse direction'), (age, 'Note age'), (fx2, 'FX2')):
        _integer(value, 255, name)
    if not fx2 & 7:
        return width, direction
    _table(slot, 8, 'Pulse slot')
    step = fx2 & 0xf0
    for index in (2, 4, 6):
        if age <= slot[index] & 0x7f:
            step = slot[index + 1]
            if slot[index] & 0x80:
                direction = 0
            break
    if direction:
        width = (width + step) & 65535
        if width >> 8 >= slot[1]:
            if slot[0] & 0x80:
                return ((slot[0] & 15) << 8) | 1, 1
            direction = 0
    else:
        width = (width - step) & 65535
        if width >> 8 < slot[0] & 15:
            direction = 1
    return width, direction


def advance_filter(cutoff_high: int, age: int, program) -> tuple[int, int]:
    """Return mode/volume and cutoff high for one enabled filter-program body.

    The ten-byte program holds initial cutoff, three additive steps, terminal
    cutoff, mode/volume and four age thresholds. Archive $AC97–$ACC5 tests
    thresholds in descending table-index order; keep that priority even for
    nonmonotonic parameters. Routing, shared ownership, fallback and register
    writes belong to the caller. This function does not modify cutoff low.
    """
    _integer(cutoff_high, 255, 'Cutoff high')
    _integer(age, 255, 'Note age')
    _table(program, 10, 'Filter program')
    if age >= program[9]:
        return program[5], program[4]
    for index in (8, 7, 6):
        if age >= program[index]:
            return program[5], (cutoff_high + program[index - 5]) & 255
    return program[5], program[0]
