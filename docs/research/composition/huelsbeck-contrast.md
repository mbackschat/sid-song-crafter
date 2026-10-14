# Hülsbeck contrast: Shades and Giana in-game tune 1

The required [M1 contrast](../study-plan.md#required-contrasting-references-for-the-six-composers) compares the accepted [Shades primary study](shades-preparation.md) with **The Great Giana Sisters, HVSC subtune 3, in-game tune 1**. Intake completed on 2026-10-14 for the first 32 seconds. This establishes source identity, explicit selection and initialized modeled playback; the mechanism comparison and human listening verdict remain unverified. Preserve the accepted Shades reconstruction and familiar transfer.

## Source and musical selection

Existing [composer research](../composers/huelsbeck-tel.md) and cached HVSC STIL identify Hülsbeck's reggae intention for the in-game music but do not number its subtunes. The primary [Ultimate SID Collection v1.7 catalogue](https://ultimatesid.dk/download/pdf/_Ultimate%20SID%20Collection%20V1-7.pdf), page 6, row 96, identifies **in-game tune 1 as HVSC subtune 03**, credited to Chris Hülsbeck, 1987 Time Warp. Its page 5 distinguishes intro #1 and title #5; page 6 identifies high score #2. The [curator's methodology](https://ultimatesid.dk/#sidinfofaq) describes checking function against HVSC and practical game testing. The catalogue's 1:51 is its edited recording duration, not our verified source form or loop length.

Select #3 because its documented in-game role directly tests the primary's methods in the rhythm-led context requested by the plan. Avoid inferring a musical role from the default #1, a remix title or the audio alone. The [composer's interview](https://www.retrogamingplanet.it/dal-c64-alliphone-chris-huelsbeck-ed-i-suoi-30-anni-di-musica/) separates reggae-inspired in-game material from the opening's Madonna homage and the menu. Keep Chris Hülsbeck's C64 music credit; the opening homage is not a source-composition attribution for selected #3. [CSDb](https://csdb.dk/sid/?id=13997) independently identifies the archive, composer and 1987 Time Warp credit.

| Intake item | Verified value |
| --- | --- |
| Original source | [HVSC download](https://hvsc.c64.org/download/C64Music/MUSICIANS/H/Huelsbeck_Chris/Great_Giana_Sisters.sid); registered as `great-giana-sisters` in [local assets](../../../config/local-assets.json) |
| Source SHA-256 / bytes | `014764e6ee11df4b458c6b30e235ea639d702bd56766a87b5e90d4737558b1c8` / 23,445 |
| Header | RSID v2, flags `$0014`, PAL, one MOS6581; 23 subtunes, default #1, explicitly selected #3 |
| Payload / entries | `$71E3–$CCF9`; init `$CC86`, play `$0000` |
| Timing declaration | Machine-controlled; RSID's reserved zero speed word is not VBI evidence |
| Callable admission | `pal-banked` rejected: `Audit requires a complete PSID header`; no CPU ledger requested |
| Catalogue local pin | Ignored `.local/research/giana/ultimate-sid-collection-v1.7.pdf`, SHA-256 `fe18124e7e79d36c9024e1c4141b27b3054de964b05e104e54d9fa7e9fc88e29`; table text and page-6 rendering checked |
| STIL local pin | Existing `.local/downloads/HVSC-STIL.txt`, SHA-256 `b1ef3584a5b3501e2bbd2ef056d6539a1bbee7933a7828537c3946c1b16cde43`; composer-attributed game-wide commentary, no #3 label |

## Bounded execution and reproduction

The [Giana-only intake spec](../../../config/reference-intake/giana-contrast.json) uses the existing [full-machine-render route](../../workflows/reference-intake.md). All five stages completed: source selection, initialized render, measurements and two excerpt windows. The [working listening index](../../../build/reference-intake/giana-contrast/listening.md) links the 32-second original-source render and excerpts at **0–12 seconds** and **16–28 seconds**. These are preparation windows, not yet identified causal probes or source-versus-reconstruction comparisons. The [run receipt](../../../build/reference-intake/giana-contrast/run.json) retains stage outputs and dependency fingerprints; [readiness receipt](../../../evidence/huelsbeck-contrast/intake/readiness.json) retains compact source/selection evidence without audio bytes.

```sh
python3 scripts/setup-project.py --only references --include great-giana-sisters
python3 scripts/reference-intake.py run config/reference-intake/giana-contrast.json --output build/reference-intake/giana-contrast
```

Settings are explicit subtune 3, forced PAL, MOS6581, libsidplayfp 3.1.1/SIDLite, power-on delay zero, 44.1 kHz mono PCM16, unity gain and no normalization. The full bounded render contains 1,411,200 PCM frames, peak 15,819, AC RMS 2,529.41 and zero rail samples; WAV SHA-256 is `0ac9ddd314a85d941d446c73f0ad403ea8dbb4f35e50f3ba79ecaa188ce12c98`. These checks establish captured duration and signal health, not musical quality, hardware fidelity, complete form or an ending.

The renderer also retains register snapshots after rendering iterations. They are not ordered stores or one observation per PAL frame. They cannot prove sample absence, retain fast `$D418` modulation, identify the responsible instructions or establish original bus timing. The composer mentions digitized drums, bass sounds and effects for Giana at game level; this does not identify which of those roles selected #3 uses. Resolve that distinction with full-machine instruction/store evidence before assigning every audible part to the three oscillators or transferring a once-per-refresh instrument model. Do not patch the RSID header or weaken callable admission.

## Three testable findings

| Primary finding from Shades | Question and evidence that will settle the Giana contrast | Current result |
| --- | --- | --- |
| A rest clears GATE while pulse/program motion can continue through release; the listener heard the moving-pulse opening as quieter and more vibrant than its frozen diagnostic. | Across a selected #3 note and rest, do pulse updates continue after gate-off, restart on the next note, or stop? Retain ordered pulse/control stores and the state update/reset instructions, then use one pulse-step-only intervention with a same-material original comparison if this motion exists. | Unverified; the 32-second source render supplies an opening context only. |
| Shared-filter trigger ownership differs from routing and from ongoing contour advancement; Shades' opening voice 1 does not trigger its voice-3-owned contour. | Which selected #3 voice or score command owns cutoff resets, and which voices are routed through the filter? Capture cutoff, resonance/routing and mode/volume stores with their executed owners across an onset and one subsequent phrase change. Separate any volume-path audio from filter-mode bits. | Unverified; successful PAL/6581 rendering does not establish shared-filter ownership. |
| Delayed pitch modulation, target glide and note articulation have separate state rules; the accepted familiar Shades transfer verifies useful pulse/vibrato sounds without approving every glide ending. | Do selected #3 sustained and short notes retain delayed modulation or intentionally emphasize prompt retriggers? Identify score/onset boundaries and executed frequency changes rather than treating every pitch write as a new note; test one delay/depth parameter only after locating its real owner. | Unverified; reggae intent motivates the context, but does not prove a particular driver mechanism. |

The next smallest probe is an initialized **12-second full-machine store/instruction capture of subtune 3**, first accounting for `$D418` writers, cadence and sample-data or arithmetic sources alongside oscillator stores. Reuse the proven [Arkanoid machine-observation pattern](galway-contrast.md#sources-and-execution-boundary) where compatible, with an explicit Giana entry/interrupt contract; its source-specific script is not an admitted Giana tracer. This role/timing census decides whether a pulse-through-release intervention is appropriate or would omit a software-audio role. No Giana intervention, reconstruction, transfer or listening acceptance is claimed here.

Model assistance is not requested at this intake-only checkpoint. Reassess its usefulness at the first representative audition after role attribution; the [audio-assessment policy](../audio-assessment.md#use-and-reassess-model-assistance) preserves human musical authority. Original SID bytes, catalogue downloads, WAVs and all source excerpts remain ignored under `.local/` or `build/`. Canonical evidence promotion is separate and should retain reviewed metadata/analysis records rather than the source-audio cache.
