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

; Independent numeric programs; semantics and ordered stores are owned by
; scripts/monty_title_programs.py and evidence/monty-programs/contract.json.

mo_initialize_note:
  LDA mo_append
  BNE mo_fx_patch
  LDA mo_note,X
  JSR mo_lookup_base
  LDY mo_sid_offsets,X
  LDA mo_lookup_hi
  STA mo_held_frequency_hi,X
  STA $d401,Y
  LDA mo_lookup_lo
  STA mo_held_frequency_lo,X
  STA $d400,Y
mo_fx_patch:
  LDY mo_instrument_index,X
  LDA mo_inst_waveform,Y
  STA mo_voice_control,X
  LDY mo_append
  BEQ mo_fx_setup_control
  AND #$fe
mo_fx_setup_control:
  JSR mo_write_control
  LDY mo_instrument_index,X
  LDA mo_inst_pulse_lo,Y
  LDY mo_sid_offsets,X
  STA $d402,Y
  LDY mo_instrument_index,X
  LDA mo_inst_pulse_hi,Y
  LDY mo_sid_offsets,X
  STA $d403,Y
  LDY mo_instrument_index,X
  LDA mo_inst_attack_decay,Y
  LDY mo_sid_offsets,X
  STA $d405,Y
  LDY mo_instrument_index,X
  LDA mo_inst_sustain_release,Y
  LDY mo_sid_offsets,X
  STA $d406,Y
  RTS

mo_advance_body:
  JSR mo_fx_release
  JSR mo_fx_vibrato
  JSR mo_fx_pwm
  JSR mo_fx_portamento
  JSR mo_fx_drum
  JSR mo_fx_descent
  JMP mo_fx_octave

mo_fx_release:
  LDA mo_score_tick
  BEQ mo_fx_release_done
  LDA mo_control,X
  AND #$20
  BNE mo_fx_release_done
  LDA mo_remaining,X
  BNE mo_fx_release_done
  LDA mo_voice_control,X
  AND #$fe
  JSR mo_write_control
  LDY mo_sid_offsets,X
  LDA #0
  STA $d405,Y
  STA $d406,Y
mo_fx_release_done:
  RTS

mo_fx_vibrato:
  LDY mo_instrument_index,X
  LDA mo_inst_vibrato_depth,Y
  BNE mo_fx_vibrato_active
  RTS
mo_fx_vibrato_active:
  CMP #$81
  BCC mo_fx_depth_normal
  LDA #0
mo_fx_depth_normal:
  CLC
  ADC #1
  STA mo_fx_shifts
  LDA mo_note,X
  JSR mo_lookup_base
  LDA mo_lookup_lo
  STA mo_fx_base_lo
  LDA mo_lookup_hi
  STA mo_fx_base_hi
  LDA mo_note,X
  JSR mo_lookup_adjacent
  LDA mo_lookup_lo
  SEC
  SBC mo_fx_base_lo
  STA mo_fx_delta_lo
  LDA mo_lookup_hi
  SBC mo_fx_base_hi
  STA mo_fx_delta_hi
mo_fx_shift_loop:
  LSR mo_fx_delta_hi
  ROR mo_fx_delta_lo
  DEC mo_fx_shifts
  BNE mo_fx_shift_loop
  LDA mo_control,X
  AND #$1f
  CMP #8
  BCC mo_fx_vibrato_store
  LDA mo_counter
  AND #7
  CMP #4
  BCC mo_fx_phase_ready
  EOR #7
mo_fx_phase_ready:
  TAY
  BEQ mo_fx_vibrato_store
mo_fx_vibrato_add:
  CLC
  LDA mo_fx_base_lo
  ADC mo_fx_delta_lo
  STA mo_fx_base_lo
  LDA mo_fx_base_hi
  ADC mo_fx_delta_hi
  STA mo_fx_base_hi
  DEY
  BNE mo_fx_vibrato_add
mo_fx_vibrato_store:
  LDY mo_sid_offsets,X
  LDA mo_fx_base_lo
  STA $d400,Y
  LDA mo_fx_base_hi
  STA $d401,Y
  RTS

mo_fx_pwm:
  LDY mo_instrument_index,X
  LDA mo_inst_pulse_value,Y
  BEQ mo_fx_pwm_done
  DEC mo_pulse_delay,X
  BPL mo_fx_pwm_done
  AND #$1f
  STA mo_pulse_delay,X
  LDA mo_inst_pulse_value,Y
  AND #$e0
  STA mo_fx_step
  LDA mo_pulse_direction,X
  BNE mo_fx_pwm_subtract
  LDA mo_inst_pulse_lo,Y
  CLC
  ADC mo_fx_step
  STA mo_inst_pulse_lo,Y
  LDA mo_inst_pulse_hi,Y
  ADC #0
  AND #$0f
  STA mo_inst_pulse_hi,Y
  CMP #$0e
  BNE mo_fx_pwm_store
  INC mo_pulse_direction,X
  JMP mo_fx_pwm_store
mo_fx_pwm_subtract:
  LDA mo_inst_pulse_lo,Y
  SEC
  SBC mo_fx_step
  STA mo_inst_pulse_lo,Y
  LDA mo_inst_pulse_hi,Y
  SBC #0
  AND #$0f
  STA mo_inst_pulse_hi,Y
  CMP #8
  BNE mo_fx_pwm_store
  DEC mo_pulse_direction,X
mo_fx_pwm_store:
  LDY mo_sid_offsets,X
  STA $d403,Y
  LDY mo_instrument_index,X
  LDA mo_inst_pulse_lo,Y
  LDY mo_sid_offsets,X
  STA $d402,Y
mo_fx_pwm_done:
  RTS

mo_fx_portamento:
  LDA mo_portamento,X
  BEQ mo_fx_portamento_done
  AND #$7e
  STA mo_fx_step
  LDA mo_portamento,X
  AND #1
  BNE mo_fx_portamento_subtract
  LDA mo_held_frequency_lo,X
  CLC
  ADC mo_fx_step
  STA mo_held_frequency_lo,X
  LDA mo_held_frequency_hi,X
  ADC #0
  JMP mo_fx_portamento_store
mo_fx_portamento_subtract:
  LDA mo_held_frequency_lo,X
  SEC
  SBC mo_fx_step
  STA mo_held_frequency_lo,X
  LDA mo_held_frequency_hi,X
  SBC #0
mo_fx_portamento_store:
  STA mo_held_frequency_hi,X
  LDY mo_sid_offsets,X
  LDA mo_held_frequency_lo,X
  STA $d400,Y
  LDA mo_held_frequency_hi,X
  STA $d401,Y
mo_fx_portamento_done:
  RTS

mo_fx_drum:
  LDY mo_instrument_index,X
  LDA mo_inst_effects,Y
  AND #1
  BEQ mo_fx_drum_done
  LDA mo_held_frequency_hi,X
  BEQ mo_fx_drum_done
  LDA mo_remaining,X
  BEQ mo_fx_drum_done
  LDA mo_control,X
  AND #$1f
  SEC
  SBC #1
  CMP mo_remaining,X
  BCS mo_fx_drum_decay
  LDY mo_sid_offsets,X
  LDA mo_held_frequency_hi,X
  STA $d401,Y
  LDA #$80
  JMP mo_write_control
mo_fx_drum_decay:
  LDY mo_sid_offsets,X
  LDA mo_held_frequency_hi,X
  DEC mo_held_frequency_hi,X
  STA $d401,Y
  LDA mo_voice_control,X
  AND #$fe
  BNE mo_fx_drum_control
  LDA mo_held_frequency_hi,X
  STA $d401,Y
  LDA #$80
mo_fx_drum_control:
  JMP mo_write_control
mo_fx_drum_done:
  RTS

mo_fx_descent:
  LDY mo_instrument_index,X
  LDA mo_inst_effects,Y
  AND #2
  BEQ mo_fx_descent_done
  LDA mo_counter
  AND #1
  BEQ mo_fx_descent_done
  LDA mo_held_frequency_hi,X
  BEQ mo_fx_descent_done
  DEC mo_held_frequency_hi,X
  LDY mo_sid_offsets,X
  STA $d401,Y
mo_fx_descent_done:
  RTS

