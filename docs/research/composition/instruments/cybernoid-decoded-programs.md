# Cybernoid pulse programs in a familiar phrase

Use this example for a moving-pulse bass with a brief noise attack, filtered harmonic replies and a pulse lead whose initial pitch stays clear. The [owning Cybernoid study](../cybernoid-ii-preparation.md) retains Jeroen Tel's music attribution, Charles Deenen's recovered-driver credit and the executed mechanism evidence. The [editable title](../../../../songs/cybernoid-title.json) supplies the numeric programs; preparation and playback need no original SID or captured-write replay.

**Status, 2026-10-13:** the [bounded adapter](../../../../scripts/prepare-cybernoid-elise.py) and [source-free tests](../../../../tests/cybernoid_elise_transfer_test.py) verify the complete numeric models, source-event selection, lookup mapping, gaps, native gate timing and finite fade. Both compiled versions pass full CPU/VICE checks, including two stopped calls, and render unclipped with settled final seconds. The [audio recipe](../cybernoid-elise-audio.json) pins reproduction and the [listening package](../cybernoid-ii-preparation.md#listening-package-and-reproduction) supplies both references and candidates. The listener accepted this same-material pair: “Cybernoid version works musically,” in response to the question including its ending. This acceptance is separate from the numerical checks and does not establish hardware equivalence.

## Choose and edit the programs

The [transfer](../../../../songs/cybernoid-elise-transfer.json) retains these original records and their parameter tables. All three use pulse without ring/sync coupling. Physical voice indices are zero-based.

| Role / voice | Original record and retained properties | Reason for this use |
| --- | --- | --- |
| Bass / 0 | Record 1: pulse `$41`, AD/SR `$08/$89`, initial width `$0500`, PWM slot 4, vibrato `$53` with wait 12, onset length 2 and onset wave `$81` | The short noise attack distinguishes the six bass notes; staged pulse motion continues through their bodies. The brief notes finish before the centered vibrato wait expires. |
| Harmony / 1 | Record 5: pulse `$41`, AD/SR `$00/$B8`, initial width `$0C00`, PWM slot 2, vibrato `$52` with wait 24, filter program 0 | A filtered pulse separates the twelve harmonic replies from the lead. Short source notes retain their base pitch while the delayed vibrato phase advances. |
| Melody / 2 | Record 17: pulse `$41`, AD/SR `$08/$89`, initial width `$0700`, PWM slot 1, no vibrato/onset/filter effect | Pulse motion animates the thirty-five melodic notes while each attack immediately selects its intended lookup pitch. No glide or tone arpeggio changes the familiar cadence. |

Edit `records[index]`, the selected `pulse_slots`, `vibrato_wait` and, for harmony, `filter_programs[0]`. PWM compares accumulator high bytes and retains overshoot; use the [pulse/filter functions](../../../../scripts/cybernoid_programs.py) rather than replacing this with clamped generic sweeps. Bass PWM uses stage steps `$70/$60/$50` through note ages 3/6/9, then `$60`; harmony uses `$80/$60/$40` through 4/8/12, then `$20`; the lead uses `$30`. Note initialization skips body effects. Bass age 1 substitutes noise and frequency high `$FA`; ages 2–3 restore its saved pulse/base pitch. These transient pitches belong to the retained onset program, rather than extra score notes.

Only harmony is routed through the shared filter: `sid_init.routing=$82` gives resonance 8 and physical voice 1 routing. Record 5 selects filter program 0, which starts cutoff high `$A0`, subtracts two from age 2, and retains the later source stages for longer reuse. Cutoff low remains zero. Moving this role requires updating routing intentionally; concurrent filter-enabled records would share ownership and the voice-order writes. The [named pitch component](../../../../scripts/cybernoid_pitch.py) and [caller primitives](../../../../scripts/cybernoid_state.py) own retained phase, wait and gate semantics.

## Preserved material and matched reference

The phrase is beats `[0,12)` of the [preserved Für Elise arrangement](../../../../songs/fuer-elise.json): the first repeat body and complete A-minor first ending, with all 53 source events retained. Its [score guide](../../../songs/fuer-elise-score.md) owns the edition and original-source provenance. Source pitches, event order, note-row ends and gaps are accounted for individually; no ending notes are invented. This follows the [accepted Shades familiar-transfer lesson](shades-decoded-programs.md#familiar-transfer-accepted): keep the material fixed and choose glides separately from instrument names.

The [plain reference](../../../../songs/cybernoid-elise-reference.json) has identical rows, row calendar, initial state, lookup words and ending. It selects triangle `$11` with the source arrangement's AD/SR envelopes, zero modulation and no filter routing. It is a generated same-material reference, not an original performance. Source notes replace the title's notes; the transfer retains the three original sound records rather than the original title arrangement.

## Timing, pitch and ending limits

The target is a single PAL MOS6581 with one update per 19,656 CPU cycles at clock `17734475/18` Hz, approximately 50.12 calls per second. Tempo reload 2 schedules a row decrement every three calls. Each absolute source beat boundary rounds to the nearest scheduled call, half up; `row_duration + 1` gives its scheduled intervals. The measured boundary error is at most **29.764 ms**, below the **29.925 ms** bound, without cumulative beat-rounding drift. The adapter accepts monophonic quarter-beat boundaries, rejects clipping/overlap, and limits rows to 1–128 scheduled intervals, with at least two for notes.

This is not exact source note-off timing. The zero native gate threshold clears a note's gate **three calls, 59.851 ms, before its next row**. The numeric tests confirm every retained note's initial frequency and this gate transition. The largest measured gate-end and gate-duration discrepancy from the source is **88.632 ms**. Explicit rest rows use silent record 0; loading that record replaces the preceding patch and can shorten its envelope release. Envelope decay and sounding duration still require listening.

Original lookup indices are opaque identities. The adapter chooses the nearest PAL sounding pitch among the first 87 chromatic entries and preserves the complete 257-word table in both banks. For this phrase the result is `pitchIndex = MIDI - 20`; retained tuning is **34.657–35.361 cents sharp** relative to the source's equal-tempered pitches. The per-pitch words/errors are recorded in each fixture's `sourceEvidence.pitchMapping`. Do not assume that raw index zero names MIDI 21 or extend the opaque adjacent data as a scale.

Beat 12 rounds to call **501**. The arranged tail introduces no new rows: it forces every gate low, continues eligible programs for 64 release calls, then applies sixteen four-call fade levels. Volume is zero from call 625; the export finishes after **629 calls**, approximately **12.549 seconds** including release/fade. This is an added finite ending, separate from Cybernoid's source order restart. The rendered comparison was accepted for this phrase; the native onset, early gates, tuning and shortened rest releases remain constraints when applying these programs elsewhere.

## Reproduce and reuse

Verify the saved pair, or prepare and compile into fresh paths:

```sh
python3 scripts/prepare-cybernoid-elise.py --check
python3 -m unittest discover -s tests -p 'cybernoid_elise_transfer_test.py' -v
python3 scripts/prepare-cybernoid-elise.py --transfer-output build/cybernoid-elise-reuse-new/transfer.json --reference-output build/cybernoid-elise-reuse-new/reference.json
PYTHONPATH=.tools/test-deps python3 scripts/compose-cybernoid.py build/cybernoid-elise-reuse-new/transfer.json --output build/cybernoid-elise-reuse-new/candidate
PYTHONPATH=.tools/test-deps python3 scripts/compose-cybernoid.py build/cybernoid-elise-reuse-new/reference.json --output build/cybernoid-elise-reuse-new/reference
```

The adapter prints input/output fingerprints, event counts, per-pitch tuning and timing errors. Existing outputs are rejected; `--check` is read-only. Edit the source notes through an alternate `--source`, or the numeric program bank through `--programs`, then regenerate both matching descriptions. Timing edits require rebuilding the absolute row calendar. Preserve the plain pair, source hashes and listening judgment when promoting another phrase through the [decoded-song workflow](../../../workflows/decoded-song-workflow.md).
