"""Extract source-pinned editable Monty title data and verify its cold state."""

import argparse
import hashlib
import json
from pathlib import Path

from psid_audit import audit_psid
from psid_profile import psid_profile
from verify_player import require


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA256 = '528a7330817e4a0a0f75a505e9fe2444e07c5072ce5383ceaa89f183f0eee3ab'
SOURCE_URL = 'https://www.hvsc.de/download/C64Music/MUSICIANS/H/Hubbard_Rob/Monty_on_the_Run.sid'
ORDER_EXTENTS = ((0x8618, 65), (0x8659, 76), (0x86a5, 132))
PATTERN_LOW_BASE = 0x857e
PATTERN_HIGH_BASE = 0x85cb
FREQUENCY_BASE = 0x8400
INSTRUMENT_BASE = 0x93b4
VOICE_ADDRESSES = dict(order_cursor=0x84c4, pattern_cursor=0x84c7, remaining=0x84ca,
                       control=0x84cd, voice_control=0x84d0, note=0x84d3,
                       instrument_index=0x84d6, pulse_delay=0x84e5,
                       pulse_direction=0x84e8, portamento=0x84f5)
GLOBAL_ADDRESSES = dict(tempo_countdown=0x84eb, tempo_reload=0x84ec, status=0x84ee,
                        counter=0x84fa, sfx_priority=0x84fb, sfx_flags=0x84fc,
                        output_enable=0x84fd)
HELD_LOW_BASE = 0x84f2
HELD_HIGH_BASE = 0x84ef
INSTRUMENT_FIELDS = ('waveform', 'attack_decay', 'sustain_release', 'vibrato_depth',
                     'pulse_value', 'effects')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(path.read_bytes()))


def source_slice(memory, address, count, load, end):
    require(load <= address and address + count <= end, 'Numeric table extends outside the pinned payload')
    return memory[address:address + count]


def location(memory, address, count):
    return dict(address=address, bytes=count, sha256=sha(bytes(memory[address:address + count])))


def extract_score(memory, load, end):
    orders, order_locations = [], []
    for voice, (address, count) in enumerate(ORDER_EXTENTS):
        values = source_slice(memory, address, count, load, end)
        require(values[-1] == 255 and 255 not in values[:-1], 'Title order must end with one FF')
        require(254 not in values, 'Unsupported FE transport exit in title orders')
        orders.append(dict(voice_index=voice, bytes=values))
        order_locations.append(dict(voice_index=voice, **location(memory, address, count)))
    patterns, pattern_locations = [], []
    indices = sorted({value for order in orders for value in order['bytes'] if value < 254})
    for index in indices:
        low = source_slice(memory, PATTERN_LOW_BASE + index, 1, load, end)[0]
        high = source_slice(memory, PATTERN_HIGH_BASE + index, 1, load, end)[0]
        pointer = low | high << 8
        cursor = 0
        while cursor < 256:
            control = source_slice(memory, pointer + cursor, 1, load, end)[0]
            if control == 255:
                require(cursor != 0, 'Unsupported empty title pattern')
                break
            count = 1 if control & 64 else 3 if control & 128 else 2
            require(cursor + count < 256, 'Pattern does not terminate within its byte cursor')
            source_slice(memory, pointer + cursor, count, load, end)
            cursor += count
        else:
            raise ValueError('Pattern does not terminate within its byte cursor')
        values = source_slice(memory, pointer, cursor + 1, load, end)
        patterns.append(dict(pattern_id=index, bytes=values))
        pattern_locations.append(dict(pattern_id=index, **location(memory, pointer, cursor + 1)))
    return dict(orders=orders, patterns=patterns), dict(orders=order_locations, patterns=pattern_locations)


