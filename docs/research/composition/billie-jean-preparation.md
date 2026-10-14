# Billie Jean: independent reconstruction and reusable programs

P2 is complete for the accepted reconstruction, authored ending and familiar transfer, following the accepted [Take On Me case](take-on-me-preparation.md#familiar-transfer-and-case-closure). This document owns source provenance, score/sound findings, the independent compiled reconstruction and scoped listening judgments for the pinned Johannes Bjerregaard SID. The [shared intake](pop-theme-preparation.md) retains STIL's source-song attribution to Michael Jackson's *Billie Jean*, from *Thriller*; the archive credits Johannes Bjerregaard, 1990, for this SID. Its [registered download](../../../config/local-assets.json) is the [HVSC archive](https://www.hvsc.de/download/C64Music/MUSICIANS/B/Bjerregaard_Johannes/Billie_Jean.sid), SHA-256 `16d8eae4d22f368520589c44e9db399b64092664bee6e1e70ca4b21c60bf0c54`. The original SID and audio remain local.

The intact single/default subtune 1 declares PAL, MOS6581 and VBI playback, with load `$1000`, exclusive end `$1EAD`, init `$14A0` and play `$1000`. The [banked callable host](../../validation/psid-audit.md#select-a-subtune-and-expose-ram-beneath-basic) supplies explicit selection, bank `$36` and validated call-return state. This is a controlled execution contract, not evidence of the original release's scheduling environment.

## Find the score reader

The [structured contract](../../../evidence/billie-jean-form/contract.json) and [executed hooks](../../../evidence/billie-jean-form/complete14274/hooks.json) preserve exact fields and PCs. Three order streams select patterns through split pointer tables `$1900/$1980`; patterns begin at `$1C00`. The driver processes physical voices 3, 2, 1 in that order.

| Consumed field | Executed location | Selected semantics |
| --- | --- | --- |
| Order byte | `$102C`; streams `$1600/$1700/$1800`, cursors `$1460+voice` | A non-`$FF` high-bit byte sets unsigned transpose `value & $7F`, advances the cursor and reads a pattern index at `$104D`. Other pattern selections retain transpose. |
| Order `$FF` | `$1032–$103D` | Reset **all three order cursors**, then reread the current voice's order within the same call. Sound/program state is retained; this does not call PSID init. |
| Row header | `$1060`; pattern cursor `$145D+voice` | Low five bits are duration. Class `$C0–$DF` consumes no instrument/glide/note payload and sets the software gate mask to `$FE`; continuing sound processing still runs. It is not a measured silence. |
| Optional setup | `$1099`, `$10AB/$10B1` | Header bit `$80` consumes an instrument argument, storing `(argument × 8) & $FF`. Bit `$40` consumes glide step and target before the ordinary note. |
| Ordinary note | `$10BB`; base note `$145A+voice` | Add retained transpose modulo 256; header bit `$20` supplies the gate-hold flag. This score proof does not calculate resulting pitch/modulation programs. |
| Following `$FF` | Rest peek `$1079`, ordinary peek `$10C9` | Reset this pattern cursor and increment this voice's order cursor; otherwise the cursor addresses the next header. |

The shared divider `$1479` reloads 2 after a negative decrement result. Only divider zero decrements each row counter `$144A+voice`; a negative result dispatches the next row. Thus duration *d* spans **3 × (d+1) play calls**, and initialization's zero counters produce the first row at call **2**. Init clears score cursors, counters, hold flags and transpose, but retains loaded base notes/instrument offsets; the contract names these separately.

The frozen source-format expander uses the low five bits of `row.header` as its runtime duration. Its legacy `row.duration` is descriptive: changing that field alone has no effect. A duration edit changes the header bits, as the private source-copy guard below does. The [portable score schema](#portable-score-and-automated-retained-proof-recheck) removes this duplicate editing field and rejects it explicitly.

## Complete score cycle and bounded recurrence

The [decoded score](../../../evidence/billie-jean-form/complete14274/score.json) has **16 selected patterns and 261 stored rows**. Each voice's order spans **2,368 row-divider steps**, or **7,104 play calls**, despite different pattern and row counts. The [summary](../../../evidence/billie-jean-form/summary.json) retains order selections, transposes and pattern spans.

| Physical voice | Pattern visits per traversal | Executed rows per traversal | First decoded note row |
| --- | --- | --- | --- |
| 1 | 28 | 503 | Call 2 |
| 2 | 70 | 550 | Call 194 |
| 3 | 42 | 498 | Call 962 |

One initialized [14,274-call proof](../../../evidence/billie-jean-form/complete14274/receipt.json) observes global order wraps at **7106 and 14210**, both first encountered by physical voice 3. The independent [numeric decoder/expander](../../../evidence/billie-jean-form/score.py) matches all **20,343 consumed fields, 3,110 completed rows and 14,274 named return states**. It computes order/row timing from numeric data without original-driver execution or timed-event replay; it does not compute SID stores. The source [ordered ledger](../../../evidence/billie-jean-form/complete14274/writes.json.gz) retains **278,617 init/play stores**, including three init stores. Its 64-call prefix matches all 1,271 earlier intake records. Every callable RTS is checked against the actual host return word and stack depth. The [CPU report](../../../evidence/billie-jean-form/complete14274/audit.json) measures init 203 cycles and maximum play 1,277 against a 19,656-cycle per-call budget.

Equal backing-RAM plus A/X/Y/SP/P/PC hashes at the two wrap returns establish that scoped CPU/RAM recurrence, with absolute cycle counts excluded. The initialized first and second 7,104-call SID streams nevertheless differ: both contain 138,653 stores, but their first differing value is `$D412=$20` versus `$F0`. The second and third 64-call openings match all 1,268 stores, including instruction-start cycles. The [return observations](../../../evidence/billie-jean-form/complete14274/returns.json.gz) and summary preserve these comparisons. No physical SID/CIA/VIC state, full-machine or acoustic recurrence follows from the hashes or score cycle.

The [selected VICE wrap proof](../../../evidence/billie-jean-form/vice-wrap/trace/study.json), with [projection](../../../evidence/billie-jean-form/vice-wrap/projection.json) and [provenance](../../../evidence/billie-jean-form/vice-wrap/provenance.json), independently matches **261 stores: three init and 258 play** across calls **7100–7112**. All preceding host calls execute; 7,113 entries have maximum cadence error eight cycles against nine allowed. Parsed checkpoints verify the controlled PAL host, not exact SID bus-write timestamps or original-game cadence.

## Edit guard and reproduction

The [private duration intervention](../../../evidence/billie-jean-form/edit128/receipt.json) changes the first pattern-1 header at `$1C08` from `$83` to `$82`, reducing duration from 3 to 2. Two 128-call source executions match the numeric score reads; the next physical-voice-1 note moves from call **14 to 11**, as the three-call divider predicts. [Complete cases](../../../evidence/billie-jean-form/edit128/cases.json.gz) retain reads and source stores. The original stays unchanged; this is a score-timing guard, not independently synthesized output or a modified full-form proof.

The following commands describe the historical fresh capture at commit `37081db`, whose four shared-tool hashes match the frozen probe pins. Use that historical source/tool version when reproducing the capture; the archived probe intentionally rejects changed shared helpers. For a current-checkout retained-evidence recheck, use the portable recipe below. Obtain the pinned asset, then copy the historical analysis tools into a fresh one-level directory below `build/` to preserve their repository-relative paths and local imports. Do not rewrite frozen fingerprints to make a newer toolset pass.

```sh
python3 scripts/setup-project.py --only references --include billie-jean
mkdir build/billie-jean-new
cp evidence/billie-jean-form/score.py evidence/billie-jean-form/probe.py evidence/billie-jean-form/check-edit.py evidence/billie-jean-form/vice-wrap.py build/billie-jean-new/
PYTHONPATH=.tools/test-deps python3 build/billie-jean-new/probe.py --calls 64 --output build/billie-jean-new/opening64
PYTHONPATH=.tools/test-deps python3 build/billie-jean-new/probe.py --calls 14274 --output build/billie-jean-new/complete14274
PYTHONPATH=.tools/test-deps python3 build/billie-jean-new/check-edit.py --output build/billie-jean-new/edit128
PYTHONPATH=.tools/test-deps python3 build/billie-jean-new/vice-wrap.py --output build/billie-jean-new/vice-wrap
```

To repeat only the VICE boundary check, pass `--ledger evidence/billie-jean-form/complete14274/writes.json.gz`; no CPU traversal is then rerun. Canonical analysis archives follow the [evidence workflow](../../workflows/build-cache.md). Source reads, rows, return hashes and stores are retained losslessly; original payloads, full RAM, whole instruction logs and raw monitor dumps are excluded. The sound, numeric player and compiled proofs below extend this retained form evidence under their separate execution contracts.

## Active delivery boundary

The editable independent title, authored finite ending and familiar-material transfer have passed their declared numeric, compiled CPU, callable VICE and rendered checks. All three [listening verdicts](#listening-verdicts-and-case-closure) are accepted for their submitted scope. Preserve these workfiles and evidence; continue with Airwolf under the [delivery workflow](../../workflows/decoded-song-workflow.md#deliver-one-musical-case).

Existing source/form and VICE-wrap evidence retain their stated scope; no new full-form source capture is needed solely to relocate or recheck unchanged score logic. The portable header remains the sole duration/flag owner, source addresses remain provenance and byte offsets derive from encoded rows. Model assistance was reviewed at the first representative auditions; the decision and next checkpoints are retained below.

## Portable score and automated retained-proof recheck

The [current score module](../../../scripts/studies/billie-jean/billie_jean_score.py) and [portable score](../../../evidence/billie-jean-score/score.json) use `billie-jean-score-v1`. Each row’s `header` owns duration, note/rest kind and optional instrument/glide/hold flags. Payload fields must exactly match those flags; redundant editable `duration` and `kind` fields reject rather than silently ignoring an edit. `set_duration(row, value)` updates only the low five bits. Byte offsets and row kinds are derived by encoding; `sourceAddress` fields label observations without influencing scheduling. Named initial state and the global reset behavior remain explicit. The unique module name avoids collisions with another study’s helpers when tests run together.

The [checker](../../../scripts/studies/billie-jean/check-score.py) verifies the local source fingerprint and canonical archive hashes, decodes the pinned source data without executing it, then independently re-expands the portable score. The [receipt](../../../evidence/billie-jean-score/receipt.json) matches all **20,343 reads, 3,110 completed rows and 14,274 return states**, both global wraps and both retained 128-call duration cases. Complete [computed reads](../../../evidence/billie-jean-score/reads.json.gz), [rows](../../../evidence/billie-jean-score/rows.json.gz) and [returns](../../../evidence/billie-jean-score/returns.json.gz) preserve the comparison. The additional row `command` field exposes the authoritative payload to sound integration; sound-owned gate/glide state is not copied back from a stale score snapshot.

```sh
python3 scripts/listening-package.py config/listening/billie-jean-score.json --output build/billie-jean-score-work
python3 scripts/studies/billie-jean/check-score.py --check evidence/billie-jean-score/score.json
python3 scripts/evidence.py verify --group billie-jean-score
```

The [two-stage recipe](../../../config/listening/billie-jean-score.json) combines [nine bounded guards](../../../evidence/billie-jean-score/guards.txt) with the retained proof. On 2026-10-14 its [executed recheck](../../../evidence/billie-jean-score/run-executed.json) took **2.51 seconds**, and the [unchanged cached repeat](../../../evidence/billie-jean-score/run-reused.json) took **0.05 seconds**. This is a fresh numeric data decode and retained-execution recheck, **not fresh CPU/VICE capture**, sound synthesis or listening acceptance. Historical traces and their tool pins remain untouched. Later proofs retain their separate sound, numeric integration and compiled execution scopes.

## Editable sound programs and full-cycle contextual proof

The [independent sound helpers](../../../scripts/studies/billie-jean/billie_jean_programs.py) compute named voice/filter transitions and ordered writes from an [editable parameter bank](../../../evidence/billie-jean-sound/description.json), without original routine execution or event replay. The [source probe](../../../scripts/studies/billie-jean/sound-probe.py) supplies observed routine inputs and compares both resulting state and ordered stores at each exit. Its [7,107-call receipt](../../../evidence/billie-jean-sound/receipt.json) covers the initialized first traversal through the global wrap: **49,749 boundaries**, all **14 instrument offsets**, **1,393 hard restarts**, **64 legato setups**, **2,015 vibrato bodies**, and both glide directions and clamps. There are 133 body inputs with a nonzero glide step; a paired pitch-table stage can take priority over glide processing. These counts describe executed coverage, not audible role attribution.

| Mechanism | Verified behavior and reuse constraint |
| --- | --- |
| Note restart versus legato | The software gate mask selects the path. A restart writes control zero, AD, SR and TEST/GATE `$09`, resets age/table cursor and initializes pulse/filter parameters, but retains cached pitch, waveform and PWM direction. It skips the ordinary writer until the next body. Legato refreshes pitch and vibrato seed while preserving ongoing motion. |
| Moving pulse | Each body adds or subtracts the editable step, masks to 12 bits, then changes direction at the high-byte threshold. The crossing value is retained. Restart duplicates the initial byte into both halves before the next body masks it. |
| Paired pitch/waveform program | `$7E` holds; `$7F` redirects to the instrument's loop cursor. Other entries set waveform and absolute or base-relative pitch before advancing. The helper rejects a loop that cannot reach a value or hold. |
| Delayed vibrato and glide | Hold permits the pitch-motion stage. The note high bit can bypass ordinary vibrato delay while frequency lookup masks it off. Downward glides and a clamped upward glide bypass that body's filter and late gate logic; preserving this branch is necessary for shared-filter write order. |
| Shared filter and output | Voices run in physical order 3, 2, 1. Eligible bodies update routing, and enabled filter records update mode and subtract cutoff step. The ordinary writer emits control, frequency low/high and pulse low/high in that order. Age advances after each voice; mode/master-volume output is last. |
| Cold versus retained state | The [captured post-init image](../../../evidence/billie-jean-sound/initialSound.json) is taken at init's actual return, `$14A5`. Init emits only three control-zero stores. Score-owned inputs and mutable sound state must remain distinct when integrating the scheduler; a stale score snapshot must not restore a sound-owned gate mask or completed glide. |

Four private source-copy interventions each execute 1,500 calls and compare another 10,500 boundaries. Every intervention changes output, and every store outside its declared ports remains exact. The original file remains unchanged; modified SIDs are not retained in the public evidence.

| Control | Source data edit | Declared changed ports |
| --- | --- | --- |
| PWM step | `$151C`: `$20` → `$10` | Three voices' pulse low/high |
| Vibrato step | `$154D`: `$27` → `$17`; retain seed/filter bits | Three voices' frequency low/high |
| Attack pitch | `$1A08`: `$D5` → `$D4` | Three voices' frequency low/high |
| Filter start/step | `$151E`: `$20` → `$21`; this byte owns both fields | Cutoff high `$D416` |

Retained [contexts](../../../evidence/billie-jean-sound/contexts.json.gz), [parameter reads](../../../evidence/billie-jean-sound/reads.json.gz), [ordered stores](../../../evidence/billie-jean-sound/writes.json.gz) and the matching control archives preserve the full observations. The [recipe](../../../config/listening/billie-jean-sound.json) runs nine pure guards and the full source proof; the separate short integration test is subsumed by that proof rather than executed twice. On 2026-10-14 the [fresh run](../../../evidence/billie-jean-sound/run-executed.json) took **85.76 seconds** and the [unchanged cached repeat](../../../evidence/billie-jean-sound/run-reused.json) took **0.11 seconds**. This is fresh callable CPU execution and contextual helper verification, not an independently scheduled player, compiled export, SID synthesis, bus-timing proof or listening verdict.

```sh
python3 scripts/listening-package.py config/listening/billie-jean-sound.json --output build/billie-jean-sound-work
python3 scripts/evidence.py verify --group billie-jean-sound
```

## Complete independent numeric player

The [numeric player](../../../scripts/studies/billie-jean/billie_jean_player.py) consumes the [portable composition](../../../evidence/billie-jean-player/composition.json): explicit PAL/MOS6581 target, header-owned score, editable sound parameters and complete named cold state. It contains no original executable or timed-register replay. Each call processes physical voices 3, 2, 1, choosing setup for a new ordinary row and the continuing body otherwise, advances each voice's age and emits global mode/volume last. Initialization computes only the source's three control-zero stores.

Score owns base note, remaining duration, hold and instrument offset. An ordinary row clears glide step, then applies any new glide step/target with retained transpose; a rest closes the software gate mask and still runs the body. Sound owns gate mask, glide completion and modulation state between rows. The cold image rejects duplicate score-owned fields and requires every named sound/filter field, preventing incidental default state from silently changing the opening. Source addresses remain nonexecuting annotations.

The [retained-evidence checker](../../../scripts/studies/billie-jean/check-player.py) verifies source and archive fingerprints, then recomputes **278,617 ordered init/play stores and 14,274 score returns**, matching the original two-traversal ledger exactly. It also matches all **49,749 named sound boundaries through call 7106**, both 128-call duration cases and four 1,500-call sound interventions. The latter change editable numeric parameters independently, match the private source-copy results and preserve every store outside their declared ports. The [receipt](../../../evidence/billie-jean-player/receipt.json), full [stores](../../../evidence/billie-jean-player/writes.json.gz), [return states](../../../evidence/billie-jean-player/returns.json.gz) and [contexts](../../../evidence/billie-jean-player/contexts.json.gz) retain these distinct comparisons. The checker executes no original CPU code or new VICE traversal.

```sh
python3 scripts/listening-package.py config/listening/billie-jean-player.json --output build/billie-jean-player-work
python3 scripts/evidence.py verify --group billie-jean-player
```

The [recipe](../../../config/listening/billie-jean-player.json) combines [ten focused state-ownership guards](../../../evidence/billie-jean-player/guards.txt) and the full retained proof. Its final [executed proof](../../../evidence/billie-jean-player/run-executed.json) on 2026-10-14 took **27.66 seconds** with unchanged guards reused; the [fully cached repeat](../../../evidence/billie-jean-player/run-reused.json) took **0.14 seconds**. This receipt establishes numeric integration alone. The [post-ending-extension recheck](../../../evidence/billie-jean-compiled/post-ending-numeric-recheck.json) reproduces the same complete baseline and intervention outputs with the extended player; compiled execution and listening retain separate evidence below.

## Compiled export and listening package

The [editable title](../../../songs/studies/billie-jean-reconstruction/README.md) preserves the initialized first traversal and adds an explicit finite ending. The [compiler](../../../scripts/studies/billie-jean/compose.py) lowers `billie-jean-composition-v1` into our [runtime scheduler](../../../songs/players/billie-jean.asm) and [generated sound routines](../../../scripts/studies/billie-jean/billie_jean_effects_asm.py). Order/pattern rows, instrument parameters, paired pitch/waveform banks, frequency words and named cold state remain numeric data consumed at runtime. Original driver instructions and captured-register replay are absent. The PSID2 and standalone PRG target one PAL MOS6581 at `$D400`, with one call per 19,656-cycle frame; the title retains native tuning and cold state. The [compiler workflow contract](../../workflows/decoded-song-workflow.md#billie-jean-runtime-score-and-sound-programs) defines the admitted scope.

The [complete compiled proof](../../../evidence/billie-jean-compiled/candidate/verification.json) checks **7,203 play calls, 7,204 named init/play states and all 138,703 ordered stores**, including executed writer sites. Maximum play cost is **1,703 of 19,656 cycles**. Poisoned reinitialization restores the complete mutable image and workspace, and decimal-mode caller guards preserve binary row arithmetic. The frozen [assembly](../../../evidence/billie-jean-compiled/candidate/player.asm.gz), [listing](../../../evidence/billie-jean-compiled/candidate/player.listing.gz), [state checkpoints](../../../evidence/billie-jean-compiled/candidate/state-checkpoints.json.gz) and [ordered stores](../../../evidence/billie-jean-compiled/candidate/writes.json.gz) retain the executable evidence. The [source-prefix comparison](../../../evidence/billie-jean-compiled/source-prefix.json) matches **138,696 stores**, including the three init stores and music calls **0–7105**; the seven authored ending stores are excluded from that source comparison.

The [full callable VICE proof](../../../evidence/billie-jean-compiled/vice/study.json) independently matches all 138,703 stores through call 7202, with maximum entry-cadence error **five cycles against nine allowed**. This runs the exported SID in a controlled PAL host. The separate actual PRG bootstrap check executes BASIC `SYS 2061`, poisoned init and **only the first two play calls**, matching 43 stores with modeled raster/CIA reads. It does not claim a full standalone PRG run or real VICE autostart. Neither execution check establishes original-host timing, exact SID bus timestamps or audible identity.

The [ending selection](../../../evidence/billie-jean-compiled/ending-boundary-review.json) places the cut before the source's global wrap at **7106**. The exported ending closes the last actually emitted hardware gates, freezes score and modulation for **32 calls**, then at **7138** zeros controls and master volume while retaining filter-mode bits `$30`. Calls 7139–7202 confirm 64 further calls without stores. The source already has all gates low after 7105, but the ending mechanism also handles a cut after a hard restart, whose hardware control differs from cached waveform state. This is an authored held release, with **no fade**; the original continues looping.

Both [145-second render checks](../../../evidence/billie-jean-compiled/audio.json) use 44.1-kHz mono PCM16 and find no clipping. The [ending measurements](../../../evidence/billie-jean-compiled/ending-measurements.json) record **zero AC RMS before mute** in the 142.202–142.402-second window, with DC −153, and zero final-second AC RMS with DC −157. Renderer register snapshots bracket the final volume transition at 142.414–142.432 seconds; they are not exact bus timestamps. These measurements support a settled decay before volume-zero, while naturalness and musical completeness remain listening judgments.

```sh
python3 scripts/studies/billie-jean/prepare-title.py --check
PYTHONPATH=.tools/test-deps python3 scripts/studies/billie-jean/compose.py songs/studies/billie-jean-reconstruction/composition.json --output build/billie-jean-compiled-new
python3 scripts/listening-package.py config/listening/billie-jean-full.json --output build/billie-jean-full-work
python3 scripts/publish-listening.py build/billie-jean-full-work/run.json --selection scripts/studies/billie-jean/title-audition.json --output build/billie-jean-listening
python3 scripts/evidence.py verify --group billie-jean-compiled
```

The [full recipe](../../../config/listening/billie-jean-full.json) includes preparation, bounded guards, complete compiled verification, source-prefix comparison, full callable VICE, both renders and audition windows. On 2026-10-14 its [executed run](../../../evidence/billie-jean-compiled/run-executed.json) took **64.820518 seconds**; the [unchanged cached run](../../../evidence/billie-jean-compiled/run-reused.json) took **0.53328125 seconds**. These are routine execution times, not engineering effort or time to musical acceptance. Standalone compiler and publication destinations must be fresh; the recipe supports validated cache reuse. Original SID/WAV assets and generated exports/audio remain in ignored local storage.

The [listening submission](../../../evidence/billie-jean-compiled/listening/submission.json) binds the files and hashes to this completed run. The [phrase comparison](../../../build/billie-jean-listening/phrase-reference-then-ours.ab.wav) presents original then reconstruction over 24–40 seconds; the [ending comparison](../../../build/billie-jean-listening/ending-reference-then-ours.ab.wav) presents the same order over 125–145 seconds. The [opening](../../../build/billie-jean-listening/opening-reference-then-ours.ab.wav) covers 0–12 seconds, and both full renders are available through the title README. The original restarts within the ending window; the authored exit and decay require their own judgment.

The [reusable tonal palette](instruments/billie-jean-decoded-programs.md) and [matched familiar-transfer recipe](../../../config/listening/billie-jean-elise-transfer.json) apply selected programs to the same 53-note Für Elise material as a plain reference, with explicit A440 retuning and three-call timing adaptation. Both transfer exports pass their complete numeric/CPU/VICE and rendered checks; the card owns those adaptation limits and its [separate listening submission](../../../evidence/billie-jean-elise/listening/submission.json). The [verdicts below](#listening-verdicts-and-case-closure) accept the reconstruction phrase, authored ending and familiar transfer.

The [first-audition model review](../../../evidence/billie-jean-compiled/model-review.json) records **no model call**: fine timbral/phrasing fidelity, balance and natural decay remain outside calibrated eligibility. CPU/VICE and PCM settle execution and signal health; human feedback settles these musical judgments. Reassess assistance after feedback or substantive revision and again before closure under the [standing rule](../audio-assessment.md#use-and-reassess-model-assistance). Existing models remain experimental supporting signals.

## Listening verdicts and case closure

On 2026-10-14 the listener reported **“I don't hear any difference”** for both the phrase and ending comparisons, and **“plays nice”** for the familiar transfer. The [title review](../../../songs/studies/billie-jean-reconstruction/listening-review.json) and [transfer review](../../../songs/studies/billie-jean-elise/listening-review.json) retain the exact answers, submission hashes and unchanged audio fingerprints. The title verdicts accept the submitted sound/phrasing and ending without a requested correction; they do not claim PCM identity or equal final content. The original loops, while the reconstruction deliberately stops after the initialized first traversal.

P2 is complete for that pinned C64 arrangement, its separately authored finite ending and selected tonal palette reused over the same 53-note Für Elise material. The [accepted instrument card](instruments/billie-jean-decoded-programs.md) owns the editable example and constraints: native pitch accents and articulation, explicit transfer retuning, three-call timing quantization and shared-filter setup ownership. This does not claim reproduction of the full Michael Jackson studio recording, universal instrument suitability, real-hardware equivalence or NTSC support for this study backend. Composition effort was not measured reliably; recipe execution timings remain separate from time to musical acceptance.

Feedback and closure model-assistance review: **no model call**. Fine fidelity, balance and natural endings remain outside calibrated eligibility; the listener identifies no remaining defect that a model probe would resolve. Together with the retained first-audition review, all required checkpoints are accounted for. Models remain experimental supporting signals. Reassess usefulness at Airwolf’s first representative audition, after feedback/revision and before closure; proceed to Airwolf, then Ghostbusters, under the existing delivery order.
