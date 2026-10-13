"""Retain the verified numeric contract and bounded native instruction loci."""

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_profile import psid_profile
from verify_player import cpu_type
from py65.disassembler import Disassembler

data = (ROOT / '.local/monty-source.sid').read_bytes()
assert hashlib.sha256(data).hexdigest() == '528a7330817e4a0a0f75a505e9fe2444e07c5072ce5383ceaa89f183f0eee3ab'
profile = psid_profile(data, profile='pal-banked', subtune=1)
ram = [0] * 65536
ram[profile['loadAddress']:profile['endAddress']] = profile['payload']
cpu = cpu_type()(memory=ram, pc=0x80ed)
disassembler = Disassembler(cpu)
blocks = []
for name, first, end in (('pitch-and-instrument-setup', 0x80ed, 0x8171), ('scheduled-release', 0x8174, 0x81a3),
        ('vibrato', 0x81a3, 0x8230), ('shared-pwm', 0x8230, 0x8297), ('portamento', 0x8297, 0x82de),
        ('drum', 0x82de, 0x831a), ('saved-high-descent', 0x831a, 0x8336), ('octave-alternation', 0x8336, 0x8367)):
    pc, instructions = first, []
    while pc < end:
        size, assembly = disassembler.instruction_at(pc)
        instructions.append(dict(pc=pc, bytes=bytes(ram[pc:pc + size]).hex(), assembly=assembly))
        pc += size
    assert pc == end
    blocks.append(dict(name=name, firstPC=first, endExclusive=end, instructions=instructions,
        bytesSha256=hashlib.sha256(bytes(ram[first:end])).hexdigest(),
        classification='Pinned static instructions; execution evidence is supplied separately by verification/context receipts'))

result = dict(schemaVersion=1, sourceSha256=hashlib.sha256(data).hexdigest(),
    sourceURL='https://www.hvsc.de/download/C64Music/MUSICIANS/H/Hubbard_Rob/Monty_on_the_Run.sid',
    listing=dict(sha256='52dbbf891b1a1d0f8750842ef91ebaf1fc62d65d7b46497ae6951576ece3ae6c',
        gitBlobSha1='332b81b5ddd21d1ab20c7cd37c32ac786760a267',
        url='https://raw.githubusercontent.com/realdmx/c64_6581_sid_players/f215174fc4c983674808fcd47bc506f96b3d2d04/Hubbard_Rob/Hubbard_Rob_Monty_on_the_Run.asm',
        attribution='Anthony McSweeney disassembly/commenting, dmx87 ACME port',
        role='Interpretation route; actual archive instructions and source execution settle the arithmetic'),
    numericAPI=dict(module='model.py', initializer='initialize_note(state,instrument,*,note=None,frequency_word=None,append=False)->Step',
        body='advance_body(state,instrument,lookups,*,counter,release_check=False)->Step',
        outputs='Immutable VoiceState, immutable replacement Instrument, ordered relative SID offset/value pairs',
        instrumentFields={'pulse_word': 'uint16; native fields0/1, retained shared mutable width', 'waveform': 'uint8 field2',
            'attack_decay': 'uint8 field3', 'sustain_release': 'uint8 field4', 'vibrato_depth': 'uint8 field5',
            'pulse_value': 'uint8 field6; step=value&E0, reload=value&1F', 'effects': 'uint8 field7; masks01/02/04 select drum/descent/octave'},
        voiceAddresses={'note': 0x84d3, 'control': 0x84cd, 'remaining': 0x84ca, 'held_frequency_low': 0x84f2,
            'held_frequency_high': 0x84ef, 'voice_control': 0x84d0, 'pulse_delay': 0x84e5,
            'pulse_direction': 0x84e8, 'portamento': 0x84f5},
        sharedInstrumentBase=0x93b4, counterAddress=0x84fa,
        callerResponsibilities=['Resolve frequency/adjacent/octave words from current numeric tables/state at the proper stages',
            'Install returned shared instrument before processing the next voice',
            'Own row scheduling, portamento setup/reset, cursors and init/body selection',
            'Use this helper only for enabled negative84FD context; positive overlay branch is outside scope',
            'Retain all ordered stores; final word can combine vibrato low and descent high']),
    establishedScope=dict(retainedCalls=[0, 511], actualComponents=1536, actualNoteSetups=17,
        actualAppendSetups=7, actualContinuingBlocks=1512, isolatedCases=11568,
        selectedRecordSyntheticCases=2688, sharedRecordSyntheticCases=192, aliasForkCases=2,
        actualTitleNoteRange=[19, 104], actualTitleSelectedRecords=[0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 14, 15]),
    controls=['Disable only pulse_value: source removes PWM writes and retains non-PW writes in the bounded case',
        'Rawnote104 lookup with prior voice1control41 versus81: source changes only initializer frequency-high store and held word'],
    nativeBlocks=blocks,
    limits='Not a score decoder, complete player, frequency-alias resolver, oscillator/envelope model or reconstruction. Synthetic cases are explicit edited RAM inputs to original blocks, not extra title traversals. No original SID, complete payload/RAM or full third-party listing is exported.',
    hashes={name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in
        ('model.py', 'check.py', 'context.py', 'verification.json', 'context-verification.json', 'records.json', 'context-cases.json.gz')},
    recipeSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
trace = json.load(gzip.open(ROOT / 'build/monty-form/boundary.trace.json.gz', 'rt'))
pc_counts = Counter(row['pc'] for row in trace['instructions'])
result['actualOpeningBodyVisits'] = {name: {'pc': pc, 'visits': pc_counts[pc]} for name, pc in
    (('releaseStores', 0x8190), ('vibratoStores', 0x8227), ('pwmUpdates', 0x8287),
     ('portamentoUpdatesUp', 0x82d0), ('portamentoUpdatesDown', 0x82b2),
     ('drumActive', 0x82ef), ('descentUpdates', 0x832d), ('octaveStores', 0x835e))}
with (HERE / 'contract.json').open('x') as output:
    json.dump(result, output, indent=2)
    output.write('\n')
print(json.dumps({'blocks': len(blocks), 'instructions': sum(len(block['instructions']) for block in blocks),
                  'output': str(HERE / 'contract.json')}))
