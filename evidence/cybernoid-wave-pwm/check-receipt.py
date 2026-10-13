import gzip
import hashlib
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
receipt_path = HERE / 'mechanisms-verified.json'
receipt = json.loads(receipt_path.read_bytes())
trace = json.loads(gzip.decompress((ROOT / receipt['provenance']['trace']['path']).read_bytes()))
rows = trace['instructions']
indices = sorted(index for call in receipt['calls'] for index in call['writerTraceIndices'].values())
actual = [
    {'phase': 'play', 'tick': rows[index]['tick'], 'instructionStartCycle': rows[index]['instructionStartCycle'],
     'address': rows[index]['operandAddress'], 'value': rows[index]['a'], 'instructionPc': rows[index]['pc']}
    for index in indices
]
expected = [
    write for write in trace['sidWrites']
    if write['instructionPc'] in (0xAE0B, 0xAE11, 0xAE17, 0xAE1D, 0xAE23)
    and (write['address'] - 0xD400) // 7 in (0, 2)
]
assert actual == expected and len(actual) == 640
pcs = {row['pc'] for row in receipt['selectedInstructions']}
assert all(pc in pcs for contract in receipt['contracts'] for pc in contract['executedPcs'])
spec = importlib.util.spec_from_file_location('checker', HERE / 'check-mechanisms.py')
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)
assert hashlib.sha256((HERE / 'check-mechanisms.py').read_bytes()).hexdigest() == receipt['provenance']['checker']['sha256']

slot = receipt['staticArchiveTables']['pulseSlot4']['bytes'].copy()
slot[2] -= 1
width, direction = 0x500, 1
wrong_pulse = []
for call in (call for call in receipt['calls'] if call['voiceIndex'] == 0 and not call['initializer']):
    width, direction, _ = model.pulse_step(width, direction, call['age'], slot, 0x64)
    if width != call['pulseWord']:
        wrong_pulse.append(call['call'])
assert wrong_pulse[0] == 3
wrong_wave = []
for call in (call for call in receipt['calls'] if call['voiceIndex'] == 2 and not call['initializer']):
    before = call['preWaveState']
    word = before['frequencyLow'] | before['frequencyHigh'] << 8
    wave, _, mask = model.drum_step(
        call['age'], before['wave'], word, before['gateMask'],
        receipt['listingBoundary']['tableComparisons']['drum0Wave']['listingBytes'],
        receipt['staticArchiveTables']['drum0FrequencyHigh']['bytes'])
    if wave & mask != call['control']:
        wrong_wave.append(call['call'])
assert wrong_wave == [call for call in range(64) if 2 <= call % 24 <= 10]
result = {
    'receiptSha256': hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
    'checkerSha256': receipt['provenance']['checker']['sha256'],
    'validationToolSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'command': 'python3 build/cybernoid-wave-pwm/check-receipt.py',
    'orderedFinalWriterStoresEqualCanonicalLedger': len(actual),
    'allContractPcsExecuted': True,
    'negativeControls': {
        'basis': 'Local arithmetic perturbations, not new source-driver executions or causal SID interventions.',
        'threshold3ChangedTo2': {'firstMismatchCall': wrong_pulse[0], 'mismatchCalls': wrong_pulse},
        'substituteRecoveredListingDrumWave': {'firstMismatchCall': wrong_wave[0], 'mismatchCalls': wrong_wave},
    },
}
with (HERE / 'validation.json').open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result))
