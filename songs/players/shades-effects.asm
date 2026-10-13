sd_portamento:
  LDA sd_portamento_step_lo,X
  BNE sd_portamento_enabled
  RTS
sd_portamento_enabled:
  LDA sd_mode,X
  CMP #$01
  BNE sd_portamento_not_down
  JMP sd_portamento_subtract
sd_portamento_not_down:
  CMP #$02
  BNE sd_portamento_target
  JMP sd_portamento_add
sd_portamento_target:
  LDA sd_frequency_hi,X
  CMP sd_target_frequency_hi,X
  BCC sd_portamento_rising
  BNE sd_portamento_falling
  LDA sd_frequency_lo,X
  CMP sd_target_frequency_lo,X
  BCC sd_portamento_rising
  BNE sd_portamento_falling
  RTS
sd_portamento_rising:
  SEC
  LDA sd_target_frequency_lo,X
  SBC sd_frequency_lo,X
  STA sd_tmp_lo
  LDA sd_target_frequency_hi,X
  SBC sd_frequency_hi,X
  CMP sd_portamento_step_hi,X
  BCC sd_portamento_snap
  BNE sd_portamento_add
  LDA sd_tmp_lo
  CMP sd_portamento_step_lo,X
  BCC sd_portamento_snap
  JMP sd_portamento_add
sd_portamento_falling:
  SEC
  LDA sd_frequency_lo,X
  SBC sd_target_frequency_lo,X
  STA sd_tmp_lo
  LDA sd_frequency_hi,X
  SBC sd_target_frequency_hi,X
  CMP sd_portamento_step_hi,X
  BCC sd_portamento_snap
  BNE sd_portamento_subtract
  ; The executed downward equal-high comparison differs from upward snapping.
  ; shades_programs.advance_portamento and its source fixture settle this edge.
  LDA sd_tmp_lo
  CMP sd_portamento_step_lo,X
  BCS sd_portamento_snap
  JMP sd_portamento_subtract
sd_portamento_snap:
  LDA sd_target_frequency_lo,X
  STA sd_frequency_lo,X
  LDA sd_target_frequency_hi,X
  STA sd_frequency_hi,X
  LDA sd_vibrato_delay,X
  AND #$FD
  STA sd_vibrato_delay,X
  JMP sd_write_pitch
sd_portamento_add:
  CLC
  LDA sd_frequency_lo,X
  ADC sd_portamento_step_lo,X
  STA sd_frequency_lo,X
  LDA sd_frequency_hi,X
  ADC sd_portamento_step_hi,X
  STA sd_frequency_hi,X
  JMP sd_portamento_delay
sd_portamento_subtract:
  SEC
  LDA sd_frequency_lo,X
  SBC sd_portamento_step_lo,X
  STA sd_frequency_lo,X
  LDA sd_frequency_hi,X
  SBC sd_portamento_step_hi,X
  STA sd_frequency_hi,X
sd_portamento_delay:
  LDA sd_vibrato_delay,X
  ORA #$02
  STA sd_vibrato_delay,X
  JMP sd_write_pitch

sd_vibrato:
  LDA sd_vibrato_extent,X
  BNE sd_vibrato_enabled
  RTS
sd_vibrato_enabled:
  LDA sd_vibrato_delay,X
  BEQ sd_vibrato_phase_test
  DEC sd_vibrato_delay,X
  BEQ sd_vibrato_delayed_return
  RTS
sd_vibrato_delayed_return:
  ; The model's executed delayed-return fixture preserves both pitch stores.
  JSR sd_vibrato_minus
  JSR sd_vibrato_minus
  LDA #$00
  STA sd_vibrato_phase,X
  RTS
sd_vibrato_phase_test:
  LDA sd_vibrato_phase,X
  BMI sd_vibrato_minus
  CMP sd_vibrato_extent,X
  BCC sd_vibrato_plus
  LDA #$00
  SEC
  SBC sd_vibrato_extent,X
  STA sd_vibrato_phase,X
  RTS
sd_vibrato_plus:
  CLC
  LDA sd_frequency_lo,X
  ADC sd_vibrato_step,X
  STA sd_frequency_lo,X
  LDA sd_frequency_hi,X
  ADC #$00
  STA sd_frequency_hi,X
  JMP sd_vibrato_moved
sd_vibrato_minus:
  SEC
  LDA sd_frequency_lo,X
  SBC sd_vibrato_step,X
  STA sd_frequency_lo,X
  LDA sd_frequency_hi,X
  SBC #$00
  STA sd_frequency_hi,X
sd_vibrato_moved:
  LDA sd_frequency_lo,X
  STA sd_target_frequency_lo,X
  LDA sd_frequency_hi,X
  STA sd_target_frequency_hi,X
  INC sd_vibrato_phase,X
  JMP sd_write_pitch

sd_filter:
  LDA sd_filter_up_calls
  BEQ sd_filter_down
  DEC sd_filter_up_calls
  CLC
  LDA sd_filter_cutoff_low
  ADC sd_filter_fine_step
  STA sd_filter_cutoff_low
  CMP #$07
  BCC sd_filter_write
  AND #$07
  STA sd_filter_cutoff_low
  CLC
  LDA sd_filter_cutoff_high
  ADC sd_filter_coarse_step
  STA sd_filter_cutoff_high
  JMP sd_filter_write
sd_filter_down:
  LDA sd_filter_down_calls
  BNE sd_filter_descending
  RTS
sd_filter_descending:
  DEC sd_filter_down_calls
  SEC
  LDA sd_filter_cutoff_low
  SBC sd_filter_fine_step
  STA sd_filter_cutoff_low
  BCS sd_filter_write
  AND #$07
  STA sd_filter_cutoff_low
  LDA sd_filter_cutoff_high
  CMP sd_filter_coarse_step
  BCC sd_filter_write
  SEC
  SBC sd_filter_coarse_step
  STA sd_filter_cutoff_high
sd_filter_write:
  JMP sd_write_filter

sd_pulse_up:
  LDA sd_pulse_up_calls,X
  BNE sd_pulse_ascending
  RTS
sd_pulse_ascending:
  CLC
  LDA sd_pulse_width_lo,X
  ADC sd_pulse_step,X
  STA sd_pulse_width_lo,X
  LDA sd_pulse_width_hi,X
  ADC #$00
  STA sd_pulse_width_hi,X
  DEC sd_pulse_up_calls,X
  JMP sd_write_pulse
sd_pulse_down:
  LDA sd_pulse_up_calls,X
  BEQ sd_pulse_check_down
  RTS
sd_pulse_check_down:
  LDA sd_pulse_down_calls,X
  BNE sd_pulse_check_width
  RTS
sd_pulse_check_width:
  LDA sd_pulse_width_hi,X
  BNE sd_pulse_descending
  LDA sd_pulse_width_lo,X
  CMP sd_pulse_step,X
  BCS sd_pulse_descending
  RTS
sd_pulse_descending:
  SEC
  LDA sd_pulse_width_lo,X
  SBC sd_pulse_step,X
  STA sd_pulse_width_lo,X
  LDA sd_pulse_width_hi,X
  SBC #$00
  STA sd_pulse_width_hi,X
  DEC sd_pulse_down_calls,X
  JMP sd_write_pulse
