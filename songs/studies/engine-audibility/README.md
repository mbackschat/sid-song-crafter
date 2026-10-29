# Engine-limit audibility comparison

This study decides whether a project-owned engine beyond SID-Wizard Extra is musically needed. SID-Wizard Extra combines instruments in one song and carries the accepted native songs, but a source review of its player found four decoded master mechanisms it cannot express exactly (the [instrument-library proposal](../../../docs/proposals/instrument-library.md) owns the engine question). Two of those mechanisms already have accepted exact transfers, so a bounded subtraction comparison can test whether replacing each one with SID-Wizard's nearest behaviour is audible.

## Questions, fixed before building

| Comparison | Exact version (accepted) | Variant: only this mechanism replaced | Question to the listener |
| --- | --- | --- | --- |
| Deflektor pulse arithmetic | [Deflektor familiar transfer](../deflektor-elise-transfer/README.md): low-byte-only pulse addition/subtraction, high byte unchanged between targets | SID-Wizard `PWSWEEP` behaviour: signed low-byte movement carries into the pulse high byte | Does the variant lose something you care about in the pulse sound? |
| Shades update rate | [Shades familiar transfer](../../../docs/research/composition/instruments/shades-decoded-programs.md): CIA-timed calls at about 79.93 Hz | One update per PAL frame (about 50.12 Hz), call-counted parameters rescaled to keep real-time durations as closely as integer counts allow | Does the variant lose something you care about in motion, vibrato or timing? |

Each comparison presents the plain reference, then the exact version, then the variant, on the same 53 familiar notes, following the [comparison workflow](../../../docs/workflows/audio-comparisons.md#package-a-listening-review). Everything except the named mechanism stays identical; each variant's audit must show differences only where the mechanism acts.

## Decision rule

If neither variant loses anything the listener cares about, keep SID-Wizard Extra as the composition engine and extend only the converter. If one or both do, the superset engine is justified for the mechanisms heard, each verified against its decoded player. A verdict covers this phrase and these programs; it does not settle the other two inexpressible mechanisms (Monty's shared pulse record and Ghostbusters' continuing vibrato phase), which have no isolated exact transfer to subtract from.

## Model assistance

Standing decision at opening: no model call. The [existing calibrations](../../../docs/research/audio-assessment.md#use-and-reassess-model-assistance) do not validate a model for detecting subtle pulse or timing differences that matter to this listener; human listening decides.
