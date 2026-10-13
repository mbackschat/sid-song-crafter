from collections import Counter
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
raw = (HERE / 'coverage.json').read_bytes()
receipt = json.loads(raw)
mechanisms = receipt['mechanisms']
counts = Counter()
record_counts = Counter()
for group in mechanisms:
    counts[group['mechanism']] += group['visits']
for group in receipt['records']:
    record_counts[group['observation']] += group['visits']
assert record_counts['recordBody'] + record_counts['recordInitializer'] == sum(receipt['voiceEntryCounts'])
assert counts['pulseSelectorZero'] + counts['pulseTableSelection'] == record_counts['recordBody']
assert counts['pulseTableStep'] + counts['pulseFallbackStep'] == counts['pulseTableSelection']
assert counts['pulseAdd'] + counts['pulseSubtract'] == counts['pulseTableSelection']
assert counts['filterInitial'] + counts['filterAdditive'] + counts['filterTerminal'] == counts['filterModeTableRead']
assert counts['drumWaveConsume'] == counts['drumAbsolutePitch'] + counts['drumRelativePitch']
hook_counts = [dict(name=hook['name'], pc=hook['pc'], visits=(record_counts[hook['name']]
                if hook['name'].startswith('record') else counts[hook['name']])) for hook in receipt['hookPins']]
result = dict(
    scope=receipt['scope'], source=receipt['source'],
    censusSha256=hashlib.sha256(raw).hexdigest(), toolSha256=receipt['toolSha256'],
    summaryToolSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    reproduce=receipt['command'], summarizeCommand='python3 build/cybernoid-title-mechanism-coverage/summarize.py',
    recordCounts=dict(record_counts), voiceEntryCounts=receipt['voiceEntryCounts'],
    selectedRecordsByVoice={str(voice): sorted({group['recordIndex'] for group in receipt['records'] if group['voiceIndex'] == voice}) for voice in range(3)},
    hookCounts=hook_counts,
    zeroExecutedHooks=[hook for hook in hook_counts if hook['visits'] == 0],
    representativeRoutes=[
        dict(mechanism=name, voiceIndex=group['voiceIndex'], recordIndex=group['recordIndex'],
             variant=group['variant'], firstCall=group['firstCall'], lastCall=group['lastCall'],
             distinctCalls=group['distinctCalls'])
        for name in ('glideOutputCommit', 'glideTargetCompletion', 'vibratoAgeDepthOpcode',
                     'filterAdditive', 'filterOwnerFallback', 'filterTerminal', 'drumWaveConsume',
                     'highByteSweep', 'pulseRunInitialize', 'pulseRunHighWrap', 'onsetNoiseHighOverride')
        for group in mechanisms if group['mechanism'] == name
    ],
    writeComparison=receipt['orderedWriteComparison'],
    audit={name: receipt['audit'][name] for name in ('playCalls', 'initWriteCount', 'playWriteCount', 'maximumPlayCycles')},
    consistencyChecks=['Every voice visit joins a patch initializer or synthesis body.',
                       'Every body joins zero-selector PWM copy or selected PWM arithmetic.',
                       'PWM stages/fallback and add/subtract each cover selected arithmetic.',
                       'Filter initial/additive/terminal cover all mode-table updates.',
                       'Every consumed drum waveform joins absolute or relative pitch.'],
    archiveListingBoundary=dict(
        actualArchiveRange=[0xAC46, 0xAD44],
        sequence=['PWM copy', 'FX3 bit20 high-byte sweep', 'FX3 bit01 filter', 'FX3 bit02 pulse-run', 'packed field4 bit08 frequency addition'],
        absentRecoveredListingBlocks=['waveform arpeggio', 'pulse arpeggio', 'strange filter'],
        basis='Pinned archive bytes and static hook pins, not a zero-visit inference about listing-only code.'),
    limits=receipt['limitations'])
with (HERE / 'summary.json').open('x') as target:
    json.dump(result, target, indent=2)
    target.write('\n')
print(json.dumps(dict(records=dict(record_counts), absentExecutedHooks=[hook['name'] for hook in result['zeroExecutedHooks']],
                     summarySha256=hashlib.sha256((HERE / 'summary.json').read_bytes()).hexdigest())))
