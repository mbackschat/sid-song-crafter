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
