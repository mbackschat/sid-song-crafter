entry_init:
  CLD
  JSR gb_restore_state
  LDX #$17
  LDA #$00
gb_clear_ports:
  STA $d400,X
  DEX
  BPL gb_clear_ports
gb_init_done:
  RTS

entry_play:
  CLD
  LDX #$02
gb_voice_loop:
  LDA gb_phase
  AND #$03
  BEQ gb_quarter
  JSR gb_body
  JMP gb_next_voice
gb_quarter:
  LDA gb_remaining,X
  BPL gb_active_quarter
  JMP gb_next_voice
gb_active_quarter:
  DEC gb_remaining,X
  BMI gb_fetch_row
  JSR gb_body
  JMP gb_next_voice
gb_fetch_row:
  LDA gb_order_ptr_lo,X
  STA $e0
  LDA gb_order_ptr_hi,X
  STA $e1
  LDY gb_order_cursor,X
  LDA ($e0),Y
  CMP #$ff
  BNE gb_selected_pattern
  LDX #$02
  LDA #$00
gb_reset_cursors:
  STA gb_order_cursor,X
  STA gb_pattern_cursor,X
  STA gb_remaining,X
  DEX
  BPL gb_reset_cursors
  JMP gb_advance_phase
gb_selected_pattern:
  TAY
  LDA gb_pattern_ptr_lo,Y
  STA $e0
  LDA gb_pattern_ptr_hi,Y
  STA $e1
  LDY gb_pattern_cursor,X
  LDA ($e0),Y
  STA gb_header,X
  AND #$1f
  STA gb_remaining,X
  INY
  LDA gb_header,X
  AND #$40
  BNE gb_lookahead
  LDA ($e0),Y
  STA gb_note,X
  INY
  LDA gb_header,X
  BPL gb_lookahead
  LDA ($e0),Y
  STA $ed
  AND #$0f
  STA gb_instrument,X
  LDA $ed
  LSR A
  LSR A
  LSR A
  LSR A
  JSR gb_volume_output
  INY
gb_lookahead:
  LDA ($e0),Y
  CMP #$ff
  BNE gb_keep_pattern
  LDA #$00
  STA gb_pattern_cursor,X
  INC gb_order_cursor,X
  JMP gb_row_ready
gb_keep_pattern:
  TYA
  STA gb_pattern_cursor,X
gb_row_ready:
  JSR gb_onset
gb_next_voice:
  DEX
  BMI gb_advance_phase
  JMP gb_voice_loop
gb_advance_phase:
  INC gb_phase
gb_call_done:
  RTS

gb_volume_output:
  CMP #$0f
  BNE gb_volume_store
  LDA #$6d
  SEC
  SBC gb_order_cursor
  CMP #$0f
  BCC gb_volume_store
  LDA #$0f
gb_volume_store:
  STA $d418
  RTS

gb_load_frequency:
  LDA gb_note,X
  AND #$7f
  TAY
  STY $e4
  LDA gb_frequency_lo,Y
  STA $e5
  LDA gb_frequency_hi,Y
  STA $e6
  RTS

gb_onset:
  LDA gb_header,X
  AND #$40
  BNE gb_patch_setup
  JSR gb_load_frequency
  LDY gb_sid_offsets,X
  LDA $e6
  STA $d401,Y
  LDA $e5
  STA $d400,Y
gb_patch_setup:
  LDY gb_instrument,X
  LDA gb_patch_control,Y
  STA gb_cached_control,X
  LDA gb_patch_pulse_low,Y
  STA $e5
  LDA gb_patch_pulse_high,Y
  STA $e6
  LDA gb_patch_attack_decay,Y
  STA $e7
  LDA gb_patch_sustain_release,Y
  STA $e8
  LDY gb_sid_offsets,X
  LDA gb_header,X
  AND #$40
  BEQ gb_note_control
  LDA gb_cached_control,X
  AND #$fe
  JMP gb_setup_ports
