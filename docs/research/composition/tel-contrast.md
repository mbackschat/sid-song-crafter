# Tel contrast: Cybernoid II and Turbo Outrun intro

The required [M2 contrast](../study-plan.md#required-contrasting-references-for-the-six-composers) checks the accepted [Cybernoid II primary](cybernoid-ii-preparation.md) against **Turbo Outrun intro, subtune 1**. The bounded contrast is complete: initialized execution establishes packed sample playback alongside oscillator programs and a tonal pulse-to-saw onset. The listener heard no difference in the onset-removal comparison. Preserve the accepted Cybernoid title and [familiar transfer](instruments/cybernoid-decoded-programs.md); no new Turbo instrument or perceptual editing benefit is promoted.

## Source, credits and execution route

[HVSC STIL](https://hvsc.c64.org/download/C64Music/DOCUMENTS/STIL.txt) identifies #1 as the intro, based on **Magical Sound Shower by Hiroshi Kawaguchi**, with Tel's sampled voice. Study Jeroen Tel's C64 arrangement separately from the arcade composition. Tel's [published account](https://blog.de.playstation.com/?p=4937), also discussed in the [composer research](../composers/huelsbeck-tel.md), names sampled drums and his own voice in Turbo Outrun; it does not locate every sampled role within this selected passage. General Maniacs of Noise collaboration and the recovered Cybernoid driver credit do not establish Turbo-specific driver authorship.

| Intake item | Verified value |
| --- | --- |
| Source | [HVSC original](https://hvsc.c64.org/download/C64Music/MUSICIANS/T/Tel_Jeroen/Turbo_Outrun.sid), asset `turbo-outrun` in [local assets](../../../config/local-assets.json) |
| SHA-256 / bytes | `02e3840800c4f5f8b626864eeae92bd46a3742085c6a37b532acb363ad5cabfc` / 56,430 |
| Header / selection | RSID v2, flags `$0014`, PAL, one MOS6581; 12 subtunes, default and explicitly selected #1 |
| Payload / entries | `$0810–$E3FF`; init `$CB40`, play `$0000` |
| Timing / admission | Machine-controlled; existing `pal-banked` callable profile rejects RSID. The reserved zero speed word does not establish VBI playback |
| STIL pin | `.local/downloads/HVSC-STIL.txt`, SHA-256 `b1ef3584a5b3501e2bbd2ef056d6539a1bbee7933a7828537c3946c1b16cde43` |

The [source receipt](../../../evidence/tel-contrast/intake/source.json) preserves credits, fingerprints and route limits. Keep original SID bytes, modified diagnostic copies and all reference audio under ignored `.local/` or `build/`.

Keep lossless sample fetches and ordered sample-amplitude traces local as well: those can encode the original audio even without a WAV container. Public evidence retains verification summaries, fingerprints, reproducible commands and the separate oscillator-onset ledger. The compressed private trace, monitor log and process log remain in the recipe cache, with hashes in each verification receipt. This applies the existing source-audio boundary without discarding the local causal evidence.

## Repeatable intake

Use the existing [reference-intake workflow](../../workflows/reference-intake.md) and [Turbo specification](../../../config/reference-intake/turbo-outrun-contrast.json):

```sh
python3 scripts/setup-project.py --only references --include turbo-outrun
python3 scripts/reference-intake.py run config/reference-intake/turbo-outrun-contrast.json --output build/reference-intake/turbo-outrun-contrast
```

The [working listening index](../../../build/reference-intake/turbo-outrun-contrast/listening.md) links a 32-second initialized original and source-only windows at **0–12** and **16–28 seconds**. Settings are explicit subtune 1, PAL/MOS6581, libsidplayfp 3.1.1/SIDLite, power-on delay zero, 44.1 kHz mono PCM16, unity gain and no normalization. The [measurement receipt](../../../evidence/tel-contrast/intake/summary.json) records 1,411,200 frames, peak 9,300, AC RMS 1,839.12 and no rail samples; WAV SHA-256 is `c6edc179b19ff53e20830d0ba80fabcec283aeb103ae1b1baf31534392a87e77`. This establishes captured duration and signal health, not musical quality, complete form or an ending.

On 2026-10-14 the five-stage [first run](../../../evidence/tel-contrast/intake/run-cold.json) completed in 7.93 seconds. An [unchanged recheck](../../../evidence/tel-contrast/intake/run-reused.json) took 0.19 seconds, reusing all five stages after artifact verification. This measures cached workflow execution, not a faster renderer or fresh machine capture.

Renderer register snapshots are observations after rendering iterations. They cannot retain intervening rapid volume writes, identify executed instructions or establish sample absence. The separate machine probe below settles those questions within its captured windows. Do not alter the RSID header to obtain callable admission.

## Initialized machine and sample path

The [source-specific probe](../../../scripts/studies/turbo-outrun/probe-contrast.py) enters `$CB40` with `A=0` through a real `JSR`, then returns to an idle host. The selected branch sets CPU port `$35`, installs RAM IRQ vector `$CD30` and NMI vector `$0943`, and schedules raster line 52. The raster IRQ calls the oscillator player; the sample dispatcher starts CIA2 Timer A, whose NMI emits the packed samples. This is a controlled headless VICE KERNAL-READY host with declared PAL/MOS6581 and CIA models, not a claim of complete original-game or renderer-state identity.

The [opening census](../../../evidence/tel-contrast/machine/verification.json) covers 128 completed IRQs, no initialization IRQ and 2.55697 seconds from init. It records 12,471 SID stores and zero monitored non-dummy SID loads across physical `$D400–$D7FF`. The sample oracle verifies **5,137 packed-source fetches, 10,250 nibble writes, 11 termination writes and two explicit retriggers that cancel a pending low nibble**. All 10,261 sample paths are paired with their observed NMI entry. A source byte supplies its high nibble then low nibble; the selected metadata chooses full-depth `nibble + $30` or half-depth `(nibble >> 1) + $34`. Sentinel `$1F` stops the timer and restores `$38`. The receipt retains safe counts, selected metadata and private artifact hashes; it does not publish the packed bytes or amplitude stream.

NMI work can delay music IRQ entry into raster line 53. Observed opening IRQ intervals range from 19,590 to 19,721 checkpoint cycles, but subtracting the difference in raster-entry phase gives exactly **19,656 cycles for all 128 intervals**. Validate the scheduled frame cadence separately from interrupt-entry latency; neither checkpoint denotes an exact SID bus-write time. The guard checks bank/vector changes, registration and enabled coverage, entry/return stacks, stop boundaries, complete IRQ counts and sample-fetch/phase/output pairing. Missing records, altered destinations and malformed completion cannot establish a successful capture.

Packed playback here is a different resource contract from Cybernoid's oscillator programs. It requires the sample data, timer service and source-specific machine host; a once-per-frame instrument scheduler cannot express it. `$D418` also controls the oscillator mix's master gain, so this is not an independent fourth oscillator or a guarantee of unchanged oscillator PCM. Published credits establish sampled drums/voice at tune level; this capture does not identify every sample by ear.

## Two findings and their limits

| Primary finding | Executed contrast | Reuse consequence |
| --- | --- | --- |
| Cybernoid's percussion and bass onset use oscillator programs, including a brief noise phase before the pitched body. | Turbo's opening executes the separate packed-sample NMI path above alongside oscillator output. | Do not infer three-voice allocation from the number of perceived parts, or transfer its sampled percussion into the ordinary oscillator-instrument model. |
| Cybernoid stages waveform changes by note age; its bass onset need not become an extra score note. | Turbo record 1 uses **pulse `$41` at observed ages 1–23**, restores **saw `$21` at ages 24–25**, then retains the saw body. The [151-row onset ledger](../../../evidence/tel-contrast/onset/onset-ledger.json) connects actual record/age comparisons to the final voice-1 control writes. | The shared authoring idea is staged tone shaping, not universally noise percussion. This parameter's perceptual value remains unestablished: the listener heard no change when its pulse phase was removed from the selected mix. |

Cybernoid's precise vibrato wait, retained phase and glide rules remain driver-specific for this contrast. Related Turbo code is an investigation lead, not an executed equivalence proof; no third finding or complete second player is required to close this bounded check.

## Isolated onset diagnostic and listening

The [later machine window](../../../evidence/tel-contrast/onset/baseline/verification.json) advances from initialization through 1,120 IRQs with selected observations disabled, then retains 192 IRQs, indices 1120–1311. Monitor checkpoint-state tables verify that full SID read/store coverage and tonal hooks are enabled in that window. It contains 19,976 SID stores. All 1,312 scheduled IRQ intervals retain the PAL frame cadence. The early sample arithmetic proof is not silently extended through the quiet interval; the later sample writer/value stream is separately protected by the comparison.

The [analysis helper](../../../scripts/studies/turbo-outrun/analyze-onset.py) changes only source address **`$10F7: 24→0`**, record 1's onset duration. The [patch receipt](../../../evidence/tel-contrast/onset/patch.json) pins both source and private candidate hashes. The [isolation proof](../../../evidence/tel-contrast/onset/verification.json) verifies exactly all **147** observed pulse-phase control writes changing to saw, preserving their GATE bits. Every other oscillator/filter value, writer order and IRQ attribution remains unchanged across 3,371 stores; the separate sequence of 16,605 volume writer/address/value records is identical. Cross-stream interleaving, exact checkpoint timing and PCM identity are not asserted equal.

The frozen [original-then-without-pulse-onset-23to26s.ab.wav](../../../build/turbo-outrun-onset-listening/original-then-without-pulse-onset-23to26s.ab.wav) contains three seconds of original, half a second of silence, then the same phrase with the pulse phase removed. Context files are [original-26s.wav](../../../build/turbo-outrun-onset-listening/original-26s.wav) and [without-pulse-onset-26s.wav](../../../build/turbo-outrun-onset-listening/without-pulse-onset-26s.wav). These are source interventions, not independent reconstructions or a proposed improved arrangement. Explicit subtune 1, PAL/MOS6581 and unity gain are retained. Window AC RMS is 2,347.77 original versus 2,088.84 diagnostic, with no rail samples; [comparison metadata](../../../evidence/tel-contrast/onset/comparison.json) pins the actual files and levels. A signal difference does not establish an audible improvement.

On 2026-10-14, the listener answered **“I don't hear any difference”**. Preserve the [exact submission](../../../evidence/tel-contrast/onset/listening-submission.json) and separate [scoped review](../../../evidence/tel-contrast/onset/listening-review.json). This means no audible difference detected for this pair; it does not prove identical sound, establish masking as the cause or endorse either arrangement. Do not intensify the effect merely to force a positive answer. No new instrument is promoted, so no new different-material transfer is required.

## Reproduce and close the bounded check

The [cached recipe](../../../config/listening/turbo-outrun-verification.json) automates focused guards, opening census, later capture, duration intervention, rendering, signal checks and comparison. Publish to a fresh directory to preserve submitted auditions:

```sh
python3 scripts/listening-package.py config/listening/turbo-outrun-verification.json --output build/turbo-outrun-verification
python3 scripts/publish-listening.py build/turbo-outrun-verification/run.json --selection scripts/studies/turbo-outrun/audition.json --output build/turbo-outrun-onset-listening-new
```

The [final verified run](../../../evidence/tel-contrast/workflow/run-verified.json) passes 23 focused guards and complete onset removal, including rejection of partial or extra changes. All three published WAVs exactly match its outputs. The [unchanged repeat](../../../evidence/tel-contrast/workflow/run-reused.json) reuses all eight stages in 1.16 seconds with no stage subprocesses; that is a verified recheck, not fresh machine execution. Use a fresh recipe output directory for a fresh capture. Safe canonical receipts and the private lossless logs jointly preserve the analysis without publishing sampled audio.

M2 is complete for these two bounded findings and its listening result. Full Turbo form, specific sample identities by ear, delayed-pitch/glide equivalence and a universal composer signature remain unverified. Preserve Cybernoid's accepted primary programs and their existing conversion constraints. Continue with Monty/Commando.

Model-assistance reviews at intake, first audition, after feedback and before closure all select **no hosted call**. The [Trap calibration](../audio-assessment.md#trap-melodic-motion-and-development-calibration) supports experimental coarse descriptions, not instruction causality, reliable oscillator/sample attribution or subtle paired timbre judgments. Human feedback plus the executed isolation settle the bounded question; model agreement would not establish perceptual benefit. The next review belongs to Monty/Commando's first representative audition under the [standing policy](../audio-assessment.md#use-and-reassess-model-assistance).
