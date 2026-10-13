"""Test bounded Gauntlet attack/PWM hypotheses against initialized execution."""

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
from ghouls_programs import FilterState, VoiceState, note_setup, onset_step, pulse_step
from psid_audit import audit_psid
from sid_intake import inspect_sid
from verify_player import require


SOURCE_SHA = 'caec9549f437f6c1a1ee77edc9a034436fb66b2c8ba939adf45b889656c99328'
SOURCE_URL = 'https://www.hvsc.de/download/C64Music/MUSICIANS/F/Follin_Tim/Gauntlet_III.sid'
BYTE_FIELDS = {
    'waveform': 0x0b, 'gate_enabled': 0x17, 'rest_reload': 0x26, 'rest_remaining': 0x29,
    'pulse_step': 0x2c, 'transpose': 0x2f, 'onset_delay': 0x32, 'onset_control': 0x35,
    'frequency_delay_reload': 0x38, 'note_positive_duration': 0x3b, 'note_negative_duration': 0x3e,
    'note_remaining': 0x41, 'glide_rate': 0x44, 'note_index': 0x47, 'target_note_index': 0x4d,
    'frequency_delay_remaining': 0x5f, 'frequency_direction_default': 0x62,
    'frequency_half_remaining': 0x65, 'frequency_half_reload': 0x68, 'frequency_step': 0x6b,
    'onset_remaining': 0x6e, 'gate_time': 0x71, 'note_step': 0x74,
}
IMMEDIATE_FIELDS = {
    'frequency_direction': (0xabe5, 0xadd2, 0xafc1),
    'note_direction': (0xac1a, 0xae07, 0xaff6),
    'pulse_direction': (0xac6a, 0xae57, 0xb046),
    'pulse_restart': (0xad50, 0xaf3d, 0xb12c),
    'pitch_index_mode': (0xacfe, 0xaeeb, 0xb0da),
}
ONSET_FREQUENCY = (0xb556, 0xb571, 0xb58c)
FILTER_RESTART = (0xad67, 0xaf56, 0xb145)
ENTRIES = {
    'onset': (0xabb7, 0xada4, 0xaf93),
    'pulse': (0xac69, 0xae56, 0xb045),
    'setup': (0xacfb, 0xaee8, 0xb0d7),
}
EXITS = {
    'onset': (0xabd4, 0xadc1, 0xafb0),
    'pulse': (0xacb4, 0xaea1, 0xb090),
    'setup': (0xad8a, 0xaf79, 0xb168),
}
DISPATCH = (0xacde, 0xaecb, 0xb0ba)
REST_ENTRIES = (0xacf3, 0xaee0, 0xb0cf)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def word(ram, address):
    return ram[address] | ram[address + 1] << 8


def voice_state(ram, voice):
    values = {name: ram[address + voice] for name, address in BYTE_FIELDS.items()}
    values.update({name: ram[addresses[voice]] for name, addresses in IMMEDIATE_FIELDS.items()})
    values.update(pulse_word=word(ram, 0x1a + 2 * voice), pulse_default=word(ram, 0x20 + 2 * voice),
                  onset_frequency=word(ram, ONSET_FREQUENCY[voice]),
                  current_frequency=ram[0x56 + voice] | ram[0x59 + voice] << 8)
    return VoiceState(**values)


def filter_state(ram):
    owner = ram[0x55]
    return FilterState(word=word(ram, 0x50), default=word(ram, 0x52), step=ram[0x54], owner=owner,
                       direction=ram[0xb17c], reset_direction=ram[FILTER_RESTART[owner]],
                       lower=ram[0xb195] | ram[0xb18f] << 8, upper=ram[0xb1af] | ram[0xb1a9] << 8)


def sid_store(cpu, ram):
    opcode = ram[cpu.pc]
    if opcode not in (0x8d, 0x9d, 0x99, 0x8e, 0x8c):
        return None
    address = word(ram, cpu.pc + 1)
    address = (address + (cpu.x if opcode == 0x9d else cpu.y if opcode == 0x99 else 0)) & 65535
    if not 0xd400 <= address <= 0xd41f:
        return None
    return address, cpu.x if opcode == 0x8e else cpu.y if opcode == 0x8c else cpu.a


