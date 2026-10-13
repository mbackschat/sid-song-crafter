entry_init:
  CLD
  JSR gh_restore_state
  LDX #$1c
gh_init_clear:
  LDA #$08
  STA $d400,X
  LDA #$00
  STA $d400,X
  DEX
  BPL gh_init_clear
gh_init_done:
  RTS

entry_play:
  CLD
  LDX #$00
gh_play_voice:
  JSR gh_play_step
  INX
  CPX #$03
  BNE gh_play_voice
  JSR gh_select_filter_restart
  JSR gh_advance_filter
gh_call_done:
  RTS

gh_play_step:
  LDA gh_score_enabled,X
  BMI gh_play_active
  RTS
gh_play_active:
  JSR gh_advance_sound
  DEC gh_score_remaining,X
  LDA gh_score_remaining,X
  CMP gh_gate_time,X
  BEQ gh_score_gate
  LDA gh_rest_remaining,X
  BNE gh_score_rest_countdown
gh_score_gate:
  LDA gh_waveform,X
  AND #$fe
  LDY gh_sid_offsets,X
  STA $d404,Y
  INC gh_rest_remaining,X
gh_score_rest_countdown:
  DEC gh_rest_remaining,X
  LDA gh_score_remaining,X
  BEQ gh_score_begin
  RTS
gh_score_begin:
  LDA #$00
  STA gh_command_budget_lo
  STA gh_command_budget_hi
gh_score_fetch:
  LDA gh_command_budget_hi
  BEQ gh_score_budget_ready
  JMP gh_score_failure
gh_score_budget_ready:
  INC gh_command_budget_lo
  BNE gh_score_budget_counted
  INC gh_command_budget_hi
gh_score_budget_counted:
  LDA gh_score_cursor_lo,X
  STA $e0
  LDA gh_score_cursor_hi,X
  STA $e1
  LDY #$00
  LDA gh_score_override,X
  BEQ gh_score_variant
  LDY #$02
gh_score_variant:
  LDA ($e0),Y
  STA $e2
  INY
  LDA ($e0),Y
  STA $e3
  ORA $e2
  BNE gh_score_variant_ready
  JMP gh_score_failure
gh_score_variant_ready:
  LDY #$01
  LDA ($e2),Y
  STA $e4
  INY
  LDA ($e2),Y
  STA $e5
  INY
  LDA ($e2),Y
  STA $e6
  INY
  LDA ($e2),Y
  STA $e7
  LDY #$00
  LDA ($e2),Y
  TAY
  LDA gh_kind_ptr_lo,Y
  STA $e9
  LDA gh_kind_ptr_hi,Y
  STA $ea
  JMP ($e9)

gh_continue:
  JSR gh_save_next
  JMP gh_score_fetch
gh_save_next:
  LDA $e4
  STA gh_score_cursor_lo,X
  LDA $e5
  STA gh_score_cursor_hi,X
  RTS

gh_kind_note:
  JSR gh_select_filter_restart
  LDY #$05
  LDA ($e2),Y
  JSR gh_note_setup
  JMP gh_row_duration
gh_kind_rest:
  LDA gh_rest_reload,X
  STA gh_rest_remaining,X
gh_row_duration:
  LDA gh_score_override,X
  BNE gh_row_store_duration
  LDY #$06
  LDA ($e2),Y
gh_row_store_duration:
  STA gh_score_remaining,X
  JMP gh_save_next

gh_cmd_repeat_start:
  LDY #$05
  LDA ($e2),Y
  STA gh_score_repeat,X
  LDA $e4
  STA gh_score_repeat_lo,X
  LDA $e5
  STA gh_score_repeat_hi,X
  JMP gh_continue
gh_cmd_repeat_end:
  DEC gh_score_repeat,X
  BEQ gh_continue
  LDA gh_score_repeat_lo,X
  STA gh_score_cursor_lo,X
  LDA gh_score_repeat_hi,X
  STA gh_score_cursor_hi,X
  JMP gh_score_fetch

gh_cmd_call:
  LDA gh_score_depth,X
  CMP #$08
  BCC gh_score_push
  JMP gh_score_failure
