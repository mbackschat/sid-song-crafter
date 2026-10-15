# Ghostbusters: static patches with shared-phase vibrato

These editable programs come from the [independent Ghostbusters music study](../ghostbusters-preparation.md#independent-score-and-sound-components). Complete numeric, compiled CPU and NTSC VICE music execution is verified; musical reuse has not yet received a listening verdict. The target is one NTSC MOS6581 at `$D400`, with one music call per 17,095 cycles. Opening sampled speech is a separate mechanism and is not part of this instrument bank.

## Select a patch by behavior

The [editable bank](../../../../evidence/ghostbusters-player/composition.json) and [pure sound helpers](../../../../scripts/studies/ghostbusters/programs.py) retain six patch fields. Hexadecimal values below are SID register bytes; pulse width combines the low byte with the low nibble of the high byte. Waveforms and widths stay fixed between onsets. There is no continuing PWM, filter program, oscillator sync or ring modulation in this music component.

| Patch | Waveform | Pulse width | AD | SR | Vibrato shift | Source use |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | Pulse | `$040` | `$2F` | `$FF` | 0 | Initialized patch; not an explicit score selection |
| 1 | Sawtooth | `$800` | `$28` | `$88` | 0 | Selected |
| 2 | Pulse | `$100` | `$2F` | `$FF` | 2 | Selected |
| 3 | Noise | `$800` | `$14` | `$00` | 0 | Selected |
| 4 | Pulse | `$800` | `$2F` | `$FF` | 0 | Present in the bank; not selected in the verified traversal |
| 5 | Sawtooth | `$800` | `$26` | `$8F` | 0 | Selected |
| 6 | Sawtooth | `$800` | `$22` | `$AA` | 0 | Selected |
| 7 | Pulse | `$800` | `$02` | `$26` | 0 | Selected |
| 8 | Sawtooth | `$800` | `$88` | `$88` | 3 | Selected |

Pulse width is still written for sawtooth and noise patches, but does not make those waveforms pulse-width-modulated. Patch identity alone does not determine articulation: the score header, duration countdown, shared phase and preceding gate state also matter. Candidate musical roles must be checked in context rather than inferred from register values.

## Preserve articulation and modulation

Onset writes frequency high then low, control, pulse low/high and AD/SR. It does not first clear control to force a new attack. A new pitched row therefore need not retrigger the envelope when the previous gate remains high. A rest leaves frequency untouched and masks GATE in the hardware write, while retaining the unmasked control in the software cache.

The score advances on every fourth call. On continuing quarter steps, a header without `$20` releases GATE. On that release path, remaining zero additionally clears AD/SR; header `$20` suppresses both GATE release and these envelope clears. Treat these as native articulation rules, not an assurance that an arbitrary imported note sustains until its nominal score end. Evaluate attack, body, release and next retrigger using the [short-note guidance](../sound-design-repertoire.md#shape-short-note-endings-in-context).

For the used vibrato shifts 2 and 3, displacement is the unsigned adjacent-note frequency difference divided by `2^(shift+1)`, multiplied by the shared phase sequence `[0,1,2,3,3,2,1,0]`. Displacement is enabled only when the original header's low-five-bit duration is at least 5. This is a one-sided pitch excursion above the base word, not centered vibrato, and its phase continues across notes. Continuing pitch writes low then high, reversing the onset order. Supply the adjacent frequency entry even where a short header suppresses displacement: the helper still performs that lookup.

Shared volume belongs to the score action order, not an individual instrument. Voices execute in descending order. A volume nibble of `$F` computes `min(15, (109 - voice0OrderCursor) & 255)` from the cursor saved when that action occurs; other nibbles set their literal level. Reading the final scheduler state instead would change simultaneous events around order transitions. Global reset preserves instrument, note, header and cached-control state; restart is not a cold reinitialization.

## Reuse and evidence

Use the [numeric player](../../../../scripts/studies/ghostbusters/player.py) for editable experiments and the [compiler](../../../../scripts/studies/ghostbusters/compiler.py) for native music exports. The [numeric receipt](../../../../evidence/ghostbusters-player/receipt.json), [compiled proof](../../../../evidence/ghostbusters-compiler/compiled/verification.json) and [VICE comparison](../../../../evidence/ghostbusters-compiler/vice/study.json) establish the declared execution scope. They do not establish the quality of a new instrument assignment, tuning conversion or ending. The owning [study plan](../../study-plan.md#delivery-order-and-work-in-progress) keeps the familiar-material transfer and complete speech/music audition open until listening review.
