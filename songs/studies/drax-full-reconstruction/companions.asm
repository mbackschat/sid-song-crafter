; Independent pulse lead and two-call chord sequencer.
; Parameters and provenance are owned by this study's instrument.json and README.md.
entry_init:
  JSR init
  LDA #$00
  LDX #$01
comp_clear:
  STA comp_active,X
  STA comp_age,X
  STA comp_index,X
  STA comp_control,X
  STA comp_vibrato,X
  STA comp_pwlo,X
  LDA comp_initial_hi,X
  STA comp_pwhi,X
  LDA #$01
  STA comp_direction,X
  LDA comp_ad_value,X
  STA comp_ad,X
  LDA comp_sr_value,X
  STA comp_sr,X
  LDA #$00
  DEX
  BPL comp_clear
  RTS
entry_play:
  LDA tick
  CMP #PLAY_CALLS
  BCC full_active
  JMP play
full_active:
  LDX #$01
  JSR comp_play
  LDX #$00
  JSR comp_play
  JMP play
comp_play:
  LDA comp_offsets,X
  STA comp_offset
  LDY comp_index,X
  CPX #$00
  BEQ lead_schedule
  CPY #$01
  BCS comp_evolve
  LDA #CHORD_INIT
  JMP check_comp_schedule
lead_schedule:
  CPY #LEAD_COUNT
  BCS comp_evolve
  LDA lead_calls,Y
check_comp_schedule:
  STA comp_next
  SEC
  SBC #$02
  CMP tick
  BNE comp_check_reset
  JMP comp_restart
comp_check_reset:
  LDA comp_next
  SEC
  SBC #$01
  CMP tick
  BNE comp_check_init
  JMP comp_reset
comp_check_init:
  LDA comp_next
  CMP tick
  BNE comp_evolve
  JMP comp_start
comp_evolve:
  JSR comp_move
  LDA comp_active,X
  BNE comp_instrument
  LDA tick
  BNE comp_pre_second
  LDA #PRE_FIRST_LO
  STA comp_freqlo,X
  LDA #PRE_FIRST_HI
  STA comp_freqhi,X
  JMP comp_write
comp_pre_second:
  CMP #$01
  BNE comp_pre_body
  LDA #PRE_SECOND_LO
  STA comp_freqlo,X
  LDA #PRE_SECOND_HI
  STA comp_freqhi,X
  JMP comp_write
comp_pre_body:
  LDA #PRE_BODY_LO
  STA comp_freqlo,X
  LDA #PRE_BODY_HI
  STA comp_freqhi,X
  LDA #$40
  STA comp_control,X
  JMP comp_write
comp_instrument:
  INC comp_age,X
  LDA comp_age,X
  CMP #GATE_CLOSE_AGE
  BCS comp_gate_closed
  LDA comp_waves,X
  ORA #$01
  JMP comp_set_control
comp_gate_closed:
  LDA comp_waves,X
comp_set_control:
  STA comp_control,X
  CPX #$01
  BNE comp_lead_pitch
  LDA comp_age,X
  SEC
  SBC #$01
  LSR A
chord_modulo:
  CMP #$03
  BCC chord_pitch
  SEC
  SBC #$03
  JMP chord_modulo
chord_pitch:
  TAY
  LDA chord_lo,Y
  STA comp_freqlo,X
  LDA chord_hi,Y
  STA comp_freqhi,X
  JMP comp_write
comp_lead_pitch:
  LDA comp_age,X
  CMP #VIBRATO_START_AGE
  BCC comp_base_pitch
  INC comp_vibrato,X
  LDA comp_vibrato,X
  AND #$07
  TAY
  CLC
  LDA comp_baselo,X
  ADC vibrato_lo,Y
  STA comp_freqlo,X
  LDA comp_basehi,X
  ADC vibrato_hi,Y
  STA comp_freqhi,X
  JMP comp_write
comp_base_pitch:
  LDA comp_baselo,X
  STA comp_freqlo,X
  LDA comp_basehi,X
  STA comp_freqhi,X
  JMP comp_write
comp_restart:
  LDY comp_offset
  LDA #RESTART_AD
  STA comp_ad,X
  STA $D405,Y
  LDA #RESTART_SR
  STA comp_sr,X
  STA $D406,Y
  RTS
