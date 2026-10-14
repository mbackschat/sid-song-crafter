# Bach Toccata: complete interpretation with integrated lead motion

This separate full-song extension applies the [listening-accepted opening's pulse program](../bach-toccata-integrated-motion/README.md) to the [accepted complete mono Toccata](../bach-toccata-full/README.md). **Full-song listening is pending.** The opening's [recorded acceptance](../bach-toccata-integrated-motion/listening-review.json), “yes, better. I like it”, approves that opening only.

- [Score](score.json): byte-identical to the accepted full score, retaining its 895 arranged notes, 84.6025-second musical span, source reductions and final cadence. The [accepted source preparation](../bach-toccata-full/preparation.json) remains the owning event/source ledger.
- [Native recipe](hybrid.json): only `instruments.lead.pulse` changes from the accepted full recipe. It uses the exact [opening program](../bach-toccata-integrated-motion/hybrid.json) and [pulse specification and oracle](../bach-toccata-integrated-motion/preparation.json). Pitches, lead waveform and envelope, bass, harmony, chord cycles, shared filter, pacing and release tail retain their accepted definitions.
- [Paired listening recipe](../../../config/listening/bach-toccata-integrated-full.json): builds both complete versions, renders them at their original levels, checks that only lead pulse-width frame registers differ, and runs standalone VICE checkpoints through the ending. The [run receipt](../../../build/bach-integrated-full/run.json) and [listening index](../../../build/bach-integrated-full/listening.md) retain execution results and audio paths separately from human judgment.

```sh
python3 scripts/listening-package.py config/listening/bach-toccata-integrated-full.json --output build/bach-integrated-full
```

Target: one MOS8580 at `$D400`, PAL, A=440 Hz and pinned SID-Wizard 1.97 Extra at 1x. This is an original timbral revision using accepted Bach inputs and written intentions; no Gyruss binary, traces, extracted notes, audio or program was consulted for this design. Full-song review asks whether the accepted opening's integrated motion remains useful through the runs, chord pillars and final hold. Model-assistance review: skip unvalidated preference inference; human full-song feedback is the next checkpoint.
