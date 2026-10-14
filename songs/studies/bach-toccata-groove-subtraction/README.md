# Bach groove: repeated-A3 subtraction diagnostic

This bounded diagnostic removes the suspected thin accompaniment voice after the listener found the [release revision](../bach-toccata-groove-release/README.md) better but still disliked a drum-like background sound without convincing bass. The phrase “both variants” does not uniquely identify a SID voice. This audition tests whether removing the repeated A3 line resolves that complaint; it is not an accepted musical correction.

The [editable score](score.json) removes only the 56 A3 accompaniment events beginning inside performed seconds 30.71–41.9725. Every foreground event and the complete A2 bass remain verbatim. All other notes, the complete duration, and every instrument in the [native recipe](hybrid.json) remain unchanged from the release revision. The [preparation record](preparation.json) lists every removed event and points back to the existing score and source-provenance ledger.

The [listening recipe](../../../config/listening/bach-toccata-groove-subtraction.json) renders both complete initialized arrangements, verifies their CPU schedules, limits register changes to voice 3, and checks the subtraction PRG in headless VICE. Its main pair plays the prior release revision, a half-second gap, then the diagnostic without A3, covering performed seconds 30–43.5 at unity gain. The unchanged [accepted original passage](../../../build/bach-groove-release-listening/original-passage.wav) remains available alongside the pair.

```sh
python3 scripts/listening-package.py config/listening/bach-toccata-groove-subtraction.json --output build/bach-toccata-groove-subtraction-fresh
```

The [listener confirms](listening-review.json) that the unwanted sound disappears and the result is “much better now”. Preserve this as the preferred passage and reference for any replacement trial. This verdict covers the compared passage, not separate full-song acceptance. Model-assistance review: skip unvalidated preference inference; this single human subtraction audition is the next checkpoint.

Executed checks on 2026-10-14 verified 867 candidate notes against the prior release revision's 923. Only the 56 declared A3 starts are absent; every retained pitch, onset, duration, gate-off and instrument selection matches. Across 4,419 post-call snapshots, changes remain confined to voice 3; foreground, bass and shared filter/global registers are identical. The standalone PRG passed headless VICE through call 4,400. Both renders remain 88.122925 seconds with zero clipping and silent tails. The [subtraction guard and PCM summary](../../../evidence/bach-groove-subtraction/subtraction-check.json) retain these checks separately from the pending listening judgment.

The listener explicitly authorized removal **as a test** after clarifying a preference for a better drum or rhythmic instrument rather than a boring, sparse result. Treat this as attribution evidence, not the intended final arrangement. The positive subtraction verdict confirms the offending part; any requested rhythmic replacement must improve on this preferred texture rather than being inserted by default.

Listen to [previous release revision then without upper pulse](../../../build/bach-groove-subtraction-listening/previous-then-without-upper-pulse.ab.wav), 27.5 seconds. Publish fresh copies with the [stable filename selection](../../../config/listening/bach-toccata-groove-subtraction-audition.json).
