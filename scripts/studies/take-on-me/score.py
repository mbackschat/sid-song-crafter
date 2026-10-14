"""Expand editable Take On Me orders and semantic rows without a CPU or SID writes."""

from copy import deepcopy


FIELDS = {
    'remaining': 0x1a99, 'orderCursor': 0x1a9c, 'repeat': 0x1a9f,
    'transpose': 0x1aa2, 'patternCursor': 0x1aa5, 'instrument': 0x1aa8,
    'durationTicks': 0x1aab, 'glideStepLow': 0x1aae, 'glideStepHigh': 0x1ab1,
    'baseNote': 0x1ab4, 'glideTarget': 0x1ab7, 'arpeggio': 0x1ac0,
}


def byte(value, name, maximum=255):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError(f'{name} must be an integer in 0..{maximum}')
    return value


def encode_rows(rows):
    values, offsets = [], []
    for row in rows:
        offsets.append(len(values))
        if 'arpeggio' in row:
            values.extend((254, byte(row['arpeggio'], 'arpeggio')))
        if 'instrument' in row:
            values.append(192 | byte(row['instrument'], 'instrument', 31))
        if 'durationUnits' in row:
            duration = byte(row['durationUnits'], 'durationUnits', 127)
            if duration >= 64 and 'instrument' not in row:
                raise ValueError('Duration 64..127 requires instrument context to avoid a command alias')
            values.append(128 | duration)
        if 'glide' in row:
            if 'note' in row:
                raise ValueError('A row must have either note or glide')
            glide = row['glide']
            step = byte(glide['stepWord'], 'glide step word', 65535)
            values.extend((96, step & 255, step >> 8,
                           byte(glide['note'], 'glide note'), byte(glide['target'], 'glide target')))
        else:
            note = byte(row['note'], 'note', 127)
            if note == 96:
                raise ValueError('Note 96 is reserved for the glide command')
            values.append(note)
    if not rows or len(values) >= 256:
        raise ValueError('A pattern must contain rows and fit its byte cursor')
    return values + [255], offsets


def decode(ram):
    """Read the pinned driver data into semantic rows; source addresses label evidence."""
    orders, patterns = [], {}
    for voice in range(3):
        address = ram[0x15a1 + (2 - voice) * 2] | ram[0x15a2 + (2 - voice) * 2] << 8
        values, cursor = [], 0
        while cursor < 256:
            value = ram[address + cursor]
            values.append(value)
            cursor += 1
            if value == 254:
                break
            if value == 255:
                values.append(ram[address + cursor])
                break
            if value >= 128:
                continue
            if str(value) in patterns:
                continue
            base = ram[0x15ad + value] | ram[0x15bf + value] << 8
            position, rows = base, []
            while position - base < 255:
                row, code = {}, ram[position]
                if code == 254:
                    row['arpeggio'] = ram[position + 1]
                    position += 2
                    code = ram[position]
                if code >= 192:
                    row['instrument'] = code & 31
                    position += 1
                    code = ram[position]
                if code >= 128:
                    row['durationUnits'] = code & 127
                    position += 1
                    code = ram[position]
                if code == 96:
                    row['glide'] = dict(stepWord=ram[position + 1] | ram[position + 2] << 8,
                                        note=ram[position + 3], target=ram[position + 4])
                    position += 5
                else:
                    row['note'] = code
                    position += 1
                rows.append(row)
                if ram[position] == 255:
                    break
            else:
                raise ValueError('Pattern lacks a terminator within its byte cursor')
            encoded, _ = encode_rows(rows)
            if encoded != ram[base:position + 1]:
                raise ValueError('Semantic pattern does not round-trip source bytes')
            patterns[str(value)] = dict(address=base, rows=rows)
        else:
            raise ValueError('Order lacks a stop or jump within its byte cursor')
        orders.append(dict(address=address, bytes=values))
    initial = [{name: ram[address + voice] for name, address in FIELDS.items()} for voice in range(3)]
    for state in initial:
        state.update(remaining=1, orderCursor=0, repeat=0, transpose=0, patternCursor=0, instrument=0, durationTicks=0)
    return dict(schemaVersion=1, dividerReloads=ram[0x159f:0x15a1],
                initialDividers=ram[0x1a97:0x1a99], orders=orders, patterns=patterns,
                initialVoices=initial,
                limits='Score expansion only. Source addresses label modeled reads; numeric rows and live state drive execution. Sound, SID stores, compiled playback and acoustic recurrence are separate.')


