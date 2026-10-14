# Deflektor tonal programs on familiar material

The three selected Deflektor pulse programs work musically on a different, familiar score: on 2026-10-14 the listener judged the matched Für Elise transfer **“instruments, balance and ending work musically”**. The [structured verdict](../../../../songs/studies/deflektor-elise-transfer/listening-review.json) binds that acceptance to the exact submitted audio. The [primary study](../deflektor-preparation.md#compiled-export-and-listening-package) owns the original source and accepted reconstruction phrase/ending.

## Choose by musical role

| Role | Selected source record | Useful behavior and boundary |
| --- | --- | --- |
| Melody | Record 6 | Moving pulse plus delayed raw-frequency-word motion on longer holds; a 30-body-call delay leaves shorter notes unaffected. Pitch excursion in cents depends on the note. |
| Bass | Record 3 | Moving pulse with sustained body and release; low-byte-only PWM arithmetic and retained phase differ from an ordinary full-word pulse sweep. |
| Harmony | Record 7 | Faster low-byte pulse motion with zero sustain; supports short responses in this accepted phrase. Suitability for other mixes remains a listening question. |

All three are uncoupled pulse programs, with no SYNC/RING or waveform macro. The shared resonance updates remain numerically ordered but filter routing and modes are clear; no audible filter effect is claimed. This palette does not include the title's staged percussion candidate, whose precise cowbell attribution remains unresolved. The [Trap contrast](../daglish-contrast.md) also shows why the inactive filter path is specific to this case, not a general Daglish characteristic.

The [editable example and mechanism contract](../../../../songs/studies/deflektor-elise-transfer/README.md) owns exact patch fields, observed source contexts, aliased tables, native-versus-computed tradeoffs, pitch mapping, timing and ending adaptations. Its [mapping](../../../../songs/studies/deflektor-elise-transfer/mapping.json), [candidate](../../../../songs/studies/deflektor-elise-transfer/transfer.json) and [plain reference](../../../../songs/studies/deflektor-elise-transfer/reference.json) are portable workfiles. Use the computed backend to preserve the verified target/marker algorithms and row-boundary interaction; do not translate its low-byte movement directly to a full-word native PWM sweep.

## Reproduce and assess

```sh
python3 scripts/listening-package.py config/listening/deflektor-elise-transfer.json --output build/deflektor-elise-transfer
python3 scripts/publish-listening.py build/deflektor-elise-transfer/run.json --selection config/listening/deflektor-elise-transfer.audition.json --output build/deflektor-elise-listening
```

The [completed run](../../../../evidence/deflektor-elise-transfer/run.json) covers deterministic preparation, all 717 calls of both independently compiled descriptions, full callable VICE playback, rendered signal and the same-material comparison. All 53 source notes, quantized onsets and native gate-end times are preserved; final rows deliberately keep release programs running before the shared stop. The [pre-stop measurement](../../../../evidence/deflektor-elise-transfer/pre-stop-tail.json) finds zero AC RMS for both versions in seconds 12.507592–12.957592, before control zero at approximately 13.007592 seconds. This distinguishes an already-settled release from silence caused only by cutting the waveform. The final post-stop window is independently checked by the recipe. Neither measurement replaces the accepted musical ending verdict.

To reproduce the pre-stop measurement from the published files, use the existing window tool; each input’s `window` measurement in the resulting comparison JSON reports AC RMS:

```sh
python3 scripts/compare-audio.py window build/deflektor-elise-listening/plain-reference.wav build/deflektor-elise-listening/deflektor-transfer.wav build/deflektor-pre-stop-check --start-seconds 12.507592048820165 --end-seconds 12.957592048820165 --gap-seconds 0
```

The [submitted pair](../../../../evidence/deflektor-elise-transfer/listening-submission.json) is `build/deflektor-elise-listening/plain-then-deflektor.ab.wav`, approximately 29.1 seconds: generated plain Für Elise first, the same phrase with Deflektor programs second. Separate files are `plain-reference.wav` and `deflektor-transfer.wav` in that folder. Both share native pitch words and scheduling; this is a timbral/program transfer, not a comparison with an original Beethoven recording.

Model-assistance review, 2026-10-14, first transfer audition and feedback: skip another model call because the tested configurations remain unqualified for musical balance and ending judgments. Human feedback directly accepts this submitted example; no model score is needed to select it. Keep eligibility experimental under the [standing review rule](../../audio-assessment.md#use-and-reassess-model-assistance), with the next review at Daglish case closure or a substantive new revision.
