cy_advance_arpeggio:
  LDA cy_fx3
  AND #$10
  BNE cy_effect_arp_return
  LDA cy_fx3
  AND #$04
  BEQ cy_effect_arp_return
  LDY cy_arpeggio_index,X
  LDA cy_arp_ptr_lo,Y
  STA $F8
  LDA cy_arp_ptr_hi,Y
  STA $F9
  DEC cy_arpeggio_counter,X
  BPL cy_effect_arp_offset
  LDY #$00
  LDA ($F8),Y
  STA cy_arpeggio_counter,X
cy_effect_arp_offset:
  LDY cy_arpeggio_counter,X
  INY
  LDA ($F8),Y
  CLC
  ADC cy_base_pitch,X
  STA cy_current_pitch,X
  TAY
  LDA cy_freq_lo,Y
  STA cy_frequency_lo,X
  LDA cy_freq_hi,Y
  STA cy_frequency_hi,X
cy_effect_arp_return:
  RTS

cy_advance_pulse:
  LDA cy_fx2
  AND #$07
  BNE cy_effect_pulse_selected
  JMP cy_effect_pulse_copy
cy_effect_pulse_selected:
  TAY
  DEY
  LDA cy_pulse_ptr_lo,Y
  STA $F8
  LDA cy_pulse_ptr_hi,Y
  STA $F9
  LDA cy_fx2
  AND #$F0
  STA cy_effect_step
  LDY #$02
cy_effect_pulse_stage:
  LDA ($F8),Y
  STA cy_effect_stage
  AND #$7F
  CMP cy_note_age,X
  BCS cy_effect_pulse_stage_selected
  INY
  INY
  CPY #$08
  BCC cy_effect_pulse_stage
  JMP cy_effect_pulse_move
cy_effect_pulse_stage_selected:
  INY
  LDA ($F8),Y
  STA cy_effect_step
  LDA cy_effect_stage
  BPL cy_effect_pulse_move
  LDA #$00
  STA cy_pulse_direction,X
cy_effect_pulse_move:
  LDA cy_pulse_direction,X
  BEQ cy_effect_pulse_down
  CLC
  LDA cy_pulse_accumulator_lo,X
  ADC cy_effect_step
  STA cy_pulse_accumulator_lo,X
  LDA cy_pulse_accumulator_hi,X
  ADC #$00
  STA cy_pulse_accumulator_hi,X
  LDY #$01
  CMP ($F8),Y
  BCC cy_effect_pulse_copy
  DEY
  LDA ($F8),Y
  BMI cy_effect_pulse_wrap
  LDA #$00
  STA cy_pulse_direction,X
  JMP cy_effect_pulse_copy
cy_effect_pulse_wrap:
  ; cybernoid_programs.advance_pulse settles the low-one reset and high-only limits.
  AND #$0F
  STA cy_pulse_accumulator_hi,X
  LDA #$01
  STA cy_pulse_accumulator_lo,X
  STA cy_pulse_direction,X
  JMP cy_effect_pulse_copy
cy_effect_pulse_down:
  SEC
  LDA cy_pulse_accumulator_lo,X
  SBC cy_effect_step
  STA cy_pulse_accumulator_lo,X
  LDA cy_pulse_accumulator_hi,X
  SBC #$00
  STA cy_pulse_accumulator_hi,X
  LDY #$00
  LDA ($F8),Y
  AND #$0F
  STA cy_effect_limit
  LDA cy_pulse_accumulator_hi,X
  CMP cy_effect_limit
  BCS cy_effect_pulse_copy
  LDA #$01
  STA cy_pulse_direction,X
cy_effect_pulse_copy:
  LDA cy_pulse_accumulator_lo,X
  STA cy_pulse_output_lo,X
  LDA cy_pulse_accumulator_hi,X
  STA cy_pulse_output_hi,X
  RTS

cy_sweep_high:
  LDA cy_fx3
  AND #$20
  BEQ cy_effect_sweep_return
  DEC cy_held_frequency_hi,X
  LDA cy_held_frequency_hi,X
  STA cy_frequency_hi,X
cy_effect_sweep_return:
  RTS

cy_filter:
  LDA cy_fx3
  AND #$01
  BNE cy_effect_filter_active
  TXA
  CMP cy_filter_owner
  BNE cy_effect_filter_return
  LDA cy_fx2
  AND #$08
  BNE cy_effect_filter_return
  LDA #$1F
  JSR cy_write_mode
  LDA #$80
  STA cy_filter_cutoff,X
  STA $D416
cy_effect_filter_return:
  RTS
cy_effect_filter_active:
  TXA
  STA cy_filter_owner
  LDA cy_packed_filter,X
  AND #$07
  TAY
  LDA cy_filter_ptr_lo,Y
  STA $F8
  LDA cy_filter_ptr_hi,Y
  STA $F9
  LDY #$05
  LDA ($F8),Y
  JSR cy_write_mode
  LDY #$09
  LDA cy_note_age,X
  CMP ($F8),Y
  BCS cy_effect_filter_terminal
  ; cybernoid_programs.advance_filter preserves descending index priority for edits.
  DEY
