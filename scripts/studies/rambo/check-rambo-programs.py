#!/usr/bin/env python3
"""Capture and verify the full Rambo SOUND contract against its pinned source.

By default, execute the original through the finite stop and independently
check every SOUND state/store plus isolated interventions. --capture reuses
an existing hash-verified capture without repeating the complete execution.
All outputs require a fresh directory below build/. This is source-specific
research tooling; it reads no reference source inside the numeric component.
"""

import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid, BankedAuditMemory
from psid_profile import psid_profile
from verify_player import cpu_type
from rambo_programs import advance_voice

SOURCE_SHA = '88a2b538ee3d3d1d8b0b754bef77a63d9750812694786977ae8c539f6ecd000e'
PRIMARY_SHA = '78e7927e6c2e8f7d42c18d2e02bec764a2911d2d8180cec789020bdd60cdbb75'
CANONICAL_SHA = 'f9ef28f1a5a2b274236a3bc5513be1bfafdd897fbd6b600e0c705b12461a2c64'
SB = (0x29b2, 0x29d9, 0x2a00)
ENTRY = (0x2231, 0x24e0, 0x2799)


def decode(ram, voice):
    b = SB[voice]
    word = lambda i: ram[b + i] | ram[b + i + 1] << 8
    return dict(frequencySteps=[word(i) for i in (0, 2, 4, 6)],
                frequencyDurations=[ram[b + i] for i in (8, 9, 10, 11)],
                frequencyDelay=ram[b + 12], frequencyFlags=ram[b + 13],
                pulseDurations=[ram[b + i] for i in (14, 15)],
                pulseDelay=ram[b + 16], pulseFlags=ram[b + 17],
                pulseSteps=[word(i) for i in (18, 20)], pulseInitial=word(22),
                control=ram[b + 26], releaseCountdown=ram[b + 27], life=ram[b + 28],
                frequency=word(29), frequencyRemaining=[ram[b + i] for i in (31, 32, 33, 34)],
                pulse=word(35), pulseRemaining=[ram[b + i] for i in (37, 38)])


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(data, output):
    source = ROOT / '.local/rambo-source.sid'
    pending, bodies, frequencies = {}, [], {}
    visits, offset_counts = Counter(), Counter()

    def observe(cpu, memory):
        if memory.phase != 'play':
            return
        if cpu.pc in ENTRY:
            voice = ENTRY.index(cpu.pc)
            if voice in pending:
                raise ValueError('Overlapping SOUND entry')
            pending[voice] = dict(call=memory.tick, voice=voice,
                                  rowRemaining=memory.data[0x1a + voice],
                                  activeMask=memory.data[0x19],
                                  before=decode(memory.data, voice),
                                  sp=cpu.sp, writeStart=len(memory.writes))
        for voice, body in tuple(pending.items()):
            visits[voice, cpu.pc] += 1
            if cpu.pc in (0x2301, 0x2869):
                offset_counts[voice, cpu.x] += 1
            if cpu.pc in (0x2309, 0x2871):
                value = memory.data[0x2a90 + cpu.y] | memory.data[0x2a37 + cpu.y] << 8
                if cpu.y in frequencies and frequencies[cpu.y] != value:
                    raise ValueError('Observed frequency table changed')
                frequencies[cpu.y] = value
                body['arpeggioPitch'] = cpu.y
                body['arpeggioFrequency'] = value
            if memory.instruction == 'RTS' and cpu.sp == body['sp']:
                body['after'] = decode(memory.data, voice)
                body['writes'] = [(w['address'], w['value']) for w in memory.writes[body['writeStart']:]]
                del body['sp'], body['writeStart']
                bodies.append(body)
                del pending[voice]

    report, writes = audit_psid(data, 10817, subtune=1, profile='pal-banked', observer=observe)
    canonical = json.loads(gzip.decompress((ROOT / 'evidence/rambo-form/complete40000/writes.json.gz').read_bytes()))
    expected = [w for w in canonical if w['phase'] == 'init' or w['tick'] <= 10816]
    if pending or writes != expected:
        raise ValueError('Incomplete capture or canonical write mismatch')
    artifacts = {}
    for name, value in [('bodies.json.gz', bodies), ('visits.json', [dict(voice=v, pc=p, count=n) for (v,p),n in sorted(visits.items())]),
                        ('frequency-words.json', frequencies), ('audit.json', report)]:
        raw = (json.dumps(value, separators=(',', ':')) + '\n').encode()
        path = output / name
        path.write_bytes(gzip.compress(raw, mtime=0) if name.endswith('.gz') else raw)
        artifacts[name] = dict(sha256=sha(path), uncompressedSha256=hashlib.sha256(raw).hexdigest())
    receipt = dict(sourceSha256=sha(source), primarySourceSha256=sha(ROOT / '.tools/martin-galway-c64/rambload.asm'),
                   probeSha256=sha(Path(__file__)), matchedCanonicalRecords=len(writes),
                   calls=[0,10816], bodies=len(bodies), soundWrites=sum(len(b['writes']) for b in bodies),
                   arpeggioBodies=sum('arpeggioPitch' in b for b in bodies),
                   arpeggioOffsets=[dict(voice=v, offset=i, count=n) for (v,i),n in sorted(offset_counts.items())],
                   artifacts=artifacts)
    (output / 'capture.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def original(data, state, voice, row_remaining, frequency_words):
    profile = psid_profile(data, subtune=1, profile='pal-banked')
    ram = BankedAuditMemory((0xd400,))
    ram.data[0x2000:0x2000 + len(profile['payload'])] = profile['payload']
    b = SB[voice]

    def byte(offset, value):
        ram.data[b + offset] = value

    def word(offset, value):
        byte(offset, value & 255)
        byte(offset + 1, value >> 8)

    for key, offsets, writer in [
        ('frequencySteps', (0,2,4,6), word), ('frequencyDurations', (8,9,10,11), byte),
        ('pulseDurations', (14,15), byte), ('pulseSteps', (18,20), word),
        ('frequencyRemaining', (31,32,33,34), byte), ('pulseRemaining', (37,38), byte)]:
        for offset, value in zip(offsets, state[key]):
            writer(offset, value)
    for key, offset in [('frequencyDelay',12), ('frequencyFlags',13), ('pulseDelay',16), ('pulseFlags',17),
                        ('control',26), ('releaseCountdown',27), ('life',28)]:
        byte(offset, state[key])
    for key, offset in [('pulseInitial',22), ('frequency',29), ('pulse',35)]:
        word(offset, state[key])
    ram.data[0x1a + voice] = row_remaining
    if frequency_words is not None:
        for index, value in frequency_words.items():
            ram.data[0x2a90 + index] = value & 255
            ram.data[0x2a37 + index] = value >> 8
    ram.phase = 'play'
    ram.tick = None
    cpu = cpu_type()(memory=ram, pc=ENTRY[voice])
    cpu.p = cpu.UNUSED | cpu.INTERRUPT
    cpu.stPushWord(0x01ff)
    pcs = []
    while cpu.pc != 0x0200:
        if cpu.processorCycles >= 4096:
            raise ValueError('Isolated SOUND exceeded 4096 cycles')
        ram.instruction = cpu.disassemble[ram[cpu.pc]][0]
        if ram.instruction in ('???', 'BRK', 'RTI'):
            raise ValueError('Unsupported isolated instruction')
        ram.instruction_cycle = cpu.processorCycles
        pcs.append(cpu.pc)
        cpu.step()
    if cpu.sp != 255:
        raise ValueError('Isolated stack did not return')
    return decode(ram.data, voice), [(w['address'],w['value']) for w in ram.writes], pcs


def verify_capture(data, capture_dir, output):
    source = ROOT / '.local/rambo-source.sid'
    capture = json.loads((capture_dir / 'capture.json').read_text())
    if capture.get('sourceSha256') != SOURCE_SHA or capture.get('primarySourceSha256') != PRIMARY_SHA:
        raise ValueError('Capture does not describe the pinned source')
    if capture.get('calls') != [0,10816] or capture.get('matchedCanonicalRecords') != 87534:
        raise ValueError('Capture does not cover the full selected loader')
    if set(capture['artifacts']) != {'bodies.json.gz', 'visits.json', 'frequency-words.json', 'audit.json'}:
        raise ValueError('Capture artifact set differs from the supported contract')
    for name, record in capture['artifacts'].items():
        if sha(capture_dir / name) != record['sha256']:
            raise ValueError('Captured evidence changed')
    bodies = json.loads(gzip.decompress((capture_dir / 'bodies.json.gz').read_bytes()))
    counts = Counter(row['voice'] for row in bodies)
    if len(bodies) != capture.get('bodies') or counts != Counter({0:10816, 1:10816, 2:10816}):
        raise ValueError('Capture does not contain every selected SOUND invocation')
    frequencies = {int(k):v for k,v in json.loads((capture_dir / 'frequency-words.json').read_text()).items()}
    branches = Counter()
    for row in bodies:
        before = deepcopy(row['before'])
        after, writes = advance_voice(before, voice=row['voice'], row_remaining=row['rowRemaining'],
                                      frequency_words=frequencies)
        if before != row['before'] or after != row['after'] or writes != [tuple(w) for w in row['writes']]:
            raise ValueError(f'Context mismatch call {row["call"]}, voice {row["voice"]}')
        label = 'arpeggio' if 'arpeggioPitch' in row else 'other'
        branches[row['voice'],label] += 1
    seeds = [next(r['before'] for r in bodies if r['call'] == 10561 and r['voice'] == v) for v in range(3)]
    cases = []
    for voice, seed in enumerate(seeds):
        candidates = [('observed-ending', deepcopy(seed), 0, None)]
        for label, changes, remaining in [
            ('life-zero', {'life':0}, 0), ('life-one', {'life':1}, 0),
            ('release-expiry', {'releaseCountdown':1}, 0),
            ('row-release-below', {'control':0x49, 'releaseCountdown':3}, 2),
            ('row-release-equal', {'control':0x49, 'releaseCountdown':3}, 3),
            ('row-release-above', {'control':0x49, 'releaseCountdown':3}, 4),
            ('zero-control-fallthrough', {'control':9, 'releaseCountdown':3}, 0),
            ('pulse-disabled', {'pulseFlags':0}, 0), ('pulse-delay', {'pulseFlags':1, 'pulseDelay':1}, 0),
            ('pulse-word-wrap', {'pulse':65535, 'pulseRemaining':[1,0], 'pulseSteps':[1,65535], 'pulseFlags':1}, 0),
            ('pulse-borrow', {'pulse':0, 'pulseRemaining':[0,1], 'pulseSteps':[1,65535], 'pulseFlags':1}, 0),
            ('pulse-counter-only', {'pulseFlags':1, 'pulseRemaining':[0,0], 'pulseDurations':[1,1]}, 0),
            ('pulse-full-reset', {'pulseFlags':128, 'pulseRemaining':[0,0], 'pulseDurations':[1,1]}, 0),
            ('pulse-no-repeat', {'pulseFlags':4, 'pulseRemaining':[0,0]}, 0),
            ('frequency-disabled', {'frequencyFlags':0}, 0),
            ('frequency-delay-hold', {'frequencyFlags':1, 'frequencyDelay':1}, 0),
            ('frequency-delay-step', {'frequencyFlags':2, 'frequencyDelay':1}, 0),
            ('frequency-wrap', {'frequency':65535, 'frequencyFlags':1, 'frequencyDelay':0,
                                'frequencySteps':[1,1,1,1], 'frequencyRemaining':[1,0,0,0]}, 0),
            ('frequency-borrow', {'frequency':0, 'frequencyFlags':1, 'frequencyDelay':0,
                                  'frequencySteps':[65535]*4, 'frequencyRemaining':[1,0,0,0]}, 0),
            ('frequency-reload', {'frequencyFlags':1, 'frequencyDelay':0,
                                  'frequencyRemaining':[0,0,0,0], 'frequencyDurations':[1,1,1,1]}, 0),
            ('fourth-counter', {'frequencyFlags':1, 'frequencyDelay':0,
                                'frequencySteps':[1,2,3,99], 'frequencyRemaining':[0,0,0,1],
                                'frequencyDurations':[1,0,0,7]}, 0),
        ]:
            state = deepcopy(seed)
            state.update(changes)
            candidates.append((label, state, remaining, None))
        for phase in range(4 if voice == 0 else 3):
            state = deepcopy(seed)
            state.update(frequencyFlags=1, frequencyDelay=0, frequencyRemaining=[0]*4)
            state['frequencyRemaining'][phase] = 1
            candidates.append((f'sequential-phase-{phase}', state, 0, None))
        if voice != 1:
            for position in list(range(10)) + [128,255]:
                state = deepcopy(seed)
                state.update(frequencyFlags=10, frequencyDelay=position,
                             frequencySteps=[0x0700,0x0c04,0x0201,0x0603],
                             frequencyDurations=[9,5,48,9])
                # Numeric synthetic table stays inside the separate 89-byte table extents.
                table = {index:(0x1000 + index * 257) & 65535 for index in range(48,61)}
                candidates.append((f'arpeggio-position-{position}', state, 0, table))
            state = deepcopy(seed)
            state.update(frequencyFlags=8, frequencyDelay=0, frequencySteps=[9,0,0,0],
                         frequencyDurations=[0,0,250,0])
            candidates.append(('arpeggio-byte-wrap', state, 0, {3:0xabcd}))
        for label, state, row_remaining, table in candidates:
            predicted, predicted_writes = advance_voice(state, voice=voice, row_remaining=row_remaining,
                                                        frequency_words=table)
            actual, writes, pcs = original(data, state, voice, row_remaining, table)
            if predicted != actual or predicted_writes != writes:
                raise ValueError(f'Isolated mismatch {label}, voice {voice}')
            cases.append(dict(label=label, voice=voice, rowRemaining=row_remaining, frequencyWords=table,
                              before=state, after=actual, orderedWrites=writes, executedPcs=pcs))
    spec = importlib.util.spec_from_file_location('legacy_rambo', ROOT / 'evidence/rambo-programs/model.py')
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    third = next(c for c in cases if c['voice']==2 and c['label']=='fourth-counter')
    legacy_state, legacy_writes = legacy.advance_voice(third['before'], voice=2, row_remaining=third['rowRemaining'])
    if legacy_state == third['after'] or legacy_writes == [tuple(w) for w in third['orderedWrites']]:
        raise ValueError('Incorrect fourth-phase negative control did not fail')
    raw = (json.dumps(cases, separators=(',',':')) + '\n').encode()
    (output / 'isolated.json.gz').write_bytes(gzip.compress(raw, mtime=0))
    result = dict(sourceSha256=sha(source), componentSha256=sha(ROOT / 'scripts/rambo_programs.py'),
                  checkerSha256=sha(Path(__file__)), captureSha256=sha(capture_dir / 'capture.json'),
                  contextBodies=len(bodies), contextOrderedStores=sum(len(r['writes']) for r in bodies),
                  arpeggioBodies=sum('arpeggioPitch' in r for r in bodies),
                  perVoiceBranches=[dict(voice=v,branch=b,bodies=n) for (v,b),n in sorted(branches.items())],
                  isolatedCases=len(cases), isolatedSha256=sha(output / 'isolated.json.gz'),
                  allNamedStatesAndOrderedStoresMatched=True,
                  negativeControl=dict(physicalVoice=3, label='incorrect fourth sequential phase', detected=True,
                                       legacyFrequency=legacy_state['frequency'], actualFrequency=third['after']['frequency']),
                  contract='Binary SOUND input; physical voice0..2, row remaining byte; numeric ten-byte chord overlay and resolved frequency words; lifetime, release, 16-bit PWM, sequential4/3/3 pitch and delayed fourth step, descending arpeggios.',
                  excluded='Score/note initialization, shared filter, scheduler, CPU registers/flags, original code runtime, audio or listening proof.')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Fresh output directory below build/')
    parser.add_argument('--capture', type=Path, help='Existing capture directory under build/ or evidence/')
    args = parser.parse_args(argv)
    try:
        output = args.output.absolute()
        if any(parent.is_symlink() for parent in (output, *output.parents)):
            raise ValueError('Output paths must not contain symlinks')
        output = output.resolve()
        if output.exists() or output == ROOT / 'build' or not output.is_relative_to(ROOT / 'build'):
            raise ValueError('Choose a fresh directory below build/')
        capture_dir = args.capture.resolve() if args.capture else output
        if args.capture and not any(capture_dir.is_relative_to(ROOT / prefix) for prefix in ('build', 'evidence')):
            raise ValueError('Capture must be below build/ or evidence/')
        source = ROOT / '.local/rambo-source.sid'
        primary = ROOT / '.tools/martin-galway-c64/rambload.asm'
        canonical = ROOT / 'evidence/rambo-form/complete40000/writes.json.gz'
        if sha(source) != SOURCE_SHA or sha(primary) != PRIMARY_SHA:
            raise ValueError('Pinned SID or primary source changed')
        if not args.capture and sha(canonical) != CANONICAL_SHA:
            raise ValueError('Canonical full-title ledger changed')
        if args.capture and not (capture_dir / 'capture.json').is_file():
            raise ValueError('Capture directory must contain capture.json')
        inputs = dict(sourceSha256=sha(source), primarySourceSha256=sha(primary),
                      componentSha256=sha(ROOT / 'scripts/rambo_programs.py'),
                      checkerSha256=sha(Path(__file__)),
                      capturePath=str(capture_dir.relative_to(ROOT)),
                      captureReused=bool(args.capture),
                      tools={name:sha(ROOT / 'scripts' / name) for name in
                             ('psid_audit.py','psid_profile.py','sid_audit_host.py','verify_player.py')},
                      legacyComponentSha256=sha(ROOT / 'evidence/rambo-programs/model.py'))
        output.mkdir(parents=True)
        (output / 'preflight.json').write_text(json.dumps(inputs, indent=2) + '\n')
        (output / 'checker-executed.py').write_bytes(Path(__file__).read_bytes())
        (output / 'component.py').write_bytes((ROOT / 'scripts/rambo_programs.py').read_bytes())
        data = source.read_bytes()
        if not args.capture:
            capture(data, output)
        result = verify_capture(data, capture_dir, output)
        result['inputs'] = inputs
        (output / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
        if sha(source) != SOURCE_SHA or sha(primary) != PRIMARY_SHA:
            raise ValueError('Reference inputs changed during verification')
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, EOFError, ValueError) as error:
        print(f'rambo-programs: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