gb_note_control:
  LDA gb_cached_control,X
gb_setup_ports:
  STA $d404,Y
  LDA $e5
  STA $d402,Y
  LDA $e6
  STA $d403,Y
  LDA $e7
  STA $d405,Y
  LDA $e8
  STA $d406,Y
  RTS

gb_body:
  LDA gb_phase
  AND #$03
  BNE gb_vibrato
  LDA gb_header,X
  AND #$20
  BNE gb_vibrato
  LDY gb_sid_offsets,X
  LDA gb_cached_control,X
  AND #$fe
  STA $d404,Y
  LDA gb_remaining,X
  BNE gb_vibrato
  STA $d405,Y
  STA $d406,Y
gb_vibrato:
  LDY gb_instrument,X
  LDA gb_patch_vibrato_shift,Y
  BEQ gb_body_done
  STA $e9
  JSR gb_load_frequency
  LDY $e4
  INY
  LDA gb_frequency_lo,Y
  SEC
  SBC $e5
  STA $e7
  LDA gb_frequency_hi,Y
  SBC $e6
  STA $e8
gb_divide_delta:
  LSR $e8
  ROR $e7
  DEC $e9
  BPL gb_divide_delta
  LDA gb_phase
  AND #$07
  CMP #$04
  BCC gb_multiplier_ready
  EOR #$07
gb_multiplier_ready:
  STA $ea
  LDA gb_header,X
  AND #$1f
  CMP #$05
  BCC gb_body_pitch
  LDA $ea
  BEQ gb_body_pitch
gb_add_displacement:
  CLC
  LDA $e5
  ADC $e7
  STA $e5
  LDA $e6
  ADC $e8
  STA $e6
  DEC $ea
  BNE gb_add_displacement
gb_body_pitch:
  LDY gb_sid_offsets,X
  LDA $e5
  STA $d400,Y
  LDA $e6
  STA $d401,Y
gb_body_done:
  RTS

gb_state_begin:
gb_phase:
  .byte $00
gb_order_cursor:
  .byte $00,$00,$00
gb_pattern_cursor:
  .byte $00,$00,$00
gb_remaining:
  .byte $00,$00,$00
gb_note:
  .byte $00,$00,$00
gb_header:
  .byte $00,$00,$00
gb_instrument:
  .byte $00,$00,$00
gb_cached_control:
  .byte $00,$00,$00
gb_state_end:
gb_initial_image:
  .byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
gb_restore_state:
  LDY #GB_STATE_LAST
gb_restore_loop:
  LDA gb_initial_image,Y
  STA gb_state_begin,Y
  DEY
  BPL gb_restore_loop
  LDX #$0f
  LDA #$00
gb_clear_workspace:
  STA $e0,X
  DEX
  BPL gb_clear_workspace
  RTS
gb_order_ptr_lo:
  .byte GB_ORDER_PTR_LO_0,GB_ORDER_PTR_LO_1,GB_ORDER_PTR_LO_2
gb_order_ptr_hi:
  .byte GB_ORDER_PTR_HI_0,GB_ORDER_PTR_HI_1,GB_ORDER_PTR_HI_2
