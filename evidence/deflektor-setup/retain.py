"""Retain selected numeric cold state and the pinned Deflektor setup contract."""

import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from psid_profile import psid_profile

SOURCE_SHA = '606ad4cb19e29c060bb77a9b44253dee62d3d972724acb6cddf625fc2466d44d'
source = ROOT / '.local/research/deflektor/Deflektor.sid'
data = source.read_bytes()
assert hashlib.sha256(data).hexdigest() == SOURCE_SHA
profile = psid_profile(data, profile='pal-banked', subtune=1, host_base=0x0400)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def byte(address):
    return profile['payload'][address - profile['loadAddress']]


def cold_byte(address):
    if 0xc0ae <= address <= 0xc104 or 0xc08b <= address <= 0xc093 or address == 0xc0ac:
        return 0
    if address in (0xc006, 0xc0ad):
        return 15
    return byte(address)


FIELDS = {
    'frequency': (0xc095, 7, 2), 'pulse_word': (0xc097, 7, 2), 'control': (0xc099, 7, 1),
    'attack_decay': (0xc09a, 7, 1), 'sustain_release': (0xc09b, 7, 1),
    'remaining': (0xc0b1, 1, 1), 'rest': (0xc0e7, 1, 1), 'release_threshold': (0xc0b7, 1, 1),
    'detune': (0xc0c0, 1, 1), 'pitch_index': (0xc102, 1, 1), 'pwm_interval': (0xc0ba, 1, 1),
    'pwm_base': (0xc0bd, 1, 1), 'pwm_elapsed': (0xc0f0, 1, 1), 'pwm_step': (0xc0f3, 1, 1),
    'pwm_position': (0xc0f6, 1, 1), 'pitch_selector': (0xc0c6, 1, 1), 'pitch_wait': (0xc0c3, 1, 1),
    'pitch_position': (0xc0c9, 1, 1), 'wave_selector': (0xc0cc, 1, 1),
    'wave_countdown': (0xc0d2, 1, 1), 'wave_position': (0xc0cf, 1, 1),
    'score_pitch_selector': (0xc0d5, 1, 1), 'score_pitch_countdown': (0xc0ed, 1, 1),
    'score_pitch_position': (0xc0ea, 1, 1), 'resonance_selector': (0xc0ff, 1, 1),
    'resonance_countdown': (0xc0fc, 1, 1), 'resonance_position': (0xc0f9, 1, 1),
    'glide_wait': (0xc0e1, 1, 1), 'glide_remaining': (0xc0d8, 1, 1), 'glide_flags': (0xc0e4, 1, 1),
    'glide_step': (0xc0db, 1, 2),
}
GLOBALS = {'play_flag': 0xc006, 'cutoff_low': 0xc0aa, 'cutoff_high': 0xc0ab,
           'routing': 0xc0ac, 'mode_volume': 0xc0ad}


def value(field, voice):
    base, stride, size = FIELDS[field]
    address = base + stride * voice
    if field == 'glide_step':
        return cold_byte(address) | cold_byte(0xc0de + voice) << 8
    return cold_byte(address) | (cold_byte(address + 1) << 8 if size == 2 else 0)


cold = dict(globals={name: cold_byte(address) for name, address in GLOBALS.items()},
            voices=[{name: value(name, voice) for name in FIELDS} for voice in range(3)])
initial_path = ROOT / 'evidence/deflektor-form/full40000/initial-state.json'
initial = json.loads(initial_path.read_text())
for voice, row in enumerate(initial['voices']):
    shadow = row['sidShadow']
    assert cold['voices'][voice]['frequency'] == shadow[0] | shadow[1] << 8
    assert cold['voices'][voice]['pulse_word'] == shadow[2] | shadow[3] << 8
    assert [cold['voices'][voice][name] for name in ('control', 'attack_decay', 'sustain_release')] == shadow[4:]
    assert all(value == 0 for name, value in cold['voices'][voice].items()
               if name not in ('frequency', 'pulse_word', 'control', 'attack_decay', 'sustain_release'))
assert cold['globals'] == dict(play_flag=initial['globals']['playFlag'], cutoff_low=initial['globals']['filterCutoffLow'],
    cutoff_high=initial['globals']['filterCutoffHigh'], routing=initial['globals']['filterRouting'], mode_volume=initial['globals']['modeVolume'])
mapping = [byte(address) for address in range(0xc070, 0xc088)]
assert mapping == initial['instrumentMapping']

instruction_path = ROOT / 'evidence/deflektor-form/full40000/instructions.json.gz'
instructions = json.load(gzip.open(instruction_path, 'rt'))
init_stores = []
for row in instructions:
    if row['phase'] != 'init' or row['opcode'] not in (0x8d, 0x9d, 0x85):
        continue
    pc, cpu = row['pc'], row['cpu']
    address = byte(pc + 1) if row['opcode'] == 0x85 else byte(pc + 1) | byte(pc + 2) << 8
    if row['opcode'] == 0x9d:
        address = (address + cpu['x']) & 65535
    init_stores.append(dict(pc=pc, address=address, value=cpu['a']))
assert not any(0xd000 <= row['address'] <= 0xdfff for row in init_stores)
assert {row['address'] for row in init_stores if row['pc'] == 0xc84c} == set(range(0xc0ae, 0xc105))
assert {row['address'] for row in init_stores if row['pc'] == 0xc854} == set(range(0xc08b, 0xc094))
frequency_words = [byte(0xc8cd + i) | byte(0xc92d + i) << 8 for i in range(256)]


def publish(name, value):
    with (HERE / name).open('x') as output:
        json.dump(value, output, indent=2)
        output.write('\n')