gh_score_push:
  CLC
  ADC gh_stack_bases,X
  TAY
  LDA $e4
  STA gh_score_return_lo,Y
  LDA $e5
  STA gh_score_return_hi,Y
  INC gh_score_depth,X
  LDA $e6
  STA gh_score_cursor_lo,X
  LDA $e7
  STA gh_score_cursor_hi,X
  JMP gh_score_fetch
gh_cmd_return:
  LDA gh_score_depth,X
  BNE gh_score_pop
  JMP gh_score_failure
gh_score_pop:
  DEC gh_score_depth,X
  LDA gh_score_depth,X
  CLC
  ADC gh_stack_bases,X
  TAY
  LDA gh_score_return_lo,Y
  STA gh_score_cursor_lo,X
  LDA gh_score_return_hi,Y
  STA gh_score_cursor_hi,X
  JMP gh_score_fetch
gh_cmd_disable_voice:
  INC gh_score_enabled,X
  RTS

gh_cmd_rest_parameters:
  LDA #$01
  STA gh_gate_enabled,X
  LDY #$05
  LDA ($e2),Y
  STA gh_rest_reload,X
  JMP gh_continue
gh_cmd_waveform:
  LDY #$05
  LDA ($e2),Y
  STA gh_waveform,X
  LDY gh_sid_offsets,X
  STA $d404,Y
  AND #$40
  BEQ gh_waveform_no_pulse
  LDA #$ff
  JMP gh_waveform_phase
gh_waveform_no_pulse:
  LDA #$01
gh_waveform_phase:
  STA gh_pulse_direction,X
  STA gh_pulse_restart,X
  JMP gh_continue
gh_cmd_pulse_parameters:
  LDY #$05
  LDA ($e2),Y
  STA gh_pulse_step,X
  INY
  LDA ($e2),Y
  STA gh_pulse_default_lo,X
  STA gh_pulse_word_lo,X
  INY
  LDA ($e2),Y
  STA gh_pulse_default_hi,X
  STA gh_pulse_word_hi,X
  ORA gh_pulse_word_lo,X
  BNE gh_pulse_parameters_done
  LDA gh_pulse_fallback_lo,X
  STA gh_pulse_word_lo,X
  LDA gh_pulse_fallback_hi,X
  STA gh_pulse_word_hi,X
gh_pulse_parameters_done:
  JMP gh_continue

gh_cmd_filter_parameters:
  LDY #$05
  LDA ($e2),Y
  STA gh_filter_step
  INY
  LDA ($e2),Y
  STA gh_filter_restart_phase,X
  INY
  LDA ($e2),Y
  STA gh_filter_word_lo
  STA gh_filter_default_lo
  INY
  LDA ($e2),Y
  STA gh_filter_word_hi
  STA gh_filter_default_hi
  INY
  LDA ($e2),Y
  STA gh_filter_lower_lo
  INY
  LDA ($e2),Y
  STA gh_filter_lower_hi
  INY
  LDA ($e2),Y
  STA gh_filter_upper_lo
  INY
  LDA ($e2),Y
  STA gh_filter_upper_hi
  JSR gh_select_filter_restart
  JMP gh_continue
gh_cmd_filter_owner:
  STX gh_filter_owner
  JSR gh_select_filter_restart
  JMP gh_continue
gh_select_filter_restart:
  LDY gh_filter_owner
  LDA gh_filter_restart_phase,Y
  STA gh_filter_reset_direction
  RTS

gh_cmd_sid_store_list:
  LDY #$05
  LDA ($e2),Y
  STA $e8
  LDA $e2
  CLC
  ADC #$06
  STA $e2
  BCC gh_store_list
  INC $e3
gh_store_list:
  LDY #$00
  LDA ($e2),Y
  STA $e9
  INY
  LDA ($e2),Y
  LDY $e9
  STA $d400,Y
  LDA $e2
  CLC
  ADC #$02
  STA $e2
  BCC gh_store_advanced
  INC $e3
gh_store_advanced:
  DEC $e8
  BNE gh_store_list
  JMP gh_continue

gh_score_failure:
  LDA #$01
  STA gh_score_failed
  RTS
