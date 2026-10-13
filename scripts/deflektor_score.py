"""Expand Deflektor's numeric order/pattern grammar without executing its driver."""


def require(ok, message):
    if not ok:
        raise ValueError(message)


def byte_values(values, name):
    require(isinstance(values, (list, tuple)) and all(type(value) is int and 0 <= value <= 255
                                                   for value in values),
            f'{name} must contain byte values')


def unique(rows, key, name):
    values = [row[key] for row in rows]
    require(all(type(value) is int for value in values), f'{name} IDs must be integers')
    require(len(values) == len(set(values)), f'Duplicate {name} ID')
    return values


def validate_tables(tables):
    """Reject ambiguous IDs and invalid numeric data before score expansion."""
    require(set(unique(tables['orders'], 'voiceIndex', 'voice')) == {0, 1, 2},
            'Orders must define voices 0, 1 and 2')
    ids = unique(tables['patterns'], 'patternId', 'pattern')
    require(all(0 <= value < 128 for value in ids), 'Pattern IDs must be in 0..127')
    for name in ('orders', 'patterns'):
        for row in tables[name]:
            byte_values(row['bytes'], name)
            pointer = row['pointer']
            require(type(pointer) is int and 0 <= pointer <= 65535,
                    f'{name} pointer must be a 16-bit address')
            require(0 < len(row['bytes']) <= 256 and pointer + len(row['bytes']) <= 65536,
                    f'{name} must fit its byte cursor and address space')
    mapping = tables['initMappingDefaults']['bytes']
    byte_values(mapping, 'Instrument mapping')
    require(len(mapping) == 24, 'Instrument mapping must contain 24 slots')
    records = tables['recordTable']['records']
    offsets = unique(records, 'recordOffset', 'record')
    require(all(0 <= value <= 255 and value % 9 == 0 for value in offsets),
            'Record offsets must select nine-byte records')
    for record in records:
        byte_values(record['fields'], 'Sound record')
        require(len(record['fields']) == 9, 'Sound records must contain nine bytes')


def expand_score(tables, *, calls):
    """Expand editable numeric score tables into timed consumption and row events.

    The input uses the table schema retained in evidence/deflektor-form/full40000.
    Source addresses are provenance labels; no SID file, CPU or observed events
    are read. Calls start at zero, use the original 0/1/2 voice order, and stop
    immediately when one voice consumes an order FF. The exclusive call cap
    alone does not imply an ending. Input tables are never mutated.

    This models score navigation, not synthesis or an acoustic tail. Opaque
    effects remain numeric commands. Only the pinned title's executed grammar
    has a complete source comparison; zero-duration scheduling is unsupported.
    """
    validate_tables(tables)
    require(type(calls) is int and calls >= 0, 'calls must be a nonnegative integer')
    orders = {row['voiceIndex']: row for row in tables['orders']}
    patterns = {row['patternId']: row for row in tables['patterns']}
    mapping = list(tables['initMappingDefaults']['bytes'])
    records = {row['recordOffset']: row for row in tables['recordTable']['records']}
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
                    require(duration != 0, 'Unsupported zero duration; no one-call substitution')
                    state['nextCall'] = call + duration
                    break
                if token == 0xa0:
                    state['patternCursor'] = (state['patternCursor'] + 1) & 255
                    duration = consume(voice, call, 'helper')
                    state['patternCursor'] = (state['patternCursor'] + 1) & 255
                    rows.append(dict(call=call, voiceIndex=voice, rowKind='rest', value=duration))
                    require(duration != 0, 'Unsupported zero duration; no one-call substitution')
                    state['nextCall'] = call + duration
                    break
                if token < 0x90:
                    slot = voice * 8 + (token & 15)
                    require(slot < len(mapping), 'Instrument slot escapes retained mapping; no guessed adjacent memory')
                    offset = mapping[slot]
                    require(offset in records, 'Record offset is outside the established 9-byte record table')
                    instruments.append(dict(call=call, voiceIndex=voice, slot=slot, recordOffset=offset,
                                            fields=list(records[offset]['fields'])))
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
