"""Observe bounded form navigation in the pinned Cybernoid II title player."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from psid_audit import audit_psid
from verify_player import require


ROOT = Path(__file__).resolve().parents[1]
# The source pin is required because this navigation hook/state map comes from evidence/cybernoid-title-instructions/form-navigation.json.gz.
HOOKS = dict(orderByte=0xa754, patternPointer=0xa7ad, patternStart=0xa7c0,
             patternHelper=0xa936, patternPeek=0xa8f6, patternEnd=0xa8fc,
             patternRepeat=0xa906, orderAdvance=0xa90b, orderWrap=0xa75f,
             globalStop=0xa70f, rowReload=0xa877, tempoReload=0xa725)
STATE = dict(tempoReload=0xa629, tempoCountdown=0xa682, playFlag=0xa717,
             orderCursor=0xa62d, patternCursor=0xa630, rowCountdown=0xa633,
             durationReload=0xa636, repeatCount=0xa684, transpose=0xa661,
             instrumentIndexOffset=0xa699, orderPointerLow=0xaefb, orderPointerHigh=0xaefe,
             patternScratch=0x46, patternTable=0xaf01)
# The first FE stop reaches a different return: pinned bytes at A714 branch through A704's clearing loop to A70E.
RETURNS = {0xae2c: 'body', 0xa71a: 'stopped', 0xa70e: 'stopClearing'}
RAM_HASH_RECIPE = 'SHA256(bytes(AuditMemory.data)): all 65536 backing-memory bytes in ascending address order, including loaded source, stack and I/O write shadows; no normalization.'
MACHINE_HASH_RECIPE = 'SHA256(bytes(AuditMemory.data) + bytes([A,X,Y,SP,P]) + PC.to_bytes(2,"little")), immediately before the final RTS; no normalization.'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def reference_entry():
    manifest = json.loads((ROOT / 'config/local-assets.json').read_text())
    entries = [entry for entry in manifest['references'] if entry['id'] == 'cybernoid-ii']
    require(len(entries) == 1, 'Missing or ambiguous pinned Cybernoid II reference')
    return entries[0]


def verify_source(data):
    entry = reference_entry()
    require(digest(data) == entry['sha256'], 'Source is not the pinned Cybernoid II archive')
    return entry


def _observe_form(data, ticks, *, hooks=HOOKS, state_addresses=STATE, returns=RETURNS):
    """Use the guarded CPU oracle; alternate hook layouts are only for independent fixtures."""
    events, states, last_order, last_pattern, last_pointer = [], [], {}, {}, {}
    at_pc = {pc: kind for kind, pc in hooks.items()}

    def word(memory, address):
        return memory[address] | memory[address + 1] << 8

    def cpu_state(cpu):
        return dict(a=cpu.a, x=cpu.x, y=cpu.y, sp=cpu.sp, p=cpu.p, pc=cpu.pc)

    def voice_state(memory, voice):
        result = {name: memory[state_addresses[name] + voice] for name in
                  ('orderCursor', 'patternCursor', 'rowCountdown', 'durationReload', 'repeatCount',
                   'transpose', 'instrumentIndexOffset')}
        result.update(voiceIndex=voice, orderPointer=memory[state_addresses['orderPointerLow'] + voice]
                      | memory[state_addresses['orderPointerHigh'] + voice] << 8)
        return result

    def observe(cpu, memory):
        if memory.phase != 'play':
            return
        ram = memory.data
        if cpu.pc in returns:
            require(memory.instruction == 'RTS' and cpu.sp == 253, 'Form checkpoint is not the final callable RTS')
            encoded = bytes(ram)
            registers = cpu_state(cpu)
            states.append(dict(call=memory.tick, returnPc=cpu.pc, returnKind=returns[cpu.pc],
                               instructionStartCycle=memory.instruction_cycle, cpu=registers,
                               ramSha256=digest(encoded), machineStateSha256=digest(encoded + bytes(
                                   [cpu.a, cpu.x, cpu.y, cpu.sp, cpu.p]) + cpu.pc.to_bytes(2, 'little')),
                               globals={name: ram[state_addresses[name]] for name in
                                        ('tempoReload', 'tempoCountdown', 'playFlag')},
                               patternScratchPointer=word(ram, state_addresses['patternScratch']),
                               voices=[voice_state(ram, voice) for voice in range(3)]))
            return
        kind = at_pc.get(cpu.pc)
        if kind is None and memory.instruction == 'LDA' and ram[cpu.pc] == 0xb1 and ram[cpu.pc + 1] == state_addresses['patternScratch']:
            kind = 'scratchRead'
        if kind is None:
            return
        voice = None if kind == 'tempoReload' or kind == 'scratchRead' and not 0 <= cpu.x <= 2 else cpu.x
        require(voice is None or 0 <= voice <= 2, 'Form hook lacks a valid voice index')
        mnemonic, mode = cpu.disassemble[ram[cpu.pc]]
        size = 2 if mode in ('imm', 'zpg', 'iny') else 3
        event = dict(kind=kind, call=memory.tick, pc=cpu.pc, instructionStartCycle=memory.instruction_cycle,
                     voiceIndex=voice, bytes=bytes(ram[cpu.pc:cpu.pc + size]).hex(), cpu=cpu_state(cpu))
        if voice is not None:
            event['stateBefore'] = voice_state(ram, voice)
        if kind in ('orderByte', 'patternStart', 'patternHelper', 'patternPeek', 'scratchRead'):
            require(mnemonic == 'LDA' and mode == ('aby' if kind == 'orderByte' else 'iny'),
                    'Form consumption hook opcode changed')
            pointer = word(ram, cpu.pc + 1) if kind == 'orderByte' else word(ram, state_addresses['patternScratch'])
            event.update(sourceAddress=(pointer + cpu.y) & 65535, context={'orderByte': 'order',
                         'patternStart': 'start', 'patternHelper': 'helper', 'patternPeek': 'peek',
                         'scratchRead': 'unclassified'}[kind])
            event['sourceValue'] = ram[event['sourceAddress']]
            if kind == 'orderByte':
                last_order[voice] = len(events)
            else:
                last_pattern[voice] = len(events)
                event['kind'] = 'pointerRead'
                owner = last_pointer.get(voice)
                owned = owner is not None and events[owner]['call'] == memory.tick and events[owner]['patternPointer'] == pointer
                event['selectedPatternPointerEventIndex'] = owner if owned else None
                if kind == 'scratchRead' and owned:
                    event['context'] = 'continuation'
        elif kind == 'patternPointer':
            require(mnemonic == 'STA' and mode == 'zpg' and ram[cpu.pc + 1] == state_addresses['patternScratch'] + 1,
                    'Pattern-pointer hook opcode changed')
            require(cpu.y % 2 == 0, 'Pattern-pointer table index must be even')
            address = state_addresses['patternTable'] + cpu.y
            event.update(patternId=cpu.y // 2, sourceAddress=address,
                         pointerTableBytes=ram[address:address + 2],
                         patternPointer=ram[state_addresses['patternScratch']] | cpu.a << 8)
            require(event['patternPointer'] == word(ram, address), 'Resolved pattern pointer differs from its table bytes')
            last_pointer[voice] = len(events)
        elif kind in ('orderWrap', 'globalStop', 'patternEnd'):
            expected = 0xfe if kind == 'globalStop' else 0xff
            consumed = (last_pattern if kind == 'patternEnd' else last_order).get(voice)
            require(consumed is not None and events[consumed]['call'] == memory.tick
                    and events[consumed]['sourceValue'] == expected, 'Executed marker path lacks its consumed source marker')
            event.update(causedByEventIndex=consumed, sourceAddress=events[consumed]['sourceAddress'], sourceValue=expected)
        elif kind in ('patternRepeat', 'orderAdvance'):
            name = 'repeatCount' if kind == 'patternRepeat' else 'orderCursor'
            require(mnemonic == ('DEC' if kind == 'patternRepeat' else 'INC') and mode == 'abx',
                    'Form counter hook opcode changed')
            event.update(sourceAddress=state_addresses[name] + voice, before=event['stateBefore'][name],
                         after=(event['stateBefore'][name] + (-1 if kind == 'patternRepeat' else 1)) & 255,
                         transitionBasis='Executed NMOS instruction semantics; after is not a separate RAM observation')
        elif kind in ('rowReload', 'tempoReload'):
            require(mnemonic == 'STA', 'Counter-reload hook opcode changed')
            name = 'rowCountdown' if kind == 'rowReload' else 'tempoCountdown'
            address = state_addresses[name] + (voice if voice is not None else 0)
            event.update(sourceAddress=address, before=ram[address], value=cpu.a)
        events.append(event)

    report, writes = audit_psid(data, ticks, observer=observe, profile='pal-banked', subtune=1)
    require([state['call'] for state in states] == list(range(ticks)),
            'Every requested call must have exactly one completed form-state checkpoint')
    return report, events, states, writes


def summarize(events, states, ticks):
    """Summarize observed events and exact backing-memory/CPU repeats without inferring a song cycle."""
    require(len(states) == ticks, 'Summary needs every requested call-state observation')
    counts = Counter(event['kind'] for event in events)
    seen, repeats = {}, []
    for state in states:
        key = state['machineStateSha256']
        if key in seen:
            repeats.append(dict(firstCall=seen[key], repeatCall=state['call'], distanceCalls=state['call'] - seen[key],
                                returnPc=state['returnPc'], machineStateSha256=key))
        else:
            seen[key] = state['call']
    return dict(playCalls=ticks, eventCounts=dict(sorted(counts.items())),
                orderReadCounts={str(voice): sum(event['kind'] == 'orderByte' and event['voiceIndex'] == voice for event in events)
                                 for voice in range(3)},
                orderWrapCalls={str(voice): [event['call'] for event in events if event['kind'] == 'orderWrap'
                                           and event['voiceIndex'] == voice] for voice in range(3)},
                patternEndCalls={str(voice): [event['call'] for event in events if event['kind'] == 'patternEnd'
                                            and event['voiceIndex'] == voice] for voice in range(3)},
                globalStopCalls=[event['call'] for event in events if event['kind'] == 'globalStop'],
                firstState=states[0], lastState=states[-1], wholeStateRepeats=repeats,
                recurrenceClaim=None,
                limits='Pattern ends/repeats are distinct from per-voice order wraps and global stops. Exact hash repeats concern this callable backing-memory/CPU model only, not SID oscillator/envelope state, PCM or a complete musical form.')


def analyze_source(data, ticks):
    """Return receipt, compact events, exact call-state hashes and full ordered SID writes for the pinned title."""
    entry = verify_source(data)
    report, events, states, writes = _observe_form(data, ticks)
    provenance = {name: digest((ROOT / 'scripts' / name).read_bytes()) for name in
                  ('analyze-cybernoid.py', 'psid_audit.py', 'psid_profile.py', 'verify_player.py')}
    receipt = dict(schemaVersion=1, classification='Bounded executed Cybernoid II title form navigation',
                   sourceSha256=digest(data), sourceRegistryEntry=entry,
                   sourceRegistrySha256=digest((ROOT / 'config/local-assets.json').read_bytes()),
                   toolSha256=provenance['analyze-cybernoid.py'], toolchainSha256=provenance,
                   profile='pal-banked', selectedSubtune=1, firstCall=0, lastCallInclusive=ticks - 1,
                   playCalls=ticks, hookPcs=HOOKS, returnPcs={str(pc): kind for pc, kind in RETURNS.items()},
                   pointerReadRule='Retain every play-phase LDA ($46),Y. Same-call same-voice table-derived pointer equality supplies ownership; other reads remain unclassified.',
                   stateAddresses=STATE, ramHashRecipe=RAM_HASH_RECIPE, machineStateHashRecipe=MACHINE_HASH_RECIPE,
                   navigationBasis='evidence/cybernoid-title-instructions/form-navigation.json.gz',
                   audit=report, summary=summarize(events, states, ticks),
                   limits='Original bytes/header retained. Read-only observer; instruction-start timing and RAM operand values, not bus cycles. No synthesis, complete traversal, score decoder, source-listing equivalence or listening claim.')
    return receipt, events, states, writes


def run_analysis(source, output, ticks):
    require(not output.exists() and not output.is_symlink(), 'Choose a fresh analysis output directory')
    data = source.read_bytes()
    receipt, events, states, writes = analyze_source(data, ticks)
    receipt['sourcePath'] = str(source.resolve())
    receipt['artifacts'] = {}
    artifacts = {'events.json': events, 'call-state.json': states, 'audit.writes.json': writes,
                 'audit.json': receipt.pop('audit')}
    encoded = {name: (json.dumps(value, separators=(',', ':')) + '\n').encode() for name, value in artifacts.items()}
    for name, value in encoded.items():
        receipt['artifacts'][name] = dict(sha256=digest(value), bytes=len(value))
    encoded['receipt.json'] = (json.dumps(receipt, indent=2) + '\n').encode()
    output.mkdir(parents=True)
    created = []
    try:
        for name, value in encoded.items():
            path = output / name
            with path.open('xb') as file:
                created.append(path)
                file.write(value)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        try:
            output.rmdir()
        except OSError:
            pass
        raise
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sid', type=Path, nargs='?', default=ROOT / reference_entry()['path'])
    parser.add_argument('--ticks', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run_analysis(args.sid.resolve(), args.output.resolve(), args.ticks)
    summary = result['summary']
    print(json.dumps(dict(receipt=str(args.output / 'receipt.json'), playCalls=result['playCalls'],
                          eventCounts=summary['eventCounts'], orderWrapCalls=summary['orderWrapCalls'],
                          globalStopCalls=summary['globalStopCalls'], wholeStateRepeatCount=len(summary['wholeStateRepeats']),
                          finalOrderCursors=[voice['orderCursor'] for voice in summary['lastState']['voices']]),
                     separators=(',', ':')))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f'Cybernoid analysis failed: {error}')
