"""Compile the frame-rate Shades variant to a PAL VBI PSID and audit it at 19,656 cycles per call.

compose-shades.py hard-wires the CIA route in three places: PSID speed word 1,
the driver's `STA $DC05` timer-high command and its CIA-window audit. Instead of
changing that supported tool, this wrapper reuses its parameter tables and
assembler on a copy of the driver source whose timer store is neutralized,
declares the VBI speed word and audits with the strict VBI profile of
scripts/psid_audit.py. Everything else in the player is the same assembly.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))

from psid_audit import audit_psid  # noqa: E402
from shades_player import Player, compute  # noqa: E402
from sid_assembler import assemble  # noqa: E402
from verify_player import cpu_type, require  # noqa: E402


spec = importlib.util.spec_from_file_location('compose_shades', ROOT / 'scripts/compose-shades.py')
compose = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compose)

TIMER_STORE = '  STA $DC05\n'
TIMER_NEUTRAL = '  NOP\n  NOP\n  NOP\n'
TIMER_ADDRESS = 0xdc05


def driver_source():
    source = '\n'.join((ROOT / 'songs/players' / name).read_text() for name in ('shades.asm', 'shades-effects.asm'))
    require(source.count(TIMER_STORE) == 1, 'Expected exactly one timer-high store in the Shades driver')
    return source.replace(TIMER_STORE, TIMER_NEUTRAL)


def build(score, programs):
    """Return a VBI PSID and build facts for editable frame-rate score/program descriptions."""
    player = Player(score, programs)
    generated, state_bytes, block_count, token_count = compose.parameters(score, player)
    constants = dict(SD_STATE_BYTES=state_bytes, SD_STOP_LO=player.stop_call & 255, SD_STOP_HI=player.stop_call >> 8)
    source = driver_source() + '\n' + generated
    cpu_type()
    payload, symbols, listing = assemble(source, constants, load=compose.LOAD_ADDRESS)
    require(compose.LOAD_ADDRESS + len(payload) <= 0xa000, 'Payload exceeds callable RAM')
    header = bytearray(124)
    header[:4] = b'PSID'
    # Same header as compose-shades.build except the speed word: zero declares VBI/raster calls.
    for offset, value in ((4, 2), (6, 124), (8, compose.LOAD_ADDRESS), (10, symbols['entry_init']),
                          (12, symbols['entry_play']), (14, 1), (16, 1), (118, 0x14)):
        struct.pack_into('>H', header, offset, value)
    struct.pack_into('>I', header, 18, 0)
    for offset, value in ((22, 'Shades frame-rate variant'), (54, 'SID Song Crafter'),
                          (86, '2026 engine-audibility study')):
        header[offset:offset + 31] = value.encode('ascii')[:31].ljust(31, b'\0')
    return bytes(header) + payload, dict(symbols=symbols, source=source, listing=listing, payloadBytes=len(payload),
                                         loadAddress=compose.LOAD_ADDRESS, stopCall=player.stop_call,
                                         stateBytes=state_bytes, patternTokens=token_count,
                                         orders=len(score['orders']), blocks=block_count,
                                         originalDriverIncluded=False, registerDumpPlayback=False)


def run(score_path, programs_path, output):
    score_path, programs_path, output = Path(score_path), Path(programs_path), Path(output)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh output directory')
    score_data, program_data = score_path.read_bytes(), programs_path.read_bytes()
    score, programs = json.loads(score_data), json.loads(program_data)
    sid, built = build(score, programs)
    require(int.from_bytes(sid[18:22], 'big') == 0 and int.from_bytes(sid[118:120], 'big') == 0x14,
            'Frame variant must declare VBI speed and explicit PAL MOS6581')
    count = built['stopCall'] + 1
    audit, writes = audit_psid(sid, count)
    require(audit['maximumPlayCycles'] <= audit['frameCycleBudget'] and audit['initWriteCount'] == 0,
            'Frame variant violates the VBI call budget or writes during init')
    require(all(row['address'] != TIMER_ADDRESS for row in writes), 'Frame variant must not touch the CIA timer')
    # The semantic model still schedules the timer-high command; the VBI player deliberately omits it.
    expected = [row for row in compute(score, programs, calls=count, include_stop=True) if row['address'] != TIMER_ADDRESS]
    identity = lambda rows: [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]
    require(identity(expected) == identity(writes), 'Compiled ordered SID stores differ from the semantic model')
    output.mkdir(parents=True)
    (output / 'reconstructed.sid').write_bytes(sid)
    (output / 'player.asm').write_text(built.pop('source'))
    (output / 'player.listing').write_text(built.pop('listing'))
    built.pop('symbols')
    report = dict(scorePath=str(score_path.resolve()), programsPath=str(programs_path.resolve()),
                  scoreSha256=hashlib.sha256(score_data).hexdigest(),
                  programsSha256=hashlib.sha256(program_data).hexdigest(),
                  sidSha256=hashlib.sha256(sid).hexdigest(), playCalls=count,
                  speedWord=0, timingDeclaration='PSID speed 0: one play call per PAL video frame (VBI/raster)',
                  timerStoreNeutralized='songs/players/shades.asm sd_select `STA $DC05` replaced by three NOPs in the assembled copy only',
                  orderedStoreComparison=dict(matchedStores=len(writes), fields=['phase', 'tick', 'address', 'value'],
                                              excluded='$DC05 timer-high stores (CIA cadence only)'),
                  limits='Independent compiled state computation and strict VBI CPU audit; no bus timing, audio or listening claim.',
                  **built)
    for name, value in (('build.json', report), ('audit.json', audit), ('writes.json', writes)):
        with (output / name).open('x') as handle:
            json.dump(value, handle, indent=None if name == 'writes.json' else 2, allow_nan=False)
            handle.write('\n')
    return report, audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('score', type=Path)
    parser.add_argument('--programs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report, audit = run(args.score, args.programs, args.output)
    print(json.dumps({key: report[key] for key in ('sidSha256', 'playCalls', 'payloadBytes', 'speedWord', 'orderedStoreComparison')}, indent=2))
    print(f"Audited {audit['playCalls']} calls; peak {audit['maximumPlayCycles']}/{audit['frameCycleBudget']} cycles at {audit['callRateHz']:.3f} Hz")


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f'Frame variant build failed: {error}')
