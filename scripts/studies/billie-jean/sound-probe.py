"""Check bounded Billie Jean sound boundaries and private parameter controls."""

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from psid_audit import audit_psid
from psid_profile import psid_profile
from verify_player import require
import billie_jean_programs as sound


SOURCE_SHA = '16d8eae4d22f368520589c44e9db399b64092664bee6e1e70ca4b21c60bf0c54'
BYTE_FIELDS = {
    'waveform': 0x1447, 'base_note': 0x145a, 'remaining': 0x144a, 'hold': 0x1484,
    'instrument_offset': 0x1470, 'gate_mask': 0x146c, 'glide_step': 0x1466,
    'glide_target': 0x1469, 'pulse_direction': 0x1473, 'age': 0x1476,
    'vibrato_phase': 0x147a, 'wave_cursor': 0x1487,
}
PULSE_PORTS = tuple(0xd402 + 7 * voice + half for voice in range(3) for half in range(2))
FREQUENCY_PORTS = tuple(0xd400 + 7 * voice + half for voice in range(3) for half in range(2))
CONTROLS = (
    ('pulse-step', 0x151c, 32, 16, PULSE_PORTS),
    ('vibrato-step', 0x154d, 39, 23, FREQUENCY_PORTS),
    ('attack-pitch', 0x1a08, 213, 212, FREQUENCY_PORTS),
    ('cutoff-start-and-step', 0x151e, 32, 33, (0xd416,)),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def voice_state(ram, voice):
    values = {name: ram[address + voice] for name, address in BYTE_FIELDS.items()}
    values.update(pulse=ram[0x144e + voice] | ram[0x1451 + voice] << 8,
                  frequency=ram[0x1454 + voice] | ram[0x1457 + voice] << 8)
    return sound.VoiceState(**values)


def filter_state(ram):
    return sound.FilterState(cutoff=ram[0x144d], mode=ram[0x146f], routing=ram[0x147d])


def description(ram):
    instruments = {}
    for offset in range(0, 112, 8):
        record = ram[0x1500 + offset:0x1508 + offset]
        low = record[5] & 15
        instruments[offset] = sound.Instrument(
            attack_decay=record[0], sustain_release=record[1], pulse_initial=record[2],
            pulse_step=(record[4] & 240) >> 1, pulse_lower=record[3] >> 4, pulse_upper=record[3] & 15,
            vibrato_delay=(record[4] & 15) * 4, vibrato_step=record[5] & 240,
            vibrato_half=(record[5] & 14) >> 1, vibrato_period=record[5] & 14,
            vibrato_seed=(low >> 2) + 1 + ((low >> 1) & 1),
            filter_initialize=record[5] & 1, filter_start=record[6],
            filter_enabled=int(bool(record[7] & 240)), filter_step=record[6] & 15,
            filter_mode=record[7] & 112, wave_loop=record[7] & 15)
    bank = sound.Programs(
        frequencies={index: ram[0x1336 + 2 * index] | ram[0x1337 + 2 * index] << 8 for index in range(96)},
        pitches=ram[0x1a00:0x1b00], waveforms=ram[0x1b00:0x1c00],
        routing_set=ram[0x147e:0x1481], routing_clear=ram[0x1481:0x1484])
    return instruments, bank


def source_read(cpu, ram):
    pc = cpu.pc
    if ram[pc] != 0xb9:
        return None
    base = ram[pc + 1] | ram[pc + 2] << 8
    if base not in (0x1336, 0x1337, 0x1a00, 0x1b00) and not 0x1500 <= base <= 0x1507:
        return None
    address = (base + cpu.y) & 65535
    return dict(readerPc=pc, x=cpu.x, y=cpu.y, address=address, value=ram[address])


def execute(data, calls, *, retain=True):
    instruments, bank, initialized = None, None, None
    pending, contexts, reads = {}, [], []
    counts, paths, offsets = Counter(), Counter(), set()
    active_glides = 0

    def observe(cpu, memory):
        nonlocal instruments, bank, initialized, active_glides
        ram, pc, voice = memory.data, cpu.pc, cpu.x
        if instruments is None:
            instruments, bank = description(ram)
        if memory.phase == 'init':
            if pc == 0x14a5:
                initialized = dict(voices=[asdict(voice_state(ram, voice)) for voice in range(3)],
                                   filter=asdict(filter_state(ram)))
            return
        read = source_read(cpu, ram)
        if read and retain:
            reads.append(dict(call=memory.tick, **read))
        if pc in (0x131f, 0x1327, 0x1335):
            stage = 'sound' if pc == 0x131f else 'age' if pc == 0x1327 else 'global'
            require(stage in pending, f'Unexpected {stage} boundary at call {memory.tick}')
            row, expected = pending.pop(stage)
            actual_writes = [(write['address'], write['value']) for write in memory.writes[row.pop('writeStart'):]]
            require(actual_writes == expected.writes,
                    f'{row["stage"]} stores differ at call {memory.tick}, voice {voice}: {actual_writes} != {expected.writes}')
            if stage != 'global':
                actual_state, actual_filter = voice_state(ram, voice), filter_state(ram)
                require(actual_state == expected.state,
                        f'{row["stage"]} state differs at call {memory.tick}, voice {voice}: {asdict(actual_state)} != {asdict(expected.state)}')
                require(actual_filter == expected.filter_state, f'{row["stage"]} filter state differs at call {memory.tick}, voice {voice}')
                row.update(after=asdict(actual_state), filterAfter=asdict(actual_filter))
            row.update(writes=actual_writes, exitPc=pc, path=expected.path)
            counts[row['stage']] += 1
            paths[row['stage'] + ':' + expected.path] += 1
            if retain:
                contexts.append(row)
        if pc in (0x10d7, 0x1148):
            require('sound' not in pending, 'Overlapping sound boundaries')
            state, shared = voice_state(ram, voice), filter_state(ram)
            offset = state.instrument_offset
            require(offset in instruments, f'Unsupported instrument offset {offset}')
            offsets.add(offset)
            active_glides += int(bool(state.glide_step) and pc == 0x1148)
            result = (sound.note_setup(state, shared, instruments[offset], bank, voice) if pc == 0x10d7 else
                      sound.body_step(state, shared, instruments[offset], bank, voice, ram[0x1479]))
            pending['sound'] = (dict(stage='setup' if pc == 0x10d7 else 'body', call=memory.tick,
                voice=voice, instrumentOffset=offset, divider=ram[0x1479], entryPc=pc,
                before=asdict(state), filterBefore=asdict(shared), writeStart=len(memory.writes)), result)
        if pc == 0x131f:
            state, shared = voice_state(ram, voice), filter_state(ram)
            pending['age'] = (dict(stage='age', call=memory.tick, voice=voice, entryPc=pc,
                before=asdict(state), filterBefore=asdict(shared), writeStart=len(memory.writes)),
                sound.SoundResult(sound.advance_age(state), shared, [], 'saturating'))
        if pc == 0x132d:
            shared = filter_state(ram)
            pending['global'] = (dict(stage='global-output', call=memory.tick, entryPc=pc,
                filterBefore=asdict(shared), writeStart=len(memory.writes)),
                sound.SoundResult(sound.VoiceState(), shared, sound.global_output(shared), 'mode-volume'))

    report, writes = audit_psid(data, calls, observer=observe, profile='pal-banked', subtune=1)
    require(not pending and initialized is not None, 'Incomplete source sound boundaries or initialization image')
    return dict(audit=report, writes=writes, contexts=contexts, reads=reads,
                initialSound=initialized, instrumentOffsets=sorted(offsets), activeGlideBodyInputs=active_glides,
                boundaryCounts=dict(counts), boundaryComparisons=sum(counts.values()), paths=dict(paths),
                description=dict(instruments={offset: asdict(instrument) for offset, instrument in instruments.items()},
                                 programs=asdict(bank)))


def projection(writes, calls, excluded=()):
    return [(row['phase'], row['tick'], row['address'], row['value']) for row in writes
            if (row['tick'] is None or row['tick'] < calls) and row['address'] not in excluded]


def patch_parameter(data, address, original, candidate):
    profile = psid_profile(data, profile='pal-banked', subtune=1)
    prefix = len(data) - len(profile['payload'])
    offset = prefix + address - profile['loadAddress']
    require(prefix <= offset < len(data) and data[offset] == original, 'Parameter intervention differs from its source pin')
    changed = bytearray(data)
    changed[offset] = candidate
    require(bytes(changed[:prefix]) == data[:prefix], 'Parameter intervention changed original metadata')
    return bytes(changed)


def verify(data, *, calls=7107, controls=False, control_calls=1500, retain=True):
    require(sha(data) == SOURCE_SHA, 'Pinned Billie Jean source hash differs')
    require(type(calls) is int and 1 <= calls <= 7107, 'Sound proof supports 1..7107 initialized calls')
    if controls:
        require(type(control_calls) is int and 1 <= control_calls <= calls, 'Control calls must fit the baseline prefix')
    baseline = execute(data, calls, retain=retain)
    checked_controls = []
    if controls:
        for name, address, original, candidate, ports in CONTROLS:
            changed = patch_parameter(data, address, original, candidate)
            controlled = execute(changed, control_calls, retain=retain)
            require(projection(baseline['writes'], control_calls, ports) == projection(controlled['writes'], control_calls, ports),
                    f'{name} changed undeclared ports')
            require(projection(baseline['writes'], control_calls) != projection(controlled['writes'], control_calls),
                    f'{name} has no output change inside the control window')
            checked_controls.append(dict(name=name, address=address, original=original, candidate=candidate,
                calls=control_calls, candidateSha256=sha(changed), declaredPorts=list(ports), onlyDeclaredPortsChanged=True,
                boundaryComparisons=controlled['boundaryComparisons'], paths=controlled['paths'], audit=controlled['audit'],
                description=controlled['description'], contexts=controlled['contexts'], reads=controlled['reads'], writes=controlled['writes']))
    return dict(sourceSha256=SOURCE_SHA, playCalls=calls, selectedSubtune=1, sidModel='MOS6581', clock='pal',
        **baseline, controls=checked_controls,
        limitations='Original-routine observed input/state/ordered-store proof in the RAM-only PAL banked callable host. No independent score scheduling, compiled export, SID synthesis, bus timing, original-host equivalence or listening acceptance.')


def save_json(path, value):
    with path.open('x') as output:
        json.dump(value, output, separators=(',', ':'))
        output.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/research/billie-jean/Billie_Jean.sid')
    parser.add_argument('--calls', type=int, default=7107)
    parser.add_argument('--controls', action='store_true')
    parser.add_argument('--control-calls', type=int, default=1500)
    parser.add_argument('--output', type=Path, required=True, help='Fresh ignored output directory; emits plain JSON for generic promotion')
    args = parser.parse_args()
    require(not args.output.exists(), 'Sound output exists; choose a fresh directory')
    result = verify(args.source.read_bytes(), calls=args.calls, controls=args.controls, control_calls=args.control_calls)
    args.output.mkdir(parents=True)
    for field in ('description', 'contexts', 'reads', 'writes', 'initialSound'):
        save_json(args.output / f'{field}.json', result.pop(field))
    for control in result['controls']:
        for field in ('description', 'contexts', 'reads', 'writes'):
            save_json(args.output / f'{control["name"]}.{field}.json', control.pop(field))
    result['toolHashes'] = {name: sha((Path(__file__).parent / name).read_bytes()) for name in ('billie_jean_programs.py', 'sound-probe.py')}
    result['oracleToolHashes'] = {name: sha((ROOT / 'scripts' / name).read_bytes()) for name in
        ('psid_audit.py', 'psid_profile.py', 'sid_clock.py', 'sid_audit_host.py', 'verify_player.py')}
    result['outputHashes'] = {path.name: sha(path.read_bytes()) for path in sorted(args.output.iterdir())}
    save_json(args.output / 'receipt.json', result)
    print(f'Checked {result["boundaryComparisons"]} sound boundaries, {len(result["instrumentOffsets"])} instruments and {len(result["controls"])} controls')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
