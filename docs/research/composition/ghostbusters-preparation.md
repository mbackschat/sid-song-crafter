# Ghostbusters: NTSC machine-controlled title

Ghostbusters is the active T2 case after [Airwolf closure](airwolf-preparation.md#listening-verdicts-and-case-closure). The intended deliverable is an editable independent reconstruction with source-faithful continuation and a familiar-material instrument transfer. The [shared intake](pop-theme-preparation.md#ghostbusters) owns historical header admission; this study will own executed form, sound mechanisms and delivery. Successful rendering alone does not establish reconstruction or musical acceptance.

## Source and selected scope

The registered [HVSC source](https://www.hvsc.de/download/C64Music/MUSICIANS/L/Lieblich_Russell/Ghostbusters.sid) has SHA-256 `f7f05616972d7fd5ad31df91284edbf4e0917d39422f8d004d50b40501a0dcde` and stays at ignored `.local/research/ghostbusters/Ghostbusters.sid`. The original song is Ray Parker, Jr.'s *Ghostbusters*; the selected C64 arrangement is credited to Russell Lieblich, 1984 Activision. Cached STIL credits all speech separately to Electronic Speech Systems. Do not treat that attribution as evidence that speech is active in a particular passage.

The [pinned header](../../../evidence/pop-theme-intake/ghostbusters.header.json) declares RSID v2, one NTSC MOS6581, flags `$0018`, five subtunes and default/selected **#1**. The payload occupies `$900D–$A834`, init is `$900D`, and the play address is zero. The reserved zero speed word does not declare VBI playback. Preserve the source header and use a machine-controlled route; the existing callable PAL audit correctly rejects this input.

## First execution question

Identify the selected title's actual initialization, interrupt/foreground scheduling and SID/speech writers before implementing its score or effects. The evidence must distinguish declared NTSC from measured cadence, renderer snapshots from ordered writes, and oscillator instruments from any volume-path or other sampled sound. Reuse the [Giana machine-init precedent](huelsbeck-contrast.md#machine-initialization-contract) and [Arkanoid foreground/IRQ analysis](galway-contrast.md), but derive Ghostbusters' own entry contract rather than importing their PAL timing or addresses.

The [bounded source spec](../../../config/reference-intake/ghostbusters-title.json) selects #1 explicitly and requests 32 seconds, with source-only windows at 0–12 and 16–28 seconds. These are preparation excerpts, not a complete-form claim or a reference-versus-reconstruction comparison.

```sh
python3 scripts/setup-project.py --check --only references --include ghostbusters
python3 scripts/reference-intake.py run config/reference-intake/ghostbusters-title.json --output build/reference-intake/ghostbusters-title
```

Reference audio remains outside Git and LFS. Retain source fingerprints, numeric traces, measured bounds and reproducible commands. Use the [recipe runner](../../workflows/listening-package.md) for routine preparation rather than repeated manual render/copy calls. Preserve any loop restart throughout fidelity comparison windows under the [ending coverage rule](../../workflows/audio-comparisons.md#package-a-listening-review).

Apply the [Turbo sample-evidence boundary](tel-contrast.md#source-credits-and-execution-route) to speech as well: lossless sample fetches, ordered amplitude streams and monitor logs that contain them stay local. Public evidence retains aggregate verification results, fingerprints and reproduction commands. A JSON or compressed trace can encode original audio just as a WAV can; its container does not change that boundary.

## Bounded initialized render

The [executed intake](../../../evidence/ghostbusters-intake/run.json) completed all five stages on 2026-10-14 in **1.299 seconds**. The [source receipt](../../../evidence/ghostbusters-intake/source.json) records explicit subtune 1, forced NTSC matching the header, MOS6581, power-on delay zero, 44.1 kHz mono PCM16 and unity gain. The 32-second capture contains 1,411,200 frames, peak 10,822, AC RMS 2052.641 and zero rail samples; WAV SHA-256 is `0db7f82e1dfc7758fea9fa23d0d836f166442dd8326c27e56b3afcba78a2df38`.

The [local listening index](../../../build/reference-intake/ghostbusters-title/listening.md) links the full original capture and the two labelled source-only excerpts. [Renderer snapshots](../../../evidence/ghostbusters-intake/registers.tsv.gz) are numeric observations after rendering batches. They cannot recover intervening speech writes, identify writers, prove update cadence or establish a complete score cycle. This renderer stage uses its own machine emulation; the separate initialized VICE capture below supplies ordered checkpoint evidence.

The reusable [intake workflow](../../workflows/reference-intake.md#specification-contract) now admits explicitly declared NTSC only on `full-machine-render`; callable `pal-banked` remains PAL-only. Fifteen focused tests pass, including NTSC subtune/clock propagation, source preservation, absence of callable audit claims and rejection of unknown/mixed declarations. This is source-preparation support, not a new NTSC composition backend.

## Initialized machine entry contract

Read-only inspection of the pinned source identified these entry paths; the bounded capture below now verifies their execution and writer ownership, without proving the speech decoding arithmetic. Default init at `$900D` relocates code into RAM beneath KERNAL, invokes and waits for speech commands 1 and 3, then installs IRQ `$90D2` and returns at `$9096`. The music body at `$93F0` is relocated from source `$A04E`. Rotating NMI handlers around `$F083–$F0E9` write `$D418`; their dispatcher configures CIA2 Timer B with latch `$0065`, control `$91` and interrupt mask `$82`. The capture verifies volume-writing speech during initialization. Full speech decoding and audible identities of individual commands remain separate questions.

The [source-pinned probe](../../../scripts/studies/ghostbusters/probe-machine.py) starts **before init**, preserving the opening speech path. It reuses the Giana/Turbo file-monitor approach with NTSC/MOS6581 and explicit CIA models/KERNAL context. A real host `JSR $900D` at `$0400` returns to idle `$0403`, with `A=0` selecting subtune 1. Capture continues through 128 completed `$93F0` body calls and stops before the next. Count body entries rather than every `$90D2` IRQ entry, since the latter also dispatches ordinary KERNAL CIA interrupts.

The private trace retains ordered SID stores, CPU-port changes, VIC/CIA accesses, IRQ/NMI vectors, instruction checkpoint times and raster positions. Guards check `$02A6=0`, the actual VIC comparator and 263×65 NTSC geometry. Init writes `$D012=1` without clearing the high raster bit in `$D011`; the comparator is therefore 257, not 1. The existing callable PAL audit and PAL probe parsers are unchanged.

The pinned libsidplayfp 3.1.1 `src/psiddrv.a65` selects CIA1 Timer A latch **`$4295` for NTSC**, rather than the PAL `$4025`, and retains `$D011=$9B`, `$D012=$37` for matching-clock RSID initialization. `src/psiddrv.cpp` sets `$02A6=0`. Together with the source's later low-byte write, this predicts raster **257**, not line 1; the initial comparator 311 lies outside the selected 263-line NTSC frame. The actual monitor snapshots confirm comparator 311 before init and 257 at idle and the terminal boundary. KERNAL-READY startup does not reproduce all renderer power-on RAM and interrupt state, so matching these entries must not be described as whole-machine or PCM identity.

## Executed opening census and reproduction

The [128-body verification](../../../evidence/ghostbusters-machine/verification.json) covers **6.668944 seconds from init**, with init returning after 4.528522 seconds. It observes **30,225 SID stores and zero non-dummy SID reads** across physical `$D400–$D7FF`. Both opening speech commands execute before music initialization: command 1 has 15,151 NMI entries and 12,346 volume writes; command 3 has 25,899 NMI entries and 17,770 volume writes. Every observed speech volume write is paired with its expected NMI handler. Both commands execute the checked CIA2 Timer B start/stop sequence. This verifies scheduling and writer ownership, not the encoded speech decoder or bus-cycle accuracy.

The 128 completed music bodies have **17,095-cycle raster-normalized intervals** throughout. Their instruction-entry intervals vary from 17,044 to 17,281 cycles because entry latency varies. Body entry occurs on raster lines 5–8, **774–960 cycles after the line-257 comparator**, crossing the frame boundary. The source wrapper swaps 32 working bytes before calling music; that work alone requires 724 cycles including its two calls. Normalize latency modulo the NTSC frame instead of treating the wrapped raster line as a timing failure. Music body execution takes 175–1,036 checkpoint cycles in this passage. No unexecuted terminal body is included in the retained capture.

CPU banking is verified separately for source and host: init uses `$35` while speech runs, idle restores `$37`, music uses `$36`, and KERNAL CIA dispatch also writes `$37`. All 41,050 observed NMI entries occur during init; the subsequent music window has one score-owned `$D418` write and no speech NMI. That bounded separation does not yet prove the whole title never retriggers speech.

```sh
python3 scripts/listening-package.py config/listening/ghostbusters-machine.json --output build/ghostbusters-machine-verification
python3 scripts/evidence.py verify --group ghostbusters-machine
```

The [recipe](../../../config/listening/ghostbusters-machine.json) runs 14 focused guards and the real initialized capture. The [fresh run](../../../evidence/ghostbusters-machine/run-executed.json) took **8.932 seconds** on 2026-10-15; the [unchanged recheck](../../../evidence/ghostbusters-machine/run-reused.json) took **0.237 seconds**, reusing both stages without subprocesses. These measure workflow execution, not playback duration. A fresh output directory requests fresh execution. The receipt hashes the private compressed trace/logs and source payload; only the safe summary, commands and run receipts are public.

## Reconstruction map and next proof

Static source inspection maps music code `$A040–$A1F3` to runtime `$93E2–$9595`. Music init resets the three order cursors, pattern cursors and remaining-duration counters; the body processes voices **2→0**. Preserve the wrapper's context exchange and `$E2` increment when testing the body independently: reading idle zero page would inspect the swapped-out host context. The next executed boundary is `$90E3` through `$90F5`, with the active state retained before it is exchanged back.

| Runtime state / source data | Static interpretation to verify through execution |
| --- | --- |
| `$82`, `$85`, `$88` (three bytes each) | Per-voice order cursor, pattern cursor, remaining duration |
| `$8B`, `$8E`, `$91`, `$94` (three bytes each) | Note, row header, cached control, instrument |
| `$E2` | Shared phase; score work runs when its low two bits are zero |
| `$A2B7/$A2BA` | Three order-stream pointer tables; streams start at `$A2BD`, `$A32B`, `$A399` |
| `$A75B` | Pattern-pointer table |
| `$A1F4` | 96-word frequency bank |
| `$A7EF` | Eight-byte patch records; nine records, with six used bytes in the final record |

The recovered row grammar uses header low five bits for duration, `$20` for retained gate, `$40` for rest and `$80` for an extra packed volume/instrument parameter. Note rows consume header, note and optional parameter; rests consume only their header. Pattern `$FF` advances the order; order `$FF` reaches the global reset at `$942E` (source `$A08C`). Static expansion predicts 109 order entries per voice, 65 selected patterns and 2,391 semantic rows, with each voice spanning 3,488 duration-plus-one units. This predicts the first terminal at **zero-based body index 13,952 (the 13,953rd invocation)**, followed by the next first row at index 13,956. Reset retains note/header/control/instrument caches and phase, so it does not prove whole-state recurrence. These counts are **not yet an executed full-form proof**; compare them against source execution before selecting the complete reconstruction window or its ending.

### Static sound and speech interfaces

Patch records at `$A7EF` contain pulse low/high, control, AD, SR and vibrato shift, followed by two unused fields. Explicit score selections use records 1, 2, 3, 5, 6, 7 and 8; initialized record zero also matters. Controls select pulse `$41`, saw `$21` or noise `$81`; no continuing PWM, filter or sync/ring path was found in this music body. These are recovered code semantics, awaiting an independent numeric model and executed parameter controls before reuse.

Onsets write frequency **high then low**, then control, pulse low/high and AD/SR. Rests retain pitch and write patch setup with GATE masked low. Continuing quarter-step bodies clear GATE unless header `$20` retains it; remaining duration zero additionally clears AD/SR. Vibrato instead writes frequency **low then high**, using phase `[0,1,2,3,3,2,1,0]` and the adjacent-note difference divided by `2^(shift+1)`; displacement requires original duration at least 5. Instruments 2 and 8 use shifts 2 and 3. Preserve both write orders when verifying independent output.

Packed volume commands write at `$9486` (source `$A0E4`). Nibble `$F` computes a fade from the **voice-zero order cursor**, `min(15,109−cursor)` over the selected range. Descending voice processing therefore affects simultaneous volume commands. Combined with global reset, this predicts a fading loop rather than a finite stop; execution and listening must settle its complete ending behavior.

The speech relocation is source `$9124–$A03F` to runtime `$F080–$FF9B`. Default init invokes commands 1 and 3 through `$9097` → `$F080` before installing the music IRQ; nondefault subtunes take the speech-only branch. Dispatcher `$F42E` (source `$94D2`) supports `$FF` busy query, `$FE` timer stop and `$FD` dictionary-base assignment through X/Y. The dictionary at `$F4EA` (source `$958E`) has descriptors containing **two pointers, not start/end bounds**: command 1 selects `$F524/$F6BC`, command 3 selects `$F580/$F70C`. Keep those speech data private. No music-body speech API call was found statically; the bounded executed census independently observes speech only during init, but the full decoder remains unimplemented.

For the next score oracle, observe `$9422` order reads, `$9446` headers, `$945C` packed parameters, `$9490` notes, `$94F0` pattern lookahead and `$942E` global reset, plus completed body `$90E6` before the phase increment. Read active `$82–$96` and `$DC–$E6` before `$90B3` exchanges them with `$9104–$9118` and `$9119–$9123`. Verify the predicted reset indexes and all writer ordering before claiming an editable independent reconstruction.

## Listening and model checkpoints

Machine-preparation review on 2026-10-15: no OpenRouter or local SongBench inference. The unresolved questions concern executed timing, state ownership and speech decoding, which require machine evidence rather than a musical score or prose critique. The existing model routes remain experimental; assess their usefulness again at the first representative Ghostbusters audition rather than treating this no-call decision as a case-wide exclusion.

No independent reconstruction or transfer is available yet, and no Ghostbusters musical verdict is inferred from earlier cases. At the first representative comparison, after feedback or a substantive revision, and before closure, record the [model-assistance review](../audio-assessment.md#use-and-reassess-model-assistance). Models remain experimental supporting signals; execution and PCM checks must not be presented as musical acceptance.