mo_fx_octave:
  LDY mo_instrument_index,X
  LDA mo_inst_effects,Y
  AND #4
  BEQ mo_fx_octave_done
  LDA mo_counter
  AND #1
  BEQ mo_fx_octave_even
  LDA mo_note,X
  CLC
  ADC #$0c
  JMP mo_fx_octave_lookup
mo_fx_octave_even:
  LDA mo_note,X
mo_fx_octave_lookup:
  JSR mo_lookup_base
  LDY mo_sid_offsets,X
  LDA mo_lookup_hi
  STA $d401,Y
  LDA mo_lookup_lo
  STA $d400,Y
mo_fx_octave_done:
  RTS

mo_fx_scratch:
mo_fx_shifts:
  .byte 0
mo_fx_base_lo:
  .byte 0
mo_fx_base_hi:
  .byte 0
mo_fx_delta_lo:
  .byte 0
mo_fx_delta_hi:
  .byte 0
mo_fx_step:
  .byte 0

mo_sid_offsets:
  .byte $00,$07,$0e
mo_frequency_bytes:
  .byte $16,$01,$27,$01,$38,$01,$4b,$01,$5f,$01,$73,$01,$8a,$01,$a1,$01,$ba,$01,$d4,$01,$f0,$01,$0e,$02,$2d,$02,$4e,$02,$71,$02,$96,$02,$bd,$02,$e7,$02,$13,$03,$42,$03,$74,$03,$a9,$03,$e0,$03,$1b,$04,$5a,$04,$9b,$04,$e2,$04,$2c,$05,$7b,$05,$ce,$05,$27,$06,$85,$06,$e8,$06,$51,$07,$c1,$07,$37,$08,$b4,$08,$37,$09,$c4,$09,$57,$0a,$f5,$0a,$9c,$0b,$4e,$0c,$09,$0d,$d0,$0d,$a3,$0e,$82,$0f,$6e,$10,$68,$11,$6e,$12,$88,$13,$af,$14,$eb,$15,$39,$17,$9c,$18,$13,$1a,$a1,$1b,$46,$1d,$04,$1f,$dc,$20,$d0,$22,$dc,$24,$10,$27,$5e,$29,$d6,$2b,$72,$2e,$38,$31,$26,$34,$42,$37,$8c,$3a,$08,$3e,$b8,$41,$a0,$45,$b8,$49,$20,$4e,$bc,$52,$ac,$57,$e4,$5c,$70,$62,$4c,$68,$84,$6e,$18,$75,$10,$7c,$70,$83,$40,$8b,$70,$93,$40,$9c,$78,$a5,$58,$af,$c8,$b9,$e0,$c4,$98,$d0,$08,$dd,$30,$ea,$20,$f8,$2e,$fd
mo_order_ptr_lo:
  .byte MO_ORDER_0_LO,MO_ORDER_1_LO,MO_ORDER_2_LO
mo_order_ptr_hi:
  .byte MO_ORDER_0_HI,MO_ORDER_1_HI,MO_ORDER_2_HI
mo_order_0:
  .byte $11,$14,$17,$1a,$00,$27,$00,$28,$03,$05,$00,$27,$00,$28,$03,$05,$07,$3a,$14,$17,$00,$27,$00,$28,$2f,$30,$31,$31,$32,$33,$33,$34,$34,$34,$34,$34,$34,$34,$34,$35,$35,$35,$35,$35,$35,$36,$12,$37,$38,$09,$2a,$09,$2b,$09,$0a,$09,$2a,$09,$2b,$09,$0a,$0d,$0d,$0f,$ff
mo_order_1:
  .byte $12,$15,$18,$1b,$2d,$39,$39,$39,$39,$39,$39,$2c,$39,$39,$39,$39,$39,$39,$2c,$39,$39,$39,$01,$01,$29,$29,$2c,$15,$18,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$39,$01,$01,$01,$29,$39,$39,$39,$01,$01,$01,$29,$39,$39,$39,$39,$ff
mo_order_2:
  .byte $13,$16,$19,$1c,$02,$02,$1d,$1e,$02,$02,$1d,$1f,$04,$04,$20,$20,$06,$02,$02,$1d,$1e,$02,$02,$1d,$1f,$04,$04,$20,$20,$06,$08,$08,$08,$08,$21,$21,$21,$21,$22,$22,$22,$23,$22,$24,$25,$3b,$26,$26,$26,$26,$26,$26,$26,$26,$26,$26,$26,$26,$26,$26,$26,$26,$02,$02,$1d,$1e,$02,$02,$1d,$1f,$2f,$2f,$2f,$2f,$2f,$2f,$2f,$2f,$2f,$2f,$2f,$2f,$2f,$0b,$0b,$1d,$1d,$0b,$0b,$1d,$0b,$0b,$0b,$0c,$0c,$1d,$1d,$1d,$10,$0b,$0b,$1d,$1d,$0b,$0b,$1d,$0b,$0b,$0b,$0c,$0c,$1d,$1d,$1d,$10,$0b,$1d,$0b,$1d,$0b,$1d,$0b,$1d,$0b,$0c,$1d,$0b,$0c,$23,$0b,$0b,$ff
mo_pattern_ptr_lo:
  .byte MO_PATTERN_0_LO,MO_PATTERN_1_LO,MO_PATTERN_2_LO,MO_PATTERN_3_LO,MO_PATTERN_4_LO,MO_PATTERN_5_LO,MO_PATTERN_6_LO,MO_PATTERN_7_LO,MO_PATTERN_8_LO,MO_PATTERN_9_LO,MO_PATTERN_10_LO,MO_PATTERN_11_LO,MO_PATTERN_12_LO,MO_PATTERN_13_LO,MO_PATTERN_14_LO,MO_PATTERN_15_LO,MO_PATTERN_16_LO,MO_PATTERN_17_LO,MO_PATTERN_18_LO,MO_PATTERN_19_LO,MO_PATTERN_20_LO,MO_PATTERN_21_LO,MO_PATTERN_22_LO,MO_PATTERN_23_LO,MO_PATTERN_24_LO,MO_PATTERN_25_LO,MO_PATTERN_26_LO,MO_PATTERN_27_LO,MO_PATTERN_28_LO,MO_PATTERN_29_LO,MO_PATTERN_30_LO,MO_PATTERN_31_LO,MO_PATTERN_32_LO,MO_PATTERN_33_LO,MO_PATTERN_34_LO,MO_PATTERN_35_LO,MO_PATTERN_36_LO,MO_PATTERN_37_LO,MO_PATTERN_38_LO,MO_PATTERN_39_LO,MO_PATTERN_40_LO,MO_PATTERN_41_LO,MO_PATTERN_42_LO,MO_PATTERN_43_LO,MO_PATTERN_44_LO,MO_PATTERN_45_LO,MO_PATTERN_46_LO,MO_PATTERN_47_LO,MO_PATTERN_48_LO,MO_PATTERN_49_LO,MO_PATTERN_50_LO,MO_PATTERN_51_LO,MO_PATTERN_52_LO,MO_PATTERN_53_LO,MO_PATTERN_54_LO,MO_PATTERN_55_LO,MO_PATTERN_56_LO,MO_PATTERN_57_LO,MO_PATTERN_58_LO,MO_PATTERN_59_LO
mo_pattern_ptr_hi:
  .byte MO_PATTERN_0_HI,MO_PATTERN_1_HI,MO_PATTERN_2_HI,MO_PATTERN_3_HI,MO_PATTERN_4_HI,MO_PATTERN_5_HI,MO_PATTERN_6_HI,MO_PATTERN_7_HI,MO_PATTERN_8_HI,MO_PATTERN_9_HI,MO_PATTERN_10_HI,MO_PATTERN_11_HI,MO_PATTERN_12_HI,MO_PATTERN_13_HI,MO_PATTERN_14_HI,MO_PATTERN_15_HI,MO_PATTERN_16_HI,MO_PATTERN_17_HI,MO_PATTERN_18_HI,MO_PATTERN_19_HI,MO_PATTERN_20_HI,MO_PATTERN_21_HI,MO_PATTERN_22_HI,MO_PATTERN_23_HI,MO_PATTERN_24_HI,MO_PATTERN_25_HI,MO_PATTERN_26_HI,MO_PATTERN_27_HI,MO_PATTERN_28_HI,MO_PATTERN_29_HI,MO_PATTERN_30_HI,MO_PATTERN_31_HI,MO_PATTERN_32_HI,MO_PATTERN_33_HI,MO_PATTERN_34_HI,MO_PATTERN_35_HI,MO_PATTERN_36_HI,MO_PATTERN_37_HI,MO_PATTERN_38_HI,MO_PATTERN_39_HI,MO_PATTERN_40_HI,MO_PATTERN_41_HI,MO_PATTERN_42_HI,MO_PATTERN_43_HI,MO_PATTERN_44_HI,MO_PATTERN_45_HI,MO_PATTERN_46_HI,MO_PATTERN_47_HI,MO_PATTERN_48_HI,MO_PATTERN_49_HI,MO_PATTERN_50_HI,MO_PATTERN_51_HI,MO_PATTERN_52_HI,MO_PATTERN_53_HI,MO_PATTERN_54_HI,MO_PATTERN_55_HI,MO_PATTERN_56_HI,MO_PATTERN_57_HI,MO_PATTERN_58_HI,MO_PATTERN_59_HI
