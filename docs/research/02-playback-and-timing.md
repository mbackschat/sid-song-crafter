# C64 playback and timing

## Convert notes to frequency words

For equal temperament and A4 = 440 Hz:

```text
frequency_hz = 440 × 2^((midi_note - 69) / 12)
sid_word = round(frequency_hz × 2^24 / clock_hz)
low = sid_word & 255
high = sid_word >> 8
```

The oscillator equation comes from the SID interface; machine clock values below are calculated from libsidplayfp's C64 model constants. Use the intended machine variant rather than a generic “1 MHz”. [S01](sources.md#s01), [S05](sources.md#s05)

| Target | Clock used here | A4 word | E5 word |
| --- | --- | --- | --- |
| PAL | 985248.611111 Hz | 7492 / `$1D44` | 11226 / `$2BDA` |
| NTSC | 1022727.272857 Hz | 7218 / `$1C32` | 10815 / `$2A3F` |

These are locally calculated examples. Playing the PAL table at the NTSC clock raises pitch by approximately 64.63 cents. Changing a SID file's clock flag does not rewrite its note table.

## Separate pitch, player ticks, rows, and tempo

The SID oscillator runs continuously; the CPU periodically changes its registers. An IRQ player typically advances envelopes/effect tables on every call and advances tracker rows only when a separate speed counter expires.

```text
row_seconds = ticks_per_row / calls_per_second
BPM = 60 × calls_per_second / (ticks_per_row × rows_per_quarter)
```

At exactly 50 calls/s, six ticks per row and four rows per quarter give 125 BPM. Doubling the call rate requires twelve ticks per row to preserve that tempo. Nominal 50/60 Hz and actual raster frame rates differ: using 312×63 cycles gives approximately 50.1246 Hz for the PAL model above; 263×65 gives 59.8261 Hz for the corresponding NTSC model. Other video revisions require their own parameters. [S05](sources.md#s05)

For a score importer, quantize absolute event times or use a fractional accumulator. Rounding each duration independently accumulates drift. At 180 BPM, a sixteenth note is 83.333 ms: 4.1667 nominal PAL frames, not an exact integer. Higher call rates improve scheduling resolution but consume more CPU and do not add voices.

## Runtime integration

The CPU must expose I/O when writing SID registers. `$01` memory banking, the processor-port direction register, IRQ vector ownership, and KERNAL availability affect which player wrapper is valid. A KERNAL-dispatched IRQ through `$0314/$0315` is different from a bare hardware vector at `$FFFE/$FFFF`. Document memory load range, zero-page use, clobbered registers, stack assumptions, and IRQ acknowledgement. [S06](sources.md#s06)

MiniPlayer2's PRG example supplies a concrete raster-IRQ wrapper, SID initialization, and border profiling. Its return through the KERNAL is part of that example's environment, not a universal ending for custom IRQ code. [S07](sources.md#s07)

## Integration contract to record

- Machine model and SID model; number and addresses of chips.
- Load address, init entry, play entry, subtune argument, and expected call cadence.
- Memory and zero-page reservation; interaction with display and other interrupts.
- Whether the tune owns its interrupts or the host calls it.
- Worst-case execution time, measured under the intended display load.

These are proposed acceptance fields for this project. A simple sound-producing loop is not yet a reusable music driver.
