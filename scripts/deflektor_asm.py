"""Independent 6502 implementation of the verified Deflektor numeric contract."""

from sid_assembler import BRANCHES


def long_branches(source):
    """Keep generated table sizes from changing conditional branch admission."""
    inverse = dict(BCC='BCS', BCS='BCC', BEQ='BNE', BNE='BEQ', BMI='BPL', BPL='BMI',
                   BVC='BVS', BVS='BVC')
    lines = []
    for line in source.splitlines():
        parts = line.strip().split(None, 1)
        if parts and parts[0] in BRANCHES:
            label = f'df_long_branch_{len(lines)}'
            lines.extend((f'  {inverse[parts[0]]} {label}', f'  JMP {parts[1]}', label + ':'))
        else:
            lines.append(line)
    return '\n'.join(lines) + '\n'


PLAYER = """
entry_init:
  CLD
  JSR df_restore_state
df_init_done:
  RTS
entry_play:
  CLD
  LDA df_play_flag
  BNE df_play_active
  JMP df_call_done
df_play_active:
  LDA #$00
  STA df_skip
  LDX #$00
df_prepare_voice:
  LDA df_remaining,X
  CMP #$01
  BNE df_prepare_next
  LDA #$00
  STA df_remaining,X
  STA df_rest,X
  LDA #$01
  STA df_skip
df_prepare_next:
  INX
  CPX #$03
  BNE df_prepare_voice
  LDX #$00
df_process_voice:
  LDA df_remaining,X
  BEQ df_process_row
  JSR df_body
  JMP df_process_next
df_process_row:
  LDA df_glide_remaining,X
  CMP #$ff
  BEQ df_row_glide_ready
  LDA #$00
  STA df_glide_remaining,X
df_row_glide_ready:
  JSR df_score_row
  LDA df_play_flag
  BEQ df_call_done
df_process_next:
  INX
  CPX #$03
  BNE df_process_voice
  LDA df_skip
  BNE df_call_done
  LDX #$00
df_write_voice:
  LDA df_rest,X
  BNE df_write_next
  LDY df_sid_offsets,X
  LDA df_frequency_lo,X
  STA $d400,Y
  LDA df_frequency_hi,X
  STA $d401,Y
  LDA df_pulse_word_lo,X
  STA $d402,Y
  LDA df_pulse_word_hi,X
  STA $d403,Y
  LDA df_control,X
  STA $d404,Y
  LDA df_attack_decay,X
  STA $d405,Y
  LDA df_sustain_release,X
  STA $d406,Y
df_write_next:
  INX
  CPX #$03
  BNE df_write_voice
  LDA df_cutoff_low
  STA $d415
  LDA df_cutoff_high
  STA $d416
  LDA df_routing
  STA $d417
  LDA df_mode_volume
  STA $d418
df_call_done:
  RTS

df_pattern_read:
  LDA df_pattern_lo,X
  STA $e0
  LDA df_pattern_hi,X
  STA $e1
  LDY df_pattern_cursor,X
  LDA ($e0),Y
  INC df_pattern_cursor,X
  RTS
df_order_read:
  LDA df_order_lo,X
  STA $e0
  LDA df_order_hi,X
  STA $e1
  LDY df_order_cursor,X
  LDA ($e0),Y
  INC df_order_cursor,X
  RTS
df_score_row:
  JSR df_pattern_read
  CMP #$ff
  BEQ df_pattern_end
  CMP #$80
  BCC df_score_note
  CMP #$90
  BCC df_score_instrument
  CMP #$96
  BCC df_score_pitch_effect
  CMP #$a0
  BEQ df_score_rest
  JMP df_failure
df_pattern_end:
  LDA df_repeat_count,X
  BEQ df_order_next
  DEC df_repeat_count,X
  LDA #$00
  STA df_pattern_cursor,X
  JMP df_score_row
df_order_next:
  JSR df_order_read
  CMP #$ff
  BEQ df_stop
  CMP #$80
  BCC df_order_pattern
  STA $e2
  CMP #$e8
  BEQ df_order_volume
  AND #$60
  BEQ df_order_transpose
  CMP #$20
  BEQ df_order_repeat
  CMP #$40
  BEQ df_order_detune
  LDA $e2
  AND #$07
  CLC
  ADC df_mapping_offsets,X
  PHA
  JSR df_order_read
  STA $e3
  PLA
  TAY
  LDA $e3
  STA df_mapping,Y
  JMP df_order_next
df_order_volume:
  JSR df_order_read
  STA df_mode_volume
  JMP df_order_next
df_order_transpose:
  JSR df_order_read
  STA df_transpose,X
  JMP df_order_next
df_order_repeat:
  LDA $e2
  AND #$1f
  SEC
  SBC #$01
  STA df_repeat_count,X
  JMP df_order_next
df_order_detune:
  JSR df_order_read
  STA df_detune,X
  JMP df_order_next
df_order_pattern:
  TAY
  LDA df_pattern_table_lo,Y
  STA df_pattern_lo,X
  LDA df_pattern_table_hi,Y
  STA df_pattern_hi,X
  LDA #$00
  STA df_pattern_cursor,X
  JMP df_score_row
df_stop:
  LDA #$00
  STA df_play_flag
  STA $d404
  STA $d40b
  STA $d412
  RTS
df_failure:
  LDA #$01
  STA df_failed
  JMP df_stop
df_score_pitch_effect:
  AND #$0f
  ASL A
  ASL A
  ASL A
  STA df_score_pitch_selector,X
  JMP df_score_row
df_score_rest:
  JSR df_pattern_read
  STA df_remaining,X
  STA df_rest,X
  LDA #$00
  LDY df_sid_offsets,X
  STA $d404,Y
  RTS
df_score_instrument:
  AND #$0f
  CLC
  ADC df_mapping_offsets,X
  TAY
  LDA df_mapping,Y
  TAY
  LDA df_record_0,Y
  AND #$0f
  STA df_pwm_interval,X
  SEC
  SBC #$01
  STA df_pwm_elapsed,X
  LDA df_record_0,Y
  AND #$f0
  STA df_pwm_base,X
  LDA df_record_1,Y
  STA df_pulse_word_hi,X
  LDA df_record_2,Y
  STA df_control,X
  LDA df_record_3,Y
  STA df_attack_decay,X
  LDA df_record_4,Y
  STA df_sustain_release,X
  LDA df_record_5,Y
  STA df_release_threshold,X
  LDA df_record_6,Y
  STA df_pwm_step,X
  LDA df_record_7,Y
  STA df_pitch_selector,X
  LDA df_record_8,Y
  STA df_wave_selector,X
  LDA df_record_resonance,Y
  STA df_resonance_selector,X
  LDA #$00
  STA df_pwm_position,X
  STA df_resonance_position,X
  JMP df_score_row
df_score_note:
  CLC
  ADC df_transpose,X
  CLC
  ADC #$14
  STA df_pitch_index,X
  TAY
  JSR df_frequency_lookup
  JSR df_pattern_read
  STA df_remaining,X
  LDA df_control,X
  ORA #$01
  STA df_control,X
  LDY df_pitch_selector,X
  BEQ df_note_wave
  LDA df_motion++24,Y
  STA df_pitch_wait,X
  LDA #$01
  STA df_pitch_position,X
df_note_wave:
  LDY df_wave_selector,X
  BEQ df_note_resonance
  JSR df_wave_pointer
  LDY #$02
  LDA ($e0),Y
  ORA #$01
  STA df_control,X
  INY
  LDA ($e0),Y
  CLC
  ADC #$01
  STA df_wave_countdown,X
  LDA #$01
  STA df_wave_position,X
df_note_resonance:
  LDY df_resonance_selector,X
  BEQ df_note_pwm
  LDA df_resonance++1,Y
  PHA
  AND #$0f
  CLC
  ADC #$01
  STA df_resonance_countdown,X
  LDA #$01
  STA df_resonance_position,X
  PLA
  JSR df_resonance_shadow
df_note_pwm:
  LDA df_pwm_base,X
  BEQ df_note_score_pitch
  LDA df_pwm_interval,X
  SEC
  SBC #$01
  STA df_pwm_elapsed,X
  LDA #$00
  STA df_pwm_position,X
df_note_score_pitch:
  LDY df_score_pitch_selector,X
  BEQ df_note_glide
  JSR df_score_pitch_pointer
  LDY #$02
  LDA ($e0),Y
  STA df_score_pitch_countdown,X
  LDA #$01
  STA df_score_pitch_position,X
df_note_glide:
  LDA df_glide_flags,X
  AND #$1f
  STA df_glide_wait,X
  RTS
df_frequency_lookup:
  LDA df_frequency_table_lo,Y
  CLC
  ADC df_detune,X
  STA df_frequency_lo,X
  LDA df_frequency_table_hi,Y
  ADC #$00
  STA df_frequency_hi,X
  RTS

df_body:
  LDA df_remaining,X
  CMP df_release_threshold,X
  BNE df_body_count
  LDA df_control,X
  AND #$fe
  STA df_control,X
df_body_count:
  DEC df_remaining,X
  LDA df_rest,X
  BEQ df_body_skip
  DEC df_rest,X
  RTS
df_body_skip:
  LDA df_skip
  BEQ df_body_glide
  RTS
df_body_glide:
  LDA df_glide_wait,X
  BEQ df_glide_length
  DEC df_glide_wait,X
  JMP df_body_motion
df_glide_length:
  LDA df_glide_remaining,X
  BEQ df_body_motion
  LDA df_glide_flags,X
  AND #$20
  BNE df_glide_subtract
  LDA df_frequency_lo,X
  CLC
  ADC df_glide_step_lo,X
  STA df_frequency_lo,X
  LDA df_frequency_hi,X
  ADC df_glide_step_hi,X
  STA df_frequency_hi,X
  JMP df_glide_decrement
df_glide_subtract:
  LDA df_frequency_lo,X
  SEC
  SBC df_glide_step_lo,X
  STA df_frequency_lo,X
  LDA df_frequency_hi,X
  SBC df_glide_step_hi,X
  STA df_frequency_hi,X
df_glide_decrement:
  LDA df_glide_remaining,X
  CMP #$ff
  BEQ df_body_motion
  DEC df_glide_remaining,X
df_body_motion:
  JSR df_pwm
  JSR df_pitch
  JSR df_wave
  JSR df_score_pitch
  JMP df_resonance_step

df_pwm:
  LDA df_pwm_interval,X
  BNE df_pwm_enabled
  RTS
df_pwm_enabled:
  INC df_pwm_elapsed,X
  LDA df_pwm_elapsed,X
  CMP df_pwm_interval,X
  BNE df_pwm_interpolate
  LDA #$00
  STA df_pwm_elapsed,X
df_pwm_marker:
  LDA df_pwm_position,X
  AND #$7f
  CLC
  ADC df_pwm_base,X
  TAY
  LDA df_motion,Y
  PHA
  AND #$0f
  STA df_pulse_word_hi,X
  LDA #$00
  STA df_pulse_word_lo,X
  PLA
  AND #$f0
  BEQ df_pwm_advance
  CMP #$10
  BEQ df_pwm_forward_marker
  CMP #$20
  BEQ df_pwm_reverse_marker
  LDA #$00
  STA df_pwm_position,X
  JMP df_pwm_interpolate
df_pwm_forward_marker:
  LDA df_pwm_position,X
  BPL df_pwm_advance
  AND #$7f
  CLC
  ADC #$01
  STA df_pwm_position,X
  JMP df_pwm_marker
df_pwm_reverse_marker:
  LDA df_pwm_position,X
  ORA #$80
  SEC
  SBC #$01
  STA df_pwm_position,X
  JMP df_pwm_marker
df_pwm_advance:
  LDA df_pwm_position,X
  BMI df_pwm_backwards
  INC df_pwm_position,X
  JMP df_pwm_interpolate
df_pwm_backwards:
  DEC df_pwm_position,X
  LDA df_pwm_position,X
  BMI df_pwm_interpolate
  INC df_pwm_position,X
df_pwm_interpolate:
  LDA df_pwm_position,X
  AND #$7f
  CLC
  ADC df_pwm_base,X
  TAY
  LDA df_motion,Y
  AND #$0f
  CMP df_pulse_word_hi,X
  BEQ df_pwm_done
  BCC df_pwm_subtract
  LDA df_pulse_word_lo,X
  CLC
  ADC df_pwm_step,X
  STA df_pulse_word_lo,X
  RTS
df_pwm_subtract:
  LDA df_pulse_word_lo,X
  SEC
  SBC df_pwm_step,X
  STA df_pulse_word_lo,X
df_pwm_done:
  RTS

df_pitch:
  LDA df_pitch_selector,X
  BNE df_pitch_enabled
  RTS
df_pitch_enabled:
  LDA df_pitch_wait,X
  BEQ df_pitch_step
  BMI df_pitch_negative_wait
  DEC df_pitch_wait,X
  RTS
df_pitch_negative_wait:
  CMP #$80
  BNE df_pitch_step
  RTS
df_pitch_step:
  LDA df_pitch_position,X
  AND #$7f
  CLC
  ADC df_pitch_selector,X
  TAY
  LDA df_motion++24,Y
  STA $e8
  LDY #$00
  CMP #$80
  BCC df_pitch_sign
  LDY #$ff
df_pitch_sign:
  STY $e9
  LDA df_pitch_position,X
  BPL df_pitch_add
  LDA #$00
  SEC
  SBC $e8
  STA $e8
  LDA #$00
  SBC $e9
  STA $e9
df_pitch_add:
  LDA df_frequency_lo,X
  CLC
  ADC $e8
  STA df_frequency_lo,X
  LDA df_frequency_hi,X
  ADC $e9
  STA df_frequency_hi,X
  INC df_pitch_position,X
  LDA df_pitch_position,X
  AND #$7f
  CMP #$08
  BNE df_pitch_done
  LDA df_pitch_position,X
  EOR #$89
  STA df_pitch_position,X
  CMP #$01
  BNE df_pitch_done
  LDA df_pitch_wait,X
  BEQ df_pitch_done
  DEC df_pitch_wait,X
df_pitch_done:
  RTS

df_wave_pointer:
  LDA df_wave_table_lo,Y
  STA $e0
  LDA df_wave_table_hi,Y
  STA $e1
  RTS
df_wave:
  LDY df_wave_selector,X
  BNE df_wave_enabled
  RTS
df_wave_enabled:
  DEC df_wave_countdown,X
  BNE df_wave_done
  LDA df_wave_position,X
  BMI df_wave_done
  JSR df_wave_pointer
  LDA df_wave_position,X
  ASL A
  CLC
  ADC #$02
  TAY
  LDA ($e0),Y
  STA $e2
  LDA df_control,X
  AND #$01
  ORA $e2
  STA df_control,X
  INY
  LDA ($e0),Y
  STA df_wave_countdown,X
  INC df_wave_position,X
  LDY #$00
  LDA ($e0),Y
  CMP df_wave_position,X
  BNE df_wave_done
  INY
  LDA ($e0),Y
  BNE df_wave_loop
  LDA #$ff
  JMP df_wave_position_store
df_wave_loop:
  LDA #$00
df_wave_position_store:
  STA df_wave_position,X
df_wave_done:
  RTS

df_score_pitch_pointer:
  LDA df_score_pitch_table_lo,Y
  STA $e0
  LDA df_score_pitch_table_hi,Y
  STA $e1
  RTS
df_score_pitch:
  LDY df_score_pitch_selector,X
  BNE df_score_pitch_enabled
  RTS
df_score_pitch_enabled:
  DEC df_score_pitch_countdown,X
  BNE df_score_pitch_done
  LDA df_score_pitch_position,X
  BPL df_score_pitch_stage
  CMP #$ff
  BNE df_score_pitch_done
  LDA #$fe
  STA df_score_pitch_position,X
  LDY df_pitch_index,X
  JMP df_frequency_lookup
df_score_pitch_stage:
  JSR df_score_pitch_pointer
  LDA df_score_pitch_position,X
  BEQ df_score_pitch_restart
  ASL A
  CLC
  ADC #$02
  TAY
  LDA ($e0),Y
  STA $e2
  INY
  LDA ($e0),Y
  STA df_score_pitch_countdown,X
  JMP df_score_pitch_advance
df_score_pitch_restart:
  LDY #$03
  LDA ($e0),Y
  STA df_score_pitch_countdown,X
  LDA #$00
  STA $e2
df_score_pitch_advance:
  INC df_score_pitch_position,X
  LDY #$00
  LDA ($e0),Y
  CLC
  ADC #$01
  CMP df_score_pitch_position,X
  BNE df_score_pitch_frequency
  INY
  LDA ($e0),Y
  BNE df_score_pitch_loop
  LDA #$ff
  JMP df_score_pitch_position_store
df_score_pitch_loop:
  LDA #$00
df_score_pitch_position_store:
  STA df_score_pitch_position,X
df_score_pitch_frequency:
  LDA df_pitch_index,X
  CLC
  ADC $e2
  TAY
  JMP df_frequency_lookup
df_score_pitch_done:
  RTS

df_resonance_shadow:
  AND #$f0
  STA $e2
  LDA df_routing
  AND #$0f
  ORA $e2
  STA df_routing
  RTS
df_resonance_step:
  LDY df_resonance_selector,X
  BNE df_resonance_enabled
  RTS
df_resonance_enabled:
  DEC df_resonance_countdown,X
  BNE df_resonance_done
  LDA df_resonance_position,X
  BMI df_resonance_done
  CLC
  ADC df_resonance_selector,X
  TAY
  LDA df_resonance++1,Y
  PHA
  AND #$0f
  STA df_resonance_countdown,X
  INC df_resonance_position,X
  LDY df_resonance_selector,X
  LDA df_resonance,Y
  STA $e3
  AND #$07
  CMP df_resonance_position,X
  BNE df_resonance_update
  LDA $e3
  BMI df_resonance_loop
  LDA #$ff
  JMP df_resonance_position_store
df_resonance_loop:
  LDA #$00
df_resonance_position_store:
  STA df_resonance_position,X
df_resonance_update:
  PLA
  JMP df_resonance_shadow
df_resonance_done:
  RTS
"""
