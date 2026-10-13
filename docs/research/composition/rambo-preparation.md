# Rambo: First Blood Part II — loader preparation

This prepares Martin Galway's **Rambo: First Blood Part II**, selected subtune **1**, while [Shades](shades-preparation.md) remains the active reconstruction awaiting listening. The retained evidence now covers attribution, archive declarations, executed command grammar and the complete finite loader traversal with its natural stop. No independent player, rendered-audio, audible-tail or listening result is claimed. Start with the [Galway composer study](../composers/hubbard-galway.md#galway-a-source-language-instrument-and-a-rapid-audition-system), [commented-source boundary](../tools/source-studies.md) and [technique lookup](../technique-index.md).

## Loader credit and pinned sources

The optional `rambo-first-blood-part-ii` entry in [the asset registry](../../../config/local-assets.json) owns the [HVSC SID](https://www.hvsc.de/download/C64Music/MUSICIANS/G/Galway_Martin/Rambo_First_Blood_Part_II.sid), ignored destination `.local/rambo-source.sid` and SHA-256 `88a2b538ee3d3d1d8b0b754bef77a63d9750812694786977ae8c539f6ecd000e`. The archive is 16,805 bytes; its header credits Martin Galway, released by Ocean in 1985. The original stays outside Git.

Galway's [primary loader source](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/rambload.asm), at revision `a458a3687e27a63647bbe41968094f0e6d0965a0`, explicitly identifies loading music and credits **composition, arrangement and programming to Martin Galway**, dated November 12, 1985. It also warns that this is a limited SSI version. The [composer-owned repository statement](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/README.md) and [Ocean assembler notes](https://github.com/MartinGalway/C64_music/blob/a458a3687e27a63647bbe41968094f0e6d0965a0/ocean_assembler_directives.txt) establish its provenance; the source was not rebuilt or assumed byte-identical to the archive.

Cached [STIL](https://hvsc.c64.org/download/C64Music/DOCUMENTS/STIL.txt) v85, June 28, 2026, identifies **#1** as the creator-name Morse-code introduction and **#2** as the same loader with corrected Morse code. Its comment discusses the I/E encoding error. STIL separately attributes source compositions in #3, #6, #7, #8, #10, #11 and #21 to Jerry Goldsmith and #22 to Richard Wagner; #11 names the First Patrol/Brian Carter disco version as the covered arrangement. Those credits do not replace the direct loader credit or establish that all 24 subtunes are original Galway compositions. The [attribution receipt](../../../evidence/rambo-intake/attribution.json) retains source, STIL and primary-source hashes, subtune scope and correspondence boundaries.

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

The [executed snapshot](../../../evidence/rambo-form/complete40000/probe-executed.py) pins the proof version; the source-specific probe requires the matching primary source and opening evidence before CPU startup. The offline checker reads the canonical compressed event ledger directly and rejects an existing output before processing it. Standard evidence restoration produces decompressed `.json` files; use the archive `.gz` path for this checker, or copy that compressed file unchanged. The [earlier verification](../../../evidence/rambo-form/transition-verification.json) and its [exact checker snapshot](../../../evidence/rambo-form/check-transitions-executed.py) retain the original proof hashes. The next musical task is to map ongoing pulse/frequency programs and timed phrases to these consumed commands before choosing an intervention. Preserve source SIDs and reference audio in ignored storage; Shades remains the active reconstruction.
