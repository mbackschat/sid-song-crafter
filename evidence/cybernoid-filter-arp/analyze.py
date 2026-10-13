"""Join the retained opening instructions to sound fields and the shared filter."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / '.tools/test-deps')]
from psid_profile import psid_profile
from verify_player import cpu_type
from py65.disassembler import Disassembler

SOURCE_SHA = '41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192'
LISTING_SHA = '119b8cb1ecaf6a9700d1847c9879fa78d50229345dccaaa4f555d8354b73fe66'
TRACE_SHA = 'a2ac87f2b73424a27145eaef9c3720786f78ee4d4e83b6f4642891068413753e'
RECORD_BASE = 0xb014
ROLES = {1: (0, 'bass', 1505), 4: (1, 'arp+filt', 1508), 2: (2, 'bassdrm', 1506)}
STATE = {0x40: 'fx1', 0x41: 'fx2', 0x42: 'fx3', 0x44: 'filterPointerLow',
         0x45: 'filterPointerHigh', 0x48: 'voiceIndex', 0xa683: 'lastFilterOwner'}
for base, name in [(0xa642, 'soundIndex'), (0xa65e, 'noteAge'),
                   (0xa63f, 'basePitchIndex'), (0xa645, 'savedFrequencyHigh'),
                   (0xa64b, 'savedFrequencyLow'),
                   (0xa66d, 'arpeggioPosition'), (0xa670, 'arpeggioPointerLow'),
                   (0xa673, 'arpeggioPointerHigh'),
                   (0xa678, 'filterCutoffHigh'), (0xa67b, 'packedGateFilterDetune')]:
    for voice in range(3):
        STATE[base + voice] = f'{name}.voice{voice + 1}'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def analyze(source, listing, trace_path):
    source_bytes, listing_bytes = source.read_bytes(), listing.read_bytes()
    trace_bytes = gzip.decompress(trace_path.read_bytes())
    check(sha(source_bytes) == SOURCE_SHA, 'Source pin mismatch')
    check(sha(listing_bytes) == LISTING_SHA, 'Listing pin mismatch')
    check(sha(trace_bytes) == TRACE_SHA, 'Canonical opening trace pin mismatch')
    trace = json.loads(trace_bytes)
    check(trace['sourceSha256'] == SOURCE_SHA and trace['profile'] == 'pal-banked'
          and trace['firstCall'] == 0 and trace['lastCallInclusive'] == 63,
          'Expected the canonical title opening')
    profile = psid_profile(source_bytes, profile='pal-banked', subtune=1)
    memory = [0] * 65536
    memory[profile['loadAddress']:profile['endAddress']] = profile['payload']
    disassembler = Disassembler(cpu_type()(memory=memory))

    def static(lo, hi):
        result = []
        while lo < hi:
            length, assembly = disassembler.instruction_at(lo)
            result.append(dict(pc=lo, bytes=bytes(memory[lo:lo + length]).hex(), assembly=assembly))
            lo += length
        check(lo == hi, 'Static range must end on an instruction boundary')
        return result

    programs = []
    for index in range(4):
        pointer = int.from_bytes(bytes(memory[0xafc4 + index * 2:0xafc6 + index * 2]), 'little')
        values = memory[pointer:pointer + 10]
        programs.append(dict(index=index, address=pointer, bytes=values,
                             initialCutoffHigh=values[0], additiveSteps=values[1:4],
                             terminalCutoffHigh=values[4], modeVolume=values[5],
                             ageThresholds=values[6:10]))
    check(programs[1]['address'] == 0xafd6 and programs[1]['bytes'] ==
          [0xa0, 0xfe, 0x01, 0xff, 0x62, 0x3f, 0x02, 0x22, 0x62, 0xa2],
          'Selected filter program differs')

    known = {}
    sid = {w['address']: w['value'] for w in trace['initSidWrites']}
    loads, filter_writes, routing_writes, patch_setups, endings = [], [], [], [], []
    pending_filter = {}
    for index, instruction in enumerate(trace['instructions']):
        address = instruction.get('operandAddress')
        before = instruction.get('operandValueBefore')
        mnemonic = instruction['assembly'].split()[0]
        if address in STATE:
            if address in known:
                check(known[address] == before, f'Retained-state discrepancy at instruction {index}')
            known[address] = before
        voice = known.get(0x48)
        if mnemonic == 'LDA' and address is not None and RECORD_BASE <= address < 0xb0ac:
            record, offset = divmod(address - RECORD_BASE, 8)
            check(record in ROLES and voice == ROLES[record][0], 'Opening role join failed')
            check(before == memory[address], 'Sound record was changed before reading')
            loads.append(dict(instructionIndex=index, call=instruction['tick'],
                              instructionStartCycle=instruction['instructionStartCycle'],
                              pc=instruction['pc'], bytes=instruction['bytes'],
                              voiceIndex=voice, recordIndex=record, fieldOffset=offset,
                              sourceAddress=address, sourceValue=before,
                              x=instruction['x'], y=instruction['y']))
            if instruction['pc'] == 0xa8b4:
                stop = index
                while trace['instructions'][stop]['pc'] != 0xa8ed:
                    stop += 1
                    check(stop - index < 40, 'Patch setup did not reach its filter-state store')
                patch_setups.append(dict(voiceIndex=voice, recordIndex=record,
                                         call=instruction['tick'],
                                         instructions=trace['instructions'][index:stop + 1]))

        if mnemonic in ('STA', 'STX', 'STY'):
            value = instruction[mnemonic[-1].lower()]
            if voice in range(3) and address == 0xa678 + voice:
                pending_filter[voice] = dict(before=before, value=value, instructionIndex=index)
            if address in STATE:
                known[address] = value
            if address is not None and 0xd400 <= address <= 0xd418:
                sid[address] = value
            if address == 0xd417:
                prior = trace['instructions'][index - 1]
                check(prior['pc'] == 0xa7e1 and prior['operandValueBefore'] == value,
                      'Routing must join the actual pattern parameter read')
                routing_writes.append(dict(instructionIndex=index, call=instruction['tick'],
                                           voiceIndex=voice, pc=instruction['pc'], value=value,
                                           parameterRead=prior, resonance=value >> 4,
                                           filteredVoices=[v + 1 for v in range(3) if value & (1 << v)]))
            if address in (0xd416, 0xd418):
                owner, age = known[0xa683], known[0xa65e + voice]
                packed, effects = known[0xa67b + voice], known[0x42]
                check(voice == 1 and owner == voice and effects & 1 and packed & 7 == 1,
                      'Opening shared filter owner/selector changed')
                pointer = known[0x44] | known[0x45] << 8
                check(pointer == programs[1]['address'], 'Filter pointer join failed')
                event = dict(instructionIndex=index, call=instruction['tick'],
                             instructionStartCycle=instruction['instructionStartCycle'],
                             pc=instruction['pc'], address=address, value=value,
                             voiceIndex=voice, retainedState={STATE[a]: v for a, v in sorted(known.items())},
                             filterPointer=pointer, age=age, packedGateFilterDetune=packed,
                             effectFlags=effects, owner=owner)
                if address == 0xd418:
                    check(value == programs[1]['modeVolume'], 'Mode/volume table join failed')
                else:
                    table = programs[1]['bytes']
                    if age < table[6]:
                        phase, expected = 'initial', table[0]
                    elif age >= table[9]:
                        phase, expected = 'terminal', table[4]
                    else:
                        step = max(i for i in range(3) if age >= table[6 + i])
                        phase = f'additive-{step + 1}'
                        expected = (pending_filter[voice]['before'] + table[1 + step]) & 255
                    check(value == expected and pending_filter[voice]['value'] == value,
                          'Cutoff arithmetic disagrees with executed store')
                    event.update(phase=phase, perVoiceCutoffBefore=pending_filter[voice]['before'],
                                 modeledValue=expected, filterStateStore=pending_filter[voice])
                filter_writes.append(event)
        elif address in STATE and mnemonic in ('INC', 'DEC'):
            known[address] = (before + (1 if mnemonic == 'INC' else -1)) & 255
        if instruction['pc'] == 0xae2c:
            endings.append(dict(call=instruction['tick'], instructionIndex=index,
                                state={STATE[a]: v for a, v in sorted(known.items())},
                                sidFilter={f'{a:04x}': sid[a] for a in range(0xd415, 0xd419)}))

    counts = {record: {offset: sum(r['recordIndex'] == record and r['fieldOffset'] == offset
                                  for r in loads) for offset in range(8)} for record in ROLES}
    check(all(sum(fields.values()) == 215 for fields in counts.values()), 'Record load count changed')
    check(len(routing_writes) == 1 and routing_writes[0]['value'] == 0x82,
          'Opening routing observation changed')
    check(len(filter_writes) == 126 and len(endings) == 64, 'Opening coverage changed')
    cutoff = [e for e in filter_writes if e['address'] == 0xd416]
    check([e['call'] for e in cutoff] == list(range(1, 64)), 'Filter cutoff call span changed')
    check(all(e['sidFilter']['d415'] == 0 for e in endings), 'Cutoff low bits changed')
    arp_selection = [dict(instructionIndex=i, **r) for i, r in enumerate(trace['instructions'])
                     if r['tick'] == 0 and r['x'] == 1 and 0xa858 <= r['pc'] <= 0xa871]
    arp_reads = [r for r in arp_selection if r['pc'] in (0xa861, 0xa869)]
    check([r['operandAddress'] for r in arp_reads] == [0xaf81, 0xaf89]
          and [r['operandValueBefore'] for r in arp_reads] == [0x97, 0xaf],
          'Opening arpeggio pointer selection changed')
    arp_pointer = arp_reads[0]['operandValueBefore'] | arp_reads[1]['operandValueBefore'] << 8
    arp_table = memory[arp_pointer:arp_pointer + 4]
    check(arp_table == [2, 0, 5, 8], 'Arpeggio header/offsets changed')
    arp_events, arp_counter = [], 0
    for call in range(1, 64):
        records = [dict(instructionIndex=i, **r) for i, r in enumerate(trace['instructions'])
                   if r['tick'] == call and r['x'] == 1 and 0xa999 <= r['pc'] <= 0xa9be]
        at_pc = {r['pc']: r for r in records}
        check(at_pc[0xa999]['operandValueBefore'] == arp_counter, 'Arpeggio counter continuity changed')
        decremented = (arp_counter - 1) & 255
        wraps = bool(decremented & 128)
        arp_counter = arp_table[0] if wraps else decremented
        check((0xa99e in at_pc) == wraps, 'Signed arpeggio counter wrap branch differs')
        if wraps:
            check(at_pc[0xa99e]['operandAddress'] == arp_pointer
                  and at_pc[0xa99e]['operandValueBefore'] == arp_table[0], 'Arpeggio header read differs')
        check(at_pc[0xa9aa]['operandAddress'] == arp_pointer + arp_counter + 1
              and at_pc[0xa9aa]['operandValueBefore'] == arp_table[arp_counter + 1], 'Arpeggio tone read differs')
        base, offset = at_pc[0xa9ae]['operandValueBefore'], arp_table[arp_counter + 1]
        pitch = (base + offset) & 255
        check(at_pc[0xa9b1]['a'] == pitch and at_pc[0xa9b5]['y'] == pitch
              and at_pc[0xa9bb]['y'] == pitch, 'Arpeggio pitch-index arithmetic differs')
        frequency = [memory[0xae3f + pitch], memory[0xae96 + pitch]]
        check(at_pc[0xa9b5]['operandAddress'] == 0xae3f + pitch
              and at_pc[0xa9bb]['operandAddress'] == 0xae96 + pitch
              and [at_pc[0xa9b5]['operandValueBefore'], at_pc[0xa9bb]['operandValueBefore']] == frequency
              and [at_pc[0xa9b8]['a'], at_pc[0xa9be]['a']] == frequency, 'Arpeggio lookup/shadow stores differ')
        writes = [dict(sidWriteIndex=i, **w) for i, w in enumerate(trace['sidWrites'])
                  if w['tick'] == call and w['address'] in (0xd407, 0xd408)]
        check([w['address'] for w in writes] == [0xd407, 0xd408], 'Voice2 final frequency store layout differs')
        start_length = memory[0xb0c0 + 4]
        check(start_length == 5 and memory[0xb0cc + 4] == 0x41, 'Opening onset parameters changed')
        age_read = next(dict(instructionIndex=i, **r) for i, r in enumerate(trace['instructions'])
                        if r['tick'] == call and r['x'] == 1 and r['pc'] == 0xadc6)
        age = age_read['operandValueBefore']
        restored = start_length <= age < start_length + 2
        expected = [memory[0xae3f + base], memory[0xae96 + base]] if restored else frequency
        if restored:
            restoration = [dict(instructionIndex=i, **r) for i, r in enumerate(trace['instructions'])
                           if r['tick'] == call and r['x'] == 1 and 0xadef <= r['pc'] <= 0xadf8]
            check([r['operandValueBefore'] for r in restoration if r['pc'] in (0xadef, 0xadf5)] == expected,
                  'Onset tail must restore the actual saved base-frequency bytes')
        else:
            restoration = []
        check([w['value'] for w in writes] == expected, 'Final frequency differs from arp plus onset-tail model')
        arp_events.append(dict(call=call, instructions=records, counterAfter=arp_counter,
                               decremented=decremented, headerReloaded=wraps, basePitchIndex=base,
                               offset=offset, pitchIndex=pitch, lookupFrequencyBytes=frequency,
                               onsetAgeRead=age_read, onsetLength=start_length,
                               onsetTailRestoresBase=restored, restorationInstructions=restoration,
                               modeledFinalFrequencyBytes=expected, finalFrequencyWrites=writes))

    fields = [
        ('pulsehi', 'Initial pulse-high low nibble; the unmasked byte is retained. Bit $10 has a separate end-of-row SR=$02 branch, static here.'),
        ('waveform', 'Initial control byte copied to per-voice waveform/control shadows; later onset/drum code can replace it.'),
        ('attdec', 'SID attack/decay byte written at patch setup.'),
        ('susrel', 'SID sustain/release byte written at patch setup.'),
        ('filcount', 'Packed byte: high nibble shifted right twice controls gate masking; low three bits select a filter pointer; bit $08 enables +$0C frequency-word addition in another branch.'),
        ('fx1', 'Contextual pitch-effect byte; with effect flag $10 it instead selects the drum table through its low nibble. Pitch progression belongs to the separate pitch study.'),
        ('fx2', 'Low three bits select a PWM table; upper nibble supplies a later PWM step. Bit $08 also suppresses default filter-owner reset. Do not assign independent meanings to selector/magnitude bits.'),
        ('fx3', 'Effect flags; opening $85 enables filter $01, tone arpeggio $04 and onset transient $80. Drum $10, high-byte sweep $20 and pulse-run $02 have separate archive branches.')]
    check(all(e['basePitchIndex'] == 47 for e in arp_events), 'Opening base pitch changed')
    expected_filter_stores = [(w['tick'], w['instructionPc'], w['address'], w['value'])
                              for w in trace['sidWrites'] if w['address'] in (0xd416, 0xd418)]
    check([(e['call'], e['pc'], e['address'], e['value']) for e in filter_writes] == expected_filter_stores,
          'Filter instruction events disagree with the complete canonical SID ledger')
    return dict(schemaVersion=1, classification='Retained opening instruction/table analysis; no new CPU execution',
                source=dict(path=str(source.relative_to(ROOT)), sha256=SOURCE_SHA,
                            url='https://www.hvsc.de/download/C64Music/MUSICIANS/T/Tel_Jeroen/Cybernoid_II.sid'),
                listing=dict(path=str(listing.relative_to(ROOT)), sha256=LISTING_SHA,
                             url='https://github.com/realdmx/c64_6581_sid_players/blob/f215174fc4c983674808fcd47bc506f96b3d2d04/Tel_Jeroen_MON/Tel_Jeroen_Cybernoid2.asm'),
                trace=dict(path=str(trace_path.relative_to(ROOT)), storedSha256=sha(trace_path.read_bytes()),
                           originalSha256=TRACE_SHA, firstCall=0, lastCallInclusive=63,
                           profile='pal-banked', selectedSubtune=1),
                analyzerSha256=sha(Path(__file__).read_bytes()),
                fields=[dict(offset=i, sourceName=name, contract=contract) for i, (name, contract) in enumerate(fields)],
                records=[dict(index=i, voiceIndex=voice, sourceLabel=label, sourceLine=line,
                              address=RECORD_BASE + i * 8, bytes=memory[RECORD_BASE + i * 8:RECORD_BASE + (i + 1) * 8],
                              fieldLoadCounts=counts[i]) for i, (voice, label, line) in ROLES.items()],
                fieldLoads=loads, patchSetups=patch_setups, routingWrites=routing_writes,
                arpeggioSelection=dict(selector=0x72, index=2, voiceIndex=1, call=0,
                                       instructions=arp_selection, resolvedPointer=arp_pointer,
                                       tableBytes=arp_table),
                arpeggioEvents=arp_events,
                filterPrograms=programs, filterWrites=filter_writes, completedCallStates=endings,
                staticInstructions=dict(patchSetup=static(0xa8b4, 0xa8f0),
                                        gateAndFields=static(0xa916, 0xa985),
                                        routing=static(0xa7c0, 0xa7e9),
                                        arpeggio=static(0xa985, 0xa9c1),
                                        onset=static(0xadbd, 0xae01),
                                        pwmSelection=static(0xab8d, 0xabc3),
                                        pwmTailStep=static(0xabf4, 0xabfb),
                                        highByteSweep=static(0xac54, 0xac68),
                                        pulseRun=static(0xace2, 0xad2a),
                                        filter=static(0xac68, 0xace2),
                                        packedDetune=static(0xad2a, 0xad44)),
                verified=dict(recordLoads=645, filterOwner=1, filterProgram=1,
                              modeVolume=0x3f, routing=0x82, cutoffLow=0,
                              cutoffWriteCalls=[1, 63], executedPhases=sorted({e['phase'] for e in cutoff}),
                              allCutoffWritesMatchParameterizedArithmetic=True,
                              arpeggioBodyCalls=63, arpeggioHeaderReloads=sum(e['headerReloaded'] for e in arp_events),
                              basePitchIndex=47, relativeOffsetsInConsumptionOrder=[8, 5, 0],
                              pitchIndicesInConsumptionOrder=[55, 52, 47],
                              onsetTailBaseRestorationCalls=[e['call'] for e in arp_events if e['onsetTailRestoresBase']],
                              allFinalVoice2FrequencyWritesMatchArpeggioAndOnsetTail=True),
                mechanism=dict(routingOwner='Score prefix; shared D417 is independent of the eight-byte record.',
                               filterOwner='Each enabled voice stores its index at A683. Voices run 3,2,1; multiple enabled writers would overwrite shared D418/D416 in that order.',
                               fallback='Static ACC8..ACDF: only the remembered owner with filter flag clear and FX2 bit08 clear restores D418=1F and cutoff-high80.',
                               stages='Unsigned age comparisons select initial, three additive modulo-256 phases, then terminal cutoff. Note age, not remaining row countdown, drives the filter.',
                               arpeggio='Each synthesis body decrements an unsigned byte, reloads header2 when the result has its sign bit set, then reads position+1. This reverses the data order to offsets8,5,0; add to base index47 and use source low/high frequency tables.',
                               arpeggioOverrides='Record4 onset flag80 restores the saved base frequency at ages5 and6 after the arpeggio lookup; the counter continues independently. Consequently an arpeggio table read is not automatically the final SID pitch.',
                               onset='Patch setup writes the record and skips synthesis body; first filter update is call1, not call0.'),
                additionalWindows=['Later note ages crossing $62/$A2 to execute filter phases 3/terminal, if the score holds a suitable note that long.',
                                   'A record/filter-owner change to exercise fallback and competing filter writers; current voice2 remains sole enabled owner.',
                                   'Full-title instrument roles and actual bass/drum time-sharing require later executed selections; opening labels alone do not prove them.'],
                limits=['The listing is an interpretation route, not complete archive-code equivalence; archive instruction bytes and canonical execution are authoritative.',
                        'Static branches and filter tables outside observed phases are retained separately, not promoted to executed mechanism coverage.',
                        'Retained state is the named working state supported by trace operands/stores, not SID readable state or a full memory dump.',
                        'No original IRQ-host equivalence, sound-quality, reconstructed synthesis, PCM comparison or listening verdict.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/research/cybernoid-ii/Cybernoid_II.sid')
    parser.add_argument('--listing', type=Path, default=ROOT / '.local/downloads/tel-cybernoid2.asm')
    parser.add_argument('--trace', type=Path, default=ROOT / 'evidence/cybernoid-title-instructions/opening.trace.json.gz')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    check(not args.output.exists() and not args.output.is_symlink(), 'Choose a fresh output file')
    result = analyze(args.source.resolve(), args.listing.resolve(), args.trace.resolve())
    with args.output.open('xb') as stream:
        stream.write((json.dumps(result, separators=(',', ':')) + '\n').encode())
    print(json.dumps(dict(output=str(args.output), sha256=sha(args.output.read_bytes()),
                          verified=result['verified'])))
