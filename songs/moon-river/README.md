# Moon River: score-backed SID interpretation

The requested *Breakfast at Tiffany's* theme is interpreted as Henry Mancini's **Moon River**. This case starts from an existing piano MIDI arrangement, not an invented score. Its arranger is unidentified; it is not claimed to be Mancini's original film edition. [Source intake](../../docs/research/composition/moon-river-preparation.md) owns URLs, fingerprints and musical scope. The source, complete imported score, selected notes and audio remain local.

## Musical intent and arrangement

Give the melody a singing pulse tone with delayed vibrato and ongoing width motion, over warm filtered bass and a quieter triangle accompaniment. These three native patches already exist: [Elise native palette](../fuer-elise-sidwizard.json) supplies `melody-pulse` and `harmony-soft`; [Bach full palette](../studies/bach-toccata-full/hybrid.json) supplies `bass`. This is a proposed use in Moon River, not prior listening acceptance of this arrangement. The bass alone owns the shared filter; the other two voices bypass it. No percussion or invented harmonic progression is added.

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

Listening is pending. Judge whether the familiar melody/harmony survives the reduction and whether the SID phrasing, tone, balance and ending make a convincing interpretation. Technical execution checks cannot establish this. At first audition, no audio-model call is justified: existing perception trials do not validate musical preference or harmonic-fidelity scoring on this source. Reassess after listener feedback and before closure; model outputs remain experimental supporting signals.

## First listening package

- [Plain then SID opening](../../build/moon-river-listening/plain-then-sid.ab.wav): 48.5 seconds, 24 seconds per version with a half-second gap, unity gain on both.
- [Complete first statement in SID](../../build/moon-river-listening/moon-river-sid.wav) and [matching plain reference](../../build/moon-river-listening/plain-reference.wav): 98.66 seconds including release/verification tail.
- [Canonical checks](../../evidence/moon-river-first-statement/checks.json), [recipe receipt](../../evidence/moon-river-first-statement/run.json) and [audition fingerprints](../../evidence/moon-river-first-statement/sources.json).

The full source import retains 750 notes; the first-statement view selects 319. The SID reduction retains 293 source notes (87 melody, 46 bass, 160 harmony), omits 26 and shortens 12. Every original note remains available in the complete local common score. Both versions pass 4,947 CPU calls and complete note/stop checks; candidate standalone VICE checkpoints extend through call 4,910 after the verified stop at 4,894. Both renders are unclipped and end quietly. The successful recipe took 112.77 seconds; this excludes source research, preparation and prior rejected build attempts, so it is not a total productivity measurement. First listening acceptance is pending.
