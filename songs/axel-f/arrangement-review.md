# Axel F: restore musical roles and rhythmic contrast

The narrow-pulse hook was accepted, but the complete arrangement was not. The listener reported an annoying persistent background sound at 64.60–68.80 seconds, an annoying lead at 120–140 seconds, and an interpretation that is boring compared with Hülsbeck. The [full review](full-huelsbeck-pulse-review.json) retains both the earlier scoped acceptance and these objections. The current musical task is broader than another pulse-width adjustment.

## Two distinct roles carried by the same lead patch

| Passage | Score and executed behavior | Arrangement decision |
| --- | --- | --- |
| Held chord at 64.54–68.73 seconds | The reduction selects B♭4 from a four-note source chord and assigns it the hook's foreground pulse. Physical voice 1 has 207 consecutive gated body updates, then correctly clears GATE at 68.689 seconds. It is an intentional sustained note, not a stuck gate. | Keep the source pitch and duration, but give the held chord top the existing quieter `PLUCKSOF` triangle program. The entire beats 128–156 section contains just this one melody-voice event. |
| High lead at 118.98–139.05 seconds | A distinct source part supplies 97 notes at A♭5–E♭6. Their bodies last only 3–12 updates. Every pulse onset resets to `$200`, reaches at most `$381` while gated, and ends before the developed modulation heard in the hook. | Use the existing `ELSOFT` triangle program for the high lead in beats 236–276, preserving its pitches and rhythm. Keep its sustain/release distinct from the marimba accompaniment. |
| Hook returns and the high descent | These are different roles from the held chord and later high lead. A separate long F5 in the descent also has correct sustained gating; no listening complaint was reported there. | Retain the preferred moving-pulse lead; avoid a global patch replacement based on two role-specific objections. |

The first row's source event is from `held-chord-and-descent`, source beat 132; trimming the four initial silent beats places it at arranged beat 128. The later high lead comes from its own source track, not the hook track. The initial mapping preserved those origins in the adaptation report but did not use them when assigning timbre. That loses a useful arrangement distinction: a physical voice carrying several score parts does not make them one musical role. It motivates separate auditions, but does not establish that both roles need replacement patches.

The high lead's measured frequency variation is just one frequency-word unit during each gated body; delayed vibrato does not develop there. Increasing the same delayed effect would miss the actual short-note behavior. A source-correct pitch can still have the wrong spectrum, prominence and articulation for its register. The proposed triangle programs reuse existing patches, but their prior acceptance does not establish that this new context works musically.

Detailed diagnosis remains private under `build/axel-f-held-diagnosis/`, with source/conversion/frame fingerprints and event-specific evidence. The source MIDI, native note schedule and prior listening files remain unchanged.

## What the master reference adds beyond lead PWM

The [bounded arrangement evidence](huelsbeck-arrangement-observations.json) combines the existing 1,600-call CPU/VICE capture with 60 seconds of renderer snapshots. It shows three contrasting roles: percussion on physical voice 3, a pulse hook entering on voice 2 after the percussion introduction, then a low pulse bass entering on voice 1. The percussion alternates noise-to-falling-triangle, short noise and longer noise programs. It is not merely a transient before every bass note. The additional renderer interval is not a new ordered CPU-write or hardware-equivalence proof. Reproduce the source-pinned capture with the [master-study recipe](../../config/listening/axel-f-huelsbeck-study.json), then the additional renderer interval with the [60-second opening recipe](../../config/listening/axel-f-huelsbeck-opening.json); commands are retained in the aggregate.

This suggests useful design choices: independent percussion envelopes, contrasting bass and lead behavior, staged entrances, and space between phrases. These observations identify mechanisms available for arranging; they do not establish which one explains the listener's overall preference. The reference also differs from our score in key, tempo, form and chip model, so it is not a same-score fidelity comparison.

Our tonal reduction omitted all percussion even during sections where a voice was idle. In arranged beats 64–96, the hook and bass occupy two voices and the harmony voice is silent. The source has 48 kick events there. Each coincides with a bass onset, so restoring them adds a separate percussion body and envelope, not a new onset rhythm. By contrast, all three tonal roles are active during the later high lead; an independent drum there needs an explicit allocation tradeoff.

## How Hülsbeck’s version differs from ours

The central learning objective, clarified by the user, is how the master translated this piece into SID: the musical roles he prioritized, the tonal/percussion tradeoff, staged entrances, and the relationship between phrasing and sound programs. A patch extraction is supporting evidence, not the study’s end product. We can observe the choices in the executed arrangement; we cannot infer his private intentions or every omission relative to an unverified source arrangement. Keep these Axel F findings specific until other songs corroborate them.

The useful distinction is a staged, rhythm-led SID arrangement versus our tonal reduction of a multitrack score. This is an interpretation of the bounded source evidence and the listener’s verdicts, not an independent whole-song listening judgment or an explanation proven by one parameter test.

| Aspect | Hülsbeck reference, bounded opening | Our interpretation |
| --- | --- | --- |
| Development | Percussion begins first; lead enters around 9.5 seconds, low pulse bass around 28 seconds. | Tonal score sections determine the changes; omitted percussion removes one axis of contrast. |
| Rhythmic identity | One oscillator supplies several distinct percussion behaviors, separate from the lead and bass. | The initial reduction omits drums. Restoring kicks on bass onsets produced no reported useful difference. |
| Lead character | Asymmetric drifting pulse motion, lower programmed sustain (`$4`), continuing release motion, and tightly spaced gate retriggers without a per-note TEST frame. | Bounded pulse motion, higher programmed sustain (`$A`), and the native Extra TEST onset. The transferred pulse program is only one component of the source’s sound. |
| Musical roles | The measured opening assigns percussion, hook and low bass distinct programs and entrances. | Several source parts share one lead voice. The high-line substitution helps; the soft held-note substitution does not. |

The source uses PAL MOS6581 and CIA updates near 54.98 Hz; ours targets PAL MOS8580 with native updates near 50.12 Hz. Those conditions constrain effect transfer, but do not by themselves explain the musical preference or imply that one song’s tempo is faster. Key, form and score source also differ. Copying the patch or changing chip models cannot turn our arrangement into the same musical performance.

The practical recommendation is to borrow the reference’s arrangement discipline: establish distinct jobs for the voices, introduce contrast at phrase boundaries, and test whether percussion contributes movement rather than merely level. Keep the independently sourced melody and harmony, and describe any reductions or duration changes explicitly. Master influence should shape decisions at both phrase and instrument timescales.

## Bounded next auditions

The role-aware palette comparison changes the two problematic roles without changing notes or the liked hook. Judge whether the held support stops intruding and the high melody remains clear without the irritating tone. This trial alone does not claim to resolve the overall lack of interest.

The separate kick trial puts the existing `KICKFALL` program in the hook's idle harmony voice, using only the source's kick onsets. It preserves the immediate bass body and its filter ownership. Source MIDI drum durations are only about 31.5 ms; the candidate deliberately extends them toward 180 ms, capped by the next kick or passage boundary. Eight gaps are only 126 ms and therefore cannot preserve the instrument's full seven-update gated fall. Check actual exported behavior and make that limitation explicit rather than describing every hit as an intact drum program.

The earlier kick and Bach percussion experiments do not establish musical usefulness here: one comparison was inaudible and a stronger adaptation became annoying. Do not raise the level simply to obtain an audible difference. This is a new contextual test of a separate percussion role, with the unchanged tonal mix as reference. No new composition, full drum reconstruction or new backend is required.

