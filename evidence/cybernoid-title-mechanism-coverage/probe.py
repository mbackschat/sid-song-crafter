import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / '.tools/test-deps')]
from psid_audit import audit_psid
from psid_profile import psid_profile
from verify_player import cpu_type
from py65.disassembler import Disassembler

SOURCE_SHA = '41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192'
LISTING_SHA = '119b8cb1ecaf6a9700d1847c9879fa78d50229345dccaaa4f555d8354b73fe66'
HOOKS = {
    0xA826: 'recordAssignment', 0xA8AD: 'recordInitializer', 0xA963: 'recordBody',
    0xA999: 'toneArpeggio', 0xA9CA: 'vibratoActive', 0xAA0D: 'vibratoAgeDepthOpcode',
    0xAA16: 'vibratoDeltaShift', 0xAA25: 'vibratoDescendingPhase', 0xAA2F: 'vibratoAscendingPhase',
    0xAA2A: 'vibratoLowerReversal', 0xAA3D: 'vibratoUpperReversal',
    0xAA5F: 'vibratoCenterSubtract', 0xAA75: 'vibratoPhaseAdd', 0xAA89: 'vibratoOutputCommit',
    0xAAA4: 'glideActive', 0xAAD2: 'glideInterpolation', 0xAAF0: 'glideNegativeDifference',
    0xAB58: 'glideOutputCommit', 0xAB6C: 'glideTargetCompletion',
    0xAB69: 'pulseSelectorZero', 0xAB9B: 'pulseTableSelection',
    0xABA3: 'pulseWrapHeaderEnabled', 0xABE7: 'pulseThresholdForceDown',
    0xABEE: 'pulseTableStep', 0xABF8: 'pulseFallbackStep',
    0xAC00: 'pulseSubtract', 0xAC1A: 'pulseAdd', 0xAC16: 'pulseLowerReversal',
    0xAC30: 'pulseUpperBoundary', 0xAC34: 'pulseWrapReset', 0xAC41: 'pulseUpperReversal',
    0xAC5C: 'highByteSweep', 0xAC70: 'filterOwnerAssignment',
    0xAC90: 'filterModeTableRead', 0xACB2: 'filterInitial', 0xACC3: 'filterAdditive',
    0xACA2: 'filterTerminal', 0xACD7: 'filterOwnerFallback',
    0xACEA: 'pulseRunActive', 0xACEF: 'pulseRunInitialize', 0xAD03: 'pulseRunAdvance',
    0xAD0D: 'pulseRunCarry', 0xAD17: 'pulseRunHighWrap',
    0xAD33: 'packedField4FrequencyAdd', 0xAD4A: 'drumPointerSetup',
    0xAD7F: 'drumWaveConsume', 0xADA1: 'drumRelativePitch', 0xADAD: 'drumAbsolutePitch',
    0xADC3: 'onsetEnabled', 0xADCE: 'onsetWaveConsume', 0xADD5: 'onsetNoiseHighOverride',
    0xADEF: 'onsetBaseRestore', 0xA75F: 'orderWrap', 0xA70F: 'globalStop',
}
FIELDS = ['pulseHighFlags', 'waveform', 'attackDecay', 'sustainRelease', 'packedGateFilter', 'fx1', 'fx2', 'fx3']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def ledger_hash(rows):
    return sha((json.dumps(rows, separators=(',', ':')) + '\n').encode())


