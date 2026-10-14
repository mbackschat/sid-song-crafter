# Billie Jean independent reconstruction

The [editable composition](composition.json) preserves the pinned Johannes Bjerregaard arrangement's initialized first traversal, with a separately authored finite ending. The original song is Michael Jackson's *Billie Jean*. The [owning study](../../../docs/research/composition/billie-jean-preparation.md#compiled-export-and-listening-package) retains source attribution, numerical evidence and listening status. The [listener verdicts](listening-review.json) report no difference in the phrase and ending comparisons; this declared reconstruction is accepted.

```sh
python3 scripts/studies/billie-jean/prepare-title.py --check
python3 scripts/listening-package.py config/listening/billie-jean-full.json --output build/billie-jean-full-work
python3 scripts/publish-listening.py build/billie-jean-full-work/run.json --selection scripts/studies/billie-jean/title-audition.json --output build/billie-jean-listening
```

Publication requires a fresh destination. The [preparation receipt](preparation.json) pins the canonical composition and leaves its score, sound bank and cold state unchanged. Music calls 0–7105 remain exact; the authored ending replaces the loop restart at 7106, holds gate-low registers for 32 calls, stops controls/master volume at 7138 and checks 64 further write-free calls. This is a deliberate finite interpretation, not an original source ending or a fade.

Listen to the [phrase comparison](../../../build/billie-jean-listening/phrase-reference-then-ours.ab.wav), 32.5 seconds, original first, then ours; the [ending comparison](../../../build/billie-jean-listening/ending-reference-then-ours.ab.wav) is 40.5 seconds in the same order. Full [reference](../../../build/billie-jean-listening/reference.wav) and [reconstruction](../../../build/billie-jean-listening/reconstructed.wav) are 145 seconds. The original restarts during the ending window; judge our phrase exit and decay rather than requiring those final seconds to match.

The exported PSID and standalone PRG contain our runtime score scheduler and sound routines, targeting one PAL MOS6581 at `$D400`. CPU and headless VICE match all 138,703 init/play stores, including the seven authored ending stores. Original reference binaries/audio and all generated audio stay in ignored local storage. The [reusable tonal example](../billie-jean-elise/README.md) applies selected programs to familiar different material.