Model-assistance review: no call. The human feedback identifies specific roles and a broader musical problem; the models are not calibrated to choose suitable timbres or judge whether restored percussion improves the arrangement. Use source/execution evidence to constrain the candidates and focused listening to select them.

## Verified listening packages

All comparisons use common unity gain and a half-second gap. These are generated local files, not public downloads. The source score and all generated music stay private.

| Folder under `build/` | Comparison file | Order and question |
| --- | --- | --- |
| `axel-f-role-aware-listening/` | `held-support-before-then-after.ab.wav` (24.5 seconds) | Previous → quieter held support, covering seconds 60–72. Does the held tone support the music without intruding? |
| `axel-f-role-aware-listening/` | `high-lead-before-then-after.ab.wav` (48.5 seconds) | Previous → rounder high lead, covering seconds 118–142. Is the melody clear without the annoying character? |
| `axel-f-kick-trial-listening/` | `without-then-with-kick.ab.wav` (32.77 seconds) | Same candidate SID with kick muted → all voices. Does percussion add useful drive without competing? |

The [role review](role-aware-review.json) pins the complete renders and submitted clips. All 1,025 note schedules are unchanged across 9,006 CPU calls; exactly one held-support and 97 upper-lead assignments change. Other voices, filter, volume, GATE/TEST and coupling schedules agree. Sampled VICE checks cover both changes and returns through call 9,000; both full WAVs are unclipped and end quietly. This establishes the declared timbre intervention, not musical improvement.

The [kick review](kick-trial-review.json) pins its separate source-backed experiment. Its 144 notes (46 lead, 48 kick and 50 bass) pass 987 CPU calls and sampled VICE checks through call 980. Forty hits retain three gated updates of the low C1 body; three retain one, and five retain none because the next source hit arrives too soon. The unchanged lead and bass preserve their own envelopes and the bass remains the sole filter owner. This is a bounded percussion test, not the complete drum arrangement.

```sh
python3 scripts/listening-package.py config/listening/axel-f-role-aware.json --output build/axel-f-role-aware
python3 scripts/publish-listening.py build/axel-f-role-aware/run.json --selection config/listening/axel-f-role-aware.audition.json --output build/axel-f-role-aware-listening-new
python3 scripts/listening-package.py config/listening/axel-f-kick-trial.json --output build/axel-f-kick-trial
python3 scripts/publish-listening.py build/axel-f-kick-trial/run.json --selection config/listening/axel-f-kick-trial.audition.json --output build/axel-f-kick-trial-listening-new
```

Use fresh publication destinations. The [small source-specific adapter](../../scripts/studies/axel-f/prepare-kick-trial.py) checks the pinned reduction, four-beat source offset, vacant harmony voice, source kick count and unchanged reusable instrument. It retains private note provenance and explicit duration adaptation. The existing recipe runner handles compilation, rendering, execution checks and listening assembly.

### Post-call equality does not isolate an audio contribution

Adding kick processing shifts the timing of unchanged lead/bass register writes within each player call. The two separately compiled native scores have 17,783 identical ordered non-kick stores by call/address/value, but their instruction starts differ by up to 397 CPU cycles. Their PCM difference therefore includes oscillator-phase changes, not just the new drum. The same-SID muted/unmuted comparison avoids that cross-export workload difference. Its rendered difference RMS is about 653 over 19.65 seconds; the separate-export difference is about 2,149 and must not be labelled the kick's contribution.

This diagnostic is appropriate here because the kick has no ring/sync coupling, bypasses the filter, and does not control bass or lead. Muting still changes synthesis inputs; the renderer's unchanged register-shadow snapshots are not proof of identical internal synthesis state. The solo is not a linear stem, and numerical signal strength does not establish that the kick helps the music. Follow the [voice-selection constraints](../../docs/workflows/audio-workflow.md#diagnostic-voice-selection).

## Listening decisions and selected revision

The listener reviewed all three comparisons on 2026-10-15:

| Comparison | Exact feedback | Decision |
| --- | --- | --- |
| Held support | “before is much bette” | Reject the soft-triangle substitution and keep the prior pulse for now. This relative preference does not withdraw the earlier complaint about the sustained tone. |
| High lead | “before seems more authentic, but honestly, after is nicer, not so annoyingly.” | Keep the rounder `ELSOFT` high lead. Preserve the authenticity tradeoff instead of describing it as a more faithful instrument. |
| Kick | “no difference, may a bit louder” | Leave the added kick out. Its measured contribution did not produce a reported musical benefit; another level increase is not the next step. |

These findings narrow the earlier diagnosis: recognizing distinct source roles helped find a useful high-lead change, but did not justify the specific softer held-support patch. Less brightness is not universally better, and a perceived improvement in comfort can coexist with reduced authenticity. The listener's words take precedence over a technically plausible explanation.

The selected revision combines the previous hook and held support with only the preferred high-lead change. Its score and all accompaniment remain unchanged; the kick is excluded. The original full-song criticism—limited interest compared with Hülsbeck—remains open. The next arrangement question is phrase/section development and contrasting source percussion roles, not another gain-only kick or a wholesale replacement of the preferred lead. Source inspection in beats 68–100 finds 68 maracas (GM 70) attacks, 30 away from bass onsets. This is the next bounded test: a short original noise program in the spare harmony voice, retaining source timings and durations. The source also contains a denser cabasa part and snare backbeats, but most snare hits coincide with bass. Do not label the chosen maracas part a recovered Hülsbeck drum or claim its noise approximation reproduces the GM instrument.

Model assistance remains no-call after this feedback: existing models have no demonstrated authority for these timbral and musical preferences. Reassess on the next substantive arrangement audition; do not use a model to override the mixed human verdict.

## Integrated preferred timbres

The [selected palette](selected-roles.json) and [verified review](selected-roles-review.json) retain the original pulse held support and replace only the 97 upper-lead assignments with the preferred `ELSOFT` program. No kick is added. All 1,025 source/native note schedules pass across 9,006 calls, all register values agree outside the upper-lead/release window, and sampled VICE checks run through call 9,000. The complete 179.635-second render is unclipped and ends quietly. The previous full version remains available alongside it.

```sh
python3 scripts/listening-package.py config/listening/axel-f-selected-roles.json --output build/axel-f-selected-roles
python3 scripts/publish-listening.py build/axel-f-selected-roles/run.json --selection config/listening/axel-f-selected-roles.audition.json --output build/axel-f-selected-roles-listening-new
```

The stable local folder is `build/axel-f-selected-roles-listening/`: `axel-f-selected-roles-full.wav`, `previous-full.wav`, and `high-lead-before-then-after.ab.wav`. The upper-lead program and post-call states match the preferred prior treatment; the full compilation does not produce byte-identical excerpt PCM. This integrates a scoped instrument preference and is not complete-song acceptance.

## Next rhythm audition: source maracas

The [rhythm configuration](rhythm-trial.json) selects the source’s 68 GM-maracas attacks in beats 68–100, including 30 that do not coincide with bass. The original short noise program uses a fixed oscillator frequency, `AD=$14/SR=$00`, and no filter, vibrato or oscillator coupling. The [Ghostbusters noise instrument](../../docs/research/composition/instruments/ghostbusters-decoded-programs.md) supplies prior envelope evidence; Hülsbeck supplies the stronger arrangement lesson of a dedicated, contrasting percussion role. Neither makes this a recovered master patch or a faithful acoustic-maracas emulation.

