entry_init:
  CLD
  JSR aw_restore_state
  JSR aw_fixed_output
  JSR aw_consume_row
aw_init_done:
  RTS

entry_play:
  CLD
  LDA aw_ending_phase
  CMP #$02
  BNE aw_check_ending
  JMP aw_call_done
aw_check_ending:
  LDA #AW_ENDING_ENABLED
  BEQ aw_play_music
  LDA aw_ending_phase
  BNE aw_check_stop
  LDA aw_call_hi
  CMP #AW_END_START_HI
  BNE aw_play_music
  LDA aw_call_lo
  CMP #AW_END_START_LO
  BNE aw_play_music
  JSR aw_close_gates
  LDA #$01
  STA aw_ending_phase
  JMP aw_increment_call
aw_check_stop:
  LDA aw_call_hi
  CMP #AW_END_STOP_HI
  BNE aw_increment_call
  LDA aw_call_lo
  CMP #AW_END_STOP_LO
  BNE aw_increment_call
  LDX #$00
aw_stop_voices:
  LDY aw_sid_offsets,X
  LDA #$00
  STA aw_control,X
  STA $d404,Y
  INX
  CPX #$03
  BNE aw_stop_voices
  LDA #$00
  STA aw_volume
  STA $d418
  LDA #$02
  STA aw_ending_phase
  JMP aw_call_done

aw_play_music:
  JSR aw_fixed_output
  DEC aw_countdown
  LDA aw_countdown
  CMP #$ff
  BNE aw_increment_call
  LDA aw_next_row
  CMP #AW_ROW_COUNT
  BNE aw_dispatch_row
  LDA #$00
  STA aw_next_row
  JSR aw_fixed_output
aw_dispatch_row:
  JSR aw_consume_row
aw_increment_call:
  INC aw_call_lo
  BNE aw_call_done
  INC aw_call_hi
aw_call_done:
  RTS

aw_fixed_output:
  LDA #AW_VOLUME
  STA aw_volume
  STA $d418
  LDA #AW_PULSE_HIGH_0
  STA aw_pulse_high
  STA $d403
  LDA #AW_PULSE_HIGH_1
  STA aw_pulse_high++1
  STA $d40a
  RTS

aw_close_gates:
  LDX #$00
aw_close_voice:
  LDY aw_sid_offsets,X
  LDA aw_control,X
  AND #$fe
  STA aw_control,X
  STA $d404,Y
  INX
  CPX #$03
  BNE aw_close_voice
  RTS

aw_consume_row:
  LDX aw_next_row
  LDA aw_row_ptr_lo,X
  STA $e0
  LDA aw_row_ptr_hi,X
  STA $e1
  LDY #$00
  LDA ($e0),Y
  STA aw_countdown
  INY
  STY $e2
  LDX #$00
aw_row_voice:
  LDY $e2
  LDA ($e0),Y
  BEQ aw_next_voice
  CMP #$01
  BNE aw_pitched_voice
  LDY aw_sid_offsets,X
  LDA aw_control,X
  AND #$fe
  STA aw_control,X
  STA $d404,Y
  JMP aw_next_voice
aw_pitched_voice:
  INY
  LDA ($e0),Y
  STA aw_frequency_hi,X
  INY
  LDA ($e0),Y
  STA aw_frequency_lo,X
  LDY aw_sid_offsets,X
  LDA aw_patch_ad,X
  STA aw_attack_decay,X
  STA $d405,Y
  LDA aw_patch_sr,X
  STA aw_sustain_release,X
  STA $d406,Y
  LDA #$00
  STA $d404,Y
  LDA aw_patch_control,X
  STA aw_control,X
  STA $d404,Y
  LDA aw_frequency_hi,X
  STA $d401,Y
  LDA aw_frequency_lo,X
  STA $d400,Y
aw_next_voice:
  LDA $e2
  CLC
  ADC #$03
  STA $e2
  INX
  CPX #$03
  BNE aw_row_voice
  INC aw_next_row
  RTS
