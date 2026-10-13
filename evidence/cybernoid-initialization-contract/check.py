"""Check caller note/gate/filter behavior against short isolated archive paths."""

import argparse
from dataclasses import asdict
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT / 'scripts')]
from model import CallerState, begin_voice_call, begin_row, initialize_note, finish_row, body_prelude, filter_ownership
from psid_audit import BankedAuditMemory
from psid_profile import psid_profile
from verify_player import cpu_type

PIN = '41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192'
FIELDS = dict(row_remaining=0xa633, row_duration=0xa636, arpeggio_counter=0xa66d,
              base_pitch=0xa63f, current_pitch=0xa63c, frequency=(0xa693, 0xa696),
              held_frequency=(0xa64b, 0xa645), held_high_copy=0xa648,
              base_wave=0xa639, wave=0xa687, pulse_flags=0xa65a,
              pulse_accumulator=(0xa654, 0xa657), pulse_output=(0xa6ab, 0xa6ae),
              pulse_direction=0xa67e, packed_filter=0xa67b, gate_mask=0xa69c,
              note_age=0xa65e, vibrato_age=0xa6a8, glide_enabled=0xa64e, glide_active=0xa651,
              vibrato_direction=0xa667, vibrato_position=0xa66a, filter_cutoff=0xa678,
              pulse_run_flag=0xa69f, pulse_run_low=0xa6a2, pulse_run_high=0xa6a5)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main(output=None):
    folder = Path(__file__).parent
    target = output or folder / 'verification.json'
    assert not target.exists() and not target.is_symlink()
    source_path = ROOT / '.local/research/cybernoid-ii/Cybernoid_II.sid'
    source = source_path.read_bytes()
    assert sha(source) == PIN
    profile = psid_profile(source, profile='pal-banked', subtune=1)
    original = [0] * 65536
    original[profile['loadAddress']:profile['endAddress']] = profile['payload']
    cpu_class = cpu_type()
    checks = []
    initial = CallerState(**{name: 0x5678 if isinstance(address, tuple) else 0x55 for name, address in FIELDS.items()})

    def fresh(voice, state):
        ram = BankedAuditMemory((0xd400,))
        ram.data[:] = original
        ram.data[0:2] = [0x2f, 0x36]
        ram.data[0x48], ram.data[0x49] = voice, voice * 7
        for name, address in FIELDS.items():
            value = getattr(state, name)
            if isinstance(address, tuple):
                ram.data[address[0] + voice], ram.data[address[1] + voice] = value & 255, value >> 8
            else:
                ram.data[address + voice] = value
        ram.phase = 'play'
        return ram

    def state_of(ram, voice):
        result = {}
        for name, address in FIELDS.items():
            result[name] = (ram.data[address[0] + voice] | ram.data[address[1] + voice] << 8
                            if isinstance(address, tuple) else ram.data[address + voice])
        return CallerState(**result)

    def execute(ram, voice, entry, stop, allowed):
        cpu = cpu_class(memory=ram)
        cpu.pc, cpu.x, cpu.y, cpu.p = entry, voice, voice * 7, 0x26
        pcs = []
        while cpu.pc != stop:
            assert any(lo <= cpu.pc < hi for lo, hi in allowed), hex(cpu.pc)
            assert len(pcs) < 150
            ram.pc = cpu.pc
            ram.instruction = cpu.disassemble[ram.data[cpu.pc]][0]
            pcs.append(cpu.pc)
            cpu.step()
        assert cpu.sp == 255
        return pcs

    def writes(ram):
        return [(w['address'], w['value']) for w in ram.writes]

    for voice in range(3):
        ram = fresh(voice, initial)
        pcs = execute(ram, voice, 0xa7af, 0xa7bd, [(0xa7af, 0xa7bd)])
        predicted = begin_row(initial)
        assert state_of(ram, voice) == predicted and not ram.writes
        checks.append(dict(kind='beginRow', voice=voice, before=asdict(initial), after=asdict(predicted), pcs=pcs))

    for voice, age in itertools.product(range(3), (0, 127, 255)):
        state = CallerState(**dict(asdict(initial), note_age=age))
        ram = fresh(voice, state)
        pcs = execute(ram, voice, 0xa72a, 0xa72d, [(0xa72a, 0xa72d)])
        predicted = begin_voice_call(state)
        assert state_of(ram, voice) == predicted and not ram.writes
        checks.append(dict(kind='voiceAge', voice=voice, age=age, resultingAge=predicted.note_age, pcs=pcs))

    for voice, record_index, pitch, preserve in itertools.product(range(3), (0, 1, 4, 12), (0, 28), (False, True)):
        ram = fresh(voice, initial)
        record = original[0xb014 + record_index * 8:0xb01c + record_index * 8]
        frequency = original[0xae3f + pitch] | original[0xae96 + pitch] << 8
        ram.data[0xa642 + voice] = record_index
        ram.data[0xa68a + voice] = int(preserve)
        ram.data[0xa661 + voice], ram.data[0x43] = 0, pitch
        pcs = execute(ram, voice, 0xa874, 0xa8f0, [(0xa874, 0xa8f0)])
        predicted, expected_writes = initialize_note(initial, voice, pitch, frequency, record, preserve)
        assert state_of(ram, voice) == predicted and writes(ram) == expected_writes
        pcs += execute(ram, voice, 0xa90e, 0xa913, [(0xa90e, 0xa913)])
        predicted = finish_row(predicted)
        assert state_of(ram, voice) == predicted
        checks.append(dict(kind='note', voice=voice, record=record_index, pitch=pitch, preservePatch=preserve,
                           before=asdict(initial), after=asdict(predicted), orderedSetupWrites=expected_writes, pcs=pcs))

    for voice, remaining, scheduled, flags, tempo in itertools.product(range(3), (0, 1, 60, 61), (False, True), (5, 16), (1, 2)):
        state = CallerState(**dict(asdict(initial), row_remaining=remaining, pulse_flags=flags))
        ram = fresh(voice, state)
        record_index = 2 if remaining >= 60 else 1
        record = original[0xb014 + record_index * 8:0xb01c + record_index * 8]
        ram.data[0xa642 + voice], ram.data[0xa682] = record_index, tempo
        entry = 0xa916 if scheduled else 0xa944
        pcs = execute(ram, voice, entry, 0xa978, [(0xa916, 0xa932), (0xa93f, 0xa978)])
        predicted, fx, expected_writes = body_prelude(state, voice, record, tempo, scheduled)
        assert state_of(ram, voice) == predicted and writes(ram) == expected_writes
        assert tuple(ram.data[0x40:0x43]) == fx
        checks.append(dict(kind='bodyPrelude', voice=voice, record=record_index, remaining=remaining,
                           scheduled=scheduled, pulseFlags=flags, tempoCountdown=tempo,
                           after=asdict(predicted), effectBytes=fx, orderedSetupWrites=expected_writes, pcs=pcs))

    for voice, owner, fx2, fx3 in itertools.product(range(3), (0, 1, 2, 255), (0, 8), (0, 1)):
        ram = fresh(voice, initial)
        ram.data[0xa683], ram.data[0x41], ram.data[0x42] = owner, fx2, fx3
        stop = 0xac73 if fx3 & 1 else 0xace2
        pcs = execute(ram, voice, 0xac68, stop, [(0xac68, 0xac73), (0xacc8, 0xace2)])
        predicted_owner, cutoff, run, expected_writes = filter_ownership(voice, fx2, fx3, owner, initial.filter_cutoff)
        assert ram.data[0xa683] == predicted_owner and ram.data[0xa678 + voice] == cutoff
        assert writes(ram) == expected_writes and run == bool(fx3 & 1)
        checks.append(dict(kind='filterDispatch', voice=voice, owner=owner, fx2=fx2, fx3=fx3,
                           resultingOwner=predicted_owner, resultingCutoff=cutoff, runProgram=run,
                           orderedSetupWrites=expected_writes, pcs=pcs))

    census_path = ROOT / 'evidence/cybernoid-title-mechanism-coverage/coverage.json.gz'
    census_bytes = gzip.decompress(census_path.read_bytes())
    census = json.loads(census_bytes)
    selected_records = {r['recordIndex']: r['fields'] for r in census['records']}
    release_visits = {r['pc']: r['visits'] for r in census['rawEffectInstructionVisits'] if r['pc'] in (0xa94b, 0xa959)}
    assert not any(r['pulseHighFlags'] & 16 for r in selected_records.values()) and not release_visits
    assert source_path.read_bytes() == source
    result = dict(schemaVersion=1, sourceSha256=PIN,
                  modelSha256=sha((folder / 'model.py').read_bytes()), checkerSha256=sha(Path(__file__).read_bytes()),
                  dependencies={name: sha((ROOT / 'scripts' / name).read_bytes()) for name in ('psid_audit.py', 'psid_profile.py', 'verify_player.py')},
                  addressMap=FIELDS, syntheticChecks=checks,
                  actualTitle=dict(censusPath=str(census_path.relative_to(ROOT)), censusOriginalSha256=sha(census_bytes),
                                   selectedRecords=sorted(selected_records), pulseFlag10Records=[], specialSr02Visits=release_visits),
                  contract=dict(noteOrdering='increment age before score dispatch; selected row reset before score prefixes; note lookup; SID frequency high then low; optional AD/SR; score-owned peek/end; maskFF; final writer with body skipped.',
                                retained='Current effective pitch, vibrato direction/position, filter cutoff, pulse-run flag/accumulator survive patch initialization. Body prelude resets current effective pitch to base before tone arpeggio.',
                                gate='Only scheduled non-new bodies recompute mask from current record4; other bodies retain it. Remaining0 or remaining<=((record4&F0)>>2) clears gate. Later drum/onset runs even after gate clear.',
                                filter='Active flag01 stores the last owner then runs selected program. Otherwise matching owner and FX2&08==0 falls back to D4181F then D41680, retaining owner/routing/cutoff-low.'),
                  limits=['Short isolated archive execution with named synthetic caller state, not full-title or cycle equality.',
                          'Patch preservation is checked at its setup flag only; even-F prefix and helper-FF grammar remain fixture-gated in the score decoder.',
                          'SR02 retained pulse-flag10 path and FX2 bit08 fallback inhibition are synthetic/static here, not observed title behavior.',
                          'Scheduling/counter decrement, score prefixes/peek, macro arithmetic and final writer are owned by separate components.',
                          'Global PSID initialization and full-title per-body equality are not implemented by these caller primitives.',
                          'No original IRQ-host, physical SID/envelope, rendered audio or listening claim.'])
    with target.open('x') as stream:
        json.dump(result, stream, separators=(',', ':'))
        stream.write('\n')
    print(json.dumps(dict(checks=len(checks), matched=True)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    main(parser.parse_args().output)