def execute(data, subtune, calls):
    pending, contexts, dispatches, setters, stores, shadows = {}, [], [], [], [], {}
    rest_pending, rests = {}, []
    last_read, pcs = {}, Counter()
    entries = {address: (stage, voice) for stage, addresses in ENTRIES.items() for voice, address in enumerate(addresses)}
    exits = {address: (stage, voice) for stage, addresses in EXITS.items() for voice, address in enumerate(addresses)}

    def observe(cpu, memory):
        ram, pc = memory.data, cpu.pc
        write = sid_store(cpu, ram)
        if write:
            address, value = write
            shadows[address] = value
            stores.append(dict(phase=memory.phase, call=memory.tick, pc=pc, address=address, value=value,
                               instructionStartCycle=memory.instruction_cycle))
        if memory.phase != 'play':
            return
        pcs[pc] += 1
        if ram[pc] == 0xb1 and ram[pc + 1] in (2, 4, 6):
            voice = (ram[pc + 1] - 2) // 2
            address = (word(ram, 2 + 2 * voice) + cpu.y) & 65535
            last_read[voice] = dict(address=address, value=ram[address], readerPc=pc)
            if pc in DISPATCH:
                dispatches.append(dict(call=memory.tick, voice=voice, **last_read[voice]))
        if ram[pc] == 0x85 and ram[pc + 1] in (0x2c, 0x2d, 0x2e, 0x32, 0x33, 0x34):
            address = ram[pc + 1]
            voice = (address - 0x2c) if address < 0x32 else (address - 0x32)
            require(voice in last_read, 'Parameter setter lacks its executed source read')
            require(cpu.a == last_read[voice]['value'], 'Parameter setter changed its source operand')
            setters.append(dict(call=memory.tick, voice=voice, field='pulse_step' if address < 0x32 else 'onset_delay',
                                setterPc=pc, **last_read[voice]))
        if pc in exits:
            key = exits[pc]
            if key[0] == 'setup' and key[1] in rest_pending:
                rest = rest_pending.pop(key[1])
                after = voice_state(ram, key[1])
                expected = dict(rest['before'], rest_remaining=rest['before']['rest_reload'])
                require(asdict(after) == expected, 'Zero-note rest changed continuing sound state')
                require(len(stores) == rest.pop('writeStart'), 'Zero-note rest emitted setup SID stores')
                rest.update(after=asdict(after), exitPc=pc)
                rests.append(rest)
            if key in pending:
                record = pending.pop(key)
                actual = voice_state(ram, key[1])
                actual_writes = [(row['address'], row['value']) for row in stores[record.pop('writeStart'):]]
                expected = record.pop('expected')
                expected_filter = record.pop('expectedFilter', None)
                require(actual == expected, f'{key} named state mismatch at call {memory.tick}')
                require(actual_writes == record['writes'], f'{key} ordered output mismatch at call {memory.tick}')
                if expected_filter is not None:
                    require(filter_state(ram) == expected_filter, 'Setup shared-filter state differs')
                record.update(after=asdict(actual), exitPc=pc)
                contexts.append(record)
        if pc in REST_ENTRIES:
            voice = REST_ENTRIES.index(pc)
            rest_pending[voice] = dict(call=memory.tick, voice=voice, entryPc=pc,
                                      before=asdict(voice_state(ram, voice)), writeStart=len(stores))
        if pc in entries:
            stage, voice = entries[pc]
            if stage == 'setup' and cpu.a == 0:
                return
            before = voice_state(ram, voice)
            if stage == 'setup':
                lookup = [ram[0xb6b1 + index] | ram[0xb712 + index] << 8 for index in range(256)]
                expected, expected_filter, writes = note_setup(before, filter_state(ram), voice, cpu.a, lookup)
                record = dict(rawNote=cpu.a, expectedFilter=expected_filter, path='positive-note',
                              envelope=[shadows[0xd405 + 7 * voice], shadows[0xd406 + 7 * voice]])
            else:
                result = (onset_step if stage == 'onset' else pulse_step)(before, voice)
                expected, writes = result.state, result.writes
                record = dict(path=result.path)
            record.update(stage=stage, voice=voice, call=memory.tick, entryPc=pc, before=asdict(before),
                          writes=writes, expected=expected, writeStart=len(stores))
            pending[stage, voice] = record

    audit, ledger = audit_psid(data, calls, observer=observe, profile='pal-banked', subtune=subtune, host_base=0x8000)
    require(not pending and not rest_pending, 'Unfinished observed component context')
    require([(row['phase'], row['tick'], row['address'], row['value']) for row in ledger] ==
            [(row['phase'], row['call'], row['address'], row['value']) for row in stores], 'Writer observer omitted source stores')
    return dict(audit=audit, contexts=contexts, rests=rests, stores=stores, dispatches=dispatches, setters=setters,
                executedPcs={f'{pc:04x}': count for pc, count in sorted(pcs.items())})


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def patch_source(data, header, changes):
    """Change verified data operands in a private copy without relocating code."""
    result = bytearray(data)
    prefix = header['dataOffset'] + (2 if header['headerLoadAddress'] == 0 else 0)
    for change in changes:
        offset = prefix + change['address'] - header['loadAddress']
        require(prefix <= offset < len(data), 'Intervention escapes original payload')
        require(data[offset] == change['original'], 'Executed parameter does not correspond to its source byte')
        result[offset] = change['candidate']
    return bytes(result)


