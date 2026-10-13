"""Retain source-pinned Deflektor order/row observations under the guarded banked host."""

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid
from verify_player import require


SOURCE_SHA = '606ad4cb19e29c060bb77a9b44253dee62d3d972724acb6cddf625fc2466d44d'
TOOLS = {
    'psid_profile.py': 'edc1109d1b393541a1df1c8d678923faab1d5240996c2eaee63db8691e9ea0ff',
    'psid_audit.py': '4446a19a325e625e59f100aac0b186478fb1633f65886b260db2ad3da11419a5',
    'sid_audit_host.py': 'ea1949d711126b5150225f0d68a3462dbbfe9fffe094e448f9b758889808b0ed',
    'verify_player.py': 'c69317c5d781c175ef0cef39a6e2713187b17e1de5b3f144ad69d49e6a271aab',
}
PATTERN_READS = {0xc2b0: 'token', 0xc2b9: 'token', 0xc2be: 'token',
                 0xc477: 'noteDuration', 0xc480: 'noteDuration', 0xc485: 'noteDuration',
                 0xc8bc: 'helper', 0xc8c3: 'helper', 0xc8c6: 'helper'}
ORDER_READS = {0xc2d6: 'command', 0xc871: 'parameterC0C0', 0xc880: 'transpose',
               0xc89b: 'instrumentMapping', 0xc2fc: 'modeVolume'}
RETURNS = {0xc291: 'writer', 0xc1e4: 'rowBoundarySkip', 0xc2f2: 'stopClearing', 0xc10b: 'stopped'}
EFFECT_NAMES = {0xc0ae: 'repeatCount', 0xc0b1: 'rowCountdown', 0xc0b7: 'releaseThreshold',
                0xc0c0: 'orderParameterC0C0', 0xc0e7: 'restCountdown', 0xc102: 'pitchIndex'}
HOOK_PCS = sorted(set(PATTERN_READS) | set(ORDER_READS) | set(RETURNS) | {
    0xc292, 0xc2c4, 0xc2c9, 0xc2d3, 0xc2e0, 0xc335, 0xc3df, 0xc3e3,
    0xc354, 0xc525, 0xc44a, 0xc886, 0xc877, 0xc8ac, 0xc8a3, 0xc301, 0xc86d,
    0xc118, 0xc127, 0xc136, 0xc373, 0xc389})
RAM_HASH_RECIPE = 'SHA256(bytes(AuditMemory.data)): all 65536 backing-memory bytes in ascending address order, including loaded source, stack and I/O write shadows; no normalization.'
MACHINE_HASH_RECIPE = 'SHA256(bytes(AuditMemory.data)+bytes([A,X,Y,SP,P])+PC.to_bytes(2,"little")), immediately before the final callable RTS; no normalization. Absolute instruction-cycle bookkeeping is not included.'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def word(ram, address):
    return ram[address] | ram[address + 1] << 8


def registers(cpu):
    return dict(a=cpu.a, x=cpu.x, y=cpu.y, sp=cpu.sp, p=cpu.p, pc=cpu.pc)


def named_state(ram):
    voices = []
    for voice in range(3):
        fields = dict(voiceIndex=voice, orderCursor=ram[0xc08b + voice],
                      transpose=ram[0xc08e + voice], patternCursor=ram[0xc091 + voice],
                      patternPointer=word(ram, 0xf7 + 2 * voice),
                      sidShadow=ram[0xc095 + 7 * voice:0xc09c + 7 * voice])
        fields.update({EFFECT_NAMES.get(base, f'driver{base:04X}'): ram[base + voice]
                       for base in range(0xc0ae, 0xc105, 3)})
        voices.append(fields)
    return dict(globals=dict(playFlag=ram[0xc006], songEntryOffset=ram[0xc094],
                             currentVoice=ram[0xc08a], sidVoiceOffset=ram[0xc089],
                             filterCutoffLow=ram[0xc0aa], filterCutoffHigh=ram[0xc0ab],
                             filterRouting=ram[0xc0ac], modeVolume=ram[0xc0ad],
                             rowBoundarySkip=ram[0xc105]),
                instrumentMapping=ram[0xc058:0xc070], voices=voices)


