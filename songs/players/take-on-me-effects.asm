; scripts/studies/take-on-me/programs.py owns arithmetic and stage order.
; X selects physical voice X+1 and is preserved; A/Y and $E0-$EF are scratch.

tm_note_setup:
  CLD
  LDA #$00
  STA tm_sound_failed
  LDY tm_base_note,X
  JSR tm_lookup_frequency
  LDY tm_instrument,X
  LDA tm_i_pulse_lo,Y
  STA tm_pulse_lo,X
  LDA tm_i_pulse_hi,Y
  STA tm_pulse_hi,X
  LDA tm_i_onset_control,Y
  STA tm_control,X
  CPX #$00
  BNE tm_setup_adsr
  LDA #$00
  STA tm_filter_initial
  LDA tm_i_filter_word_lo,Y
  STA tm_filter_word_lo
  LDA tm_i_filter_word_hi,Y
  STA tm_filter_word_hi
tm_setup_adsr:
  LDA tm_i_attack_decay,Y
  STA $e4
  LDA tm_i_sustain_release,Y
  STA $e5
  LDY tm_sid_offsets,X
  LDA $e4
  STA $d405,Y
  LDA $e5
  STA $d406,Y
  RTS

tm_body:
  CLD
  LDA #$00
  STA tm_sound_failed
  LDA tm_onset_initial,X
  BMI tm_body_arpeggio
  DEC tm_onset_initial,X
  LDY tm_instrument,X
  LDA tm_i_body_control,Y
  STA tm_control,X
tm_body_arpeggio:
  JSR tm_step_arpeggio
  LDA tm_sound_failed
  BNE tm_body_done
  JSR tm_step_tables
  LDA tm_sound_failed
  BNE tm_body_done
  JSR tm_step_pulse
  LDA tm_glide_active,X
  BEQ tm_body_vibrato
  JSR tm_step_glide
  JMP tm_body_filter
tm_body_vibrato:
  JSR tm_step_vibrato
tm_body_filter:
  CPX #$00
  BNE tm_body_gate
  JSR tm_step_filter
tm_body_gate:
  LDY tm_instrument,X
  LDA tm_i_gate_half,Y
  BEQ tm_body_release
  LDA tm_duration,X
  LSR A
  CMP tm_remaining,X
  BCC tm_body_release
  JSR tm_clear_gate
tm_body_release:
  LDY tm_instrument,X
  LDA tm_i_release_program,Y
  BEQ tm_body_done
  TAY
  LDA tm_r_gate,Y
  CMP tm_remaining,X
  BCC tm_body_sr
  JSR tm_clear_gate
tm_body_sr:
  LDA tm_r_sr_zero,Y
  CMP tm_remaining,X
  BNE tm_body_done
  LDY tm_sid_offsets,X
  LDA #$00
  STA $d406,Y
tm_body_done:
  RTS

tm_clear_gate:
  LDA tm_control,X
  AND #$fe
  STA tm_control,X
  RTS

tm_lookup_frequency:
  LDA tm_frequency_table_lo,Y
  STA tm_frequency_lo,X
  LDA tm_frequency_table_hi,Y
  STA tm_frequency_hi,X
  RTS

tm_step_arpeggio:
  LDY tm_instrument,X
  LDA tm_i_arpeggio_enabled,Y
  BEQ tm_arpeggio_done
  LDY tm_arpeggio,X
  LDA tm_arpeggio_ptr_lo,Y
  STA $e0
  LDA tm_arpeggio_ptr_hi,Y
  STA $e1
  LDA tm_arpeggio_cursor,X
  JSR tm_table_step
  STA $e4
  LDA tm_table_cursor
  STA tm_arpeggio_cursor,X
  BCC tm_arpeggio_done
  LDA $e4
  CLC
  ADC tm_base_note,X
  TAY
  JSR tm_lookup_frequency
tm_arpeggio_done:
  RTS

tm_step_tables:
  LDY tm_instrument,X
  LDA tm_i_table_program,Y
  BEQ tm_tables_done
  STA $e6
  TAY
  LDA tm_waveform_ptr_lo,Y
  STA $e0
  LDA tm_waveform_ptr_hi,Y
  STA $e1
  LDA tm_waveform_cursor,X
  JSR tm_table_step
  STA $e4
  LDA tm_table_cursor
  STA tm_waveform_cursor,X
  BCC tm_tables_pitch
  LDA $e4
  STA tm_control,X
tm_tables_pitch:
  LDA tm_sound_failed
  BNE tm_tables_done
  LDY $e6
  LDA tm_pitch_ptr_lo,Y
  STA $e0
  LDA tm_pitch_ptr_hi,Y
  STA $e1
  LDA tm_pitch_cursor,X
  JSR tm_table_step
  STA $e4
  LDA tm_table_cursor
  STA tm_pitch_cursor,X
  BCC tm_tables_done
  LDY tm_base_note,X
  JSR tm_lookup_frequency
  LDA tm_frequency_hi,X
  CLC
  ADC $e4
  STA tm_frequency_hi,X
