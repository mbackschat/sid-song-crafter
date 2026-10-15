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

## Independent score and sound components

Source inspection and isolated execution map music code `$A040–$A1F3` to runtime `$93E2–$9595`. Music init resets the three order cursors, pattern cursors and remaining-duration counters; the body processes voices **2→0**. Preserve the wrapper's context exchange and `$E2` increment when testing the body independently: reading idle zero page would inspect the swapped-out host context. The score oracle executes `$90E3` through `$90F5`, retaining the active state before it is exchanged back.

| Runtime state / source data | Verified component interpretation |
| --- | --- |
| `$82`, `$85`, `$88` (three bytes each) | Per-voice order cursor, pattern cursor, remaining duration |
| `$8B`, `$8E`, `$91`, `$94` (three bytes each) | Note, row header, cached control, instrument |
| `$E2` | Shared phase; score work runs when its low two bits are zero |
| `$A2B7/$A2BA` | Three order-stream pointer tables; streams start at `$A2BD`, `$A32B`, `$A399` |
| `$A75B` | Pattern-pointer table |
| `$A1F4` | 96-word frequency bank |
| `$A7EF` | Eight-byte patch records; nine records, with six used bytes in the final record |

The [independent score scheduler](../../../scripts/studies/ghostbusters/score.py) decodes editable semantic rows and generates scheduling decisions without executing the original player. Header low five bits give duration, `$20` retains gate, `$40` marks a header-only rest and `$80` introduces a packed volume/instrument parameter. Pattern `$FF` advances the order; order `$FF` invokes the global reset. The [original-code oracle](../../../scripts/studies/ghostbusters/probe-form.py) retains both context exchanges and the NTSC phase increment, but executes isolated RAM music fragments rather than the RSID's complete machine environment.

The [complete component proof](../../../evidence/ghostbusters-components/form/receipt.json) matches 35,315 score reads, 2,394 semantic rows and all 13,961 named return states. The first traversal comprises 109 order entries per voice, 65 selected patterns, 400 distinct rows and 2,391 executed rows. Reset occurs at zero-based body index **13,952**; the first restart rows occur at **13,956**. Reset retains instruments `[5,1,3]`, notes `[59,30,95]`, headers `[71,3,3]` and sound-owned control caches `[33,33,129]`. Restart therefore differs from cold initialization; it is not proof of whole-state recurrence.

Private one-byte note and duration controls agree with independently edited scores. Duration+1 moves the next melody onset from body 16 to 20 while preserving companion/global stores. The first 128 source-oracle calls also match all 85 music stores and 24 initialization clears in the initialized machine capture. That capture did not sample the active named RAM state: distinguish the full isolated score proof from the bounded machine corroboration.

### Sound programs

Patch records at `$A7EF` contain pulse low/high, control, AD, SR and vibrato shift, followed by two unused fields. Explicit score selections use records 1, 2, 3, 5, 6, 7 and 8; initialized record zero also matters. Controls select pulse `$41`, saw `$21` or noise `$81`; no continuing PWM, filter or sync/ring path was found in this music body. The [pure sound helpers](../../../scripts/studies/ghostbusters/programs.py) independently implement onset, continuing body and shared-volume behavior; the [sound probe](../../../scripts/studies/ghostbusters/sound-probe.py) compares their outputs at executed source boundaries. The [sound receipt](../../../evidence/ghostbusters-components/sound/receipt.json) verifies 42,083 stage boundaries and partitions all 41,506 play stores across 13,961 calls; the 24 initialization clears are counted separately. Four private controls change pulse width, sustain/release, vibrato shift and row volume while preserving all stores outside their declared ports. The vibrato test edits the original patch 8 shift at a gated, eligible body (call 1,697), rather than enabling an unrelated effect just to create a difference. This is numeric port behavior, not an oscillator/envelope model or a listening verdict.

Onsets write frequency **high then low**, then control, pulse low/high and AD/SR. Rests retain pitch and write patch setup with GATE masked low. Continuing quarter-step bodies clear GATE unless header `$20` retains it; remaining duration zero additionally clears AD/SR. Vibrato instead writes frequency **low then high**, using phase `[0,1,2,3,3,2,1,0]` and the adjacent-note difference divided by `2^(shift+1)`; displacement requires original duration at least 5. Instruments 2 and 8 use shifts 2 and 3. Preserve both write orders when verifying independent output.

Packed volume commands write at `$9486` (source `$A0E4`). Nibble `$F` computes a fade from the **voice-zero order cursor**, `min(15,109−cursor)` over the selected range. Descending voice processing therefore affects simultaneous volume commands. The score executes that global reset and restart. Preserve its continuation when preparing fidelity comparisons; a finite ending would be a separate arrangement decision and listening judgment.

### Serialized speech decoding and timing boundary