def projection(rows, excluded=()):
    return [(row['phase'], row['call'], row['address'], row['value']) for row in rows if row['address'] not in excluded]


def analyze(original, no_onset, stationary, rest_control):
    setups = [row for row in original['contexts'] if row['stage'] == 'setup']
    restores = {(row['voice'], row['call']): row for row in original['contexts']
                if row['stage'] == 'onset' and row['path'] == 'restore'}
    attacks, pending_attacks = [], []
    for row in setups:
        state = row['before']
        if not state['onset_delay'] or not state['onset_control'] & 128:
            continue
        key = row['voice'], row['call'] + state['onset_delay']
        if key not in restores:
            require(key[1] >= original['audit']['playCalls'], 'Scheduled attack restoration is missing inside the observed window')
            pending_attacks.append(dict(voice=key[0], onsetCall=row['call'], scheduledRestoreCall=key[1]))
            continue
        restore = restores[key]
        require(restore['before']['current_frequency'] == row['after']['current_frequency'], 'Body pitch was not retained through onset')
        first, last = row['call'], restore['call']
        envelope_addresses = (0xd405 + 7 * row['voice'], 0xd406 + 7 * row['voice'])
        require(not any(first < store['call'] <= last and store['address'] in envelope_addresses
                        for store in original['stores'] if store['phase'] == 'play'), 'Envelope was rewritten during restoration')
        attacks.append(dict(voice=row['voice'], onsetCall=first, restoreCall=last, delay=state['onset_delay'],
                            attackControl=state['onset_control'] | 1, bodyControl=state['waveform'] | 1,
                            attackWord=state['onset_frequency'], bodyWord=row['after']['current_frequency'],
                            envelope=row['envelope'], setupPc=row['entryPc'], restorePc=restore['entryPc']))
    retained = [dict(call=row['call'], beforeWord=row['before']['pulse_word'], afterWord=row['after']['pulse_word'],
                     phase=row['before']['pulse_direction'], default=row['before']['pulse_default'])
                for row in setups if row['voice'] == 0 and row['call'] >= 768]
    require(attacks and retained, 'Selected passage must exercise both hypotheses')
    require(all(row['beforeWord'] == row['afterWord'] and row['default'] == 0 for row in retained), 'Zero-default notes restarted PWM')
    reset_notes = [dict(voice=row['voice'], call=row['call'], beforeWord=row['before']['pulse_word'],
                        afterWord=row['after']['pulse_word'], default=row['before']['pulse_default'])
                   for row in setups if row['before']['pulse_default'] and row['before']['pulse_word'] != row['after']['pulse_word']]
    require(projection(original['stores'], (0xd40e, 0xd40f, 0xd412)) ==
            projection(no_onset['stores'], (0xd40e, 0xd40f, 0xd412)), 'Onset removal changed companion/envelope/filter/PWM stores')
    require(original['dispatches'] == no_onset['dispatches'], 'Onset removal changed the score')
    require(projection(original['stores'], (0xd402, 0xd403)) == projection(stationary['stores'], (0xd402, 0xd403)),
            'Stationary PWM changed pitch, score gate, ADSR or companion/global stores')
    require(original['dispatches'] == stationary['dispatches'], 'Stationary PWM changed the score')
    require(projection(original['stores']) != projection(stationary['stores']), 'Stationary PWM did not alter its intended outputs')
    require(not original['rests'] and rest_control['rests'], 'Rest continuation must distinguish controlled from natural evidence')
    pulse_ports = (0xd402, 0xd403)
    original_pulse = [row for row in original['stores'] if row['address'] in pulse_ports]
    changed_pulse = [row for row in rest_control['stores'] if row['address'] in pulse_ports]
    require(projection(original_pulse) == projection(changed_pulse), 'Controlled zero-note rests changed ongoing PWM')
    rest_calls = [row['call'] for row in rest_control['rests']]
    moving_after_rest = [row for row in rest_control['contexts'] if row['stage'] == 'pulse' and row['voice'] == 0
                         and row['call'] in {call + 1 for call in rest_calls}]
    require(all(row['after']['pulse_word'] != row['before']['pulse_word'] for row in moving_after_rest),
            'PWM did not advance after the controlled rest')
    return dict(
        attack=dict(classification='supported across both', observedTransitions=len(attacks),
                    pendingAtWindowEnd=pending_attacks,
                    noiseToTriangle=sum(row['bodyControl'] == 17 for row in attacks),
                    noiseToPulse=sum(row['bodyControl'] == 65 for row in attacks), examples=attacks,
                    samePitchAndEnvelopeRetained=True, onsetRemovalChangesOnlyVoice3PitchControlStores=True),
        pulseAcrossNotes=dict(classification='supported across both', retainedZeroDefaultNotes=retained,
                              nonzeroDefaultResetNotes=reset_notes, stationaryChangesOnlyVoice1PulseStores=True),
        pulseAcrossRests=dict(classification='supported across both — controlled evidence', naturalGauntletRests=0,
                              controlledRestCalls=rest_calls, followingMovingBodies=len(moving_after_rest),
                              completeVoice1PulseTrajectoryUnchanged=True,
                              limitation='No zero-note rests occur in the selected original passage; this is a deliberately edited score check.'),
        universality=dict(classification='tune-driver specific',
                          limitation='These are executed contracts of the selected related drivers and patch defaults; joint credit does not identify an individual author or a universal style.'))