tm_tables_done:
  RTS

tm_table_step:
  STA tm_table_cursor
  LDA #$00
  STA tm_table_hops
tm_table_read:
  LDY tm_table_cursor
  LDA ($e0),Y
  CMP #$fe
  BEQ tm_table_hold
  CMP #$ff
  BNE tm_table_value
  INY
  LDA ($e0),Y
  STA tm_table_cursor
  INC tm_table_hops
  BNE tm_table_read
  LDA #$01
  STA tm_sound_failed
tm_table_hold:
  CLC
  RTS
tm_table_value:
  INC tm_table_cursor
  SEC
  RTS

tm_step_pulse:
  LDY tm_instrument,X
  LDA tm_i_pulse_program,Y
  BEQ tm_pulse_done
  TAY
  LDA tm_pulse_ptr_lo,Y
  STA $e2
  LDA tm_pulse_ptr_hi,Y
  STA $e3
  LDA tm_pulse_lo,X
  STA tm_sweep_word_lo
  LDA tm_pulse_hi,X
  STA tm_sweep_word_hi
  LDA tm_pulse_initial,X
  STA tm_sweep_initial
  LDA tm_pulse_direction,X
  STA tm_sweep_direction
  JSR tm_sweep_step
  LDA tm_sweep_word_lo
  STA tm_pulse_lo,X
  LDA tm_sweep_word_hi
  STA tm_pulse_hi,X
  LDA tm_sweep_initial
  STA tm_pulse_initial,X
  LDA tm_sweep_direction
  STA tm_pulse_direction,X
tm_pulse_done:
  RTS

tm_step_filter:
  LDY tm_instrument,X
  LDA tm_i_filter_program,Y
  BEQ tm_filter_done
  TAY
  LDA tm_filter_ptr_lo,Y
  STA $e2
  LDA tm_filter_ptr_hi,Y
  STA $e3
  LDA tm_filter_word_lo
  STA tm_sweep_word_lo
  LDA tm_filter_word_hi
  STA tm_sweep_word_hi
  LDA tm_filter_initial
  STA tm_sweep_initial
  LDA tm_filter_direction
  STA tm_sweep_direction
  JSR tm_sweep_step
  LDA tm_sweep_word_lo
  STA tm_filter_word_lo
  LDA tm_sweep_word_hi
  STA tm_filter_word_hi
  LDA tm_sweep_initial
  STA tm_filter_initial
  LDA tm_sweep_direction
  STA tm_filter_direction
tm_filter_done:
  RTS

; A shared engine preserves programs.sweep_step's overshoot and reset rules.
tm_sweep_step:
  LDA tm_sweep_initial
  BMI tm_sweep_phase
  DEC tm_sweep_initial
  LDY #$00
  LDA ($e2),Y
  STA tm_sweep_direction
tm_sweep_phase:
  LDA tm_sweep_direction
  BMI tm_sweep_done
  BNE tm_sweep_up
  LDY #$01
  LDA tm_sweep_word_lo
  SEC
  SBC ($e2),Y
  STA tm_sweep_word_lo
  INY
  LDA tm_sweep_word_hi
  SBC ($e2),Y
  STA tm_sweep_word_hi
  LDY #$04
  CMP ($e2),Y
  BCC tm_sweep_lower
  BNE tm_sweep_done
  DEY
  LDA tm_sweep_word_lo
  CMP ($e2),Y
  BCS tm_sweep_done
tm_sweep_lower:
  LDY #$05
  LDA ($e2),Y
  STA tm_sweep_direction
  BNE tm_sweep_done
  LDY #$08
  LDA ($e2),Y
  STA tm_sweep_word_lo
  INY
  LDA ($e2),Y
  STA tm_sweep_word_hi
  RTS
tm_sweep_up:
  LDY #$06
  LDA tm_sweep_word_lo
  CLC
  ADC ($e2),Y
  STA tm_sweep_word_lo
  INY
  LDA tm_sweep_word_hi
  ADC ($e2),Y
  STA tm_sweep_word_hi
  LDY #$09
  CMP ($e2),Y
  BCC tm_sweep_done
  BNE tm_sweep_upper
  DEY
  LDA tm_sweep_word_lo
  CMP ($e2),Y
  BCC tm_sweep_done
tm_sweep_upper:
  LDY #$0a
  LDA ($e2),Y
  STA tm_sweep_direction
  BEQ tm_sweep_done
  BMI tm_sweep_done
  LDY #$03
  LDA ($e2),Y
  STA tm_sweep_word_lo
  INY
  LDA ($e2),Y
  STA tm_sweep_word_hi
