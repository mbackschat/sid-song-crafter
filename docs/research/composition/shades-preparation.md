# Shades: form, clock and evolving instruments

Study Chris Hülsbeck's filter-corrected **Shades**, default subtune 1, PAL MOS6581. The [reference intake](../composers/huelsbeck-tel.md#shades-reference-intake) owns archive URLs, hashes, attribution and the composer's filter-intent account. This study owns the executed form and instrument findings. The reference form, independent reconstruction and original transfer have CPU, CIA-dispatch and rendered-audio evidence. The independent reconstruction and fade are listening-approved; the invented transfer instruments were accepted but its ending rejected; the replacement familiar Für Elise transfer and ending are accepted under the [study plan](../study-plan.md).

## Reuse the right evidence

| Task | Reusable route / retained evidence |
| --- | --- |
| Trace source calls with the real timer | [CIA tracer and host contract](../../validation/cia-tracing.md), [script](../../../scripts/trace-shades-vice.py) |
| Observe instructions and source state | Import `shades_oracle(data, calls, observer=...)` from the tracer; this callable oracle does not emulate the CIA |
| Check instruction costs | [CPU timing lookup and shared adapter](../../validation/cpu-timing.md) |
| Recover the full order, row and fade structure | [Executed form receipt](../../../evidence/shades-form-intake/form-receipt.json); source addresses below support decoding, not an editable runtime contract |
| Understand the opening's animation | [Pulse mechanism and listening verdict](#moving-pulse-through-release), [controlled comparison receipt](../../../build/shades-pwm-intervention/comparison.json) |

The complete [VICE trace](../../../evidence/shades-intake/vice-cia-corrected-full-final/trace.json.gz), [callable store ledger](../../../evidence/shades-intake/vice-cia-corrected-full-final/oracle.writes.json.gz), [consumed rows](../../../evidence/shades-form-intake/rows.json.gz) and [per-call score state](../../../evidence/shades-form-intake/call-state.json.gz) retain the detail behind the summaries. Keep these raw records; the tables below are navigation and interpretation, not lossless substitutes.

Historical Soundmonitor prose supplies useful parameter concepts, but the archived player uses combined 64-byte blocks and a different layout from the published editor. Do not import the manual's addresses or assume binary compatibility. Likewise, the original and corrected archive payloads differ beyond filter values; use a one-variable intervention when attributing an audible effect.

## Complete selected form and ending

The selected deliverable is the first traversal, source play calls **0–24,384 inclusive**, followed by an authored finite stop at call 24,385. The source itself continues playing, fades to zero, and loops. Preserve its fade before adding the stop; do not truncate at the order counter's wrap.

The [form receipt](../../../evidence/shades-form-intake/form-receipt.json) observes 48,770 explicit source calls, covering two traversals. It verifies consumed rows and state; it does not establish analogue oscillator/envelope recurrence. The [full CIA trace](../../../evidence/shades-intake/vice-cia-corrected-full-final/study.json.gz) separately executes all 24,385 selected calls with real timer interrupts and matches 296,907 ordered source stores, including 128 timer writes. Its [current-oracle revalidation](../../../evidence/shades-intake/vice-cia-corrected-full-final/current-oracle-revalidation.json) confirms the same writes and every source-call instruction duration after tightening the host's entry-state contract.

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

The experiment changes exactly one source byte, `$562F`, from `$10` to `$00`, freezing this patch's pulse movement while retaining its reset width. The [patched diagnostic receipt](../../../build/shades-pwm-intervention/patch.json) records both hashes. The [corrected-cycle intervention](../../../evidence/shades-intake/opening-instrument-corrected-cycles/intervention-1280.json) compares 1,280 calls: 1,906 changed writes are confined to `$D402/$D403`; all non-pulse writes, instruction timestamps, timer writes and call durations remain identical. This is a reference-program intervention, not an independent reconstruction.