mo_pattern_0:
  .byte $83,$00,$37,$01,$3e,$01,$3e,$03,$3d,$03,$3e,$03,$43,$03,$3e,$03,$3d,$03,$3e,$03,$37,$01,$3e,$01,$3e,$03,$3d,$03,$3e,$03,$43,$03,$42,$03,$43,$03,$45,$03,$46,$01,$48,$01,$46,$03,$45,$03,$43,$03,$4b,$01,$4d,$01,$4b,$03,$4a,$03,$48,$ff
mo_pattern_1:
  .byte $83,$01,$43,$01,$4f,$01,$5b,$87,$03,$2f,$83,$01,$43,$01,$4f,$01,$5b,$87,$03,$2f,$ff
mo_pattern_2:
  .byte $83,$02,$13,$03,$13,$03,$1f,$03,$1f,$03,$13,$03,$13,$03,$1f,$03,$1f,$ff
mo_pattern_3:
  .byte $bf,$06,$48,$07,$48,$01,$4b,$01,$4a,$01,$4b,$01,$4a,$03,$4b,$03,$4d,$03,$4b,$03,$4a,$3f,$48,$07,$48,$01,$4b,$01,$4a,$01,$4b,$01,$4a,$03,$4b,$03,$4d,$03,$4b,$03,$48,$3f,$4c,$07,$4c,$01,$4f,$01,$4e,$01,$4f,$01,$4e,$03,$4f,$03,$51,$03,$4f,$03,$4e,$3f,$4c,$07,$4c,$01,$4f,$01,$4e,$01,$4f,$01,$4e,$03,$4f,$03,$51,$03,$4f,$03,$4c,$ff
mo_pattern_4:
  .byte $03,$18,$03,$18,$03,$24,$03,$24,$03,$18,$03,$18,$03,$24,$03,$24,$03,$20,$03,$20,$03,$2c,$03,$2c,$03,$20,$03,$20,$03,$2c,$03,$2c,$ff
mo_pattern_5:
  .byte $83,$04,$26,$03,$29,$03,$28,$03,$29,$03,$26,$03,$35,$03,$34,$03,$32,$03,$2d,$03,$30,$03,$2f,$03,$30,$03,$2d,$03,$3c,$03,$3b,$03,$39,$03,$30,$03,$33,$03,$32,$03,$33,$03,$30,$03,$3f,$03,$3e,$03,$3c,$03,$46,$03,$45,$03,$43,$03,$3a,$03,$39,$03,$37,$03,$2e,$03,$2d,$03,$26,$03,$29,$03,$28,$03,$29,$03,$26,$03,$35,$03,$34,$03,$32,$03,$2d,$03,$30,$03,$2f,$03,$30,$03,$2d,$03,$3c,$03,$3b,$03,$39,$03,$30,$03,$33,$03,$32,$03,$33,$03,$30,$03,$3f,$03,$3e,$03,$3c,$03,$34,$03,$37,$03,$36,$03,$37,$03,$34,$03,$37,$03,$3a,$03,$3d,$03,$3e,$07,$3e,$07,$3f,$07,$3e,$03,$3c,$07,$3e,$57,$ff
mo_pattern_6:
  .byte $03,$1a,$03,$1a,$03,$26,$03,$26,$03,$1a,$03,$1a,$03,$26,$03,$26,$03,$15,$03,$15,$03,$21,$03,$21,$03,$15,$03,$15,$03,$21,$03,$21,$03,$18,$03,$18,$03,$24,$03,$24,$03,$18,$03,$18,$03,$24,$03,$24,$03,$1f,$03,$1f,$03,$2b,$03,$2b,$03,$1f,$03,$1f,$03,$2b,$03,$2b,$03,$1a,$03,$1a,$03,$26,$03,$26,$03,$1a,$03,$1a,$03,$26,$03,$26,$03,$15,$03,$15,$03,$21,$03,$21,$03,$15,$03,$15,$03,$21,$03,$21,$03,$18,$03,$18,$03,$24,$03,$24,$03,$18,$03,$18,$03,$24,$03,$24,$03,$1c,$03,$1c,$03,$28,$03,$28,$03,$1c,$03,$1c,$03,$28,$03,$28,$83,$04,$36,$07,$36,$07,$37,$07,$36,$03,$33,$07,$32,$57,$ff
mo_pattern_7:
  .byte $8b,$00,$3a,$01,$3a,$01,$3c,$03,$3d,$03,$3f,$03,$3d,$03,$3c,$0b,$3a,$03,$39,$07,$3a,$81,$06,$4b,$01,$4d,$01,$4e,$01,$4d,$01,$4e,$01,$4d,$05,$4b,$81,$00,$3a,$01,$3c,$01,$3d,$03,$3f,$03,$3d,$03,$3c,$03,$3a,$03,$39,$1b,$3a,$0b,$3b,$01,$3b,$01,$3d,$03,$3e,$03,$40,$03,$3e,$03,$3d,$0b,$3b,$03,$3a,$07,$3b,$81,$06,$4c,$01,$4e,$01,$4f,$01,$4e,$01,$4f,$01,$4e,$05,$4c,$81,$00,$3b,$01,$3d,$01,$3e,$03,$40,$03,$3e,$03,$3d,$03,$3b,$03,$3a,$1b,$3b,$8b,$05,$35,$03,$33,$07,$32,$03,$30,$03,$2f,$0b,$30,$03,$32,$0f,$30,$0b,$35,$03,$33,$07,$32,$03,$30,$03,$2f,$1f,$30,$8b,$00,$3c,$01,$3c,$01,$3e,$03,$3f,$03,$41,$03,$3f,$03,$3e,$0b,$3d,$01,$3d,$01,$3f,$03,$40,$03,$42,$03,$40,$03,$3f,$03,$3e,$01,$3e,$01,$40,$03,$41,$03,$40,$03,$3e,$03,$3d,$03,$3e,$03,$3c,$03,$3a,$01,$3a,$01,$3c,$03,$3d,$03,$3c,$03,$3a,$03,$39,$03,$3a,$03,$3c,$ff
mo_pattern_8:
  .byte $83,$02,$1b,$03,$1b,$03,$27,$03,$27,$03,$1b,$03,$1b,$03,$27,$03,$27,$ff
mo_pattern_9:
  .byte $83,$00,$32,$01,$35,$01,$34,$03,$32,$03,$35,$03,$34,$03,$32,$03,$35,$01,$34,$01,$32,$03,$32,$03,$3a,$03,$39,$03,$3a,$03,$32,$03,$3a,$03,$39,$03,$3a,$ff
mo_pattern_10:
  .byte $03,$37,$01,$3a,$01,$39,$03,$37,$03,$3a,$03,$39,$03,$37,$03,$3a,$01,$39,$01,$37,$03,$37,$03,$3e,$03,$3d,$03,$3e,$03,$37,$03,$3e,$03,$3d,$03,$3e,$03,$3d,$01,$40,$01,$3e,$03,$3d,$03,$40,$01,$3e,$01,$3d,$03,$40,$03,$3e,$03,$40,$03,$40,$01,$43,$01,$41,$03,$40,$03,$43,$01,$41,$01,$40,$03,$43,$03,$41,$03,$43,$03,$43,$01,$46,$01,$45,$03,$43,$03,$46,$01,$45,$01,$43,$03,$46,$03,$45,$03,$43,$01,$48,$01,$49,$01,$48,$01,$46,$01,$45,$01,$46,$01,$45,$01,$43,$01,$41,$01,$43,$01,$41,$01,$40,$01,$3d,$01,$39,$01,$3b,$01,$3d,$ff
