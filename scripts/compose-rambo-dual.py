"""Compile two editable Rambo graphs into one PAL MOS6581 dual-SID PSID."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
from time import perf_counter

from psid_audit import audit_psid
from rambo_player import LoaderPlayer
from sid_assembler import assemble
from verify_player import require


ROOT = Path(__file__).resolve().parents[1]
WRAPPER_ADDRESS = 0x0400
PRIMARY_ADDRESS = 0x1000
SID_BASES = (0xd400, 0xd420)


def load_compiler():
    spec = importlib.util.spec_from_file_location('rambo_single_compiler', ROOT / 'scripts/compose-rambo.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


single = load_compiler()


def compatible(primary, secondary):
    require(isinstance(primary, dict) and isinstance(secondary, dict), 'Expected two composition descriptions')
    for description in (primary, secondary):
        single.compiler_contract(description)
    require(primary['profile'] == secondary['profile'], 'Dual graphs must share the same PAL/6581 profile')
    require(primary['range']['auditCalls'] == secondary['range']['auditCalls'],
            'Dual graphs must declare the same auditCalls')


def numeric_run(primary, secondary, checkpoint_calls=()):
    """Compute both graphs independently, retaining chip A then chip B store order."""
    compatible(primary, secondary)
    players = [LoaderPlayer(description) for description in (primary, secondary)]
    checkpoints = {0: [single.model_state(player) for player in players]}
    writes = []

    def append(bank, rows):
        for row in rows:
            require(0xd400 <= row['address'] <= 0xd418, 'Model store escapes its declared SID bank')
            writes.append(dict(row, address=row['address'] + bank * 32))

    for bank, player in enumerate(players):
        append(bank, player.writes)
    for call in range(primary['range']['auditCalls']):
        for bank, player in enumerate(players):
            start = len(player.writes)
            player.play(call)
            append(bank, player.writes[start:])
        if call + 1 in checkpoint_calls:
            checkpoints[call + 1] = [single.model_state(player) for player in players]
    return dict(writes=writes, checkpoints=checkpoints)


def compute_writes(primary, secondary, *, calls=None):
    compatible(primary, secondary)
    count = primary['range']['auditCalls'] if calls is None else calls
    require(type(count) is int and 1 <= count <= primary['range']['auditCalls'],
            'Requested calls exceed declared range')
    return [row for row in numeric_run(primary, secondary)['writes']
            if row['tick'] is None or row['tick'] < count]


def _build(primary, secondary):
    a_payload, a = single._assemble_player(primary, load_address=PRIMARY_ADDRESS, sid_base=SID_BASES[0])
    b_address = (PRIMARY_ADDRESS + len(a_payload) + 255) & ~255
    b_payload, b = single._assemble_player(secondary, load_address=b_address, sid_base=SID_BASES[1])
    wrapper_source = '''entry_init:
  JSR PRIMARY_INIT
  JSR SECONDARY_INIT
dual_init_done:
  RTS
entry_play:
  JSR PRIMARY_PLAY
  JSR SECONDARY_PLAY
dual_call_done:
  RTS
'''
    constants = {'PRIMARY_INIT': a['symbols']['entry_init'], 'PRIMARY_PLAY': a['symbols']['entry_play'],
                 'SECONDARY_INIT': b['symbols']['entry_init'], 'SECONDARY_PLAY': b['symbols']['entry_play']}
    wrapper, symbols, listing = assemble(wrapper_source, constants, load=WRAPPER_ADDRESS)
    a_end, b_end = PRIMARY_ADDRESS + len(a_payload), b_address + len(b_payload)
    require(WRAPPER_ADDRESS + len(wrapper) <= PRIMARY_ADDRESS < a_end <= b_address < b_end <= 0xa000,
            'Dual engines and wrapper must occupy separate callable RAM regions')
    payload = bytearray(b_end - WRAPPER_ADDRESS)
    for address, encoded in ((WRAPPER_ADDRESS, wrapper), (PRIMARY_ADDRESS, a_payload), (b_address, b_payload)):
        start = address - WRAPPER_ADDRESS
        payload[start:start + len(encoded)] = encoded
    header = bytearray(124)
    header[:4] = b'PSID'
    for offset, value in ((4, 3), (6, 124), (8, WRAPPER_ADDRESS), (10, symbols['entry_init']),
                          (12, symbols['entry_play']), (14, 1), (16, 1), (118, 0x54)):
        struct.pack_into('>H', header, offset, value)
    header[122] = 0x42
    for offset, value in ((22, 'Rambo six-voice interpretation'), (54, 'SID Song Crafter'),
                          (86, '2026 independent interpretation')):
        header[offset:offset + 31] = value.encode('ascii')[:31].ljust(31, b'\0')
    return bytes(header) + payload, dict(
        symbols=symbols, payloadBytes=len(payload), loadAddress=WRAPPER_ADDRESS,
        playCalls=primary['range']['auditCalls'], sidBases=list(SID_BASES),
        outputLayout='independent-dual-engines', chipExecutionOrder=[0, 1],
        wrapperSource=wrapper_source, wrapperListing=listing, wrapperBytes=len(wrapper),
        players=[a, b], originalDriverIncluded=False, registerDumpPlayback=False,
        runtimeScoreScheduler=True, supportedCallRange=a['supportedCallRange'],
        indefinitePlaybackSupported=False,
        endingMechanism='Independent top-level score returns and sound lifetimes; no added fade',
        zeroPageContract='Shared $E0-$FF scratch; each engine runs to completion before the next engine',
    )


def build(primary, secondary):
    numeric_run(primary, secondary)
    return _build(primary, secondary)


def read_state(memory, built):
    return [single.read_state(memory, player) for player in built['players']]


def identity(rows):
    return [(row['phase'], row['tick'], row['address'], row['value']) for row in rows]


def run(primary, secondary, output, calls=None):
    paths, output = [Path(primary), Path(secondary)], Path(output)
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh output directory')
    encoded = [path.read_bytes() for path in paths]
    descriptions = [json.loads(value) for value in encoded]
    compatible(*descriptions)
    count = descriptions[0]['range']['auditCalls'] if calls is None else calls
    require(type(count) is int and 1 <= count <= descriptions[0]['range']['auditCalls'],
            'Requested calls exceed declared range')
    selected = {call for call in (0, 1, 49, 50, 51, 10813, 10814, 10815, count - 1) if call < count}
    stages = {}
    started = perf_counter()
    numeric = numeric_run(*descriptions, checkpoint_calls={call + 1 for call in selected})
    stages['model'] = perf_counter() - started
    started = perf_counter()
    sid, built = _build(*descriptions)
    stages['assembly'] = perf_counter() - started
    checkpoints, writer_sites = [], {}
    writer_count = 0

    def observer(cpu, memory):
        nonlocal writer_count
        writer = single.check_sid_writer(cpu, memory)
        if writer is not None:
            pc, opcode, address = writer
            writer_sites.setdefault(pc, dict(opcode=opcode, addresses=set()))['addresses'].add(address)
            writer_count += 1
        boundary = (memory.phase == 'init' and cpu.pc == built['symbols']['dual_init_done']
                    or memory.phase == 'play' and memory.tick in selected
                    and cpu.pc == built['symbols']['dual_call_done'])
        if boundary and cpu.sp == 0xfd:
            checkpoints.append(dict(phase=memory.phase, call=memory.tick, state=read_state(memory, built)))

    started = perf_counter()
    audit, actual = audit_psid(sid, count, observer=observer)
    stages['cpuAudit'] = perf_counter() - started
    started = perf_counter()
    expected = [row for row in numeric['writes'] if row['tick'] is None or row['tick'] < count]
    for index, (wanted, observed) in enumerate(zip(identity(expected), identity(actual))):
        require(wanted == observed,
                f'Dual compiled SID stores differ at {index}: expected {wanted}, observed {observed}')
    require(len(expected) == len(actual),
            f'Dual compiled store count differs: expected {len(expected)}, observed {len(actual)}')
    require(writer_count == len(actual), 'Executed SID writer coverage is incomplete')
    require(len(checkpoints) == len(selected) + 1, 'Compiled state checkpoint coverage is incomplete')
    for checkpoint in checkpoints:
        call_count = 0 if checkpoint['phase'] == 'init' else checkpoint['call'] + 1
        require(checkpoint['state'] == numeric['checkpoints'][call_count],
                f'Dual compiled state differs at {checkpoint["phase"]} call {checkpoint["call"]}')
    stages['checkpointComparison'] = perf_counter() - started
    started = perf_counter()
    output.mkdir(parents=True)
    (output / 'reconstructed.sid').write_bytes(sid)
    (output / 'wrapper.asm').write_text(built.pop('wrapperSource'))
    (output / 'wrapper.listing').write_text(built.pop('wrapperListing'))
    for name, engine in zip(('primary', 'secondary'), built['players']):
        (output / f'{name}.asm').write_text(engine.pop('source'))
        (output / f'{name}.listing').write_text(engine.pop('listing'))
    dependencies = ('scripts/compose-rambo-dual.py', 'scripts/compose-rambo.py',
                    'songs/players/rambo.asm', 'songs/players/rambo-sound.asm',
                    'scripts/rambo_player.py', 'scripts/rambo_score.py', 'scripts/rambo_programs.py',
                    'scripts/sid_assembler.py', 'scripts/psid_audit.py', 'scripts/psid_profile.py',
                    'scripts/sid_audit_host.py', 'scripts/sid_clock.py', 'scripts/verify_player.py')
    report = dict(
        compositions=[dict(path=str(path.resolve()), sha256=hashlib.sha256(value).hexdigest())
                      for path, value in zip(paths, encoded)],
        sidSha256=hashlib.sha256(sid).hexdigest(), checkedPlayCalls=count,
        orderedStoreComparison=dict(matchedStores=len(actual), fields=['phase', 'tick', 'address', 'value']),
        stateComparison=dict(matchedCheckpoints=len(checkpoints), engineCount=2,
                             fields=['data', 'sound', 'score', 'Morse']),
        sidWriterValidation=dict(checkedStores=writer_count,
                                 writers=[dict(pc=pc, opcode=site['opcode'], addresses=sorted(site['addresses']))
                                          for pc, site in sorted(writer_sites.items())]),
        stageSeconds=stages,
        toolSha256={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in dependencies},
        limits='Independent computed chip programs under one shared PAL frame budget. Chip A executes before chip B; no bus timing, audio or listening claim.',
        **built,
    )
    for name, value in (('audit.json', audit), ('writes.json', actual), ('state-checkpoints.json', checkpoints)):
        with (output / name).open('x', encoding='utf-8') as target:
            json.dump(value, target, indent=None if name == 'writes.json' else 2, allow_nan=False)
            target.write('\n')
    stages['output'] = perf_counter() - started
    with (output / 'build.json').open('x', encoding='utf-8') as target:
        json.dump(report, target, indent=2, allow_nan=False)
        target.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('primary', type=Path)
    parser.add_argument('secondary', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calls', type=int)
    args = parser.parse_args()
    print(json.dumps(run(args.primary, args.secondary, args.output, args.calls), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, IndexError) as error:
        raise SystemExit(f'Dual Rambo compilation failed: {error}')
