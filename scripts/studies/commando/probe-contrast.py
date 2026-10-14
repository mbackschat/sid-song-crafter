"""Prove bounded Commando channel sharing and mutable low-byte PWM."""

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid
from psid_profile import psid_profile
from verify_player import require


SOURCE_SHA = '5295378dacb06593a9c1853ce11a325ce885a16e26d56274d424e06492948de8'
SOURCE_URL = 'https://www.hvsc.de/download/C64Music/MUSICIANS/H/Hubbard_Rob/Commando.sid'
INSTRUMENT_BASE = 0x5591
HOST_BASE = 0x0400


def sha(data):
    return hashlib.sha256(data).hexdigest()


def word(ram, address):
    return ram[address] | ram[address + 1] << 8


def advance_low_pulse(low, step, incoming_carry):
    """Compute the selected $523D ADC, including its caller-owned carry."""
    require(type(low) is int and 0 <= low <= 255 and type(step) is int and 0 <= step <= 255,
            'Pulse low and step must be bytes')
    require(incoming_carry in (0, 1), 'Incoming carry must be zero or one')
    return (low + step + incoming_carry) & 255


def voice_state(ram, voice):
    instrument = ram[0x54fe + voice]
    record = ram[INSTRUMENT_BASE + 8 * instrument:INSTRUMENT_BASE + 8 * instrument + 8]
    return dict(instrument=instrument, record=record, pulseWord=record[0] | record[1] << 8,
                note=ram[0x54fb + voice], rawLength=ram[0x54f5 + voice], remaining=ram[0x54f2 + voice],
                savedControl=ram[0x54f8 + voice], heldWord=ram[0x551d + voice] | ram[0x551a + voice] << 8,
                phase=[ram[0x550d + voice], ram[0x5510 + voice]])


def sid_store(cpu, ram):
    opcode = ram[cpu.pc]
    if opcode not in (0x8d, 0x9d, 0x99, 0x8e, 0x8c):
        return None
    address = word(ram, cpu.pc + 1)
    address = (address + (cpu.x if opcode == 0x9d else cpu.y if opcode == 0x99 else 0)) & 65535
    if not 0xd400 <= address <= 0xd41f:
        return None
    value = cpu.x if opcode == 0x8e else cpu.y if opcode == 0x8c else cpu.a
    return address, value


