# Ghouls pulse and staged-onset programs on familiar material

The [Ghouls study](../ghouls-preparation.md) owns source attribution and the complete reconstruction. This card describes selected programs reused on the same 53 notes of [Für Elise](../../../../songs/fuer-elise.json), beats `[0,12)`, with a generated plain reference. Numeric preparation, both compiled players, full callable VICE playback and rendered release are verified. Instruments, balance and ending are accepted, with a tentative tune reservation; the declared reuse scope is closed with that qualification.

## Musical purpose and patch selection

| Role / destination voice | Source entry, zero-based voice and call | Reused behavior |
| --- | --- | --- |
| Melody / 1 | Voice 2, call 1413 | Uncoupled pulse body with width step 100; native phase continues between notes when the pulse default is zero |
| Bass / 2 | Voice 1, call 1413 | Triangle body preceded by one PAL call of noise; body pitch is restored by the delayed-onset program |
| Harmony / 3 | Voice 2, call 1413 | The same moving pulse body on the preserved accompaniment notes |

The selected source patches have no filter routing, pitch sweeps, alternating-note replacement, glide, ring modulation or oscillator synchronization. This keeps the familiar notes identifiable while testing pulse motion and a staged attack. It does not establish that every Ghouls program is transferable to an arbitrary melody, or a general Follin sound. The [Gauntlet III comparison](../follin-contrast.md) corroborates the selected staged-onset and zero-default phase-retention contracts. Nonzero pulse defaults reset phase in that same reference; preservation is a patch choice, not a universal behavior. Natural rests are absent from its selected passage, so rest continuation is supported by a controlled score edit. Joint Tim and Geoff Follin credit remains explicit. The listener finds the original Gauntlet pulse more animated and hears its “chiptuning” character diminished by the stationary diagnostic; that verdict is scoped to this two-parameter comparison.

## Editable source and reproduction

[prepare-ghouls-elise.py](../../../../scripts/studies/ghouls/prepare-ghouls-elise.py) observes the selected positive-note entries in the independent [numeric player](../../../../scripts/ghouls_player.py). It captures named program parameters, pulse phase/default/fallback, shared-filter state and the actual envelope stores. It needs no original SID. Previous-note pitch and countdown transients are cleared before the first score row; PWM is admitted by a setup waveform command immediately before each voice's first positive note, after its initial gap. This preserves the captured starting phase instead of warming PWM silently before the phrase; later rests retain native continuing motion.

The [transfer](../../../../songs/ghouls-elise-transfer.json) and [plain reference](../../../../songs/ghouls-elise-reference.json) retain the same notes, durations, gaps and navigation. Setup envelope/waveform stores and gate-off waveform bits differ. The reference uses the source score's triangle/envelope settings and disables staged onset and PWM; it is generated from the preserved score, not an original recording.

```sh
python3 scripts/studies/ghouls/prepare-ghouls-elise.py --check
python3 scripts/listening-package.py config/listening/ghouls-elise-transfer.json --output build/ghouls-elise-transfer
```

[The listening recipe](../../../../config/listening/ghouls-elise-transfer.json) checks preparation, both compiled players, VICE execution, rendered signal and the release tail, then supplies the plain-first comparison and separate full files through `build/ghouls-elise-transfer/listening.md`. The [successful run](../../../../evidence/ghouls-elise-transfer/run.json) retains all execution and audio fingerprints. The full [candidate](../../../../evidence/ghouls-elise-transfer/candidate/verification.json) and [reference](../../../../evidence/ghouls-elise-transfer/reference/verification.json) CPU proofs and their VICE records cover every declared call; musical judgment remains separate.

The submitted files are `build/ghouls-elise-listening/plain-then-ghouls.ab.wav`, `plain-reference.wav` and `ghouls-transfer.wav`, with the generated plain reference first in the 29.1-second comparison. The [submission record](../../../../evidence/ghouls-elise-transfer/listening-review.json) pins their hashes; the [subsequent verdict](../../../../evidence/ghouls-elise-transfer/listening-verdict.json) records the qualified acceptance. Use [publish-listening.py](../../../../scripts/publish-listening.py) with the completed run and [audition selection](../../../../config/listening/ghouls-elise-transfer.audition.json) to recreate a fresh stable folder.

