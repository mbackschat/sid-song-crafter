# Ghostbusters: static patches with shared-phase vibrato

These editable programs come from the [independent Ghostbusters music study](../ghostbusters-preparation.md#independent-score-and-sound-components). Complete numeric, compiled CPU and NTSC VICE music execution is verified; the familiar-material transfer has been accepted for instruments, balance and ending. The target is one NTSC MOS6581 at `$D400`, with one music call per 17,095 cycles. Opening sampled speech is a separate mechanism and is not part of this instrument bank.

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

Use the [numeric player](../../../../scripts/studies/ghostbusters/player.py) for editable experiments and the [compiler](../../../../scripts/studies/ghostbusters/compiler.py) for native music exports. The [numeric receipt](../../../../evidence/ghostbusters-player/receipt.json), [compiled proof](../../../../evidence/ghostbusters-compiler/compiled/verification.json) and [VICE comparison](../../../../evidence/ghostbusters-compiler/vice/study.json) establish the declared execution scope. They do not establish the quality of a new instrument assignment, tuning conversion or ending. The owning [study plan](../../study-plan.md#delivery-order-and-work-in-progress) keeps the complete speech/music audition separate from the accepted familiar-material transfer.

## Familiar-material transfer and listening verdict

The [editable example](../../../../songs/studies/ghostbusters-elise/README.md) retains all 53 notes from beats `[0,12)` of the preserved Für Elise score: 35 melody, six bass and twelve harmony events. Physical voices 1, 2 and 3 use native patches 2, 1 and 7 respectively. The generated plain reference uses triangle sounds and zero vibrato, sharing exactly the same score and NTSC A440 bank. The [preparation report](../../../../songs/studies/ghostbusters-elise/preparation.json) retains every original event, native note index, original and replacement frequency word, adaptation and quantization error.

Absolute boundaries round to the nearest four-call step. The maximum measured boundary error is 32.945 ms and duration error 59.108 ms; base-frequency quantization is within 0.464 cents. Both versions clear header `$20`: their first native gate-off is 66.860 ms after onset, and the release path clears AD/SR one step before each nominal note end. Consequently, preserving all 53 nominal pitches does not promise 53 identical envelope attacks or source-score sustain lengths. The shared-phase pitch modulation of native patch 2 remains enabled where its duration permits it.

The final source boundary is call 600, followed by a gate-low rest and padded rests. Both exports are verified through 720 calls; the first possible reset is call 864, beyond the twelve-second render and the declared audit range. No master-volume fade or extra stopping engine is added. The callable PSID is not promised to remain silent indefinitely outside that range. The [audio receipt](../../../../evidence/ghostbusters-elise/audio.json) reports no clipping and zero final-second AC RMS in both renders; a constant residual DC value is not an audible tail.

Seven [focused guards](../../../../tests/ghostbusters_transfer_test.py) include an independent comparison of the preserved score against actual emitted note indices, frequency words, order and timing, plus a deliberate consistent-transposition failure. Complete CPU and actual NTSC VICE checks cover both 720-call versions. The [reference](../../../../evidence/ghostbusters-elise/reference/verification.json) and [candidate](../../../../evidence/ghostbusters-elise/candidate/verification.json) proofs retain their different stores and cycle costs; neither establishes musical acceptance.

Listen to [plain-then-ghostbusters.ab.wav](../../../../build/ghostbusters-elise-listening/plain-then-ghostbusters.ab.wav), 24.5 seconds: twelve seconds of plain reference, a half-second gap, then the native palette. Separate files are [plain-reference.wav](../../../../build/ghostbusters-elise-listening/plain-reference.wav) and [ghostbusters-transfer.wav](../../../../build/ghostbusters-elise-listening/ghostbusters-transfer.wav). The [submission](../../../../evidence/ghostbusters-elise/listening/submission.json) binds the unchanged unity-gain pair to its execution evidence. On 2026-10-15 the listener confirmed “instruments, balance and ending work musically” and asked why the plain reference differs from previous ones. The [feedback record](../../../../songs/studies/ghostbusters-elise/listening-review.json) binds this acceptance to the submitted audio. Transfer revisions requested: none; active effort: not recorded.

First-audition model review: skip musical-quality inference for this transfer because the tested models are not validated for palette balance or native short-note articulation. A separate bounded Qwen speech-recognition trial is planned for the complete title's changed speech scheduling, as recorded in the [owning study](../ghostbusters-preparation.md#planned-bounded-speech-recognition-check). Reassess after feedback or a musical revision and before closure.

The plain reference is generated for this backend, not a fixed cross-study recording. Ghostbusters uses the preserved score’s triangle envelopes but its native scheduler releases GATE about 66.860 ms after each onset and later clears AD/SR. The [Airwolf reference](airwolf-static-tones.md#editable-transfer-and-timing) instead kept Airwolf’s native envelopes; the [Billie Jean preparer](../../../../scripts/studies/billie-jean/prepare-elise.py) used held/legato plain articulation. These are concrete envelope and note-shaping differences despite the same 53 nominal notes and A440 tuning. Native timing quantization also varies. This comparison establishes usefulness within the submitted pair, not an isolated timbre ranking across studies. Future submissions must name the case-specific reference and disclose articulation/envelope changes, following the [transfer workflow](../../../workflows/decoded-song-workflow.md#deliver-one-musical-case).

Post-feedback model review: no transfer inference is needed; generator settings explain the changed reference directly, and the listener has accepted the musical result. Fine articulation and palette balance remain outside calibrated model eligibility. The [case-closure review](../ghostbusters-preparation.md#listening-verdicts-and-case-closure) retains this decision; the separate speech-recognition trial does not assess this transfer. Reassess for new material or a substantive musical revision.
