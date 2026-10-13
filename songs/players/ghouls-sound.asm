gh_advance_sound:
  ; scripts/ghouls_programs.py owns the stage order and unsigned arithmetic contract.
  CLD
  JSR gh_step_onset
  JSR gh_step_frequency
  JSR gh_step_note
  JMP gh_step_pulse

gh_step_onset:
  CLD
  LDA gh_onset_remaining,X
  BEQ gh_onset_done
  DEC gh_onset_remaining,X
  BNE gh_onset_done
  JSR gh_write_frequency
  LDA gh_gate_enabled,X
  BEQ gh_onset_done
  LDA gh_waveform,X
  ORA #$01
  LDY gh_sid_offsets,X
  STA $d404,Y
gh_onset_done:
  RTS

gh_step_frequency:
  CLD
  LDA gh_frequency_delay_reload,X
  BEQ gh_frequency_done
  LDA gh_frequency_delay_remaining,X
  BEQ gh_frequency_motion
  DEC gh_frequency_delay_remaining,X
  BNE gh_frequency_done
gh_frequency_motion:
  LDA gh_frequency_direction,X
  BEQ gh_frequency_down
  LDA gh_current_frequency_lo,X
  CLC
  ADC gh_frequency_step,X
  STA gh_current_frequency_lo,X
  BCC gh_frequency_phase
  INC gh_current_frequency_hi,X
  LDA gh_current_frequency_hi,X
  BNE gh_frequency_phase
  ; Numeric frequency_step retains the source-backed high-byte-wrap fallthrough.
  LDA gh_current_frequency_lo,X
  SEC
  SBC gh_frequency_step,X
  STA gh_current_frequency_lo,X
  LDA #$ff
  STA gh_current_frequency_hi,X
  JMP gh_frequency_phase
gh_frequency_down:
  LDA gh_current_frequency_lo,X
  SEC
  SBC gh_frequency_step,X
  STA gh_current_frequency_lo,X
  LDA gh_current_frequency_hi,X
  SBC #$00
  STA gh_current_frequency_hi,X
gh_frequency_phase:
  DEC gh_frequency_half_remaining,X
  BNE gh_frequency_output
  LDA gh_frequency_half_reload,X
  BEQ gh_frequency_output
  ASL A
  STA gh_frequency_half_remaining,X
  LDA gh_frequency_direction,X
  EOR #$ff
  STA gh_frequency_direction,X
gh_frequency_output:
  JMP gh_write_frequency
gh_frequency_done:
  RTS

gh_step_note:
  CLD
  LDA gh_note_remaining,X
  BEQ gh_note_glide
  DEC gh_note_remaining,X
  BNE gh_note_glide
  LDA gh_note_direction,X
  EOR #$ff
  STA gh_note_direction,X
  BEQ gh_note_alternate_down
  LDA gh_note_positive_duration,X
  STA gh_note_remaining,X
  LDA gh_note_index,X
  CLC
  ADC gh_note_step,X
  JMP gh_note_store_index
gh_note_alternate_down:
  LDA gh_note_negative_duration,X
  STA gh_note_remaining,X
  LDA gh_note_index,X
  SEC
  SBC gh_note_step,X
  JMP gh_note_store_index
gh_note_glide:
  LDA gh_glide_rate,X
  BEQ gh_note_done
  LDA gh_note_index,X
  CMP gh_target_note_index,X
  BEQ gh_note_done
  BCC gh_note_glide_up
  SEC
  SBC gh_glide_rate,X
  CMP gh_target_note_index,X
  BCS gh_note_store_index
  LDA gh_target_note_index,X
  JMP gh_note_store_index
gh_note_glide_up:
  CLC
  ADC gh_glide_rate,X
  CMP gh_target_note_index,X
  BCC gh_note_store_index
  LDA gh_target_note_index,X
gh_note_store_index:
  STA gh_note_index,X
  JMP gh_lookup_frequency
gh_note_done:
  RTS

gh_step_pulse:
  CLD
  LDA gh_pulse_direction,X
  BEQ gh_pulse_down
  CMP #$ff
  BEQ gh_pulse_up
  RTS
gh_pulse_down:
  LDA gh_pulse_word_lo,X
  SEC
  SBC gh_pulse_step,X
  STA gh_pulse_word_lo,X
  LDA gh_pulse_word_hi,X
  SBC #$00
  STA gh_pulse_word_hi,X
  BMI gh_pulse_lower_reverse
  BNE gh_pulse_output
  LDA gh_pulse_word_lo,X
  CMP #$64
  BCS gh_pulse_output
gh_pulse_lower_reverse:
  LDA #$ff
  STA gh_pulse_direction,X
gh_pulse_up:
  LDA gh_pulse_word_lo,X
  CLC
  ADC gh_pulse_step,X
  STA gh_pulse_word_lo,X
  LDA gh_pulse_word_hi,X
  ADC #$00
  STA gh_pulse_word_hi,X
  CMP #$0f
  BCC gh_pulse_output
  BNE gh_pulse_upper_reverse
  LDA gh_pulse_word_lo,X
  CMP #$9b
  BCC gh_pulse_output
gh_pulse_upper_reverse:
  LDA #$00
  STA gh_pulse_direction,X
  LDA gh_pulse_word_lo,X
  SEC
  SBC gh_pulse_step,X
  STA gh_pulse_word_lo,X
  LDA gh_pulse_word_hi,X
  SBC #$00
  STA gh_pulse_word_hi,X
