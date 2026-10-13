"""Capture every initialized SOUND invocation through the finite loader stop."""

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid

OUT = Path(__file__).resolve().parent
SOURCE_SHA = '88a2b538ee3d3d1d8b0b754bef77a63d9750812694786977ae8c539f6ecd000e'
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


def main():
    source = ROOT / '.local/rambo-source.sid'
    data = source.read_bytes()
    if sha(source) != SOURCE_SHA:
        raise ValueError('Pinned source changed')
    if (OUT / 'bodies.json.gz').exists():
        raise ValueError('Output already exists')
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
        path = OUT / name
        path.write_bytes(gzip.compress(raw, mtime=0) if name.endswith('.gz') else raw)
        artifacts[name] = dict(sha256=sha(path), uncompressedSha256=hashlib.sha256(raw).hexdigest())
    receipt = dict(sourceSha256=sha(source), primarySourceSha256=sha(ROOT / '.tools/martin-galway-c64/rambload.asm'),
                   probeSha256=sha(Path(__file__)), matchedCanonicalRecords=len(writes),
                   calls=[0,10816], bodies=len(bodies), soundWrites=sum(len(b['writes']) for b in bodies),
                   arpeggioBodies=sum('arpeggioPitch' in b for b in bodies),
                   arpeggioOffsets=[dict(voice=v, offset=i, count=n) for (v,i),n in sorted(offset_counts.items())],
                   artifacts=artifacts)
    (OUT / 'capture.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
