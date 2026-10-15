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

The listener strongly accepts the level-matched pairing: “the "Hülsbeck-informed combination second" is so much better!!!” and “The "Hülsbeck-informed combination second" has just the right choice of instruments”. This settles the tested ensemble choice, not which individual parameter caused the preference or whether it works across the complete arrangement. Extend the pairing across its existing lead and bass roles, preserving the separately preferred rounder high lead, held-support treatment, source notes and form. Keep the undecided percussion balance separate.

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
