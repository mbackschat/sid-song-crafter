# The Pink Panther Theme: character-first SID audition

The brief is a light, sly, mischievous jazz interpretation. [Mood research and source intake](../../docs/research/composition/pink-panther-preparation.md) distinguish the original theme's character from D. W. Barnes's MIDI arrangement, which supplies our notes. [Mancini's official recording](https://www.youtube.com/watch?v=dtnNO5_Ao6U) is the artistic reference; the generated plain rendering below checks the selected musical material. Neither establishes musical acceptance of our SID version.

## Hear the first trial

- [Plain then SID](../../build/pink-panther-theme-listening/plain-then-sid.ab.wav): 40.5 seconds, 20 seconds per version with a half-second gap.
- [SID passage](../../build/pink-panther-theme-listening/pink-panther-sid.wav) and [matching plain reference](../../build/pink-panther-theme-listening/plain-reference.wav): 38.29 seconds each, including release and verification tail.
- [Listening status, hashes and measurements](listening-review.json): pending. Judge whether the lead, groove and support convey a sly, light, playful character together.

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
