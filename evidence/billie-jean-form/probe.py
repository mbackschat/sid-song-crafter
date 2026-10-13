"""Compare initialized Billie Jean score consumption with independent numeric expansion."""

import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid
from psid_profile import psid_profile
from score import decode, expand

SOURCE_SHA = '16d8eae4d22f368520589c44e9db399b64092664bee6e1e70ca4b21c60bf0c54'
PINS = {
    'psid_audit.py': 'eeea11cdbb5159745f36802526ee2f2986d12fe19ce47b3609fedcf15f47e1bd',
    'psid_profile.py': 'c2c696db133ed024840cfa5edbc76e3a07ef1f30345cc1820c978a51a73c816d',
    'sid_audit_host.py': 'ea1949d711126b5150225f0d68a3462dbbfe9fffe094e448f9b758889808b0ed',
    'verify_player.py': 'c69317c5d781c175ef0cef39a6e2713187b17e1de5b3f144ad69d49e6a271aab',
}
READS = {0x102c: 'order', 0x104d: 'patternAfterTranspose', 0x1053: 'patternPointerLow',
         0x1058: 'patternPointerHigh', 0x1060: 'rowHeader', 0x1079: 'followingByte',
         0x1099: 'instrument', 0x10ab: 'glideStep', 0x10b1: 'glideTarget',
         0x10bb: 'note', 0x10c9: 'followingByte'}
VOICE_FIELDS = {'orderCursor': 0x1460, 'patternCursor': 0x145d, 'remaining': 0x144a,
                'transpose': 0x1493, 'baseNote': 0x145a, 'instrumentOffset': 0x1470,
                'holdFlag': 0x1484, 'patternIndex': 0x148a}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def voice_state(ram, voice):
    return {name: ram[address + voice] for name, address in VOICE_FIELDS.items()}