def named_state(memory):
    globals_ = {name: memory[address] for name, address in GLOBAL_ADDRESSES.items()}
    # Archive $8012 loads #$0f each call; it does not read a saved SID register.
    require(memory[0x8012:0x8017] == [0xa9, 15, 0x8d, 0x18, 0xd4], 'Title volume instruction differs')
    globals_['mode_volume'] = memory[0x8013]
    voices = []
    for voice in range(3):
        row = {name: memory[address + voice] for name, address in VOICE_ADDRESSES.items()}
        row['held_frequency'] = memory[HELD_LOW_BASE + voice] | memory[HELD_HIGH_BASE + voice] << 8
        voices.append(row)
    return dict(globals=globals_, voices=voices)


def frequency_alias_bindings():
    """Map live bytes required by note 104 and its adjacent/octave lookups.

    The owning native mappings are in evidence/monty-programs/contract.json.
    Base104 reads controls0/1, vibrato's shifted base reads control2/note0,
    and the controlled octave104+12 lookup reads PWM directions0/1.
    """
    return [dict(offset=address - FREQUENCY_BASE, voice_index=voice, field=field)
            for field, voices in (('voice_control', range(3)), ('note', range(1)),
                                  ('pulse_direction', range(2)))
            for voice in voices
            for address in (VOICE_ADDRESSES[field] + voice,)]


def cold_state(data, memory):
    observed = []
    def observer(cpu, guarded_memory):
        if guarded_memory.phase == 'play' and guarded_memory.tick == 0 and cpu.pc == 0x8012:
            observed.append(named_state(guarded_memory.data))
    report, writes = audit_psid(data, 1, profile='pal-banked', subtune=1, observer=observer)
    require(len(observed) == 1, 'Native cold state was not observed exactly once')
    expected = named_state(memory)
    expected['globals']['status'] = 64
    require(observed[0] == expected, 'Native cold state differs from the named initialization contract')
    initialization = [row for row in writes if row['phase'] == 'init']
    require([(row['address'], row['value']) for row in initialization]
            == [(0xd404, 0), (0xd40b, 0), (0xd412, 0)], 'Native initialization stores differ')
    require(report['initCycles'] == 165, 'Native initialization cycle count differs')
    return observed[0], dict(cycles=report['initCycles'], controlledPlayCalls=1,
                            boundary='Before first play entry $8012, after selected native initialization',
                            initStoreCount=len(initialization),
                            namedStateSha256=sha(json.dumps(observed[0], sort_keys=True, separators=(',', ':')).encode()),
                            stateBasis='Loaded named values with only status changed to $40 by native init; score reset occurs inside first play.',
                            limits='One guarded play call captures the post-init boundary; no full-title CPU execution or SID synthesis.')


def attribution():
    receipt_path = ROOT / 'evidence/monty-intake/provenance.json'
    receipt = json.loads(receipt_path.read_text())
    require(receipt['source']['sha256'] == SOURCE_SHA256, 'Monty provenance source pin differs')
    selected = next(row for row in receipt['stil']['subtuneAnnotations'] if row['subtune'] == 1)
    return dict(musicCredit=receipt['source']['credit'],
                inspiration=dict(subtune=1, title=selected['title'], artist=selected['artist'],
                                 meaning=selected['meaning'],
                                 stilVersion=receipt['stil']['version'],
                                 stilSha256=receipt['stil']['sha256'],
                                 entrySha256=receipt['stil']['entrySha256'],
                                 sourceReceipt=fingerprint(receipt_path)))


