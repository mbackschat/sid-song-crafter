"""Test a duration edit against a private source copy, retaining compact score reads."""

import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

from probe import HERE, ROOT, SOURCE_SHA, PINS, READS, fingerprint, sha
from score import decode, expand
from psid_profile import psid_profile

TRACER_SHA = '0f5d9d5297236774227ccbb92c8aa3acc639846b0116fd445fc15b4520c7431b'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError('Choose a fresh output directory')
    source = ROOT / '.local/research/billie-jean/Billie_Jean.sid'
    original = source.read_bytes()
    assert sha(original) == SOURCE_SHA
    for name, expected in PINS.items():
        assert sha((ROOT / 'scripts' / name).read_bytes()) == expected, name
    tracer_path = ROOT / 'scripts/trace-sid-program.py'
    assert sha(tracer_path.read_bytes()) == TRACER_SHA
    spec = importlib.util.spec_from_file_location('billie_edit_trace', tracer_path)
    tracer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tracer)
    variants, cases = [], []
    for name, edit in (('control', False), ('first-pattern-duration', True)):
        data = bytearray(original)
        address = 0x1c08
        offset = 126 + address - 0x1000
        assert data[offset] == 0x83
        if edit:
            data[offset] = 0x82
        profile = psid_profile(data, profile='pal-banked', subtune=1)
        ram = [0] * 65536
        ram[profile['loadAddress']:profile['endAddress']] = profile['payload']
        predicted = expand(decode(ram), 128)
        trace = tracer.trace_program(bytes(data), first_call=0, last_call=127,
                                     profile='pal-banked', subtune=1)
        reads = [dict(tick=row['tick'], voice=row['x'], pc=row['pc'], address=row['operandAddress'],
                      value=row['operandValueBefore'], field=READS[row['pc']])
                 for row in trace['instructions'] if row['pc'] in READS]
        assert predicted['reads'] == reads
        variants.append(reads)
        cases.append(dict(name=name, sourceVariantSha256=sha(data), address=address,
                          originalByte=0x83, variantByte=data[offset], matchedReads=len(reads),
                          scoreReads=reads, orderedWrites=trace['initSidWrites'] + trace['sidWrites'],
                          noteCallsVoice0=[row['tick'] for row in reads if row['voice'] == 0 and row['field'] == 'note']))
    assert variants[0] != variants[1]
    assert cases[0]['noteCallsVoice0'][:2] == [2, 14]
    assert cases[1]['noteCallsVoice0'][:2] == [2, 11]
    assert source.read_bytes() == original
    args.output.mkdir(parents=True)
    (args.output / 'check-edit-executed.py').write_bytes(Path(__file__).read_bytes())
    raw = (json.dumps(cases, separators=(',', ':')) + '\n').encode()
    stored = gzip.compress(raw, mtime=0)
    (args.output / 'cases.json.gz').write_bytes(stored)
    receipt = dict(schemaVersion=1, passed=True, sourceSha256=SOURCE_SHA, originalUnchanged=True,
        callsPerCase=128, cases=[{key: row[key] for key in ('name', 'sourceVariantSha256', 'address',
            'originalByte', 'variantByte', 'matchedReads', 'noteCallsVoice0')} for row in cases],
        inputs=dict(checker=fingerprint(Path(__file__)), decoder=fingerprint(HERE / 'score.py'),
                    observerDefinitions=fingerprint(HERE / 'probe.py'), tracer=fingerprint(tracer_path), tools=PINS),
        artifact=dict(bytes=len(stored), sha256=sha(stored), decodedSha256=sha(raw), decodedBytes=len(raw)),
        limits='One duration-byte intervention in an in-memory original copy. Numeric expansion matches score reads; source SID writes are retained, not independently synthesized. No binary copy, rendering or listening.')
    (args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