The candidate retains every selected source onset and duration. Native execution yields 36 one-update, 31 two-update and one three-update gated noise bodies, followed by the declared release. The unchanged lead and bass plus 68 percussion events pass 987 calls and sampled VICE checks. The [review](rhythm-trial-review.json) records the counts, source projection, same-SID muted control, signal checks and the liked-role/too-loud verdict. A measured contribution remains separate from musical benefit.

```sh
python3 scripts/listening-package.py config/listening/axel-f-rhythm-trial.json --output build/axel-f-rhythm-trial
python3 scripts/publish-listening.py build/axel-f-rhythm-trial/run.json --selection config/listening/axel-f-rhythm-trial.audition.json --output build/axel-f-rhythm-trial-listening-new
```

The stable folder `build/axel-f-rhythm-trial-listening/` contains `without-then-with-maracas.ab.wav` (32.77 seconds, muted first, full second, common unity gain), `without-maracas.wav`, `with-maracas.wav`, and the optional `maracas-only.wav` diagnostic. The primary question is whether the source-backed off-bass attacks add useful movement while preserving melody and bass clarity. No further gain-only kick trial is queued. The complete selected-timbre render does not include this addition; its rhythmic role is liked but its level requires the balance revision below. Model review is no-call: the present models are not calibrated to settle this musical preference.

## Full-version verdict and named master passages

The listener rates the selected full render “mediocre” and identifies three strengths in Hülsbeck’s original: the main instrument and background beat around 9.50 seconds, the supporting instrument around 28.80 seconds, and the instrument change heard around 60 seconds. These reference times belong to the pinned original SID, not our independently sourced score. The earlier relative high-lead preference does not establish a compelling arrangement.

The maracas comparison receives “yes, maracas add a nice touch, but a bit too loud”. Retain its rhythmic role, with native balance revision required. The next work separates that small level correction from a deeper master-informed instrument/ensemble trial. Inspect the named source transitions before assigning an explanation; a perceived instrument change can arise from a program, register, articulation or ensemble change. Preserve that distinction in the executed evidence and test one coherent source-informed palette on our existing score rather than continuing arbitrary patch substitutions.

Model review after these verdicts is no-call: the user has supplied specific positive reference moments and a useful-role/excessive-level distinction. Source analysis and native checks can narrow the interventions, while neither current model scores nor register agreement establish a compelling musical result.

## Quieter native maracas

The [balance configuration](rhythm-balanced.json) changes only the noise instrument’s decay nibble, `AD=$14→$11`, retaining attack, zero sustain/release, source notes, durations and all 68 attacks. The [verified balance review](rhythm-balanced-review.json) records a 4.83 dB reduction in noise AC RMS and same-SID contribution. Its peak is unchanged: this is a shorter body, not a linear gain control. The previous and revised exports have identical ordered write timing and byte-identical muted audio; only voice 2’s AD register changes across 987 calls. Native, sampled VICE, unclipped-signal and quiet-tail checks pass. The reusable verifier now rejects instruction-timing drift and changed muted PCM rather than merely reporting them; negative tests cover both, and retained AD11/AD13 evidence satisfies the stronger guards unchanged. Listening then rejects this setting as too quiet: “In the second one, I can barely hear the maracas”.

An initially screened slower attack (`AD=$34`) increased noise RMS by 1.768 dB and was rejected before submission. In this short-note context, a slower attack did not provide quieter support. Retain the measured result with the source gate/history and target; do not infer a universal attack-to-loudness rule. Envelope rates shape a trajectory and must be checked at the actual note ages.

```sh
python3 scripts/listening-package.py config/listening/axel-f-rhythm-balanced.json --output build/axel-f-rhythm-balanced-new
python3 scripts/publish-listening.py build/axel-f-rhythm-balanced-new/run.json --selection config/listening/axel-f-rhythm-balanced.audition.json --output build/axel-f-rhythm-balanced-listening-new
```

The stable pair is `build/axel-f-rhythm-balanced-listening/previous-then-quieter.ab.wav` (32.77 seconds; previous then revised at common unity gain). Separate files are `previous-maracas.wav` and `quieter-maracas.wav`. The shorter body did not retain sufficient prominence for the listener; keep this failed balance as the lower comparison bound. This balance trial does not alter the complete arrangement or settle its instrument choices.

## Master-informed ensemble audition

