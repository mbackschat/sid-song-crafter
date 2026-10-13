"""Capture the bounded instruction context of the historical SID-window rejection."""
from collections import deque
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid

source = ROOT / '.local/research/ghouls-n-ghosts/Ghouls_n_Ghosts.sid'
raw = source.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '265644a66d6043e6fe5ddeeb0d87e9b4269386a73c3e26457c8d96ce3d042df4'
context = deque(maxlen=12)


def observe(cpu, memory):
    context.append(dict(phase=memory.phase, tick=memory.tick, pc=cpu.pc,
        instruction=memory.instruction, a=cpu.a, x=cpu.x, y=cpu.y,
        instructionStartCycle=memory.instruction_cycle,
        instructionBytes=memory.data[cpu.pc:cpu.pc + 3], capturedWrites=len(memory.writes)))


try:
    audit_psid(raw, 64, subtune=1, profile='pal-banked', observer=observe)
except ValueError as error:
    assert str(error) == 'Unsupported I/O write at $d41c', str(error)
    result = dict(schemaVersion=1, sourceSha256=hashlib.sha256(raw).hexdigest(),
        requestedCalls=64, error=str(error), recentInstructions=list(context),
        tools={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
               ('scripts/psid_audit.py', 'scripts/psid_profile.py', 'scripts/verify_player.py')},
        probeSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        limits='Historical rejected execution context only; no completed-call or SID-state/audio claim. InstructionBytes contains a fixed three-byte context, not a full code/RAM dump.')
    with Path(__file__).with_name('rejection.json').open('x') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
    print(json.dumps(dict(error=str(error), failingInstruction=context[-1])))
else:
    raise AssertionError('Expected the historical canonical-window guard to reject')