def mismatch(expected, actual):
    if expected == actual:
        return None
    for index, (left, right) in enumerate(zip(expected, actual)):
        if left != right:
            return dict(index=index, expected=left, actual=right)
    return dict(index=min(len(expected), len(actual)), expectedCount=len(expected), actualCount=len(actual))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--calls', type=int, default=64)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.calls <= 40000 or args.output.exists() or args.output.is_symlink():
        raise ValueError('Choose a fresh output and 1..40000 calls')
    source = ROOT / '.local/research/billie-jean/Billie_Jean.sid'
    data = source.read_bytes()
    assert sha(data) == SOURCE_SHA
    for name, digest in PINS.items():
        assert sha((ROOT / 'scripts' / name).read_bytes()) == digest, name
    baseline_path = ROOT / 'evidence/pop-theme-intake/billie-jean.audit64.writes.json.gz'
    baseline = json.loads(gzip.decompress(baseline_path.read_bytes()))
    profile = psid_profile(data, profile='pal-banked', subtune=1)
    ram = [0] * 65536
    ram[profile['loadAddress']:profile['endAddress']] = profile['payload']
    score = decode(ram)
    predicted = expand(score, args.calls)
    inputs = dict(source=fingerprint(source), baseline=fingerprint(baseline_path),
                  probe=fingerprint(Path(__file__)), model=fingerprint(HERE / 'score.py'), tools=PINS)
    args.output.mkdir(parents=True)
    (args.output / 'preflight.json').write_text(json.dumps(inputs, indent=2) + '\n')
    for filename in ('probe.py', 'score.py'):
        (args.output / (filename[:-3] + '-executed.py')).write_bytes((HERE / filename).read_bytes())
    reads, rows, wraps, returns, hooks = [], [], [], [], {}
    pending = {}
    init_state = None
    visits = Counter()

    def observe(cpu, memory):
        nonlocal init_state
        ram, pc = memory.data, cpu.pc
        if memory.phase == 'init':
            if pc == 0x14a5:
                assert cpu.sp == 253 and (ram[0x1fe] | ram[0x1ff] << 8) == 0xc039
                init_state = [voice_state(ram, voice) for voice in range(3)]
            return
        tick, voice = memory.tick, cpu.x
        if pc in READS or pc in (0x1032, 0x1087, 0x10d7, 0x1335, 0x1005):
            visits[pc] += 1
            if pc not in hooks:
                size = 2 if pc in (0x1032, 0x1087) else 1 if pc in (0x1335, 0x1005) else 3 if pc in (0x1053, 0x1058, 0x10d7) else 2
                hooks[pc] = dict(pc=pc, bytes=bytes(ram[pc:pc + size]).hex(),
                                 firstCall=tick, instructionStartCycle=memory.instruction_cycle)
        if pc in READS:
            if pc in (0x1053, 0x1058):
                address = (0x1900 if pc == 0x1053 else 0x1980) + cpu.y
            else:
                assert ram[pc:pc + 2] == [0xb1, 0xfa]
                address = ((ram[0xfa] | ram[0xfb] << 8) + cpu.y) & 65535
            value = ram[address]
            reads.append(dict(tick=tick, voice=voice, pc=pc, address=address, value=value, field=READS[pc]))
            if pc == 0x1060:
                assert voice not in pending
                pending[voice] = dict(tick=tick, voice=voice, address=address, header=value,
                                      kind='rest' if value & 224 == 192 else 'note')
        if pc == 0x1032:
            assert cpu.a == 255
            wraps.append(dict(tick=tick, voice=voice))
        if pc in (0x1087, 0x10d7):
            row = pending.pop(voice)
            row['state'] = voice_state(ram, voice)
            rows.append(row)
        if pc in (0x1335, 0x1005):
            assert cpu.sp == 253 and (ram[0x1fe] | ram[0x1ff] << 8) == 0xc04c and not pending
            returns.append(dict(tick=tick, divider=ram[0x1479], voices=[voice_state(ram, v) for v in range(3)],
                                returnPc=pc, ramSha256=sha(bytes(ram)),
                                machineSha256=sha(bytes(ram) + bytes((cpu.a, cpu.x, cpu.y, cpu.sp, cpu.p)) + pc.to_bytes(2, 'little')),
                                cpu=dict(a=cpu.a, x=cpu.x, y=cpu.y, sp=cpu.sp, p=cpu.p)))
            if tick % 1000 == 0:
                print(json.dumps(dict(completedCall=tick, rows=len(rows), wraps=wraps)), flush=True)

    report, writes = audit_psid(data, args.calls, profile='pal-banked', subtune=1, observer=observe)
    core_returns = [{key: row[key] for key in ('tick', 'divider', 'voices')} for row in returns]
    opening = [row for row in writes if row['phase'] == 'init' or row['tick'] < min(args.calls, 64)]
    expected_opening = [row for row in baseline if row['phase'] == 'init' or row['tick'] < min(args.calls, 64)]
    failures = {key: value for key, value in dict(reads=mismatch(predicted['reads'], reads),
        rows=mismatch(predicted['rows'], rows), wraps=mismatch(predicted['wraps'], wraps),
        returns=mismatch(predicted['returns'], core_returns), opening=mismatch(expected_opening, opening),
        init=mismatch(score['initialVoices'], init_state)).items() if value is not None}
    assert not pending and len(returns) == args.calls and source.read_bytes() == data
    artifacts = {}
    for name, value in [('score.json', score), ('audit.json', report), ('reads.json.gz', reads),
                        ('rows.json.gz', rows), ('returns.json.gz', returns), ('writes.json.gz', writes),
                        ('hooks.json', [dict(row, visits=visits[pc]) for pc, row in sorted(hooks.items())])]:
        raw = (json.dumps(value, separators=(',', ':')) + '\n').encode()
        stored = gzip.compress(raw, mtime=0) if name.endswith('.gz') else raw
        path = args.output / name
        path.write_bytes(stored)
        artifacts[name] = dict(sha256=sha(stored), bytes=len(stored), decodedSha256=sha(raw), decodedBytes=len(raw))
    result = dict(schemaVersion=1, passed=not failures, inputs=inputs, calls=args.calls,
        matchedReads=len(reads), matchedRows=len(rows), matchedOpeningRecords=len(opening),
        orderedWrites=len(writes), validatedPlayReturns=len(returns), sourceUnchanged=True,
        globalWraps=wraps, failures=failures, artifacts=artifacts,
        limits='Initialized controlled PAL banked calls with score/read/row/return state equality only. Score expansion computes no sound programs or SID writes. RAM/CPU hashes exclude absolute cycles and physical SID/CIA/VIC state; no original-game cadence, bus-write timing, reconstruction, rendering or listening judgment.')
    (args.output / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('passed', 'calls', 'matchedReads', 'matchedRows', 'orderedWrites', 'globalWraps', 'failures')}, indent=2))
    if failures:
        raise ValueError('Numeric expansion mismatch; closed source evidence retained')


if __name__ == '__main__':
    main()