Listen to [original-then-static-pulse.wav](../../../build/shades-pwm-intervention/original-then-static-pulse.wav): the corrected reference's moving pulse comes first, then the frozen version, separated by half a second. Both use seconds 5–12 of renders started from initialization, PAL MOS6581, libsidplayfp 3.1.1/SIDLite, 44.1 kHz mono PCM16, unity gain and no individual normalization. The [comparison receipt](../../../build/shades-pwm-intervention/comparison.json) pins the files and settings.

On 2026-10-13 the listener said: **“original is little quieter and more vibrant”**. The measured window AC RMS is about 2,123 for moving pulse and 2,331 for frozen pulse, consistent with the reported level difference; both have peak 4,550. Retain moving pulse for this sound. The verdict supports this opening intervention only; it does not approve an independent player, the entire reconstruction or a transfer phrase.

The [reusable comparison tool](../../../scripts/compare-shades-pwm.py) performs the one-byte patch and ordered-write isolation proof, optionally rendering and assembling the audition. The [portable audio recipe](shades-reference-audio.json) retains exact source/output hashes, renderer settings, frame boundaries and commands; reference SIDs and WAVs remain out of Git. Reproduction in [the retained tool receipt](../../../evidence/shades-pwm-reusable-final/comparison.json) produced a byte-identical comparison WAV and frozen-pulse render. The new 16-second baseline's PCM also matches the original 330-second render's prefix exactly.

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

Choose fresh output paths. The model CLI writes the complete computed store ledger and a verification receipt; adding `--reference` compares every source call before the four authored stop stores. Generated stores are analysis output, never the runtime sound program. The [full comparison receipt](../../../evidence/shades-semantic-verified/verification.json) verifies all 296,907 source SID/timer stores across 24,385 calls. The score importer can additionally retain consumed events, row/call snapshots, source mappings and ordered writes, with hashes rather than a prose-only summary; the [retained score-evidence receipt](../../../evidence/shades-score-verified/receipt.json) indexes those complete records.

### Behavior lookup for reuse

The [program guards](../../../tests/shades_programs_test.py) connect these rules to executed source transitions or focused source fixtures. The [full transition receipt](../../../evidence/shades-program-model/receipt.json) indexes a lossless named-state delta ledger with ordered source writes, covering every modulation stage and row across the selected span. The [scheduler guards](../../../tests/shades_player_test.py) exercise ordered writes, source-free annotations, a changed pulse parameter and the finite ending. These are behavioral contracts of the inspected driver, not general SID hardware rules.

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

## Independent export and original transfer

The [compiler](../../../scripts/compose-shades.py) assembles our [scheduler](../../../songs/players/shades.asm) and [effect routines](../../../songs/players/shades-effects.asm) from editable score/program JSON. It includes no original driver and no register replay. The full payload occupies 8,282 bytes, including 98 bytes of named mutable state, 3,520 pattern tokens, 128 orders and 14 selected blocks. Source annotations do not affect generated bytes. Reinitialization restores the complete state image, and calls after the finite stop remain silent. The [compiler guards](../../../tests/shades_compiler_test.py) include edited programs, pitches, durations, placement and state boundaries; the [CIA candidate audit](../../validation/cia-tracing.md) enforces this backend's hardware contract.

The [compiled comparison receipt](../../../evidence/shades-independent-full/reference-comparison.json) matches all 296,907 original stores by phase, call, address, value and order, followed by four authored stop stores. Candidate instruction-start offsets relative to the original range from −195 to +1,260 cycles. Equal ordered stores therefore do not establish exact bus timing, oscillator phase or PCM identity.

| Export | Calls / stores | Maximum play cost | Independent CIA proof |
| --- | --- | --- | --- |
| [Complete first traversal](../../../evidence/shades-independent-full/build.json) | 24,386 / 296,911 | 3,607 cycles; init 1,667 | [Full VICE receipt](../../../evidence/shades-independent-full/vice/study.json.gz): all stores and call costs match; interval error ≤4 cycles, accumulated phase ≤2 |
| [Original transfer](../../../evidence/shades-transfer/build.json) | 1,522 / 10,734 | 3,138 cycles; init 1,643 | [Transfer VICE receipt](../../../evidence/shades-transfer/vice/study.json.gz): all stores and call costs match; interval error ≤4 cycles, accumulated phase ≤3 |

