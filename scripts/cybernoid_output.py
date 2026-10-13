from dataclasses import dataclass
from typing import Optional


def byte(value, name):
    if type(value) is not int or not 0 <= value <= 255:
        raise ValueError(f'{name} must be a byte')


def word(value, name):
    if type(value) is not int or not 0 <= value <= 65535:
        raise ValueError(f'{name} must be a word')


def lookup(values, index, maximum, name):
    if not isinstance(values, (list, tuple)) or not 0 <= index < len(values):
        raise ValueError(f'{name} lacks index {index}')
    value = values[index]
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError(f'{name} value is outside 0..{maximum}')
    return value


@dataclass(frozen=True)
class ArpeggioResult:
    counter: int
    pitch_index: int
    frequency_word: int


def advance_arpeggio(counter, base_pitch, table, frequency_words):
    """Compute the accepted A985..A9BE path; keep the signed decrement and byte index wrap."""
    byte(counter, 'Arpeggio counter')
    byte(base_pitch, 'Base pitch')
    counter = (counter - 1) & 255
    if counter & 128:
        counter = lookup(table, 0, 255, 'Arpeggio table')
    offset = lookup(table, (counter + 1) & 255, 255, 'Arpeggio table')
    pitch_index = (base_pitch + offset) & 255
    return ArpeggioResult(counter, pitch_index, lookup(frequency_words, pitch_index, 65535, 'Frequency table'))


def sweep_high_byte(base_frequency, output_frequency):
    """AC5C..AC65 decrements saved high and replaces output high, preserving both low bytes."""
    word(base_frequency, 'Base frequency')
    word(output_frequency, 'Output frequency')
    high = ((base_frequency >> 8) - 1) & 255
    return (high << 8) | (base_frequency & 255), (high << 8) | (output_frequency & 255)


@dataclass(frozen=True)
class PulseRunResult:
    needs_initialization: int
    low: int
    high: int
    pulse_override: Optional[int]


def advance_pulse_run(active, needs_initialization, low, high, pulse_accumulator_high):
    """ACE2..AD27 resets the flag while inactive, then advances a separate accumulator when active."""
    if type(active) is not bool:
        raise ValueError('Pulse-run active must be boolean')
    for value, name in ((needs_initialization, 'Initialization flag'), (low, 'Pulse-run low'),
                        (high, 'Pulse-run high'), (pulse_accumulator_high, 'PWM accumulator high')):
        byte(value, name)
    if not active:
        return PulseRunResult(1, low, high, None)
    if needs_initialization:
        low, high = 0, pulse_accumulator_high
    total = low + 0x63
    low = total & 255
    if total > 255:
        high = (high + 1) & 255
        if high == 15:
            high ^= 8
    return PulseRunResult(0, low, high, low | high << 8)


@dataclass(frozen=True)
class OutputResult:
    wave: int
    frequency_word: int
    gate_mask: int
    phase: str


def apply_onset(age, length, onset_wave, base_wave, base_frequency, output_wave, output_frequency, gate_mask):
    """Model the accepted ADBD onset path; the restore limit is an ADC byte, not an unbounded sum."""
    for value, name in ((age, 'Age'), (length, 'Onset length'), (onset_wave, 'Onset wave'),
                        (base_wave, 'Base wave'), (output_wave, 'Output wave'), (gate_mask, 'Gate mask')):
        byte(value, name)
    word(base_frequency, 'Base frequency')
    word(output_frequency, 'Output frequency')
    if age < length:
        if onset_wave >= 0x7F:
            return OutputResult(0x81, 0xFA00 | (output_frequency & 255), gate_mask, 'onsetNoise')
        return OutputResult(onset_wave, output_frequency, gate_mask, 'onsetWave')
    if age < ((length + 2) & 255):
        return OutputResult(base_wave, base_frequency, gate_mask, 'restoreBase')
    return OutputResult(output_wave, output_frequency, gate_mask, 'expired')


def apply_drum(age, fx1, pitch_index, waves, pitch_values, frequency_words, output_wave, output_frequency, gate_mask):
    """AD4A..ADBA consumes wave[age], then pitch[age-1] with DEY byte wrap; expiration preserves buffers."""
    for value, name in ((age, 'Age'), (fx1, 'FX1'), (pitch_index, 'Pitch index'),
                        (output_wave, 'Output wave'), (gate_mask, 'Gate mask')):
        byte(value, name)
    word(output_frequency, 'Output frequency')
    length = lookup(waves, 0, 255, 'Drum wave table')
    if age >= length:
        return OutputResult(output_wave, output_frequency, gate_mask, 'expiredDrum')
    wave = lookup(waves, age, 255, 'Drum wave table')
    pitch = lookup(pitch_values, (age - 1) & 255, 255, 'Drum pitch table')
    mask = 255 if wave & 1 else 254
    if fx1 & 0x10:
        index = (pitch_index + pitch) & 255
        frequency = lookup(frequency_words, index, 65535, 'Frequency table')
        return OutputResult(wave, frequency, mask, 'relativeDrum')
    return OutputResult(wave, pitch << 8, mask, 'absoluteDrum')


def apply_wave_program(fx3, age, fx1, pitch_index, waves, pitch_values, frequency_words,
                       length, onset_wave, base_wave, base_frequency, output_wave, output_frequency, gate_mask):
    """Drum bit10 takes precedence over onset bit80, including after the drum age window expires."""
    byte(fx3, 'FX3')
    if fx3 & 0x10:
        return apply_drum(age, fx1, pitch_index, waves, pitch_values, frequency_words,
                          output_wave, output_frequency, gate_mask)
    if fx3 & 0x80:
        return apply_onset(age, length, onset_wave, base_wave, base_frequency,
                           output_wave, output_frequency, gate_mask)
    for value, name in ((output_wave, 'Output wave'), (gate_mask, 'Gate mask')):
        byte(value, name)
    word(output_frequency, 'Output frequency')
    return OutputResult(output_wave, output_frequency, gate_mask, 'disabled')


def voice_writes(voice, wave, gate_mask, frequency, pulse):
    """Return the AE01..AE23 ordered group; note setup and shared-filter stores belong to the caller."""
    if type(voice) is not int or not 0 <= voice <= 2:
        raise ValueError('Voice must be 0..2')
    byte(wave, 'Wave')
    byte(gate_mask, 'Gate mask')
    word(frequency, 'Frequency')
    word(pulse, 'Pulse')
    base = 0xD400 + voice * 7
    return [(base + 4, wave & gate_mask), (base, frequency & 255), (base + 1, frequency >> 8),
            (base + 2, pulse & 255), (base + 3, pulse >> 8)]
