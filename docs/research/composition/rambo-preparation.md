# Rambo: First Blood Part II — loader preparation

This prepares Martin Galway's **Rambo: First Blood Part II**, selected subtune **1**, while [Shades](shades-preparation.md) remains the active reconstruction awaiting listening. The intake establishes attribution, archive declarations, source correspondence and 64 guarded CPU calls. It makes no whole-form, independent-player, rendered-audio or listening claim. Start with the [Galway composer study](../composers/hubbard-galway.md#galway-a-source-language-instrument-and-a-rapid-audition-system), [commented-source boundary](../tools/source-studies.md) and [technique lookup](../technique-index.md).

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

These are **64 controlled sequential calls under a per-call PAL-frame cycle budget; cadence is declared, not measured**. The CPU audit supplies no idle cycles or raster/IRQ dispatch measurement; its nominal `callRateHz` is a profile assumption. The source remained unchanged and the existing RAM, ROM, I/O, stack and call-budget guards passed. No actual VICE cadence, bus-write timing, complete form, ending, sound synthesis or listening judgment follows.

The [final receipt](../../../evidence/rambo-intake/receipt.json) pins source/tools/results and records a cadence-prose correction without repeat execution. The [exact executed probe](../../../evidence/rambo-intake/probe-executed.py) and [original execution receipt](../../../evidence/rambo-intake/receipt.original-execution.json) preserve historical hashes; their superseded cadence wording must be read through the final correction. The [current probe](../../../evidence/rambo-intake/probe.py) is the reproduction template with corrected wording.

## Reproduce and extend the bounded intake

Run from the repository root after [local setup](../../setup/local-setup.md). Choose a fresh output directory; these tools protect existing outputs. The source-specific probe also requires the pinned cached STIL and primary-source checkout named in its attribution receipt. The following commands reproduce the intake; they were not run a second time for the documentation.

```sh
python3 scripts/setup-project.py --only references --include rambo-first-blood-part-ii
python3 scripts/setup-project.py --check --only references --include rambo-first-blood-part-ii
python3 scripts/sid_intake.py .local/rambo-source.sid --subtune 1 --output build/rambo-intake-new/header.json
cp evidence/rambo-intake/probe.py build/rambo-intake-new/probe.py
PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 build/rambo-intake-new/probe.py
```

For the standard report and ledger alone, use `PYTHONPATH=.tools/test-deps:.tools/arrangement-deps python3 scripts/psid_audit.py .local/rambo-source.sid --ticks 64 --profile pal-banked --subtune 1 --output build/rambo-audit-new/audit64.json`. The next bounded execution check can use the existing [selected-subtune VICE route](../tools/sid-program-analysis.md#trace-a-selected-subtune-in-banked-ram) with this ledger and calls 0–63, measuring the controlled host's cadence. Musical analysis should then connect actual score/code commands and ongoing pulse/frequency programs to executed state before any reconstruction. Keep source SIDs and reference audio ignored; restore compressed working records through [the evidence workflow](../../workflows/build-cache.md).
