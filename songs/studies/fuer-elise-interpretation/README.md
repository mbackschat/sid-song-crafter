# Für Elise: expressive opening studies

Two original 21-second interpretations use [the retained opening melody](../../fuer-elise.json) with new accompaniment. [score.json](score.json) preserves all 70 melody events from beats 0–23.5 and records original source hashes and deliberate changes. The complete source and fidelity arrangement remain unchanged.

## Musical decisions

- Replace the original accompaniment with 38 bass events and 17 chord carriers: low A1 roots, E2 dominant roots, fifth answers, displaced chord stabs and rests.
- Change accompaniment rhythm and lead pulse width on the second pass. Keep the recognizable melody intact while giving its surroundings freedom.
- Give bass its own resonant low-pass contour and noise-to-pulse attack; keep lead and chords unfiltered.
- [Palette A](recipe.json) uses a moving pulse lead and pulse chord bursts. [Palette B](recipe-b.json) changes lead width/motion and uses triangle-plus-pulse chord bursts, with identical bass, score and envelopes.

These original programs draw on [measured DRAX mechanisms](../../../docs/research/composition/fuer-elise-reference.md) and the [gesture library](../../../docs/research/composition/gestures/README.md); no reference player or instrument-table bytes were copied.

## Reproduce and listen

Use fresh output directories with the [native toolchain](../../../docs/native-song-workflow.md):

```sh
python3 scripts/native-song.py build songs/studies/fuer-elise-interpretation/recipe.json --output build/elise-interpretation-v1
python3 scripts/native-song.py build songs/studies/fuer-elise-interpretation/recipe-b.json --output build/elise-interpretation-v2
python3 scripts/compare-audio.py prepare build/elise-interpretation-v1/native-song.wav build/elise-interpretation-v2/native-song.wav build/elise-interpretation-listen/versions --individual-copies
```

- [A: pulse palette](../../../build/elise-interpretation-listen/versions.a.matched.wav)
- [B: combined chord palette](../../../build/elise-interpretation-listen/versions.b.matched.wav)
- [A then B](../../../build/elise-interpretation-listen/versions.ab.wav)

Listener finding, mbackschat, 2026-10-12: **B is better**, but its bass remains too simple or “small” compared with DRAX. Retain B's lead/chord direction and investigate bass weight and musical variety separately. Playback equipment was unspecified; this is not acceptance of the complete song.

## Verification and limits

Both PAL MOS8580 exports pass 1,060 independent CPU calls, all 125 scheduled events, silent ending and unclipped 44.1 kHz mono rendering. Maximum call cost is 2,319 cycles; this RAM-only check excludes VIC contention. Original amplitudes remain in each build directory; A receives only −0.082 dB in the paired audition.

Trace inspection verifies pulse melody bodies, noise-to-root-pulse bass attacks, bass-only filter routing, and the intended A–C–E / G-sharp–B–E chord tones. The chord tables have a known limitation: after seven audible body calls, the jump to a delay row clears waveform bits for the rest of that event. These samples therefore contain finite bursts, not sustained arpeggio loops. Correct the jump/waveform restoration and guard complete cycles before reusing them as continuous chord instruments. No hardware or VICE comparison of these specific excerpts is claimed.

The separate [layered-entrance study](../elise-layered-entrance/README.md) provides corrected waveform-preserving tables and two new accompaniment treatments. These original samples and their source remain intact for comparison.
