"""Lock coverage accounting when the final traversal call only initializes rows."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    source = ROOT / 'build/cybernoid-title-mechanism-coverage/coverage.json'
    data = source.read_bytes()
    census = json.loads(data)
    last_call = census['scope']['lastCallInclusive']
    bodies = [row for row in census['records'] if row['observation'] == 'recordBody']
    initializers = [row for row in census['records'] if row['observation'] == 'recordInitializer']
    body_counts = [sum(row['visits'] for row in bodies if row['voiceIndex'] == voice) for voice in range(3)]
    initializer_counts = [sum(row['visits'] for row in initializers if row['voiceIndex'] == voice) for voice in range(3)]
    body_last = [max(row['lastCall'] for row in bodies if row['voiceIndex'] == voice) for voice in range(3)]
    initializer_last = [max(row['lastCall'] for row in initializers if row['voiceIndex'] == voice) for voice in range(3)]
    assert last_call == 17280 and body_last == [17279] * 3 and initializer_last == [17280] * 3
    assert body_counts == [15682, 16595, 15232]
    assert all(body_counts[v] + initializer_counts[v] == census['voiceEntryCounts'][v] for v in range(3))
    instruction_counts = {r['pc']: r['visits'] for r in census['rawEffectInstructionVisits']}
    assert sum(body_counts) == instruction_counts[0xaa97] == instruction_counts[0xab8d] == 47509
    try:
        assert max(body_last) == last_call
    except AssertionError:
        old_guard_rejected_complete_coverage = True
    else:
        raise AssertionError('Final initializer-only call must expose the obsolete body-per-final-call assumption')
    result = dict(schemaVersion=1, censusPath=str(source.relative_to(ROOT)),
                  censusSha256=hashlib.sha256(data).hexdigest(), firstCall=0, lastCallInclusive=last_call,
                  expectedAuditCalls=last_call + 1, expectedBodiesPerVoice=body_counts,
                  expectedBodyCount=sum(body_counts), lastBodiesPerVoice=body_last,
                  lastInitializersPerVoice=initializer_last,
                  oldGuardRejectedCompleteCoverage=old_guard_rejected_complete_coverage,
                  correctedGuard='Require complete audit call count, no pending entries and body counts per voice equal the census; do not require a body on the final call.',
                  limits='Read-only accounting of an existing intact-execution census, not a new CPU or pitch-model run.')
    target = Path(__file__).with_name('guard-reproducer.json')
    with target.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