cy_effect_filter_stage:
  CMP ($F8),Y
  BCS cy_effect_filter_add
  DEY
  CPY #$06
  BCS cy_effect_filter_stage
  LDY #$00
  LDA ($F8),Y
  JMP cy_effect_filter_write
cy_effect_filter_add:
  TYA
  SEC
  SBC #$05
  TAY
  LDA cy_filter_cutoff,X
  CLC
  ADC ($F8),Y
  JMP cy_effect_filter_write
cy_effect_filter_terminal:
  LDY #$04
  LDA ($F8),Y
cy_effect_filter_write:
  STA cy_filter_cutoff,X
  STA $D416
  RTS

cy_pulse_run:
  LDA cy_fx3
  AND #$02
  BNE cy_effect_run_active
  LDA #$01
  STA cy_pulse_run_flag,X
  RTS
cy_effect_run_active:
  LDA cy_pulse_run_flag,X
  BEQ cy_effect_run_move
  LDA #$00
  STA cy_pulse_run_flag,X
  STA cy_pulse_run_low,X
  LDA cy_pulse_accumulator_hi,X
  STA cy_pulse_run_high,X
cy_effect_run_move:
  CLC
  LDA cy_pulse_run_low,X
  ADC #$63
  STA cy_pulse_run_low,X
  BCC cy_effect_run_copy
  INC cy_pulse_run_high,X
  LDA cy_pulse_run_high,X
  CMP #$0F
  BNE cy_effect_run_copy
  EOR #$08
  STA cy_pulse_run_high,X
cy_effect_run_copy:
  LDA cy_pulse_run_low,X
  STA cy_pulse_output_lo,X
  LDA cy_pulse_run_high,X
  STA cy_pulse_output_hi,X
  RTS

cy_wave:
  LDA cy_fx3
  AND #$10
  BEQ cy_effect_wave_onset_check
  JMP cy_effect_wave_drum
cy_effect_wave_onset_check:
  LDA cy_fx3
  AND #$80
  BEQ cy_effect_wave_return
  LDY cy_sound_index,X
  LDA cy_onset_lengths,Y
  STA cy_effect_limit
  LDA cy_note_age,X
  CMP cy_effect_limit
  BCC cy_effect_wave_onset
  LDA cy_effect_limit
  CLC
  ADC #$02
  STA cy_effect_limit
  LDA cy_note_age,X
  CMP cy_effect_limit
  BCS cy_effect_wave_return
  LDA cy_base_wave,X
  STA cy_output_wave,X
  LDA cy_held_frequency_lo,X
  STA cy_frequency_lo,X
  LDA cy_held_frequency_hi,X
  STA cy_frequency_hi,X
  RTS
cy_effect_wave_onset:
  LDA cy_onset_waves,Y
  CMP #$7F
  BCC cy_effect_wave_onset_control
  LDA #$FA
  STA cy_frequency_hi,X
  LDA #$81
cy_effect_wave_onset_control:
  STA cy_output_wave,X
cy_effect_wave_return:
  RTS
cy_effect_wave_drum:
  ; cybernoid_output.apply_wave_program gives drums priority even after expiry.
  LDA cy_fx1
  AND #$0F
  TAY
  LDA cy_drum_wave_ptr_lo,Y
  STA $F8
  LDA cy_drum_wave_ptr_hi,Y
  STA $F9
  LDY #$00
  LDA cy_note_age,X
  CMP ($F8),Y
  BCS cy_effect_wave_return
  TAY
  LDA ($F8),Y
  STA cy_output_wave,X
  AND #$01
  BEQ cy_effect_wave_drum_gate_off
  LDA #$FF
  BNE cy_effect_wave_drum_gate
cy_effect_wave_drum_gate_off:
  LDA #$FE
cy_effect_wave_drum_gate:
  STA cy_gate_mask,X
  LDA cy_fx1
  AND #$0F
  TAY
  LDA cy_drum_pitch_ptr_lo,Y
  STA $F8
  LDA cy_drum_pitch_ptr_hi,Y
  STA $F9
  LDY cy_note_age,X
  DEY
  LDA ($F8),Y
  STA cy_effect_pitch
  LDA cy_fx1
  AND #$10
  BNE cy_effect_wave_drum_relative
  LDA cy_effect_pitch
  STA cy_frequency_hi,X
  LDA #$00
  STA cy_frequency_lo,X
  RTS
cy_effect_wave_drum_relative:
  CLC
  LDA cy_effect_pitch
  ADC cy_current_pitch,X
  TAY
  LDA cy_freq_lo,Y
  STA cy_frequency_lo,X
  LDA cy_freq_hi,Y
  STA cy_frequency_hi,X
  RTS

cy_effect_step:
  .byte $00
cy_effect_stage:
  .byte $00
cy_effect_limit:
  .byte $00
cy_effect_pitch:
  .byte $00
