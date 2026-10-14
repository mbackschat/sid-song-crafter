# Hubbard contrast: Monty on the Run and Commando

The required [M3 contrast](../study-plan.md#required-contrasting-references-for-the-six-composers) checks the accepted [Monty primary](monty-preparation.md) against **Commando music, subtune 1**. The bounded contrast is complete: source intake and causal execution are verified, and the listener heard no difference in the percussion diagnostic. Preserve Monty's accepted first-cycle reconstruction, source-continuation comparison and [familiar transfer](instruments/monty-decoded-programs.md).

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

## Executed percussion substitution and retained pulse state

The [source-specific probe](../../../scripts/studies/commando/probe-contrast.py) uses the existing callable CPU observer, preserving every ordered SID store and its instruction context. Across 512 calls, the [execution receipt](../../../evidence/hubbard-contrast/execution/receipt.json) records 5,245 original stores, 132 note setups, 1,404 continuing bodies and 60 closed tonal/noise/tonal substitutions. Both original and candidate peak at 1,248 cycles. The separate [VICE check](../../../evidence/hubbard-contrast/vice/study.json) matches all six initialization and 1,289 play writes through the first 128 calls; maximum controlled-host cadence error is seven cycles. This corroborates the callable environment, not original-game IRQ timing or renderer-host identity.

Record 7 on voice 1 starts triangle/ring control `$15` at call 0, emits noise `$80` at calls 1–2 and restores `$14` at call 3. Record 1 supplies pulse/noise/pulse substitutions on voices 1 and 2 from calls 24–27. The [ordered contexts](../../../evidence/hubbard-contrast/execution/original.json.gz) retain setup, body, writer and score observations. Noise/restoration does not rewrite AD/SR; GATE is clear in these body controls. This is a shared-envelope sequence, not an independently retriggered drum or an additional voice with its own overlapping tail. The later octave writer can replace the earlier high-frequency store, so final register snapshots alone omit part of the program.

Commando also mutates instrument-bank pulse state, but the observed algorithm differs from Monty's full-word, bidirectional PWM. Record 2's effect bit `$08` selects `$523D` low-byte ADC and writes the changed low byte back into the shared record; its high byte stays unchanged. All 352 observed ADC inputs have carry zero. The independent arithmetic helper includes incoming carry and guards carry-one behavior synthetically; naturally varying carry is not established. Voice 3's first four record-2 onsets read `$0180`, `$01F6`, `$0164`, `$0156`, demonstrating continued mutable pulse state across notes. Note setup skips that call's body. Delay/direction bytes remain zero across the observed onsets: equality verifies this window, not retention of a moving bidirectional phase. No bidirectional PWM store site executes in these 512 calls.

The reusable conclusion is **preserve the scope and ownership of modulation state**, not “all Hubbard instruments use the same PWM.” Shared mutable records can make later onsets depend on earlier execution. Monty's exact articulation, vibrato, pitch lookup and direction behavior remain its own verified contract; this contrast neither replaces its accepted instruments nor introduces a new production backend.

## Controlled diagnostic and listening boundary

The private diagnostic changes only record 7's effect byte at **`$55D0: $05→$04`**, retaining the octave flag. Its SHA-256 is `138ddf406df2f63f90f19454b48521d784dbbc84342d04b5c04316288e21d6e4`. The [causal findings](../../../evidence/hubbard-contrast/execution/findings.json) require the candidate sequence to equal the original after removing exactly 160 record-7 stores from writers `$5321`, `$532E`, `$5333`, including 20 noise-control writes. Every remaining event retains its phase, call, writer, address, value and instrument. Score reads, pulse updates and selected note/phase fields also match. Instruction cycle positions differ because the removed branch costs time; complete hidden-state or PCM equality is not asserted.

Listen to [original-then-without-record7-drum-0to3s.ab.wav](../../../build/commando-drum-listening/original-then-without-record7-drum-0to3s.ab.wav): three seconds original, half a second silence, then the same passage without this instrument's brief percussion phase. Focus on the first half-second in each version, which contains the two affected opening notes. Context is available as [original-10s.wav](../../../build/commando-drum-listening/original-10s.wav) and [without-record7-drum-10s.wav](../../../build/commando-drum-listening/without-record7-drum-10s.wav). This is a diagnostic source intervention, not an independent reconstruction or proposed improvement. Other instruments' percussion remains.

The [submission](../../../evidence/hubbard-contrast/listening/submission.json) pins the frozen audition files; the [comparison](../../../evidence/hubbard-contrast/listening/comparison.json) retains unity gain and unmodified source levels. Both windows have zero rail samples, with AC RMS 3,750.68 original and 3,788.06 diagnostic. Measured signal differences do not establish an audible effect or preference. The [independent review](../../../evidence/hubbard-contrast/execution/review.json) found no blocker for these bounded claims and explicitly retained the unverified internal-state boundary. On 2026-10-14 the listener reported **“no difference”** for the named comparison. The [listening review](../../../evidence/hubbard-contrast/listening/review.json) preserves that verdict separately from execution evidence. This establishes no detected audible difference in this passage, not identical sound, a masking explanation or musical preference. Do not increase the effect merely to obtain a positive verdict.

## Reproduction and next decision

The [recipe](../../../config/listening/commando-verification.json) automates guards, original/candidate execution, source CPU/VICE agreement, rendering, signal checks and the comparison:

```sh
python3 scripts/listening-package.py config/listening/commando-verification.json --output build/commando-probe/verification
python3 scripts/publish-listening.py build/commando-probe/verification/run.json --selection scripts/studies/commando/audition.json --output build/commando-drum-listening-new
```

Use a fresh output beneath `build/commando-probe/` for fresh execution and a fresh audition directory to preserve submitted files. The [verified run](../../../evidence/hubbard-contrast/workflow/run-verified.json) completed eight stages in 9.76 seconds, including six focused guards; the [unchanged repeat](../../../evidence/hubbard-contrast/workflow/run-reused.json) took 0.32 seconds with every stage reused and no stage subprocesses. Canonical compressed observations preserve analysis without SID payloads or audio. The manifest owns hashes and restoration paths.

The first-audition model review selects no hosted call: the current calibration does not establish reliable subtle paired timbre judgment, and a model cannot resolve the causal question better than the verified intervention. The post-feedback and closure review also selects no call: the human verdict plus causal isolation settles this check without establishing perceptual editing value. M3 is complete for its declared bounded scope; no new instrument is promoted, so a new different-material transfer is unnecessary. Continue with Take On Me and review model usefulness at its first representative audition. Full Commando form, unselected subtunes and a universal composer signature remain outside this check.