def run(source, output, *, calls=1604, subtune=2):
    data = Path(source).read_bytes()
    require(sha(data) == SOURCE_SHA, 'Gauntlet source fingerprint mismatch')
    require(subtune == 2 and type(calls) is int and 817 <= calls <= 1604,
            'Contrast requires explicit subtune 2 and 817..1604 initialized calls')
    output = Path(output)
    require(not output.exists() and not any(path.is_symlink() for path in (output, *output.parents)),
            'Choose a fresh output directory without symlink parents')
    require(output.resolve().is_relative_to(ROOT / 'build/follin-contrast'), 'Keep contrast evidence under build/follin-contrast')
    header = inspect_sid(data, subtune=subtune, host_base=0x8000)
    require(header['callableProfile']['accepted'] and header['initAddress'] == 0xc460 and header['playAddress'] == 0xabb0,
            'Unexpected Gauntlet host/entry contract')
    original = execute(data, subtune, calls)
    delay = next(row for row in original['setters'] if row['voice'] == 2 and row['call'] == 336 and row['field'] == 'onset_delay')
    pulse = next(row for row in original['setters'] if row['voice'] == 0 and row['call'] == 768 and row['field'] == 'pulse_step')
    note = next(row for row in original['dispatches'] if row['voice'] == 0 and row['call'] == 800)
    require((delay['value'], pulse['value'], note['value']) == (1, 40, 48), 'Selected controlled operands changed')
    changes = {
        'no-onset': [dict(address=delay['address'], original=1, candidate=0, parameter='voice3 onset delay')],
        'stationary-pwm': [dict(address=pulse['address'], original=40, candidate=0, parameter='voice1 pulse step'),
                           dict(address=0xb382, original=0, candidate=8, parameter='voice1 zero-default fallback high byte')],
        'rest-control': [dict(address=note['address'], original=48, candidate=0, parameter='voice1 selected score note becomes rest')],
    }
    candidates = {name: patch_source(data, header, edits) for name, edits in changes.items()}
    results = {name: execute(candidate, subtune, calls) for name, candidate in candidates.items()}
    findings = analyze(original, results['no-onset'], results['stationary-pwm'], results['rest-control'])
    output.mkdir(parents=True)
    for name, result in dict(original=original, **results).items():
        with gzip.open(output / (name + '.json.gz'), 'wt') as stream:
            json.dump(result, stream, separators=(',', ':'))
    for name, candidate in candidates.items():
        (output / (name + '.sid')).write_bytes(candidate)
    write_json(output / 'findings.json', findings)
    artifacts = {path.name: dict(bytes=path.stat().st_size, sha256=sha(path.read_bytes())) for path in output.iterdir()}
    report = dict(passed=True, source=dict(url=SOURCE_URL, sha256=SOURCE_SHA, selectedSubtune=subtune, header=header),
                  method=dict(clock='PAL', sidModel='MOS6581', hostBase=0x8000, calls=calls,
                              registerEvidence='Ordered pre-instruction CPU stores and named state; no renderer snapshots used as a write ledger',
                              reference=['scripts/ghouls_programs.py', 'evidence/ghouls-numeric/sound/receipt.json']),
                  initializedOriginal=dict(matchedContexts=len(original['contexts']), stores=len(original['stores']),
                                           paths=dict(Counter(row['stage'] + '/' + row['path'] for row in original['contexts']))),
                  interventions={name: dict(changes=edits, candidateSha256=sha(candidates[name]),
                                            matchedContexts=len(results[name]['contexts'])) for name, edits in changes.items()},
                  findings={name: row['classification'] for name, row in findings.items()}, outputHashes=artifacts,
                  tools={name: sha((ROOT / name).read_bytes()) for name in
                         ('scripts/studies/gauntlet/probe-contrast.py', 'scripts/ghouls_programs.py', 'scripts/psid_audit.py',
                          'scripts/psid_profile.py', 'scripts/sid_audit_host.py', 'scripts/sid_intake.py', 'scripts/verify_player.py')},
                  limits='Bounded initialized CPU corroboration and causal data interventions, not whole Gauntlet reconstruction, hardware/VICE/audio identity or musical acceptance.')
    write_json(output / 'receipt.json', report)
    require(Path(source).read_bytes() == data, 'Original reference changed')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/research/gauntlet-iii/Gauntlet_III.sid')
    parser.add_argument('--subtune', type=int, default=2)
    parser.add_argument('--calls', type=int, default=1604)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run(args.source, args.output, calls=args.calls, subtune=args.subtune)
    print(json.dumps(dict(output=str(args.output), findings=report['findings'], contexts=report['initializedOriginal']['matchedContexts'])))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(f'Gauntlet contrast failed: {error}')