## Listening verdict and independent pitch review

On 2026-10-13 the listener said the instruments, balance and ending work musically, but heard a “slightly wrong tune (I am not really sure, though)”. Retain that uncertainty rather than treating this as unqualified melodic-fidelity acceptance.

The [independent pitch review](../../../../evidence/ghouls-elise-transfer/pitch-review.json) decodes the retained compiled candidate/reference SID stores directly, without the preparer's MIDI-to-native-note formula. All 35 melody, 6 bass and 12 harmony tonal bodies match the source's nearest MIDI notes; scheduled gate-on calls, gate-offs and gaps also match. Both versions have identical tonal frequency words. Their tuning is **+34.6568 to +35.3614 cents sharp** of A440 equal temperament, with a largest successive-interval error below 0.45 cents. The six bass attacks briefly use noise and restore the correct tonal words one call later; no unexpected body-pitch changes occur.

No note-mapping defect was found. Shared native tuning could differ from a remembered performance, but cannot explain a candidate-versus-plain difference by itself. Pulse timbre/PWM, noise attacks and release continuing through earlier gaps are plausible perceptual influences only; the cause remains unknown. One SID voice retains its current oscillator pitch during release, rather than mixing independent old and new pitches. This review compares the existing source score, not an external edition or performance, and cannot settle the listener's impression.

Rerun the [retained probe](../../../../evidence/ghouls-elise-transfer/pitch-review.py) with the local submitted WAVs and compiled build artifacts present; it checks their pins and creates a fresh report without rendering or capturing again:

```sh
python3 evidence/ghouls-elise-transfer/pitch-review.py --output build/ghouls-transfer-pitch-review-new
```

## Articulation, tuning and ending limits

All 35 melody, 6 bass and 12 harmony notes are preserved. Absolute source beat boundaries round to PAL calls, with a maximum boundary error of 9.81345 ms in this phrase. Both descriptions retain Ghouls' native tuning; the signed deviations and compiled-store checks are retained in the [pitch review](#listening-verdict-and-independent-pitch-review), rather than claiming concert-pitch accuracy.

The source gate-time value 1 would release one call before a following row. This transfer deliberately uses explicit control-register gate-offs at the preserved note ends, with gate-time/rest-reload values 255 preventing an earlier scheduler release for these bounded rows. A gate-off store leaves PWM phase intact. The following note still uses native positive-note setup, so the one-call noise attack remains part of the bass articulation. Preparation rejects a note too short for its delayed onset, preventing a pending attack from reopening the gate during the following rest.

All voices are gated off and disable at call 501, the quantized twelve-beat boundary. The initial untouched source release nibble 15 sustained the final chord until approximately 33 seconds: the [diagnostic](../../../../evidence/ghouls-elise-transfer/native-release/profile.json) measured AC RMS 1,679 at `[13,14)` seconds and zero from `[33,34)` onward. Stopping capture after three release seconds cut that decay short. The exact independently assembled prototype is retained beside the diagnostic for inspection; it is not the submitted arrangement.

The delivered transfer deliberately changes only each voice's final note release nibble from 15 to 9 immediately before its last gate-off, preserving the sustain nibble. Earlier notes keep their source envelope, including release continuing through score gaps. The plain reference keeps its source release nibble zero. This is an explicit phrase-ending adaptation, with no extra notes or master-volume fade. Both descriptions then allow three release seconds plus 64 confirmation calls, for 717 calls and 14.30436 rendered seconds. [Both final one-second windows](../../../../evidence/ghouls-elise-transfer/audio.json) have zero AC RMS and neither render clips. The listener separately accepted the ending.

## Reuse outcome

Reused unchanged: the complete numeric scheduler, native positive-note setup, pulse motion and delayed-onset implementation. New material: a deterministic familiar-score graph and matched plain reference. Deliberate adaptations: source voice reassignment, cleared previous-note transients, zero transpose, explicit source-boundary articulation and a shorter release for each final note. One technical audio revision replaced the cut-off long native release before submission. Instruments, balance and ending are accepted with the tune reservation preserved; the bounded Gauntlet corroboration is also complete. This closes the declared Ghouls/Follin scope. No productivity improvement is inferred from numeric agreement or this listening verdict alone.
