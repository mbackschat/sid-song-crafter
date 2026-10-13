rb_advance_sound:
  ; scripts/rambo_programs.py defines unsigned word addition, regardless of caller mode.
  CLD
  LDA rb_sound_ptr_lo,X
  STA $f0
  LDA rb_sound_ptr_hi,X
  STA $f1
  LDA rb_sid_offsets,X
  STA $f2
  LDY #$1c
  LDA ($f0),Y
  BNE rb_sound_lifetime
  RTS
rb_sound_lifetime:
  LDY #$1a
  LDA ($f0),Y
  AND #$08
  BEQ rb_sound_release
  LDY #$1b
  LDA rb_remaining,X
  CMP ($f0),Y
  BCC rb_sound_row_release
  JMP rb_sound_pwm
rb_sound_row_release:
  LDA #$00
  STA ($f0),Y
  DEY
  LDA ($f0),Y
  AND #$f6
  STA ($f0),Y
  BEQ rb_sound_decay
  LDY $f2
  STA $d404,Y
  JMP rb_sound_pwm
rb_sound_release:
  LDY #$1b
  LDA ($f0),Y
  BEQ rb_sound_decay
  SEC
  SBC #$01
  STA ($f0),Y
  BNE rb_sound_pwm
  DEY
  LDA ($f0),Y
  AND #$f6
  LDY $f2
  STA $d404,Y
  JMP rb_sound_pwm
rb_sound_decay:
  LDY #$1c
  LDA ($f0),Y
  SEC
  SBC #$01
  STA ($f0),Y
  BNE rb_sound_pwm
  LDA $f2
  CLC
  ADC #$06
  TAY
  LDA #$00
rb_sound_terminal_clear:
  STA $d400,Y
  CPY $f2
  BEQ rb_sound_done
  DEY
  JMP rb_sound_terminal_clear
rb_sound_done:
  RTS

rb_sound_pwm:
  LDY #$11
  LDA ($f0),Y
  BNE rb_sound_pwm_delay
  JMP rb_sound_frequency
rb_sound_pwm_delay:
  DEY
  LDA ($f0),Y
  BEQ rb_sound_pwm_phase
  SEC
  SBC #$01
  STA ($f0),Y
  JMP rb_sound_frequency
rb_sound_pwm_phase:
  LDY #$25
  LDA ($f0),Y
  BNE rb_sound_pwm_step
  INY
  LDA ($f0),Y
  BNE rb_sound_pwm_step
  LDY #$11
  LDA ($f0),Y
  AND #$81
  BNE rb_sound_pwm_reload
  JMP rb_sound_pwm_store
rb_sound_pwm_reload:
  LDY #$0e
  LDA ($f0),Y
  LDY #$25
  STA ($f0),Y
  LDY #$0f
  LDA ($f0),Y
  LDY #$26
  STA ($f0),Y
  LDY #$11
  LDA ($f0),Y
  AND #$80
  BEQ rb_sound_pwm_phase
  LDY #$16
  LDA ($f0),Y
  LDY #$23
  STA ($f0),Y
  LDY #$17
  LDA ($f0),Y
  LDY #$24
  STA ($f0),Y
  JMP rb_sound_pwm_phase
rb_sound_pwm_step:
  SEC
  SBC #$01
  STA ($f0),Y
  TYA
  SEC
  SBC #$25
  ASL A
  CLC
  ADC #$12
  TAY
  LDA ($f0),Y
  STA $f5
  INY
  LDA ($f0),Y
  STA $f6
  LDY #$23
  LDA ($f0),Y
  CLC
  ADC $f5
  STA ($f0),Y
  INY
  LDA ($f0),Y
  ADC $f6
  STA ($f0),Y
rb_sound_pwm_store:
  LDY #$23
  LDA ($f0),Y
  LDY $f2
  STA $d402,Y
  LDY #$24
  LDA ($f0),Y
  LDY $f2
  STA $d403,Y

rb_sound_frequency:
  LDY #$0d
  LDA ($f0),Y
  BNE rb_sound_frequency_mode
  RTS
rb_sound_frequency_mode:
  STA $f7
  CPX #$01
  BEQ rb_sound_frequency_delay
  AND #$08
  BEQ rb_sound_frequency_delay
  JMP rb_sound_arpeggio
rb_sound_frequency_delay:
  LDY #$0c
  LDA ($f0),Y
  BEQ rb_sound_frequency_phase_start
  SEC
  SBC #$01
  STA ($f0),Y
  LDA $f7
  AND #$02
  BNE rb_sound_frequency_delayed_step
  RTS
rb_sound_frequency_delayed_step:
  LDY #$06
  JMP rb_sound_frequency_add
rb_sound_frequency_phase_start:
  LDY #$1f
rb_sound_frequency_phase:
  LDA ($f0),Y
  BNE rb_sound_frequency_step
  INY
  CPY #$22
  BCC rb_sound_frequency_phase
  ; Full-title capture evidence/rambo-sound-full proves only voice 0 uses phase four.
  CPX #$00
  BNE rb_sound_frequency_reload
  LDA ($f0),Y
  BNE rb_sound_frequency_step
rb_sound_frequency_reload:
  LDY #$08
rb_sound_frequency_reload_counter:
  LDA ($f0),Y
  PHA
  TYA
  CLC
  ADC #$17
  TAY
  PLA
  STA ($f0),Y
  TYA
  SEC
  SBC #$16
  TAY
  CPY #$0c
  BNE rb_sound_frequency_reload_counter
  JMP rb_sound_frequency_phase_start
rb_sound_frequency_step:
  SEC
  SBC #$01
  STA ($f0),Y
  TYA
  SEC
  SBC #$1f
  ASL A
  TAY
rb_sound_frequency_add:
  LDA ($f0),Y
  STA $f5
  INY
  LDA ($f0),Y
  STA $f6
  LDY #$1d
  LDA ($f0),Y
  CLC
  ADC $f5
  STA ($f0),Y
  INY
  LDA ($f0),Y
  ADC $f6
  STA ($f0),Y
  JMP rb_sound_frequency_store

rb_sound_arpeggio:
  LDY #$0c
  LDA ($f0),Y
  BPL rb_sound_arpeggio_position
  LDY #$0b
  LDA ($f0),Y
rb_sound_arpeggio_position:
  STA $f9
  TAY
  LDA ($f0),Y
  STA $f5
  LDY #$0a
  LDA ($f0),Y
  CLC
  ADC $f5
  TAY
  LDA rb_frequency_lo,Y
  STA $f5
  LDA rb_frequency_hi,Y
  STA $f6
  LDY #$0c
  LDA $f9
  SEC
  SBC #$01
  STA ($f0),Y
  LDY #$1d
  LDA $f5
  STA ($f0),Y
  INY
  LDA $f6
  STA ($f0),Y
rb_sound_frequency_store:
  LDY #$1d
  LDA ($f0),Y
  LDY $f2
  STA $d400,Y
  LDY #$1e
  LDA ($f0),Y
  LDY $f2
  STA $d401,Y
  RTS
