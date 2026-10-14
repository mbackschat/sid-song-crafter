entry_init:
  CLD
  JSR tm_restore_state
  LDA #$00
  STA $d404
  STA $d40b
  STA $d412
  LDA tm_mix_routing
  STA $d417
  LDA tm_mode_volume
  STA $d418
tm_init_done:
  RTS

entry_play:
  CLD
  LDA tm_ending_phase
  CMP #$02
  BNE tm_check_ending
  JMP tm_call_done
tm_check_ending:
  LDA #TM_ENDING_ENABLED
  BEQ tm_play_music
  LDA tm_call_hi
  CMP #TM_END_START_HI
  BNE tm_check_release_phase
  LDA tm_call_lo
  CMP #TM_END_START_LO
  BNE tm_check_release_phase
  LDA #$01
  STA tm_ending_phase
  LDA tm_control
  AND #$fe
  STA tm_control
  STA $d404
  LDA tm_control++1
  AND #$fe
  STA tm_control++1
  STA $d40b
  LDA tm_control++2
  AND #$fe
  STA tm_control++2
  STA $d412
  JMP tm_increment_call
tm_check_release_phase:
  LDA tm_ending_phase
  BEQ tm_play_music
  LDA tm_call_hi
  CMP #TM_END_STOP_HI
  BNE tm_increment_call
  LDA tm_call_lo
  CMP #TM_END_STOP_LO
  BNE tm_increment_call
  LDA #$00
  STA tm_control
  STA tm_control++1
  STA tm_control++2
  JSR tm_stop_controls
  LDA tm_mode_volume
  AND #$f0
  STA tm_mode_volume
  STA $d418
  LDA #$02
  STA tm_ending_phase
  JMP tm_call_done
tm_play_music:
  LDA tm_active
  BEQ tm_increment_call
  DEC tm_divider_a
  BPL tm_second_divider
  LDA #TM_DIVIDER_A_RELOAD
  STA tm_divider_a
  BNE tm_process_voices
tm_second_divider:
  DEC tm_divider_b
  BPL tm_process_voices
  LDA #TM_DIVIDER_B_RELOAD
  STA tm_divider_b
  DEC tm_remaining
  DEC tm_remaining++1
  DEC tm_remaining++2
tm_process_voices:
  LDX #$02
tm_voice_loop:
  LDA tm_remaining,X
  BNE tm_voice_body
  JSR tm_score_row
  LDA tm_active
  BEQ tm_increment_call
  JSR tm_note_setup
  JMP tm_voice_emit
tm_voice_body:
  JSR tm_body
tm_voice_emit:
  LDA tm_sound_failed
  BEQ tm_voice_valid
  LDA #$01
  STA tm_failed
  JMP tm_increment_call
tm_voice_valid:
  JSR tm_voice_output
  DEX
  BPL tm_voice_loop
  JSR tm_filter_output
tm_increment_call:
  INC tm_call_lo
  BNE tm_call_done
  INC tm_call_hi
tm_call_done:
  RTS

tm_stop_controls:
  LDA #$00
  STA $d404
  STA $d40b
  STA $d412
  RTS

tm_score_row:
  LDA #$00
  STA tm_glide_active,X
  STA tm_onset_initial,X
  STA tm_arpeggio_cursor,X
  STA tm_waveform_cursor,X
  STA tm_pitch_cursor,X
  STA tm_pulse_initial,X
  STA tm_vibrato_initial,X
  LDA tm_order_ptr_lo,X
  STA $d0
  LDA tm_order_ptr_hi,X
  STA $d1
  LDY tm_order_cursor,X
  LDA ($d0),Y
  CMP #$fe
  BNE tm_order_not_stop
  LDA #$00
  STA tm_active
  JMP tm_stop_controls
tm_order_not_stop:
  CMP #$ff
  BNE tm_order_commands
  INY
  LDA ($d0),Y
  STA tm_order_cursor,X
  TAY
  LDA ($d0),Y
tm_order_commands:
  BPL tm_order_pattern
  CMP #$c0
  BCC tm_order_transpose
  AND #$1f
  STA tm_repeat,X
  INY
  LDA ($d0),Y
tm_order_transpose:
  CMP #$80
  BCC tm_order_cursor_save
  AND #$1f
  STA tm_transpose,X
  INY
tm_order_cursor_save:
  TYA
  STA tm_order_cursor,X
  LDA ($d0),Y
tm_order_pattern:
  TAY
  LDA tm_pattern_ptr_lo,Y
  STA $d0
  LDA tm_pattern_ptr_hi,Y
  STA $d1
  LDY tm_pattern_cursor,X
  LDA ($d0),Y
  BPL tm_pattern_note
  CMP #$fe
  BNE tm_pattern_instrument
  INY
  LDA ($d0),Y
  STA tm_arpeggio,X
  INY
  LDA ($d0),Y
tm_pattern_instrument:
  CMP #$c0
  BCC tm_pattern_duration
  AND #$1f
  STA tm_instrument,X
  INY
  LDA ($d0),Y
tm_pattern_duration:
  CMP #$80
  BCC tm_pattern_note
  AND #$7f
  ASL A
  STA tm_duration,X
  INY
  LDA ($d0),Y
tm_pattern_note:
  CMP #$60
  BNE tm_plain_note
  INY
  LDA ($d0),Y
  STA tm_glide_step_lo,X
  INY
  LDA ($d0),Y
  STA tm_glide_step_hi,X
  INY
  LDA ($d0),Y
  CLC
  ADC tm_transpose,X
  STA tm_base_note,X
  INY
  LDA ($d0),Y
  ADC tm_transpose,X
  STA tm_glide_target,X
  LDA #$01
  STA tm_glide_active,X
  JMP tm_note_duration
tm_plain_note:
  CLC
  ADC tm_transpose,X
  STA tm_base_note,X
tm_note_duration:
  LDA tm_duration,X
  STA tm_remaining,X
  INY
  LDA ($d0),Y
  CMP #$ff
  BNE tm_pattern_cursor_save
  LDA tm_repeat,X
  BEQ tm_advance_order
  DEC tm_repeat,X
  JMP tm_restart_pattern
tm_advance_order:
  INC tm_order_cursor,X
tm_restart_pattern:
  LDY #$00
tm_pattern_cursor_save:
  TYA
  STA tm_pattern_cursor,X
  RTS
