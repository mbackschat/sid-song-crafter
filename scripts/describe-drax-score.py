"""Describe one pinned DRAX thematic cycle through executed score consumption."""

import argparse
import hashlib
import json
from pathlib import Path

from psid_audit import audit_psid
from verify_player import require


SOURCE_SHA256 = 'ea6b7eba46844d399e415368eae86c3ddf03bd9041ecba93e7bb53b384daa2a1'
STOP_CALL = 2018
CYCLE_CALLS = 2016
PATCH_NAMES = {
    0: 'bass-noise-pulse', 16: 'lead-pulse', 8: 'chord-minor',
    40: 'chord-dominant-inversion', 48: 'chord-major', 56: 'chord-dominant',
}


def word(memory, address):
    return memory[address] | memory[address + 1] << 8


def decode_patch(memory, offset):
    row = memory[0x1aa2 + offset:0x1aaa + offset]
    modulation = row[6]
    delay, counter, increment = memory[0x19a2 + modulation:0x19a5 + modulation]
    packed_width = row[4]
    patch = {
        'attackDecay': row[0], 'sustainRelease': row[1],
        'pulseInitial': (packed_width & 240) | ((packed_width & 15) << 8),
        'pulseStep': row[3], 'pulseLowerHighByte': row[2] >> 4,
        'pulseUpperHighByte': row[2] & 15,
        'sourceEvidence': {
            'sourceInstrumentOffset': offset, 'waveProgramStartIndex': row[7],
            'vibratoDelayCalls': delay, 'vibratoCounter': counter, 'vibratoIncrement': increment << 2,
        },
    }
    if offset in (8, 40, 48, 56):
        index, pitches = row[7], []
        while memory[0x16a2 + index] != 127:
            require(len(pitches) < 16 and memory[0x17a2 + index] == 0x51, 'Unsupported chord program')
            pitches.append(memory[0x16a2 + index])
            index += 1
        require(memory[0x17a2 + index] == row[7], 'Chord must loop to its first tone')
        require(pitches[::2] == pitches[1::2], 'Chord tones must dwell for two calls')
        patch['sourceEvidence'].update(toneSemitones=pitches[::2],
                                       pulseLowerHighByte=patch.pop('pulseLowerHighByte'),
                                       pulseUpperHighByte=patch.pop('pulseUpperHighByte'))
        patch.update(waveform=80, toneDwellCalls=2)
    elif offset == 16:
        require((delay, counter, increment) == (10, 3, 32), 'Lead vibrato differs from decoded mechanism')
        patch.update(waveform=64, vibratoStartAge=11,
                     vibratoDeltas=[0, 128, 256, 128, 0, -128, -256, -128])
    else:
        require(offset == 0, 'Unsupported instrument')
        patch.update(instrumentGateCloseAge=3, noiseControl=129, pulseControl=65,
                     releaseControl=64, noiseFrequency=50400, attackCutoffHigh=240,
                     bodyCutoffHigh=8, filterRoutingResonance=241, filterModeVolume=31)
    return patch


