# Musical gestures and improvisation

A reusable gesture describes a musical action: what to play, when to leave space, and how native SID behaviour supports the phrase. Pair these with the [instrument bank](../instruments/README.md); a patch alone does not specify a groove. Return to [composition](../README.md).

| Gesture | Musical use | Evidence |
| --- | --- | --- |
| [GROOVE-01: bass answer](bass-answer.md) | Give a melodic arrival weight, then answer it rhythmically | Original arrangement rendered; listening pending |
| [CHORD-01: selective chord bursts](chord-bursts.md) | Suggest fuller harmony with one oscillator while leaving melodic space | Original burst arrangement rendered; listening pending |
| [FORM-01: vary a returning phrase](phrase-variation.md) | Keep the theme recognizable while changing its energy | Returning-phrase variation rendered; listening pending |
| [FORM-02: organ weight with forward motion](driven-organ-phrasing.md) | Compress holds and gaps while preserving rapid-note clarity | Bach faster opening and complete mono interpretation accepted |

The first [editable interpretation study](../../../../songs/studies/fuer-elise-interpretation/README.md) combines these gestures in two new Für Elise palettes. Its score preserves the opening melody and records original accompaniment; technical checks and listening acceptance remain separate.

The listener prefers palette B's direction and the later Weight bass, while DRAX remains the reference for accompaniment richness. The first study records a finite-burst limitation in its native chord tables. The [layered-entrance study](../../../../songs/studies/elise-layered-entrance/README.md) corrects waveform preservation and compares sustained layering with playful replies, but both were judged not close to DRAX. Technical correctness and plausible arrangement mechanisms are insufficient evidence that the target sound has been captured.

## How to use and extend the library

Choose a desired impression first: playful, tense, tender, driving or spacious. Name a concrete musical action that could create it. Combine a small number of compatible gestures, then audition the resulting phrase; adding more effects is not itself a success criterion.

Each entry needs its harmonic and rhythmic context, editable example when implemented, native voice/filter dependencies, meaningful variations, failure cases, provenance, and a bounded listening verdict. Keep source notation untouched and record invented notes, displaced registers, changed rhythms and omissions in the arrangement's own source. Native modulation remains independently editable and must not be flattened into a restrictive interchange format.

Use a fixed phrase for an isolated effect comparison. For an interpretation, compare corresponding musical passages and document intentional differences in tempo, rhythm, harmony and texture. Such a comparison tests the overall impression; it cannot attribute improvement to one parameter. Keep original-amplitude audio alongside matched excerpts.

## Listening findings that guide selection

Evidence: mbackschat's listening feedback on 2026-10-12; playback equipment unspecified. These are useful preferences in the named examples, not universal rankings.

- [Triangle-attack Für Elise](../../../../build/elise-attack-preview/opening.b.matched.wav) removed the reported noise-like quality, but the arrangement remained too clinical. Smoothing an attack solves timbre harshness; phrasing and accompaniment need separate creative work.
- [DRAX's opening](../../../../build/reference-studies/drax/reference.opening.wav) was strongly preferred for richness, playfulness and bass, and described as louder, crisper and broader in range than the clean triangle sample. These are listening descriptions. The later [bass-solo audition](../fuer-elise-reference.md#identify-the-preferred-layer-by-listening) locates vibrancy in the bass itself. Use the [executed-program study](../../tools/sid-program-analysis.md) for its mechanism and reconstruction; the preference alone does not identify the cause or establish DRAX's creative intent.
- [Pulse motion A/B](../../../../build/instrument-trials/comparisons/pulse.ab.wav) was audibly different; no preference was stated. [Bass transient A/B](../../../../build/instrument-trials/comparisons/bass.ab.wav) produced little or no perceived difference. Do not label either an improvement merely because registers change.
- [Bass-presence variants](../../../../songs/studies/elise-bass-presence/README.md): Weight (A) was judged nice; Resonant (B) was odd or brass-like. Keep Weight as the preferred direction, with DRAX's roughly two-second bass/chord entrance still the stronger reference. Greater resonance and a sharper cutoff contour did not make this candidate preferable.

The [Bach intention-blend trials](../bach-toccata.md#bolder-foreground-attack-paired-audition) add a scoped warning: the listener rejected both extra pitched replies and short foreground pitch/waveform attacks as odd short sounds. Stronger ongoing lead pulse motion was liked but considered subtle. For this brief, moving a brief effect into another voice role did not solve musical integration; the next hypothesis concerns sustained accompaniment and phrase-level momentum. This does not establish that short effects fail universally.

The target is an expressive SID interpretation with intentional freedom. A faithful reduction remains a useful source and correctness reference; the creative arrangement needs its own musical judgment.

For the [Bach running-passage groove](../../../../songs/studies/bach-toccata-groove-blend/README.md), the listener provisionally liked the direction but heard abruptly cut-off accompaniment. Native checks found repeated short A3 bodies with fast release. Treat rhythmic separation and acoustic decay as separate design controls: real gate gaps prove articulation occurred, but do not establish a musically satisfying ending for each pulse. The release-only follow-up was judged better locally, but the sound remained rejected as a thin “wanna be drum”. Follow the [role/body and subtraction guidance](../sound-design-repertoire.md#shape-short-note-endings-in-context); relative improvement is not acceptance.