def extract_data(data, *, play_calls=40000):
    require(sha(data) == SOURCE_SHA256, 'Source is not the pinned Monty archive')
    require(type(play_calls) is int and 1 <= play_calls <= 40000, 'Choose 1..40000 calls within the retained title window')
    profile = psid_profile(data, profile='pal-banked', subtune=1)
    require((profile['loadAddress'], profile['endAddress'], profile['initAddress'], profile['playAddress'])
            == (0x8000, 0x95c0, 0x8000, 0x8012), 'Monty callable source layout differs')
    memory = [0] * 65536
    memory[profile['loadAddress']:profile['endAddress']] = profile['payload']
    score, score_locations = extract_score(memory, profile['loadAddress'], profile['endAddress'])
    state, initialization = cold_state(data, memory)
    frequency_bytes = source_slice(memory, FREQUENCY_BASE, 192, profile['loadAddress'], profile['endAddress'])
    frequencies = [frequency_bytes[2 * i] | frequency_bytes[2 * i + 1] << 8 for i in range(96)]
    instrument_bytes = source_slice(memory, INSTRUMENT_BASE, 160, profile['loadAddress'], profile['endAddress'])
    instruments = []
    for index in range(20):
        values = instrument_bytes[index * 8:(index + 1) * 8]
        instruments.append(dict(pulse_word=values[0] | values[1] << 8,
                                **dict(zip(INSTRUMENT_FIELDS, values[2:]))))
    mappings = dict(voiceBytes=VOICE_ADDRESSES, globals=GLOBAL_ADDRESSES,
                    heldFrequency=dict(lowBase=HELD_LOW_BASE, highBase=HELD_HIGH_BASE),
                    modeVolume=dict(operandAddress=0x8013, basis='Immediate operand in $8012 LDA'))
    evidence = dict(sourceSha256=SOURCE_SHA256, sourceUrl=SOURCE_URL, selectedSubtune=1,
                    profile='pal-banked', loadAddress=profile['loadAddress'],
                    initAddress=profile['initAddress'], playAddress=profile['playAddress'],
                    clock='PAL', sidModel='MOS6581', sidBases=[0xd400],
                    **attribution(), initialization=initialization,
                    stateMappings=mappings, scoreMappings=score_locations,
                    patternPointerBanks=dict(lowBase=PATTERN_LOW_BASE, highBase=PATTERN_HIGH_BASE),
                    tables=dict(frequencyWords=location(memory, FREQUENCY_BASE, 192),
                                instruments=location(memory, INSTRUMENT_BASE, 160)),
                    extractor=fingerprint(Path(__file__)),
                    dependencies={name: fingerprint(ROOT / 'scripts' / name) for name in
                                  ('psid_profile.py', 'psid_audit.py', 'sid_audit_host.py', 'verify_player.py')},
                    frequencyDomain='Exactly 96 interleaved source words. Beyond-table lookups bind named live state bytes; no inferred chromatic extension.',
                    instrumentPolicy='All twenty loaded eight-byte records are named numeric parameters; pulse words are shared mutable state.',
                    limits='Editable numeric score, instrument parameters and cold named state; no source driver, full RAM image, captured-event replay, cycle-equivalent player, PCM or listening claim.')
    return dict(format='monty-editable-title-v1', play_calls=play_calls, initial_state=state,
                score=score, instruments=instruments, frequency_words=frequencies,
                frequency_alias_bindings=frequency_alias_bindings(), sourceEvidence=evidence)


def write_description(path, description):
    require(not path.exists() and not path.is_symlink(), 'Use a fresh output path')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as target:
        json.dump(description, target, indent=2)
        target.write('\n')


def check_description(path, description):
    require(json.loads(path.read_text()) == description, 'Prepared description differs from the pinned source extraction')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sid', nargs='?', type=Path, default=ROOT / '.local/monty-source.sid')
    parser.add_argument('--play-calls', type=int, default=40000)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--output', type=Path)
    target.add_argument('--check', type=Path)
    args = parser.parse_args()
    if args.output is not None:
        require(not args.output.exists() and not args.output.is_symlink(), 'Use a fresh output path')
    description = extract_data(args.sid.read_bytes(), play_calls=args.play_calls)
    if args.check is not None:
        check_description(args.check, description)
        path = args.check
    else:
        write_description(args.output, description)
        path = args.output
    print(json.dumps(dict(path=str(path), checked=args.check is not None,
                          sha256=sha(path.read_bytes()), patterns=len(description['score']['patterns']),
                          instruments=len(description['instruments']), playCalls=description['play_calls'])))


if __name__ == '__main__':
    main()
