"""Replace observed register shadows with the independent fixed-reset parameters."""

import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folder = Path(__file__).parent
    state_path, receipt_path = folder / 'initial-state.json', folder / 'receipt.json'
    original_state, original_receipt = folder / 'initial-state.original-execution.json', folder / 'receipt.original-execution.json'
    assert not original_state.exists() and not original_receipt.exists()
    state = json.loads(state_path.read_bytes())
    receipt = json.loads(receipt_path.read_bytes())
    assert digest(state_path) == receipt['initialState']['sha256']
    shadows = state.pop('sid_registers')
    parameters = dict(cutoff_low=shadows['D415'], cutoff_high=shadows['D416'],
                      routing=shadows['D417'], mode_volume=shadows['D418'],
                      clear_offsets_inclusive=[0, 21], clear_value=0)
    assert parameters['cutoff_low'] == parameters['clear_value']
    independently_generated = [(0xd416, parameters['cutoff_high']), (0xd417, parameters['routing']),
                              (0xd418, parameters['mode_volume'])]
    first, last = parameters['clear_offsets_inclusive']
    independently_generated += [(0xd400 + offset, parameters['clear_value']) for offset in range(last, first - 1, -1)]
    original_writes = [(write['address'], write['value']) for write in receipt['initSidWrites']]
    assert independently_generated == original_writes
    state['initial_sid'] = parameters
    state['initRule'] = 'Generate cutoff-high, routing, mode-volume stores, then clear SID offsets21..0 descending. cutoff-low is cleared by that range. This is a fixed reset rule, not an ordered captured-event bank.'
    source_state_sha, source_receipt_sha = digest(state_path), digest(receipt_path)
    state_path.rename(original_state)
    receipt_path.rename(original_receipt)
    with state_path.open('x') as stream:
        json.dump(state, stream, indent=2)
        stream.write('\n')
    receipt['initialState']['sha256'] = digest(state_path)
    receipt['descriptorDerivation'] = dict(
        scriptSha256=digest(Path(__file__)), sourceDescriptorPath=original_state.name,
        sourceDescriptorSha256=source_state_sha, sourceReceiptPath=original_receipt.name,
        sourceReceiptSha256=source_receipt_sha, independentlyGeneratedInitWritesMatch=True,
        rule='Named caller/pitch/score/output/global values unchanged. Replace captured shadow map with numeric reset parameters and a clear-range rule; regenerate all25stores and compare with the retained original init ledger.',
        sourceExecution='No new source execution; original bounded CPU proof and source/probe/trace hashes remain unchanged.')
    with receipt_path.open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(stateSha256=digest(state_path), receiptSha256=digest(receipt_path),
                          initialSid=parameters, initWritesRegenerated=len(independently_generated))))


if __name__ == '__main__':
    main()
