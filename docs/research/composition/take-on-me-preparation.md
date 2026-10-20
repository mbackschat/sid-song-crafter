# Take On Me: source, score and sound preparation

This is the completed P1 case in the [study plan](../../PLAN.md), closed for its declared scope on 2026-10-14. [Shared pop/theme intake](pop-theme-preparation.md#sources-and-attribution) retains the HVSC download pin and a-ha composition credit separately from Pascal van Loosbroek’s C64 arrangement. Preserve the source and apply the [independent delivery workflow](../../workflows/decoded-song-workflow.md#deliver-one-musical-case).

The completed delivery is an editable, independently computed reconstruction of this pinned SID arrangement, with its complete introduction/loop boundary, an explicitly authored ending and a familiar-material instrument transfer. Source score and sound behavior remain separate from deliberate arrangement changes. The model audition, complete independent numeric integration and compiled SID/PRG delivery below are verified. The listener reports no audible difference in the reconstruction phrase and ending comparisons. The matched familiar-material transfer is also accepted for instruments, balance and ending.

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

Use a fresh audition directory to preserve reviewed files. First-audition and post-feedback model-assistance reviews decline a hosted call because current calibration does not qualify subtle paired timbre preference. Reassess at the first independent reconstruction audition.

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

The [recipe](../../../config/listening/take-on-me-form.json) runs grammar guards, complete source/score proof and the VICE wrap check. Retained evidence verification checks fingerprints without claiming a fresh source capture. The numeric score proof does not establish an independent sound player, compiled export or musical acceptance; those have separate evidence below.

## Editable sound programs and isolated controls

The [pure sound helpers](../../../scripts/studies/take-on-me/programs.py) compute note setup, ongoing body behavior and ordered voice/filter output from named state and editable numeric tables. The [source adapter and executed probe](../../../scripts/studies/take-on-me/sound-probe.py) retain source addresses separately. They are study components for integration, not yet an exported instrument bank or a listening-accepted transfer.

| Instrument ID / observed physical voice | Numeric sound contract |
| --- | --- |
| 0 / voices 1 and 3 | Zero control/AD/SR, with continuing numeric pitch and pulse output; do not infer the entire chip is silent. |
| 1 / voice 3 | Pulse `$41`, initial width `$0AC0`, one-way width sweep, delayed vibrato, half-duration gate and late release program. |
| 2 / voice 2 | Saw `$21` with cycling pitch offsets held for two calls per tone, half-duration gate and late release program. |
| 3 / voice 1 | Pulse `$41`, width `$0200`, bidirectional full-word width sweep and shared-filter descent. |
| 4 / voice 1 | TEST/gate onset `$09`, then table-driven `$81 → $41 → $10` noise/pulse/triangle stages with independent high-byte pitch offsets; terminal table hold preserves the final state. |

These roles describe executed programming in the bounded opening, not isolated listening judgments. The named [numeric sound description](../../../evidence/take-on-me-sound/sound-description.json) owns the exact parameters and native frequency table. Preserve its values rather than silently regularizing pitch. At the declared PAL clock, `frequencyWord × (17734475 / 18) / 2^24` gives 423.821 Hz for index 57 (word 7,217), about 64.86 cents below A440 if index zero maps to MIDI 12. Index 32 contains 1,712 and is about 55.72 cents below that equal-tempered mapping, so the offset is not perfectly uniform. These are measured table consequences, not evidence of the arranger’s intended clock. Preserve them in the title; a familiar transfer should explicitly retune both its plain reference and candidate to the same declared pitch standard, recording that adaptation.

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

The [sound recipe](../../../config/listening/take-on-me-sound.json) runs pure guards and the separate executed source/control proof, avoiding a duplicate source capture inside the unit-test stage. Full-score integration, compiled execution, acoustic quality and familiar-material reuse have separate evidence below.

## Complete independent numeric player

The [portable composition](../../../evidence/take-on-me-player/composition.json) combines editable score rows, numeric sound programs, declared PAL/MOS8580 target, mix settings and a named initial sound image. The [independent player](../../../scripts/studies/take-on-me/player.py) computes its stores without original driver code, source-address reads or captured-event replay. Source addresses and provenance do not affect synthesis. Score state owns remaining duration, base note, glide step/target and arpeggio selection; sound owns live modulation phases and glide completion. Project score-owned fields into every voice at the call boundary, including voices whose sound stage is skipped by a stop. Otherwise the returned named state can disagree with its own score countdown even when the emitted stores look correct.

The [integration receipt](../../../evidence/take-on-me-player/receipt.json) matches **159,083 ordered init/play stores and all 8,961 score-return states** across the introduction and two loop traversals. It also matches all **7,168 named sound boundaries over calls 0–1,023**, and reproduces the four later RAM-field changes at 768 → 4,864 and no changes at 4,864 → 8,960. These are distinct coverage levels; matching complete stores does not assert complete hidden sound-state observation on every later call.

The [checker](../../../scripts/studies/take-on-me/check-player.py) verifies canonical artifact/source/tool fingerprints, freshly captures initialization, and rechecks retained full execution rather than rerunning the unchanged original for every integration edit. It reproduces the private-copy hashes and independently computes the earlier duration control (2,227 stores over 128 calls, companion/global stores protected) and pulse-step control (18,136 stores and 7,168 contexts over 1,024 calls, only voice-3 pulse ports changed). [Complete computed stores](../../../evidence/take-on-me-player/writes.json.gz), [returns](../../../evidence/take-on-me-player/returns.json.gz), [contexts](../../../evidence/take-on-me-player/contexts.json.gz) and [control results](../../../evidence/take-on-me-player/controls.json.gz) retain the detailed results.

```sh
python3 scripts/listening-package.py config/listening/take-on-me-player.json --output build/take-on-me-player-verification
python3 scripts/evidence.py verify --group take-on-me-player
```

The [integration recipe](../../../config/listening/take-on-me-player.json) includes [stop-state guards](../../../evidence/take-on-me-player/guards.txt.gz) that independently expose and prevent stale projection. The [executed integration proof](../../../evidence/take-on-me-player/run-executed.json) computes the player anew against retained whole-source execution; it is not a fresh full source capture. Compiled export, finite ending and listening comparisons have separate evidence below.

## Compiled export and complete listening package

The [editable title](../../../songs/studies/take-on-me-reconstruction/README.md) preserves the source introduction and first complete loop at calls 0–4,863, then adds a declared 32-call held release and stop. The source restarts indefinitely; our finite ending is an arrangement choice. The [compiler contract](../../workflows/decoded-song-workflow.md#take-on-me-runtime-score-and-sound-programs) documents runtime score/program tables, shared state ownership, reset, caller decimal-mode handling and the explicit PAL/MOS8580 limit. No original driver instructions or captured-write replay enter the export.

The [complete compiled proof](../../../evidence/take-on-me-compiled/candidate/verification.json) covers **4,961 calls, 86,309 ordered stores and 4,962 named init/play boundaries**, with maximum play cost **1,946 of 19,656 cycles**. The 6,442-byte payload has 109 bytes of cold mutable state. Poisoned-state reset and the actual standalone PRG's SYS 2061 bootstrap pass; the latter uses modeled raster/CIA reads, not real VICE autostart. A strict shared-host `init_return` label also marks its recurring wait loop: observe cold initialization only on the first visit, then compare later playback boundaries against progressed state. Entry `CLD` makes score arithmetic independent of the caller's decimal flag; a set-D transposed-note guard reproduces the otherwise incorrect arithmetic.

The [source-prefix proof](../../../evidence/take-on-me-compiled/source-prefix.json) matches all **86,302 source stores** through call 4,863, excluding exactly seven authored ending stores. The separate [full VICE proof](../../../evidence/take-on-me-compiled/vice/study.json) covers all 86,309 candidate stores through call 4,960, with maximum cadence error **5 cycles** against the 9-cycle tolerance. Complete [CPU writes](../../../evidence/take-on-me-compiled/candidate/writes.json.gz), [named checkpoints](../../../evidence/take-on-me-compiled/candidate/state-checkpoints.json.gz) and [VICE trace](../../../evidence/take-on-me-compiled/vice/trace.json.gz) preserve the evidence; original/reference binaries and audio remain local.

Both 100-second renders use PAL, subtune 1, MOS8580 and unity gain. Only the original needs an explicit unknown-model assumption; the candidate declares 8580. [PCM checks](../../../evidence/take-on-me-compiled/audio.json) find no clipping and a settled final candidate second with AC RMS zero; the DC value is reported separately. [Pre-stop measurements](../../../evidence/take-on-me-compiled/ending-measurements.json) find AC RMS about 1.60 PCM units immediately before the first zero-volume snapshot at 97.696 seconds, supporting a quiet tail before muting. These measurements do not establish a natural musical ending or audible fidelity.

Reproduce and publish with the existing runners:

```sh
python3 scripts/listening-package.py config/listening/take-on-me-full.json --output build/take-on-me-full-work
python3 scripts/publish-listening.py build/take-on-me-full-work/run.json --selection config/listening/take-on-me-full.audition.json --output build/take-on-me-listening
python3 scripts/evidence.py verify --group take-on-me-compiled
```

Publication requires a fresh destination. The [fresh recipe](../../../evidence/take-on-me-compiled/run.json) took **47.41 seconds** on 2026-10-14; its [fingerprint-verified repeat](../../../evidence/take-on-me-compiled/repeat-run.json) took **0.66 seconds** with all eleven stages reused. Renderer consoles retain the chip/clock/subtune confirmation. The complete model comparison and title-delivery recipes remain different evidence scopes.

The [frozen submission](../../../evidence/take-on-me-compiled/listening/submission.json) binds the listening files to this run. On 2026-10-14 the listener answered **“I don't hear any difference”** for the representative phrase. The [scoped review](../../../evidence/take-on-me-compiled/listening/phrase-review.json) accepts its sound and phrasing; it does not establish PCM identity, whole-song listening, ending or transfer acceptance. For the ending comparison the listener also answered **“I don't hear any difference”**; the [ending review](../../../evidence/take-on-me-compiled/listening/ending-review.json) retains the authored stop with no reported objection. The source restart and candidate stop remain structurally different. The familiar transfer is separately accepted below:

- [Representative phrase](../../../build/take-on-me-listening/phrase-reference-then-ours.ab.wav): 16–32 seconds of each, original first, then ours; assess sound and phrasing.
- [Ending](../../../build/take-on-me-listening/ending-reference-then-ours.ab.wav): 85–100 seconds of each, original first, then ours; the reference restarts, while our authored release ends playback.
- Full [reference](../../../build/take-on-me-listening/reference.wav) and [reconstruction](../../../build/take-on-me-listening/reconstructed.wav); optional [opening](../../../build/take-on-me-listening/opening-reference-then-ours.ab.wav).

Model-assistance review at this first independent audition (2026-10-14): no model call. The questions are fine sound/phrasing preservation and natural decay, outside the [measured models' supported scope](../audio-assessment.md#use-and-reassess-model-assistance). CPU/VICE comparisons and PCM measurements answer the technical questions; the listener retains musical judgment. Reassess after feedback or revision and at closure, including whether a specifically calibrated descriptive probe would resolve a remaining question.

Model-assistance review after phrase feedback (2026-10-14): no call; a model agreement check would not add validated fine-fidelity evidence to this human verdict. The ending feedback likewise identifies no defect for a model to resolve; the next checkpoints are transfer feedback and case closure.

## Familiar transfer and case closure

The [accepted tonal-program card](instruments/take-on-me-decoded-programs.md) owns the same 53-note Für Elise transfer, exact editable workfiles, preparation limits, complete CPU/VICE/render evidence, reuse outcome and listening verdict. On 2026-10-14 the listener answered **“they work musically”** for its instruments, balance and ending. Both generated versions use A440 tuning; the original title’s native tuning remains intact. The source saw/arpeggio and percussion programs are reconstructed, but this reuse acceptance applies to the selected pulse lead/replies and filtered pulse bass.

P1 is complete for the pinned C64 arrangement's introduction plus first complete loop, deliberate finite ending and matched familiar-material instrument transfer. Human phrase/ending feedback, complete execution proofs, reproducible recipes, source fingerprints and reusable sound documentation are retained. This does not claim the full a-ha studio recording, every possible loop repetition, historical chip identification, hardware playback, NTSC export support for this backend or a generally validated musical-judge model. Proceed to Billie Jean under the plan's existing order.

Closure model review (2026-10-14): all required checkpoints are accounted for. No model call would resolve an outstanding musical question; current calibration does not qualify fine reconstruction fidelity, balance or natural endings. The listener's accepted verdicts remain authoritative. Review model usefulness at Billie Jean's first representative audition, after feedback/revision and at closure.
