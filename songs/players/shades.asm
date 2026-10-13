entry_init:
  CLD
  LDY #$00
sd_restore_state:
  LDA sd_initial_state,Y
  STA sd_state_begin,Y
  INY
  CPY #SD_STATE_BYTES
  BNE sd_restore_state
  RTS

entry_play:
  LDA $FB
  PHA
  LDA $FC
  PHA
  JSR sd_frame
  PLA
  STA $FC
  PLA
  STA $FB
  RTS

sd_frame:
  CLD
  LDA sd_ended
  BEQ sd_check_stop
  RTS
sd_check_stop:
  LDA sd_tick_hi
  CMP #SD_STOP_HI
  BNE sd_check_setup
  LDA sd_tick_lo
  CMP #SD_STOP_LO
  BNE sd_check_setup
  LDA #$01
  STA sd_ended
  LDA #$00
  STA $D404
  STA $D40B
  STA $D412
  STA $D418
  RTS
sd_check_setup:
  LDA sd_tick_lo
  ORA sd_tick_hi
  BNE sd_effects
  JSR sd_select
  JMP sd_tick
sd_effects:
  LDX #$00
sd_portamento_loop:
  JSR sd_portamento
  INX
  CPX #$03
  BNE sd_portamento_loop
  LDX #$00
sd_vibrato_loop:
  JSR sd_vibrato
  INX
  CPX #$03
  BNE sd_vibrato_loop
  JSR sd_filter
  LDX #$00
sd_pulse_up_loop:
  JSR sd_pulse_up
  INX
  CPX #$03
  BNE sd_pulse_up_loop
  LDX #$00
sd_pulse_down_loop:
  JSR sd_pulse_down
  INX
  CPX #$03
  BNE sd_pulse_down_loop
  LDA sd_counter
  BEQ sd_row_frame
  DEC sd_counter
  JMP sd_tick
sd_row_frame:
  JSR sd_fade
  LDA sd_select_pending
  BEQ sd_row_voices
  INC sd_order
  JSR sd_select
sd_row_voices:
  LDX #$00
sd_row_voice_loop:
  JSR sd_consume_row
  INX
  CPX #$03
  BNE sd_row_voice_loop
  INC sd_row
  DEC sd_rows_left
  BNE sd_row_countdown
  LDA #$01
  STA sd_select_pending
sd_row_countdown:
  SEC
  LDA sd_duration
  SBC #$01
  STA sd_counter
sd_tick:
  INC sd_tick_lo
  BNE sd_tick_done
  INC sd_tick_hi
sd_tick_done:
  RTS

sd_select:
  LDA sd_order
  LSR A
  LSR A
  LSR A
  LSR A
  STA sd_tmp_hi
  LDA sd_order
  ASL A
  ASL A
  ASL A
  ASL A
  CLC
  ADC sd_order_base
  STA $FB
  LDA sd_tmp_hi
  ADC sd_order_base+1
  STA $FC
  LDX #$00
sd_select_patterns:
  TXA
  ASL A
  TAY
  LDA ($FB),Y
  STA sd_pattern_lo,X
  INY
  LDA ($FB),Y
  STA sd_pattern_hi,X
  TXA
  CLC
  ADC #$06
  TAY
  LDA ($FB),Y
  STA sd_transpose,X
  INX
  CPX #$03
  BNE sd_select_patterns
  LDY #$09
  LDA ($FB),Y
  STA sd_block
  INY
  LDA ($FB),Y
  STA sd_absolute
  INY
  LDA ($FB),Y
  STA sd_rows_left
  INY
  LDA ($FB),Y
  STA sd_duration
  INY
  LDA ($FB),Y
  STA $DC05
  INY
  LDA ($FB),Y
  BEQ sd_select_fade_done
  CMP #$01
  BNE sd_select_start_fade
  LDA #$00
  STA sd_fade_interval
  STA sd_fade_countdown
  JMP sd_select_fade_done
sd_select_start_fade:
  STA sd_fade_interval
  SEC
  SBC #$01
  STA sd_fade_countdown
sd_select_fade_done:
  LDA #$00
  STA sd_row
  STA sd_counter
  STA sd_select_pending
  JSR sd_load_block
  LDY #$0E
  LDA ($FB),Y
  CMP #$02
  BCC sd_select_done
  LDA sd_filter_mode_volume
  STA sd_fade_volume
