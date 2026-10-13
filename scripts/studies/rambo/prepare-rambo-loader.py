"""Extract editable score graphs and numeric sound data from the pinned loader."""

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_audit import audit_psid
from rambo_score import validate_program


SOURCE_SHA256 = '88a2b538ee3d3d1d8b0b754bef77a63d9750812694786977ae8c539f6ecd000e'
DATA_BASES = (0x28d4, 0x291e, 0x2968)
SOUND_BASES = (0x29b2, 0x29d9, 0x2a00)
KINDS = ('return', 'volume', 'write-data', 'frequency', 'pulse', 'call',
         'transpose', 'call-transposed', 'poke-data', 'jump-transposed',
         'code', 'poke-sound', 'chord', 'loop', 'next')
COPY_WIDTHS = {'volume': 5, 'frequency': 14, 'pulse': 10, 'chord': 10}
CODE_IDS = {0x316f: 'start-morse', 0x2e27: 'increment-transpose',
            0x2e2b: 'morse-pitch-one', 0x2e31: 'morse-pitch-two'}


def extract(data):
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('Loader source differs from the pinned archive')
    initialized = []

    def observe(cpu, memory):
        if memory.phase == 'play' and not initialized:
            initialized.append(list(memory.data))

    _, writes = audit_psid(data, 1, profile='pal-banked', subtune=1, observer=observe)
    ram = initialized[0]
    word = lambda address: ram[address] | ram[address + 1] << 8
    program, banks, addresses = {}, {}, {}

    def node_id(voice, address):
        key = (voice, address)
        if key not in addresses:
            addresses[key] = f'voice-{voice + 1}-row-{len(addresses):04d}'
        return addresses[key]

    starts = [word(0x10 + 2 * voice) for voice in range(3)]
    pending = [(voice, address) for voice, address in enumerate(starts)]
    for voice, address in pending:
        name = node_id(voice, address)
        if name in program:
            continue
        if not 0x2b43 <= address < 0x30f0:
            raise ValueError(f'Score target outside the pinned data region: {address:04x}')
        opcode = ram[address]
        node = {'sourceAddress': address, 'sourceOpcode': opcode}
        size = 2
        if opcode < 192:
            node.update(kind='row', sourceNote=opcode, duration=ram[address + 1])
        else:
            if opcode & 1 or opcode > 0xdc:
                raise ValueError(f'Unsupported score command {opcode:02x}')
            kind = KINDS[(opcode - 192) // 2]
            node['kind'] = kind
            if kind in ('return', 'next'):
                size = 1
            elif kind in ('transpose', 'loop'):
                node['transpose' if kind == 'transpose' else 'repeat'] = ram[address + 1]
            elif kind in ('poke-data', 'poke-sound'):
                size = 3
                node.update(offset=ram[address + 1], value=ram[address + 2])
            else:
                size = 4 if kind in ('call-transposed', 'jump-transposed') else 3
                target = word(address + 1)
                if kind in ('call', 'call-transposed', 'jump-transposed'):
                    node['target'] = node_id(voice, target)
                    pending.append((voice, target))
                    if size == 4:
                        node['transpose'] = ram[address + 3]
                elif kind == 'code':
                    if target not in CODE_IDS:
                        raise ValueError(f'Unknown executable score hook {target:04x}')
                    node['codeId'] = CODE_IDS[target]
                else:
                    width = (49 if voice == 0 else 29) if kind == 'write-data' else COPY_WIDTHS[kind]
                    bank_id = f'data-{target:04x}-{width}'
                    node['dataId'] = bank_id
                    banks[bank_id] = list(ram[target:target + width])
        if node['kind'] not in ('return', 'jump-transposed'):
            node['next'] = node_id(voice, address + size)
            pending.append((voice, address + size))
        program[name] = node
    validate_program(program)
    return {
        'format': 'rambo-loader-composition-v1',
        'profile': {'clock': 'PAL', 'sidModel': 'MOS6581', 'sidBase': 0xd400, 'callCycles': 19656},
        'sourceEvidence': {'sourceSha256': SOURCE_SHA256, 'subtune': 1,
                           'url': 'https://www.hvsc.de/download/C64Music/MUSICIANS/G/Galway_Martin/Rambo_First_Blood_Part_II.sid'},
        'program': program, 'dataBanks': banks,
        'initialData': [ram[base:base + 49] for base in DATA_BASES],
        'initialSound': [ram[base:base + 39] for base in SOUND_BASES],
        'voices': [{'cursor': node_id(voice, address), 'remaining': ram[0x1a + voice],
                    'transpose': ram[DATA_BASES[voice] + 73], 'stackIndex': ram[0x1d + voice],
                    'stack': [{'returnNode': None, 'repeatRemaining': 0} for _ in range(8)]}
                   for voice, address in enumerate(starts)],
        'frequencyWords': [ram[0x2a90 + index] | ram[0x2a37 + index] << 8 for index in range(89)],
        'morse': {'letters': ram[0x319e:0x31d5], 'codes': ram[0x31d5:0x31ef],
                  'initialFrequency': 0x224b, 'pitchChanges': [0x1b38, 0x19b1]},
        'initialization': {'volume': next(row['value'] for row in writes if row['address'] == 0xd418)},
        'range': {'auditCalls': 11000},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.local/rambo-source.sid')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    description = extract(args.source.read_bytes())
    if args.check:
        if json.loads(args.output.read_text()) != description:
            raise ValueError('Saved loader description differs from pinned extraction')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x') as output:
            output.write(json.dumps(description, indent=2) + '\n')
    print(f'Verified {len(description["program"])} score instructions: {args.output}')


if __name__ == '__main__':
    main()