mo_pattern_11:
  .byte $83,$02,$1a,$03,$1a,$03,$26,$03,$26,$03,$1a,$03,$1a,$03,$26,$03,$26,$ff
mo_pattern_12:
  .byte $03,$13,$03,$13,$03,$1d,$03,$1f,$03,$13,$03,$13,$03,$1d,$03,$1f,$ff
mo_pattern_13:
  .byte $01,$3e,$01,$39,$01,$35,$01,$39,$01,$3e,$01,$39,$01,$35,$01,$39,$03,$3e,$01,$41,$01,$40,$03,$40,$01,$3d,$01,$3e,$01,$40,$01,$3d,$01,$39,$01,$3d,$01,$40,$01,$3d,$01,$39,$01,$3d,$03,$40,$01,$43,$01,$41,$03,$41,$01,$3e,$01,$40,$01,$41,$01,$3e,$01,$39,$01,$3e,$01,$41,$01,$3e,$01,$39,$01,$3e,$03,$41,$01,$45,$01,$43,$03,$43,$01,$40,$01,$41,$01,$43,$01,$40,$01,$3d,$01,$40,$01,$43,$01,$40,$01,$3d,$01,$40,$01,$46,$01,$43,$01,$45,$01,$46,$01,$44,$01,$43,$01,$40,$01,$3d,$ff
mo_pattern_15:
  .byte $01,$3e,$01,$39,$01,$35,$01,$39,$01,$3e,$01,$39,$01,$35,$01,$39,$01,$3e,$01,$39,$01,$35,$01,$39,$01,$3e,$01,$39,$01,$35,$01,$39,$01,$3e,$01,$3a,$01,$37,$01,$3a,$01,$3e,$01,$3a,$01,$37,$01,$3a,$01,$3e,$01,$3a,$01,$37,$01,$3a,$01,$3e,$01,$3a,$01,$37,$01,$3a,$01,$40,$01,$3d,$01,$39,$01,$3d,$01,$40,$01,$3d,$01,$39,$01,$3d,$01,$40,$01,$3d,$01,$39,$01,$3d,$01,$40,$01,$3d,$01,$39,$01,$3d,$01,$41,$01,$3e,$01,$39,$01,$3e,$01,$41,$01,$3e,$01,$39,$01,$3e,$01,$41,$01,$3e,$01,$39,$01,$3e,$01,$41,$01,$3e,$01,$39,$01,$3e,$01,$43,$01,$3e,$01,$3a,$01,$3e,$01,$43,$01,$3e,$01,$3a,$01,$3e,$01,$43,$01,$3e,$01,$3a,$01,$3e,$01,$43,$01,$3e,$01,$3a,$01,$3e,$01,$43,$01,$3f,$01,$3c,$01,$3f,$01,$43,$01,$3f,$01,$3c,$01,$3f,$01,$43,$01,$3f,$01,$3c,$01,$3f,$01,$43,$01,$3f,$01,$3c,$01,$3f,$01,$45,$01,$42,$01,$3c,$01,$42,$01,$45,$01,$42,$01,$3c,$01,$42,$01,$48,$01,$45,$01,$42,$01,$45,$01,$4b,$01,$48,$01,$45,$01,$48,$01,$4b,$01,$4a,$01,$48,$01,$4a,$01,$4b,$01,$4a,$01,$48,$01,$4a,$01,$4b,$01,$4a,$01,$48,$01,$4a,$01,$4c,$01,$4e,$03,$4f,$ff
mo_pattern_16:
  .byte $07,$1a,$4f,$47,$ff
mo_pattern_17:
  .byte $bf,$06,$56,$1f,$57,$1f,$56,$1f,$5b,$1f,$56,$1f,$57,$1f,$56,$1f,$4f,$ff
mo_pattern_18:
  .byte $bf,$0c,$68,$7f,$7f,$7f,$7f,$7f,$7f,$7f,$ff
mo_pattern_19:
  .byte $bf,$08,$13,$3f,$13,$3f,$13,$3f,$13,$3f,$13,$3f,$13,$3f,$13,$1f,$13,$ff
mo_pattern_20:
  .byte $97,$09,$2e,$03,$2e,$1b,$32,$03,$32,$1b,$31,$03,$31,$1f,$34,$43,$17,$32,$03,$32,$1b,$35,$03,$35,$1b,$34,$03,$34,$0f,$37,$8f,$0a,$37,$43,$ff
mo_pattern_21:
  .byte $97,$09,$2b,$03,$2b,$1b,$2e,$03,$2e,$1b,$2d,$03,$2d,$1f,$30,$43,$17,$2e,$03,$2e,$1b,$32,$03,$32,$1b,$31,$03,$31,$0f,$34,$8f,$0a,$34,$43,$ff
mo_pattern_22:
  .byte $0f,$1f,$0f,$1f,$0f,$1f,$0f,$1f,$0f,$1f,$0f,$1f,$0f,$1f,$0f,$1f,$0f,$1f,$0f,$1f,$0f,$1f,$0f,$1f,$0f,$1f,$0f,$1f,$0f,$1f,$0f,$1f,$ff
mo_pattern_23:
  .byte $97,$09,$33,$03,$33,$1b,$37,$03,$37,$1b,$36,$03,$36,$1f,$39,$43,$17,$37,$03,$37,$1b,$3a,$03,$3a,$1b,$39,$03,$39,$2f,$3c,$21,$3c,$21,$3d,$21,$3e,$21,$3f,$21,$40,$21,$41,$21,$42,$21,$43,$21,$44,$01,$45,$ff
mo_pattern_24:
  .byte $97,$09,$30,$03,$30,$1b,$33,$03,$33,$1b,$32,$03,$32,$1f,$36,$43,$17,$33,$03,$33,$1b,$37,$03,$37,$1b,$36,$03,$36,$2f,$39,$21,$39,$21,$3a,$21,$3b,$21,$3c,$21,$3d,$21,$3e,$21,$3f,$21,$40,$21,$41,$01,$42,$ff
mo_pattern_25:
  .byte $0f,$1a,$0f,$1a,$0f,$1a,$0f,$1a,$0f,$1a,$0f,$1a,$0f,$1a,$0f,$1a,$0f,$1a,$0f,$1a,$0f,$1a,$0f,$1a,$0f,$1a,$0f,$1a,$0f,$1a,$0f,$1a,$ff
mo_pattern_26:
  .byte $1f,$46,$bf,$0a,$46,$7f,$7f,$ff
mo_pattern_27:
  .byte $1f,$43,$bf,$0a,$43,$7f,$ff
mo_pattern_28:
  .byte $83,$02,$13,$03,$13,$03,$1e,$03,$1f,$03,$13,$03,$13,$03,$1e,$03,$1f,$03,$13,$03,$13,$03,$1e,$03,$1f,$03,$13,$03,$13,$03,$1e,$03,$1f,$03,$13,$03,$13,$03,$1e,$03,$1f,$03,$13,$03,$13,$03,$1e,$03,$1f,$03,$13,$03,$13,$03,$1e,$03,$1f,$03,$13,$03,$13,$03,$1e,$03,$1f,$ff
mo_pattern_29:
  .byte $03,$15,$03,$15,$03,$1f,$03,$21,$03,$15,$03,$15,$03,$1f,$03,$21,$ff
mo_pattern_30:
  .byte $03,$1a,$03,$1a,$03,$1c,$03,$1c,$03,$1d,$03,$1d,$03,$1e,$03,$1e,$ff
mo_pattern_31:
  .byte $03,$1a,$03,$1a,$03,$24,$03,$26,$03,$13,$03,$13,$07,$1f,$ff
mo_pattern_32:
  .byte $03,$19,$03,$19,$03,$25,$03,$25,$03,$19,$03,$19,$03,$25,$03,$25,$03,$21,$03,$21,$03,$2d,$03,$2d,$03,$21,$03,$21,$03,$2d,$03,$2d,$ff
