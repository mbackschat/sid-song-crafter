import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / '.local/research/cybernoid-ii/Cybernoid_II.sid'
LISTING = ROOT / '.local/downloads/tel-cybernoid2.asm'
TRACE = ROOT / 'evidence/cybernoid-title-instructions/opening.trace.json.gz'
PINS = {
    'source': '41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192',
    'listing': '119b8cb1ecaf6a9700d1847c9879fa78d50229345dccaaa4f555d8354b73fe66',
    'trace': '4d2427d09244af5a56f7afeda21696ff60c4107aae19196fb163008622641cef',
    'decodedTrace': 'a2ac87f2b73424a27145eaef9c3720786f78ee4d4e83b6f4642891068413753e',
}
STATE = {
    'instrument': 0xA642, 'age': 0xA65E, 'baseWave': 0xA639,
    'baseFrequencyLow': 0xA64B, 'baseFrequencyHigh': 0xA645,
    'frequencyLow': 0xA693, 'frequencyHigh': 0xA696,
    'pulseLow': 0xA654, 'pulseHigh': 0xA657, 'pulseDirection': 0xA67E,
    'pulseFlags': 0xA65A, 'pulseOutputLow': 0xA6AB, 'pulseOutputHigh': 0xA6AE,
    'wave': 0xA687, 'gateMask': 0xA69C, 'packedGateFilter': 0xA67B,
}
TABLES = {
    'bassRecord': (0xB01C, 8), 'bassdrmRecord': (0xB024, 8),
    'pulseSlot4': (0xB00C, 8), 'drum0Pointers': (0xAF45, 4),
    'drum0Wave': (0xAF4D, 13), 'drum0FrequencyHigh': (0xAF5A, 12),
    'onsetLength': (0xB0C0, 12), 'onsetWave': (0xB0CC, 12),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pulse_step(width, up, age, slot, fx2):
    step = next((slot[i + 1] for i in (2, 4, 6) if age <= (slot[i] & 0x7F)), fx2 & 0xF0)
    width = (width + (step if up else -step)) & 0xFFFF
    if up and width >> 8 >= slot[1]:
        up = 0
    elif not up and width >> 8 < (slot[0] & 0x0F):
        up = 1
    return width, up, step


def onset_step(age, base_wave, base_word, output_wave, output_word, length, onset):
    if age < length:
        return (0x81, (0xFA << 8) | (output_word & 0xFF)) if onset >= 0x7F else (onset, output_word)
    if age < length + 2:
        return base_wave, base_word
    return output_wave, output_word


def drum_step(age, output_wave, output_word, mask, waves, high_words):
    if age < waves[0]:
        wave = waves[age]
        return wave, high_words[age - 1] << 8, 0xFF if wave & 1 else 0xFE
    return output_wave, output_word, mask


def main(output):
    raw = {'source': SOURCE.read_bytes(), 'listing': LISTING.read_bytes(), 'trace': TRACE.read_bytes()}
    raw['decodedTrace'] = gzip.decompress(raw['trace'])
    for name, data in raw.items():
        assert sha(data) == PINS[name], f'{name} hash differs'
    trace = json.loads(raw['decodedTrace'])
    assert (trace['firstCall'], trace['lastCallInclusive'], trace['profile']) == (0, 63, 'pal-banked')
    source = raw['source']
    offset = int.from_bytes(source[6:8], 'big')
    assert int.from_bytes(source[8:10], 'big') == 0
    load = int.from_bytes(source[offset:offset + 2], 'little')
    payload = source[offset + 2:]
    assert load == 0xA600

    def archive(address, length):
        result = payload[address - load:address - load + length]
        assert len(result) == length
        return list(result)

    tables = {name: {'address': address, 'bytes': archive(address, length)} for name, (address, length) in TABLES.items()}
    relevant_addresses = {base + voice for base in STATE.values() for voice in range(3)}
    memory = {}
    contexts = defaultdict(list)
    snapshots = {}
    voice = None
    for index, row in enumerate(trace['instructions']):
        if row['pc'] == 0xA728:
            voice = row['x']
        if voice not in (0, 2):
            continue
        contexts[row['tick'], voice].append((index, row))
        address = row.get('operandAddress')
        if address in relevant_addresses:
            if address in memory:
                assert memory[address] == row['operandValueBefore'], (index, address)
            memory[address] = row['operandValueBefore']
            mnemonic = row['assembly'].split()[0]
            if mnemonic in ('STA', 'STX', 'STY'):
                memory[address] = row[{'STA': 'a', 'STX': 'x', 'STY': 'y'}[mnemonic]]
            elif mnemonic in ('INC', 'DEC'):
                memory[address] = (memory[address] + (1 if mnemonic == 'INC' else -1)) & 0xFF
        if row['pc'] in (0xAD44, 0xAE01):
            snapshots[row['tick'], voice, row['pc']] = {name: memory.get(base + voice) for name, base in STATE.items()}

    def one(items, pc):
        rows = [(index, row) for index, row in items if row['pc'] == pc]
        assert len(rows) == 1, (pc, len(rows))
        return rows[0]

    def word(state, prefix):
        return state[prefix + 'Low'] | state[prefix + 'High'] << 8

    call_rows = []
    checks = Counter()
    selected = {}
    table_reads = defaultdict(list)
    coverage = Counter()
    width, up = 0x500, 1
    boundary_calls = (22, 23, 39, 40, 56, 57)
    for (tick, voice), items in sorted(contexts.items()):
        init = any(row['pc'] == 0xA8CD for _, row in items)
        state = snapshots[tick, voice, 0xAE01]
        writes = {pc: one(items, pc) for pc in (0xAE0B, 0xAE11, 0xAE17, 0xAE1D, 0xAE23)}
        result = {
            'call': tick, 'voiceIndex': voice, 'recordId': 1 if voice == 0 else 2,
            'initializer': init, 'age': state['age'],
            'control': writes[0xAE0B][1]['a'],
            'frequencyWord': writes[0xAE11][1]['a'] | writes[0xAE17][1]['a'] << 8,
            'pulseWord': writes[0xAE1D][1]['a'] | writes[0xAE23][1]['a'] << 8,
            'writerTraceIndices': {str(pc): index for pc, (index, _) in writes.items()},
            'postProgramState': state,
        }
        if init:
            assert not any(row['pc'] == 0xAB8D for _, row in items)
            checks['initializerSkipsMacros'] += 1
            expected_wave = tables['bassRecord' if voice == 0 else 'bassdrmRecord']['bytes'][1]
            assert result['control'] == expected_wave and state['gateMask'] == 0xFF
        elif voice == 0:
            width, up, step = pulse_step(width, up, state['age'], tables['pulseSlot4']['bytes'], 0x64)
            assert (width, up) == (result['pulseWord'], state['pulseDirection'])
            result['computedPulse'] = {'word': width, 'direction': up, 'step': step}
            checks['computedBassPulseBodies'] += 1
            before = snapshots[tick, voice, 0xAD44]
            predicted_wave, predicted_word = onset_step(
                state['age'], before['baseWave'], word(before, 'baseFrequency'),
                before['wave'], word(before, 'frequency'),
                tables['onsetLength']['bytes'][1], tables['onsetWave']['bytes'][1])
            assert predicted_wave & state['gateMask'] == result['control']
            assert predicted_word == result['frequencyWord']
            checks['computedBassOnsetBodies'] += 1
            result['preWaveState'] = before
        else:
            before = snapshots[tick, voice, 0xAD44]
            predicted_wave, predicted_word, predicted_mask = drum_step(
                state['age'], before['wave'], word(before, 'frequency'), before['gateMask'],
                tables['drum0Wave']['bytes'], tables['drum0FrequencyHigh']['bytes'])
            assert predicted_wave & predicted_mask == result['control']
            assert (predicted_word, predicted_mask) == (result['frequencyWord'], state['gateMask'])
            assert result['pulseWord'] == 0x800
            checks['computedDrumBodies'] += 1
            result['preWaveState'] = before
        call_rows.append(result)
        for index, row in items:
            pc = row['pc']
            if 0xAB8D <= pc <= 0xAC51 or 0xAD44 <= pc <= 0xAE23 or 0xA8AD <= pc <= 0xA913 or pc in (0xA72A, 0xA7B7, 0xA963, 0xA968, 0xA973):
                coverage[voice, pc] += 1
                key = (voice, pc, row['bytes'])
                selected.setdefault(key, {'traceIndex': index, 'voiceIndex': voice, **row})
                if voice == 0 and tick in boundary_calls and pc in (0xABFB, 0xAC12, 0xAC2C, 0xAC30, 0xAC43, 0xAC48, 0xAC4E):
                    selected[('boundary', index)] = {'traceIndex': index, 'voiceIndex': voice, **row}
            address = row.get('operandAddress')
            if address is not None and row['assembly'].startswith(('LDA ', 'CMP ')) and any(start <= address < start + length for start, length in TABLES.values()):
                assert row['operandValueBefore'] == archive(address, 1)[0]
                table_reads[voice, pc, address, row['operandValueBefore']].append({'call': tick, 'traceIndex': index})

    assert len(call_rows) == 128
    assert checks == Counter(initializerSkipsMacros=4, computedBassPulseBodies=63, computedBassOnsetBodies=63, computedDrumBodies=61)
    listing_lines = raw['listing'].decode().splitlines()
    listing_table_lines = {
        'bassRecord': (1505, 1505), 'bassdrmRecord': (1506, 1506),
        'pulseSlot4': (1493, 1494), 'drum0Wave': (1416, 1419),
        'drum0FrequencyHigh': (1421, 1423),
        'onsetLength': (1532, 1534), 'onsetWave': (1537, 1539),
    }
    listing_comparisons = {}
    for name, (first, last) in listing_table_lines.items():
        lines = [line.split(';')[0] for line in listing_lines[first - 1:last]]
        values = [int(value, 16) for line in lines for value in re.findall(r'\$([0-9a-fA-F]{2})\b', line)]
        original = tables[name]['bytes']
        assert len(values) == len(original)
        equal = values == original
        assert equal == (name != 'drum0Wave')
        listing_comparisons[name] = {
            'listingLines': [first, last], 'listingBytes': values,
            'archiveAddress': tables[name]['address'], 'archiveBytes': original, 'match': equal,
            'differentOffsets': [index for index, (a, b) in enumerate(zip(values, original)) if a != b],
        }
    listing_regions = [(430, 488), (843, 951), (1213, 1333), (1411, 1424), (1483, 1507), (1531, 1539)]
    receipt = {
        'schemaVersion': 1,
        'scope': {'subtune': 1, 'firstCall': 0, 'lastCallInclusive': 63, 'voiceIndices': [0, 2], 'additionalDriverExecution': False, 'oracle': 'Existing canonical instruction trace; independent local arithmetic compared with traced final writes'},
        'provenance': {
            'source': {'path': str(SOURCE.relative_to(ROOT)), 'sha256': PINS['source'], 'loadAddress': load},
            'listing': {'path': str(LISTING.relative_to(ROOT)), 'sha256': PINS['listing'], 'revision': 'f215174fc4c983674808fcd47bc506f96b3d2d04'},
            'trace': {'path': str(TRACE.relative_to(ROOT)), 'compressedSha256': PINS['trace'], 'decodedSha256': PINS['decodedTrace'], 'instructionCount': len(trace['instructions']), 'producerToolSha256': trace['toolSha256'], 'audit': trace['audit']},
            'checker': {'sha256': sha(Path(__file__).read_bytes()), 'command': f'python3 build/cybernoid-wave-pwm/check-mechanisms.py --output {output}'},
            'owningStudy': 'docs/research/composition/cybernoid-ii-preparation.md',
        },
        'recipes': {
            'voiceOwnership': 'Latest executed STX $48 at A728 gives driver voiceIndex even while X is temporarily an instrument/drum-table offset. No claim that arbitrary later X is a voice.',
            'state': 'Retain only named bytes. Seed first access from trace operandValueBefore, check each subsequent pre-access value, update STA/STX/STY/INC/DEC from pre-instruction state. No CPU replay or whole-RAM dump.',
            'instructionEvidence': 'First original trace row for each (voiceIndex,pc,executed instruction bytes), plus exact PWM-boundary rows. Rows retain canonical zero-based traceIndex and pre-instruction CPU/operand state.',
            'timestamps': 'instructionStartCycle is elapsed CPU cycles at instruction entry, not a SID bus timestamp.',
        },
        'stateAddresses': STATE,
        'staticArchiveTables': tables,
        'listingBoundary': {
            'tableComparisons': listing_comparisons,
            'selectedLineHashes': [{'firstLine': first, 'lastLineInclusive': last, 'sha256Utf8JoinedWithLf': sha(('\n'.join(listing_lines[first - 1:last]) + '\n').encode())} for first, last in listing_regions],
        },
        'contracts': [
            {'name': 'initializer', 'executedPcs': [0xA7B7, 0xA8AD, 0xA8CD, 0xA8D0, 0xA8D5, 0xA8D8, 0xA8DC, 0xA8E1, 0xA8E4, 0xA8E9, 0xA8ED, 0xA910, 0xA913], 'semantics': 'New note resets age to0, waveform/base waveform from field1, pulse low/output low to0, pulse high/output high to field0&0F, raw field0 flags retained, direction1, packed gate/filter field4 retained. Sets gate maskFF and jumps straight to writer: no PWM/onset/drum body at age0. Observed initializer calls bass[0], bassdrm[0,24,48].'},
            {'name': 'bassPWM', 'executedPcs': [0xAB8D, 0xAB98, 0xAB9A, 0xAB9B, 0xABA5, 0xABAB, 0xABB2, 0xABBB, 0xABCA, 0xABD9, 0xABEE, 0xABF8, 0xABFB, 0xAC00, 0xAC12, 0xAC1A, 0xAC2C, 0xAC43, 0xAC46], 'semantics': 'FX2=64: selector low3=4. Three ASLs leave C0, so SBC07 produces 8*4-8=24, selecting AFF4+24=B00C. Slot lower07 upper0D, age thresholds3/6/9, steps70/60/50, then FX2&F0=60 from age10. Direction1 adds, direction0 subtracts the step as16-bit arithmetic. Up crossing high>=0D flips down; down crossing high<07 flips up. No clamp: observed reversals at widths0D40(call22),06E0(call39),0D40(call56). Copy accumulator to pulse output every body.'},
            {'name': 'bassOnset', 'executedPcs': [0xADBD, 0xADC3, 0xADC6, 0xADC9, 0xADCE, 0xADD1, 0xADD7, 0xADDF, 0xADE3, 0xADE5, 0xADEB, 0xADEF, 0xADF2, 0xADF8, 0xADFE], 'semantics': 'FX3 bit80 active. Instrument1 length2 atB0C1, onset81 atB0CD. Age1 sets waveform81 and output frequency highFA, retaining existing low byte (observed FACF). Ages2/3 restore waveform41 and frequency from base buffers. Age>=4 does no onset override. Age0 initializer skips this path, hence only one observed noise call.'},
            {'name': 'bassdrm', 'executedPcs': [0xAD44, 0xAD4A, 0xAD50, 0xAD51, 0xAD5A, 0xAD63, 0xAD69, 0xAD6F, 0xAD72, 0xAD77, 0xAD7A, 0xAD7F, 0xAD82, 0xAD8F, 0xAD93, 0xAD9F, 0xADB2, 0xADB7, 0xADBA], 'semantics': 'FX3 bit10 active; FX1 low-nibble0 selects pointer pairAF45/AF47 -> waveAF4D/frequencyAF5A. Patches absolute waveform-length/data and frequency operands, then reads length11 and patches comparisonAD7B. Active ages1..10 read waveform[age] and frequencyHigh[age-1], output low0; set gate maskFF iff waveform bit0, elseFE. Age>=11 skips program modifications. Initializers0/24/48 output11 and score frequency, then ages1..10 produce wave81,41,40x8 and frequency3400,0A00,0800,0600,0400,0500,0600,0500,0400,0500. Existing output40/0500 persists after age10 in this observed passage. FX2 selector0 skips PWM arithmetic and keeps pulse0800.'},
            {'name': 'writer', 'executedPcs': [0xAE01, 0xAE08, 0xAE0B, 0xAE11, 0xAE17, 0xAE1D, 0xAE23], 'semantics': 'Restores driver X and SID-offset Y; writes control=(wave&gateMask), frequency low, frequency high, pulse low, pulse high in that order. This checker compares that final group only; initializer earlier frequency/AD/SR stores are preserved in the canonical trace.'},
        ],
        'checks': dict(checks),
        'calls': call_rows,
        'executedInstructionCoverage': [{'voiceIndex': voice, 'pc': pc, 'count': count} for (voice, pc), count in sorted(coverage.items())],
        'selectedInstructions': sorted(selected.values(), key=lambda row: row['traceIndex']),
        'executedTableReads': [{'voiceIndex': voice, 'pc': pc, 'address': address, 'value': value, 'occurrences': occurrences} for (voice, pc, address, value), occurrences in sorted(table_reads.items())],
        'staticUnexecuted': [
            {'name': 'pulseWrapHeader80', 'address': 0xAC30, 'bytes': archive(0xAC30, 22), 'limit': 'Selected slot header07 has no80 bit; reset-to-lower branch AC34..AC3F is static only. Do not generalize checker to wrap mode.'},
            {'name': 'pulseThresholdDirectionBit80', 'address': 0xABE1, 'bytes': archive(0xABE1, 13), 'limit': 'Selected threshold bytes03/06/09 have no80 bit. Direction-clear alternative is not executed.'},
            {'name': 'drumRelativePitch', 'address': 0xAD9B, 'bytes': archive(0xAD9B, 18), 'limit': 'FX1 bit10 clear in selected drum record; note-relative path ADA1..ADAA not executed or independently modeled.'},
        ],
        'limitations': [
            'Only pinned title subtune1 calls0..63 and records1/2. No full-title waveform/PWM completeness claim or additional source execution.',
            'Onset/drum check uses traced incoming frequency/wave/gate buffers: this isolates program arithmetic and does not independently model upstream pitch, filter, arpeggio, gate scheduling or envelope routines.',
            'PWM model covers selected non-wrap header and zero threshold-direction flags. Word arithmetic wrap follows instructions but no selected64-call case reaches16-bit wrap.',
            'Raw field0 bit10 is checked separately atA947/A949, outside this bounded model. FX2 low3 selects PWM slot and upper nibble is fallback step; individual bit1/bit7 are not separate booleans in this path.',
            'AC54 FX3&20 is a static high-byte sweep (AC5C baseFrequencyHigh; SEC/SBC1; storebase/output), not a waveform-arpeggio claim. Neither selected record activates bit20.',
            'No waveform oscillator, envelope, physical chip, PCM or listening equivalence claim; no reference binary/audio is emitted.',
        ],
    }
    with output.open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'output': str(output), 'sha256': sha(output.read_bytes()), 'checks': dict(checks), 'selectedInstructions': len(selected), 'tableReadGroups': len(table_reads), 'calls': len(call_rows)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args().output)
