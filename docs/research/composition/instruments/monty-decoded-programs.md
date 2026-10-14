# Monty tonal programs in a familiar phrase

Use this example for a narrow pulse bass, short pulse replies and a moving-pulse melody. The [owning Monty study](../monty-preparation.md) retains Rob Hubbard's SID credit, the separate Charles Williams inspiration attribution, source pins and executed program evidence. The [editable title source](../../../../songs/monty-title-source.json) supplies twenty named numeric records and 96 frequency words; the [independent player](../../../../scripts/monty_title_player.py) computes score and sound state without the original driver or captured-write replay.

**Status, 2026-10-13: listening accepted.** The listener reports “music is spot on” for this familiar Für Elise pair, in response to the musical-use question including its ending. The [bounded adapter](../../../../scripts/studies/monty/prepare-monty-elise.py) and [transfer guards](../../../../tests/monty_elise_test.py) independently verify every source-note onset, initial frequency and scheduled gate release, the matched plain pair and complete finite numeric execution. Both compiled exports match all 630 calls and eleven named-state/shared-bank checkpoints against the pure model: 1,396 ordered stores for the plain reference and 2,832 for the Monty candidate, including initialization. VICE matches all 632 play calls, including two stopped calls with no SID stores; maximum cadence error is seven cycles. Both fifteen-second renders have no PCM rail samples and zero AC energy in their final second. The [audio recipe](../monty-elise-audio.json) retains the scoped verdict, hashes, CPU/VICE receipts, renderer settings and measured PCM. This acceptance applies to the presented phrase and mix, not arbitrary material or hardware equivalence.


## Listen

[Plain then Monty](../../../../build/monty-elise-transfer/listening/plain-then-monty.ab.wav) presents both complete fifteen-second renders with a half-second gap. The comparison matches full-file AC RMS by attenuation: plain reference at unity, Monty at **−4.721 dB**. Separate original-level full files are [plain reference](../../../../build/monty-elise-transfer/reference/reference.wav) and [Monty candidate](../../../../build/monty-elise-transfer/candidate/reconstructed.wav).

The [ending pair](../../../../build/monty-elise-transfer/listening/ending-plain-then-monty.ab.wav) copies seconds 8–14 from each raw render at unity gain, plain first, with the same half-second gap; it has no normalization or added fade. It includes the approach to the ending and settled tail. The last second of each full render is constant sample −157 with AC RMS zero, retaining SIDLite's DC offset rather than claiming zero-valued PCM.

## Choose and edit the programs

The [transfer](../../../../songs/monty-elise-transfer.json) preserves these actual loaded records. All selected records use pulse without ring/sync coupling or drum, saved-high descent and octave pitch replacement; physical voice indices are zero-based.

| Role / voice | Native record and retained parameters | Purpose and constraint |
| --- | --- | --- |
| Bass / 0 | Record 2: pulse `$41`, width `$02A0`, AD/SR `$09/$80`, no vibrato or PWM, effects 0 | A narrow tonal pulse gives the six short bass notes a distinct attack while retaining their source pitches. |
| Harmony / 1 | Record 6: pulse `$41`, width `$0800`, AD/SR `$04/$40`, vibrato depth 2, no PWM, effects 0 | Twelve brief harmonic replies use the native envelope. Their duration fields are below eight, so the native vibrato program advances without pitch displacement. |
| Melody / 2 | Record 15: pulse `$41`, width `$0900`, AD/SR `$19/$70`, vibrato depth 2, packed PWM `$A8`, effects 0 | Shared pulse motion continues across the thirty-five melody notes; longer notes admit native vibrato displacement. |

Edit `instruments[index].pulse_word`, `waveform`, `attack_decay`, `sustain_release`, `vibrato_depth`, `pulse_value` and `effects` in an alternate `--programs` description. The packed PWM byte uses `value & $E0` as its step and `value & $1F` as its delay reload; `$A8` therefore supplies step `$A0` and reload 8. The [sound helper](../../../../scripts/monty_title_programs.py) retains native arithmetic: updates wrap at twelve bits, and high-byte equality `$E` or `$8` changes direction without clamping. Note setup skips body programs that call.

Pulse width belongs to the mutable instrument bank, while delay and direction belong to each voice. If two voices select the same record, both change its width in voice order 2, 1, 0. New notes, appends and order restarts retain these phases; installing a fixed onset width on every note would erase the decoded mechanism. This transfer explicitly starts delay/direction and held voice state at zero for the different material, rather than inheriting the title's loaded state. Record widths remain their source values. The original title also binds raw note 104 to live voice-control bytes, with stage-specific adjacent and octave lookups; this phrase uses ordinary table indices and introduces no such alias pitches.

## Preserved material and plain reference