sd_select_done:
  RTS

sd_patch_y:
  LDA sd_block
  ASL A
  CLC
  ADC sd_block
  STA sd_patch_index
  TXA
  CLC
  ADC sd_patch_index
  TAY
  RTS

sd_load_block:
  LDX #$00
sd_load_envelopes:
  JSR sd_patch_y
  LDA sd_patch_attack_decay,Y
  STA sd_attack_decay,X
  LDA sd_patch_sustain_release,Y
  STA sd_sustain_release,X
  INX
  CPX #$03
  BNE sd_load_envelopes
  LDY sd_block
  LDA sd_block_routing,Y
  STA sd_filter_routing
  LDA sd_block_mode_volume,Y
  STA sd_filter_mode_volume
  RTS

sd_fade:
  LDA sd_fade_interval
  BEQ sd_fade_done
  LDA sd_fade_countdown
  BEQ sd_fade_step
  DEC sd_fade_countdown
  RTS
sd_fade_step:
  SEC
  LDA sd_fade_interval
  SBC #$01
  STA sd_fade_countdown
  LDA sd_fade_volume
  AND #$0F
  BEQ sd_fade_done
  DEC sd_fade_volume
  LDA sd_fade_volume
  STA $D418
sd_fade_done:
  RTS

sd_consume_row:
  LDA sd_last_row,X
  STA sd_previous
  LDA sd_pattern_lo,X
  STA $FB
  LDA sd_pattern_hi,X
  STA $FC
  LDY sd_row
  LDA ($FB),Y
  CMP #$80
  BNE sd_row_not_hold
  LDA #$01
  STA sd_last_row,X
  RTS
sd_row_not_hold:
  CMP #$00
  BNE sd_row_note
  STA sd_last_row,X
  JMP sd_row_off
sd_row_note:
  PHA
  AND #$80
  STA sd_gate
  PLA
  AND #$7F
  STA sd_note
  LDA #$02
  STA sd_last_row,X
  CPX #$00
  BNE sd_transpose_note
  LDA sd_absolute
  BEQ sd_transpose_note
  LDA sd_note
  CMP #$30
  BCS sd_resolved_note
sd_transpose_note:
  CLC
  LDA sd_note
  ADC sd_transpose,X
  STA sd_note
sd_resolved_note:
  LDY sd_note
  LDA sd_frequency_table_lo,Y
  STA sd_tmp_lo
  LDA sd_frequency_table_hi,Y
  STA sd_tmp_hi
  JSR sd_patch_y
  CLC
  LDA sd_tmp_lo
  ADC sd_patch_fine_tune,Y
  STA sd_tmp_lo
  LDA sd_patch_portamento_step_lo,Y
  BEQ sd_note_frequency
  LDA sd_tmp_lo
  STA sd_target_frequency_lo,X
  LDA sd_tmp_hi
  STA sd_target_frequency_hi,X
  LDA sd_previous
  CMP #$01
  BEQ sd_note_gate
sd_note_frequency:
  LDA sd_tmp_lo
  STA sd_frequency_lo,X
  LDA sd_tmp_hi
  STA sd_frequency_hi,X
sd_note_gate:
  LDA sd_gate
  BEQ sd_row_on
sd_row_off:
  CPX #$01
  BEQ sd_off_write
  LDA sd_previous
  BNE sd_off_write
  RTS
sd_off_write:
  LDA sd_control,X
  AND #$FE
  STA sd_control,X
  JSR sd_reload_modulation
  JMP sd_write_voice

sd_row_on:
  CPX #$00
  BNE sd_on_control
  LDA #$00
  STA sd_percussion
  LDY sd_block
  LDA sd_block_percussion_control,Y
  BEQ sd_on_control
  LDA sd_note
  CMP #$30
  BCC sd_on_control
  LDA #$01
  STA sd_percussion
sd_on_control:
  JSR sd_patch_y
  LDA sd_patch_control,Y
  STA sd_tmp_lo
  CPX #$00
  BNE sd_on_selected_control
  LDA sd_percussion
  BEQ sd_on_selected_control
  LDY sd_block
  LDA sd_block_percussion_control,Y
  STA sd_tmp_lo
  JSR sd_patch_y