gb_pattern_ptr_lo:
  .byte GB_PATTERN_PTR_LO_0,GB_PATTERN_PTR_LO_1,GB_PATTERN_PTR_LO_2,GB_PATTERN_PTR_LO_3,GB_PATTERN_PTR_LO_4,GB_PATTERN_PTR_LO_5,GB_PATTERN_PTR_LO_6,GB_PATTERN_PTR_LO_7,GB_PATTERN_PTR_LO_8,GB_PATTERN_PTR_LO_9,GB_PATTERN_PTR_LO_10,GB_PATTERN_PTR_LO_11,GB_PATTERN_PTR_LO_12,GB_PATTERN_PTR_LO_13,GB_PATTERN_PTR_LO_14,GB_PATTERN_PTR_LO_15,GB_PATTERN_PTR_LO_16,GB_PATTERN_PTR_LO_17,GB_PATTERN_PTR_LO_18,GB_PATTERN_PTR_LO_19,GB_PATTERN_PTR_LO_20,GB_PATTERN_PTR_LO_21,GB_PATTERN_PTR_LO_22,GB_PATTERN_PTR_LO_23,GB_PATTERN_PTR_LO_24,GB_PATTERN_PTR_LO_25,GB_PATTERN_PTR_LO_26,GB_PATTERN_PTR_LO_27,GB_PATTERN_PTR_LO_28,GB_PATTERN_PTR_LO_29,GB_PATTERN_PTR_LO_30,GB_PATTERN_PTR_LO_31,GB_PATTERN_PTR_LO_32,GB_PATTERN_PTR_LO_33,GB_PATTERN_PTR_LO_34,GB_PATTERN_PTR_LO_35,GB_PATTERN_PTR_LO_36,GB_PATTERN_PTR_LO_37,$00,$00,GB_PATTERN_PTR_LO_40,GB_PATTERN_PTR_LO_41,GB_PATTERN_PTR_LO_42,GB_PATTERN_PTR_LO_43,GB_PATTERN_PTR_LO_44,GB_PATTERN_PTR_LO_45,GB_PATTERN_PTR_LO_46,GB_PATTERN_PTR_LO_47,GB_PATTERN_PTR_LO_48,GB_PATTERN_PTR_LO_49,GB_PATTERN_PTR_LO_50,$00,$00,GB_PATTERN_PTR_LO_53,GB_PATTERN_PTR_LO_54,GB_PATTERN_PTR_LO_55,GB_PATTERN_PTR_LO_56,GB_PATTERN_PTR_LO_57,$00,$00,GB_PATTERN_PTR_LO_60,GB_PATTERN_PTR_LO_61,GB_PATTERN_PTR_LO_62,GB_PATTERN_PTR_LO_63,GB_PATTERN_PTR_LO_64,GB_PATTERN_PTR_LO_65,GB_PATTERN_PTR_LO_66,GB_PATTERN_PTR_LO_67,GB_PATTERN_PTR_LO_68,GB_PATTERN_PTR_LO_69,GB_PATTERN_PTR_LO_70,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
gb_pattern_ptr_hi:
  .byte GB_PATTERN_PTR_HI_0,GB_PATTERN_PTR_HI_1,GB_PATTERN_PTR_HI_2,GB_PATTERN_PTR_HI_3,GB_PATTERN_PTR_HI_4,GB_PATTERN_PTR_HI_5,GB_PATTERN_PTR_HI_6,GB_PATTERN_PTR_HI_7,GB_PATTERN_PTR_HI_8,GB_PATTERN_PTR_HI_9,GB_PATTERN_PTR_HI_10,GB_PATTERN_PTR_HI_11,GB_PATTERN_PTR_HI_12,GB_PATTERN_PTR_HI_13,GB_PATTERN_PTR_HI_14,GB_PATTERN_PTR_HI_15,GB_PATTERN_PTR_HI_16,GB_PATTERN_PTR_HI_17,GB_PATTERN_PTR_HI_18,GB_PATTERN_PTR_HI_19,GB_PATTERN_PTR_HI_20,GB_PATTERN_PTR_HI_21,GB_PATTERN_PTR_HI_22,GB_PATTERN_PTR_HI_23,GB_PATTERN_PTR_HI_24,GB_PATTERN_PTR_HI_25,GB_PATTERN_PTR_HI_26,GB_PATTERN_PTR_HI_27,GB_PATTERN_PTR_HI_28,GB_PATTERN_PTR_HI_29,GB_PATTERN_PTR_HI_30,GB_PATTERN_PTR_HI_31,GB_PATTERN_PTR_HI_32,GB_PATTERN_PTR_HI_33,GB_PATTERN_PTR_HI_34,GB_PATTERN_PTR_HI_35,GB_PATTERN_PTR_HI_36,GB_PATTERN_PTR_HI_37,$00,$00,GB_PATTERN_PTR_HI_40,GB_PATTERN_PTR_HI_41,GB_PATTERN_PTR_HI_42,GB_PATTERN_PTR_HI_43,GB_PATTERN_PTR_HI_44,GB_PATTERN_PTR_HI_45,GB_PATTERN_PTR_HI_46,GB_PATTERN_PTR_HI_47,GB_PATTERN_PTR_HI_48,GB_PATTERN_PTR_HI_49,GB_PATTERN_PTR_HI_50,$00,$00,GB_PATTERN_PTR_HI_53,GB_PATTERN_PTR_HI_54,GB_PATTERN_PTR_HI_55,GB_PATTERN_PTR_HI_56,GB_PATTERN_PTR_HI_57,$00,$00,GB_PATTERN_PTR_HI_60,GB_PATTERN_PTR_HI_61,GB_PATTERN_PTR_HI_62,GB_PATTERN_PTR_HI_63,GB_PATTERN_PTR_HI_64,GB_PATTERN_PTR_HI_65,GB_PATTERN_PTR_HI_66,GB_PATTERN_PTR_HI_67,GB_PATTERN_PTR_HI_68,GB_PATTERN_PTR_HI_69,GB_PATTERN_PTR_HI_70,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
