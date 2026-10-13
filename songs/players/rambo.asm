entry_init:
  CLD
  JSR rb_restore_state
  LDA #RB_INITIAL_VOLUME
  STA $d418
  LDX #$17
  LDA #$00
rb_init_clear:
  STA $d400,X
  DEX
  BPL rb_init_clear
rb_init_done:
  RTS

entry_play:
  CLD
  LDA rb_morse_active
  BEQ rb_play_score
  JSR rb_morse
  JMP rb_call_done
rb_play_score:
  JSR rb_refresh
rb_call_done:
  RTS

rb_refresh:
  LDX #$00
rb_refresh_voice:
  JSR rb_step
  INX
  CPX #$03
  BNE rb_refresh_voice
  RTS

rb_step:
  LDA rb_data_ptr_lo,X
  STA $e0
  LDA rb_data_ptr_hi,X
  STA $e1
  LDA rb_sound_ptr_lo,X
  STA $e2
  LDA rb_sound_ptr_hi,X
  STA $e3
  LDA rb_voice_bits,X
  AND rb_active_mask
  BEQ rb_sound
  DEC rb_remaining,X
  BEQ rb_fetch
rb_sound:
  JSR rb_advance_sound
  RTS

rb_fetch:
  LDA rb_cursor_lo,X
  STA $e4
  LDA rb_cursor_hi,X
  STA $e5
  LDY #$01
  LDA ($e4),Y
  STA $e8
  INY
  LDA ($e4),Y
  STA $e9
  INY
  LDA ($e4),Y
  STA $ea
  INY
  LDA ($e4),Y
  STA $eb
  INY
  LDA ($e4),Y
  STA $e6
  INY
  LDA ($e4),Y
  STA $e7
  LDY #$00
  LDA ($e4),Y
  TAY
  LDA rb_kind_ptr_lo,Y
  STA $ee
  LDA rb_kind_ptr_hi,Y
  STA $ef
  JMP ($ee)

rb_continue:
  LDA $e8
  STA rb_cursor_lo,X
  LDA $e9
  STA rb_cursor_hi,X
  JMP rb_fetch

rb_kind_row:
  LDA $ea
  CMP #$60
  BCC rb_row_note_ready
  SEC
  SBC #$60
rb_row_note_ready:
  CMP #$5f
  BEQ rb_row_duration
  STA $ec
  JSR rb_note
rb_row_duration:
  LDA $ea
  CMP #$60
  BCS rb_row_literal
  LDA $eb
  CLC
  ADC #$20
  TAY
  LDA ($e0),Y
  JMP rb_row_length
rb_row_literal:
  LDA $eb
rb_row_length:
  STA rb_remaining,X
  LDA $e8
  STA rb_cursor_lo,X
  LDA $e9
  STA rb_cursor_hi,X
  JMP rb_sound

rb_kind_return:
  INC rb_stack_index,X
  LDA rb_stack_index,X
  CMP #$08
  BNE rb_return_nested
  LDA rb_voice_bits,X
  EOR #$ff
  AND rb_active_mask
  STA rb_active_mask
  RTS
rb_return_nested:
  JSR rb_stack_slot
  LDA rb_return_lo,Y
  STA rb_cursor_lo,X
  LDA rb_return_hi,Y
  STA rb_cursor_hi,X
  JMP rb_fetch

rb_stack_slot:
  CLC
  ADC rb_stack_bases,X
  TAY
  RTS

rb_push:
  LDA rb_stack_index,X
  JSR rb_stack_slot
  LDA $e8
  STA rb_return_lo,Y
  LDA $e9
  STA rb_return_hi,Y
  DEC rb_stack_index,X
  RTS

rb_kind_call_transposed:
  LDA $ea
  STA rb_transpose,X
rb_kind_call:
  JSR rb_push
rb_target:
  LDA $e6
  STA rb_cursor_lo,X
  LDA $e7
  STA rb_cursor_hi,X
  JMP rb_fetch

