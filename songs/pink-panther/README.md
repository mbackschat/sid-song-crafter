# The Pink Panther Theme: character-first SID audition

The brief is a light, sly, mischievous jazz interpretation. [Mood research and source intake](../../docs/research/composition/pink-panther-preparation.md) distinguish the original theme's character from D. W. Barnes's MIDI arrangement, which supplies our notes. [Mancini's official recording](https://www.youtube.com/watch?v=dtnNO5_Ao6U) is the artistic reference; the generated plain rendering below checks the selected musical material. On 2026-10-15 the listener called our audition “quite good”; that acceptance covers the excerpt, not a completed full-form interpretation.

## Hear the first trial

- [Plain then SID](../../build/pink-panther-theme-listening/plain-then-sid.ab.wav): 40.5 seconds, 20 seconds per version with a half-second gap.
- [SID passage](../../build/pink-panther-theme-listening/pink-panther-sid.wav) and [matching plain reference](../../build/pink-panther-theme-listening/plain-reference.wav): 38.29 seconds each, including release and verification tail.
- [Listening status, hashes and measurements](listening-review.json): positively reviewed (“The SID version is quite good.”).

This is an excerpt from source beats 107/3 through 100, retaining the main theme's chromatic pickup and four phrases. It contains 34.77 seconds of source music. No selected source note crosses its boundaries, but the bass and accompaniment approach the next section near the end: this is an audition stop, not an authenticated tonic cadence or the source song's ending. The complete 196.76-second source arrangement remains preserved for later work.

## Map intent to the chip

| Role | Editable choice in [native.json](native.json) | Musical hypothesis and boundary |
| --- | --- | --- |
| Light foreground with some reed-like colour | Saw body, ADSR `$2674`; lead alone owns a low-pass contour from cutoff 832 toward 736, resonance 1. | Soften upper harmonics while retaining more colour than the plain triangle. This is a SID interpretation, not a physical saxophone model. |
| Expression on held notes | Delayed vibrato `$14`, delay 16 PAL calls; no pitch scoops or added noise transient. | Preserve each chromatic attack, then introduce motion. SID-Wizard's low nibble sets the period: `$14` is about 6.27 Hz at 1x PAL, unlike the roughly 12.53 Hz `$12` initially considered. The amplitude nibble controls pitch step, not a fixed cents excursion. |
| Walking bass that leaves room | Independent source bass, triangle, ADSR `$0533`, unfiltered. | A defined arrival and lighter sustain rather than a heavy held pulse or an added kick. |
| Sparse harmonic support | Highest simultaneous source piano-accompaniment note, triangle, ADSR `$0312`, unfiltered. | Keep source placement without filling every chord across multiple voices. Omitted chord tones and entire omitted parts remain explicit. |

The filter program and delayed modulation reuse existing native table mechanisms; the envelopes are adapted for this musical role. [LEAD-02](../../docs/research/composition/instruments/lead-02-moving-pulse.md), [BASS-02 filter semantics](../../docs/research/composition/instruments/bass-02-kick-to-bass.md), [soft pluck evidence](../../docs/research/composition/instruments/pluck-01-bright-attack.md) and [Moon River's lesson](../moon-river/README.md) informed selection. Prior listening approval of those studies does not approve this palette.

The [projection](reduction.json) retains 145 of 360 selected notes: 71 melody, 44 bass and 30 accompaniment. The 215 omissions are individually traceable to the complete 2,113-note source. Source swing is already encoded; no second swing transform, new pitch, transposition or note-duration extension is applied. Native frame quantization and gate timing still follow the [existing converter contract](../../docs/workflows/native-song-workflow.md). Source velocities survive in the common score and origin records, but this trial uses fixed per-role envelopes; it does not yet reproduce phrase dynamics or legato marks. The plain reference uses a different whole palette, so this is not an isolated lead/filter comparison.

## Reproduce

Prepare the [native tools](../../docs/workflows/native-song-workflow.md), then use fresh output and publication directories:

```sh
python3 scripts/setup-project.py --only references --include pink-panther-score
python3 scripts/listening-package.py config/listening/pink-panther-theme.json --output build/pink-panther-theme-reproduction
python3 scripts/publish-listening.py build/pink-panther-theme-reproduction/run.json --selection config/listening/pink-panther-theme-audition.json --output build/pink-panther-theme-reproduction-listening
```

The [recipe](../../config/listening/pink-panther-theme.json) prepares, builds, audits, renders, checks standalone VICE execution and creates the comparison. Both versions use PAL MOS8580 and the same score; NTSC and stereo are separate validation targets. The candidate passes 1,921 CPU calls, all 145 note starts and the stop at call 1,868; VICE checkpoints extend through 1,905. Its audio has no clipping and a quiet verification tail. These checks do not settle musical character or whether the excerpt boundary feels complete.

## Reuse assessment

| Area | Outcome and next-song consequence |
| --- | --- |
| Existing capabilities | Reused the MIDI importer, native instrument tables, exporter, CPU audit, renderer, VICE verifier, comparison tool, cached recipe runner and stable audition publisher. No new synthesis engine. |
| Concrete preparation gap | The older reducer accepts two source parts. The new [configurable audition projection](../../docs/workflows/song-workflow.md#prepare-a-multitrack-score-audition) selects passages and maps three parts from a larger score, retaining exact source origins and declared omissions. The next compatible MIDI changes configuration instead of requiring another song-specific script. |
| Evidence of reuse | Independent synthetic six-part MIDI tests use different part names and two noncontiguous spans. The actual Barnes source exercises the same command. This verifies the narrow preparation contract, not arbitrary musical reduction quality. |
| Routine execution | The first recipe run took 33.05 seconds; an unchanged repeat took 0.24 seconds with every stage reused and no stage subprocesses. These measured times exclude research, adapter implementation and review; they do not establish total productivity improvement over Moon River. |
| Remaining judgment | Mood, passage boundaries, omitted voices, palette balance and useful expressive gestures still require musical decisions. A note-safe boundary can still leave a harmonic approach unresolved. Source velocities and full-form contrast need explicit treatment when extending this trial. |

At this audition checkpoint, no model call is justified: the current [audio-model calibrations](../../docs/research/audio-assessment.md) do not validate subtle character or preference judgments on this source. Reassess after listener feedback and before closure. Keep the reference MIDI, imported notes and generated audio local; public files retain source fingerprints, configuration and reproducible commands.

## Learn from the selected BASIC interpretation

The listener selected Stan Kicak’s **Pink_Panther_BASIC.sid** and praised its main instrument as matching the intention. The earlier non-BASIC filename is superseded as the comparison target. Listen to the [BASIC then ours comparison](../../build/pink-panther-basic-listening/basic-then-ours.ab.wav), 40.5 seconds: BASIC main-theme passage first, our existing audition second. Whole-mix AC RMS is matched by attenuating BASIC by 5.6043 dB; ours stays at unity. These are different arrangements, registers and timings, not an isolated timbre test. Original-level files: [external BASIC interpretation](../../build/pink-panther-basic-listening/external-pink-panther.wav), 103 seconds including startup and natural stop, and [our unchanged excerpt](../../build/pink-panther-basic-listening/our-pink-panther.wav).

The [reference receipt](basic-reference.json) pins the source, ROMs, renderer, audio and trims. The [instrument evidence](basic-instrument-evidence.json) records BASIC line locations and initialized register observations without redistributing the source program or score. Source NTSC is declared; MOS6581 is explicitly assumed because the header leaves the chip model unspecified. Our audition is PAL MOS8580. Do not attribute the whole perceptual difference to the patch alone.

| Verified property | BASIC reference | Our existing audition |
| --- | --- | --- |
| Lead waveform | Fixed pulse `$41`, width `$F37` (3895/4096 threshold, about 4.9% narrow complement) | Saw `$21` |
| Main melody envelope | AD `$09`, SR `$22`; intro and supporting voices use `$0A/$29` | AD `$26`, SR `$74` |
| Continuing effects | No PWM, vibrato, sync, ring modulation or filter | Low-pass contour and delayed vibrato |
| Articulation | Score explicitly distinguishes reattack from connected retuning; zero-frequency rests retain gate | Native tempo-1 note/gate policy: hard restart bypassed; adjacent notes without gate-off also stay connected |

The reference demonstrates a liked sound with few moving parameters. A narrow-pulse spectrum, lower sustain and selective rearticulation are plausible contributors, but the user’s approval of the whole instrument does not establish which parameter caused it. The BASIC interpreter also separates high- and low-frequency writes enough to expose intermediate words in snapshots; this is an implementation observation, not a proven desirable effect to copy.

**Evidence priority:** the established master-composer studies remain the primary repertoire and arrangement foundation. This BASIC song is a supporting, song-specific contrast. Cross-reference [Airwolf’s accepted static pulse transfer](../../docs/research/composition/instruments/airwolf-static-tones.md) and [Ghostbusters’s score-owned articulation](../../docs/research/composition/instruments/ghostbusters-decoded-programs.md); neither implies that their patches or this BASIC patch fit every song. Add another master reference only to answer a concrete unresolved musical or technical question. Do not replace the master studies with a collection of convenient BASIC presets.

Recreate the external comparison after preparing the original audition above. The commands reuse the existing downloader, ROM-backed renderer, cached recipe runner, PCM comparison and publisher; no new song-specific execution script is needed:

```sh
python3 scripts/setup-project.py --only references --include pink-panther-basic
python3 scripts/listening-package.py config/listening/pink-panther-basic.json --output build/pink-panther-basic-reference
python3 scripts/publish-listening.py build/pink-panther-basic-reference/run.json --selection config/listening/pink-panther-basic-audition.json --output build/pink-panther-basic-listening
```

Publication requires a fresh destination. The raw capture is 150 seconds; the full listening copy retains frames `[0,4542300)` at 44100 Hz without gain or fade, and its final second has zero AC energy. The comparison selects raw BASIC seconds 17.45–37.45, just before the main melody pickup, and our seconds 0–20. Native reference-intake currently requires a declared chip model and lacks ROM arguments, so this case deliberately uses its supported lower-level recipe runner rather than weakening that admission contract. This is a recorded automation gap, not a reason to create a parallel intake framework.

## Independent lead transfer: insufficient vibrancy

Listen to [baseline then pulse](../../build/pink-panther-pulse-transfer-listening/baseline-then-pulse.ab.wav), 40.5 seconds: 20 seconds of our liked audition, half a second of silence, then the identical score/backing with the static pulse lead. Both halves retain unity gain so the changed lead’s actual balance remains audible. Separate full excerpts: [baseline](../../build/pink-panther-pulse-transfer-listening/accepted-sid-baseline.wav) and [pulse transfer](../../build/pink-panther-pulse-transfer-listening/basic-inspired-pulse-transfer.wav). This is a whole-lead-patch substitution, not an isolated pulse-width test.

The editable [transfer palette](basic-inspired.json) uses exact width `$F37`, waveform `$41`, ADSR `$0922`, no vibrato and no filter. It retains our source score, arrangement, bass, harmony and native gate/TEST scheduling; BASIC legato and interpreter timing are not reconstructed. The target remains PAL MOS8580. The listener reports that the external version is “much much more vibrant” and this transfer misses its “vibrato kind of instrument”. The patch transfer does not capture the desired character; retain it as a rejected comparison, not an accepted reusable solution. No explicit vibrato loop was found in the BASIC program, but that does not explain away perceived motion in the full mix. Investigate articulation, simultaneous voices, register and rendering before treating the patch bytes as a complete sound definition.

The [transfer receipt](pulse-transfer-review.json) records unchanged score/native scheduling, identical bass/harmony registers over all 1,921 snapshots, exact pulse/ADSR over 1,850 active pulse frames, CPU checks and VICE beyond the stop. Rebuilt baseline PCM is byte-identical to the accepted audition. No clipping occurs, and the final half-second is silent. These checks establish the substitution, leaving musical fit to listening.

```sh
python3 scripts/listening-package.py config/listening/pink-panther-pulse-transfer.json --output build/pink-panther-pulse-transfer
python3 scripts/publish-listening.py build/pink-panther-pulse-transfer/run.json --selection config/listening/pink-panther-pulse-transfer.audition.json --output build/pink-panther-pulse-transfer-listening
```

The transfer uses the existing native builder, register comparator, VICE verification and cached workflow. Only an editable palette and recipe are new; the unchanged repeat took 0.201 seconds with all eight stages reused. This is routine execution reuse, not a measurement of total musical decision time. The model-assistance review again found no calibrated model useful for this subtle preference; reassess after feedback or before closure.

## BASIC intervention limit

A source-copy diagnostic changed only the main melody patch’s width, leaving score bytes, envelope, other instruments and BASIC links intact. Both a four-byte `$F37`→`$800` edit and a one-byte `$F37`→`$C37` edit shifted observed frequency/gate timing. Therefore neither is presented as a clean pulse-width listening experiment. The changed numeric DATA text is a plausible interpreter-timing mechanism, not independently traced. Byte-local changes do not guarantee timing-local changes; snapshot evidence detects the confound but does not establish its exact cause, cycle cost or audibility.

The independent native transfer above is the useful musical test: it preserves a verified common note schedule, with its deliberate whole-patch changes disclosed. It does not establish that width alone explains the source preference. Stop the source-intervention branch here rather than adding ad hoc timing corrections to make the diagnostic appear isolated.

The [diagnostic receipt](width-diagnostic-review.json) retains source-byte and register evidence; the [guarded study tool](../../scripts/studies/pink-panther/probe-width.py) and [cached recipe](../../config/listening/pink-panther-width-diagnostic.json) reproduce the failed isolation check without publishing the source binary. Run `python3 scripts/listening-package.py config/listening/pink-panther-width-diagnostic.json --output build/pink-panther-width-diagnostic-package`. A completed recipe means the inspection ran; its `snapshotIsolationPassed: false` explicitly rejects the experimental premise. Four synthetic-fixture tests cover source pinning, BASIC link preservation, exact one-byte scope and rejection of timing-confounded snapshots.

## Locate the missing vibrato-like character

After the static transfer, the listener reports: “external-pink-panther.wav is much much more vibrant . YOur pulse misses this vibrato kind of instrument...” This rejects the transfer’s musical adequacy, not the measured pulse settings. A patch-byte match is insufficient evidence that the source’s perceived instrument has been reproduced.

Start with [external intro, full mix then lead alone](../../build/pink-panther-intro-motion-listening/intro-full-then-lead.ab.wav), 16.5 seconds: raw source seconds 2–10 twice, separated by half a second. This includes the intro body where measurable ensemble motion is strongest. Both halves are from the original, at unity gain. The following main-theme check tests the later, different patch context.

Listen to [external full mix then its lead alone](../../build/pink-panther-motion-listening/full-then-lead-diagnostic.ab.wav), 28.5 seconds: source seconds 17.45–31.45, a half-second gap, then the same original lead with its accompaniment muted. This is entirely the external interpretation, not a new candidate. Separate [full passage](../../build/pink-panther-motion-listening/external-main-theme.wav) and [lead diagnostic](../../build/pink-panther-motion-listening/external-lead-only-diagnostic.wav) preserve unity gain. The reference uses no ring/sync/filter coupling or SID read dependencies in this passage; register snapshots stay unchanged under the renderer’s diagnostic voice mask.

The [motion inspection](motion-diagnostic-review.json) finds steady lead pitch in sampled held-note bodies, while the full intro mix has substantial narrow-band amplitude and phase movement around the same harmonic. This supports ensemble interaction as a candidate explanation, not a proven explanation of the listener’s perceptual label or every note in the song. The initial main-theme pickup occupies the same register in both arrangements; do not assume an octave mismatch. Source articulation and later register changes still differ.

The listener confirms: “No, the vibrant, vibrato-like quality does NOT remain in the second half.” This verdict applies to the intro pair: the supporting voices or their interaction with the lead are necessary for the desired perceived quality in this audition. It does not isolate which supporting voice matters or prove a particular harmonic-beating mechanism. Keep the lead and score fixed and test the accompaniment’s spectral/body contribution next; adding lead vibrato would not follow this evidence. This is the [master-study execution method](../../docs/research/tools/sid-program-analysis.md) applied to a supporting reference, with a bounded listening checkpoint rather than another ungrounded preset trial.

```sh
python3 scripts/listening-package.py config/listening/pink-panther-motion-diagnostic.json --output build/pink-panther-motion-diagnostic
python3 scripts/publish-listening.py build/pink-panther-motion-diagnostic/run.json --selection config/listening/pink-panther-motion-diagnostic.audition.json --output build/pink-panther-motion-listening
```

The source and candidate are unchanged. Model assistance was reviewed after feedback: current calibrations do not establish subtle timbral cause; use source execution, signal measurements and this focused listening check. Reassess after the next revision or before closure.

To publish the intro diagnostic from the same run, use `python3 scripts/publish-listening.py build/pink-panther-motion-diagnostic/run.json --selection config/listening/pink-panther-intro-motion.audition.json --output build/pink-panther-intro-motion-listening`. Choose a fresh directory on repetition.

## Test the accompaniment’s contribution

The intro subtraction verdict localizes the desired quality to supporting voices or their interaction with the lead. The next bounded trial preserves our existing 145-note reduction, all timing and the rejected static-pulse transfer’s lead, and changes only its two supporting patches: triangle bass/harmony become static narrow pulses `$41/$F37`, AD/SR `$0A/$29`, matching the supporting patch in the historical reference. No lead vibrato, PWM, new notes, octave change or filter is introduced.

This is a test on our existing main-theme score, not a reconstruction of the reference intro’s voicing. The reference’s longer held intervals, selective rearticulation and score reduction remain relevant differences. A positive result would support this palette in this arrangement; a negative result would direct attention to voice placement, note overlap and articulation rather than justify stronger lead modulation.

The study follows the primary repertoire’s role-based approach: [DRAX’s coordinated bass/lead/chord analysis](../../docs/research/composition/instruments/drax-decoded-trio.md) separates perceived richness from an individual lead program, and [Shades’ independent voice and articulation constraints](../../docs/research/composition/instruments/shades-decoded-programs.md) show why simultaneous trajectories and note lifetimes belong to the instrument context. Their original drivers and patch parameters are not transplanted into this case. The BASIC palette is the specific supporting hypothesis under test, while the master studies continue to guide the method and wider repertoire.

The [ensemble palette](ensemble-pulse.json) and [trial receipt](ensemble-transfer-review.json) are ready. Listen to [previous backing then pulse ensemble](../../build/pink-panther-ensemble-listening/baseline-then-ensemble.level-matched.ab.wav): 20 seconds of the previous static-lead/triangle-support version, half a second of silence, then the same passage with pulse support. The second half is attenuated by 6.052 dB to match overall AC RMS; each version’s internal balance is preserved. The verified lead identity applies before this whole-mix listening gain. Full original-level versions are [baseline](../../build/pink-panther-ensemble-listening/static-lead-triangle-backing.wav) and [ensemble candidate](../../build/pink-panther-ensemble-listening/static-lead-pulse-ensemble.wav), 38.29 seconds each. Judge whether the ensemble restores useful vibrancy while keeping the melody clear; listening acceptance remains pending.

Both versions pass 1,921 CPU calls and all 1,922 VICE checkpoints including initialization. Lead registers, note events, every voice’s pitch/gate/TEST schedule and shared controls match; only declared supporting waveform, pulse-width and ADSR fields differ. The render has no clipping and its final half-second has zero AC energy. These are implementation checks, not an audible beating diagnosis or balance verdict. The unchanged recipe repeat reuses all eleven stages in 0.464 seconds; no new general-purpose code was needed.

```sh
python3 scripts/listening-package.py config/listening/pink-panther-ensemble-transfer.json --output build/pink-panther-ensemble-transfer
python3 scripts/publish-listening.py build/pink-panther-ensemble-transfer/run.json --selection config/listening/pink-panther-ensemble-transfer.audition.json --output build/pink-panther-ensemble-listening
```

Model assistance was reviewed after this revision: use the established register/score/audio checks and the focused listener verdict; current model calibrations do not validate this vibrancy/balance judgment. Reassess after feedback or at closure.
