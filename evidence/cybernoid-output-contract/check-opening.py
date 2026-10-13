from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from model import advance_arpeggio, apply_wave_program, voice_writes


def read(path):
    raw = path.read_bytes()
    decoded = gzip.decompress(raw) if path.suffix == '.gz' else raw
    return json.loads(decoded), hashlib.sha256(decoded).hexdigest()


source = (ROOT / '.local/research/cybernoid-ii/Cybernoid_II.sid').read_bytes()
assert hashlib.sha256(source).hexdigest() == '41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192'
ram = [0] * 65536
ram[0xA600:0xB718] = source[126:]
frequencies = [ram[0xAE3F + index] | ram[0xAE96 + index] << 8 for index in range(256)]
wave_path = ROOT / 'evidence/cybernoid-wave-pwm/mechanisms-verified.json.gz'
arp_path = ROOT / 'evidence/cybernoid-filter-arp/receipt.json.gz'
trace_path = ROOT / 'evidence/cybernoid-title-instructions/opening.trace.json.gz'
wave, wave_sha = read(wave_path)
arp, arp_sha = read(arp_path)
trace, trace_sha = read(trace_path)
assert wave_sha == 'b98f03cd366dc508b1d9715125de5ec8ebf1bd7273952a61e0514a72676792f6'
assert trace_sha == 'a2ac87f2b73424a27145eaef9c3720786f78ee4d4e83b6f4642891068413753e'
current_pitch, pitch_at_wave = {}, {}
for instruction in trace['instructions']:
    address = instruction.get('operandAddress', 0)
    if 0xA63C <= address <= 0xA63E:
        voice = address - 0xA63C
        current_pitch[voice] = instruction['operandValueBefore']
        if instruction['assembly'].startswith('STA '):
            current_pitch[voice] = instruction['a']
    if instruction['pc'] == 0xAD44:
        pitch_at_wave[instruction['tick'], instruction['x']] = current_pitch[instruction['x']]
checks = []
table = arp['arpeggioSelection']['tableBytes']
for event in arp['arpeggioEvents']:
    old_counter = event['instructions'][0]['operandValueBefore']
    predicted = asdict(advance_arpeggio(old_counter, event['basePitchIndex'], table, frequencies))
    expected = dict(counter=event['counterAfter'], pitch_index=event['pitchIndex'],
                    frequency_word=event['lookupFrequencyBytes'][0] | event['lookupFrequencyBytes'][1] << 8)
    assert predicted == expected
    checks.append(dict(component='arpeggio', call=event['call'], expected=expected, predicted=predicted))
writer_count = 0
for event in wave['calls']:
    voice = event['voiceIndex']
    if not event['initializer']:
        before = event['preWaveState']
        record = event['recordId']
        predicted = apply_wave_program(
            0x80 if voice == 0 else 0x10, event['age'], 0, pitch_at_wave[event['call'], voice],
            wave['staticArchiveTables']['drum0Wave']['bytes'],
            wave['staticArchiveTables']['drum0FrequencyHigh']['bytes'], frequencies,
            ram[0xB0C0 + record], ram[0xB0CC + record], before['baseWave'],
            before['baseFrequencyLow'] | before['baseFrequencyHigh'] << 8,
            before['wave'], before['frequencyLow'] | before['frequencyHigh'] << 8, before['gateMask'])
        expected = event['postProgramState']
        assert predicted.wave == expected['wave'] and predicted.gate_mask == expected['gateMask']
        assert predicted.frequency_word == event['frequencyWord']
        checks.append(dict(component='waveProgram', voiceIndex=voice, call=event['call'], result=asdict(predicted)))
    state = event['postProgramState']
    actual = [(trace['instructions'][event['writerTraceIndices'][str(pc)]]['operandAddress'],
               trace['instructions'][event['writerTraceIndices'][str(pc)]]['a'])
              for pc in (0xAE0B, 0xAE11, 0xAE17, 0xAE1D, 0xAE23)]
    assert voice_writes(voice, state['wave'], state['gateMask'], event['frequencyWord'], event['pulseWord']) == actual
    writer_count += len(actual)
result = dict(sourceSha256=hashlib.sha256(source).hexdigest(),
              modelSha256=hashlib.sha256((HERE / 'model.py').read_bytes()).hexdigest(),
              checkerSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              inputs=[dict(path=str(path.relative_to(ROOT)), decodedSha256=digest)
                      for path, digest in ((wave_path, wave_sha), (arp_path, arp_sha), (trace_path, trace_sha))],
              checks=checks, arpeggioBodies=63, waveProgramBodies=124, finalWriterStores=writer_count,
              limits='No new CPU execution. Wave-program checks use retained incoming buffers, separating program arithmetic from preceding pitch/filter/gate routines. Original initializer skips macro age0.')
output = HERE / 'opening-verification-accurate-inputs.json'
with output.open('x') as target:
    json.dump(result, target, indent=2)
    target.write('\n')
print(json.dumps(dict(arpeggioBodies=63, waveProgramBodies=124, finalWriterStores=writer_count,
                     sha256=hashlib.sha256(output.read_bytes()).hexdigest())))