gb_order_0:
  .byte $01,$01,$01,$01,$01,$02,$02,$02,$03,$04,$05,$04,$1a,$1b,$1c,$02,$1d,$1b,$1c,$07,$08,$09,$0a,$09,$0a,$0b,$0c,$0b,$18,$0d,$02,$04,$1a,$1b,$1c,$02,$1d,$1b,$1c,$07,$08,$09,$0a,$09,$0a,$0b,$0c,$0b,$18,$04,$05,$04,$1a,$1e,$1f,$20,$06,$0e,$0f,$10,$11,$19,$00,$12,$13,$04,$05,$04,$21,$22,$22,$23,$06,$00,$14,$15,$16,$00,$14,$15,$17,$09,$0a,$09,$0a,$0b,$0c,$0b,$18,$04,$05,$04,$1a,$24,$25,$23,$06,$04,$05,$04,$05,$04,$05,$04,$05,$04,$05,$04,$05,$ff
gb_order_1:
  .byte $28,$29,$2a,$2b,$2b,$2c,$2d,$2c,$2d,$2c,$2d,$2c,$2d,$2c,$2d,$2c,$2d,$2c,$2d,$2c,$2d,$2e,$2f,$30,$31,$2e,$2f,$30,$31,$2c,$2d,$2c,$2d,$2c,$2d,$2c,$2d,$2c,$2d,$2c,$2d,$2e,$2f,$30,$31,$2e,$2f,$30,$31,$2c,$2d,$2c,$2d,$2c,$2d,$2c,$2d,$36,$37,$36,$37,$36,$37,$38,$39,$2c,$2d,$2c,$2d,$2c,$2d,$2c,$2d,$32,$32,$32,$32,$32,$32,$32,$35,$2e,$2f,$30,$31,$2e,$2f,$30,$31,$2c,$2d,$2c,$2d,$2c,$2d,$2c,$2d,$2c,$2d,$2c,$2d,$2c,$2d,$2c,$2d,$2c,$2d,$2c,$2d,$ff
gb_order_2:
  .byte $3c,$3d,$3e,$3f,$40,$41,$41,$41,$41,$41,$41,$41,$42,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$44,$41,$41,$43,$41,$41,$41,$41,$41,$41,$41,$41,$45,$41,$45,$41,$45,$41,$45,$46,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$41,$ff
gb_pattern_0:
  .byte $5f,$ff
gb_pattern_1:
  .byte $23,$2d,$23,$2e,$23,$2d,$23,$2e,$23,$2d,$23,$2e,$23,$2d,$23,$2e,$ff
