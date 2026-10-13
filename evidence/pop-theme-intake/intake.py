"""Retain source identities, STIL attribution and bounded execution provenance."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from sid_intake import inspect_sid


def fingerprint(path):
    raw = path.read_bytes()
    return dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


manifest_path = ROOT / 'config/local-assets.json'
manifest = json.loads(manifest_path.read_text())
downloads = json.loads((HERE / 'downloads.json').read_text())
stil_path = ROOT / '.local/downloads/HVSC-STIL.txt'
stil = stil_path.read_bytes()
assert hashlib.sha256(stil).hexdigest() == 'b1ef3584a5b3501e2bbd2ef056d6539a1bbee7933a7828537c3946c1b16cde43'
lines = stil.splitlines(keepends=True)
results = []
for downloaded in downloads:
    key = downloaded['id']
    asset = next(row for row in manifest['references'] if row['id'] == key)
    raw = (ROOT / asset['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == asset['sha256'] == downloaded['sha256']
    header = json.loads((HERE / f'{key}.header.json').read_text())
    inspected = inspect_sid(raw, subtune=1)
    assert all(header[field] == value for field, value in inspected.items())
    entry_path = '/' + asset['hvscPath']
    first = next(i for i, line in enumerate(lines) if line.rstrip(b'\r\n') == entry_path.encode())
    last = first + 1
    while last < len(lines) and not lines[last].startswith(b'/'):
        last += 1
    entry = b''.join(lines[first:last])
    fields = [line.decode('latin-1').strip() for line in lines[first:last]
              if line.lstrip().startswith((b'TITLE:', b'ARTIST:', b'(#'))]
    record = dict(id=key, source=asset, header=fingerprint(HERE / f'{key}.header.json'),
        stil=dict(entryPath=entry_path, firstLine=first + 1, lastLine=last,
            entrySha256=hashlib.sha256(entry).hexdigest(), fields=fields,
            hashRecipe='Original CRLF bytes from the path line through blank lines before the next path'),
        execution=dict(attempted=False, admission=header['callableProfile']))
    if header['callableProfile']['accepted']:
        audit = json.loads((HERE / f'{key}.audit64.json').read_text())
        vice = json.loads((HERE / f'{key}.vice64/study.json').read_text())
        writes = json.loads((HERE / f'{key}.audit64.writes.json').read_text())
        assert audit['sourceSha256'] == vice['sourceSha256'] == asset['sha256']
        assert audit['playCalls'] == vice['verification']['playCalls'] == 64
        assert len(writes) == vice['verification']['matchedWrites']
        prefix = int.from_bytes(raw[8:10], 'big')
        expected_payload = prefix.to_bytes(2, 'little') + raw[124:] if prefix else raw[124:]
        assert (HERE / f'{key}.vice64/payload.prg').read_bytes() == expected_payload
        names = [f'{key}.audit64.json', f'{key}.audit64.writes.json',
                 f'{key}.vice64/study.json', f'{key}.vice64/trace.json']
        record['execution'] = dict(attempted=True, profile='pal-banked', selectedSubtune=1,
            hostBase=audit['hostBase'], playCalls=64, verification=vice['verification'],
            files={name: fingerprint(HERE / name) for name in names},
            sourcePreservation='Original still matches the download/registry pin; VICE export equals the intact source payload with its load prefix.')
    results.append(record)
receipt = dict(schemaVersion=1, date='2026-10-13', candidates=results,
    registry=fingerprint(manifest_path), downloads=fingerprint(HERE / 'downloads.json'),
    stil=dict(url='https://hvsc.c64.org/download/C64Music/DOCUMENTS/STIL.txt',
        version='85, June 28, 2026', **fingerprint(stil_path)),
    tools={name: fingerprint(ROOT / 'scripts' / name) for name in
           ('sid_intake.py', 'psid_profile.py', 'sid_audit_host.py', 'psid_audit.py', 'verify_player.py', 'trace-sid-vice.py')},
    collector=fingerprint(Path(__file__)),
    limitations=['STIL and header credits distinguish original composition/performance from the SID arranger; unspecified subtune labels remain unknown.',
        'Take On Me has no declared SID model; Ghostbusters is NTSC RSID with zero play address. Neither was executed by the callable PAL tools.',
        'Billie Jean and Airwolf results cover init plus 64 controlled calls only; no full form, decoded synthesis, render, ending or listening verdict.',
        'Original SID files, full executable payloads, reference audio and raw VICE logs remain private and excluded from the archive.'])
with (HERE / 'provenance.json').open('x') as output:
    json.dump(receipt, output, indent=2)
    output.write('\n')
print('Verified four source pins, exact STIL entry fingerprints and two bounded CPU/VICE comparisons')
