# Independent three-voice DRAX reconstruction

This study follows **executed program → musical description → reusable mechanism → new 6502 implementation** for the preferred 2.02–2.75-second passage of DRAX's Für Elise. It reconstructs the opening from initialization, including silent preparation. It contains neither the original driver nor captured-register playback. The [earlier contextual bass test](../drax-bass-reconstruction/README.md) retained DRAX's accompaniment; this version independently programs all three voices.

## Listen

- [Exact passage, original then reconstruction](../../../build/drax-independent-trio/exact.ab.wav): 0.73 seconds each, separated by half a second.
- [Three-second opening, original then reconstruction](../../../build/drax-independent-trio/full.ab.wav): includes the entrance and musical context.
- [Our independent opening alone](../../../build/drax-independent-trio/reconstructed.wav).

The reference is the pinned DRAX SID documented in [the reference study](../../../docs/research/composition/fuer-elise-reference.md). Both renders use the same PAL MOS6581 renderer and common unity gain. The reference audio is checked against the existing `build/reference-studies/drax/reference.opening.wav`. Listener verdict: “Nice” — positive feedback on the independent reconstruction. The listener has not explicitly judged it indistinguishable from DRAX.

## Description and library mapping

[The editable description](instrument.json) retains exact native pitch words, note initializer calls, lead PWM/vibrato, chord pitches, envelopes and score gate-off age. It references the already independently implemented [bass recipe](../drax-bass-reconstruction/instrument.json). [The musical mapping card](../../../docs/research/composition/instruments/drax-decoded-trio.md) connects these programs to bass, lead, chord texture and coordinated arrangement, in both directions.

[companions.asm](companions.asm) computes pulse movement, delayed vibrato and two-call chord cycling; [the builder](../../../scripts/reconstruct-drax-full.py) assembles it with our bass state machine. Small note and modulation tables describe the music and effects, not a stream of recorded register writes. A test changes the description's lead and chord pitches and verifies the resulting new execution without changing the engine.

Nuances retained include silent oscillator preparation, two-stage hard restart/TEST, deferred pulse-width writes at initialization, different prehistory and active PWM bounds, gate ownership, modulation during release, voice order, and repeated shared-cutoff writes before bass updates it. Companion gate-off comes from the score; bass gate-off comes from its instrument. These must not be conflated in the library.

## Reproduce and verify

After [renderer setup](../../../docs/audio-workflow.md), choose a fresh output directory:

```sh
PYTHONPATH=.tools/test-deps python3 scripts/reconstruct-drax-full.py --reference .local/research/fuer-elise/drax-fuer-elise.sid --output build/drax-independent-trio/new --vice
PYTHONPATH=.tools/test-deps python3 -m unittest discover -s tests -p drax_full_reconstruction_test.py -v
```

Omit `--reference` to build/render without reading the original SID. Original bytes enter only the optional comparison stage, after the independent build.

All **3,507 initialization and playback writes** match the reference by call, address, value and order through calls 0–150, including every intermediate cutoff write. VICE independently matches 3,485 runtime writes through call 153, including three terminal volume-zero writes. The reconstruction uses at most 793 cycles per call against the 19,656-cycle PAL budget.

Within-frame instruction starts differ by −1,061 to +93 cycles. The new implementation has not reproduced exact bus timing, oscillator/noise phase or physical chip variation; PCM is not identical. The [comparison report](../../../build/drax-independent-trio/study.json) retains these boundaries. This is a bounded executable musical description, not a complete-song driver or a universal reverse-engineering tool.
