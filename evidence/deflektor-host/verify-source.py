"""Pin the relocated host proof without retaining original executable bytes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def fingerprint(path):
    raw = path.read_bytes()
    return dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


source = ROOT / '.local/research/deflektor/Deflektor.sid'
raw = source.read_bytes()
expected = '606ad4cb19e29c060bb77a9b44253dee62d3d972724acb6cddf625fc2466d44d'
assert hashlib.sha256(raw).hexdigest() == expected
header = json.loads((HERE / 'header.json').read_text())
audit = json.loads((HERE / 'audit64.json').read_text())
vice = json.loads((HERE / 'vice64/study.json').read_text())
assert header['sha256'] == audit['sourceSha256'] == vice['sourceSha256'] == expected
assert vice['profile']['hostBase'] == audit['hostBase'] == 0x0400
assert raw[8:10] == b'\0\0' and int.from_bytes(raw[124:126], 'little') == 0xc000
exported = (HERE / 'vice64/payload.prg').read_bytes()
assert exported == raw[124:]
assert audit['initReturnAddress'] == vice['harnessLabels']['init_return']
assert audit['playReturnAddress'] == vice['harnessLabels']['play_return']
names = ['header.json', 'audit64.json', 'audit64.writes.json', 'vice64/study.json',
         'vice64/trace.json', 'regressions.json', 'check-regressions.py', 'verify-source.py']
tools = ['psid_profile.py', 'psid_audit.py', 'sid_audit_host.py', 'verify_player.py',
         'trace-sid-vice.py', 'trace-sid-program.py', 'sid_intake.py']
receipt = dict(schemaVersion=1, date='2026-10-13',
    sourceUrl='https://www.hvsc.de/download/C64Music/MUSICIANS/D/Daglish_Ben/Deflektor.sid',
    source=fingerprint(source), sourceHeaderSha256=hashlib.sha256(raw[:124]).hexdigest(),
    sourcePayloadSha256=hashlib.sha256(raw[126:]).hexdigest(),
    exportedLoadPrefixedPayload=fingerprint(HERE / 'vice64/payload.prg'),
    sourcePreservation='Pre-execution intake and both execution receipts match the canonical source hash; the current original still matches, and VICE payload.prg equals the original embedded load word plus every payload byte.',
    selection=1, hostBase=0x0400, hostEndExclusive=0x0600,
    initReturnAddress=audit['initReturnAddress'], playReturnAddress=audit['playReturnAddress'],
    hostProgram=fingerprint(HERE / 'vice64/harness.prg'),
    verification=vice['verification'],
    files={name: fingerprint(HERE / name) for name in names},
    tools={name: fingerprint(ROOT / 'scripts' / name) for name in tools},
    limitations=['Bounded controlled-host init plus calls 0..63; no form, instrument, audio or listening verdict.',
        'Source and private executable export fingerprints are retained; source bytes, payload, raw process/monitor logs and audio are excluded.',
        'CPU cycles are instruction-start/call costs; VICE timestamps are monitor checkpoints, not exact SID bus-write cycles.'])
with (HERE / 'verification.json').open('x') as output:
    json.dump(receipt, output, indent=2)
    output.write('\n')
print('Verified unchanged source, exact exported payload and shared CPU/VICE return sites')
