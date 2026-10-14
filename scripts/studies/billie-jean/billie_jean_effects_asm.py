"""Generate independent Billie Jean sound routines and immutable numeric tables.

The bj_ ABI uses three-byte arrays for VoiceState fields, splitting pulse and
frequency into _lo/_hi arrays, plus bj_filter_cutoff/mode/routing scalars.
Score owns base_note, remaining, hold, instrument_offset and bj_divider;
sound owns the other voice fields, including gate_mask and mutable glide_step.
The caller applies row setters and restores the cold image. It calls
bj_note_setup or bj_body, then bj_advance_age for voices 2, 1 and 0, and
bj_global_output last. Setup/body already emit all their SID stores.

Each callable entry preserves X and the stack, clobbering A/Y/flags and
sound scratch at $E0–$EF; scheduler scratch $D0–$DF is untouched.
bj_sound_failed reports a bounded pitch-table loop failure, which the caller
must check before continuing. Generation takes admitted numeric dataclasses,
without an original SID, executable source payload, init routine or scheduler.
"""

from collections.abc import Mapping, Sequence
from dataclasses import fields

import billie_jean_programs as sound


def field_labels(state_type, prefix, words=()):
    return {item.name: ((prefix + item.name + '_lo', prefix + item.name + '_hi') if item.name in words else
                       (prefix + item.name,)) for item in fields(state_type)}


VOICE_FIELD_LABELS = field_labels(sound.VoiceState, 'bj_', sound.WORD_FIELDS)
FILTER_FIELD_LABELS = field_labels(sound.FilterState, 'bj_filter_')
STATE_STORAGE = (tuple((label, 3) for labels in VOICE_FIELD_LABELS.values() for label in labels)
                 + tuple((label, 1) for labels in FILTER_FIELD_LABELS.values() for label in labels))
SCRATCH_STORAGE = tuple((label, 1) for label in
    ('bj_sound_failed', 'bj_pitch_changed', 'bj_filter_bypass', 'bj_table_hops'))


def sound_state_values(voices, shared):
    sound.require(len(voices) == 3, 'Sound state requires three voices')
    for state in voices:
        sound.validate_state(state, sound.VoiceState, sound.WORD_FIELDS)
    sound.validate_state(shared, sound.FilterState)
    values = {label: [(getattr(state, name) >> (8 * half)) & 255 for state in voices]
              for name, labels in VOICE_FIELD_LABELS.items() for half, label in enumerate(labels)}
    values.update({label: [getattr(shared, name)] for name, labels in FILTER_FIELD_LABELS.items() for label in labels})
    return values


def read_state(memory, symbols, labels, state_type, voice):
    ram = memory.data if hasattr(memory, 'data') else memory
    return state_type(**{name: sum(ram[symbols[label] + voice] << (8 * half) for half, label in enumerate(parts))
                         for name, parts in labels.items()})


def read_voice(memory, symbols, voice):
    sound.unsigned(voice, 2, 'Voice index')
    return read_state(memory, symbols, VOICE_FIELD_LABELS, sound.VoiceState, voice)


def read_filter(memory, symbols):
    return read_state(memory, symbols, FILTER_FIELD_LABELS, sound.FilterState, 0)


def declarations(values):
    result = ''
    for label, items in values.items():
        sound.require(bool(items), f'{label} requires data')
        for value in items:
            sound.unsigned(value, 255, label)
        result += label + ':\n  .byte ' + ','.join(f'${value:02x}' for value in items) + '\n'
    return result


def generate(instruments, bank):
    """Return callable routines and immutable tables; mutable storage is separate."""
    sound.require(isinstance(instruments, Mapping) and instruments, 'Expected an instrument mapping')
    sound.require(isinstance(bank, sound.Programs), 'Expected Programs')
    for index, instrument in instruments.items():
        sound.unsigned(index, 255, 'Instrument offset')
        sound.validate_inputs(sound.VoiceState(), sound.FilterState(), instrument, 0)
    values = {'bj_sid_offsets': [0, 7, 14]}
    for item in fields(sound.Instrument):
        values['bj_i_' + item.name] = [getattr(instruments[index], item.name) if index in instruments else 0 for index in range(256)]
    sound.require(isinstance(bank.frequencies, Mapping), 'Expected a numeric frequency mapping')
    for index, word in bank.frequencies.items():
        sound.unsigned(index, 127, 'Normalized frequency index')
        sound.unsigned(word, 65535, 'Frequency word')
    values['bj_frequency_table_lo'] = [bank.frequencies.get(index, 0) & 255 for index in range(128)]
    values['bj_frequency_table_hi'] = [bank.frequencies.get(index, 0) >> 8 for index in range(128)]
    for name, items, size in (('pitch_bank', bank.pitches, 256), ('waveform_bank', bank.waveforms, 256),
                              ('routing_set', bank.routing_set, 3), ('routing_clear', bank.routing_clear, 3)):
        sound.require(isinstance(items, Sequence) and len(items) == size, f'{name} requires {size} bytes')
        values['bj_' + name] = list(items)
    return ROUTINES + declarations(values)