mo_pattern_33:
  .byte $03,$1c,$03,$1c,$03,$28,$03,$28,$03,$1c,$03,$1c,$03,$28,$03,$28,$ff
mo_pattern_34:
  .byte $03,$1d,$03,$1d,$03,$29,$03,$29,$03,$1d,$03,$1d,$03,$29,$03,$29,$ff
mo_pattern_35:
  .byte $03,$18,$03,$18,$03,$24,$03,$24,$03,$18,$03,$18,$03,$24,$03,$24,$ff
mo_pattern_36:
  .byte $03,$1e,$03,$1e,$03,$2a,$03,$2a,$03,$1e,$03,$1e,$03,$2a,$03,$2a,$ff
mo_pattern_37:
  .byte $83,$05,$26,$01,$4a,$01,$34,$03,$29,$03,$4c,$03,$4a,$03,$31,$03,$4a,$03,$24,$03,$22,$01,$46,$01,$30,$03,$25,$03,$48,$03,$46,$03,$2d,$03,$46,$03,$24,$ff
mo_pattern_38:
  .byte $87,$02,$1a,$87,$03,$2f,$83,$02,$26,$03,$26,$87,$03,$2f,$ff
mo_pattern_39:
  .byte $1f,$4a,$ff
mo_pattern_40:
  .byte $03,$46,$01,$48,$01,$46,$03,$45,$03,$4a,$0f,$43,$ff
mo_pattern_41:
  .byte $8f,$0b,$38,$4f,$ff
mo_pattern_42:
  .byte $03,$34,$01,$37,$01,$35,$03,$34,$03,$37,$03,$35,$03,$34,$03,$37,$01,$35,$01,$34,$03,$34,$03,$3a,$03,$39,$03,$3a,$03,$34,$03,$3a,$03,$39,$03,$3a,$ff
mo_pattern_43:
  .byte $03,$39,$03,$38,$03,$39,$03,$3a,$03,$39,$03,$37,$03,$35,$03,$34,$03,$35,$03,$34,$03,$35,$03,$37,$03,$35,$03,$34,$03,$32,$03,$31,$ff
mo_pattern_44:
  .byte $83,$0e,$32,$07,$32,$07,$2f,$07,$2f,$03,$2b,$87,$0b,$46,$83,$0e,$2c,$03,$2c,$8f,$0b,$32,$ff
mo_pattern_45:
  .byte $43,$83,$0e,$32,$03,$32,$03,$2f,$03,$2f,$03,$2c,$87,$0b,$38,$ff
mo_pattern_47:
  .byte $03,$1a,$03,$1a,$03,$24,$03,$26,$03,$1a,$03,$1a,$03,$18,$03,$19,$03,$1a,$03,$1a,$03,$24,$03,$26,$03,$1a,$03,$1a,$03,$18,$03,$19,$03,$18,$03,$18,$03,$22,$03,$24,$03,$18,$03,$18,$03,$16,$03,$17,$03,$18,$03,$18,$03,$22,$03,$24,$03,$18,$03,$18,$03,$16,$03,$17,$03,$13,$03,$13,$03,$1d,$03,$1f,$03,$13,$03,$13,$03,$1d,$03,$1e,$03,$13,$03,$13,$03,$1d,$03,$1f,$03,$13,$03,$13,$03,$1d,$03,$1e,$03,$1a,$03,$1a,$03,$24,$03,$26,$03,$1a,$03,$1a,$03,$18,$03,$19,$03,$1a,$03,$1a,$03,$24,$03,$26,$03,$1a,$03,$1a,$03,$18,$03,$19,$ff
mo_pattern_48:
  .byte $bf,$0f,$32,$0f,$32,$8f,$90,$30,$3f,$32,$13,$32,$03,$32,$03,$35,$03,$37,$3f,$37,$0f,$37,$8f,$90,$30,$3f,$32,$13,$32,$03,$2d,$03,$30,$03,$32,$ff
mo_pattern_49:
  .byte $0f,$32,$af,$90,$35,$0f,$37,$a7,$99,$37,$07,$35,$3f,$32,$13,$32,$03,$32,$a3,$e8,$35,$03,$37,$0f,$35,$af,$90,$37,$0f,$37,$a7,$99,$37,$07,$35,$3f,$32,$13,$32,$03,$2d,$a3,$e8,$30,$03,$32,$ff
mo_pattern_50:
  .byte $07,$32,$03,$39,$13,$3c,$a7,$9a,$37,$a7,$9b,$38,$07,$37,$03,$35,$03,$32,$03,$39,$1b,$3c,$a7,$9a,$37,$a7,$9b,$38,$07,$37,$03,$35,$03,$32,$03,$39,$03,$3c,$03,$3e,$03,$3c,$07,$3e,$03,$3c,$03,$39,$a7,$9a,$37,$a7,$9b,$38,$07,$37,$03,$35,$03,$32,$af,$90,$3c,$1f,$3e,$43,$03,$3e,$03,$3c,$03,$3e,$ff
mo_pattern_51:
  .byte $03,$3e,$03,$3e,$a3,$e8,$3c,$03,$3e,$03,$3e,$03,$3e,$a3,$e8,$3c,$03,$3e,$03,$3e,$03,$3e,$a3,$e8,$3c,$03,$3e,$03,$3e,$03,$3e,$a3,$e8,$3c,$03,$3e,$af,$91,$43,$1f,$41,$43,$03,$3e,$03,$41,$03,$43,$03,$43,$03,$43,$a3,$e8,$41,$03,$43,$03,$43,$03,$43,$a3,$e8,$41,$03,$43,$03,$45,$03,$48,$a3,$fd,$45,$03,$44,$01,$43,$01,$41,$03,$3e,$03,$3c,$03,$3e,$2f,$3e,$bf,$98,$3e,$43,$03,$3e,$03,$3c,$03,$3e,$ff
mo_pattern_52:
  .byte $03,$4a,$03,$4a,$a3,$f8,$48,$03,$4a,$03,$4a,$03,$4a,$a3,$f8,$48,$03,$4a,$ff
mo_pattern_53:
  .byte $01,$51,$01,$54,$01,$51,$01,$54,$01,$51,$01,$54,$01,$51,$01,$54,$01,$51,$01,$54,$01,$51,$01,$54,$01,$51,$01,$54,$01,$51,$01,$54,$ff
mo_pattern_54:
  .byte $01,$50,$01,$4f,$01,$4d,$01,$4a,$01,$4f,$01,$4d,$01,$4a,$01,$48,$01,$4a,$01,$48,$01,$45,$01,$43,$01,$44,$01,$43,$01,$41,$01,$3e,$01,$43,$01,$41,$01,$3e,$01,$3c,$01,$3e,$01,$3c,$01,$39,$01,$37,$01,$38,$01,$37,$01,$35,$01,$32,$01,$37,$01,$35,$01,$32,$01,$30,$ff
mo_pattern_55:
  .byte $5f,$5f,$5f,$47,$83,$0e,$32,$07,$32,$07,$2f,$03,$2f,$07,$2f,$97,$0b,$3a,$5f,$5f,$47,$8b,$0e,$32,$03,$32,$03,$2f,$03,$2f,$47,$97,$0b,$3a,$5f,$5f,$47,$83,$0e,$2f,$0b,$2f,$03,$2f,$03,$2f,$87,$0b,$30,$17,$3a,$5f,$8b,$0e,$32,$0b,$32,$0b,$2f,$0b,$2f,$07,$2c,$07,$2c,$ff
mo_pattern_56:
  .byte $87,$0b,$34,$17,$3a,$5f,$5f,$84,$0e,$32,$04,$32,$05,$32,$04,$2f,$04,$2f,$05,$2f,$47,$97,$0b,$3a,$5f,$5f,$84,$0e,$32,$04,$32,$05,$32,$04,$2f,$04,$2f,$05,$2f,$ff
mo_pattern_57:
  .byte $83,$01,$43,$01,$4f,$01,$5b,$87,$03,$2f,$83,$01,$43,$01,$4f,$01,$5b,$87,$03,$2f,$83,$01,$43,$01,$4f,$01,$5b,$87,$03,$2f,$83,$01,$43,$01,$4f,$01,$5b,$87,$03,$2f,$83,$01,$43,$01,$4f,$01,$5b,$87,$03,$2f,$83,$01,$43,$01,$4f,$01,$5b,$87,$03,$2f,$83,$01,$43,$01,$4f,$01,$5b,$87,$03,$2f,$83,$01,$43,$01,$4f,$01,$5b,$87,$03,$2f,$ff
