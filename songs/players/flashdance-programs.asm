fd_init_voice:
  CLD
  LDY instrument,X
  LDA instrument_wave_row,Y
  STA wave_row,X
  LDA instrument_pwm_row,Y
  STA pulse_row,X
  TAY
  LDA #$00
  STA pulse_remaining,X
  LDA pwm_reset,Y
  BEQ fd_init_voice_done
  LDA pwm_reset_lo,Y
  STA pulse_lo,X
  LDA pwm_reset_hi,Y
  STA pulse_hi,X
fd_init_voice_done:
  RTS

fd_step_pwm:
  CLD
  LDA pulse_remaining,X
  BEQ fd_pulse_read_row
  DEC pulse_remaining,X
  JMP fd_pulse_motion
fd_pulse_read_row:
  LDY pulse_row,X
  LDA pwm_lower,Y
  STA pulse_lower,X
  LDA pwm_upper,Y
  STA pulse_upper,X
  LDA pwm_step,Y
  STA pulse_step,X
  LDA pwm_duration,Y
  STA pulse_remaining,X
  LDA pwm_reset,Y
  BEQ fd_pulse_row_position
  LDA pwm_reset_lo,Y
  STA pulse_lo,X
  LDA pwm_reset_hi,Y
  STA pulse_hi,X
  ; Initialization retains direction until row consumption; see the decoded
  ; initialization contract in docs/research/composition/flashdance-preparation.md.
  LDA #$00
  STA pulse_direction,X
fd_pulse_row_position:
  LDA pwm_hold,Y
  BNE fd_pulse_motion
  INC pulse_row,X
  LDA pulse_row,X
  AND #$3F
  STA pulse_row,X
fd_pulse_motion:
  LDA pulse_direction,X
  BNE fd_pulse_subtract
  LDA pulse_lo,X
  CLC
  ADC pulse_step,X
  STA pulse_lo,X
  LDA pulse_hi,X
  ADC #$00
  STA pulse_hi,X
  CMP pulse_upper,X
  BEQ fd_pulse_reverse
  RTS
fd_pulse_subtract:
  LDA pulse_lo,X
  SEC
  SBC pulse_step,X
  STA pulse_lo,X
  LDA pulse_hi,X
  SBC #$00
  STA pulse_hi,X
  CMP pulse_lower,X
  BNE fd_pulse_done
fd_pulse_reverse:
  LDA pulse_direction,X
  EOR #$01
  STA pulse_direction,X
fd_pulse_done:
  RTS

fd_step_wave:
  CLD
  LDY wave_row,X
  LDA wave_is_jump,Y
  BEQ fd_wave_pitch_mode
  LDA wave_jump,Y
  STA wave_row,X
  TAY
fd_wave_pitch_mode:
  LDA wave_mode,Y
  STA absolute_pitch,X
  BEQ fd_wave_relative
  LDA wave_note,Y
  TAY
  JMP fd_wave_lookup
fd_wave_relative:
  LDA wave_note,Y
  CLC
  ADC base_note,X
  ASL A
  CLC
  ADC transpose,X
  LSR A
  TAY
fd_wave_lookup:
  LDA frequency_table_lo,Y
  CLC
  ADC tuning,X
  STA frequency_lo,X
  LDA frequency_table_hi,Y
  ADC #$00
  STA frequency_hi,X
  LDY wave_row,X
  LDA wave_control_table,Y
  AND gate_mask,X
  STA wave_control,X
  INC wave_row,X
  RTS

fd_init_filter:
  CLD
  LDY instrument,X
  LDA instrument_filter_command,Y
  AND #$0F
  BEQ fd_init_filter_done
  LDA instrument_filter_row,Y
  STA filter_row
  TAY
  LDA #$00
  STA filter_remaining
  LDA filter_reset_table,Y
  BEQ fd_init_filter_done
  LDA filter_reset_cutoff_table,Y
  STA filter_cutoff
fd_init_filter_done:
  RTS

fd_step_filter:
  CLD
  LDA filter_remaining
  BEQ fd_filter_read_row
  DEC filter_remaining
  JMP fd_filter_motion
fd_filter_read_row:
  LDY filter_row
  LDA filter_lower_table,Y
  STA filter_lower
  LDA filter_upper_table,Y
  STA filter_upper
  LDA filter_step_table,Y
  STA filter_step
  LDA filter_duration_table,Y
  STA filter_remaining
  LDA filter_reset_table,Y
  BEQ fd_filter_row_position
  LDA filter_reset_cutoff_table,Y
  STA filter_cutoff
  LDA #$00
  STA filter_direction
fd_filter_row_position:
  LDA filter_hold_table,Y
  BNE fd_filter_motion
  INC filter_row
  LDA filter_row
  AND #$3F
  STA filter_row
fd_filter_motion:
  LDA filter_direction
  BNE fd_filter_subtract
  LDA filter_cutoff
  CLC
  ADC filter_step
  STA filter_cutoff
  CMP filter_upper
  BCS fd_filter_reverse
  RTS
fd_filter_subtract:
  LDA filter_cutoff
  SEC
  SBC filter_step
  STA filter_cutoff
  CMP filter_lower
  BCS fd_filter_done
fd_filter_reverse:
  LDA filter_direction
  EOR #$01
  STA filter_direction
fd_filter_done:
  RTS
