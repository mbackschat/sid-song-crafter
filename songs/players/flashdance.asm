entry_init:
  CLD
  LDY #$00
fd_restore_state:
  LDA fd_initial_state,Y
  STA fd_state_begin,Y
  INY
  CPY #FD_STATE_BYTES
  BNE fd_restore_state
  LDX #$02
fd_restore_score:
  TXA
  ASL A
  TAY
  LDA fd_score_starts,Y
  STA fd_score_lo,X
  INY
  LDA fd_score_starts,Y
  STA fd_score_hi,X
  DEX
  BPL fd_restore_score
  LDY #$00
  LDA #$00
fd_clear_sid:
  STA FD_SID_FREQ_LO,Y
  INY
  CPY #$19
  BNE fd_clear_sid
  LDA fd_volume
  STA FD_SID_MODE_VOLUME
  RTS

entry_play:
  LDA $FB
  PHA
  LDA $FC
  PHA
  JSR fd_play_frame
  PLA
  STA $FC
  PLA
  STA $FB
  RTS

fd_play_frame:
  CLD
  LDA fd_ended
  BEQ fd_check_phase
  JMP fd_mute
fd_check_phase:
  LDA fd_tick_hi
  CMP #FD_STOP_HI
  BCC fd_phase_music
  BNE fd_phase_tail
  LDA fd_tick_lo
  CMP #FD_STOP_LO
  BCC fd_phase_music
fd_phase_tail:
  LDA fd_tick_hi
  CMP #FD_END_HI
  BCC fd_phase_release
  BNE fd_phase_ended
  LDA fd_tick_lo
  CMP #FD_END_LO
  BCC fd_phase_release
fd_phase_ended:
  LDA #$01
  STA fd_ended
  JMP fd_mute
fd_phase_music:
  LDA #$00
  STA fd_tail
  JMP fd_play_voices
fd_phase_release:
  LDA #$01
  STA fd_tail
  LDA fd_tick_hi
  CMP fd_fade_tick_hi
  BNE fd_play_voices
  LDA fd_tick_lo
  CMP fd_fade_tick_lo
  BNE fd_play_voices
  LDA fd_volume
  BEQ fd_fade_write
  DEC fd_volume
fd_fade_write:
  LDA fd_filter_mode
  ORA fd_volume
  STA FD_SID_MODE_VOLUME
  CLC
  LDA fd_fade_tick_lo
  ADC #FD_FADE_STEP
  STA fd_fade_tick_lo
  LDA fd_fade_tick_hi
  ADC #$00
  STA fd_fade_tick_hi
fd_play_voices:
  LDX #$02
fd_play_voice:
  LDA #$00
  STA fd_restart
  LDA fd_tail
  BEQ fd_voice_score
  LDA #$FE
  STA gate_mask,X
  JMP fd_voice_body
fd_voice_score:
  JSR fd_delayed_sr
  JSR fd_score_commands
  LDA fd_restart
  BEQ fd_voice_body
  JSR fd_start_voice
  JMP fd_next_voice
fd_voice_body:
  CPX #FD_FILTER_OWNER
  BNE fd_voice_program
  JSR fd_step_filter
fd_voice_program:
  JSR fd_step_pwm
  JSR fd_step_wave
  JSR fd_step_pitch
  LDY fd_voice_offsets,X
  LDA pulse_lo,X
  STA FD_SID_PULSE_LO,Y
  LDA pulse_hi,X
  STA FD_SID_PULSE_HI,Y
  LDA filter_cutoff
  STA FD_SID_CUTOFF
  LDA frequency_lo,X
  STA FD_SID_FREQ_LO,Y
  LDA frequency_hi,X
  STA FD_SID_FREQ_HI,Y
  LDA wave_control,X
  STA FD_SID_CONTROL,Y
fd_next_voice:
  DEX
  BPL fd_play_voice
  INC fd_tick_lo
  BNE fd_frame_done
  INC fd_tick_hi
fd_frame_done:
  RTS

fd_mute:
  LDA #$00
  STA FD_SID_CONTROL
  STA FD_SID_CONTROL_1
  STA FD_SID_CONTROL_2
  STA FD_SID_MODE_VOLUME
  RTS

fd_delayed_sr:
  LDA fd_pending_sr,X
  BEQ fd_delayed_done
  LDA fd_sr_tick_hi,X
  CMP fd_tick_hi
  BNE fd_delayed_done
  LDA fd_sr_tick_lo,X
  CMP fd_tick_lo
  BNE fd_delayed_done
  LDA #$00
  STA fd_pending_sr,X
  LDY fd_voice_offsets,X
  LDA fd_sr_value,X
  STA FD_SID_SR,Y
fd_delayed_done:
  RTS

fd_score_commands:
  LDA fd_score_lo,X
  STA $FB
  LDA fd_score_hi,X
  STA $FC
