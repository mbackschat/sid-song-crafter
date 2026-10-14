entry_init:
  CLD
  JSR bj_restore_state
  LDA #$00
  STA $d404
  STA $d40b
  STA $d412
bj_init_done:
  RTS

entry_play:
  CLD
  LDA bj_ending_phase
  CMP #$02
  BNE bj_check_ending
  JMP bj_call_done
bj_check_ending:
  LDA #BJ_ENDING_ENABLED
  BEQ bj_play_music
  LDA bj_call_hi
  CMP #BJ_END_START_HI
  BNE bj_check_release_phase
  LDA bj_call_lo
  CMP #BJ_END_START_LO
  BNE bj_check_release_phase
  LDA #$01
  STA bj_ending_phase
  LDA bj_held_control
  AND #$fe
  STA bj_held_control
  STA $d404
  LDA bj_held_control++1
  AND #$fe
  STA bj_held_control++1
  STA $d40b
  LDA bj_held_control++2
  AND #$fe
  STA bj_held_control++2
  STA $d412
  JMP bj_increment_call
bj_check_release_phase:
  LDA bj_ending_phase
  BEQ bj_play_music
  LDA bj_call_hi
  CMP #BJ_END_STOP_HI
  BNE bj_increment_call
  LDA bj_call_lo
  CMP #BJ_END_STOP_LO
  BNE bj_increment_call
  LDA #$00
  STA bj_held_control
  STA bj_held_control++1
  STA bj_held_control++2
  STA $d404
  STA $d40b
  STA $d412
  LDA bj_mode_volume
  AND #$f0
  STA bj_mode_volume
  STA $d418
  LDA #$02
  STA bj_ending_phase
  JMP bj_call_done

bj_play_music:
  DEC bj_divider
  BPL bj_process_voices
  LDA #BJ_DIVIDER_RELOAD
  STA bj_divider
bj_process_voices:
  LDX #$02
bj_voice_loop:
  LDA bj_divider
  BNE bj_voice_body
  DEC bj_remaining,X
  LDA bj_remaining,X
  BPL bj_voice_body
  JSR bj_score_row
  LDA $d3
  BEQ bj_voice_body
  LDA bj_gate_mask,X
  AND #$01
  STA $d4
  JSR bj_note_setup
  LDA bj_sound_failed
  BEQ bj_setup_valid
  JMP bj_voice_failed
bj_setup_valid:
  LDA $d4
  BNE bj_project_control
  LDA #$09
  STA bj_held_control,X
  JMP bj_voice_age
bj_voice_body:
  JSR bj_body
  LDA bj_sound_failed
  BEQ bj_project_control
bj_voice_failed:
  LDA #$01
  STA bj_failed
  JMP bj_increment_call
bj_project_control:
  LDA bj_waveform,X
  AND bj_gate_mask,X
  STA bj_held_control,X
bj_voice_age:
  JSR bj_advance_age
  DEX
  BPL bj_voice_loop
  JSR bj_global_output
  LDA bj_filter_mode
  ORA #$0b
  STA bj_mode_volume
bj_increment_call:
  INC bj_call_lo
  BNE bj_call_done
  INC bj_call_hi
bj_call_done:
  RTS

bj_score_row:
  LDA bj_order_ptr_lo,X
  STA $d0
  LDA bj_order_ptr_hi,X
  STA $d1
  LDY bj_order_cursor,X
  LDA ($d0),Y
  CMP #$ff
  BNE bj_order_commands
  LDA #$00
  STA bj_order_cursor
  STA bj_order_cursor++1
  STA bj_order_cursor++2
  TAY
  LDA ($d0),Y
bj_order_commands:
  BPL bj_order_pattern
  AND #$7f
  STA bj_transpose,X
  INY
  TYA
  STA bj_order_cursor,X
  LDA ($d0),Y
bj_order_pattern:
  STA bj_pattern_index,X
  TAY
  LDA bj_pattern_ptr_lo,Y
  STA $d0
  LDA bj_pattern_ptr_hi,Y
  STA $d1
  LDY bj_pattern_cursor,X
  LDA ($d0),Y
  STA $d2
  AND #$1f
  STA bj_remaining,X
  LDA $d2
  AND #$e0
  CMP #$c0
  BNE bj_note_row
  LDA #$00
  STA $d3
  LDA #$fe
  STA bj_gate_mask,X
  JMP bj_finish_row
bj_note_row:
  LDA #$01
  STA $d3
  LDA #$00
  STA bj_glide_step,X
  LDA $d2
  AND #$20
  STA bj_hold,X
  LDA $d2
  AND #$80
  BEQ bj_note_glide
  INY
  LDA ($d0),Y
  ASL A
  ASL A
  ASL A
  STA bj_instrument_offset,X
bj_note_glide:
  LDA $d2
  AND #$40
  BEQ bj_note_value
  INY
  LDA ($d0),Y
  STA bj_glide_step,X
  INY
  LDA ($d0),Y
  CLC
  ADC bj_transpose,X
  STA bj_glide_target,X
bj_note_value:
  INY
  LDA ($d0),Y
  CLC
  ADC bj_transpose,X
  STA bj_base_note,X
bj_finish_row:
  INY
  LDA ($d0),Y
  CMP #$ff
  BNE bj_save_pattern_cursor
  INC bj_order_cursor,X
  LDY #$00
bj_save_pattern_cursor:
  TYA
  STA bj_pattern_cursor,X
  RTS
