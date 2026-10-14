# Billie Jean pulse lead and filtered support

This editable tonal palette has complete numeric, CPU/VICE and rendered validation; **human musical acceptance is pending**. It comes from Johannes Bjerregaard's SID arrangement of Michael Jackson's *Billie Jean*. The [owning study](../billie-jean-preparation.md) retains source attribution and the separate reconstruction evidence. Do not treat technical agreement as evidence that this palette suits every arrangement.

## Select by musical role and shared state

| Transfer role | Instrument offset / physical voice | Behavior and constraint |
| --- | --- | --- |
| Melody | 88 / 1 | Pulse body and delayed vibrato; relative root then two `+24` attack stages. No sync/ring dependency or shared cutoff reset. |
| Bass | 32 / 2 | Filtered pulse with one `+1` attack stage; fixed cutoff high 32 and mode 48. |
| Harmony | 24 / 3 | Four `+12` attack stages before root pulse; uses the same fixed cutoff/mode as bass. Moving this record from source physical voice 2 to 3 is an explicit adaptation. |

Filter updates run in physical order 3, 2, 1. Both support voices are routed through the shared filter. An unfiltered patch can still reset cutoff during setup: offset 72 was excluded because it initializes cutoff to zero. Offset 96 was excluded because its sync stages depend on the companion oscillator. Routing and audible filtering are not sufficient to determine setup ownership; inspect both note setup and continuing bodies before combining patches.

The [editable example](../../../../songs/studies/billie-jean-elise/README.md), [candidate](../../../../songs/studies/billie-jean-elise/transfer.json) and [plain reference](../../../../songs/studies/billie-jean-elise/reference.json) share 53 nominal Für Elise notes. The [preparer](../../../../scripts/studies/billie-jean/prepare-elise.py) derives palette provenance from verified source contexts, preserves the native bank except explicit frequency retuning and records every adaptation in the [report](../../../../songs/studies/billie-jean-elise/preparation.json). Its role assignments are design choices, not claims that a numbered source voice was perceptually identified by the listener.

## Reproduce and assess

Run the [matched-transfer recipe](../../../../config/listening/billie-jean-elise-transfer.json) and publication commands in the example README. The [completed run](../../../../evidence/billie-jean-elise/run.json) verifies both 598-call exports, poisoned reset and actual modeled PRG bootstrap, full callable VICE playback and two twelve-second renders. CPU/VICE agree on 9,458 plain-reference stores and 10,407 candidate stores; maximum candidate cost is 1,692 of 19,656 PAL cycles and both VICE cadence errors stay within five cycles. [PCM checks](../../../../evidence/billie-jean-elise/audio.json) find no clipping and zero final-second AC RMS in both renders. These checks do not establish hardware equivalence or musical acceptance.

Listen to [plain-then-billie-jean.ab.wav](../../../../build/billie-jean-elise-listening/plain-then-billie-jean.ab.wav), 24.5 seconds with the generated reference first. The [submission](../../../../evidence/billie-jean-elise/listening/submission.json) binds the pair to the checks. Judge instruments, balance and ending; native octave/semitone attack gestures, vibrato and shortened articulation remain audible candidates, despite identical nominal score notes.

Both banks use A440, with nominal frequency-word error within 0.319 cents. An unused overflowing high index is omitted, not clamped. Required attack pitches are validated separately from base notes. Absolute score boundaries are rounded to three-call positions; maximum boundary and duration errors are 29.764 ms and 31.070 ms. The title retains native tuning and cold state; the transfer uses complete fresh named state. This study backend supports PAL/MOS6581 only; the project's general native regional exporter is a separate contract.

First-audition model-assistance review: no call. Fine timbral fidelity, musical balance and natural endings remain outside calibrated model eligibility. Models remain experimental supporting signals under the [standing rule](../../audio-assessment.md#use-and-reassess-model-assistance); reassess after listener feedback/revision and before closure. Routine recipe execution took 22.69 seconds on 2026-10-14; this is not a measurement of engineering effort or time to musical acceptance.
