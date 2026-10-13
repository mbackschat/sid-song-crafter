"""Inspect PSID/RSID v2 declarations without executing or exporting source bytes."""

import argparse
import hashlib
import json
from pathlib import Path

from psid_profile import psid_profile


def inspect_sid(data, *, subtune, host_base=None):
    """Read structural metadata and separately assess the existing callable profile.

    Field layout follows libsidplayfp 3.1.1 src/sidtune/PSID.cpp. Timing is a
    header declaration, not an observed rate. RSID's reserved zero speed word
    does not mean VBI. This is not a complete SID format validator or an audit.
    """
    if len(data) < 124 or data[:4] not in (b'PSID', b'RSID'):
        raise ValueError('Expected a complete PSID/RSID v2 header')
    word = lambda offset: int.from_bytes(data[offset:offset + 2], 'big')
    if word(4) != 2:
        raise ValueError('Intake currently supports PSID/RSID version 2 only')
    offset, songs, default = word(6), word(14), word(16)
    if not 124 <= offset < len(data):
        raise ValueError('Data offset must follow the header and precede payload')
    if not 1 <= songs <= 256 or not 1 <= default <= songs:
        raise ValueError('Invalid subtune count or default')
    if type(subtune) is not int or not 1 <= subtune <= songs:
        raise ValueError('Select an explicit one-based subtune within the declared count')
    load = word(8)
    payload_offset = offset
    if load == 0:
        if len(data) < offset + 3:
            raise ValueError('Embedded load address requires two bytes and a payload')
        load = int.from_bytes(data[offset:offset + 2], 'little')
        payload_offset += 2
    size = len(data) - payload_offset
    if load + size > 65536:
        raise ValueError('Payload extends beyond C64 address space')
    flags = word(118)
    speed = int.from_bytes(data[18:22], 'big')
    magic = data[:4].decode('ascii')
    if magic == 'RSID':
        timing = 'machine-controlled'
    elif flags & 1:
        timing = 'MUS-specific'
    else:
        # SidTuneBase.cpp selectSong wraps PlaySID-specific entries; ordinary v2
        # convertOldStyleSpeedToTables retains bit 31 for every subtune above 32.
        bit = (subtune - 1) & 31 if flags & 2 else min(subtune - 1, 31)
        timing = 'CIA1 Timer A' if speed & (1 << bit) else 'VBI'
    try:
        profile = psid_profile(data, subtune=subtune, profile='pal-banked', host_base=host_base)
        support = dict(profile='pal-banked', accepted=True, reason=None, hostBase=profile['hostBase'])
    except ValueError as error:
        support = dict(profile='pal-banked', accepted=False, reason=str(error))
    if host_base is not None:
        support['requestedHostBase'] = host_base
    text = lambda start: data[start:start + 32].split(b'\0', 1)[0].decode('latin-1')
    return dict(schemaVersion=1, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
        format=magic, version=2, dataOffset=offset, headerLoadAddress=word(8),
        loadAddress=load, payloadBytes=size, endAddressExclusive=load + size,
        initAddress=word(10), playAddress=word(12), subtunes=songs,
        defaultSubtune=default, selectedSubtune=subtune, speedWord=speed,
        flags=flags, clockDeclaration=('unknown', 'PAL', 'NTSC', 'PAL/NTSC')[(flags >> 2) & 3],
        sidModelDeclaration=('unknown', 'MOS6581', 'MOS8580', 'MOS6581/MOS8580')[(flags >> 4) & 3],
        selectedTimingDeclaration=timing, title=text(22), author=text(54), released=text(86),
        callableProfile=support,
        limits='Header declarations and current profile admission only; no driver execution, measured cadence, subtune-role identification or listening verdict.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sid', type=Path)
    parser.add_argument('--subtune', type=int, required=True)
    parser.add_argument('--host-base', type=lambda value: int(value, 0), help='Assess an explicit pal-banked host address; decimal or 0x-prefixed')
    parser.add_argument('--output', type=Path, help='Exclusive-create JSON report; omit for stdout')
    args = parser.parse_args()
    report = inspect_sid(args.sid.read_bytes(), subtune=args.subtune, host_base=args.host_base)
    report['sourcePath'] = str(args.sid)
    report['inspectorSha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report['profileSha256'] = hashlib.sha256(Path(__file__).with_name('psid_profile.py').read_bytes()).hexdigest()
    content = json.dumps(report, indent=2) + '\n'
    if args.output is None:
        print(content, end='')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x') as output:
            output.write(content)


if __name__ == '__main__':
    main()
