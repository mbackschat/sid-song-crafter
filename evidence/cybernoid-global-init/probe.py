"""Extract named cold title initialization without retaining a payload or RAM image."""

from collections import defaultdict
import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid

SOURCE = ROOT / '.local/research/cybernoid-ii/Cybernoid_II.sid'
PIN = '41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192'
CALLER_PROOF = ROOT / 'evidence/cybernoid-initialization-contract/verification-final.json.gz'
PITCH_MODEL = ROOT / 'evidence/cybernoid-pitch-contract/model.py'
CANONICAL = ROOT / 'evidence/cybernoid-form-36000/audit.writes.json.gz'
SCORE_FIELDS = dict(order_cursor=0xa62d, pattern_cursor=0xa630, row_remaining=0xa633,
                    row_duration=0xa636, transpose=0xa661, sound_offset=0xa699,
                    current_record=0xa642, repeat_count=0xa684, patch_preservation=0xa68a,
                    arpeggio_counter=0xa66d, arpeggio_pointer=[0xa670, 0xa673])
PITCH_FIELDS = dict(base_note=0xa63f, frequency=[0xa693, 0xa696], held_frequency=[0xa64b, 0xa645],
                    vibrato_extent=0xa664, vibrato_direction=0xa667, vibrato_position=0xa66a,
                    vibrato_age=0xa6a8, glide_enabled=0xa64e, glide_active=0xa651,
                    glide_control=0xa690, glide_target=0xa68d)
OUTPUT_FIELDS = dict(wave=0xa687, frequency= [0xa693, 0xa696], gate_mask=0xa69c,
                     pulse=[0xa6ab, 0xa6ae], base_wave=0xa639, held_frequency=[0xa64b, 0xa645],
                     pulse_run_flag=0xa69f, pulse_run_low=0xa6a2, pulse_run_high=0xa6a5)
GLOBAL_FIELDS = dict(tempo_reload=0xa629, tempo_countdown=0xa682,
                    play_flag=0xa717, filter_owner=0xa683)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def prefix_records(path, count):
    decoder, rows = json.JSONDecoder(), []
    with gzip.open(path, 'rt') as stream:
        buffer, offset = stream.read(65536), 0
        for _ in range(count):
            while buffer[offset] in ' \t\r\n[,':
                offset += 1
            row, offset = decoder.raw_decode(buffer, offset)
            rows.append(row)
    return rows


