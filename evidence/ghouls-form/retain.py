"""Pin the completed form, source correspondence and controlled-host stop proof."""

import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
from probe import COMMANDS, ROOT, SOURCE_SHA, TABLE_BASES, psid_profile, source
from py65.disassembler import Disassembler
from py65.devices import mpu6502
from verify_player import cpu_type

HERE = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
data, entry = source()
profile = psid_profile(data, profile='pal-banked', subtune=1)
run = json.loads((HERE / 'full40000/receipt.json').read_text())
opening = json.loads((HERE / 'opening256/receipt.json').read_text())
form = json.loads((HERE / 'form.json').read_text())
vice = json.loads((HERE / 'vice-stop/trace/study.json').read_text())
assert run['sourceSha256'] == form['sourceSha256'] == vice['sourceSha256'] == SOURCE_SHA
assert run['scriptSha256'] == sha(HERE / 'probe.py')
assert opening['scriptSha256'] == sha(HERE / 'opening256/probe-executed.py')
for name, digest in run['tools'].items():
    assert digest == sha(ROOT / 'scripts' / name)
assert vice['verification']['matchedWrites'] == 102
assert vice['verification']['maximumCadenceError'] <= 9

ram = [0] * 65536
ram[profile['loadAddress']:profile['endAddress']] = profile['payload']
disassembler = Disassembler(cpu_type()(memory=ram))
basis = []
for pc in (0x6110, 0x6120, 0x7316, 0x731a, 0x2982, 0x2985, 0x298b, 0x298e, 0x2996,
        0x29b9, 0x29bb, 0x29c6, 0x29c8, 0x29db, 0x29dd, 0x29e4,
        0x6156, 0x615b, 0x6160, 0x6165, 0x616a, 0x616f,
        0x6234, 0x6236, 0x6238, 0x6421, 0x6423, 0x6425, 0x6610, 0x6612, 0x6614,
        0x6362, 0x6368, 0x636e, 0x6374, 0x654f, 0x6555, 0x655b, 0x6561,
        0x673e, 0x6744, 0x674a, 0x6750, 0x693f, 0x6941, 0x6944,
        0x6958, 0x695a, 0x695d, 0x6971, 0x6973, 0x6976,
        0x698a, 0x698c, 0x698f, 0x6991, 0x6994, 0x6996,
        0x683c, 0x683e, 0x684c, 0x684e, 0x6851, 0x6853, 0x6855, 0x6857):
    size, assembly = disassembler.instruction_at(pc)
    basis.append(dict(pc=pc, bytes=bytes(ram[pc:pc + size]).hex(), assembly=assembly))

tables = []
executed = {(row['voice'], row['command']) for row in json.loads((HERE / 'full40000/summary.json').read_text())['commandCounts']}
for code in range(0x80, 0x95):
    for voice, (low, high) in enumerate(TABLE_BASES):
        tables.append(dict(code=code, voice=voice, annotation=COMMANDS[code], lowAddress=low + code,
            highAddress=high + code, bytes=[ram[low + code], ram[high + code]],
            target=ram[low + code] | ram[high + code] << 8, dispatchedInFullRun=(voice, code) in executed))

files = ['probe.py', 'opening256/probe-executed.py', 'check-opening.py', 'describe.py', 'opening.trace.json',
    'opening-validation.json', 'opening256/observations.json.gz', 'opening256/audit.writes.json.gz',
    'opening256/audit.json', 'opening256/summary.json', 'opening256/receipt.json',
    'full40000/observations.json.gz', 'full40000/audit.writes.json.gz', 'full40000/audit.json',
    'full40000/summary.json', 'full40000/receipt.json', 'form.json', 'vice-stop/projection.json',
    'vice-stop/oracle.json', 'vice-stop/trace/study.json', 'vice-stop/trace/trace.json']
result = dict(sourceSha256=SOURCE_SHA, sourceURL=entry['url'], selectedSubtune=1, musicalRole='provisional',
    pythonVersion=platform.python_version(), py65Version=version('py65'),
    py65CoreSourceSha256=sha(Path(mpu6502.__file__)),
    tools={name: sha(ROOT / 'scripts' / name) for name in ('psid_profile.py', 'psid_audit.py',
        'sid_audit_host.py', 'verify_player.py', 'trace-sid-program.py', 'trace-sid-vice.py')},
    scriptSha256=sha(Path(__file__)), artifacts={name: dict(bytes=(HERE / name).stat().st_size, sha256=sha(HERE / name)) for name in files},
    nativeStaticInstructionBasis=basis, commandTables=tables,
    annotationBoundary='Command names describe native state/output families, not musical roles or complete synthesis contracts. Basis bytes are static archive instructions; patched JMP targets and consumed bytes are executed observations in the full ledger.',
    sourceCopies=form['initializationCopies'], scoreForm='Finite per-voice stream consumption; all voices inactive after call12995',
    stateEquality=form['sampledStateEquality'], viceVerification=vice['verification'],
    proofScope='Complete40000-call CPU ordered ledger,256-call instruction/hook validation, and all-init plus12989..13002 VICE ordered-store comparison.',
    excluded=['Original SID', 'Whole source payload/RAM dump', 'Full third-party listing', 'Executable payload/host', 'Raw monitor/process logs', 'Rendered audio'],
    limits='Controlled PAL callable host, provisional selection1. Score stop retains two filter stores per later call. No original IRQ host, SID reads/bus-state model, cycle-equivalent reconstruction, acoustic ending or listening verdict.')
with (HERE / 'provenance.json').open('x') as output:
    json.dump(result, output, indent=2)
    output.write('\n')
print(json.dumps(dict(source=SOURCE_SHA, artifacts=len(files), staticInstructionLoci=len(basis),
    commandTableEntries=len(tables), viceMatchedWrites=vice['verification']['matchedWrites'])))