def run(ticks, output):
    if output.exists() or output.is_symlink():
        raise ValueError('Output already exists; choose a fresh JSON path')
    entry = next(entry for entry in json.loads((ROOT / 'config/local-assets.json').read_text())['references'] if entry['id'] == 'cybernoid-ii')
    source = (ROOT / entry['path']).read_bytes()
    assert sha(source) == SOURCE_SHA == entry['sha256']
    listing_path = ROOT / '.local/downloads/tel-cybernoid2.asm'
    listing = listing_path.read_bytes()
    assert sha(listing) == LISTING_SHA
    profile = psid_profile(source, profile='pal-banked', subtune=1)
    original = [0] * 65536
    original[profile['loadAddress']:profile['endAddress']] = profile['payload']
    disassembler = Disassembler(cpu_type()(memory=original))
    pins = {}
    for pc, name in HOOKS.items():
        size, assembly = disassembler.instruction_at(pc)
        pins[pc] = dict(pc=pc, name=name, bytes=bytes(original[pc:pc + size]).hex(), assembly=assembly)
    census, record_counts, pc_counts = {}, {}, Counter()
    voice = None
    entries = [0, 0, 0]
    record_lines = listing.decode().splitlines()[1503:1522]
    labels = [line.split(';', 1)[1].strip() for line in record_lines]
    listing_records = [[int(value, 16) for value in re.findall(r'\$([0-9a-fA-F]{2})\b', line.split(';')[0])]
                       for line in record_lines]
    assert all(original[0xB014 + index * 8:0xB01C + index * 8] == values
               for index, values in enumerate(listing_records)), 'Listing record labels do not match archive bytes'

    def sample(cpu, memory, record):
        ram = memory.data
        return dict(call=memory.tick, instructionStartCycle=memory.instruction_cycle, pc=cpu.pc,
                    a=cpu.a, x=cpu.x, y=cpu.y, status=cpu.p,
                    voiceIndex=voice, recordIndex=record, age=ram[0xA65E + voice],
                    fx1=ram[0x40], fx2=ram[0x41], fx3=ram[0x42],
                    basePitch=ram[0xA63F + voice], pitchIndex=ram[0xA63C + voice],
                    glideTarget=ram[0xA68D + voice], glidePacked=ram[0xA690 + voice],
                    pulseWord=ram[0xA654 + voice] | ram[0xA657 + voice] << 8,
                    pulseDirection=ram[0xA67E + voice], filterOwner=ram[0xA683],
                    filterPointer=ram[0x44] | ram[0x45] << 8,
                    actualOpcode=ram[cpu.pc], actualOperandBytes=ram[cpu.pc + 1:cpu.pc + 3])

    def count(groups, key, event):
        if key not in groups:
            groups[key] = dict(visits=0, distinctCalls=0, firstCall=event['call'], lastCall=None,
                               minimumAge=event['age'], maximumAge=event['age'], examples=[])
        group = groups[key]
        group['visits'] += 1
        group['minimumAge'] = min(group['minimumAge'], event['age'])
        group['maximumAge'] = max(group['maximumAge'], event['age'])
        if group['lastCall'] != event['call']:
            group['distinctCalls'] += 1
            if len(group['examples']) < 3:
                group['examples'].append(event)
        group['lastCall'] = event['call']
        group['lastExample'] = event

    def observe(cpu, memory):
        nonlocal voice
        if memory.phase != 'play':
            return
        pc, ram = cpu.pc, memory.data
        if pc == 0xA603 and memory.tick % 1024 == 0:
            print(f'heartbeat call {memory.tick}/{ticks}', flush=True)
        if pc == 0xA728:
            voice = cpu.x
            assert voice in range(3)
            entries[voice] += 1
        if 0xA944 <= pc < 0xAE01:
            pc_counts[pc] += 1
        name = HOOKS.get(pc)
        if name is None:
            return
        assert voice in range(3)
        assert ram[pc] == original[pc] or pc == 0xAA0D and ram[pc] == 0x7D
        record = cpu.a if name == 'recordAssignment' else ram[0xA642 + voice]
        assert 0 <= record < 19
        event = sample(cpu, memory, record)
        if name.startswith('record'):
            count(record_counts, (voice, record, name), event)
            return
        variant = {}
        if name.startswith('vibrato'):
            variant.update(fx1=ram[0x40], depthNibble=ram[0x40] & 15,
                           extent=(ram[0x40] >> 4) & 7, bit7=bool(ram[0x40] & 128))
            if name == 'vibratoAgeDepthOpcode':
                variant['operation'] = 'ADC age high-delta' if ram[pc] == 0x7D else 'LDY age'
        if name.startswith('glide'):
            variant.update(packed=ram[0xA690 + voice], lowNibble=ram[0xA690 + voice] & 15,
                           targetComparison='up' if ram[0xA68D + voice] > ram[0xA63F + voice] else 'down' if ram[0xA68D + voice] < ram[0xA63F + voice] else 'equal')
            if name == 'glideOutputCommit':
                variant['operation'] = 'ADC' if ram[0xAB53] == 0x69 else 'SBC'
        if name.startswith('pulse') and not name.startswith('pulseRun'):
            selector = ram[0x41] & 7
            variant['selector'] = selector
            if name == 'pulseTableSelection':
                pointer = 0xAFF4 + cpu.y
                event.update(tableAddress=pointer, tableBytes=ram[pointer:pointer + 8])
            if name == 'pulseTableStep':
                variant.update(stage=(cpu.y - (selector - 1) * 8 - 1) // 2, step=cpu.a)
            elif name == 'pulseFallbackStep':
                variant['step'] = cpu.a
        if name.startswith('filter'):
            variant['selector'] = ram[0xA67B + voice] & 7
            if name != 'filterOwnerAssignment' and name != 'filterOwnerFallback':
                pointer = ram[0x44] | ram[0x45] << 8
                assert profile['loadAddress'] <= pointer < profile['endAddress'] - 9
                variant['programAddress'] = pointer
                event['tableBytes'] = ram[pointer:pointer + 10]
            if name == 'filterAdditive':
                variant['stage'] = cpu.y
                event['parameterAddress'] = event['filterPointer'] + cpu.y
                event['parameterValue'] = ram[event['parameterAddress']]
        if name.startswith('drum'):
            variant['selector'] = ram[0x40] & 15
            if name == 'drumWaveConsume':
                pointer = ram[pc + 1] | ram[pc + 2] << 8
                event.update(tableAddress=pointer, sourceAddress=(pointer + cpu.y) & 65535,
                             sourceValue=ram[(pointer + cpu.y) & 65535])
        if name == 'toneArpeggio':
            pointer = ram[0xA670 + voice] | ram[0xA673 + voice] << 8
            variant['programAddress'] = pointer
            event['tableHeader'] = ram[pointer]
        if name.startswith('onset'):
            variant.update(length=ram[0xB0C0 + record], onset=ram[0xB0CC + record])
        count(census, (voice, record, name, json.dumps(variant, sort_keys=True)), event)

    print('starting pinned pal-banked title audit', ticks, 'calls', flush=True)
    report, writes = audit_psid(source, ticks, observer=observe, subtune=1, profile='pal-banked')
    canonical_path = ROOT / 'evidence/cybernoid-form-36000/audit.writes.json.gz'
    packed = canonical_path.read_bytes()
    canonical = json.loads(gzip.decompress(packed))
    expected = [row for row in canonical if row['phase'] == 'init' or row['tick'] < ticks]
    assert writes == expected, 'Ordered init/play write ledger differs from canonical prefix'
    records = []
    for (v, record, kind), value in sorted(record_counts.items()):
        address = 0xB014 + record * 8
        values = original[address:address + 8]
        records.append(dict(voiceIndex=v, recordIndex=record, observation=kind, sourceAddress=address,
                            fields=dict(zip(FIELDS, values)), sourceLabel=labels[record], **value))
    result = dict(schemaVersion=1, scope=dict(firstCall=0, lastCallInclusive=ticks - 1, selectedSubtune=1,
                  executionProfile='pal-banked', purpose='Executed mechanism coverage and representative windows'),
                  source=dict(path=entry['path'], url=entry['url'], sha256=SOURCE_SHA),
                  listing=dict(path=str(listing_path.relative_to(ROOT)), sha256=LISTING_SHA),
                  toolSha256=sha(Path(__file__).read_bytes()),
                  sharedToolHashes={name: sha((ROOT / 'scripts' / name).read_bytes()) for name in ('psid_audit.py', 'psid_profile.py', 'verify_player.py')},
                  hookPins=list(pins.values()), voiceEntryCounts=entries,
                  records=records,
                  mechanisms=[dict(voiceIndex=v, recordIndex=record, mechanism=name, variant=json.loads(variant), **value)
                              for (v, record, name, variant), value in sorted(census.items())],
                  rawEffectInstructionVisits=[dict(pc=pc, visits=visits, classifiedHook=HOOKS.get(pc)) for pc, visits in sorted(pc_counts.items())],
                  audit=report,
                  orderedWriteComparison=dict(equal=True, recordCount=len(writes),
                      hashRecipe='SHA256(UTF8(json.dumps(ordered_records,separators=(",",":"))+"\\n")); no field or timing normalization.',
                      prefixSha256=ledger_hash(writes), canonicalPrefixSha256=ledger_hash(expected),
                      canonicalPath=str(canonical_path.relative_to(ROOT)), canonicalCompressedSha256=sha(packed)),
                  command=f'PYTHONPATH=.tools/test-deps python3 build/cybernoid-title-mechanism-coverage/probe.py --ticks {ticks} --output {output}',
                  limitations=[
                      'Mechanism hooks mark instructions inside accepted paths, not preceding flag tests. Counts distinguish raw instruction visits from distinct calls; looped arithmetic may visit a hook multiple times in one call.',
                      'Voice index follows executed STX48 atA728, not temporary X table/division indexes. Record counts distinguish score assignments, patch initializers, and synthesis bodies.',
                      'Raw effect instruction visits are unclassified instruction coverage, not independent semantic claims; no full instruction dump or CPU/RAM snapshot is emitted.',
                      'Recovered waveform-/pulse-arpeggio and strange-filter blocks are absent from actual archive AC46..AD44; no hooks are assigned to those listing-only blocks.',
                      'Flag parameters, retained buffers and table bytes are source-bound observations, not a complete editable synthesis model. No IRQ-host, SID physical-state, PCM or listening equivalence claim.',
                  ])
    with output.open('x') as target:
        json.dump(result, target, indent=2)
        target.write('\n')
    print(json.dumps(dict(output=str(output), sha256=sha(output.read_bytes()), mechanisms=len(census), recordGroups=len(records), writes=len(writes), peakCycles=report['maximumPlayCycles'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ticks', type=int, default=17281)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.ticks, args.output)
