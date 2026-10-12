; Independent voice-one player. Instrument state is computed each PAL call.
; The source hash and executed instruction evidence live in instrument.json and README.md.
entry_init:
  JMP init
entry_play:
  JMP play
init:
  LDX #$00
  LDA #$00
clear_sid:
  STA $D400,X
  INX
  CPX #$18
  BNE clear_sid
  STA tick
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
  CPX #PLAY_CALLS
  BCC scheduled
  ; playCalls bounds the editable study even when the host keeps calling play.
  LDA #$00
  STA $D418
  RTS
scheduled:
  LDY note_index
  CPY #NOTE_COUNT
  BCS evolve
  LDA note_calls,Y
  SEC
  SBC #$02
  CMP tick
  BNE check_reset
  JMP hard_restart
check_reset:
  LDA note_calls,Y
  SEC
  SBC #$01
  CMP tick
  BNE check_init
  JMP reset
check_init:
  LDA note_calls,Y
  CMP tick
  BNE evolve
  JMP start_note
evolve:
  JSR move_pulse
  LDA active
  BNE instrument
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
  RTS
tick:
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
