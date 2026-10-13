import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('cybernoid_composed_invariants', HERE / 'model.py')
model = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = model
spec.loader.exec_module(model)
description_path = ROOT / 'build/cybernoid-editable-data/title-runtime.json'
description_raw = description_path.read_bytes()
description = json.loads(description_raw)
cases = []
for voice, value, label in [(0, -1, 'outOfBounds'), (0, 1, 'inconsistent'), (2, True, 'boolean')]:
    edited = copy.deepcopy(description)
    edited['initial_state']['voices'][voice]['pitch']['vibrato_direction'] = value
    try:
        model.compute_writes(edited, calls=1)
    except ValueError as error:
        cases.append(dict(kind=label, voiceIndex=voice, value=value, error=str(error)))
    else:
        raise AssertionError(label + ' was accepted')
states = []
baseline = model._compute_writes(description, calls=2, observer=states.append)
for state in states:
    caller = model.caller.CallerState(**state['state'])
    pitch = model.pitch.PitchState(**state['pitch'])
    assert model.pitch_from_caller(caller, pitch) == pitch
before = copy.deepcopy(description)
with patch.object(Path, 'read_bytes', side_effect=AssertionError('Runtime file I/O')), patch.object(Path, 'read_text', side_effect=AssertionError('Runtime file I/O')):
    assert model.compute_writes(description, calls=2) == baseline
assert description == before
result = dict(modelSha256=hashlib.sha256((HERE / 'model.py').read_bytes()).hexdigest(),
              guardSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              descriptionSha256=hashlib.sha256(description_raw).hexdigest(),
              rejectedInputs=cases, synchronizedCompletedVoiceStates=states,
              runtimeFileIO=False, inputUnchanged=True,
              scope='Pure model2-call checks; no original CPU execution or full-span duplicate ledger.')
with (HERE / 'invariants.json').open('x') as target:
    json.dump(result, target, indent=2)
    target.write('\n')
print(json.dumps(dict(rejectedInputs=len(cases), synchronizedCompletedVoiceStates=len(states), runtimeFileIO=False)))
