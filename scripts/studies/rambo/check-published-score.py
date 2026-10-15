#!/usr/bin/env python3
"""Compare the editable loader with Galway's pinned published score data.

This bounded data-directive reader checks composition identity without a SID
file or an assembler rebuild. It deliberately does not assemble instructions,
execute the player, or decide whether a licence clears a proposed publication.
"""

import argparse
import ast
from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
SOURCE_SHA256 = '78e7927e6c2e8f7d42c18d2e02bec764a2911d2d8180cec789020bdd60cdbb75'
REVISION = 'a458a3687e27a63647bbe41968094f0e6d0965a0'
SOURCE_URL = f'https://github.com/MartinGalway/C64_music/blob/{REVISION}/rambload.asm'
HOOKS = {'STARTMC': 'start-morse', 'YNCREMENT': 'increment-transpose',
         'MCFC1': 'morse-pitch-one', 'MCFC2': 'morse-pitch-two'}
KINDS = ('return', 'volume', 'write-data', 'frequency', 'pulse', 'call',
         'transpose', 'call-transposed', 'poke-data', 'jump-transposed',
         'code', 'poke-sound', 'chord', 'loop', 'next')
WIDTHS = {'volume': 5, 'frequency': 14, 'pulse': 10, 'chord': 10, 'write-data': 29}


