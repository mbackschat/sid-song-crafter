"""Verify editable Ghouls selection-1 sound arithmetic against executed boundaries."""

import argparse
from collections import Counter
from dataclasses import asdict, replace
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import AuditMemory, audit_psid
from verify_player import cpu_type, require
from ghouls_programs import (
    FilterState, VoiceResult, VoiceState, filter_step, frequency_step,
    note_setup, note_step, onset_step, pulse_step,
)

SOURCE_SHA = '265644a66d6043e6fe5ddeeb0d87e9b4269386a73c3e26457c8d96ce3d042df4'
VOICE_OFFSETS = (0, 0x1ed, 0x3dc)
PHASE_ADDRESSES = {
    'frequency_direction': (0x6269, 0x6456, 0x6645),
    'note_direction': (0x629e, 0x648b, 0x667a),
    'pulse_direction': (0x62ee, 0x64db, 0x66ca),
    'pulse_restart': (0x63d4, 0x65c1, 0x67b0),
    'pitch_index_mode': (0x6382, 0x656f, 0x675e),
}
ONSET_FREQUENCY_ADDRESSES = (0x6bda, 0x6bf5, 0x6c10)
FILTER_RESET_ADDRESSES = (0x63eb, 0x65da, 0x67c9)
BYTE_FIELDS = {
    'waveform': 0x2a, 'gate_enabled': 0x36, 'rest_reload': 0x39,
    'rest_remaining': 0x3c, 'pulse_step': 0x4b, 'transpose': 0x4e,
    'onset_delay': 0x51, 'onset_control': 0x54, 'frequency_delay_reload': 0x57,
    'note_positive_duration': 0x5a, 'note_negative_duration': 0x5d,
    'note_remaining': 0x60, 'glide_rate': 0x63, 'note_index': 0x66,
    'target_note_index': 0x6c, 'frequency_delay_remaining': 0x7e,
    'frequency_direction_default': 0x81, 'frequency_half_remaining': 0x84,
    'frequency_half_reload': 0x87, 'frequency_step': 0x8a,
    'onset_remaining': 0x8d, 'gate_time': 0x90, 'note_step': 0x93,
}
WORD_FIELDS = {'pulse_word': 0x3f, 'pulse_default': 0x45}



def word(ram, address):
    return ram[address] | ram[address + 1] << 8


def read_voice(ram, voice):
    values = {name: ram[address + voice] for name, address in BYTE_FIELDS.items()}
    values.update({name: word(ram, address + voice * 2) for name, address in WORD_FIELDS.items()})
    values.update({name: ram[addresses[voice]] for name, addresses in PHASE_ADDRESSES.items()})
    values['onset_frequency'] = word(ram, ONSET_FREQUENCY_ADDRESSES[voice])
    values['current_frequency'] = ram[0x75 + voice] | ram[0x78 + voice] << 8
    return VoiceState(**values)


def write_voice(ram, voice, state):
    for name, address in BYTE_FIELDS.items():
        ram[address + voice] = getattr(state, name)
    for name, address in WORD_FIELDS.items():
        value = getattr(state, name)
        ram[address + voice * 2:address + voice * 2 + 2] = [value & 255, value >> 8]
    for name, addresses in PHASE_ADDRESSES.items():
        ram[addresses[voice]] = getattr(state, name)
    address, value = ONSET_FREQUENCY_ADDRESSES[voice], state.onset_frequency
    ram[address:address + 2] = [value & 255, value >> 8]
    ram[0x75 + voice] = state.current_frequency & 255
    ram[0x78 + voice] = state.current_frequency >> 8


def read_filter(ram):
    return FilterState(word(ram, 0x6f), word(ram, 0x71), ram[0x73], ram[0x74],
                       ram[0x6800], ram[FILTER_RESET_ADDRESSES[ram[0x74]]],
                       ram[0x6819] | ram[0x6813] << 8,
                       ram[0x6833] | ram[0x682d] << 8)


def write_filter(ram, state):
    ram[0x6f:0x73] = [state.word & 255, state.word >> 8, state.default & 255, state.default >> 8]
    ram[0x73], ram[0x74], ram[0x6800] = state.step, state.owner, state.direction
    ram[FILTER_RESET_ADDRESSES[state.owner]] = state.reset_direction
    ram[0x6819], ram[0x6813] = state.lower & 255, state.lower >> 8
    ram[0x6833], ram[0x682d] = state.upper & 255, state.upper >> 8


