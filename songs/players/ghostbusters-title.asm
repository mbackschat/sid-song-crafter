title_init:
  SEI
  CLD
  LDA #$2f
  STA $00
  LDA #$35
  STA $01
  LDA #$00
  STA $d011
  STA $d01a
  STA $dc0e
  STA $dd0f
  STA title_stage
  LDA #$7f
  STA $dc0d
  STA $dd0d
  LDA $dc0d
  LDA $dd0d
  LDA #$ff
  STA $d019
  LDX #$17
  LDA #$00
title_clear_sid:
  STA $d400,X
  DEX
  BPL title_clear_sid
  LDA #$0f
  STA $d418
  LDA #SPEECH_LO
  STA $d0
  LDA #SPEECH_HI
  STA $d1
  LDA #NMI_LO
  STA $fffa
  LDA #NMI_HI
  STA $fffb
  LDA #IRQ_LO
  STA $fffe
  LDA #IRQ_HI
  STA $ffff
  LDA #$65
  STA $dd06
  LDA #$00
  STA $dd07
  LDA #$82
  STA $dd0d
  LDA #$11
title_sample_timer_start:
  STA $dd0f
title_wait_init:
  LDA title_stage
  BEQ title_wait_init
  JSR MUSIC_INIT
title_music_initialized:
  LDA #$c6
  STA $dc04
  LDA #$42
  STA $dc05
  LDA #$81
  STA $dc0d
title_wait_music:
  LDA title_stage
  CMP #$02
  BNE title_wait_music
  LDA #$11
title_music_timer_start:
  STA $dc0e
  JSR MUSIC_PLAY
  CLI
title_init_return:
  RTS
title_idle:
  JMP title_idle
title_nmi:
  PHA
  TYA
  PHA
  LDA $dd0d
  LDY #$00
  LDA ($d0),Y
  CMP #$ff
  BEQ title_next_sample
  CMP #$fc
  BEQ title_init_marker
  CMP #$fe
  BEQ title_music_marker
title_sample_write:
  STA $d418
  JMP title_next_sample
title_init_marker:
  LDA #$01
  STA title_stage
  JMP title_next_sample
title_music_marker:
  LDA #$00
  STA $dd0f
  LDA #$7f
  STA $dd0d
  LDA $dd0d
  LDA #$02
  STA title_stage
title_next_sample:
  INC $d0
  BNE title_nmi_restore
  INC $d1
title_nmi_restore:
  PLA
  TAY
  PLA
title_nmi_return:
  RTI
title_irq:
  PHA
  TXA
  PHA
  TYA
  PHA
  LDA $dc0d
  JSR MUSIC_PLAY
  PLA
  TAY
  PLA
  TAX
  PLA
  RTI
title_stage:
  .byte $00