The speech relocation is source `$9124–$A03F` to runtime `$F080–$FF9B`. Default init invokes commands 1 and 3 through `$9097` → `$F080` before installing the music IRQ; nondefault subtunes take the speech-only branch. Dispatcher `$F42E` (source `$94D2`) supports `$FF` busy query, `$FE` timer stop and `$FD` dictionary-base assignment through X/Y. The dictionary at `$F4EA` (source `$958E`) has descriptors containing **two pointers, not start/end bounds**: command 1 selects `$F524/$F6BC`, command 3 selects `$F580/$F70C`. Keep those encoded speech data private.

The [independent decoder](../../../scripts/studies/ghostbusters/speech.py) implements waveform unpacking, rounded interpolation, ramp updates, signed pitch trajectories and handler/output order from private encoded descriptors. It neither executes source instructions nor replays captured amplitude events. The [checker](../../../scripts/studies/ghostbusters/check-speech.py) executes the original code separately, finishing each NMI before starting the next, and compares every generated 128-byte buffer, named state, pointer, handler and volume store. The [serialized proof](../../../evidence/ghostbusters-components/speech/verification.json) covers both opening commands and two private one-byte controls that change the actual output sequence.

| Decoder constraint | Reusable implementation rule |
| --- | --- |
| First encoded symbol | Duplicate the first actual sample; in variable two-bit encoding, the first symbol selects the amplitude scale |
| Packed order | Nibbles continue low then high; two-bit and one-bit symbols advance from low bits |
| Interpolation | Use rounded integer average `(a+b+1)//2` and preserve sequential buffer updates |
| Header `$10` | Suppresses the first interpolation only on interpolating paths; the ramp path's tail jump bypasses that processing |
| Pitch descriptor | Preserve the five-bit countdown and signed delta table; do not interpret the two pointers as sample bounds |
| Unsupported scale zero | Reject the source-code alias rather than inventing a portable amplitude table |

Serialized command 1 produces 15,143 NMI events and 12,338 volume stores; command 3 produces 25,897 events and 17,768 stores. The initialized machine capture instead has **eight extra events/stores in command 1 and two in command 3**. This is a known unresolved scheduling difference, not rounding tolerance or established PCM equivalence. The first divergence is diagnosed below; complete interrupt interleaving and buffer production remain prerequisites for a source-matching native speech timing claim. Do not infer that removing ten samples would align the streams. The component decoder is verified; complete speech integration and native export remain open.

The retained first-mismatch analysis (`build/ghostbusters-speech-timing/first-mismatch.json`, SHA-256 `0a0fdc0d24d6002b52a64466dd6d5eb574e7491af899aa1d7a4e18800a894cc9`) identifies command 1 event 337 as the first handler/output divergence. Source events 321–337 contain 17 forward entries, versus 16 serialized entries; both following reverse runs contain 16. At checkpoint cycle 2,302,947, `$F0F5` publishes the forward NMI vector while the outer handler is active; 19 cycles later another forward handler enters with a nested stack. Further nested entries interrupt buffer production. This proves non-atomic producer/consumer overlap. Source order and cycle spacing strongly place the first interruption before `$F101` resets the forward count, explaining a lost decrement; the exact interrupted PC and counter stores were not checkpointed, so that precise locus remains an inference. An atomic serialized sampler would be a declared scheduling adaptation, not verified reproduction of this interleaving.

### Reproduce the component checkpoint

```sh
python3 scripts/listening-package.py config/listening/ghostbusters-components.json --output build/ghostbusters-components
python3 scripts/evidence.py verify --group ghostbusters-components
```

The [combined recipe](../../../config/listening/ghostbusters-components.json) runs component guards, initialized machine capture, complete isolated score/sound proofs and serialized speech controls. It binds the original source, imported helpers, py65 and machine dependencies. The [fresh run](../../../evidence/ghostbusters-components/run-executed.json) took **178.087 seconds** on 2026-10-15 and passed all 42 guards; the [unchanged recheck](../../../evidence/ghostbusters-components/run-reused.json) took **0.256 seconds**, reusing all five stages without subprocesses. Retained stage receipts bind their exact dependency fingerprints, including the CPU oracle. Public evidence includes complete music records and aggregate speech verification; speech-bearing machine traces and decoder output streams stay under ignored `build/`. The output is preparation for an independent player, not a compiled reconstruction, transfer or musical acceptance.

## Independent numeric player

The [independent player](../../../scripts/studies/ghostbusters/player.py) consumes `Scheduler.step().actions` in order, retaining one authoritative score state and three sound-owned cached controls. A volume action must use its saved `voice0OrderCursor`; reading the scheduler's final state would use a later cursor. Global reset stops the current call's remaining voice processing and preserves cached controls. Hardware GATE writes and cached control are distinct: rests and releases mask the emitted value without clearing the cache. Initialization clears `$D417` through `$D400` in descending order and does not invent a volume store.