fd_score_next:
  LDY #$01
  LDA ($FB),Y
  CMP fd_tick_hi
  BNE fd_score_done
  DEY
  LDA ($FB),Y
  CMP fd_tick_lo
  BNE fd_score_done
  LDY #$02
  LDA ($FB),Y
  JSR fd_dispatch_command
  CLC
  LDA $FB
  ADC #$08
  STA $FB
  BCC fd_score_next
  INC $FC
  JMP fd_score_next
fd_score_done:
  LDA $FB
  STA fd_score_lo,X
  LDA $FC
  STA fd_score_hi,X
  RTS

fd_dispatch_command:
  CMP #FD_CMD_INSTRUMENT
  BNE fd_dispatch_note
  JMP fd_command_instrument
fd_dispatch_note:
  CMP #FD_CMD_NOTE
  BNE fd_dispatch_hold
  JMP fd_command_note
fd_dispatch_hold:
  CMP #FD_CMD_HOLD
  BNE fd_dispatch_off
  LDA #$FF
  STA gate_mask,X
  RTS
fd_dispatch_off:
  CMP #FD_CMD_OFF
  BNE fd_dispatch_vibrato
  LDA #$FE
  STA gate_mask,X
  RTS
fd_dispatch_vibrato:
  CMP #FD_CMD_VIBRATO
  BNE fd_dispatch_slide
  JMP fd_command_vibrato
fd_dispatch_slide:
  CMP #FD_CMD_SLIDE
  BNE fd_dispatch_sr
  JMP fd_command_slide
fd_dispatch_sr:
  JMP fd_command_sr

fd_command_instrument:
  LDY #$03
  LDA ($FB),Y
  STA instrument,X
  RTS
fd_command_note:
  LDY #$03
  LDA ($FB),Y
  STA base_note,X
  INY
  LDA ($FB),Y
  STA transpose,X
  INY
  LDA ($FB),Y
  STA fd_restart
  LDA #$FF
  STA gate_mask,X
  JMP fd_note_changed
fd_command_vibrato:
  LDY #$03
  LDA ($FB),Y
  STA vibrato_enabled,X
  INY
  LDA ($FB),Y
  STA vibrato_interval,X
  INY
  LDA ($FB),Y
  STA vibrato_remaining,X
  INY
  LDA ($FB),Y
  STA vibrato_shift,X
  INY
  LDA ($FB),Y
  STA vibrato_growth,X
  LDA #$00
  STA vibrato_direction,X
  STA vibrato_depth,X
  STA vibrato_offset_lo,X
  STA vibrato_offset_hi,X
  RTS
fd_command_slide:
  LDY #$03
  LDA ($FB),Y
  STA slide_enabled,X
  INY
  LDA ($FB),Y
  STA slide_step_lo,X
  INY
  LDA ($FB),Y
  STA slide_step_hi,X
  LDA #$00
  STA slide_subtract,X
  STA slide_offset_lo,X
  STA slide_offset_hi,X
  RTS
fd_command_sr:
  LDY #$03
  LDA ($FB),Y
  CLC
  ADC fd_tick_lo
  STA fd_sr_tick_lo,X
  LDA fd_tick_hi
  ADC #$00
  STA fd_sr_tick_hi,X
  INY
  LDA ($FB),Y
  STA fd_sr_value,X
  LDA #$01
  STA fd_pending_sr,X
  RTS

fd_start_voice:
  LDY fd_voice_offsets,X
  LDA #$00
  STA FD_SID_AD,Y
  LDA #$0F
  STA FD_SID_SR,Y
  LDA #$08
  STA FD_SID_CONTROL,Y
  JSR fd_init_voice
  LDY instrument,X
  LDA instrument_filter_command,Y
  STA fd_tmp_lo
  AND #$0F
  BEQ fd_filter_unroute
  ASL A
  ASL A
  ASL A
  ASL A
  STA fd_filter_mode
  ORA fd_volume
  STA FD_SID_MODE_VOLUME
  LDA fd_routing
  AND #$0F
  ORA fd_voice_filter_bits,X
  STA fd_tmp_hi
  LDA fd_tmp_lo
  AND #$F0
  ORA fd_tmp_hi
  STA fd_routing
  JMP fd_filter_route_write
fd_filter_unroute:
  LDA fd_routing
  AND fd_voice_filter_masks,X
  STA fd_routing
fd_filter_route_write:
  LDA fd_routing
  STA FD_SID_ROUTING
  JSR fd_init_filter
  LDY instrument,X
  LDA instrument_ad,Y
  LDY fd_voice_offsets,X
  STA FD_SID_AD,Y
  LDY instrument,X
  LDA instrument_sr,Y
  LDY fd_voice_offsets,X
  STA FD_SID_SR,Y
  LDA #$09
  STA FD_SID_CONTROL,Y
  RTS
