"""Editable Ghostbusters music rows and independent quarter-phase scheduling."""

from copy import deepcopy


FIELDS = dict(orderCursor=0x82, patternCursor=0x85, remaining=0x88,
              note=0x8b, header=0x8e, instrument=0x94)
CACHED_CONTROL = 0x91
SOURCE_SHA = 'f7f05616972d7fd5ad31df91284edbf4e0917d39422f8d004d50b40501a0dcde'


def byte(value, name, maximum=255):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError(f'{name} must be an integer in 0..{maximum}')
    return value


def encode_rows(rows):
    """Encode exactly the payload selected by the authoritative source header."""
    values, offsets = [], []
    for row in rows:
        if set(row) - {'header', 'note', 'parameter', 'sourceEvidence'}:
            raise ValueError('Unknown or duplicate editable row fields')
        header = byte(row['header'], 'header', 254)
        payload = set(row) - {'header', 'sourceEvidence'}
        expected = set() if header & 64 else {'note'} | ({'parameter'} if header & 128 else set())
        if payload != expected:
            raise ValueError('Header flags must match exact note/rest payload fields')
        offsets.append(len(values))
        values.append(header)
        if not header & 64:
            values.append(byte(row['note'], 'note', 95))
            if header & 128:
                parameter = row['parameter']
                if set(parameter) != {'volume', 'instrument'}:
                    raise ValueError('Packed parameter requires volume and instrument')
                values.append(byte(parameter['volume'], 'volume', 15) << 4
                              | byte(parameter['instrument'], 'instrument', 8))
    if not rows or len(values) >= 256:
        raise ValueError('Pattern rows and terminator must fit a byte cursor')
    return values + [255], offsets


def set_duration(row, duration):
    edited = deepcopy(row)
    edited['header'] = byte(row['header'], 'header', 254) & 224 | byte(duration, 'duration', 31)
    encode_rows([edited])
    return edited


def validate(description):
    if description['schemaVersion'] != 1 or len(description['orders']) != 3:
        raise ValueError('Choose the three-voice version-one score contract')
    initial = description['initialState']
    if set(initial) != {'phase', 'voices'} or len(initial['voices']) != 3:
        raise ValueError('Initial score state requires phase and three voices')
    byte(initial['phase'], 'phase')
    for voice in initial['voices']:
        if set(voice) != set(FIELDS):
            raise ValueError('Score state owns exactly its named fields; cached control belongs to sound')
        for field, value in voice.items():
            byte(value, field, 95 if field == 'note' else 8 if field == 'instrument' else 255)
    if not description['patterns']:
        raise ValueError('Score requires selected patterns')
    for key, pattern in description['patterns'].items():
        if str(byte(int(key), 'pattern ID', 127)) != str(key):
            raise ValueError('Pattern IDs must use canonical decimal keys')
        if set(pattern) - {'rows', 'sourceEvidence'}:
            raise ValueError('Unknown pattern fields')
        encode_rows(pattern['rows'])
    for order in description['orders']:
        if set(order) - {'patterns', 'sourceEvidence'} or not 1 <= len(order['patterns']) <= 255:
            raise ValueError('Order requires 1..255 pattern selections')
        for pattern in order['patterns']:
            if str(byte(pattern, 'order pattern ID', 127)) not in description['patterns']:
                raise ValueError('Order selects an absent pattern')


def decode(ram):
    """Decode only music data; source addresses annotate oracle reads, not runtime."""
    orders, patterns = [], {}
    for voice in range(3):
        base = ram[0xa2b7 + voice] | ram[0xa2ba + voice] << 8
        selected = []
        for offset in range(256):
            pattern = ram[base + offset]
            if pattern == 255:
                break
            selected.append(byte(pattern, 'pattern ID', 127))
            if str(pattern) in patterns:
                continue
            address = ram[0xa75b + pattern * 2] | ram[0xa75c + pattern * 2] << 8
            position, rows = 0, []
            while position < 255 and ram[address + position] != 255:
                header = ram[address + position]
                row = dict(header=header)
                position += 1
                if not header & 64:
                    row['note'] = ram[address + position]
                    position += 1
                    if header & 128:
                        packed = ram[address + position]
                        position += 1
                        row['parameter'] = dict(volume=packed >> 4, instrument=packed & 15)
                rows.append(row)
            encoded, _ = encode_rows(rows)
            if encoded != ram[address:address + position + 1]:
                raise ValueError('Semantic rows do not round-trip selected source bytes')
            patterns[str(pattern)] = dict(rows=rows, sourceEvidence=dict(address=address))
        else:
            raise ValueError('Order lacks an FF terminator within its byte cursor')
        orders.append(dict(patterns=selected, sourceEvidence=dict(address=base)))
    initial = [{field: ram[0x9104 + address - 0x82 + voice] for field, address in FIELDS.items()}
               for voice in range(3)]
    for voice in initial:
        voice.update(orderCursor=0, patternCursor=0, remaining=0)
    description = dict(schemaVersion=1, orders=orders, patterns=patterns,
        initialState=dict(phase=0, voices=initial),
        sourceEvidence=dict(sha256=SOURCE_SHA, selectedSubtune=1, clock='NTSC', sidModel='MOS6581'),
        limits='Music score component only. Header owns duration; packed parameters select volume/instrument. Sound owns cached control. Source addresses annotate reads and may be removed without changing scheduling. No speech data, full-machine RSID admission, synthesis, compiled playback or indefinite-playback claim.')
    validate(description)
    return description


