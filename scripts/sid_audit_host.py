"""Generate the controlled fixed-PAL caller shared by CPU and VICE audits."""

from verify_player import require


DEFAULT_HOST_BASE = 0xc000
HOST_SIZE = 0x200
HARNESS_BASE = DEFAULT_HOST_BASE
COUNTER = DEFAULT_HOST_BASE + 0x100
INIT_ACTIVE = COUNTER + 2


def harness(profile, calls):
    """Return a PRG and callable-return labels for a validated execution profile.

    Return labels are the addresses after the actual JSR instructions, so the
    CPU oracle can reproduce stack introspection without executing host code.
    The instruction sequence preserves the established fixed-PAL polling ABI.
    """
    require(type(calls) is int and 1 <= calls <= 65535, 'Harness supports 1..65535 play calls')
    host_base = profile.get('hostBase', DEFAULT_HOST_BASE)
    counter, init_active = host_base + 0x100, host_base + 0x102
    code = bytearray()
    labels, branches = {}, []

    def emit(*values):
        code.extend(values)

    def absolute(opcode, address):
        emit(opcode, address & 255, address >> 8)

    def label(name):
        labels[name] = host_base + len(code)

    def branch(opcode, name):
        emit(opcode, 0)
        branches.append((len(code) - 1, name))

    banked = profile.get('profile') == 'pal-banked'
    # The strict oracle's established init assumptions remain byte-identical;
    # pal-banked additionally matches the selected raster-host entry contract.
    emit(0x78, 0xd8, 0xa2, 0xff, 0x9a)
    emit(0xa9, 0x7f)
    absolute(0x8d, 0xdc0d)
    absolute(0x8d, 0xdd0d)
    absolute(0xad, 0xdc0d)
    absolute(0xad, 0xdd0d)
    emit(0xa9, 0)
    for address in (0xd01a, 0xd011, 0xd015, counter, counter + 1):
        absolute(0x8d, address)
    if banked:
        emit(0xa9, 1)
        absolute(0x8d, init_active)
    emit(0xa9, 0x2f, 0x85, 0, 0xa9, profile.get('entryBank', 0x37), 0x85, 1,
         0xa9, profile.get('initAccumulator', 0), 0xa2, 0, 0xa0, 0)
    absolute(0x20, profile['initAddress'])
    label('init_return')
    if banked:
        emit(0xa9, 0)
        absolute(0x8d, init_active)
        label('restore_bank')
        emit(0xa9, 0x36, 0x85, 1)
    label('wait')
    emit(0xa9, 250)
    absolute(0xcd, 0xd012)
    branch(0xd0, 'wait')
    label('call')
    absolute(0x20, profile['playAddress'])
    label('play_return')
    absolute(0xee, counter)
    branch(0xd0, 'check_count')
    absolute(0xee, counter + 1)
    label('check_count')
    absolute(0xad, counter)
    emit(0xc9, calls & 255)
    branch(0xd0, 'leave')
    absolute(0xad, counter + 1)
    emit(0xc9, calls >> 8)
    branch(0xf0, 'done')
    label('leave')
    emit(0xa9, 250)
    absolute(0xcd, 0xd012)
    branch(0xf0, 'leave')
    absolute(0x4c, labels['restore_bank'] if banked else labels['wait'])
    label('done')
    absolute(0x4c, labels['done'])
    for offset, target in branches:
        distance = labels[target] - (host_base + offset + 1)
        require(-128 <= distance <= 127, 'Harness branch exceeds the relative range')
        code[offset] = distance & 255
    require(host_base + len(code) < counter, 'Harness overlaps its call counter')
    return host_base.to_bytes(2, 'little') + code, labels