def execute(data, calls):
    require(type(calls) is int and 128 <= calls <= 512, 'Commando probe requires 128..512 calls')
    notes, bodies, pwm, score, stores = [], [], [], [], []
    pending_note, pending_body, pending_pwm = {}, {}, {}
    pcs = Counter()

    def observe(cpu, memory):
        ram, pc = memory.data, cpu.pc
        store = sid_store(cpu, ram)
        if store:
            address, value = store
            voice = (address - 0xd400) // 7 if address < 0xd415 else None
            stores.append(dict(phase=memory.phase, call=memory.tick, pc=pc, address=address, value=value,
                               instructionStartCycle=memory.instruction_cycle,
                               instrument=ram[0x54fe + voice] if voice is not None else None))
        if memory.phase != 'play':
            return
        pcs[pc] += 1
        if pc in (0x5089, 0x50c2, 0x50dd, 0x50ee):
            pointer = 0x5d if pc == 0x5089 else 0x5f
            address = (word(ram, pointer) + cpu.y) & 65535
            score.append(dict(call=memory.tick, voice=cpu.x + 1, pc=pc, address=address, value=ram[address]))
        if pc == 0x511b:
            require(cpu.x not in pending_note, 'Unfinished previous note setup')
            pending_note[cpu.x] = dict(call=memory.tick, voice=cpu.x + 1, **voice_state(ram, cpu.x),
                                      writeStart=len(stores))
        elif pc == 0x5171:
            row = pending_note.pop(cpu.x)
            after = voice_state(ram, cpu.x)
            row.update(phaseBefore=row.pop('phase'), phaseAfter=after['phase'], savedControlAfter=after['savedControl'],
                       writes=stores[row.pop('writeStart'):])
            require(after['record'] == row['record'], 'Note setup unexpectedly changed its shared instrument record')
            require(row['phaseBefore'] == row['phaseAfter'], 'Note setup reset per-voice PWM phase')
            notes.append(row)
        elif pc == 0x51a3:
            require(cpu.x not in pending_body, 'Unfinished continuing sound body')
            pending_body[cpu.x] = dict(call=memory.tick, voice=cpu.x + 1, before=voice_state(ram, cpu.x),
                                      writeStart=len(stores))
        elif pc == 0x538f and cpu.x in pending_body:
            row = pending_body.pop(cpu.x)
            row.update(after=voice_state(ram, cpu.x), writes=stores[row.pop('writeStart'):])
            bodies.append(row)
        if pc == 0x523d:
            address = INSTRUMENT_BASE + cpu.y
            state = voice_state(ram, cpu.x)
            require(cpu.a == ram[address] and state['record'][7] & 8, 'PWM ADC lacks its executed record lookup')
            pending_pwm[cpu.x] = dict(call=memory.tick, voice=cpu.x + 1, instrument=state['instrument'],
                                     address=address, beforeLow=cpu.a, beforeHigh=ram[address + 1],
                                     step=ram[0x5507], incomingCarry=int(bool(cpu.p & cpu.CARRY)),
                                     record=state['record'], adcPc=pc, writeStart=len(stores))
        elif pc == 0x5240:
            row = pending_pwm[cpu.x]
            require(cpu.a == advance_low_pulse(row['beforeLow'], row['step'], row['incomingCarry']),
                    'Executed low-byte PWM differs from ADC arithmetic')
            row['tableStorePc'] = pc
        elif pc == 0x52b3 and cpu.x in pending_pwm:
            row = pending_pwm.pop(cpu.x)
            address = row['address']
            row.update(afterLow=ram[address], afterHigh=ram[address + 1], writes=stores[row.pop('writeStart'):])
            require(row['afterLow'] == advance_low_pulse(row['beforeLow'], row['step'], row['incomingCarry']),
                    'PWM table mutation differs from executed ADC')
            require(row['beforeHigh'] == row['afterHigh'], 'Low-byte PWM changed the instrument high byte')
            require([(store['address'], store['value']) for store in row['writes']] ==
                    [(0xd402 + 7 * (row['voice'] - 1), row['afterLow'])], 'PWM SID store differs from shared table mutation')
            pwm.append(row)

    audit, ledger = audit_psid(data, calls, observer=observe, profile='pal-banked', subtune=1, host_base=HOST_BASE)
    require(not pending_note and not pending_body and not pending_pwm, 'Unfinished bounded component observation')
    require([(row['phase'], row['tick'], row['instructionStartCycle'], row['address'], row['value']) for row in ledger] ==
            [(row['phase'], row['call'], row['instructionStartCycle'], row['address'], row['value']) for row in stores],
            'Commando observer omitted or changed ordered SID stores')
    return dict(audit=audit, notes=notes, bodies=bodies, pwm=pwm, score=score, stores=stores,
                executedPcs={f'{pc:04x}': count for pc, count in sorted(pcs.items())})


def remove_record7_drum(data):
    require(sha(data) == SOURCE_SHA, 'Commando source fingerprint mismatch')
    profile = psid_profile(data, profile='pal-banked', subtune=1, host_base=HOST_BASE)
    address = INSTRUMENT_BASE + 8 * 7 + 7
    prefix = len(data) - len(profile['payload'])
    offset = prefix + address - profile['loadAddress']
    require(data[offset] == 5, 'Commando record 7 effects differ from the pinned source')
    candidate = bytearray(data)
    candidate[offset] = 4
    require(sum(left != right for left, right in zip(data, candidate)) == 1, 'Intervention must change exactly one data byte')
    return bytes(candidate), dict(address=address, original=5, candidate=4, parameter='instrument 7 drum flag')


def projection(stores, excluded=()):
    return [(row['phase'], row['call'], row['address'], row['value']) for row in stores if row['address'] not in excluded]


