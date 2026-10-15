# Axel F: restore musical roles and rhythmic contrast

The narrow-pulse hook was accepted, but the complete arrangement was not. The listener reported an annoying persistent background sound at 64.60–68.80 seconds, an annoying lead at 120–140 seconds, and an interpretation that is boring compared with Hülsbeck. The [full review](full-huelsbeck-pulse-review.json) retains both the earlier scoped acceptance and these objections. The current musical task is broader than another pulse-width adjustment.

## Two roles incorrectly treated as the same lead

| Passage | Score and executed behavior | Arrangement decision |
| --- | --- | --- |
| Held chord at 64.54–68.73 seconds | The reduction selects B♭4 from a four-note source chord and assigns it the hook's foreground pulse. Physical voice 1 has 207 consecutive gated body updates, then correctly clears GATE at 68.689 seconds. It is an intentional sustained note, not a stuck gate. | Keep the source pitch and duration, but give the held chord top the existing quieter `PLUCKSOF` triangle program. The entire beats 128–156 section contains just this one melody-voice event. |
| High lead at 118.98–139.05 seconds | A distinct source part supplies 97 notes at A♭5–E♭6. Their bodies last only 3–12 updates. Every pulse onset resets to `$200`, reaches at most `$381` while gated, and ends before the developed modulation heard in the hook. | Use the existing `ELSOFT` triangle program for the high lead in beats 236–276, preserving its pitches and rhythm. Keep its sustain/release distinct from the marimba accompaniment. |
| Hook returns and the high descent | These are different roles from the held chord and later high lead. A separate long F5 in the descent also has correct sustained gating; no listening complaint was reported there. | Retain the preferred moving-pulse lead; avoid a global patch replacement based on two role-specific objections. |

The first row's source event is from `held-chord-and-descent`, source beat 132; trimming the four initial silent beats places it at arranged beat 128. The later high lead comes from its own source track, not the hook track. The initial mapping preserved those origins in the adaptation report but did not use them when assigning timbre. That is the arrangement error: a physical voice carrying several score parts does not make them one musical role.

The high lead's measured frequency variation is just one frequency-word unit during each gated body; delayed vibrato does not develop there. Increasing the same delayed effect would miss the actual short-note behavior. A source-correct pitch can still have the wrong spectrum, prominence and articulation for its register. The proposed triangle programs reuse existing patches, but their prior acceptance does not establish that this new context works musically.

Detailed diagnosis remains private under `build/axel-f-held-diagnosis/`, with source/conversion/frame fingerprints and event-specific evidence. The source MIDI, native note schedule and prior listening files remain unchanged.

## What the master reference adds beyond lead PWM

The [bounded arrangement evidence](huelsbeck-arrangement-observations.json) combines the existing 1,600-call CPU/VICE capture with 60 seconds of renderer snapshots. It shows three contrasting roles: percussion on physical voice 3, a pulse hook entering on voice 2 after the percussion introduction, then a low pulse bass entering on voice 1. The percussion alternates noise-to-falling-triangle, short noise and longer noise programs. It is not merely a transient before every bass note. The additional renderer interval is not a new ordered CPU-write or hardware-equivalence proof. Reproduce the source-pinned capture with the [master-study recipe](../../config/listening/axel-f-huelsbeck-study.json), then the additional renderer interval with the [60-second opening recipe](../../config/listening/axel-f-huelsbeck-opening.json); commands are retained in the aggregate.

This suggests useful design choices: independent percussion envelopes, contrasting bass and lead behavior, staged entrances, and space between phrases. These observations identify mechanisms available for arranging; they do not establish which one explains the listener's overall preference. The reference also differs from our score in key, tempo, form and chip model, so it is not a same-score fidelity comparison.

Our tonal reduction omitted all percussion even during sections where a voice was idle. In arranged beats 64–96, the hook and bass occupy two voices and the harmony voice is silent. The source has 48 kick events there. Each coincides with a bass onset, so restoring them adds a separate percussion body and envelope, not a new onset rhythm. By contrast, all three tonal roles are active during the later high lead; an independent drum there needs an explicit allocation tradeoff.

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

The [kick review](kick-trial-review.json) pins its separate source-backed experiment. Its 146 notes pass 987 CPU calls and sampled VICE checks through call 980. Forty hits retain three gated updates of the low C1 body; three retain one, and five retain none because the next source hit arrives too soon. The unchanged lead and bass preserve their own envelopes and the bass remains the sole filter owner. This is a bounded percussion test, not the complete drum arrangement.

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

The three listening verdicts remain pending. If the role corrections help, retain them without changing the accepted hook. If the kick helps, assess source-supported percussion and section contrast across the form before extending it; a repeated kick alone does not solve the broader musical criticism. Model assistance remains no-call at this checkpoint for the reasons above; reassess after feedback or a substantive revision.
