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
