# Moon River: score-backed SID interpretation

The requested *Breakfast at Tiffany's* theme is interpreted as Henry Mancini's **Moon River**. This case starts from an existing piano MIDI arrangement, not an invented score. Its arranger is unidentified; it is not claimed to be Mancini's original film edition. [Source intake](../../docs/research/composition/moon-river-preparation.md) owns URLs, fingerprints and musical scope. The source, complete imported score, selected notes and audio remain local.

## Musical intent and arrangement

The intended character is **tender, intimate, wistful and quietly hopeful**, a mood brief confirmed by the listener after rejecting the first candidate. The [owning study](../../docs/research/composition/moon-river-preparation.md#mood-brief-and-restrained-revision) records the film context, sources and reusable lesson: choose sounds for the song's emotional role, and retain acceptance within the musical context that earned it.

The rejected [first native palette](native.json) gives the melody a singing pulse tone with delayed vibrato and ongoing width motion, over filtered bass and a triangle accompaniment. The [Elise native palette](../fuer-elise-sidwizard.json) supplies `melody-pulse` and `harmony-soft`; the [Bach full palette](../studies/bach-toccata-full/hybrid.json) supplies `bass`. The bass alone owns the shared filter; the other voices bypass it. Earlier acceptance of these sounds in their owning arrangements did not establish their suitability for Moon River. The original candidate and its evidence remain available below.

The [reduction policy](reduction.json) uses the existing three-voice reducer: top active right-hand note for melody, source low/measure-start left-hand notes for bass, and a remaining source note for harmony. All rendered pitches and intervals come from source note events; omitted and shortened inner notes are reported. The full polyphonic source remains available to reassess a reduction or a later stereo interpretation. [Native palette](native.json) and [plain palette](plain.json) use the same selected score and timing.

The source's complete first statement is beats 0–111, ending after its F-major tonic bar, before a modulation. No note crosses this boundary. The later statement is excluded explicitly: this is a complete first statement, not the full 234-beat piano arrangement. Source rubato is replaced by the opening quarter-note tempo of 70 for this initial rendition; the original 38-event tempo map is retained. Musical duration is approximately 95.14 seconds, followed by the native release tail without an added fade. The full-score attempt exceeded SID-Wizard's existing 100-pattern limit; the first-statement scope avoids changing the engine or accelerating the ballad.

## Reproduce and listen

```sh
python3 scripts/setup-project.py --only references --include moon-river-score
python3 scripts/listening-package.py config/listening/moon-river.json --output build/moon-river-reproduction
python3 scripts/publish-listening.py build/moon-river-reproduction/run.json --selection config/listening/moon-river-audition.json --output build/moon-river-reproduction-listening
```

The first command installs the optional pinned source along with default references. Prepare the existing [native tools](../../docs/workflows/native-song-workflow.md) first. The case adapter freezes only tempo values in a derived MIDI, checks every other event and delta tick before/after serialization, and uses the existing importer and reducer. No new synthesis backend is involved.

The comparison plays a plain triangle rendering first, then the SID interpretation of exactly the same reduced score. It is a generated score reference, not an original recording or an acoustic piano performance. Full reference and candidate renders accompany the opening comparison. The initial target is one MOS8580 at `$D400`, PAL; NTSC export and any stereo follow-up remain separate checks.

## Acceptance and model review

On **2026-10-15**, the listener recognized the tune and considered the score acceptable, but rejected the first SID interpretation as bad, too loud and offensive. The first candidate is **musically rejected**; correct execution and recognizable notes do not establish a convincing interpretation. The listener subsequently accepted the mood brief above. The [structured listening record](listening-review.json) retains the verdict and the pending revision; no later audio acceptance has been given.

At first audition and again after this feedback, no audio-model call is justified: the [existing perception trials](../../docs/research/audio-assessment.md#use-and-reassess-model-assistance) do not validate mood, musical preference or harmonic-fidelity scoring on this source. The human rejection determines the outcome. Reassess model usefulness after the restrained audition and before closure; model outputs remain experimental supporting signals.

## Restrained revision

The [restrained palette](restrained.json) uses triangle on all three voices. The lead has ADSR `$4676`, vibrato `$12` delayed by 20 frames, bass ADSR `$0535` and harmony ADSR `$0414`; all pulse-width and filter programs are empty. The hypothesis is a gentler lead and less sustained supporting weight suited to the confirmed mood. This changes the instruments rather than merely reducing publication gain. No percussion or new harmonic progression is added.

The source, reduction, constant quarter = 70, complete 111-beat statement and source note lengths remain the same. This revision does not restore rubato or introduce legato. Build and publish it with the [restrained recipe](../../config/listening/moon-river-restrained.json) and the existing [audition selection](../../config/listening/moon-river-audition.json), using fresh output directories:

```sh
python3 scripts/listening-package.py config/listening/moon-river-restrained.json --output build/moon-river-restrained-reproduction
python3 scripts/publish-listening.py build/moon-river-restrained-reproduction/run.json --selection config/listening/moon-river-audition.json --output build/moon-river-restrained-reproduction-listening
```

- [Plain then restrained opening](../../build/moon-river-restrained-listening/plain-then-sid.ab.wav): 48.5 seconds, plain reference first, 24 seconds per version with a half-second gap.
- [Complete restrained statement](../../build/moon-river-restrained-listening/moon-river-sid.wav) and [matching plain reference](../../build/moon-river-restrained-listening/plain-reference.wav): 98.66 seconds including release/verification tail.
- [Recipe receipt](../../build/moon-river-restrained/run.json) and [audition fingerprints](../../build/moon-river-restrained-listening/sources.json).

The restrained render passes 4,947 CPU calls with the same 87 melody, 46 bass and 160 harmony events and stop at call 4,894; sampled standalone VICE checks extend through call 4,910. PCM checks find zero clipping and a quiet ending; the reduced score hash is unchanged. Its full-file AC RMS is approximately 7.96 dB lower than the rejected candidate without post-render gain adjustment, a level measurement rather than a LUFS measurement or musical verdict. The 98.656689-second full WAV has SHA-256 `fa517698dbb9991a25edd295dd7399e7bb43de6d51d2c915662592eaa12cb4cc`.

The restrained candidate awaits listening feedback. Judge whether its tone, balance and phrasing convey the intended intimacy while keeping the melody clear; the patch choice and technical checks are not an accepted solution.

## First listening package

- [Plain then SID opening](../../build/moon-river-listening/plain-then-sid.ab.wav): 48.5 seconds, 24 seconds per version with a half-second gap, unity gain on both.
- [Complete first statement in SID](../../build/moon-river-listening/moon-river-sid.wav) and [matching plain reference](../../build/moon-river-listening/plain-reference.wav): 98.66 seconds including release/verification tail.
- [Canonical checks](../../evidence/moon-river-first-statement/checks.json), [recipe receipt](../../evidence/moon-river-first-statement/run.json) and [audition fingerprints](../../evidence/moon-river-first-statement/sources.json).

The full source import retains 750 notes; the first-statement view selects 319. The SID reduction retains 293 source notes (87 melody, 46 bass, 160 harmony), omits 26 and shortens 12. Every original note remains available in the complete local common score. Both versions pass 4,947 CPU calls and complete note/stop checks; candidate standalone VICE checkpoints extend through call 4,910 after the verified stop at 4,894. Both renders are unclipped and end quietly. The successful recipe took 112.77 seconds; this excludes source research, preparation and prior rejected build attempts, so it is not a total productivity measurement. These are the retained technical checks for the first, musically rejected candidate; they do not establish acceptance of the restrained revision.