mo_pattern_58:
  .byte $03,$3e,$07,$3e,$07,$3f,$07,$3e,$03,$3c,$07,$3e,$57,$ff
mo_pattern_59:
  .byte $83,$04,$36,$07,$36,$07,$37,$07,$36,$03,$33,$07,$32,$57,$ff
mo_lookup_ptr_lo:
  .byte MO_LOOKUP_0_LO,MO_LOOKUP_1_LO,MO_LOOKUP_2_LO,MO_LOOKUP_3_LO,MO_LOOKUP_4_LO,MO_LOOKUP_5_LO,MO_LOOKUP_6_LO,MO_LOOKUP_7_LO,MO_LOOKUP_8_LO,MO_LOOKUP_9_LO,MO_LOOKUP_10_LO,MO_LOOKUP_11_LO,MO_LOOKUP_12_LO,MO_LOOKUP_13_LO,MO_LOOKUP_14_LO,MO_LOOKUP_15_LO,MO_LOOKUP_16_LO,MO_LOOKUP_17_LO,MO_LOOKUP_18_LO,MO_LOOKUP_19_LO,MO_LOOKUP_20_LO,MO_LOOKUP_21_LO,MO_LOOKUP_22_LO,MO_LOOKUP_23_LO,MO_LOOKUP_24_LO,MO_LOOKUP_25_LO,MO_LOOKUP_26_LO,MO_LOOKUP_27_LO,MO_LOOKUP_28_LO,MO_LOOKUP_29_LO,MO_LOOKUP_30_LO,MO_LOOKUP_31_LO,MO_LOOKUP_32_LO,MO_LOOKUP_33_LO,MO_LOOKUP_34_LO,MO_LOOKUP_35_LO,MO_LOOKUP_36_LO,MO_LOOKUP_37_LO,MO_LOOKUP_38_LO,MO_LOOKUP_39_LO,MO_LOOKUP_40_LO,MO_LOOKUP_41_LO,MO_LOOKUP_42_LO,MO_LOOKUP_43_LO,MO_LOOKUP_44_LO,MO_LOOKUP_45_LO,MO_LOOKUP_46_LO,MO_LOOKUP_47_LO,MO_LOOKUP_48_LO,MO_LOOKUP_49_LO,MO_LOOKUP_50_LO,MO_LOOKUP_51_LO,MO_LOOKUP_52_LO,MO_LOOKUP_53_LO,MO_LOOKUP_54_LO,MO_LOOKUP_55_LO,MO_LOOKUP_56_LO,MO_LOOKUP_57_LO,MO_LOOKUP_58_LO,MO_LOOKUP_59_LO,MO_LOOKUP_60_LO,MO_LOOKUP_61_LO,MO_LOOKUP_62_LO,MO_LOOKUP_63_LO,MO_LOOKUP_64_LO,MO_LOOKUP_65_LO,MO_LOOKUP_66_LO,MO_LOOKUP_67_LO,MO_LOOKUP_68_LO,MO_LOOKUP_69_LO,MO_LOOKUP_70_LO,MO_LOOKUP_71_LO,MO_LOOKUP_72_LO,MO_LOOKUP_73_LO,MO_LOOKUP_74_LO,MO_LOOKUP_75_LO,MO_LOOKUP_76_LO,MO_LOOKUP_77_LO,MO_LOOKUP_78_LO,MO_LOOKUP_79_LO,MO_LOOKUP_80_LO,MO_LOOKUP_81_LO,MO_LOOKUP_82_LO,MO_LOOKUP_83_LO,MO_LOOKUP_84_LO,MO_LOOKUP_85_LO,MO_LOOKUP_86_LO,MO_LOOKUP_87_LO,MO_LOOKUP_88_LO,MO_LOOKUP_89_LO,MO_LOOKUP_90_LO,MO_LOOKUP_91_LO,MO_LOOKUP_92_LO,MO_LOOKUP_93_LO,MO_LOOKUP_94_LO,MO_LOOKUP_95_LO,MO_LOOKUP_96_LO,MO_LOOKUP_97_LO,MO_LOOKUP_98_LO,MO_LOOKUP_99_LO,MO_LOOKUP_100_LO,MO_LOOKUP_101_LO,MO_LOOKUP_102_LO,MO_LOOKUP_103_LO,MO_LOOKUP_104_LO,MO_LOOKUP_105_LO,MO_LOOKUP_106_LO,MO_LOOKUP_107_LO,MO_LOOKUP_108_LO,MO_LOOKUP_109_LO,MO_LOOKUP_110_LO,MO_LOOKUP_111_LO,MO_LOOKUP_112_LO,MO_LOOKUP_113_LO,MO_LOOKUP_114_LO,MO_LOOKUP_115_LO,MO_LOOKUP_116_LO,MO_LOOKUP_117_LO,MO_LOOKUP_118_LO,MO_LOOKUP_119_LO,MO_LOOKUP_120_LO,MO_LOOKUP_121_LO,MO_LOOKUP_122_LO,MO_LOOKUP_123_LO,MO_LOOKUP_124_LO,MO_LOOKUP_125_LO,MO_LOOKUP_126_LO,MO_LOOKUP_127_LO,MO_LOOKUP_128_LO,MO_LOOKUP_129_LO,MO_LOOKUP_130_LO,MO_LOOKUP_131_LO,MO_LOOKUP_132_LO,MO_LOOKUP_133_LO,MO_LOOKUP_134_LO,MO_LOOKUP_135_LO,MO_LOOKUP_136_LO,MO_LOOKUP_137_LO,MO_LOOKUP_138_LO,MO_LOOKUP_139_LO,MO_LOOKUP_140_LO,MO_LOOKUP_141_LO,MO_LOOKUP_142_LO,MO_LOOKUP_143_LO,MO_LOOKUP_144_LO,MO_LOOKUP_145_LO,MO_LOOKUP_146_LO,MO_LOOKUP_147_LO,MO_LOOKUP_148_LO,MO_LOOKUP_149_LO,MO_LOOKUP_150_LO,MO_LOOKUP_151_LO,MO_LOOKUP_152_LO,MO_LOOKUP_153_LO,MO_LOOKUP_154_LO,MO_LOOKUP_155_LO,MO_LOOKUP_156_LO,MO_LOOKUP_157_LO,MO_LOOKUP_158_LO,MO_LOOKUP_159_LO,MO_LOOKUP_160_LO,MO_LOOKUP_161_LO,MO_LOOKUP_162_LO,MO_LOOKUP_163_LO,MO_LOOKUP_164_LO,MO_LOOKUP_165_LO,MO_LOOKUP_166_LO,MO_LOOKUP_167_LO,MO_LOOKUP_168_LO,MO_LOOKUP_169_LO,MO_LOOKUP_170_LO,MO_LOOKUP_171_LO,MO_LOOKUP_172_LO,MO_LOOKUP_173_LO,MO_LOOKUP_174_LO,MO_LOOKUP_175_LO,MO_LOOKUP_176_LO,MO_LOOKUP_177_LO,MO_LOOKUP_178_LO,MO_LOOKUP_179_LO,MO_LOOKUP_180_LO,MO_LOOKUP_181_LO,MO_LOOKUP_182_LO,MO_LOOKUP_183_LO,MO_LOOKUP_184_LO,MO_LOOKUP_185_LO,MO_LOOKUP_186_LO,MO_LOOKUP_187_LO,MO_LOOKUP_188_LO,MO_LOOKUP_189_LO,MO_LOOKUP_190_LO,MO_LOOKUP_191_LO,MO_LOOKUP_192_LO,MO_LOOKUP_193_LO,MO_LOOKUP_194_LO,MO_LOOKUP_195_LO,MO_LOOKUP_196_LO,MO_LOOKUP_197_LO,MO_LOOKUP_198_LO,MO_LOOKUP_199_LO,MO_LOOKUP_200_LO,MO_LOOKUP_201_LO,MO_LOOKUP_202_LO,MO_LOOKUP_203_LO,MO_LOOKUP_204_LO,MO_LOOKUP_205_LO,MO_LOOKUP_206_LO,MO_LOOKUP_207_LO,MO_LOOKUP_208_LO,MO_LOOKUP_209_LO,MO_LOOKUP_210_LO,MO_LOOKUP_211_LO,MO_LOOKUP_212_LO,MO_LOOKUP_213_LO,MO_LOOKUP_214_LO,MO_LOOKUP_215_LO,MO_LOOKUP_216_LO,MO_LOOKUP_217_LO,MO_LOOKUP_218_LO,MO_LOOKUP_219_LO,MO_LOOKUP_220_LO,MO_LOOKUP_221_LO,MO_LOOKUP_222_LO,MO_LOOKUP_223_LO,MO_LOOKUP_224_LO,MO_LOOKUP_225_LO,MO_LOOKUP_226_LO,MO_LOOKUP_227_LO,MO_LOOKUP_228_LO,MO_LOOKUP_229_LO,MO_LOOKUP_230_LO,MO_LOOKUP_231_LO,MO_LOOKUP_232_LO,MO_LOOKUP_233_LO,MO_LOOKUP_234_LO,MO_LOOKUP_235_LO,MO_LOOKUP_236_LO,MO_LOOKUP_237_LO,MO_LOOKUP_238_LO,MO_LOOKUP_239_LO,MO_LOOKUP_240_LO,MO_LOOKUP_241_LO,MO_LOOKUP_242_LO,MO_LOOKUP_243_LO,MO_LOOKUP_244_LO,MO_LOOKUP_245_LO,MO_LOOKUP_246_LO,MO_LOOKUP_247_LO,MO_LOOKUP_248_LO,MO_LOOKUP_249_LO,MO_LOOKUP_250_LO,MO_LOOKUP_251_LO,MO_LOOKUP_252_LO,MO_LOOKUP_253_LO,MO_LOOKUP_254_LO,MO_LOOKUP_255_LO