comp_reset:
  JSR comp_move
  LDY comp_index,X
  CPX #$01
  BNE comp_lead_reset
  LDA chord_lo
  STA comp_baselo,X
  LDA chord_hi
  JMP comp_reset_pitch
comp_lead_reset:
  LDA lead_lo,Y
  STA comp_baselo,X
  LDA lead_hi,Y
comp_reset_pitch:
  STA comp_basehi,X
  STA comp_freqhi,X
  LDA comp_baselo,X
  STA comp_freqlo,X
  LDA #$00
  STA comp_ad,X
  STA comp_sr,X
  LDA #$08
  STA comp_control,X
  JMP comp_write
comp_start:
  LDA #$00
  STA comp_age,X
  STA comp_vibrato,X
  LDA #$01
  STA comp_active,X
  LDA #$00
  STA comp_direction,X
  CPX #$01
  BEQ comp_start_envelope
  LDA #LEAD_PULSE_LO
  STA comp_pwlo,X
  LDA #LEAD_PULSE_HI
  STA comp_pwhi,X
comp_start_envelope:
  LDY comp_offset
  LDA comp_ad_value,X
  STA comp_ad,X
  STA $D405,Y
  LDA comp_sr_value,X
  STA comp_sr,X
  STA $D406,Y
  LDA #$09
  STA comp_control,X
  STA $D404,Y
  INC comp_index,X
  RTS
comp_move:
  CPX #$01
  BEQ comp_move_done
  LDA comp_direction,X
  BNE comp_subtract
  CLC
  LDA comp_pwlo,X
  ADC #LEAD_STEP
  STA comp_pwlo,X
  LDA comp_pwhi,X
  ADC #$00
  STA comp_pwhi,X
  LDA comp_active,X
  BNE comp_main_upper
  LDA comp_pwhi,X
  CMP #LEAD_PRE_BOUND
  BEQ comp_reverse
  RTS
comp_main_upper:
  LDA comp_pwhi,X
  CMP #LEAD_UPPER
  BNE comp_move_done
  JMP comp_reverse
comp_subtract:
  SEC
  LDA comp_pwlo,X
  SBC #LEAD_STEP
  STA comp_pwlo,X
  LDA comp_pwhi,X
  SBC #$00
  STA comp_pwhi,X
  LDA comp_active,X
  BNE comp_main_lower
  LDA comp_pwhi,X
  CMP #LEAD_PRE_BOUND
  BEQ comp_reverse
  RTS
comp_main_lower:
  LDA comp_pwhi,X
  CMP #LEAD_LOWER
  BNE comp_move_done
comp_reverse:
  LDA comp_direction,X
  EOR #$01
  STA comp_direction,X
comp_move_done:
  RTS
comp_write:
  LDY comp_offset
  LDA comp_pwlo,X
  STA $D402,Y
  LDA comp_pwhi,X
  STA $D403,Y
  ; Original writer slots repeat the previous bass cutoff before its own update.
  LDA cutoff_hi
  STA $D416
  LDA comp_freqlo,X
  STA $D400,Y
  LDA comp_freqhi,X
  STA $D401,Y
  LDA comp_ad,X
  STA $D405,Y
  LDA comp_sr,X
  STA $D406,Y
  LDA comp_control,X
  STA $D404,Y
  RTS
comp_active:
  .byte $00,$00
comp_age:
  .byte $00,$00
comp_index:
  .byte $00,$00
comp_control:
  .byte $00,$00
comp_vibrato:
  .byte $00,$00
comp_pwlo:
  .byte $00,$00
comp_pwhi:
  .byte $00,$00
comp_direction:
  .byte $00,$00
comp_freqlo:
  .byte $00,$00
comp_freqhi:
  .byte $00,$00
comp_baselo:
  .byte $00,$00
comp_basehi:
  .byte $00,$00
comp_ad:
  .byte $00,$00
comp_sr:
  .byte $00,$00
comp_offset:
  .byte $00
comp_next:
  .byte $00
comp_offsets:
  .byte $07,$0e
comp_initial_hi:
  .byte LEAD_PRE_PULSE_HI,CHORD_PULSE_HI
comp_ad_value:
  .byte LEAD_AD,CHORD_AD
comp_sr_value:
  .byte LEAD_SR,CHORD_SR
comp_waves:
  .byte LEAD_WAVE,CHORD_WAVE