def pitch_lookup(ram):
    return [ram[0x6d35 + index] | ram[0x6d96 + index] << 8 for index in range(256)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def publish(path, data, compressed=False):
    encoded = (json.dumps(data, separators=(',', ':') if compressed else None, indent=None if compressed else 2) + '\n').encode()
    stored = gzip.compress(encoded, mtime=0) if compressed else encoded
    path.write_bytes(stored)
    return dict(bytes=len(stored), sha256=hashlib.sha256(stored).hexdigest(),
                decodedSha256=hashlib.sha256(encoded).hexdigest())


def isolated_stage(snapshot, stage, changes):
    ram, registers, voice = snapshot
    memory = AuditMemory()
    memory.data[:] = ram
    cpu = cpu_type()(memory=memory)
    for name, value in registers.items():
        setattr(cpu, name, value)
    lookup = pitch_lookup(memory.data)
    if stage == 'filter':
        before = replace(read_filter(ram), **changes)
        write_filter(memory.data, before)
        expected, writes, path = filter_step(before)
        end_pc = 0x6851
    else:
        before = replace(read_voice(ram, voice), **changes)
        write_voice(memory.data, voice, before)
        if stage == 'setup':
            expected, filter_expected, writes = note_setup(before, read_filter(memory.data), voice, cpu.a, lookup)
            path = 'positive-note'
            end_pc = (0x640e, 0x65fd, 0x67ec)[voice]
        else:
            functions = {'onset': onset_step, 'frequency': frequency_step, 'note': note_step, 'pulse': pulse_step}
            result = functions[stage](before, voice, lookup) if stage == 'note' else functions[stage](before, voice)
            expected, writes, path = result.state, result.writes, result.path
            end_pc = {'onset': 0x6258, 'frequency': 0x6295, 'note': 0x62ed, 'pulse': 0x6338}[stage] + VOICE_OFFSETS[voice]
    for _ in range(2048):
        if cpu.pc == end_pc:
            break
        memory.instruction = cpu.disassemble[memory.data[cpu.pc]][0]
        require(memory.instruction not in ('???', 'BRK', 'RTI'), 'Unsupported isolated-stage instruction')
        cpu.step()
    else:
        raise ValueError('Isolated source stage did not reach its output boundary')
    actual = read_filter(memory.data) if stage == 'filter' else read_voice(memory.data, voice)
    actual_writes = [(r['address'], r['value']) for r in memory.writes]
    require(actual == expected and actual_writes == writes, f'Controlled {stage} parameters disagree with the source')
    if stage == 'setup':
        require(read_filter(memory.data) == filter_expected, 'Controlled setup filter state disagrees')
    return dict(stage=stage, voice=voice if stage != 'filter' else 'shared', changes=changes,
                before=asdict(before), after=asdict(actual), writes=writes, path=path, matchedSource=True)


def controlled_checks(snapshots):
    specifications = [
        ('frequency', 'down', {'frequency_step': 0}, 'freeze word-frequency motion'),
        ('frequency', 'down', {'frequency_direction': 255}, 'reverse word-frequency motion'),
        ('frequency', 'down', {'frequency_half_remaining': 1, 'frequency_half_reload': 2}, 'reverse after countdown expiry'),
        ('frequency', 'down', {'frequency_delay_remaining': 2}, 'defer word-frequency motion'),
        ('frequency', 'down', {'current_frequency': 65535, 'frequency_direction': 255, 'frequency_step': 1}, 'retain native high-byte wrap fallthrough'),
        ('note', 'alternate-up', {'note_step': 0}, 'freeze automatic note alternation'),
        ('note', 'alternate-up', {'note_step': 12}, 'widen automatic note alternation'),
        ('note', 'hold', {'glide_rate': 2, 'note_index': 40, 'target_note_index': 41, 'note_remaining': 0}, 'clamp upward glide to target'),
        ('note', 'hold', {'glide_rate': 2, 'note_index': 40, 'target_note_index': 39, 'note_remaining': 0}, 'clamp downward glide to target'),
        ('pulse', 'disabled', {'pulse_direction': 0, 'pulse_word': 768, 'pulse_step': 25}, 'activate downward pulse motion'),
        ('pulse', 'disabled', {'pulse_direction': 0, 'pulse_word': 100, 'pulse_step': 25}, 'undo lower-bound pulse overshoot'),
        ('pulse', 'disabled', {'pulse_direction': 255, 'pulse_word': 3990, 'pulse_step': 25}, 'undo upper-bound pulse overshoot'),
        ('onset', 'idle', {'onset_remaining': 1, 'gate_enabled': 1, 'waveform': 64}, 'restore body pitch and gate'),
        ('onset', 'idle', {'onset_remaining': 2}, 'retain staged onset before restoration'),
        ('setup', 'positive-note', {'onset_delay': 2, 'onset_control': 128, 'onset_frequency': 20480, 'gate_enabled': 1}, 'substitute a staged noise onset'),
        ('filter', 'down', {'step': 8, 'word': 512, 'lower': 50, 'upper': 1229, 'direction': 0}, 'move shared cutoff downward'),
        ('filter', 'down', {'step': 8, 'word': 50, 'lower': 50, 'upper': 1229, 'direction': 0}, 'undo lower-bound filter overshoot'),
        ('filter', 'down', {'step': 8, 'word': 1229, 'lower': 50, 'upper': 1229, 'direction': 255}, 'undo upper-bound filter overshoot'),
        ('filter', 'down', {'step': 1, 'word': 0x8001, 'lower': 0, 'upper': 0xffff, 'direction': 0}, 'retain negative high byte without low-byte borrow'),
        ('filter', 'down', {'step': 1, 'word': 0x8100, 'lower': 0, 'upper': 0xffff, 'direction': 0}, 'reverse negative high byte after low-byte borrow'),
    ]
    checks, unavailable = [], []
    for stage, path, changes, purpose in specifications:
        key = (stage, path)
        if key not in snapshots:
            unavailable.append(dict(stage=stage, requiredPath=path, purpose=purpose))
            continue
        baseline = isolated_stage(snapshots[key], stage, {})
        changed = isolated_stage(snapshots[key], stage, changes)
        changed.update(purpose=purpose, baselineWrites=baseline['writes'],
                       writesDiffer=baseline['writes'] != changed['writes'],
                       namedStateDiff={name: [baseline['after'][name], value]
                                       for name, value in changed['after'].items() if value != baseline['after'][name]})
        checks.append(changed)
    return checks, unavailable


def boundary_map(proof):
    comparisons = proof['comparisons']
    used = sorted({row['after']['note_index'] for row in comparisons
                   if row['stage'] == 'setup' or row['stage'] == 'note' and row['writes']})
    stages = []
    for voice in (0, 1, 2, 'shared'):
        for stage in ('onset', 'frequency', 'note', 'pulse', 'setup', 'filter'):
            rows = [row for row in comparisons if row['voice'] == voice and row['stage'] == stage]
            if not rows:
                continue
            evolving = {'onset': 'onset_remaining', 'frequency': 'current_frequency', 'note': 'note_index',
                        'pulse': 'pulse_word', 'setup': 'note_index', 'filter': 'word'}[stage]
            stages.append(dict(voice=voice, stage=stage, boundaries=len(rows),
                               callsWithWrites=sum(bool(row['writes']) for row in rows),
                               callsChangingValue=sum(row['before'][evolving] != row['after'][evolving] for row in rows),
                               changingField=evolving,
                               paths=dict(Counter(row['path'] for row in rows))))
    parameters = []
    parameter_fields = ('waveform', 'gate_enabled', 'pulse_default', 'pulse_step', 'pulse_restart',
                        'frequency_delay_reload', 'frequency_step', 'frequency_half_reload',
                        'frequency_direction_default', 'note_step', 'note_positive_duration',
                        'note_negative_duration', 'glide_rate', 'onset_delay', 'onset_control', 'onset_frequency')
    for voice in range(3):
        rows = [row for row in comparisons if row['voice'] == voice and row['stage'] == 'setup']
        parameters.append(dict(voice=voice, values={field: sorted({row['before'][field] for row in rows})
                                                   for field in parameter_fields}))
    filters = Counter(tuple(row['before'][field] for field in ('step', 'default', 'owner', 'lower', 'upper', 'reset_direction'))
                      for row in comparisons if row['stage'] == 'filter')
    return dict(schemaVersion=1, stages=stages, perVoiceParameters=parameters,
                voiceByteFields=BYTE_FIELDS, voiceWordFields=WORD_FIELDS,
                voicePhaseAddresses=PHASE_ADDRESSES, onsetFrequencyAddresses=ONSET_FREQUENCY_ADDRESSES,
                filterResetAddresses=FILTER_RESET_ADDRESSES,
                sharedFilterFields=dict(word=0x6f, default=0x71, step=0x73, owner=0x74,
                                        direction=0x6800, lowerLow=0x6819, lowerHigh=0x6813,
                                        upperLow=0x6833, upperHigh=0x682d),
                usedLookup=dict(minimum=min(used), maximum=max(used), distinct=len(used),
                                values=[dict(index=index, word=proof['lookup'][index]) for index in used],
                                lowArrayStart=0x6d35, highArrayStart=0x6d96, nominalArrayLength=97,
                                adjacentAliases=[dict(index=index, word=proof['lookup'][index]) for index in used if index >= 97],
                                scope='Used numeric index map; indices beyond 96 read adjacent initialized data, not additional conventional notes.'),
                filterParameterSets=[dict(step=values[0], default=values[1], owner=values[2], lower=values[3],
                                          upper=values[4], resetDirection=values[5], calls=count)
                                     for values, count in filters.items()],
                musicalPurposeHypotheses=dict(frequency='Delayed word-frequency motion supplies vibrato or sweeps.',
                                              note='Alternating note indices supply octave/fifth motion; index glide connects score notes.',
                                              onset='Voice 1 substitutes a one-call high-frequency noise onset before restoring body pitch.',
                                              pulse='Pulse widths can remain fixed with repeated writes or move between native bounds.',
                                              filter='Owner-1 note resets create repeated short downward cutoff trajectories.'),
                limits='Musical purpose is inferred from parameter/register motion and awaits listening. Helpers receive observed stage state; an independent integrated player remains required.')


def collect(data, ticks):
    stage_pcs = {}
    stages = ((0x623b, 'onset'), (0x6258, 'frequency'), (0x6295, 'note'), (0x62ed, 'pulse'))
    ends = {}
    for voice, offset in enumerate(VOICE_OFFSETS):
        for pc, name in stages:
            stage_pcs[pc + offset] = (voice, name)
        ends[0x6338 + offset] = (voice, 'pulse')
        stage_pcs[0x6381 + offset] = (voice, 'setup')
        ends[(0x640e, 0x65fd, 0x67ec)[voice]] = (voice, 'setup')
    pending, proofs, examples = {}, [], {}
    counts, paths, pcs = Counter(), Counter(), Counter()
    lookup, init_state = None, None
    source_snapshots = {}

    def finish(voice, name, cpu, memory):
        key = (voice, name)
        row = pending.pop(key)
        actual = read_voice(memory.data, voice)
        writes = [(r['address'], r['value']) for r in memory.writes[row['writeStart']:]]
        require(actual == row['result'].state,
                f'{name} state mismatch at call {memory.tick}, voice {voice}: {actual} != {row["result"].state}')
        require(writes == row['result'].writes,
                f'{name} store mismatch at call {memory.tick}, voice {voice}: {writes} != {row["result"].writes}')
        if name == 'setup':
            require(read_filter(memory.data) == row['filterResult'], 'Note setup shared-filter state mismatch')
        proof = dict(call=memory.tick, voice=voice, stage=name, path=row['result'].path,
                     before=asdict(row['before']), after=asdict(actual), writes=writes)
        proofs.append(proof)
        counts[key] += 1
        paths[(voice, name, proof['path'])] += 1
        signature = (name, proof['path'])
        if signature not in examples:
            examples[signature] = proof
            source_snapshots[signature] = row['snapshot']

    def observe(cpu, memory):
        nonlocal lookup, init_state
        if memory.phase != 'play':
            return
        pc, ram = cpu.pc, memory.data
        pcs[pc] += 1
        if lookup is None:
            lookup = pitch_lookup(ram)
            init_state = dict(voices=[asdict(read_voice(ram, v)) for v in range(3)], filter=asdict(read_filter(ram)))
        if pc in stage_pcs:
            voice, name = stage_pcs[pc]
            predecessor = {'frequency': 'onset', 'note': 'frequency', 'pulse': 'note'}.get(name)
            if predecessor:
                finish(voice, predecessor, cpu, memory)
            before = read_voice(ram, voice)
            if name == 'setup':
                state, filt, writes = note_setup(before, read_filter(ram), voice, cpu.a, lookup)
                result = VoiceResult(state, writes, 'positive-note')
            else:
                functions = {'onset': onset_step, 'frequency': frequency_step, 'note': note_step, 'pulse': pulse_step}
                result = functions[name](before, voice, lookup) if name == 'note' else functions[name](before, voice)
                filt = None
            signature = (name, result.path)
            snapshot = None
            if signature not in examples:
                snapshot = (ram.copy(), dict(a=cpu.a, x=cpu.x, y=cpu.y, p=cpu.p, sp=cpu.sp, pc=cpu.pc), voice)
            pending[(voice, name)] = dict(before=before, result=result, filterResult=filt,
                                          writeStart=len(memory.writes), snapshot=snapshot)
        if pc in ends:
            finish(*ends[pc], cpu, memory)
        if pc == 0x67ff:
            require(not pending, 'Voice stage did not reach its boundary')
            before = read_filter(ram)
            after, writes, path = filter_step(before)
            pending['filter'] = dict(before=before, after=after, writes=writes, path=path, writeStart=len(memory.writes))
            signature = ('filter', path)
            if signature not in source_snapshots:
                source_snapshots[signature] = (ram.copy(), dict(a=cpu.a, x=cpu.x, y=cpu.y, p=cpu.p, sp=cpu.sp, pc=cpu.pc), 0)
        if pc == 0x6851:
            row = pending.pop('filter')
            require(read_filter(ram) == row['after'], f'Filter state mismatch at call {memory.tick}')
            actual = [(r['address'], r['value']) for r in memory.writes[row['writeStart']:]]
            require(actual == row['writes'], f'Filter stores mismatch at call {memory.tick}')
            counts[('shared', 'filter')] += 1
            paths[('shared', 'filter', row['path'])] += 1
            proofs.append(dict(call=memory.tick, voice='shared', stage='filter', path=row['path'],
                               before=asdict(row['before']), after=asdict(row['after']), writes=actual))

    audit, writes = audit_psid(data, ticks, observer=observe, profile='pal-banked', subtune=1)
    require(not pending and counts[('shared', 'filter')] == ticks, 'Incomplete sound traversal')
    return dict(initialState=init_state, comparisons=proofs, lookup=lookup,
                stageCounts=[dict(voice=v, stage=s, count=n) for (v, s), n in counts.items()],
                pathCounts=[dict(voice=v, stage=s, path=p, count=n) for (v, s, p), n in paths.items()],
                executedPCCounts=[dict(pc=pc, count=n) for pc, n in sorted(pcs.items())]), audit, writes, source_snapshots


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ticks', type=int, default=12996)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(1 <= args.ticks <= 12996, 'Select 1..12996 calls within the finite study boundary')
    require(not args.output.exists(), 'Choose a fresh output directory')
    source = ROOT / '.local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid'
    data = source.read_bytes()
    require(hashlib.sha256(data).hexdigest() == SOURCE_SHA, 'Pinned reference changed')
    proof, audit, writes, snapshots = collect(data, args.ticks)
    controls, unavailable = controlled_checks(snapshots)
    require(args.ticks != 12996 or not unavailable, 'The full traversal lacks a required controlled-check path')
    frozen_path = ROOT / 'evidence/ghouls-form/full40000/audit.writes.json.gz'
    frozen = json.loads(gzip.decompress(frozen_path.read_bytes()))
    expected = [row for row in frozen if row['phase'] == 'init' or row['tick'] < args.ticks]
    require(writes == expected, 'Observed sound run differs from the retained full-form ledger')
    args.output.mkdir(parents=True)
    outputs = {
        'proofs.json.gz': publish(args.output / 'proofs.json.gz', proof, True),
        'audit.json': publish(args.output / 'audit.json', audit),
        'writes.json.gz': publish(args.output / 'writes.json.gz', writes, True),
        'controls.json': publish(args.output / 'controls.json', controls),
        'boundary-map.json': publish(args.output / 'boundary-map.json', boundary_map(proof)),
    }
    receipt = dict(sourceSha256=SOURCE_SHA, selectedSubtune=1, profile='pal-banked',
                   calls=args.ticks, fullFiniteTraversal=args.ticks == 12996, allComparisonsPass=True,
                   retainedFormLedgerSha256=sha(frozen_path), retainedFormPrefixStoresMatched=len(writes),
                   controlledChecksPassed=len(controls),
                   unavailableControlledChecks=unavailable,
                   scriptSha256=sha(Path(__file__)), outputHashes=outputs,
                   tools={name: sha(ROOT / 'scripts' / name) for name in ('ghouls_programs.py', 'psid_audit.py', 'psid_profile.py', 'sid_audit_host.py', 'verify_player.py')},
                   scope='Each helper receives observed named boundary state; full independent scheduler/state integration is a separate proof. Ordered values are checked, not instruction cycle equivalence, SID internals or listening.')
    publish(args.output / 'receipt.json', receipt)
    print(json.dumps(dict(output=str(args.output), stages=proof['stageCounts'], paths=proof['pathCounts'])), flush=True)


if __name__ == '__main__':
    main()