publish('cold-state.json', cold)
publish('frequency-words.json', frequency_words)
contract = dict(sourceSha256=SOURCE_SHA, sourceUnchanged=source.read_bytes() == data,
    runtimeColdStateFile='cold-state.json', numericLookupFile='frequency-words.json',
    fieldSourceEvidence={name: dict(baseAddress=base, voiceStride=stride, byteCount=size,
        highAddress=0xc0de if name == 'glide_step' else None) for name, (base, stride, size) in FIELDS.items()},
    globalSourceEvidence=GLOBALS,
    coldInit=dict(locus=[0xc810, 0xc86d], clearInclusiveRanges=[[0xc0ae, 0xc104], [0xc08b, 0xc093]],
        retainedVoiceShadowRange=[0xc095, 0xc0a9], patternPointers='Three C8CC FF stubs',
        mappingDefaults=mapping, sidStores=[],
        retainedSourceOnlyGlobals=dict(currentVoice=2, sidVoiceOffset=14, rowBoundarySkip=0),
        basis='Static selected numeric data plus native explicit init rules; exact loaded shadow/default values and init clear-store addresses checked against retained initialization. No new CPU execution.'),
    instrumentSetup=dict(locus=[0xc3d9, 0xc43c],
        fields=dict(pwmPacked=0, pulseHigh=1, control=2, attackDecay=3, sustainRelease=4, releaseThreshold=5,
                    pwmLowStep=6, delayedPitchSelector=7, waveformSelector=8, contextualResonanceSelector=9),
        operations=['Retain pulse LOW; replace pulse HIGH, control, AD, SR',
            'Replace release threshold and delayed-pitch/wave/resonance selectors and PWM step',
            'pwm_interval=field0&15; pwm_base=field0&240 (unshifted)',
            'pwm_elapsed=(interval-1)&255; pwm_position=0; resonance_position=0',
            'Other counters/positions and frequency remain unchanged until a note initializer'], sidStores=[]),
    noteSetup=dict(locus=[0xc442, 0xc528], frequencyIndex='(sourceNote+transpose+20)&255',
        frequencyLowBase=0xc8cd, frequencyHighBase=0xc92d, lookupDomain=[0, 255], lowHighBaseSeparation=96,
        frequency='(numeric frequency_words[index]+unsigned detune)&65535; update RAM HIGH then LOW',
        order=['Frequency/pitch-index and control|1', 'Consume duration', 'Delayed-pitch initializer if enabled',
               'Waveform initializer if enabled', 'Shared-resonance initializer if enabled',
               'PWM elapsed/position reset ONLY when unshifted pwm_base nonzero', 'Score-pitch initializer if enabled',
               'glide_wait=glide_flags&31', 'remaining=duration'],
        sidStores=[], retained='Rest counter, glide flags/step/length; disabled program counters/positions; PWM phase when base zero',
        lookupBoundary='256 native byte-index lookups include adjacent source numeric data, without guessed chromatic extension.'),
    restSetup=dict(locus=[0xc34b, 0xc365], operations=['rest=remaining=duration', 'Immediate SID control zero for that voice'],
        retained='All frequency/PW/control/envelope shadows and programs; no new-note initializers'),
    scoreEffects=dict(selector90Through95='score_pitch_selector=(token&15)<<3; no phase reset until enabled note initialization',
        bf='Clear only glide_remaining', threeByteGlide='token>=C0: flags=token, wait=token&31, consume low/high step and length; body flag20 subtracts',
        rowEntry='Clear glide_remaining unless FF, before any score commands',
        modeVolumeE8='Next ORDER byte replaces mode_volume shadow at C301; no immediate D418 store'),
    globalRowPreparation=dict(locus=[0xc10c, 0xc139], operations='For each remaining==1: remaining=rest=0 and increment rowBoundarySkip',
        scope='Bodies still decrement row/rest counters; nonzero skip prevents continuing programs. Notes initialize and rest direct stores still occur.',
        writerSuppression='After all voices, nonzero skip resets to0 and returns without any voice/global writer stores'),
    writer=dict(locus=[0xc1e5, 0xc291], order='For voices0,1,2 with rest==0: seven ascending SID voice registers; then D415,D416,D417,D418',
        selectedSongEntryOffset=0, boundary='Alternate entry offsets>=5 suppress voice2 processing/writes; outside selected title'),
    stop=dict(locus=[0xc2e0, 0xc2f2], orderedStores=[[0xd404, 0], [0xd40b, 0], [0xd412, 0]],
        operations='play_flag=0; unwind voice JSR and return immediately; no writer or skip reset',
        observedCall=8480, retainedRowBoundarySkip=3, laterCalls='Immediate C10B return, no SID stores'),
    retainedInitStoreEvidence=init_stores,
    proofScope='Cold/init and setup source contract checked by static native instructions and existing initialized records. Pure player separately verifies complete ordered stores; this is not another complete player or CPU run.',
    inputs={str(path.relative_to(ROOT)): sha(path) for path in (initial_path, instruction_path)},
    tools={name: sha(ROOT / 'scripts' / name) for name in ('psid_profile.py', 'psid_audit.py', 'sid_audit_host.py', 'verify_player.py')},
    scriptSha256=sha(Path(__file__)), artifacts={name: sha(HERE / name) for name in ('cold-state.json', 'frequency-words.json')},
    limits='Loaded SID shadows are numeric software state, not initialization SID writes or known physical chip state. No source SID, whole payload/RAM image, rendered audio or new original CPU traversal is retained.')
publish('contract.json', contract)
print(json.dumps(dict(coldFieldsPerVoice=len(FIELDS), retainedInitStores=len(init_stores), frequencyWords=len(frequency_words),
                     coldState=str(HERE / 'cold-state.json'), contract=str(HERE / 'contract.json'))))