def describe_score(data):
    require(hashlib.sha256(data).hexdigest() == SOURCE_SHA256, 'Source differs from pinned DRAX tune')
    records, commands, patches = [], [], {}

    def observe(cpu, memory):
        if memory.phase != 'play':
            return
        current, voice = memory.data, cpu.x + 1
        if cpu.pc in (0x1138, 0x1176, 0x116c):
            commands.append({'call': memory.tick, 'voice': voice, 'pc': cpu.pc, 'value': cpu.a})
        if cpu.pc != 0x12b2:
            return
        offset = current[0x101d + cpu.x]
        require(offset in PATCH_NAMES, 'Unexpected source instrument')
        index = (2 * current[0x1014 + cpu.x] + current[0x1017 + cpu.x]) & 255
        root = word(current, 0x1468 + index)
        # $1340 processes the preceding instrument before $12B2 resets its program.
        prepared = current[0x100c + cpu.x] | current[0x100f + cpu.x] << 8
        patch = decode_patch(current, offset)
        name = PATCH_NAMES[offset]
        require(name not in patches or patches[name] == patch, 'Instrument parameters changed during execution')
        patches[name] = patch
        record = {'voice': voice, 'initCall': memory.tick, 'frequency': prepared,
                  'baseFrequency': root, 'patch': name}
        if voice == 3:
            record['frequencies'] = [word(current, 0x1468 + index + 2 * tone)
                                     for tone in patch['sourceEvidence']['toneSemitones']]
        records.append(record)

    _, writes = audit_psid(data, 4 + 2 * CYCLE_CALLS + 1, observer=observe)
    play = [write for write in writes if write['phase'] == 'play']
    grouped = {}
    for write in play:
        grouped.setdefault((write['tick'], write['address']), []).append(write['value'])
    initializations = [(write['tick'], (write['address'] - 0xd404) // 7 + 1)
                       for write in play if write['address'] in (0xd404, 0xd40b, 0xd412) and write['value'] == 9]
    require(initializations == [(record['initCall'], record['voice']) for record in records],
            'Executed note initializations differ from SID onset signatures')
    for record in records:
        call, base = record['initCall'], 0xd400 + 7 * (record['voice'] - 1)
        require(grouped[(call - 1, base + 4)] == [8], 'Note lacks a TEST preparation')
        require(grouped[(call - 1, base)][-1] | grouped[(call - 1, base + 1)][-1] << 8 == record['frequency'],
                'Preparation frequency state differs from executed stores')
        require(any(command['call'] == call - 2 and command['voice'] == record['voice']
                    and command['pc'] == 0x1138 for command in commands), 'Initialization lacks a consumed score note')

    def events(voice, start, stop):
        selected = [record for record in records if record['voice'] == voice and start <= record['initCall'] < stop]
        notes = []
        for index, record in enumerate(selected):
            note = {key: value for key, value in record.items() if key not in ('voice', 'baseFrequency')}
            if voice == 3:
                note['sourceEvidence'] = {'baseFrequency': record['baseFrequency']}
            end = selected[index + 1]['initCall'] - 2 if index + 1 < len(selected) else stop
            off = next((command['call'] for command in commands if command['voice'] == voice
                        and command['pc'] == 0x1176 and record['initCall'] < command['call'] < end), None)
            if off is not None:
                require(not any(command['voice'] == voice and command['pc'] == 0x116c
                                and off < command['call'] < end for command in commands), 'Score reopens a released note')
                control = 0xd404 + 7 * (voice - 1)
                require(grouped[(off, control)][-1] & 1 == 0 and grouped[(off - 1, control)][-1] & 1 == 1,
                        'Score gate closure differs from executed control writes')
                note['gateOffCall'] = off
            notes.append(note)
        return notes

    roles = {}
    for voice, name in ((1, 'bass'), (2, 'lead'), (3, 'chord')):
        first = events(voice, 0, STOP_CALL)
        second = events(voice, CYCLE_CALLS, STOP_CALL + CYCLE_CALLS)

        def musical_signature(note, shift):
            return (note['initCall'] - shift, note.get('sourceEvidence', {}).get('baseFrequency', note['frequency']), note['patch'],
                    tuple(note.get('frequencies', [])), note.get('gateOffCall', shift) - shift)

        require([musical_signature(note, 0) for note in first] ==
                [musical_signature(note, CYCLE_CALLS) for note in second], 'Musical cycle does not repeat')
        roles[name] = {'voice': voice, 'notes': first}
    require({name: len(role['notes']) for name, role in roles.items()} == {'bass': 26, 'lead': 123, 'chord': 26},
            'Thematic cycle note counts differ')
    boundary = next(record for record in records if record['voice'] == 2 and record['initCall'] == 2020)
    roles['lead']['boundaryNote'] = {'initCall': 2020, 'frequency': boundary['frequency'], 'patch': boundary['patch'],
                                   'purpose': 'Next cycle metadata only; excluded before stopCall 2018'}
    return {
        'format': 'sid-decoded-composition-v1',
        'source': {'path': '.local/research/fuer-elise/drax-fuer-elise.sid', 'sha256': SOURCE_SHA256,
                   'initAddress': 4096, 'playAddress': 4099},
        'profile': {'clock': 'PAL', 'chip': 'MOS6581', 'callCycles': 19656},
        'range': {'firstCall': 0, 'lastCallInclusive': 2017, 'stopCall': STOP_CALL, 'firstLeadInitCall': 4,
                  'cycleCalls': CYCLE_CALLS, 'nextCycleFirstLeadInitCall': 2020, 'nextCyclePreparationFirstCall': 2018},
        'bassRecipe': '../drax-bass-reconstruction/instrument.json', 'roles': roles, 'patches': patches,
        'evidence': {
            'method': 'Executed score consumption at PCs $1138/$1176 and instrument initialization at $12B2; base pitch derives from consumed note/transpose at table $1468, while frequency preserves the preceding preparation pitch state. No per-frame register events are stored.',
            'gateClosure': 'Lead/chord gateOffCall is score-owned; bass instrumentGateCloseAge is patch-owned.',
            'sourcePCs': {'scoreNote': 4408, 'scoreGateOff': 4470, 'instrumentInit': 4786,
                          'pitchProgram': 4928, 'waveProgram': 4978, 'pulseUpdate': 4821, 'vibrato': 5060},
            'noteCounts': {name: len(role['notes']) for name, role in roles.items()},
            'originalDriverIncluded': False, 'registerDumpPlayback': False,
        },
        'limits': 'One complete recurring DRAX thematic cycle from initialization, stopping before next-cycle setup. Not Beethoven full-form score coverage or listening acceptance.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sid', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check', action='store_true', help='Verify an existing description without changing it')
    args = parser.parse_args()
    result = describe_score(args.sid.read_bytes())
    if args.check:
        require(json.loads(args.output.read_text()) == result, 'Existing description differs from executed source')
        print(f'Verified complete thematic description: {args.output}')
    else:
        require(not args.output.exists() and not args.output.is_symlink(), 'Choose a fresh output file')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as output:
            json.dump(result, output, indent=2, allow_nan=False)
            output.write('\n')
        print(f'Described complete thematic cycle: {args.output}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, StopIteration) as error:
        raise SystemExit(f'DRAX score description failed: {error}')
