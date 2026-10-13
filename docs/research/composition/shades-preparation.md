# Shades: form, clock and evolving instruments

Study Chris Hülsbeck's filter-corrected **Shades**, default subtune 1, PAL MOS6581. The [reference intake](../composers/huelsbeck-tel.md#shades-reference-intake) owns archive URLs, hashes, attribution and the composer's filter-intent account. This study owns the executed form and instrument findings. The reference form and CIA dispatch are verified; independent reconstruction and transfer remain active work under the [study plan](../study-plan.md).

## Reuse the right evidence

| Task | Reusable route / retained evidence |
| --- | --- |
| Trace source calls with the real timer | [CIA tracer and host contract](../../validation/cia-tracing.md), [script](../../../scripts/trace-shades-vice.py) |
| Observe instructions and source state | Import `shades_oracle(data, calls, observer=...)` from the tracer; this callable oracle does not emulate the CIA |
| Check instruction costs | [CPU timing lookup and shared adapter](../../validation/cpu-timing.md) |
| Recover the full order, row and fade structure | [Executed form receipt](../../../build/shades-form-intake/form-receipt.json); source addresses below support decoding, not an editable runtime contract |
| Understand the opening's animation | [Pulse mechanism and listening verdict](#moving-pulse-through-release), [controlled comparison receipt](../../../build/shades-pwm-intervention/comparison.json) |

The complete [VICE trace](../../../build/shades-intake/vice-cia-corrected-full-final/trace.json.gz), [callable store ledger](../../../build/shades-intake/vice-cia-corrected-full-final/oracle.writes.json.gz), [consumed rows](../../../build/shades-form-intake/rows.json.gz) and [per-call score state](../../../build/shades-form-intake/call-state.json.gz) retain the detail behind the summaries. Keep these raw records; the tables below are navigation and interpretation, not lossless substitutes.

Historical Soundmonitor prose supplies useful parameter concepts, but the archived player uses combined 64-byte blocks and a different layout from the published editor. Do not import the manual's addresses or assume binary compatibility. Likewise, the original and corrected archive payloads differ beyond filter values; use a one-variable intervention when attributing an audible effect.

## Complete selected form and ending

The selected deliverable is the first traversal, source play calls **0–24,384 inclusive**, followed by an authored finite stop at call 24,385. The source itself continues playing, fades to zero, and loops. Preserve its fade before adding the stop; do not truncate at the order counter's wrap.

The [form receipt](../../../build/shades-form-intake/form-receipt.json) observes 48,770 explicit source calls, covering two traversals. It verifies consumed rows and state; it does not establish analogue oscillator/envelope recurrence. The [full CIA trace](../../../build/shades-intake/vice-cia-corrected-full-final/study.json.gz) separately executes all 24,385 selected calls with real timer interrupts and matches 296,907 ordered source stores, including 128 timer writes. Its [current-oracle revalidation](../../../build/shades-intake/vice-cia-corrected-full-final/current-oracle-revalidation.json) confirms the same writes and every source-call instruction duration after tightening the host's entry-state contract.

| Landmark | Source call / contract | Reason it matters |
| --- | --- | --- |
| Select initial slot 0 | 0 | One startup call precedes the first consumed row |
| Consume first row | 1 | Counter reload 2 gives three calls per row because the decrement precedes the next row |
| First voice 1 pitch | 385, slot 2 | Slots 0 and 1 precede the opening pulse phrase |
| First voice 2 / voice 3 pitches | 1,153 / 1,921 | Texture enters progressively |
| Short slots | 54 and 55, 32 rows each | All other slots have 64 rows; assuming a fixed size misplaces later sections |
| Select fade block | 22,849, slot 120 | Fade operates only on row updates |
| First volume reduction | 22,942, `$D418=$1E` | Fade reload 30 yields 31 row updates, or 93 calls, per step |
| Next-order index wraps | 24,193, beginning slot 127 | This starts the final slot; it is not the loop restart |
| Master volume first reaches zero | 24,244, `$D418=$10` | Low-pass mode remains set while the master-volume nibble is zero |
| Last row / final selected call | 24,382 / 24,384 | Retain modulation through the full last slot |
| Actual next slot 0 selection | 24,385, then 48,769 | Recurring traversal length is 24,384 calls |

The 128-slot form contains 8,128 rows. The playing flag remains set through the fade and restart; a zero-volume observation is not a native stop. The 330-second [reference window](../../../build/shades-reference-window/filter-corrected.wav) corroborates fade and restart under libsidplayfp, but renderer snapshots and VICE call checkpoints have different startup alignment.

## Source decoding lookup

These addresses apply only to the pinned corrected archive. Keep them at the import/evidence boundary; an independently authored player should consume named musical and instrument fields.