ROUTINES = """
bj_note_setup:
  CLD
  LDA #$00
  STA bj_sound_failed
  LDY bj_instrument_offset,X
  LDA bj_i_vibrato_seed,Y
  STA bj_vibrato_phase,X
  LDA bj_gate_mask,X
  AND #$01
  BNE bj_setup_legato
  LDA bj_i_attack_decay,Y
  STA $e4
  LDA bj_i_sustain_release,Y
  STA $e5
  LDY bj_sid_offsets,X
  LDA #$00
  STA $d404,Y
  LDA $e4
  STA $d405,Y
  LDA $e5
  STA $d406,Y
  LDA #$09
  STA $d404,Y
  LDA #$ff
  STA bj_gate_mask,X
  LDY bj_instrument_offset,X
  LDA bj_i_pulse_initial,Y
  STA bj_pulse_lo,X
  STA bj_pulse_hi,X
  LDA bj_i_filter_initialize,Y
  BEQ bj_setup_reset
  LDA bj_i_filter_start,Y
  STA bj_filter_cutoff
bj_setup_reset:
  LDA #$00
  STA bj_wave_cursor,X
  STA bj_age,X
  RTS
bj_setup_legato:
  LDA bj_base_note,X
  JSR bj_lookup_frequency
  JMP bj_voice_output

bj_body:
  CLD
  LDA #$00
  STA bj_sound_failed
  STA bj_filter_bypass
  JSR bj_step_pulse
  JSR bj_step_pitch
  LDA bj_sound_failed
  BNE bj_body_done
  LDA bj_pitch_changed
  BNE bj_body_filter
  LDA bj_age,X
  BEQ bj_body_filter
  LDA bj_glide_step,X
  BEQ bj_body_vibrato
  JSR bj_step_glide
  LDA bj_filter_bypass
  BNE bj_body_writer
  JMP bj_body_filter
bj_body_vibrato:
  JSR bj_step_vibrato
bj_body_filter:
  JSR bj_step_filter
  JSR bj_late_gate
bj_body_writer:
  JMP bj_voice_output
bj_body_done:
  RTS

bj_step_pulse:
  LDY bj_instrument_offset,X
  LDA bj_pulse_direction,X
  BNE bj_pulse_down
  LDA bj_pulse_lo,X
  CLC
  ADC bj_i_pulse_step,Y
  STA bj_pulse_lo,X
  LDA bj_pulse_hi,X
  ADC #$00
  AND #$0f
  STA bj_pulse_hi,X
  CMP bj_i_pulse_upper,Y
  BCC bj_pulse_done
  INC bj_pulse_direction,X
  RTS
bj_pulse_down:
  LDA bj_pulse_lo,X
  SEC
  SBC bj_i_pulse_step,Y
  STA bj_pulse_lo,X
  LDA bj_pulse_hi,X
  SBC #$00
  AND #$0f
  STA bj_pulse_hi,X
  CMP bj_i_pulse_lower,Y
  BCS bj_pulse_done
  DEC bj_pulse_direction,X
bj_pulse_done:
  RTS

bj_step_pitch:
  LDA #$00
  STA bj_table_hops
  STA bj_pitch_changed
bj_pitch_read:
  LDA bj_instrument_offset,X
  CLC
  ADC bj_wave_cursor,X
  TAY
  LDA bj_pitch_bank,Y
  CMP #$7e
  BEQ bj_pitch_done
  CMP #$7f
  BNE bj_pitch_value
  LDY bj_instrument_offset,X
  LDA bj_i_wave_loop,Y
  STA bj_wave_cursor,X
  INC bj_table_hops
  BNE bj_pitch_read
  LDA #$01
  STA bj_sound_failed
  RTS
bj_pitch_value:
  STA $e0
  LDA bj_waveform_bank,Y
  STA bj_waveform,X
  LDA $e0
  BMI bj_pitch_absolute
  CLC
  ADC bj_base_note,X
bj_pitch_absolute:
  JSR bj_lookup_frequency
  INC bj_wave_cursor,X
  LDA #$01
  STA bj_pitch_changed
bj_pitch_done:
  RTS

bj_lookup_frequency:
  AND #$7f
  TAY
  LDA bj_frequency_table_lo,Y
  STA bj_frequency_lo,X
  LDA bj_frequency_table_hi,Y
  STA bj_frequency_hi,X
  RTS

bj_step_glide:
  LDA bj_glide_target,X
  AND #$7f
  TAY
  LDA bj_frequency_table_lo,Y
  STA $e4
  LDA bj_frequency_table_hi,Y
  STA $e5
  LDA bj_glide_target,X
  CMP bj_base_note,X
  BCC bj_glide_down
  LDA bj_frequency_lo,X
  CLC
  ADC bj_glide_step,X
  STA bj_frequency_lo,X
  LDA bj_frequency_hi,X
  ADC #$00
  STA bj_frequency_hi,X
  CMP $e5
  BCC bj_glide_done
  BNE bj_glide_clamp
  LDA bj_frequency_lo,X
  CMP $e4
  BCC bj_glide_done
  BEQ bj_glide_done
  JMP bj_glide_clamp
bj_glide_down:
  LDA bj_frequency_lo,X
  SEC
  SBC bj_glide_step,X
  STA bj_frequency_lo,X
  LDA bj_frequency_hi,X
  SBC #$00
  STA bj_frequency_hi,X
  CMP $e5
  BCC bj_glide_clamp
  BNE bj_glide_down_done
  LDA bj_frequency_lo,X
  CMP $e4
  BCC bj_glide_clamp
  BEQ bj_glide_clamp
bj_glide_down_done:
  LDA #$01
  STA bj_filter_bypass
  RTS
bj_glide_clamp:
  LDA $e4
  STA bj_frequency_lo,X
  LDA $e5
  STA bj_frequency_hi,X
  LDA #$00
  STA bj_glide_step,X
  LDA #$01
  STA bj_filter_bypass
bj_glide_done:
  RTS

bj_step_vibrato:
  LDY bj_instrument_offset,X
  LDA bj_base_note,X
  BMI bj_vibrato_motion
  LDA bj_i_vibrato_delay,Y
  BEQ bj_vibrato_done
  CMP bj_age,X
  BCS bj_vibrato_done
bj_vibrato_motion:
  LDA bj_i_vibrato_half,Y
  CMP bj_vibrato_phase,X
  BCS bj_vibrato_down
  LDA bj_frequency_lo,X
  CLC
  ADC bj_i_vibrato_step,Y
  STA bj_frequency_lo,X
  LDA bj_frequency_hi,X
  ADC #$00
  STA bj_frequency_hi,X
  JMP bj_advance_vibrato_phase
bj_vibrato_down:
  LDA bj_frequency_lo,X
  SEC
  SBC bj_i_vibrato_step,Y
  STA bj_frequency_lo,X
  LDA bj_frequency_hi,X
  SBC #$00
  STA bj_frequency_hi,X
bj_advance_vibrato_phase:
  INC bj_vibrato_phase,X
  LDA bj_i_vibrato_period,Y
  CMP bj_vibrato_phase,X
  BCS bj_vibrato_done
  LDA #$01
  STA bj_vibrato_phase,X
bj_vibrato_done:
  RTS

bj_step_filter:
  LDY bj_instrument_offset,X
  LDA bj_i_filter_enabled,Y
  BEQ bj_filter_clear
  LDA bj_i_filter_mode,Y
  STA bj_filter_mode
  LDA bj_filter_cutoff
  SEC
  SBC bj_i_filter_step,Y
  STA bj_filter_cutoff
  STA $d416
  LDA bj_filter_routing
  ORA bj_routing_set,X
  JMP bj_filter_store
bj_filter_clear:
  LDA bj_filter_routing
  AND bj_routing_clear,X
bj_filter_store:
  STA bj_filter_routing
  STA $d417
  RTS

bj_late_gate:
  LDA bj_remaining,X
  BNE bj_gate_done
  LDA bj_divider
  CMP #$01
  BNE bj_gate_done
  LDA bj_hold,X
  BNE bj_gate_done
  LDA #$fe
  STA bj_gate_mask,X
bj_gate_done:
  RTS

bj_voice_output:
  LDY bj_sid_offsets,X
  LDA bj_waveform,X
  AND bj_gate_mask,X
  STA $d404,Y
  LDA bj_frequency_lo,X
  STA $d400,Y
  LDA bj_frequency_hi,X
  STA $d401,Y
  LDA bj_pulse_lo,X
  STA $d402,Y
  LDA bj_pulse_hi,X
  STA $d403,Y
  RTS

bj_advance_age:
  LDA bj_age,X
  BMI bj_age_done
  INC bj_age,X
bj_age_done:
  RTS

bj_global_output:
  LDA bj_filter_mode
  ORA #$0b
  STA $d418
  RTS
"""
