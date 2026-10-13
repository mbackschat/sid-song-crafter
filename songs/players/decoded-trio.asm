; Computed bass, lead and chord families with absolute 16-bit note scheduling.
; See docs/workflows/decoded-song-workflow.md for timing, ownership and supported limits.
init:
  LDX #$00
  LDA #$00
clear_sid:
  STA $D400,X
  INX
  CPX #$18
  BNE clear_sid
  STA tick
  STA tick_hi
  STA note_index
  STA active
  STA age
  STA control
  LDA #MODE_VOLUME
  STA $D418
  LDA #PRE_PULSE_LO
  STA pulse_lo
  LDA #PRE_PULSE_HI
  STA pulse_hi
  LDA #PRE_DIRECTION
  STA direction
  LDA #PRE_STEP
  STA step
  LDA #PRE_LOWER
  STA lower
  LDA #PRE_UPPER
  STA upper
  LDA #AD
  STA attack_decay
  LDA #SR
  STA sustain_release
  LDA #BODY_CUTOFF
  STA cutoff_hi
  RTS
play:
  LDX tick
scheduled:
  LDY note_index
  CPY #NOTE_COUNT
  BCS evolve
bass_check_restart:
  LDA bass_restart_hi,Y
  CMP tick_hi
  BNE bass_check_prep
  LDA bass_restart_lo,Y
  CMP tick
  BNE bass_check_prep
  JMP hard_restart
bass_check_prep:
  LDA bass_prep_hi,Y
  CMP tick_hi
  BNE bass_check_init
  LDA bass_prep_lo,Y
  CMP tick
  BNE bass_check_init
  JMP reset
bass_check_init:
  LDA bass_init_hi,Y
  CMP tick_hi
  BNE evolve
  LDA bass_init_lo,Y
  CMP tick
  BNE evolve
  JMP start_note
evolve:
  JSR move_pulse
  LDA active
  BNE instrument
  LDA tick_hi
  BNE pre_body
  CPX #$00
  BNE pre_second
  LDA #PRE_FIRST_LO
  STA frequency_lo
  LDA #PRE_FIRST_HI
  STA frequency_hi
  JMP write_body
pre_second:
  CPX #$01
  BNE pre_body
  LDA #PRE_SECOND_LO
  STA frequency_lo
  LDA #PRE_SECOND_HI
  STA frequency_hi
  JMP write_body
pre_body:
  LDA #PRE_BODY_LO
  STA frequency_lo
  LDA #PRE_BODY_HI
  STA frequency_hi
  LDA #RELEASE_CONTROL
  STA control
  JMP write_body
instrument:
  INC age
  LDA age
  CMP #$01
  BNE pulse_body
  LDA #NOISE_LO
  STA frequency_lo
  LDA #NOISE_HI
  STA frequency_hi
  LDA #ATTACK_CUTOFF
  STA cutoff_hi
  LDA #NOISE_CONTROL
  STA control
  JMP write_body
pulse_body:
  LDA base_lo
  STA frequency_lo
  LDA base_hi
  STA frequency_hi
  LDA #BODY_CUTOFF
  STA cutoff_hi
  LDA age
  CMP #$02
  BNE release
  LDA #PULSE_CONTROL
  STA control
  JMP write_body
release:
  LDA #RELEASE_CONTROL
  STA control
  JMP write_body
hard_restart:
  LDA #RESTART_AD
  STA attack_decay
  STA $D405
  LDA #RESTART_SR
  STA sustain_release
  STA $D406
  JMP finish
reset:
  JSR move_pulse
  LDA note_frequency_lo,Y
  STA base_lo
  STA frequency_lo
  LDA note_frequency_hi,Y
  STA base_hi
  STA frequency_hi
  LDA #$00
  STA attack_decay
  STA sustain_release
  LDA #$08
  STA control
  JMP write_body
start_note:
  LDA #PULSE_LO
  STA pulse_lo
  LDA #PULSE_HI
  STA pulse_hi
  LDA #$00
  STA direction
  STA age
  LDA #$01
  STA active
  LDA #PULSE_STEP
  STA step
  LDA #PULSE_LOWER
  STA lower
  LDA #PULSE_UPPER
  STA upper
  LDA #ROUTING
  STA $D417
  LDA #AD
  STA attack_decay
  STA $D405
  LDA #SR
  STA sustain_release
  STA $D406
  LDA #$09
  STA control
  STA $D404
  INC note_index
  JMP finish
move_pulse:
  LDA step
  BEQ pulse_done
  LDA direction
  BNE subtract_pulse
  CLC
  LDA pulse_lo
  ADC step
  STA pulse_lo
  LDA pulse_hi
  ADC #$00
  STA pulse_hi
  CMP upper
  BNE pulse_done
  JMP reverse_pulse
