cy_advance_pitch:
  CLD
  LDA cy_fx3
  AND #$10
  BEQ cy_pitch_check_vibrato
  JMP cy_pitch_glide
cy_pitch_check_vibrato:
  LDA cy_fx1
  BNE cy_pitch_check_active
  JMP cy_pitch_glide
cy_pitch_check_active:
  LDA cy_glide_active,X
  BEQ cy_pitch_vibrato
  JMP cy_pitch_glide

cy_pitch_vibrato:
  LDA cy_fx1
  LSR A
  LSR A
  LSR A
  LSR A
  AND #$07
  STA cy_vibrato_extent,X
  LDA cy_vibrato_age,X
  CMP #$30
  BCS cy_pitch_difference
  INC cy_vibrato_age,X
cy_pitch_difference:
  LDY cy_current_pitch,X
  SEC
  LDA cy_freq_lo+1,Y
  SBC cy_freq_lo,Y
  STA cy_pitch_delta_lo
  LDA cy_freq_hi+1,Y
  SBC cy_freq_hi,Y
  STA cy_pitch_delta_hi
  LDA cy_fx1
  BPL cy_pitch_shift_setup
  ; advance_pitch retains the word subtraction carry in high-byte age growth.
  LDA cy_pitch_delta_hi
  ADC cy_vibrato_age,X
  STA cy_pitch_delta_hi
cy_pitch_shift_setup:
  LDA cy_fx1
  AND #$0f
  TAY
  BEQ cy_pitch_phase
cy_pitch_shift:
  LSR cy_pitch_delta_hi
  ROR cy_pitch_delta_lo
  DEY
  BNE cy_pitch_shift

cy_pitch_phase:
  LDA cy_vibrato_direction,X
  BPL cy_pitch_ascending
  DEC cy_vibrato_position,X
  LDA cy_vibrato_position,X
  BNE cy_pitch_base_frequency
  INC cy_vibrato_direction,X
  LDA cy_vibrato_direction,X
  BPL cy_pitch_base_frequency
cy_pitch_ascending:
  INC cy_vibrato_position,X
  LDA cy_vibrato_extent,X
  CMP cy_vibrato_position,X
  BCS cy_pitch_base_frequency
  DEC cy_vibrato_direction,X
  SEC
  SBC #$01
  STA cy_vibrato_position,X
cy_pitch_base_frequency:
  LDY cy_current_pitch,X
  LDA cy_freq_lo,Y
  STA cy_frequency_lo,X
  LDA cy_freq_hi,Y
  STA cy_frequency_hi,X
  LDA cy_vibrato_extent,X
  LSR A
  STA cy_pitch_center
  BEQ cy_pitch_add_setup
  LDY cy_sound_index,X
  LDA cy_note_age,X
  CMP cy_vibrato_wait,Y
  BCC cy_pitch_hold
  LDY cy_pitch_center
cy_pitch_subtract:
  SEC
  LDA cy_frequency_lo,X
  SBC cy_pitch_delta_lo
  STA cy_frequency_lo,X
  LDA cy_frequency_hi,X
  SBC cy_pitch_delta_hi
  STA cy_frequency_hi,X
  DEY
  BNE cy_pitch_subtract
cy_pitch_add_setup:
  LDA cy_vibrato_position,X
  CMP #$81
  BCS cy_pitch_hold
  TAY
  BEQ cy_pitch_hold
cy_pitch_add:
  CLC
  LDA cy_frequency_lo,X
  ADC cy_pitch_delta_lo
  STA cy_frequency_lo,X
  LDA cy_frequency_hi,X
  ADC cy_pitch_delta_hi
  STA cy_frequency_hi,X
  DEY
  BNE cy_pitch_add
cy_pitch_hold:
  LDA cy_frequency_lo,X
  STA cy_held_frequency_lo,X
  LDA cy_frequency_hi,X
  STA cy_held_frequency_hi,X

cy_pitch_glide:
  LDA cy_glide_enabled,X
  BNE cy_pitch_glide_timing
  RTS
cy_pitch_glide_timing:
  LDA cy_glide_control,X
  LSR A
  LSR A
  LSR A
  LSR A
  STA cy_pitch_length
  LDA cy_glide_control,X
  AND #$0f
  SEC
  SBC #$01
  CLC
  ADC cy_row_remaining,X
  CMP cy_row_duration,X
  BCC cy_pitch_glide_start
  RTS
cy_pitch_glide_start:
  STA cy_pitch_timing
  LDA #$01
  STA cy_glide_active,X
  CLC
  LDA cy_pitch_timing
  ADC cy_pitch_length
  CMP cy_row_duration,X
  BCS cy_pitch_glide_interpolate
  LDY cy_glide_target,X
  TYA
  STA cy_base_pitch,X
  LDA cy_freq_lo,Y
  STA cy_frequency_lo,X
  STA cy_held_frequency_lo,X
  LDA cy_freq_hi,Y
  STA cy_frequency_hi,X
  STA cy_held_frequency_hi,X
  LDA #$00
  STA cy_glide_enabled,X
  STA cy_glide_active,X
  RTS