gb_pattern_2:
  .byte $83,$2f,$f5,$03,$2f,$47,$03,$39,$43,$03,$38,$43,$ff
gb_pattern_3:
  .byte $03,$2f,$03,$2f,$47,$03,$39,$03,$39,$03,$38,$43,$ff
gb_pattern_4:
  .byte $43,$81,$3b,$f5,$01,$3b,$23,$3f,$03,$3b,$23,$3d,$03,$39,$47,$ff
gb_pattern_5:
  .byte $47,$01,$3b,$01,$3b,$01,$3b,$01,$3b,$23,$39,$03,$3b,$47,$ff
gb_pattern_6:
  .byte $47,$81,$3b,$f5,$01,$3b,$01,$3b,$01,$3b,$23,$39,$03,$3d,$03,$3b,$43,$ff
gb_pattern_7:
  .byte $03,$2f,$03,$2f,$47,$03,$3d,$43,$03,$3b,$43,$ff
gb_pattern_8:
  .byte $03,$2f,$03,$2f,$47,$03,$3d,$03,$3d,$03,$3b,$03,$36,$ff
gb_pattern_9:
  .byte $85,$3e,$f2,$01,$3b,$43,$05,$3e,$01,$3b,$43,$05,$3e,$01,$3b,$ff
gb_pattern_10:
  .byte $43,$05,$3e,$01,$3b,$43,$03,$3e,$03,$3b,$21,$39,$21,$3a,$03,$3b,$ff
gb_pattern_11:
  .byte $05,$42,$01,$3e,$43,$05,$42,$01,$3e,$43,$05,$42,$01,$3e,$ff
gb_pattern_12:
  .byte $43,$05,$42,$01,$3e,$43,$03,$42,$03,$3e,$21,$3c,$21,$3d,$03,$3e,$ff
gb_pattern_13:
  .byte $03,$3b,$03,$3b,$47,$03,$39,$43,$03,$38,$43,$ff
gb_pattern_14:
  .byte $47,$87,$3e,$f2,$07,$3d,$27,$39,$ff
gb_pattern_15:
  .byte $0f,$39,$4f,$ff
gb_pattern_16:
  .byte $47,$07,$3d,$07,$39,$27,$3b,$ff
gb_pattern_17:
  .byte $07,$3b,$57,$ff
gb_pattern_18:
  .byte $47,$07,$3d,$07,$39,$07,$40,$ff
gb_pattern_19:
  .byte $07,$3e,$07,$3d,$07,$3b,$03,$39,$03,$36,$ff
gb_pattern_20:
  .byte $81,$47,$f7,$01,$47,$01,$47,$41,$87,$3e,$f2,$07,$3d,$27,$39,$ff
gb_pattern_21:
  .byte $0f,$39,$4f,$ff
gb_pattern_22:
  .byte $81,$47,$f7,$01,$47,$01,$47,$41,$45,$a1,$2a,$f2,$01,$36,$01,$36,$03,$34,$07,$36,$ff
gb_pattern_23:
  .byte $47,$87,$2a,$f5,$07,$36,$21,$39,$21,$3a,$03,$3b,$ff
gb_pattern_24:
  .byte $43,$05,$42,$01,$3e,$43,$0f,$47,$ff
gb_pattern_25:
  .byte $47,$03,$3e,$03,$40,$23,$42,$21,$40,$25,$3e,$03,$3e,$ff
gb_pattern_26:
  .byte $47,$01,$3b,$01,$3b,$01,$3b,$01,$3b,$23,$39,$03,$3d,$03,$3b,$81,$2f,$f8,$01,$2f,$ff
gb_pattern_27:
  .byte $03,$32,$03,$2f,$07,$32,$83,$39,$f5,$43,$03,$38,$81,$2f,$f8,$01,$2d,$ff
gb_pattern_28:
  .byte $03,$2f,$03,$2f,$07,$2f,$83,$39,$f5,$43,$03,$38,$43,$ff
