"""Verify every SOUND body and independent original-routine interventions."""

from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import BankedAuditMemory
from psid_profile import psid_profile
from verify_player import cpu_type
from rambo_programs import advance_voice
from probe import decode, ENTRY, SB, SOURCE_SHA


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def main():
    source = ROOT / '.local/rambo-source.sid'
    data = source.read_bytes()
    capture = json.loads((OUT / 'capture.json').read_text())
    if sha(source) != SOURCE_SHA:
        raise ValueError('Pinned source changed')
    for name, record in capture['artifacts'].items():
        if sha(OUT / name) != record['sha256']:
            raise ValueError('Captured evidence changed')
    bodies = json.loads(gzip.decompress((OUT / 'bodies.json.gz').read_bytes()))
    frequencies = {int(k):v for k,v in json.loads((OUT / 'frequency-words.json').read_text()).items()}
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
    (OUT / 'isolated.json.gz').write_bytes(gzip.compress(raw, mtime=0))
    result = dict(sourceSha256=sha(source), componentSha256=sha(ROOT / 'scripts/rambo_programs.py'),
                  checkerSha256=sha(Path(__file__)), captureSha256=sha(OUT / 'capture.json'),
                  contextBodies=len(bodies), contextOrderedStores=sum(len(r['writes']) for r in bodies),
                  arpeggioBodies=sum('arpeggioPitch' in r for r in bodies),
                  perVoiceBranches=[dict(voice=v,branch=b,bodies=n) for (v,b),n in sorted(branches.items())],
                  isolatedCases=len(cases), isolatedSha256=sha(OUT / 'isolated.json.gz'),
                  allNamedStatesAndOrderedStoresMatched=True,
                  negativeControl=dict(physicalVoice=3, label='incorrect fourth sequential phase', detected=True,
                                       legacyFrequency=legacy_state['frequency'], actualFrequency=third['after']['frequency']),
                  contract='Binary SOUND input; physical voice0..2, row remaining byte; numeric ten-byte chord overlay and resolved frequency words; lifetime, release, 16-bit PWM, sequential4/3/3 pitch and delayed fourth step, descending arpeggios.',
                  excluded='Score/note initialization, shared filter, scheduler, CPU registers/flags, original code runtime, audio or listening proof.')
    (OUT / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