cy_pitch_glide_interpolate:
  LDY cy_base_pitch,X
  LDA cy_freq_lo,Y
  STA cy_pitch_base_lo
  LDA cy_freq_hi,Y
  STA cy_pitch_base_hi
  LDY cy_glide_target,X
  LDA cy_freq_lo,Y
  STA cy_pitch_target_lo
  LDA cy_freq_hi,Y
  STA cy_pitch_target_hi
  LDA cy_pitch_base_hi
  CMP cy_pitch_target_hi
  BCC cy_pitch_distance_add
  BNE cy_pitch_distance_subtract
  LDA cy_pitch_base_lo
  CMP cy_pitch_target_lo
  BCC cy_pitch_distance_add
cy_pitch_distance_subtract:
  LDA #$01
  STA cy_pitch_subtract_flag
  SEC
  LDA cy_pitch_base_lo
  SBC cy_pitch_target_lo
  STA cy_pitch_distance_lo
  LDA cy_pitch_base_hi
  SBC cy_pitch_target_hi
  STA cy_pitch_distance_hi
  JMP cy_pitch_divisor_setup
cy_pitch_distance_add:
  LDA #$00
  STA cy_pitch_subtract_flag
  SEC
  LDA cy_pitch_target_lo
  SBC cy_pitch_base_lo
  STA cy_pitch_distance_lo
  LDA cy_pitch_target_hi
  SBC cy_pitch_base_hi
  STA cy_pitch_distance_hi

cy_pitch_divisor_setup:
  LDA cy_tempo_reload
  CMP #$81
  BCS cy_pitch_divisor_once
  CLC
  ADC #$01
  TAY
  JMP cy_pitch_divisor_start
cy_pitch_divisor_once:
  LDY #$01
cy_pitch_divisor_start:
  LDA #$00
  CLC
cy_pitch_divisor_add:
  ; glide_divisor preserves carry between byte sums and signed speed cases.
  ADC cy_pitch_length
  DEY
  BNE cy_pitch_divisor_add
  STA cy_pitch_divisor
  LDA cy_pitch_distance_hi
  AND #$80
  STA cy_pitch_high_bit
  LDA #$00
  STA cy_pitch_quotient_lo
  STA cy_pitch_quotient_hi
  STA cy_pitch_remainder
  LDA cy_pitch_divisor
  BNE cy_pitch_divide_setup
  LDA cy_pitch_high_bit
  EOR #$80
  STA cy_pitch_quotient_hi
  JMP cy_pitch_apply_glide

cy_pitch_divide_setup:
  ; rounded_glide_step divides only bits 0..14 and restores bit 15 afterward.
  LDA cy_pitch_distance_hi
  AND #$7f
  STA cy_pitch_distance_hi
  ASL cy_pitch_distance_lo
  ROL cy_pitch_distance_hi
  LDY #$0f
cy_pitch_divide:
  ASL cy_pitch_quotient_lo
  ROL cy_pitch_quotient_hi
  ASL cy_pitch_distance_lo
  ROL cy_pitch_distance_hi
  ROL cy_pitch_remainder
  BCS cy_pitch_divide_subtract
  LDA cy_pitch_remainder
  CMP cy_pitch_divisor
  BCC cy_pitch_divide_next
cy_pitch_divide_subtract:
  SEC
  LDA cy_pitch_remainder
  SBC cy_pitch_divisor
  STA cy_pitch_remainder
  INC cy_pitch_quotient_lo
cy_pitch_divide_next:
  DEY
  BNE cy_pitch_divide
  LDA cy_pitch_remainder
  ASL A
  CMP cy_pitch_divisor
  BCC cy_pitch_restore_high_bit
  INC cy_pitch_quotient_lo
  BNE cy_pitch_restore_high_bit
  INC cy_pitch_quotient_hi
cy_pitch_restore_high_bit:
  LDA cy_pitch_quotient_hi
  ORA cy_pitch_high_bit
  STA cy_pitch_quotient_hi
cy_pitch_apply_glide:
  LDA cy_pitch_subtract_flag
  BNE cy_pitch_apply_subtract
  CLC
  LDA cy_held_frequency_lo,X
  ADC cy_pitch_quotient_lo
  STA cy_frequency_lo,X
  STA cy_held_frequency_lo,X
  LDA cy_held_frequency_hi,X
  ADC cy_pitch_quotient_hi
  STA cy_frequency_hi,X
  STA cy_held_frequency_hi,X
  RTS
cy_pitch_apply_subtract:
  SEC
  LDA cy_held_frequency_lo,X
  SBC cy_pitch_quotient_lo
  STA cy_frequency_lo,X
  STA cy_held_frequency_lo,X
  LDA cy_held_frequency_hi,X
  SBC cy_pitch_quotient_hi
  STA cy_frequency_hi,X
  STA cy_held_frequency_hi,X
  RTS

cy_pitch_scratch:
cy_pitch_delta_lo:
  .byte $00
cy_pitch_delta_hi:
  .byte $00
cy_pitch_center:
  .byte $00
cy_pitch_length:
  .byte $00
cy_pitch_timing:
  .byte $00
cy_pitch_base_lo:
  .byte $00
cy_pitch_base_hi:
  .byte $00
cy_pitch_target_lo:
  .byte $00
cy_pitch_target_hi:
  .byte $00
cy_pitch_subtract_flag:
  .byte $00
cy_pitch_distance_lo:
  .byte $00
cy_pitch_distance_hi:
  .byte $00
cy_pitch_divisor:
  .byte $00
cy_pitch_high_bit:
  .byte $00
cy_pitch_quotient_lo:
  .byte $00
cy_pitch_quotient_hi:
  .byte $00
cy_pitch_remainder:
  .byte $00