mo_lookup_ptr_hi:
  .byte MO_LOOKUP_0_HI,MO_LOOKUP_1_HI,MO_LOOKUP_2_HI,MO_LOOKUP_3_HI,MO_LOOKUP_4_HI,MO_LOOKUP_5_HI,MO_LOOKUP_6_HI,MO_LOOKUP_7_HI,MO_LOOKUP_8_HI,MO_LOOKUP_9_HI,MO_LOOKUP_10_HI,MO_LOOKUP_11_HI,MO_LOOKUP_12_HI,MO_LOOKUP_13_HI,MO_LOOKUP_14_HI,MO_LOOKUP_15_HI,MO_LOOKUP_16_HI,MO_LOOKUP_17_HI,MO_LOOKUP_18_HI,MO_LOOKUP_19_HI,MO_LOOKUP_20_HI,MO_LOOKUP_21_HI,MO_LOOKUP_22_HI,MO_LOOKUP_23_HI,MO_LOOKUP_24_HI,MO_LOOKUP_25_HI,MO_LOOKUP_26_HI,MO_LOOKUP_27_HI,MO_LOOKUP_28_HI,MO_LOOKUP_29_HI,MO_LOOKUP_30_HI,MO_LOOKUP_31_HI,MO_LOOKUP_32_HI,MO_LOOKUP_33_HI,MO_LOOKUP_34_HI,MO_LOOKUP_35_HI,MO_LOOKUP_36_HI,MO_LOOKUP_37_HI,MO_LOOKUP_38_HI,MO_LOOKUP_39_HI,MO_LOOKUP_40_HI,MO_LOOKUP_41_HI,MO_LOOKUP_42_HI,MO_LOOKUP_43_HI,MO_LOOKUP_44_HI,MO_LOOKUP_45_HI,MO_LOOKUP_46_HI,MO_LOOKUP_47_HI,MO_LOOKUP_48_HI,MO_LOOKUP_49_HI,MO_LOOKUP_50_HI,MO_LOOKUP_51_HI,MO_LOOKUP_52_HI,MO_LOOKUP_53_HI,MO_LOOKUP_54_HI,MO_LOOKUP_55_HI,MO_LOOKUP_56_HI,MO_LOOKUP_57_HI,MO_LOOKUP_58_HI,MO_LOOKUP_59_HI,MO_LOOKUP_60_HI,MO_LOOKUP_61_HI,MO_LOOKUP_62_HI,MO_LOOKUP_63_HI,MO_LOOKUP_64_HI,MO_LOOKUP_65_HI,MO_LOOKUP_66_HI,MO_LOOKUP_67_HI,MO_LOOKUP_68_HI,MO_LOOKUP_69_HI,MO_LOOKUP_70_HI,MO_LOOKUP_71_HI,MO_LOOKUP_72_HI,MO_LOOKUP_73_HI,MO_LOOKUP_74_HI,MO_LOOKUP_75_HI,MO_LOOKUP_76_HI,MO_LOOKUP_77_HI,MO_LOOKUP_78_HI,MO_LOOKUP_79_HI,MO_LOOKUP_80_HI,MO_LOOKUP_81_HI,MO_LOOKUP_82_HI,MO_LOOKUP_83_HI,MO_LOOKUP_84_HI,MO_LOOKUP_85_HI,MO_LOOKUP_86_HI,MO_LOOKUP_87_HI,MO_LOOKUP_88_HI,MO_LOOKUP_89_HI,MO_LOOKUP_90_HI,MO_LOOKUP_91_HI,MO_LOOKUP_92_HI,MO_LOOKUP_93_HI,MO_LOOKUP_94_HI,MO_LOOKUP_95_HI,MO_LOOKUP_96_HI,MO_LOOKUP_97_HI,MO_LOOKUP_98_HI,MO_LOOKUP_99_HI,MO_LOOKUP_100_HI,MO_LOOKUP_101_HI,MO_LOOKUP_102_HI,MO_LOOKUP_103_HI,MO_LOOKUP_104_HI,MO_LOOKUP_105_HI,MO_LOOKUP_106_HI,MO_LOOKUP_107_HI,MO_LOOKUP_108_HI,MO_LOOKUP_109_HI,MO_LOOKUP_110_HI,MO_LOOKUP_111_HI,MO_LOOKUP_112_HI,MO_LOOKUP_113_HI,MO_LOOKUP_114_HI,MO_LOOKUP_115_HI,MO_LOOKUP_116_HI,MO_LOOKUP_117_HI,MO_LOOKUP_118_HI,MO_LOOKUP_119_HI,MO_LOOKUP_120_HI,MO_LOOKUP_121_HI,MO_LOOKUP_122_HI,MO_LOOKUP_123_HI,MO_LOOKUP_124_HI,MO_LOOKUP_125_HI,MO_LOOKUP_126_HI,MO_LOOKUP_127_HI,MO_LOOKUP_128_HI,MO_LOOKUP_129_HI,MO_LOOKUP_130_HI,MO_LOOKUP_131_HI,MO_LOOKUP_132_HI,MO_LOOKUP_133_HI,MO_LOOKUP_134_HI,MO_LOOKUP_135_HI,MO_LOOKUP_136_HI,MO_LOOKUP_137_HI,MO_LOOKUP_138_HI,MO_LOOKUP_139_HI,MO_LOOKUP_140_HI,MO_LOOKUP_141_HI,MO_LOOKUP_142_HI,MO_LOOKUP_143_HI,MO_LOOKUP_144_HI,MO_LOOKUP_145_HI,MO_LOOKUP_146_HI,MO_LOOKUP_147_HI,MO_LOOKUP_148_HI,MO_LOOKUP_149_HI,MO_LOOKUP_150_HI,MO_LOOKUP_151_HI,MO_LOOKUP_152_HI,MO_LOOKUP_153_HI,MO_LOOKUP_154_HI,MO_LOOKUP_155_HI,MO_LOOKUP_156_HI,MO_LOOKUP_157_HI,MO_LOOKUP_158_HI,MO_LOOKUP_159_HI,MO_LOOKUP_160_HI,MO_LOOKUP_161_HI,MO_LOOKUP_162_HI,MO_LOOKUP_163_HI,MO_LOOKUP_164_HI,MO_LOOKUP_165_HI,MO_LOOKUP_166_HI,MO_LOOKUP_167_HI,MO_LOOKUP_168_HI,MO_LOOKUP_169_HI,MO_LOOKUP_170_HI,MO_LOOKUP_171_HI,MO_LOOKUP_172_HI,MO_LOOKUP_173_HI,MO_LOOKUP_174_HI,MO_LOOKUP_175_HI,MO_LOOKUP_176_HI,MO_LOOKUP_177_HI,MO_LOOKUP_178_HI,MO_LOOKUP_179_HI,MO_LOOKUP_180_HI,MO_LOOKUP_181_HI,MO_LOOKUP_182_HI,MO_LOOKUP_183_HI,MO_LOOKUP_184_HI,MO_LOOKUP_185_HI,MO_LOOKUP_186_HI,MO_LOOKUP_187_HI,MO_LOOKUP_188_HI,MO_LOOKUP_189_HI,MO_LOOKUP_190_HI,MO_LOOKUP_191_HI,MO_LOOKUP_192_HI,MO_LOOKUP_193_HI,MO_LOOKUP_194_HI,MO_LOOKUP_195_HI,MO_LOOKUP_196_HI,MO_LOOKUP_197_HI,MO_LOOKUP_198_HI,MO_LOOKUP_199_HI,MO_LOOKUP_200_HI,MO_LOOKUP_201_HI,MO_LOOKUP_202_HI,MO_LOOKUP_203_HI,MO_LOOKUP_204_HI,MO_LOOKUP_205_HI,MO_LOOKUP_206_HI,MO_LOOKUP_207_HI,MO_LOOKUP_208_HI,MO_LOOKUP_209_HI,MO_LOOKUP_210_HI,MO_LOOKUP_211_HI,MO_LOOKUP_212_HI,MO_LOOKUP_213_HI,MO_LOOKUP_214_HI,MO_LOOKUP_215_HI,MO_LOOKUP_216_HI,MO_LOOKUP_217_HI,MO_LOOKUP_218_HI,MO_LOOKUP_219_HI,MO_LOOKUP_220_HI,MO_LOOKUP_221_HI,MO_LOOKUP_222_HI,MO_LOOKUP_223_HI,MO_LOOKUP_224_HI,MO_LOOKUP_225_HI,MO_LOOKUP_226_HI,MO_LOOKUP_227_HI,MO_LOOKUP_228_HI,MO_LOOKUP_229_HI,MO_LOOKUP_230_HI,MO_LOOKUP_231_HI,MO_LOOKUP_232_HI,MO_LOOKUP_233_HI,MO_LOOKUP_234_HI,MO_LOOKUP_235_HI,MO_LOOKUP_236_HI,MO_LOOKUP_237_HI,MO_LOOKUP_238_HI,MO_LOOKUP_239_HI,MO_LOOKUP_240_HI,MO_LOOKUP_241_HI,MO_LOOKUP_242_HI,MO_LOOKUP_243_HI,MO_LOOKUP_244_HI,MO_LOOKUP_245_HI,MO_LOOKUP_246_HI,MO_LOOKUP_247_HI,MO_LOOKUP_248_HI,MO_LOOKUP_249_HI,MO_LOOKUP_250_HI,MO_LOOKUP_251_HI,MO_LOOKUP_252_HI,MO_LOOKUP_253_HI,MO_LOOKUP_254_HI,MO_LOOKUP_255_HI
