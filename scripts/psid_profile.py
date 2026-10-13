"""Validate explicit callable PAL VBI PSID execution profiles without changing headers."""

from enum import Enum

from sid_audit_host import DEFAULT_HOST_BASE, HOST_SIZE
from verify_player import require


class ExecutionProfile(str, Enum):
    STRICT = 'strict'
    PAL_BANKED = 'pal-banked'


def psid_profile(data, *, subtune=None, profile='strict', host_base=None):
    """Return payload, chip layout, selection and entry-bank parameters.

    Strict retains the single-subtune RAM contract. PAL banked requires an
    explicit one-based selection and permits RAM through $CFFF, excluding its
    selected 512-byte caller workspace. An explicit caller base must be in
    always-visible lower RAM; the default remains $C000.
    Both profiles require callable entries and unchanged PAL VBI declarations.
    """
    require(profile in tuple(ExecutionProfile), 'Unknown PSID execution profile')
    profile = ExecutionProfile(profile)
    require(len(data) >= 0x7c and data[:4] == b'PSID', 'Audit requires a complete PSID header')
    word = lambda offset: int.from_bytes(data[offset:offset + 2], 'big')
    require(word(6) == 0x7c, 'Audit requires a $7c-byte PSID header')
    songs, default = word(14), word(16)
    if profile is ExecutionProfile.STRICT:
        require(host_base is None, 'Strict audit does not permit an explicit host placement')
        require(songs == 1 and default == 1, 'Audit requires exactly one subtune')
        require(subtune is None or type(subtune) is int and subtune == 1,
                'Strict audit permits only subtune 1')
        selected, bank, upper = 1, 0x37, 0xa000
    else:
        # libsidplayfp 3.1.1 SidTuneBase.h MAX_SONGS=256; reject malformed raw metadata instead of repairing it.
        require(1 <= songs <= 256 and 1 <= default <= songs, 'Invalid PSID subtune count or default')
        require(type(subtune) is int and 1 <= subtune <= songs,
                'PAL banked requires an explicit one-based subtune within the declared song count')
        require(host_base is None or type(host_base) is int and 0x0400 <= host_base <= 0x9e00 and host_base % 256 == 0,
                'Explicit host base must be page-aligned RAM $0400–$9e00')
        host_base = DEFAULT_HOST_BASE if host_base is None else host_base
        selected, bank, upper = subtune, 0x36, 0xd000
    require(data[18:22] == bytes(4), 'CIA timing is unsupported; use a full C64 emulator')
    if word(4) == 2:
        require(word(118) in (0x14, 0x24), 'Audit requires explicit PAL and one declared SID model without MUS/PlaySID flags')
        require(data[122:124] == bytes(2), 'PSID v2 requires zero additional-SID fields')
        sids = [{'baseAddress': 0xd400, 'model': 'MOS8580' if word(118) == 0x24 else 'MOS6581'}]
    else:
        require(word(4) == 3 and word(118) in (0x54, 0xa4) and data[122:124] == b'\x42\x00',
                'Dual-SID audit requires PSID v3 PAL with two same-model MOS6581s or MOS8580s at $d400/$d420')
        sids = [{'baseAddress': base, 'model': 'MOS6581' if word(118) == 0x54 else 'MOS8580'} for base in (0xd400, 0xd420)]
    load = word(8)
    payload = bytes(data[0x7c:])
    if load == 0:
        require(len(payload) >= 2, 'Missing embedded load address')
        load = int.from_bytes(payload[:2], 'little')
        payload = payload[2:]
    end, init, play = load + len(payload), word(10) or load, word(12)
    require(0x0400 <= load < end <= upper, f'Audit supports payloads entirely in RAM $0400–${upper - 1:04x}')
    if profile is ExecutionProfile.PAL_BANKED:
        require(end <= host_base or host_base + HOST_SIZE <= load,
                f'Payload overlaps fixed host RAM ${host_base:04x}–${host_base + HOST_SIZE - 1:04x}')
    require(load <= init < end and load <= play < end,
            'Callable init/play must lie inside the payload; IRQ players are unsupported')
    result = dict(loadAddress=load, endAddress=end, initAddress=init, playAddress=play, payload=payload,
                sidModel=sids[0]['model'], sidBases=[sid['baseAddress'] for sid in sids], sids=sids,
                subtunes=songs, defaultSubtune=default, selectedSubtune=selected,
                initAccumulator=selected - 1, entryBank=bank, profile=profile.value)
    if profile is ExecutionProfile.PAL_BANKED:
        result['hostBase'] = host_base
    return result