gb_pattern_29:
  .byte $03,$2f,$03,$2f,$47,$03,$39,$03,$39,$03,$38,$81,$2f,$f8,$01,$2f,$ff
gb_pattern_30:
  .byte $03,$32,$03,$2f,$03,$32,$83,$3b,$f5,$23,$3d,$03,$39,$45,$81,$2f,$f8,$ff
gb_pattern_31:
  .byte $03,$2f,$03,$2f,$01,$2f,$81,$3b,$f5,$01,$3b,$01,$3b,$23,$39,$03,$3b,$43,$83,$2f,$f8,$ff
gb_pattern_32:
  .byte $03,$2f,$81,$3b,$f5,$01,$3b,$23,$3f,$03,$3b,$23,$3d,$03,$39,$47,$ff
gb_pattern_33:
  .byte $47,$01,$3b,$01,$3b,$01,$3b,$01,$3b,$23,$39,$03,$3d,$03,$3b,$83,$2f,$f8,$ff
gb_pattern_34:
  .byte $43,$07,$32,$01,$31,$01,$2f,$07,$32,$03,$2f,$03,$2d,$ff
gb_pattern_35:
  .byte $41,$01,$2d,$01,$2f,$01,$2d,$07,$2f,$4f,$ff
gb_pattern_36:
  .byte $07,$36,$03,$34,$03,$32,$07,$36,$45,$01,$2f,$ff
gb_pattern_37:
  .byte $01,$2f,$01,$2f,$03,$2f,$03,$2f,$03,$2d,$03,$2f,$4b,$ff
gb_pattern_40:
  .byte $af,$17,$61,$2f,$1f,$ff
gb_pattern_41:
  .byte $2f,$1e,$2f,$1d,$ff
gb_pattern_42:
  .byte $2f,$1c,$2f,$1a,$ff
gb_pattern_43:
  .byte $3f,$22,$ff
gb_pattern_44:
  .byte $83,$17,$f1,$05,$17,$01,$1b,$03,$1e,$03,$21,$03,$21,$03,$1c,$03,$1c,$ff
gb_pattern_45:
  .byte $03,$17,$05,$17,$01,$1b,$03,$1e,$03,$21,$03,$21,$03,$1c,$03,$1e,$ff
gb_pattern_46:
  .byte $07,$23,$07,$2f,$07,$23,$07,$2d,$ff
gb_pattern_47:
  .byte $07,$21,$07,$2d,$03,$21,$03,$21,$03,$21,$03,$21,$ff
gb_pattern_48:
  .byte $07,$20,$07,$2c,$07,$20,$07,$28,$ff
gb_pattern_49:
  .byte $07,$1c,$07,$28,$03,$1c,$03,$1c,$03,$1c,$03,$1c,$ff
gb_pattern_50:
  .byte $03,$12,$03,$12,$03,$12,$03,$12,$03,$12,$03,$12,$03,$12,$03,$19,$ff
gb_pattern_53:
  .byte $03,$1e,$37,$1e,$03,$1e,$ff
gb_pattern_54:
  .byte $83,$17,$f6,$37,$15,$23,$15,$ff
gb_pattern_55:
  .byte $0b,$15,$03,$17,$03,$17,$43,$47,$ff
gb_pattern_56:
  .byte $03,$17,$37,$1a,$03,$26,$ff
gb_pattern_57:
  .byte $07,$1e,$07,$1e,$07,$12,$07,$12,$ff
gb_pattern_60:
  .byte $2f,$2f,$2f,$2b,$ff
gb_pattern_61:
  .byte $2f,$2a,$2f,$29,$ff
gb_pattern_62:
  .byte $2f,$28,$2f,$32,$ff
gb_pattern_63:
  .byte $3f,$2e,$ff