def source_tables(data):
    # Embedded load/payload extents and table boundaries are fixed by this exact source pin.
    require(digest(data) == SOURCE_SHA, 'Source is not the pinned Deflektor reference')
    require(len(data) == 4081 and data[124:126] == b'\x00\xc0', 'Pinned payload layout changed')
    ram = [0] * 65536
    ram[0xc000:0xcf73] = data[126:]
    pointers = [ram[0xcad1 + index] | ram[0xcaf5 + index] << 8 for index in range(36)]
    require(pointers == sorted(pointers) and len(set(pointers)) == 36,
            'Pattern-table span is not the pinned ascending layout')
    orders = [dict(voiceIndex=index, pointer=base, bytes=ram[base:end]) for index, (base, end) in
              enumerate(((0xca27, 0xca5b), (0xca5b, 0xca9b), (0xca9b, 0xcad1)))]
    require([word(ram, 0xca21 + 2 * i) for i in range(3)] == [order['pointer'] for order in orders],
            'Title order-pointer triplet changed')
    return ram, dict(schemaVersion=1, sourceSha256=SOURCE_SHA,
                     tableBasis='Exact pinned data boundaries; pointer-table cardinality 36 follows CAD1/CAF5/CB19 boundaries. Final pattern is bounded by payload end, not a claim that every retained byte is consumed.',
                     orderPointerTable=dict(address=0xca21, entries=[order['pointer'] for order in orders]),
                     orders=orders,
                     patternPointerTables=dict(lowAddress=0xcad1, highAddress=0xcaf5, pointers=pointers),
                     patterns=[dict(patternId=i, pointer=base, bytes=ram[base:end]) for i, (base, end) in
                               enumerate(zip(pointers, pointers[1:] + [0xcf73]))],
                     recordTable=dict(address=0xc007, recordBytes=9,
                                      records=[dict(recordIndex=i, recordOffset=9 * i,
                                                    fields=ram[0xc007 + 9 * i:0xc010 + 9 * i]) for i in range(9)]),
                     initialMapping=dict(address=0xc058, bytes=ram[0xc058:0xc070]),
                     initMappingDefaults=dict(address=0xc070, bytes=ram[0xc070:0xc088]),
                     hookBytes=[dict(pc=pc, bytes=bytes(ram[pc:pc + 4]).hex()) for pc in HOOK_PCS],
                     stateMap=dict(orderCursor=0xc08b, transpose=0xc08e, patternCursor=0xc091,
                                   repeatCount=0xc0ae, rowCountdown=0xc0b1, playFlag=0xc006,
                                   patternPointers=0xf7, instrumentMapping=0xc058,
                                   sidShadow=0xc095, effectTriples=[dict(address=base,
                                   name=EFFECT_NAMES.get(base, f'driver{base:04X}')) for base in range(0xc0ae, 0xc105, 3)]))