subtract_pulse:
  SEC
  LDA pulse_lo
  SBC step
  STA pulse_lo
  LDA pulse_hi
  SBC #$00
  STA pulse_hi
  CMP lower
  BNE pulse_done
reverse_pulse:
  LDA direction
  EOR #$01
  STA direction
pulse_done:
  RTS
write_body:
  LDA pulse_lo
  STA $D402
  LDA pulse_hi
  STA $D403
  LDA cutoff_hi
  STA $D416
  LDA frequency_lo
  STA $D400
  LDA frequency_hi
  STA $D401
  LDA attack_decay
  STA $D405
  LDA sustain_release
  STA $D406
  LDA control
  STA $D404
finish:
  INC tick
  BNE tick_done
  INC tick_hi
tick_done:
  RTS
tick:
  .byte $00
tick_hi:
  .byte $00
note_index:
  .byte $00
active:
  .byte $00
age:
  .byte $00
pulse_lo:
  .byte $00
pulse_hi:
  .byte $00
direction:
  .byte $00
step:
  .byte $00
lower:
  .byte $00
upper:
  .byte $00
frequency_lo:
  .byte $00
frequency_hi:
  .byte $00
base_lo:
  .byte $00
base_hi:
  .byte $00
attack_decay:
  .byte $00
sustain_release:
  .byte $00
control:
  .byte $00
cutoff_hi:
  .byte $00

; Independent pulse lead and two-call chord sequencer.
; Score-owned releases remain independent of the evolving instrument body.
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
  LDA tick_hi
  CMP #STOP_HI
  BCC full_active
  BNE full_stop
  LDA tick
  CMP #STOP_LO
  BCC full_active
full_stop:
  LDA #$00
  STA $D418
  STA $D404
  STA $D40B
  STA $D412
  RTS
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
  CPX #$01
  BEQ chord_schedule
  CPY #LEAD_COUNT
  BCC lead_check_restart
  JMP comp_evolve
lead_check_restart:
  LDA lead_restart_hi,Y
  CMP tick_hi
  BNE lead_check_prep
  LDA lead_restart_lo,Y
  CMP tick
  BNE lead_check_prep
  JMP comp_restart
lead_check_prep:
  LDA lead_prep_hi,Y
  CMP tick_hi
  BNE lead_check_init
  LDA lead_prep_lo,Y
  CMP tick
  BNE lead_check_init
  JMP comp_reset
lead_check_init:
  LDA lead_init_hi,Y
  CMP tick_hi
  BEQ lead_check_init_low
  JMP comp_evolve
lead_check_init_low:
  LDA lead_init_lo,Y
  CMP tick
  BEQ lead_start
  JMP comp_evolve
lead_start:
  JMP comp_start
chord_schedule:
  CPY #CHORD_COUNT
  BCS comp_evolve
chord_check_restart:
  LDA chord_restart_hi,Y
  CMP tick_hi
  BNE chord_check_prep
  LDA chord_restart_lo,Y
  CMP tick
  BNE chord_check_prep
  JMP comp_restart
chord_check_prep:
  LDA chord_prep_hi,Y
  CMP tick_hi
  BNE chord_check_init
  LDA chord_prep_lo,Y
  CMP tick
  BNE chord_check_init
  JMP comp_reset
chord_check_init:
  LDA chord_init_hi,Y
  CMP tick_hi
  BNE comp_evolve
  LDA chord_init_lo,Y
  CMP tick
  BNE comp_evolve
  JMP comp_start
comp_evolve:
  JSR comp_move
  LDA comp_active,X
  BNE comp_instrument
  LDA tick_hi
  BNE comp_pre_body
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
  CMP comp_gate_age,X
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
  CMP chord_length
  BCC chord_pitch
  SEC
  SBC chord_length
  JMP chord_modulo
chord_pitch:
  CLC
  ADC chord_start
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
  LDA chord_note_lo,Y
  STA comp_baselo,X
  LDA chord_note_hi,Y
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
  LDY comp_index,X
  CPX #$01
  BEQ chord_start_parameters
  LDA lead_gate_ages,Y
  JMP set_gate_age
chord_start_parameters:
  LDA chord_lengths,Y
  STA chord_length
  LDA chord_starts,Y
  STA chord_start
  LDA chord_pulse_high,Y
  STA comp_pwhi,X
  LDA #$00
  STA comp_pwlo,X
  LDA chord_gate_ages,Y
set_gate_age:
  STA comp_gate_age,X
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

comp_gate_age:
  .byte $ff,$ff
chord_length:
  .byte $03
chord_start:
  .byte $00