def analyze(original, candidate):
    require(original['score'] == candidate['score'], 'Drum intervention changed executed score reads')
    require(projection(original['stores'], (0xd401, 0xd404)) == projection(candidate['stores'], (0xd401, 0xd404)),
            'Drum intervention changed protected companion, low-pitch, ADSR, PWM or global stores')
    require(original['pwm'] == candidate['pwm'], 'Drum intervention changed shared PWM execution')
    removed = [row for row in original['stores'] if row['instrument'] == 7 and row['pc'] in (0x5321, 0x532e, 0x5333)]
    remaining = [row for row in original['stores'] if not (row['instrument'] == 7 and row['pc'] in (0x5321, 0x532e, 0x5333))]
    event_projection = lambda rows: [(row['phase'], row['call'], row['pc'], row['address'], row['value'], row['instrument']) for row in rows]
    require(removed and event_projection(remaining) == event_projection(candidate['stores']),
            'Drum intervention differs from exact record 7 drum-store removal')
    require(projection(original['stores']) != projection(candidate['stores']), 'Drum intervention changed no outputs')
    note_keys = lambda value: [(row['call'], row['voice'], row['instrument'], row['note'], row['rawLength'], row['pulseWord'],
                                row['phaseBefore'], row['phaseAfter']) for row in value['notes']]
    require(note_keys(original) == note_keys(candidate), 'Drum intervention changed note setup or retained PWM phase')
    require(not {(row['call'], row['voice']) for row in original['notes']} &
            {(row['call'], row['voice']) for row in original['bodies']}, 'Note initializer did not skip continuing body')

    controls = [row for row in original['stores'] if row['phase'] == 'play' and row['address'] in (0xd404, 0xd40b, 0xd412)]
    examples, pending, latest_setup = [], {}, {}
    for row in controls:
        voice = (row['address'] - 0xd404) // 7 + 1
        if row['pc'] == 0x5139:
            latest_setup[voice] = row
            pending.pop(voice, None)
        elif row['pc'] == 0x5333 and row['value'] == 0x80:
            setup = latest_setup.get(voice)
            if setup and setup['value'] & 0x70 and not setup['value'] & 0x80:
                pending.setdefault(voice, (setup, row))
        elif row['pc'] == 0x5333 and row['value'] & 0x70 and not row['value'] & 0x80 and voice in pending:
            setup, noise = pending.pop(voice)
            envelope_ports = (row['address'] + 1, row['address'] + 2)
            retained = not any(store['phase'] == 'play' and noise['call'] <= store['call'] <= row['call'] and
                               store['address'] in envelope_ports for store in original['stores'])
            require(retained, 'Noise-to-tone restoration rewrote its ADSR')
            examples.append(dict(voice=voice, instrument=setup['instrument'], setupCall=setup['call'], noiseCall=noise['call'],
                                 restoreCall=row['call'], setupControl=setup['value'], noiseControl=0x80,
                                 restoreControl=row['value'], setupPc=setup['pc'], noiseRestorePc=row['pc'], envelopeRetained=retained))
    require(examples and any(row['voice'] == 1 for row in examples) and any(row['voice'] == 2 for row in examples),
            'Bounded passage lacks closed tonal/noise substitutions on two voices')
    original_noise = [row for row in original['stores'] if row['pc'] == 0x5333 and row['instrument'] == 7 and row['value'] == 0x80]
    candidate_noise = [row for row in candidate['stores'] if row['pc'] == 0x5333 and row['instrument'] == 7 and row['value'] == 0x80]
    require(original_noise and not candidate_noise, 'Record 7 drum intervention did not remove its noise substitutions')
    notes = [row for row in original['notes'] if row['voice'] == 3 and row['instrument'] == 2]
    require([(row['call'], row['pulseWord']) for row in notes[:4]] == [(0, 0x180), (18, 0x1f6), (36, 0x164), (48, 0x156)],
            'Selected onsets do not reload the expected mutated pulse record')
    return dict(channelSharing=dict(classification='supported in bounded Commando passage', examples=examples,
                                    basis='Executed instrument effect bit $01, length comparison and ordered same-voice control writes'),
                mutablePulse=dict(classification='supported with driver-specific arithmetic',
                                  observedSteps=len(original['pwm']),
                                  onsets=[{key: row[key] for key in ('call', 'voice', 'instrument', 'pulseWord')} for row in notes],
                                  arithmetic='Instrument effect bit $08 selects low-byte ADC with incoming carry; record high byte is retained. This is not Monty full-word bidirectional PWM.',
                                  noteSetupSkipsBody=True, perVoiceDelayDirectionRetained=True),
                intervention=dict(protectedProjectionEqual=True, scoreReadsEqual=True, pwmEqual=True, noteSetupEqual=True,
                                  record7NoiseRemoved=True, removedRecord7NoiseStores=len(original_noise),
                                  exactRecord7DrumStoreRemoval=True, removedRecord7DrumStores=len(removed),
                                  removedWriterPcs=[0x5321, 0x532e, 0x5333],
                                  allowedPorts=[0xd401, 0xd404],
                                  basis='Remove instrument 7 effect bit $01 only; retain ordered stores, including later octave overwrites.'))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def run(source, output, *, calls=512, subtune=1):
    require(subtune == 1, 'Contrast requires explicit Commando subtune 1')
    data = Path(source).read_bytes()
    require(sha(data) == SOURCE_SHA, 'Commando source fingerprint mismatch')
    registry = json.loads((ROOT / 'config/local-assets.json').read_text())
    asset = next(row for row in registry['references'] if row['id'] == 'commando')
    require(asset['sha256'] == SOURCE_SHA and asset['url'] == SOURCE_URL, 'Commando asset registry differs from probe provenance')
    output = Path(output)
    require(not output.exists() and not any(path.is_symlink() for path in (output, *output.parents)),
            'Choose a fresh output directory without symlink parents')
    require(output.resolve().is_relative_to(ROOT / 'build/commando-probe'), 'Keep private candidate and evidence under build/commando-probe')
    original = execute(data, calls)
    candidate_data, change = remove_record7_drum(data)
    candidate = execute(candidate_data, calls)
    findings = analyze(original, candidate)
    output.mkdir(parents=True)
    for name, result in (('original', original), ('no-record7-drum', candidate)):
        with gzip.GzipFile(filename=str(output / (name + '.json.gz')), mode='wb', mtime=0) as stream:
            stream.write((json.dumps(result, separators=(',', ':')) + '\n').encode())
    (output / 'no-record7-drum.sid').write_bytes(candidate_data)
    write_json(output / 'findings.json', findings)
    cpu_type_module = sys.modules['py65.devices.mpu6502']
    tool_paths = ['scripts/studies/commando/probe-contrast.py', 'scripts/psid_audit.py', 'scripts/psid_profile.py',
                  'scripts/sid_audit_host.py', 'scripts/sid_clock.py', 'scripts/verify_player.py', 'config/local-assets.json']
    tools = {name: sha((ROOT / name).read_bytes()) for name in tool_paths}
    tools['py65.devices.mpu6502'] = sha(Path(cpu_type_module.__file__).read_bytes())
    receipt = dict(passed=True, source=dict(url=SOURCE_URL, sha256=SOURCE_SHA, selectedSubtune=1),
                   execution=dict(profile='pal-banked', hostBase=HOST_BASE, calls=calls, clock='PAL', sidModel='MOS6581',
                                  sourceMaximumPlayCycles=original['audit']['maximumPlayCycles'],
                                  candidateMaximumPlayCycles=candidate['audit']['maximumPlayCycles']),
                   intervention=dict(change=change, candidateSha256=sha(candidate_data)),
                   counts=dict(sourceStores=len(original['stores']), candidateStores=len(candidate['stores']),
                               noteSetups=len(original['notes']), continuingBodies=len(original['bodies']),
                               pulseSteps=len(original['pwm']), closedNoiseSubstitutions=len(findings['channelSharing']['examples'])),
                   findings={name: value['classification'] for name, value in findings.items() if 'classification' in value},
                   tools=tools, outputs={path.name: dict(sha256=sha(path.read_bytes()), bytes=path.stat().st_size) for path in output.iterdir()},
                   limits='Bounded controlled callable execution and data intervention; no full reconstruction, original-game or renderer-host identity, hardware sound or listening judgment. Candidate SID remains private; compressed observations contain no payload/RAM dump.')
    write_json(output / 'receipt.json', receipt)
    require(Path(source).read_bytes() == data, 'Original Commando reference changed')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/commando-source.sid')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calls', type=int, default=512)
    parser.add_argument('--subtune', type=int, required=True)
    args = parser.parse_args()
    report = run(args.source, args.output, calls=args.calls, subtune=args.subtune)
    print(json.dumps(dict(output=str(args.output), counts=report['counts'], findings=report['findings'])))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(f'Commando contrast failed: {error}')