class Scheduler:
    def __init__(self, description):
        validate(description)
        self.description = deepcopy(description)
        self.voices = deepcopy(description['initialState']['voices'])
        self.phase = description['initialState']['phase']
        self.tick = 0
        self.patterns = {key: (*encode_rows(pattern['rows']), pattern)
                         for key, pattern in self.description['patterns'].items()}

    def step(self):
        tick, phase = self.tick, self.phase
        reads, rows, resets, actions = [], [], [], []

        def read(voice, field, offset, value, *, pattern=None, address=None, pc=None):
            reads.append(dict(tick=tick, voice=voice, field=field, pattern=pattern,
                              offset=offset, value=value, address=address, pc=pc))
            return value

        for voice in (2, 1, 0):
            state, order = self.voices[voice], self.description['orders'][voice]
            if phase & 3:
                actions.append(dict(tick=tick, voice=voice, stage='body', phase=phase, state=deepcopy(state)))
                continue
            order_base = order.get('sourceEvidence', {}).get('address')
            for field, table, shift, pc in (('orderPointerLow', 0xa2b7, 0, 0x9405),
                                           ('orderPointerHigh', 0xa2ba, 8, 0x940a)):
                read(voice, field, voice, None if order_base is None else order_base >> shift & 255,
                     address=table + voice if order_base is not None else None, pc=pc)
            if state['remaining'] & 128:
                actions.append(dict(tick=tick, voice=voice, stage='inactive', phase=phase, state=deepcopy(state)))
                continue
            state['remaining'] = (state['remaining'] - 1) & 255
            if not state['remaining'] & 128:
                actions.append(dict(tick=tick, voice=voice, stage='body', phase=phase, state=deepcopy(state)))
                continue
            cursor = state['orderCursor']
            if not 0 <= cursor <= len(order['patterns']):
                raise ValueError('Order cursor is outside its data')
            pattern_id = 255 if cursor == len(order['patterns']) else order['patterns'][cursor]
            read(voice, 'order', cursor, pattern_id,
                 address=None if order_base is None else order_base + cursor, pc=0x9422)
            if pattern_id == 255:
                caches = [{field: value[field] for field in ('note', 'header', 'instrument')} for value in self.voices]
                resets.append(dict(tick=tick, voice=voice, phase=phase, retainedCaches=caches))
                for value in self.voices:
                    value.update(orderCursor=0, patternCursor=0, remaining=0)
                break
            values, offsets, pattern = self.patterns[str(pattern_id)]
            pattern_base = pattern.get('sourceEvidence', {}).get('address')
            for field, delta, shift, pc in (('patternPointerLow', 0, 0, 0x9436),
                                           ('patternPointerHigh', 1, 8, 0x943b)):
                read(voice, field, pattern_id * 2 + delta,
                     None if pattern_base is None else pattern_base >> shift & 255,
                     pattern=pattern_id, address=None if pattern_base is None else 0xa75b + pattern_id * 2 + delta, pc=pc)
            position = state['patternCursor']
            if position not in offsets:
                raise ValueError('Pattern cursor is not a semantic row boundary')
            row_index = offsets.index(position)

            def pattern_read(offset, field, pc):
                return read(voice, field, offset, values[offset], pattern=pattern_id,
                            address=None if pattern_base is None else pattern_base + offset, pc=pc)

            header = pattern_read(position, 'rowHeader', 0x9446)
            state['header'], state['remaining'] = header, header & 31
            rest = bool(header & 64)
            following = position + 1
            if not rest:
                following += 1
                if header & 128:
                    packed = pattern_read(position + 2, 'packedParameter', 0x945c)
                    state['instrument'] = packed & 15
                    actions.append(dict(tick=tick, voice=voice, stage='volume', nibble=packed >> 4,
                                        voice0OrderCursor=self.voices[0]['orderCursor']))
                    following += 1
                state['note'] = pattern_read(position + 1, 'note', 0x9490)
            next_byte = pattern_read(following, 'patternLookahead', 0x94f0)
            if next_byte == 255:
                state['patternCursor'] = 0
                state['orderCursor'] = (state['orderCursor'] + 1) & 255
            else:
                state['patternCursor'] = following
            row = dict(tick=tick, voice=voice, pattern=pattern_id, row=row_index,
                       kind='rest' if rest else 'note', state=deepcopy(state))
            rows.append(row)
            actions.append(dict(tick=tick, voice=voice, stage='onset', phase=phase, state=deepcopy(state)))
        self.phase = (phase + 1) & 255
        self.tick += 1
        returned = dict(tick=tick, phaseBefore=phase, phaseAfter=self.phase, voices=deepcopy(self.voices))
        return dict(reads=reads, rows=rows, resets=resets, actions=actions, returned=returned)


def expand(description, calls):
    if type(calls) is not int or not 1 <= calls <= 100000:
        raise ValueError('Choose 1..100000 bounded music-body calls')
    scheduler = Scheduler(description)
    result = dict(reads=[], rows=[], resets=[], actions=[], returns=[])
    for _ in range(calls):
        current = scheduler.step()
        for field in ('reads', 'rows', 'resets', 'actions'):
            result[field].extend(current[field])
        result['returns'].append(current['returned'])
    return result
