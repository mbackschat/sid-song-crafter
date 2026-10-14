# Take On Me: independent single-SID title

This editable title selects the original introduction and first complete loop of Pascal van Loosbroek’s C64 arrangement of a-ha’s *Take On Me*. The [owning study](../../../docs/research/composition/take-on-me-preparation.md) retains source attribution, the chip-model audition, executed mechanisms and numeric verification. Compiled CPU/VICE playback and rendered signal checks pass; the listener reports no audible difference in the reviewed phrase and ending comparisons. See the [complete delivery evidence and listening package](../../../docs/research/composition/take-on-me-preparation.md#compiled-export-and-complete-listening-package).

- [Composition](composition.json): runtime score, instrument programs, named initial state and explicit PAL/MOS8580 target. The original archive declares no chip model; the listener heard no difference in the source-model comparison and 8580 was selected as our working target.
- [Preparation receipt](preparation.json): pinned [canonical numeric composition](../../../evidence/take-on-me-player/composition.json), selected range and deliberate ending. Reference SID binaries and their audio remain local.
- [Preparation script](../../../scripts/studies/take-on-me/prepare-title.py): reproduce these editable inputs without downloading or executing the original SID.

| Calls | Behavior |
| --- | --- |
| 0–4,863 | Preserve the source introduction and first loop, including its exact frequency table and evolving instrument state. |
| 4,864 | Begin the authored ending: clear held gates and write the three controls; freeze the score and modulation. The source would restart its loop here. |
| 4,865–4,895 | Allow the held release without further writes. |
| 4,896 | Clear controls and master volume while preserving filter-mode bits. |
| 4,897–4,960 | Verify that stopped playback emits no further stores. |

The 32-call release interval passes the rendered settled-tail check; the listener reports no audible difference in the ending comparison and raises no objection to the authored stop. All three source gates are already closed at call 4,863. The source loops indefinitely, so neither its restart nor our authored stop should be presented as an original finite ending. No fade is added.

```sh
python3 scripts/studies/take-on-me/prepare-title.py --check
python3 scripts/studies/take-on-me/prepare-title.py --output build/take-on-me-title-new
```

The first command checks this retained preparation byte-for-byte. The second writes a fresh editable copy. Preserve the source inputs separately when making arrangement changes; native tuning, rhythmic timing and instrumentation are independent musical choices.