Both use the shortest timer period of 12,326 cycles and pass the conservative 12,165-cycle play budget. Complete VICE traces and callable ledgers are retained losslessly alongside the receipts in [the archive](../../../evidence/README.md). The full reconstruction preserves the source fade and adds silence at call 24,385; it does not include the next loop.

The [instrument card](instruments/shades-decoded-programs.md) explains the original eight-bar C-major transfer, cold initialization, pulse motion, shared-filter ownership and voice-3 pitch glide. Its [parameter-isolation receipt](../../../evidence/shades-transfer-model-01/parameter-isolation.json) changes only the glide step from 96 to zero: differences remain confined to voice-3 pitch stores. This is an execution experiment; the two musical halves use different notes and are not an isolated listening A/B.

### Reproduce and review listening

Follow [the compiler workflow](../../workflows/decoded-song-workflow.md) and [portable audio recipe](shades-independent-audio.json) for fresh-output commands, input/output hashes and renderer settings. All reference and comparison audio remains local and excluded from Git/LFS.

- [Reference then reconstruction](../../../build/shades-independent-full/listening/reference-then-ours.ab.wav): seconds 24–36 from each initialized render, a half-second gap, unity gain. This passage includes all three voices; A is the corrected reference, B our independent player.
- [Full matching reference](../../../build/shades-reference-window/filter-corrected.wav): 330 seconds of the filter-corrected archive, including the next loop; this is the reference used for the comparison. The [original archive variant](../../../build/shades-reference-window/original.wav) is also available locally for comparison.
- [Complete reconstruction](../../../build/shades-independent-full/reconstructed.wav): 310 seconds, including the source fade and finite ending.
- [Original transfer phrase](../../../build/shades-transfer/reconstructed.wav): 22 seconds, including its release/fade.

The [full audio receipt](../../../evidence/shades-independent-full/audio-evidence.json) and [transfer audio receipt](../../../evidence/shades-transfer/audio-evidence.json) record PAL MOS6581, libsidplayfp 3.1.1/SIDLite, default subtune 1, mono PCM16 at 44.1 kHz and no normalization. Neither render clips. The final half-second has zero AC RMS in both, with a constant renderer DC offset; this establishes a settled tail, not subjective ending quality.

**Reconstruction listening approved on 2026-10-13:** the listener answered “yes to first” when asked whether the reference-first comparison preserves sound and phrasing. After initially describing the full ending as “it seems so” and requesting the original, the listener clarified: “it sounds ok, it fades out nice, if that what's your expectation.” The intended ending preserves the source fade and stops before its next loop; this accepts that declared reconstruction and ending. It does not establish PCM identity or approve the separate transfer phrase; the later feedback below accepts its instruments but rejects its ending.

**Transfer feedback on 2026-10-13:** the listener reports “the last 2-4 s sound odd like wrong musical notes. The instruments are ok, though” and explains that an invented fragment makes judgment difficult. Retain this as instrument acceptance with an unsuccessful ending, not approval of the whole phrase. The replacement comparison uses familiar, preserved Für Elise material to separate sound reuse from composition quality; the [instrument card](instruments/shades-decoded-programs.md#reuse-outcome) owns the reuse outcome.

**Replacement transfer accepted on 2026-10-13:** the listener answers “Works musically, including the ending” for the matched plain-reference/Shades Für Elise phrase. The [familiar-transfer card](instruments/shades-decoded-programs.md#familiar-transfer-accepted) owns its source mapping, executable adapter, 53-event guards, full compiled/CIA verification, listening files and [reproduction recipe](shades-elise-audio.json). This closes the Shades study's transfer stage without approving the rejected invented ending or every possible glide application.
