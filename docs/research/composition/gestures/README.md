# Musical gestures and improvisation

A reusable gesture describes a musical action: what to play, when to leave space, and how native SID behaviour supports the phrase. Pair these with the [instrument bank](../instruments/README.md); a patch alone does not specify a groove. Return to [composition](../README.md).

| Gesture | Musical use | Evidence |
| --- | --- | --- |
| [GROOVE-01: bass answer](bass-answer.md) | Give a melodic arrival weight, then answer it rhythmically | Original arrangement rendered; listening pending |
| [CHORD-01: selective chord bursts](chord-bursts.md) | Suggest fuller harmony with one oscillator while leaving melodic space | Original burst arrangement rendered; listening pending |
| [FORM-01: vary a returning phrase](phrase-variation.md) | Keep the theme recognizable while changing its energy | Returning-phrase variation rendered; listening pending |

The first [editable interpretation study](../../../../songs/studies/fuer-elise-interpretation/README.md) combines these gestures in two new Für Elise palettes. Its score preserves the opening melody and records original accompaniment; technical checks and listening acceptance remain separate.

The listener prefers palette B's direction and the later Weight bass, while DRAX remains the reference for accompaniment richness. The first study records a finite-burst limitation in its native chord tables. The [layered-entrance study](../../../../songs/studies/elise-layered-entrance/README.md) corrects waveform preservation and compares sustained layering with playful replies; listening approval is pending.

## How to use and extend the library

Choose a desired impression first: playful, tense, tender, driving or spacious. Name a concrete musical action that could create it. Combine a small number of compatible gestures, then audition the resulting phrase; adding more effects is not itself a success criterion.

Each entry needs its harmonic and rhythmic context, editable example when implemented, native voice/filter dependencies, meaningful variations, failure cases, provenance, and a bounded listening verdict. Keep source notation untouched and record invented notes, displaced registers, changed rhythms and omissions in the arrangement's own source. Native modulation remains independently editable and must not be flattened into a restrictive interchange format.

Use a fixed phrase for an isolated effect comparison. For an interpretation, compare corresponding musical passages and document intentional differences in tempo, rhythm, harmony and texture. Such a comparison tests the overall impression; it cannot attribute improvement to one parameter. Keep original-amplitude audio alongside matched excerpts.

## Listening findings that guide selection

Evidence: mbackschat's listening feedback on 2026-10-12; playback equipment unspecified. These are useful preferences in the named examples, not universal rankings.

- [Triangle-attack Für Elise](../../../../build/elise-attack-preview/opening.b.matched.wav) removed the reported noise-like quality, but the arrangement remained too clinical. Smoothing an attack solves timbre harshness; phrasing and accompaniment need separate creative work.
- [DRAX's opening](../../../../build/reference-studies/drax/reference.opening.wav) was strongly preferred for richness, playfulness and bass, and described as louder, crisper and broader in range than the clean triangle sample. “Broader range” is a listening description, not yet a measured distinction between pitch span, spectral breadth or dynamics. Its [measured study](../fuer-elise-reference.md) identifies moving pulse, bass/percussion sharing and chord arpeggiation together. The preference does not isolate which mechanism caused it or establish DRAX's creative intent.
- [Pulse motion A/B](../../../../build/instrument-trials/comparisons/pulse.ab.wav) was audibly different; no preference was stated. [Bass transient A/B](../../../../build/instrument-trials/comparisons/bass.ab.wav) produced little or no perceived difference. Do not label either an improvement merely because registers change.
- [Bass-presence variants](../../../../songs/studies/elise-bass-presence/README.md): Weight (A) was judged nice; Resonant (B) was odd or brass-like. Keep Weight as the preferred direction, with DRAX's roughly two-second bass/chord entrance still the stronger reference. Greater resonance and a sharper cutoff contour did not make this candidate preferable.

The target is an expressive SID interpretation with intentional freedom. A faithful reduction remains a useful source and correctness reference; the creative arrangement needs its own musical judgment.
