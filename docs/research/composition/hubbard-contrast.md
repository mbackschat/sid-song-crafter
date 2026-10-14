# Hubbard contrast: Monty on the Run and Commando

The required [M3 contrast](../study-plan.md#required-contrasting-references-for-the-six-composers) checks the accepted [Monty primary](monty-preparation.md) against **Commando music, subtune 1**. Source intake is verified; the bounded causal check and its listening diagnostic are in progress. Preserve Monty's accepted first-cycle reconstruction, source-continuation comparison and [familiar transfer](instruments/monty-decoded-programs.md).

## Source, credits and intake

Commando's SID header credits **Rob Hubbard**; the exact [HVSC STIL entry](https://hvsc.c64.org/download/C64Music/DOCUMENTS/STIL.txt) credits **Tamayo Kawamoto's arcade composition** for the selected opening BGM1 and identified later material. These are separate composition and C64 arrangement credits. Archive subtune count does not establish 19 complete musical pieces. STIL's later timestamps remain metadata, not freshly verified form boundaries.

| Item | Verified selection |
| --- | --- |
| Source | [HVSC Commando](https://www.hvsc.de/download/C64Music/MUSICIANS/H/Hubbard_Rob/Commando.sid), asset `commando` in [local assets](../../../config/local-assets.json) |
| SHA-256 / bytes | `5295378dacb06593a9c1853ce11a325ce885a16e26d56274d424e06492948de8` / 4,165 |
| Header | PSID v2, flags `$0014`, PAL, one MOS6581; 19 subtunes, default and explicitly selected #1 |
| Payload / entries | `$5000–$5FC6`; init `$5FB2`, play `$5012`; selected speed bit declares VBI |
| Execution | Existing `pal-banked` callable profile, host `$0400`; controlled calls do not establish original-game IRQ scheduling |
| Metadata pin | [Exact-entry receipt](../../../evidence/hubbard-contrast/intake/stil-entry.json), STIL lines 50466–50493; preserves original bytes locally |

The [source receipt](../../../evidence/hubbard-contrast/intake/source.json) retains attribution and header details. The [reference-intake specification](../../../config/reference-intake/commando-contrast.json) uses existing tools:

```sh
python3 scripts/setup-project.py --only references --include commando
python3 scripts/reference-intake.py run config/reference-intake/commando-contrast.json --output build/reference-intake/commando-contrast
```

The [intake summary](../../../evidence/hubbard-contrast/intake/summary.json) records 128 callable play calls, 1,289 ordered play stores and a maximum 1,248 cycles against the 19,656-cycle PAL frame budget. A separate initialized 32-second source render uses explicit #1, PAL/MOS6581, libsidplayfp 3.1.1/SIDLite, power-on delay zero, 44.1 kHz mono PCM16 and unity gain. It has nonzero AC signal and no rail samples. The [working listening index](../../../build/reference-intake/commando-contrast/listening.md) contains the bounded source and windows at 0–12 and 16–28 seconds; these are not a reconstruction or complete-form comparison.

On 2026-10-14, the [first run](../../../evidence/hubbard-contrast/intake/run-cold.json) took 2.09 seconds; an [unchanged recheck](../../../evidence/hubbard-contrast/intake/run-reused.json) took 0.07 seconds and reused all six stages. Reuse verifies retained inputs and outputs; it is not fresh capture. Original/modified SID files and all source audio remain ignored and local.

## Questions that settle the bounded contrast

| Monty finding | Commando question | Required evidence |
| --- | --- | --- |
| Source sound records encode percussion, pitch and waveform behavior; the opening's dormant drum branch was only covered by synthetic component tests. | Does Commando execute brief noise substitution inside an existing pitched voice, then restore its tone? | Ordered executed stores, source state and a record-level drum-bit intervention with other musical state protected. |
| Pulse width is mutable instrument-bank state, while per-voice phase/direction persists across notes. | Does Commando also carry pulse state across note boundaries, and does its actual arithmetic match Monty's bidirectional full-word PWM? | Executed table mutation, incoming arithmetic state and note-boundary reads; absence in a bounded window does not establish absence throughout the tune. |

[Newman's published analysis](https://www.gamejournal.it/wp-content/uploads/2019/08/GAME_06_HearTheMusic_Journal_Newman.pdf), discussed in the [Hubbard research](../composers/hubbard-galway.md), motivates the percussion-sharing question. It is contextual evidence, not a substitute for tracing this pinned archive. Monty's exact articulation, vibrato, live pitch aliases and late pitch-writer priorities must not be inferred unchanged from a related driver.

Model-assistance review at intake selects no hosted call: existing calibration does not qualify models to establish instruction causality or reliable voice attribution. Reassess at the first representative audition under the [standing policy](../audio-assessment.md#use-and-reassess-model-assistance); models remain experimental supporting signals.