The [extended master study](huelsbeck-study.md#targeted-role-study-lead-support-and-the-apparent-switch) confirms a moving, unfiltered supporting pulse and no lead-program selection change near one minute. It also identifies the lower bass register relative to the lead. The first coherent palette trial deliberately keeps our source pitches and rhythm: lead `ADSR=$0A49`, bass `ADSR=$0999`, an independently moving bass pulse and filter bypass. Native TEST onsets, PAL MOS8580 and the existing bounded lead pulse remain explicit departures from Hülsbeck’s source. Programmed sustain is not interpreted as a simple gain ratio.

This trial asks whether the lead/support combination provides a more useful character than our current palette. It does not test the source’s lower bass octave, reconstruct its arrangement, or roll the quieter maracas into the full song. Retain those as separate choices; the short ensemble verdict below accepts only this pairing.

The listener strongly accepts the level-matched pairing: “the "Hülsbeck-informed combination second" is so much better!!!” and “The "Hülsbeck-informed combination second" has just the right choice of instruments”. This settles the tested ensemble choice, not which individual parameter caused the preference or whether it works across the complete arrangement. Extend the pairing across its existing lead and bass roles, preserving the separately preferred rounder high lead, held-support treatment, source notes and form. Keep the separately reviewed percussion balance distinct from this pairing verdict.

The [palette review](master-palette-review.json) pins the accepted comparison, native exports and verification. `build/axel-f-master-palette-matched-listening/previous-then-master-palette-matched.ab.wav` is 32.77 seconds, previous first and candidate second. One constant candidate attenuation of 2.3489 dB matches AC RMS while preserving internal balance; this is playback preparation, not a per-voice SID gain control. All 96 projected notes and 987 calls retain their pitch, gate/TEST and waveform schedules; sampled VICE, unclipped audio and quiet ending checks pass. The three original Hülsbeck context clips use his distinct arrangement and are not fidelity comparisons.

```sh
python3 scripts/listening-package.py config/listening/axel-f-master-palette.json --output build/axel-f-master-palette-new
python3 scripts/publish-listening.py build/axel-f-master-palette-new/run.json --selection config/listening/axel-f-master-palette.audition.json --output build/axel-f-master-palette-listening-new
```

Model checkpoint after acceptance: no call. Human feedback settles the pairing; current model calibration cannot attribute the preference or predict complete-song acceptance. Reassess at the full rendition.

## Intermediate maracas balance

The [middle configuration](rhythm-middle.json) and [pinned review](rhythm-middle-review.json) retain all 68 attacks and change only `AD14→AD13`. Noise AC RMS falls from 700.52 to 576.39, a 1.694 dB reduction; this is 3.137 dB above the barely audible `AD11` trial. An intermediate `AD12` screen measured −3.048 dB and fell outside the preselected 1–3 dB reduction range; retain that screen without presenting it as musically rejected. The final candidate passes schedule, ordered-write timing, sampled VICE, clipping and quiet-tail checks. The listener accepts it: “yes to: second half keep the nice rhythmic touch without becoming too prominent”. Retain AD13 for this role; its balance with the newly accepted lead/bass pairing and coverage through the full arrangement still need checking.

Nonzero signal on all attacks and a chosen decibel target were insufficient acceptance criteria for the prior candidate; the useful noise body must remain perceptible in the mix. `build/axel-f-rhythm-middle-listening/previous-then-middle.ab.wav` plays the original then intermediate balance at common gain (32.77 seconds). `previous-maracas.wav` and `middle-maracas.wav` preserve separate renders. This accepts the bounded balance trial, not full-song percussion coverage.

```sh
python3 scripts/listening-package.py config/listening/axel-f-rhythm-middle.json --output build/axel-f-rhythm-middle-new
python3 scripts/publish-listening.py build/axel-f-rhythm-middle-new/run.json --selection config/listening/axel-f-rhythm-middle.audition.json --output build/axel-f-rhythm-middle-listening-new
```

## Complete source-maracas allocation

The accepted AD13 setting can be extended conservatively to four sections where the reduced harmony voice is entirely vacant. A read-only comparison against the pinned MIDI identifies 186 source attacks with unique onsets and no overlaps; every original duration fits. These ranges are arranged beats, with source beats four beats later.

| Arranged section | Source maracas attacks | Allocation |
| --- | ---: | --- |
| 32–64 | 68 | Vacant harmony voice |
| 64–96 | 68 | Vacant harmony voice; includes the reviewed rhythm excerpt |
| 128–156 | 16 | Vacant harmony voice below retained held support |
| 156–172 | 34 | Vacant harmony voice during source high descent |

Preserve all 259 tonal harmony events, melody, bass and form. No source maracas occur in the final section or omitted percussion tail. Across all nominal note gaps, 261 source records represent 249 distinct attacks, including 12 simultaneous duplicates; the first full integration should exclude the 63 additional distinct gap hits rather than risk tonal releases or add duplicate attacks. The user authorizes this integration after the positive full-palette response. The [full-rhythm configuration](full-rhythm.json) and [source-specific projector](../../scripts/studies/axel-f/prepare-full-rhythm.py) implement the allocation; complete execution and combined listening remain separate checks. Retain the percussion-free full version as the comparison reference.

To reproduce the coverage check, resolve the `prepare` stage’s `attemptDirectory` in `build/axel-f-rhythm-trial/completed-run.json`. Read `score/full-common-score.json` and `score/score.json` there; their source and reduced-score hashes are pinned in [the rhythm review](rhythm-trial-review.json). Select GM70 source events starting in `[4,353.3125)`, subtract four beats from each onset, and preserve duration. Use exact rational source times and `Fraction(str(value))` for reduced decimal times. Compare half-open event intervals with the reduced harmony intervals. The full projection has 512 records / 478 distinct attacks; nominal free gaps admit 261 / 249, and the four entirely vacant sections admit 186 / 186. The projector preserves source identities and rejects overlaps, rather than treating these aggregate counts as its sole oracle.

Implementation reuses the current backend with a small source-specific full-projection preparation step: append AD13 without shifting existing instrument IDs, add the 186 source events to harmony, and select that instrument only in the four vacant sections. Projected voice totals are `[288,445,478]`, preserving all 1,025 tonal notes. The excerpt verifier assumes every harmony event is noise and cannot be reused unchanged; the full guard distinguishes the 259 tonal harmony events from percussion. At the occupied-to-empty boundary near beat 128, the previous harmony gate clears 17 native calls (about 339 ms) before the first maracas onset; verify actual release sound rather than treating that timing margin as proof of silence. Whole-track voice-2 muting would remove tonal harmony as well, so restrict any contribution diagnostic to the vacant windows. Added processing can shift instruction timing; do not impose the decay-only trial’s exact timing/PCM invariant on this different intervention.

## Accepted pairing across the complete tonal arrangement

The [full palette](full-master-palette.json), [recipe](../../config/listening/axel-f-full-master-palette.json) and [review](full-master-palette-review.json) extend the accepted lead/bass pairing through the existing complete score. Main lead uses the accepted envelope; bass uses the accepted independently moving, unfiltered pulse. The original held-support program is copied into its own role for arranged beats 128–156, retaining `ADSR=$08A8`; the 97 preferred ELSOFT high-lead notes retain their program. Score, pitches, form and all 1,025 tonal notes remain unchanged. No percussion is added in this package.

All 9,006 calls pass the full schedule/register checks; held and upper-lead registers match their previous programs over each exact role lifetime. Role verification uses the first assigned onset inclusive and the next different role’s onset exclusive: its initial end-boundary check incorrectly included the next role’s TEST/ADSR setup. The same failure reproduced at both preserved-role transitions and was fixed without changing or rerendering the music. Fourteen sampled VICE checkpoints through call 9,000 pass with maximum cadence error five cycles. The 179.634943-second candidate has peak 12,178, no clipped samples and zero measured AC RMS in its pre-stop release and final tail.

`build/axel-f-full-master-palette-listening/axel-f-full-master-palette.wav` is the complete candidate at native unity gain; `previous-selected-full.wav` preserves the exact earlier full version. The held-support and high-lead context pairs use whole-excerpt level matching, with candidate attenuation of 0.8610 and 1.3573 dB respectively. Their preserved lead programs do not imply identical full mixes: the bass underneath them changes. `ending-before-then-after.ab.wav` retains unity gain. The listener responds “Nice. what next?” after delivery of the full version, then authorizes combining it with the accepted AD13 maracas. Preserve that positive response without inventing a specific ending verdict; the later combined-arrangement verdict is recorded below.

```sh
python3 scripts/listening-package.py config/listening/axel-f-full-master-palette.json --output build/axel-f-full-master-palette-new
python3 scripts/publish-listening.py build/axel-f-full-master-palette-new/run.json --selection config/listening/axel-f-full-master-palette.audition.json --output build/axel-f-full-master-palette-listening-new
```

The recipe imports the previous full render and execution artifacts from a frozen successful receipt with file hashes; it builds only the new candidate. That candidate stage took 127.18 seconds on 2026-10-15; the final verification/preparation run reused it and completed in 1.15 seconds. This comparison recipe requires the retained baseline receipt and its files at the declared relative paths; it is a new candidate render against retained reference evidence, not a from-scratch baseline recipe. A fresh selected-roles run produces different attempt paths, so reproducing that recipe alone does not populate this frozen reference bundle. Restore the pinned bundle for this exact comparison. Receipt matching uses stage/relative artifact identity and hashes rather than binding the archive to one machine’s absolute path. Source scores, native song files, original reference and rendered audio remain private. Model review is no-call: available models cannot establish full-form preference; retain the user’s listening verdict as the decision point.

## Full-rhythm verification contract

The full projector preserves the pinned source and accepted palette, appends the AD13 instrument without shifting prior instrument IDs, and rejects duplicate, overlapping or section-crossing source attacks. Complete native checks recover every original tonal note by its musical identity rather than by the harmony event index, which changes when percussion is inserted. Source-count agreement is insufficient: the verifier independently recomputes native onset, duration and gate boundaries from source timing.

Post-call register equality can hide a transient write, so the full verifier also preserves ordered tonal and shared-register stores. Only voice 2’s noise history, from its first noise onset until the next tonal onset, is exempt; its preceding release and restored tonal program remain guarded. Write-cycle shifts from added processing are reported, not mistaken for changed notes or additive audio stems. Every declared noise body must follow its exact gate schedule; a later spurious retrigger cannot count as the same source hit.

Harmony-only diagnostic renders are bound to their corresponding full exports through matching renderer register snapshots before any silence measurement. Same duration and channel layout alone cannot establish that a quiet file measures the intended SID. Measure both incoming-noise and returning-tonal boundaries, check all 186 rendered bodies, and verify clipping and the complete ending. These checks establish execution and signal properties; musical balance with the newly accepted ensemble still requires listening.

The full render exposes one contribution limitation: the source attack at arranged beat 168 (source beat 172, native TEST tick 4,246) has one gated noise-body call before gate-off at 4,248, but its voice-2 diagnostic is exactly silent throughout the scheduled interval until the next source onset at 4,252. The other 185 attack windows have measured bodies (minimum AC RMS 238.99), including same-length notes at beats 166.5, 167 and 167.5. Preserve the distinction between 186 correctly scheduled native attacks and 185 nonzero diagnostic windows. Keep the accepted AD13 instrument and exact source durations for this audition; do not silently lengthen the note or retune the whole instrument to satisfy an all-attacks-audible claim. The contribution guard pins this specific zero window and rejects additional missing bodies. Correct GATE/waveform writes alone do not establish an audible attack; the internal envelope mechanism and perceptual consequence are not established by this measurement.

Choose transition clips from executed note onsets, not merely section boundaries. The first percussion block returns to a tonal harmony note at beat 96.5 (about 48.659 seconds); after the second block ends at beat 172, harmony does not return until beat 204 (about 102.864 seconds). A clip around 86–88 seconds would show the end of percussion but would not test restoration of the next tonal instrument.

The complete noise-to-tone transitions reproduce the [native first-frame constraint](../../docs/songs/fuer-elise-native.md): at returning tonal TEST ticks 2,439 and 5,156, voice 2’s frequency low byte can still contain the previous noise value while control is `$09` (TEST, no selected waveform). The high byte and remaining registers agree, and the following full-pitch body restores every tonal register. The full check permits only this inactive-TEST low-byte residue at the two verified handovers; it still rejects different pitch in the sounding body, altered gates/programs, or changed ordered tonal/shared stores. This is a verification-model correction, not a timing or arrangement change.

Measure quietness immediately before a handover without requiring the earlier, legitimate release to disappear. Before the noise entry at tick 3,235, the original `[-150,-30] ms` window contains preserved tonal decay: baseline/candidate AC RMS is 54.017/54.076. Both signals settle to zero in the fixed `[-60,-5] ms` and `[-25,-1] ms` windows. The verifier retains the earlier measurements and 20 ms diagnostic bins, but applies the unchanged AC RMS limit of 16 to those two immediate windows at all four handovers. A regression rejects residue near the actual handover. The arrangement and audio are unchanged; shortening a valid source release to satisfy a misplaced measurement would be the wrong correction.

The [full-rhythm recipe](../../config/listening/axel-f-full-rhythm.json) imports the verified tonal baseline, builds the combined candidate, checks it in VICE, renders voice-2 diagnostics and prepares common-gain comparisons. Baseline import resolves stage/artifact identities through a valid completed receipt and verifies file hashes; it also supports a regenerated baseline with different cache paths. A full baseline register snapshot added for diagnostic binding is pinned separately rather than misrepresented as part of the old receipt. This remains retained-evidence import, not fresh execution of the baseline. The longer candidate uses the [explicit bounded native-audit deadline](../../docs/workflows/native-song-workflow.md); changing that deadline does not change the number of audited calls or the audio.

```sh
python3 scripts/listening-package.py config/listening/axel-f-full-rhythm.json --output build/axel-f-full-rhythm
python3 scripts/publish-listening.py build/axel-f-full-rhythm/run.json --selection config/listening/axel-f-full-rhythm.audition.json --output build/axel-f-full-rhythm-listening
```

Keep the referenced full-palette evidence bundle available; the publisher requires a fresh destination. Unchanged successful stages are reused by the recipe. Source notes, original references, native exports and audio stay private; the checked-in projection configuration and verification summaries contain no complete score. Model-assistance review for this integration is no-call: human feedback has selected AD13 and the palette, while available models are not calibrated to judge their combined balance or the complete form. Reassess at the listener verdict and case closure.

The [completed aggregate review](full-rhythm-review.json) pins the full export and delivered comparison. All 9,006 native calls pass; sampled VICE checks and the 200,317 preserved ordered stores pass, with a maximum instruction-start shift of 406 cycles. The 179.634943-second candidate has peak 12,372, no clipping and a quiet ending. The full build/audit/render stage took 126.583 seconds; after the verification corrections, the final recipe took 11.125 seconds while reusing the native export, VICE results and both diagnostic renders. These are measured execution times, not a claim about total arrangement productivity.

The submitted `build/axel-f-full-rhythm-listening/` package contains the full `axel-f-full-rhythm.wav`, exact prior `tonal-full-reference.wav`, a 32.769-second hook pair and separate entry, return-to-tone and ending pairs. Each comparison plays the prior version first and uses common unity gain. The known zero percussion window is disclosed rather than presented as complete source-percussion fidelity. The feedback below does not select this combined arrangement.

## Full-rhythm feedback: useful drive, unwanted maracas character

The listener says: “yes to: rhythm add useful drive without competing with the tune . However: i am not a fan of the maracas here.” Record rhythmic contribution and balance as positive, but instrument suitability as negative in this context. The earlier AD13 balance verdict remains valid for its question; it did not settle whether maracas belong in the complete interpretation. No transitions or ending verdict was supplied, and this does not reject percussion in general.

Park the combined maracas version and retain the positively received [complete tonal palette](full-master-palette-review.json) as the current baseline. This is the coordinator’s conservative selection, not a claim that the listener explicitly preferred one complete version over another. Its existing WAV, SID, SWM and pinned export manifest already exist; no rerender or destructive rollback is needed. Keep the trial’s sound files and technical evidence available.

The reusable lesson is to assess rhythmic function, mix balance and instrument character separately. Once the listener likes the drive but dislikes the sound, another loudness adjustment does not address the stated objection. A later replacement should compare one different, source-informed percussion character on the same short phrase with unchanged attacks and tonal palette before extending it through the full song. Do not claim a replacement is already chosen or validated.

Model-assistance checkpoint after this verdict: no call. Human feedback settles this preference distinction; current models cannot choose a suitable replacement or override the dislike. Reassess at a materially different sound audition or case closure.

## Falling-triangle percussion character audition

On 2026-10-16 the user authorizes closing the overall plan. The unresolved rhythm question is whether a different percussion character preserves the useful drive without the disliked maracas texture. The [editable configuration](rhythm-character.json), [verification summary](rhythm-character-review.json) and [recipe](../../config/listening/axel-f-rhythm-character.json) provide a short comparison before any full-song integration. The percussion-free [full tonal palette](full-master-palette-review.json) remains the selected baseline while feedback is pending.

The [executed master observations](huelsbeck-arrangement-observations.json) identify Hülsbeck's voice-3 `AD20/SR50` noise-to-falling-triangle percussion. This adaptation omits the noise prelude, uses absolute D♯4/C4/G3/C3 steps and `AD20/SR53`, and retains native TEST onset. It is a new compact electronic drum inspired by that tonal body, not a recovered source patch: the source is PAL MOS6581 with CIA timing, while this native candidate is PAL MOS8580 at VBI rate. The waveform table continues through release. No filter or oscillator coupling is added.

The projector reuses the pinned MIDI70 rhythm at source beats 68–100 (arranged 64–96), preserving all 68 attacks and exact source durations. Lead and bass use the positively received full palette. Both no-percussion and AD13-maracas references are prepared on this same palette; the maracas reference retains its instrument character, rather than copying an older render with different tonal instruments. The primary no-percussion comparison mutes only voice 2 in the candidate SID, retaining its scheduling and shared state; a separately built no-percussion native export verifies ordered tonal-store preservation. These are diagnostic mixes, not additive stems.

All 987 native calls pass, with maximum play cost 2,311 of 19,656 PAL cycles. Sampled VICE checks reach call 980 after the stop. Each comparison preserves 17,783 ordered non-percussion stores; the largest instruction-start shift is 393 cycles against the no-percussion export, and 88 against maracas. All 68 triangle diagnostic attack windows contain signal; minimum AC RMS is 194.27. Triangle-only phrase RMS is 0.6512 of the retained maracas, about 3.73 dB lower; no PCM gain adjustment is applied. The last 20 ms before a retrigger can contain release (maximum measured AC RMS 267.34), so this is not a claim of silence between every hit. The complete hook tail settles before volume clear, and full/muted/solo renders are unclipped and bound to the corresponding SID by identical renderer snapshots. These measurements do not establish audibility, natural articulation or musical suitability.

```sh
python3 scripts/listening-package.py config/listening/axel-f-rhythm-character.json --output build/axel-f-rhythm-character
python3 scripts/publish-listening.py build/axel-f-rhythm-character/run.json --selection config/listening/axel-f-rhythm-character.audition.json --output build/axel-f-rhythm-character-listening
```

Use a fresh publication directory for a subsequent run. Both comparisons contain the same 16.134432-second phrase per side, separated by half a second, at common unity gain:

- [No percussion → falling triangle](../../build/axel-f-rhythm-character-listening/without-then-triangle.ab.wav): does the second half add useful drive with a sound that fits?
- [Retained maracas → falling triangle](../../build/axel-f-rhythm-character-listening/maracas-then-triangle.ab.wav): same tonal palette and rhythm; inspect the change of percussion character.
- Full hook renders with release tails: [no percussion](../../build/axel-f-rhythm-character-listening/without-percussion.wav), [maracas](../../build/axel-f-rhythm-character-listening/retained-maracas.wav), [triangle](../../build/axel-f-rhythm-character-listening/falling-triangle.wav); [triangle-only diagnostic](../../build/axel-f-rhythm-character-listening/triangle-only.wav).

The listener reports: “I head triangle, but's it's very faint. And with Maracas, I fear it's more of a distraction.  Hülsbeck did it better”. The triangle is heard but too faint; maracas is now described as distracting in this comparison. Neither is selected for full integration. Model-assistance review at audition and feedback: no call; existing trials cannot select percussion character or override this feedback. Reassess at a materially different role audition or case closure.

## Source kick/snare role audition

The faint triangle verdict blocks full integration. Source timing inspection finds the same pattern at Hülsbeck calls 7, 63 and 575: `AD20/SR50` stays gated for 16 CIA calls, with four noise calls followed by twelve falling-triangle calls, about 291 ms in total. The preceding native triangle trial put one sound on the 68 maracas attacks; 36 hits had one gated body update, 31 had two and one had three. Its measurable signal did not establish a useful rhythmic body. This identifies a timing and role mismatch with the master, not proof that either factor alone caused the listener's preference.

The [new role configuration](drum-pair.json) and [verification/diagnosis record](drum-pair-review.json) test a compact drum pair on the same source-score phrase. The MIDI supplies 48 kick36 and 16 snare38 onsets. Twelve coincide: snare takes priority on the one vacant harmony voice, leaving 36 kick and 16 snare events. The 68 maracas and continuous shaker attacks are omitted. Both source pitches and timing of the tonal parts remain unchanged. This is an explicit drum reduction, not full source-percussion fidelity or a copy of Hülsbeck's rhythm.

The kick compresses the master's noise-to-triangle idea into one noise update followed by a falling triangle body. The snare uses a descending noise program informed by the master's `AD20/SR90` record. Absolute pitches are quantized native table choices, not exact source frequency-word trajectories; both programs use release 2 with native TEST onset. Kick score duration is deliberately extended to at most 240 ms and snare to 180 ms, each capped at the next selected source onset or phrase boundary. The native gate inset remains explicit. The [preparer and verifier](../../scripts/studies/axel-f/prepare-drum-pair.py) records every source origin, omitted collision and duration adaptation privately.

All 987 CPU calls and sampled VICE checkpoints pass; maximum play cost is 2,309 of 19,656 PAL cycles. The 17,783 ordered non-percussion stores remain identical, with a maximum instruction-start shift of 397 cycles. Adding drum patterns renumbers unchanged bass patterns in SID-Wizard's global pattern pool, so tonal identity compares every native note field except that storage identifier; regression tests still reject pitch, onset or gate changes. The full ordered-store check independently guards the sounding result.

All 52 diagnostic attack windows contain signal (minimum AC RMS 543.66 for kick and 736.45 for snare). Kicks have 4–10 gated body updates and snares 7. Full-mix AC RMS is 3,434.27 against 3,321.88 with drums muted; the renders are unclipped, use unity gain and have a quiet pre-stop tail. Maximum AC RMS in the final 20 ms before a retrigger is 865.71; tails are not claimed silent at every retrigger. Natural articulation and freedom from distraction remain listening questions. Same-SID diagnostic snapshots match the full render; diagnostic mixes are not additive stems.

```sh
python3 scripts/listening-package.py config/listening/axel-f-drum-pair.json --output build/axel-f-drum-pair
python3 scripts/publish-listening.py build/axel-f-drum-pair/run.json --selection config/listening/axel-f-drum-pair.audition.json --output build/axel-f-drum-pair-listening
```

Use a fresh publication directory for a later submission. The [primary comparison](../../build/axel-f-drum-pair-listening/without-then-kick-and-snare.ab.wav) plays no percussion first, then the source kick/snare adaptation, 16.134432 seconds each with a half-second gap and common unity gain. [No-percussion reference](../../build/axel-f-drum-pair-listening/without-percussion.wav), [candidate](../../build/axel-f-drum-pair-listening/source-kick-and-snare.wav) and [drums-only diagnostic](../../build/axel-f-drum-pair-listening/drums-only.wav) retain the full hook release tail. The [Hülsbeck lead-and-beat passage](../../build/axel-f-master-palette-matched-listening/huelsbeck-lead-and-beat-9.5-20s.wav) is the separately timed arrangement reference, not an exact reconstruction target. This is a joint role/articulation/timbre revision, not an isolated waveform comparison.

The listener says “kick and snare is better, although not too convincing since boring”, preferring Hülsbeck’s more sophisticated percussion with some rhythmic changes and, separately, its lead. This is relative improvement, not selection for full integration. Preserve the percussion-free tonal baseline. No model call was made for this audition; the subsequent explicit question about model consultation triggers a bounded descriptive-assistance review, rather than treating the lack of a validated quality judge as a reason to skip all useful perception research.


## Descriptive model review after the drum-pair verdict

The user asked whether models had been consulted about Hülsbeck’s appeal. They had not: earlier reviews skipped model calls because quality judgment was unvalidated. That was too broad a reason to exclude a bounded descriptive probe. With explicit upload approval, the [four-clip Qwen follow-up](../../docs/research/audio-assessment.md#axel-f-descriptive-follow-up-silence-failure) reused the Trap prompt and controls. It failed silence while describing both musical excerpts as predominantly repeating. No model observation is used to select instruments or rhythm. The [assessment](../../evidence/axel-f-model-perception/assessment.json) preserves this failure, actual cost and exact response bindings; no second model or retry is queued. Next review is the complete selected arrangement before closure, with no automatic paid call.


## Master-derived percussion phrase contrast

The kick/snare verdict identifies phrase development as the next musical question: can changing percussion roles and a short fill make this hook engaging without competing with the melody? The [recipe](../../config/listening/axel-f-master-rhythm.json) re-executes the pinned Hülsbeck study before adapting its calls 519–1542. The [configuration](master-rhythm.json) pins decompressed snapshot/write hashes, so gzip header timestamps cannot invalidate identical execution. Source lead onsets in the first eight-beat phrase exactly match the independent MIDI phrase when divided by 32 calls per beat. Its lead is four semitones above our MIDI lead; pitched kick/fill programs are transposed down four semitones, while the unpitched noise roles retain their source pitch scale.

The master uses 19 attacks in the first eight beats and 22 in the next, then repeats this pair. The second phrase changes the kick/snare pattern and finishes with four descending pitched attacks using the same noise-to-triangle program at different initial frequencies. Across the 32-beat window there are 42 kick/fill, 24 short-noise hat and 16 falling-noise snare attacks. This is source execution and role classification, not inferred composer intention. The new candidate adopts that percussion arrangement as an explicit departure from the MIDI drum reduction; MIDI melody, bass, key, tempo and phrase length remain unchanged. The prior drum pair and full percussion-free baseline are preserved.

The [preparer](../../scripts/studies/axel-f/prepare-master-rhythm.py) uses editable native programs that approximate the master’s elapsed-time pitch falls at PAL VBI cadence. Absolute pitches are quantized; native TEST onset, release 2 and the minimum table pitch remain adaptations. The rejected first build exposed two native grammar constraints in SID-Wizard’s `player.asm`, `WFARPTB`/`NORMARP`: waveform-column `00..0F` changes table speed, and pitch `80` is NOP. Consequently, source waveform-off `01` is replaced by gate-off/release, and the falling snare uses pitch `81` at its tail. Source and native drivers’ envelope histories and tail behavior are not equivalent. These are source-specific adaptation corrections, not changes to the shared native backend.

The [verified submission](master-rhythm-review.json), [retained execution](../../evidence/axel-f-master-rhythm/verification.json) and [tonal-boundary proof](../../evidence/axel-f-master-rhythm/mechanism.json) record 987 CPU calls, a maximum 2,312 cycles within the 19,656-cycle frame, sampled standalone VICE agreement, all 82 nonzero drum diagnostic windows, zero clipped samples and a settled release before volume clear. All 17,783 ordered non-percussion stores and tonal note semantics match the no-percussion reference; extra work shifts instruction starts by at most 399 cycles, so this does not claim PCM identity of separate exports. The published pair’s two PCM windows were checked directly against the old and new files. Common unity gain preserves balance; it does not equalize percussion loudness.

```sh
python3 scripts/listening-package.py config/listening/axel-f-master-rhythm.json --output build/axel-f-master-rhythm
python3 scripts/publish-listening.py build/axel-f-master-rhythm/run.json --selection config/listening/axel-f-master-rhythm.audition.json --output build/axel-f-master-rhythm-listening
```

The [previous-then-varied comparison](../../build/axel-f-master-rhythm-listening/previous-then-varied.ab.wav) contains two 16.134432-second windows separated by half a second. The [new candidate](../../build/axel-f-master-rhythm-listening/varied-master-drums.wav), [previous kick/snare](../../build/axel-f-master-rhythm-listening/previous-kick-and-snare.wav), [percussion-free diagnostic](../../build/axel-f-master-rhythm-listening/without-percussion.wav), and [Hülsbeck reference](../../build/axel-f-master-palette-matched-listening/huelsbeck-lead-and-beat-9.5-20s.wav) remain available. The source reference has a different tempo, key, chip model and accompaniment; it is an arrangement reference, not an isolated timbre A/B. The listener prefers the varied version but still finds Hülsbeck’s lead snappier and drums punchier. Select the varied rhythm direction; this does not accept its instrument character or the full arrangement. Keep the previously accepted lead/bass pairing as the comparison baseline while testing articulation. Full integration and complete-performance/ending review remain open.


## Lead snap and drum impact: chip response and envelope contour

The listener’s verdict is specific: “I like varied more” but Hülsbeck’s lead is “snappier” and the drums have “more punch”. Preserve that relative rhythmic preference without claiming final instrument acceptance. The user also confirms that SID means MOS6581, MOS8580 and stereo in this project; both model targets and dual-SID exports are supported, and a case must declare which it uses.

The lead already uses the master’s `AD0A/SR49`; copying those values again cannot explain the remaining difference. The reference uses MOS6581 and its original CIA driver; our native audition uses MOS8580 with a TEST first frame and a different release/retrigger history. The [source study](huelsbeck-study.md#what-the-executed-lead-teaches) and [native onset constraint](../../docs/songs/fuer-elise-native.md#timing-and-verification-boundary) own these observations. Source and MIDI articulation also differ: corresponding melody attacks align in the first phrase, but note lengths and subsequent gaps are not identical. None of these observations alone proves the cause of the listener’s preference.

The [bounded recipe](../../config/listening/axel-f-timbre.json) prepares two separate comparisons over the same preferred varied rhythm. The chip candidate changes only MOS8580 to MOS6581. The contour candidate stays on MOS8580: lead `0A49` becomes `0847` for faster decay/release at unchanged sustain, and the three drum programs change attack `2` to `4`, retaining decay, sustain and release. This deliberately tests a later envelope peak relative to the native TEST interval: a faster numeric attack could spend more of its transient before the waveform becomes audible. Retained envelope level and SID rate-counter history prevent treating nominal ADSR times as a measured attack trajectory. This is an audible-body hypothesis, not an assertion that slower attack always gives more punch or a recreation of Hülsbeck’s retriggering.

[Preparation and guards](../../scripts/studies/axel-f/prepare-timbre.py) retain the score, rhythm, full note/gate schedule, pulse/wave/pitch programs and bass patch. The chip trial must keep every ordered register value unchanged; the contour trial permits changes only to lead AD/SR and drum AD. Native TEST remains because a sounding first-frame waveform would expose an incomplete frequency word on this player. Neither the shared player nor the accepted full tonal baseline is modified.

Model-assistance review: no new model call. The immediately preceding authorized Qwen trial failed digital silence; its descriptions remain excluded. Source execution, isolated PCM diagnostics and human audition address this question. Reassess usefulness at the selected complete rendition, without assuming another paid trial.


The [verified listening record](timbre-review.json) and [retained boundary/PCM evidence](../../evidence/axel-f-timbre/mechanism.json) confirm identical note/gate schedules for all three renders and all 24,699 ordered store identities. The chip trial changes no register value; the contour trial changes only `$D405/$D406/$D40C`. Both standalone variants pass sampled VICE checks. All 82 percussion diagnostic windows remain nonzero, no render clips, and pre-stop release AC RMS is zero in all three versions. The rebuilt baseline WAV is byte-identical to the preferred varied-rhythm audition. Both published pairs are exact 8.067216-second PCM windows with a half-second separator and common unity gain. The contour version has a lower overall AC RMS (2,738 versus 3,272 PCM16 units) and higher peak (13,198 versus 11,537), which verifies changed dynamics without establishing perceptual punch.

The user reports **“No useful difference”** for [8580 then 6581](../../build/axel-f-timbre-listening/8580-then-6581.ab.wav). Retain MOS8580 for this interpretation. This result narrows the immediate cause of dissatisfaction; it does not establish hardware/model equivalence or a universal preference. For the [current then revised-envelope comparison](../../build/axel-f-timbre-listening/current-then-envelope.ab.wav), the listener reports “The envelopes improve a bit, but the lead instrument sound ticked off, which is relevant”, clarified as “Notes sound cut short”. Preserve the relative improvement without claiming independent drum acceptance; the shortened lead release is the next isolated correction. [Current full hook](../../build/axel-f-timbre-listening/varied-8580.wav), [revised-envelope full hook](../../build/axel-f-timbre-listening/varied-8580-envelope.wav), and the [master passage](../../build/axel-f-master-palette-matched-listening/huelsbeck-lead-and-beat-9.5-20s.wav) retain context and release tails.

```sh
python3 scripts/listening-package.py config/listening/axel-f-timbre.json --output build/axel-f-timbre
python3 scripts/publish-listening.py build/axel-f-timbre/run.json --selection config/listening/axel-f-timbre.audition.json --output build/axel-f-timbre-listening
```


## Restore the lead tail without changing the rhythm

The unresolved question is whether restoring the previous lead release removes the cut-short quality while retaining the modest envelope improvement. This blocks timbre selection for full integration. The [release-only patch](lead-tail.patch.json) changes `0847` to `0849`; decay, sustain, drum programs, varied rhythm and all tonal notes remain fixed. The [recipe](../../config/listening/axel-f-lead-tail.json) applies the existing checked patch tool and verifies the intervention against the complete native hook execution. This is a correction to the audition, not selection of a new full-song baseline.

The [review record](lead-tail-review.json) and [retained evidence](../../evidence/axel-f-lead-tail/boundary.json) confirm unchanged note schedules and 24,699 ordered store identities, with values changing only at lead SR `$D406`. All 987 post-call frames agree outside that register; standalone VICE checks cover initialization, the phrase and ending. The candidate is unclipped and its pre-stop release is quiet. The previous WAV is byte-identical to the submitted contour version; the common-unity-gain pair contains exact 8.067216-second PCM windows separated by half a second. These checks establish a controlled comparison, not natural-sounding articulation.

Listen to [short release then restored tail](../../build/axel-f-lead-tail-listening/short-then-restored-release.ab.wav), with the complete [short-release hook](../../build/axel-f-lead-tail-listening/short-release.wav), [restored-release hook](../../build/axel-f-lead-tail-listening/restored-release.wav) and [Hülsbeck reference](../../build/axel-f-master-palette-matched-listening/huelsbeck-lead-and-beat-9.5-20s.wav) available separately. The reference remains an arrangement/timbre reference with different key, tempo and accompaniment. The listener prefers the correction: “restored-release is better”, but still wants Hülsbeck’s “lagging/fade out kind of tune in the main voice”, associated with chiptuning. Retain the restored release for the next comparison; this does not accept the complete lead character. Model-assistance review: no additional call is useful for this scoped correction after the preceding silence-control failure; reassess at the selected full rendition.

```sh
python3 scripts/listening-package.py config/listening/axel-f-lead-tail.json --output build/axel-f-lead-tail
python3 scripts/publish-listening.py build/axel-f-lead-tail/run.json --selection config/listening/axel-f-lead-tail.audition.json --output build/axel-f-lead-tail-listening
```


## Trailing lead character: delayed downward pitch motion

After preferring the restored release, the listener still hears a “lagging/fade out kind of tune in the main voice” in Hülsbeck’s version and associates it with chiptuning. This identifies a desired character, not a uniquely identified synthesis mechanism. The next decision is whether stronger late-note pitch motion moves the lead toward that character; the preferred release and varied rhythm remain the baseline while listening settles it.

The executed first source lead note supplies a bounded hypothesis. Its frequency word stays at 7,493 for 18 calls, then moves downward by 160-word steps, ranging from 7,173 to 7,653 while continuing through GATE-off. At the source cadence this begins around 327 ms, with excursions of approximately −75.6/+36.6 cents. Our restored-release lead starts its much shallower motion upward at call 14 (279 ms), around ±11 cents. Pulse-width motion already continues during release in both implementations. Neither this observation nor the word “fade” proves that vibrato explains the perceived difference; an echo or amplitude change has not been established by this comparison.

The [editable pitch-motion patch](lead-motion.patch.json) changes native control `1A→3A`, vibrato `24→83` and delay `12→14`. The [recipe](../../config/listening/axel-f-lead-motion.json) retains ADSR `0849`, all pulse/wave programs, every note/gate schedule and both other voices. The executed first-note trajectory begins downward at call 16 (319 ms), reaches approximately −69.5 cents and returns to the target in a six-call cycle. This is a native downward-biased adaptation, not recovery of the source’s asymmetric excursions: it has no above-target crest and runs at PAL VBI cadence rather than the source CIA cadence. The pinned Extra player’s `SETVIBR`/`DOVIBRA` behavior and actual frequency stores, rather than parameter names alone, settle its direction and size.

The [review](lead-motion-review.json) and [pitch diagnostic](../../evidence/axel-f-lead-motion/source-motion-diagnosis.json) retain the measured trajectories. Across 987 complete calls, frame differences occur only in lead frequency offsets 0/1, and all 24,699 ordered store identities agree with changed values confined to `$D400/$D401`. Sampled standalone VICE checks pass through the ending. The full hook is unclipped and quiet before the terminal volume clear. The baseline WAV is byte-identical to the preferred restored-release audition. The exact PCM pair uses common unity gain, 8.067216 seconds per half and a half-second gap; measurable differences establish delivery, not musical acceptance.

The submitted [restored lead then trailing vibrato](../../build/axel-f-lead-motion-listening/restored-then-trailing-vibrato.ab.wav) compares only this pitch program. The full [preferred hook](../../build/axel-f-lead-motion-listening/restored-release.wav), [pitch-motion candidate](../../build/axel-f-lead-motion-listening/trailing-vibrato.wav) and [Hülsbeck reference](../../build/axel-f-master-palette-matched-listening/huelsbeck-lead-and-beat-9.5-20s.wav) retain context. The master differs in key, tempo, chip and accompaniment. Feedback is pending; do not integrate this patch across the full arrangement or apply it to the separately preferred high-lead/held-support roles on the strength of numeric checks.

Model-assistance review: no new call. The preceding authorized Qwen trial failed silence, and the current question needs human attribution and preference rather than another unqualified description. Reassess at the selected full rendition.

```sh
python3 scripts/listening-package.py config/listening/axel-f-lead-motion.json --output build/axel-f-lead-motion
python3 scripts/publish-listening.py build/axel-f-lead-motion/run.json --selection config/listening/axel-f-lead-motion.audition.json --output build/axel-f-lead-motion-listening
```
