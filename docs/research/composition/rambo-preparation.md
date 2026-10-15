# Rambo: First Blood Part II — loader preparation

Martin Galway's **Rambo: First Blood Part II**, selected subtune **1**, is complete for its declared scope in the [study plan](../study-plan.md): independent compiled reconstruction, accepted characteristic phrase and natural ending, accepted familiar-material instrument transfer, and bounded contrasting Arkanoid check. The [delivery and listening evidence](#independent-compiled-loader-and-musical-delivery) separates execution agreement from the listener's judgments. Start with the [Galway composer study](../composers/hubbard-galway.md#galway-a-source-language-instrument-and-a-rapid-audition-system), [commented-source boundary](../tools/source-studies.md) and [technique lookup](../technique-index.md).

## Loader credit and pinned sources

The optional `rambo-first-blood-part-ii` entry in [the asset registry](../../../config/local-assets.json) owns the [HVSC SID](https://www.hvsc.de/download/C64Music/MUSICIANS/G/Galway_Martin/Rambo_First_Blood_Part_II.sid), ignored destination `.local/rambo-source.sid` and SHA-256 `88a2b538ee3d3d1d8b0b754bef77a63d9750812694786977ae8c539f6ecd000e`. The archive is 16,805 bytes; its header credits Martin Galway, released by Ocean in 1985. The original stays outside Git.

Galway's [primary loader source](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/rambload.asm), at revision `a458a3687e27a63647bbe41968094f0e6d0965a0`, explicitly identifies loading music and credits **composition, arrangement and programming to Martin Galway**, dated November 12, 1985. It also warns that this is a limited SSI version. The [composer-owned repository statement](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/README.md) and [Ocean assembler notes](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/ocean_assembler_directives.txt) establish its provenance; the source was not rebuilt or assumed byte-identical to the archive.

Cached [STIL](https://hvsc.c64.org/download/C64Music/DOCUMENTS/STIL.txt) v85, June 28, 2026, identifies **#1** as the creator-name Morse-code introduction and **#2** as the same loader with corrected Morse code. Its comment discusses the I/E encoding error. STIL separately attributes source compositions in #3, #6, #7, #8, #10, #11 and #21 to Jerry Goldsmith and #22 to Richard Wagner; #11 names the First Patrol/Brian Carter disco version as the covered arrangement. Those credits do not replace the direct loader credit or establish that all 24 subtunes are original Galway compositions. The [attribution receipt](../../../evidence/rambo-intake/attribution.json) retains source, STIL and primary-source hashes, subtune scope and correspondence boundaries.

## Publication and source identity

The [downloadable reconstruction](../../../samples/rambo-loader/README.md) includes our accepted SID/WAV, editable graph, corresponding build sources and a pinned manifest under GPLv3. Galway’s published source and ownership statement supply the scoped licensing basis; see the [game-music review](../game-music-permissions.md). The [source-data checker](../../../scripts/studies/rambo/check-published-score.py) compares the complete reachable graph and referenced banks to the pinned published loader without needing a reference SID. Its [receipt](../../../evidence/rambo-source-license/receipt.json) records 457 graph nodes, 32 banks, three initial data banks and 89 frequency words matched, plus altered-note/bank negative controls. It checks composition identity, not original executable-byte identity or legal ownership.

```sh
python3 scripts/studies/rambo/check-published-score.py --source .tools/martin-galway-c64/rambload.asm --description songs/rambo-loader.json --falsify --output build/rambo-published-score-check.json
```

The user requested a separate creative interpretation on 2026-10-15; reconstruction acceptance must not be carried over to that candidate. Preserve this faithful baseline while the new treatment awaits listening.

## Archive declarations and callable admission

The reusable [header inspector](../../../scripts/sid_intake.py) records declarations separately from admission in the [header receipt](../../../evidence/rambo-intake/header.json).

| Field | Inspected value |
| --- | --- |
| Format / data offset | PSID v2 / `$007C` |
| Subtunes / default / selected | 24 / 1 / 1 |
| Load / payload extent | Embedded `$6F00`; 16,679 payload bytes, ending `$B027` exclusive |
| Init / play | `$B010` / `$AFE8` |
| Speed word / selected declaration | `$00000000` / VBI |
| Flags / layout | `$0014`: PAL, MOS6581, one SID at `$D400` |

The existing [PAL banked profile](../../validation/psid-audit.md#select-a-subtune-and-expose-ram-beneath-basic) accepts the intact archive with explicit subtune 1. It restores `$01=$36` before init and each play call, supplies A=0, X/Y=0 and P=`$26` at init, and uses the controlled raster host's play-entry ABI. This establishes admission and bounded execution under that contract, not the original loader's interrupt environment. Strict admission retains its single-subtune and lower-RAM limits.

## Source correspondence and executed hooks

| Observation | Basis and scope |
| --- | --- |
| Creator-name data at `$809E` | The published source's doubled character bytes and terminator match 55 archive bytes exactly. The text names Bill Barna, David Collier, Martin Galway, Tony Pomfret and Steve Wahid. |
| Morse table at `$80D5` | All 26 bytes generated from the source's 13 words match the archive. Its I entry at `$80DD` is `$10`. |
| Subtune selection at `$B019–$B022` | The executed #1 initializer loads `$B025=$10`, stores it to `$80DD`, sets X=0 and transfers to `$AF8B`. The neighboring `$B026=$11` and wrapper branches support the corrected #2 interpretation statically; #2 was not executed. |
| Play wrapper at `$AFE8` | Initialization changes its jump target from `$FFFF` to `$AFEB`; all 64 observed outer play entries use `$AFEB`. That wrapper calls `$2006` and transfers to `$2000`. |

The [bounded hook record](../../../evidence/rambo-intake/hooks.json.gz) retains entry registers, the first 48 executed init instructions as PCs/mnemonics, PC visit counts and selected state fields. It excludes full payload, relocation-copy values and RAM dumps. Matching these data and wrapper paths does not establish full source-build equivalence or decode the loader's instrument programs. The published source's raster-polling audition host is a separate static observation, not measured archive cadence.

## Executed calls 0–63 and timing limits

The [CPU report](../../../evidence/rambo-intake/audit64.json) records **65,430 init cycles**, **25 init SID stores** and **552 play SID stores**. Maximum play-body cost is **1,954 / 19,656 cycles**; mean cost is **539.140625 cycles**. Init uses the auditor's separate million-cycle ceiling and exceeds one PAL frame. The [ordered ledger](../../../evidence/rambo-intake/audit64.writes.json.gz) preserves all 577 records, including phase, call, address, value and instruction-start cycle.

These are **64 controlled sequential calls under a per-call PAL-frame cycle budget; cadence is declared, not measured**. The CPU audit supplies no idle cycles or raster/IRQ dispatch measurement; its nominal `callRateHz` is a profile assumption. The source remained unchanged and the existing RAM, ROM, I/O, stack and call-budget guards passed. This opening audit alone establishes no actual VICE cadence, bus-write timing, complete form, ending, sound synthesis or listening judgment; the distinct full-form and selected VICE checks below supply their own scopes.

The [final receipt](../../../evidence/rambo-intake/receipt.json) pins source/tools/results and records a cadence-prose correction without repeat execution. The [exact executed probe](../../../evidence/rambo-intake/probe-executed.py) and [original execution receipt](../../../evidence/rambo-intake/receipt.original-execution.json) preserve historical hashes; their superseded cadence wording must be read through the final correction. The [current probe](../../../evidence/rambo-intake/probe.py) is the reproduction template with corrected wording.

## Executed command grammar and stream addresses

The [opening map](../../../evidence/rambo-form/mapping64-complete/mapping.json) locates ordinary `REFRESH` at `$2606`. It calls the three physical SID voices in order. Stream pointers, remaining-duration bytes and descending stack indices occupy `$10–$15`, `$1A–$1C` and `$1D–$1F`; `$19` holds active bits 0–2. The [mapping verification](../../../evidence/rambo-form/mapping64-complete/mapping-verification.json) matches all 577 opening records to the original intake and checks 81 bounded entry/dispatch instructions against archive bytes loaded at `$6F00` and executed after relocation to `$2000`. This is bounded correspondence, not a rebuilt SSI-source identity.

| Physical voice | Initial stream | Fetch PC / indirect pointer | Command JMP / pointer table |
| --- | --- | --- | --- |
| 1 | `$2CE0` | `$20B8` / `$10–$11` | `$20D8` / `$2AE9` |
| 2 | `$302E` | `$238E` / `$12–$13` | `$23AE` / `$2B25` |
| 3 | `$2ECC` | `$2629` / `$14–$15` | `$2649` / `$2B07` |

Each dispatcher distinguishes rows below `$C0` from commands, then uses `opcode & $3F` as a byte offset into its own pointer table. The [instruction evidence](../../../evidence/rambo-form/complete40000/static-command-instructions.json) and [lossless events](../../../evidence/rambo-form/complete40000/events.json.gz) preserve selected targets, operands, named state and exact instruction-start context.

| Command | Executed semantics |
| --- | --- |
| `$CA` Call / `$CE` transposed call | Save stream+3 or stream+4 in the current stack slot, decrement the byte stack index and jump to the supplied word. `$CE` also replaces the transpose byte. |
| `$C0` Return | Increment the stack index and restore the saved stream. At index 8, clear the voice's active bit instead of reading another return slot. Transpose is retained. |
| `$DA` Loop / `$DC` Next | Share the same eight-slot stack with calls. Loop saves stream+2 and a repeat byte; Next decrements that byte, returns to the saved body while nonzero, otherwise pops the slot and advances past Next. |
| `$CC` Transpose / `$D2` transposed jump | Replace the transpose byte; `$D2` transfers to the supplied word without pushing a return. Availability is voice-specific. |
| `$C2/$C4/$C6/$C8/$D8` | Select volume, data, frequency, pulse or chord copy routines. Their copy widths and available slots differ by voice; this is not yet a decoded instrument bank. |
| `$D0/$D6` | Write a selected byte in the voice's data or sounding-state block. |
| `$D4` Code | Prepare a hardware-stack return to stream advancement, then jump through the supplied code pointer. This path is available on physical voice 1. |

Rows use either a duration-table lookup for raw values below 96 or a literal duration byte for values 96–191. Source `Rest` values 95/191 skip note initialization and retain ongoing sound processing; they do not imply silence. A stored zero duration wraps through byte decrement. The [offline arithmetic check](../../../evidence/rambo-form/transition-verification-cli.json), reproduced by [check-transitions.py](../../../evidence/rambo-form/check-transitions.py), matches all 1,124 selected call/return/loop/transpose transitions and 2,504 duration stores. It does not independently schedule the tune or prove unexecuted parameter edges.

The 67 executed code commands select four pointers: `$316F` once for Morse startup, `$2E2B/$2E31` once each, and `$2E27` 64 times. These correspond structurally to the published `STARTMC`, `MCFC1/MCFC2` and `YNCREMENT` routines. At call 50, Morse startup re-enters `REFRESH` within physical voice 1 processing; voices 2 and 3 are consequently processed again within that outer call. A clock that assumes one voice update per play call would lose this timing. The [selected opening instructions](../../../evidence/rambo-form/mapping64-complete/selected-instructions.json.gz) preserve that causal path.

## Finite traversal and natural stop

The [40,000-call CPU receipt](../../../evidence/rambo-form/complete40000/receipt.json) retains the unchanged source, tool/probe hashes and a cap chosen before execution. Its [complete ordered ledger](../../../evidence/rambo-form/complete40000/writes.json.gz) contains **25 init plus 87,509 play stores**; the opening prefix agrees exactly with all 577 historical records. Maximum play cost is **3,130 / 19,656 cycles**, with init still **65,430 cycles**. The cap is a bound, not a duration estimate.

The [form result](../../../evidence/rambo-form/complete40000/form.json) distinguishes three boundaries:

- **Morse introduction:** at call 1557, PC `$3100` begins restoring ordinary `REFRESH` after the zero terminator; its letter index is 54. This is not the score's end.
- **Score completion:** top-level returns clear physical voices 2, 3 and 1 at calls **10544, 10559 and 10560**, at PCs `$2457`, `$2703` and `$2192`. Each stack index reaches 8. No top-level stream restart is observed.
- **Sound-processing completion:** final stores for physical voices 1/2/3 occur at **10660/10799/10814**. At call **10815**, PC `$2605` returns A=0 from `activeMask | soundLife1 | soundLife2 | soundLife3`, with all lifetimes zero and the main dispatcher already restored. Calls **10815–39999** produce no further SID stores. This establishes a finite loader under the controlled CPU host, rather than a presumed wrap or PCM recurrence.

The independent [selected VICE check](../../../evidence/rambo-form/vice-end/trace/study.json) matches **56 stores: 25 init and 31 play**, selecting calls **10808–10822** after initialization and all preceding calls. Its 10,823 entry checkpoints remain within **4 / 9 cycles** of the controlled one-PAL-frame cadence. The [projection](../../../evidence/rambo-form/vice-end/projection.json), [oracle](../../../evidence/rambo-form/vice-end/oracle.json), [provenance](../../../evidence/rambo-form/vice-end/provenance.json) and [trace](../../../evidence/rambo-form/vice-end/trace/trace.json.gz) retain this window's store equality and absence after the final store. Store coverage outside that selected window remains CPU evidence. Neither check measures an analogue tail, establishes the original loader host, or supplies listening approval.

## Ongoing sound lifetime and programmed motion

Score completion clears an active bit; it does not terminate the voice's sound routine. Inactive `MUSIC` paths still enter `SOUND` at `$2231/$24E0/$2799`. Each routine checks a separate **sound-life byte at state offset 28**. With release countdown zero, it decrements that byte and continues PWM/pitch while nonzero. Transition **1→0** clears all seven voice registers in descending address order and returns before either program advances. Later invocations return immediately. The [named-state contract](../../../evidence/rambo-programs/contract.json) retains field offsets, arithmetic, actual PCs and supported branches.

| Physical voice | State block / life decrement PC | Life at score return → final clear | Observed ending programs |
| --- | --- | --- | --- |
| 1 | `$29B2` / `$2258` | 100 at 10560 → 10660 | PWM flag `$FF`: reload word `$969D` and ten-step counter, add `$0800` per step. Sequential pitch continues the fourth phase with encoded step `$FFFD` (−3). |
| 2 | `$29D9` / `$2507` | 255 at 10544 → 10799 | PWM disabled. Its three-phase pitch cycle adds +8/−8/+8 for 3/6/3 steps, then reloads in the same invocation. |
| 3 | `$2A00` / `$27C0` | 255 at 10559 → 10814 | PWM flag `$05`: 25 steps of +10, then 25 of −10, reloading counters while retaining width. Sequential pitch uses the retained four-phase program; its input, counters and every emitted word remain in the proof. |

These are raw programmed words and stores, without an inferred audible role. PWM uses **16-bit arithmetic**, not a normalized 12-bit state: low-byte carry propagates into the full high byte, which the driver emits unchanged. On counter exhaustion, flag bit 7 reloads width and counters; bit 0 alone reloads counters while preserving width. Delay suppresses stores for that invocation. Lifetime/control processing precedes PWM, then frequency low/high writes. The full-title follow-up below corrects the earlier phase-count interpretation: physical voice 1 has four sequential phases, while voices 2 and 3 have three. Their fourth step can still apply during frequency delay. Frequency delay either holds output or adds the fourth step according to flag bit `$02`.

The normal release-countdown path emits `control & $F6` without replacing its stored control byte. That RAM field is therefore not the last-written SID control value. The separate control-bit `$08` path compares remaining row duration with release countdown and updates the stored control when its threshold is crossed. Neither gate state nor the score-active bit substitutes for the lifetime check.

The [initialized narrow-window receipt](../../../evidence/rambo-programs/ending/receipt.json) captures calls **10540–10816**, after initialization and their preceding calls, with **828 SOUND invocations** and **2,105 stores**. Its complete executed prefix matches all **87,534** records in the earlier canonical ledger. [Input/output states](../../../evidence/rambo-programs/ending/bodies.json.gz) and [selected executed instructions](../../../evidence/rambo-programs/ending/instructions.json.gz) preserve the underlying observations without a RAM/payload dump or another 40,000-call run.

The independent [Python helper](../../../evidence/rambo-programs/model.py) accepts named SOUND state, physical voice index 0–2 and a remaining-row byte, returning new state and ordered address/value pairs. It reads no original source, CPU or event ledger at runtime. The [verification](../../../evidence/rambo-programs/verification/verification.json) matches every captured state field and all 2,105 stores, plus **54 isolated original-routine cases** for lifetime, release thresholds, PWM reset/hold/delay, pitch delay/reload and word carry/borrow. The [isolated records](../../../evidence/rambo-programs/verification/isolated.json.gz) retain exact inputs, outputs, store order and executed PCs. Forcing life=1 clears immediately without advancing either program; forcing life=0 suppresses all stores; disabling PWM retains lifetime and pitch evolution. A deliberately incorrect score-active gate misses **595** writing invocations after all score bits clear.

This component requires binary arithmetic, as supplied by the controlled host's `CLD`. The historical ending-only helper leaves arpeggio pitch on physical voices 1/3 unsupported; the full-title replacement below implements it. All-zero repeating templates are rejected as non-terminating. Note/waveform initialization, filter/global behavior, CPU register/flag outputs and whole-title component coverage remain outside this proof. Successful state/store comparison does not establish the audible tail or listening quality.

After obtaining the pinned SID and primary source, reproduce this bounded component check with fresh output directories:

```sh
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 evidence/rambo-programs/probe.py --first 10540 --last 10816 --output build/rambo-programs/new-ending
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 evidence/rambo-programs/check.py --bodies evidence/rambo-programs/ending/bodies.json.gz --output build/rambo-programs/new-check
```

The checker consumes the canonical `.gz` directly; a standard evidence restore may instead produce decompressed JSON. Its [executed helper snapshot](../../../evidence/rambo-programs/verification/model.py) and [checker snapshot](../../../evidence/rambo-programs/verification/check.py) preserve exact proof versions. The remaining program variants are retained as named inputs for later investigation, not silently approximated by this component.

## Full-title sound programs and corrected phase coverage

The reusable [sound component](../../../scripts/rambo_programs.py) extends the historical ending-only model with descending arpeggios and corrects physical voice 3's sequential phase count. The [retained full-title proof](../../../evidence/rambo-sound-full/verification.json) compares **32,448 SOUND invocations**, all named output states and **57,498 ordered stores**, including **5,728 arpeggio invocations**, over initialized calls 0–10,816. Its executed prefix matches all 87,534 records in the canonical loader ledger. The [102 isolated cases](../../../evidence/rambo-sound-full/isolated.json.gz) cover boundaries beyond the naturally occurring title inputs.

At archive PCs `$28A3–$28CE`, physical voice 3 reloads after its third sequential phase; the fourth step applies only on the delayed-frequency path. The earlier ending window never exposed an active fourth sequential phase. A negative control now makes that old assumption produce a different frequency word from original execution. Keep the historical component and receipts as evidence of their narrower coverage; use the new component for composition.

Arpeggio mode treats SOUND offsets 0–9 as ten editable chord bytes, overlaying the four frequency-step words and first two duration bytes. The position descends through `frequencyDelay`; a high-bit position reloads from `frequencyDurations[3]`. Add the selected byte to the base at `frequencyDurations[2]`, wrap to a byte, and resolve it through the supplied numeric frequency table. The selected loader accesses positions 0–8; the component supports 0–9 and rejects references outside that declared chord bank. This describes executed arithmetic, not a universal Galway instrument format.

A single source-specific command captures and checks the complete initialized sound path, or rechecks an explicitly selected retained capture:

```sh
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 scripts/studies/rambo/check-rambo-programs.py --output build/rambo-sound-new
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 scripts/studies/rambo/check-rambo-programs.py --capture evidence/rambo-sound-full --output build/rambo-sound-recheck
```

These modes preserve distinct provenance: the first executes a fresh initialized capture, while the second checks the supplied complete capture and runs isolated source comparisons. Both retain inputs, tool fingerprints and detailed outputs. Original SID and primary-source dependencies remain local.

## Independent numeric loader

The [editable description](../../../songs/rambo-loader.json), [symbolic score scheduler](../../../scripts/rambo_score.py), [sound component](../../../scripts/rambo_programs.py) and [integrated player](../../../scripts/rambo_player.py) compute initialization and the complete finite loader without original driver instructions, a CPU or a captured-event stream at runtime. The [source-specific importer](../../../scripts/studies/rambo/prepare-rambo-loader.py) alone reads and verifies the original. Its 457 symbolic instructions exactly cover the voice/address pairs consumed by the retained original score observation; original addresses remain nonexecuting annotations.

The description separates a symbolic call/loop/row graph, numeric copy banks, per-voice data and SOUND state, frequency words, and Morse letters/codes. Note initialization preserves alternating zero/data stores in descending voice-register order, raw-row arpeggio bases and selectively retained sound state. The Morse hook can recursively enter REFRESH inside physical voice 1; its terminator restores ordinary dispatch without running REFRESH on that call. Morse workspace shares the first four score repeat counters, following the published `MWK=DB0+65` alias rather than maintaining an independent copy.

When deriving accompaniment calendars, use executed next-row transitions rather than summing nominal row durations: the Morse terminator's skipped REFRESH changes an actual boundary. The [ensemble preparer's `observe_source`](../../../scripts/studies/rambo/prepare-ensemble.py) obtains each row's end from the next executed row or top-level return. This is a source-scheduler constraint, not a universal extra tick to add to every note.

The integrated regression and [retained whole-player verification](../../../evidence/rambo-verification-workflow/numeric-verification.json) compare **all 87,534 initialization/play stores** through 11,000 calls with the pinned 40,000-call original ledger, whose remainder is silent. Final physical-voice stores remain at calls 10,660, 10,799 and 10,814. Separate source interventions change an opening row duration and an instrument frequency delay; independently executing those edited source bytes agrees with the corresponding editable-description changes. Source annotations can be removed without changing output, and runtime computation performs no file access.

The supported composition contract uses the declared PAL/6581 layout and 19,656-cycle caller cadence. Table-duration selectors are 0–16; data pokes may target offsets 0–48 or the explicit transpose field 73, while SOUND pokes stay within its 39-byte record. Write-data banks contain exactly 29 bytes, matching the available physical voice 2/3 routines; physical voice 1 has no write-data command. Direct score-stack pokes are rejected. Numeric store equality establishes no compiled instruction timing, bus-cycle equality or audio verdict. The compiled export and listening package below provide those separate delivery stages, with the [accepted familiar transfer](instruments/rambo-decoded-programs.md) and [bounded Arkanoid comparison](galway-contrast.md).

Use the [study verification recipes](../../workflows/listening-package.md#verify-a-study-before-compiled-playback) for routine extraction checks, full numeric comparison, focused guards and fresh or retained SOUND evidence. The [whole-player checker](../../../scripts/studies/rambo/check-rambo-player.py) measures the stop at call 10,815 and verifies 185 subsequent quiet calls and unchanged stopped state. Cached fresh-capture results remain labelled as reused stages; a new output directory forces a new original execution.

## Independent compiled loader and musical delivery

[compose-rambo.py](../../../scripts/compose-rambo.py) compiles the editable description into our [score/Morse runtime](../../../songs/players/rambo.asm) and [SOUND component](../../../songs/players/rambo-sound.asm). Seven-byte graph records retain runtime call/return, loops, transpose, data copies, pokes and the four declared code hooks. Reentrant Morse refresh preserves the live score-stack aliases. Initialization restores all named state. The export contains no original driver instructions or captured-register schedule; the original SID is only an input to reference rendering and source verification.

The [complete compiled proof](../../../evidence/rambo-independent-full/build.json) matches all 87,534 initialization/play stores over 11,000 calls and ten named-state checkpoints. The 6,327-byte payload's maximum play call takes 5,427 cycles within the 19,656-cycle budget. The separate [VICE proof](../../../evidence/rambo-independent-full/vice/study.json) checks the same complete ordered stream, including all 25 initialization stores, and all 11,000 host entries with a maximum cadence error of seven checkpoint cycles. Raw monitor and structured trace evidence are retained in that evidence group. These comparisons do not claim identical within-call bus timing or oscillator phase.

Every executed SID writer uses a non-RMW absolute or absolute-indexed instruction, checked during compilation against the [VICE decoder's contract](../../../scripts/trace-sid-vice.py). The first implementation used indirect note writers, which passed numeric execution but could not be decoded by that verifier; the final writer preserves descending alternating zero/data stores with directly verifiable addressing. Unsupported graph reads, nonterminating numeric programs and payloads outside callable RAM fail before export. Verification is bounded to the declared call range; indefinite behavior of arbitrary edited graphs is not asserted.

```sh
python3 scripts/listening-package.py config/listening/rambo-loader-full.json --output build/rambo-independent-full
python3 scripts/listening-package.py config/listening/rambo-elise-transfer.json --output build/rambo-elise-transfer
```

The [loader recipe](../../../config/listening/rambo-loader-full.json) verifies the source pin, complete numeric source correspondence, compilation and full VICE execution before rendering the original and candidate from initialization for 225 seconds with explicit subtune 1. It prepares original-first comparisons for the intro `[0,12)`, first musical phrase `[32,48)` and complete ending `[205,225)`, with a half-second gap. Both final one-second windows have zero AC RMS; the [audio receipt](../../../evidence/rambo-independent-full/audio.json) retains duration, clipping, level and tail measurements without audio bytes. The loader follows the source's natural final release and clear, without an added volume fade. The capture boundary follows the completed musical ending.

Open the generated `build/rambo-independent-full/listening.md` for both full WAVs and the three comparisons. The submitted files are also retained locally under `build/listening-ready-20261013/rambo-loader/`, with source hashes in `sources.json`. On 2026-10-13, the listener reported no audible difference in the ending: “I can't hear a difference”. The phrase response “I can hear a difference. nice” was corrected by the listener to “I mean: can't”, accepting the phrase without an audible difference. This is no claim of PCM or hardware identity.

The different-material [Für Elise transfer](instruments/rambo-decoded-programs.md) is accepted for musical use, balance, phrasing and ending. Its two generated performances preserve the same 53 source notes and have complete CPU/VICE and settled-audio proofs. The [Galway contrast](galway-contrast.md) corroborates continuous PWM through rests and score hooks while distinguishing Arkanoid's fast computed volume-path percussion; the listener heard no difference in its small drum-parameter diagnostic, limiting its demonstrated audible editing value. These reusable musical and engine constraints, rather than store equality alone, are the study's workbench contribution.

## Reproduce and extend the bounded intake

Run from the repository root after [local setup](../../setup/local-setup.md). Choose a fresh output directory; these tools protect existing outputs. The source-specific probe also requires the pinned cached STIL and primary-source checkout named in its attribution receipt. The following commands reproduce the intake; they were not run a second time for the documentation.

```sh
python3 scripts/setup-project.py --only references --include rambo-first-blood-part-ii
python3 scripts/setup-project.py --check --only references --include rambo-first-blood-part-ii
python3 scripts/sid_intake.py .local/rambo-source.sid --subtune 1 --output build/rambo-intake-new/header.json
cp evidence/rambo-intake/probe.py build/rambo-intake-new/probe.py
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 build/rambo-intake-new/probe.py
```

For the standard opening report and ledger alone, use `PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 scripts/psid_audit.py .local/rambo-source.sid --ticks 64 --profile pal-banked --subtune 1 --output build/rambo-audit-new/audit64.json`. To reproduce form research, restore the archived opening map and canonical intake ledger to their original `build/` paths through [the evidence workflow](../../workflows/build-cache.md), then run the retained probes with fresh output directories:

```sh
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 evidence/rambo-form/form-probe.py --calls 40000 --output build/rambo-form/reproduce40000
python3 evidence/rambo-form/check-transitions.py --events evidence/rambo-form/complete40000/events.json.gz --output build/rambo-form/reproduce-transitions.json
```

The [executed snapshot](../../../evidence/rambo-form/complete40000/probe-executed.py) pins the proof version; the source-specific probe requires the matching primary source and opening evidence before CPU startup. The offline checker reads the canonical compressed event ledger directly and rejects an existing output before processing it. Standard evidence restoration produces decompressed `.json` files; use the archive `.gz` path for this checker, or copy that compressed file unchanged. The [earlier verification](../../../evidence/rambo-form/transition-verification.json) and its [exact checker snapshot](../../../evidence/rambo-form/check-transitions-executed.py) retain the original proof hashes. The compiled delivery above supersedes the earlier mapping milestone. Preserve source SIDs and reference audio in ignored storage, and use the [study plan](../study-plan.md) for the current listening gates and next case.
