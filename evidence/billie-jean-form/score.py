"""Decode and expand the pinned Billie Jean score grammar without a CPU."""

from copy import deepcopy


def decode(ram):
    patterns, orders = {}, []
    for voice in range(3):
        base = ram[0x1440 + voice] | ram[0x1443 + voice] << 8
        values = []
        for offset in range(256):
            value = ram[base + offset]
            values.append(value)
            if value == 255:
                break
        else:
            raise ValueError('Order lacks an FF terminator')
        orders.append(dict(address=base, bytes=values))
        cursor = 0
        while values[cursor] != 255:
            if values[cursor] & 128:
                cursor += 1
            index = values[cursor]
            cursor += 1
            if index in patterns:
                continue
            base = ram[0x1900 + index] | ram[0x1980 + index] << 8
            address, rows = base, []
            while address - base < 256:
                header = ram[address]
                fields = dict(address=address, header=header, duration=header & 31,
                              kind='rest' if header & 224 == 192 else 'note')
                address += 1
                if fields['kind'] == 'note':
                    if header & 128:
                        fields['instrument'] = ram[address]
                        address += 1
                    if header & 64:
                        fields['glideStep'], fields['glideTarget'] = ram[address:address + 2]
                        address += 2
                    fields['note'] = ram[address]
                    address += 1
                rows.append(fields)
                if ram[address] == 255:
                    break
            else:
                raise ValueError('Pattern exceeds its byte cursor')
            patterns[index] = dict(address=base, rows=rows, terminatorAddress=address)
    initial = [dict(orderCursor=0, patternCursor=0, remaining=0, transpose=0,
                    baseNote=ram[0x145a + voice], instrumentOffset=ram[0x1470 + voice],
                    holdFlag=0, patternIndex=ram[0x148a + voice]) for voice in range(3)]
    return dict(schemaVersion=1, orders=orders, patterns=patterns, initialVoices=initial,
                rowDividerReload=2,
                limits='Numeric score/order expansion only; initial note/instrument values are loaded state retained by init. No sound programs or SID writes are computed.')


def expand(score, calls):
    if type(calls) is not int or not 1 <= calls <= 40000:
        raise ValueError('Choose 1..40000 calls')
    voices = deepcopy(score['initialVoices'])
    reads, rows, wraps, returns = [], [], [], []
    divider = 0

    def read(tick, voice, pc, address, value, field):
        reads.append(dict(tick=tick, voice=voice, pc=pc, address=address, value=value, field=field))

    for tick in range(calls):
        divider = (divider - 1) & 255
        if divider & 128:
            divider = score['rowDividerReload']
        for voice in (2, 1, 0):
            state = voices[voice]
            if divider:
                continue
            state['remaining'] = (state['remaining'] - 1) & 255
            if not state['remaining'] & 128:
                continue
            order = score['orders'][voice]
            cursor = state['orderCursor']
            value = order['bytes'][cursor]
            read(tick, voice, 0x102c, order['address'] + cursor, value, 'order')
            if value == 255:
                wraps.append(dict(tick=tick, voice=voice))
                for other in voices:
                    other['orderCursor'] = 0
                cursor = 0
                value = order['bytes'][0]
                read(tick, voice, 0x102c, order['address'], value, 'order')
            if value & 128:
                state['transpose'] = value & 127
                cursor += 1
                state['orderCursor'] = cursor
                value = order['bytes'][cursor]
                read(tick, voice, 0x104d, order['address'] + cursor, value, 'patternAfterTranspose')
            state['patternIndex'] = value
            pattern = score['patterns'][value] if value in score['patterns'] else score['patterns'][str(value)]
            read(tick, voice, 0x1053, 0x1900 + value, pattern['address'] & 255, 'patternPointerLow')
            read(tick, voice, 0x1058, 0x1980 + value, pattern['address'] >> 8, 'patternPointerHigh')
            row = next(row for row in pattern['rows'] if row['address'] == pattern['address'] + state['patternCursor'])
            address, header = row['address'], row['header']
            read(tick, voice, 0x1060, address, header, 'rowHeader')
            state['remaining'] = header & 31
            address += 1
            if row['kind'] == 'note':
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
            end = address == pattern['terminatorAddress']
            following = 255 if end else next(other['header'] for other in pattern['rows'] if other['address'] == address)
            read(tick, voice, 0x1079 if row['kind'] == 'rest' else 0x10c9,
                 address, following, 'followingByte')
            if end:
                state['patternCursor'] = 0
                state['orderCursor'] = (state['orderCursor'] + 1) & 255
            rows.append(dict(tick=tick, voice=voice, address=row['address'], header=header,
                             kind=row['kind'], state=deepcopy(state)))
        returns.append(dict(tick=tick, divider=divider, voices=deepcopy(voices)))
    return dict(reads=reads, rows=rows, wraps=wraps, returns=returns)
