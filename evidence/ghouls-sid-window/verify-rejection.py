"""Verify the frozen rejection context without replacing its original receipt."""
from collections import deque
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
receipt = json.loads((HERE / 'rejection.json').read_text())
snapshot = HERE / 'psid_audit-before.py'
assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == receipt['tools']['scripts/psid_audit.py']
for name in ('scripts/psid_profile.py', 'scripts/verify_player.py'):
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == receipt['tools'][name], name
assert hashlib.sha256((HERE / 'reproduce-rejection.py').read_bytes()).hexdigest() == receipt['probeSha256']
spec = importlib.util.spec_from_file_location('ghouls_historical_audit', snapshot)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
source = ROOT / '.local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid'
raw = source.read_bytes()
assert hashlib.sha256(raw).hexdigest() == receipt['sourceSha256']
context = deque(maxlen=12)


def observe(cpu, memory):
    context.append(dict(phase=memory.phase, tick=memory.tick, pc=cpu.pc,
        instruction=memory.instruction, a=cpu.a, x=cpu.x, y=cpu.y,
        instructionStartCycle=memory.instruction_cycle,
        instructionBytes=memory.data[cpu.pc:cpu.pc + 3], capturedWrites=len(memory.writes)))


try:
    module.audit_psid(raw, receipt['requestedCalls'], subtune=1, profile='pal-banked', observer=observe)
except ValueError as error:
    assert str(error) == receipt['error'], str(error)
    assert list(context) == receipt['recentInstructions']
    print('Verified exact historical rejection and 12-instruction context using the frozen auditor')
else:
    raise AssertionError('Historical audit unexpectedly accepted this driver')