rb_kind_loop:
  JSR rb_push
  LDA $ea
  STA rb_repeat,Y
  JMP rb_continue

rb_kind_next:
  LDA rb_stack_index,X
  CLC
  ADC #$01
  STA $ec
  JSR rb_stack_slot
  LDA rb_repeat,Y
  SEC
  SBC #$01
  STA rb_repeat,Y
  BEQ rb_next_done
  LDA rb_return_lo,Y
  STA rb_cursor_lo,X
  LDA rb_return_hi,Y
  STA rb_cursor_hi,X
  JMP rb_fetch
rb_next_done:
  LDA $ec
  STA rb_stack_index,X
  JMP rb_continue

rb_kind_transpose:
  LDA $ea
  STA rb_transpose,X
  JMP rb_continue
rb_kind_jump_transposed:
  LDA $ea
  STA rb_transpose,X
  JMP rb_target

rb_kind_volume:
rb_kind_write_data:
rb_kind_frequency:
rb_kind_pulse:
rb_kind_chord:
  LDA $e0
  CLC
  ADC $eb
  STA $ec
  LDA $e1
  ADC #$00
  STA $ed
  LDY $ea
  DEY
rb_copy_data:
  LDA ($e6),Y
  STA ($ec),Y
  DEY
  BPL rb_copy_data
  JMP rb_continue

rb_kind_poke_data:
  LDA $ea
  CMP #$49
  BEQ rb_poke_transpose
  TAY
  LDA $eb
  STA ($e0),Y
  JMP rb_continue
rb_poke_transpose:
  LDA $eb
  STA rb_transpose,X
  JMP rb_continue
rb_kind_poke_sound:
  LDY $ea
  LDA $eb
  STA ($e2),Y
  JMP rb_continue

rb_kind_code:
  LDA $ea
  BEQ rb_increment_transpose
  CMP #$03
  BEQ rb_start_morse
  TAY
  LDA rb_morse_pitch_lo,Y
  STA $d400
  LDA rb_morse_pitch_hi,Y
  STA $d401
  JMP rb_continue
rb_increment_transpose:
  INC rb_transpose
  JMP rb_continue

rb_start_morse:
  LDA #$a0
  STA $d406
  LDA rb_morse_pitch_lo
  STA $d400
  LDA rb_morse_pitch_hi
  STA $d401
  LDA #$01
  STA rb_morse_active
  LDA #$00
  STA rb_repeat
  STA $d405
  STA rb_sound_0++28
  STA $d404
  STA rb_morse_phase
  ; STARTMC re-enters REFRESH before its node advances (rambo_score.ScoreRuntime).
  TXA
  PHA
  LDX #$00
rb_save_refresh_scratch:
  LDA $e0,X
  PHA
  INX
  CPX #$10
  BNE rb_save_refresh_scratch
  JSR rb_refresh
  LDX #$0f
rb_restore_refresh_scratch:
  PLA
  STA $e0,X
  DEX
  BPL rb_restore_refresh_scratch
  PLA
  TAX
  JMP rb_continue

rb_note:
  LDA $ec
  CLC
  ADC rb_transpose,X
  PHA
  LDA $e0
  CLC
  ADC #$16
  STA $e6
  LDA $e1
  ADC #$00
  STA $e7
  LDA rb_sid_offsets,X
  CLC
  ADC #$06
  STA $ed
  LDA #$04
  STA $ec
rb_note_registers:
  LDY $ed
  LDA #$00
  STA $d400,Y
  LDY $ec
  LDA ($e6),Y
  STA $ef
  LDY $ed
  LDA $ef
  STA $d400,Y
  DEC $ed
  DEC $ec
  BPL rb_note_registers
  LDY #$18
  LDA ($e0),Y
  LDY #$1a
  STA ($e2),Y
  PLA
  TAY
  LDA rb_frequency_lo,Y
  STA $e6
  LDA rb_frequency_hi,Y
  STA $e7
  LDY #$1d
  LDA $e6
  STA ($e2),Y
  INY
  LDA $e7
  STA ($e2),Y
  LDY rb_sid_offsets,X
  LDA $e6
  STA $d400,Y
  LDA $e7
  STA $d401,Y
  LDY #$11
  LDA ($e0),Y
  STA ($e2),Y
  BEQ rb_note_frequency
  LDY #$17