def observe_form(data, calls):
    source, tables = source_tables(data)
    events, states, instructions = [], [], []
    last_order, last_pattern, last_slot = {}, {}, {}
    first_stop = None
    initial_state = None
    pending_instructions = []
    pending_call = None

    def observe(cpu, memory):
        nonlocal first_stop, initial_state, pending_instructions, pending_call
        ram = memory.data
        if memory.phase == 'init':
            instructions.append(dict(phase='init', call=None, pc=cpu.pc,
                                     instructionStartCycle=memory.instruction_cycle,
                                     cpu=registers(cpu), opcode=ram[cpu.pc]))
            if cpu.pc == 0xc86d:
                require(memory.instruction == 'RTS' and cpu.sp == 253 and word(ram, 0x1fe) == 0x0439,
                        'Initialization checkpoint is not the shared callable return')
                initial_state = named_state(ram)
            return
        if pending_call != memory.tick:
            pending_call = memory.tick
            pending_instructions = []
        # Retain the ending call in full without buffering the complete title instruction stream.
        pending_instructions.append(dict(phase='play', call=memory.tick, pc=cpu.pc,
                                         instructionStartCycle=memory.instruction_cycle,
                                         cpu=registers(cpu), opcode=ram[cpu.pc]))
        if cpu.pc in RETURNS:
            require(memory.instruction == 'RTS' and cpu.sp == 253 and word(ram, 0x1fe) == 0x044c,
                    'Form checkpoint is not the final shared callable RTS')
            encoded = bytes(ram)
            states.append(dict(call=memory.tick, returnPc=cpu.pc, returnKind=RETURNS[cpu.pc],
                               instructionStartCycle=memory.instruction_cycle, cpu=registers(cpu),
                               ramSha256=digest(encoded), machineStateSha256=digest(encoded + bytes(
                                   [cpu.a, cpu.x, cpu.y, cpu.sp, cpu.p]) + cpu.pc.to_bytes(2, 'little')),
                               **named_state(ram)))
            if memory.tick < 64 or first_stop is not None and first_stop <= memory.tick <= first_stop + 64:
                instructions.extend(pending_instructions)
            return
        pc = cpu.pc
        if pc not in HOOK_PCS:
            return
        voice = (pc - 0xc118) // 15 if pc in (0xc118, 0xc127, 0xc136) else ram[0xc08a]
        require(0 <= voice <= 2, 'Executed score hook has no valid logical voice')
        event = dict(call=memory.tick, pc=pc, voiceIndex=voice,
                     instructionStartCycle=memory.instruction_cycle, cpu=registers(cpu),
                     stateBefore=named_state(ram)['voices'][voice])
        if pc in PATTERN_READS or pc in ORDER_READS:
            is_pattern = pc in PATTERN_READS
            expected_mode = 'iny' if is_pattern or pc == 0xc2fc else 'aby'
            require(cpu.disassemble[ram[pc]] == ('LDA', expected_mode), 'Consumption opcode changed')
            if is_pattern:
                zp = ram[pc + 1]
                require(zp == 0xf7 + 2 * voice, 'Pattern pointer/voice association changed')
                pointer = word(ram, zp)
                event.update(kind='patternRead', context=PATTERN_READS[pc], patternPointer=pointer,
                             patternId=tables['patternPointerTables']['pointers'].index(pointer)
                             if pointer in tables['patternPointerTables']['pointers'] else None)
            else:
                pointer = word(ram, 0xfd) if pc == 0xc2fc else word(ram, pc + 1)
                require(pointer == tables['orders'][voice]['pointer'], 'Order binding changed')
                event.update(kind='orderRead', context=ORDER_READS[pc], orderPointer=pointer)
            address = (pointer + cpu.y) & 65535
            event.update(sourceAddress=address, sourceValue=ram[address], readOffset=cpu.y)
            (last_pattern if is_pattern else last_order)[voice] = len(events)
        elif pc == 0xc335:
            require(cpu.x == 2 * voice and memory.instruction == 'STA' and ram[pc:pc + 2] == [0x95, 0xf8],
                    'Pattern-selection hook changed')
            require(0 <= cpu.y < 36, 'Pattern selection exceeds the established table span')
            pointer = source[0xcad1 + cpu.y] | source[0xcaf5 + cpu.y] << 8
            require(ram[0xf7 + cpu.x] | cpu.a << 8 == pointer, 'Selected pointer differs from source table')
            event.update(kind='patternSelection', patternId=cpu.y, patternPointer=pointer,
                         pointerLowAddress=0xcad1 + cpu.y, pointerHighAddress=0xcaf5 + cpu.y)
        elif pc == 0xc3df:
            require(memory.instruction == 'LDA' and ram[pc:pc + 3] == [0xb9, 0x58, 0xc0], 'Instrument mapping hook changed')
            event.update(kind='instrumentSlot', slot=cpu.y, mappingAddress=0xc058 + cpu.y,
                         recordOffset=ram[0xc058 + cpu.y])
            last_slot[voice] = len(events)
        elif pc == 0xc3e3:
            slot = last_slot.get(voice)
            require(slot is not None and events[slot]['call'] == memory.tick
                    and events[slot]['recordOffset'] == cpu.y, 'Record selection lacks its executed mapping read')
            event.update(kind='instrumentSelection', causedByEventIndex=slot, slot=events[slot]['slot'],
                         recordOffset=cpu.y, recordIndex=cpu.y // 9 if cpu.y % 9 == 0 else None,
                         recordAddress=0xc007 + cpu.y, fields=ram[0xc007 + cpu.y:0xc010 + cpu.y])
        elif pc in (0xc2c4, 0xc2c9, 0xc2d3, 0xc2e0):
            consumed = (last_order if pc == 0xc2e0 else last_pattern).get(voice)
            require(consumed is not None and events[consumed]['call'] == memory.tick
                    and events[consumed]['sourceValue'] == 255, 'Marker path lacks its exact consumed FF')
            event.update(kind={0xc2c4: 'patternEnd', 0xc2c9: 'patternRepeat',
                               0xc2d3: 'orderAdvance', 0xc2e0: 'globalStop'}[pc],
                         causedByEventIndex=consumed, sourceAddress=events[consumed]['sourceAddress'], sourceValue=255)
            if pc == 0xc2e0:
                require(first_stop is None and ram[0xc006] != 0, 'Stop is not a first playing-to-stopped path')
                first_stop = memory.tick
                event['playFlagBefore'] = ram[0xc006]
        elif pc in (0xc354, 0xc525):
            consumed = last_pattern.get(voice)
            require(consumed is not None and events[consumed]['call'] == memory.tick
                    and events[consumed]['sourceValue'] == cpu.a,
                    'Row duration reload differs from its consumed duration byte')
            require(events[consumed]['context'] == ('helper' if pc == 0xc354 else 'noteDuration'),
                    'Row reload has a different consumption context')
            event.update(kind='rowReload', rowKind='rest' if pc == 0xc354 else 'note',
                         value=cpu.a, causedByEventIndex=consumed)
        elif pc == 0xc44a:
            consumed = last_pattern.get(voice)
            require(consumed is not None and events[consumed]['context'] == 'token'
                    and events[consumed]['sourceValue'] < 128, 'Note setup lacks its consumed note token')
            event.update(kind='noteSetup', pitchIndex=cpu.a, sourceNote=events[consumed]['sourceValue'],
                         transpose=ram[0xc08e + voice], causedByEventIndex=consumed)
        elif pc in (0xc118, 0xc127, 0xc136):
            event.update(kind='rowExpire', voiceIndex=(pc - 0xc118) // 15, value=cpu.y)
        elif pc == 0xc292:
            event.update(kind='channelEntry')
        else:
            event.update(kind={0xc886: 'transposeSet', 0xc877: 'orderParameterSet',
                               0xc8ac: 'repeatSetBeforeDecrement', 0xc8a3: 'instrumentMappingSet',
                               0xc301: 'modeVolumeSet', 0xc373: 'routingBitSet',
                               0xc389: 'routingBitClear'}[pc], value=cpu.a)
            if pc == 0xc8a3:
                event['slot'] = cpu.y
        events.append(event)

    report, writes = audit_psid(data, calls, profile='pal-banked', subtune=1, host_base=0x0400, observer=observe)
    require(initial_state is not None, 'Initialization checkpoint missing')
    require([state['call'] for state in states] == list(range(calls)),
            'Every completed play call must have exactly one validated final-RTS checkpoint')
    if first_stop is not None:
        require(states[first_stop]['returnKind'] == 'stopClearing' and states[first_stop]['globals']['playFlag'] == 0,
                'Executed stop did not return with cleared playing state')
        require(calls >= first_stop + 65, 'At least 64 post-stop confirming calls are required')
        later = states[first_stop + 1:]
        require(all(state['returnKind'] == 'stopped' and state['globals']['playFlag'] == 0 for state in later),
                'Transport restarted during the retained post-stop window')
        require(not any(row['phase'] == 'play' and row['tick'] > first_stop for row in writes),
                'Post-stop SID stores invalidate the no-new-write observation')
        require(all(named_state_equal(state, states[first_stop + 1]) for state in later),
                'Named driver state changes during stopped calls')
    return report, tables, initial_state, events, states, instructions, writes


def named_state_equal(a, b):
    return all(a[key] == b[key] for key in ('globals', 'voices', 'instrumentMapping'))


def summarize(events, states, writes):
    stops = [event for event in events if event['kind'] == 'globalStop']
    end = stops[0]['call'] if stops else None
    repeats = []
    seen = {}
    for state in states:
        key = state['machineStateSha256']
        if key in seen:
            repeats.append(dict(firstCall=seen[key], repeatedCall=state['call'], returnKind=state['returnKind']))
        else:
            seen[key] = state['call']
    voices = []
    for voice in range(3):
        selected = [event for event in events if event['voiceIndex'] == voice and event['kind'] == 'patternSelection']
        rows = [event for event in events if event['voiceIndex'] == voice and event['kind'] == 'rowReload']
        instruments = [event for event in events if event['voiceIndex'] == voice and event['kind'] == 'instrumentSelection']
        voices.append(dict(voiceIndex=voice, patternSelections=len(selected),
                           executedPatternOrder=[dict(call=e['call'], patternId=e['patternId'],
                                                      orderCursor=e['stateBefore']['orderCursor']) for e in selected],
                           rows=len(rows), rowKinds=dict(Counter(e['rowKind'] for e in rows)),
                           rowDurationValues=sorted({e['value'] for e in rows}),
                           patternIds=sorted({e['patternId'] for e in selected}),
                           instrumentSelectionCount=len(instruments),
                           recordIndices=sorted({e['recordIndex'] for e in instruments if e['recordIndex'] is not None}),
                           finalState=states[-1]['voices'][voice]))
    return dict(schemaVersion=1, playCalls=len(states), eventKinds=dict(Counter(e['kind'] for e in events)),
                firstStopCall=end, stopEvent=stops[0] if stops else None,
                selectedFormCallsInclusive=[0, end] if end is not None else None,
                postStopObservedCalls=len(states) - end - 1 if end is not None else 0,
                stopCallWrites=[row for row in writes if row['phase'] == 'play' and row['tick'] == end] if end is not None else None,
                noPostStopWrites=not any(row['phase'] == 'play' and end is not None and row['tick'] > end for row in writes),
                voices=voices, exactMachineRepeatCount=len(repeats), firstExactMachineRepeats=repeats[:5],
                repeatBasis=MACHINE_HASH_RECIPE,
                limitations=['These are source-pinned title transport/order/row observations under the selected controlled banked host, not original IRQ/game execution or PCM identity.',
                             'Final-RTS snapshots are immediately before the actual final RTS, followed by successful guarded callable return; they are not post-RTS register snapshots.',
                             'Whole backing-memory/register hashes omit physical SID, CIA, VIC and analog state. Repeated stopped states are not a musical-loop claim.',
                             'Order and pattern tables retain exact numeric data; actual consumption events distinguish executed bytes from unconsumed suffixes. Sound-record field meanings and audible instrument attribution are not established.',
                             'Global stop clears three control registers but does not prove audible silence, envelope decay duration or a complete acoustic ending. No audio or listening test is included.'])


def save_json(path, value, *, compressed=False):
    with path.open('xb') as raw:
        if compressed:
            with gzip.GzipFile(filename='', mode='wb', fileobj=raw, compresslevel=6, mtime=0) as stream:
                for chunk in json.JSONEncoder(separators=(',', ':')).iterencode(value):
                    stream.write(chunk.encode())
                stream.write(b'\n')
        else:
            raw.write((json.dumps(value, indent=2) + '\n').encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sid', type=Path)
    parser.add_argument('--calls', type=int, default=40000)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(type(args.calls) is int and 1 <= args.calls <= 40000, 'This form probe is bounded to 1..40000 calls')
    require(not args.output.exists() and not args.output.is_symlink(), 'Choose a fresh output directory')
    for name, expected in TOOLS.items():
        require(digest((ROOT / 'scripts' / name).read_bytes()) == expected,
                f'Pinned dependency changed: scripts/{name}; retain/review the executed version before reproduction')
    data = args.sid.read_bytes()
    report, tables, initial, events, states, instructions, writes = observe_form(data, args.calls)
    summary = summarize(events, states, writes)
    args.output.mkdir(parents=True)
    outputs = [('audit.json', report, False), ('tables.json', tables, False), ('initial-state.json', initial, False),
               ('summary.json', summary, False), ('events.json.gz', events, True), ('states.json.gz', states, True),
               ('instructions.json.gz', instructions, True), ('writes.json.gz', writes, True)]
    created = []
    try:
        for name, value, compressed in outputs:
            path = args.output / name
            created.append(path)
            save_json(path, value, compressed=compressed)
        receipt = dict(schemaVersion=1, sourceSha256=SOURCE_SHA, sourceUrl='https://www.hvsc.de/download/C64Music/MUSICIANS/D/Daglish_Ben/Deflektor.sid',
                       sourceBytes=len(data), sourcePayloadExported=False, originalSidPath=str(args.sid),
                       executionProfile=dict(profile='pal-banked', subtune=1, hostBase=0x0400),
                       calls=args.calls, firstStopCall=summary['firstStopCall'],
                       toolSha256=digest(Path(__file__).read_bytes()), dependencies=TOOLS,
                       ramHashRecipe=RAM_HASH_RECIPE, machineHashRecipe=MACHINE_HASH_RECIPE,
                       instructionsScope='All init instructions, complete calls0..63, the first stop call and its next64 calls. Other calls retain every score hook/event, final named state/hashes and SID store, not a full instruction trace.',
                       files=[dict(path=name, bytes=(args.output / name).stat().st_size,
                                   sha256=digest((args.output / name).read_bytes())) for name, _, _ in outputs])
        created.append(args.output / 'receipt.json')
        save_json(created[-1], receipt)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        args.output.rmdir()
        raise
    print(json.dumps(dict(calls=args.calls, firstStopCall=summary['firstStopCall'],
                          postStopObservedCalls=summary['postStopObservedCalls'], events=len(events),
                          playWrites=report['playWriteCount'], maximumPlayCycles=report['maximumPlayCycles'])))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