The phrase is beats `[0,12)` of the [preserved Für Elise arrangement](../../../../songs/fuer-elise.json), with all **53 source events** retained: 35 melody, six bass and twelve harmony notes. The [score guide](../../../songs/fuer-elise-score.md) owns the edition and original-source provenance. Source notes, order and real gaps are preserved; the title's score is replaced by packed numeric Monty orders and patterns. Silent record 20 is added for gaps, with waveform, ADSR and effects zero.

The [plain reference](../../../../songs/monty-elise-reference.json) uses identical score bytes, initial state, pitch words, calendar and finite ending. Selected records become triangle `$11` with the source arrangement's AD/SR envelopes and no modulation. It is a generated same-material reference, not an original performance. The transfer and plain pair share native articulation and rest limitations, allowing a listening comparison of these timbre choices.

## Timing, pitch and ending limits

The target is one PAL MOS6581 at `$D400`, with one call per 19,656 CPU cycles at clock `17734475/18` Hz. Tempo reload 1 schedules score decrements every two calls. Absolute beat boundaries round independently to the nearest two-call boundary, half up, so timing error does not accumulate. For this phrase, measured boundary error is at most **19.299 ms**, below the **19.950 ms** bound. The adapter accepts monophonic quarter-beat boundaries and rejects overlap, clipping and notes outside 2–32 scheduled intervals; longer gaps split into silent rows.

A duration field counts remaining score ticks after initialization. With the native sustain-control bit clear, scheduled gate release occurs **two calls, 39.901 ms, before the next row**; the largest source gate-end and gate-duration discrepancy is **57.561 ms**. New-note setup writes the selected control without a universal gate-off or TEST prelude, so adjacent notes do not guarantee a fresh envelope attack. Loading a silent rest record replaces the preceding ADSR patch and can shorten its release. These are retained player semantics, separate from calendar rounding and from an audible judgment.

The adapter chooses the nearest PAL sounding pitch among the exact 96 source words and retains them in both descriptions. For these notes, the selected index equals `MIDI - 12`; measured base-pitch errors span approximately **−0.980 to +0.402 cents**, with per-pitch words and errors in each fixture's `sourceEvidence.pitchMapping`. Native vibrato adds its own displacement when enabled; this base-pitch measurement does not describe the entire sounding note. Do not extrapolate the title's live-state aliases into a chromatic extension.

Beat 12 rounds to call **502**. The added finite ending freezes score scheduling, clears actual gates while retaining saved controls, continues sound programs for 64 release calls, then applies sixteen four-call fade levels. Volume reaches zero at call **626**, and the complete description ends after **630 calls**, approximately **12.569 seconds** including the tail. No ending notes are invented. This arrangement ending is separate from the original title's order restart; oscillator, envelope, rendered silence and perceptual results require their respective evidence.

## Reuse outcome

| Item | Recorded result |
| --- | --- |
| Material | All 53 events from preserved Für Elise beats `[0,12)`, with the same-material generated plain reference |
| Reused unchanged | Native records 2/6/15, frequency words, independent scheduler, sound programs and finite-ending engine |
| Adapted | New packed score and zeroed starting voice phases; added silent rest record 20 |
| New work | Source-backed phrase adapter, plain-reference bank and paired verification/listening package |
| Listening-driven revisions | None requested for this pair; first presented version accepted as “music is spot on” |
| Effort | Active time and parallel-agent effort not recorded; no measured productivity claim |

## Reproduce and reuse

These commands use the checked-in numeric descriptions and source arrangement, without the original SID:

```sh
python3 scripts/studies/monty/prepare-monty-elise.py --check
python3 -m unittest discover -s tests -p 'monty_elise_test.py' -v
python3 scripts/studies/monty/prepare-monty-elise.py --transfer-output build/monty-elise-reuse-new/transfer.json --reference-output build/monty-elise-reuse-new/reference.json
```

The [audio recipe](../monty-elise-audio.json) supplies complete fresh-path compile, VICE, render, comparison and PCM-measurement commands with the checked code/library fingerprints. The adapter reports source/output fingerprints, retained event counts, tuning and timing errors. Existing output paths reject; `--check` is read-only. Use alternate `--source` or `--programs` inputs to regenerate both matching descriptions. Retain the plain pair and a scoped listening judgment when applying these programs to different material through the [decoded-song workflow](../../../workflows/decoded-song-workflow.md).

The [bounded Commando contrast](../hubbard-contrast.md) corroborates shared mutable instrument-bank state but narrows arithmetic reuse: its observed pulse motion is low-byte ADC, not Monty’s full-word bidirectional PWM. Commando also executes brief same-voice noise substitutions. These findings do not change this accepted transfer’s selected records or establish a universal Hubbard instrument contract.