| Purpose | Source location / semantics |
| --- | --- |
| Order selection | `$5580`, identity slots 0–127; `$033F` is the next order index |
| Three track-pointer banks | `$5000`, `$5100`, `$5200` |
| Combined parameter-block pointers | `$5300`; 14 distinct blocks used by the full form |
| Per-voice transpose banks | `$5400`, `$5480`, `$5500` |
| Row index / countdown / reload | `$0340` / `$0341` / `$0342` |
| Pitch lookup | High bytes beginning `$7370`, low bytes beginning `$73CF`; preserve the actually consumed lookup values |
| Timer-high source | Combined block offset `$0E`, written by `STA $DC05` at `$7852` |
| Fade command | Combined block offset `$3F`; zero retains the active fade state, `$FF` cancels it |

| Raw row command | Executed meaning | Portable description |
| --- | --- | --- |
| `$00` | Clear GATE; modulation can continue through release | Rest/release |
| `$80` | Special hold branch | Hold |
| Other byte with bit 7 clear | Select pitch/target with transpose and perform note-on behavior | Note with gate on |
| Other byte with bit 7 set | Select pitch/target, then clear GATE | Note with gate off |

The last command is **not gate-preserving legato**. The inspected branches are `$74D6→$7537`, `$7597→$75D9` and `$7633→$7675`. The early form diagnostic calls it `pitch-without-retrigger`; interpret that historical label through this executed gate contract.

## Moving pulse through release

At call 385, slot 2 selects the opening block `$5600`. Voice 1 consumes `$13` from `$5940`, adds transpose 1 and selects frequency word `$0374`. The patch uses pulse control `$40/$41`, attack/decay `$09`, sustain/release `$0A`, and reset width `$0DFF`. A rest at call 388 clears GATE; pulse evolution continues during release. Voice 1's sustain/release write occurs inside the following voice's writer at `$76E6`, so a faithful ordered-write model must preserve that ordering.

| Opening pulse field | Value | Source evidence |
| --- | --- | --- |
| Reset width | `$0DFF` | `$5623/$5624` |
| Up / down counts | 16 / 16 calls | `$5629/$562C` |
| Step | `$10` = 16 | `$562F` |
| Arithmetic | 16-bit pulse accumulator | `$72F8–$733D`; retain intermediate writes, not just final 12-bit SID width |
| Turnaround | Final ascent and first descent can occur in one call | `$72C4` rechecks the updated counter; call 425 writes `$0EFF` then `$0EEF` |

The global pulse scheduler processes ascending stages before eligible descending stages. Replacing this with one mutually exclusive up/down branch shifts the turnaround and loses an observable intermediate write. Similarly, freezing modulation on a rest discards the evolving release heard in the reference.

This opening is not evidence of a voice-1-triggered filter contour. Block `$5600` has filter trigger mask `$04`, selecting voice 3; voice 1 fails the trigger test at `$7236`. Routing `$F4` selects voice 3 for filtering and the retained cutoff byte pair is `$7B/$00` (high/low). Keep trigger ownership separate from the global contour's per-call advancement.

### Causal experiment and listening result

The experiment changes exactly one source byte, `$562F`, from `$10` to `$00`, freezing this patch's pulse movement while retaining its reset width. The [patched diagnostic receipt](../../../build/shades-pwm-intervention/patch.json) records both hashes. The [corrected-cycle intervention](../../../build/shades-intake/opening-instrument-corrected-cycles/intervention-1280.json) compares 1,280 calls: 1,906 changed writes are confined to `$D402/$D403`; all non-pulse writes, instruction timestamps, timer writes and call durations remain identical. This is a reference-program intervention, not an independent reconstruction.

Listen to [original-then-static-pulse.wav](../../../build/shades-pwm-intervention/original-then-static-pulse.wav): the corrected reference's moving pulse comes first, then the frozen version, separated by half a second. Both use seconds 5–12 of renders started from initialization, PAL MOS6581, libsidplayfp 3.1.1/SIDLite, 44.1 kHz mono PCM16, unity gain and no individual normalization. The [comparison receipt](../../../build/shades-pwm-intervention/comparison.json) pins the files and settings.

On 2026-10-13 the listener said: **“original is little quieter and more vibrant”**. The measured window AC RMS is about 2,123 for moving pulse and 2,331 for frozen pulse, consistent with the reported level difference; both have peak 4,550. Retain moving pulse for this sound. The verdict supports this opening intervention only; it does not approve an independent player, the entire reconstruction or a transfer phrase.

The [reusable comparison tool](../../../scripts/compare-shades-pwm.py) performs the one-byte patch and ordered-write isolation proof, optionally rendering and assembling the audition. The [portable audio recipe](shades-reference-audio.json) retains exact source/output hashes, renderer settings, frame boundaries and commands; reference SIDs and WAVs remain out of Git. Reproduction in [the retained tool receipt](../../../build/shades-pwm-reusable-final/comparison.json) produced a byte-identical comparison WAV and frozen-pulse render. The new 16-second baseline's PCM also matches the original 330-second render's prefix exactly.

```sh
PYTHONPATH=.tools/test-deps python3 scripts/compare-shades-pwm.py .local/research/shades/Shades_filter_corrected.sid --output build/shades-pwm-new --render
```

