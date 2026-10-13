"""Reenact bounded pulse/pitch source segments using retained named incoming states."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import BankedAuditMemory
from psid_profile import psid_profile
from verify_player import cpu_type, require

SOURCE_SHA = '606ad4cb19e29c060bb77a9b44253dee62d3d972724acb6cddf625fc2466d44d'
PINS = {'states.json.gz': '3b5fc9904cdb384b2b2e214ba9cf709827e205b1be2d1270833ece542f518891',
        'events.json.gz': '776c2aaa1effe25b1a70dc53630297b2d90961534db8f5febf4a232d59b4748a'}
TOOLS = {'psid_profile.py': 'edc1109d1b393541a1df1c8d678923faab1d5240996c2eaee63db8691e9ea0ff',
         'psid_audit.py': '4446a19a325e625e59f100aac0b186478fb1633f65886b260db2ad3da11419a5',
         'sid_audit_host.py': 'ea1949d711126b5150225f0d68a3462dbbfe9fffe094e448f9b758889808b0ed',
         'verify_player.py': 'c69317c5d781c175ef0cef39a6e2713187b17e1de5b3f144ad69d49e6a271aab'}
PULSE_FIELDS = {'interval': 0xc0ba, 'tableBase': 0xc0bd, 'countdown': 0xc0f0,
                'position': 0xc0f6, 'lowStep': 0xc0f3}
PITCH_FIELDS = {'programOffset': 0xc0c6, 'wait': 0xc0c3, 'position': 0xc0c9}


def component_state(voice, kind):
    fields = PULSE_FIELDS if kind == 'pulse' else PITCH_FIELDS
    result = {name: voice[f'driver{address:04X}'] for name, address in fields.items()}
    shadow = voice['sidShadow']
    offset = 2 if kind == 'pulse' else 0
    result['word'] = shadow[offset] | shadow[offset + 1] << 8
    return result


def original_segment(profile, voice, kind, before):
    memory = BankedAuditMemory((0xd400,), 0x0400)
    memory.data[profile['loadAddress']:profile['endAddress']] = profile['payload']
    ram = memory.data
    fields = PULSE_FIELDS if kind == 'pulse' else PITCH_FIELDS
    for name, address in fields.items():
        ram[address + voice] = before[name]
    word_offset = 2 if kind == 'pulse' else 0
    ram[0xc095 + 7 * voice + word_offset] = before['word'] & 255
    ram[0xc096 + 7 * voice + word_offset] = before['word'] >> 8
    ram[0xc089], ram[0xc08a] = 7 * voice, voice
    cpu = cpu_type()(memory=memory, pc=0xc59a if kind == 'pulse' else 0xc640)
    cpu.x, cpu.p = voice, 0x26
    stop = 0xc640 if kind == 'pulse' else 0xc6cf
    reads, instructions = [], []
    while cpu.pc != stop:
        require(cpu.processorCycles < 6000, 'Retained-context segment exceeds bounded budget')
        memory.instruction = cpu.disassemble[memory[cpu.pc]][0]
        require(memory.instruction not in ('???', 'BRK', 'RTI'), 'Unsupported component instruction')
        memory.instruction_cycle = cpu.processorCycles
        instructions.append(dict(pc=cpu.pc, opcode=ram[cpu.pc], a=cpu.a, x=cpu.x, y=cpu.y,
                                 p=cpu.p, sp=cpu.sp, instructionStartCycle=cpu.processorCycles))
        if cpu.pc in (0xc5b4, 0xc5e7, 0xc665):
            address = (0xc9a5 if cpu.pc == 0xc665 else 0xc98d) + cpu.y
            reads.append(dict(pc=cpu.pc, address=address, value=ram[address], index=cpu.y))
        cpu.step()
    require(cpu.sp == 255 and not memory.writes, 'Component unexpectedly stores to SID or changes stack depth')
    after = {name: ram[address + voice] for name, address in fields.items()}
    after['word'] = ram[0xc095 + 7 * voice + word_offset] | ram[0xc096 + 7 * voice + word_offset] << 8
    return after, dict(tableReads=reads, instructions=instructions, cycles=cpu.processorCycles)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sid', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.output.is_symlink(), 'Choose a fresh path-check output')
    data = args.sid.read_bytes()
    require(hashlib.sha256(data).hexdigest() == SOURCE_SHA, 'Source is not pinned Deflektor')
    for name, pin in TOOLS.items():
        require(hashlib.sha256((ROOT / 'scripts' / name).read_bytes()).hexdigest() == pin, f'Dependency changed: {name}')
    profile = psid_profile(data, profile='pal-banked', subtune=1, host_base=0x0400)
    base = ROOT / 'evidence/deflektor-form/full40000'
    inputs = {}
    for name, pin in PINS.items():
        raw = (base / name).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == pin, f'Retained input differs: {name}')
        inputs[name] = json.loads(gzip.decompress(raw))
    states, events = inputs['states.json.gz'], inputs['events.json.gz']
    rows = {(event['call'], event['voiceIndex']) for event in events if event['kind'] == 'rowReload'}
    seen, cases = set(), []
    for call in range(1, 8480):
        previous, current = states[call - 1], states[call]
        if current['returnKind'] != 'writer':
            continue
        for voice in range(3):
            a, b = previous['voices'][voice], current['voices'][voice]
            if (call, voice) in rows or a['restCountdown'] or a['rowCountdown'] <= 1:
                continue
            for kind in ('pulse', 'pitch'):
                before, expected = component_state(a, kind), component_state(b, kind)
                if kind == 'pulse':
                    if not before['interval']:
                        continue
                    deadline = (before['countdown'] + 1) & 255 == before['interval']
                    key = (kind, voice, before['interval'], before['tableBase'], before['position'], deadline)
                else:
                    if before['programOffset'] != 8 or a['driverC0D5'] != 0 or b['driverC0D5'] != 0:
                        continue
                    key = (kind, before['wait'] == 1, before['wait'] > 1, before['position'])
                if key in seen:
                    continue
                seen.add(key)
                actual, execution = original_segment(profile, voice, kind, before)
                require(actual == expected, f'{kind} reenactment differs from full execution at call{call},voice{voice}')
                cases.append(dict(call=call, voiceIndex=voice, kind=kind, before=before,
                                  expected=expected, actual=actual, **execution))
    require(any(case['kind'] == 'pitch' and case['tableReads'] for case in cases), 'No executed signed pitch step coverage')
    require(any(case['kind'] == 'pulse' and case['before']['tableBase'] == 32 for case in cases), 'No aliased pulse-table base32 coverage')
    result = dict(schemaVersion=1, sourceSha256=SOURCE_SHA,
        toolSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), dependencies=TOOLS, canonicalEvidenceSha256=PINS,
        cases=cases, pulseCases=sum(case['kind'] == 'pulse' for case in cases),
        pitchCases=sum(case['kind'] == 'pitch' for case in cases),
        limits=['These are isolated original source segments seeded with named real incoming states, compared to the existing complete execution. They are contextual source verification, not an independent pulse/pitch synthesis model.',
                'Rows, rests and globally suppressed writer calls are excluded; pitch contexts also exclude source score-selected pitch macros, so later macros cannot mask a component difference.',
                'Only the selected actual contexts and source table reads are retained. No full RAM snapshot, source payload, render, audio or listening judgment is exported.'])
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(pulseCases=result['pulseCases'], pitchCases=result['pitchCases'],
                          tableAddresses=sorted({read['address'] for case in cases for read in case['tableReads']}))))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
