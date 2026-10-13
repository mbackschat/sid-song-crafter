"""Import editable numeric title data from the pinned archive, without driver execution."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_profile import psid_profile
from verify_player import require

SOURCE = ROOT / '.local/research/cybernoid-ii/Cybernoid_II.sid'
PIN = '41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192'
DECODER = ROOT / 'evidence/cybernoid-score-contract/decode.py'
DECODER_PIN = '823c4819f98c9b0dcb69bef1427d86e930f38edf310e72f92fea4631d6b2b880'
INITIAL = ROOT / 'build/cybernoid-global-init/initial-state.json'
INITIAL_PIN = 'acfe0503edba9dcdd015eb88ebe8911dc5f199896b4cd0d408e81cf0afa4151b'
INITIAL_RECEIPT = ROOT / 'build/cybernoid-global-init/receipt.json'
INITIAL_RECEIPT_PIN = 'a89cf5c33a26f8ca583e28cdbe4c979dfa4b4fc9212d5eed25fc171c7b9bc616'
FIELD_NAMES = ('pulse_flags', 'wave', 'attack_decay', 'sustain_release',
               'packed_gate_filter', 'fx1', 'fx2', 'fx3')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def load_decoder():
    require(sha(DECODER.read_bytes()) == DECODER_PIN, 'Independent score decoder pin differs')
    name = 'cybernoid_independent_score_decoder'
    spec = importlib.util.spec_from_file_location(name, DECODER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module.Decoder


def extract_data(play_calls=36000):
    require(type(play_calls) is int and 1 <= play_calls <= 36000,
            'Choose 1..36000 calls within the independently verified score window')
    raw = SOURCE.read_bytes()
    require(sha(raw) == PIN, 'Reference SID pin differs')
    require(sha(INITIAL.read_bytes()) == INITIAL_PIN
            and sha(INITIAL_RECEIPT.read_bytes()) == INITIAL_RECEIPT_PIN, 'Cold initialization proof pin differs')
    profile = psid_profile(raw, profile='pal-banked', subtune=1)
    memory = [0] * 65536
    memory[profile['loadAddress']:profile['endAddress']] = profile['payload']
    mappings = []

    def table(name, address, count):
        require(profile['loadAddress'] <= address and address + count <= profile['endAddress'],
                f'{name} extends beyond the pinned payload')
        values = memory[address:address + count]
        mappings.append(dict(name=name, sourceAddress=address, endExclusive=address + count,
                             bytes=count, sourceBytesSha256=sha(bytes(values))))
        return values

    low = table('frequency.low.byte-index-domain-plus-adjacent', 0xae3f, 257)
    high = table('frequency.high.byte-index-domain-plus-adjacent', 0xae96, 257)
    frequency_words = [lo | hi << 8 for lo, hi in zip(low, high)]
    records_raw = table('records', 0xb014, 19 * 8)
    records = [dict(zip(FIELD_NAMES, records_raw[8 * i:8 * (i + 1)])) for i in range(19)]
    wait = table('vibrato_wait', 0xb0ac, 20)
    lengths = table('onset_lengths', 0xb0c0, 12)
    waves = table('onset_waves', 0xb0cc, 12)
    pulse_raw = table('pulse_slots', 0xaff4, 32)
    pulse_slots = [pulse_raw[8 * i:8 * (i + 1)] for i in range(4)]

    def pointer(address):
        return memory[address] | memory[address + 1] << 8

    filter_pointers = [pointer(0xafc4 + i * 2) for i in range(4)]
    require(filter_pointers == [0xafcc, 0xafd6, 0xafe0, 0xafea], 'Filter extent/pointers differ')
    filter_programs = [table(f'filter_programs.{i}', address, 10) for i, address in enumerate(filter_pointers)]
    arp_pointers = [memory[0xaf7f + i] | memory[0xaf87 + i] << 8 for i in range(8)]
    require(arp_pointers == [0xaf8f, 0xaf93, 0xaf97, 0xaf9b, 0xaf9f, 0xafa3, 0xafa7, 0xafc0],
            'Arpeggio extent/pointers differ')
    arpeggios = []
    for i, address in enumerate(arp_pointers):
        end = arp_pointers[i + 1] if i < 7 else 0xafc4
        values = table(f'arpeggios.{i}', address, end - address)
        require(len(values) == values[0] + 2, 'Arpeggio header does not cover its complete offset vector')
        arpeggios.append(values)
    drum_pointers = [(pointer(0xaf45 + i * 4), pointer(0xaf47 + i * 4)) for i in range(2)]
    require(drum_pointers == [(0xaf4d, 0xaf5a), (0xaf66, 0xaf73)], 'Drum extent/pointers differ')
    drums = [dict(waves=table(f'drums.{i}.waves', a, 13),
                  pitch_values=table(f'drums.{i}.pitch_values', b, 12)) for i, (a, b) in enumerate(drum_pointers)]
    require(all(d['waves'][0] == 11 for d in drums), 'Declared drum program lengths differ')

    decoder = load_decoder()(memory)
    decoder.expand(play_calls)
    rows = []
    for original in decoder.rows:
        note = next(c for c in original['commands'] if c['kind'] == 'note')
        transpose = (original['pitchIndex'] - note['rawIndex']) & 255
        commands = []
        for command in original['commands']:
            kind = command['kind']
            if kind == 'note':
                commands.append(dict(kind=kind, sourceNote=command['rawIndex']))
            elif kind == 'glide':
                commands.append(dict(kind=kind, control=command['control'],
                                     targetNote=(command['targetIndex'] - transpose) & 255))
            else:
                commands.append({key: value for key, value in command.items() if key not in ('origin', 'origins')})
        require(original['soundIndex'] < len(records), 'Score selects a sound outside the decoded bank')
        require(original['arpeggioIndex'] is None or original['arpeggioIndex'] < len(arpeggios),
                'Score selects an arpeggio outside its decoded bank')
        rows.append(dict(call=original['call'], voiceIndex=original['voiceIndex'], transpose=transpose,
                         patchSetup=original['patchSetup'], commands=commands,
                         sourceEvidence={key: value for key, value in original.items() if key not in ('commands', 'call', 'voiceIndex', 'patchSetup')},
                         ))
        rows[-1]['sourceEvidence']['commandOrigins'] = [
            dict(kind=c['kind'], origins=c.get('origins', [c['origin']] if 'origin' in c else []))
            for c in original['commands']]
    initial = json.loads(INITIAL.read_bytes())
    require(all(v['sound_index'] == 0 and v['arpeggio_index'] is None for v in initial['voices']),
            'Initial program selections differ')
    require(initial['globals']['tempo_reload'] == 2, 'Title cadence differs')
    sid_init = {name: initial['initial_sid'][name] for name in ('cutoff_high', 'routing', 'mode_volume')}
    state_fields = ('caller', 'pitch', 'sound_index', 'arpeggio_index')
    initial_state = dict(globals=initial['globals'],
                         voices=[{name: voice[name] for name in state_fields} for voice in initial['voices']])
    initial_annotations = {key: value for key, value in initial.items() if key not in ('globals', 'voices')}
    initial_annotations['voices'] = [
        {key: value for key, value in voice.items() if key not in state_fields} for voice in initial['voices']]
    lookup_uses = sorted({r['pitchIndex'] for r in decoder.rows}
                         | {c['targetIndex'] for r in decoder.rows for c in r['commands'] if c['kind'] == 'glide'})
    return dict(format='cybernoid-editable-title-v1', play_calls=play_calls,
                frequency_words=frequency_words, records=records, vibrato_wait=wait,
                onset_lengths=lengths, onset_waves=waves, pulse_slots=pulse_slots,
                filter_programs=filter_programs, arpeggios=arpeggios, drums=drums,
                rows=rows, initial_state=initial_state, sid_init=sid_init,
                sourceEvidence=dict(source=fingerprint(SOURCE),
                                    sourceUrl='https://www.hvsc.de/download/C64Music/MUSICIANS/T/Tel_Jeroen/Cybernoid_II.sid',
                                    selectedSubtune=1, profile='pal-banked',
                                    extractor=fingerprint(Path(__file__)), scoreDecoder=fingerprint(DECODER),
                                    initialState=fingerprint(INITIAL), initializationProof=fingerprint(INITIAL_RECEIPT),
                                    initializationAnnotations=initial_annotations,
                                    sharedDependencies={name: fingerprint(ROOT / 'scripts' / name)
                                                        for name in ('psid_profile.py', 'verify_player.py')},
                                    tables=mappings, declaredChromaticFrequencyCount=87,
                                    frequencyDomain='0..255 ordinary byte-index lookups; slot256 only for shifted-base adjacent lookup. Values87..256 derive from adjacent source data and are opaque lookup words, not inferred chromatic notes.',
                                    score='Runtime rows are expanded by the pinned independent score Decoder using static source bytes only. No captured event/state/register ledger is read by this extractor.',
                                    noteIndexUses=lookup_uses,
                                    coldInitialization='Named source-free post-init state. Only cold state is imported; warm re-init differs for voice2 pulse-output high.',
                                    sidInitialization='Three editable setup values followed by the known D415..D400 descending zero-clear operation. Main model generates this operation; no captured init-write ledger is supplied.',
                                    schedulingTradeoff='Row calls are independently generated absolute positions at tempo2/one row decrement per3calls. Editing a note/patch/action changes runtime behavior directly; changing durations requires regenerating later row calls, since this prepared data does not retain a runtime pattern/order scheduler.',
                                    tableExtentPolicy='Declared complete fixed table extents retained, including unused arp/drum entries. Helper/even-F score edges remain rejected by the source decoder. Source RAM addresses appear only in annotations.',
                                    limits='Numeric editable data and score, not a driver or register replay. Main model must join caller/macro ordering and prove its own outputs; no complete synthesis, original IRQ-host, SID physical-state, PCM or listening claim.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--play-calls', type=int, default=36000)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.output.is_symlink(), 'Choose a fresh output')
    data = extract_data(args.play_calls)
    with args.output.open('x') as stream:
        json.dump(data, stream, separators=(',', ':'))
        stream.write('\n')
    print(json.dumps(dict(path=str(args.output), bytes=args.output.stat().st_size,
                          sha256=sha(args.output.read_bytes()), rows=len(data['rows']), playCalls=data['play_calls'])))
