# Take On Me: source, score and sound preparation

This is the active P1 case in the [study plan](../study-plan.md). [Shared pop/theme intake](pop-theme-preparation.md#sources-and-attribution) retains the HVSC download pin and a-ha composition credit separately from Pascal van Loosbroek’s C64 arrangement. Preserve the source and apply the [independent delivery workflow](../../workflows/decoded-song-workflow.md#deliver-one-musical-case).

The active delivery target is an editable, independently computed reconstruction of this pinned SID arrangement, with its complete introduction/loop boundary, an explicitly authored ending and a familiar-material instrument transfer. Source score and sound behavior remain separate from deliberate arrangement changes. The model audition and complete numeric score proof below are complete. The next gate is an independent player combining editable score and instrument/onset/body behavior, checked against executed state and isolated changes. Preserve pitch/modulation dependencies between score and sound rather than treating the event list as a complete instrument description. Compiled export, an authored finite ending, matched listening and familiar-material transfer remain required.

The source has PAL timing but no declared chip model. Keep that uncertainty in the original header and every reference record. The [explicit model-assumption contract](../../validation/psid-audit.md#keep-an-assumed-sid-model-separate-from-the-header) now permits separate 6581 and 8580 experiments without changing the source. The metadata inspector still reports unknown model and rejected **unassumed** admission; it does not silently choose a chip.

The [bounded experiment receipt](../../../evidence/take-on-me-model/checked/receipt.json) pins the unchanged source, tools and both assumptions. Initialization plus calls 0–63 produce identical CPU ledgers under both assumptions: **5 init and 1,116 play writes**, 375 init cycles, peak 1,205 play cycles and mean 686.171875. Independent headless VICE agrees with all **1,121** stores in each experiment, with maximum cadence error **7 / 9 cycles**. The separate [6581 report](../../../evidence/take-on-me-model/checked/MOS6581/vice/study.json) and [8580 report](../../../evidence/take-on-me-model/checked/MOS8580/vice/study.json) retain the effective model and `sidModelAssumption`; each exported private payload equals the original with its load prefix.

The RAM-only auditor does not synthesize a SID, so equal numeric trajectories are expected across these assumptions and do not establish equal sound. No preferred model, full form, instrument interpretation, original-host equivalence or listening verdict follows. Choose an explicit model for later rendering and compare models audibly where relevant; never promote that choice into archive metadata.

After the pinned download and dependency setup, reproduce both controlled experiments into a fresh directory:

```sh
PYTHONPATH=.tools/test-deps python3 evidence/take-on-me-model/probe.py --output build/take-on-me-model-new
```

The [probe](../../../evidence/take-on-me-model/probe.py) checks source/tool hashes, runs both CPU and VICE comparisons, verifies unchanged payloads, and records exact settings. It retains no original binary or reference audio in the public evidence archive.

## Explicit chip-model audition and working target

The [model recipe](../../../config/listening/take-on-me-models.json) renders the unchanged source with the renderer’s [explicit unknown-model option](../../workflows/audio-workflow.md#render-an-explicit-unknown-model-assumption). Both 32-second renders select #1, PAL, power-on delay zero, libsidplayfp 3.1.1/SIDLite, 44.1 kHz mono PCM16 and unity gain. [Signal checks](../../../evidence/take-on-me-model/listening/audio.json) show nonzero AC signal and no rail samples. [The study receipt](../../../evidence/take-on-me-model/listening/study.json) confirms identical renderer snapshot streams, without claiming that snapshots capture every SID write.

The frozen [MOS6581-then-MOS8580 comparison](../../../build/take-on-me-model-listening/mos6581-then-mos8580-16to24s.ab.wav) contains the same 16–24 second passage under each assumption, with a half-second gap. This window includes all three voice controls and changing routed cutoff in the snapshots; it avoids the sparse opening. Separate context files are [MOS6581](../../../build/take-on-me-model-listening/source-mos6581-32s.wav) and [MOS8580](../../../build/take-on-me-model-listening/source-mos8580-32s.wav). Both are original-source renders, not reconstructions. [Comparison metadata](../../../evidence/take-on-me-model/listening/comparison.json) and [submission hashes](../../../evidence/take-on-me-model/listening/submission.json) preserve the exact presented pair.

On 2026-10-14 the listener answered **“I don't hear any difference”**. The [scoped verdict](../../../evidence/take-on-me-model/listening/review.json) selects **MOS8580 as the explicit working target**, matching the established fallback because no preference was heard. The source header remains unknown. This does not identify the historical chip, establish hardware/model equivalence or accept an independent reconstruction. Existing MOS6581 callable proofs remain labelled numeric experiments; their RAM-only auditor does not synthesize the analog chip.

```sh
python3 scripts/listening-package.py config/listening/take-on-me-models.json --output build/take-on-me-model-listening-work
python3 scripts/publish-listening.py build/take-on-me-model-listening-work/run.json --selection scripts/studies/take-on-me/audition.json --output build/take-on-me-model-listening-new
```

Use a fresh audition directory to preserve reviewed files. The [unchanged recheck](../../../evidence/take-on-me-model/listening/run-reused.json) reuses all five stages in 0.05 seconds with no stage subprocesses; the [preparation run](../../../evidence/take-on-me-model/listening/run-prepared.json) reused existing renders before assembling the chosen window and is not a cold benchmark. First-audition and post-feedback model-assistance reviews decline a hosted call because current calibration does not qualify subtle paired timbre preference. Reassess at the first independent reconstruction audition.

## Complete score form and editable scheduler

The [score model](../../../scripts/studies/take-on-me/score.py) expands [editable orders and semantic rows](../../../evidence/take-on-me-form/score.json) without executing the original CPU or replaying SID writes. The source contains 18 patterns and 460 stored semantic rows. Source addresses label modeled reads for verification; row values and live countdown/order state drive expansion. The [executed probe](../../../scripts/studies/take-on-me/probe-form.py) checks every consumed field and score-return state against the independently expanded model.

The [complete receipt](../../../evidence/take-on-me-form/receipt.json) verifies 8,961 calls: **15,502 score reads, 2,615 note-setup rows and every score-return state**. The score has a **768-call introduction and 4,096-call loop**, with all three orders jumping to byte offset 4 at calls 4,864 and 8,960. No stop is reachable in the pinned score. The [ordered reads](../../../evidence/take-on-me-form/reads.json.gz), [rows](../../../evidence/take-on-me-form/rows.json.gz), [score returns](../../../evidence/take-on-me-form/returns.json.gz) and [original ordered stores](../../../evidence/take-on-me-form/writes.json.gz) retain full observations rather than only counts.

The score repeats before all internal sound state settles. At the return checkpoints, RAM plus A/X/Y/P/SP/PC differs between calls 768 and 4,864 at `$1AD0`, `$1AE1`, `$1AE4` and `$1AE6`; calls 4,864 and 8,960 match. This establishes a settled recurrence in the callable RAM/CPU model, excluding absolute cycles and physical SID/CIA/VIC state. It does not establish repeating audio or a natural finite ending.

| Editable field / command context | Executed meaning and constraint |
| --- | --- |
| `durationUnits` | Stored duration becomes twice the value in the byte countdown; zero takes a complete 256-count traversal. Values 64–127 require an explicit instrument prefix, otherwise their encoding aliases a command. |
| Order repeat and transpose | Repeat applies before order advancement; transpose is a five-bit note offset. Order `$FE` stops, while `$FF` consumes a byte-offset jump target. |
| Pattern arpeggio and instrument | Pattern `$FE` consumes an arpeggio value; an instrument prefix selects the next instrument before the optional duration. Byte meaning depends on the parser position. |
| `glide.stepWord` | A 16-bit frequency delta, low byte at `$1AAE` and high byte at `$1AB1`, not a reload counter. The executed body subtracts/adds both bytes at `$12FD/$1304` and `$131F/$1326`. The pinned natural score has no glide rows; grammar guards are synthetic coverage. |
| Voice order | Each call handles zero-based voices 2, 1, 0. Score setup, continuing sound and shared-filter ownership need separate integration checks. |

An [isolated duration intervention](../../../evidence/take-on-me-form/intervention.json.gz) changes only private-copy byte `$174D` from `$84` to `$85`. Physical voice 2's second onset moves from call 8 to 10; the independent edited score matches the changed execution, while companion score rows and companion/global ordered SID stores remain equal. The original source remains unchanged. [Eight focused guards](../../../evidence/take-on-me-form/guards.txt.gz) cover the contextual grammar, countdowns, repeat, transpose, glide carry and edit isolation.

[Independent headless VICE](../../../evidence/take-on-me-form/vice/study.json) advances from initialization through call 4,868 and observes calls 4,860–4,868 around the first wrap. It matches **165 ordered stores: five init and 160 play**, with maximum cadence error seven cycles against nine allowed. The [trace](../../../evidence/take-on-me-form/vice/trace.json.gz) and [monitor commands](../../../evidence/take-on-me-form/vice/commands.mon) preserve this bounded independent check. It is not a whole-form VICE trace or the original release's boot environment.

```sh
python3 scripts/listening-package.py config/listening/take-on-me-form.json --output build/take-on-me-form-verification
python3 scripts/evidence.py verify --group take-on-me-form
```

The [three-stage recipe](../../../config/listening/take-on-me-form.json) runs grammar guards, complete source/score proof and the VICE wrap check. On 2026-10-14 the [fresh run](../../../evidence/take-on-me-form/run-fresh.json) took 89.13 seconds; the [unchanged recheck](../../../evidence/take-on-me-form/run-reused.json) took 0.19 seconds with all stages reused and no stage subprocesses. Retained evidence verification checks fingerprints without claiming a fresh source capture. The numeric score proof does not yet establish an independent sound player, compiled export or musical acceptance.

## Editable sound programs and isolated controls

The [pure sound helpers](../../../scripts/studies/take-on-me/programs.py) compute note setup, ongoing body behavior and ordered voice/filter output from named state and editable numeric tables. The [source adapter and executed probe](../../../scripts/studies/take-on-me/sound-probe.py) retain source addresses separately. They are study components for integration, not yet an exported instrument bank or a listening-accepted transfer.

| Instrument ID / observed physical voice | Numeric sound contract |
| --- | --- |
| 0 / voices 1 and 3 | Zero control/AD/SR, with continuing numeric pitch and pulse output; do not infer the entire chip is silent. |
| 1 / voice 3 | Pulse `$41`, initial width `$0AC0`, one-way width sweep, delayed vibrato, half-duration gate and late release program. |
| 2 / voice 2 | Saw `$21` with cycling pitch offsets held for two calls per tone, half-duration gate and late release program. |
| 3 / voice 1 | Pulse `$41`, width `$0200`, bidirectional full-word width sweep and shared-filter descent. |
| 4 / voice 1 | TEST/gate onset `$09`, then table-driven `$81 → $41 → $10` noise/pulse/triangle stages with independent high-byte pitch offsets; terminal table hold preserves the final state. |

These roles describe executed programming in the bounded opening, not isolated listening judgments. The named [numeric sound description](../../../evidence/take-on-me-sound/sound-description.json) owns the exact parameters and native frequency table. Preserve its values rather than silently regularizing pitch; source index 32 contains 1,712 while other octaves suggest a slightly different value. A later transfer needs an explicit pitch-mapping check.

At `$1168`, setup selects base frequency, initial pulse/control and ADSR; physical voice 1 alone initializes the shared filter. The continuing body at `$11B3` applies staged control, arpeggio, waveform/pitch tables, PWM, glide or vibrato, voice-1 filter motion, then gate/release rules. Output emits control, pulse high/low and frequency high/low for each voice, then filter low/high. Setup does not itself reset every modulation phase; the score caller and sound helper must retain their separate ownership.

The [bounded receipt](../../../evidence/take-on-me-sound/receipt.json) matches **7,168 executed boundaries over 1,024 initialized calls**: 262 setups, 2,810 continuing bodies, 3,072 voice outputs and 1,024 filter outputs. It covers all five instrument IDs and captures five init plus 18,131 play stores. Each of five private-copy controls independently matches another 7,168 boundaries, for **43,008 comparisons** in total, with changes confined to the declared output ports:

| Control | Source field / edit | Allowed changed output |
| --- | --- | --- |
| Pulse descent | `$168C`: 96 → 48 | Voice 3 pulse width |
| Vibrato delay | `$16AA`: 9 → 5 | Voice 3 frequency |
| Arpeggio offset | `$1660`: 8 → 12 | Voice 2 frequency |
| Percussion waveform | `$1680`: `$81 → $41` | Voice 1 control |
| Filter descent | `$16B6`: high step byte 16 → 8 | Shared filter cutoff |

The [complete baseline contexts](../../../evidence/take-on-me-sound/contexts.json.gz), [data reads](../../../evidence/take-on-me-sound/reads.json.gz) and [ordered writes](../../../evidence/take-on-me-sound/writes.json.gz), together with identically named per-control records in the [manifest](../../../evidence/manifest.json), preserve all observations. These proofs explicitly use experimental **MOS6581** and do not synthesize the chip; the musical target remains **MOS8580** following the audition. Natural glide-body coverage is zero. Synthetic guards cover its contract without asserting natural-source execution.

```sh
python3 scripts/listening-package.py config/listening/take-on-me-sound.json --output build/take-on-me-sound-verification
python3 scripts/evidence.py verify --group take-on-me-sound
```

The [sound recipe](../../../config/listening/take-on-me-sound.json) runs eight pure guards and the separate executed source/control proof, avoiding a duplicate source capture inside the unit-test stage. On 2026-10-14 its [fresh run](../../../evidence/take-on-me-sound/run-fresh.json) took 62.26 seconds and its [unchanged recheck](../../../evidence/take-on-me-sound/run-reused.json) took 0.02 seconds with no stage subprocesses. Full-score integration, compiled execution, acoustic quality and familiar-material reuse remain separate gates.
