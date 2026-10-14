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

## Bounded initialized render

The [executed intake](../../../evidence/ghostbusters-intake/run.json) completed all five stages on 2026-10-14 in **1.299 seconds**. The [source receipt](../../../evidence/ghostbusters-intake/source.json) records explicit subtune 1, forced NTSC matching the header, MOS6581, power-on delay zero, 44.1 kHz mono PCM16 and unity gain. The 32-second capture contains 1,411,200 frames, peak 10,822, AC RMS 2052.641 and zero rail samples; WAV SHA-256 is `0db7f82e1dfc7758fea9fa23d0d836f166442dd8326c27e56b3afcba78a2df38`.

The [local listening index](../../../build/reference-intake/ghostbusters-title/listening.md) links the full original capture and the two labelled source-only excerpts. [Renderer snapshots](../../../evidence/ghostbusters-intake/registers.tsv.gz) are numeric observations after rendering batches. They cannot recover intervening speech writes, identify writers, prove update cadence or establish a complete score cycle. The renderer uses its machine emulation; no separate VICE or ordered CPU trace has yet been captured for this case.

The reusable [intake workflow](../../workflows/reference-intake.md#specification-contract) now admits explicitly declared NTSC only on `full-machine-render`; callable `pal-banked` remains PAL-only. Fifteen focused tests pass, including NTSC subtune/clock propagation, source preservation, absence of callable audit claims and rejection of unknown/mixed declarations. This is source-preparation support, not a new NTSC composition backend.

## Static entry contract and next capture

Read-only inspection of the pinned source identifies the following **static code paths**, not yet an executed instruction/store proof. Default init at `$900D` relocates code into RAM beneath KERNAL, invokes and waits for speech commands 1 and 3, then installs IRQ `$90D2` and returns at `$9096`. The music body at `$93F0` is relocated from source `$A04E`. Rotating NMI handlers around `$F083–$F0E9` write `$D418`; their dispatcher configures CIA2 Timer B with latch `$0065`, control `$91` and interrupt mask `$82`. This supports a volume-writing speech mechanism hypothesis; measured cadence, ordering and audible passage roles remain unverified.

The next bounded probe must start **before init**, or it would omit the opening speech path. Reuse the existing Giana/Turbo file-monitor infrastructure in a source-pinned Ghostbusters adapter, retaining NTSC/MOS6581 and explicit CIA models/KERNAL context. A real host `JSR $900D` at `$0400` should return to idle `$0403`, with `A=0` selecting subtune 1. Capture init through idle, then 128 completed `$93F0` body calls and stop before the next. Count body entries rather than every `$90D2` IRQ entry, since the latter also dispatches ordinary KERNAL CIA interrupts.

Retain ordered SID stores, CPU-port changes, VIC/CIA accesses, IRQ/NMI vectors, instruction checkpoint times and raster positions. Explicitly check `$02A6` reports NTSC and the inherited `$D011/$D012` seed matches the renderer: init writes `$D012=1` without clearing the high raster bit in `$D011`. Low raster byte 1 alone does not determine the selected line. Use the declared NTSC raster geometry rather than the existing PAL parser bounds. No original-source instruction capture has been performed for this assessment; this is the next proof required before score/program reconstruction.

## Listening and model checkpoints

No independent reconstruction or transfer is available yet, and no Ghostbusters musical verdict is inferred from earlier cases. At the first representative comparison, after feedback or a substantive revision, and before closure, record the [model-assistance review](../audio-assessment.md#use-and-reassess-model-assistance). Models remain experimental supporting signals; execution and PCM checks must not be presented as musical acceptance.