mo_state_begin:
mo_tempo_countdown:
  .byte $00
mo_tempo_reload:
  .byte $01
mo_counter:
  .byte $fa
mo_status:
  .byte $40
mo_mode_volume:
  .byte $0f
mo_sfx_priority:
  .byte $00
mo_sfx_flags:
  .byte $ff
mo_output_enable:
  .byte $ff
mo_note:
  .byte $46,$26,$43
mo_control:
  .byte $25,$17,$25
mo_remaining:
  .byte $01,$13,$01
mo_portamento:
  .byte $00,$00,$00
mo_instrument_index:
  .byte $10,$02,$10
mo_order_cursor:
  .byte $04,$02,$04
mo_pattern_cursor:
  .byte $22,$0a,$22
mo_held_frequency_lo:
  .byte $08,$c4,$26
mo_held_frequency_hi:
  .byte $3e,$09,$34
mo_voice_control:
  .byte $41,$41,$41
mo_pulse_delay:
  .byte $00,$01,$1d
mo_pulse_direction:
  .byte $01,$00,$00
mo_inst_pulse_lo:
  .byte $80,$00,$a0,$00,$00,$00,$00,$00,$80,$80,$00,$80,$a0,$00,$00,$00,$00,$00,$00,$00
mo_inst_pulse_hi:
  .byte $0b,$08,$02,$02,$08,$01,$08,$08,$0a,$08,$09,$07,$0b,$08,$08,$09,$02,$00,$08,$08
mo_inst_waveform:
  .byte $41,$81,$41,$81,$41,$41,$41,$41,$41,$41,$41,$81,$41,$41,$41,$41,$41,$11,$41,$11
mo_inst_attack_decay:
  .byte $48,$02,$09,$09,$08,$3f,$04,$09,$09,$4a,$40,$0a,$3f,$90,$06,$19,$09,$0a,$37,$07
mo_inst_sustain_release:
  .byte $60,$08,$80,$09,$50,$c0,$40,$00,$70,$69,$6f,$0a,$ff,$f0,$0a,$70,$90,$fa,$40,$70
mo_inst_vibrato_depth:
  .byte $03,$00,$00,$00,$02,$02,$02,$02,$02,$02,$00,$00,$01,$01,$00,$02,$02,$00,$02,$02
mo_inst_pulse_value:
  .byte $81,$00,$00,$00,$00,$00,$00,$00,$5f,$81,$81,$00,$e7,$e8,$00,$a8,$00,$00,$00,$00
mo_inst_effects:
  .byte $00,$01,$00,$05,$04,$00,$00,$00,$04,$00,$02,$01,$02,$02,$01,$00,$00,$05,$00,$00
mo_score_tick:
  .byte $00
mo_append:
  .byte $00
mo_lookup_lo:
  .byte $00
mo_lookup_hi:
  .byte $00
mo_unmapped_value:
  .byte $00
mo_actual_control:
  .byte $00,$00,$00
mo_tick_lo:
  .byte $00
mo_tick_hi:
  .byte $00
mo_tail:
  .byte $00
mo_tail_age:
  .byte $00
mo_stopped:
  .byte $00
mo_volume_scratch:
  .byte $00
mo_state_end:
mo_initial_state:
  .byte $00,$01,$fa,$40,$0f,$00,$ff,$ff,$46,$26,$43,$25,$17,$25,$01,$13,$01,$00,$00,$00,$10,$02,$10,$04,$02,$04,$22,$0a,$22,$08,$c4,$26,$3e,$09,$34,$41,$41,$41,$00,$01,$1d,$01,$00,$00,$80,$00,$a0,$00,$00,$00,$00,$00,$80,$80,$00,$80,$a0,$00,$00,$00,$00,$00,$00,$00,$0b,$08,$02,$02,$08,$01,$08,$08,$0a,$08,$09,$07,$0b,$08,$08,$09,$02,$00,$08,$08,$41,$81,$41,$81,$41,$41,$41,$41,$41,$41,$41,$81,$41,$41,$41,$41,$41,$11,$41,$11,$48,$02,$09,$09,$08,$3f,$04,$09,$09,$4a,$40,$0a,$3f,$90,$06,$19,$09,$0a,$37,$07,$60,$08,$80,$09,$50,$c0,$40,$00,$70,$69,$6f,$0a,$ff,$f0,$0a,$70,$90,$fa,$40,$70,$03,$00,$00,$00,$02,$02,$02,$02,$02,$02,$00,$00,$01,$01,$00,$02,$02,$00,$02,$02,$81,$00,$00,$00,$00,$00,$00,$00,$5f,$81,$81,$00,$e7,$e8,$00,$a8,$00,$00,$00,$00,$00,$01,$00,$05,$04,$00,$00,$00,$04,$00,$02,$01,$02,$02,$01,$00,$00,$05,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
mo_restore_state:
  LDY #$00
mo_restore_0:
  LDA mo_initial_state++0,Y
  STA mo_state_begin++0,Y
  INY
  CPY #$da
  BNE mo_restore_0
  RTS
