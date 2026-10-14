"""Decode and expand editable Billie Jean headers without source execution."""

from copy import deepcopy


FIELD_ADDRESSES = dict(orderCursor=0x1460, patternCursor=0x145d, remaining=0x144a,
    transpose=0x1493, baseNote=0x145a, instrumentOffset=0x1470,
    holdFlag=0x1484, patternIndex=0x148a)


def byte(value, name, maximum=255):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError(f'{name} must be an integer in 0..{maximum}')
    return value


def row_kind(header):
    return 'rest' if header & 224 == 192 else 'note'


def encode_rows(rows):
    """Derive byte widths and offsets from the single authoritative row header."""
    encoded, offsets = [], []
    for row in rows:
        unknown = set(row) - {'header', 'instrument', 'glideStep', 'glideTarget', 'note', 'sourceEvidence'}
        if unknown:
            raise ValueError(f'Unknown row fields: {sorted(unknown)}')
        header = byte(row['header'], 'header', 254)
        offsets.append(len(encoded))
        encoded.append(header)
        payload = set(row) - {'header', 'sourceEvidence'}
        if row_kind(header) == 'rest':
            if payload:
                raise ValueError('Rest header consumes no note/instrument/glide payload')
            continue
        expected = {'note'}
        if header & 128:
            expected.add('instrument')
        if header & 64:
            expected.update(('glideStep', 'glideTarget'))
        if payload != expected:
            raise ValueError('Header flags must match the exact note payload fields')
        for field in ('instrument', 'glideStep', 'glideTarget', 'note'):
            if field in expected:
                encoded.append(byte(row[field], field))
    if not rows or len(encoded) >= 256:
        raise ValueError('Pattern rows and terminator must fit a byte cursor')
    return encoded + [255], offsets


def set_duration(row, duration):
    """Return a row with only the low five header bits changed."""
    edited = deepcopy(row)
    edited['header'] = (byte(row['header'], 'header', 254) & 224) | byte(duration, 'duration', 31)
    encode_rows([edited])
    return edited


def decode(ram):
    """Decode source data; optional sourceAddress fields label evidence only."""
    patterns, orders = {}, []
    for voice in range(3):
        base = ram[0x1440 + voice] | ram[0x1443 + voice] << 8
        values = []
        for offset in range(256):
            values.append(ram[base + offset])
            if values[-1] == 255:
                break
        else:
            raise ValueError('Order lacks an FF terminator')
        orders.append(dict(sourceAddress=base, bytes=values))
        cursor = 0
        while values[cursor] != 255:
            if values[cursor] & 128:
                cursor += 1
            index = values[cursor]
            byte(index, 'Pattern ID', 127)
            cursor += 1
            if str(index) in patterns:
                continue
            base = ram[0x1900 + index] | ram[0x1980 + index] << 8
            address, rows = base, []
            while address - base < 256:
                header = ram[address]
                row = dict(header=header)
                address += 1
                if row_kind(header) == 'note':
                    if header & 128:
                        row['instrument'] = ram[address]
                        address += 1
                    if header & 64:
                        row['glideStep'], row['glideTarget'] = ram[address:address + 2]
                        address += 2
                    row['note'] = ram[address]
                    address += 1
                rows.append(row)
                if ram[address] == 255:
                    break
            else:
                raise ValueError('Pattern exceeds its byte cursor')
            encoded, _ = encode_rows(rows)
            if encoded != ram[base:address + 1]:
                raise ValueError('Decoded pattern does not round-trip source data')
            patterns[str(index)] = dict(sourceAddress=base, rows=rows)
    initial = [dict(orderCursor=0, patternCursor=0, remaining=0, transpose=0,
        baseNote=ram[0x145a + voice], instrumentOffset=ram[0x1470 + voice],
        holdFlag=0, patternIndex=ram[0x148a + voice]) for voice in range(3)]
    return dict(schema='billie-jean-score-v1', orders=orders, patterns=patterns,
        initialVoices=initial, initialDivider=0, rowDividerReload=2)