sd_on_selected_control:
  LDA sd_tmp_lo
  ORA #$01
  STA sd_control,X
  LDA sd_patch_pulse_width_lo,Y
  STA sd_pulse_width_lo,X
  LDA sd_patch_pulse_width_hi,Y
  STA sd_pulse_width_hi,X
  LDA sd_patch_pulse_up_calls,Y
  STA sd_pulse_up_calls,X
  LDA sd_patch_pulse_down_calls,Y
  STA sd_pulse_down_calls,X
  LDA sd_patch_vibrato_delay,Y
  STA sd_vibrato_delay,X
  LDA sd_tmp_lo
  PHA
  JSR sd_trigger_filter
  JSR sd_reload_modulation
  PLA
  LDY sd_voice_offsets,X
  STA $D404,Y
  JMP sd_write_voice

sd_reload_modulation:
  JSR sd_patch_y
  LDA sd_patch_pulse_step,Y
  STA sd_pulse_step,X
  LDA sd_patch_portamento_step_lo,Y
  STA sd_portamento_step_lo,X
  LDA sd_patch_portamento_step_hi,Y
  STA sd_portamento_step_hi,X
  LDA sd_patch_mode,Y
  STA sd_mode,X
  LDA sd_patch_vibrato_extent,Y
  STA sd_vibrato_extent,X
  LDA sd_patch_vibrato_step,Y
  STA sd_vibrato_step,X
  RTS

sd_trigger_filter:
  LDY sd_block
  LDA sd_block_trigger_mask,Y
  AND sd_voice_bits,X
  BNE sd_trigger_selected
  RTS
sd_trigger_selected:
  LDA sd_percussion
  BEQ sd_trigger_normal
  LDA sd_block_trigger_mask,Y
  AND #$01
  BEQ sd_trigger_normal
  LDA sd_percussion_contour_cutoff_low,Y
  STA sd_filter_cutoff_low
  LDA sd_percussion_contour_cutoff_high,Y
  STA sd_filter_cutoff_high
  LDA sd_percussion_contour_up_calls,Y
  STA sd_filter_up_calls
  LDA sd_percussion_contour_down_calls,Y
  STA sd_filter_down_calls
  LDA sd_percussion_contour_fine_step,Y
  STA sd_filter_fine_step
  LDA sd_percussion_contour_coarse_step,Y
  STA sd_filter_coarse_step
  LDA sd_block_percussion_mode_volume,Y
  STA sd_filter_mode_volume
  RTS
sd_trigger_normal:
  LDA sd_contour_cutoff_low,Y
  STA sd_filter_cutoff_low
  LDA sd_contour_cutoff_high,Y
  STA sd_filter_cutoff_high
  LDA sd_contour_up_calls,Y
  STA sd_filter_up_calls
  LDA sd_contour_down_calls,Y
  STA sd_filter_down_calls
  LDA sd_contour_fine_step,Y
  STA sd_filter_fine_step
  LDA sd_contour_coarse_step,Y
  STA sd_filter_coarse_step
  LDA sd_block_mode_volume,Y
  STA sd_filter_mode_volume
  RTS

sd_write_voice:
  CPX #$01
  BNE sd_write_frequency
  LDA sd_sustain_release
  STA $D406
sd_write_frequency:
  JSR sd_write_pitch
  JSR sd_write_pulse
  LDY sd_voice_offsets,X
  LDA sd_attack_decay,X
  STA $D405,Y
  CPX #$00
  BEQ sd_write_control
  LDA sd_sustain_release,X
  STA $D406,Y
sd_write_control:
  LDA sd_control,X
  STA $D404,Y
  JSR sd_write_filter
  LDA sd_filter_routing
  STA $D417
  LDA sd_fade_interval
  BNE sd_write_done
  LDA sd_filter_mode_volume
  STA $D418
sd_write_done:
  RTS

sd_write_pitch:
  LDY sd_voice_offsets,X
  LDA sd_frequency_lo,X
  STA $D400,Y
  LDA sd_frequency_hi,X
  STA $D401,Y
  RTS
sd_write_pulse:
  LDY sd_voice_offsets,X
  LDA sd_pulse_width_lo,X
  STA $D402,Y
  LDA sd_pulse_width_hi,X
  STA $D403,Y
  RTS
sd_write_filter:
  LDA sd_filter_cutoff_low
  STA $D415
  LDA sd_filter_cutoff_high
  STA $D416
  RTS