def expand(score, calls):
    """Compute contextual reads, note setup and score return state for bounded calls."""
    if type(calls) is not int or not 1 <= calls <= 100000:
        raise ValueError('Choose 1..100000 calls')
    voices = deepcopy(score['initialVoices'])
    dividers = list(score['initialDividers'])
    patterns = {str(key): (*encode_rows(value['rows']), value['address']) for key, value in score['patterns'].items()}
    reads, rows, wraps, stops, returns = [], [], [], [], []
    active = True

    def read(tick, voice, pc, address, value, field):
        reads.append(dict(tick=tick, voice=voice, pc=pc, address=address, value=value, field=field))
        return value

    for tick in range(calls):
        if active:
            dividers[0] = (dividers[0] - 1) & 255
            skip = False
            if dividers[0] >= 128:
                dividers[0] = byte(score['dividerReloads'][0], 'first divider reload')
                skip = dividers[0] != 0
            if not skip:
                dividers[1] = (dividers[1] - 1) & 255
                if dividers[1] >= 128:
                    dividers[1] = byte(score['dividerReloads'][1], 'second divider reload')
                    for state in voices:
                        state['remaining'] = (state['remaining'] - 1) & 255
            for voice in (2, 1, 0):
                state = voices[voice]
                if state['remaining']:
                    continue
                order = score['orders'][voice]
                cursor = state['orderCursor']

                def order_read(pc, field):
                    if not 0 <= cursor < len(order['bytes']):
                        raise ValueError('Order cursor is outside its data')
                    return read(tick, voice, pc, order['address'] + cursor, byte(order['bytes'][cursor], field), field)

                code = order_read(0x10a5, 'order')
                if code == 254:
                    active = False
                    stops.append(dict(tick=tick, voice=voice))
                    break
                if code == 255:
                    cursor += 1
                    cursor = order_read(0x10b8, 'orderJumpTarget')
                    state['orderCursor'] = cursor
                    wraps.append(dict(tick=tick, voice=voice, target=cursor))
                    code = order_read(0x10be, 'orderAfterJump')
                if code >= 128:
                    if code >= 192:
                        state['repeat'] = code & 31
                        cursor += 1
                        code = order_read(0x10cc, 'orderAfterRepeat')
                    if code >= 128:
                        state['transpose'] = code & 31
                        cursor += 1
                    state['orderCursor'] = cursor
                    code = order_read(0x10dc, 'patternAfterCommands')
                if code >= 128 or str(code) not in patterns:
                    raise ValueError('Order does not select a decoded pattern')
                values, offsets, address = patterns[str(code)]
                read(tick, voice, 0x10df, 0x15ad + code, address & 255, 'patternPointerLow')
                read(tick, voice, 0x10e4, 0x15bf + code, address >> 8, 'patternPointerHigh')
                position = state['patternCursor']
                if position not in offsets:
                    raise ValueError('Pattern cursor is not a row boundary')
                row_index = offsets.index(position)

                def pattern_read(pc, field):
                    return read(tick, voice, pc, address + position, values[position], field)

                value = pattern_read(0x10ec, 'rowHeader')
                if value == 254:
                    position += 1
                    state['arpeggio'] = pattern_read(0x10f5, 'arpeggio')
                    position += 1
                    value = pattern_read(0x10fb, 'afterArpeggio')
                if value >= 192:
                    state['instrument'] = value & 31
                    position += 1
                    value = pattern_read(0x1107, 'afterInstrument')
                if value >= 128:
                    state['durationTicks'] = ((value & 127) * 2) & 255
                    position += 1
                    value = pattern_read(0x1114, 'afterDuration')
                glide_active = int(value == 96)
                if glide_active:
                    position += 1
                    state['glideStepLow'] = pattern_read(0x111b, 'glideStepLow')
                    position += 1
                    state['glideStepHigh'] = pattern_read(0x1121, 'glideStepHigh')
                    position += 1
                    note = pattern_read(0x1127, 'glideNote') + state['transpose']
                    state['baseNote'] = note & 255
                    position += 1
                    state['glideTarget'] = (pattern_read(0x1131, 'glideTarget') + state['transpose'] + int(note > 255)) & 255
                else:
                    state['baseNote'] = (value + state['transpose']) & 255
                state['remaining'] = state['durationTicks']
                position += 1
                following = pattern_read(0x114e, 'followingByte')
                if following == 255:
                    if state['repeat']:
                        state['repeat'] -= 1
                    else:
                        state['orderCursor'] = (state['orderCursor'] + 1) & 255
                    position = 0
                state['patternCursor'] = position
                rows.append(dict(tick=tick, voice=voice, pattern=code, row=row_index,
                                 address=address + offsets[row_index], glideActive=glide_active,
                                 state=deepcopy(state)))
        returns.append(dict(tick=tick, active=active, dividers=list(dividers), voices=deepcopy(voices)))
    return dict(reads=reads, rows=rows, wraps=wraps, stops=stops, returns=returns)
