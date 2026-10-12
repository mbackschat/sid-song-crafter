.org $0801
    .word basic_end
    .word 10
    .byte $9e, "2064", 0
basic_end:
    .word 0

.org $0810
standalone:
    php
    sei
    lda $00
    pha
    ora #$07
    sta $00
    lda $01
    pha
    ora #$07
    sta $01
    jsr init

; VIC-II $D011 bit 7 crosses at raster 256; both edges prevent duplicate
; calls within a PAL frame (Commodore PRG, VIC-II register 17).
wait_low:
    lda $d011
    bmi wait_low
wait_high:
    lda $d011
    bpl wait_high
    jsr play
    lda finished
    beq wait_low
    pla
    sta $01
    pla
    sta $00
    plp
standalone_return:
    rts

.org $1000
init:
    jmp initialise
play:
    jmp tick

initialise:
    lda #0
    ldx #24
clear_sid:
    sta $d400,x
    dex
    bpl clear_sid
    sta finished
    lda #1
    sta first_tick
    lda #VOICE_0_WAVEFORM
    sta $d404
    lda #VOICE_0_ATTACK_DECAY
    sta $d405
    lda #VOICE_0_SUSTAIN_RELEASE
    sta $d406
    lda #VOICE_0_PULSE_LOW
    sta $d402
    lda #VOICE_0_PULSE_HIGH
    sta $d403
    lda #VOICE_1_WAVEFORM
    sta $d40b
    lda #VOICE_1_ATTACK_DECAY
    sta $d40c
    lda #VOICE_1_SUSTAIN_RELEASE
    sta $d40d
    lda #VOICE_1_PULSE_LOW
    sta $d409
    lda #VOICE_1_PULSE_HIGH
    sta $d40a
    lda #VOICE_2_WAVEFORM
    sta $d412
    lda #VOICE_2_ATTACK_DECAY
    sta $d413
    lda #VOICE_2_SUSTAIN_RELEASE
    sta $d414
    lda #VOICE_2_PULSE_LOW
    sta $d410
    lda #VOICE_2_PULSE_HIGH
    sta $d411
    lda #VOLUME
    sta $d418
    lda #(event_stream & $ff)
    sta stream_read+1
    lda #(event_stream >> 8)
    sta stream_read+2
    jsr read_delay
    rts

tick:
    lda finished
    bne tick_return
    lda first_tick
    beq advance_tick
    lda #0
    sta first_tick
    lda ticks_left_low
    ora ticks_left_high
    beq next_write
    rts
advance_tick:
    lda ticks_left_low
    ora ticks_left_high
    beq next_write
    lda ticks_left_low
    bne decrement_low
    dec ticks_left_high
decrement_low:
    dec ticks_left_low
    lda ticks_left_low
    ora ticks_left_high
    bne tick_return
next_write:
    jsr read_byte
    tax
    jsr read_byte
    cpx #$ff
    beq finish
    sta $d400,x
    jsr read_delay
    lda ticks_left_low
    ora ticks_left_high
    beq next_write
tick_return:
    rts
finish:
    lda #1
    sta finished
    rts

read_delay:
    jsr read_byte
    sta ticks_left_low
    jsr read_byte
    sta ticks_left_high
    rts

; The absolute operand is the 16-bit stream cursor; using RAM code preserves
; the caller's entire zero page (calling contract in docs/three-voice-player.md).
read_byte:
stream_read:
    lda event_stream
    inc stream_read+1
    bne read_return
    inc stream_read+2
read_return:
    rts

ticks_left_low:
    .byte 0
ticks_left_high:
    .byte 0
finished:
    .byte 0
first_tick:
    .byte 0
