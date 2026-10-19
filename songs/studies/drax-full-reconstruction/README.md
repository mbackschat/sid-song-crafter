# Independent DRAX Für Elise reconstruction

Our own 6502 code reconstructs all three voices of DRAX's complete recurring thematic arrangement: roughly **40.26 seconds**, with 123 lead notes, 26 bass entries and 26 chords. This is the complete DRAX theme cycle, **not every section of Beethoven's Für Elise**. Attribution and the pinned original belong to [the reference study](../../../docs/research/composition/fuer-elise-reference.md).

## Listen in full

- [DRAX original](../../../build/drax-full-listen/reference.wav).
- [Our independent reconstruction](../../../build/drax-full-listen/reconstructed.wav).
- [Our playable SID](../../../build/drax-full-listen/reconstructed.sid).

Both WAVs are 42 seconds, rendered with identical PAL MOS6581 settings and unity gain. The original starts looping around 40.3 seconds; ours ends and retains a quiet verification tail. The full comparison received “nice so far,” with the finding that Elise feels unfinished. A complete Beethoven interpretation remains deferred behind Flashdance in the [work plan](../../../docs/PLAN.md). The earlier [independent opening A/B](../../../build/drax-independent-trio/full.ab.wav) received “Nice”; that does not establish full-song indistinguishability.

## Description, library and build

[full-composition.json](full-composition.json) describes notes, preparation pitches, releases and six patches. [The musical mapping](../../../docs/research/composition/instruments/drax-decoded-trio.md) explains their roles and effects. [Our player](../../players/decoded-trio.asm) computes their behavior; no original driver or register recording is embedded. Editable runtime parameters are separate from `sourceEvidence`.

Follow [the reusable workflow](../../../docs/workflows/decoded-song-workflow.md) for the build command, supported edits, limits and output contract. [The transcriber](../../../scripts/studies/drax/describe-drax-score.py) recovers this score from executed note/instrument readers, preserving provenance. Building the independent SID does not need the original.

## Useful findings and verification

The full arrangement requires three- and four-tone chord programs, patch-dependent pulse widths, and score releases at age 4 or 10. A chord's TEST preparation pitch can inherit the previous program's offset rather than equal its first audible tone. Preserve this distinction when describing articulation and oscillator history. Silent preparation must use the full call counter; a byte rollover is not initialization.

[The comparison receipt](../../../build/drax-full-listen/register-comparison.json) checks every initialization/music write through calls 0–2017, including repeated cutoff writes and release evolution. [Headless VICE](../../../build/drax-full-listen/vice/study.json) independently verifies the generated program through its ending. [The build receipt](../../../build/drax-full-listen/study.json) retains hashes, audio checks and limitations. Within-frame instruction timing and oscillator/noise phase differ; PCM identity and physical-chip equivalence are not claimed.

## Earlier bounded proof

[instrument.json](instrument.json), [companions.asm](companions.asm) and [reconstruct-drax-full.py](../../../scripts/studies/drax/reconstruct-drax-full.py) retain the separately verified 151-call opening experiment. Its 3,507 ordered writes matched the source. Use the complete workflow above for new score edits; the opening experiment remains the reproduction path for the already reviewed short sample.