Optionally pass `--baseline-reference build/shades-reference-window/filter-corrected.wav` to verify the regenerated baseline against that initialized reference's PCM prefix. The metadata recipe includes the command for recreating the 330-second reference when it is absent.

## Reconstruction boundary

The [editable score](../../../songs/shades-score.json) separates patterns, order, transpose, explicit gate semantics, row timing and fade commands. The [editable instrument description](../../../songs/shades-programs.json) supplies named voice/filter patches, the frequency lookup and named preloaded state. Source address annotations are provenance; neither description contains executable source-driver code or a captured playback ledger.

The [program module](../../../scripts/shades_programs.py) implements `Programs`/`State`, `load_block`, `consume_row`, `advance_portamento`, `advance_vibrato`, `advance_filter` and `advance_pulse`. The [independent scheduler](../../../scripts/shades_player.py) owns modulation-before-row order, fade-before-selection order, conditional voice writers, timer-high commands and the finite stop. Its `compute(score, programs, calls=None, include_stop=False)` API runs without the original SID. The [score importer](../../../scripts/describe-shades-score.py) is a separate pinned-source analysis path; `expand_score(description)` requires only editable JSON.

```sh
python3 scripts/shades_player.py songs/shades-score.json --programs songs/shades-programs.json --output build/shades-model-new
PYTHONPATH=.tools/test-deps python3 scripts/shades_player.py songs/shades-score.json --programs songs/shades-programs.json --reference .local/research/shades/Shades_filter_corrected.sid --output build/shades-model-checked-new
PYTHONPATH=.tools/test-deps python3 scripts/describe-shades-score.py .local/research/shades/Shades_filter_corrected.sid --output songs/shades-score.json --check --evidence-output build/shades-score-evidence-new
python3 scripts/shades_programs.py .local/research/shades/Shades_filter_corrected.sid --output build/shades-programs-new.json
```

Choose fresh output paths. The model CLI writes the complete computed store ledger and a verification receipt; adding `--reference` compares every source call before the four authored stop stores. Generated stores are analysis output, never the runtime sound program. The [full comparison receipt](../../../build/shades-semantic-verified/verification.json) verifies all 296,907 source SID/timer stores across 24,385 calls. The score importer can additionally retain consumed events, row/call snapshots, source mappings and ordered writes, with hashes rather than a prose-only summary; the [retained score-evidence receipt](../../../build/shades-score-verified/receipt.json) indexes those complete records.

### Behavior lookup for reuse

The [program guards](../../../tests/shades_programs_test.py) connect these rules to executed source transitions or focused source fixtures. The [full transition receipt](../../../build/shades-program-model/receipt.json) indexes a lossless named-state delta ledger with ordered source writes, covering every modulation stage and row across the selected span. The [scheduler guards](../../../tests/shades_player_test.py) exercise ordered writes, source-free annotations, a changed pulse parameter and the finite ending. These are behavioral contracts of the inspected driver, not general SID hardware rules.

| Mechanism / parameter | Retained behavior and constraint |
| --- | --- |
| Pulse width and counters | Use a 16-bit accumulator; all up stages precede eligible down stages, including the same-call turnaround. A down step larger than the current accumulator stalls without consuming its counter. |
| Rest and hold | Hold skips pitch/gate work. Rest clears GATE while effects continue; voice 2 emits its rest writer on every rest, while voices 1 and 3 suppress it when the previous row was already a rest. |
| Portamento enable | The low byte of the step enables the effect; a step such as `$0100` is inactive despite its nonzero high byte. |
| Downward target slide | Preserve the source's asymmetric byte comparison: with a `$0010` step, `$1020→$1000` snaps to target, while `$1008→$1000` subtracts to `$0FF8`. A conventional distance clamp would change the sound. |
| Up/down pitch movement | Movement sets bit 1 of vibrato delay; reaching the target through the snap branch clears it. Preserve byte-width arithmetic and wraparound. |
| Delayed vibrato | When delay expires, emit two subtractive pitch updates, then reset the phase before the ascending stage. Preserve both writes. |
| Fine tune | Voices 2 and 3 add their fine-tune byte to the frequency low byte without carrying into the high byte. Keep this distinct from a conventional 16-bit cents offset. |
| Global filter | One contour advances per call. The low-byte carry test uses a threshold of seven; descending high-byte subtraction is suppressed when it would underflow. Trigger mask chooses which voice can reset the contour. |
| Envelope write ordering | Voice 1's SR is emitted by voice 2's writer; do not silently regroup all seven registers per voice. |
| Fade | Advance before selecting the next row's block. An active fade suppresses normal voice-writer volume stores, including after it reaches zero. |

The complete finite export and an original transfer phrase still need compiled execution, rendering and listening evidence before this study can close. Ordered computed-store equality establishes the semantic model; it does not establish CPU cost, within-call bus timing, analogue identity or musical approval of an independent player.
