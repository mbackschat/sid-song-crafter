# Cybernoid II: pinned title reference and intake boundary

This is bounded binary intake for Jeroen Tel's **Cybernoid II**, title subtune **1**, while Shades remains the sole active reconstruction under the [study plan](../study-plan.md). It establishes archive identity, a limited static connection to the recovered listing and a rendered opening. It does not establish executed instruments, actual update cadence, complete form, reconstruction fidelity or a listening verdict. Consult the [composer account](../composers/huelsbeck-tel.md#jeroen-tel-arrangement-and-driver-collaboration), [listening catalogue](../composers/listening-catalogue.md) and [source-study boundary](../tools/source-studies.md) before extending this intake.

## Archive identity

The [optional `cybernoid-ii` asset](../../../config/local-assets.json) owns the [HVSC URL](https://www.hvsc.de/download/C64Music/MUSICIANS/T/Tel_Jeroen/Cybernoid_II.sid), SHA-256 `41f338f44b4f54e351e672156ee0e2a60c8437eb24645db3f9d4abfbb0cff192` and ignored destination `.local/research/cybernoid-ii/Cybernoid_II.sid`. The downloaded file is 4,502 bytes. Its header credits **Jeroen Tel**, title `Cybernoid II`, release `1988 Hewson`. The [recovered source](https://github.com/realdmx/c64_6581_sid_players/blob/f215174fc4c983674808fcd47bc506f96b3d2d04/Tel_Jeroen_MON/Tel_Jeroen_Cybernoid2.asm) separately credits **Charles Deenen** for `MUSICFILE V01-07-1988`; retain music and driver credit separately.

| Actual archive field | Inspected value |
| --- | --- |
| Format / header size | PSID v2 / `$007C` bytes |
| Subtunes / default | 2 / 1 |
| Selected musical scope | #1 title; cached HVSC STIL labels #2 game over |
| Speed word | `$00000000`: VBI declaration for both subtunes |
| Flags / SID layout | `$0014`: explicit PAL, MOS6581, one SID; additional-SID fields zero |
| Header / embedded load | Header zero; embedded little-endian `$A600` |
| Init / play | `$A600` / `$A603` |
| Payload | 4,376 bytes, `$A600–$B717`; end `$B718` exclusive |
| Relocation fields | Start page and page count zero |

Reproduce acquisition and verification through the existing [setup workflow](../../setup/local-setup.md), without another downloader:

```sh
python3 scripts/setup-project.py --only references --include cybernoid-ii
python3 scripts/setup-project.py --check --only references --include cybernoid-ii
```

Both commands also select the two existing default DRAX references. Setup installs only verified bytes and preserves a modified local file rather than overwriting it. Reference binaries and WAVs remain outside Git.

## Bounded correspondence with the recovered listing

The existing cached listing `.local/downloads/tel-cybernoid2.asm` has SHA-256 `119b8cb1ecaf6a9700d1847c9879fa78d50229345dccaaa4f555d8354b73fe66` and the source revision linked above. It declares a generated `$1000` layout with init `$1000`, play `$1006`, two/default 1, zero speed word and PAL/6581 flags. The archive instead contains entry shims: `$A600→$A606` (`TAX`, then jump through `$A620→$A6CA`) and `$A603→$A626→$A716`. Do not reuse listing addresses as archive PCs.

| Static comparison | Result and limit |
| --- | --- |
| Literal initialization fragment, listing lines 190–194 | `STY $D416; INY; STY $D417; LDA #$1F; STA $D418` matches bytes `8c16d4c88c17d4a91f8d18d4` once at `$A6F5`. This is a code-byte match, not an observed store sequence. |
| Annotated nonempty eight-byte sound records, listing lines 1505–1522 | All 18 match once each, in source order, contiguously at `$B01C–$B0AB`. The 144-byte block has SHA-256 `25e907f6d8b97bb30b49d57e8d750032812a975ff892a409e4420fa958126377`. |
| Selected labels retained as navigation | `bass` at `$B01C`, `bassdrm` at `$B024`, `snardrm` at `$B02C`, `arp+filt` at `$B034`, first `melo-1` at `$B03C`. These are source labels attached to matching bytes, not proven title-instrument selections. |

The limited comparison makes the recovered listing a useful interpretation route. It does not prove that the entire player, score, tables or effect timing are byte-identical. The listing was not assembled during this intake. The [source-comparison receipt](../../../evidence/cybernoid-ii-intake/source-comparison.json) retains the exact record matches, bounded static disassembly and comparison limits; the [header receipt](../../../evidence/cybernoid-ii-intake/header.json) retains the inspected archive metadata. Separate bass and drum definitions do not establish actual voice time-sharing in a particular phrase.

## Reproduce the opening reference

Use the existing [audio renderer](../../workflows/audio-workflow.md), libsidplayfp **3.1.1 / SIDLite**, from initialization. Its `selectSong(0)` selects the archive's default #1. The render uses forced PAL, the declared MOS6581, power-on delay zero, 44,100 Hz mono PCM16, 30 seconds, unity gain, no normalization and no trimming. Choose a fresh output directory; the renderer does not protect an existing output from replacement.

```sh
mkdir build/cybernoid-ii-intake-new
.local/bin/render-sid .local/research/cybernoid-ii/Cybernoid_II.sid build/cybernoid-ii-intake-new/reference-opening.wav 30
shasum -a 256 build/cybernoid-ii-intake-new/reference-opening.wav
```

The [observed opening WAV](../../../build/cybernoid-ii-intake/reference-opening.wav) SHA-256 is `60c139597792fbe0251ecf563c6dfcd6c544c3486c7ff0c78e967b9723cd650c`. It contains 1,323,000 sample frames, peak 11,661, AC RMS approximately 3,186.94 and zero PCM rail samples. The renderer executable SHA-256 is `80c6e88730445f65e03e28a56bb251922461e6d4364897b0bd79195edb53fdfe`; its [source](../../../scripts/render-sid.cpp) SHA-256 is `c7bc5f7b0fe8d18a54ecde7338b6efa786f87f54ec258a00fb01025486bad5fc`. The [render receipt](../../../evidence/cybernoid-ii-intake/render-receipt.json) retains the command, settings and measurements. This is an opening reference, with no listening verdict or complete-form/ending claim.

## Exact next execution contract

Current [RAM-only audit](../../../scripts/psid_audit.py), [instruction tracer](../../../scripts/trace-sid-program.py) and [fixed-PAL VICE tracer](../../../scripts/trace-sid-vice.py) require one subtune and payload entirely within `$0400–$9FFF`; they reject this intact archive. The [Shades CIA route](../../validation/cia-tracing.md) additionally requires CIA speed word 1 and its source wrapper is hash-pinned. No auditor was changed, header adapted or guard bypassed for this intake.

The next bounded task should establish a **selected-subtune execution profile for this pinned archive**: explicitly select one-based #1 and pass A=0 to init, retain the original two-subtune header and speed declarations, expose RAM beneath BASIC for the `$A600–$B717` code/data, preserve the driver's banking/zero-page behavior, and prove bounded ordered stores against a real headless VICE run from init. Subtune #2, if supported later, requires A=1 and its own evidence. Define the callable entry-register/status contract as well: the existing CPU audit retains A/status from the preceding driver call, whereas the fixed-PAL raster host enters play after its `A=250` polling comparison. Likewise, existing VICE store tracing begins after init. A new profile must verify any required entry-state agreement and label initialization-store coverage explicitly. Do not infer executable cadence from the zero speed word alone. Actual hardware dependencies, call cost, source correspondence beyond the compared regions and the complete title form remain open; mechanism decoding follows those checks.
