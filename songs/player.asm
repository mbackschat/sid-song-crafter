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

; VIC-II $D011 bit 7 changes at raster 256; crossing both edges prevents
; duplicate calls in one PAL frame (Commodore PRG, VIC-II register 17).
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
    sta event_index
    sta ticks_left
    sta finished
    lda #ATTACK_DECAY
    sta $d405
    lda #SUSTAIN_RELEASE
    sta $d406
    lda #VOLUME
    sta $d418
    rts

tick:
    lda finished
    bne tick_return
    lda ticks_left
    beq next_event
    dec ticks_left
    lda ticks_left
    beq next_event
    cmp #RELEASE_TICKS
    bne tick_return
    lda #WAVEFORM
    sta $d404
tick_return:
    rts

next_event:
    ldx event_index
    cpx #EVENT_COUNT
    bcc start_event
    lda #WAVEFORM
    sta $d404
    lda #0
    sta $d418
    lda #1
    sta finished
    rts

start_event:
    lda duration_ticks,x
    sta ticks_left
    lda frequency_low,x
    sta $d400
    lda frequency_high,x
    sta $d401
    lda control,x
    sta $d404
    inc event_index
    rts

event_index:
    .byte 0
ticks_left:
    .byte 0
finished:
    .byte 0
