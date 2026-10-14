# Billie Jean sounds on Für Elise

This [candidate](transfer.json) and [generated plain reference](reference.json) use the same 53 nominal notes from beats `[0,12)` of [the preserved Für Elise score](../../fuer-elise.json), at BPM 72. The [program card](../../../docs/research/composition/instruments/billie-jean-decoded-programs.md) owns palette selection, constraints and listening status. This is a generated score reference, not an original recording. Human musical review is pending.

```sh
python3 scripts/studies/billie-jean/prepare-elise.py --output songs/studies/billie-jean-elise --check
python3 scripts/listening-package.py config/listening/billie-jean-elise-transfer.json --output build/billie-jean-elise-work
python3 scripts/publish-listening.py build/billie-jean-elise-work/run.json --selection scripts/studies/billie-jean/elise-audition.json --output build/billie-jean-elise-listening
```

Use a fresh destination when publishing. Listen to [plain-then-billie-jean.ab.wav](../../../build/billie-jean-elise-listening/plain-then-billie-jean.ab.wav), 24.5 seconds: plain first, native sounds second. Separate files are [plain-reference.wav](../../../build/billie-jean-elise-listening/plain-reference.wav) and [billie-jean-transfer.wav](../../../build/billie-jean-elise-listening/billie-jean-transfer.wav).

The [preparation report](preparation.json) retains all events, native and A440 frequency words, quantization errors, sound evidence fingerprints and adaptations. Physical voices 1/2/3 carry melody/bass/harmony using instrument offsets 88/32/24. Both renders use PAL MOS6581, A440 and master volume 11. Nearest-three-call scheduling gives at most 29.764 ms boundary error and 31.070 ms duration error. Initial divider 1 makes the first rows occur at call zero; the phrase ends at 501, with a held release through 532, final stop at 533 and 64 confirmation calls.

Native programs preserve their short pitch accents: the melody rises two octaves for two body updates, bass has a one-update semitone accent, and harmony begins an octave above for four updates. These are instrument gestures over the preserved nominal score, not added composition notes. Native TEST restart delays ordinary output until the next call and closes gates before subsequent rows; the plain triangle holds gates between contiguous notes. Rests close the gate while sound programs continue releasing. These articulation differences are intentional and require musical judgment.
