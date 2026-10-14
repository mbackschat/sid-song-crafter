# Take On Me pulse lead and filtered bass

The listener accepted the matched Für Elise transfer on 2026-10-14: **“they work musically”**, answering whether its instruments, balance and ending work. The [scoped verdict](../../../../songs/studies/take-on-me-elise/listening-review.json) binds that judgment to the submitted pair. This is a reusable tonal palette recovered from Pascal van Loosbroek’s C64 arrangement of a-ha’s *Take On Me*; the [owning study](../take-on-me-preparation.md) retains source attribution and accepted reconstruction comparisons. It does not establish a composer-wide style or imply unrestricted rights to the source arrangement.

## Choose by musical role

| Role | Editable source record | Behavior and constraint |
| --- | --- | --- |
| Melody and harmonic replies | Instrument 1 | Pulse body, one-way pulse-width descent and delayed pitch motion; AD `$02`, SR `$5C`, native half-gate and release program 2. Its movement can develop on longer notes, while shorter notes retain the early program phases. |
| Bass and filter anchor | Instrument 3 | Bidirectional pulse-width motion with AD `$00`, SR `$64`; physical voice 1 owns the shared descending filter program and release program 1. |

The accepted transfer uses bass on physical voice 1, harmony on voice 2 and melody on voice 3. No SYNC/RING coupling is needed. Filter routing/mode belong to the shared mix; moving the bass to another voice requires revisiting the explicit owner and routing, not merely swapping note rows. The source’s arpeggiated saw and waveform/pitch percussion records remain verified parts of the title but are not included in this accepted tonal transfer.

The [editable example](../../../../songs/studies/take-on-me-elise/README.md) owns exact parameter fields, note mapping, tuning, articulation and ending adaptations. Its [candidate](../../../../songs/studies/take-on-me-elise/transfer.json) and [generated plain reference](../../../../songs/studies/take-on-me-elise/reference.json) use the same 53 score notes. The [preparation receipt](../../../../songs/studies/take-on-me-elise/preparation.json) records every event and its timing error. Change the numeric program fields and rebuild through the [runtime compiler](../../../workflows/decoded-song-workflow.md#take-on-me-runtime-score-and-sound-programs); captured writes are verification output, not editable instrument source.

## Reproduce and assess

```sh
python3 scripts/listening-package.py config/listening/take-on-me-elise-transfer.json --output build/take-on-me-elise-transfer-work
python3 scripts/publish-listening.py build/take-on-me-elise-transfer-work/run.json --selection config/listening/take-on-me-elise-transfer.audition.json --output build/take-on-me-elise-listening
```

Publication requires a fresh destination. The [complete recipe](../../../../evidence/take-on-me-elise/run.json) took 10.53 seconds on 2026-10-14 and covers preparation, both 599-call compiled descriptions, poisoned reset, modeled standalone bootstrap, complete callable VICE playback and two twelve-second renders. CPU and VICE agree on 8,690 stores for the plain reference and 8,737 for the candidate; both VICE cadence errors stay within 5 cycles. Peak candidate play cost is 1,769 of 19,656 PAL cycles. [PCM checks](../../../../evidence/take-on-me-elise/audio.json) find no clipping and zero final-second AC RMS for both versions. Hardware playback and within-call bus timing remain unverified.

Listen to [plain-then-take-on-me.ab.wav](../../../../build/take-on-me-elise-listening/plain-then-take-on-me.ab.wav), 24.5 seconds with the generated plain reference first. Separate [plain reference](../../../../build/take-on-me-elise-listening/plain-reference.wav) and [transfer](../../../../build/take-on-me-elise-listening/take-on-me-transfer.wav) retain unity gain. The [submission](../../../../evidence/take-on-me-elise/listening/submission.json) preserves their fingerprints. This is a same-material instrument comparison, not an original Beethoven recording. Playback equipment was not recorded.

## Reuse outcome and limits

The transfer uses beats `[0,12)` of [the preserved Für Elise score](../../../../songs/fuer-elise.json) at BPM 72: 35 melody, six bass and twelve harmony note setups. Original instrument/program fields are reused unchanged except the explicitly replaced frequency lookup. Both versions use PAL A440 tuning, with selected words within 0.319 cents; the original title retains its approximately 65-cent-flat native table. Do not interpret that tuning difference as evidence of an NTSC source. Scheduling rounds absolute boundaries to even PAL calls; maximum boundary error is 19.299 ms. The [workfile README](../../../../songs/studies/take-on-me-elise/README.md) explains native gate shortening, plain legato and silent-row release truncation, which are audible articulation choices beyond nominal note identity.

New work was a deterministic score-to-backend preparer and explicit plain-reference patches; the title compiler and sound programs were reused. There were **zero listening-driven revisions** before acceptance of this submitted phrase. Effort to acceptance was not recorded reliably; the 10.53-second recipe measurement is routine execution time, not total engineering effort. The next arrangement can reuse the preparation pattern and compiler rather than repeat source decoding. Other ranges, tempos, mixes and regional targets require their own numeric and listening checks; this study backend currently targets PAL/MOS8580 only.

Model-assistance review at first transfer audition, feedback and case closure (2026-10-14): no call. Current models are not calibrated for musical balance or natural ending judgments, and the listener identified no unresolved defect. Retain them as experimental supporting signals under the [standing review rule](../../audio-assessment.md#use-and-reassess-model-assistance); reassess in the next musical case or after a substantive revision.