def expand(description, calls):
    """Compute score consumption and row commands from numeric data and live state.

    Header low bits own duration; note/rest kind and payload width are derived.
    Row commands expose gate/glide setters to sound integration, which owns the
    evolving gate mask and glide step. Source addresses affect labels only.
    The declared call window establishes no sound, ending or musical verdict.
    """
    if description.get('schema') != 'billie-jean-score-v1':
        raise ValueError('Expected billie-jean-score-v1')
    if type(calls) is not int or not 1 <= calls <= 40000:
        raise ValueError('Choose 1..40000 calls')
    voices = deepcopy(description['initialVoices'])
    if len(voices) != 3 or len(description['orders']) != 3:
        raise ValueError('Score requires three initial voices and orders')
    for state in voices:
        if set(state) != set(FIELD_ADDRESSES):
            raise ValueError('Initial voice fields must match the named score state')
        for name, value in state.items():
            byte(value, name)
    divider = byte(description['initialDivider'], 'initialDivider')
    reload = byte(description['rowDividerReload'], 'rowDividerReload')
    patterns = {}
    for index, pattern in description['patterns'].items():
        if isinstance(index, str) and index.isdecimal():
            index = int(index)
        byte(index, 'Pattern ID', 127)
        if index in patterns:
            raise ValueError('Duplicate numeric pattern IDs')
        encoded, offsets = encode_rows(pattern['rows'])
        patterns[index] = dict(rows=pattern['rows'], bytes=encoded, offsets=offsets,
            address=byte(pattern.get('sourceAddress', 0), 'sourceAddress', 65535))
    for order in description['orders']:
        if not 1 <= len(order['bytes']) <= 256:
            raise ValueError('Order must fit its byte cursor')
        for value in order['bytes']:
            byte(value, 'Order byte')
    reads, rows, wraps, returns = [], [], [], []

    def read(tick, voice, pc, address, value, field):
        reads.append(dict(tick=tick, voice=voice, pc=pc, address=address, value=value, field=field))

    for tick in range(calls):
        divider = (divider - 1) & 255
        if divider & 128:
            divider = reload
        for voice in (2, 1, 0):
            state = voices[voice]
            if divider:
                continue
            state['remaining'] = (state['remaining'] - 1) & 255
            if not state['remaining'] & 128:
                continue
            order = description['orders'][voice]
            base = byte(order.get('sourceAddress', 0), 'sourceAddress', 65535)
            cursor = state['orderCursor']
            if cursor >= len(order['bytes']):
                raise ValueError('Order cursor escapes its data')
            value = order['bytes'][cursor]
            read(tick, voice, 0x102c, base + cursor, value, 'order')
            if value == 255:
                wraps.append(dict(tick=tick, voice=voice))
                for other in voices:
                    other['orderCursor'] = 0
                cursor = 0
                value = order['bytes'][0]
                read(tick, voice, 0x102c, base, value, 'order')
            if value & 128:
                state['transpose'] = value & 127
                cursor += 1
                state['orderCursor'] = cursor
                if cursor >= len(order['bytes']):
                    raise ValueError('Transpose command lacks a pattern ID')
                value = order['bytes'][cursor]
                read(tick, voice, 0x104d, base + cursor, value, 'patternAfterTranspose')
            if value not in patterns:
                raise ValueError(f'Missing selected pattern {value}')
            state['patternIndex'] = value
            pattern = patterns[value]
            read(tick, voice, 0x1053, 0x1900 + value, pattern['address'] & 255, 'patternPointerLow')
            read(tick, voice, 0x1058, 0x1980 + value, pattern['address'] >> 8, 'patternPointerHigh')
            offset = state['patternCursor']
            if offset not in pattern['offsets']:
                raise ValueError('Pattern cursor does not select a row boundary')
            row_index = pattern['offsets'].index(offset)
            row = pattern['rows'][row_index]
            header, address = row['header'], pattern['address'] + offset
            kind = row_kind(header)
            read(tick, voice, 0x1060, address, header, 'rowHeader')
            state['remaining'] = header & 31
            address += 1
            if kind == 'note':
                state['holdFlag'] = header & 32
                if header & 128:
                    read(tick, voice, 0x1099, address, row['instrument'], 'instrument')
                    state['instrumentOffset'] = (row['instrument'] * 8) & 255
                    address += 1
                if header & 64:
                    read(tick, voice, 0x10ab, address, row['glideStep'], 'glideStep')
                    read(tick, voice, 0x10b1, address + 1, row['glideTarget'], 'glideTarget')
                    address += 2
                read(tick, voice, 0x10bb, address, row['note'], 'note')
                state['baseNote'] = (row['note'] + state['transpose']) & 255
                address += 1
            state['patternCursor'] = (address - pattern['address']) & 255
            end = row_index == len(pattern['rows']) - 1
            following = 255 if end else pattern['rows'][row_index + 1]['header']
            read(tick, voice, 0x1079 if kind == 'rest' else 0x10c9, address, following, 'followingByte')
            if end:
                state['patternCursor'] = 0
                state['orderCursor'] = (state['orderCursor'] + 1) & 255
            rows.append(dict(tick=tick, voice=voice, address=pattern['address'] + offset,
                header=header, kind=kind, rowIndex=row_index, command=deepcopy(row), state=deepcopy(state)))
        returns.append(dict(tick=tick, divider=divider, voices=deepcopy(voices)))
    return dict(reads=reads, rows=rows, wraps=wraps, returns=returns)
