entry_init:
  CLD
  LDY #$00
cy_restore_state:
  LDA cy_initial_state,Y
  STA cy_state_begin,Y
  INY
  CPY #CY_STATE_BYTES
  BNE cy_restore_state
  LDX #$02
cy_restore_schedules:
  TXA
  ASL A
  TAY
  LDA cy_schedule_bases,Y
  STA cy_schedule_lo,X
  INY
  LDA cy_schedule_bases,Y
  STA cy_schedule_hi,X
  DEX
  BPL cy_restore_schedules
  LDA #CY_INIT_CUTOFF
  STA $D416
  LDA #CY_INIT_ROUTING
  STA $D417
  LDA #CY_INIT_MODE_VOLUME
  JSR cy_write_mode
  LDA #$00
  LDX #$15
cy_clear_sid:
  STA $D400,X
  DEX
  BPL cy_clear_sid
  RTS

entry_play:
  LDA $F8
  PHA
  LDA $F9
  PHA
  JSR cy_frame
  PLA
  STA $F9
  PLA
  STA $F8
  RTS

cy_frame:
  CLD
  LDA cy_tick_hi
  CMP #CY_CALLS_HI
  BNE cy_frame_run
  LDA cy_tick_lo
  CMP #CY_CALLS_LO
  BNE cy_frame_run
  RTS
cy_frame_run:
  LDA cy_tail
  BNE cy_tail_frame
  LDA cy_tick_hi
  CMP #CY_MUSIC_HI
  BNE cy_music_frame
  LDA cy_tick_lo
  CMP #CY_MUSIC_LO
  BNE cy_music_frame
  INC cy_tail
cy_tail_frame:
  LDA #$00
  STA cy_scheduled
  LDA cy_tick_hi
  CMP #CY_FADE_HI
  BNE cy_start_voices
  LDA cy_tick_lo
  CMP #CY_FADE_LO
  BNE cy_start_voices
  INC cy_fading
  JMP cy_start_voices
cy_music_frame:
  DEC cy_tempo_countdown
  BPL cy_tempo_ready
  LDA cy_tempo_reload
  STA cy_tempo_countdown
cy_tempo_ready:
  LDA #$00
  STA cy_scheduled
  LDA cy_tempo_countdown
  CMP cy_tempo_reload
  BNE cy_start_voices
  INC cy_scheduled
cy_start_voices:
  LDX #$02
cy_voice_loop:
  LDA cy_tail
  BEQ cy_increment_age
  LDA cy_note_age,X
  CMP #$FF
  BEQ cy_voice_body
  INC cy_note_age,X
  JMP cy_voice_body
cy_increment_age:
  INC cy_note_age,X
  LDA cy_scheduled
  BEQ cy_voice_schedule
  DEC cy_row_remaining,X
cy_voice_schedule:
  LDA cy_schedule_lo,X
  STA $F8
  LDA cy_schedule_hi,X
  STA $F9
  LDY #$00
  LDA ($F8),Y
  CMP cy_tick_lo
  BNE cy_voice_body
  INY
  LDA ($F8),Y
  CMP cy_tick_hi
  BNE cy_voice_body
  JSR cy_consume_row
  JMP cy_voice_output
cy_voice_body:
  JSR cy_body_prelude
  JSR cy_advance_arpeggio
  JSR cy_advance_pitch
  JSR cy_advance_pulse
  JSR cy_sweep_high
  JSR cy_filter
  JSR cy_pulse_run
  LDA cy_packed_filter,X
  AND #$08
  BEQ cy_voice_wave
  CLC
  LDA cy_frequency_lo,X
  ADC #$0C
  STA cy_frequency_lo,X
  LDA cy_frequency_hi,X
  ADC #$00
  STA cy_frequency_hi,X
cy_voice_wave:
  JSR cy_wave
cy_voice_output:
  LDA cy_tail
  BEQ cy_voice_write
  LDA cy_gate_mask,X
  AND #$FE
  STA cy_gate_mask,X
cy_voice_write:
  JSR cy_writer
  DEX
  BMI cy_tick
  JMP cy_voice_loop
cy_tick:
  LDA cy_tail
  BEQ cy_increment_tick
  LDA cy_mode_volume
  JSR cy_write_mode
  LDA cy_fading
  BEQ cy_increment_tick
  DEC cy_fade_remaining
  BNE cy_increment_tick
  LDA #CY_FADE_STEP
  STA cy_fade_remaining
  LDA cy_tail_volume
  BEQ cy_increment_tick
  DEC cy_tail_volume
cy_increment_tick:
  INC cy_tick_lo
  BNE cy_frame_done
  INC cy_tick_hi
cy_frame_done:
  RTS

; The arranged ending masks every filter write (cybernoid_player.ending_parameters).
cy_write_mode:
  PHA
  STA cy_mode_volume
  LDA cy_tail
  BEQ cy_write_mode_store
  LDA cy_mode_volume
  AND #$F0
  ORA cy_tail_volume
  STA cy_mode_volume
cy_write_mode_store:
  LDA cy_mode_volume
  STA $D418
  PLA
  RTS