rb_note_pulse_copy:
  LDA ($e0),Y
  STA ($e2),Y
  DEY
  CPY #$0d
  BNE rb_note_pulse_copy
  LDY #$16
  LDA ($e2),Y
  LDY #$23
  STA ($e2),Y
  LDY #$17
  LDA ($e2),Y
  LDY #$24
  STA ($e2),Y
  LDY #$0e
  LDA ($e2),Y
  LDY #$25
  STA ($e2),Y
  LDY #$0f
  LDA ($e2),Y
  LDY #$26
  STA ($e2),Y
rb_note_frequency:
  LDY #$0d
  LDA ($e0),Y
  STA ($e2),Y
  BEQ rb_note_lifetime
  LDY #$0d
rb_note_frequency_copy:
  LDA ($e0),Y
  STA ($e2),Y
  DEY
  BPL rb_note_frequency_copy
  CPX #$01
  BEQ rb_note_frequency_counters
  LDY #$0d
  LDA ($e2),Y
  AND #$08
  BEQ rb_note_frequency_counters
  LDA $ea
  CLC
  ADC rb_transpose,X
  LDY #$0a
  STA ($e2),Y
  LDY #$0c
  LDA #$ff
  STA ($e2),Y
rb_note_frequency_counters:
  LDY #$08
  LDA ($e2),Y
  LDY #$1f
  STA ($e2),Y
  LDY #$09
  LDA ($e2),Y
  LDY #$20
  STA ($e2),Y
  LDY #$0a
  LDA ($e2),Y
  LDY #$21
  STA ($e2),Y
  LDY #$0b
  LDA ($e2),Y
  LDY #$22
  STA ($e2),Y
rb_note_lifetime:
  LDY #$1b
  LDA ($e0),Y
  STA ($e2),Y
  INY
  LDA ($e0),Y
  STA ($e2),Y
  RTS

rb_morse:
  LDA rb_morse_phase
  CMP #$02
  BCC rb_morse_dispatch
  DEC rb_repeat++3
  BMI rb_morse_expired
  JMP rb_refresh
rb_morse_expired:
  CMP #$02
  BNE rb_morse_not_tone
  LDA #$20
  STA $d404
  LDA #$02
  STA rb_repeat++3
  LDA #$03
  STA rb_morse_phase
  JMP rb_refresh
rb_morse_not_tone:
  CMP #$04
  BEQ rb_morse_gap_done
  DEC rb_repeat++2
  BMI rb_morse_letter_gap
  LDA #$01
  STA rb_morse_phase
  JMP rb_morse_shift
rb_morse_letter_gap:
  LDA #$06
  STA rb_repeat++3
  LDA #$04
  STA rb_morse_phase
  JMP rb_refresh
rb_morse_gap_done:
  JMP rb_morse_read
rb_morse_dispatch:
  LDA rb_morse_phase
  BNE rb_morse_shift
rb_morse_read:
  LDY rb_repeat
  LDA rb_morse_letters,Y
  BNE rb_morse_letter
  LDA #$00
  STA rb_morse_active
  RTS
rb_morse_letter:
  INC rb_repeat
  LSR A
  SEC
  SBC #$41
  TAY
  LDA rb_morse_codes,Y
  STA rb_repeat++1
  AND #$03
  STA rb_repeat++2
  LDA #$01
  STA rb_morse_phase
  JMP rb_refresh
rb_morse_shift:
  ASL rb_repeat++1
  LDA #$02
  BCC rb_morse_dot
  LDA #$06
rb_morse_dot:
  STA rb_repeat++3
  LDA #$21
  STA $d404
  LDA #$02
  STA rb_morse_phase
  JMP rb_refresh
