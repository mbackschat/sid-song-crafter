fd_note_changed:
  LDA slide_enabled,X
  BEQ fd_pitch_note_vibrato
  DEC slide_enabled,X
fd_pitch_note_vibrato:
  LDA vibrato_enabled,X
  BEQ fd_pitch_note_done
  DEC vibrato_enabled,X
fd_pitch_note_done:
  RTS

fd_step_pitch:
  ; advance_pitch in scripts/flashdance_pitch.py requires binary word wrapping.
  CLD
  LDA slide_enabled,X
  BEQ fd_pitch_check_vibrato
  LDA slide_subtract,X
  BNE fd_pitch_slide_subtract
  CLC
  LDA slide_offset_lo,X
  ADC slide_step_lo,X
  STA slide_offset_lo,X
  LDA slide_offset_hi,X
  ADC slide_step_hi,X
  STA slide_offset_hi,X
  JMP fd_pitch_slide_apply
fd_pitch_slide_subtract:
  SEC
  LDA slide_offset_lo,X
  SBC slide_step_lo,X
  STA slide_offset_lo,X
  LDA slide_offset_hi,X
  SBC slide_step_hi,X
  STA slide_offset_hi,X
fd_pitch_slide_apply:
  LDA absolute_pitch,X
  BEQ fd_pitch_slide_relative
  RTS
fd_pitch_slide_relative:
  CLC
  LDA frequency_lo,X
  ADC slide_offset_lo,X
  STA frequency_lo,X
  LDA frequency_hi,X
  ADC slide_offset_hi,X
  STA frequency_hi,X
  RTS

fd_pitch_check_vibrato:
  LDA vibrato_enabled,X
  BNE fd_pitch_vibrato
  RTS
fd_pitch_vibrato:
  LDY base_note,X
  LDA frequency_table_lo,Y
  STA fd_tmp_lo
  LDA frequency_table_hi,Y
  STA fd_tmp_hi
  INY
  SEC
  LDA frequency_table_lo,Y
  SBC fd_tmp_lo
  STA fd_tmp_lo
  LDA frequency_table_hi,Y
  SBC fd_tmp_hi
  CLC
  ADC vibrato_depth,X
  STA fd_tmp_hi
  LDY vibrato_shift,X
  BEQ fd_pitch_vibrato_phase
fd_pitch_vibrato_shift:
  LSR fd_tmp_hi
  ROR fd_tmp_lo
  DEY
  BNE fd_pitch_vibrato_shift
fd_pitch_vibrato_phase:
  DEC vibrato_remaining,X
  BPL fd_pitch_vibrato_direction
  LDA vibrato_direction,X
  EOR #$01
  STA vibrato_direction,X
  LDA vibrato_interval,X
  STA vibrato_remaining,X
fd_pitch_vibrato_direction:
  LDA vibrato_direction,X
  BNE fd_pitch_vibrato_subtract
  CLC
  LDA vibrato_offset_lo,X
  ADC fd_tmp_lo
  STA vibrato_offset_lo,X
  LDA vibrato_offset_hi,X
  ADC fd_tmp_hi
  STA vibrato_offset_hi,X
  JMP fd_pitch_vibrato_apply
fd_pitch_vibrato_subtract:
  SEC
  LDA vibrato_offset_lo,X
  SBC fd_tmp_lo
  STA vibrato_offset_lo,X
  LDA vibrato_offset_hi,X
  SBC fd_tmp_hi
  STA vibrato_offset_hi,X
fd_pitch_vibrato_apply:
  CLC
  LDA vibrato_depth,X
  ADC vibrato_growth,X
  STA vibrato_depth,X
  CLC
  LDA frequency_lo,X
  ADC vibrato_offset_lo,X
  STA frequency_lo,X
  LDA frequency_hi,X
  ADC vibrato_offset_hi,X
  STA frequency_hi,X
  RTS
