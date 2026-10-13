"""Expand the pinned score tables independently and compare executed consumption/timing."""

import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read_json(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def expand(tables, calls):
    """Expand score navigation only; numeric effects are retained without synthesizing them."""
    orders = {row['voiceIndex']: row for row in tables['orders']}
    patterns = {row['patternId']: row for row in tables['patterns']}
    mapping = list(tables['initMappingDefaults']['bytes'])
    voices = [dict(orderCursor=0, patternCursor=0, patternId=None, repeatCount=0,
                   transpose=0, nextCall=0) for _ in range(3)]
    reads, selections, rows, notes, instruments, commands = [], [], [], [], [], []
    stopped = None

    def consume(voice, call, context, *, order=False):
        state = voices[voice]
        if order:
            index = state['orderCursor']
            table = orders[voice]
            require(index < len(table['bytes']), 'Order cursor escapes retained source table')
            state['orderCursor'] = (index + 1) & 255
            pointer, value = table['pointer'], table['bytes'][index]
        else:
            index = state['patternCursor']
            if state['patternId'] is None:
                require(index == 0, 'Initial FF stub has no further bytes')
                pointer, value = 0xc8cc, 255
            else:
                table = patterns[state['patternId']]
                require(index < len(table['bytes']), 'Pattern cursor escapes retained source table')
                pointer, value = table['pointer'], table['bytes'][index]
        reads.append(dict(call=call, voiceIndex=voice, context=context,
                          sourceAddress=pointer + index, sourceValue=value,
                          kind='orderRead' if order else 'patternRead'))
        return value

    for call in range(calls):
        if stopped is not None:
            break
        for voice, state in enumerate(voices):
            if call != state['nextCall']:
                continue
            for _ in range(4096):
                token = consume(voice, call, 'token')
                if token == 255:
                    if state['repeatCount']:
                        state['repeatCount'] = (state['repeatCount'] - 1) & 255
                        state['patternCursor'] = 0
                        continue
                    for _ in range(256):
                        command = consume(voice, call, 'command', order=True)
                        if command == 255:
                            stopped = call
                            break
                        if command < 128:
                            require(command in patterns, 'Pattern ID exceeds retained table')
                            state['patternId'], state['patternCursor'] = command, 0
                            selections.append(dict(call=call, voiceIndex=voice, patternId=command,
                                                   patternPointer=patterns[command]['pointer']))
                            break
                        if command == 0xe8:
                            value = consume(voice, call, 'modeVolume', order=True)
                            kind = 'modeVolume'
                        elif command & 0x60 == 0:
                            value = consume(voice, call, 'transpose', order=True)
                            state['transpose'], kind = value, 'transpose'
                        elif command & 0x60 == 0x20:
                            value = command & 31
                            state['repeatCount'], kind = (value - 1) & 255, 'repeatTotal'
                        elif command & 0x60 == 0x40:
                            value = consume(voice, call, 'parameterC0C0', order=True)
                            kind = 'parameterC0C0'
                        else:
                            value = consume(voice, call, 'instrumentMapping', order=True)
                            mapping[voice * 8 + (command & 7)] = value
                            kind = 'instrumentMapping'
                        commands.append(dict(call=call, voiceIndex=voice, sourceCommand=command, kind=kind, value=value))
                    else:
                        raise ValueError('Order commands do not reach a pattern/stop within the byte cursor domain')
                    if stopped is not None:
                        break
                    continue
                if token < 128:
                    notes.append(dict(call=call, voiceIndex=voice, sourceNote=token,
                                      transpose=state['transpose'], pitchIndex=(token + state['transpose'] + 20) & 255))
                    state['patternCursor'] = (state['patternCursor'] + 1) & 255
                    duration = consume(voice, call, 'noteDuration')
                    state['patternCursor'] = (state['patternCursor'] + 1) & 255
                    rows.append(dict(call=call, voiceIndex=voice, rowKind='note', value=duration))
                    state['nextCall'] = call + max(1, duration)
                    break
                if token == 0xa0:
                    state['patternCursor'] = (state['patternCursor'] + 1) & 255
                    duration = consume(voice, call, 'helper')
                    state['patternCursor'] = (state['patternCursor'] + 1) & 255
                    rows.append(dict(call=call, voiceIndex=voice, rowKind='rest', value=duration))
                    state['nextCall'] = call + max(1, duration)
                    break
                if token < 0x90:
                    slot = voice * 8 + (token & 15)
                    require(slot < len(mapping), 'Instrument slot escapes retained mapping; no guessed adjacent memory')
                    offset = mapping[slot]
                    records = {r['recordOffset']: r for r in tables['recordTable']['records']}
                    require(offset in records, 'Record offset is outside the established 9-byte record table')
                    instruments.append(dict(call=call, voiceIndex=voice, slot=slot, recordOffset=offset,
                                            fields=records[offset]['fields']))
                elif token >= 0xc0:
                    arguments = []
                    for _ in range(3):
                        state['patternCursor'] = (state['patternCursor'] + 1) & 255
                        arguments.append(consume(voice, call, 'helper'))
                    commands.append(dict(call=call, voiceIndex=voice, sourceCommand=token,
                                         kind='opaqueThreeByteEffect', arguments=arguments))
                else:
                    commands.append(dict(call=call, voiceIndex=voice, sourceCommand=token,
                                         kind='routingBitSet' if token == 0xa1 else
                                              'routingBitClear' if token == 0xa2 else 'opaqueSingleByteEffect'))
                state['patternCursor'] = (state['patternCursor'] + 1) & 255
            else:
                raise ValueError('Pattern commands do not reach a timed row/stop within the bounded expansion')
            if stopped is not None:
                break
    return dict(reads=reads, selections=selections, rows=rows, notes=notes,
                instruments=instruments, commands=commands, firstStopCall=stopped)


def compare(expanded, events):
    checks = [
        ('reads', ('kind', 'call', 'voiceIndex', 'context', 'sourceAddress', 'sourceValue'),
         ('orderRead', 'patternRead')),
        ('selections', ('call', 'voiceIndex', 'patternId', 'patternPointer'), ('patternSelection',)),
        ('rows', ('call', 'voiceIndex', 'rowKind', 'value'), ('rowReload',)),
        ('notes', ('call', 'voiceIndex', 'sourceNote', 'transpose', 'pitchIndex'), ('noteSetup',)),
        ('instruments', ('call', 'voiceIndex', 'slot', 'recordOffset', 'fields'), ('instrumentSelection',)),
    ]
    results = []
    for name, keys, kinds in checks:
        expected = [tuple(row[key] for key in keys) for row in expanded[name]]
        actual = [tuple(row[key] for key in keys) for row in events if row['kind'] in kinds]
        require(expected == actual, f'Independent source-table expansion differs: {name}')
        results.append(dict(component=name, records=len(expected), comparedFields=list(keys), exact=True))
    stops = [row['call'] for row in events if row['kind'] == 'globalStop']
    require(stops == ([] if expanded['firstStopCall'] is None else [expanded['firstStopCall']]),
            'Independent table expansion predicts a different first global stop')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.output.is_symlink(), 'Choose a fresh checker output')
    tables = read_json(args.run / 'tables.json')
    events = read_json(args.run / 'events.json.gz')
    receipt = read_json(args.run / 'receipt.json')
    require(tables['sourceSha256'] == '606ad4cb19e29c060bb77a9b44253dee62d3d972724acb6cddf625fc2466d44d',
            'Only the pinned table grammar is supported')
    for name in ('tables.json', 'events.json.gz'):
        entry = next(row for row in receipt['files'] if row['path'] == name)
        require(hashlib.sha256((args.run / name).read_bytes()).hexdigest() == entry['sha256'], 'Run receipt hash differs')
    expanded = expand(tables, receipt['calls'])
    results = compare(expanded, events)
    changed = copy.deepcopy(tables)
    row = next(row for row in events if row['kind'] == 'patternRead' and row['context'] == 'noteDuration')
    pattern = next(p for p in changed['patterns'] if p['patternId'] == row['patternId'])
    offset = row['sourceAddress'] - pattern['pointer']
    pattern['bytes'][offset] = (pattern['bytes'][offset] + 1) & 255
    rejected = False
    try:
        compare(expand(changed, receipt['calls']), events)
    except ValueError:
        rejected = True
    require(rejected, 'A consumed note-duration edit must break score/timing equality')
    result = dict(schemaVersion=1, sourceSha256=tables['sourceSha256'],
                  checkerSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  observedProbeSha256=receipt['toolSha256'], playCalls=receipt['calls'],
                  dependencies={name: hashlib.sha256((args.run / name).read_bytes()).hexdigest()
                                for name in ('tables.json', 'events.json.gz', 'receipt.json')},
                  firstStopCall=expanded['firstStopCall'], comparisons=results,
                  consumedDurationMutationRejected=rejected,
                  distinctOpaquePatternTokens=sorted({command['sourceCommand'] for command in expanded['commands']
                                                      if command['kind'].startswith('opaque')}),
                  limits=['Independent score expansion consumes retained source tables, never observed events or SID stores as runtime input. Events are comparison oracle only.',
                          'This proves selected title consumption, timing, pattern/record selection and lookup-index agreement; it does not synthesize SID sound or prove acoustic form.',
                          'Opaque effect token semantics remain unnamed; only executed operand consumption is compared. Unencountered byte combinations and zero-duration scheduling are not separately validated.',
                          'Extraction boundaries and initial FF stub are pinned archive facts, not a general Daglish format specification.'])
    with args.output.open('x') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
    print(json.dumps(dict(firstStopCall=result['firstStopCall'], comparisons=results, negativeControl=rejected)))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