gh_pulse_output:
  LDY gh_sid_offsets,X
  LDA gh_pulse_word_lo,X
  STA $d402,Y
  LDA gh_pulse_word_hi,X
  STA $d403,Y
  RTS

gh_note_setup:
  CLD
  STA gh_sound_tmp
  LDA gh_pitch_index_mode,X
  BEQ gh_setup_transpose
  INC gh_pitch_index_mode,X
  BEQ gh_setup_raw_index
gh_setup_transpose:
  LDA gh_sound_tmp
  CLC
  ADC gh_transpose,X
  JMP gh_setup_glide
gh_setup_raw_index:
  LDA gh_sound_tmp
gh_setup_glide:
  LDY gh_glide_rate,X
  BEQ gh_setup_index
  STA gh_target_note_index,X
  LDA gh_note_index,X
gh_setup_index:
  STA gh_note_index,X
  JSR gh_lookup_frequency
  LDA gh_note_positive_duration,X
  STA gh_note_remaining,X
  LDA gh_frequency_delay_reload,X
  BEQ gh_setup_motion_done
  STA gh_frequency_delay_remaining,X
  LDA gh_frequency_direction_default,X
  STA gh_frequency_direction,X
  LDA gh_frequency_half_reload,X
  STA gh_frequency_half_remaining,X
gh_setup_motion_done:
  LDA #$00
  STA gh_note_direction,X
  LDA gh_rest_reload,X
  STA gh_rest_remaining,X
  LDA gh_pulse_default_lo,X
  ORA gh_pulse_default_hi,X
  BEQ gh_setup_filter
  LDA gh_pulse_default_lo,X
  STA gh_pulse_word_lo,X
  LDA gh_pulse_default_hi,X
  STA gh_pulse_word_hi,X
  LDA gh_pulse_restart,X
  STA gh_pulse_direction,X
gh_setup_filter:
  TXA
  CMP gh_filter_owner
  BNE gh_setup_gate
  LDA gh_filter_default_lo
  ORA gh_filter_default_hi
  BEQ gh_setup_gate
  LDA gh_filter_default_lo
  STA gh_filter_word_lo
  LDA gh_filter_default_hi
  STA gh_filter_word_hi
  LDA gh_filter_reset_direction
  STA gh_filter_direction
gh_setup_gate:
  LDA gh_gate_enabled,X
  BEQ gh_setup_done
  LDA gh_onset_delay,X
  BEQ gh_setup_body_control
  STA gh_onset_remaining,X
  LDY gh_sid_offsets,X
  LDA gh_onset_frequency_lo,X
  STA $d400,Y
  LDA gh_onset_frequency_hi,X
  STA $d401,Y
  LDA gh_onset_control,X
  JMP gh_setup_control
gh_setup_body_control:
  LDA gh_waveform,X
gh_setup_control:
  ORA #$01
  LDY gh_sid_offsets,X
  STA $d404,Y
gh_setup_done:
  RTS

gh_lookup_frequency:
  LDY gh_note_index,X
  LDA gh_frequency_lo,Y
  STA gh_current_frequency_lo,X
  LDA gh_frequency_hi,Y
  STA gh_current_frequency_hi,X
gh_write_frequency:
  LDY gh_sid_offsets,X
  LDA gh_current_frequency_lo,X
  STA $d400,Y
  LDA gh_current_frequency_hi,X
  STA $d401,Y
  RTS

gh_advance_filter:
  CLD
  LDA #$00
  STA gh_filter_failed
  STA gh_filter_attempts
  LDA gh_filter_direction
  BNE gh_filter_up
gh_filter_down:
  LDA gh_filter_word_lo
  SEC
  SBC gh_filter_step
  STA gh_filter_word_lo
  BCS gh_filter_lower_threshold
  DEC gh_filter_word_hi
  ; scripts/ghouls_programs.py's edited $8001/$8100 controls settle the borrow-only sign test.
  LDA gh_filter_word_hi
  BMI gh_filter_lower_reverse
gh_filter_lower_threshold:
  LDA gh_filter_word_hi
  CMP gh_filter_lower_hi
  BNE gh_filter_output
  LDA gh_filter_word_lo
  CMP gh_filter_lower_lo
  BCS gh_filter_output
gh_filter_lower_reverse:
  DEC gh_filter_direction
  INC gh_filter_attempts
  BEQ gh_filter_failure
gh_filter_up:
  LDA gh_filter_word_lo
  CLC
  ADC gh_filter_step
  STA gh_filter_word_lo
  LDA gh_filter_word_hi
  ADC #$00
  STA gh_filter_word_hi
  CMP gh_filter_upper_hi
  BCC gh_filter_output
  LDA gh_filter_word_lo
  CMP gh_filter_upper_lo
  BCC gh_filter_output
  INC gh_filter_direction
  INC gh_filter_attempts
  BEQ gh_filter_failure
  JMP gh_filter_down
gh_filter_failure:
  LDA #$01
  STA gh_filter_failed
  SEC
  RTS
gh_filter_output:
  LDA gh_filter_word_lo
  STA $d415
  ; The numeric output contract folds high bits 4..7 into the emitted low nibble.
  LDA gh_filter_word_hi
  AND #$07
  ASL A
  ASL A
  ASL A
  ASL A
  ASL A
  STA gh_sound_tmp
  LDA gh_filter_word_hi
  LSR A
  LSR A
  LSR A
  LSR A
  ORA gh_sound_tmp
  STA gh_sound_tmp
  LDA gh_filter_word_lo
  LSR A
  LSR A
  LSR A
  ORA gh_sound_tmp
  STA $d416
  CLC
  RTS
