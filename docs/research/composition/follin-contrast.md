# Ghouls and Gauntlet III: bounded instrument contrast

Gauntlet III corroborates two Ghouls mechanisms in an executed contrasting work: a brief noise attack restores a retained tonal pitch and waveform, and a zero pulse default preserves the running PWM word across positive notes. A deliberately edited Gauntlet zero-note rest also preserves the complete PWM trajectory. The selected original Gauntlet passage contains no zero-note rests, so natural rest continuation remains unobserved there. This is a bounded driver/patch finding, not a universal composer style or an individual authorship attribution.

Read the [Ghouls preparation](ghouls-preparation.md), [Follin composer study](../composers/follin-daglish.md), [technique lookup](../technique-index.md) and [execution procedure](../tools/sid-program-analysis.md) for the owning source context and method. The [probe](../../../scripts/studies/gauntlet/probe-contrast.py) reuses the independently implemented [Ghouls numeric helpers](../../../scripts/ghouls_programs.py); it does not reconstruct the Gauntlet score, copy its driver into a backend or replay captured stores.

## Pin and bounded method

| Declaration | Selected source/profile |
| --- | --- |
| Reference | [HVSC Gauntlet III SID](https://www.hvsc.de/download/C64Music/MUSICIANS/F/Follin_Tim/Gauntlet_III.sid), privately installed through the [asset registry](../../../config/local-assets.json) |
| SHA-256 / size | `caec9549f437f6c1a1ee77edc9a034436fb66b2c8ba939adf45b889656c99328` / 6,642 bytes |
| Header credit | Tim & Geoff Follin; retain joint credit and unknown musical roles |
| Selection | Explicit subtune **2** of two; default subtune 1 is not substituted |
| Machine | PAL / MOS6581 / one SID at `$D400`; VBI declaration |
| Native load / init / play | `$AB00` / `$C460` / `$ABB0` |
| Controlled host | `pal-banked`, host `$8000`, exposing RAM beneath BASIC without moving source bytes |
| Execution | Initialization followed by calls **0–1603**; approximately the first 32 seconds |
| Audio | Initialized 32-second mono PCM16 renders at 44,100 Hz, explicit `--subtune 2`, pinned project renderer and libsidplayfp |

The [receipt](../../../evidence/follin-contrast/receipt.json) pins the source, probe, numeric helper and audit dependencies. The original execution matches **10,071** named onset, positive-note setup and PWM contexts, with **17,747** ordered initialization/play stores. The [original contexts](../../../evidence/follin-contrast/original.json.gz) retain full before/after voice state, relevant writer PCs, source parameter reads and ordered stores. The probe checks every admitted observed stage in this window against the reused helpers, rather than inferring motion from one final register snapshot.

These are pre-instruction CPU observations under the controlled callable host. They do not prove SID internal state, exact bus-cycle timing, original-game scheduling, VICE agreement, alternate-note/glide priority, every hypothetical Gauntlet parameter boundary or a complete Gauntlet form. AD/SR preservation below means retained register settings; oscillator and envelope internals are not observed.

## Findings and limits

| Tested claim | Classification | Settling evidence |
| --- | --- | --- |
| A short attack can restore a retained tonal body without rewriting AD/SR. | **Supported across both.** | Gauntlet subtune 2 has **150** noise-to-body restorations: **30** to triangle and **120** to pulse. The selected voice-3 example starts at call 336 and restores after one PAL call, matching the Ghouls delayed-onset mechanism. |
| PWM is a continuing program; a zero pulse default can retain width and phase across positive notes. | **Supported across both.** | Gauntlet voice 1 has **38** retained zero-default note entries from call 768. Widths at calls 784 and 800 remain 640 and 1280 through note setup. The independent PWM helper predicts subsequent carry, direction and reversal state. |
| PWM continues across zero-note rests in this original contrasting passage. | **Unverified as natural source behavior.** | There are **zero** original zero-note rests in calls 0–1603. |
| A deliberately introduced zero-note rest leaves ongoing PWM intact. | **Supported across both through controlled evidence.** | Changing the selected Gauntlet note byte 48 to zero introduces rests at calls 800 and 992. Both reload only rest state; the complete voice-1 PWM store trajectory remains identical, including the next moving body. |
| Every note retains PWM rather than restarting it. | **Contradicted as an unconditional rule.** | **107** Gauntlet note entries visibly reset width when their pulse default is nonzero. Retention depends on the patch contract, as it does in Ghouls. |

The [classified findings](../../../evidence/follin-contrast/findings.json) retain all examples and explicit limits. The same executed transformation can therefore inform Ghouls sound reuse, provided delay, waveform, pitch state, pulse default/restart phase and actual voice/filter constraints remain explicit. Agreement in this related driver family does not attribute the mechanism to Tim alone or establish an accepted sound on different material.

## Causal controls

| Control | Verified intervention and output boundary |
| --- | --- |
| Selected attack delay removed | Change the source operand at `$C28F` from 1 to 0, consumed by the voice-3 delay setter at `$B575` on call 336. This removes only the **six** onsets at calls 336, 344, 352, 360, 368 and 376; another setter at call 384 restores delay 1. The complete ordered score reads and all companion, AD/SR, filter and PWM stores remain equal. Differences are confined to voice 3's frequency/control stores. |
| Stationary pulse | Change the voice-1 pulse step at `$C12D` from 40 to 0 and its zero-default fallback high byte at `$B382` from 0 to 8, selecting useful stationary width `$0800`. These are **two parameters**, not a rate-only freeze. Call 768 still emits the preceding `$00D0` width before the setter; body 769 onward emits `$0800` while PWM remains active. The source disables this PWM program from call 1153. Complete ordered pitch, gate, AD/SR, companion/global stores and score reads remain equal. |
| Controlled rest | Change the selected score byte at `$C145` from 48 to 0. The same source location is visited at calls 800 and 992. This is an edited-score experiment, not a naturally observed rest or a timbral listening diagnostic. |

The [delay-control contexts](../../../evidence/follin-contrast/no-onset.json.gz), [stationary-PWM contexts](../../../evidence/follin-contrast/stationary-pwm.json.gz) and [rest-control contexts](../../../evidence/follin-contrast/rest-control.json.gz) preserve complete observed comparisons. The [receipt](../../../evidence/follin-contrast/receipt.json) records each original/candidate byte and candidate fingerprint. Controlled copies remain private in ignored `build/`; original and derivative SID binaries, WAVs and whole RAM snapshots are excluded from canonical evidence and Git.

For the first attack example, onset delay `$34=1` initializes countdown `$70`, `$37=$80` selects noise, and `$B58C/$B58D=$2800` supplies the attack pitch. The voice's retained frequency state `$58/$5B=$0B30` remains the tonal body. Setup writers `$B158/$B15E/$B165` emit the attack; restoration writers `$AF9D/$AFA2/$AFAD` emit word 2864 and triangle/GATE `$11` at call 337. AD/SR stays `$09/$0F`. Pulse state is independently stored at `$1A/$1B`, with step `$2C` and phase immediate `$AC6A`; writers `$ACAC/$ACB1` precede score processing. These names are analysis labels for the pinned binary, not recovered author symbols.

## Reproduce and listen

The [reusable recipe](../../../scripts/studies/gauntlet/listening.json) executes the original and three controlled copies, checks the named contexts and permitted output differences, renders the original and two timbral controls, checks signal integrity and makes unity-gain A/B windows. It retains the complete original 32-second render alongside each complete controlled 32-second render. The source and its roles remain separately identified; none is an independent Gauntlet reconstruction.

```sh
python3 scripts/setup-project.py --only references --include gauntlet-iii
PYTHONPATH=.tools/test-deps python3 scripts/studies/gauntlet/probe-contrast.py --output build/follin-contrast/proof-new
python3 scripts/listening-package.py scripts/studies/gauntlet/listening.json --output build/follin-contrast/listening-new
PYTHONPATH=.tools/test-deps python3 -m unittest discover -s tests -p gauntlet_contrast_test.py -v
```

The probe requires a fresh output directory below `build/follin-contrast`, supports only selection 2 and allows 817–1604 initialized calls. A scheduled attack restoration beyond a shorter window is recorded as pending at that boundary, not claimed as observed. The optional private-source test verifies the first attack, retained PWM note entries, controlled rests, source immutability and output fingerprints. Without the private reference it skips that executed check, leaving only the data-patch admission guard.

The [exact executed probe](../../../evidence/follin-contrast/probe-executed.py) matches the capture receipt. The current probe only replaces a hardcoded “32-second passage” caption with “selected original passage” so its optional shorter run is accurately described; calculation and verification behavior are unchanged.

Canonical promotion uses the [generic evidence workflow](../../workflows/build-cache.md). The captured receipt pins its original working gzip containers; canonical promotion recompresses JSON. [Archive transport](../../../evidence/follin-contrast/archive-transport.json) maps those original container hashes to identical decoded JSON, while the evidence manifest pins canonical containers. Do not compare a recompressed container directly against the captured container hash or overwrite frozen provenance.

| Audition | Link and question |
| --- | --- |
| Original moving pulse, then stationary `$0800` pulse | [Stable 16–24-second A/B](../../../build/gauntlet-listening/original-then-stationary-pulse.ab.wav), original first, 0.5-second gap, then the two-parameter stationary control. Does the original feel more animated, or is there little difference? |
| Complete original context | [Initialized original subtune-2 render, 32 seconds](../../../build/gauntlet-listening/reference.wav) |
| Complete stationary control | [Initialized stationary-step/fallback diagnostic, 32 seconds](../../../build/gauntlet-listening/stationary-pulse.wav) |
| Selected attack comparison | [Recipe listening index](../../../build/follin-contrast/listening/listening.md): original then selected delay-zero control, 6.4–7.7 seconds. Available, not yet submitted for a listening judgment. |
| Audition identity and signal/window records | [Stable-source manifest](../../../build/gauntlet-listening/sources.json), [retained audition manifest](../../../evidence/follin-contrast/audition-sources.json), [stationary signal check](../../../evidence/follin-contrast/stationary-pwm-signal.json), [stationary window comparison](../../../evidence/follin-contrast/stationary-pwm-comparison.json) |

The listener reviewed the pulse comparison on 2026-10-13: “the original sound more animated, yes: the main voice has this nice "chiptuning" vibe that's lost a bit with stationary-pulse”. The [exact verdict](../../../evidence/follin-contrast/listening-verdict.json) pins the submitted audio, and the [submission record](../../../evidence/follin-contrast/listening-review.json) preserves its original pending state. This supports an audible contribution from the original pulse treatment in this passage. Because both step and stationary fallback width changed, it does not isolate a preferred rate or establish universal superiority of moving pulse. The required bounded corroboration is complete; no new instrument or arrangement is promoted by this diagnostic. The [canonical run receipt](../../../evidence/follin-contrast/run.json) and [working listening index](../../../build/follin-contrast/listening/listening.md) retain the remaining original and controlled outputs without turning an archive excerpt into a complete musical-form claim.