def main():
    folder = Path(__file__).parent
    receipt_path, state_path, trace_path = (folder / name for name in
                                          ('receipt.json', 'initial-state.json', 'instructions.json.gz'))
    assert not any(path.exists() for path in (receipt_path, state_path, trace_path))
    source = SOURCE.read_bytes()
    assert sha(source) == PIN
    caller = json.loads(gzip.decompress(CALLER_PROOF.read_bytes()))
    assert caller['sourceSha256'] == PIN
    caller_fields = caller['addressMap']
    trace_spec = importlib.util.spec_from_file_location('global_init_trace_helpers', ROOT / 'scripts/trace-sid-program.py')
    helpers = importlib.util.module_from_spec(trace_spec)
    trace_spec.loader.exec_module(helpers)
    snapshots, instructions, writes_by_address = {}, [], defaultdict(list)
    disassembler = None
    maps = dict(score=SCORE_FIELDS, caller=caller_fields, pitch=PITCH_FIELDS, output=OUTPUT_FIELDS)

    def voice_state(memory, mapping, voice):
        return {name: (memory.data[address[0] + voice] | memory.data[address[1] + voice] << 8
                       if isinstance(address, (tuple, list)) else memory.data[address + voice])
                for name, address in mapping.items()}

    def snapshot(memory):
        return dict(voices=[{kind: voice_state(memory, mapping, voice) for kind, mapping in maps.items()}
                            for voice in range(3)],
                    globals={name: memory.data[address] for name, address in GLOBAL_FIELDS.items()},
                    selected_order_pointers=[memory.data[0xaefb + voice] | memory.data[0xaefe + voice] << 8
                                             for voice in range(3)],
                    sid_register_shadows={f'{address:04X}': memory.data[address] for address in range(0xd400, 0xd419)})

    def observe(cpu, memory):
        nonlocal disassembler
        if memory.phase == 'init' and cpu.pc == 0xa600:
            snapshots['loaded_before_init'] = snapshot(memory)
        if memory.phase == 'play' and cpu.pc == 0xa603:
            snapshots['cold_post_init_before_first_play'] = snapshot(memory)
        if memory.phase == 'play' and cpu.pc == 0xae2c:
            snapshots['after_first_play'] = snapshot(memory)
        if disassembler is None:
            from py65.disassembler import Disassembler
            disassembler = Disassembler(cpu)
        size, assembly = disassembler.instruction_at(cpu.pc)
        encoded = bytes(memory.data[cpu.pc:cpu.pc + size])
        mnemonic, mode = cpu.disassemble[encoded[0]]
        row = dict(phase=memory.phase, call=memory.tick, pc=cpu.pc,
                   instructionStartCycle=memory.instruction_cycle, bytes=encoded.hex(), assembly=assembly,
                   a=cpu.a, x=cpu.x, y=cpu.y, status=cpu.p, sp=cpu.sp)
        address = helpers.operand_address(mode, encoded[1:], cpu, memory.data)
        if address is not None:
            row.update(operandAddress=address, operandValueBefore=memory.data[address])
            if mnemonic in ('STA', 'STX', 'STY'):
                value = cpu.a if mnemonic == 'STA' else cpu.x if mnemonic == 'STX' else cpu.y
                row['storedValue'] = value
                if memory.phase == 'init':
                    writes_by_address[address].append(dict(pc=cpu.pc, cycle=memory.instruction_cycle, value=value))
        instructions.append(row)

    audit, writes = audit_psid(source, 1, profile='pal-banked', subtune=1, observer=observe)
    assert set(snapshots) == {'loaded_before_init', 'cold_post_init_before_first_play', 'after_first_play'}
    initial = snapshots['cold_post_init_before_first_play']
    expected_caller = [{name: 255 if name == 'note_age' else 2048 if name == 'pulse_output' and voice == 2 else 0
                       for name in caller_fields} for voice in range(3)]
    assert [voice['caller'] for voice in initial['voices']] == expected_caller
    assert all(not any(voice['pitch'].values()) for voice in initial['voices'])
    assert initial['globals'] == dict(tempo_reload=2, tempo_countdown=0, play_flag=0, filter_owner=0)
    assert initial['selected_order_pointers'] == [0xb0d8, 0xb14d, 0xb164]
    assert 0xa6b0 not in writes_by_address
    assert set(range(0xa62d, 0xa6b0)).issubset(writes_by_address)
    init_writes = [write for write in writes if write['phase'] == 'init']
    assert [(write['address'], write['value']) for write in init_writes] == \
        [(0xd416, 255), (0xd417, 0), (0xd418, 31)] + [(address, 0) for address in range(0xd415, 0xd3ff, -1)]
    canonical = prefix_records(CANONICAL, len(writes))
    assert writes == canonical
    origins = {}
    for kind, mapping in maps.items():
        origins[kind] = []
        for voice in range(3):
            records = {}
            for name, addresses in mapping.items():
                addresses = addresses if isinstance(addresses, (tuple, list)) else [addresses]
                loaded = snapshots['loaded_before_init']['voices'][voice][kind][name]
                post_init = initial['voices'][voice][kind][name]
                records[name] = [dict(address=address + voice,
                                      loadedByteValue=(loaded >> (8 * index)) & 255,
                                      postInitByteValue=(post_init >> (8 * index)) & 255,
                                      initWrites=writes_by_address.get(address + voice, []))
                                 for index, address in enumerate(addresses)]
            origins[kind].append(records)
    semantic = dict(schemaVersion=1, classification='Cold title state after PSID init; before first play',
                    selectedSubtune=1, voices=copy.deepcopy(initial['voices']), globals=initial['globals'],
                    sid_registers=initial['sid_register_shadows'],
                    order_bindings=[dict(voice=voice, scorePart=voice) for voice in range(3)],
                    arpeggio_selections=[None, None, None],
                    selectionMeaning='Zero arpeggio-pointer storage means unselected; it does not name arpeggio0. Source template operands are not program selection.',
                    warmInitRule='Reset every mapped CallerState field except preserve voice2 pulse_output high byte; clear its low byte. Set note_age255; other mapped values zero. Source does not restore loaded A6B0=8 on warm init.',
                    firstPlayRule='Tempo countdown0 decrements to255 and reloads2; each age255 increments to0; zero row_remaining decrements to255, selecting each opening row. Initializers skip synthesis bodies.',
                    sourceAddressPolicy='Semantic state uses named fields/voicepart bindings; pointers and addresses belong only to the separate provenance receipt.')
    # Address-bearing arpeggio fields remain provenance, with null semantic selection.
    for voice in semantic['voices']:
        voice['sound_index'] = voice['score']['current_record']
        voice['arpeggio_index'] = None
        del voice['score']['arpeggio_pointer']
    with state_path.open('x') as stream:
        json.dump(semantic, stream, indent=2)
        stream.write('\n')
    trace_bytes = (json.dumps(dict(schemaVersion=1, sourceSha256=PIN, snapshots=snapshots,
                                   instructions=instructions, orderedWrites=writes), separators=(',', ':')) + '\n').encode()
    with trace_path.open('xb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as compressed:
        compressed.write(trace_bytes)
    receipt = dict(schemaVersion=1, sourceSha256=PIN, sourceFileUnchanged=SOURCE.read_bytes() == source,
                   probeSha256=sha(Path(__file__).read_bytes()),
                   tools={name: sha((ROOT / 'scripts' / name).read_bytes()) for name in
                          ('psid_audit.py', 'psid_profile.py', 'verify_player.py', 'trace-sid-program.py')},
                   initialState=dict(path=str(state_path.relative_to(ROOT)), sha256=sha(state_path.read_bytes())),
                   trace=dict(path=str(trace_path.relative_to(ROOT)), compressedSha256=sha(trace_path.read_bytes()),
                              originalSha256=sha(trace_bytes), originalBytes=len(trace_bytes),
                              initInstructions=sum(row['phase'] == 'init' for row in instructions),
                              firstPlayInstructions=sum(row['phase'] == 'play' for row in instructions)),
                   audit=audit, initSidWrites=init_writes,
                   canonicalComparison=dict(path=str(CANONICAL.relative_to(ROOT)), exactRecordEquality=True,
                                            comparedInitRecords=len(init_writes), comparedInitAndFirstPlayRecords=len(writes),
                                            prefixSha256=sha((json.dumps(writes, separators=(',', ':')) + '\n').encode())),
                   addressMaps=dict(maps, globals=GLOBAL_FIELDS), origins=origins,
                   loadedVersusInit=dict(clearRangeInclusive=[0xa62d, 0xa6af], clearLoopPcs=[0xa6b4, 0xa6b6, 0xa6b9, 0xa6ba],
                                         noteAgeFFPcs=[0xa6bc, 0xa6bd, 0xa6c0, 0xa6c3],
                                         retainedLoadedPulseHigh=dict(address=0xa6b0, coldValue=8, writtenByInit=False),
                                         pulseRunFlags='A69F..A6A1 receive1 before clear loop, then0; post-init semantic value is0.'),
                   pointerSelection=dict(sourceTable=0xaeef, destinationLowBase=0xaefb, destinationHighBase=0xaefe,
                                         selectedTitlePointers=initial['selected_order_pointers'],
                                         copyPcs=[0xa6eb, 0xa6ee, 0xa6f1, 0xa6f2, 0xa6f3],
                                         rule='Init copies six pointer bytes for chosen subtune; independent data binds voice0/1/2 to title score parts0/1/2. Pattern/record/pulse/filter/drum tables remain numeric source data, not CPU state.'),
                   codeOperands=dict(playLatch=0xa717, selectionMultiplier=0xa6e4,
                                     arpDefaultTemplate='Encoded arp read operands AF9B are overwritten from per-voice selected pointer when enabled. Post-init pointers are0; no arpeggio selected.',
                                     otherSelfModified='Wait/depth/glide/table operands are not reset globally; accepted component paths establish their numeric operands before use. They are code implementation details, not opaque independent runtime memory.'),
                   limits='Exactly cold init plus first title call under declared PAL banked host; no full traversal, warm-init execution, hardware/IRQ/bus/SID-state/audio claim. Warm retention is settled by bounded executed init write coverage, not a second source run. Instruction operand values are backing-memory snapshots; no full RAM or payload is retained.')
    assert receipt['sourceFileUnchanged']
    with receipt_path.open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(saved=str(receipt_path.relative_to(ROOT)), initStores=len(init_writes),
                          comparedRecords=len(writes), initialState=str(state_path.relative_to(ROOT)),
                          initialStateSha256=receipt['initialState']['sha256'],
                          receiptSha256=sha(receipt_path.read_bytes()))))


if __name__ == '__main__':
    main()
