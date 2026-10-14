# Tel contrast: Cybernoid II and Turbo Outrun intro

The required [M2 contrast](../study-plan.md#required-contrasting-references-for-the-six-composers) checks the accepted [Cybernoid II primary](cybernoid-ii-preparation.md) against **Turbo Outrun intro, subtune 1**. Source intake and initialized rendering are complete; causal mechanism checks and listening remain open. Preserve the accepted Cybernoid title and [familiar transfer](instruments/cybernoid-decoded-programs.md). This bounded contrast does not require a complete second reconstruction.

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

## Repeatable intake

Use the existing [reference-intake workflow](../../workflows/reference-intake.md) and [Turbo specification](../../../config/reference-intake/turbo-outrun-contrast.json):

```sh
python3 scripts/setup-project.py --only references --include turbo-outrun
python3 scripts/reference-intake.py run config/reference-intake/turbo-outrun-contrast.json --output build/reference-intake/turbo-outrun-contrast
```

The [working listening index](../../../build/reference-intake/turbo-outrun-contrast/listening.md) links a 32-second initialized original and source-only windows at **0–12** and **16–28 seconds**. Settings are explicit subtune 1, PAL/MOS6581, libsidplayfp 3.1.1/SIDLite, power-on delay zero, 44.1 kHz mono PCM16, unity gain and no normalization. The [measurement receipt](../../../evidence/tel-contrast/intake/summary.json) records 1,411,200 frames, peak 9,300, AC RMS 1,839.12 and no rail samples; WAV SHA-256 is `c6edc179b19ff53e20830d0ba80fabcec283aeb103ae1b1baf31534392a87e77`. This establishes captured duration and signal health, not musical quality, complete form or an ending.

On 2026-10-14 the five-stage [first run](../../../evidence/tel-contrast/intake/run-cold.json) completed in 7.93 seconds. An [unchanged recheck](../../../evidence/tel-contrast/intake/run-reused.json) took 0.19 seconds, reusing all five stages after artifact verification. This measures cached workflow execution, not a faster renderer or fresh machine capture.

Renderer register snapshots are observations after rendering iterations. They cannot retain intervening rapid volume writes, identify executed instructions or establish sample absence. A full-machine ledger must settle the initialized host/interrupt contract and sound-path ownership before choosing a causal listening intervention. Do not alter the RSID header to obtain callable admission.

## Bounded questions and completion evidence

| Primary finding | Contrast question | Required evidence |
| --- | --- | --- |
| Cybernoid's staged noise onset and table-driven drums use oscillator programs; a transient can precede a pitched body on the same physical voice. | Which Turbo roles use oscillators and which use a separate rapid audio path? Does the same resource-sharing assumption hold? | Initialized full-machine SID reads/stores with executed writers and source data paths. Rapid volume writes alone cannot distinguish computed synthesis from stored samples or identify every audible drum. |
| Cybernoid separates note age, conditional vibrato wait, glide suppression and retained pitch phase. | Does a selected Turbo tonal passage share one of these articulation/modulation contracts, or require a narrower driver-specific rule? | Executed state transitions for one bounded phrase and a parameter-specific intervention, with protected sound paths checked. Leave untested pitch rules explicitly unverified. |

The next deliverable is an isolated, original-first listening comparison supported by executed evidence, followed by updated reuse constraints. No new instrument is promoted at intake. A new or changed promoted mechanism would require the plan's different-material transfer; existing Cybernoid acceptance remains intact.

Model-assistance review at intake: no call is useful before identifying the causal paths. The [Trap calibration](../audio-assessment.md#trap-melodic-motion-and-development-calibration) supports only experimental coarse descriptions, not instruction causality or reliable oscillator/sample attribution. Review again at the first representative audition, after feedback and before closure under the [standing policy](../audio-assessment.md#use-and-reassess-model-assistance).
