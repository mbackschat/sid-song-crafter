# Flashdance preparation

Use DRAX's **Flashdance (conversion)** as the studied reference for **What a Feeling**. Its staged lead, evolving bass and moving chord extend the mechanisms learned from the positively received [independent Elise trio](../../../songs/studies/drax-full-reconstruction/README.md). The accepted reconstruction covers calls 0–1537 plus an authored ending; the original transfer phrase was judged to work, while the revised dual-SID arrangement is accepted in raw stereo. The existing [20-second preview](../../../.local/research/flashdance/drax.preview.wav) provides reference context.

## Pinned evidence

The [reference study](flashdance-reference.md) owns attribution, cached [HVSC STIL](https://www.hvsc.de/download/C64Music/DOCUMENTS/STIL.txt) identity and the [archived SID](https://www.hvsc.de/download/C64Music/MUSICIANS/D/DRAX/Worktunes/Flashdance_conversion.sid): DRAX, `1990 Vibrants`, one PAL MOS6581, default subtune 1. Pinned local SHA-256: `2f5216ab8f4438d8ef20c0153ce4671afbc5bc6e66d3b0984bb112fdbf46794c`.

The retained [frames](../../../build/reference-studies/drax/flashdance.frames.json) and [ordered writes](../../../build/reference-studies/drax/flashdance.writes.json) cover 6,000 calls. Their diagnostic adapter permits only the pinned initialization's two zero paddle-register writes; this is not a production-auditor pass or a complete-song coverage claim.

| Opening observation | Difference from decoded Elise |
| --- | --- |
| Bass: TEST at call 2, noise `$C4E0/$81` at 3, pitched pulse at 4, gate clear at 5; AD/SR `$02/$5F`; width advances `$40`. Cutoff descends 1280→832→512→384→256. | Different envelope, narrower step and several filter stages; retain the releasing body. |
| Lead: triangle at 3, saw at 4–5, pulse from 6. Width rises `$70`, reverses, then changes to `$10` descent at 12. Pitch first moves by 79 at 30. | Waveform staging and changing PWM rate replace the simple pulse lead; modulation needs its own decoded contract. |
| Chord: B-flat3/D4/F4/B-flat4, two calls per tone, plain pulse and width movement `$0D` per opening call. | Four-tone moving pulse replaces the fixed-width triangle/pulse triad. |

These initial measurements motivated the executed mechanism studies below. The editable programs now compute their state transitions; sound quality and successful musical reuse remain separate questions.

## Selected form and ending contract

The single-SID deliverable covers **one complete recurring score cycle of the selected DRAX arrangement**, including startup: calls **0–1537**, followed by an independently authored ending. A fresh 6,500-call diagnostic execution on 2026-10-13 reproduces the retained [form evidence](../../../build/flashdance-f1-f2/score-form.json) exactly. The score starts at call 2 and repeats at call 1538: 1,536 calls, approximately 30.64365 seconds at the pinned PAL cadence. The two startup calls and the eventual ending are additional duration; call positions are not exact WAV timestamps.

All three voices advance through six synchronized blocks. Pattern identifiers describe executed driver structure; the published-source comparison below supplies the musical section map.

| Block | Inclusive calls | Bass pattern | Lead pattern | Chord pattern |
| --- | --- | --- | --- | --- |
| 1 | 2–257 | 1 | 2 | 3 |
| 2 | 258–513 | 5 | 4 | 6 |
| 3 | 514–769 | 1 | 7 | 3 |
| 4 | 770–1025 | 5 | 8 | 6 |
| 5 | 1026–1281 | 10 | 9 | 11 |
| 6 | 1282–1537 | 12 | 13 | 14 |

PC `$128F` restores all three track pointers at call 1534; PC `$1134` selects the first patterns again at 1538. Cutting at pointer restoration would truncate the final block. Restores at 3070, 4606 and 6142 corroborate the period, and the first two cycles agree in executed pattern selections and consumed note/hold/off commands. This establishes recurring score structure, not identical oscillator, envelope, filter or modulation state between cycles.

**Source coverage:** the [licensed Hal Leonard piano/vocal/guitar preview](https://www.virtualsheetmusic.com/score/HL-4939.html), crediting Giorgio Moroder's music and Keith Forsey/Irene Cara's lyrics, and [Martin Seiler's 2015 HELBLING SMATB sample, HI-C7727](https://www.helbling.com/sites/default/files/media/documents/C7727_DEMO_C7727_Flashdance%20What%20a%20Feeling_SMATB_sample.pdf) support this map:

| Selected span | Inclusive calls | Published-source correspondence | DRAX harmony |
| --- | --- | --- | --- |
| Startup and opening variation | 0–513 | Two startup calls, then the four-bar introduction's harmonic span. | B-flat–F/A–C minor–G minor/D |
| Verse fragment | 514–1537 | First eight bars of Verse 1, published bars 5–12. | B-flat–F/A–C minor–G minor/D–E-flat–B-flat–A-flat–Fsus4→F |

The [comparison receipt](../../../build/flashdance-original-form/source-form-comparison.json) retains 13 executed chord witnesses, six melody anchors and source/download hashes. Landmarks include D4 at 514, G4 at 1034, F4 at 1154 and E-flat4→D4→C4 at 1282/1306/1314. DRAX adds chromatic approaches and changes voicing, phrasing and the published final E-flat/F→F harmony to Fsus4→F.

**Omissions and limits:** the loop returns before Verse 1's remaining eight bars; later verses, choruses and instrumental/outro development have no separate passages. Bar labels belong to Seiler's edition. Original-recording timestamps, exact introduction identity and version-specific ending remain unverified. No selected SID block is omitted; this deliverable remains an abbreviated DRAX arrangement. Its [listening verdict](#independent-export-and-listening) applies to that selected scope.

**Authored ending:** preserve the reference through call 1537 and suppress the next score cycle. The editable model clears gate from call 1538 while continuing modulation, retains 64 release calls, then lowers volume every four calls. Volume reaches zero at call 1658; from call 1666 it repeatedly clears control and volume. This is an arrangement change after the comparison span, not an ending found in the source. Export execution, settled audio and the listener's acceptance verify this ending for F4.

The local form-analysis entry point and its tests remain deferred, untracked work. The retained evidence pins tool SHA-256 `6e0bbd4e08056c5b04426cedad194e1d5d62accb0e53b08d47d2efd94822fd55`; reproducing that form receipt still requires the local tool. Its six tests passed on 2026-10-13. Portable instruction tracing is separately supported by [trace-sid-program.py](../../../scripts/trace-sid-program.py) with its explicit pinned `flashdance-diagnostic` profile; it does not depend on the deferred tool. The retained opening traces match all 9,345 initialization and calls 0–513 sound-register writes in the cached reference oracle. These checks establish analysis evidence, not listening acceptance.

## Executed feasibility findings

A bounded execution study of the pinned binary identifies requirements beyond the Elise backend:

| Mechanism | Executed evidence and consequence |
| --- | --- |
| Same-call restart | Instrument initialization writes AD `$00`, SR `$0F`, TEST `$08` at PCs `$12D3/$12D8/$12DD`, followed by actual ADSR and TEST/GATE `$09` at `$1374/$1380/$1385`. Do not impose Elise's two preceding preparation calls. |
| Different body writer | PCs `$15F7–$1618` write pulse width, shared cutoff, frequency and control. ADSR belongs to initialization rather than being reasserted every body call. |
| Staged lead | Instrument offset `$10` selects AD/SR `$03/$3C`, triangle→saw→pulse stages and a looping body. PWM begins at `$D00`, bounds high `$A/$F`, step `$70`; a later row changes the step to `$10` without resetting width. Preserve row transitions and state, not just extrema. |
| Moving chord variants | Initializers at calls 2/130/258/386 select four chord programs. The opening has offsets `[0,0,4,4,7,7,12,12]`, AD/SR `$03/$34`, width `$040` and step `$0D`. Describe the four-tone cycle independently from the score note. |
| Per-voice fine tuning | PC `$14FB` adds the table `$1762,X` value: 0/1/2 for bass/lead/chord. The opening lead `$2710` becomes `$2711`; chord `$0F82` becomes `$0F84`. Preserve the exact programmed words alongside their musical interpretation. |

The first four-chord turn, calls 0–513, is the [plan's first reconstruction milestone](../study-plan.md#flashdance-next-executable-milestones). The contracts below refine the score and PWM requirements. The complete selected score, waveform/pitch, PWM and filter programs now have an editable description; the pinned diagnostic adapter retains the production auditor's strict I/O boundary.

### Editable full-span model

The [portable composition](../../../songs/flashdance-decoded.json) separates musical commands, instrument programs, retained startup state and nonexecuting `sourceEvidence`. The [pinned score decoder](../../../scripts/describe-flashdance-score.py) checks two executed score cycles; the [program model](../../../scripts/flashdance_programs.py) computes waveform selection, absolute/relative pitch, PWM and the shared filter. The [scheduler](../../../scripts/flashdance_player.py) handles same-call restarts, legato changes, instrument-owned release, delayed SR writes and the authored ending without reading reference bytes during playback. See [reproduction and editable controls](../../workflows/decoded-song-workflow.md#flashdance-description).

On 2026-10-13, the independently scheduled Python model matched **all 27,905 ordered sound-register writes**, including initialization and calls 0–1537, against the pinned original execution. The [receipt](../../../build/flashdance-computed-model/receipt.json) identifies the serialized input. The score/program/pitch/scheduler guards cover parameter interventions, source-read isolation, changed-note execution, JSON round-trip verification and release/fade behavior. The original writes remain a comparison oracle; the composition contains semantic programs and commands rather than per-call register playback.

The shared filter advances only when its declared owner runs; companion voices repeat the retained cutoff write in the original voice order. Its rows carry independent lower/upper bounds, step, duration, optional reset and hold. Unlike PWM's equality reversal, the filter reverses upward at or above the upper bound and downward below the lower bound after byte arithmetic. The [executed program guards](../../../tests/flashdance_programs_test.py) compare all selected transitions and isolated boundary interventions against the original routines.

### Independent export and listening

The [compiler](../../../scripts/compose-flashdance.py) generates semantic score records and program tables for our [6502 scheduler](../../../songs/players/flashdance.asm), [instrument routines](../../../songs/players/flashdance-programs.asm) and [pitch routines](../../../songs/players/flashdance-pitch.asm). It reads the portable description and our source templates, with no reference-driver instructions or captured-register playback. The [compiler guards](../../../tests/flashdance_compiler_test.py) verify changed pitches/PWM, repeated initialization, zero-page preservation and all-register model equality through the ending.

The [full export](../../../build/flashdance-independent-full/reconstructed.sid) independently matches all 27,905 reference initialization/music writes. Its [reference comparison](../../../build/flashdance-independent-full/reference-comparison.json) also records the remaining timing difference: candidate-minus-original instruction-start offsets range from −235 to +418 cycles. Equal call/address/value/order does not imply equal SID bus timing, oscillator phase or analog sound.

The [corrected CPU audit](../../../build/cpu-timing-correction/flashdance-single.audit.json) covers 1,667 calls with a maximum of 2,231 cycles per call against the 19,656-cycle PAL budget. The [headless VICE check](../../../build/flashdance-independent-full/vice/study.json) independently matches all 30,203 playback writes through the first fully muted call, with at most five cycles of harness polling jitter. Its controlled harness disables IRQs, sprites and display DMA; this is not the reference's original machine environment. The [shared CPU timing correction](../../validation/cpu-timing.md) supersedes the older audit's cycle costs without changing the exported SID, register values/order or accepted audio.

Both 35-second renders use the same PAL MOS6581, default subtune, libsidplayfp 3.1.1/SIDLite, mono PCM16 at 44.1 kHz and unity gain. Neither is individually normalized. The [audio receipt](../../../build/flashdance-full-listening/audio-evidence.json) records no clipped samples and zero AC RMS in our final half-second. The reference begins its next loop; our export releases, fades and stops.

- [Opening comparison: reference, half-second gap, ours](../../../build/flashdance-full-listening/opening-reference-then-ours.wav): 10.5 seconds per side, rendered from initialization.
- [Complete selected reconstruction with authored ending](../../../build/flashdance-full-listening/reconstructed.wav).
- [Reference at the same gain and duration](../../../build/flashdance-full-listening/reference.wav).

**Listening verdict, 2026-10-13:** when asked whether the reconstruction preserves the sound/phrasing and whether its ending feels natural, the listener replied **“yes, quite good.”** This accepts the delivered opening comparison and complete selected reconstruction with its ending, closing F3/F4. It does not assert perceptual indistinguishability, physical-hardware equivalence or acceptance of the separate transfer and dual-SID arrangements.

### Score changes, restarts and gate ownership

The [opening score inventory](../../../build/flashdance-opening-score-review/inventory.json) retains source-addressed commands and executed instruction witnesses for calls 0–513. Voice 1 consumes 13 note commands and restarts on each; voice 2 consumes 12 notes but restarts only ten times; voice 3 consumes four notes and restarts on each. Startup calls 0–1 consume no score commands, although the synthesis body runs from preloaded state.

| Role | Selected instrument record offset | Opening distinction |
| --- | --- | --- |
| Bass | `$00` | All 13 notes use the same instrument; there is no score-off command in this passage. |
| Lead | `$10` | Notes at calls 102 and 274 change pitch while suppressing restart. Score-off begins at 478 and repeats every four calls through 510. |
| Chord | `$18/$20/$28/$30` at calls 2/130/258/386 | The four records share ADSR and PWM; their wave/pitch program offsets are `$10/$19/$22/$2B`. |

The duration/control byte `$80` clears restart suppression, whereas `$90` sets it to `$10`; both load duration value 3 at `$1195–$11A4`, producing four-call score rows. On the two lead `$90` notes, `$114B` changes the score pitch and `$1166` restores gate mask `$FF`, but `$12AD–$12C3` skips the initializer and enters the ongoing body at `$138B`. Preserve waveform/PWM position across these note changes. A hold `$7E` also continues the body; score-off `$00` instead sets gate mask `$FE` through `$116C–$1178`. The final control writer at `$1615/$1618` applies that mask.

Instrument release is separate: at bass call 5, `$150C` reads waveform/control `$40` from `$197D`; the gate mask is still `$FF`, so the instrument program itself clears gate. Also distinguish the score effect `$C0` from note-off: it selects `$82/$00`, scheduling SR `$00` two calls later via `$123D/$1243` and `$10F1–$1101`. At lead call 96, that SR write occurs while control remains `$41`. Conflating these commands would change articulation and envelope evolution.

Two pitch controls are present. `$C1` selects `$60/$42`, initializing pitch-relative vibrato with interval 4, shift 2 and cleared phase/accumulators; the next note decrements its enable state at `$1153`. `$C2` selects `$10/$28` at lead call 262, enabling an accumulating `$28` pitch increment on calls 262–273; note 274 cancels that state at `$115B` despite suppressing the instrument restart. Command meanings here apply only to the executed branches of this pinned driver.

The independent [pitch-effect model](../../../scripts/flashdance_pitch.py) computes slide and vibrato from editable state. Vibrato uses the adjacent frequency-table difference at the untransposed score note, adds its evolving depth to the difference's high byte, then shifts it. Counter decrement precedes the sign-bit check: the opening interval 4 starts with counter 3, giving three ascending updates before the first reversal and five updates between subsequent reversals. Slide has priority; it continues accumulating on an absolute-pitch waveform step even though its offset is not added to that step. A note decrements enabled effects without clearing their phase or accumulated offset.

The [pitch guards](../../../tests/flashdance_pitch_test.py) cover cancellation, priority, absolute pitch, byte/word wrap and the asymmetric first vibrato half-cycle. On 2026-10-13, the model matched all 1,515 original pitch-effect body transitions in calls 0–513, including output pitch and retained state. Each comparison starts from the original routine's entry state; the [full-player comparison](#independent-export-and-listening) separately verifies independent scheduling.

### PWM state and row transitions

PCs `$138B–$141A` operate on per-voice state at these base addresses plus voice index `X`: lower reversal high byte `$1731`, upper reversal high byte `$1734`, step `$1737`, direction `$173A`, row offset `$173D`, remaining calls `$1740`, and width low/high `$1743/$1746`. Direction zero adds the unsigned step; nonzero subtracts it. Both operations carry/borrow across the full two-byte state. After movement, the new high byte is compared for **equality** with the relevant reversal byte; equality toggles direction. Neither clamping nor a greater-than/less-than crossing test reproduces this code.

Each row at `$1B7B + offset` occupies four bytes:

| Byte | Executed meaning |
| --- | --- |
| 0 | High nibble is the lower reversal high byte; low nibble is the upper reversal high byte. |
| 1 | Unsigned movement step. |
| 2 | Low six bits reload the remaining-call counter. Bit 7 resets width and direction; bit 6 retains the row offset, otherwise it advances by four. |
| 3 | Packed reset width: low byte is `value & $F0`, high byte is `value & $0F`. Thus `$0D` means `$D00`, `$40` means `$040`, and `$01` means `$100`. Used only when bit 7 requests a reset. |

At routine entry, a nonzero counter is decremented; a zero counter consumes a row. Both paths then move the width on that same call. A row loading counter 8 therefore moves on its load call and on eight following countdown calls; the next row is consumed on the tenth call. The opening attack row is consumed at call 3 and its successor at 12. The successor's `$4F` flags retain width, direction and row offset, with a reread every 16 calls. This permits the lead to change its step from `$70` to `$10` while retaining its descending motion.

| Role | Initial width | Lower / upper reversal high bytes | Attack / following step |
| --- | --- | --- | --- |
| Bass | `$100` | `$4 / $F` | `$40 / $40` |
| Lead | `$D00` | `$A / $F` | `$70 / $10` |
| All four chord variants | `$040` | `$1 / $F` | `$0D / $0D` |

The initializer at `$12E9–$130A` selects the first row, clears its counter and sets packed width if requested; it does **not** load bounds/step or reset direction. That happens when the next body call consumes the row. The initializer exits before PWM movement and pulse-register writes. For a concrete arithmetic check, lead call 7 advances `$EC0 → $F30` and reverses on high byte `$F`; call 51 descends `$B00 → $AF0` and reverses on `$A`. These are high-byte reversal bands, not exact pulse-width endpoints. Bass movement continues after its instrument-owned gate release.

The [bounded PWM probe](../../../build/flashdance-opening-pwm-review/probe.py) independently calculates each routine transition from its observed entry state. On 2026-10-13, all 1,515 transitions across calls 0–513 matched fresh CPU execution; six isolated interventions on RAM copies confirmed equality-only reversal and 16-bit wrap. The [receipt](../../../build/flashdance-opening-pwm-review/probe.json) preserves the state comparisons and interventions. This is a one-step mechanism check using original execution state, not an independently scheduled instrument, complete synthesis model or listening verdict.

## Description → library → our code

Decode one chosen phrase from initialization, including silent preparation. Retain exact frequency words, initializer/off calls, attack stages, PWM arithmetic, vibrato phase/delay, arpeggio dwell, release evolution and shared-filter write order. Keep score events separate from instrument-owned gate closure. Promote each verified mechanism into an editable library card with provenance, constraints, demonstration and listening verdict; then implement it in our computed engine. Include neither the original driver nor captured-register playback. Require ordered-write equality and independent VICE execution for the single-SID reconstruction before arrangement changes.

## Deliberate dual-SID interpretation

The [dual compiler](../../../scripts/compose-flashdance-dual.py) combines two independently assembled players for PAL MOS6581s at `$D400/$D420`, following [the address and validation contract](../sid/dual-sid.md). Chip A retains the accepted reconstruction; the [secondary description](../../../songs/flashdance-secondary.json) authors supporting parts. These choices are new interpretation, not recovered DRAX instructions.

| Chip B voice | Authored role and controls | Placement |
| --- | --- | --- |
| B1 | Sustained low triangle root, AD/SR `$48/$47`. Sole advancing owner of chip B's shared static low-pass filter, cutoff high `$60`, resonance/routing `$25`. | Twelve roots: B-flat2/F2/C3/G2, repeated, then E-flat2/B-flat2/A-flat2/F2. First trigger at call 2 produces body call 3; later legato changes match primary chord-body calls 131, 259, … 1411. |
| B2 | Unfiltered noise backbeat, AD/SR `$04/$04`, four gated body calls at absolute `$C4E0`, then instrument-owned release. | Sixteen attacks on beats 2 and 4 of the eight-bar verse fragment, retained from the audible revision. |
| B3 | Sustained pulse fifth seven semitones above B1, static width `$600`, AD/SR `$48/$37`, routed through the same low-pass filter. | Same note-body timing as B1; no separate reply melody, pitch modulation or intended unison doubling of the lead. Lower sustain is a register setting, not a cross-waveform loudness guarantee. |

Both pitched parts hold F/C across the final Fsus4-to-F change. Chip B starts at volume 12, while chip A retains volume 15. Both suppress new notes at call 1538 and use the same release/fade schedule; both control banks and master volumes are explicitly zero from call 1666. Each engine owns separate RAM state and tables; a wrapper calls A then B under one frame budget. The [secondary guards](../../../tests/flashdance_secondary_test.py) check harmonic membership throughout held notes and ending release, body timing, articulation, initial silence and filter routing; a deliberately delayed change proves the guard catches a stale chord tone. [Dual compiler guards](../../../tests/flashdance_dual_compiler_test.py) check state/address isolation and endings.

On 2026-10-13, the [corrected dual CPU audit](../../../build/cpu-timing-correction/flashdance-dual.audit.json) verified 1,667 calls with a maximum 3,514 of 19,656 PAL cycles. All 30,229 chip A initialization/music/ending writes retain their single-SID values and order. The [full VICE trace](../../../build/flashdance-dual-support/vice/study.json) matches all 60,231 playback writes on both banks, with at most six cycles of polling jitter. The [PSID v3 export](../../../build/flashdance-dual-support/reconstructed.sid) declares both 6581 chips explicitly. The [verification receipt](../../../build/flashdance-dual-support/verification.json) pins the final source and export; prose-only source clarification reassembles to the same SID bytes.

**Accepted stereo presentation:** [raw-stereo.wav](../../../build/flashdance-dual-support/raw-stereo.wav) places chip A left and chip B right, at unity gain, without crossfeed or normalization. It uses libsidplayfp 3.1.1/SIDLite, PAL MOS6581 pair, default subtune, 35 seconds of stereo PCM16 at 44.1 kHz. Both channels are unclipped and have zero AC RMS in the final half-second; chip B measures about 4.8 dB below chip A. This is a level check, separate from the musical verdict.

**Listening verdict, 2026-10-13:** the listener identified `build/flashdance-dual-support/raw-stereo.wav` and said it **“is really good. Stereo sound is convincing!”** This accepts the revised full dual arrangement in that raw stereo presentation and closes F5. It does not transfer the same preference to the alternative crossfed or mono mixes, or assert physical-hardware equivalence.

Other retained listening files are useful comparisons, with no separate preference verdict:

- [Three voices, then six voices](../../../build/flashdance-dual-support/listening/three-then-six-voices.wav): seconds 8–16, chip A alone at gain 0.5, half-second gap, then mono A+B at gain 0.5 each.
- [Crossfed stereo alternative](../../../build/flashdance-dual-support/listening/dual-listening-stereo.wav): A centered at gain 0.5, B at 0.35 left/0.65 right.
- [Complete mono mix](../../../build/flashdance-dual-support/listening/dual-mono.wav): `0.5 A + 0.5 B`.
- [Second-chip-only diagnostic](../../../build/flashdance-dual-support/listening/second-chip-only.wav): raw chip B at gain 1.0.

The [mix receipt](../../../build/flashdance-dual-support/listening/listening.json) pins these matrices and their audio-health checks. All full-file outputs are unclipped and settled at the ending.

### Retained arrangement lesson

The initial dual candidate received **“I don't hear a difference.”** Its [audibility check](../../../build/flashdance-dual/audibility-review.json) found chip B about 13.4 dB below A; masking was a plausible explanation. Raising levels and extending attacks made the additions audible, but the listener described [that revision](../../../build/flashdance-dual-audible/raw-stereo.wav) as **“i hear them, but it is maybe only a bit  better, sounds like a kind of second tune slightly off”.** Audibility alone did not establish musical fit.

The [score/program diagnosis](../../../build/flashdance-dual-audible/musical-diagnosis-v2.json) found that the late pad changes retained D4 over E-flat harmony at calls 1027–1033, F4 over A-flat at 1283–1289 and E-flat4 over Fsus4 at 1411–1417. Onset-only chord checks missed those held spans. The high static pad also doubled nominal lead pitches while the primary vibrato moved around them, and the triangle replies introduced an independent rising contour. These are measured arrangement differences and plausible explanations, not proof of which one the listener heard; the late harmonic conflicts lie beyond the short comparison window.

The accepted revision uses lower root/fifth support aligned to the primary chord bodies and removes the reply contour. For subordinate layers, validate the whole sounding span, preserve phrase timing and check register overlap before increasing level. A source MIDI/MusicXML is required only if preserving the original song's form beyond DRAX's arrangement is requested.
