"""Retain a pinned 512-call Monty instruction window through the shared auditor."""

import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
SOURCE_SHA = '528a7330817e4a0a0f75a505e9fe2444e07c5072ce5383ceaa89f183f0eee3ab'
LISTING_SHA = '52dbbf891b1a1d0f8750842ef91ebaf1fc62d65d7b46497ae6951576ece3ae6c'


def main():
    source = ROOT / '.local/monty-source.sid'
    listing = Path(__file__).with_name('Hubbard_Rob_Monty_on_the_Run.asm')
    data = source.read_bytes()
    assert hashlib.sha256(data).hexdigest() == SOURCE_SHA
    assert hashlib.sha256(listing.read_bytes()).hexdigest() == LISTING_SHA
    spec = importlib.util.spec_from_file_location('monty_source_trace', ROOT / 'scripts/trace-sid-program.py')
    trace = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trace)
    report = trace.trace_program(data, first_call=0, last_call=511, profile='pal-banked', subtune=1)
    report['researchProvenance'] = {
        'sourcePath': str(source.relative_to(ROOT)), 'listingSha256': LISTING_SHA,
        'listingGitBlobSha1': '332b81b5ddd21d1ab20c7cd37c32ac786760a267',
        'tools': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
                  ('scripts/psid_profile.py', 'scripts/psid_audit.py', 'scripts/sid_audit_host.py',
                   'scripts/trace-sid-program.py', 'scripts/verify_player.py')},
        'probeSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'limits': '512 source calls only; listing correspondence, score semantics and form recurrence require separate evidence.'}
    encoded = (json.dumps(report, separators=(',', ':')) + '\n').encode()
    target = Path(__file__).with_name('boundary.trace.json.gz')
    with target.open('xb') as output:
        output.write(gzip.compress(encoded, mtime=0))
    print(json.dumps({'path': str(target), 'instructions': len(report['instructions']),
                      'playWrites': len(report['sidWrites']), 'initWrites': len(report['initSidWrites']),
                      'maximumPlayCycles': report['audit']['maximumPlayCycles'],
                      'decodedSha256': hashlib.sha256(encoded).hexdigest()}))


if __name__ == '__main__':
    main()