def fingerprint(path):
    raw = path.read_bytes()
    return {'path': os.path.relpath(path.resolve(), ROOT), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def expression(text, symbols):
    text = re.sub(r'\$([0-9A-Fa-f]+)', r'0x\1', text.strip())
    text = re.sub(r'%([01]+)', r'0b\1', text)
    text = re.sub(r'(?<!\w)0+(\d+)\b', r'\1', text)

    def calculate(node):
        if isinstance(node, ast.Constant):
            return ord(node.value) if isinstance(node.value, str) else node.value
        if isinstance(node, ast.Name):
            return symbols[node.id]
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return -calculate(node.operand)
            if isinstance(node.op, ast.UAdd):
                return calculate(node.operand)
        if isinstance(node, ast.BinOp):
            left, right = calculate(node.left), calculate(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
        raise ValueError(f'Unsupported data expression: {text}')

    return calculate(ast.parse(text, mode='eval').body)


def read_data(source):
    symbols, statements = {}, []
    cursor = 0x4000
    for line in source.splitlines():
        for part in line.split(';', 1)[0].split(':'):
            matched = re.fullmatch(r'\s*(?:(\w+)\s+)?(EQU|DFB|DFW|DFS)\s+(.+?)\s*', part)
            if not matched:
                continue
            label, directive, operands = matched.groups()
            if directive == 'EQU':
                try:
                    symbols[label] = expression(operands, symbols)
                except (KeyError, SyntaxError, ValueError):
                    pass
                continue
            if label:
                symbols[label] = cursor
            fields = [field.strip() for field in operands.split(',')]
            size = (expression(fields[0], symbols) if directive == 'DFS'
                    else len(fields) * (2 if directive == 'DFW' else 1))
            statements.append((cursor, directive, fields))
            cursor += size

    # The four published targets are compared by name, not relocated code address.
    for index, label in enumerate(HOOKS):
        symbols[label] = 0xf000 + index
    data, unresolved = {}, {}
    for address, directive, fields in statements:
        if directive == 'DFS':
            fields = [fields[1] if len(fields) > 1 else '0'] * expression(fields[0], symbols)
        for field in fields:
            width = 2 if directive == 'DFW' else 1
            try:
                value = expression(field, symbols)
            except KeyError:
                value = 0
                unresolved.update({address + offset: field for offset in range(width)})
            for offset in range(width):
                data[address + offset] = (value >> (8 * offset)) & 255
            address += width
    return symbols, data, unresolved


def require_equal(label, actual, expected):
    if actual != expected:
        raise ValueError(f'{label} differs from the published score')


def compare(description, symbols, data, unresolved):
    require_equal('Description format', description['format'], 'rambo-loader-composition-v1')
    require_equal('Selected subtune', description['sourceEvidence']['subtune'], 1)
    program, banks = description['program'], description['dataBanks']
    used, seen, bank_ids, hook_ids = set(), set(), set(), set()
    mappings, reverse = {}, {}

    def read(address, width):
        used.update(range(address, address + width))
        return [data[address + offset] for offset in range(width)]

    pending = [(voice, symbols[label], state['cursor']) for voice, (label, state)
               in enumerate(zip(('CH0D0', 'CH2D0', 'CH1D0'), description['voices']))]
    require_equal('Voice count', len(description['voices']), 3)
    while pending:
        voice, address, name = pending.pop()
        if name in mappings:
            require_equal(f'{name} source correspondence', mappings[name], (voice, address))
            continue
        require_equal(f'{name} unique source node', reverse.get((voice, address), name), name)
        mappings[name], reverse[voice, address] = (voice, address), name
        seen.add(name)
        node = program[name]
        opcode = read(address, 1)[0]
        kind = 'row' if opcode < 192 else KINDS[(opcode - 192) // 2]
        require_equal(f'{name} kind', node['kind'], kind)
        size, fields = 2, {}
        if kind == 'row':
            fields = {'sourceNote': opcode, 'duration': read(address + 1, 1)[0]}
        elif kind in ('return', 'next'):
            size = 1
        elif kind in ('transpose', 'loop'):
            fields = {'transpose' if kind == 'transpose' else 'repeat': read(address + 1, 1)[0]}
        elif kind in ('poke-data', 'poke-sound'):
            size = 3
            fields = dict(zip(('offset', 'value'), read(address + 1, 2)))
        else:
            low, high = read(address + 1, 2)
            target = low + 256 * high
            size = 4 if kind in ('call-transposed', 'jump-transposed') else 3
            if kind in ('call', 'call-transposed', 'jump-transposed'):
                pending.append((voice, target, node['target']))
                if size == 4:
                    fields['transpose'] = read(address + 3, 1)[0]
            elif kind == 'code':
                fields['codeId'] = next(HOOKS[label] for label in HOOKS if symbols[label] == target)
                hook_ids.add(fields['codeId'])
            else:
                bank_id = node['dataId']
                require_equal(f'{name} copy bank {bank_id}', banks[bank_id], read(target, WIDTHS[kind]))
                bank_ids.add(bank_id)
        for field, value in fields.items():
            require_equal(f'{name} {field}', node[field], value)
        if kind not in ('return', 'jump-transposed'):
            pending.append((voice, address + size, node['next']))

    require_equal('Reachable graph coverage', seen, set(program))
    require_equal('Referenced copy-bank coverage', bank_ids, set(banks))
    require_equal('Named hook coverage', hook_ids, set(HOOKS.values()))
    require_equal('Initial data-bank count', len(description['initialData']), 3)
    for index, label in enumerate(('DB0', 'DB1', 'DB2')):
        require_equal(label, description['initialData'][index], read(symbols[label], 49))
    frequency = [low + 256 * high for low, high in
                 zip(read(symbols['LOFRQ'], 89), read(symbols['HIFRQ'], 89))]
    require_equal('Frequency words', description['frequencyWords'], frequency)
    require_equal('Unresolved compared bytes', {address: unresolved[address] for address in used & unresolved.keys()}, {})
    return {'graphNodes': len(seen), 'nodesByKind': dict(sorted(Counter(node['kind'] for node in program.values()).items())),
            'copyBanks': len(bank_ids), 'copyBankBytes': sum(len(banks[name]) for name in bank_ids),
            'namedHooks': len(hook_ids), 'initialDataBanks': 3, 'initialDataBytes': 147,
            'frequencyWords': len(frequency), 'comparedPublishedDataBytes': len(used),
            'unresolvedComparedBytes': 0, 'differences': 0}


def falsify(description, symbols, data, unresolved):
    controls = []
    altered = deepcopy(description)
    name = next(name for name, node in altered['program'].items()
                if node['kind'] == 'row' and node['sourceNote'] % 96 < 94)
    altered['program'][name]['sourceNote'] ^= 1
    note_control = ('alter-one-note', name, altered)
    altered = deepcopy(description)
    bank = next(iter(altered['dataBanks']))
    altered['dataBanks'][bank][0] ^= 1
    for name, target, changed in (note_control, ('alter-one-copy-bank-byte', bank, altered)):
        try:
            compare(changed, symbols, data, unresolved)
        except ValueError as error:
            controls.append({'name': name, 'target': target, 'rejected': True, 'diagnostic': str(error)})
        else:
            raise ValueError(f'Falsification was not rejected: {name}')
    return controls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--description', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--falsify', action='store_true', help='Require altered-note and copy-bank controls to fail')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output receipt already exists; choose a fresh path')
    source = fingerprint(args.source)
    require_equal('Pinned published source fingerprint', source['sha256'], SOURCE_SHA256)
    description = json.loads(args.description.read_bytes())
    symbols, data, unresolved = read_data(args.source.read_text())
    controls = falsify(description, symbols, data, unresolved) if args.falsify else []
    result = compare(description, symbols, data, unresolved)
    receipt = {'schemaVersion': 1, 'status': 'pass', 'source': source,
               'sourceRevision': REVISION, 'sourceUrl': SOURCE_URL,
               'description': fingerprint(args.description), 'checker': fingerprint(Path(__file__)),
               'comparison': result, 'falsification': controls,
               'limits': [
                   'Pinned-source data-directive comparison, not a general assembler or legal adjudication.',
                   'Virtual data addresses ignore instruction lengths; graph edges and hook targets are matched symbolically.',
                   'Source address/opcode annotations are ignored; runtime graph operands and referenced bank contents are compared.',
                   'Hook instruction bodies, Morse letters/codes/frequencies, initial SOUND state and host initialization are not compared.',
                   'No original SID, machine execution, register timing, audio rendering or listening is involved.',
                   'Does not establish historical binary identity, ownership, licence compliance or permission for other subtunes.'
               ]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': 'pass', 'output': str(args.output), **result, 'falsificationControls': len(controls)}))


if __name__ == '__main__':
    main()