tm_sweep_done:
  RTS

tm_step_glide:
  LDY tm_glide_target,X
  LDA tm_frequency_table_lo,Y
  STA $e4
  LDA tm_frequency_table_hi,Y
  STA $e5
  LDA tm_base_note,X
  CMP tm_glide_target,X
  BCC tm_glide_up
  LDA tm_frequency_lo,X
  SEC
  SBC tm_glide_step_lo,X
  STA tm_frequency_lo,X
  LDA tm_frequency_hi,X
  SBC tm_glide_step_hi,X
  STA tm_frequency_hi,X
  CMP $e5
  BCC tm_glide_clamp
  BNE tm_glide_done
  LDA tm_frequency_lo,X
  CMP $e4
  BCS tm_glide_done
  JMP tm_glide_clamp
tm_glide_up:
  LDA tm_frequency_lo,X
  CLC
  ADC tm_glide_step_lo,X
  STA tm_frequency_lo,X
  LDA tm_frequency_hi,X
  ADC tm_glide_step_hi,X
  STA tm_frequency_hi,X
  CMP $e5
  BCC tm_glide_done
  BNE tm_glide_clamp
  LDA tm_frequency_lo,X
  CMP $e4
  BCC tm_glide_done
tm_glide_clamp:
  LDA #$00
  STA tm_glide_active,X
  LDA $e4
  STA tm_frequency_lo,X
  LDA $e5
  STA tm_frequency_hi,X
tm_glide_done:
  RTS

tm_step_vibrato:
  LDY tm_instrument,X
  LDA tm_i_vibrato_program,Y
  BNE tm_vibrato_active
  RTS
tm_vibrato_active:
  STA $e6
  TAY
  LDA tm_vibrato_initial,X
  BMI tm_vibrato_delay_check
  DEC tm_vibrato_initial,X
  LDA tm_v_delay,Y
  STA tm_vibrato_delay,X
  LDA tm_v_direction,Y
  STA tm_vibrato_direction,X
  LDA tm_v_duration,Y
  LSR A
  ADC #$00
  STA tm_vibrato_remaining,X
  LDY tm_base_note,X
  LDA tm_frequency_table_lo,Y
  STA $e4
  LDA tm_frequency_table_hi,Y
  STA $e5
  INY
  LDA tm_frequency_table_lo,Y
  SEC
  SBC $e4
  STA tm_vibrato_step_lo,X
  LDA tm_frequency_table_hi,Y
  SBC $e5
  STA tm_vibrato_step_hi,X
  LDY $e6
  LDA tm_v_shift,Y
  TAY
  BEQ tm_vibrato_delay_check
tm_vibrato_shift:
  LSR tm_vibrato_step_hi,X
  ROR tm_vibrato_step_lo,X
  DEY
  BNE tm_vibrato_shift
tm_vibrato_delay_check:
  LDA tm_vibrato_delay,X
  BEQ tm_vibrato_motion
  DEC tm_vibrato_delay,X
  RTS
tm_vibrato_motion:
  LDA tm_vibrato_remaining,X
  BEQ tm_vibrato_reverse
  DEC tm_vibrato_remaining,X
  LDA tm_vibrato_direction,X
  BNE tm_vibrato_up
  LDA tm_frequency_lo,X
  SEC
  SBC tm_vibrato_step_lo,X
  STA tm_frequency_lo,X
  LDA tm_frequency_hi,X
  SBC tm_vibrato_step_hi,X
  STA tm_frequency_hi,X
  RTS
tm_vibrato_up:
  LDA tm_frequency_lo,X
  CLC
  ADC tm_vibrato_step_lo,X
  STA tm_frequency_lo,X
  LDA tm_frequency_hi,X
  ADC tm_vibrato_step_hi,X
  STA tm_frequency_hi,X
  RTS
tm_vibrato_reverse:
  LDY $e6
  LDA tm_v_duration,Y
  STA tm_vibrato_remaining,X
  LDA tm_vibrato_direction,X
  EOR #$01
  STA tm_vibrato_direction,X
  RTS

tm_voice_output:
  LDY tm_sid_offsets,X
  LDA tm_control,X
  STA $d404,Y
  LDA tm_pulse_hi,X
  STA $d403,Y
  LDA tm_pulse_lo,X
  STA $d402,Y
  LDA tm_frequency_hi,X
  STA $d401,Y
  LDA tm_frequency_lo,X
  STA $d400,Y
  RTS

tm_filter_output:
  LDA tm_filter_word_lo
  STA $d415
  LDA tm_filter_word_hi
  STA $d416
  RTS
