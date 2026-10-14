"""Verify bounded Take On Me sound helpers against original executed inputs."""

import argparse
from collections import Counter
from dataclasses import asdict
import gzip
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
import programs


SOURCE_SHA = 'c7e45037d20c3b85d18fc955a1cdfb70041f08dfc171e9b12d1c3327300101e6'
BYTE_FIELDS = {
    'control': 0x1e, 'base_note': 0x1ab4, 'remaining': 0x1a99, 'duration': 0x1aab,
    'glide_target': 0x1ab7, 'glide_active': 0x1aba, 'arpeggio': 0x1ac0,
    'onset_initial': 0x1abd, 'arpeggio_cursor': 0x1ac3,
    'waveform_cursor': 0x1ac7, 'pitch_cursor': 0x1aca,
    'pulse_initial': 0x1acd, 'pulse_direction': 0x1ad0,
    'vibrato_initial': 0x1ad3, 'vibrato_delay': 0x1ad6,
    'vibrato_direction': 0x1ad9, 'vibrato_remaining': 0x1adc,
}
INSTRUMENT_FIELDS = {
    'onset_control': 0x15ff, 'body_control': 0x1606,
    'attack_decay': 0x160d, 'sustain_release': 0x1614,
    'release_program': 0x161b, 'arpeggio_enabled': 0x1622,
    'table_program': 0x1629, 'pulse_program': 0x1630,
    'vibrato_program': 0x1637, 'filter_program': 0x163e,
    'gate_half': 0x1653,
}
CONTROLS = (
    ('pulse-down-step', 0x168c, 96, 48, (0xd410, 0xd411)),
    ('vibrato-delay', 0x16aa, 9, 5, (0xd40e, 0xd40f)),
    ('arpeggio-offset', 0x1660, 8, 12, (0xd407, 0xd408)),
    ('percussion-waveform', 0x1680, 129, 65, (0xd404,)),
    ('filter-down-step', 0x16b6, 16, 8, (0xd415, 0xd416)),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def split_word(ram, low, high, index=0):
    return ram[low + index] | ram[high + index] << 8


def voice_state(ram, voice):
    values = {name: ram[address + voice] for name, address in BYTE_FIELDS.items()}
    values.update(frequency=split_word(ram, 0x12, 0x15, voice), pulse=split_word(ram, 0x18, 0x1b, voice),
                  glide_step=split_word(ram, 0x1aae, 0x1ab1, voice),
                  vibrato_step=split_word(ram, 0x1adf, 0x1ae2, voice))
    return programs.VoiceState(**values)


def filter_state(ram):
    return programs.FilterState(word=split_word(ram, 0x21, 0x22), initial=ram[0x1ae5], direction=ram[0x1ae6])


def sweep_program(ram, index, addresses):
    initial, down_low, down_high, low_low, low_high, low_phase, up_low, up_high, high_low, high_high, high_phase = addresses
    return programs.SweepProgram(ram[initial + index], split_word(ram, down_low, down_high, index),
                                 split_word(ram, low_low, low_high, index), ram[low_phase + index],
                                 split_word(ram, up_low, up_high, index), split_word(ram, high_low, high_high, index),
                                 ram[high_phase + index])


def description(ram):
    """Decode declared numeric tables; keep executable bytes out of the result."""
    instruments = {}
    for index in range(5):
        values = {name: ram[address + index] for name, address in INSTRUMENT_FIELDS.items()}
        values.update(pulse=split_word(ram, 0x15f1, 0x15f8, index),
                      filter_word=split_word(ram, 0x1645, 0x164c, index))
        instruments[index] = programs.Instrument(**values)
    pulse_addresses = (0x1688, 0x168b, 0x168e, 0x1691, 0x1694, 0x1697,
                       0x169a, 0x169d, 0x16a0, 0x16a3, 0x16a6)
    filter_addresses = (0x16b1, 0x16b3, 0x16b5, 0x16b7, 0x16b9, 0x16bb,
                        0x16bd, 0x16bf, 0x16c1, 0x16c3, 0x16c5)
    sound = programs.Programs(
        frequencies={index: split_word(ram, 0x14d9, 0x1539, index) for index in range(96)},
        arpeggios={index: ram[0x1660 + index * 8:0x1668 + index * 8] for index in range(4)},
        waveforms={1: ram[0x1680:0x1684]}, pitches={1: ram[0x1684:0x1688]},
        pulses={index: sweep_program(ram, index, pulse_addresses) for index in (1, 2)},
        vibratos={1: programs.VibratoProgram(ram[0x16aa], ram[0x16ac], ram[0x16ae], ram[0x16b0])},
        filters={1: sweep_program(ram, 1, filter_addresses)},
        releases={index: (ram[0x165a + index], ram[0x165d + index]) for index in (1, 2)},
    )
    return instruments, sound


def source_read(cpu, ram):
    pc, opcode = cpu.pc, ram[cpu.pc]
    if opcode == 0xb9:
        base = ram[pc + 1] | ram[pc + 2] << 8
        if 0x14d9 <= base < 0x16c7:
            address = (base + cpu.y) & 65535
            return address, ram[address]
    if pc in (0x11db, 0x11e6, 0x1219, 0x1224, 0x1241, 0x124c):
        address = (split_word(ram, 0xe0, 0xe1) + cpu.y) & 65535
        return address, ram[address]
    return None


def execute(data, calls, *, retain=True):
    pending, records, reads = {}, [], []
    counts, instruments_used, active_glides = Counter(), set(), 0
    instrument_bank, sound = None, None

    def observe(cpu, memory):
        nonlocal instrument_bank, sound, active_glides
        ram, pc, voice = memory.data, cpu.pc, cpu.x
        if instrument_bank is None:
            instrument_bank, sound = description(ram)
        if memory.phase != 'play':
            return
        read = source_read(cpu, ram)
        if read and retain:
            reads.append(dict(call=memory.tick, pc=pc, voice=voice, address=read[0], value=read[1]))
        if pc in (0x14af, 0x14c8, 0x14d8):
            stage = 'sound' if pc == 0x14af else 'output' if pc == 0x14c8 else 'filter'
            require(stage in pending, f'Unexpected {stage} exit at call {memory.tick}')
            record, expected = pending.pop(stage)
            actual_writes = [(row['address'], row['value']) for row in memory.writes[record.pop('writeStart'):]]
            require(actual_writes == expected.writes,
                    f'{record["stage"]} ordered stores differ at call {memory.tick}, voice {voice}: {actual_writes} != {expected.writes}')
            if stage == 'sound':
                actual_state, actual_filter = voice_state(ram, voice), filter_state(ram)
                require(actual_state == expected.state,
                        f'{record["stage"]} state differs at call {memory.tick}, voice {voice}: {asdict(actual_state)} != {asdict(expected.state)}')
                require(actual_filter == expected.filter_state, f'Shared filter state differs at call {memory.tick}, voice {voice}')
                record.update(after=asdict(actual_state), filterAfter=asdict(actual_filter))
            record.update(writes=actual_writes, exitPc=pc)
            counts[record['stage']] += 1
            if retain:
                records.append(record)
        if pc in (0x1168, 0x11b3):
            require('sound' not in pending, 'Overlapping sound contexts')
            instrument_id = ram[0x1aa8 + voice]
            require(instrument_id in instrument_bank, f'Unsupported instrument ID {instrument_id}')
            instruments_used.add(instrument_id)
            state, shared = voice_state(ram, voice), filter_state(ram)
            active_glides += int(bool(state.glide_active) and pc == 0x11b3)
            instrument = instrument_bank[instrument_id]
            result = (programs.note_setup(state, shared, instrument, voice, sound.frequencies) if pc == 0x1168 else
                      programs.body_step(state, shared, instrument, sound, voice))
            pending['sound'] = (dict(stage='setup' if pc == 0x1168 else 'body', call=memory.tick,
                                     voice=voice, instrument=instrument_id, entryPc=pc,
                                     before=asdict(state), filterBefore=asdict(shared), writeStart=len(memory.writes)), result)
        if pc == 0x14af:
            state, shared = voice_state(ram, voice), filter_state(ram)
            pending['output'] = (dict(stage='voice-output', call=memory.tick, voice=voice, entryPc=pc,
                                      writeStart=len(memory.writes)),
                                 programs.SoundResult(state, shared, programs.voice_output(state, voice)))
        if pc == 0x14ce:
            state, shared = voice_state(ram, 0), filter_state(ram)
            pending['filter'] = (dict(stage='filter-output', call=memory.tick, voice=0, entryPc=pc,
                                      writeStart=len(memory.writes)),
                                 programs.SoundResult(state, shared, programs.filter_output(shared)))

    report, writes = audit_psid(data, calls, observer=observe, profile='pal-banked', subtune=1,
                                assume_sid_model='MOS6581')
    require(not pending, 'Unfinished observed sound boundary')
    return dict(audit=report, writes=writes, contexts=records, reads=reads,
                instrumentIds=sorted(instruments_used), activeGlideBodyInputs=active_glides,
                boundaryCounts=dict(counts), boundaryComparisons=sum(counts.values()),
                description=dict(instruments={index: asdict(value) for index, value in instrument_bank.items()},
                                 programs=asdict(sound)))


def projection(rows, excluded=()):
    return [(row['phase'], row['tick'], row['address'], row['value']) for row in rows if row['address'] not in excluded]


def patch_parameter(data, address, original, candidate):
    parsed = psid_profile(data, profile='pal-banked', subtune=1, assume_sid_model='MOS6581')
    prefix = len(data) - len(parsed['payload'])
    offset = prefix + address - parsed['loadAddress']
    require(prefix <= offset < len(data), 'Parameter intervention escapes the original payload')
    require(data[offset] == original, f'Parameter ${address:04x} differs from its declared source value')
    changed = bytearray(data)
    changed[offset] = candidate
    require(bytes(changed[:prefix]) == data[:prefix], 'Intervention changed the source header')
    return bytes(changed)


def verify(data, *, calls=1024, controls=False, retain=True):
    require(sha(data) == SOURCE_SHA, 'Pinned Take On Me source hash differs')
    require(type(calls) is int and 1 <= calls <= 8000, 'Sound probe supports 1..8000 initialized calls')
    baseline = execute(data, calls, retain=retain)
    control_results = []
    if controls:
        for name, address, original, candidate, ports in CONTROLS:
            changed = patch_parameter(data, address, original, candidate)
            controlled = execute(changed, calls, retain=retain)
            require(projection(baseline['writes'], ports) == projection(controlled['writes'], ports),
                    f'{name} changed stores outside its declared SID ports')
            original_ports = projection([row for row in baseline['writes'] if row['address'] in ports])
            candidate_ports = projection([row for row in controlled['writes'] if row['address'] in ports])
            require(original_ports != candidate_ports, f'{name} did not reach a changed output; extend the bounded call window')
            require(baseline['instrumentIds'] == controlled['instrumentIds'], f'{name} changed selected instrument IDs')
            control_results.append(dict(name=name, address=address, original=original, candidate=candidate,
                                        candidateSha256=sha(changed), declaredPorts=list(ports), onlyDeclaredPortsChanged=True,
                                        boundaryComparisons=controlled['boundaryComparisons'], audit=controlled['audit'],
                                        contexts=controlled['contexts'], reads=controlled['reads'], writes=controlled['writes']))
    result = dict(sourceSha256=SOURCE_SHA, playCalls=calls, boundaryComparisons=baseline['boundaryComparisons'],
                  boundaryCounts=baseline['boundaryCounts'], instrumentIds=baseline['instrumentIds'],
                  activeGlideBodyInputs=baseline['activeGlideBodyInputs'], audit=baseline['audit'],
                  description=baseline['description'], contexts=baseline['contexts'], reads=baseline['reads'],
                  writes=baseline['writes'], controls=control_results,
                  limitations='Observed setup/body/output inputs under initialized RAM-only callable PAL PSID execution with an explicit experimental MOS6581 assumption. No scheduler/full-form equivalence, SID synthesis, bus timing, original-host equivalence or listening verdict. Natural rows do not exercise glide.')
    return result


def write_compressed(path, value):
    encoded = json.dumps(value, separators=(',', ':')).encode() + b'\n'
    path.write_bytes(gzip.compress(encoded, mtime=0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/research/take-on-me/Take_on_Me.sid')
    parser.add_argument('--calls', type=int, default=1024)
    parser.add_argument('--controls', action='store_true')
    parser.add_argument('--output', type=Path, required=True, help='Fresh output directory')
    args = parser.parse_args()
    require(not args.output.exists(), 'Sound output exists; choose a fresh directory')
    result = verify(args.source.read_bytes(), calls=args.calls, controls=args.controls)
    args.output.mkdir(parents=True)
    description_data = result.pop('description')
    (args.output / 'sound-description.json').write_text(json.dumps(description_data, indent=2) + '\n')
    for key in ('contexts', 'reads', 'writes'):
        write_compressed(args.output / f'{key}.json.gz', result.pop(key))
    for control in result['controls']:
        for key in ('contexts', 'reads', 'writes'):
            write_compressed(args.output / f'{control["name"]}.{key}.json.gz', control.pop(key))
    result['toolHashes'] = {name: sha((Path(__file__).parent / name).read_bytes()) for name in ('programs.py', 'sound-probe.py')}
    result['oracleToolHashes'] = {name: sha((ROOT / 'scripts' / name).read_bytes()) for name in ('psid_audit.py', 'psid_profile.py')}
    result['outputHashes'] = {path.name: sha(path.read_bytes()) for path in sorted(args.output.iterdir())}
    (args.output / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'Checked {result["boundaryComparisons"]} sound boundaries and {len(result["controls"])} isolated controls in {args.output}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(str(error))