The [retained-only checker](../../../scripts/studies/ghostbusters/check-player.py) verifies canonical component hashes and historical dependency bindings before comparing complete initialization/play stores, named score returns, control caches and sound contexts. The [receipt](../../../evidence/ghostbusters-player/receipt.json) records agreement on all 41,530 stores, 13,961 return states and 42,083 sound contexts, including reset and restart, plus isolated note, duration and pulse controls. This recheck executes no original CPU code and needs no private SID. The [editable composition](../../../evidence/ghostbusters-player/composition.json) declares NTSC/MOS6581 and a bounded call count; runtime generation consumes orders, rows and patches, not captured writes. Reuse the [shared assembler](../../../scripts/sid_assembler.py) and [explicit-clock audit](../../../scripts/psid_audit.py); the [Airwolf compiler](../../../scripts/studies/airwolf/airwolf_compiler.py) is a structural precedent, not a PAL timing contract to copy. Compile editable orders, rows and patches rather than expanded captured stores. A callable NTSC music-component export remains preparation until independent opening speech, machine scheduling, complete rendering and familiar transfer are delivered and reviewed.

### Reproduce the independent integration

```sh
python3 scripts/listening-package.py config/listening/ghostbusters-player.json --output build/ghostbusters-player-verification
python3 scripts/evidence.py verify --group ghostbusters-player
```

The [recipe](../../../config/listening/ghostbusters-player.json) runs 13 focused guards and the retained integration check. The [fresh run](../../../evidence/ghostbusters-player/run-executed.json) took 5.480 seconds on 2026-10-15; the [unchanged recheck](../../../evidence/ghostbusters-player/run-reused.json) took 0.053 seconds with no stage subprocesses. Changes to the evidence manifest invalidate the retained-check cache even when the component records remain unchanged. Full numeric outputs are retained losslessly; original speech amplitudes are excluded.

### Compiled music and explicit NTSC verification

The [compiler](../../../scripts/studies/ghostbusters/compiler.py) assembles [new runtime code](../../../songs/players/ghostbusters.asm) from editable orders, rows, patch records and frequency tables. Its callable PSID declares one NTSC MOS6581. The [CPU proof](../../../evidence/ghostbusters-compiler/compiled/verification.json) covers all 13,961 declared calls, all 41,530 initialization/play stores and 13,962 named state boundaries. Peak play cost is 1,148 of 17,095 cycles. Poisoned-state reinitialization and decimal-flag entry checks pass; standalone packaging rejects counts outside the composition's declared range. The SYS 2061 bootstrap has a separate two-call check with modeled raster/CIA reads, which is not real-machine autostart evidence.

The [actual VICE proof](../../../evidence/ghostbusters-compiler/vice/study.json) checks all 41,506 play stores and 13,961 calls through reset/restart. Maximum cadence error is 8 cycles against the 17,095-cycle grid and 9-cycle polling tolerance. This controlled callable-SID harness does not retain initialization stores or named RAM states; those are covered by the CPU proof. It does not execute the source RSID environment or the standalone PRG's boot path. Speech and complete audio delivery remain open; the music component is not the final reconstruction.

```sh
python3 scripts/listening-package.py config/listening/ghostbusters-compiler.json --output build/ghostbusters-compiler-verification
python3 scripts/evidence.py verify --group ghostbusters-compiler
```

The [recipe](../../../config/listening/ghostbusters-compiler.json) binds the editable composition, compiler and imported helpers, py65, shared NTSC VICE tracer, emulator and ROM/data assets. It runs ten compiler guards, full CPU execution and full music VICE comparison. On 2026-10-15 the [fresh run](../../../evidence/ghostbusters-compiler/run-executed.json) took 45.374 seconds; the [unchanged recheck](../../../evidence/ghostbusters-compiler/run-reused.json) took 0.133 seconds without stage subprocesses. Generated binaries remain local; numeric proofs and generated assembly are retained losslessly.

### Full source render for the eventual comparison

The [full-reference intake](../../../config/reference-intake/ghostbusters-complete.json) renders 245 seconds of unchanged subtune 1 at NTSC/MOS6581, retaining the source restart and continuation. Recreate it with `python3 scripts/reference-intake.py run config/reference-intake/ghostbusters-complete.json --output build/reference-intake/ghostbusters-complete`. The [source receipt](../../../evidence/ghostbusters-reference-full/source.json) and [stage fingerprints](../../../evidence/ghostbusters-reference-full/stages/sourceA-render.json) bind the source, renderer, settings and WAV SHA-256 `91360cff28fcb4610edbe5425662ace00aa95b186ef67705f6b81079db784f1b`. Original audio remains local. Source-only windows cover 0–12, 16–28 and 225–245 seconds; these are preparation, not independent comparisons or listening acceptance.

## Listening and model checkpoints

Machine-preparation review on 2026-10-15: no OpenRouter or local SongBench inference. The unresolved questions concern executed timing, state ownership and speech decoding, which require machine evidence rather than a musical score or prose critique. The existing model routes remain experimental; assess their usefulness again at the first representative Ghostbusters audition rather than treating this no-call decision as a case-wide exclusion.

No independent reconstruction or transfer is available yet, and no Ghostbusters musical verdict is inferred from earlier cases. At the first representative comparison, after feedback or a substantive revision, and before closure, record the [model-assistance review](../audio-assessment.md#use-and-reassess-model-assistance). Models remain experimental supporting signals; execution and PCM checks must not be presented as musical acceptance.
