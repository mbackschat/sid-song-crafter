from collections import Counter
from dataclasses import asdict
import hashlib
import itertools
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(Path(__file__).resolve().parent), str(ROOT / 'scripts'), str(ROOT / '.tools/test-deps')]
from model import advance_arpeggio, sweep_high_byte, advance_pulse_run, apply_wave_program, voice_writes
from verify_player import cpu_type

SOURCE_SHA = '41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192'


class Memory(list):
    def __init__(self, values):
        super().__init__(values)
        self.sid_writes = []

    def __setitem__(self, address, value):
        if isinstance(address, int) and 0xD400 <= address <= 0xD418:
            self.sid_writes.append((address, value))
        super().__setitem__(address, value)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main(output):
    if output.exists() or output.is_symlink():
        raise ValueError('Use a fresh output JSON path')
    source_path = ROOT / '.local/research/cybernoid-ii/Cybernoid_II.sid'
    source = source_path.read_bytes()
    assert sha(source) == SOURCE_SHA
    assert source[124:126] == b'\x00\xa6'
    original = [0] * 65536
    original[0xA600:0xB718] = source[126:]
    cpu_class = cpu_type()
    cases, counts = [], Counter()
    coverage = Counter()

    def execute(component, entry, stop, voice, changes, allowed):
        ram = Memory(original)
        ram[0x48], ram[0x49] = voice, voice * 7
        for address, value in changes.items():
            ram[address] = value
        cpu = cpu_class(memory=ram, pc=entry)
        cpu.x = voice
        cpu.p = cpu.UNUSED | cpu.INTERRUPT
        pcs = []
        while cpu.pc != stop:
            assert any(first <= cpu.pc < last for first, last in allowed), (component, hex(cpu.pc))
            assert len(pcs) < 500, component
            pcs.append(cpu.pc)
            coverage[component, cpu.pc] += 1
            cpu.step()
        assert cpu.x == voice and cpu.sp == 255
        return ram, pcs

    def frequency_words(ram):
        return [ram[0xAE3F + index] | ram[0xAE96 + index] << 8 for index in range(256)]

    def record(component, inputs, expected, predicted, pcs):
        assert predicted == expected, (component, inputs, predicted, expected)
        cases.append(dict(component=component, inputs=inputs, expected=expected, predicted=predicted,
                          executedInstructions=len(pcs)))
        counts[component] += 1

    arp_tables = [[2, 0, 5, 8] + [0] * 252,
                  [(index * 3 + 5) & 255 for index in range(256)],
                  [255] + [(index * 7) & 255 for index in range(1, 256)]]
    for voice, program, counter, base in itertools.product(range(3), range(3), (0, 1, 2, 127, 128, 129, 255), (0, 12, 80, 128, 255)):
        table = arp_tables[program]
        changes = {0xA670 + voice: 0, 0xA673 + voice: 0x70, 0xA66D + voice: counter,
                   0xA63F + voice: base, 0xA64B + voice: 0xEF, 0xA645 + voice: 0xBE}
        changes.update({0x7000 + index: value for index, value in enumerate(table)})
        ram, pcs = execute('arpeggio', 0xA985, 0xA9C1, voice, changes, [(0xA985, 0xA9C1)])
        expected = dict(counter=ram[0xA66D + voice], pitch_index=ram[0xA63C + voice],
                        frequency_word=ram[0xA693 + voice] | ram[0xA696 + voice] << 8)
        predicted = asdict(advance_arpeggio(counter, base, table, frequency_words(ram)))
        assert ram[0xA63F + voice] == base and (ram[0xA64B + voice], ram[0xA645 + voice]) == (0xEF, 0xBE)
        assert not ram.sid_writes
        record('arpeggio', dict(voice=voice, program=program, counter=counter, base=base), expected, predicted, pcs)

    for voice, base, output_word in itertools.product(range(3), (0, 0x00EF, 0x0100, 0x1234, 0xFFFF), (0, 0xFACF, 0xFFFF, 0x1234)):
        changes = {0xA64B + voice: base & 255, 0xA645 + voice: base >> 8,
                   0xA693 + voice: output_word & 255, 0xA696 + voice: output_word >> 8}
        ram, pcs = execute('sweep', 0xAC5A, 0xAC68, voice, changes, [(0xAC5A, 0xAC68)])
        expected = [ram[0xA64B + voice] | ram[0xA645 + voice] << 8,
                    ram[0xA693 + voice] | ram[0xA696 + voice] << 8]
        assert not ram.sid_writes
        record('sweep', dict(voice=voice, base=base, output=output_word), expected, list(sweep_high_byte(base, output_word)), pcs)

    for voice, active, flag, low, high, pulse_high in itertools.product(
            range(3), (False, True), (0, 1, 255), (0, 156, 157, 255), (7, 14, 15, 255), (0, 8, 255)):
        changes = {0x42: 2 if active else 0, 0xA69F + voice: flag, 0xA6A2 + voice: low,
                   0xA6A5 + voice: high, 0xA657 + voice: pulse_high,
                   0xA6AB + voice: 0xCD, 0xA6AE + voice: 0xAB}
        ram, pcs = execute('pulseRun', 0xACE2, 0xAD2A, voice, changes, [(0xACE2, 0xAD2A)])
        override = ram[0xA6AB + voice] | ram[0xA6AE + voice] << 8 if active else None
        expected = dict(needs_initialization=ram[0xA69F + voice], low=ram[0xA6A2 + voice],
                        high=ram[0xA6A5 + voice], pulse_override=override)
        assert ram[0xA657 + voice] == pulse_high and not ram.sid_writes
        if not active:
            assert (ram[0xA6AB + voice], ram[0xA6AE + voice]) == (0xCD, 0xAB)
        record('pulseRun', dict(voice=voice, active=active, flag=flag, low=low, high=high, pulse_high=pulse_high),
               expected, asdict(advance_pulse_run(active, flag, low, high, pulse_high)), pcs)

    def waveform_case(component, voice, fx3, age, length, onset_wave, fx1, pitch, drum_length):
        waves = [drum_length] + [((index * 13) ^ 0x81) & 255 for index in range(1, 256)]
        pitch_values = [(index * 17 + 4) & 255 for index in range(256)]
        selector = fx1 & 15
        changes = {0x40: fx1, 0x42: fx3, 0xA642 + voice: 0, 0xA65E + voice: age,
                   0xA63C + voice: pitch, 0xA639 + voice: 0x41,
                   0xA64B + voice: 0xEF, 0xA645 + voice: 0xBE,
                   0xA693 + voice: 0xCF, 0xA696 + voice: 0x12,
                   0xA687 + voice: 0x21, 0xA69C + voice: 0x55,
                   0xB0C0: length, 0xB0CC: onset_wave,
                   0xAF45 + selector * 4: 0, 0xAF46 + selector * 4: 0x70,
                   0xAF47 + selector * 4: 0, 0xAF48 + selector * 4: 0x71}
        changes.update({0x7000 + index: value for index, value in enumerate(waves)})
        changes.update({0x7100 + index: value for index, value in enumerate(pitch_values)})
        ram, pcs = execute(component, 0xAD44, 0xAE01, voice, changes, [(0xAD44, 0xAE01), (0xAE2D, 0xAE3F)])
        if 0xAD4A in pcs:
            phase = 'relativeDrum' if 0xADA1 in pcs else 'absoluteDrum' if 0xADAD in pcs else 'expiredDrum'
        elif 0xADCE in pcs:
            phase = 'onsetNoise' if 0xADD5 in pcs else 'onsetWave'
        elif 0xADEF in pcs:
            phase = 'restoreBase'
        else:
            phase = 'expired' if 0xADC3 in pcs else 'disabled'
        expected = dict(wave=ram[0xA687 + voice], frequency_word=ram[0xA693 + voice] | ram[0xA696 + voice] << 8,
                        gate_mask=ram[0xA69C + voice], phase=phase)
        predicted = asdict(apply_wave_program(fx3, age, fx1, pitch, waves, pitch_values, frequency_words(ram),
                                             length, onset_wave, 0x41, 0xBEEF, 0x21, 0x12CF, 0x55))
        assert ram[0xA63C + voice] == pitch and not ram.sid_writes
        record(component, dict(voice=voice, fx3=fx3, age=age, length=length, onset_wave=onset_wave,
                               fx1=fx1, pitch=pitch, drum_length=drum_length), expected, predicted, pcs)

    for voice, length, onset, age in itertools.product(range(3), (0, 1, 2, 253, 254, 255), (0, 0x41, 0x7F, 0x81), (0, 1, 2, 3, 10, 253, 254, 255)):
        waveform_case('onset', voice, 0x80, age, length, onset, 0, 12, 11)
    for voice, age in itertools.product(range(3), (0, 1, 2, 3, 10, 253, 254, 255)):
        waveform_case('disabled', voice, 0, age, 2, 0x81, 0, 12, 11)
    for voice, fx3, length, age, fx1, pitch in itertools.product(
            range(3), (0x10, 0x90), (0, 11, 255), (0, 1, 2, 10, 11, 255), (0, 1, 0x10, 0x11), (0, 12, 255)):
        waveform_case('drum', voice, fx3, age, 2, 0x81, fx1, pitch, length)

    for voice, wave, mask, frequency, pulse in itertools.product(range(3), (0, 0x11, 0x41, 0x81, 0xFF),
                                                               (0, 0xFE, 0xFF), (0, 0x1234, 0xFFFF), (0, 0x0800, 0xFFFF)):
        changes = {0xA687 + voice: wave, 0xA69C + voice: mask,
                   0xA693 + voice: frequency & 255, 0xA696 + voice: frequency >> 8,
                   0xA6AB + voice: pulse & 255, 0xA6AE + voice: pulse >> 8}
        ram, pcs = execute('writer', 0xAE01, 0xAE26, voice, changes, [(0xAE01, 0xAE26)])
        expected = [list(write) for write in ram.sid_writes]
        record('writer', dict(voice=voice, wave=wave, mask=mask, frequency=frequency, pulse=pulse),
               expected, [list(write) for write in voice_writes(voice, wave, mask, frequency, pulse)], pcs)

    assert source_path.read_bytes() == source
    census_path = ROOT / 'build/cybernoid-title-mechanism-coverage/coverage.json'
    census = json.loads(census_path.read_bytes())
    actual = Counter()
    for group in census['mechanisms']:
        actual[group['mechanism']] += group['visits']
    result = dict(schemaVersion=1, sourceSha256=SOURCE_SHA, sourceFileUnchanged=True,
                  modelSha256=sha((Path(__file__).with_name('model.py')).read_bytes()),
                  checkerSha256=sha(Path(__file__).read_bytes()), verifierSha256=sha((ROOT / 'scripts/verify_player.py').read_bytes()),
                  syntheticCaseCounts=dict(counts), syntheticCases=cases,
                  arithmeticParameters=dict(arpeggioTables=arp_tables,
                    drumWaveRecipe='wave[0]=drum_length; wave[i]=((i*13)^0x81)&255 for1..255',
                    drumPitchRecipe='pitch[i]=(i*17+4)&255 for0..255',
                    frequencyLookupRecipe='frequency_words[i]=RAM[AE3F+i]|RAM[AE96+i]<<8 after explicit case data replacements; native8-bit indexed lookups, not a claim every index denotes a musical note'),
                  originalExecutionBounds=dict(arpeggio=[0xA985, 0xA9C1], sweep=[0xAC5A, 0xAC68],
                      pulseRun=[0xACE2, 0xAD2A], waveProgram=[0xAD44, 0xAE01], relativeLookup=[0xAE2D, 0xAE3F], writer=[0xAE01, 0xAE26]),
                  syntheticInstructionCoverage=[dict(component=name, pc=pc, visits=count) for (name, pc), count in sorted(coverage.items())],
                  actualTitleCoverage=dict(censusPath=str(census_path.relative_to(ROOT)), censusSha256=sha(census_path.read_bytes()),
                      scope=census['scope'], hooks={name: actual[name] for name in ('toneArpeggio', 'highByteSweep', 'pulseRunActive', 'pulseRunInitialize', 'pulseRunHighWrap', 'onsetWaveConsume', 'onsetNoiseHighOverride', 'onsetBaseRestore', 'drumWaveConsume', 'drumRelativePitch', 'drumAbsolutePitch')}),
                  contracts=dict(macroOrder=['tone arpeggio', 'vibrato/glide (separate pitch contract)', 'PWM', 'high-byte sweep', 'shared filter', 'pulse-run output override', 'packed field4 frequency addition', 'drum or onset', 'final writer'],
                      state=dict(arpeggio='A66D counter; A63C current pitch; A693/A696 output frequency; saved base frequency untouched',
                      sweep='A645 saved high and A696 output high; both low bytes untouched',
                      pulseRun='A69F initialization flag; A6A2/A6A5 independent accumulator; only A6AB/A6AE output pulse replaced',
                      waveProgram='A687 wave; A693/A696 output frequency; A69C gate mask; current pitch byte unchanged',
                      writer='No working-state mutation before AE26; five SID stores control/frequency-low/frequency-high/pulse-low/pulse-high'),
                      caller='Caller owns flag eligibility, note initializer skip, table selection, per-voice named state, shared-filter ownership and execution in voice order2,1,0. Output helpers do not overwrite saved frequency except the explicit sweep helper.'),
                  limits=['Isolated original instructions execute against explicit synthetic RAM/parameters with decimal clear, bounded PCs/steps and all three voice indexes. This is not a production auditor or full-machine host.',
                          'Synthetic age0 drum consumes length as waveform and pitch255 after DEY; actual patch initializer skips macro age0. Relative drum and unusual table/length/counter edges are synthetic, not claimed title usage.',
                          'No full-title rerun, note decoder, original IRQ cadence, call-cycle budget, SID oscillator/envelope state, PCM or listening claim. Model receives editable numeric tables and has no original-source dependency.'])
    with output.open('x') as target:
        json.dump(result, target, indent=2)
        target.write('\n')
    print(json.dumps(dict(output=str(output), sha256=sha(output.read_bytes()), caseCounts=dict(counts), totalCases=len(cases))), flush=True)


if __name__ == '__main__':
    main(Path(__file__).with_name('verification.json'))
