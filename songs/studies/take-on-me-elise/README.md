# Take On Me programs on Für Elise

This is a matched twelve-beat transfer of [the preserved common score](../../fuer-elise.json), using the editable sound bank from [the independent Take On Me composition](../../../evidence/take-on-me-player/composition.json). Numeric preparation, complete compiled CPU/VICE playback and rendered signal checks pass. On 2026-10-14 the listener answered **“they work musically”** for the instruments, balance and ending; the [scoped verdict](listening-review.json) and [reusable instrument card](../../../docs/research/composition/instruments/take-on-me-decoded-programs.md) preserve that acceptance.

- [Plain reference](reference.json): source triangle waveform and role-specific AD/SR envelopes, with modulation and filter disabled.
- [Native transfer](transfer.json): original Take On Me pulse, delayed vibrato, sweep, gate and release programs, with the explicit tuning adaptation below.
- [Preparation receipt](preparation.json): source/table/tool hashes, all 53 retained events, pitch mapping, boundary and duration errors, role assignments and output fingerprints.
- [Owning Take On Me study](../../../docs/research/composition/take-on-me-preparation.md): executed source evidence, native parameter contracts and remaining musical decisions.

| Role | Physical SID voice | Native instrument | Plain instrument |
| --- | --- | --- | --- |
| Bass | 1 | Source record 3; shared-filter owner | Triangle with source bass AD/SR |
| Harmony | 2 | Source record 1; lead pulse program | Triangle with source harmony AD/SR |
| Melody | 3 | Source record 1; lead pulse program | Triangle with source melody AD/SR |

Both versions preserve the 35 melody, six bass and twelve harmony note setups, pitch identities and nominal durations from beats `[0,12)` at quarter-note BPM 72. No percussion or arpeggio notes are added. Absolute event starts and ends round to the nearest even PAL call because native duration units count two calls. The preparation rejects collapsed notes, collapsed source gaps and overlaps. Its recorded maximum boundary error is 19.299 ms and maximum nominal-duration error is 31.070 ms.

The title's native frequency table remains unchanged in its own composition. For this familiar phrase, both comparison banks are explicitly retuned to A440 equal temperament with `pitchIndex = MIDI - 12` and `frequencyWord = round(targetHz × 2^24 / (17734475 / 18))`. The selected native words are 64.743–65.703 cents flat relative to that mapping; the retuned selected words deviate by at most 0.319 cents. Unused index 95 would exceed the SID's 16-bit range after retuning and is omitted; required out-of-range pitches are rejected, never clamped. Native and retuned table hashes and per-pitch consequences are retained in the preparation receipt.

Fresh zero modulation state replaces incidental initialized source data. The candidate retains all original instrument and program parameters except its explicitly replaced frequency table. Physical voice 1 alone resets and advances the shared filter; lead and harmony preserve its state. During source gaps, silent instrument 0 clears the waveform after the preceding note's native gate/release rules have run. This may cut remaining envelope energy at the nominal gap boundary. The plain triangle holds GATE between contiguous note setups and drops it on silent rows; a nominal note setup is not necessarily a fresh envelope attack. Native half-gate and release thresholds can shorten its sounding span, while delayed vibrato can move its pitch during a longer note. These articulation differences are part of the comparison and are not extra score events.

The authored phrase ending starts at call 502. After 32 calls of gate-off release, call 534 clears waveform and master volume; the declared range includes that stop and 64 confirmation calls, for 599 calls total. This is a selected finite ending for the transfer, not the archived title's natural ending. Numeric stopped state does not establish acoustic settling or musical quality.

```sh
python3 scripts/studies/take-on-me/prepare-elise.py --check
python3 tests/take_on_me_transfer_test.py -v
```

The preparer defaults to this directory and exclusively creates `reference.json`, `transfer.json` and `preparation.json` when they do not exist. Use `--output build/take-on-me-elise-preparation` for fresh generation; `--check` verifies saved bytes without writing. It reads the common score and canonical numeric composition, requires no original SID binary, and leaves both inputs unchanged.

The listening question is whether the native lead pulse and filtered bass remain clear and useful on the familiar phrase while its melody and harmonic replies remain recognizable. The submitted familiar phrase is accepted; this does not qualify every arrangement, register or tempo.