gb_pattern_64:
  .byte $81,$5f,$63,$01,$5f,$01,$5f,$01,$5f,$81,$5f,$93,$01,$5f,$01,$5f,$01,$5f,$81,$5f,$c3,$01,$5f,$01,$5f,$01,$5f,$81,$5f,$f3,$01,$5f,$01,$5f,$01,$5f,$ff
gb_pattern_65:
  .byte $83,$5f,$f3,$03,$5f,$03,$17,$03,$5f,$03,$5f,$03,$5f,$03,$17,$03,$5f,$ff
gb_pattern_66:
  .byte $81,$5f,$f3,$01,$5f,$01,$5f,$01,$5f,$01,$5f,$01,$5f,$01,$5f,$01,$5f,$01,$5f,$01,$5f,$01,$5f,$01,$5f,$01,$5f,$01,$5f,$01,$5f,$01,$5f,$ff
gb_pattern_67:
  .byte $87,$42,$f2,$07,$40,$07,$3e,$07,$3d,$ff
gb_pattern_68:
  .byte $03,$5f,$03,$5f,$83,$3b,$f2,$03,$3d,$23,$3e,$21,$3d,$25,$3b,$03,$3b,$ff
gb_pattern_69:
  .byte $03,$17,$03,$5f,$47,$01,$5f,$01,$5f,$01,$5f,$01,$5f,$01,$17,$45,$ff
gb_pattern_70:
  .byte $83,$34,$f2,$03,$32,$03,$34,$03,$32,$05,$36,$23,$34,$21,$32,$03,$2f,$ff
gb_patch_pulse_low:
  .byte $40,$00,$00,$00,$00,$00,$00,$00,$00
gb_patch_pulse_high:
  .byte $00,$08,$01,$08,$08,$08,$08,$08,$08
gb_patch_control:
  .byte $41,$21,$41,$81,$41,$21,$21,$41,$21
gb_patch_attack_decay:
  .byte $2f,$28,$2f,$14,$2f,$26,$22,$02,$88
gb_patch_sustain_release:
  .byte $ff,$88,$ff,$00,$ff,$8f,$aa,$26,$88
gb_patch_vibrato_shift:
  .byte $00,$00,$02,$00,$00,$00,$00,$00,$03
gb_frequency_lo:
  .byte $0c,$1c,$2d,$3e,$51,$66,$7b,$91,$a9,$c3,$dd,$fa,$18,$38,$5a,$7d,$a3,$cc,$f6,$23,$53,$86,$bb,$f4,$30,$70,$b4,$fb,$47,$98,$ed,$47,$a7,$0c,$77,$e9,$61,$e1,$68,$f7,$8f,$30,$da,$8f,$4e,$18,$ef,$d2,$c3,$c3,$d1,$ef,$1f,$60,$b5,$1e,$9c,$31,$df,$a5,$87,$86,$a2,$df,$3e,$c1,$6b,$3c,$39,$63,$be,$4b,$0f,$0c,$45,$bf,$7d,$83,$d6,$61,$73,$c7,$7c,$97,$1e,$18,$8b,$7e,$fa,$06,$ac,$f3,$e6,$8f,$f8,$2e
gb_frequency_hi:
  .byte $01,$01,$01,$01,$01,$01,$01,$01,$01,$01,$01,$01,$02,$02,$02,$02,$02,$02,$02,$03,$03,$03,$03,$03,$04,$04,$04,$04,$05,$05,$05,$06,$06,$07,$07,$07,$08,$08,$09,$09,$0a,$0b,$0b,$0c,$0d,$0e,$0e,$0f,$10,$11,$12,$13,$15,$16,$17,$19,$1a,$1c,$1d,$1f,$21,$23,$25,$27,$2a,$2c,$2f,$32,$35,$38,$3b,$3f,$43,$47,$4b,$4f,$54,$59,$5e,$68,$6a,$70,$77,$7e,$86,$8e,$96,$9f,$a8,$b3,$bd,$c8,$d4,$e1,$ee,$fd
gb_sid_offsets:
  .byte $00,$07,$0e
