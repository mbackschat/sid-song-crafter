"""Start the computed Rambo loader at a verified score boundary, retaining its ending."""

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid
from rambo_player import LoaderPlayer
from sid_assembler import assemble
from sid_clock import clock_spec
from verify_player import require


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def registers_after(writes):
    registers = [0] * 25
    for row in writes:
        registers[row['address'] - 0xd400] = row['value']
    return registers


def rebase(description, start_call):
    require(type(start_call) is int and 0 < start_call < description['range']['auditCalls'],
            'Cut must lie inside the verified call range')
    player = LoaderPlayer(description)
    for call in range(start_call):
        player.play(call)
    require(player.score.active_mask == 7 and not player.morse_active,
            'Main entry requires three active score voices outside Morse playback')
    # LoaderPlayer.code('start-morse') resets its phase before any future Morse run.
    result = deepcopy(description)
    result['initialData'] = deepcopy(player.data)
    result['initialSound'] = deepcopy(player.sound)
    result['voices'] = deepcopy(player.score.voices)
    result['range']['auditCalls'] -= start_call
    result['sampleEntry'] = dict(sourceStartCall=start_call,
                                sourceStartSeconds=start_call / clock_spec().ticks_per_second,
                                sourceSha256=hashlib.sha256(json.dumps(description, sort_keys=True).encode()).hexdigest(),
                                limitation='Software continuation with fresh SID envelopes/oscillators, not an audio crop.')
    return result, registers_after(player.writes)


def initialize_registers(sid, banks):
    header = bytearray(sid[:124])
    load, init = struct.unpack_from('>HH', header, 8)
    address = load + len(sid) - 124
    source = f'entry:\n  JSR ${init:04x}\n'
    for chip, registers in enumerate(banks):
        # Restore controls last so fresh envelopes start with their intended ADSR.
        for offset in [n for n in range(25) if n not in (4, 11, 18)] + [4, 11, 18]:
            source += f'  LDA #${registers[offset]:02x}\n  STA ${0xd400 + chip * 32 + offset:04x}\n'
    source += '  RTS\n'
    wrapper, _, _ = assemble(source, {}, load=address)
    require(address + len(wrapper) < 0xa000, 'Entry wrapper exceeds callable RAM')
    struct.pack_into('>H', header, 10, address)
    header[22:54] = b'Rambo main music'.ljust(32, b'\0')
    return bytes(header) + sid[124:] + wrapper, source


def build(paths, output, start_call=1586):
    output = Path(output)
    require(not output.exists(), 'Choose a fresh output directory')
    require(len(paths) in (1, 2), 'Expected one or two Rambo score descriptions')
    descriptions = [json.loads(Path(path).read_text()) for path in paths]
    entries = [rebase(description, start_call) for description in descriptions]
    compiler = load_script('compose-rambo' if len(paths) == 1 else 'compose-rambo-dual')
    source_sid, _ = compiler.build(*descriptions)
    raw_sid, _ = compiler.build(*(entry[0] for entry in entries))
    sid, wrapper = initialize_registers(raw_sid, [entry[1] for entry in entries])
    count = descriptions[0]['range']['auditCalls']
    _, original = audit_psid(source_sid, count)
    audited, actual = audit_psid(sid, count - start_call)
    expected = [(row['tick'] - start_call, row['address'], row['value']) for row in original
                if row['phase'] == 'play' and row['tick'] >= start_call]
    observed = [(row['tick'], row['address'], row['value']) for row in actual if row['phase'] == 'play']
    require(expected == observed, 'Main-entry SID must preserve every remaining ordered play store')
    output.mkdir(parents=True)
    for index, (description, registers) in enumerate(entries):
        (output / f'chip-{index + 1}.json').write_text(json.dumps(description, indent=2) + '\n')
    (output / 'main.sid').write_bytes(sid)
    (output / 'entry.asm').write_text(wrapper)
    report = dict(sourceStartCall=start_call, sourceStartSeconds=start_call / clock_spec().ticks_per_second,
                  originalSidSha256=hashlib.sha256(source_sid).hexdigest(),
                  sidSha256=hashlib.sha256(sid).hexdigest(), checkedRemainingCalls=count - start_call,
                  matchedOrderedPlayStores=len(observed), audit=audited,
                  initializationRegisters=[entry[1] for entry in entries],
                  limitation='Fresh SID envelopes and oscillator phase; preserved computed score/sound state and remaining ordered play writes.',
                  inputs=[dict(path=str(path), sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest()) for path in paths])
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    (output / 'writes.json').write_text(json.dumps(actual, separators=(',', ':')) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sources', type=Path, nargs='+')
    parser.add_argument('--start-call', type=int, default=1586)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.sources, args.output, args.start_call), indent=2))
