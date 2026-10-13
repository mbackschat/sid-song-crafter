"""Compose two independent editable engines into one PAL dual-SID PSID."""

import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

from flashdance_player import compute_writes as single_writes
from psid_audit import audit_psid
from sid_assembler import assemble
from verify_player import require


ROOT = Path(__file__).resolve().parents[1]
WRAPPER_ADDRESS = 0x0400
PRIMARY_ADDRESS = 0x1000
SID_BASES = (0xd400, 0xd420)


def load_compiler():
    spec = importlib.util.spec_from_file_location('flashdance_single_compiler', ROOT / 'scripts/compose-flashdance.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


single = load_compiler()


def compatible(primary, secondary):
    require(isinstance(primary, dict) and isinstance(secondary, dict), 'Expected two composition descriptions')
    for description in (primary, secondary):
        single_writes(description, calls=1)
    require(primary['score']['profile'] == secondary['score']['profile'],
            'Dual compositions must share the same profile')
    require(primary['score']['range']['stopCall'] == secondary['score']['range']['stopCall'],
            'Dual compositions must share the same stopCall')
    require(primary['ending'] == secondary['ending'], 'Dual compositions must share the same ending')


def compute_writes(primary, secondary, *, calls=None):
    """Merge independent model stores in wrapper order: chip A, then chip B."""
    compatible(primary, secondary)
    calls = primary['score']['range']['stopCall'] if calls is None else calls
    banks = []
    for offset, description in zip((0, 32), (primary, secondary)):
        grouped = defaultdict(list)
        for row in single_writes(description, calls=calls):
            grouped[row['tick']].append(dict(row, address=row['address'] + offset))
        banks.append(grouped)
    return [row for call in [None] + list(range(calls)) for bank in banks for row in bank[call]]


def build(primary, secondary):
    """Build separate engines and a wrapper; no assembled bytes are patched."""
    compatible(primary, secondary)
    a_payload, a = single.assemble_player(primary, load_address=PRIMARY_ADDRESS, sid_base=SID_BASES[0])
    b_address = (PRIMARY_ADDRESS + len(a_payload) + 255) & ~255
    b_payload, b = single.assemble_player(secondary, load_address=b_address, sid_base=SID_BASES[1])
    wrapper_source = '''entry_init:
  JSR PRIMARY_INIT
  JSR SECONDARY_INIT
  RTS
entry_play:
  JSR PRIMARY_PLAY
  JSR SECONDARY_PLAY
  RTS
'''
    wrapper_constants = {'PRIMARY_INIT': a['symbols']['entry_init'], 'PRIMARY_PLAY': a['symbols']['entry_play'],
                         'SECONDARY_INIT': b['symbols']['entry_init'], 'SECONDARY_PLAY': b['symbols']['entry_play']}
    wrapper, symbols, listing = assemble(wrapper_source, wrapper_constants, load=WRAPPER_ADDRESS)
    a_end, b_end = PRIMARY_ADDRESS + len(a_payload), b_address + len(b_payload)
    require(WRAPPER_ADDRESS + len(wrapper) <= PRIMARY_ADDRESS <= a_end <= b_address < b_end <= 0xa000,
            'Dual engines and wrapper must occupy separate callable RAM regions')
    payload = bytearray(b_end - WRAPPER_ADDRESS)
    for address, value in ((WRAPPER_ADDRESS, wrapper), (PRIMARY_ADDRESS, a_payload), (b_address, b_payload)):
        start = address - WRAPPER_ADDRESS
        payload[start:start + len(value)] = value
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 3), (6, 124), (8, WRAPPER_ADDRESS), (10, symbols['entry_init']),
                          (12, symbols['entry_play']), (14, 1), (16, 1), (118, 0x54)):
        struct.pack_into('>H', header, offset, value)
    header[122] = 0x42
    for offset, value in ((22, 'Flashdance dual SID interpretation'), (54, 'SID Song Crafter'),
                          (86, '2026 independent interpretation')):
        header[offset:offset + 31] = value.encode('ascii')[:31].ljust(31, b'\0')
    return bytes(header) + payload, {
        'symbols': symbols, 'payloadBytes': len(payload), 'loadAddress': WRAPPER_ADDRESS,
        'stopCall': a['stopCall'], 'endCall': a['endCall'], 'sidBases': list(SID_BASES),
        'wrapperSource': wrapper_source, 'wrapperListing': listing, 'wrapperBytes': len(wrapper),
        'players': [a, b], 'originalDriverIncluded': False, 'registerDumpPlayback': False,
    }


def run(primary, secondary, output, calls=None):
    paths, output = [Path(primary), Path(secondary)], Path(output)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh output directory')
    encoded = [path.read_bytes() for path in paths]
    descriptions = [json.loads(value) for value in encoded]
    sid, built = build(*descriptions)
    calls = built['endCall'] + 1 if calls is None else calls
    expected = compute_writes(*descriptions, calls=calls)
    audit, actual = audit_psid(sid, calls)
    identity = lambda rows: [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]
    require(identity(expected) == identity(actual), 'Dual ordered SID writes differ from the computed models')
    output.mkdir(parents=True)
    (output / 'reconstructed.sid').write_bytes(sid)
    (output / 'wrapper.asm').write_text(built.pop('wrapperSource'))
    (output / 'wrapper.listing').write_text(built.pop('wrapperListing'))
    for name, engine in zip(('primary', 'secondary'), built['players']):
        (output / f'{name}.asm').write_text(engine.pop('source'))
        (output / f'{name}.listing').write_text(engine.pop('listing'))
    report = {
        'compositions': [{'path': str(path.resolve()), 'sha256': hashlib.sha256(value).hexdigest()}
                         for path, value in zip(paths, encoded)],
        'sidSha256': hashlib.sha256(sid).hexdigest(), 'playCalls': calls,
        'orderedWriteComparison': {'matchedWrites': len(actual), 'sameCallAddressValueOrder': True,
                                   'allSoundRegistersOnBothChips': True, 'exactCycleEquality': False},
        'limits': 'Independent computed chip programs under one shared PAL frame budget. Chip A executes before chip B; no bus-timing or musical-quality claim. VICE, rendering, stereo/mono comparison and listening require separate evidence.',
        **built,
    }
    for name, value in (('build.json', report), ('audit.json', audit), ('writes.json', actual)):
        with (output / name).open('x', encoding='utf-8') as target:
            json.dump(value, target, indent=None if name == 'writes.json' else 2, allow_nan=False)
            target.write('\n')
    print(f'Independent dual-SID Flashdance player: {output}')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('primary', type=Path)
    parser.add_argument('secondary', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calls', type=int, help='Override the default complete score, tail and first silent call')
    args = parser.parse_args()
    run(args.primary, args.secondary, args.output, args.calls)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, IndexError) as error:
        raise SystemExit(f'Dual Flashdance compilation failed: {error}')
