# The Pink Panther Theme: source preparation

The first [SID audition and reuse assessment](../../../songs/pink-panther/README.md) are ready after mood research. Its source preparation, reduction and technical playback pass; the listener calls the first audition “quite good”. Follow the [source-to-SID workflow](../../workflows/song-workflow.md), keeping the complete source separate from later reductions and musical changes.

## Source and scope

The optional `pink-panther-score` entry in the [asset registry](../../../config/local-assets.json) pins the [public MIDI](https://www.dongrays.com/midi/archive/tv-film/ppanther.mid) at ignored `.local/research/pink-panther/dw-barnes-ppanther.mid`. Its embedded metadata and [catalogue entry](https://www.dongrays.com/midi/archive/tv-film/) credit Henry Mancini as composer and D. W. Barnes as sequencer. This is Barnes's arrangement, not an authenticated original edition. The archive's [legal notice](https://www.dongrays.com/midi/) does not establish redistribution or adaptation permission; public availability is not an open-license claim. Keep the original MIDI, imported notes and reference audio outside Git.

Inspection on 2026-10-15 verifies a format-1 MIDI with nine tracks, six sounding parts, 96 ticks per quarter, constant 4/4 and 540,540 microseconds per quarter (approximately 111 BPM). Its complete sequential timeline spans 364 quarter beats, or 196.75656 seconds. That covers the supplied arrangement through its ending; equivalence to the original film score's form has not been established. No repeat unfolding or source truncation is applied.

| MIDI track, zero-based | Preserved part | Source role |
| --- | --- | --- |
| 1 | `piano-lead` | Piano melody, including the introduction |
| 2 | `piano-accompaniment` | Polyphonic harmonic accompaniment |
| 3 | `alto-sax` | Later melody doubling |
| 4 | `baritone-sax` | Low accompaniment |
| 5 | `bass` | Independent bass part |
| 6 | `drums` | GM percussion; retain its drum mapping from the original MIDI |

Swing is already encoded: common offbeat attacks occur at tick 64 of each 96-tick quarter. Preserve exact rational onset and duration values instead of applying a second swing transform. Additional subdivisions occur, so a universal swung-eighth quantization would also lose source timing.

## Reproduce and inspect losses

Use the existing checksum-verifying downloader and [import recipe](../../../config/scores/pink-panther-import.json):

```sh
python3 scripts/setup-project.py --only references --include pink-panther-score
python3 scripts/setup-project.py --check --only references --include pink-panther-score
PYTHONPATH=.tools/arrangement-deps python3 scripts/import-midi.py .local/research/pink-panther/dw-barnes-ppanther.mid config/scores/pink-panther-import.json build/pink-panther-source-intake/source.common-score.json
```

The 2026-10-15 smoke import preserves all 2,113 source notes across the six sounding tracks, with matched positive-duration note pairs and no added trailing rest. The importer checks the source hash and requires every sounding track to remain represented. Its generated loss report retains 25 unmapped controller messages (volume, pan, reverb and chorus), six GM program changes and one instrument-name message. Channel identities and note-off velocities are not represented in common-score v1; the original MIDI retains them. There are no source pitch-bend or sustain-controller messages. Engraved spelling, slurs, articulation marks and repeat notation cannot be recovered from this MIDI alone.

The imported score proves source preservation within that contract. The [audition](../../../songs/pink-panther/README.md) now applies an explicit three-voice reduction and native palette. The first excerpt and the [complete sourced ensemble interpretation](../../../songs/pink-panther/README.md#complete-sourced-arrangement) are now accepted, including the full version’s ending. This verdict covers the declared PAL MOS8580 three-voice interpretation.

## Mood and interpretation brief

Research checked on 2026-10-15 establishes a light, mischievous jazz character with rhythmic precision and room for contrast. “Sly”, “cool” and “playful sneaking” are our concise interpretation target, not a quotation from Mancini or a claim that the entire piece stays quiet. The evidence below concerns the original theme or explicitly identified teaching arrangements; Barnes's MIDI remains the separately preserved note/form source.

| Evidence | Supported finding and boundary |
| --- | --- |
| [Mancini official site, “10 Essential Henry Mancini Recordings”, Pink Panther entry](https://www.henrymancini.com/blogs/news/10-essential-henry-mancini-recordings-from-moon-river-to-the-pink-panther-theme-1) | Describes the theme as jazzy and mischievous and relates its melody to Plas Johnson's light tenor-sax playing. This is contextual editorial prose hosted by the composer's estate, not a first-person composition statement. It supports lightness and individual phrasing rather than a generic forceful brass lead. |
| [National Arts Centre, *The Composer is Dead* teacher guide, PDF p.9](https://naccna-assets.s3.amazonaws.com/composer_teacher_study_guide_jan_2016.pdf) | Identifies the tenor line's dotted-eighth/sixteenth and triplet mixture as a source of the sneaky comic character. Use this specific rhythmic observation; it does not authenticate Barnes's sequencing or prescribe one universal swing ratio. |
| [RSL Classical Guitar sample pack, printed p.32, performance notes](https://www.rslawards.com/download/8415/) | Calls for a sophisticated, mysterious character, a clear melody, sustained notes, attention to the phrase's arch and deliberate dynamic contrast. These are RSL's performance recommendations for its own guitar arrangement, not recovered markings from Mancini's original score. Its bar numbers, ending chord and suggested dynamics must not silently replace Barnes's arrangement. |

Use [Henry Mancini, “The Pink Panther Theme (From The Pink Panther)” — official audio](https://www.youtube.com/watch?v=dtnNO5_Ao6U) as the artistic reference alongside the MIDI-derived comparison. The Official Artist Channel's description identifies the recording as originally recorded in 1963. The upload is an orchestral recording reference, not Barnes's arrangement or proof that the preserved MIDI matches the film cue's full form. No audio download or listening verdict is recorded by this research entry.

## Translate the character into a SID trial

The following began as design hypotheses; the resulting first excerpt was subsequently called “quite good”, without isolating individual patch choices. They follow the [technique lookup](../technique-index.md), [sound repertoire](sound-design-repertoire.md) and owning cards' constraints. Preserve the source pitches, rhythmic irregularities, rests and form before judging the sounds.

| Musical purpose | SID hypothesis to audition | Constraint and acceptance question |
| --- | --- | --- |
| Light, individual sax-like foreground | Begin with a rounded pulse or softened saw body, a shaped attack/body/release and restrained width motion. Treat a breathy onset as an optional short texture trial, not a reason to add constant noise. | A SID waveform is not an acoustic tenor model. Clear pitch and audible note bodies matter more than the patch name. Does the melody sound sly and lightly articulated rather than piercing, blunt or drum-like? |
| Rhythmic wit and sneaking motion | Preserve the MIDI's encoded swing, triplets, accents and silences; shape articulation within those timings. Keep support below the lead so the displaced attacks remain perceptible. | Do not apply a second swing transform. Use the [short-note ending guidance](sound-design-repertoire.md#shape-short-note-endings-in-context): gate gaps alone do not establish natural decay. Can the listener follow the groove without hearing chopped-off repeated ticks? |
| Sustained-note expression without obscuring chromatic identity | Try subtle delayed vibrato or slow pulse movement on sufficiently long notes; start each chromatic note at its intended pitch. | The [accepted Shades transfer](instruments/shades-decoded-programs.md#familiar-transfer-accepted) supports delayed modulation in one context; its [glide limitation](instruments/shades-decoded-programs.md#choose-glides-by-phrase-not-by-instrument-name) argues against sliding every transition. Are long notes alive while the recognizable semitone gestures stay clear? |
| Restrained rhythmic and harmonic support | Give bass and accompaniment separate envelope/register roles; audition dry or lightly filtered bass and sparse harmonic attacks before adding a foreground drum transient. | Three simultaneous SID voices require a declared reduction of the six source parts. Time-sharing percussion with bass delays or interrupts the pitched body; the [repertoire](sound-design-repertoire.md#multiplex-instrument-roles-within-three-voices) records this cost. Does support propel the phrase without competing with its melody? |
| Sophistication through contrast | Make selected arrivals and returns more emphatic through envelope, register or filter colour, while letting quieter motifs recede. | Shared filter and master volume affect the mix; [two-chip roles](../sid/dual-sid.md) can separate control domains only if the arrangement needs them. Contrast is an authored interpretation choice unless already represented in the source. Does the full phrase retain suspense and shape instead of one constant level of brightness? |

The first listening decision is whether the lead, groove and accompaniment convey the intended character together. Compare the same representative source phrase with the official reference available; report musical fit separately from score-preservation, register and PCM checks. Do not promote prior acceptance of a patch on another song as evidence that this trial succeeds.

## Supporting historical contrast

The listener praised the main instrument in Stan Kicak’s BASIC interpretation. The [source inspection, matched-level comparison and reuse boundaries](../../../songs/pink-panther/README.md#learn-from-the-selected-basic-interpretation) connect that verdict to fixed narrow pulse and explicit score articulation. Established master-composer studies remain the primary knowledge base; this is supplementary, song-specific evidence, not a replacement hierarchy.
