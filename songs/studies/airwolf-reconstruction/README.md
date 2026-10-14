# Airwolf independent reconstruction

The [composition](composition.json) preserves the pinned Mark Cooksey C64 arrangement’s complete initialized first traversal of Sylvester Levay’s *Airwolf Theme*. A separate authored ending replaces the next loop restart. The [owning study](../../../docs/research/composition/airwolf-preparation.md) records verification and listening status; the [preparation receipt](preparation.json) pins source data and ending selection. Human phrase and ending judgments are pending.

```sh
python3 scripts/studies/airwolf/prepare-title.py --check
python3 scripts/listening-package.py config/listening/airwolf-full.json --output build/airwolf-full-work
python3 scripts/publish-listening.py build/airwolf-full-work/run.json --selection scripts/studies/airwolf/title-audition.json --output build/airwolf-listening
```

Publish to a fresh directory. Init consumes row zero; play calls 0–1240 preserve the rest of the first traversal. At call 1241 the candidate closes held gates and suspends native fixed writes, then stops controls/master volume at 1273 after a 32-call release. The audit includes 64 further write-free calls. The original loops; this finite ending has no added fade and requires its own listening judgment.

Listen to the [phrase comparison](../../../build/airwolf-listening/phrase-reference-then-ours.ab.wav), 32.5 seconds, and [ending comparison](../../../build/airwolf-listening/ending-reference-then-ours.ab.wav), 24.5 seconds; both present the original first and reconstruction second. Full [reference](../../../build/airwolf-listening/reference.wav) and [reconstruction](../../../build/airwolf-listening/reconstructed.wav) renders are 27 seconds. The [submission](../../../evidence/airwolf-compiled/listening/submission.json) binds these samples to the checks. Judge the authored exit separately from the original’s repeating content.

The [compiled proof](../../../evidence/airwolf-compiled/candidate/verification.json) and full callable VICE check cover all 1,338 play calls and 5,593 init/play stores: 5,586 preserved source-prefix stores plus seven authored ending stores. The actual PRG bootstrap check executes init and two calls with modeled raster/CIA reads; it is separate from full callable VICE playback. Render checks do not establish perceptual agreement or musical acceptance.

The declared target is one PAL MOS6581 at `$D400`. Source pulse-low and filter registers are unwritten; controlled rendering starts from the renderer’s reset state. Exported software-state restoration does not establish arbitrary prior hardware-state independence. Keep original SID/audio and generated exports in ignored local storage. The [static-tone card](../../../docs/research/composition/instruments/airwolf-static-tones.md) and [familiar transfer](../airwolf-elise/README.md) retain editable reuse and its pending listening outcome.