cy_consume_row:
  LDY #$02
  LDA ($F8),Y
  STA cy_core_row_lo
  INY
  LDA ($F8),Y
  STA cy_core_row_hi
  CLC
  LDA cy_schedule_lo,X
  ADC #$04
  STA cy_schedule_lo,X
  LDA cy_schedule_hi,X
  ADC #$00
  STA cy_schedule_hi,X
  LDA cy_core_row_lo
  STA $F8
  LDA cy_core_row_hi
  STA $F9
  LDA #$00
  STA cy_glide_enabled,X
  STA cy_glide_active,X
  STA cy_note_age,X
  STA cy_vibrato_age,X
  LDY #$00
  JSR cy_row_byte
  STA cy_core_transpose
  JSR cy_row_byte
  STA cy_core_preserve
cy_command:
  JSR cy_row_byte
  CMP #CY_OP_ROUTING
  BNE cy_dispatch_sound
  JSR cy_row_byte
  STA $D417
  JMP cy_command
cy_dispatch_sound:
  CMP #CY_OP_SOUND
  BNE cy_dispatch_duration
  JSR cy_row_byte
  STA cy_sound_index,X
  JMP cy_command
cy_dispatch_duration:
  CMP #CY_OP_DURATION
  BEQ cy_command_duration
  CMP #CY_OP_EXTEND_DURATION
  BNE cy_dispatch_arpeggio
cy_command_duration:
  JSR cy_row_byte
  STA cy_row_duration,X
  JMP cy_command
cy_dispatch_arpeggio:
  CMP #CY_OP_ARPEGGIO
  BNE cy_dispatch_glide
  JSR cy_row_byte
  STA cy_arpeggio_index,X
  JMP cy_command
cy_dispatch_glide:
  CMP #CY_OP_GLIDE
  BNE cy_command_note
  JSR cy_row_byte
  STA cy_glide_control,X
  JSR cy_row_byte
  CLC
  ADC cy_core_transpose
  STA cy_glide_target,X
  LDA #$01
  STA cy_glide_enabled,X
  JMP cy_command
cy_command_note:
  JSR cy_row_byte
  CLC
  ADC cy_core_transpose
  STA cy_base_pitch,X
  TAY
  LDA cy_freq_lo,Y
  STA cy_frequency_lo,X
  STA cy_held_frequency_lo,X
  LDA cy_freq_hi,Y
  STA cy_frequency_hi,X
  STA cy_held_frequency_hi,X
  STA cy_held_high_copy,X
  LDA cy_row_duration,X
  STA cy_row_remaining,X
  LDA #$00
  STA cy_arpeggio_counter,X
  LDY cy_sid_offsets,X
  LDA cy_frequency_hi,X
  STA $D401,Y
  LDA cy_frequency_lo,X
  STA $D400,Y
  LDA cy_core_preserve
  BNE cy_finish_row
  LDY cy_sound_index,X
  LDA cy_record_wave,Y
  STA cy_base_wave,X
  STA cy_output_wave,X
  LDA cy_record_pulse_flags,Y
  STA cy_pulse_flags,X
  AND #$0F
  STA cy_pulse_accumulator_hi,X
  STA cy_pulse_output_hi,X
  LDA #$00
  STA cy_pulse_accumulator_lo,X
  STA cy_pulse_output_lo,X
  LDA #$01
  STA cy_pulse_direction,X
  LDA cy_record_packed_gate_filter,Y
  STA cy_packed_filter,X
  LDA cy_record_attack_decay,Y
  STA cy_core_threshold
  LDA cy_record_sustain_release,Y
  STA cy_core_preserve
  LDY cy_sid_offsets,X
  LDA cy_core_threshold
  STA $D405,Y
  LDA cy_core_preserve
  STA $D406,Y
cy_finish_row:
  LDA #$FF
  STA cy_gate_mask,X
  RTS

cy_row_byte:
  LDA ($F8),Y
  INY
  RTS

cy_body_prelude:
  LDY cy_sound_index,X
  LDA cy_record_fx1,Y
  STA cy_fx1
  LDA cy_record_fx2,Y
  STA cy_fx2
  LDA cy_record_fx3,Y
  STA cy_fx3
  LDA cy_scheduled
  BEQ cy_body_sr
  LDA cy_record_packed_gate_filter,Y
  AND #$F0
  LSR A
  LSR A
  STA cy_core_threshold
  LDA cy_row_remaining,X
  CMP cy_core_threshold
  BCC cy_gate_off
  BEQ cy_gate_off
  LDA #$FF
  BNE cy_store_gate
cy_gate_off:
  LDA #$FE
cy_store_gate:
  STA cy_gate_mask,X
cy_body_sr:
  LDA cy_pulse_flags,X
  AND #$10
  BEQ cy_body_pitch
  LDA cy_row_remaining,X
  BNE cy_body_pitch
  LDA cy_tempo_countdown
  CMP #$01
  BNE cy_body_pitch
  LDY cy_sid_offsets,X
  LDA #$02
  STA $D406,Y
cy_body_pitch:
  LDA cy_base_pitch,X
  STA cy_current_pitch,X
  RTS

cy_writer:
  LDY cy_sid_offsets,X
  LDA cy_output_wave,X
  AND cy_gate_mask,X
  STA $D404,Y
  LDA cy_frequency_lo,X
  STA $D400,Y
  LDA cy_frequency_hi,X
  STA $D401,Y
  LDA cy_pulse_output_lo,X
  STA $D402,Y
  LDA cy_pulse_output_hi,X
  STA $D403,Y
  RTS
