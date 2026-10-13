entry_init:
  CLD
  JSR mo_restore_state
  LDA #$00
  STA $D404
  STA $D40B
  STA $D412
mo_init_done:
  RTS

entry_play:
  CLD
  LDA mo_stopped
  BEQ mo_frame_start
  RTS
mo_frame_start:
  LDA #MO_HAS_ENDING
  BEQ mo_output_volume
  LDA mo_tail
  BNE mo_tail_volume
  LDA mo_tick_hi
  CMP #MO_MUSIC_HI
  BNE mo_output_volume
  LDA mo_tick_lo
  CMP #MO_MUSIC_LO
  BNE mo_output_volume
  INC mo_tail
mo_tail_volume:
  LDA mo_tail_age
  CMP #$40
  BCC mo_output_volume
  SEC
  SBC #$40
  LSR A
  LSR A
  EOR #$0F
  STA mo_volume_scratch
  LDA mo_mode_volume
  AND #$F0
  ORA mo_volume_scratch
  STA mo_mode_volume
mo_output_volume:
  LDA mo_mode_volume
  STA $D418
  INC mo_counter
  LDA mo_tail
  BEQ mo_music_status
  LDA #$00
  STA mo_score_tick
  LDA mo_tail_age
  BNE mo_start_voices
  LDX #$02
mo_release_controls:
  LDA mo_actual_control,X
  AND #$FE
  JSR mo_write_control
  DEX
  BPL mo_release_controls
  JMP mo_start_voices
mo_music_status:
  LDA mo_status
  AND #$40
  BEQ mo_tempo
  LDA #$00
  STA mo_counter
  STA mo_status
  LDX #$02
mo_restart_sequence:
  STA mo_order_cursor,X
  STA mo_pattern_cursor,X
  STA mo_remaining,X
  STA mo_note,X
  DEX
  BPL mo_restart_sequence
mo_tempo:
  DEC mo_tempo_countdown
  BPL mo_tempo_ready
  LDA mo_tempo_reload
  STA mo_tempo_countdown
mo_tempo_ready:
  LDA #$00
  STA mo_score_tick
  LDA mo_tempo_countdown
  CMP mo_tempo_reload
  BNE mo_start_voices
  INC mo_score_tick
mo_start_voices:
  LDX #$02
mo_voice_loop:
  LDA mo_score_tick
  BEQ mo_voice_body
  DEC mo_remaining,X
  BPL mo_voice_body
  JSR mo_consume_row
  JMP mo_next_voice
mo_voice_body:
  JSR mo_advance_body
mo_next_voice:
  DEX
  BPL mo_voice_loop
  INC mo_tick_lo
  BNE mo_tick_ready
  INC mo_tick_hi
mo_tick_ready:
  LDA mo_tail
  BEQ mo_call_done
  INC mo_tail_age
  LDA mo_tail_age
  CMP #$80
  BNE mo_call_done
  INC mo_stopped
mo_call_done:
  RTS

mo_consume_row:
  LDA mo_order_ptr_lo,X
  STA mo_order_read+1
  LDA mo_order_ptr_hi,X
  STA mo_order_read+2
mo_select_pattern:
  LDY mo_order_cursor,X
mo_order_read:
  LDA $FFFF,Y
  CMP #$FF
  BNE mo_pattern_pointer
  LDA #$00
  STA mo_remaining,X
  STA mo_order_cursor,X
  STA mo_pattern_cursor,X
  JMP mo_select_pattern
mo_pattern_pointer:
  TAY
  LDA mo_pattern_ptr_lo,Y
  STA mo_pattern_read+1
  LDA mo_pattern_ptr_hi,Y
  STA mo_pattern_read+2
  LDA #$00
  STA mo_portamento,X
  STA mo_append
  LDY mo_pattern_cursor,X
  JSR mo_pattern_read
  STA mo_control,X
  AND #$1F
  STA mo_remaining,X
  LDA mo_control,X
  AND #$40
  BNE mo_append_row
  INY
  INC mo_pattern_cursor,X
  LDA mo_control,X
  BPL mo_pitch_row
  JSR mo_pattern_read
  BMI mo_portamento_row
  STA mo_instrument_index,X
  JMP mo_parameter_done
mo_portamento_row:
  STA mo_portamento,X
mo_parameter_done:
  INY
  INC mo_pattern_cursor,X
mo_pitch_row:
  JSR mo_pattern_read
  STA mo_note,X
  JMP mo_initialize_row
mo_append_row:
  INC mo_append
mo_initialize_row:
  JSR mo_initialize_note
  INC mo_pattern_cursor,X
  LDY mo_pattern_cursor,X
  JSR mo_pattern_read
  CMP #$FF
  BNE mo_row_done
  LDA #$00
  STA mo_pattern_cursor,X
  INC mo_order_cursor,X
mo_row_done:
  RTS

mo_pattern_read:
  LDA $FFFF,Y
  RTS

mo_write_control:
  PHA
  LDY mo_tail
  BEQ mo_control_ready
  AND #$FE
mo_control_ready:
  STA mo_actual_control,X
  LDY mo_sid_offsets,X
  STA $D404,Y
  PLA
  RTS

mo_lookup_base:
  ASL A
  TAY
  JMP mo_lookup_word

mo_lookup_adjacent:
  ASL A
  CLC
  ADC #$02
  BCS mo_lookup_overflow
  TAY
mo_lookup_word:
  JSR mo_lookup_byte
  STA mo_lookup_lo
  INY
  JSR mo_lookup_byte
  STA mo_lookup_hi
  RTS

mo_lookup_byte:
  LDA mo_lookup_ptr_lo,Y
  STA mo_lookup_read+1
  LDA mo_lookup_ptr_hi,Y
  STA mo_lookup_read+2
mo_lookup_read:
  LDA $FFFF
  RTS

mo_lookup_overflow:
  LDA MO_ALIAS_256
  STA mo_lookup_lo
  LDA MO_ALIAS_257
  STA mo_lookup_hi
  RTS
