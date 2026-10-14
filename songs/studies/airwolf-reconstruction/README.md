# Airwolf independent reconstruction

The accepted reconstruction preserves Mark Cooksey’s pinned C64 arrangement of Sylvester Levay’s *Airwolf Theme*, including its native restart. The listener accepted the original phrase comparison and the corrected continuation; the [case closure](../../../docs/research/composition/airwolf-preparation.md#listening-verdicts-and-case-closure) records the declared scope. The optional [finite composition](composition.json) and its [preparation receipt](preparation.json) remain historical workfiles; their imposed ending is unaccepted.

## Accepted source continuation

Use the [editable source composition](../../../evidence/airwolf-player/composition.json) and [continuation recipe](../../../config/listening/airwolf-continuation.json). They retain both checked native restarts without the optional `ending`. The [complete source/CPU/VICE evidence](../../../docs/research/composition/airwolf-preparation.md#reference-continuation-correction) covers 2,500 play calls and all 11,253 init/play stores.

```sh
python3 scripts/listening-package.py config/listening/airwolf-continuation.json --output build/airwolf-continuation-work
python3 scripts/publish-listening.py build/airwolf-continuation-work/run.json --selection scripts/studies/airwolf/title-audition.json --output build/airwolf-continuation-listening
```

Publish to a fresh directory. The [corrected ending comparison](../../../build/airwolf-continuation-listening/ending-reference-then-ours.ab.wav) is 24.5 seconds, original first and reconstruction second, over song seconds 15–27. Full [reference](../../../build/airwolf-continuation-listening/reference.wav) and [reconstruction](../../../build/airwolf-continuation-listening/reconstructed.wav) are 27-second captures. Both continue the loop; the recording boundary is not a composed stop. The [submission](../../../evidence/airwolf-continuation/listening/submission.json) binds the audio to the completed checks.

On 2026-10-14 the listener answered **“Now it's fine”** to the corrected ending. The [continuation review](continuation-listening-review.json) retains the exact answer and hashes; this continuation is accepted. The prior phrase verdict, “I don't hear any difference”, remains accepted in the [historical review](listening-review.json); the [original phrase sample](../../../build/airwolf-listening/phrase-reference-then-ours.ab.wav), 32.5 seconds, remains unchanged. Acceptance does not establish PCM or hardware identity.

## Historical finite variant

Init consumes row zero; the finite workfile preserves music calls 0–1240, closes held gates at 1241 and stops controls/master volume at 1273 after a 32-call release, then checks 64 write-free calls. This omitted the native restart heard in the reference. The [source-continuation diagnosis](../../../docs/research/composition/airwolf-preparation.md#reference-continuation-correction) explains why a longer release would not recover the missing notes. The listener’s premature-cut qualification left this finite variant unaccepted; the historical review and original [ending comparison](../../../build/airwolf-listening/ending-reference-then-ours.ab.wav), 24.5 seconds, are preserved without replacement.

```sh
python3 scripts/studies/airwolf/prepare-title.py --check
python3 scripts/listening-package.py config/listening/airwolf-full.json --output build/airwolf-full-work
python3 scripts/publish-listening.py build/airwolf-full-work/run.json --selection scripts/studies/airwolf/title-audition.json --output build/airwolf-listening
```

The [finite compiled proof](../../../evidence/airwolf-compiled/candidate/verification.json) and callable VICE run cover 1,338 play calls and 5,593 stores: 5,586 source-prefix stores plus seven authored ending stores. Technical correctness of that deliberate stop did not establish whole-window source coverage or musical acceptance. Original finite [reference](../../../build/airwolf-listening/reference.wav) and [reconstruction](../../../build/airwolf-listening/reconstructed.wav) captures remain 27 seconds.

## State and reuse limits

The target is one PAL MOS6581 at `$D400`. Pulse-low and filter registers are unwritten; controlled rendering starts from the renderer’s reset state. Software-state restoration does not establish arbitrary prior hardware-state independence. The actual modeled PRG bootstrap checks init plus two calls, separate from complete callable VICE playback. Keep original SID/audio and generated exports in ignored local storage.

The [static-tone card](../../../docs/research/composition/instruments/airwolf-static-tones.md) and [accepted familiar transfer](../airwolf-elise/README.md) retain editable reuse. Model assistance was explicitly skipped at corrected feedback and closure: fine fidelity, balance and natural endings remain uncalibrated, and no unresolved listener defect requires a model probe. Models remain experimental supporting signals; reassess at Ghostbusters’s first representative audition.
